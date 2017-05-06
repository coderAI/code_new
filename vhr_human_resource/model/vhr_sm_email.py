# -*-coding:utf-8-*-
import logging
import traceback

from openerp.osv import osv, fields
from openerp import SUPERUSER_ID
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
# from hr_job import WAITING_DEPT
log = logging.getLogger(__name__)
import threading
max_connections = 1
semaphore = threading.BoundedSemaphore(max_connections)

class vhr_sm_email(osv.osv):
    _name = 'vhr.sm.email'
    _description = 'VHR Staff Movement Email'
    _inherit = ['mail.thread']

    _columns = {
        'email_from': fields.text('Email From'),
        'email_to': fields.text('Email To'),  # required
        'email_cc': fields.text('Email cc'),
        'action_user': fields.char('Action User'),#user approved/rejected/returned the form
        'request_code': fields.char('Request Code'),
        'link_email': fields.char('Link email'),  # required
        'approve': fields.char('Approve', size=255),  # required
        'return': fields.char('Return', size=255),  # required
        'reject': fields.char('Reject', size=255),  # required
        'state': fields.selection([('new', 'New'),
                                   ('return', 'Return'),
                                   ('approve', 'Approve'),
                                   ('reject', 'Reject')], 'State'),
        'wr_id': fields.many2one('vhr.working.record', 'Working Record'),
        'mass_id': fields.many2one('vhr.mass.movement', 'Mass movement'),
        'tr_id': fields.many2one('vhr.termination.request', 'Termination Request'),
        'exit_id': fields.many2one('vhr.exit.checklist.request', 'Exit Checklist'),
        'renew_id': fields.many2one('vhr.multi.renew.contract', 'Renewal Contract'),
        'contract_id': fields.many2one('hr.contract', 'Contract'),

        'number_of_days_late': fields.integer('Number of Days Late'),
        'subject_element_name': fields.char('Subject Element Name'),#For some template, base on enviroment will have a different number in subject, ex:Multi Renew Contract: remnind
        'domain_account_of_employee': fields.char('Domain Account Of Employee'),#For some template need to loop data in field one2many
        'date': fields.char('Date'),#You need to convert from date to char fist to get correct format
        'reason': fields.char('Reason'),#For some template,need to have reason or sth else
        }
    
        

    _defaults = {
        'state': 'new'
    }

    def send_email(self, cr, uid, name_email, res, context=None):
        log.info('VHR HR : start vhr_email_sm send_mail()')
        if context is None:
            context = {}
        if res is None:
            res = {}
        email_temp_obj = self.pool.get('email.template')
        hrs_mail = self.pool.get('mail.thread')
        email_from = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_master_data_email_system_config') or ''
        res['email_from'] = email_from
        
        template_id = email_temp_obj.search(cr, uid, [('name', '=', name_email)])
        #Remove duplicate email in email_to or email_cc
        if template_id:
            mail_template = email_temp_obj.browse(cr, uid, template_id[0])
            if mail_template.mail_group_id:
                
                to_email = res.get('email_to','') or ''
                cc_email = res.get('email_cc','') or ''
                old_email_to  = to_email.split(';')
                old_email_cc  = cc_email.split(';')
                
                email_to = []
                email_cc = []
                for group in mail_template.mail_group_id:
                    group_email = []
                    if group.to_email:
                        group_email.extend( group.to_email.split(';'))
                    if group.cc_email:
                        group_email.extend(group.cc_email.split(';'))
                        
                    email_to = [item for item in email_to if item not in group_email]
                    email_cc = [item for item in email_cc if item not in group_email]
                
                email_to.extend(old_email_to)
                email_cc.extend(old_email_cc)
                res['email_to'] = ';'.join(email_to)
                res['email_cc'] = ';'.join(email_cc)
        
        list_email_to = res.get('email_to','').split(';')
        list_email_cc = res.get('email_cc','').split(';')
        
        list_email_cc = [mail for mail in list_email_cc if mail not in list_email_to]
        res['email_cc'] = ';'.join(list(set(list_email_cc)))
                
        mail_ids = []
        if list_email_to:
            if context.get('not_split_email',False):
                res['email_to'] = ';'.join(list(set(list_email_to)))
                mail_id = self.create(cr, uid, res, context)
                mail_ids.append(mail_id)
            else:
                for email_to in list_email_to:
                    res['email_to'] = email_to
                    if list_email_to.index(email_to) > 0:
                        res['email_cc'] = ''
                    
                    mail_id = self.create(cr, uid, res, context)
                    mail_ids.append(mail_id)
    #                 log.debug('Email infor: %s ' % (res))
                    
                    if context.get('action_from_email',False):
                        
                        model_data_ids = self.pool.get('ir.model.data').search(cr, uid, [('name','=','ir_actions_server_vhr_sm_approve_by_email')])
                        action_id = False
                        if model_data_ids:
                            model_data = self.pool.get('ir.model.data').read(cr, uid, model_data_ids[0], ['res_id'])
                            action_id = model_data.get('res_id', False)
                
                        res_item = {'approve': hrs_mail.kms_get_link(res['email_to'].lower() + ';', mail_id, 'approve', self._name, action_id),
                                    'reject': hrs_mail.kms_get_link(res['email_to'].lower() + ';', mail_id, 'reject', self._name, action_id),
                                    'return': hrs_mail.kms_get_link(res['email_to'].lower() + ';', mail_id, 'return', self._name, action_id)
                                    }
                        
                        log.debug('Approve Email infor: %s ;email_to: %s; mail_id: %s' % (res_item, res['email_to'],mail_id))
                        self.write(cr, uid, mail_id, res_item)
        
        if template_id and mail_ids:
            log.info('VHR HR : Use email template:' + name_email)
            for mail_id in mail_ids:
                email_temp_obj.send_mail(cr, uid, template_id[0], mail_id, None, True, False, context)
        else:
            log.info('VHR HR : Can\'t search email template' + name_email)
        log.info('VHR HR : end vhr_email_sm send_mail()')
        return True
    
    def change_mail_group_detail(self, cr, uid, context=None):
        """
        """
        mail_group_pool = self.pool.get('vhr.email.group')
        record_ids = mail_group_pool.search(cr, uid, [])
        if record_ids:
            records = mail_group_pool.read(cr, uid, record_ids, ['to_email','cc_email'])
            for record in records:
                vals = {}
                to_email = record.get('to_email','') or ''
                cc_email = record.get('cc_email','') or ''
                
                mail_group_pool.write(cr, uid, record['id'],{'to_email': to_email, 'cc_email': cc_email})
        
        return True
    
    def do_read_mail_from_mail_box(self, cr, uid, ids, context=None):
        log.info('VHR HR start do_read_mail_from_mail_box Email : %s' % (ids))
        log.debug('VHR HR context : %s' % (context))
        if not isinstance(ids, list):
            ids = [ids]
        if context is None:
            context = {}
        if ids and context.has_key('mail_decide'):
            for item in self.browse(cr, uid, ids):
                log.info('Approve by email: excecute for email : %s ' % (item.id))
