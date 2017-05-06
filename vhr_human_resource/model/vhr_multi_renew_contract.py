# -*-coding:utf-8-*-
import logging
import json
from openerp.osv import osv, fields
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from openerp.addons.vhr_common.model.vhr_common import vhr_common
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from lxml import etree
import simplejson as json
from openerp import SUPERUSER_ID
from vhr_multi_renew_contract_mail_template_process import mail_process_official, mail_process_collaborator
from vhr_human_resource_abstract import vhr_human_resource_abstract

STATES_ALL = [('draft','Draft'),
#               ('lm_approval','Waiting LM'),
              ('department','Waiting Department'),
#               ('hrbp','Waiting HRBP'),
              ('cb','Waiting C&B'),
              ('finish','Finish'),
              ('cancel','Cancel')]

STATES_OFFICIAl = [('draft','Draft'),
              ('department','Waiting Department'),
#               ('hrbp','Waiting HRBP'),
              ('cb','Waiting C&B'),
              ('finish','Finish'),
              ('cancel','Cancel')]

STATES_COLLABORATOR = [('draft','Draft'),
                       ('department','Waiting Department'),
#                        ('hrbp','Waiting HRBP'),
                       ('cb','Waiting C&B'),
                       ('finish','Finish'),
                       ('cancel','Cancel')]


log = logging.getLogger(__name__)

