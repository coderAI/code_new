# -*-coding:utf-8-*-
import logging
import thread
import sys
import re
import simplejson as json

from openerp.osv import osv, fields
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from lxml import etree
from openerp.sql_db import Cursor
from openerp.sql_db import ConnectionPool
from openerp import tools
from openerp import SUPERUSER_ID
from datetime import datetime
from vhr_working_record import STATES_ALL as STATES_ALL
from vhr_working_record import STATES_TRANSFER_DEPARTMENT as STATES_TRANSFER_DEPARTMENT
from vhr_working_record import STATES_NOT_TRANSFER_DEPARTMENT as STATES_NOT_TRANSFER_DEPARTMENT
from vhr_working_record import dict_salary_fields

from openerp.addons.vhr_human_resource.wizard.vhr_working_record_mass_movement import FIELD_PARENT_AFFECTS

from vhr_mass_movement_mail_template_process import mail_process_of_mass_not_adjust_salary


log = logging.getLogger(__name__)

class vhr_mass_movement(osv.osv):
    _name = 'vhr.mass.movement'
    _description = 'Mass Movement'
    
    def _count_attachment(self, cr, uid, ids, prop, unknow_none, context=None):
        ir_attachment = self.pool.get('ir.attachment')
        res = {}
        for item in ids:
            number = ir_attachment.search(cr, uid, [('res_id', '=', item), ('res_model', '=', self._name)], count=True)
            res[item] = number
        return res
    
    def _is_person_do_action(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if not ids:
            return True
        if not isinstance(ids, list):
            ids = [ids]
        for record_id in ids:
            res[record_id] = self.is_person_do_action(cr, uid, [record_id], context)
            
        return res
    
#     def _is_able_to_do_action_reject(self, cr, uid, ids, field_name, arg, context=None):
#         res = {}
#         if not isinstance(ids, list):
#             ids = [ids]
#             
#         for record_id in ids:
#             res[record_id] = self.is_able_to_do_action_reject(cr, uid, [record_id], context)
#                         
#         return res
    
    def _check_waiting_for(self, cr, uid, ids, prop, unknow_none, context = None):
        if not context:
            context= {}
        
        context["search_all_employee"] = True
        context['active_test'] = False
        
        if uid:
            user = self.pool.get('res.users').read(cr, uid, uid, ['login'])
            login = user.get('login','')
            context['login'] = login
            
        res,emp_ids = self.pool.get('vhr.working.record').get_login_users_waiting_for_action(cr, uid, ids, 'vhr.mass.movement', context)
        return res
    
    def is_action_user_search(self, cr, uid, obj, name, args, context=None):
        if not args:
            return []
        
        working_pool = self.pool.get('vhr.working.record')
        domain = []
        employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=',uid)])
        res = []
        if employee_ids:
            #search requester
            domain.extend(['&',('requester_id','in',employee_ids),('state','=','draft')])
        
                
            department_ids = working_pool.get_department_of_hrbp(cr, uid, employee_ids[0], context)
            
            if department_ids:
                
                #State New HRBP
                if domain:
                    domain.insert(0,'|')
                domain.extend(['&',('state','=','new_hrbp'),('department_id_new','in',department_ids)])
            
            groups = working_pool.get_groups(cr, uid, context={'get_correct_cb': True})
            if 'vhr_hr_dept_head' in groups:
                if domain:
                    domain.insert(0,'|')
                domain.append(('state','=','dept_hr'))
            
            if 'vhr_cb_working_record' in groups:
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
    
    def _is_able_to_create(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if not isinstance(ids, list):
            ids = [ids]
        
        for record_id in ids:
            res[record_id] = True
        return res
    
    def _is_change_form_adjust_salary(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for record in self.browse(cr, uid, ids):
            res[record.id] = False
            if record.change_form_ids:
                for change_form in record.change_form_ids:
                    if change_form.is_salary_adjustment:
                        res[record.id] = True
        return res
    
    
    def _get_data_from_change_form(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        
        config_obj = self.pool.get('ir.config_parameter')
        form_code = config_obj.get_param(cr, uid, 'vhr_human_resource_change_form_check_show_change_type_in_mass_movement') or ''
        form_code = form_code.split(',')
            
        for record in self.browse(cr, uid, ids, fields_process=['change_form_ids']):
            res[record.id] = {}
            fields_name = []
            change_form_name = []
            is_transfer_department = False
            remove_data_for_custom_name = []
            if record.change_form_ids:
                for change_form in record.change_form_ids:
                    change_form_name.append(change_form.name or '')
                    
                    access_field_ids = change_form.access_field_ids or []
                    field_ids = [field.id for field in access_field_ids]
                    field_transfer_ids = self.pool.get('ir.model.fields').search(cr, uid, [('id','in',field_ids),
                                                                                           ('name','=','department_id_new')])
                    if field_transfer_ids:
                        is_transfer_department = True
                    
                    if change_form.code in form_code:
                        remove_data_for_custom_name.append(change_form.name)
                    
                    if access_field_ids:
                        for field in access_field_ids:
                            fields_name.append(field.name or '')
                            
            fields_name = list(set(fields_name))
            res[record.id]['fields_affect_by_change_form'] = ', '.join(fields_name)
            res[record.id]['change_form_name'] = ' - '.join(change_form_name)
            
            #Remove dieu chinh luong in custom name for send email
            if remove_data_for_custom_name and is_transfer_department:
                change_form_name = [name for name in change_form_name if name not in remove_data_for_custom_name]
            res[record.id]['change_form_name_custom'] = ' - '.join(change_form_name)
        
        return res
    
    def invisible_change_salary(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if not isinstance(ids, list):
            ids = [ids]
        
        if not context:
            context = {}
        
        working_pool = self.pool.get('vhr.working.record')
        for record_id in ids:
            record = self.browse(cr, uid, record_id)
            
            change_form_ids = [change_form.id for change_form in record.change_form_ids]
            is_mixed = self.is_special_case_for_change_form(cr, uid, change_form_ids, context)
            
            if is_mixed:
                department_id = record.department_id_new  and record.department_id_new.id or False
                department_code = record.department_id_new and record.department_id_new.code or ''
            else:
                department_id = record.department_id_old  and record.department_id_old.id or False
                department_code = record.department_id_old and record.department_id_old.code or ''
            
            invisible = working_pool.set_invisible_change_salary(cr, uid, department_id, department_code, context)
            res[record_id] = invisible
                        
        return res
    
    def is_change_salary_percentage_by_hand(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if not isinstance(ids, list):
            ids = [ids]
        
        for record_id in ids:
            res[record_id] = True
        
        return res
    
    def _get_is_required_attachment(self, cr, uid, ids, field_name, arg, context=None):
        '''
        # Với SM có chứa đồng thời 2 loại: "Điều chỉnh lương" và "luân chuyển phòng ban" thì khi approve tại bước New HRBP bắt buộc phải attach email offline                      
          Bắt buộc attach file tại bước draft
        '''
        res = {}
        if not isinstance(ids, list):
            ids = [ids]
        
        for record in self.read(cr, uid, ids, ['state','change_form_ids']):
            res[record['id']] = False
            
            state = record.get('state', False)
            change_form_ids = record.get('change_form_ids',[])
            is_mixed = self.is_special_case_for_change_form(cr, uid, change_form_ids, context)
            
            if state == 'draft' or (state == 'new_hrbp' and is_mixed):
                res[record['id']] = True
        
        return res
    
    _columns = {
                'name': fields.char('Name', size=64),
                'requester_id': fields.many2one('hr.employee', 'Requester', ondelete='restrict'),
                'company_id': fields.many2one('res.company', 'Entity', ondelete='restrict'),
                'effect_from': fields.date('Effective From'),
                'decision_no': fields.char('Decision No', size=128),
                'sign_date': fields.date('Sign Date'),
                'signer_id': fields.char("Signer"),
                'signer_job_title_id': fields.char("Signer Job Title"),
                'note': fields.text('Note'),
                
                'division_id_old': fields.many2one('hr.department', 'Business Unit', domain=[('organization_class_id.level','=', '1')], ondelete='restrict'),
                'department_group_id_old': fields.many2one('hr.department', 'Department Group', domain=[('organization_class_id.level','=', '2')], ondelete='restrict'), 
                'department_id_old': fields.many2one('hr.department', 'Department', domain=[('organization_class_id.level','=', '3')], ondelete='restrict'),
                'manager_id_old': fields.related('department_id_old', 'manager_id', type='many2one', relation='hr.employee', string='Old Dept Head'),
                'work_for_company_id_new': fields.many2one('res.company', 'Work for Company', ondelete='restrict'),
                'office_id_new': fields.many2one('vhr.office', 'Office', ondelete='restrict'),
                'division_id_new': fields.many2one('hr.department', 'Business Unit', domain=[('organization_class_id.level','=', '1')], ondelete='restrict'),
                'department_group_id_new': fields.many2one('hr.department', 'Department Group', domain=[('organization_class_id.level','=', '2')], ondelete='restrict'), 
                'department_id_new': fields.many2one('hr.department', 'Department', domain=[('organization_class_id.level','=', '3')], ondelete='restrict'),
                'team_id_new': fields.many2one('hr.department', 'Team', domain=[('organization_class_id.level','>=', '4')], ondelete='restrict'),
                'job_title_id_new': fields.many2one('vhr.job.title', 'Title', ondelete='restrict'),
                'job_level_id_new': fields.many2one('vhr.job.level', 'Level', ondelete='restrict'),
                #New job level
                'job_level_position_id_new': fields.many2one('vhr.job.level.new', 'Position Level', ondelete='restrict'),
                'job_level_person_id_new': fields.many2one('vhr.job.level.new', 'Person Level', ondelete='restrict'),
                
                 #LuanNG: Remove this field in future version of vHRS
                'position_class_id_new': fields.many2one('vhr.position.class', 'Position Class', ondelete='restrict'),
                'report_to_new': fields.many2one('hr.employee', 'Reporting Line', ondelete='restrict'),
#                 'approver_id_new': fields.many2one('hr.employee', 'Approver', ondelete='restrict'),
#                 'mentor_id_new': fields.many2one('hr.employee', 'Mentor', ondelete='restrict'),
                'manager_id_new': fields.many2one('hr.employee', 'Dept Head', ondelete='restrict'),
                
                'pro_job_family_id_new': fields.many2one('vhr.job.family','Pro Job Family',ondelete='restrict',domain=[('track_id.code','=', 'Professional')]),
                'pro_job_group_id_new': fields.many2one('vhr.job.group','Pro Job Group',ondelete='restrict'),
                'pro_sub_group_id_new': fields.many2one('vhr.sub.group','Pro Sub Group',ondelete='restrict'),
                'pro_ranking_level_id_new': fields.many2one('vhr.ranking.level','Pro Level',ondelete='restrict'),
                'pro_grade_id_new': fields.many2one('vhr.grade','Pro Grade',ondelete='restrict'),
                
                'mn_job_family_id_new': fields.many2one('vhr.job.family','Management Job Family',ondelete='restrict',domain=[('track_id.code','=', 'Management')]),
                'mn_job_group_id_new': fields.many2one('vhr.job.group','Management Job Group',ondelete='restrict'),
                'mn_sub_group_id_new': fields.many2one('vhr.sub.group','Management Sub Group',ondelete='restrict'),
                'mn_ranking_level_id_new': fields.many2one('vhr.ranking.level','Management Level',ondelete='restrict'),
                'mn_grade_id_new': fields.many2one('vhr.grade','Management Grade',ondelete='restrict'),
                
                'salary_setting_id_new': fields.many2one('vhr.salary.setting', 'Type of salary', ondelete='restrict'),
                
                'seat_new': fields.char('Seat No', size=32),
                'ext_new': fields.char('Ext', size=32),
                'work_phone_new': fields.char('Office phone', size=32),
                'work_email_new': fields.char('Working email', size=32),
                'mobile_phone_new': fields.char('Cell phone', size=32),
                
                'gross_salary_new': fields.float('Gross Salary'),
                'basic_salary_new': fields.float('Basic Salary'),
                'kpi_amount_new': fields.float('KPI'),
                'general_allowance_new': fields.float('General Allowance'),
                'v_bonus_salary_new': fields.float('V_Bonus'),
                'salary_percentage_new': fields.float('% Split Salary'),
                'collaboration_salary_new': fields.float('Collaboration Salary'),
                
                
                'employee_ids': fields.many2many('hr.employee', 'mass_movement_employee_rel', 'mass_movement_id', 'employee_id', 'Employees'),
                
                'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                          domain=[('object_id.model', '=', _name),
                                                  ('field_id.name', 'not in',
                                                   ['write_date','audit_log_ids'])]),
                'state': fields.selection(STATES_ALL, 'Status', readonly=True),
                'current_state': fields.selection(STATES_ALL, 'Current Stage', readonly=True),
                'passed_state': fields.text('Passed State'),
                'attachment_count': fields.function(_count_attachment, type='integer', string='Attachments'),
                'create_uid': fields.many2one('res.users', 'Create User', ondelete='restrict'),
                'create_user': fields.related('create_uid', 'login', type="char", string="Create User"),
                'create_date': fields.date('Create Date'),
                
                'write_uid': fields.many2one('res.users', 'Update User', ondelete='restrict'),
                'write_user': fields.related('write_uid', 'login', type="char", string="Update User"),
                'write_date': fields.date('Update Date'),
                'is_person_do_action': fields.function(_is_person_do_action, type='boolean', string='Is Person Do Action'),
#                 'is_able_to_do_action_reject': fields.function(_is_able_to_do_action_reject, type='boolean', string='Is Person Do Action Reject'),
                'state_log_ids': fields.one2many('vhr.state.change', 'res_id', 'History', domain=[('model', '=', _name)]),
                'waiting_for' : fields.function(_check_waiting_for, type='char', string='Waiting For', readonly = 1, multi='waiting_for'),
                'is_waiting_for_action' : fields.function(_check_waiting_for, type='boolean', string='Is Waiting For Approval', readonly = 1, multi='waiting_for', fnct_search=is_action_user_search),
                'users_validated': fields.text('User Validate'),
                'is_public': fields.boolean('Is Public'),
                
                'change_form_ids':fields.many2many('vhr.change.form','mass_movement_change_form_rel','mass_movement_id','change_form_id','Change Form'),
                'is_able_to_create': fields.function(_is_able_to_create, type='boolean', string='Is Able To Create'),
                'is_change_form_adjust_salary': fields.function(_is_change_form_adjust_salary, type='boolean', string='Is Change Form Adjust Salary'),
                'change_form_name': fields.function(_get_data_from_change_form, type='text', string='Change Form',multi='get_data'),
                'change_form_name_custom': fields.function(_get_data_from_change_form, type='text', string='Change Form Name Custom',multi='get_data'),

                'fields_affect_by_change_form': fields.function(_get_data_from_change_form, type='text', string="Fields Affect By Change Form",multi='get_data'),
                'invisible_change_salary': fields.function(invisible_change_salary, type='boolean', string='Invisible Change Salary Group'),
                
                'is_change_salary_percentage_by_hand': fields.function(is_change_salary_percentage_by_hand, type='boolean', string='Is Change Salary Percentage By Hand'),
                'is_change_basic_salary_by_hand': fields.function(is_change_salary_percentage_by_hand, type='boolean', string='Is Change Basic Salary By Hand'),
                'attachment_ids': fields.one2many('ir.attachment', 'res_id', 'Attachment', domain=[('res_model', '=', _name)]),
                'is_required_attachment': fields.function(_get_is_required_attachment, type='boolean', string="Is Require Attachment"),
    }
    
    
    _order = "effect_from desc"
    
    def _get_default_company_id(self, cr, uid, context=None):
        company_ids = self.pool.get('res.company').search(cr, uid, [('is_member', '=', False)], order="id asc")
        if company_ids:
            return company_ids[0]

        return False
    
    def _get_requester_id(self, cr, uid, context=None):
        return self.get_requester_id(cr, uid, context)
    
    def _get_is_able_to_create(self, cr, uid, context=None):
        """
        Only allow 'vhr_assistant_to_hrbp','vhr_hrbp','vhr_cb_working_record' to create request, multi request, mass request
        """
        if not context:
            context = {}
        
        context['title_request'] = 'Mass Request'
        return self.pool.get('vhr.working.record').check_is_able_to_create_request(cr, uid, context)
    
    _defaults = {
        'name': 'Mass Request',
        'is_person_do_action': True,
        'is_public': True,
        'company_id': _get_default_company_id,
        'requester_id': _get_requester_id,
        'state': 'draft',
        'current_state': 'draft',
        'is_able_to_create': _get_is_able_to_create,
        'invisible_change_salary': False,
        'passed_state': '',
        'is_change_salary_percentage_by_hand': True,
        'is_change_basic_salary_by_hand': True
        
    }
    
    def read(self, cr, user, ids, fields=None, context=None, load='_classic_read'):
        if not context:
            context = {}
        
        if 'active_test' not in context:
            context['active_test'] = False
        
        
        res =  super(vhr_mass_movement, self).read(cr, user, ids, fields, context, load)
        return res
    
    def onchange_company_id(self, cr, uid, ids, department_id, company_id, effect_from, context=None):
        res = {'employee_ids': []}
        
        return {'value': res}
    
    def onchange_effect_from(self, cr, uid, ids, department_id, company_id, effect_from, context=None):
        res = {'employee_ids': []}
        
        return {'value': res}
    
    def onchange_change_form_ids(self, cr, uid, ids, change_form_ids, fields_affect_by_change_form, division_id_old, department_group_id_old, department_id_old, context=None):
        res = {'is_change_form_adjust_salary': False, 'gross_salary_new': 0,'salary_percentage_new': 0,
               'basic_salary_new': 0,'kpi_amount_new':0,'general_allowance_new':0,'v_bonus_salary_new':0,
               'fields_affect_by_change_form': ''}
        fields_name  = []
        if change_form_ids and change_form_ids[0] and len(change_form_ids[0]) == 3 and change_form_ids[0][2]:
            change_form_ids = change_form_ids[0][2]
            change_forms = self.pool.get('vhr.change.form').browse(cr, uid, change_form_ids)
            for change_form in change_forms:
                access_field_ids = change_form.access_field_ids
                if access_field_ids:
                    for field in access_field_ids:
                        fields_name.append(field.name or '')
                if change_form.is_salary_adjustment:
                    res = {'is_change_form_adjust_salary': True}
#                     return {'value': res}
            
        if fields_affect_by_change_form:
            old_fields_affect = fields_affect_by_change_form.split(',')
            old_fields_affect = [item.strip() for item in old_fields_affect]
            fail_fields = [item for item in old_fields_affect if item not in fields_name]
            for field in fail_fields:
                res[field] = False
                if field == 'division_id_new':
                    res[field] = division_id_old
                
                elif field == 'department_group_id_new':
                    res[field] = department_group_id_old
                    
                elif field == 'department_id_new':
                    res[field] = department_id_old
                
        fields_name = list(set(fields_name))
        res['fields_affect_by_change_form'] = ', '.join(fields_name)
                    
        return {'value': res}
    
    
#     def onchange_signer_id(self, cr, uid, ids, signer_id, context=None):
#         value = {}
#         if signer_id:
#             signer_info = self.pool.get('hr.employee').read(cr, uid, signer_id, ['title_id'])
#             title_id = signer_info.get('title_id', False) and signer_info['title_id'][0] or False
#             value['signer_job_title_id'] = title_id
#         
#         return {'value': value}
    
    def onchange_division_id_old(self, cr, uid, ids, division_id, context=None):
        res = {'department_id_old': False,'employee_ids': [], 'department_group_id_old': False}
        
        res['division_id_new'] = division_id
        
        return {'value': res}
    
    def onchange_department_group_id_old(self, cr, uid, ids, department_group_id_old, context=None):
        res = {'department_id_old': False,'employee_ids': []}
        
        res['department_group_id_new'] = department_group_id_old
        
        return {'value': res} 
    
    def onchange_department_id_old(self, cr, uid, ids, department_id_old, division_id_old,division_id_new, context=None):
        res = {'employee_ids': []}
        
        if division_id_old and division_id_new and division_id_old == division_id_new:
            res['department_id_new'] = department_id_old
        
        return {'value': res}
    
    
    def onchange_office_id_new(self, cr, uid, ids, context=None):
        return {'value': {'division_id_new': False} }
        
    def onchange_division_id_new(self, cr, uid, ids, context=None):
        res = {'department_group_id_new': False,
               'department_id_new': False,
               'manager_id_new': False,
               'team_id_new': False
               }
        
        return {'value': res}   
    
    def onchange_department_group_id_new(self, cr, uid, ids, context=None):
        res = {'department_id_new': False,
               'manager_id_new': False,
               'team_id_new': False
               }
        
        return {'value': res}   
    
    def onchange_department_id_new(self, cr, uid, ids, department_id, context=None):
        res = {'manager_id_new': False, 'team_id_new': False, 'report_to_new': False}
        if department_id:
            department_info = self.pool.get('hr.department').read(cr, uid, department_id, ['manager_id'])
            manager_id = department_info.get('manager_id', False) and department_info['manager_id'][0] or False   
            res['manager_id_new'] = manager_id
            res['report_to_new'] = manager_id
        return {'value': res}
    
    def onchange_team_id_new(self, cr, uid, ids, team_id, context=None):
        res = {}
        if team_id:
            department_info = self.pool.get('hr.department').read(cr, uid, team_id, ['manager_id'])
            manager_id = department_info.get('manager_id', False) and department_info['manager_id'][0] or False   
            res['report_to_new'] = manager_id
            
        return {'value': res}
    
    def onchange_attachment_ids(self, cr, uid, ids, attachment_temp_ids, context=None):
        res = {'attachment_count': 0}
        if attachment_temp_ids:
            attachment_count = 0
            for attachment in attachment_temp_ids:
                attachment_count += 1
                
            res['attachment_count'] = attachment_count
            
        return {'value': res}
    
    def onchange_job_title_id_new(self, cr, uid, ids, job_title_id, job_level_id, pro_sub_group_id_new, context=None):
        return self.pool.get('vhr.working.record').onchange_job_title_id(cr, uid, ids, job_title_id, job_level_id, pro_sub_group_id_new, False, context)
    
    def onchange_pro_job_family_id_new(self, cr, uid, ids, pro_job_family_id_new, pro_job_group_id_new, context=None):
        return self.pool.get('vhr.working.record').onchange_pro_job_family_id_new(cr, uid, ids, pro_job_family_id_new, pro_job_group_id_new, context)
    
    def onchange_pro_job_group_id_new(self, cr, uid, ids, pro_job_group_id_new, pro_sub_group_id_new, context=None):
        return self.pool.get('vhr.working.record').onchange_pro_job_group_id_new(cr, uid, ids, pro_job_group_id_new, pro_sub_group_id_new, context)
    
    def onchange_pro_ranking_level_id_new(self, cr, uid, ids, pro_ranking_level_id_new, pro_grade_id_new, context=None):
        return self.pool.get('vhr.working.record').onchange_pro_ranking_level_id_new(cr, uid, ids, pro_ranking_level_id_new, pro_grade_id_new, context)

    def onchange_mn_job_family_id_new(self, cr, uid, ids, mn_job_family_id_new, mn_job_group_id_new, context=None):
        return self.pool.get('vhr.working.record').onchange_mn_job_family_id_new(cr, uid, ids, mn_job_family_id_new, mn_job_group_id_new, context)
    
    def onchange_mn_job_group_id_new(self, cr, uid, ids, mn_job_group_id_new, mn_sub_group_id_new ,context=None):
        return self.pool.get('vhr.working.record').onchange_mn_job_group_id_new(cr, uid, ids, mn_job_group_id_new, mn_sub_group_id_new, context)

    def onchange_mn_ranking_level_id_new(self, cr, uid, ids, mn_ranking_level_id_new, mn_grade_id_new, context=None):
        return self.pool.get('vhr.working.record').onchange_mn_ranking_level_id_new(cr, uid, ids, mn_ranking_level_id_new, mn_grade_id_new, context)
    
    
    def onchange_gross_salary(self, cr, uid, ids, gross_salary, basic_salary, kpi_amount, salary_percentage, is_change_salary_percentage_by_hand, context=None):
        return self.pool.get('vhr.working.record').onchange_gross_salary(cr, uid, ids, gross_salary, basic_salary, kpi_amount, salary_percentage, is_change_salary_percentage_by_hand, context)
    
    def onchange_salary_percentage(self, cr, uid, ids, gross_salary, basic_salary, kpi_amount, salary_percentage, is_change_salary_percentage_by_hand, context=None):
        return self.pool.get('vhr.working.record').onchange_salary_percentage(cr, uid, ids, gross_salary, basic_salary, kpi_amount, salary_percentage, is_change_salary_percentage_by_hand, context)
   
    def onchange_basic_salary(self, cr, uid, ids, gross_salary, basic_salary, kpi_amount, salary_percentage, is_change_basic_salary_by_hand,context=None):
        return self.pool.get('vhr.working.record').onchange_basic_salary(cr, uid, ids, gross_salary, basic_salary, kpi_amount, salary_percentage, is_change_basic_salary_by_hand,context)
    
    def onchange_kpi_amount(self, cr, uid, ids, gross_salary, basic_salary, kpi_amount, context=None):
        return self.pool.get('vhr.working.record').onchange_kpi_amount(cr, uid, ids, gross_salary, basic_salary, kpi_amount, context)
    
    def onchange_general_allowance(self, cr, uid, ids, gross_salary, basic_salary, kpi_amount, general_allowance, context=None):
        return self.pool.get('vhr.working.record').onchange_general_allowance(cr, uid, ids, gross_salary, basic_salary, kpi_amount, general_allowance, context)
    
    def onchange_v_bonus_salary(self, cr, uid, ids, gross_salary, basic_salary, kpi_amount, v_bonus_salary, context=None):
        return self.pool.get('vhr.working.record').onchange_v_bonus_salary(cr, uid, ids, gross_salary, basic_salary, kpi_amount, v_bonus_salary, context)
    
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        #Search rule in staff movement
        if not context:
            context = {}
        if 'active_test' not in context:
            context['active_test'] = False
        
        if context.get('record_type', False) == 'request':
            context['model'] = self._name
            args = self.pool.get('vhr.working.record').build_condition_menu_for_staff_movement(cr, uid, args, offset, limit, order, context, count)
            
        
        res =  super(vhr_mass_movement, self).search(cr, uid, args, offset, limit, order, context, count)
        return res
    
    #Do not allow to create record have same emp-comp with WR have state!= cancel and Mass movement with state not in [cancel,finish]
    def check_record_same_effect_from(self, cr, uid, ids, context=None):
        if ids:
            if not isinstance(ids, list):
                ids = [ids]
            
            wr_pool = self.pool.get('vhr.working.record')
            
            mass_movements = self.browse(cr, uid, ids, fields_process=['company_id','employee_ids', 'effect_from'])
            for mass_movement in mass_movements:
                error = ""
                company_id = mass_movement.company_id and mass_movement.company_id.id or False
                employees = mass_movement.employee_ids
                effect_from = mass_movement.effect_from
                for employee in employees:
                    #Search in mass movement
                    same_mass = self.search(cr, uid, [('company_id','=',company_id),
                                                      ('employee_ids','=',employee.id),
                                                      ('state','not in',['cancel','finish'])])
                    if mass_movement.id in same_mass:
                        same_mass.remove(mass_movement.id)
                    if same_mass:
                        dup_mass = self.read(cr, uid, same_mass[0], ['effect_from'])
                        effect_from_str = datetime.strptime(dup_mass['effect_from'],DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y")
                        
                        error += employee.name + " - " + employee.login + " - " + effect_from_str + "\n"
                    else:
                        #Search in staff movement
                        same_mass = wr_pool.search(cr, uid, [('company_id','=',company_id),
                                                             ('employee_id','=',employee.id),
                                                             ('state','not in',['cancel','finish',False])])
                        if same_mass:
                            dup_mass = wr_pool.read(cr, uid, same_mass[0], ['effect_from'])
                            effect_from_str = datetime.strptime(dup_mass['effect_from'],DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y")
                        
                            error += employee.name + " - " + employee.login + " - " + effect_from_str + "\n"
                            continue
                        
                        #search WR effect_from on same day
                        same_mass = wr_pool.search(cr, uid, [('company_id','=',company_id),
                                                             ('employee_id','=',employee.id),
                                                             ('state','in',[False,'finish']),
                                                             ('effect_from','=',effect_from)])
                        if same_mass:
                            dup_mass = wr_pool.read(cr, uid, same_mass[0], ['effect_from'])
                            effect_from_str = datetime.strptime(dup_mass['effect_from'],DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y")
                            
                            error += employee.name + " - " + employee.login + " - " + effect_from_str + "\n"
                    
                if error:        
                    effect_from = datetime.strptime(effect_from,DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y")
                    raise osv.except_osv('Validation Error !', 
                                         'The following employees have a working record \nor a staff movement/ mass movement does not finish :\n\n %s' % (error))
        
        return True
    
    def create(self, cr, uid, vals, context=None):
        res = super(vhr_mass_movement, self).create(cr, uid, vals, context)
        
        if res:
            self.check_record_same_effect_from(cr, uid, [res], context)
        
        return res
    
    def write(self, cr, uid, ids, vals, context=None):
        if not context:
            context = {}
        
        if not isinstance(ids, list):
            ids = [ids]
            
        if vals.get('users_validated', False):
            record = self.read(cr, uid, ids[0],['users_validated'])
            if record.get('users_validated', False):
                users_validated = filter(None, map(lambda x: x.strip(), record['users_validated'].split(',')))
                #If do action return, remove user from users_validated to can approve later
                if context.get('return_to_previous_state', False):
                    if vals['users_validated'] in users_validated:
                        users_validated.remove(vals['users_validated'])
                    vals['users_validated'] = ','.join(users_validated)
                else:
                    if vals['users_validated'] not in users_validated:
                        vals['users_validated'] += ',' + record['users_validated']
                    else:
                        del vals['users_validated']
                        
        if vals.get('passed_state', False):
            record = self.read(cr, uid, ids[0],['passed_state'])
            if record.get('passed_state', False):
                passed_state = filter(None, map(lambda x: x.strip(), record['passed_state'].split(',')))
                #If do action return, remove state from passed_state
                if context.get('return_to_previous_state', False):
                    if vals['passed_state'] in passed_state:
                        passed_state.remove(vals['passed_state'])
                    vals['passed_state'] = ','.join(passed_state)
                else:
                    if vals['passed_state'] not in passed_state:
                        vals['passed_state'] = record['passed_state'] + ',' + vals['passed_state']
                    else:
                        del vals['passed_state']
                    
        res = super(vhr_mass_movement, self).write(cr, uid, ids, vals, context=None)
        
        if res and vals.get('state',False) == 'finish':
            if context.get('create_from_fin_mass_movement', False):
                context['create_from_fin_mass_movement'].extend(ids)
            else:
                context['create_from_fin_mass_movement'] = ids
            
#             if not context.get('multi_approve_to_finish', False):
#                 self.create_working_record(cr, uid, ids, context)
        
        return res
    
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        if ids:
            records = self.read(cr, uid, ids, ['state'])
            for record in records:
                if record.get('state',False) != 'draft':
                    raise osv.except_osv('Validation Error !', 'You can only delete records which are at state Draft !')
                try:
                    res = super(vhr_mass_movement, self).unlink(cr, uid, [record['id']], context)
                except Exception as e:
                    log.exception(e)
                    raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res
    
    def create_working_record(self, cr, uid, ids, context=None):
        log.info('Start create_working_record of Mass Movement')
        
        try:
            thread.start_new_thread(vhr_mass_movement.thread_execute, (self,cr, uid, ids,context) )
        except Exception as e:
            log.exception(e)
            log.info('Error: Unable to start thread execute Mass Movement')
        log.info('End create_working_record of Mass Movement')
         
        return True
    
    def create_mass_status(self, cr, uid, context=None):
        
        vals = { 'state' : 'new' }
        
        employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', uid)])
        if employee_ids:
            vals['requester_id'] = employee_ids[0]
            
        module_ids = self.pool.get('ir.module.module').search(cr, uid, [('name','=','vhr_human_resource')])
        if module_ids:
            vals['module_id'] = module_ids[0]
             
        model_ids = self.pool.get('ir.model').search(cr, uid, [('model','=','vhr.mass.movement')])
        if model_ids:
            vals['model_id'] = model_ids[0]
         
        mass_status_id = self.pool.get('vhr.mass.status').create(cr, uid, vals)
        
        return mass_status_id
        
    
    def thread_execute(self, main_cr, uid, ids, context=None):
        if not context:
            context = {}
        log.info('Start thread_execute mass movement')
        mass_status_pool = self.pool.get('vhr.mass.status')
        mass_status_detail_pool = self.pool.get('vhr.mass.status.detail')
        working_record_pool = self.pool.get('vhr.working.record')
        change_form_pool = self.pool.get('vhr.change.form')
        parameter_obj = self.pool.get('ir.config_parameter')
        
        _pool = ConnectionPool(int(tools.config['db_maxconn']))
        #clear old thread in cache to free memory
         
        error_employees = ""
        if ids:
            if not isinstance(ids, list):
                ids = [ids]
            
            columns =  self._columns
            fields = columns.keys()
            
            working_record_columns = working_record_pool._columns
            working_record_fields = working_record_columns.keys()
                
            for record_id in ids:
                #cr used to create WR
                cr = Cursor(_pool, main_cr.dbname, True)
                #t_cr used to create/write Mass Status/ Mass Status Detail
                t_cr = Cursor(_pool, main_cr.dbname, True) #Thread's cursor
                reload(sys)
                
                mass_movement = self.browse(cr, uid, record_id)
                cons_fields = ['requester_id', 'employee_ids', 'current_state', 'audit_log_ids', 'state_log_ids',
                               'create_uid','create_user','is_person_do_action','waiting_for','attachment_ids']
                fields = [x for x in fields if x not in cons_fields]
                #read data in wizard form for create working record
                data = self.read(cr, uid, record_id, fields)
                del data['id']
                #Bug when call this thread, mass momovement does not finish write state='finish'
                data['state'] = 'finish'
                #remove data[field] = False, change data[field] from tuple (id, name) to id 
                for field in fields:
                    if not data.get(field) and field not in ['is_public']:
                        delete = True
                        if field in FIELD_PARENT_AFFECTS.keys():
                            for parent_field in FIELD_PARENT_AFFECTS[field]:
                                if data.get(parent_field, False):
                                    delete = False
                                    break
                        
                        if delete:
                            del data[field]
                    elif isinstance(data[field], tuple):
                        data[field] = data[field][0]
                 
                effect_from = data.get('effect_from',False)
                company_id = data.get('company_id',False)
                
                change_form_ids = []
                if data.get('change_form_ids',[]):
                    change_form_ids = data['change_form_ids']
                    data['change_form_ids'] = [[6,False,data['change_form_ids']]]
                else:
                    data['change_form_ids'] = [[6,False,[]]]
                     
                employees = mass_movement.employee_ids
                
                mass_status_id = self.create_mass_status(t_cr, uid, context)
                t_cr.commit()
                
                if mass_status_id:
                    mass_status_pool.write(t_cr, uid, [mass_status_id], {'state': 'running',
                                                                         'number_of_record': len(employees), 
                                                                         'number_of_execute_record': 0,
                                                                         'number_of_fail_record': 0})
                    error_message = ""
                    create_ids = []
                    try:
                        list_error = []
                        num_count = 0
                        for employee in employees:
                            if employee:
                                employee_id = employee.id
                                error_item = False
                                try:
                                    num_count += 1
                                    mass_status_pool.write(t_cr, uid, [mass_status_id], {'number_of_execute_record': num_count})
                                    t_cr.commit()
                                     
                                    record_vals = working_record_pool.default_get(cr, SUPERUSER_ID, working_record_fields, context)
                                     
                                    record_vals.update({'employee_id': employee_id} )
                                    #get data when onchange effect_from
                                    context['create_from_outside'] = True
                                    onchange_effect_from_data = working_record_pool.onchange_effect_from(cr, uid, [], effect_from, employee_id, company_id, False, False, False, False, True, False, False, False, context)
                                    #Raise error when can not find contract for employee on effect_from
                                    if onchange_effect_from_data.get('warning', False):
                                        error_item = onchange_effect_from_data['warning']
                                        list_error.append( (employee_id, error_item) )
         
                                    else:
                                        onchange_effect_from_value = onchange_effect_from_data['value']
                                        for field in onchange_effect_from_value.keys():
                                            if isinstance(onchange_effect_from_value[field], tuple):
                                                onchange_effect_from_value[field] = onchange_effect_from_value[field][0]
                                        
                                        error = False
                                        if onchange_effect_from_data.get('domain', False):
                                            #Raise error if WR near WR create by Termination have change form=termination
                                            domain_effect_from = onchange_effect_from_data['domain']
                                            if 'change_form_ids' in domain_effect_from:
                                                domain_change_form = domain_effect_from['change_form_ids']
                                                
                                                avalable_change_form_ids = change_form_pool.search(cr, uid, domain_change_form, order='id asc')
                                                if not set(avalable_change_form_ids).intersection(set(change_form_ids)):
                                                    error_item = "Change Form not satisfy domain %s" % (str(domain_change_form))
                                                    list_error.append( (employee_id, error_item) )
                                                    error = True
                                        
                                        if not error: 
                                            record_vals.update( onchange_effect_from_value )
                                            record_vals.update(data )
                                                 
                                            res = working_record_pool.create(cr, uid, record_vals, context)
                                            if res:
                                                create_ids.append(res)
                                                t_cr.commit()
                                                mass_status_detail_pool.create(t_cr, uid, {'mass_status_id': mass_status_id,
                                                                                           'employee_id': employee_id,
                                                                                           'message': '',
                                                                                           'status': 'success'})
                                             
                                except Exception as e:
                                    log.exception(e)
                                    try:
                                        error_item = e.message
                                        if not error_item:
                                            error_item = e.value
                                    except:
                                        error_item = ""
                                         
                                    list_error.append( (employee_id, error_item) )
                                #If have error during the task with employee_id, then roll back to revert action create new working record
                                if error_item:
                                    mass_status_pool.write(t_cr, uid, [mass_status_id], {'number_of_fail_record': len(list_error)})
                                    mass_status_detail_pool.create(t_cr, uid, {'mass_status_id': mass_status_id,
                                                                               'employee_id' : list_error[-1][0],
                                                                               'message':list_error[-1][1]})
                                    t_cr.commit()
                                    cr.rollback()
                                else:
                                    #if dont have error with employee_id, then commit to action with next employee_id wont affect to new WR of current employee_id
                                    t_cr.commit()
                                    cr.commit()
                        if list_error:
                            mass_status_pool.write(t_cr, uid, [mass_status_id], {'state': 'error','number_of_fail_record': len(list_error)})
                                 
                        else:
                            mass_status_pool.write(t_cr, uid, [mass_status_id], {'state': 'finish'})
                        
                        #Move attachment from Mass movement to WR
                        if create_ids:
                            attachment_pool = self.pool.get('ir.attachment')
                            attachment_ids = attachment_pool.search(cr, uid, [('res_model','=','vhr.mass.movement'),
                                                                              ('res_id','=',record_id)])
                            if attachment_ids:
                                for attachment_id in attachment_ids:
                                    attachment_data = attachment_pool.copy_data(cr, uid, attachment_id)
                                    for create_id in create_ids: 
                                        attachment_data['res_model'] = 'vhr.working.record'
                                        attachment_data['res_id'] = create_id
                                        attachment_pool.create(cr, uid, attachment_data)
                     
                    except Exception as e:
                        log.exception(e)
                        try:
                            error_message = e.message
                            if not error_message:
                                error_message = e.value
                        except:
                            error_message = ""
                             
                        #If have error with first try, then rollback to clear all created WR
                        cr.rollback()
                        self.pool.get('vhr.working.record').roll_back_working_record(cr, uid, create_ids, context)
                        log.info('Error occur while Mass Movement!')
                     
                    if error_message:
                        #Use cr in here because InternalError if use t_cr
                        mass_status_pool.write(cr, uid, [mass_status_id], {'state': 'fail','error_message': error_message})
                         
                    cr.commit()
                    cr.close()
                     
                    t_cr.commit()
                    t_cr.close()
        log.info('End thread_execute mass movement')
#                     return True
         
        return True
    
    def get_requester_id(self, cr, uid, context=None):
        employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=',uid)], context={"search_all_employee": True})
        if employee_ids:
            return employee_ids[0]
        
    def fields_view_get(self, cr, uid, view_id = None, view_type = 'form', context = None, toolbar = False, submenu = False):
        res = super(vhr_mass_movement, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar = toolbar, submenu = submenu)
        if context is None:
            context = {}
        if view_type == 'form':
            doc = etree.XML(res['arch'])
            if res['type'] == 'form':
                 #When view view_vhr_mass_movement_submit_form
                if context.get('action',False):
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
                
                config_parameter = self.pool.get('ir.config_parameter')
                adjust_salary_code = config_parameter.get_param(cr, uid, 'vhr_human_resource_change_form_code_adjust_salary') or ''
                adjust_salary_code_list = adjust_salary_code.split(',')
                
                domain = [('show_hr_rotate', '=', True),('is_salary_adjustment','=',False)]
                if adjust_salary_code_list:
                    adjust_salary_change_form_ids = self.pool.get('vhr.change.form').search(cr, uid, [('code','in',adjust_salary_code_list)])
                    domain.append(('id','not in', adjust_salary_change_form_ids))
                    
                for node in doc.xpath("//field[@name='change_form_ids']"):
                    node.set('domain', str(domain))
                
                columns =  self._columns
                fields = columns.keys()
                
                groups = self.pool.get('vhr.working.record').get_groups(cr, uid)
                #Assistant to HRBP va HRBP trong working record co cung quyen create, edit field
                if 'vhr_assistant_to_hrbp' in groups and 'vhr_hrbp' not in groups:
                    groups.append('vhr_hrbp')
                
                #Temporary add group vhr_dept_head for permission of dept head
                employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=',uid)])
                if employee_ids:
                    department_ids = self.pool.get('hr.department').search(cr, uid, [('manager_id','in',employee_ids)])
                    if department_ids:
                        groups.append('vhr_dept_head')
                
                cons_fields = ['requester_id', 'effect_from', 'change_form_type_id', 'audit_log_ids', 
                               'state_log_ids','manager_id_new','state','attachment_ids','attachment_count']
                fields = [x for x in fields if x not in cons_fields]
                for field in fields:
                    for node in doc.xpath("//field[@name='%s']" %field):
                        modifiers = json.loads(node.get('modifiers'))
                        if not modifiers.get('invisible',False):
                            args_readonly, args_invisible = self.pool.get('vhr.working.record').build_args_for_field(cr, uid, field, groups, context)
                            
                            if field in ['company_id','employee_ids','division_id_old','department_group_id_old','department_id_old']:
                                args_invisible = False
                                args_readonly = ['|',('state','!=', 'draft'),('is_person_do_action','=', False)]
                            elif field in ['change_form_ids']:
                                args_invisible = False
                                args_readonly = ['|',('state','!=', 'draft'),('is_person_do_action','=', False)]
                            elif field == 'is_public' and 'vhr_cb' not in groups:
                                args_invisible = True
                            elif not args_readonly:
                                args_readonly = ['|',('is_person_do_action','=', False),
                                                     ('state','not in',['draft','new_hrbp','cb'])]
                                
                                if field not in ['note','is_public','keep_authority','employee_ids',
                                                 'ts_working_group_id_new','timesheet_id_new']:
                                    args_invisible = [('fields_affect_by_change_form','not indexOf',field)]
                            
                                    if field in dict_salary_fields.keys():
                                        args_invisible.append(('is_change_form_adjust_salary','=',False))
                                        args_invisible.insert(0,'|')
                                        
                                        if 'salary_by_hours_timeline' in field:
                                            args_invisible.append(('is_salary_by_hours_new','=',False))
                                            args_invisible.insert(0,'|')
                                
                            modifiers.update({'invisible' : args_invisible})
                            modifiers.update({'readonly' : args_readonly})
                            node.set('modifiers', json.dumps(modifiers))
                    
            res['arch'] = etree.tostring(doc)
        return res   
    
    def is_creator(self, cr, uid, ids, context=None):
        if ids:
            meta_datas = self.perm_read(cr, SUPERUSER_ID, ids, context)
            if meta_datas and meta_datas[0].get('create_uid', False) and meta_datas[0]['create_uid'][0] == uid:
                return True
        
        return False
    
    def is_dept_head(self, cr, uid, ids, context=None):
        if ids:
            record = self.browse(cr, uid, ids[0])
            if record and record.department_id_old and record.department_id_old.manager_id\
             and record.department_id_old.manager_id.user_id \
              and uid == record.department_id_old.manager_id.user_id.id:
                return True
        return False
    
    def is_new_dept_head(self, cr, uid, ids, context=None):
        if ids:
            record = self.browse(cr, uid, ids[0])
            if record and record.department_id_new and record.department_id_new.manager_id\
             and record.department_id_new.manager_id.user_id \
              and uid == record.department_id_new.manager_id.user_id.id:
                return True
        return False
    
    def is_old_division_leader(self, cr, uid, ids, context=None):
        if ids:
            record = self.browse(cr, uid, ids[0])
            if record and record.division_id_old and record.division_id_old.manager_id\
             and record.division_id_old.manager_id.user_id \
              and uid == record.division_id_old.manager_id.user_id.id:
                return True
        return False
    
    def is_old_hrbp(self, cr, uid, ids, context=None):
        hrbp_employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=',uid)])
        if ids and hrbp_employee_ids:
            department_of_hrbp_ids = self.pool.get('vhr.working.record').get_department_of_hrbp(cr, uid, hrbp_employee_ids[0], context)
            if department_of_hrbp_ids:
                record = self.read(cr, uid, ids[0], ['department_id_old'])
                if record and record.get('department_id_old', False) and record['department_id_old'][0] in department_of_hrbp_ids:
                    return True
        
        return False
    
    def is_new_hrbp(self, cr, uid, ids, context=None):
        hrbp_employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=',uid)])
        if ids and hrbp_employee_ids:
            department_of_hrbp_ids = self.pool.get('vhr.working.record').get_department_of_hrbp(cr, uid, hrbp_employee_ids[0], context)
            if department_of_hrbp_ids:
                record = self.read(cr, uid, ids[0], ['department_id_new'])
                if record and record.get('department_id_new', False) and record['department_id_new'][0] in department_of_hrbp_ids:
                    return True
        
        return False
    
    def is_old_assist_hrbp(self, cr, uid, ids, context=None):
        hrbp_employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=',uid)])
        if ids and hrbp_employee_ids:
            department_of_hrbp_ids = self.pool.get('vhr.working.record').get_department_of_ass_hrbp(cr, uid, hrbp_employee_ids[0], context)
            if department_of_hrbp_ids:
                record = self.read(cr, uid, ids[0], ['department_id_old'])
                if record and record.get('department_id_old', False) and record['department_id_old'][0] in department_of_hrbp_ids:
                    return True
         
        return False
#     
#     def is_new_assist_hrbp(self, cr, uid, ids, context=None):
#         hrbp_employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=',uid)])
#         if ids and hrbp_employee_ids:
#             department_of_hrbp_ids = self.pool.get('vhr.working.record').get_department_of_ass_hrbp(cr, uid, hrbp_employee_ids[0], context)
#             if department_of_hrbp_ids:
#                 record = self.read(cr, uid, ids[0], ['department_id_new'])
#                 if record and record.get('department_id_new', False) and record['department_id_new'][0] in department_of_hrbp_ids:
#                     return True
#         
#         return False
    
    
    def open_window(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        
        context['do_not_validate_read_attachment'] = True
        if context.get('hide_form_view_button', False):
            context['hide_form_view_button'] = False
        if context.get('record_type',False) == 'request':
            
            is_require_data_for_submit = False
            if context.get('action', False) in ['submit','approve']:
                records = self.read(cr, uid, ids, ['attachment_ids','is_required_attachment','state'])
                for record in records:
                    if (not record.get('attachment_ids',[])or record['state'] == 'new_hrbp') and record.get('is_required_attachment', False):
                        is_require_data_for_submit = True
                        break
            
            context['is_require_data_for_submit'] = is_require_data_for_submit
        
            view_open = 'view_vhr_mass_movement_submit_form'
            action = {
                'name': 'Notes',
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': self.pool.get('ir.model.data').get_object_reference(cr, uid, 'vhr_human_resource', view_open)[1],
                'res_model': 'vhr.mass.movement',
                'context': context,
                'type': 'ir.actions.act_window',
                #'nodestroy': True,
                'target': 'new',
                #'auto_refresh': 1,
                'res_id': ids[0],
            }
            return action
        
        return self.execute_workflow(cr, uid, ids, context)
    
    def execute_workflow(self, cr, uid, ids, context=None):
        
        if isinstance(ids, (int, long)):
            ids = [ids]
        if context is None: context = {}
        context['call_from_execute'] = True
        list_ids_to_create_wr = []
        for record_id in ids:
            try:
                action_result = False
                action_next_result = False
                record = self.read(cr, uid, record_id, ['state'])
                old_state = record.get('state', False)
                
                if old_state:
                    if old_state in ['cancel','finish']:
                        raise osv.except_osv('Validation Error !', "You don't have permission to do this action")
                    
                    if context.get('action', False) == 'submit':
                        action_next_result = self.action_next(cr, uid, [record_id], context) 
                        
                    elif context.get('action', False) == 'return':
                        if old_state == 'draft':
                            raise osv.except_osv('Validation Error !', "You don't have permission to do this action")
                        
                        action_result = self.action_return(cr, uid, [record_id], context)
                        
                    elif context.get('action', False) == 'reject':
                        action_result = self.action_reject(cr, uid, [record_id], context)
                    
                    if action_next_result or action_result:
                        record = self.read(cr, uid, record_id, ['state'])
                        new_state = record.get('state', False)
                        if old_state != new_state:
                            self.send_mail(cr, uid, record_id, old_state, new_state, context)
                        
                        if new_state == 'finish' and context.get('action', False) == 'submit':
                            list_ids_to_create_wr.append(record_id)
                            
                    else:
                        raise osv.except_osv('Validation Error !', "You don't have permission to do this action")
                            
                    if context.get('action') and action_result:
                        state_vals = {}
                        STATES = self.get_state_dicts(cr, uid, record_id, context)
                        list_states = {item[0]: item[1] for item in STATES}
                        
                        record = self.read(cr, uid, record_id, ['state'])
                        new_state = record.get('state', False)
                        state_vals['old_state'] = list_states[ old_state]
                        state_vals['new_state'] = list_states[new_state]
#                         state_vals['create_uid'] = uid
        #                 state_vals['create_date'] = datetime.today().date()
                        state_vals['res_id'] = record_id
                        state_vals['model'] = self._name
                        if 'ACTION_COMMENT' in context:
                            state_vals['comment'] = context['ACTION_COMMENT']
                        self.pool.get('vhr.state.change').create(cr, uid, state_vals)
                        
            except Exception as e:
                log.exception(e)
                try:
                    error_message = e.message
                    if not error_message:
                        error_message = e.value
                except:
                    error_message = ""
                raise osv.except_osv('Validation Error !', 'Have error during execute record:\n %s!' % error_message)
        
        if list_ids_to_create_wr:
            self.create_working_record(cr, uid, list_ids_to_create_wr, context)

        return True
    
    def is_person_do_action(self, cr, uid, ids, context=None):
        if ids:
            groups = self.pool.get('vhr.working.record').get_groups(cr, uid, {'get_correct_cb': True})
            
            record = self.read(cr, uid, ids[0], ['state','change_form_ids'])
            state = record.get('state', False)
            change_form_ids = record.get('change_form_ids',[])
            
            if  (state == 'draft' and self.is_creator(cr, uid, ids, context) 
                 and set(['vhr_assistant_to_hrbp','vhr_hrbp','vhr_cb_working_record']).intersection(groups) )\
             or (state == 'new_hrbp' and self.is_new_hrbp(cr, uid, ids, context))\
             or (state == 'dept_hr' and 'vhr_hr_dept_head' in groups)\
             or (state in ['cb'] and 'vhr_cb_working_record' in groups):
                return True
        
        return False
    
     #Default button Reject invisible when is_person_do_action = False
    #When is_person_do_action=True, button Reject depend on is_able_to_do_action_reject
    #In other case if is_person_do_action=True, 
    #    button Reject will visible in state ["new_hrbp","dept_hr","cb"] 
#     def is_able_to_do_action_reject(self, cr, uid, ids, context=None):
#         if not context:
#             context = {}
#             
#         pass_state = ["new_hrbp","dept_hr",'cb']
#         value = False
#         if ids:
#             record_id = ids[0]
#             record = self.read(cr, uid, record_id, ['state','change_form_ids'])
#             state = record.get('state', False)
#             if state in pass_state:
#                 value = True
#             elif state == 'hrbp':
#                 change_form_ids = record.get('change_form_ids', [])
#                 if change_form_ids:
#                     change_forms = self.pool.get('vhr.change.form').browse(cr, uid, change_form_ids)
#                     is_adjust_salary = self.pool.get('vhr.working.record').is_change_form_about_salary(cr, uid, change_forms, context)
#                     if is_adjust_salary:
#                         value =  False
#                     else:
#                         value = True
#         
#         return value
    
    #Do not allow to submit/approve if employee do action in next state dont have user_id
    #Only need to check user do action in state :dh_approval/new_dh_approval because other state get user do action in group
    def check_exist_action_user_for_next_state(self, cr, uid, ids, next_state, context=None):
        if ids and next_state:
            records = self.browse(cr, uid, ids)
            error_employees = ""
            
            dict_state_group = {'dept_hr': 'vhr_hr_dept_head', 
                                'cb': 'vhr_cb_working_record'}
            
            for record in records:
                
                if next_state == 'new_hrbp':
                    hrbps = record.department_id_new.hrbps
#                     ass_hrbps = record.department_id_new.ass_hrbps
#                     hrbps += ass_hrbps
                    count_hrbp = len(hrbps)
                    if count_hrbp == 0:
                        raise osv.except_osv('Validation Error !', "Don't have any HRBP at department %s "% (record.department_id_new.complete_code or ''))

                    non_user_ids = 0
                    for hrbp in hrbps:
                        user_id = hrbp.user_id
                        if not user_id:
                            non_user_ids += 1
                            error_employees += "\n" + hrbp.name_related + " - " + hrbp.code
                    if non_user_ids != count_hrbp:
                        error_employees = ""
                        
                elif next_state in  dict_state_group.keys():
                    employee_ids = self.pool.get('vhr.working.record').get_employee_ids_belong_to_group(cr, uid, dict_state_group[next_state], context)
                    non_user_ids = 0
                    count_emp = len(employee_ids)
                    if employee_ids:
                        employees = self.pool.get('hr.employee').read(cr, uid, employee_ids, ['user_id','name','code'])
                        for employee in employees:
                            user_id = employee.get('user_id', False)
                            if not user_id:
                                non_user_ids += 1
                                error_employees += "\n" + hrbp.name_related + " - " + hrbp.code
                                
                        if non_user_ids != count_emp:
                            error_employees = ""
                    else:
                        group_name = 'Dept HR'
                        if next_state == 'cb':
                            group_name = "CB Working Record"
                        raise osv.except_osv('Validation Error !', "Don't have any employee belong to group %s "% group_name)
                    
            if error_employees:
                raise osv.except_osv('Validation Error !', 'The following employees do not have account domain: %s' % error_employees)
            
        return True
    
    #Return  states base on change_form_id.is_salary_adjustment and division_id_old and division_id_new
    def get_state_dicts(self, cr, uid, record_id, context=None):
        if record_id:
            record = self.browse(cr, uid, record_id, fields_process=['change_form_ids'])
            change_forms = record.change_form_ids
            if self.pool.get('vhr.working.record').is_change_form_transfer_department(cr, uid, change_forms, context):
                return STATES_TRANSFER_DEPARTMENT
            else:
                return STATES_NOT_TRANSFER_DEPARTMENT
        return []
    
    
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
    
    def is_special_case_for_change_form(self, cr, uid, change_form_ids, context=None):
        return self.pool.get('vhr.working.record').is_special_case_for_change_form(cr, uid, change_form_ids, context)
    
    #Action for workflow
    def action_next(self, cr, uid, ids, context=None):
        log.info('Change status to next state')
        if not context:
            context = {}
        if ids:
            record_id = ids[0]
            mcontext = context
            already_validate_user = self.is_person_already_validated(cr, uid, [record_id], mcontext)
            #if user A return to user B, then user B approve, prevent write in vhr.state.change with message :already validate by B.. 
            if context.get('call_from_execute', False):
                already_validate_user = False
                mcontext['call_from_execute'] = False
            if self.is_person_do_action(cr, uid, [record_id], mcontext) or already_validate_user:
                vals = {}
                record = self.read(cr, uid, record_id, ['state','is_required_attachment'])
                state = record.get('state', False)
                is_required_attachment = record.get('is_required_attachment',[])
                
                if state in ['finish','cancel']:
                    return True
                
                STATES = self.get_state_dicts(cr, uid, record_id, mcontext)
                list_state = [item[0] for item in STATES]
                
                if is_required_attachment:
          
                    attachment_ids = self.pool.get('ir.attachment').search(cr, uid, [('res_model','=','vhr.mass.movement'),
                                                                                     ('res_id','=',record_id)])
                    if not attachment_ids:
                        raise osv.except_osv('Validation Error !', 'You have to attach file before approval')
                    
                #Change something in changeform related to staff movement not finish, so movement change workflow
                index_new_state = 0
                if state not in list_state:
                    list_state_all = [item[0] for item in STATES_ALL]
                    index_state = list_state_all.index(state)
                    for new_state in list_state_all[index_state:]:
                        if new_state in list_state:
                            index_new_state = list_state.index(new_state)
                            break
                else:
                    index_new_state = list_state.index(state) + 1
                
                vals['state'] = list_state[index_new_state]
                vals['current_state'] = vals['state']
                vals['users_validated'] = str(uid)
                #Write old state to passed_state to remember where is previous pass state
                if not already_validate_user:
                    vals['passed_state'] = state
                self.check_exist_action_user_for_next_state(cr, uid, ids, vals['state'], mcontext)
                res = self.write(cr, uid, [record_id], vals, mcontext)
                
                if res:
                    if already_validate_user:
                            mcontext['ACTION_COMMENT'] = "already validate by: " + already_validate_user
                    list_dict_states = {item[0]: item[1] for item in STATES_ALL}
                    self.write_log_state_change(cr, uid, record_id, list_dict_states[state], list_dict_states[vals['state']], mcontext)
                    if vals['state'] not in ['cb','finish']:
                        mcontext['state'] = vals['state']
                        
                        self.action_next(cr, uid, ids, context=mcontext)
                        
                #TODO: open later
#                 self.send_mail(cr, uid, ids, state)
                return True
            
        return False
    
    def write_log_state_change(self, cr, uid, record_id, old_state, new_state, context=None):
        if not context:
            context = {}
        state_vals = {}
        state_vals['old_state'] = old_state
        state_vals['new_state'] = new_state
        state_vals['create_uid'] = uid
        state_vals['res_id'] = record_id
        state_vals['model'] = self._name
        if 'ACTION_COMMENT' in context:
            state_vals['comment'] = context['ACTION_COMMENT']
        self.pool.get('vhr.state.change').create(cr, uid, state_vals)
        return True
    
    def action_reject(self, cr, uid, ids, context=None):
        log.info('Change status to cancel state')
        if ids:
            record_id = ids[0]
            if self.is_person_do_action(cr, uid, [record_id], context):# and self.is_able_to_do_action_reject(cr, uid, [record_id], context)
                super(vhr_mass_movement, self).write(cr, uid, [record_id], {'state': 'cancel'}, context)
                return True
                #TODO: open later
#                 self.send_mail(cr, uid, ids, state)
        
        return False
    
    def action_return(self, cr, uid, ids, context=None):
        log.info('Change status to previous state')
        if not context:
            context = {}
        if ids:
            record_id = ids[0]
            if self.is_person_do_action(cr, uid, [record_id], context):
                vals = {}
                record = self.read(cr, uid, record_id, ['state','passed_state'])
                state = record.get('state', False)
                
                passed_state = filter(None, map(lambda x: x.strip(), record.get('passed_state','').split(',')))
                new_state = ''
                if passed_state:
                    new_state = passed_state[-1]
                else:
                    #For old data dont have data in passed_state, we can remove these code if data is empty
                    STATES = self.get_state_dicts(cr, uid, record_id, context)
                    list_state = [item[0] for item in STATES]
                    
                    index_new_state = 0
                    if state not in list_state:
                        list_state_all = [item[0] for item in STATES_ALL]
                        index_state = list_state_all.index(state)
                        for new_state in list_state_all[:index_state]:
                            if new_state in list_state:
                                index_new_state = list_state.index(new_state)
                    else:
                        index_new_state = list_state.index(state) - 1
                    
                    new_state = list_state[index_new_state]
                
                vals['state'] = new_state
                vals['current_state'] = vals['state']
                vals['users_validated'] = str(uid)
                vals['passed_state'] = new_state
                context['return_to_previous_state'] = True
                self.write(cr, uid, [record_id], vals, context)
#                 super(vhr_mass_movement, self).write(cr, uid, [record_id], vals, context)
                return True
                #TODO: open later
#                 self.send_mail(cr, uid, ids, state)
        
        return False
    
    def send_mail(self, cr, uid, record_id, state, new_state, context=None):
        if not context:
            context = {}
        working_pool = self.pool.get('vhr.working.record')
        context["search_all_employee"] = True
        context['model'] = 'vhr.mass.movement'
        if record_id and state and new_state:
            action_user = ''
            if context.get('action_user', False):
                action_user = context['action_user']
            else:
                user = self.pool.get('res.users').read(cr, uid, uid, ['login'])
                if user:
                    action_user = user.get('login','')
            
#             record = self.read(cr, uid, record_id, ['change_form_ids'])
#             change_form_ids = record.get('change_form_ids',[])
#             is_mixed = self.is_special_case_for_change_form(cr, uid, change_form_ids, context)
            
            mail_process = mail_process_of_mass_not_adjust_salary
            
            if mail_process and state in mail_process.keys():
                log.info("Send mail in Mass Movement from old state %s to new state %s"% (state, new_state))
                data = mail_process[state]
                is_have_process = False
                for mail_data in data:
                    if new_state == mail_data[0]:
                        is_have_process = True
                        mail_detail = mail_data[1]
                        vals = {'action_user':action_user, 'mass_id': record_id, 'reason': context.get('ACTION_COMMENT', False)}
                        list_group_mail_to = mail_detail['to']
                        
                        list_mail_to, list_mail_cc_from_group_mail_to = working_pool.get_email_to_send(cr, uid, record_id, list_group_mail_to, context)
                        mail_to = ';'.join(list_mail_to)
                        vals['email_to'] = mail_to
                        
                        if 'cc' in mail_detail:
                            list_group_mail_cc = mail_detail['cc']
                            
                            list_mail_cc, list_mail_cc_from_group_mail_cc = working_pool.get_email_to_send(cr, uid, record_id, list_group_mail_cc, context)
                            list_mail_cc += list_mail_cc_from_group_mail_cc + list_mail_cc_from_group_mail_to
                            list_mail_cc = list(set(list_mail_cc))
                            mail_cc = ';'.join(list_mail_cc)
                            vals['email_cc'] = mail_cc
                        
                        link_email = self.get_url(cr, uid, record_id, context)
                        vals['link_email'] = link_email
                        mcontext = {'action_from_email': mail_detail.get('action_from_email',''),'not_split_email':True}
                        self.pool.get('vhr.sm.email').send_email(cr, uid, mail_detail['mail_template'], vals, mcontext)
                
                if not is_have_process:
                    log.info("Mass movement don't have mail process from old state %s to new state %s "%(state, new_state))
            
        return True
    
    def get_url(self, cr, uid, res_id, context=None):
        if isinstance(res_id, list):
            res_id = res_id[0]
        model_data = self.pool.get('ir.model.data')
        action_id = model_data.xmlid_lookup(cr, uid, 'vhr_human_resource.action_vhr_mass_movement')[2]
        
        url = ''
        config_parameter = self.pool.get('ir.config_parameter')
        base_url = config_parameter.get_param(cr, uid, 'web.base.url') or ''
        if base_url:
            url = base_url
        url += '/web#id=%s&view_type=form&model=vhr.mass.movement&action=%s' % (res_id, action_id)
        return url


vhr_mass_movement()