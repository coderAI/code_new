# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields
from openerp.tools.translate import _
import HTMLParser


log = logging.getLogger(__name__)


class email_template(osv.osv):
    _inherit = 'email.template'

    _columns = {
        'email_to': fields.text('To (Emails)', help="Comma-separated recipient addresses (placeholders may be used here)"),
        'email_cc': fields.text('Cc', help="Carbon copy recipients (placeholders may be used here)"),
        'act_from': fields.many2one('workflow.activity', 'Source Activity', select=True),
        'act_to': fields.many2one('workflow.activity', 'Destination Activity', select=True),
        'wkf_id': fields.many2one('workflow', string='Workflow'),
        'send_when_create': fields.boolean('Send When Create'),
        'mail_group_id': fields.many2many('vhr.email.group', 'email_template_email_group_rel',
                                          'template_id', 'email_group_id', 'Mail Group'),
    }

    def onchange_model_id(self, cr, uid, ids, model_id, context=None):
        val = {}
        if model_id:
            mod_name = self.pool.get('ir.model').browse(cr, uid, model_id, context).model
            wkf_ids = self.pool.get('workflow').search(cr, uid, [('osv', '=', mod_name)], context=context)
            wkf_id = wkf_ids and wkf_ids[0] or None
            val = {'model': mod_name, 'wkf_id': wkf_id}
        return {'value': val}

    def onchange_act_from(self, cr, uid, ids, act_from, context=None):
        wkf_trans_obj = self.pool.get('workflow.transition')
        domain = {'act_to': "[('wkf_id', '=', wkf_id)]"}
        act_to_ids = []
        if act_from:
            wkf_trans = wkf_trans_obj.search(cr, uid, [('act_from', '=', act_from)])
            for wkf_tran in wkf_trans_obj.browse(cr, uid, wkf_trans):
                if wkf_tran and wkf_tran.act_to:
                    act_to_ids.append(wkf_tran.act_to.id)
            domain = {'act_to': "[('wkf_id', '=', wkf_id), ('id', 'in', %s)]" % act_to_ids}
        return {'domain': domain}

    def onchange_act_to(self, cr, uid, ids, act_to, context=None):
        wkf_trans_obj = self.pool.get('workflow.transition')
        domain = {'act_from': "[('wkf_id', '=', wkf_id)]"}
        act_from_ids = []
        if act_to:
            wkf_trans = wkf_trans_obj.search(cr, uid, [('act_to', '=', act_to)])
            for wkf_tran in wkf_trans_obj.browse(cr, uid, wkf_trans):
                if wkf_tran and wkf_tran.act_from:
                    act_from_ids.append(wkf_tran.act_from.id)
            domain = {'act_from': "[('wkf_id', '=', wkf_id), ('id', 'in', %s)]" % act_from_ids}
        return {'domain': domain}

    def send_mail(self, cr, uid, template_id, res_id, attach_ids=None, force_send=False, raise_exception=False, context=None):
        """
            Override method send_mail
        """
        if context is None:
            context = {}
        if context.get('ignore_send', False):
            return False
        mail_mail = self.pool.get('mail.mail')
        ir_attachment = self.pool.get('ir.attachment')
        # create a mail_mail based on values, without attachments
        values = self.generate_email(cr, uid, template_id, res_id, context=context)
        template_res = self.browse(cr, uid, template_id, fields_process=['mail_group_id'], context=context)
        if template_res:
            to_email = ''
            cc_email = ''
            if context.get('email_to', False):
                to_email += context['email_to'] + ";"
            if template_res.mail_group_id:
                for group in template_res.mail_group_id:
                    to_email += group.to_email and (group.to_email + ';') or ''
                    cc_email += group.cc_email and (group.cc_email + ';') or ''

            if values.get('email_to', False):
                to_email += values['email_to'] + ";"

            if values.get('email_cc', False):
                cc_email += values['email_cc'] + ";"

            values.update({'email_to': to_email, 'email_cc': cc_email})
        if values.get('subject', False):
            html = HTMLParser.HTMLParser()
            subject = html.unescape(values.get('subject'))
            values.update({'subject': subject})
        if not values.get('email_from'):
            raise osv.except_osv(_('Warning!'), _("Sender email is missing or empty after template rendering. Specify one to deliver your message"))
        values['recipient_ids'] = [(4, pid) for pid in values.get('partner_ids', list())]
        attachment_ids = values.pop('attachment_ids', [])
        attachments = values.pop('attachments', [])
        #Tuannh3: Update mail server id
        if not values.get('mail_server_id'):
            ir_mail_server = self.pool.get('ir.mail_server')
            mail_server_id = ir_mail_server.search(cr, uid, [('smtp_user', '=', values.get('email_from'))])
            if mail_server_id:
                values.update({'mail_server_id': mail_server_id[0]})
            else:
                mail_server_id = ir_mail_server.search(cr, uid, [('smtp_user', '=', False), ('smtp_encryption', '=', 'none')])
                if mail_server_id:
                    values.update({'mail_server_id': mail_server_id[0]})
        msg_id = mail_mail.create(cr, uid, values, context=context)
        mail = mail_mail.browse(cr, uid, msg_id, context=context)

        # manage attachments
        for attachment in attachments:
            attachment_data = {
                'name': attachment[0],
                'datas_fname': attachment[0],
                'datas': attachment[1],
                'res_model': 'mail.message',
                'res_id': mail.mail_message_id.id,
            }
            context.pop('default_type', None)
            attachment_ids.append(ir_attachment.create(cr, uid, attachment_data, context=context))
        if attach_ids:
            attachment_ids = list(set(attachment_ids + attach_ids))

        if attachment_ids:
            values['attachment_ids'] = [(6, 0, attachment_ids)]
            mail_mail.write(cr, uid, msg_id, {'attachment_ids': [(6, 0, attachment_ids)]}, context=context)

        if force_send:
            mail_mail.send(cr, uid, [msg_id], raise_exception=raise_exception, context=context)
        return msg_id

    def send_mail_err(self, cr, uid, subject, body_html, email_from, email_to, mail_server_id, email_cc=None, context=None):
        mail_mail = self.pool.get('mail.mail')
        values = {
            'body': body_html,
            'body_html': body_html,
            'email_from': email_from,
            'email_to': email_to,
            'email_cc': email_cc,
            'mail_server_id': mail_server_id,
            'subject': subject,
        }
        msg_id = mail_mail.create(cr, uid, values, context=context)
        mail_mail.send(cr, uid, [msg_id], context=context)
        return msg_id


email_template()