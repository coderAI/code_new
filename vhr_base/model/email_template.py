# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from datetime import datetime
from openerp import tools
from openerp import netsvc
import base64
from openerp import SUPERUSER_ID
import logging

_logger = logging.getLogger(__name__)

class email_template(osv.osv):
    _inherit = "email.template"
    
    _columns = {
                'email_bcc': fields.char('Bcc', help="Blind carbon copy recipients (placeholders may be used here)"),
                }
    
    def generate_email_batch(self, cr, uid, template_id, res_ids, context=None, fields=None):
        """Generates an email from the template for given the given model based on
        records given by res_ids.

        :param template_id: id of the template to render.
        :param res_id: id of the record to use for rendering the template (model
                       is taken from template definition)
        :returns: a dict containing all relevant fields for creating a new
                  mail.mail entry, with one extra key ``attachments``, in the
                  format [(report_name, data)] where data is base64 encoded.
        """
        if context is None:
            context = {}
        if fields is None:
            #NG: add email_bcc to fields
            fields = ['subject', 'body_html', 'email_from', 'email_to', 'email_bcc', 'partner_to', 'email_cc', 'reply_to']

        report_xml_pool = self.pool.get('ir.actions.report.xml')
        res_ids_to_templates = self.get_email_template_batch(cr, uid, template_id, res_ids, context)

        # templates: res_id -> template; template -> res_ids
        templates_to_res_ids = {}
        for res_id, template in res_ids_to_templates.iteritems():
            templates_to_res_ids.setdefault(template, []).append(res_id)

        results = dict()
        for template, template_res_ids in templates_to_res_ids.iteritems():
            # generate fields value for all res_ids linked to the current template
            for field in fields:
                generated_field_values = self.render_template_batch(
                    cr, uid, getattr(template, field), template.model, template_res_ids,
                    post_process=(field == 'body_html'),
                    context=context)
                for res_id, field_value in generated_field_values.iteritems():
                    results.setdefault(res_id, dict())[field] = field_value
            # compute recipients
            results = self.generate_recipients_batch(cr, uid, results, template.id, template_res_ids, context=context)
            # update values for all res_ids
            for res_id in template_res_ids:
                values = results[res_id]
                # body: add user signature, sanitize
                if 'body_html' in fields and template.user_signature:
                    signature = self.pool.get('res.users').browse(cr, uid, uid, context).signature
                    values['body_html'] = tools.append_content_to_html(values['body_html'], signature)
                if values.get('body_html'):
                    values['body'] = tools.html_sanitize(values['body_html'])
                # technical settings
                values.update(
                    mail_server_id=template.mail_server_id.id or False,
                    auto_delete=template.auto_delete,
                    model=template.model,
                    res_id=res_id or False,
                    attachment_ids=[attach.id for attach in template.attachment_ids],
                )

            # Add report in attachments: generate once for all template_res_ids
            if template.report_template:
                for res_id in template_res_ids:
                    attachments = []
                    report_name = self.render_template(cr, uid, template.report_name, template.model, res_id, context=context)
                    report = report_xml_pool.browse(cr, uid, template.report_template.id, context)
                    report_service = report.report_name
                    # Ensure report is rendered using template's language
                    ctx = context.copy()
                    if template.lang:
                        ctx['lang'] = self.render_template_batch(cr, uid, template.lang, template.model, [res_id], context)[res_id]  # take 0 ?

                    if report.report_type in ['qweb-html', 'qweb-pdf']:
                        result, format = self.pool['report'].get_pdf(cr, uid, [res_id], report_service, context=ctx), 'pdf'
                    else:
                        result, format = openerp.report.render_report(cr, uid, [res_id], report_service, {'model': template.model}, ctx)
            
                    # TODO in trunk, change return format to binary to match message_post expected format
                    result = base64.b64encode(result)
                    if not report_name:
                        report_name = 'report.' + report_service
                    ext = "." + format
                    if not report_name.endswith(ext):
                        report_name += ext
                    attachments.append((report_name, result))
                    results[res_id]['attachments'] = attachments

        return results

email_template()