#                 if not item.wr_id and not item.tr_id:
#                     log.info('Approve by email: Fail')
#                     break
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
                
                context = self.execute_action(cr, action_uid, item, context)
                
            self.write(cr, uid, ids, {'state': context['mail_decide']})
        log.info('VHR HR end do_read_mail_from_mail_box Email : %s' % (ids))
        return True
    
    def check_send_mail(self, cr, uid, ids, action_uid, record_id, context=None):
        record = self.browse(cr, uid, record_id)
        return self.execute_action(cr, action_uid, record, context)
    
    def execute_action(self, cr, action_uid, record, context=None):
        if not context:
            context={}
        if record:
            working_obj = self.pool.get('vhr.working.record')
            termination_obj = self.pool.get('vhr.termination.request')
            log.info('Execute Workflow with uid %s' % action_uid)
            if context.get('mail_decide', False) in ['return','approve','reject']:
                try:
                    context['action'] = context.get('mail_decide','')
                    context['ACTION_COMMENT'] = 'action from email'
                    if record.wr_id:
                        working_obj.execute_workflow(cr, action_uid, record.wr_id.id, context)
                    elif record.tr_id:
                        termination_obj.execute_workflow(cr, action_uid, record.tr_id.id, context)
                        
                except Exception as e:
                    log.exception(e)
                    description = traceback.format_exc()
                    email_to,email_cc = working_obj.get_email_to_send(cr, SUPERUSER_ID, record.id, ['BS_Error'])
                    email_to = ';'.join(email_to)
                    email_cc = ';'.join(email_cc)
                    vals = {'link_email':record.link_email,
                            'email_to': email_to,
                            'email_cc': email_cc,
                            'reason': description
                            }
                    self.send_email(cr, SUPERUSER_ID, 'vhr_sm_error_announcement', vals, context)
            else:
                log.info('We don\'t have this action: %s' % (context['mail_decide']))
        
        return context  
    
    def get_format_date(self, cr, uid, res_id, date_string, context=None):
        if isinstance(res_id, list):
            res_id = res_id[0]
        if res_id and date_string:
            return datetime.strptime(date_string, DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y")
        return ''
            
    
    
vhr_sm_email()
