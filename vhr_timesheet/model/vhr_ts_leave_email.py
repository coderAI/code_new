# -*- coding: utf-8 -*-
import logging
from datetime import datetime

from openerp.osv import osv, fields
from openerp import SUPERUSER_ID
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.addons.vhr_timesheet.model.vhr_holidays import DICT_STATES


log = logging.getLogger(__name__)
import threading

max_connections = 1
semaphore = threading.BoundedSemaphore(max_connections)


class vhr_ts_leave_email(osv.osv):
    _name = 'vhr.ts.leave.email'
    _description = 'VHR Leave Email'
    _inherit = ['mail.thread']

    _columns = {
        'email_from': fields.text('Email From'),
        'email_to': fields.text('Email To'),  # required
        'email_cc': fields.text('Email cc'),
        'request_code': fields.char('Request Code'),
        'note': fields.text('Note'),
        'link_email': fields.char('Link email'),  # required
        'approve': fields.char('Approve', size=255),  # required
        'reject': fields.char('Reject', size=255),  # required
        'action_user': fields.char('Action User'),#user approved/rejected/returned the form
        'state': fields.selection([('new', 'New'),
                                   ('approve', 'Approve'),
                                   ('reject', 'Reject')], 'State'),
        'leave_id': fields.many2one('hr.holidays', 'Leave Request', ondelete='restrict'),
        'approver': fields.many2one('hr.employee', 'Approver', ondelete='restrict'),
        'old_data': fields.char('Old data'),
        'new_data': fields.char('New data'),
        
    }

    _defaults = {
        'state': 'new'
    }

    def send_email(self, cr, uid, name_email, res, context=None):
        log.info('VHR Leave : start vhr_ts_leave_email send_mail()')
        if context is None:
            context = {}
        if res is None:
            res = {}
        email_temp_obj = self.pool.get('email.template')
        hrs_mail = self.pool.get('mail.thread')
        email_from = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_master_data_email_system_config')
        res['email_from'] = email_from if email_from else 'hr.service@hrs.com.vn'
        # Create Email
        mail_ids = []
        
        email_to = res.get('email_to', '').split(';')
        for email in email_to:
            res['email_to'] = email
            mail_id = self.create(cr, uid, res, context)
            mail_ids.append(mail_id)
            log.debug('Email infor: %s ' % (res))
            
            if context.get('action_from_email',False):
                model_data_ids = self.pool.get('ir.model.data').search(cr, uid, [('name','=','ir_actions_server_vhr_timesheet_approve_by_email')])
                action_id = False
                if model_data_ids:
                    model_data = self.pool.get('ir.model.data').read(cr, uid, model_data_ids[0], ['res_id'])
                    action_id = model_data.get('res_id', False)
                    
                email = email and email.lower() or ''
                res_item = {'approve': hrs_mail.hrs_get_link(email + ';', mail_id, 'approve', self._name, action_id),
                            'reject': hrs_mail.hrs_get_link(email + ';', mail_id, 'reject', self._name, action_id)
                }
                self.write(cr, uid, mail_id, res_item)
                
        template_id = email_temp_obj.search(cr, uid, [('name', '=', name_email)])
        if template_id:
            for mail_id in mail_ids:
                email_temp_obj.send_mail(cr, uid, template_id[0], mail_id, None, True, False, context)
        else:
            log.info('VHR Leave : Can\'t search email template')
        log.info('VHR Leave : end vhr_ts_leave_email send_mail()')
        return True

    def do_read_mail_from_mail_box(self, cr, uid, ids, context=None):
        log.info('VHR Leave start do_read_mail_from_mail_box Email : %s' % (ids))
        log.debug('VHR Leave context : %s' % (context))
        if not isinstance(ids, list):
            ids = [ids]
        if context is None:
            context = {}
        if ids and 'mail_decide' in context:
            for item in self.browse(cr, uid, ids):
                log.info('Approve by email: excecute for email : %s and job code : %s' % (item.id, item.leave_id.name))
                if not item.leave_id:
                    log.info('Approve by email: Fail, please check bill_id in email template')
                    break
                if item.state != 'new':
                    log.info('Email have been action, please check again')
                    break
                
                action_uid = uid               
                email_to = item.email_to
                if email_to:
                    list_email_to = email_to.split(';')
                    emp_pool = self.pool.get('hr.employee')
                    employee_ids = emp_pool.search(cr, uid, [('work_email','in',list_email_to)])
                    employees = emp_pool.read(cr, uid, employee_ids, ['user_id'])
                    user_ids = [employee.get('user_id') and employee['user_id'][0] for employee in employees]
                    if user_ids:
                        action_uid = user_ids[0]
                        
                if item.leave_id:
                    if context.get('mail_decide',False) == 'approve':
                        context['ACTION_COMMENT'] = 'Approve by email'
                        context['action'] = 'validate'
                    elif context.get('mail_decide', False) == 'reject':
                        context['ACTION_COMMENT'] = 'Reject by email'
                        context['action'] = 'reject'
                        
                    self.pool.get('hr.holidays').execute_workflow(cr, action_uid, [item.leave_id.id], context)
                    
            self.write(cr, uid, ids, {'state': context['mail_decide']})
        log.info('VHR Leave end do_read_mail_from_mail_box Email : %s' % (ids))
        return True

    def get_format_date(self, cr, uid, res_id, date_string, context=None):
        if isinstance(res_id, list):
            res_id = res_id[0]
        if res_id and date_string:
            return datetime.strptime(date_string, DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y")
        return ''


vhr_ts_leave_email()
