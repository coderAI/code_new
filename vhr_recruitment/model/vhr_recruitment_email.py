# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields
from openerp import SUPERUSER_ID
import threading
from hr_job import WAITING_DEPT
from vhr_recruitment_constant import RE_DEPTHEAD_REJECT_NONE_OFFICAL
from vhr_recruitment_abstract import vhr_recruitment_abstract

log = logging.getLogger(__name__)
max_connections = 1
semaphore = threading.BoundedSemaphore(max_connections)

class vhr_recruitment_email(osv.osv, vhr_recruitment_abstract):
    _name = 'vhr.recruitment.email'
    _description = 'VHR Recruitment Email'
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
        'state': fields.selection([('new', 'New'),
                                   ('approve', 'Approve'),
                                   ('reject', 'Reject')], 'State'),
        'job_id': fields.many2one('hr.job', 'Resource Request'),
        'approver': fields.many2one('hr.employee', 'Approver'),
        'old_data': fields.char('Old_data'),
        'new_data': fields.char('New data')
        }

    _defaults = {
        'state': 'new'
    }

    def send_email(self, cr, uid, name_email, res, context=None):
        log.info('VHR RR : start vhr_email_rr send_mail()')
        if context is None: context = {}
        if res is None: res = {}
        email_temp_obj = self.pool.get('email.template')
        hrs_mail = self.pool.get('mail.thread')
        email_from = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr.rr.email.system.config')
        res['email_from'] = email_from if email_from else 'hr.service@hrs'
        # IF Email ERROR
        if 'VHR_RR_ERROR' in context:
            email_to = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr.rr.email.admin.tool.config')
            res['email_to'] = email_to if email_to else 'admin@hrs'
        # Create Email
        mail_id = self.create(cr, uid, res, context)
        log.debug('Email infor: %s ' % (res))
        if 'APPROVE_EMAIL' in context:
            model_data = self.pool.get('ir.model.data')
            action_id = model_data.xmlid_lookup(cr, uid, 'vhr_recruitment.ir_actions_server_vhr_recruitment_approve_by_email')[2]
            
            res_item = {'approve': hrs_mail.hrs_get_link(res['email_to'] + ';', mail_id, 'approve', self._name, action_id),
                        'reject': hrs_mail.hrs_get_link(res['email_to'] + ';', mail_id, 'reject', self._name, action_id)
                        }
            self.write(cr, uid, mail_id, res_item)
        template_id = email_temp_obj.search(cr, uid, [('name', '=', name_email)], context=context)
        if template_id:
            email_temp_obj.send_mail(cr, uid, template_id[0], mail_id, None, True, False, context)
        else:
            log.info('VHR RR : Can\'t search email template')
        log.info('VHR RR : end vhr_email_rr send_mail()')
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
                if item.state != 'new':
                    log.info('Email have been action, please check again')
                    break
                approver = item.approver.user_id.id if item.approver.user_id.id else SUPERUSER_ID
                hr_job_obj = self.pool.get('hr.job')
                if item.job_id.none_official:
                    if not item.job_id.no_depthead_approval:
                        if context['mail_decide'] == 'approve':
                            hr_job_obj.write(cr, uid, item.job_id.id, {'no_depthead_approval': True})
                        elif context['mail_decide'] == 'reject':
                            log.info('depthead reject none office')
                            email_template = self.pool.get('email.template')
                            email_ids = email_template.search(cr, uid, [
                                            ('model', '=', self._name),
                                            ('name', '=', RE_DEPTHEAD_REJECT_NONE_OFFICAL),
                                        ], context=context)
                            if email_ids:
                                email_template.vhr_send_mail(cr, uid, email_ids[0], item.id, context=context)
                            else:
                                log.error('vhr_recruitment : can\'t search email template')
                        else:
                            log.info('We don\'t have this action: %s' % (context['mail_decide']))
                            break
                    else:
                        log.info('vhr_recruitment: job da duoc xu ly')
                else:
                    job_state = item.job_id.state
                    if job_state == WAITING_DEPT:
                        if context['mail_decide'] == 'approve':
                            context['ACTION'] = 'waiting_dept_waiting_rrm'
                            hr_job_obj.execute_workflow(cr, approver, item.job_id.id, context)
                        elif context['mail_decide'] == 'reject':
                            context['ACTION'] = 'waiting_dept_waiting_hrbp'
                            hr_job_obj.execute_workflow(cr, approver, item.job_id.id, context)
                        else:
                            log.info('We don\'t have this action: %s' % (context['mail_decide']))
                            break
                    else:
                        log.info('Resource request have been action current state : %s' % (job_state))
                        break
            self.write(cr, uid, ids, {'state': context['mail_decide']})
        log.info('VHR RR end do_read_mail_from_mail_box Email : %s' % (ids))
        return True
    
    def get_list_cc_email_delegate(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        list_hrbp = []
        list_cc_mail = []
        for item in self.browse(cr, uid, ids, context=context):
            job = item.job_id
            if job:
                    depthead = job.department_id.manager_id if job.department_id and job.department_id.manager_id  else False
                    lst_approvers = self.pool['vhr.delegate.by.depart'].get_delegate(
                            cr, uid, depthead.id, {'delegate': True, 'department_id': job.department_id.id})
                    manager_id = job.department_id.manager_id.id if job.department_id.manager_id else False
                    for hrbp in job.department_id.hrbps:
                        employee_id = hrbp.id
                        if hrbp.resource_id and hrbp.resource_id.active:
                            if employee_id and employee_id != manager_id:
                                list_hrbp.append(employee_id)
                            
        for employee in self.pool['hr.employee'].browse(cr, uid, list_hrbp, context=context):
            if employee.work_email:
                list_cc_mail.append(employee.work_email)
        return ";".join(list_cc_mail)
    
vhr_recruitment_email()
