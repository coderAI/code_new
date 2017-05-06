# -*-coding:utf-8-*-
import logging
import time
import simplejson as json
from datetime import datetime
from datetime import date
from dateutil.relativedelta import relativedelta
from lxml import etree

from openerp.osv import osv, fields
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp import SUPERUSER_ID
from vhr_termination_request_permission import draft_permission, hrbp_permission
from vhr_termination_request_mail_template_process import mail_process_of_ter_online, mail_process_of_ter_offline_official, mail_process_of_ter_offline_not_official
from openerp.addons.vhr_common.model.vhr_common import vhr_common
from vhr_human_resource_abstract import vhr_human_resource_abstract

log = logging.getLogger(__name__)

STATES = [
    ('cancel', 'Cancel'),
    ('draft', 'Draft'),
    ('supervisor', 'Waiting LM'),
    ('hrbp', 'Waiting HRBP'),
    ('dept_head', 'Waiting DH'),
    ('cb','Waiting C&B'),
    ('finish', 'Finish')]

STATES_ONLINE = [
    ('cancel', 'Cancel'),
    ('draft', 'Draft'),
    ('supervisor', 'Waiting LM'),
    ('hrbp', 'Waiting HRBP'),
    ('dept_head', 'Waiting DH'),
    ('finish', 'Finish'),]

STATES_OFFLINE = [
      ('cancel','Cancel'),
      ('draft','Draft'),
#       ('cb','Waiting C&B'),
      ('finish','Finish')
      ]


class vhr_termination_request(osv.osv, vhr_common, vhr_human_resource_abstract):
    _name = 'vhr.termination.request'
    _description = 'VHR Termination Request'

    def get_can_see_hrbp_update(self, cr, uid, ids, field_name, arg, context=None):
        '''
         return True :     HRBP, Assistant HRBP, HR Dept head, CB Termination, Dept head
                False:     Clicker, Reporting Line
        '''
        res = {}
        for item in self.browse(cr, uid, ids):
            res[item.id] = False
            
            if self.is_hrbp(cr, uid, [item.id], context) or self.is_assistant_hrbp(cr, uid, [item.id], context):
                res[item.id] = True
                
            elif set(['hrs_group_system', 'vhr_hr_dept_head', 'vhr_cb_termination']).intersection(set(self.get_groups(cr, uid))):
                res[item.id] = True
                
            elif item.department_id and item.department_id.manager_id and item.department_id.manager_id.user_id.id == uid:
                res[item.id] = True
                
#             elif item.employee_id and item.employee_id.user_id and item.employee_id.user_id.id == uid:
#                 res[item.id] = False
#                     
#             elif item.supervisor_id and item.supervisor_id.user_id and item.supervisor_id.user_id.id == uid:
#                 res[item.id] = False
        return res
    