class mail_mail(osv.osv):
    _inherit = "mail.mail"
    
    _columns = {
                'email_bcc': fields.char('Bcc', help="Blind carbon copy recipients (placeholders may be used here)"),
                }
    
    def send(self, cr, uid, ids, auto_commit=False, raise_exception=False, context=None):
        """ Sends the selected emails immediately, ignoring their current
            state (mails that have already been sent should not be passed
            unless they should actually be re-sent).
            Emails successfully delivered are marked as 'sent', and those
            that fail to be deliver are marked as 'exception', and the
            corresponding error mail is output in the server logs.

            :param bool auto_commit: whether to force a commit of the mail status
                after sending each mail (meant only for scheduler processing);
                should never be True during normal transactions (default: False)
            :param bool raise_exception: whether to raise an exception if the
                email sending process has failed
            :return: True
        """
        if context is None:
            context = {}
        ir_mail_server = self.pool.get('ir.mail_server')
        ir_attachment = self.pool['ir.attachment']
        for mail in self.browse(cr, SUPERUSER_ID, ids, context=context):
            try:
                # TDE note: remove me when model_id field is present on mail.message - done here to avoid doing it multiple times in the sub method
                if mail.model:
                    model_id = self.pool['ir.model'].search(cr, SUPERUSER_ID, [('model', '=', mail.model)], context=context)[0]
                    model = self.pool['ir.model'].browse(cr, SUPERUSER_ID, model_id, context=context)
                else:
                    model = None
                if model:
                    context['model_name'] = model.name

                # load attachment binary data with a separate read(), as prefetching all
                # `datas` (binary field) could bloat the browse cache, triggerring
                # soft/hard mem limits with temporary data.
                attachment_ids = [a.id for a in mail.attachment_ids]
                attachments = [(a['datas_fname'], base64.b64decode(a['datas']))
                                 for a in ir_attachment.read(cr, SUPERUSER_ID, attachment_ids,
                                                             ['datas_fname', 'datas'])]

                # specific behavior to customize the send email for notified partners
                email_list = []
                if mail.email_to:
                    email_list.append(self.send_get_email_dict(cr, uid, mail, context=context))
                for partner in mail.recipient_ids:
                    email_list.append(self.send_get_email_dict(cr, uid, mail, partner=partner, context=context))
                # headers
                headers = {}
                bounce_alias = self.pool['ir.config_parameter'].get_param(cr, uid, "mail.bounce.alias", context=context)
                catchall_domain = self.pool['ir.config_parameter'].get_param(cr, uid, "mail.catchall.domain", context=context)
                if bounce_alias and catchall_domain:
                    if mail.model and mail.res_id:
                        headers['Return-Path'] = '%s-%d-%s-%d@%s' % (bounce_alias, mail.id, mail.model, mail.res_id, catchall_domain)
                    else:
                        headers['Return-Path'] = '%s-%d@%s' % (bounce_alias, mail.id, catchall_domain)

                # build an RFC2822 email.message.Message object and send it without queuing
                res = None
                for email in email_list:
                    msg = ir_mail_server.build_email(
                        email_from=mail.email_from,
                        email_to=email.get('email_to'),
                        subject=email.get('subject'),
                        body=email.get('body'),
                        body_alternative=email.get('body_alternative'),
                        email_cc=tools.email_split(mail.email_cc),
                        #NG: add email_bcc from mail
                        email_bcc=tools.email_split(mail.email_bcc),
                        reply_to=mail.reply_to,
                        attachments=attachments,
                        message_id=mail.message_id,
                        references=mail.references,
                        object_id=mail.res_id and ('%s-%s' % (mail.res_id, mail.model)),
                        subtype='html',
                        subtype_alternative='plain',
                        headers=headers)
                    res = ir_mail_server.send_email(cr, uid, msg,
                                                    mail_server_id=mail.mail_server_id.id,
                                                    context=context)

                if res:
                    mail.write({'state': 'sent', 'message_id': res})
                    mail_sent = True
                else:
                    mail.write({'state': 'exception'})
                    mail_sent = False

                # /!\ can't use mail.state here, as mail.refresh() will cause an error
                # see revid:odo@openerp.com-20120622152536-42b2s28lvdv3odyr in 6.1
                self._postprocess_sent_message(cr, uid, mail, context=context, mail_sent=mail_sent)
                _logger.info('Mail with ID %r and Message-Id %r successfully sent', mail.id, mail.message_id)
            except MemoryError:
                # prevent catching transient MemoryErrors, bubble up to notify user or abort cron job
                # instead of marking the mail as failed
                _logger.exception('MemoryError while processing mail with ID %r and Msg-Id %r. '\
                                      'Consider raising the --limit-memory-hard startup option',
                                  mail.id, mail.message_id)
                raise
            except Exception as e:
                _logger.exception('failed sending mail.mail %s', mail.id)
                mail.write({'state': 'exception'})
                self._postprocess_sent_message(cr, uid, mail, context=context, mail_sent=False)
                if raise_exception:
                    if isinstance(e, AssertionError):
                        # get the args of the original error, wrap into a value and throw a MailDeliveryException
                        # that is an except_orm, with name and value as arguments
                        value = '. '.join(e.args)
                        raise MailDeliveryException(_("Mail Delivery Failed"), value)
                    raise

            if auto_commit is True:
                cr.commit()
        return True
    
mail_mail()