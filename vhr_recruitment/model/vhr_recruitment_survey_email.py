# -*- coding: utf-8 -*-
import logging

from openerp.osv import osv, fields
from vhr_recruitment_abstract import vhr_recruitment_abstract



log = logging.getLogger(__name__)
import threading

max_connections = 1
semaphore = threading.BoundedSemaphore(max_connections)


class vhr_recruitment_survey_email(osv.osv,vhr_recruitment_abstract):
    _name = 'vhr.recruitment.survey.email'
    _description = 'VHR Survey Email'
    _inherit = ['mail.thread']

    _columns = {
        'email_from': fields.text('Email From'),
        'email_to': fields.text('Email To'),  # required
        'name_email_to': fields.text('Name Email To'),  # required
        'email_cc': fields.text('Email cc'),
        'request_code': fields.char('Request Code'),
        'note': fields.text('Note'),
        'approve': fields.char('Approve', size=255),  # required
        'state': fields.selection([('new', 'New'),
                                   ('approve', 'Approve'),
                                   ('reject', 'Reject')], 'State'),
        'job_id': fields.many2one('hr.job', 'Resource Request'),
        'approver': fields.many2one('hr.employee', 'Approver', ondelete='restrict'),
        'old_data': fields.char('Old data'),
        'new_data': fields.char('New data'),

    }

    _defaults = {
        'state': 'new'
    }

    def send_email(self, cr, uid, name_email, res, context=None):
        log.info('VHR RR : start vhr_email_rr send_survey_mail()')
        if context is None: context = {}
        if res is None: res = {}
        email_temp_obj = self.pool.get('email.template')
        hrs_mail = self.pool.get('mail.thread')
        email_from = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr.rr.email.system.config')
        res['email_from'] = email_from if email_from else 'service@hrs'
        # IF Email ERROR
        if 'VHR_RR_ERROR' in context:
            email_to = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr.rr.email.admin.tool.config')
            res['email_to'] = email_to if email_to else 'admin@hrs'
        # Create Email
        mail_id = self.create(cr, uid, res, context)
        log.debug('Email infor: %s ' % (res))
        if 'APPROVE_EMAIL' in context:
            model_data = self.pool.get('ir.model.data')
            action_id = model_data.xmlid_lookup(cr, uid, 'vhr_recruitment.ir_actions_server_vhr_recruitment_survey_by_email')[2]
            
            res_item = {'approve': hrs_mail.hrs_get_link(res['email_to'] + ';', mail_id, 'approve', self._name, action_id)}
            self.write(cr, uid, mail_id, res_item)
        template_id = email_temp_obj.search(cr, uid, [('name', '=', name_email)], context=context)
        if template_id:
            email_temp_obj.send_mail(cr, uid, template_id[0], mail_id, None, True, False, context)
        else:
            log.info('VHR RR : Can\'t search email template')
        log.info('VHR RR : end vhr_email_rr send_survey_mail()')
        return True
    
    def do_read_mail_from_mail_box(self, cr, uid, ids, context=None):
        log.info('VHR RR start do_read_mail_from_mail_box Email : %s' % (ids))
        log.debug('VHR RR context : %s' % (context))
        if not isinstance(ids, list):
            ids = [ids]
        if context is None:
            context = {}
        if ids and context.has_key('mail_decide'):
            for item in self.browse(cr, uid, ids, context=context):
                log.info('Approve by email: excecute for email : %s and job code : %s' % (item.id, item.job_id.code))
                if not item.job_id:
                    log.info('Approve by email: Fail, please check bill_id in email template')
                    break
                job_obj = self.pool.get('hr.job')
                if item.job_id:
                    if context['mail_decide'] == 'approve':
                        job_obj.write(cr, uid, item.job_id.id, {'is_send_survey': True})
                    else:
                        log.info('We don\'t have this action: %s' % (context['mail_decide']))
                        break
            self.write(cr, uid, ids, {'state': context['mail_decide']})
        log.info('VHR RR end do_read_mail_from_mail_box Email : %s' % (ids))
        return True
    
    def get_list_emp_cc(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        list_emp_cc = []
        list_cc_mail = []
        job_obj = self.pool.get('hr.job')
        for item in self.browse(cr, uid, ids, context=context):
            job_id = item.job_id.id if item.job_id else False
            if job_id:
                list_emp_cc = job_obj.get_list_emp_cc_survey_job(cr, uid, job_id, context)
                            
        for employee in self.pool['hr.employee'].browse(cr, uid, list_emp_cc, context=context):
            if employee.work_email:
                list_cc_mail.append(employee.work_email)
        return ";".join(list_cc_mail)