#     def is_show_comment_log_state_change(self, cr, uid, ids, field_name, arg, context=None):
#         '''
#         Comment của quá trình phê duyệt(Log stage change) không cho clicker và LM được quyền thấy
#         '''
#         res = {}
#         login_ids = []
#         if uid:
#             login_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=',uid)])
#             
#         for item in self.read(cr, uid, ids, ['employee_id','supervisor_id']):
#             employee_id = item.get('employee_id',False) and item['employee_id'][0]
#             supervisor_id = item.get('supervisor_id',False) and item['supervisor_id'][0]
#             
#             res[item['id']] = True
#             if self.is_hrbp(cr, uid, [item['id']], context) or self.is_assistant_hrbp(cr, uid, [item['id']], context):
#                 continue
#             if set(['hrs_group_system', 'vhr_hr_dept_head', 'vhr_cb_termination']).intersection(set(self.get_groups(cr, uid))):
#                 continue
#             if employee_id in login_ids or supervisor_id in login_ids:
#                 res[item['id']] = False
#         
#         return res
            

    def _is_person_do_action(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for record_id in ids:
            res[record_id] = self.is_person_do_action(cr, uid, [record_id], context)

        return res
    
    def _is_dept_head(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for record_id in ids:
            res[record_id] = self.is_dept_head(cr, uid, [record_id], context)

        return res
    
    def _is_lm(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for record_id in ids:
            res[record_id] = self.is_lm(cr, uid, [record_id], context)

        return res
    
    def _is_requester(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for record_id in ids:
            res[record_id] = self.is_creator(cr, uid, [record_id], context)

        return res
    
    def _is_hrbp(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for record_id in ids:
            res[record_id] = self.is_hrbp(cr, uid, [record_id], context)

        return res
    
    def _is_cb(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        groups = self.pool.get('res.users').get_groups(cr, uid)
        is_cb_termination = 'vhr_cb_termination' in groups
        for record_id in ids:
            res[record_id] = is_cb_termination
        
        return res

    # res[item.id] = True when user is HRBP or HR Dept Head
    def is_hrbp_watching(self, cr, uid, ids, field_name, arg, context=None):
        '''
        Return True if user belong to one of these groups   HRBP, Assistant HRBP, group_system, CB_Termination, HR Dept Head
        '''
        res = {}
        for record_id in ids:
            res[record_id] = {}
            is_hrbp = self.is_hrbp(cr, uid, [record_id], context)
            is_assistant = self.is_assistant_hrbp(cr, uid, [record_id], context)
            if is_hrbp or is_assistant:
                res[record_id]['is_hrbp_watching'] = True
            elif set(['hrs_group_system', 'vhr_cb_termination', 'vhr_hr_dept_head']).intersection(set(self.get_groups(cr, uid))):
                res[record_id]['is_hrbp_watching'] = True
            else:
                res[record_id]['is_hrbp_watching'] = False
            
            res[record_id]['is_hrbp'] = is_hrbp
            res[record_id]['is_assistant_hrbp'] = is_assistant

        return res
    
    
    def is_require_in_hrbp_update(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for item in self.browse(cr, SUPERUSER_ID, ids):
            #With contract CTV,HDLD required input HRBP Update for HRBP, assistant HRBP
                                                                # CB in offline
            
            is_official = item.contract_id and item.contract_id.type_id and item.contract_id.type_id.contract_type_group_id \
                            and item.contract_id.type_id.contract_type_group_id.is_offical
            if is_official and (self.is_hrbp(cr, uid, ids, context) or self.is_assistant_hrbp(cr, uid, ids, context)):
                res[item.id] = True
            elif item.is_offline:
                res[item.id] = True
            else:
                res[item.id] = False

        return res
    
    
#     def _is_clear_resign_reason_detail(self, cr, uid, ids, field_name, arg, context=None):
#         res = {}
#         for item in self.read(cr, uid, ids, ['resign_reason_detail_ids']):
#             if item.get('resign_reason_detail_ids',False):
#                 res[item['id']] = False
#             else:
#                 res[item['id']] = True
# 
#         return res
    
    def _count_attachment(self, cr, uid, ids, prop, unknow_none, context=None):
        ir_attachment = self.pool.get('ir.attachment')
        res = {}
        for item in ids:
            number = ir_attachment.search(cr, uid, [('res_id', '=', item), ('res_model', '=', self._name)], count=True)
            res[item] = number
        return res
    
    def get_date_end_contract(self, cr, uid, ids, prop, unknow_none, context=None):
        res = {}
        records = self.browse(cr, SUPERUSER_ID, ids, fields_process=['contract_id'])
        for record in records:
            if record.contract_id:
                date_end_contract = record.contract_id.date_end
                
                res[record.id] = date_end_contract
        
        return res

    def get_waiting_time(self, cr, uid, ids, prop, unknow_none, context=None):
        records = self.read(cr, uid, ids, ['state'])
        res = {}
        if records:
            for record in records:
                res[record.get('id', False)] = ''
                if record.get('state', False) in ['cancel', 'finish', 'draft']:
                    res[record.get('id', False)] = ''
                else:
                    meta_data = self.read(cr, SUPERUSER_ID, record.get('id', False), ['approve_date'], context)
                    approve_date = meta_data.get('approve_date', False)
                    if approve_date:
                        approve_date = datetime.strptime(approve_date, DEFAULT_SERVER_DATETIME_FORMAT)
                        now = datetime.now()
                        # log.info("time")
                        # log.info(now)
                        # log.info(approve_date)
                        gaps = now - approve_date
                        if now < approve_date:
                            gaps = approve_date - now

                        time = " hour"
                        time_count = float(gaps.seconds) / 3600
                        if time_count > 1:
                            time += "s"
                            
                        time_day = 'day'
                        time_days_count = gaps.days
                        if time_days_count > 1:
                            time_day += 's'
                        
                        if time_days_count >0:
                            res[record.get('id', False)] = '%.f ' % time_days_count + time_day
                            
                        res[record.get('id', False)] +=  ' %.1f ' % time_count + time

                    else:
                        res[record.get('id', False)] = ''

        return res

    def _check_waiting_for(self, cr, uid, ids, prop, unknow_none, context=None):
        if not context:
            context = {}

        context["search_all_employee"] = True
        context['active_test'] = False
        
        employee_obj = self.pool.get('hr.employee')
        
        login = False
        if uid:
            user = self.pool.get('res.users').read(cr, uid, uid, ['login'])
            login = user.get('login','')
            
        res = {}
        for item in self.browse(cr, uid, ids):
            vals = ''
            
            if item.state == 'draft':
                vals = '%s' % (item.requester_id.login)
                
            elif item.state == 'supervisor':
                vals = '%s' % (item.supervisor_id.login)
                
                if item.supervisor_id:
                    #get delegator if have
                    delegator_ids = self.get_delegator(cr, uid, item.id, item.supervisor_id.id, context)
                    if delegator_ids:
                        emps = self.pool.get('hr.employee').read(cr, uid, delegator_ids, ['login'])
                        emp_logins = [emp.get('login','') for emp in emps]
                        logins = '; '.join(emp_logins)
                        vals += '; ' + logins
                    
                    #Get delegate by process
                    delegator_ids = self.get_delegator_by_process(cr, uid, item.id, item.supervisor_id.id, context)
                    print 'delegator_ids=',delegator_ids
                    if delegator_ids:
                        emps = self.pool.get('hr.employee').read(cr, uid, delegator_ids, ['login'])
                        emp_logins = [emp.get('login','') for emp in emps]
                        logins = '; '.join(emp_logins)
                        vals += '; ' + logins
                    

            elif item.state == 'hrbp':
                vals = ''
                department_id = item.department_id and item.department_id.id or False
                if department_id:
                    department = self.pool.get('hr.department').browse(cr, uid, department_id,
                                                                       fields_process=['hrbps'])
                    employees = department.hrbps
                    for employee in employees:
                        if vals:
                            vals = '%s; %s' % (vals, employee.login)
                        else:
                            vals = '%s' % (employee.login)

            elif item.state == 'dept_head':
                vals = '%s' % (
                    item.department_id and item.department_id.manager_id and item.department_id.manager_id.login or '')
                
                if item.department_id and item.department_id.manager_id:
                    #get delegator if have
                    delegator_ids = self.get_delegator(cr, uid, item.id, item.department_id and item.department_id.manager_id.id, context)
                    if delegator_ids:
                        emps = self.pool.get('hr.employee').read(cr, uid, delegator_ids, ['login'])
                        emp_logins = [emp.get('login','') for emp in emps]
                        logins = '; '.join(emp_logins)
                        vals += '; ' + logins
                    
                    #Get delegate by process
                    delegator_ids = self.get_delegator_by_process(cr, uid, item.id, item.department_id.manager_id.id, context)
                    if delegator_ids:
                        emps = self.pool.get('hr.employee').read(cr, uid, delegator_ids, ['login'])
                        emp_logins = [emp.get('login','') for emp in emps]
                        logins = '; '.join(emp_logins)
                        vals += '; ' + logins
            
            elif item.state == 'cb':
                vals = ''
                employee_ids = self.pool.get('vhr.working.record').get_employee_ids_belong_to_group(cr, uid, 'vhr_cb_termination', context)
                if employee_ids:
                    employees = self.pool.get('hr.employee').read(cr, uid, employee_ids, ['login'])
                    for employee in employees:
                        if vals:
                            vals = '%s; %s' % (vals, employee.get('login', ''))
                        else:
                            vals = '%s' % (employee.get('login', ''))

#             elif item.state == 'dept_hr':
#                 vals = ''
#                 employee_ids = self.pool.get('vhr.working.record').get_employee_ids_belong_to_group(cr, uid, 'vhr_hr_dept_head', context)
#                 if employee_ids:
#                     employees = self.pool.get('hr.employee').read(cr, uid, employee_ids, ['login'])
#                     for employee in employees:
#                         if vals:
#                             vals = '%s; %s' % (vals, employee.get('login', ''))
#                         else:
#                             vals = '%s' % (employee.get('login', ''))


            else:
                vals = ''

            res[item.id] = {'is_waiting_for_action': False}
            res[item.id]['waiting_for'] = vals
            if login in vals:
                res[item.id]['is_waiting_for_action'] = True
                
        return res
    
    def is_action_user_search(self, cr, uid, obj, name, args, context=None):
        if not args:
            return []
        
        working_pool = self.pool.get('vhr.working.record')
        domain = []
        res = []
        employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=',uid)], order='active')
        if employee_ids:
            domain.extend(['&',('requester_id','in',employee_ids),('state','=','draft')])
            
            #search Supervisor
            domain.insert(0, '|')
            domain.extend(['&',('supervisor_id','in',employee_ids),('state','=','supervisor')])
            
            #Search for dept head
            department_ids = self.pool.get('hr.department').search(cr, uid, [('manager_id','in',employee_ids)])
            domain.insert(0, '|')
            domain.extend(['&',('department_id','in',department_ids),('state','=','dept_head')])
            
            #Check if have delegate in state dept head
            dict = self.get_emp_make_delegate(cr, uid, employee_ids[0], context)
            department_delegate_ids = []
            person_make_delegate_ids = []
            if dict:
                for employee_id in dict:
                    department_delegate_ids.extend(dict[employee_id])
                    person_make_delegate_ids.append(employee_id)
            
            #Delegate at dh state
            small_domain = ['&','&',('state','=','dept_head'),('department_id','in',department_delegate_ids),('department_id.manager_id','in',person_make_delegate_ids)]
            
            if domain:
                domain.insert(0, '|')
            
            domain.extend(small_domain)
            
            #Delegate at lm state
            small_domain = ['&','&',('state','=','supervisor'),('department_id','in',department_delegate_ids),('supervisor_id','in',person_make_delegate_ids)]
            
            if domain:
                domain.insert(0, '|')
            
            domain.extend(small_domain)
            
            #if login user is delegatee by some one in delegate by process
            dict = self.get_emp_make_delegate_by_process(cr, uid, employee_ids[0], context)
            if dict:
                for employee_id in dict:
                    delegate_from_id = dict[employee_id]
                    domain.insert(0,'|')
                    domain.extend(['&','&',('supervisor_id','=',delegate_from_id),
                                             ('employee_id','=',employee_id),
                                             ('state', '=', 'supervisor')])
                    
                    domain.insert(0,'|')
                    domain.extend(['&','&',('department_id.manager_id','=',delegate_from_id),
                                             ('employee_id','=',employee_id),
                                                ('state', '=', 'dept_head')])
                    
            department_ids = working_pool.get_department_of_hrbp(cr, uid, employee_ids[0], context)
            if department_ids:
                #State HRBP
                if domain:
                    domain.insert(0,'|')
                domain.extend(['&',('state','=','hrbp'),('department_id','in',department_ids)])
                
            
            groups = working_pool.get_groups(cr, uid)
            if 'vhr_cb_termination' in groups:
                if domain:
                    domain.insert(0,'|')
                domain.append(('state','=','cb'))
            
            
            res = self.search(cr, uid, domain)
        
        operator = 'in'
        for field, oper, value in args:
            if oper == '!=' and value == True:
                operator = 'not in'
                break
            elif oper == '==' and value == False:
                operator = 'not in'
                break
         
        if not res:
            return [('id', '=', 0)]
        return [('id',operator, res)]
    
    def _is_able_to_create_termination(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if not isinstance(ids, list):
            ids = [ids]
        
        for record_id in ids:
            res[record_id] = True
        return res
    
    def _get_correct_date_end_working(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if not isinstance(ids, list):
            ids = [ids]
        
        records = self.read(cr, uid, ids, ['date_end_working_approve','date_end_working_expect'])
        for record in records:
            res[record['id']] = {'correct_date_end_working_approve': '','correct_date_end_working_expect': ''}
            
            if record.get('date_end_working_approve'):
                date_approve = datetime.strptime(record['date_end_working_approve'], DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y")
                res[record['id']]['correct_date_end_working_approve'] = date_approve
            if record.get('date_end_working_expect'):
                date_expect = datetime.strptime(record['date_end_working_expect'], DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y")
                res[record['id']]['correct_date_end_working_expect'] = date_expect
        return res
    
    def _get_correct_old_date_end_working(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if not isinstance(ids, list):
            ids = [ids]
        
        records = self.read(cr, uid, ids, ['old_date_end_working_approve'])
        for record in records:
            res[record['id']] = {'correct_old_date_end_working_approve': ''}
            
            if record.get('old_date_end_working_approve'):
                date_approve = datetime.strptime(record['old_date_end_working_approve'], DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y")
                res[record['id']]['correct_old_date_end_working_approve'] = date_approve
        return res
    
    def _get_link_survey(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if not isinstance(ids, list):
            ids = [ids]
        
        survey_link_obj = self.pool.get('vhr.resignation.link.exit.survey')
        emp_obj = self.pool.get('hr.employee')
        for record in self.read(cr, uid, ids, ['employee_id','department_id']):
            res[record['id']] = ''
            employee_id = record.get('employee_id', False) and record['employee_id'][0]
            division_id = False
            if employee_id:
                employee = emp_obj.read(cr, uid, employee_id, ['division_id'])
                division_id = employee.get('division_id', False) and employee['division_id'][0]
            
            department_id = record.get('department_id', False) and record['department_id'][0]
            domain = ['&',('department_ids','=',department_id), ('active','=',True)]
            
            if division_id:
                domain.insert(0,'|')
                domain.extend(['&',('department_ids','=',division_id), ('active','=',True)])
            
            link_ids = survey_link_obj.search(cr, uid, domain)
            if link_ids:
                link = survey_link_obj.read(cr, uid, link_ids[0], ['link'])
                res[record['id']] = link.get('link', '')
        
        return res

    _columns = {
        'name': fields.char('Code', size=128),
        'employee_id': fields.many2one('hr.employee', 'Employee', ondelete='restrict'),
        'employee_code': fields.related('employee_id', 'code', type="char", string="Employee Code"),

        'company_id': fields.many2one('res.company', 'Company', ondelete='restrict'),
        'company_code': fields.related('company_id', 'code', type='char', string='Company'),

        'working_record_id': fields.many2one('vhr.working.record', 'Working Record', ondelete='restrict'),
        'office_id': fields.related('working_record_id', 'office_id_new', type='many2one', relation='vhr.office',
                                    string='Office'),
        'job_title_id': fields.related('working_record_id', 'job_title_id_new', type='many2one',
                                       relation='vhr.job.title', string='Job Title'),
                
        'job_level_id': fields.related('working_record_id', 'job_level_id_new', type='many2one',
                                       relation='vhr.job.level', string='Level'),
                
        'department_id': fields.related('employee_id', 'department_id', type='many2one',
                                        relation='hr.department', string='Department'),
                
        'supervisor_id': fields.related('employee_id', 'report_to', type='many2one', relation='hr.employee',
                                        string='Reporting line'),
        
        'contract_id': fields.many2one('hr.contract', 'Contract', ondelete='restrict'),
        'contract_type_id': fields.related('contract_id', 'type_id', type='many2one', relation='hr.contract.type',
                                           string='Contract Type'),
            
        'date_start_contract': fields.related('contract_id', 'date_start', type="date", string="Contract effective date"),
        'date_end_contract': fields.function(get_date_end_contract, type='date', string='Contract expired date'),

        'request_date': fields.date('Request Date'),
        'date_end_working_expect': fields.date('Expected last working date'),
        'date_end_working_follow_rule': fields.date('Last working date comply with labour law'),
        'old_date_end_working_approve': fields.date('Approved old last working date'),
        'date_end_working_approve': fields.date('Approved last working date'),
        'employee_reason': fields.text('Termination Reason'),
        # TODO: change later
        'ending_probation': fields.boolean('Ending Probation'),
        'resignation_type': fields.many2one('vhr.resignation.type', 'Type of leaving', ondelete='restrict'),
#         'resign_reason_detail_ids': fields.one2many('vhr.resign.reason.detail', 'termination_request_id',
#                                                     'Termination Reason', ondelete='cascade'),
        'lm_note': fields.text("Line Manager's Note"),
        'hrbp_note': fields.text("HRBP's Note"),
        'cb_note': fields.text("C&B Note"),
        'suggest_for_holding_employee': fields.text('Action for keeping employee or more improvement in the future'),
        'continue_recruiting_id': fields.many2one('vhr.dimension', 'Recruiting Again?', ondelete='restrict',
                                                  domain=[('dimension_type_id.code', '=', 'CONTINUE_RECRUITING'),
                                                          ('active', '=', True)]),

        'resign_date': fields.date('Termination date'),
        'update_date': fields.date('Update date'),
        'date_response_to_af_fa_it': fields.date('Feedback date to AF, FA, IT'),
        'severance_allowance': fields.boolean('Severance Allowance'),
        'note': fields.text('Note'),

        # 'attached_file': fields.binary('Attached File'),
        'decision_no': fields.char('Decision No', size=128),
        'sign_date': fields.date('Sign Date'),
        'signer_id': fields.many2one('hr.employee','Signer', ondelete='restrict'),
        'signer_job_title_id': fields.related('signer_id', 'title_id', type='many2one', relation="vhr.job.title",
                                              string="Signer's title", store=True),


        'state': fields.selection(STATES, 'Status', readonly=True),
        'current_state': fields.selection(STATES, 'Stage Current', readonly=True),
       
        'resignation_reason_group_id': fields.many2one('vhr.resignation.reason.group', 'Leaving Reason Group', ondelete='restrict'),
        'main_resignation_reason_id': fields.many2one('vhr.resignation.reason', 'Leaving Reason', ondelete='restrict'),
        'resignation_reason_ids': fields.many2many('vhr.resignation.reason', 'termination_resignation_rel','termination_id','resignation_reason_id','Other termination reason'),

         # TODO: remove 2 field later
        'ending_probation': fields.boolean('Ending Probation'),
        'is_probation_contract': fields.boolean('Is Probation Contract'),

        'create_uid': fields.many2one('res.users', 'Created by', readonly=True),

        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                         domain=[('object_id.model', '=', _name),
                                                 ('field_id.name', 'not in',
                                                  ['write_date', 'audit_log_ids'])]),

        'is_person_do_action': fields.function(_is_person_do_action, type='boolean', string='Is Person Do Action'),
        'attachment_count': fields.function(_count_attachment, type='integer', string='Attachments'),
        'waiting_for': fields.function(_check_waiting_for, type='char', string='Waiting For', readonly=1, multi='waiting_for'),
        'is_waiting_for_action' : fields.function(_check_waiting_for, type='boolean', string='Is Waiting For Approval', readonly = 1, multi='waiting_for', fnct_search=is_action_user_search),
        'state_log_ids': fields.one2many('vhr.state.change', 'res_id', 'History', domain=[('model', '=', _name)]),
        'requester_id': fields.many2one('hr.employee', 'Requester', ondelete='restrict'),
#         'dismiss_working_record_id': fields.many2one('vhr.working.record', 'Terminate Working Record'),
        'dismiss_working_record_ids': fields.char('List Terminate Working Record'),#Why dont i use one2many ??
        'cancel_contract_ids': fields.char('Cancel Contract'),
        'waiting_time_from_previous_step': fields.function(get_waiting_time, type='text', string='Waiting Time'),
        'users_validated': fields.text('User Validate'),
        'approve_date': fields.datetime('Approve Date'),
        'change_form_id': fields.many2one('vhr.change.form', 'Change Form', ondelete='restrict'),
        'is_offline': fields.boolean('Is offline?'),
        'is_change_contract_type': fields.boolean('Support to change employee type', help='If check true for this field then call ESB to process termination service'),
        'is_official': fields.related('contract_type_id', 'is_official', type='boolean', string='Is official'),
        'passed_state': fields.text('Passed State'),
        
        'is_requester': fields.function(_is_requester, type='boolean', string='Is Requester'),
        'is_lm': fields.function(_is_lm, type='boolean', string='Is LM'),
        'is_dept_head': fields.function(_is_dept_head, type='boolean', string='Is Dept Head'),
        'is_cb': fields.function(_is_cb, type='boolean', string='Is C&B'),
#         'is_clear_resign_reason_detail': fields.function(_is_clear_resign_reason_detail, type='boolean', string='Is Clear Resign Reason Detail'),
#         'is_change_contract_type': fields.boolean('Support to change employee type'),
        'is_able_to_create_termination': fields.function(_is_able_to_create_termination, type='boolean', string='Is Able To Create Termination'),
        #This field use for email template to get correct format
        'correct_date_end_working_approve': fields.function(_get_correct_date_end_working, type='date', string='Correct Approved last working date', multi='get_correct_date'),
        'correct_date_end_working_expect': fields.function(_get_correct_date_end_working, type='date', string='Correct Expected last working date', multi='get_correct_date'),
        'correct_old_date_end_working_approve': fields.function(_get_correct_old_date_end_working, type='date', string='Correct Old Approved last working date', multi='get_correct_date'),
        
        'is_hrbp_watching': fields.function(is_hrbp_watching, type='boolean', string='Is HRBP Watching', multi='get_data_hrbp'),
        'is_hrbp': fields.function(is_hrbp_watching, type='boolean', string='Is HRBP', multi='get_data_hrbp'),
        'is_assistant_hrbp': fields.function(is_hrbp_watching, type='boolean', string='Is Assistant HRBP', multi='get_data_hrbp'),
        'is_require_in_hrbp_update': fields.function(is_require_in_hrbp_update, type='boolean', string='Is Required In HRBP Watching'),
        'can_see_hrbp_update': fields.function(get_can_see_hrbp_update, type='boolean',
                                               string='Can I see hrbp Update?'),
#         'is_show_comment_log_state_change': fields.function(is_show_comment_log_state_change, type='boolean', string="Is Show Comment In Log State Change"),
        'email_template_sent': fields.text('Email Template Sent'),
        'link_survey': fields.function(_get_link_survey, type='char', string='Link Survey'),
    }

    _order = "id desc"

    # def _get_date_end_working_follow_rule(self, cr, uid, context=None):
    # today = datetime.today().date()
    # result_date = today +  relativedelta(days=30)
    # return result_date.strftime(DEFAULT_SERVER_DATE_FORMAT)

    def _get_user_id(self, cr, uid, context=None):
        return uid

    def _get_change_form_termination(self, cr, uid, context=None):
        dismiss_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_master_data_dismiss_change_form_code') or ''
        dismiss_code_list = dismiss_code.split(',')
            
        res_ids = self.pool.get('vhr.change.form').search(cr, uid, [('code', 'in', dismiss_code_list)])
        if res_ids:
            return res_ids[0]
        log.error('Not found DIS change form')
        return False


    def _get_requester_id(self, cr, uid, context=None):
        employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', uid)], context={"search_all_employee": True})
        if employee_ids:
            return employee_ids[0]

        return False
    
    def _get_is_able_to_create_termination(self, cr, uid, context=None):
        return self.check_is_able_to_create_termination(cr, uid, context)
    
    def _get_is_cb(self, cr, uid, context=None):
        groups = self.pool.get('res.users').get_groups(cr, uid)
        return 'vhr_cb_termination' in groups
    
#     def _get_is_offline(self, cr, uid, context=None):
#         if set(['hrs_group_system', 'vhr_cb', 'vhr_hr_dept_head']).intersection(set(self.get_groups(cr, uid))):
#             return True
#         return False

    _defaults = {
        'is_person_do_action': True,
#         'is_clear_resign_reason_detail': True,
#         'is_change_contract_type': False,
        'is_probation_contract': False,
        # 'ending_probation': True,
        # 'create_uid': _get_user_id,
        'request_date': fields.datetime.now,
        # 'date_end_working_follow_rule': _get_date_end_working_follow_rule,
        # 'date_end_working_approve': _get_date_end_working_follow_rule,
        'state': 'draft',
        'current_state': 'draft',
        'passed_state': '',
        'employee_id': _get_requester_id,
        'requester_id': _get_requester_id,
        'change_form_id': _get_change_form_termination,
        'is_able_to_create_termination': _get_is_able_to_create_termination,
        'is_cb': _get_is_cb,
        'is_requester': True,
#         'is_offline': _get_is_offline
    }
    
    def check_is_able_to_create_termination(self, cr, uid, context=None):
        """
        Only allow login user have contract official, offer to create termination
        """
        if not context:
            context = {}
        
        contract_pool = self.pool.get('hr.contract')
        groups = self.pool.get('res.users').get_groups(cr, uid)
        if 'hrs_group_system' in groups:
            return True
        
        employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=',uid)])
        if employee_ids:
            today = time.strftime(DEFAULT_SERVER_DATE_FORMAT)
            contract_ids = contract_pool.search(cr, uid, [
                                                          ('employee_id', '=', employee_ids[0]),
                                                          ('date_start', '<=', today),
                                                          ('state', '=', 'signed'),
                                                          '|', '|',
                                                          ('liquidation_date', '>=', today),
                                                          '&', ('date_end', '>=', today),('liquidation_date', '=', False),
                                                          '&', ('date_end', '=', False), ('liquidation_date', '=', False),
                                                          ], order='date_start asc')
            if contract_ids:
                contracts = contract_pool.browse(cr, uid, contract_ids, fields_process=['type_id'])
                for contract in contracts:
                    contract_type_group_code = contract.type_id and contract.type_id.contract_type_group_id and contract.type_id.contract_type_group_id.code
                    is_contract_official = contract.type_id and contract.type_id.contract_type_group_id and contract.type_id.contract_type_group_id.is_offical
                    if not is_contract_official and contract_type_group_code != 1:
                        raise osv.except_osv('Error !', "You can't create Termination Request because your current signed contracts are not official or offer !")
            else:
                raise osv.except_osv('Warning !', "You can't create Termination Request because your current signed contracts are not official or offer !")
                    
        return True
    
    # Get list group name of user
    def get_groups(self, cr, uid):
        groups = self.pool.get('res.users').get_groups(cr, uid)
        # TODO: remove later
        groups.extend(['vhr_requestor'])
        return groups
    
    def read(self, cr, user, ids, fields=None, context=None, load='_classic_read'):
        if not context:
            context = {}
        
        if 'active_test' not in context:
            context['active_test'] = False
        
        groups = self.get_groups(cr, user)
        is_have_audit_log_field = False
        if not set(groups).intersection(['hrs_group_system','vhr_cb_termination']) and 'audit_log_ids' in fields:
            fields.remove('audit_log_ids')
            is_have_audit_log_field = True
            
        if context.get('validate_read_vhr_termination_request',False):
            context['check_to_return_none_value'] = True
            log.info('\n\n validate_read_vhr_termination_request')
            if not context.get('filter_by_permission_for_termination', False):
                context['filter_by_permission_for_termination'] = True
            result_check = self.validate_read(cr, user, ids, context)
            if not result_check:
                raise osv.except_osv('Validation Error !', 'You don’t have permission to access this data !')
            
            del context['validate_read_vhr_termination_request']
        
        res =  super(vhr_termination_request, self).read(cr, user, ids, fields, context, load)
        
        if res and is_have_audit_log_field:
            if isinstance(res, list):
                for data in res:
                    if data:
                        data['audit_log_ids'] = []
            else:
                res['audit_log_ids'] = []
        
        
        if res and context.get('check_to_return_none_value', False) and set(['lm_note','can_see_hrbp_update']).intersection(fields):
            check_fields = ['resignation_type','main_resignation_reason_id','continue_recruiting_id',
                            'suggest_for_holding_employee','resignation_reason_group_id']
            change_to_element = False
            if not isinstance(res, list):
                res = [res]
                change_to_element = True
            
            for data in res:
                if not data.get('can_see_hrbp_update', False):
                    for field in check_fields:
                        data[field] = 1
            
                if not data.get('can_see_hrbp_update', False) and not data.get('is_lm', False) and data.get('is_requester', False):
                    data['lm_note'] = '.'
                
                if not data.get('can_see_hrbp_update', False) or not data.get('is_hrbp_watching', False):
                    data['hrbp_note'] = '.'
                    data['cb_note'] = '.'
                    
            if change_to_element:
                res = res[0]
            
            
        return res
    
    def validate_read(self, cr, uid, ids, context=None):
        user_groups = self.pool.get('res.users').get_groups(cr, uid)
        if set(['hrs_group_system', 'vhr_cnb_manager', 'vhr_hr_dept_head','vhr_cb_termination']).intersection(set(user_groups)):
            return True
        if isinstance(ids, (int, long)) or (isinstance(ids, list) and len(ids)) == 1:
            check_id = ids
            if isinstance(ids, list):
                check_id = ids[0]
            new_context = context and context.copy() or {}
            lst_check = self.search(cr, uid, [], context=new_context)
            if check_id not in lst_check:
                return False
        return True
    
    
    #get list company, employee belong to in contract
    def get_default_company_id(self, cr, uid, employee_id, context=None):
        if not context:
            context = {}
            
        contract_pool = self.pool.get('hr.contract')
        
        default_company_id = False
        if employee_id:
            #Get list contract of employee
            date_compare = datetime.today().date()
                
            # Mặc định field "Company" lấy theo HĐ có "is_main"=True (HĐ hết hiệu lực thì lấy HĐ sau cùng)
            contract_ids = contract_pool.search(cr, uid, [('employee_id','=',employee_id),
                                                          ('date_start', '<=', date_compare),
                                                          ('state', '=', 'signed'),
                                                          ('is_main','=',True),
                                                          '|', '|',
                                                          ('liquidation_date', '>=', date_compare),
                                                          '&', ('date_end', '>=', date_compare),
                                                          ('liquidation_date', '=', False),
                                                          '&', ('date_end', '=', False),
                                                          ('liquidation_date', '=', False),
                                                        ], order='date_start asc')
            if contract_ids:
                contract = contract_pool.read(cr, uid, contract_ids[0], ['company_id'], context=context)
                default_company_id = contract.get('company_id',False) and contract['company_id'][0]
            else:
                contract_ids = contract_pool.search(cr, uid, [('employee_id','=',employee_id),
                                                              ('state', '=', 'signed'),
                                                              ('date_start','<=', date_compare)
                                                              ], order='date_start desc')
                if contract_ids:
                    contract = contract_pool.read(cr, uid, contract_ids[0], ['company_id'], context=context)
                    default_company_id = contract.get('company_id',False) and contract['company_id'][0]

        return default_company_id

    def onchange_employee_id(self, cr, uid, ids, requester_id, employee_id, is_offline, context=None):
        if not context:
            context = {}
            
        res = {'company_id': False,'employee_code': False,'date_end_working_expect': False}
        employee_obj = self.pool.get('hr.employee')
        if employee_id:
            is_offline = False
            if requester_id and requester_id != employee_id:
                is_offline = True
            
            res['is_offline'] = is_offline
                
            employee = employee_obj.read(cr, uid, employee_id, ['code'])
            res['employee_code'] = employee.get('code','')
            
            company_id = self.get_default_company_id(cr, uid, employee_id)
            res['company_id'] = company_id
            if company_id:
                values = self.onchange_company_id(cr, uid, ids, employee_id, company_id, is_offline, context)
                res.update(values['value'])
            
        
            #Get value of field function is_hrbp_watching, can_see_hrbp_update
            if res.get('department_id', False):
                res_f = self.get_data_of_function_field_for_onchange(cr, uid, res['department_id'], res.get('contract_id',False), is_offline, context)
                res.update(res_f)
            
            if is_offline and not res.get('is_official', False) and not context.get('is_change_contract_type',False):
                
                res.update(self.get_default_value_for_colla_emp(cr, uid, context))
            else:
                res['resignation_type'] = False
                res['main_resignation_reason_id'] = False
                res['continue_recruiting_id'] = False
                res['resignation_reason_group_id'] = False
        
        return {'value': res}

        # get list company, employee belong to in empty date_end employee instance

    
    def onchange_is_change_contract_type(self, cr, uid, ids, employee_id, is_offline, is_official, is_change_contract_type, context=None):
        res = {}
        if employee_id and is_offline and not is_official and not is_change_contract_type:
            res.update(self.get_default_value_for_colla_emp(cr, uid, context))
        elif employee_id and is_offline and not is_official and is_change_contract_type:
            res['resignation_type'] = False
            res['main_resignation_reason_id'] = False
            res['resignation_reason_group_id'] = False
            res['continue_recruiting_id'] = False
        
        return {'value': res}
            
        
    def onchange_company_id(self, cr, uid, ids, employee_id, company_id, is_offline, context=None):
        """
        Loading information from active working record of employee in company_id
        """
        res = {'working_record_id': False,
               'contract_id': False,
               'contract_type_id': False,
               'office_id': False,
               'department_id': False,
               'job_title_id': False,
               'supervisor_id': False,
               'date_start_contract': False,
               'date_end_contract': False,
               'job_level_id': False
        }

        if employee_id and company_id:
            record_ids = self.pool.get('vhr.working.record').search(cr, uid, [('employee_id', '=', employee_id),
                                                                              ('company_id', '=', company_id),
                                                                              ('state','in',[False,'finish']),
                                                                              ('active', '=', True)])
            if record_ids:
                record = self.pool.get('vhr.working.record').browse(cr, uid, record_ids[0])
                res['working_record_id'] = record_ids[0]
                res['office_id'] = record.office_id_new and record.office_id_new.id or False
                res['department_id'] = record.department_id_new and record.department_id_new.id or False
                res['job_title_id'] = record.job_title_id_new and record.job_title_id_new.id or False
#                 res['job_level_id'] = record.job_level_id_new and record.job_level_id_new.id or False
                res['supervisor_id'] = record.report_to_new and record.report_to_new.id or False

                # Get data from contract
                res_contract, gap_days, get_lwd_from_enddate_contract = self.get_data_from_effective_contract(cr, uid, employee_id, company_id,
                                                                               context)
                res.update(res_contract)
                
                if not get_lwd_from_enddate_contract:
                    today = date.today()
                    date_end = today + relativedelta(days=gap_days)
                    date_end = date_end.strftime(DEFAULT_SERVER_DATE_FORMAT)
                    res['date_end_working_follow_rule'] = date_end
                    res['date_end_working_approve'] = date_end
                
#                 if res.get('contract_id',False):
#                     is_offline = self.check_is_offline(cr, uid, res['contract_id'], context)
#                     res['is_offline'] = is_offline
                
                #Get value of field function is_hrbp_watching, can_see_hrbp_update
                if res.get('department_id', False):
                    res_f = self.get_data_of_function_field_for_onchange(cr, uid, res['department_id'], res.get('contract_id',False), is_offline, context)
                    res.update(res_f)


        return {'value': res}
    
    def get_data_of_function_field_for_onchange(self, cr, uid, department_id, contract_id, is_offline, context=None):
        """
            Bắt buộc input HRBP Update khi làm offline đối với HRBP/C&B
        """
        res = {'is_hrbp_watching': False, 'can_see_hrbp_update': False,'is_require_in_hrbp_update': False,
               'is_hrbp':False, 'is_assistant_hrbp': False}
        
        employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', uid)])
        groups = ['hrs_group_system', 'vhr_hr_dept_head', 'vhr_cb_termination']
        all_groups = self.get_groups(cr, uid)
        
        collaborator_code_list = []
        if contract_id:
            contract = self.pool.get('hr.contract').browse(cr, uid, contract_id, fields_process=['type_id'])
            is_official = contract.type_id and contract.type_id.contract_type_group_id and contract.type_id.contract_type_group_id.is_offical
                                    
        if set(groups).intersection(set(all_groups)):
            res['is_hrbp_watching'] = True
            res['can_see_hrbp_update'] = True
            if is_offline and 'vhr_cb_termination' in all_groups:
                res['is_require_in_hrbp_update'] = True
                
        #Check if login user is hrbp/assist hrbp of department
        if department_id and employee_ids and contract_id:
            department_hrbp_ids = self.get_department_of_hrbp(cr, uid, employee_ids[0], context)
            department_ass_hrbp_ids = self.get_department_of_ass_hrbp(cr, uid, employee_ids[0], context)
            department_ids = department_hrbp_ids + department_ass_hrbp_ids
            if department_ids:
                res['is_hrbp_watching'] = True
                if department_id in department_ids:
                    res['can_see_hrbp_update'] = True
                    
#                     if  is_official:
                    #Require for official and collaborator
                    res['is_require_in_hrbp_update'] = True
            
            if department_id in department_hrbp_ids:
                res['is_hrbp'] = True
            
            if department_id in department_ass_hrbp_ids:
                res['is_assistant_hrbp'] = True
                        
        return res
    

    def get_data_from_effective_contract(self, cr, uid, employee_id, company_id, context=None):
        res = {}
        gap_days = 30
        get_lwd_from_enddate_contract = False
        if employee_id and company_id:
            today = datetime.today().date()
            contract_pool = self.pool.get('hr.contract')
            contract_ids = contract_pool.search(cr, uid, [('company_id', '=', company_id),
                                                          ('employee_id', '=', employee_id),
                                                          ('date_start', '<=', today),
                                                          ('is_main','=',True),
                                                          ('state', '=', 'signed'),
                                                          '|', '|',
                                                          ('liquidation_date', '>=', today),
                                                          '&', ('date_end', '>=', today),
                                                          ('liquidation_date', '=', False),
                                                          '&', ('date_end', '=', False),
                                                          ('liquidation_date', '=', False),
            ], order='date_start asc')
            
            #HĐ hết hạn mới làm terminate: cho phép load HĐ cuối cùng lên để terminate NV với LWD là ngày cuối cùng của HĐ
            if not contract_ids:
                contract_ids = contract_pool.search(cr, uid, [('company_id', '=', company_id),
                                                              ('employee_id', '=', employee_id),
                                                              ('state', '=', 'signed'),
                                                              ('date_start', '<=', today)], 
                                                    order='date_start desc')
                
                get_lwd_from_enddate_contract = True
            if contract_ids:
                contract = contract_pool.browse(cr, uid, contract_ids[0],
                                                fields_process=['type_id', 'date_start', 'date_end',
                                                                'liquidation_date'])
                res['contract_id'] = contract_ids[0]
                res['contract_type_id'] = contract.type_id and contract.type_id.id
                res['date_start_contract'] = contract.date_start
                res['date_end_contract'] = contract.liquidation_date or contract.date_end
                res['is_official'] = contract.type_id and contract.type_id.is_official or False
                
                contract_type_code = contract.type_id and contract.type_id.contract_type_group_id.code or ''
                
                probation_type_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_human_resource_probation_contract_type_group_code') or ''
                probation_type_code = probation_type_code.split(',')
                if contract_type_code in probation_type_code:
                    res['is_probation_contract'] = True
                else:
                    res['is_probation_contract'] = False

                # if contract type if official and duration=0 then gap_day = 45
                gap_days = contract.type_id.contract_type_group_id.number_of_day_to_prepare_terminate or 0
#                 if res['contract_type_id'] and contract.type_id.is_official and contract.type_id.life_of_contract == 0:
#                     gap_days = 45
                
                if get_lwd_from_enddate_contract:
                    res['date_end_working_follow_rule'] = res['date_end_contract']
                    res['date_end_working_approve'] = res['date_end_contract']

        return res, gap_days, get_lwd_from_enddate_contract
    
    def onchange_is_offline(self, cr, uid, ids, is_offline, context=None):
        if not context:
            context = {}
            
        res = {'employee_id': False, 
               'company_id': False,
               'working_record_id': False,
               'contract_id': False,
               'contract_type_id': False,
               'office_id': False,
               'department_id': False,
               'job_title_id': False,
               'supervisor_id': False,
               'date_start_contract': False,
               'date_end_contract': False
        }
        if not is_offline:
            employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', uid)])
            if employee_ids:
                res = {'employee_id': employee_ids[0]}
        
        return {'value': res}
    
    def onchange_resignation_type(self, cr, uid, ids, resignation_type, resignation_reason_group_id, context=None):
        res = {'value': {'resignation_reason_group_id': False}}
        
        if resignation_reason_group_id and resignation_type:
            group = self.pool.get('vhr.resignation.reason.group').read(cr, uid, resignation_reason_group_id, ['resignation_type_id'])
            resignation_type_id = group.get('resignation_type_id', False) and group['resignation_type_id'][0] or False
            if resignation_type_id == resignation_type:
                del res['value']['resignation_reason_group_id']
        
        return res
    
    def onchange_resignation_reason_group_id(self, cr, uid, ids, resignation_reason_group_id, main_resignation_reason_id, context=None):
        if main_resignation_reason_id:
            resign_reason = self.pool.get('vhr.resignation.reason').read(cr, uid, main_resignation_reason_id, ['reason_group_id'])
            reason_group_id = resign_reason.get('reason_group_id', False) and resign_reason['reason_group_id'][0] 
            if (reason_group_id and reason_group_id == resignation_reason_group_id) or reason_group_id == False:
                return {'value': {}}
            
        return {'value': {'main_resignation_reason_id': False}}
    
    def get_default_value_for_colla_emp(self, cr, uid, context=None):
        list_fields = {'resignation_type': ['vhr.resignation.type','IS'],
                       'main_resignation_reason_id': ['vhr.resignation.reason','IS007'],
                       'resignation_reason_group_id': ['vhr.resignation.reason.group','RRG-015'],
                       'continue_recruiting_id': ['vhr.dimension','CR-003']
                       }
        
        res = {}
        for field in list_fields:
            data = list_fields[field]
            record_ids = self.pool.get(data[0]).search(cr, uid, [('code','=',data[1])])
            if record_ids:
                res[field] = record_ids[0]
        
        return res
    
    
#     def check_is_offline(self, cr, uid, contract_id, context=None):
#         """
#         Return True if type of contract is collaborator, in other cases return False
#         """
#         if contract_id:
#             contract = self.pool.get('hr.contract').browse(cr, uid, contract_id, fields_process=['type_id'])
#             contract_type_suffix = contract.type_id and contract.type_id.contract_type_group_id and contract.type_id.contract_type_group_id.suffix
#             
#             config_parameter = self.pool.get('ir.config_parameter')
#             restrict_dept_code = config_parameter.get_param(cr, uid, 'collaborator_suffix')
#             if restrict_dept_code:
#                 restrict_dept_code_list = restrict_dept_code.split(',')
#                 if contract_type_suffix in restrict_dept_code_list:
#                     return True
#         return False

    def onchange_date_end_working_expect(self, cr, uid, ids, date_end_working_expect, request_date, is_offline, context=None):
        res = {}
        warning = {}
        if date_end_working_expect:
            groups = self.pool.get('res.users').get_groups(cr, uid)
            if not is_offline and 'vhr_cb_termination' not in groups:
                if request_date and len(request_date) > 10:
                    request_date = request_date[:10]
                gap_date_end_greater = self.compare_day(request_date, date_end_working_expect)
                if gap_date_end_greater < 0:
                    warning = {
                            'title': 'Validation Error!',
                            'message' : "Expected last working date must be greater than or equal to Request Date !"
                             }
                    date_end_working_expect = False
                    res['date_end_working_expect'] = False
            
            res['date_end_working_approve'] = date_end_working_expect

        return {'value': res,'warning': warning}

    def onchange_date_end_working_approve(self, cr, uid, ids, date_end_working_approve, request_date, is_offline, context=None):
        res = {'resign_date': False}
        warning = {}
        if date_end_working_approve:
            groups = self.pool.get('res.users').get_groups(cr, uid)
            if not is_offline and 'vhr_cb_termination' not in groups:
                if request_date and len(request_date) > 10:
                    request_date = request_date[:10]
                gap_date_end_greater = self.compare_day(request_date, date_end_working_approve)
                if gap_date_end_greater < 0:
                    warning = {
                            'title': 'Validation Error!',
                            'message' : "Approved last working date must be greater than or equal to Request Date !"
                             }
                    res['date_end_working_approve'] = False
                    return {'value': res,'warning': warning}
                    
            date_end = datetime.strptime(date_end_working_approve, DEFAULT_SERVER_DATE_FORMAT).date()
            resign_date = date_end + relativedelta(days=1)
            res['resign_date'] = resign_date.strftime(DEFAULT_SERVER_DATE_FORMAT)

        return {'value': res}

#     def onchange_resignation_type(self, cr, uid, ids, resignation_type, resign_reason_detail_ids, context=None):
#         res = {'resignation_reason': False}
#         if resign_reason_detail_ids:
#             new_resign_reason_detail_ids = []
#             for detail in resign_reason_detail_ids:
#                 if len(detail) == 3 and detail[0] in (1, 4):
#                     new_resign_reason_detail_ids.append([2, detail[1], detail[2]])
#                 elif len(detail) == 3 and detail[0] == 2:
#                     new_resign_reason_detail_ids.append(detail)
#             res = {'resign_reason_detail_ids': new_resign_reason_detail_ids}
# 
#         return {'value': res}
#     
#     def onchange_resign_reason_detail_ids(self, cr, uid, ids, resign_reason_detail_ids, context=None):
#         res = {'is_clear_resign_reason_detail': True}
#         print resign_reason_detail_ids
#         if resign_reason_detail_ids:
#             for item in resign_reason_detail_ids:
#                 if item and item[0] != 2:
#                     res['is_clear_resign_reason_detail'] = False
#                     break
#         return {'value':res}

#     def onchange_signer_id(self, cr, uid, ids, signer_id, context=None):
#         value = {}
#         if signer_id:
#             signer_info = self.pool.get('hr.employee').read(cr, uid, signer_id, ['title_id'])
#             title_id = signer_info.get('title_id', False) and signer_info['title_id'][0] or False
#             value['signer_job_title_id'] = title_id
# 
#         return {'value': value}
    
    
    
        

    def is_creator(self, cr, uid, ids, context=None):
        if ids:
            meta_datas = self.perm_read(cr, SUPERUSER_ID, ids, context)
            if meta_datas and meta_datas[0].get('create_uid', False) and meta_datas[0]['create_uid'][0] == uid:
                return True

        return False

    def is_dept_head(self, cr, uid, ids, context=None):
        if ids:
            record = self.browse(cr, uid, ids[0])
            if record and record.department_id and record.department_id.manager_id \
                    and record.department_id.manager_id.user_id \
                    and uid == record.department_id.manager_id.user_id.id:
                return True
            elif record and record.department_id and record.department_id.manager_id:
                #Check if person is delegate by dept head
                delegator_ids = self.get_delegator(cr, uid, ids[0], record.department_id.manager_id.id, context)
                emp_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=',uid)])
                if set(emp_ids).intersection(set(delegator_ids)):
                    return True
                
                #Check if person is delegate by dept head
                delegator_ids = self.get_delegator_by_process(cr, uid, ids[0], record.department_id.manager_id.id, context)
                emp_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=',uid)])
                if set(emp_ids).intersection(set(delegator_ids)):
                    return True
                
        return False
    
    def is_lm(self, cr, uid, ids, context=None):
        if ids:
            record = self.browse(cr, uid, ids[0])
            if record and record.supervisor_id and record.supervisor_id.user_id \
                    and uid == record.supervisor_id.user_id.id:
                return True
            elif record and record.supervisor_id:
                #Check if person is delegate by dept head
                delegator_ids = self.get_delegator(cr, uid, ids[0], record.supervisor_id.id, context)
                emp_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=',uid)])
                if set(emp_ids).intersection(set(delegator_ids)):
                    return True
                
                #Check if person is delegate by dept head in delegate process
                delegator_ids = self.get_delegator_by_process(cr, uid, ids[0], record.supervisor_id.id, context)
                emp_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=',uid)])
                if set(emp_ids).intersection(set(delegator_ids)):
                    return True
                
        return False
    
    def is_hrbp(self, cr, uid, ids, context=None):
        hrbp_employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', uid)])
        if ids and hrbp_employee_ids:
            department_of_hrbp_ids = self.get_department_of_hrbp(cr, uid, hrbp_employee_ids[0], context)
            if department_of_hrbp_ids:
                record = self.read(cr, uid, ids[0], ['department_id'])
                if record and record.get('department_id', False) and record['department_id'][
                    0] in department_of_hrbp_ids:
                    return True

        return False

    def is_assistant_hrbp(self, cr, uid, ids, context=None):
        hrbp_employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', uid)])
        if ids and hrbp_employee_ids:
            department_of_hrbp_ids = self.get_department_of_ass_hrbp(cr, uid, hrbp_employee_ids[0], context)
            if department_of_hrbp_ids:
                record = self.read(cr, uid, ids[0], ['department_id'])
                if record and record.get('department_id', False) and record['department_id'][
                    0] in department_of_hrbp_ids:
                    return True
 
        return False


    # def is_hr_dept_head(self, cr, uid, context=None):
    # hr_dept_uid = self.get_hr_dept_uid(cr, uid, context)
    # if hr_dept_uid and hr_dept_uid == uid:
    # return True
    #
    # return False
    #
    # def get_hr_dept_uid(self, cr, uid, context=None):
    # department_pool = self.pool.get('hr.department')
    # hr_department_ids = department_pool.search(cr, SUPERUSER_ID, [('code','=','HR')])
    # if hr_department_ids:
    # department_info = department_pool.browse(cr, uid, hr_department_ids[0])
    # manager_user_id = department_info.manager_id and department_info.manager_id.user_id and department_info.manager_id.user_id.id or False
    # return manager_user_id
    # return False
    

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        # Search rule for specific menu
        if not context:
            context = {}
        
        if 'active_test' not in context:
            context['active_test'] = False
        
        if context.get('filter_by_permission_for_termination',False) or context.get('force_search_vhr_termination_request', False):
            if context.get('force_search_vhr_termination_request', False):
                del context['force_search_vhr_termination_request']
            args = self.build_condition_menu(cr, uid, args, offset, limit, order, context, count)
        
        res = super(vhr_termination_request, self).search(cr, uid, args, offset, limit, order, context, count)
        return res

    def build_condition_menu(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', uid)], context={'active_test': False})
        if employee_ids:

            department_ids = self.pool.get('hr.department').search(cr, SUPERUSER_ID,
                                                                   [('manager_id', 'in', employee_ids)])

            department_hrbp_ids = self.get_department_of_hrbp(cr, uid, employee_ids[0], context)
            department_ass_hrbp_ids = self.get_department_of_ass_hrbp(cr, uid, employee_ids[0], context)
            department_hrbp_ids += department_ass_hrbp_ids
            # hr_dept_uid = self.get_hr_dept_uid(cr, uid, context)
            
            #if login user is delegatee by some one
            dict = self.get_emp_make_delegate(cr, uid, employee_ids[0], context)
            person_make_delegate_ids = []
            department_delegate_ids = []
            if dict:
                for employee_id in dict:
                    department_delegate_ids.extend(dict[employee_id])
                    person_make_delegate_ids.append(employee_id)
            
                    
            user_groups = self.get_groups(cr, uid)

            new_args = ['|', '|', '|','|','|','|',
                        '&', ('create_uid', '=', uid), ('state', '!=', False),
                        '&', ('employee_id', 'in', employee_ids), ('state', '!=', False),
                        '&', ('supervisor_id', 'in', employee_ids), ('state', 'not in', ['draft']),
                        
                        '&', ('department_id', 'in', department_hrbp_ids), 
                            '|',
                              ('state', 'not in', ['draft']),
                              ('current_state', 'not in', ['draft']),
                        
                        '&',('department_id', 'in', department_ids), 
                             '|',
                                ('state', 'not in', ['draft', 'supervisor', 'hrbp']),
                                ('current_state', 'not in', ['draft', 'supervisor', 'hrbp']),
                              
                    '&','&', ('department_id', 'in', department_delegate_ids), 
                             ('department_id.manager_id', 'in', person_make_delegate_ids), 
                             '|',
                                ('state', 'not in', ['draft', 'supervisor', 'hrbp']),
                                ('current_state', 'not in', ['draft', 'supervisor', 'hrbp']),
                    
                    '&','&', ('department_id', 'in', department_delegate_ids), 
                              ('supervisor_id', 'in', person_make_delegate_ids), 
                              '|',
                                 ('state', 'not in', ['draft']),
                                 ('current_state', 'not in', ['draft']),
            ]
            
            
            #if login user is delegatee by some one in delegate by process
            dict = self.get_emp_make_delegate_by_process(cr, uid, employee_ids[0], context)
            if dict:
                for employee_id in dict:
                    delegate_from_id = dict[employee_id]
                    new_args.insert(0,'|')
                    new_args.extend(['&','&',('supervisor_id','=',delegate_from_id),
                                             ('employee_id','=',employee_id),
                                             ('state', 'not in', ['draft'])])
                    
                    new_args.insert(0,'|')
                    new_args.extend(['&','&',('department_id.manager_id','=',delegate_from_id),
                                             ('employee_id','=',employee_id),
                                             '|',
                                                ('state', 'not in', ['draft', 'supervisor', 'hrbp']),
                                                ('current_state', 'not in', ['draft', 'supervisor', 'hrbp'])])
                    

            if set(['hrs_group_system', 'vhr_cnb_manager', 'vhr_hr_dept_head','vhr_cb_termination']).intersection(
                    set(user_groups)):
                new_args = []

            args += new_args
        
        else:
            args.append(('id','in',[]))

        return args

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(vhr_termination_request, self).fields_view_get(cr, uid, view_id, view_type, context,
                                                                   toolbar=toolbar, submenu=submenu)
        if context is None:
            context = {}
        if view_type == 'form':
            res = self.add_attrs_for_field(cr, uid, res, context)
        return res

    def add_attrs_for_field(self, cr, uid, res, context=None):
        employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', uid)])
        doc = etree.XML(res['arch'])
        if res['type'] == 'form':
            # When view view_vhr_working_record_submit_form
            # To add field text action_comment
            if context.get('action', False) and context.get('active_id', False):
                node = doc.xpath("//form/separator")
                if node:
                    node = node[0].getparent()
                    if context.get('required_comment', False):
                        node_notes = etree.Element('field', name="action_comment", colspan="4",
                                                   modifiers=json.dumps({'required': True}))
                    else:
                        node_notes = etree.Element('field', name="action_comment", colspan="4")
                    node.append(node_notes)
                    res['arch'] = etree.tostring(doc)
                    res['fields'].update({
                        'action_comment': {'selectable': True, 'string': 'Action Comment', 'type': 'text',
                                           'views': {}}})

            groups = self.get_groups(cr, uid)
            fields_draft = draft_permission.keys()
            department_hrbp_ids = []
            employee_id = False
            if employee_ids:
                employee_id = employee_ids[0]

                department_hrbp_ids = self.get_department_of_hrbp(cr, uid, employee_id, context)
                department_ass_hrbp_ids = self.get_department_of_ass_hrbp(cr, uid, employee_id, context)
                department_hrbp_ids += department_ass_hrbp_ids
            # hr_dept_uid = self.get_hr_dept_uid(cr, uid, context)

            # Loop for field in file vhr_termination_request_permission
            for field in fields_draft:
                for node in doc.xpath("//field[@name='%s']" % field):
                    args = []
                    modifiers = json.loads(node.get('modifiers'))
                    if set(groups).intersection(set(draft_permission[field]['write'])):
                        # WHY: create_uid != False :D
                        args += ['&', '&', ('state', '=', 'draft'), ('create_uid', '!=', uid),
                                 ('create_uid', '!=', False)]
                    else:
                        args += [('state', '=', 'draft')]

                    if set(groups).intersection(set(hrbp_permission[field]['write'])):
                        args += ['&', ('state', '=', 'hrbp'), ('department_id', 'not in', department_hrbp_ids)]
                    else:
                        args += [('state', '=', 'hrbp')]

                    num = 2
                    # if not set(groups).intersection(set(cb_permission[field]['write'])):
                    # args += [('state', '=', 'cb')]
                    # num += 1

                    # Default readonly all fields in these state
                    args += [('state', 'in', ['supervisor', 'dept_head', 'cb','finish', 'cancel'])]

                    for index in range(num):
                        args.insert(0, '|')

                    # Allow person do action override data_end_working_approve at state supervisor/dept_head
                    if field in ['date_end_working_approve']:
                        # allow vhr_cb_termination to edit date_end_working_approve
                        if 'vhr_cb_termination' in groups:
                            args = [('state', 'in', ['cancel'])]
                            modifiers['required'] = True
                        else:
                            #readonly = not ( hrbp at role of hrbp or dept_head at role of dept_head  or lm at role of lm)
                            args = ['!','|','|',
                                    '&',('is_person_do_action', '=', True),('is_hrbp', '=', True), 
                                    '&',('is_person_do_action', '=', True),('is_dept_head', '=', True),
                                    '&',('is_person_do_action', '=', True),('is_lm', '=', True)]
                            modifiers['required'] = [  # ('is_person_do_action', '=', True),
                                                       ('state', 'in', ['supervisor','dept_head', 'finish'])]
                    elif field in ['employee_id','company_id']:
                        args.insert(0, '|')
                        args.extend(['&',('state','=','draft'),('is_hrbp_watching','=',False)])
                    
                    # Only edit these field when create
                    modifiers['readonly'] = args
                    node.set('modifiers', json.dumps(modifiers))

                if field == 'employee_id':
                    for node in doc.xpath("//field[@name='%s']" % field):
                        modifiers = json.loads(node.get('modifiers'))
                        # user in group vhr_cb/ vhr_cnb_manager can see all employee
                        # user in vhr_hrbp/vhr_assistant_to_hrbp can only see employee in department of its \
                        # or department below its department
                        # other user can not edit employee
                        # move to name_search employee

                        if not set(groups).intersection(
                                set(['vhr_cb_termination', 'vhr_hrbp', 'vhr_assistant_to_hrbp'])):  # 'vhr_cb', 'vhr_cnb_manager',
                            modifiers.update({'readonly': True})

                        node.set('modifiers', json.dumps(modifiers))

        res['arch'] = etree.tostring(doc)
        return res

    def is_person_do_action(self, cr, uid, ids, context=None):
        if ids:
            # return True
#             state = context.get('state', False)
            groups = self.get_groups(cr, uid)
            record = self.browse(cr, uid, ids[0])
#             if not state:
            state = record.state or False

            if (state == 'draft' and self.is_creator(cr, uid, ids, context)) \
                    or (state == 'supervisor' and self.is_lm(cr, uid, ids, context)) \
                    or (state == 'hrbp' and  self.is_hrbp(cr, uid, ids, context)) \
                    or (state == 'dept_head' and self.is_dept_head(cr, uid, ids, context))\
                    or (state == 'cb' and 'vhr_cb_termination' in groups):
#                     or (state == 'dept_hr' and 'vhr_hr_dept_head' in groups):
                return True

        return False

    def name_get(self, cr, uid, ids, context=None):
        if not ids or False in ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        reads = self.read(cr, uid, ids, ['employee_id'], context=context)
        res = []
        for record in reads:
            name = record.get('employee_id', False) and record['employee_id'][1]
            res.append((record['id'], name))
        return res

#     def check_total_percentage_resign_reason(self, cr, uid, vals, context=None):
#         if vals.get('resign_reason_detail_ids', False):
#             total = 0
#             is_reason_null = True
#             for detail in vals['resign_reason_detail_ids']:
#                 if detail[0] == 0 or (detail[0] == 1 and detail[2] and detail[2].get('percentage', False)):
#                     is_reason_null = False
#                     total += detail[2]['percentage']
#                 elif detail[0] == 4:
#                     is_reason_null = False
#                     res_id = detail[1]
#                     if res_id:
#                         reason = self.pool.get('vhr.resign.reason.detail').read(cr, uid, res_id, ['percentage'])
#                         total += reason.get('percentage', 0)
# 
#             if total != 100 and not is_reason_null:
#                 raise osv.except_osv('Error !', 'The total percentage of resignation reason is equal 100 !')
# 
#         return True

    def check_if_no_request_exist(self, cr, uid, employee_id, company_id, contract_id, context=None):
        """
        Return True if emp-comp dont have termination not finish; dont have any termination finish with emp-comp-contract
        """
        if not context:
            context = {}
        if employee_id and company_id:
            active_ids = context.get('active_ids',[])
            not_fin_request_ids = self.search(cr, uid, [('employee_id', '=', employee_id),
                                                        ('company_id', '=', company_id),
                                                        ('state', 'not in', ['finish', 'cancel'])])
            
            request_ids = [record_id for record_id in not_fin_request_ids if record_id not in active_ids]
            if request_ids:
                employee = self.pool.get('hr.employee').read(cr, uid, employee_id, ['login'])
                raise osv.except_osv('Validation Error !',
                                     '%s has a termination request does not finish!' % employee.get('login'))
            
            #Case employee had a termination request finish in same instance
            fin_request_ids = self.search(cr, uid, [('employee_id', '=', employee_id),
                                                    ('company_id', '=', company_id),
                                                    ('contract_id','=',contract_id),
                                                    ('state', '=', 'finish')])
            
            request_ids = [record_id for record_id in fin_request_ids if record_id not in active_ids]
            if request_ids:
                employee = self.pool.get('hr.employee').read(cr, uid, employee_id, ['login'])
                raise osv.except_osv('Validation Error !',
                                     '%s already has a termination request!' % employee.get('login'))

        return True

    # date_end_working_expect and date_end_working_approve have to greater
    # or equal effect_from of active working record of employee-company
    def check_valid_date_end(self, cr, uid, date_input, working_record_id, context=None):
        if date_input and working_record_id:
            date_input = datetime.strptime(date_input, DEFAULT_SERVER_DATE_FORMAT).date()
            working_record = self.pool.get('vhr.working.record').read(cr, uid, working_record_id, ['effect_from'])
            effect_from = working_record.get('effect_from', False)
            if effect_from:
                effect_from = datetime.strptime(effect_from, DEFAULT_SERVER_DATE_FORMAT).date()
                if date_input < effect_from:
                    raise osv.except_osv('Validation Error !',
                                         '%s have to greater than or equal to Effective Date of active Working Record!' % context.get(
                                             'name', 'Last Working Date'))

        return True

    def check_date_end_working_approve(self, cr, uid, ids, context=None):
        '''
        date_end_working_approve must be greater or equal contract date_start  and less than or equal contract end date
        '''
        if ids:
            if isinstance(ids, (int, long)):
                ids = [ids]
            records = self.browse(cr, SUPERUSER_ID, ids, fields_process=['contract_id', 'date_end_working_approve'])
            for record in records:
                date_start_contract = record and record.contract_id and record.contract_id.date_start or False
                if date_start_contract:
                    date_start_contract = datetime.strptime(date_start_contract, DEFAULT_SERVER_DATE_FORMAT).date()
                
                date_end_contract = record and record.contract_id and record.contract_id.date_end or False
                if date_end_contract:
                    date_end_contract = datetime.strptime(date_end_contract, DEFAULT_SERVER_DATE_FORMAT).date()

                date_end_working_approve = record.date_end_working_approve or False
                date_end_working_approve = datetime.strptime(date_end_working_approve,
                                                             DEFAULT_SERVER_DATE_FORMAT).date()

                if (date_start_contract and date_end_working_approve < date_start_contract) \
                        or (date_end_contract and date_end_working_approve > date_end_contract):
                    raise osv.except_osv('Validation Error !',
                                         'Approved last working date have to greater than or equal to Contract effective date and less than or equal to Contract expired date !')

        return True

    def create(self, cr, uid, vals, context=None):
        if not context:
            context = {}
        
        required_fields = ['employee_id','company_id','date_end_working_expect','employee_reason']
        dict = {'employee_id': 'Employee',
                'company_id': 'Company',
                'date_end_working_expect': 'Expected last working date',
                'employee_reason': 'Termination Reason'
                }
        for field in dict.keys():
            if not vals.get(field, False):
                raise osv.except_osv('Validation Error !', 'You have to input '+ dict[field])
        
        #Check when create termination from form for other employee, raise error if employee dont belong to any special group of HR
        employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=',uid)])
        if employee_ids and vals.get('employee_id', False) not in employee_ids:
            groups = self.pool.get('res.users').get_groups(cr, uid)
            special_groups = ['vhr_cb','vhr_hrbp','vhr_assistant_to_hrbp','hrs_group_system']
            if not set(groups).intersection(special_groups):
                raise osv.except_osv('Validation Error !', "You don't have permission to create Termination for other employees")
        
            
        if vals.get('request_date',False) and len(vals['request_date']) > 10:
            vals['request_date'] = vals['request_date'][:10]
            
        context['filter_by_permission_for_termination'] = False
        if vals.get('request_date'):
            vals['name'] = self.generate_name(cr, uid, vals['request_date'], context=context)
            
#         if vals.get('resign_reason_detail_ids', False):
#             self.check_total_percentage_resign_reason(cr, uid, vals, context)
            
        self.check_if_no_request_exist(cr, uid, vals['employee_id'], vals['company_id'], vals['contract_id'], context)

        res = super(vhr_termination_request, self).create(cr, uid, vals, context)

        if res:
            self.check_date_end_working_approve(cr, uid, res, context)

        return res

    def write(self, cr, uid, ids, vals, context=None):
        if not context:
            context = {}
        context['filter_by_permission_for_termination'] = False

        for request in self.browse(cr, uid, ids,fields_process=['employee_id', 'company_id', 'contract_id', 'state', 
                                                                'users_validated','passed_state','date_end_working_approve']):

            if request and (vals.get('employee_id', False) or vals.get('company_id', False)):
                employee_id = vals.get('employee_id', request.employee_id and request.employee_id.id or False)
                company_id = vals.get('company_id', request.company_id and request.company_id.id or False)
                contract_id = vals.get('contract_id', request.contract_id and request.contract_id.id or False)
                context['active_ids'] = ids
                self.check_if_no_request_exist(cr, uid, employee_id, company_id, contract_id, context)

            if request and 'users_validated' in vals:
                if request.users_validated:
                    users_validated = filter(None, map(lambda x: x.strip(), request.users_validated.split(',')))
                    # del users_validated when return
                    if vals['users_validated'] == -1 and users_validated:
                        vals['users_validated'] = ','.join(users_validated[1:])
                    elif vals['users_validated'] not in users_validated:
                        vals['users_validated'] += ',' + request.users_validated
                    else:
                        del vals['users_validated']
            
            if request and 'passed_state' in vals:
                if request.passed_state:
                    passed_state = filter(None, map(lambda x: x.strip(), request.passed_state.split(',')))
                    # del latest state when return
                    if vals['passed_state'] == -1 and passed_state:
                        vals['passed_state'] = ','.join(passed_state[:-1])
                    elif vals['passed_state'] not in passed_state:
                        vals['passed_state'] = request.passed_state + ',' + vals['passed_state']
                    else:
                        del vals['passed_state']
            
            if request and 'date_end_working_approve' in vals:
                vals['old_date_end_working_approve'] = request.date_end_working_approve or False

        res = super(vhr_termination_request, self).write(cr, uid, ids, vals, context)

        if res:
            records = self.read(cr, uid, ids, ['state','is_change_contract_type'])
            for record in records:
                #Send mail announce adjust Last Working Date at state finish
                if 'state' not in vals and record.get('state') == 'finish' \
                 and 'date_end_working_approve' in vals and not record.get('is_change_contract_type',False):
                    self.send_mail(cr, uid, record['id'], 'finish', 'change', context)
                    
            self.check_date_end_working_approve(cr, uid, ids, context)
            # if edit date_end_working_approve at state finish, then update to WR
            if vals.get('date_end_working_approve',False):
                self.update_working_record(cr, uid, ids, context=context)
#             self.update_family_deduct(cr, uid, ids, context=context)

        return res

#     def update_family_deduct(self, cr, uid, ids, context=None):
#         ids = self.search(cr, uid, [('state', '=', 'finish'), ('id', 'in', ids)])
#         for termination in self.browse(cr, uid, ids,
#                                        fields_process=['date_end_working_approve', 'employee_id', 'company_id']):
#             if termination.employee_id and termination.company_id:
#                 family_deduct_ids = self.pool.get('vhr.family.deduct').search(cr, SUPERUSER_ID, [
#                     ('employee_id', '=', termination.employee_id.id),
#                     ('company_id', '=', termination.company_id.id)])
#                 if family_deduct_ids:
#                     family_deduct_line_obj = self.pool.get('vhr.family.deduct.line')
#                     date_end_working_approve = termination.date_end_working_approve
#                     family_deduct_line_ids = family_deduct_line_obj.search(cr, SUPERUSER_ID,
#                                                                            [('family_deduct_id', 'in',
#                                                                              family_deduct_ids),
#                                                                             '|',
#                                                                             ('to_date', '=', False),
#                                                                             ('to_date', '>', date_end_working_approve)])
#                     if family_deduct_line_ids:
#                         family_deduct_line_obj.write(cr, SUPERUSER_ID, family_deduct_line_ids,
#                                                      {'to_date': date_end_working_approve})
#         return True

    def create_working_record_from_termination(self, cr, uid, ids, context=None):
        """
        Tự động tạo ra các WR thuộc loại “Xử lý thôi việc” tương ứng với tất cả công ty mà nhân viên đang có HĐ hiệu lực. 
        Xóa những contract đã ký trong tương lai tại các công ty được tạo WR termination nếu không có contract nào có change_form_id hoặc job_applicant_id
        
        """
        res = False
        if not context:
            context = {}
        log.info('Start create working record')
        if ids:
            if not isinstance(ids, list):
                ids = [ids]
            
            parameter_obj = self.pool.get('ir.config_parameter')
            working_pool = self.pool.get('vhr.working.record')
            
            working_record_columns = working_pool._columns
            working_record_fields = working_record_columns.keys()
            
            change_form_terminated_code = parameter_obj.get_param(cr, uid, 'vhr_master_data_dismiss_change_form_code') or ''
            change_form_terminated_code = change_form_terminated_code.split(',')
            dismiss_change_form_ids = self.pool.get('vhr.change.form').search(cr, uid, [('code', 'in', change_form_terminated_code)],context=context)
                
            for record in self.read(cr, uid, ids, ['change_form_id']):
                record_id = record.get('id', False)
                # Get change_form_id from termination, not from default_get of WR anymore
                change_form_id = record.get('change_form_id', False) and record['change_form_id'][0] or False
                error_message = ''
                error_employees = ''
                context.update({'termination_id': record_id, 'record_type': 'record'})
                res_vals = {'termination_id': record_id}
                res_vals.update(working_pool.default_get(cr, SUPERUSER_ID, working_record_fields, context))
                res_vals['is_public'] = True

                employee_id = res_vals.get('employee_id', False)
                effect_from = res_vals.get('effect_from', False)
                
                #Get company from active contract at effect_from
                default_company_id, company_ids = working_pool.get_company_ids(cr, uid, employee_id, context={'effect_date':effect_from})
#                 company_id = record_vals.get('company_id', False)
                # change_form_id = record_vals.get('change_form_id', False)
                dismiss_working_record_ids = []
                if company_ids:
                    for company_id in company_ids:
                        record_vals = res_vals.copy()
                        record_vals['company_id'] = company_id
                        employee_name_related = ''
                        employee_code = ''
                        if employee_id:
                            employee = self.pool.get('hr.employee').read(cr, uid, employee_id, ['name_related', 'code'])
                            employee_name_related = employee.get('name_related', False)
                            employee_code = employee.get('code', False)
        
                            # get data when onchange effect_from
                        context['create_from_outside'] = True
                        onchange_effect_from_data = working_pool.onchange_effect_from(cr, uid, [], effect_from, employee_id,
                                                                                      company_id, False, False, False, False, True,
                                                                                      False, False, False, context)
                        # Raise error when can not find contract for employee on effect_from
                        if onchange_effect_from_data.get('warning', False):
                            error_employees += "\n" + employee_name_related + " - " + employee_code
                            error_message = onchange_effect_from_data['warning'].get('message', '')
                        else:
                            onchange_effect_from_value = onchange_effect_from_data['value']
                            for field in onchange_effect_from_value.keys():
                                if isinstance(onchange_effect_from_value[field], tuple):
                                    onchange_effect_from_value[field] = onchange_effect_from_value[field][0]
        
                            # Raise error if WR near WR create by Termination have change_form=termination
                            nearest_working_record_id = onchange_effect_from_value.get('nearest_working_record_id',False)
                            if nearest_working_record_id:
                                nearest_wr = working_pool.read(cr, SUPERUSER_ID, nearest_working_record_id, ['change_form_ids'])
                                nearest_wr_change_form_ids = nearest_wr.get("change_form_ids",[])
                                #When change form ids of nearest WR have change form in dismiss change form, raise error
                                if set(dismiss_change_form_ids).intersection(set(nearest_wr_change_form_ids)):
                                    company = self.pool.get('res.company').read(cr, uid, company_id, ['name'])
                                    error_message = "\n" + employee_name_related + " - " + employee_code + "\n" + company.get('name', '')
                                    raise osv.except_osv('Validation Error !',
                                                         "Can't create a working record with type termination after another working record with type termination of : %s" % (
                                                             error_message))
                                
                            record_vals.update(onchange_effect_from_value)
        
                            # TODO: delete change_form_id in future
                            change_form_ids = change_form_id and [change_form_id] or []
                            record_vals['change_form_ids'] = [[6, False, change_form_ids]]
        
                            try:
                                res = working_pool.create_with_log(cr, uid, record_vals, context)
                                if res:
                                    dismiss_working_record_ids.append(res)
                                    # Inactive account
        #                             self.pool.get('vhr.ldap.interface').ldap_update_employee_info(cr, uid, ids[0],'EXIT', context=context)
                            except Exception as e:
                                log.exception(e)
                                try:
                                    error_message = e.message
                                    if not error_message:
                                        error_message = e.value
                                except:
                                    error_message = ""
                                error_employees += "\n" + employee_name_related + " - " + employee_code
        
                        if error_employees:
                            effect_from = datetime.strptime(effect_from, DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y")
                            raise osv.except_osv('Validation Error !',
                                                 "Can't create working record effect on %s for following employees: %s\
                                                 \n\n\n\n Trace Log: %s" % (effect_from, error_employees, error_message))
                
                if dismiss_working_record_ids:
                    dismiss_working_record_ids = [str(item) for item in dismiss_working_record_ids]
                    dismiss_working_record_ids = ','.join(dismiss_working_record_ids)
                    super(vhr_termination_request, self).write(cr, uid, [record_id], {'dismiss_working_record_ids': dismiss_working_record_ids})
                
                #Cancel future contract in company create Termination WR if dont have any contract with change_form_id!=False or job_applicant_id!=False
                contract_pool = self.pool.get('hr.contract')
                cancel_contract_ids = contract_pool.search(cr, uid, [('employee_id','=',employee_id),
                                                                     ('date_start','>',effect_from),
                                                                     ('company_id','in',company_ids),
                                                                     ('state','=','signed')])
                if cancel_contract_ids:
                    contract_create_wr_ids = contract_pool.search(cr, uid, [('id','in', cancel_contract_ids),
                                                                            '|',('change_form_id','!=',False),
                                                                                ('job_applicant_id','!=',False)])
                    if not contract_create_wr_ids:
                        contract_pool.button_set_to_cancel_signed(cr, uid, cancel_contract_ids, context={'do_not_inactive_employee': True})
                        cancel_contract_ids = ','.join([str(item) for item in cancel_contract_ids])
                        super(vhr_termination_request, self).write(cr, uid, record_id, {'cancel_contract_ids': cancel_contract_ids})
                

        return res

    def update_working_record(self, cr, uid, ids, context=None):
        ids = self.search(cr, uid, [('state', '=', 'finish'), ('id', 'in', ids)])
        for termination in self.read(cr, uid, ids, ['date_end_working_approve', 'dismiss_working_record_ids']):
            working_pool = self.pool.get('vhr.working.record')
            contract_pool = self.pool.get('hr.contract')
            new_date_end = termination.get('date_end_working_approve',False)
            dismiss_working_record_ids = termination.get('dismiss_working_record_ids','') or ''
            dismiss_working_record_ids = dismiss_working_record_ids.split(',')
            dismiss_working_record_ids = [int(item) for item in filter(None, dismiss_working_record_ids)]
            if not dismiss_working_record_ids:
                dismiss_working_record_ids = working_pool.search(cr, uid, [('termination_id', '=', termination['id'])])

            # We dont need to check validate effect_from of working_record_id
            # because function write of working record will do this task
            try:
                if dismiss_working_record_ids:
                    contexts = {'do_not_update_to_contract': True, 
                                'update_from_termination': True,
                                'do_not_update_nearest_larger_wr': True}
                    for record_id in dismiss_working_record_ids:
                        #Tự update liquidation date trong contract trước khi new date_end <= contract_date_end +1, 
                        #và không có WR nào có effect_from lớn hơn 
                        record = working_pool.read(cr, uid, record_id, ['contract_id','company_id','effect_from','employee_id'])
                        if record.get('contract_id', False):
                            company_id = record.get('company_id', False) and record['company_id'][0]
                            employee_id = record.get('employee_id', False) and record['employee_id'][0]
                            contract = contract_pool.read(cr, uid, record['contract_id'][0], ['date_end'])
                            if not contract.get('date_end',False) or self.compare_day(new_date_end, contract['date_end']) >= -1:
                                record_ids = working_pool.search(cr, uid, [('company_id','=','company_id'),
                                                                           ('effect_from','>', record['effect_from']),
                                                                           ('effect_from','<=',new_date_end),
                                                                           ('employee_id','=',employee_id)])
                                if not record_ids:  
                                    new_date_end_strp = datetime.strptime(new_date_end, DEFAULT_SERVER_DATE_FORMAT).date()
                                    liquidation_date = new_date_end_strp + relativedelta(days=1)
                                    liquidation_date = liquidation_date.strftime(DEFAULT_SERVER_DATE_FORMAT)
                                    contract_pool.write(cr, uid, record['contract_id'][0], {'liquidation_date': liquidation_date})
                                    
                        working_pool.write_with_log(cr, uid, record_id,
                                       {'effect_from': new_date_end, 'effect_to': False}, context=contexts)

            except Exception as e:
                log.exception(e)
                try:
                    error_message = e.message
                    if not error_message:
                        error_message = e.value
                except:
                    error_message = ""
                raise osv.except_osv('Validation Error !',
                                     "You cannot update [Approved last working date] of this request !\
                                     \n\n\n\n Trace Log: %s" % error_message)

        return

    def unlink(self, cr, uid, ids, context=None):
        if ids:
            requests = self.read(cr, uid, ids, ['state', 'is_offline'])
            for request in requests:
                state = request.get('state', False)
#                 is_offline = request.get('is_offline', False)
#                 if state not in ['hrbp'] and is_offline:
#                     raise osv.except_osv('Validation Error !',
#                                          'You can only delete offline records which are at state hrbp!')
                if state not in ['draft']:
                    raise osv.except_osv('Validation Error !', 'You can only delete records which are at state Draft !')

        res = super(vhr_termination_request, self).unlink(cr, uid, ids, context)
        return res

    # Do not allow to submit/approve if employee do action in next state dont have user_id
    # Only need to check user do action in state :draft/supervisor/hrbp because other state get user do action in group
    def check_exist_action_user_for_next_state(self, cr, uid, ids, next_state, context=None):
        if ids and next_state:
            records = self.browse(cr, uid, ids)
            error_employees = ""
            for record in records:
                supervisor_user_id = record.supervisor_id and record.supervisor_id.user_id and record.supervisor_id.user_id.id or False
                if next_state == 'supervisor' and not supervisor_user_id:
                    if not record.supervisor_id:
                        raise osv.except_osv('Validation Error !',
                                             "Don't have report to in this termination !")

                    error_employees += "\n" + record.supervisor_id.name_related + " - " + record.supervisor_id.code
                elif next_state == 'hrbp':
                    if not record.department_id:
                        raise osv.except_osv('Validation Error !',
                                             "Don't have department in this termination !")
                    hrbps = record.department_id.hrbps
                    ass_hrbps = record.department_id.ass_hrbps
                    hrbps += ass_hrbps
                    count_hrbp = len(hrbps)
                    non_user_ids = 0
                    for hrbp in hrbps:
                        user_id = hrbp.user_id
                        if not user_id:
                            non_user_ids += 1
                            error_employees += "\n" + hrbp.name_related + " - " + hrbp.code
                    if non_user_ids != count_hrbp:
                        error_employees = ""

                elif next_state == 'dept_head':
                    dept_head = record.department_id.manager_id
                    if not dept_head:
                        departments = self.pool.get('hr.department').code_get(cr, uid, [record.department_id.id],
                                                                              context)
                        department_code = departments[0][1] or ''
                        raise osv.except_osv('Validation Error !',
                                             'This department do not have manager: %s' % department_code)

                    elif not dept_head.user_id:
                        error_employees += "\n" + dept_head.name_related + " - " + dept_head.code

            if error_employees:
                raise osv.except_osv('Validation Error !',
                                     'The following employees do not have account domain: %s' % error_employees)

        return True

    def is_person_already_validated(self, cr, uid, ids, context=None):
        if ids:
            request = self.browse(cr, uid, ids[0], fields_process=['users_validated'], context=context)
            if request.users_validated and request.waiting_for:
                user_validated_ids = filter(None, map(lambda x: x and int(x) or '', request.users_validated.split(',')))
                user_validated_data = self.pool.get('res.users').read(cr, uid, user_validated_ids, ['login'])
                user_validated = filter(None, map(lambda x: x.get('login', ''), user_validated_data))
                waiting_for_list = filter(None, map(lambda x: x.strip(), request.waiting_for.split(';')))
                for i in user_validated:
                    if i in waiting_for_list:
                        return i
        return False

    # Action for workflow
#     def send_mail_template(self, cr, uid, ids, mail_name, context):
#         email_temp_obj = self.pool.get('email.template')
#         template_id = email_temp_obj.search(cr, uid, [('name', '=', mail_name)])
#         email_temp_obj.send_mail(cr, uid, template_id[0], ids[0], attach_ids=None, force_send=True,
#                                  raise_exception=False, context=context)

    def action_next(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        log.info('Change termination status to next state')
        if ids:
            record_id = ids[0]
            already_validate_user = self.is_person_already_validated(cr, uid, ids, context=context)
            
            if self.is_person_do_action(cr, uid, ids, context) or already_validate_user:
                vals = {}
                record = self.read(cr, uid, record_id, ['state'])
                state = record.get('state', False)
#                 state = context.get('state', False)
                is_offline = context.get('is_offline', False)
                is_official = context.get('is_official', False)
                is_create_wr = False
                
                CHECK_STATES = STATES_ONLINE
                if is_offline:
                    CHECK_STATES = STATES_OFFLINE
    
                list_state = [item[0] for item in CHECK_STATES]
                index_new_state = list_state.index(state) + 1
                if index_new_state >= len(list_state):
                    list_dict_states = {item[0]: item[1] for item in CHECK_STATES}
                    raise osv.except_osv('Error !', 'You can not approve at state %s !' % list_dict_states[state])
                
                vals['state'] = list_state[index_new_state]
                vals['current_state'] = list_state[index_new_state]
                vals['users_validated'] = str(uid)
                #Write old state to passed_state to remember where is previous pass state
                if not already_validate_user:
                    vals['passed_state'] = state
                    
                vals['approve_date'] = datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                
#                 if is_offline:
#                     if is_official:
#                         if vals['state'] == 'cb':
#                             vals['state'] = 'finish'
#                             vals['current_state'] = 'finish'
# #                         elif vals['state'] == 'finish':
#                             is_create_wr = True
#                     elif vals['state'] == 'finish':
#                         is_create_wr = True
                if vals['state'] == 'finish':
                    is_create_wr = True
                
                self.check_exist_action_user_for_next_state(cr, uid, ids, vals['state'], context)
                res = self.write(cr, uid, ids, vals, context)

                # by pass next state if user still is validate person
                if res:
                    if is_create_wr:
                        self.create_working_record_from_termination(cr, uid, ids, context=context)
                        
                    if already_validate_user:
                            context['ACTION_COMMENT'] = "already validate by: " + already_validate_user
                            context['action_user'] = already_validate_user
                    
                    list_dict_states = {item[0]: item[1] for item in STATES}
                    self.write_log_state_change(cr, uid, record_id, list_dict_states[state], list_dict_states[vals['state']], context)
                    
#                     if state != 'finish':
#                         self.send_mail(cr, uid, record_id, state, 'approve', context)
                    if vals['state'] not in  ['finish']:
                        context['state'] = vals['state']
                        
                        self.action_next(cr, uid, ids, context=context)
                        
#                     if vals['state'] in  ['finish']:
#                         termination = self.browse(cr, uid, ids[0],context=context)
#                         if termination:
#                             employee_id = termination.employee_id.id if termination.employee_id else False
#                             termination_id = termination.id
#                             if termination.contract_type_id and termination.contract_type_id.contract_type_group_id:
#                                 contract_type_group= termination.contract_type_id.contract_type_group_id.code
#                                 state_change = 'opening'
#                                 state_candidate = 'employee'
#                                 if employee_id and termination_id and contract_type_group in ('2','CTG-008'):
#                                     cr.execute('update hr_applicant set state = %s\
#                                         where id in (\
#                                                 select hra.id\
#                                                 from hr_applicant hra\
#                                                 left join vhr_termination_request tr on tr.employee_id = hra.emp_id\
#                                                 where tr.is_change_contract_type = true and hra.emp_id = %s and hra.state = %s and tr.id = %s\
#                                                )',(state_change,employee_id,state_candidate,termination_id))
        return True
    
    def unlink_wr(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        
        if ids:
            if not isinstance(ids, list):
                ids = [ids]
            context['update_from_termination'] = 1
            data = self.read(cr, uid, ids[0], ['dismiss_working_record_ids'], context=context)
            dismiss_working_record_ids = data.get('dismiss_working_record_ids','') or ''
            dismiss_working_record_ids = dismiss_working_record_ids.split(',')
            dismiss_working_record_ids = [int(item) for item in filter(None,dismiss_working_record_ids)]
            if dismiss_working_record_ids:
                    self.pool.get('vhr.working.record').unlink(cr, uid, dismiss_working_record_ids, context=context)
                
                #Reactive account
#                 self.pool.get('vhr.ldap.interface').ldap_update_employee_info(cr, uid, ids[0],'CANCEL', context=context)

    def action_cancel(self, cr, uid, ids, context=None):
        log.info('Cancel termination request')
        if context is None:
            context = {}
        if ids:
            record = self.read(cr, uid, ids[0], ['state','cancel_contract_ids'])
            state = record.get('state', False)
            cancel_contract_ids = record.get('cancel_contract_ids', '') or ''
            cancel_contract_ids = cancel_contract_ids.split(',')
            cancel_contract_ids = [int(item) for item in filter(None,cancel_contract_ids)]
            
            #Dont match with working record anymore, in case cancel contract link with working record in termination
            self.write(cr, uid, ids, {'state': 'cancel'}, context=context)

            # TODO: open later
            self.unlink_wr(cr, uid, ids, context=context)
            
            #signed contract
            if cancel_contract_ids:
                self.pool.get('hr.contract').button_set_to_signed(cr, uid, cancel_contract_ids)
            
            if state == 'finish':
                self.send_mail(cr, uid, record['id'], 'finish', 'change', context)
                self.write(cr, uid, ids, {'working_record_id': False}, context=context)
            
        return True

    def action_reject(self, cr, uid, ids, context=None):
        log.info('action_reject')
        if ids:
            if self.is_person_do_action(cr, uid, ids, context):
                self.action_cancel(cr, uid, ids, context=context)
        return True

    def action_return(self, cr, uid, ids, context=None):
        log.info('action_return')
        if ids:
            if self.is_person_do_action(cr, uid, ids, context):
                vals = {}
                record = self.read(cr, uid, ids[0], ['state','passed_state'])
                state = record.get('state', False)
                
                is_offline = context.get('is_offline', False)
                is_official = context.get('is_official', False)
                if state in ['draft', 'finish']:
                    raise osv.except_osv('Error !',
                                         'Termination Request can\'t return!')
                if is_offline:
#                     if is_official:
#                         if state == 'dept_hr':
#                             vals['state'] = 'draft'
#                             vals['current_state'] = 'draft'
#                     else:
                    raise osv.except_osv('Error !',
                                         'Termination Request can\'t return!')
                else:
                    list_state = [item[0] for item in STATES_ONLINE]
                    new_state = ''
                    passed_state = filter(None, map(lambda x: x.strip(), record.get('passed_state','').split(',')))
                    if passed_state and passed_state[-1] in list_state:
                        new_state = passed_state[-1]
                    else:
                        index_new_state = list_state.index(state) - 1
                        new_state = list_state[index_new_state]
                        
                    vals['state'] = new_state
                    vals['current_state'] = new_state
#                     if state == 'dept_hr':
#                         self.unlink_wr(cr, uid, ids, context=context)
                vals['approve_date'] = datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                # indicate to remove all users_validated
                vals['users_validated'] = -1
                vals['passed_state'] = -1
                self.write(cr, uid, ids, vals, context=context)
                # TODO: open later
#                 self.send_mail(cr, uid, ids[0], state, 'return')

        return True

    def open_window(self, cr, uid, ids, context=None):
        view_open = 'view_vhr_termination_request_submit_form'
        action = {
            'name': 'Notes',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.pool.get('ir.model.data').get_object_reference(cr, uid, 'vhr_human_resource', view_open)[1],
            'res_model': 'vhr.termination.request',
            'context': context,
            'type': 'ir.actions.act_window',
            # 'nodestroy': True,
            'target': 'new',
            # 'auto_refresh': 1,
            'res_id': ids[0],
        }
        return action

    def execute_workflow(self, cr, uid, ids, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        
        print '\n uid=',uid,';;;ids=',ids
        if context is None: context = {}
        list_states = {item[0]: item[1] for item in STATES}
        record_id = ids[0]
        record = self.read(cr, uid, record_id, ['state','is_change_contract_type'])
        old_state = record.get('state', False)
        state_vals = {}
        action_result = False
        action_next_result = False
        if context.get('action', False) in ['submit', 'approve']:
            action_next_result = self.action_next(cr, uid, ids, context)

        elif context.get('action', False) == 'return':
            action_result = self.action_return(cr, uid, ids, context)

        elif context.get('action', False) == 'reject':
            action_result = self.action_reject(cr, uid, ids, context)

        elif context.get('action', False) == 'cancel':
            action_result = self.action_cancel(cr, uid, ids, context)
        
        #Dont send mail when make termination for change employee type
        if (action_next_result or action_result) and not record.get('is_change_contract_type', False):
            record = self.read(cr, uid, record_id, ['state'])
            new_state = record.get('state', False)
            if old_state != new_state:
                self.send_mail(cr, uid, record_id, old_state, new_state, context)
                            
        if context.get('action') and action_result:
            record = self.read(cr, uid, record_id, ['state'])
            new_state = record.get('state', False)
            self.write_log_state_change(cr, uid, record_id, list_states[old_state], list_states[new_state], context)

        return True
    
    def write_log_state_change(self, cr, uid, record_id, old_state, new_state, context=None):
        if not context:
            context = {}
        state_vals = {}
        state_vals['old_state'] = old_state
        state_vals['new_state'] = new_state
#         state_vals['create_uid'] = uid
        state_vals['res_id'] = record_id
        state_vals['model'] = self._name
        if 'ACTION_COMMENT' in context:
            state_vals['comment'] = context['ACTION_COMMENT']
        self.pool.get('vhr.state.change').create(cr, uid, state_vals)
        return True
    

    def generate_name(self, cr, uid, request_date, context=None):
        stt = 0
        if context is None:
            context = {}
        context.update({'active_test': False})
        date_request = datetime.strptime(request_date, DEFAULT_SERVER_DATE_FORMAT).strftime("%d%m%Y")
        result = self.search(cr, uid, [('request_date', '=', request_date)], context=context)
        if result:
            stt = len(result) + 1
        else:
            stt += 1
        number = "%03d" % (stt,)
        return 'QDTV-%s/%s' % (date_request, number)

    def action_print_termination_request(self, cr, uid, ids, context=None):
        emp_obj = self.pool.get('hr.employee')
        company_obj = self.pool.get('res.company')
        office_obj = self.pool.get('vhr.office')
        data = self.read(cr, uid, ids, [
                            'name', 'employee_id', 'resign_date', 'date_end_working_expect', 'office_id', 'company_id',
                            'resignation_type','contract_id','is_official','date_end_working_approve'
        ], context=context)[0]

        emp_id = data.get('employee_id', False) and data['employee_id'][0] or []
        if emp_id:
            emp_data = emp_obj.read(cr, uid, emp_id, ['name'], context=context)
            for k, v in emp_data.iteritems():
                new_key = 'emp_' + k
                data[new_key] = emp_data[k]
        data.update({'day': '', 'month': '', 'year': '', 'hanoi': ''})
        date_end = data['date_end_working_approve'] or ''
        data['day'] = str(date_end[8:10])
        data['month'] = str(date_end[5:7])
        data['year'] = str(date_end[:4])

        office_id = data['office_id'] and data['office_id'][0] or []
        if office_id:
            office_data = office_obj.browse(cr, uid, office_id, fields_process=['city_id'], context=context)
            city = office_data.city_id and office_data.city_id.name or ''
            data.update({'city': city})
            if office_data.city_id and office_data.city_id.code == '01':
                data.update({'hanoi': u'– làm việc tại văn phòng Hà Nội -  nghỉ việc'})
        
        data['head_com_title'] = u'Tổng Giám đốc'
        data['com_office_city_id'] = ''
        com_id = data['company_id'] and data['company_id'][0] or []
        if com_id:
            com_data = company_obj.read(cr, uid, com_id, ['authorization_date','is_member','city_id','office_id'], context=context)
            if com_data.get('is_member', False):
                data['head_com_title'] = u'Giám đốc'
                
            for k, v in com_data.iteritems():
                new_key = 'com_' + k
                data[new_key] = com_data[k]
            
            office_id = com_data.get('office_id', False) and com_data['office_id'][0] or False
            if office_id:
                office = office_obj.read(cr, uid, office_id, ['city_id'])
                if office.get('city_id', False):
                    data['com_office_city_id'] = office.get('city_id', 1)
        
        data['company_name'] = data['company_id'] and data['company_id'][1] or ''
        
        #Nếu resignation_type = "IS" thì chọn mẫu Công ty cho nghỉ, ngược lại thì chọn mẫu nhân viên nghỉ việc
#         template_report_name = 'clicker_termination_report'
#         resignation_type_id = data.get('resignation_type',False) and data['resignation_type'][0] or False
#         if resignation_type_id:
#             resignation = self.pool.get('vhr.resignation.type').read(cr, uid, resignation_type_id, ['code'])
#             code = resignation.get('code','')
#             if code == 'IS':
#                 template_report_name = 'company_termination_clicker_report'
        
        template_report_name = 'official_termination_report'
        if not data.get('is_official', False):
            template_report_name = 'colla_termination_report'
        
        contract_id = data.get('contract_id',False) and data['contract_id'][0] or False
        if contract_id:
            contract = self.pool.get('hr.contract').read(cr, uid, contract_id, ['title_signer','info_signer'])
            data['title_signer'] = contract.get('title_signer', '') or ''
            data['info_signer'] = contract.get('info_signer', '') or ''
            data['title_signer_upper'] = data['title_signer'].upper()

        report_name = (data['name'] or '') + '_' + (data['emp_name'] or '')
        datas = {
            'ids': ids,
            'model': 'vhr.termination.request',
            'form': data,
        }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': template_report_name,
            'datas': datas,
            'name': report_name
        }
        
    def send_mail(self, cr, uid, record_id, state, new_state, context=None):
#         if not context:
        context = {}
        if record_id and state and new_state:
            action_user = ''
            if context.get('action_user', False):
                action_user = context['action_user']
            else:
                user = self.pool.get('res.users').read(cr, uid, uid, ['login'])
                if user:
                    action_user = user.get('login','')
            
            #Get mail template data by workflow of record
            mail_process = mail_process_of_ter_online
            record = self.read(cr, uid, record_id, ['is_offline','is_official','date_end_working_approve','email_template_sent','employee_id'])
            
            
            is_use_cc_level_fr_3 = False
            param_level = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_human_resource_level_use_cc_level_fr_3') or ''
            if param_level:
            
                employee_id = record.get('employee_id', False) and record['employee_id'][0]
                if employee_id:
                    emp = self.pool.get('hr.employee').read(cr, SUPERUSER_ID, employee_id, ['job_level_person_id'])
                    level_person = emp.get('job_level_person_id', False) and emp['job_level_person_id'][1] or ''
                    if level_person and level_person >= param_level:
                        is_use_cc_level_fr_3 = True
                    
            
            email_template_sent = record.get('email_template_sent','') or ''
            list_email_template_sent = email_template_sent and email_template_sent.split(',') or []
            if record.get('is_offline', False):
                if record.get('is_official', False):
                    mail_process = mail_process_of_ter_offline_official
                else:
                    mail_process = mail_process_of_ter_offline_not_official
            
            name = 'online'
            if mail_process == mail_process_of_ter_offline_official:
                name = 'offline official'
            elif mail_process == mail_process_of_ter_offline_not_official:
                name = 'offline not official'
            log.info("Send mail in Termination %s from old state %s to new state %s"% (name, state, new_state))
                
            if state in mail_process.keys():
                data = mail_process[state]
                for mail_data in data:
                    if new_state == mail_data[0]:
                        mail_detail = mail_data[1]
                        
                        
                        #Neu level tu 3.1 tro len dung cc theo muc cc_level_fr_3
                        if is_use_cc_level_fr_3 and 'cc_level_fr_3' in  mail_detail:
                            mail_detail['cc'] = mail_detail.get('cc_level_fr_3',[])
                        
                        vals = {'action_user':action_user, 
                                'tr_id': record_id,
                                'request_code': 'TR ' + str(record_id)}
                        
                        if mail_detail.get('days_late', False):
                            approve_date = datetime.today().date()
                            date_end_working_approve = record.get('date_end_working_approve', False)
                            if not date_end_working_approve:
                                break
                            
                            date_end_working_approve = datetime.strptime(date_end_working_approve, DEFAULT_SERVER_DATE_FORMAT).date()
                            gaps = approve_date - date_end_working_approve
                            if gaps.days > 0:
                                vals['number_of_days_late'] = gaps.days
                            else:
                                continue
                        
                        if mail_detail.get('mail_template','') in list_email_template_sent:
                            continue
                        if mail_detail.get('only_sent_once', False):
                            if email_template_sent:
                                email_template_sent += ',' 
                            email_template_sent += mail_detail.get('mail_template','')
                        
                        list_group_mail_to = mail_detail['to']
                        list_mail_to, list_mail_cc_from_group_mail_to = self.get_email_to_send(cr, uid, record_id, list_group_mail_to, context)
                        mail_to = ';'.join(list_mail_to)
                        vals['email_to'] = mail_to
                        
                        if 'cc' in mail_detail:
                            list_group_mail_cc = mail_detail['cc']
                            list_mail_cc, list_mail_cc_from_group_mail_cc = self.get_email_to_send(cr, uid, record_id, list_group_mail_cc, context)
                            list_mail_cc += list_mail_cc_from_group_mail_cc + list_mail_cc_from_group_mail_to
                            list_mail_cc = list(set(list_mail_cc))
                            mail_cc = ';'.join(list_mail_cc)
                            vals['email_cc'] = mail_cc
                        
                        link_email = self.get_url(cr, uid, record_id, context)
                        vals['link_email'] = link_email
                        context['action_from_email'] = mail_detail.get('action_from_email','')
                        context['not_split_email'] = mail_detail.get('not_split_email',False)
                        self.pool.get('vhr.sm.email').send_email(cr, uid, mail_detail['mail_template'], vals, context)
            
            if email_template_sent:
                super(vhr_termination_request, self).write(cr, uid, record_id, {'email_template_sent': email_template_sent})
        return True
    
    def get_email_to_send(self, cr, uid, record_id, list, context=None):
        """
        Returl list email from list
        """
        res = []
        res_cc = []
        if list and record_id:
            record = self.browse(cr, uid, record_id)
            
                
            for item in list:
                if item == 'lm':
                    mail = record.supervisor_id and record.supervisor_id.work_email or ''
                    if mail:
                        res.append(mail)
                    
                    #Send to delegator
                    delegator_ids = self.get_delegator(cr, uid, record_id, record.supervisor_id.id, context)
                    if delegator_ids:
                        delegators = self.pool.get('hr.employee').read(cr, uid, delegator_ids, ['work_email'])
                        delegate_mails = [delegator.get('work_email','') for delegator in delegators]
                        res.extend(delegate_mails)
                    
                elif item == 'dept_head':
                    mail = record.department_id and record.department_id.manager_id and record.department_id.manager_id.work_email or ''
                    if mail:
                        res.append(mail)
                    
                    #Send to delegator
                    delegator_ids = self.get_delegator(cr, uid, record_id, record.department_id.manager_id.id, context)
                    if delegator_ids:
                        delegators = self.pool.get('hr.employee').read(cr, uid, delegator_ids, ['work_email'])
                        delegate_mails = [delegator.get('work_email','') for delegator in delegators]
                        res.extend(delegate_mails)
                    
                elif item == 'requester':
                    name, id, mail = self.get_requester_name_and_id(cr, uid, record_id, context)
                    if mail:
                        res.append(mail)
                
                elif item == 'employee':
                    mail = record.employee_id and record.employee_id.work_email or ''
                    if mail:
                        res.append(mail)
                elif item == 'hrbp':
                    hrbps = record.department_id and record.department_id.hrbps or False
                    if hrbps:
                        mail = []
                        for hrbp in hrbps:
                            mail.append(hrbp.work_email)
                        if mail:
                            res.extend(mail)
                elif item == 'assist_hrbp':
                    hrbps = record.department_id and record.department_id.ass_hrbps or False
                    if hrbps:
                        mail = []
                        for hrbp in hrbps:
                            mail.append(hrbp.work_email)
                        if mail:
                            res.extend(mail)
                
#                 elif item == 'cb':
#                     name ,id, mail = self.pool.get('vhr.working.record').get_cb_name_and_id(cr, uid, context)
#                     if mail:
#                         res.extend(mail)
                
                elif item == 'dept_hr':
                    name ,id, mail = self.pool.get('vhr.working.record').get_dept_hr_name_and_id(cr, uid, context)
                    if mail:
                        res.extend(mail)
                
                elif item == 'lm_loop':
                    mail = self.get_lm_loop_mail(cr, uid, record_id, context)
                    if mail:
                        res.extend(mail)
                elif item == 'RAM':
                    rams = record.department_id and record.department_id.rams or False
                    if rams:
                        mail = []
                        for ram in rams:
                            mail.append(ram.work_email)
                        if mail:
                            res.extend(mail)
                
                elif item == 'cb_manager':
                    name ,id, mail = self.get_name_and_id_of_group(cr, uid, 'vhr_cnb_manager', context)
                    if mail:
                        res.extend(mail)
                else:
                    mail_group_pool = self.pool.get('vhr.email.group')
                    mail_group_ids = mail_group_pool.search(cr, uid, [('code','=',item)])
                    if mail_group_ids:
                        mail_group = mail_group_pool.read(cr, uid, mail_group_ids[0], ['to_email','cc_email'])
                        to_email = mail_group.get('to_email','') or ''
                        cc_email = mail_group.get('cc_email','') or ''
                        mail_to  = to_email.split(';')
                        mail_cc  = cc_email.split(';')
                        res.extend(mail_to)
                        res_cc.extend(mail_cc)
                    
                    else:
                        log.info("Can't find mail for " + item)
        return res, res_cc
    
    
    def get_name_and_id_of_group(self, cr, uid, group_name, context=None):
        if not context:
            context = {}
            
        names = []
        emp_ids = []
        mails = []
        
        if group_name:
            employee_ids = self.pool.get('vhr.working.record').get_employee_ids_belong_to_group(cr, uid, group_name, context)
            if employee_ids:
                employees = self.pool.get('hr.employee').read(cr, uid, employee_ids, ['login','work_email'])
                for employee in employees:
                    
                    if context.get('active_employee_id', False):
                        #Check if have permission location
                        res, res_employee_ids = self.get_domain_based_on_permission_location(cr, uid, [employee['id']], context)
                        if res and context['active_employee_id'] not in res_employee_ids:
                            continue
                        
                    emp_ids.append(employee.get('id',False))
                    names.append(employee.get('login',''))
                    mails.append(employee.get('work_email',''))
        
        return names, emp_ids, mails

            
    #TODO: check lai
    def get_url(self, cr, uid, res_id, context=None):
        if isinstance(res_id, list):
            res_id = res_id[0]
        model_data = self.pool.get('ir.model.data')
        action_id = model_data.xmlid_lookup(cr, uid, 'vhr_human_resource.act_vhr_termination_request')[2]
        
        url = ''
        config_parameter = self.pool.get('ir.config_parameter')
        base_url = config_parameter.get_param(cr, uid, 'web.base.url') or ''
        if base_url:
            url = base_url
        url += '/web#id=%s&view_type=form&model=vhr.termination.request&action=%s' % (res_id, action_id)
        return url
    
    def get_requester_name_and_id(self, cr, uid, record_id, context=None):
        requester_name = ''
        requester_id = False
        requester_mail = ''
        if record_id:
            termination = self.read(cr, uid, record_id, ['employee_id','is_offline'])
            employee_id = termination.get('employee_id', False) and termination['employee_id'][0]
            
            meta_datas = self.perm_read(cr, SUPERUSER_ID, [record_id], context)
            user_id =  meta_datas and meta_datas[0].get('create_uid', False) and meta_datas [0]['create_uid'][0] or False
            if user_id:
                employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', user_id)], 0, None, None,
                                                                   context)
                if employee_ids:
                    employee = self.pool.get('hr.employee').read(cr, uid, employee_ids[0], ['login','work_email'])
                    requester_name =employee.get('login', '')
                    requester_id = employee.get('id', False)
                    requester_mail = employee.get('work_email','')
                    
                    #khong lay mail requester trong truong hop submit gium termination online
                    if employee_id not in employee_ids and not termination.get('is_offline', False):
                        return requester_name, requester_id, ''
        
        return requester_name, requester_id, requester_mail
    
    def get_lm_loop_mail(self, cr, uid, record_id, context=None):
        mail = []
        if record_id:
            record = self.browse(cr, uid, record_id)
            report_to = record.supervisor_id or False
            dept_head_id = record.department_id and record.department_id.manager_id and record.department_id.manager_id.id or False
            department_id = record.department_id or False
            if report_to:
                mail = self.get_mail_lm_loop(cr, uid, report_to, dept_head_id, department_id, context)
        
        return mail
    
    def get_mail_lm_loop(self, cr, uid, employee, dept_head_id, department_id, context=None):
        """
            Get report_to of report_to of ....  of employee in department
        """
        mail = []
        if employee and dept_head_id:
            mail.append(employee.work_email)
            if employee.id != dept_head_id and employee.department_id == department_id:
                child_mail = self.get_mail_lm_loop(cr, uid, employee.report_to, dept_head_id, department_id, context)
                mail.extend(child_mail)
        
        return mail
    
    def update_termination_dont_have_reason_group(self, cr, uid, *args):
        log.info("Start update termination dont have reason group")
        
        request_ids = self.search(cr, uid, [('resignation_reason_group_id','=',False),
                                            ('main_resignation_reason_id','!=',False)])
        
        reason_group_pool = self.pool.get('vhr.resignation.reason')
        if request_ids:
            for request in self.read(cr, uid, request_ids, ['main_resignation_reason_id']):
                main_resignation_reason_id = request.get('main_resignation_reason_id', False) and request['main_resignation_reason_id'][0]
                if main_resignation_reason_id:
                    reason = reason_group_pool.read(cr, uid, main_resignation_reason_id, ['reason_group_id'])
                    reason_group_id = reason.get('reason_group_id', False) and reason['reason_group_id'][0]
                    if reason_group_id:
                        super(vhr_termination_request, self).write(cr, uid, request['id'], {'resignation_reason_group_id': reason_group_id})
            
        
        log.info("End update termination dont have reason group")
            


vhr_termination_request()