class vhr_multi_renew_contract(osv.osv, vhr_common, vhr_human_resource_abstract):

    _name = 'vhr.multi.renew.contract'
    _description = 'Multi Renewal Contract'
    
    def _is_person_do_action(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if not ids:
            return True
        if not isinstance(ids, list):
            ids = [ids]
        for record_id in ids:
            res[record_id] = self.is_person_do_action(cr, uid, [record_id], context)
        return res
    
    def _check_waiting_for(self, cr, uid, ids, prop, unknow_none, context = None):
        if not context:
            context= {}
        res = {}
        context["search_all_employee"] = True
        context['active_test'] = False
        
        names_cb, emp_ids_cb, mails_cb = self.get_cb_name_and_id(cr, uid, context)
        for record in self.read(cr, uid, ids, ['state','approver_id']):
            record_id = record.get('id',False)
            approver_id = record.get('approver_id', False) and record['approver_id'][0]
            state = record.get('state','')
            res[record_id] = ''
            if state == 'draft':
                res[record_id] = '; '.join(names_cb)
            elif state == 'department':
                name, dh_id, mail = self.get_approver_name_and_id(cr, uid, record_id, context)
                res[record_id] = name
                
                if record:
                    #get delegator if have
                    delegator_ids = self.get_delegator(cr, uid, record_id, approver_id, context)
                    if delegator_ids:
                        emps = self.pool.get('hr.employee').read(cr, uid, delegator_ids, ['login'])
                        emp_logins = [emp.get('login','') for emp in emps]
                        logins = '; '.join(emp_logins)
                        res[record_id] += '; ' + logins
                
#             elif state == 'dh_approval':
#                 name, dh_id, mail = self.get_dept_head_name_and_id(cr, uid, record_id, context)
#                 res[record_id] = name
            elif state == 'cb':
                res[record_id] = '; '.join(names_cb)
        
        return res
    
    def get_correct_date_request(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if not isinstance(ids, list):
            ids = [ids]
        
        records = self.read(cr, uid, ids, ['date_request'])
        for record in records:
            res[record['id']] = ''
            
            if record.get('date_request'):
                date_request = datetime.strptime(record['date_request'], DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y")
                res[record['id']] = date_request
        return res
    
    def _is_cb(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        
        groups = self.pool.get('res.users').get_groups(cr, uid)
        
        
        value = False
        if 'vhr_cb_contract' in groups:
            value = True
            
        for record_id in ids:
            res[record_id] = value
            
        
        return res
    
    def _check_count_detail(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        
        for record in self.browse(cr, uid, ids, fields_process=['contract_lines']):
            res[record.id] = {}
            contract_lines = record.contract_lines
            res[record.id]['count_detail_lines'] = len(contract_lines)
            remain_days = 999
            for line in contract_lines:
                if line.remain_day_for_renew and line.remain_day_for_renew < remain_days:
                    remain_days = line.remain_day_for_renew
            
            if remain_days == 999:
                remain_days = -1
            res[record.id]['remain_day_for_renew'] = remain_days
        
        return res
    
    def _get_gender(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for record in self.browse(cr, uid, ids, fields_process=['approver_id']):
            res[record['id']] = {'approver_gender': '',
                                 'approver_gender_up': ''}
            data = {}
            approver = record.approver_id
            if approver:
                gender = approver.gender
                if gender == 'male':
                    data['approver_gender'] = 'anh'
                    data['approver_gender_up'] = 'Anh'
                else:
                    data['approver_gender'] = 'chị'
                    data['approver_gender_up'] = 'Chị'
            
            res[record['id']].update(data)
            
        return res
    
    def _get_filter_month(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for record in self.read(cr, uid, ids, ['date_from']):
            res[record['id']] = 0
            date_from = record.get('date_from', False)
            if date_from:
                date_from = datetime.strptime(date_from, DEFAULT_SERVER_DATE_FORMAT)
                res[record['id']] = date_from.month
        
        return res
    
    def _get_deadline_to_receive_renew_status(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for record in self.read(cr, uid, ids, ['date_send_mail_dept']):
            res[record['id']] = ''
            date_send_mail_dept = record.get('date_send_mail_dept', False)
            if date_send_mail_dept:
                date_send_mail_dept = datetime.strptime(date_send_mail_dept, DEFAULT_SERVER_DATE_FORMAT)
                deadline = date_send_mail_dept + relativedelta(days=7)
                deadline = deadline.strftime('%d/%m/%Y')
                res[record['id']] = deadline
            
        return res
    
    def _get_plus_2_day_remind(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for record in self.read(cr, uid, ids, ['date_send_mail_remind']):
            res[record['id']] = ''
            date_send_mail_dept = record.get('date_send_mail_remind', False)
            if date_send_mail_dept:
                date_send_mail_dept = datetime.strptime(date_send_mail_dept, DEFAULT_SERVER_DATE_FORMAT)
                deadline = date_send_mail_dept + relativedelta(days=2)
                deadline = deadline.strftime('%d/%m/%Y')
                res[record['id']] = deadline
            
        return res
    
    def _get_link_to_renew(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        
        for multi_renew_id in ids:
            res[multi_renew_id] = self.pool.get('vhr.multi.renew.contract.detail').get_url(cr, uid, multi_renew_id, context)
        
        return res
    
    _columns = {
        'date_request': fields.date('Date Request'),
        'correct_date_request': fields.function(get_correct_date_request, type='date', string='Correct Date Request'),
        'name': fields.char('Name'),
        'contract_lines': fields.one2many('vhr.multi.renew.contract.detail', 'multi_renew_id', 'Contracts'),
        'report_to': fields.many2one('hr.employee','Report To', ondelete='restrict'),
        'manager_id': fields.many2one('hr.employee','Dept Head', ondelete='restrict'),
        'department_group_id': fields.many2one('hr.department','Department Group', ondelete='restrict'),
        'department_id': fields.many2one('hr.department','Department', ondelete='restrict'),
        'team_id': fields.many2one('hr.department','Team', ondelete='restrict'),
        'approver_id': fields.many2one('hr.employee','Approver', ondelete='restrict'),
        'cc_work_mail': fields.char('Mail CC Setting'),
        'cc_work_mail_default': fields.char('Mail CC Setting Default by Created'),
        'state': fields.selection(STATES_ALL, 'Status', readonly=True),
#         'is_access': fields.boolean('Is Access'),
#         'is_change_two_field_date': fields.boolean("Is Change Two Fields Date"),
        'date_from': fields.date('Date From'),
        'date_to': fields.date('Date To'),
#         'is_remind': fields.boolean('Is Remind'),
        'is_collaborator': fields.boolean('Is Collaborator'),
        'is_probation': fields.boolean('Is Probation'),
        'is_person_do_action': fields.function(_is_person_do_action, type='boolean', string='Is Person Do Action'),
        'waiting_for' : fields.function(_check_waiting_for, type='char', string='Waiting For', readonly = 1),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                          domain=[('object_id.model', '=', _name),
                                                  ('field_id.name', 'not in',
                                                   ['write_date','audit_log_ids'])]),
        'state_log_ids': fields.one2many('vhr.state.change', 'res_id', 'History', domain=[('model', '=', _name)]),
        'create_uid': fields.many2one('res.users', 'Create User'),
        'changed_employee': fields.text('Changed Employee'),#Employee has been change by cb , this field for send mail alert employees has been change info of new contract
        'pending_employee': fields.text('Pending Employee'),
        'is_finish_by_system': fields.boolean('Is Finish By System'),
        'note': fields.text('Note'),
        'is_cb': fields.function(_is_cb, type='boolean', string='Is CB'),
        'count_detail_lines': fields.function(_check_count_detail, type='integer', string="Number of Renew Contract", multi='get_detail_data'),
        'remain_day_for_renew': fields.function(_check_count_detail, type='integer', string="Remain days for renew", multi='get_detail_data'),
        'is_send_mail': fields.boolean('Is Send Mail'),
        'is_offline': fields.boolean('Is Offline'),
        'approver_gender': fields.function(_get_gender, type='char', string="Gender", multi='get_gender'),
        'approver_gender_up': fields.function(_get_gender, type='char', string="Gender", multi='get_gender'),
        'search_month': fields.function(_get_filter_month, type='integer', string='Search Month'),
        'date_send_mail_dept': fields.date('Date Send Mail To Department'),
        'date_send_mail_remind': fields.date('Date Send Mail Remind'),
        'deadline_receive_renew_status': fields.function(_get_deadline_to_receive_renew_status, type='char', string='Deadline to reiceive renew status'),
        'plus_two_date_from_remind': fields.function(_get_plus_2_day_remind, type='char', string="New Deadline in Remind"),
        'full_role_emp_id': fields.many2one('hr.employee', 'Full Role User', ondelete='restrict'),#NGười được nhân mail confỉm, reject từ 
        'link_url': fields.function(_get_link_to_renew, type='char',string="URL Link"),
        
        'is_overtime_remind': fields.boolean('Is Overtime Remind'),
        'contact_point': fields.char('Contact Point'),
    }
    
    _order = "id desc, date_from desc"
    
    def _get_full_role_emp_id(self, cr, uid, context=None):
        param = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_human_resource_full_role_user_multi_renew_contract') or ''
        domain = [('code','=','VG-01609')]
        if param:
            param = param.split('')
            domain = [('code','in', param)]
        
        employee_ids = self.pool.get('hr.employee').search(cr, uid, domain)
        return employee_ids and employee_ids[0] or False
         
    _defaults = {
                 'state': 'draft',
                 'is_send_mail': False,
                 'is_offline': False,
                 'full_role_emp_id': _get_full_role_emp_id,
#         'is_access': False,
#         'is_remind': False,
#         'date_from': _get_default_date_from,
#         'date_to': _get_default_date_to,
#         'is_change_two_field_date': True,
#         'is_collaborator': False,
        
    }
    
    def read(self, cr, user, ids, fields=None, context=None, load='_classic_read'):
        if not context:
            context = {}
        
        if 'active_test' not in context:
            context['active_test'] = False
        
        groups = self.pool.get('res.users').get_groups(cr, user)
        is_have_audit_log_field = False
        if not set(groups).intersection(['hrs_group_system','vhr_cb_contract']) and 'audit_log_ids' in fields:
            fields.remove('audit_log_ids')
            is_have_audit_log_field = True
            
        if context.get('validate_read_vhr_multi_renew_contract',False):
            result_check = self.validate_read(cr, user, ids, context)
            if not result_check:
                raise osv.except_osv('Validation Error !', 'You don’t have permission to access this data !')
            
            del context['validate_read_vhr_multi_renew_contract']
        
        res =  super(vhr_multi_renew_contract, self).read(cr, user, ids, fields, context, load)
        
        return res
    
    def validate_read(self, cr, uid, ids, context=None):
        user_groups = self.pool.get('res.users').get_groups(cr, uid)
        if set(['hrs_group_system', 'vhr_cnb_manager', 'vhr_hr_dept_head','vhr_cb_contract']).intersection(set(user_groups)):
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
        
    def is_person_do_action(self, cr, uid, ids, context=None):
        if ids:
            record = self.browse(cr, uid, ids[0], fields_process=['state'])
            state = record.state
            groups = self.pool.get('res.users').get_groups(cr, uid)
#             approver_user_id = record.approver_id and record.approver_id.user_id and record.approver_id.user_id.id or False
#             report_to_user_id = record.report_to and record.report_to.user_id and record.report_to.user_id.id or False
#             department_id = record.department_id and record.department_id.id or False
            
            if  (state == 'draft' and 'vhr_cb_contract' in groups)\
             or (state == 'department' and (self.is_approver(cr, uid, ids) or 'vhr_cb_contract' in groups ))\
             or (state in ['cb','finish'] and 'vhr_cb_contract' in groups):
                return True
        
            log.info("User with uid %s don't have right to do action in record %s at state %s" % (uid,ids[0],state ))
        else:
            log.info('ids not exist for check is_person_do_action')
        return False
    
    def is_person_do_reject(self, cr, uid, ids, context=None):
        groups = self.pool.get('res.users').get_groups(cr, uid)
        if not 'vhr_cb_contract' in groups:
            return False
        
        return True
    
    def is_person_do_return(self, cr, uid, ids, context=None):
        groups = self.pool.get('res.users').get_groups(cr, uid)
        if not 'vhr_cb_contract' in groups:
            return False
        
        return True
    
    def is_approver(self, cr, uid, ids, context=None):
        if ids:
            record = self.browse(cr, uid, ids[0])
            if record and record.approver_id and record.approver_id.user_id \
                    and uid == record.approver_id.user_id.id:
                return True
            elif record and record.approver_id:
                #Check if person is delegate by dept head
                delegator_ids = self.get_delegator(cr, uid, ids[0], record.approver_id.id, context)
                emp_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=',uid)])
                if set(emp_ids).intersection(set(delegator_ids)):
                    return True
        return False
    
    def open_window(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        
        if ids:
            record = self.read(cr, uid, ids[0], ['state'])
            if record.get('state', False) in ['department'] and context.get('action',False) == 'submit':
                self.check_update_term_of_contract(cr, uid, ids[0], context)
                
        
        view_open = 'view_vhr_multi_renew_contract_submit_form'
        if context.get('view_open',False):
            view_open = context['view_open']
            
        action = {
            'name': 'Notes',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.pool.get('ir.model.data').get_object_reference(cr, uid, 'vhr_human_resource', view_open)[1],
            'res_model': 'vhr.multi.renew.contract',
            'context': context,
            'type': 'ir.actions.act_window',
            #'nodestroy': True,
            'target': 'new',
            #'auto_refresh': 1,
            'res_id': ids[0],
        }
        return action
    
    def fields_view_get(self, cr, uid, view_id = None, view_type = 'form', context = None, toolbar = False, submenu = False):
        res = super(vhr_multi_renew_contract, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar = toolbar, submenu = submenu)
        if context is None:
            context = {}
        if view_type == 'form':
            res = self.add_attrs_for_field(cr, uid, res, context)
        return res
    
    def add_attrs_for_field(self, cr, uid, res, context=None):
        doc = etree.XML(res['arch'])
        if res['type'] == 'form':
            #When view view_vhr_working_record_submit_form
            #To add field text action_comment 
            if context.get('action',False) and context.get('active_id', False):
                node = doc.xpath("//form/separator")
                if node:
                    node = node[0].getparent()
                    if context.get('required_comment', False):
                        node_notes = etree.Element('field', name="action_comment", colspan="4", modifiers=json.dumps({'required' : True}))
                    else:
                        node_notes = etree.Element('field', name="action_comment", colspan="4")
                    node.append(node_notes)
                    res['arch'] = etree.tostring(doc)
                    res['fields'].update({'action_comment': {'selectable': True, 'string': 'Action Comment', 'type': 'text', 'views': {}}})
        res['arch'] = etree.tostring(doc)
        return res
    
    
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        # Search rule for specific menu
        if not context:
            context = {}
        
        
        
        new_args = [('id','in',[])]
        groups = self.pool.get('res.users').get_groups(cr, uid)
        employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', uid)])
        if set(['hrs_group_system','vhr_cb_contract']).intersection(set(groups)):
            new_args = []
        elif employee_ids:
            new_args = ['|',
                            '&',('create_uid', '=', uid), ('state', '!=', False),#Draft
                            '&',('approver_id','in',employee_ids),('state', 'not in', ['draft']),#DH
                        ]
            
            dict = self.get_emp_make_delegate(cr, uid, employee_ids[0])
            if dict:
                for employee_id in dict:
                    new_args.insert(0,'|')
                    new_args.extend(['&','&',('approver_id','=',employee_id),
                                             ('state','!=','draft'),
                                             ('department_id','in',dict[employee_id])])
        
        args += new_args
         
        return super(vhr_multi_renew_contract, self).search(cr, uid, args, offset, limit, order, context, count)
    
    def write(self, cr, uid, ids, vals, context=None):
        if not isinstance(ids, list):
            ids = [ids]
        
        record = self.read(cr, uid, ids[0], ['state'])
        state = record.get('state','')
        if 'state' not in vals and state == 'cb' and vals.get('contract_lines'):
            changed_employee = []
            contract_lines = vals.get('contract_lines',[])
            for detail_data in contract_lines:
                if len(detail_data) == 3 and detail_data[0] == 1 and detail_data[1]:
                    detail_id = detail_data[1]
                    detail = self.pool.get('vhr.multi.renew.contract.detail').browse(cr, uid, detail_id, fields_process=['employee_id'])
                    employee_login = detail.employee_id and detail.employee_id.login or ''
                    changed_employee.append(employee_login)
            if changed_employee:
                changed_employee = ' ,'.join(changed_employee)
                vals['changed_employee'] = changed_employee
                
            
        res = super(vhr_multi_renew_contract, self).write(cr, uid, ids, vals, context)
        
        if res:
            records = self.read(cr, uid, ids, ['state','contract_lines','is_send_mail'])
            for record in records:
                state = record.get('state','')
                contract_lines = record.get('contract_lines',[])
                if 'state' in vals:
                    self.pool.get('vhr.multi.renew.contract.detail').write(cr, uid, contract_lines, {'state': vals['state']})
                    
                #If CB edit information at state cb, send mail
                if 'state' not in vals and state == 'cb' and record.get('is_send_mail', False):
                    self.send_mail(cr, uid, record['id'], 'cb', 'cb', context)
        
        return res
            
    def create_update_back_renew_contract(self, cr, uid, record_id, context=None):
        '''
        Create or update to renew contract at state department, line contract with state=pending
        '''
        if not context:
            context = {}
            
        if record_id:
            record = self.browse(cr, uid, record_id)
            department_id = record.department_id and record.department_id.id or False
            team_id = record.team_id and record.team_id.id or False
            approver_id = record.approver_id and record.approver_id.id or False
            cc_work_mail = record.cc_work_mail
            report_to = record.report_to and record.report_to.id or False
            
            vals = {'department_id': department_id,
                    'team_id': team_id,
                    'approver_id': approver_id,
                    'cc_work_mail': cc_work_mail,
                    'is_collaborator': record.is_collaborator,
                    'date_from': record.date_from,
                    'date_to': record.date_to,
                    'is_send_mail': record.is_send_mail,
                    'is_probation': record.is_probation,
                    'date_request': record.date_request,
                    'date_send_mail_dept': record.date_send_mail_dept,
                    'note': 'Create back from record with id %s' % record_id
                    }
            
#             if record.is_collaborator:
#                 vals['state'] = 'lm_approval'
#             else:
            vals['state'] = 'department'
            
            if context.get('old_state', False):
                vals['state'] = context['old_state']
                
            contract_lines = record.contract_lines
            back_contract_line_ids = []
            for contract_line in contract_lines:
                state = contract_line.renew_status
                if state == 'pending':
                    back_contract_line_ids.append(contract_line.id)
            
            if back_contract_line_ids:
                back_renew_id = self.create(cr, uid, vals, context)
                if back_renew_id:
                    self.pool.get('vhr.multi.renew.contract.detail').write(cr, uid, back_contract_line_ids, {'multi_renew_id': back_renew_id, 'state': vals['state']})
        
        return True
    
    def auto_finish_over_deadline_contract(self, cr, uid, renew_detail_ids, context=None):
        '''
        If renew_detail belong to record multi.renew.contract have len(contract_lines) == 1: 
             change state of that record to finish
             
        If renew_detail belong to record multi.renew.contract have len(contract_lines) > 1:  
            create a new record multi record at state finish to hold the auto finish renew_detail
        '''
        if not context:
            context = {}
        
        list_renew_ids = []
        remove_renew_ids = []
        if renew_detail_ids:
            records = self.pool.get('vhr.multi.renew.contract.detail').browse(cr, uid, renew_detail_ids)
            for record in records:
                renew_detail_id = record.id
                multi_renew_id = record.multi_renew_id and record.multi_renew_id.id or False
                department_id = record.multi_renew_id and record.multi_renew_id.department_id and record.multi_renew_id.department_id.id or False
                manager_id = record.multi_renew_id and record.multi_renew_id.manager_id and record.multi_renew_id.manager_id.id or False
                report_to = record.multi_renew_id and record.multi_renew_id.report_to and record.multi_renew_id.report_to.id or False
                date_from = record.multi_renew_id and record.multi_renew_id.date_from
                date_to = record.multi_renew_id and record.multi_renew_id.date_to
                is_collaborator = record.multi_renew_id and record.multi_renew_id.is_collaborator or False
                contract_lines = record.multi_renew_id and record.multi_renew_id.contract_lines or []
                vals = {'department_id': department_id,
                        'manager_id': manager_id,
                        'report_to': report_to,
                        'is_collaborator': is_collaborator,
                        'date_from': date_from,
                        'date_to': date_to,
                        'is_finish_by_system': True
                        }
                
                vals['state'] = 'finish'
                
                    
                exist_ids = self.search(cr, uid, [('department_id','=',department_id),
                                              ('manager_id','=',manager_id),
                                              ('report_to','=',report_to),
                                              ('is_collaborator','=',is_collaborator),
                                              ('date_from','=',date_from),
                                              ('date_to','=',date_to),
                                              ('state','=','finish'),
                                              ('is_finish_by_system','=',True)])
                
                back_renew_id = False
                if not exist_ids and len(contract_lines) == 1:
                    back_renew_id = multi_renew_id
                    self.write(cr, uid, back_renew_id, {'state': 'finish','is_finish_by_system': True})
                elif exist_ids:
                    back_renew_id = exist_ids and exist_ids[0]
                    if len(contract_lines) == 1:
                        remove_renew_ids.append(multi_renew_id)
                        
                if not back_renew_id:
                    back_renew_id = self.create(cr, uid, vals, context)
                if back_renew_id:
                    renew_status = 'renew'
                    if context.get('renew_status', False):
                        renew_status = context['renew_status']
                    
                    list_renew_ids.append(back_renew_id)
                    self.pool.get('vhr.multi.renew.contract.detail').write(cr, uid, renew_detail_id, {'multi_renew_id': back_renew_id, 
                                                                                                      'state': vals['state'],
                                                                                                      'renew_status': renew_status})
        
        if remove_renew_ids:
            self.unlink(cr, uid, remove_renew_ids)
            
        return list_renew_ids
    
    def execute_workflow(self, cr, uid, ids, context=None):
        
        if isinstance(ids, (int, long)):
            ids = [ids]
        if context is None: 
            context = {}
#         context['call_from_execute'] = True
        for record_id in ids:
            try:
                action_result = False
                action_next_result = False
                record = self.read(cr, uid, record_id, ['state'])
                old_state = record.get('state', False)
                
                if old_state:
                    if context.get('action', False) in ['submit','approve']:
                        action_next_result = self.action_next(cr, uid, [record_id], context) 
                        
                    elif context.get('action', False) == 'return':
                        action_result = self.action_return(cr, uid, [record_id], context)
                        
                    elif context.get('action', False) == 'reject':
                        action_result = self.action_reject(cr, uid, [record_id], context)
                    
                    elif context.get('action', False) == 'renew_contract':
                        action_result = self.renew_multi_contracts(cr, uid, [record_id], context)
                    
                    if action_next_result or action_result:
                        record = self.read(cr, uid, record_id, ['state','is_send_mail'])
                        new_state = record.get('state', False)
                        is_send_mail = record.get('is_send_mail', False)
                        if old_state != new_state and is_send_mail:
                            self.send_mail(cr, uid, record_id, old_state, new_state, context)
                    
                    else:
                        raise osv.except_osv('Validation Error !', "You don't have permission to do this action")
                        
                    if context.get('action') and action_result:
                        STATES = self.get_state_dicts(cr, uid, record_id, context)
                        list_states = {item[0]: item[1] for item in STATES_ALL}
                        
                        record = self.read(cr, uid, record_id, ['state'])
                        new_state = record.get('state', False)
                        
                        self.write_log_state_change(cr, uid, record_id, list_states[old_state], list_states[new_state], context)
                        
            except Exception as e:
                log.exception(e)
                try:
                    error_message = e.message
                    if not error_message:
                        error_message = e.value
                except:
                    error_message = ""
                raise osv.except_osv('Validation Error !', 'Have error during execute record:\n %s!' % error_message)
                
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
    
    def get_state_dicts(self, cr, uid, record_id, context=None):
        if record_id:
            record = self.read(cr, uid, record_id, ['is_collaborator'])
            is_collaborator = record.get('is_collaborator',False)
            if is_collaborator:
                return STATES_COLLABORATOR
            else:
                return STATES_OFFICIAl
        return []
    
    def check_if_exist_renew_contract(self, cr, uid, record_id, context=None):
        if record_id:
            contract_obj = self.pool.get('hr.contract')
            multi = self.browse(cr, uid, record_id)
            
            support = "Ext 1180"
            suport_data = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_human_resource_suport_for_multi_renew_contract') or ''
            if suport_data:
                support = support_data
            for contract in multi.contract_lines:
                if contract.renew_status == 'renew':
                    emp_id = contract.employee_id and contract.employee_id.id or False
                    company_id =  contract.company_id and contract.company_id.id or False
                    date_start = contract.date_start or False
                    contract_ids = contract_obj.search(cr, uid, [('employee_id','=', emp_id),
                                                                 ('company_id','=', company_id),
                                                                 ('date_start','>',date_start),
                                                                 ('id','!=',contract.contract_id.id),
                                                                 ('state','!=','cancel')])
                    if contract_ids:
                        emp_login = contract.employee_id.code or ''
                        emp_name = contract.employee_id.name_related or ''
                        emp_login = emp_login + ' - ' + emp_name
                        raise osv.except_osv('Error !', 
                                             "\nHợp đồng mới của {} đã được gia hạn, không thể approve được nữa. \
                                             Anh/Chị vui lòng liên hệ C&B team ({}) để được hỗ trợ nhé ".format(emp_login, support))
        
        return True
                                
    def action_next(self, cr, uid, ids, context=None):
        log.info('Change status to next state')
        if not context:
            context = {}
        if ids:
            record_id = ids[0]
            mcontext = context
            
            
            if self.is_person_do_action(cr, uid, [record_id], mcontext):
                self.check_if_exist_renew_contract(cr, uid, record_id, context)
                
                vals = {}
                record = self.read(cr, uid, record_id, ['state','is_offline'])
                state = record.get('state', False)
                is_offline = record.get('is_offline', False)
                
                if state in ['finish','cancel']:
                    return False
                
                STATES = self.get_state_dicts(cr, uid, record_id, mcontext)
                list_state = [item[0] for item in STATES]
                
                index_new_state = list_state.index(state) + 1
                
                vals['state'] = list_state[index_new_state]
                
                if is_offline:
                    vals['state'] = 'finish'
                
                if context.get('send_mail', False):
                    contact_point = self.get_contact_point_by_action_user(cr, uid, context)
                    vals['contact_point'] = contact_point
                    vals['is_send_mail'] = True
                    if state == 'draft':
                        vals['date_send_mail_dept'] = datetime.today().date()
                    
                res = self.write(cr, uid, [record_id], vals, mcontext)
                
                if res:
                    list_dict_states = {item[0]: item[1] for item in STATES_ALL}
                    self.write_log_state_change(cr, uid, record_id, list_dict_states[state], list_dict_states[vals['state']], mcontext)
            
                if vals['state'] != 'department':
                    context['old_state'] = state
                    self.create_update_back_renew_contract(cr, uid, record_id, context)
                    
                if vals['state'] == 'cb' or (vals['state'] == 'finish' and is_offline):
                    self.check_update_term_of_contract(cr, uid, record_id, context)
                
                if vals['state'] == 'finish':
                    self.renew_multi_contracts(cr, uid, [record_id], context)
                
                return True
        
        return False
    
    def action_reject(self, cr, uid, ids, context=None):
        log.info('Change status to cancel state')
        if ids:
            record_id = ids[0]
            if self.is_person_do_action(cr, uid, [record_id], context) and \
               self.is_person_do_reject(cr, uid, [record_id], context):
                record = self.read(cr, uid, record_id, ['state'])
                state = record.get('state', False)
                
                self.write(cr, uid, [record_id], {'state': 'cancel'}, context)
                
                return True
        
        return False
    
    def action_return(self, cr, uid, ids, context=None):
        log.info('Change status to previous state')
        if not context:
            context = {}
        if ids:
            record_id = ids[0]
            if self.is_person_do_action(cr, uid, [record_id], context) and \
               self.is_person_do_return(cr, uid, [record_id], context):
                vals = {}
                record = self.read(cr, uid, record_id, ['state','passed_state'])
                state = record.get('state', False)
                
                new_state = ''
                STATES = self.get_state_dicts(cr, uid, record_id, context)
                list_state = [item[0] for item in STATES]
                    
                index_new_state = list_state.index(state) - 1
                new_state = list_state[index_new_state]
                
                if new_state == 'draft':
                    return False
                
                vals['state'] = new_state
                self.write(cr, uid, [record_id], vals, context)
                return True
               
        
        return False
    
    def check_update_term_of_contract(self, cr, uid, record_id, context=None):
        if record_id:
            record = self.browse(cr, uid, record_id, fields_process=['contract_lines'])
            contract_lines = record.contract_lines
            number_of_line_pending = 0
            for contract in contract_lines:
                if contract.renew_status == 'renew' and not contract.new_type_id and not contract.appendix_type_id:
                    raise osv.except_osv('Validation Error !', "All contract with Renew Status = 'Renew' must input 'New Term' before go to next state")
                if contract.renew_status == 'pending':
                    number_of_line_pending += 1
            
            if number_of_line_pending == len(contract_lines):
                raise osv.except_osv('Validation Error !', "You must have at least one contract lines with Renew Status is Renew/ Reject before approve")

        return True
    
    def action_send_email(self, cr, uid, ids, context=None):
        """
        C&B Send email at state dh_approval, lm_approval to lm, dh to approve
        """
        if not context:
            context = {}
        if ids and context.get('state', False):
            today = datetime.today().date()
            old_state = 'draft'
            new_state = context.get('state', False)
            contact_point = self.get_contact_point_by_action_user(cr, uid, context)
            self.write(cr, uid, ids, {'date_send_mail_dept': today,
                                      'contact_point': contact_point})
            for record_id in ids:
                self.send_mail(cr, uid, record_id, old_state, new_state, context)
            
            self.write(cr, uid, ids, {'is_send_mail': True})
        
        return True

    def get_contact_point_by_action_user(self, cr, uid, context=None):
        try:
            contact_point_dict = self.pool.get('ir.config_parameter').get_param(cr, uid ,'vhr_human_resource_contact_point_vhr_multi_renew_contract') or ''
            contact_point_dict = json.loads(contact_point_dict)
            
            user = self.pool.get('res.users').read(cr, SUPERUSER_ID, uid, ['login'])
            if contact_point_dict.get(user.get('login',''),''):
                return contact_point_dict[user['login']]
            
        except Exception as e:
            log.error(e)
        
        contact_point_dict = 'TienNHH ext: 1180; tel:0909044622'
        return contact_point_dict
    
    def name_get(self, cr, uid, ids, context=None):
        if not ids or False in ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        
        ids = filter(None, ids)
        reads = self.browse(cr, uid, ids, fields_process=['department_id','manager_id','report_to'], context=context)
        res = []
        for record in reads:
            department_name = record.department_id and record.department_id.name or ''
            manager_name = record.manager_id and record.manager_id.login or ''
            report_to = record.report_to and record.report_to.login or ''
            name = department_name + ' - ' + manager_name + report_to
            res.append((record['id'], name))
        return res
    
    def send_mail(self, cr, uid, record_id, state, new_state, context=None):
        if not context:
            context = {}
        detail_obj = self.pool.get('vhr.multi.renew.contract.detail')
        context["search_all_employee"] = True
        if record_id and state and new_state:
            action_user = ''
            if context.get('action_user', False):
                action_user = context['action_user']
            else:
                user = self.pool.get('res.users').read(cr, uid, uid, ['login'])
                if user:
                    action_user = user.get('login','')
            
            #Get mail template data by workflow of record
            mail_process = mail_process_official
#             STATES = self.get_state_dicts(cr, uid, record_id, context)
#             if STATES == STATES_COLLABORATOR:
#                 mail_process = mail_process_collaborator
            
            record = self.read(cr, uid, record_id, ['is_collaborator','approver_id','cc_work_email'])
            approver_id = record.get('approver_id', False) and record['approver_id'][0] or False
            cc_work_email = record.get('cc_work_email', '')
            approver_mail = ''
            if approver_id:
                approver = self.pool.get('hr.employee').read(cr, uid, approver_id, ['work_email'])
                approver_mail = approver.get('work_email', '')
            is_collaborator = record.get('is_collaborator',False)
            if is_collaborator:
                mail_process = mail_process_collaborator
                
            name = 'Official Contract'
            if mail_process == mail_process_collaborator:
                name = 'Collaborator Contract'
            log.info("Send mail in Renew Contract %s from old state %s to new state %s"% (name, state, new_state))
            if state in mail_process.keys():
                data = mail_process[state]
                is_have_process = False
                for mail_data in data:
                    if new_state == mail_data[0]:
                        is_have_process = True
                        mail_detail = mail_data[1]
                        is_exist_approve_line = mail_detail.get('is_exist_approve_line', False)
                        is_exist_reject_line = mail_detail.get('is_exist_reject_line', False)
                        if is_exist_approve_line:
                            approve_lines = detail_obj.search(cr, uid, [('multi_renew_id','=',record_id),
                                                                        ('renew_status','=','renew')])
                            if not approve_lines:
                                continue
                        vals = {'action_user':action_user, 'renew_id': record_id}
                        
                        if context.get('subject_element_name', False):
                            vals['subject_element_name'] = context['subject_element_name']
                        
                        if context.get('domain_account_of_employee', False):
                            vals['domain_account_of_employee'] = context['domain_account_of_employee']
                        
                        if context.get('date', False):
                            vals['date'] = context['date']
                            
                        list_group_mail_to = mail_detail['to']
                                
                        list_mail_to, list_mail_cc_from_group_mail_to = self.get_email_to_send(cr, uid, record_id, list_group_mail_to, context)
#                         list_mail_to.append(approver_mail)
                        mail_to = ';'.join(list_mail_to)
                        vals['email_to'] = mail_to
                        
                        if 'cc' in mail_detail:
                            list_group_mail_cc = mail_detail['cc']
                            
                            list_mail_cc, list_mail_cc_from_group_mail_cc = self.get_email_to_send(cr, uid, record_id, list_group_mail_cc, context)
                            list_mail_cc += list_mail_cc_from_group_mail_cc + list_mail_cc_from_group_mail_to
                            list_mail_cc = list(set(list_mail_cc))
                            
                            mail_cc = ';'.join(list_mail_cc)
                            if cc_work_email:
                                mail_cc += ';' + cc_work_email
                                
                            vals['email_cc'] = mail_cc
                        
                        link_email = self.get_url(cr, uid, record_id, context)
                        vals['link_email'] = link_email
                        context = {'action_from_email': mail_detail.get('action_from_email',''),'not_split_email': True }
                        
                        if not is_exist_reject_line:
                            self.pool.get('vhr.sm.email').send_email(cr, uid, mail_detail['mail_template'], vals, context)
                        else:
                            reject_line_ids = detail_obj.search(cr, uid, [('multi_renew_id','=',record_id),
                                                                        ('renew_status','=','reject')])
                            if reject_line_ids:
                                for line in detail_obj.browse(cr, uid, reject_line_ids):
                                    employee_login = line.employee_id and line.employee_id.login or ''
                                    employee_name = line.employee_id and line.employee_id.name_related or ''
                                    employee_code = line.employee_id and line.employee_id.code or ''
                                    date_end = line.date_end or False
                                    date_end = datetime.strptime(date_end, DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%m-%Y')
                                    vals.update({'subject_element_name': employee_name,
                                                 'domain_account_of_employee': employee_code,
                                                 'date': date_end
                                                 })
                                    self.pool.get('vhr.sm.email').send_email(cr, uid, mail_detail['mail_template'], vals, context)
                
                if not is_have_process:
                    log.info("Renew Contract %s don't have mail process from old state %s to new state %s "%(name,state, new_state))
            
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
                if item == 'depthead':
                    name, dh_id, mail = self.get_dept_head_name_and_id(cr, uid, record_id, context)
                    if mail:
                        res.append(mail)
                elif item == 'lm':
                    name, id, mail = self.get_lm_name_and_id(cr, uid, record_id, context)
                    if mail:
                        res.append(mail)
                elif item == 'hrbp':
                    name, id, mail = self.get_hrbp_name_and_id(cr, uid, record_id, context)
                    if mail:
                        res.extend(mail)
                elif item == 'ass_hrbp':
                    name, id, mail = self.get_assist_hrbp_name_and_id(cr, uid, record_id, context)
                    if mail:
                        res.extend(mail)
                elif item == 'cb':
                    name ,id, mail = self.get_cb_name_and_id(cr, uid, context)
                    if mail:
                        res.extend(mail)
                elif item == 'approver':
                    
                    mail = record.approver_id and record.approver_id.work_email or ''
                    if mail:
                        res.append(mail)
                    
                    #Send to delegator
                    delegator_ids = self.get_delegator(cr, uid, record_id, record.approver_id.id, context)
                    if delegator_ids:
                        delegators = self.pool.get('hr.employee').read(cr, uid, delegator_ids, ['work_email'])
                        delegate_mails = [delegator.get('work_email','') for delegator in delegators]
                        res.extend(delegate_mails)
                elif item == 'cc_work_email':
                    res.extend([record.cc_work_mail or ''])
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
    
    def get_hrbp_name_and_id(self, cr, uid, record_id, context=None):
        if not context:
            context = {}
        
        hrbp_names = []
        hrbp_ids = []
        hrbp_mails = []
        if record_id:
            record = self.read(cr, uid, record_id, ['department_id'])
            department_id = record.get('department_id',False) and record['department_id'][0] or False
            if department_id:
                department = self.pool.get('hr.department').browse(cr, uid, department_id, fields_process=['hrbps'])
                employees = department.hrbps
                for employee in employees:
                    hrbp_ids.append(employee.id)
                    hrbp_names.append(employee.login)
                    hrbp_mails.append(employee.work_email)
                    
        return hrbp_names, hrbp_ids, hrbp_mails
    
    def get_assist_hrbp_name_and_id(self, cr, uid, record_id, context=None):
        if not context:
            context = {}
        
        hrbp_names = []
        hrbp_ids = []
        hrbp_mails = []
        if record_id:
            record = self.read(cr, uid, record_id, ['department_id'])
            department_id = record.get('department_id',False) and record['department_id'][0] or False
            if department_id:
                department = self.pool.get('hr.department').browse(cr, uid, department_id, fields_process=['ass_hrbps'])
                employees = department.ass_hrbps
                for employee in employees:
                    hrbp_ids.append(employee.id)
                    hrbp_names.append(employee.login)
                    hrbp_mails.append(employee.work_email)
                    
        return hrbp_names, hrbp_ids, hrbp_mails
    
    def get_cb_name_and_id(self, cr, uid, context=None):
        names = []
        emp_ids = []
        mails = []
        employee_ids = self.pool.get('vhr.working.record').get_employee_ids_belong_to_group(cr, uid, 'vhr_cb_contract', context)
        if employee_ids:
            employees = self.pool.get('hr.employee').read(cr, uid, employee_ids, ['login','work_email'])
            for employee in employees:
                emp_ids.append(employee.get('id',False))
                names.append(employee.get('login',''))
                mails.append(employee.get('work_email',''))
        
        return names, emp_ids, mails
    
    def get_dept_head_name_and_id(self, cr, uid, record_id, context=None):
        name = ''
        dh_id = False
        mail = ''
        if record_id:
            record = self.browse(cr, uid, record_id, fields_process=['manager_id'])
            manager = record.manager_id or False
            if manager:
                name = record.manager_id.login or ''
                dh_id = record.manager_id.id or False
                mail = record.manager_id.work_email
        
        return name, dh_id, mail
    
    def get_approver_name_and_id(self, cr, uid, record_id, context=None):
        name = ''
        approver_id = False
        mail = ''
        if record_id:
            record = self.browse(cr, uid, record_id, fields_process=['approver_id'])
            approver = record.approver_id or False
            if approver:
                name = record.approver_id.login or ''
                dh_id = record.approver_id.id or False
                mail = record.approver_id.work_email
        
        return name, approver_id, mail
    
    def get_lm_name_and_id(self, cr, uid, record_id, context=None):
        name = ''
        dh_id = False
        mail = ''
        if record_id:
            record = self.browse(cr, uid, record_id, fields_process=['report_to'])
            report_to = record.report_to or False
            if report_to:
                name = record.report_to.login or ''
                dh_id = record.report_to.id or False
                mail = record.report_to.work_email
        
        return name, dh_id, mail
                
    #TODO: check lai
    def get_url(self, cr, uid, res_id, context=None):
        if isinstance(res_id, list):
            res_id = res_id[0]
        model_data = self.pool.get('ir.model.data')
        action_id = model_data.xmlid_lookup(cr, uid, 'vhr_human_resource.action_multi_renew_official_contract')[2]
        
        url = ''
        config_parameter = self.pool.get('ir.config_parameter')
        base_url = config_parameter.get_param(cr, uid, 'web.base.url') or ''
        if base_url:
            url = base_url
        url += '/web#id=%s&view_type=form&model=vhr.multi.renew.contract&action=%s' % (res_id, action_id)
        return url
    
    
    def renew_multi_contracts(self, cr, uid, ids, context=None):
        contract_obj = self.pool.get('hr.contract')
        res_company = self.pool.get('res.company')
        if ids:
            records = self.browse(cr, uid, ids, context=context)
            for res_item in records:
                note = ''
                contracts = res_item and res_item.contract_lines or None
                if contracts:
  
                    for line in contracts:
                        if line.renew_status == 'renew' and not line.new_contract_id and line.new_type_id:
                            ctx = {
                                'contract_id': line.contract_id.id,
                                'type_id': line.new_type_id.id,
                                'include_probation': line.include_probation,
                                'date_start': line.new_date_start,
                                'duplicate_active_id': line.contract_id.id,
                                'default_type_id': line.new_type_id.id,
                                'default_include_probation': line.include_probation,
                                'default_date_start': line.new_date_start,
                                'default_new_date_start_temp': line.new_date_start_temp,
                                'default_date_end': line.new_date_end,
                                'renew_status': 'renew',
                                'create_directly_from_contract': True,#to set state=signed in contract
                            }
                            fld = contract_obj._columns.keys()
                            values = contract_obj.default_get(cr, uid, fld, context=ctx)
                            values['date_start_temp'] = line.new_date_start_temp
                            values['state'] = 'waiting'
                            
                            val = contract_obj.get_employee_data_from_wkr(cr, uid, values.get('employee_id', False), 
                                                                                   values.get('company_id', False), 
                                                                                   None, context=context)
                            values.update(val)
                            
                            company_id = values.get('company_id', False)
                            if company_id:
                                res_read = res_company.read(cr, uid, company_id, ['sign_emp_id','job_title_id','country_signer'])
                                if res_read['sign_emp_id']:
                                    values.update({'info_signer': res_read['sign_emp_id'],
                                                  'title_signer': res_read.get('job_title_id',''),
                                                  'country_signer': res_read.get('country_signer',False) and res_read['country_signer'][0] or False,
                                                  })
                            
                            try:
                                self.check_if_exist_active_termination(cr, uid, values.get('employee_id', False),
                                                                                values.get('company_id', False),
                                                                                values.get('date_start', False))
                                
                                new_contract_id = contract_obj.create_with_log(cr, uid, values, context=ctx)
                                self.pool.get('vhr.multi.renew.contract.detail').write(cr, uid, line.id, {'new_contract_id': new_contract_id})
                            except Exception as e:
                                log.exception(e)
                                error_message = ''
                                try:
                                    error_message = e.message
                                    if not error_message:
                                        error_message = e.value
                                except:
                                    error_message = ""
                                note += "\n %s (%s): %s" % (line.employee_id and line.employee_id.login, line.employee_id and line.employee_id.code, error_message)
                        
                        elif line.renew_status == 'renew' and not line.new_contract_id and line.appendix_type_id:
                            self.create_appendix_contract(cr, uid, line, context)
                if note:
                    note = "Can't create new contract for employee(s): \n" + note
                self.write(cr, uid, res_item.id, {'note':note})
                                
  
        return True
    
    def check_if_exist_active_termination(self, cr, uid, employee_id, company_id, date_start, context=None):
        if employee_id and company_id and date_start:
            wr_pool = self.pool.get('vhr.working.record')
            
            change_form_ids = wr_pool.get_dismiss_change_form_ids(cr, uid)
            domain = [('employee_id','=',employee_id),
                      ('company_id','=',company_id),
                      ('change_form_ids','in', change_form_ids),
                      ('state','in',['finish',False])]
            
            s_domain = domain[:]
            s_domain.append(('active','=',True))
            active_terminate_wr_ids = wr_pool.search(cr, uid, s_domain)
            if active_terminate_wr_ids:
                raise  osv.except_osv('Validation Error!', 
                                      "Can not renew contract when existing active termination at same company !")
            
            s_domain = domain[:]
            s_domain.append(('effect_from','>=',date_start))
            future_terminate_wr_ids = wr_pool.search(cr, uid, s_domain)
            if future_terminate_wr_ids:
                raise  osv.except_osv('Validation Error!',
                                      "Can not renew contract when existing future termination at same company !")
            
            latest_wr_ids = wr_pool.search(cr, uid, [('employee_id','=',employee_id),
                                                     ('company_id','=',company_id),
                                                     ('state','in',['finish',False])], order='effect_from desc', limit=1)
            if latest_wr_ids:
                terminate_wr_ids = wr_pool.search(cr, uid, [('id','in', latest_wr_ids),
                                                            ('change_form_ids','in',change_form_ids)])
                if terminate_wr_ids:
                    raise  osv.except_osv('Validation Error!',
                                          "Can not renew contract when latest working record is terminated !")
        
        return True
            
            
    
    def create_appendix_contract(self, cr, uid, line, context=None):
        if line:
            app_obj = self.pool.get('vhr.appendix.contract')
            contract_id = line.contract_id and line.contract_id.id or False
            employee_id = line.employee_id and line.employee_id.id or False
            new_date_start = line.new_date_start
            new_date_end = line.new_date_end
            
            append_type_ids = self.pool.get('vhr.appendix.contract.type').search(cr, uid, [('code','=','ACT-006')])
            appendix_type_id = append_type_ids and append_type_ids[0] or False
            data_onchange_contract = app_obj.onchange_contract_id(cr, uid, [], contract_id, appendix_type_id)
            data_onchange_app_type = app_obj.onchange_appendix_type_id(cr, uid, [], appendix_type_id, contract_id)
            data_onchange_date_start = app_obj.on_change_date_start(cr, uid, [], new_date_start, context={'contract_id': contract_id})
            
            vals = {'contract_id': contract_id,
                    'date_start': new_date_start,
                    'date_end': new_date_end,
                    'is_create_code': True,
                    'appendix_type_id': append_type_ids and append_type_ids[0] or False,
                    'description': 'Created from multi renew contract'
                    }
            
            vals.update(data_onchange_contract.get('value',{}))
            vals.update(data_onchange_app_type.get('value',{}))
            vals.update(data_onchange_date_start.get('value',{}))
            
            app_id = app_obj.create(cr, uid, vals, context)
            if app_id:
                self.pool.get('vhr.multi.renew.contract.detail').write(cr, uid , line.id, {'new_appendix_contract_id': app_id})
        
        return True
                
    def create_data_for_process_official(self, cr, uid, context=None):
        if not context:
            context = {}
        today = datetime.today().date()
        current_day = today.day
#         if current_day >=1 and current_day < 15:
            #search from 1-15 of next month
        check_date = date(today.year, today.month, current_day)
        search_from = check_date.strftime('%Y-%m-%d')
        search_to = (check_date + relativedelta(days=45)).strftime('%Y-%m-%d')
#         else:
#             #search from 15 to last date of next month
#             check_date = date(today.year, today.month, 15)
#             search_from = (check_date + relativedelta(months=1)).strftime('%Y-%m-%d')
#             search_to = (date(today.year, today.month, 1) + relativedelta(months=2) - relativedelta(days=1)).strftime('%Y-%m-%d')
        
        if context.get('search_from', False) and context.get('search_to', False):
            search_from = context['search_from']
            search_to = context['search_to']
        
        self.create_data_base_on_search_date(cr, uid, search_from, search_to, False, False, context)
        return True
    
    def create_data_for_process_collaborator(self, cr, uid, context=None):
        if not context:
            context = {}
            
        today = datetime.today().date()
        search_from = today.strftime('%Y-%m-%d')
        search_to = (today + relativedelta(days=11)).strftime('%Y-%m-%d')
        
        if context.get('search_from', False) and context.get('search_to', False):
            search_from = context['search_from']
            search_to = context['search_to']
            
        self.create_data_base_on_search_date(cr, uid, search_from, search_to, True, False, context)
        return True
    
#     def create_data_for_process_probation(self, cr, uid, context=None):
#         if not context:
#             context = {}
#             
#         today = datetime.today().date()
#         search_from = (today + relativedelta(days=10)).strftime('%Y-%m-%d')
#         search_to = (today + relativedelta(days=30)).strftime('%Y-%m-%d')
#         
#         if context.get('search_from', False) and context.get('search_to', False):
#             search_from = context['search_from']
#             search_to = context['search_to']
#             
#         self.create_data_base_on_search_date(cr, uid, search_from, search_to, False, True, context)
#         return True
    
    def create_data_base_on_search_date(self, cr, uid, search_from, search_to, is_collaborator, is_probation, context=None):
        #Return list of renew_contract [(0,0,{data}), (0,0,{data}), ....]
        date_request = datetime.today().date().strftime(DEFAULT_SERVER_DATE_FORMAT)
        
        list_contracts = []
        collaborator_contact_type_group_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_human_resource_type_group_code_colla_for_renew_contract')
        if collaborator_contact_type_group_code:
            collaborator_contact_type_group_code = collaborator_contact_type_group_code.split(',')
        else:
            collaborator_contact_type_group_code = []
            
        probation_contract_type_group_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_human_resource_probation_contract_type_group_code')
        if probation_contract_type_group_code:
            probation_contract_type_group_code = probation_contract_type_group_code.split(',')
        else:
            probation_contract_type_group_code = []
        
        #Lấy danh sách hợp đồng hết hạn trong khoảng search_from - search_to là NVCT(is_collaboration=False)/ CTV (is_collaborator=True)
        if search_from and search_to:
            emp_obj = self.pool.get('hr.employee')
            contract_obj = self.pool.get('hr.contract')
            renew_detail_obj = self.pool.get('vhr.multi.renew.contract.detail')
            renew_setting_obj = self.pool.get('vhr.multi.renew.contract.setting')
            working_pool = self.pool.get('vhr.working.record')
            
            list_detail_fields = renew_detail_obj._columns.keys()
            
            domain = [
                '&', '&', 
                ('state', '=', 'signed'),
                ('employee_id.active', '=', True),
                    '|',
                        '&', '&',
                        ('liquidation_date', '=', False),
                        ('date_end', '>=', search_from),
                        ('date_end', '<=', search_to),
                        '&', '&',
                        ('liquidation_date', '!=', False),
                        ('liquidation_date', '>=', search_from),
                        ('liquidation_date', '<=', search_to),
                    ]
            
            if is_collaborator:
                #Filter hop dong CTV
                domain.insert(1,'&')
                domain.append(('type_id.contract_type_group_id.code','in',collaborator_contact_type_group_code))
            elif is_probation:
                #Dont renew for probation contract
                domain.insert(1,'&')
                domain.append(('type_id.contract_type_group_id.code','in',probation_contract_type_group_code))
            
            else:
                #Filter hop dong HDLD
                domain.insert(1,'&')
                domain.append(('type_id.contract_type_group_id.code','in',[3,4,5]))
                
            contract_ids = contract_obj.search(cr, uid, domain, context=context)
#             contract_ids, is_access = self.get_list_access_ids(cr, uid, contract_ids, context=context)
            
            remain_not_renew_contract_ids = set(contract_ids)
            if contract_ids:
                contracts = contract_obj.read(cr, uid, contract_ids, ['employee_id','company_id'])
                department_team_ids = {}# Department: [team1, team2]
                renew_team_ids = []#All team of employee need to renew
                child_division_ids = {} #division: [ child1]
                child_dept_group_ids = {} #dept-group: [child1]
                unique_couple = []# (team_id, department_id, department_group_id, division_id)
#                 field = 'manager_id_new'
                renew_contracts = {}  # (team_id, department_id) : [list renew contract]
                
#                 if is_collaborator or is_probation:
#                     field = 'report_to_new'
                
                #Read terminate change form code
                change_form_terminated_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_master_data_dismiss_change_form_code') or ''
                change_form_terminated_code = change_form_terminated_code.split(',')
                dismiss_change_form_code = change_form_terminated_code
                
                dismiss_local_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_master_data_dismiss_local_company') or ''
                dismiss_local_code = dismiss_local_code.split(',')
                
                change_form_terminated_code += dismiss_local_code
                change_form_ids = self.pool.get('vhr.change.form').search(cr, uid, [('code', 'in', change_form_terminated_code)],context=context)
                
                dismiss_change_form_ids = self.pool.get('vhr.change.form').search(cr, uid, [('code', 'in', dismiss_change_form_code)],context=context)
                
                employee_renew_ids = []
                #Get dict with field and list contract_ids to renew
                for contract in contracts:
                    employee_id = contract.get('employee_id',False) and contract['employee_id'][0] or False
                    company_id = contract.get('company_id',False) and contract['company_id'][0] or False
                    
                    #Only renew with latest contract at company
                    latest_ids = contract_obj.search(cr, uid, [('employee_id','=',employee_id),
                                                               ('company_id','=',company_id),
                                                               ('state','!=','cancel')], limit=1, order='date_start_real desc')
                    
                    
                    if employee_id and contract['id'] in latest_ids:
                        #Dont renew contract when have active terminate working record map with company in contract
                        terminate_wr_ids = working_pool.search(cr, uid, [ ('employee_id','=',employee_id),
                                                                          ('company_id','=',company_id),
                                                                          ('change_form_ids','in', change_form_ids),
                                                                          ('state','in',['finish',False]),
                                                                          ('active','in',[True,False])])
                        
                        active_wr_ids = working_pool.search(cr, uid, [('employee_id','=',employee_id),
                                                                      ('company_id','=',company_id),
                                                                      ('state','in',['finish',False]),
                                                                      ('active','=',True)])
                        
                        if not set(terminate_wr_ids).intersection(active_wr_ids): 
                            
                            if active_wr_ids:
                                employee_renew_ids.append(employee_id)
                                active_wr = working_pool.read(cr, uid, active_wr_ids[0], 
                                                              ['division_id_new','department_group_id_new','department_id_new','team_id_new','effect_from'])
                                
                                effect_from = active_wr.get('effect_from', False)
                                
                                #Khong renew contract voi cac nhan vien co termination o tuong lai voi cong ty dang duoc renew
                                terminate_wr_ids = working_pool.search(cr, uid, [ ('employee_id','=',employee_id),
                                                                                  ('company_id','=',company_id),
                                                                                ('change_form_ids','in', dismiss_change_form_ids),
                                                                                  ('effect_from','>',effect_from),
                                                                                  ('state','in',['finish',False]),])
                                
                                if terminate_wr_ids:
                                    continue
                                
                                division_id = active_wr.get('division_id_new',False) and active_wr['division_id_new'][0] or False
                                department_group_id = active_wr.get('department_group_id_new',False) and active_wr['department_group_id_new'][0] or False
                                department_id = active_wr.get('department_id_new',False) and active_wr['department_id_new'][0] or False
                                team_id = active_wr.get('team_id_new',False) and active_wr['team_id_new'][0] or False
                                
                                item = (team_id, department_id, department_group_id, division_id)
                                    
                                if department_id not in department_team_ids:
                                    department_team_ids[department_id] = []
                                
                                if team_id not in renew_team_ids:
                                    renew_team_ids.append(team_id)
                                
                                if division_id not in child_division_ids:
                                    child_division_ids[division_id] = []
                                
                                if department_group_id not in child_division_ids[division_id]:
                                    child_division_ids[division_id].append(department_group_id)
                                
                                if department_group_id not in child_dept_group_ids:
                                    child_dept_group_ids[department_group_id] = []
                                
                                if department_id not in child_dept_group_ids[department_group_id]:
                                    child_dept_group_ids[department_group_id].append(department_id)
                                
                                if team_id not in department_team_ids[department_id]:
                                    department_team_ids[department_id].append(team_id)
                                
                                if item not in unique_couple:
                                    unique_couple.append( item )
                                    renew_contracts[item ] = [contract['id']]
                                else:
                                    renew_contracts[item].append(contract['id'])
                
                record_ids = []
                if employee_renew_ids:
                    #Những employee nào mà có request to và cc tới cùng nhóm người thì gom lại thành 1 request
                    dict_request = {} #  (to, group_cc) : [renew_contract]
                    
                    mcontext = {
                                'renew_contracts': renew_contracts,
                                'department_team_ids': department_team_ids,
                                'child_division_ids': child_division_ids,
                                'child_dept_group_ids': child_dept_group_ids,
                                'is_collaborator': is_collaborator,
                                'is_probation' : is_probation
                                }
                    
                    renew_department_ids = department_team_ids.keys()
                    renew_department_group_ids = child_dept_group_ids.keys()
                    renew_division_ids = child_division_ids.keys()
                    
                    dict_request, renew_contracts = self.get_renew_contract_from_subtype_setting(cr, uid, renew_division_ids, 
                                                                                                 renew_department_group_ids,
                                                                 renew_department_ids, renew_team_ids, dict_request, mcontext)
                    mcontext['renew_contracts'] = renew_contracts
                    
                    #Kiểm tra có cấu hình team setting nào, mà team đó có renew contract
                    dict_request, renew_contracts = self.compute_data_from_setting(cr, uid, False, False, False, renew_team_ids, dict_request, mcontext)
                    mcontext['renew_contracts'] = renew_contracts
                    
                    ##Kiểm tra có cấu hình department setting nào, mà department đó có renew contract
                    
                    dict_request, renew_contracts = self.compute_data_from_setting(cr, uid, False, False, renew_department_ids, False, dict_request, mcontext)
                    mcontext['renew_contracts'] = renew_contracts
                    
                    ##Kiểm tra có cấu hình department group setting nào, mà department group đó có renew contract
                    
                    dict_request, renew_contracts = self.compute_data_from_setting(cr, uid, False, renew_department_group_ids, False, False, dict_request, mcontext)
                    mcontext['renew_contracts'] = renew_contracts
                    
                    ##Kiểm tra có cấu hình BU setting nào, mà BU đó có renew contract
                    
                    dict_request, renew_contracts = self.compute_data_from_setting(cr, uid, renew_division_ids, False, False, False, dict_request, mcontext)
                    mcontext['renew_contracts'] = renew_contracts
                                            
                    if dict_request:
                        for key in dict_request:
                            #item = [approver_id, list_mail_cc]: renew_contract_ids
                            approver_id = key[0]
                            mails_cc = key[1]
                            
                            print 'approver=',approver_id,'cc=',mails_cc
                            renew_contract_ids = dict_request[key]
                            vals = {'is_collaborator': is_collaborator, 
                                    'is_probation': is_probation,
                                    'date_request': date_request,
                                    'date_from': search_from, 
                                    'date_to': search_to,
                                    'approver_id': approver_id,
                                    'cc_work_mail':mails_cc,
                                    'cc_work_mail_default':mails_cc,
                                    'state': 'draft'}
                            
                            remain_not_renew_contract_ids = remain_not_renew_contract_ids.difference(renew_contract_ids)
                        
                            department_ids = []
                            team_ids = []
                            department_group_ids = []
                            list_contracts = []
                            for c_id in renew_contract_ids:
                                contract = contract_obj.read(cr, uid, c_id, ['employee_id'])
                                employee_id = contract.get('employee_id',False) and contract['employee_id'][0] or False
                                if employee_id:
                                    emp = emp_obj.read(cr, uid, employee_id, ['department_id', 'team_id','department_group_id'])
                                    department_group_id = emp.get('department_group_id', False) and emp['department_group_id'][0] or False
                                    department_id = emp.get('department_id', False) and emp['department_id'][0] or False
                                    team_id = emp.get('team_id', False) and emp['team_id'][0] or False
                                    if department_id:
                                        department_ids.append(department_id)
                                    if team_id:
                                        team_ids.append(team_id)
                                    
                                    if department_group_id:
                                        department_group_ids.append(department_group_id)
                                    
                                    #Only renew if contract is last contract of employee
                                    last_contract_ids = contract_obj.search(cr, uid, [('employee_id','=',employee_id),
                                                                                      ('state','!=','cancel')], limit=1, order='date_start_real desc')
                                    if c_id in last_contract_ids:
                                        #Not create anymore if exist in detail
                                        exist_detail_ids = renew_detail_obj.search(cr, uid, [('contract_id','=',c_id)])
                                        if exist_detail_ids:
                                            continue
                                        
                                        res_contract = renew_detail_obj.default_get(cr, uid, list_detail_fields, {'default_contract_id': c_id})
                                        res_contract['is_collaborator'] = is_collaborator
                                        list_contracts.append([0, 0, res_contract])
                            
                            if department_ids and len(set(department_ids)) == 1:
                                vals['department_id'] = department_ids[0]
                            
                            if team_ids and len(set(team_ids)) == 1:
                                vals['team_id'] = team_ids[0] 
                            
                            if department_group_ids and len(set(department_group_ids)) == 1:
                                vals['department_group_id'] = department_group_ids[0] 
                            
                            exist_ids = self.search(cr, uid, [('is_collaborator','=',is_collaborator),
                                                              ('is_probation','=',is_probation),
                                                              ('date_from','=',search_from),
                                                              ('date_to','=',search_to),
                                                              ('department_id','=',vals.get('department_id',False)),
                                                              ('team_id','=',vals.get('team_id',False)),
                                                              ('approver_id','=',approver_id),
                                                              ('cc_work_mail_default','=',mails_cc)])
                            if exist_ids:
                                extra_mess = 'Official Contract'
                                if is_probation:
                                    extra_mess = 'Probation Contract'
                                elif is_collaborator:
                                    extra_mess = 'Non Official Contract'
                                
                                department_id = vals.get('department_id', False)
                                team_id = vals.get('team_id', False)
                                log.info('%s at team %s department %s from %s to %s exist record show renew contract'% (extra_mess, team_id, department_id,search_from,search_to))
                                continue
                            
                            if list_contracts:
                                vals['contract_lines'] = list_contracts
                                record_id = self.create(cr, uid, vals, context)
                                if record_id:
                                    record_ids.append(record_id)
                
#                 if record_ids:
#                     self.execute_workflow(cr, uid, record_ids, {'action': 'submit'})
        
        log.info( '\n Contract not renew because of department disappear in Setting:' + str(remain_not_renew_contract_ids))
        
        return True
    
    def get_renew_contract_from_subtype_setting(self, cr, uid, renew_division_ids, renew_department_group_ids, 
                                                renew_department_ids, renew_team_ids, dict_request, mcontext):
        if not mcontext:
            mcontext = {}
        
        mcontext['is_subtype'] = True
        #Kiểm tra có cấu hình team setting subtype nào, mà team đó có renew contract
        dict_request, renew_contracts = self.compute_data_from_setting(cr, uid, False, False, False, renew_team_ids, dict_request, mcontext)
        
        ##Kiểm tra có cấu hình department setting subtype nào, mà department đó có renew contract
        dict_request, renew_contracts = self.compute_data_from_setting(cr, uid, False, False, renew_department_ids, False, dict_request, mcontext)
        
        ##Kiểm tra có cấu hình department group setting subtype nào, mà department group đó có renew contract
        dict_request, renew_contracts = self.compute_data_from_setting(cr, uid, False, renew_department_group_ids, False, False, dict_request, mcontext)
        
        ##Kiểm tra có cấu hình BU setting subtype nào, mà BU đó có renew contract
        dict_request, renew_contracts = self.compute_data_from_setting(cr, uid, renew_division_ids, False, False, False, dict_request, mcontext)
        
        mcontext['is_subtype'] = False
        return dict_request, renew_contracts
        
    def compute_data_from_setting(self, cr, uid, division_ids, department_group_ids, department_ids, team_ids, dict_request, context=None):
        if not context:
            context = {}
        
        is_sub_type_configure = context.get('is_subtype', False)
        renew_setting_obj = self.pool.get('vhr.multi.renew.contract.setting')
        contract_obj = self.pool.get('hr.contract')
        domain = []
        child_division_ids = context.get('child_division_ids', [])
        child_dept_group_ids = context.get('child_dept_group_ids', [])
        department_team_ids = context.get('department_team_ids', [])
        renew_contracts = context.get('renew_contracts', {})
        is_probation = context.get('is_probation', False)
        is_collaborator = context.get('is_collaborator', False)
        
        if division_ids:
            domain = [('division_id','in',division_ids),
                      ('is_bu','=',True),
                      ('active','=', True)]
            
        elif department_group_ids:
            domain=[ ('is_department_group','=', True),
                     ('department_group_id','in',department_group_ids),
                     ('active','=', True)]
            
        elif department_ids:
            domain=[ ('is_department','=', True),
                     ('department_id','in',department_ids),
                     ('active','=', True)]
        
        elif team_ids:
            domain=[('is_team','=', True),
                    ('team_id','in',team_ids),
                     ('active','=', True)]
        
        if is_sub_type_configure:
            domain.append(('is_sub_type_configure','=',True))
        setting_ids = renew_setting_obj.search(cr, uid, domain)
        
        if setting_ids:
            renew_subtype_contract_ids = []
            if is_sub_type_configure:
                for label in renew_contracts:
                    renew_subtype_contract_ids.extend(renew_contracts[label])
                renew_subtype_contract_ids = contract_obj.search(cr, uid, [('id','in', renew_subtype_contract_ids),
                                                                           ('sub_type_id','!=', False)])
            
            renew_subtype_contract_ids = set(renew_subtype_contract_ids)
                    
            settings = renew_setting_obj.browse(cr, uid, setting_ids)
            for setting in settings:
                team_id = setting.team_id and setting.team_id.id or False
                department_id = setting.department_id and setting.department_id.id or False
                department_group_id = setting.department_group_id and setting.department_group_id.id or False
                division_id = setting.division_id and setting.division_id.id or False
                item = (team_id, department_id, department_group_id, division_id)
                renew_contract_ids = []
                
                #Is Bu Setting 
                if division_ids:
                    child_of_division_ids = child_division_ids.get(division_id, [])
                    child_of_division_ids = list(set(child_of_division_ids))
                    for department_group_id in child_of_division_ids:
                        department_ids = child_dept_group_ids.get(department_group_id, [])
                        department_ids = list(set(department_ids))
                        for department_id in department_ids:
                            child_team_ids = department_team_ids.get(department_id,[])
                            child_team_ids = list(set(child_team_ids))
                            for team_id in child_team_ids:
                                item = (team_id, department_id, department_group_id, division_id)
                                #Get list renew contract of team-department
                                
                                renew_contract_ids, renew_contracts =self.parse_renew_contract(cr, uid, is_sub_type_configure, 
                                                                                               renew_subtype_contract_ids, 
                                                                                               renew_contracts, renew_contract_ids, item)
                
                elif department_group_ids:
                    department_ids = child_dept_group_ids.get(department_group_id, [])
                    department_ids = list(set(department_ids))
                    for department_id in department_ids:
                        child_team_ids = department_team_ids.get(department_id,[])
                        child_team_ids = list(set(child_team_ids))
                        for team_id in child_team_ids:
                            item = (team_id, department_id, department_group_id, division_id)
                            #Get list renew contract of team-department
                            renew_contract_ids, renew_contracts =self.parse_renew_contract(cr, uid, is_sub_type_configure, 
                                                                                               renew_subtype_contract_ids, 
                                                                                               renew_contracts, renew_contract_ids, item)
                
                #Is Department Setting 
                elif department_ids:
                    child_team_ids = department_team_ids.get(department_id,[])
                    child_team_ids = list(set(child_team_ids))
                    for team_id in child_team_ids:
                        item = (team_id, department_id, department_group_id, division_id)
                        #Get list renew contract of team-department
                        renew_contract_ids, renew_contracts =self.parse_renew_contract(cr, uid, is_sub_type_configure, 
                                                                                               renew_subtype_contract_ids, 
                                                                                               renew_contracts, renew_contract_ids, item)
                
                #Is Team setting
                elif team_ids:
                    #Get list renew contract of team-department
                    renew_contract_ids, renew_contracts =self.parse_renew_contract(cr, uid, is_sub_type_configure, 
                                                                                               renew_subtype_contract_ids, 
                                                                                               renew_contracts, renew_contract_ids, item)
                
                
                
                if renew_contract_ids:
                    to_person, cc_persons = self.get_list_to_cc_of_setting_by_type_renew(cr, uid, setting, is_sub_type_configure, is_collaborator, is_probation, context)
                    """
                        Các loại type person :team_leader, dept_head, hrbp, direct_boss
                    """
                    dict_request = self.compute_group_request(cr, uid, renew_contract_ids, to_person, cc_persons, dict_request, context)
        
        return dict_request, renew_contracts
    
    def parse_renew_contract(self, cr, uid, is_sub_type_configure, renew_subtype_contract_ids, renew_contracts, renew_contract_ids, item):
        intersect = renew_subtype_contract_ids.intersection(renew_contracts.get(item,[]))
        if is_sub_type_configure and intersect:
            renew_contract_ids.extend(list(intersect))
            renew_contracts[item] = [i for i in renew_contracts[item] if i not in intersect]
        elif not is_sub_type_configure:
            renew_contract_ids.extend( renew_contracts.pop(item, [])  )
        
        return renew_contract_ids, renew_contracts
        
        
    def compute_group_request(self, cr, uid, contract_ids, to_person, cc_persons, dict_request, context=None):
        print 'contract_idsss=',contract_ids
        if contract_ids and to_person:
            contract_obj = self.pool.get('hr.contract')
            for renew_contract_id in contract_ids:
                contract = contract_obj.read(cr, uid, renew_contract_id, ['employee_id'])
                employee_id = contract.get('employee_id', False) and contract['employee_id'][0]
                    
                to_name, to_person_id,to_mail = self.get_person_from_type_based_on_employee(cr, uid, employee_id, to_person, context)
                cc_names, cc_person_ids, cc_mails = [],[],[]
                if cc_persons:
                    for cc_person in cc_persons:
                        cc_name, cc_person_id, cc_mail = self.get_person_from_type_based_on_employee(cr, uid, employee_id, cc_person, context)
                        if cc_name:
                            cc_names.append(cc_name)
                            cc_person_ids.append(cc_person_id)
                            cc_mails.extend(cc_mail)
                
                cc_mails.sort()
                cc_mails = list(set(cc_mails).difference(to_mail))
                mails_cc = ';'.join(cc_mails)
                item = (to_person_id, mails_cc)
                if item not in dict_request:
                    dict_request[item] = []
                
                dict_request[item].append(renew_contract_id)
        
        return dict_request
    
    def get_list_to_cc_of_setting_by_type_renew(self, cr, uid, setting, is_subtype, is_collaborator, is_probation, context=None):
        setting_obj = self.pool.get('vhr.multi.renew.contract.setting')
        to = ''
        cc_list = []
        if setting:
            if is_subtype:
                name1 = setting.subtype_non_official_to_type_person_id and setting.subtype_non_official_to_type_person_id.code or ''
                name2 = setting.subtype_non_official_to_person_id and setting.subtype_non_official_to_person_id.login or ''
                to = name1 or name2
                
                name1 = setting_obj.get_employee_name_from_group(cr, uid, setting.subtype_non_official_cc_type_person_ids, {"get_code": True})
                name2 = setting_obj.get_employee_name_from_group(cr, uid, setting.subtype_non_official_cc_person_ids, context)
                cc_list = name1+name2
                
            elif is_collaborator:
                name1 = setting.non_official_to_type_person_id and setting.non_official_to_type_person_id.code or ''
                name2 = setting.non_official_to_person_id and setting.non_official_to_person_id.login or ''
                to = name1 or name2

                name1 = setting_obj.get_employee_name_from_group(cr, uid, setting.non_official_cc_type_person_ids, {"get_code": True})
                name2 = setting_obj.get_employee_name_from_group(cr, uid, setting.non_official_cc_person_ids, context)
                cc_list = name1+name2
            
            else:
                name1 = setting.official_to_type_person_id and setting.official_to_type_person_id.code or ''
                name2 = setting.official_to_person_id and setting.official_to_person_id.login or ''
                to = name1 or name2
                
                name1 = setting_obj.get_employee_name_from_group(cr, uid, setting.official_cc_type_person_ids, {"get_code": True})
                name2 = setting_obj.get_employee_name_from_group(cr, uid, setting.official_cc_person_ids, context)
                cc_list = name1+name2
            
        
        return to, cc_list
    
    def get_person_from_type_based_on_employee(self, cr, uid, employee_id, type_person, context=None):
        """
        Lấy thông tin login, id, email của type_person        dựa trên employee
                                           dh,lm,team lead
        """
        name = type_person
        person_id = False
        mail = []
        emp_obj = self.pool.get('hr.employee')
        if employee_id and type_person:
            emp = emp_obj.browse(cr, uid, employee_id)
            if type_person == 'team_leader':
                person_id = emp.team_id and emp.team_id.manager_id and emp.team_id.manager_id or False
                if person_id:
                    mail.append(person_id.work_email)
                name = person_id and person_id.login or False
                person_id = person_id and person_id.id or False
            
            elif type_person == 'dept_head':
                person_id = emp.department_id and emp.department_id.manager_id and emp.department_id.manager_id or False
                if person_id:
                    mail.append(person_id.work_email)
                name = person_id and person_id.login or False
                person_id = person_id and person_id.id or False
                
            
            elif type_person == 'direct_boss':
                person_id = emp.report_to or False
                if person_id:
                    mail.append(person_id.work_email)
                name = person_id and person_id.login or False
                person_id = person_id and person_id.id or False
                
            
            elif type_person == 'hrbp':
                hrbps = emp.department_id and emp.department_id.hrbps
                if hrbps:
                    name = []
                    person_id = []
                    for hrbp in hrbps:
                        name.append(hrbp.login)
                        person_id.append(hrbp.id)
                        if hrbp:
                            mail.append(hrbp.work_email)
            
            elif type_person == 'ass_hrbp':
                ass_hrbps = emp.department_id and emp.department_id.ass_hrbps
                if ass_hrbps:
                    name = []
                    person_id = []
                    for ass_hrbp in ass_hrbps:
                        name.append(ass_hrbp.login)
                        person_id.append(ass_hrbp.id)
                        if ass_hrbp:
                            mail.append(ass_hrbp.work_email)
            
            else:
                emp_ids = emp_obj.search(cr, uid, [('login','=',type_person)])
                if emp_ids:
                    person_id = emp_ids[0]
                    emp = emp_obj.read(cr, uid, person_id, ['work_email'])
                    mail.append(emp.get('work_email',''))
        
        
        return name, person_id, mail
            
            
    
    def check_over_deadline_confirm(self, cr, uid, context=None):
        '''
        Check if contract only have 1 days remain to confirm (Official must confirm before 15 days of Contract expired date, Collaborator is 7 days):
         Collaborator: change state to finish
         Official:     change state to finish, send mail alert, auto renew contract
        '''
        if not context:
            context = {}
            
        renew_contract_detail_pool = self.pool.get('vhr.multi.renew.contract.detail')
        
        #7 + 1 because check contract have 1 days remain to confirm
        deadline_official = (datetime.today().date() + relativedelta(days=8)).strftime(DEFAULT_SERVER_DATE_FORMAT)
        
        cancel_collaborator_contract_ids = renew_contract_detail_pool.search(cr, uid, [('state','=','department'),('date_end','<=', deadline_official)])
        if cancel_collaborator_contract_ids:
            context['renew_status'] = 'reject'
            self.auto_finish_over_deadline_contract(cr, uid, cancel_collaborator_contract_ids, context)
        
        deadline_official = (datetime.today().date() + relativedelta(days=16)).strftime(DEFAULT_SERVER_DATE_FORMAT)
        cancel_official_contract_ids = renew_contract_detail_pool.search(cr, uid, [('state','=','department'),('date_end','<=', deadline_official)])
        if cancel_official_contract_ids:
            context['renew_status'] = 'renew'
            list_renew_ids = self.auto_finish_over_deadline_contract(cr, uid, cancel_official_contract_ids, context)
            
            #Create renew contract
            list_renew_ids = list(set(list_renew_ids))
            self.renew_multi_contracts(cr, uid, list_renew_ids, context)
            
            details = renew_contract_detail_pool.browse(cr, uid, cancel_official_contract_ids)
            for detail in details:
                date = datetime.today().date().strftime("%d-%m-%Y")
                renew_id = detail.multi_renew_id and detail.multi_renew_id.id or False
                domain_account_of_employee = detail.employee_id and detail.employee_id.code or ''
                context = {'date':date, 'domain_account_of_employee': domain_account_of_employee}
                
                if renew_id and detail.multi_renew_id.is_send_mail:
                    self.send_mail(cr, uid, renew_id, 'department', 'finish', context)
                
        
        return True
    
    def check_remind_renew_contract(self, cr, uid, context=None):
        '''
        Đối với HĐ NVCT: Remind 2 lần:
            Lần 1: Sau 7 ngày kể từ ngày gởi yêu cầu confirm
            Lần 2: Sau 3 ngày kể từ ngày remind lần 1 (Tức sau 10 ngày kể từ ngày gởi yêu cầu confirm)
        
        Đối với HD CTV-HD Thu Viec: Remind 1 lần  sau 3 ngày kể từ ngày gửi yêu cầu confirm
        '''
        if not context:
            context = {}
        
        today =  datetime.today().date()
        
        
        
        if context.get('force_today', False):
            today = context.get('force_today', False)
            today = datetime.strptime(today, DEFAULT_SERVER_DATE_FORMAT)
        
        date_remind =today.strftime(DEFAULT_SERVER_DATE_FORMAT)
        date_remind_1 = (today - relativedelta(days=7)).strftime(DEFAULT_SERVER_DATE_FORMAT)
        date_remind_2 = (today - relativedelta(days=10)).strftime(DEFAULT_SERVER_DATE_FORMAT)
        
        #Search for official contract for remidn first time
        official_renew_remind_first_ids = self.search(cr, uid, [('is_collaborator','=',False),
                                                                ('is_probation','=', False),
                                                                ('date_send_mail_dept','=',date_remind_1),
                                                                ('state','=','department'),
                                                                ('is_send_mail','=', True)])
        if official_renew_remind_first_ids:
            context['subject_element_name'] = '1st'
            self.write(cr, uid, official_renew_remind_first_ids, {'date_send_mail_remind': datetime.today().date()})
            for renew_id in official_renew_remind_first_ids:
                self.send_mail(cr, uid, renew_id, 'department', 'department', context)
        
        #Search for official contract for remidn second time
        official_renew_remind_second_ids = self.search(cr, uid, [('is_collaborator','=',False),
                                                                 ('is_probation','=', False),
                                                                ('date_send_mail_dept','=',date_remind_2),
                                                                  ('state','=','department'),
                                                                  ('is_send_mail','=', True)])
        if official_renew_remind_second_ids:
            context['subject_element_name'] = '2nd'
            self.write(cr, uid, official_renew_remind_second_ids, {'date_send_mail_remind': datetime.today().date()})
            for renew_id in official_renew_remind_second_ids:
                self.send_mail(cr, uid, renew_id, 'department', 'department', context)
            
        over_official_renew_remind_second_ids = self.search(cr, uid, [('is_collaborator','=',False),
                                                                      ('is_probation','=', False),
                                                                      ('date_send_mail_dept','<',date_remind_2),
                                                                      ('state','=','department')])
        
        if over_official_renew_remind_second_ids:
            self.write(cr, uid, over_official_renew_remind_second_ids, {'is_overtime_remind': True})
        
        
        date_remind_1 = (today - relativedelta(days=3)).strftime(DEFAULT_SERVER_DATE_FORMAT)
        
        #Search for colla contract
        collaborator_renew_ids = self.search(cr, uid, [
                                                      ('date_send_mail_dept','=',date_remind_1),
                                                      ('state','=','department'),
                                                      ('is_send_mail','=', True),
                                                      '|',('is_collaborator','=',True),
                                                          ('is_probation','=',True)
                                                      ])
        if collaborator_renew_ids:
            self.write(cr, uid, collaborator_renew_ids, {'date_send_mail_remind': datetime.today().date()})
            for renew_id in collaborator_renew_ids:
                self.send_mail(cr, uid, renew_id, 'department', 'department', context)
        
        
        over_collaborator_renew_ids = self.search(cr, uid, [
                                                      ('date_send_mail_dept','<',date_remind_1),
                                                      ('state','=','department'),
                                                      '|',('is_collaborator','=',True),
                                                          ('is_probation','=',True)
                                                      ])
        if over_collaborator_renew_ids:
            self.write(cr, uid, over_collaborator_renew_ids, {'is_overtime_remind': True})
        
#         self.check_over_deadline_confirm(cr, uid, context)
        
        return True
    
    def format_date(self, date):
        date = datetime.strptime(date, DEFAULT_SERVER_DATE_FORMAT)
        return date.strftime('%d/%m/%Y')
    
    def split_request(self, cr, uid, ids, context=None):
        if ids:
            line_obj = self.pool.get('vhr.multi.renew.contract.detail')
            for multi in self.read(cr, uid, ids, ['count_detail_lines','contract_lines','state']):
                count_detail_lines = multi.get('count_detail_lines',0) 
                if count_detail_lines > 50:
                    contract_lines = multi.get('contract_lines',[])
                    split_num = count_detail_lines / 40 - 1
                    vals = self.copy_data(cr, uid, multi['id'], default={'contract_lines': []})
                    vals['state'] = multi.get('state','draft')
                    if not vals.get('note',''):
                        vals['note'] = ''
                    vals['note'] += '\n  Split from id ' + str(multi['id'])
                    for index in range(split_num):
                        detail_ids = contract_lines[:40]
                        if detail_ids:
                            contract_lines = list(set(contract_lines).difference(set(detail_ids)))
                            
                            new_multi_id = self.create(cr, uid, vals)
                            line_obj.write(cr, uid, detail_ids, {'multi_renew_id': new_multi_id})
                        else:
                            break
        
        return True
                    
        
    

vhr_multi_renew_contract()