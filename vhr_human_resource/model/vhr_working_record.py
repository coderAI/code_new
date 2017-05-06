# -*-coding:utf-8-*-
#LuanNG
import traceback
import logging
import time
import simplejson as json
from datetime import datetime
from dateutil.relativedelta import relativedelta
from lxml import etree
from openerp import SUPERUSER_ID

from openerp.osv import osv, fields
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from vhr_working_record_hr_admin_permission import fields_permission
from vhr_working_record_mail_template_process import mail_process_of_staff_movement
from hr_contract import translate_contract_to_wr_dict
from openerp.addons.vhr_common.model.vhr_common import vhr_common
from openerp.addons.audittrail  import audittrail

log = logging.getLogger(__name__)

STATES_ALL = [('draft','Draft'),
              ('new_hrbp','Waiting New HRBP'),
              ('dept_hr','Waiting HRD'),
              ('cb','Waiting C&B'),
              ('cb2','Waiting C&B 2'),
              ('finish','Finish'),
              ('cancel','Cancel'),
              ('reject','Reject')]

STATES_TRANSFER_DEPARTMENT =  [('draft','Draft'),
                               ('new_hrbp','Waiting New HRBP'),
                               ('dept_hr','Waiting HRD'),
                               ('cb','Waiting C&B'),
                               ('finish','Finish'),
                               ('cancel','Cancel')]

STATES_NOT_TRANSFER_DEPARTMENT =[('draft','Draft'),
                                 ('dept_hr','Waiting HRD'),
                                 ('cb','Waiting C&B'),
                                 ('finish','Finish'),
                                 ('cancel','Cancel')]

dict_fields_update =  [('work_for_company_id_old','work_for_company_id_new'), ('office_id_old','office_id_new'), ('division_id_old','division_id_new'),
                       ('department_id_old','department_id_new'), ('job_title_id_old','job_title_id_new'),('department_group_id_old','department_group_id_new'),
                       #('job_level_id_old','job_level_id_new'),
                       #('position_class_id_old','position_class_id_new'),
                       ('report_to_old','report_to_new'),('manager_id_old','manager_id_new'),('team_id_old','team_id_new'),
                      # ('approver_id_old','approver_id_new'),('mentor_id_old','mentor_id_new'),
                       ('salary_setting_id_old','salary_setting_id_new'),('seat_old','seat_new'),('ext_old','ext_new'),
                       #('work_email_old','work_email_new'),('mobile_phone_old','mobile_phone_new'),('work_phone_old','work_phone_new'),
                       ('pro_job_family_id_old','pro_job_family_id_new'),
                       ('pro_job_group_id_old','pro_job_group_id_new'),('pro_sub_group_id_old','pro_sub_group_id_new'),
                       ('pro_ranking_level_id_old','pro_ranking_level_id_new'),('pro_grade_id_old','pro_grade_id_new'),
                       #('mn_job_family_id_old','mn_job_family_id_new'),
                      # ('mn_job_group_id_old','mn_job_group_id_new'),('mn_sub_group_id_old','mn_sub_group_id_new'),
                      # ('mn_ranking_level_id_old','mn_ranking_level_id_new'),('mn_grade_id_old','mn_grade_id_new'),
                       ('ts_working_group_id_old','ts_working_group_id_new'),#('job_level_position_id_old','job_level_position_id_new'),
                        ('job_level_person_id_old','job_level_person_id_new'),('career_track_id_old','career_track_id_new')
                      ]

dict_fields = dict_fields_update + [
                                    #('ts_working_schedule_id_old','ts_working_schedule_id_new'),
                                     ('timesheet_id_old','timesheet_id_new'),
                                     ('gross_salary_old','gross_salary_new'),('basic_salary_old','basic_salary_new'),
                                     ('salary_percentage_old','salary_percentage_new'),#('general_allowance_old','general_allowance_new'),
                                     ('kpi_amount_old','kpi_amount_new'),('v_bonus_salary_old','v_bonus_salary_new')
                                     ]

SALARY_FIELDS = ['gross_salary_old','gross_salary_new',
                 'basic_salary_old','basic_salary_new',
#                  'general_allowance_old','general_allowance_new',
                 'salary_percentage_old','salary_percentage_new',
                 'v_bonus_salary_old','v_bonus_salary_new']

FIELDS_ONCHANGE = {'department_id_new': ['manager_id_new'],
                   'team_id_new': ['report_to_new'],
                   'job_title_id_new': ['pro_job_family_id_new','pro_job_group_id_new','pro_sub_group_id_new','job_level_id_new']
                   }

dict_salary_fields = {'gross_salary_new'      :'gross_salary_old',
                      'basic_salary_new'      :'basic_salary_old',
                      'kpi_amount_new'        :'kpi_amount_old',   
#                       'general_allowance_new' :'general_allowance_old',
                      'salary_percentage_new' :'salary_percentage_old',
                      'v_bonus_salary_new'    :'v_bonus_salary_old'
                      }


CT_OFFICIAL = 'OFFICIAl'
CT_PROBATION = 'PROBATION'
CT_CTV = 'CTV'
CT_DVCTV = 'DVCTV'

class vhr_working_record(osv.osv, vhr_common):
    _name = 'vhr.working.record'
    _description = 'VHR Working Record'
    
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
    
#     def is_old_division_leader(self, cr, uid, ids, context=None):
#         if ids:
#             record = self.browse(cr, uid, ids[0])
#             if record and record.division_id_old and record.division_id_old.manager_id\
#              and record.division_id_old.manager_id.user_id \
#               and uid == record.division_id_old.manager_id.user_id.id:
#                 return True
#         return False
    
    def is_old_hrbp(self, cr, uid, ids, context=None):
        hrbp_employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=',uid)])
        if ids and hrbp_employee_ids:
            department_of_hrbp_ids = self.get_department_of_hrbp(cr, uid, hrbp_employee_ids[0], context)
            if department_of_hrbp_ids:
                record = self.read(cr, uid, ids[0], ['department_id_old','employee_id'])
                if record and record.get('department_id_old', False) and record['department_id_old'][0] in department_of_hrbp_ids:
                    #Check if login employee have permission location
                    employee_id = record.get('employee_id', False) and record['employee_id'][0]
                    res, res_employee_ids = self.get_domain_based_on_permission_location(cr, uid, hrbp_employee_ids, context)
                    if res and employee_id not in res_employee_ids:
                        return False
                    
                    return True
        
        return False
    
    def is_new_hrbp(self, cr, uid, ids, context=None):
        hrbp_employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=',uid)])
        if ids and hrbp_employee_ids:
            department_of_hrbp_ids = self.get_department_of_hrbp(cr, uid, hrbp_employee_ids[0], context)
            if department_of_hrbp_ids:
                record = self.read(cr, uid, ids[0], ['department_id_new','employee_id'])
                if record and record.get('department_id_new', False) and record['department_id_new'][0] in department_of_hrbp_ids:
                    
                    #Check if login employee have permission location
                    employee_id = record.get('employee_id', False) and record['employee_id'][0]
                    res, res_employee_ids = self.get_domain_based_on_permission_location(cr, uid, hrbp_employee_ids, context)
                    if res and employee_id not in res_employee_ids:
                        return False
                    
                    return True
        
        return False
    
    def is_old_assist_hrbp(self, cr, uid, ids, context=None):
        hrbp_employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=',uid)])
        if ids and hrbp_employee_ids:
            department_of_hrbp_ids = self.get_department_of_ass_hrbp(cr, uid, hrbp_employee_ids[0], context)
            if department_of_hrbp_ids:
                record = self.read(cr, uid, ids[0], ['department_id_old','employee_id'])
                if record and record.get('department_id_old', False) and record['department_id_old'][0] in department_of_hrbp_ids:
                    #Check if login employee have permission location
                    employee_id = record.get('employee_id', False) and record['employee_id'][0]
                    res, res_employee_ids = self.get_domain_based_on_permission_location(cr, uid, hrbp_employee_ids, context)
                    if res and employee_id not in res_employee_ids:
                        return False
                    
                    return True
         
        return False
#     
#     def is_new_assist_hrbp(self, cr, uid, ids, context=None):
#         hrbp_employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=',uid)])
#         if ids and hrbp_employee_ids:
#             department_of_hrbp_ids = self.get_department_of_ass_hrbp(cr, uid, hrbp_employee_ids[0], context)
#             if department_of_hrbp_ids:
#                 record = self.read(cr, uid, ids[0], ['department_id_new'])
#                 if record and record.get('department_id_new', False) and record['department_id_new'][0] in department_of_hrbp_ids:
#                     return True
#         
#         return False
    
    def default_get(self, cr, uid, fields, context=None):
        """
        Using uid=SUPERUSER_ID if create indirectly because only allow to create request with cb, hrbp, assistant hrbp
        """
        if context is None:
            context = {}
        
        res = super(vhr_working_record, self).default_get(cr, uid, fields, context=context)
        
        if context.get('duplicate_active_id', False):
            columns =  self._columns
            fields = columns.keys()
            
            newres = self.copy_data(cr, uid, context['duplicate_active_id'], default = {'audit_log_ids': []})
            
            #Delete value of old-new field  from duplicate WR 
            for item in dict_fields:
                del newres[item[0]]
                del newres[item[1]]
                
            employee_id = newres['employee_id']
            
            requester_id = False
            employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=',uid)], context={"search_all_employee": True})
            if employee_ids:
                requester_id = employee_ids[0]
            
            if employee_id:
                employee = self.pool.get('hr.employee').read(cr, uid, employee_id, ['code'])
                newres['employee_code'] = employee.get('code','')
            
            if newres.get('contract_id',False):
                contract = self.pool.get('hr.contract').read(cr, uid, newres['contract_id'], ['date_start'])
                newres['contract_start_date'] = contract.get('date_start',False)

            newres.update(res)
            newres['employee_id'] = employee_id
            newres['requester_id'] = requester_id
            newres['effect_from'] = time.strftime(DEFAULT_SERVER_DATE_FORMAT)
            newres['users_validated'] = ''
            newres['is_change_employee_from_copy_data'] = True
            newres['is_change_company_from_copy_data'] = True
#             newres['is_change_from_contract'] = True
#             newres['is_change_team_from_contract'] = True
#             newres['is_change_effect_from_copy_data'] = True
            newres['termination_id'] = False
            newres['payroll_salary_id'] = False
            newres['ts_emp_timesheet_id'] = False
            newres['ts_ws_employee_id'] = False
            newres['state_log_ids'] = False
            newres['audit_log_ids'] = False
            newres['effect_to'] = False
            newres['change_form_ids'] = [[6,False, []]]
#             newres['nearest_working_record_id'] = context['duplicate_active_id']
            if newres.get('state', False):
                newres['state'] = 'draft'
                if context.get('record_type', False) != 'request':
                    newres['state'] = False
            return newres
                                
        #Create working record from termination
        if context.get('termination_id', False):
            termination = self.pool.get('vhr.termination.request')
            res_read = termination.read(cr, uid, context['termination_id'], ['date_end_working_approve','employee_id'])
            
            res.update({
                        'employee_id': res_read['employee_id'][0],
                        'effect_from': res_read['date_end_working_approve']
                        })
        
        #Do not get employee_id,effect_from,company_id from default_get of working record
#         elif res.get('contract_id', False) or context.get('contract_id',False):
#             contract_id = res.get('contract_id', context.get('contract_id', False))
#             hr_contract = self.pool.get('hr.contract')
#             res_read = hr_contract.read(cr, uid, contract_id, ['company_id','employee_id','date_start'])
#             res.update({
#                         'employee_id': res_read['employee_id'][0],
#                         'company_id': res_read['company_id'][0],
#                         'effect_from': res_read['date_start']
#                         })
        return res
    
    def _is_person_do_action(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if not ids:
            return True
        if not isinstance(ids, list):
            ids = [ids]
        if not context:
            context = {}
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
    
    def invisible_change_salary(self, cr, uid, ids, field_name, arg, context=None):
        '''
        Nếu chuyển phòng ban (change form có access_field là department_id_new)
          old Assistant, HRBP, DH ko  được xem thông tin lương
        '''
        res = {}
        if not isinstance(ids, list):
            ids = [ids]
        
        if not context:
            context = {}
            
        for record_id in ids:
            record = self.browse(cr, uid, record_id)
            
            department_new_id = record.department_id_new  and record.department_id_new.id or False
            department_new_code = record.department_id_new and record.department_id_new.code or ''
            
            department_old_id = record.department_id_old  and record.department_id_old.id or False
            department_old_code = record.department_id_old and record.department_id_old.code or ''
            
#             change_form_ids = [change_form.id for change_form in record.change_form_ids]
#             is_mixed = self.is_special_case_for_change_form(cr, uid, change_form_ids, context)
            is_mixed = self.is_change_form_transfer_department(cr, uid, record.change_form_ids, context)
            
            if is_mixed:
                invisible = self.set_invisible_change_salary(cr, uid, department_new_id, department_new_code, context)
            else:
                invisible = self.set_invisible_change_salary(cr, uid, department_old_id, department_old_code, context)
                if department_new_id != department_old_id and invisible:
                    invisible = self.set_invisible_change_salary(cr, uid, department_new_id, department_new_code, context)
                
            res[record_id] = invisible
                        
        return res
    
    def _count_attachment(self, cr, uid, ids, prop, unknow_none, context=None):
        ir_attachment = self.pool.get('ir.attachment')
        res = {}
        for item in ids:
            number = ir_attachment.search(cr, uid, [('res_id', '=', item), ('res_model', '=', self._name)], context=context, count=True)
            res[item] = number or 0
        return res
    
    def _get_is_special_change_form(self, cr, uid, ids, prop, unknow_none, context=None):
        res = {}
        
        code_list = self.get_code_change_form_new_to_company(cr, uid, context)
        
        special_form_ids = self.pool.get('vhr.change.form').search(cr, uid, [('code','in',code_list)])
            
        for record in self.read(cr, uid, ids, ['change_form_ids']):
            change_form_ids = record.get('change_form_ids',[])
            res[record['id']] = True if set(change_form_ids).intersection(set(special_form_ids)) else False
            
        return res
    
    def _get_is_invisible_data_when_transfer_department(self, cr, uid, ids, prop, unknow_none, context=None):
        """
        Invisible data with requester, old hrbp, old dept when have staff movement, working record transfer department
        """
        res = {}
        if not isinstance(ids, list):
            ids = [ids]
        
        employee_login_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=', uid)], context={'active_test':False})
        
        for record_id in ids:
            res[record_id] = False
            record = self.browse(cr, uid, record_id, )
            department_id = record.department_id_new and record.department_id_new.id or False
            
            is_transfer = self.is_change_form_transfer_department(cr, uid, record.change_form_ids, context)
            if is_transfer and department_id:
                
                #Dept head can see salary
                department = self.pool.get('hr.department').read(cr, uid, department_id, ['manager_id','hrbps','ass_hrbps'])
                manger_id = department.get('manager_id', False) and department['manager_id'][0]
                if manger_id in employee_login_ids:
                    continue
                
                #HRBP and Assistant of department can see salary
                hrbps = department.get('hrbps',[])
                ass_hrbps = department.get('ass_hrbps', [])
                
                hrbps += ass_hrbps
                if set(employee_login_ids).intersection(set(hrbps)):
                    continue
            
                #If user not in groups: c&b, HRD: dont allow to see salary
                groups = self.get_groups(cr, uid)
                if set(['vhr_cb_working_record','vhr_hr_dept_head','vhr_cnb_manager','vhr_cb_working_record_readonly']).intersection(set(groups)):
                    continue
                
                res[record_id] = True
        
        return res
    
     #Return list employee_ids belong groups
    def get_employee_ids_belong_to_group(self, cr, uid, group_xml_id, context={}):
        if not context:
            context= {}

        employee_ids = []
        if group_xml_id:
            model_data = self.pool.get('ir.model.data')
            model_ids = model_data.search(cr, uid, [('model','=','res.groups'),('name','=',group_xml_id)])
            if model_ids:
                model = model_data.read(cr, uid, model_ids[0], ['res_id'])
                group_id = model.get('res_id', False)
                if group_id:
                    
                    #Get user_id belong to group
                    sql = """
                            SELECT uid FROM res_groups_users_rel WHERE gid = %s
                          """
                    
                    cr.execute(sql%group_id)
                    user_ids = [group[0] for group in cr.fetchall()]
                    #Get list employee_id belong to users
                    context["search_all_employee"] = True
                    employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','in',user_ids)],0,None,None, context)
        
        return employee_ids
    
    def _check_waiting_for(self, cr, uid, ids, prop, unknow_none, context = None):
        if not context:
            context= {}
        
        context["search_all_employee"] = True
        context['active_test'] = False
        
        if uid:
            user = self.pool.get('res.users').read(cr, uid, uid, ['login'])
            login = user.get('login','')
            context['login'] = login
        
        res,emp_ids = self.get_login_users_waiting_for_action(cr, uid, ids, 'vhr.working.record', context)
        return res
    
    def _get_state(self, cr, uid, context):
        return STATES_ALL
    
    def _get_contract_start_date(self, cr, uid, ids, context=None):
        result = set()
        working_ids = self.pool.get('vhr.working.record').search(cr, uid, [('contract_id', 'in', ids)])
        for el in working_ids:
            result.add(el)
        return list(result)
    
    def _get_current_working_record(self, cr, uid, ids, context=None):
        return ids
    
    def _get_dept_complete_code(self, cr, uid, ids, field_names, unknow_none, context = None):
        res = {}
        if ids and field_names:
            records = self.browse(cr, uid, ids)
            for record in records:
                res[record.id] = {}
                department_id_old = record.department_id_old and record.department_id_old.id or False
                team_id_old       = record.team_id_old and record.team_id_old.id or False
                department_id_new = record.department_id_new and record.department_id_new.id or False
                team_id_new       = record.team_id_new and record.team_id_new.id or False
                
                dept_old_id = team_id_old or department_id_old
                dept_new_id = team_id_new or department_id_new
                
                if dept_old_id:
                    res[record.id]['dept_complete_code_old'] =  self.pool.get('hr.department').get_dept_code(cr, uid, dept_old_id)
                if dept_new_id:
                    res[record.id]['dept_complete_code_new'] =  self.pool.get('hr.department').get_dept_code(cr, uid, dept_new_id)
            
        return res
    
    def _update_dept_complete_code(self, cr, uid, ids, context=None):
        return ids
    
    def _is_able_to_create_request(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if not isinstance(ids, list):
            ids = [ids]
        
        for record_id in ids:
            res[record_id] = True
        return res
    
    def _is_change_form_adjust_salary(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if not context:
            context = {}
        for record in self.browse(cr, uid, ids, fields_process=['change_form_ids'],context=context):
            res[record.id] = False
            if record.change_form_ids:
                for change_form in record.change_form_ids:
                    if change_form.is_salary_adjustment:
                        res[record.id] = True
        return res
    
    def _get_data_from_change_form(self, cr, uid, ids, field_name, arg, context=None):
        """
        Nếu change form có luân chuyển phòng ban và điều chỉnh lương, 
          remove điều chỉnh lương ra khỏi change form name custom
        """
        res = {}
        
        config_parameter = self.pool.get('ir.config_parameter')
        code_change_salary = config_parameter.get_param(cr, uid, 'vhr_human_resource_change_form_code_adjust_salary') or ''
        code_change_salary_list = code_change_salary.split(',')
        
        for record in self.browse(cr, uid, ids, fields_process=['change_form_ids']):
            res[record.id] = {}
            fields_name = []
            change_form_name = []
            remove_data_for_custom_name = []
            is_unable_to_read_salary_adjust_form = False
            is_transfer_department = False
            if record.change_form_ids:
                for change_form in record.change_form_ids:
                    change_form_name.append(change_form.name or '')
                    access_field_ids = change_form.access_field_ids
                    if access_field_ids:
                        for field in access_field_ids:
                            fields_name.append(field.name or '')
                    
                    if not is_transfer_department:
                        access_field_ids = change_form.access_field_ids or []
                        field_ids = [field.id for field in access_field_ids]
                        field_transfer_ids = self.pool.get('ir.model.fields').search(cr, uid, [('id','in',field_ids),
                                                                                               ('name','=','department_id_new')])
                        if field_transfer_ids:
                            is_transfer_department = True
                        
                    if change_form.is_salary_adjustment:
                        remove_data_for_custom_name.append(change_form.name or '')
                            
                        if not is_unable_to_read_salary_adjust_form:
                            data = self.read(cr, uid, record.id, ['invisible_change_salary'])
                            if data.get('invisible_change_salary', False):
                                is_unable_to_read_salary_adjust_form = True
                        
                        
            fields_name = list(set(fields_name))
            res[record.id]['fields_affect_by_change_form'] = ', '.join(fields_name)
            res[record.id]['change_form_name'] = ' - '.join(change_form_name)
            
            #Remove dieu chinh luong in custom name for send email
            if remove_data_for_custom_name and is_transfer_department:
                change_form_name = [name for name in change_form_name if name not in remove_data_for_custom_name]
            res[record.id]['change_form_name_custom'] = ' - '.join(change_form_name)
            
            if is_unable_to_read_salary_adjust_form:
                res[record.id]['change_form_name'] = res[record.id]['change_form_name_custom']
        return res
    
    def is_change_salary_percentage_by_hand(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if not isinstance(ids, list):
            ids = [ids]
        
        for record_id in ids:
            res[record_id] = True
        
        return res
    
    def _is_change_data_from_copy_data(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if not isinstance(ids, list):
            ids = [ids]
        
        for record_id in ids:
            res[record_id] = False
        
        return res
    
    def _is_change_job_level_person(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if not isinstance(ids, list):
            ids = [ids]
        
        for record in self.read(cr, uid, ids, ['job_level_person_id_old','job_level_person_id_new']):
            res[record['id']] = False
            job_level_person_id_old = record.get('job_level_person_id_old', False) and record['job_level_person_id_old'][0]
            job_level_person_id_new = record.get('job_level_person_id_new', False) and record['job_level_person_id_new'][0]
            if job_level_person_id_new != job_level_person_id_old:
                res[record['id']] = True
        
        return res
    
    def _get_is_required_attachment(self, cr, uid, ids, field_name, arg, context=None):
        '''
        # Với SM có chứa đồng thời 2 loại: "Điều chỉnh lương" và "luân chuyển phòng ban" thì bước New HRBP bắt buộc phải attach email offline                      
          Bắt buộc attach file tại bước Submit
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
    
    def _get_contract_type(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        
        if not isinstance(ids, list):
            ids = [ids]
            
        for record in self.browse(cr, uid, ids, fields_process=['contract_id']):
            contract_type_group_id = record.contract_id and record.contract_id.contract_type_group_id\
                                                        and record.contract_id.contract_type_group_id.id or False
            
            res[record.id] = self.get_contract_type(cr, uid, contract_type_group_id, context)
        
        return res
    
    def is_action_user_search(self, cr, uid, obj, name, args, context=None):
        if not args:
            return []
        
        res = []
        domain = []
        employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=',uid)])
        if employee_ids:
            #search requester
            domain.extend(['&',('requester_id','in',employee_ids),('state','=','draft')])
        
            department_ids = self.get_department_of_hrbp(cr, uid, employee_ids[0], context)
            
            if department_ids:
                #State New HRBP
                if domain:
                    domain.insert(0,'|')
                domain.extend(['&',('state','=','new_hrbp'),('department_id_new','in',department_ids)])
            
            groups = self.get_groups(cr, uid, context={'get_correct_cb': True})
            if 'vhr_hr_dept_head' in groups:
                if domain:
                    domain.insert(0,'|')
                domain.append(('state','=','dept_hr'))
            
            if 'vhr_cb_working_record' in groups:
                if domain:
                    domain.insert(0,'|')
                domain.append(('state','=','cb'))
            
            group_cb2 = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_human_resource_group_cb2_working_record') or ''
            group_cb2 = group_cb2.split(',') or ''
            emp_cb2_ids = self.pool.get('hr.employee').search(cr, uid, [('login','in',group_cb2),
                                                                        ('user_id','=',uid)])
            
            if emp_cb2_ids:
                if domain:
                    domain.insert(0,'|')
                domain.append(('state','=','cb2'))
                
            
            res = self.search(cr, uid, domain, context=context)
        
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
    
    def _check_is_latest(self, cr, uid, ids, field_name, arg, context=None):
        """
        Get latest WR of an employee -company
        """
        res = {}
        if not isinstance(ids, list):
            ids = [ids]
        
        for record in self.read(cr, uid, ids, ['employee_id','company_id','state', 'effect_from']):
            res[record['id']] = False
            if record.get('state', False) in [False, 'finish']:
                employee_id = record.get('employee_id', False) and record['employee_id'][0]
                company_id = record.get('company_id', False) and record['company_id'][0]
                effect_from = record.get('effect_from', False)
                
                greater_ids = self.search(cr, uid, [('state','in',[False, 'finish']),
                                                    ('employee_id','=',employee_id),
                                                    ('company_id','=',company_id),
                                                    ('effect_from','>',effect_from)])
                if not greater_ids:
                    res[record['id']] = True
        
        return res
    
    def fnct_search_is_latest_wr(self, cr, uid, obj, name, args, context=None):
        if not args:
            return []
        
        res = []
        domain = []
            
        #Search working record have max effect_from of each employee-company and state in [False, finish]
        sql = """
                SELECT a.id FROM vhr_working_record a inner join 
                        (select employee_id, company_id, max(effect_from) effect_from from vhr_working_record 
                             where state='finish' or state is null group by employee_id, company_id) b
                    ON a.employee_id = b.employee_id and a.company_id = b.company_id and a.effect_from=b.effect_from
                WHERE a.state='finish' or a.state is null
              """
        
        cr.execute(sql)
        res = cr.fetchall()
        wr_ids = [item[0] for item in res]
        domain.extend(('id','in',wr_ids))
        
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
    
    
    def _get_keep_authority(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        
        for record in self.read(cr, uid, ids, ['keep_authority']):
            res[record['id']] = 'yes' if record.get('keep_authority', False) else 'no'
        
        return res
    
    _columns = {
        'name': fields.char('Name', size=128),
        'dept_complete_code_old' : fields.function(_get_dept_complete_code, type='char', string='Dept Complete Code', size=256, 
                                                                        multi="count_dept_code", store={'vhr.working.record':
                                                                            (_update_dept_complete_code, ['department_id_old','team_id_old'], 10)}),
        'dept_complete_code_new' : fields.function(_get_dept_complete_code, type='char', string='Dept Complete Code', size=256, 
                                                                        multi="count_dept_code", store={'vhr.working.record':
                                                                               (_update_dept_complete_code, ['department_id_new','team_id_new'], 10)}),
        'employee_id': fields.many2one('hr.employee', 'Employee', ondelete='restrict'),
        'requester_id': fields.many2one('hr.employee', 'Requester', ondelete='restrict'),
        'company_id': fields.many2one('res.company', 'Entity', ondelete='restrict'),
        'company_code': fields.related('company_id', 'code', type='char', string='Company'),
        'contract_id': fields.many2one('hr.contract', 'Contract', ondelete='restrict'),
        'contract_type': fields.function(_get_contract_type, type='char',string='Contract Type'),
        'contract_start_date': fields.related('contract_id', 'date_start', type='date', string="Contract effective date", 
                                              store={'hr.contract': (_get_contract_start_date, ['date_start'], 10),
                                                     'vhr.working.record': (_get_current_working_record, ['contract_id'], 10)}),

       #Link từ WR xử lý thôi việc nội bộ tới contract có change form chuyển đổi công ty
       #Khi đổi date start của Contract chuyển đổi công ty cần cập nhật lại effect_from của WR xử lý thôi việc nội bộ
        'contract_id_change_local_company': fields.many2one('hr.contract', 'Contract of New Company When Change Local Company', ondelete='restrict'),
        'effect_from': fields.date('Effective From'),
        'effect_to': fields.date('Effective To'),
        'decision_no': fields.char('Decision No', size=128),
#         'attached_file': fields.binary('Attached File'),
        'sign_date': fields.date('Signing Date'),
        'signer_id': fields.char('Signer',size=64),
        'signer_job_title_id': fields.char("Signer Job Title", size=128),
        'country_signer': fields.many2one('res.country', "Signer's Nationality"),
        'note': fields.text('Note'),
        
        'work_for_company_id_old': fields.many2one('res.company', 'Work for Company', ondelete='restrict'),
        'work_for_company_id_new': fields.many2one('res.company', 'Work for Company', ondelete='restrict'),
        
        'office_id_old': fields.many2one('vhr.office', 'Office', ondelete='restrict'),
        'division_id_old': fields.many2one('hr.department', 'Business Unit', domain=[('organization_class_id.level','=', '1')], ondelete='restrict'),
        'department_group_id_old': fields.many2one('hr.department', 'Department Group', domain=[('organization_class_id.level','=', '2')], ondelete='restrict'),    
        'department_id_old': fields.many2one('hr.department', 'Department', domain=[('organization_class_id.level','=', '3')], ondelete='restrict'),
        'team_id_old': fields.many2one('hr.department', 'Team', domain=[('organization_class_id.level','>=', '4')], ondelete='restrict'),
      
        'job_title_id_old': fields.many2one('vhr.job.title', 'Job Title', ondelete='restrict'),
        'job_level_id_old': fields.many2one('vhr.job.level', 'Level', ondelete='restrict'),
        
        'career_track_id_old': fields.many2one('vhr.dimension', 'Career Track', domain=[('dimension_type_id.code','=','CAREER_TRACK')], ondelete='restrict'),
        'career_track_id_new': fields.many2one('vhr.dimension', 'Career Track', domain=[('dimension_type_id.code','=','CAREER_TRACK')], ondelete='restrict'),

        #New job level
        'job_level_position_id_old': fields.many2one('vhr.job.level.new', 'Position Level', ondelete='restrict'),
        'job_level_person_id_old': fields.many2one('vhr.job.level.new', 'Person Level', ondelete='restrict'),
        
         #LuanNG: Remove this field in future version of vHRS
        'position_class_id_old': fields.many2one('vhr.position.class', 'Position Class', ondelete='restrict'),
        'report_to_old': fields.many2one('hr.employee', 'Reporting line', ondelete='restrict'),
        'approver_id_old': fields.many2one('hr.employee', 'Approver', ondelete='restrict'),
        'mentor_id_old': fields.many2one('hr.employee', 'Mentor', ondelete='restrict'),
        'manager_id_old': fields.many2one('hr.employee', 'Dept Head', ondelete='restrict'),
        
        'office_id_new': fields.many2one('vhr.office', 'Office', ondelete='restrict'),
        'division_id_new': fields.many2one('hr.department', 'Business Unit', domain=[('organization_class_id.level','=', '1')], ondelete='restrict'),
        'department_group_id_new': fields.many2one('hr.department', 'Department Group', domain=[('organization_class_id.level','=', '2')], ondelete='restrict'),    

        'department_id_new': fields.many2one('hr.department', 'Department', domain=[('organization_class_id.level','=', '3')], ondelete='restrict'),
        'team_id_new': fields.many2one('hr.department', 'Team', domain=[('organization_class_id.level','>=', '4')], ondelete='restrict'),
        'job_title_id_new': fields.many2one('vhr.job.title', 'Job Title', ondelete='restrict'),
        'job_level_id_new': fields.many2one('vhr.job.level', 'Level', ondelete='restrict'),
        
        #New job level
        'job_level_position_id_new': fields.many2one('vhr.job.level.new', 'Position Level', ondelete='restrict'),
        'job_level_person_id_new': fields.many2one('vhr.job.level.new', 'Person Level', ondelete='restrict'),
        'job_level_person_comment': fields.text('Level Comments'),
        
         #LuanNG: Remove this field in future version of vHRS
        'position_class_id_new': fields.many2one('vhr.position.class', 'Position Class (No more use)', ondelete='restrict'),
        'report_to_new': fields.many2one('hr.employee', 'Reporting line', ondelete='restrict'),
        #These fields: approver_id_new, mentor_id_new are no longer use, it should be remove in next version of Human Resource
        'approver_id_new': fields.many2one('hr.employee', 'Approver', ondelete='restrict'),
        'mentor_id_new': fields.many2one('hr.employee', 'Mentor', ondelete='restrict'),
        'manager_id_new': fields.many2one('hr.employee', 'Dept Head', ondelete='restrict'),
        
        'active': fields.boolean('Active'),
        
        'employee_code': fields.related('employee_id', 'code', type="char", string="Employee Code"),
        'salary_setting_id_old': fields.many2one('vhr.salary.setting', 'Payroll', ondelete='restrict'),
        'salary_setting_id_new': fields.many2one('vhr.salary.setting', 'Payroll', ondelete='restrict'),
        'seat_old': fields.char('Seat No', size=32),
        'ext_old': fields.char('Ext', size=32),
        'work_phone_old': fields.char('Office phone', size=32),
        'work_email_old': fields.char('Working email', size=32),
        'mobile_phone_old': fields.char('Cell phone', size=32),
        
        'seat_new': fields.char('Seat No', size=32),
        'ext_new': fields.char('Ext', size=32),
        'work_phone_new': fields.char('Office phone', size=32),
        'work_email_new': fields.char('Working email', size=32),
        'mobile_phone_new': fields.char('Cell phone', size=32),
        'keep_authority': fields.boolean('Keep current authority'),
        'gross_salary_old': fields.float('Gross Salary', digits=(12,0)),
        'basic_salary_old': fields.float('Basic Salary', digits=(12,0)),
        'kpi_amount_old': fields.float('KPI', digits=(12,0)),
        'general_allowance_old': fields.float('General Allowance', digits=(12,0)),
        'v_bonus_salary_old': fields.float('V_Bonus', digits=(12,0)),
        'salary_percentage_old': fields.float('% Basic Salary'),
#         'collaboration_salary_old': fields.float('Collaboration Salary'),
        
        'gross_salary_new': fields.float('Gross Salary', digits=(12,0)),
        'basic_salary_new': fields.float('Basic Salary', digits=(12,0)),
        'kpi_amount_new': fields.float('KPI', digits=(12,0)),
        'general_allowance_new': fields.float('General Allowance', digits=(12,0)),
        'v_bonus_salary_new': fields.float('V_Bonus', digits=(12,0)),
        'salary_percentage_new': fields.float('% Basic Salary'),
#         'collaboration_salary_new': fields.float('Collaboration Salary'),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                          domain=[('object_id.model', '=', _name),
                                                  ('field_id.name', 'not in',
                                                   ['write_date','audit_log_ids','write_uid','fields_affect_by_change_form','write_user'])]),
        
        #use this field to know where is the latest record for field permission, it must be function field -_-
#         'is_latest': fields.boolean('Is Latest'),
        'is_latest' : fields.function(_check_is_latest, type='boolean', string='Is Latest', readonly = 1, fnct_search=fnct_search_is_latest_wr),
        #use this field to allow edit employee, company, contract only when create new record
        'is_new': fields.boolean('is New'),
        
        #These field ony for view problem
        'is_change_employee_from_copy_data': fields.boolean('Is Change Emp From Copy'),
        'is_change_company_from_copy_data': fields.boolean('Is Change Company From Copy'),
        
        #When onchange contract, set is_change_from_contract = True to onchange division and onchange_department know that 
        #it doesn't need to clear data in department_id_new and manager_id_new
        'is_change_from_contract': fields.boolean('Is Change From Contract'),
        'is_change_team_from_contract': fields.boolean('Is Change Team From Contract'),
        'is_change_title_from_copy_data': fields.function(_is_change_data_from_copy_data, type='boolean', string='Is Change Title From Copy Data'),
        'is_change_job_level_person': fields.function(_is_change_job_level_person, type='boolean', string='Is Change Job Level Person'),
        'is_change_effect_from_copy_data': fields.boolean('Is Change Effect From Contract'),

        
        'state': fields.selection(_get_state, 'Status', readonly=True),
        'current_state': fields.selection(_get_state, 'Current Stage', readonly=True),
        'passed_state': fields.text('Passed State'),
        'is_person_do_action': fields.function(_is_person_do_action, type='boolean', string='Is Person Do Action'),
#         'is_able_to_do_action_reject': fields.function(_is_able_to_do_action_reject, type='boolean', string='Is Person Do Action Reject'),
        'state_log_ids': fields.one2many('vhr.state.change', 'res_id', 'History', domain=[('model', '=', _name)]),
        'waiting_for' : fields.function(_check_waiting_for, type='char', string='Waiting For', readonly = 1, multi='waiting_for'),
        'is_waiting_for_action' : fields.function(_check_waiting_for, type='boolean', string='Is Waiting For Approval', readonly = 1, multi='waiting_for', fnct_search=is_action_user_search),
        'termination_id': fields.many2one('vhr.termination.request','Terminate Request'),
        'is_change_contract_type': fields.related('termination_id','is_change_contract_type', type='boolean', string="Is Change Contract Type"),
        
        'pro_job_family_id_old': fields.many2one('vhr.job.family','Pro Job Family',ondelete='restrict'),
        'pro_job_group_id_old': fields.many2one('vhr.job.group','Pro Job Group',ondelete='restrict'),
        'pro_sub_group_id_old': fields.many2one('vhr.sub.group','Pro Sub Group',ondelete='restrict'),
        'pro_ranking_level_id_old': fields.many2one('vhr.ranking.level','Pro Level',ondelete='restrict'),
        'pro_grade_id_old': fields.many2one('vhr.grade','Pro Grade',ondelete='restrict'),
        
        'pro_job_family_id_new': fields.many2one('vhr.job.family','Pro Job Family',ondelete='restrict',domain=[('track_id.code','=', 'Professional')]),
        'pro_job_group_id_new': fields.many2one('vhr.job.group','Pro Job Group',ondelete='restrict'),
        'pro_sub_group_id_new': fields.many2one('vhr.sub.group','Pro Sub Group',ondelete='restrict'),
        'pro_ranking_level_id_new': fields.many2one('vhr.ranking.level','Pro Level',ondelete='restrict'),
        'pro_grade_id_new': fields.many2one('vhr.grade','Pro Grade',ondelete='restrict'),
        
        'mn_job_family_id_old': fields.many2one('vhr.job.family','Management Job Family',ondelete='restrict'),
        'mn_job_group_id_old': fields.many2one('vhr.job.group','Management Job Group',ondelete='restrict'),
        'mn_sub_group_id_old': fields.many2one('vhr.sub.group','Management Sub Group',ondelete='restrict'),
        'mn_ranking_level_id_old': fields.many2one('vhr.ranking.level','Management Level',ondelete='restrict'),
        'mn_grade_id_old': fields.many2one('vhr.grade','Management Grade',ondelete='restrict'),
        
        'mn_job_family_id_new': fields.many2one('vhr.job.family','Management Job Family',ondelete='restrict',domain=[('track_id.code','=', 'Management')]),
        'mn_job_group_id_new': fields.many2one('vhr.job.group','Management Job Group',ondelete='restrict'),
        'mn_sub_group_id_new': fields.many2one('vhr.sub.group','Management Sub Group',ondelete='restrict'),
        'mn_ranking_level_id_new': fields.many2one('vhr.ranking.level','Management Level',ondelete='restrict'),
        'mn_grade_id_new': fields.many2one('vhr.grade','Management Grade',ondelete='restrict'),
        
        'create_uid': fields.many2one('res.users', 'Create User'),
        'create_user': fields.related('create_uid', 'login', type="char", string="Create User"),
        'create_date': fields.date('Create Date'),
        
        'write_uid': fields.many2one('res.users', 'Update User', ondelete='restrict'),
        'write_user': fields.related('write_uid', 'login', type="char", string="Update User"),
        'write_date': fields.date('Update Date'),
        'users_validated': fields.text('User Validate'),
        'nearest_working_record_id': fields.many2one('vhr.working.record', 'Nearest Working Record'),
        'is_public': fields.boolean('Is Publish'),
        
        'change_form_ids':fields.many2many('vhr.change.form','working_record_change_form_rel','working_id','change_form_id','Change Form'),
        'invisible_change_salary': fields.function(invisible_change_salary, type='boolean', string='Invisible Change Salary Group'),
        'update_salary_in_create': fields.boolean('Update Salary in Create Function'),
        'update_mask_data_in_create': fields.boolean('Update Mask data in Create Function'),
        'is_able_to_create_request': fields.function(_is_able_to_create_request, type='boolean', string='Is Able To Create Request'),
        'is_change_form_adjust_salary': fields.function(_is_change_form_adjust_salary, type='boolean', string='Is Change Form Adjust Salary'),
        'change_form_name': fields.function(_get_data_from_change_form, type='text', string='Change Form',multi='get_data'),
        'change_form_name_custom': fields.function(_get_data_from_change_form, type='text', string='Change Form Name',multi='get_data'),
        'fields_affect_by_change_form': fields.function(_get_data_from_change_form, type='text', string="Fields Affect By Change Form",multi='get_data'),
        #Những field được lưu trong fields_not_update phải có dữ liệu bằng dữ liêu old, field fields_not_update dùng để tránh cheat với change_form_ids
        'fields_not_update': fields.text('Fields Not Update'),
        
        'is_change_salary_percentage_by_hand': fields.function(is_change_salary_percentage_by_hand, type='boolean', string='Is Change Salary Percentage By Hand'),
        'is_change_gross_salary_by_hand': fields.function(is_change_salary_percentage_by_hand, type='boolean', string='Is Change Gross Salary By Hand'),
        'is_change_basic_salary_by_hand': fields.function(is_change_salary_percentage_by_hand, type='boolean', string='Is Change Basic Salary By Hand'),
        'attachment_ids': fields.one2many('ir.attachment', 'res_id', 'Attachment', domain=[('res_model', '=', _name)]),
        'is_required_attachment': fields.function(_get_is_required_attachment, type='boolean', string="Is Require Attachment"),
        
        'attachment_count': fields.function(_count_attachment, type='integer', string='Attachments'),
        'is_special_change_form': fields.function(_get_is_special_change_form, type='boolean', string="Is Special Change Form"),
        'is_invisible_data_when_transfer_department': fields.function(_get_is_invisible_data_when_transfer_department, type='boolean', string="Is Invisible Data When Transfer Department"),
        'keep_authority_fcnt': fields.function(_get_keep_authority,type='selection', selection=[('yes', 'Yes'), ('no', 'No')], 
                                               string='Keep current authority'),

    }
    

    _order = "effect_from desc, id desc"
    
    def _get_requester_id(self, cr, uid, context=None):
        employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=',uid)], context={"search_all_employee": True})
        if employee_ids:
            return employee_ids[0]

        return False
    
    def _get_is_able_to_create_request(self, cr, uid, context=None):
        return self.check_is_able_to_create_request(cr, uid, context)
    
    _defaults = {
        'active': False,
        'keep_authority': True,
        'is_new': True,
        'is_public': True,
        'is_person_do_action': True,
        'requester_id': _get_requester_id,
        'update_salary_in_create': False, 
        'update_mask_data_in_create': False,
        'is_able_to_create_request': _get_is_able_to_create_request,
        'passed_state': '',
        'is_change_salary_percentage_by_hand': True,
        'is_change_gross_salary_by_hand': True,
        'is_change_basic_salary_by_hand': True,
        'is_invisible_data_when_transfer_department': False
    }
    
    def check_is_able_to_create_request(self, cr, uid, context=None):
        """
        Only allow 'vhr_assistant_to_hrbp','vhr_hrbp','vhr_cb_working_record' to create request, multi request, mass request
        """
        if not context:
            context = {}
        
        name = context.get('title_request', 'Request')
        groups = self.get_groups(cr, uid)
        if uid == SUPERUSER_ID:
            return True
        if context.get('record_type', False) == 'request' and not set(['vhr_assistant_to_hrbp','vhr_hrbp','vhr_cb_working_record']).intersection(groups):
            raise osv.except_osv('Warning !', "You have to belong to one of groups Assistant to HRBP/ HRBP/ C&B Working Record to create a %s" % name)
        
#         if context.get('record_type', False) == 'request':
#             raise osv.except_osv('Warning !','Currently, you can not create staff movement in vHRS. Contact Openerp Team for support !')
        return True
        
    #Return  states base on change_form_id.is_salary_adjustment 
    def get_state_dicts(self, cr, uid, record_id, context=None):
        if record_id:
            record = self.browse(cr, uid, record_id, fields_process=['change_form_ids'])
            change_forms = record.change_form_ids
            return self.get_state_dicts_for_movement(cr, uid, change_forms, context)
        return []
    
    def is_change_form_about_salary(self, cr, uid, change_forms, context=None):
        if change_forms:
            for change_form in change_forms:
                if change_form.is_salary_adjustment:
                    return True
        return False
    
    def is_change_form_transfer_department(self, cr, uid, change_forms, context=None):
        """
        Have change form allow to change department_id_new
        """
        if change_forms:
            field_obj = self.pool.get('ir.model.fields')
            for change_form in change_forms:
                field_ids_change_department = []
                field_ids = [field.id for field in change_form.access_field_ids]
                if field_ids:
                    field_ids_change_department = field_obj.search(cr, uid, [('id','in',field_ids),
                                                                             ('name','=','department_id_new')])
                if field_ids_change_department:
                    return True
        return False
    
    
    def get_state_dicts_for_movement(self, cr, uid, change_forms, context=None):
        if change_forms:
            if self.is_change_form_transfer_department(cr, uid, change_forms, context):
                return STATES_TRANSFER_DEPARTMENT
            else:
                return STATES_NOT_TRANSFER_DEPARTMENT
        return []
    
    
    def get_requester_name_and_id(self, cr, uid, record_id, context=None):
        if not context:
            context = {}
        
        model_pool = self.pool.get('vhr.working.record')
        if context.get('model'):
            model_pool = self.pool.get(context['model'])
            
        requester_name = ''
        requester_id = False
        requester_mail = ''
        if record_id:
            meta_datas = model_pool.perm_read(cr, SUPERUSER_ID, [record_id], context)
            user_id =  meta_datas and meta_datas[0] and meta_datas[0].get('create_uid', False) and meta_datas [0]['create_uid'][0] or False
            if user_id:
                context['search_all_employee'] = True
                employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', user_id)], 0, None, None, context)
                if employee_ids:
                    employee = self.pool.get('hr.employee').read(cr, uid, employee_ids[0], ['login','work_email'])
                    requester_name =employee.get('login', '')
                    requester_id = employee.get('id', False)
                    requester_mail = employee.get('work_email','')
        
        return requester_name, requester_id, requester_mail
    
    def get_old_dept_head_name_and_id(self, cr, uid, record_id, context=None):
        if not context:
            context={}
        
        model_pool = self.pool.get('vhr.working.record')
        if context.get('model'):
            model_pool = self.pool.get(context['model'])
        dept_head_name = ''
        dept_head_id = False
        dept_head_mail = ''
        if record_id:
            record = model_pool.browse(cr, uid, record_id, fields_process=['department_id_old'])
            dept_head_name = record.department_id_old and record.department_id_old.manager_id and record.department_id_old.manager_id.login or ''
            dept_head_id = record.department_id_old and record.department_id_old.manager_id and record.department_id_old.manager_id.id
            dept_head_mail = record.department_id_old and record.department_id_old.manager_id and record.department_id_old.manager_id.work_email or ''
            
        return dept_head_name, dept_head_id, dept_head_mail
    
    def get_new_dept_head_name_and_id(self, cr, uid, record_id, context=None):
        if not context:
            context={}
        
        model_pool = self.pool.get('vhr.working.record')
        if context.get('model'):
            model_pool = self.pool.get(context['model'])
        dept_head_name = ''
        dept_head_id = False
        dept_head_mail = ''
        if record_id:
            record = model_pool.browse(cr, uid, record_id, fields_process=['department_id_new'])
            dept_head_name = record.department_id_new and record.department_id_new.manager_id and record.department_id_new.manager_id.login or ''
            dept_head_id = record.department_id_new and record.department_id_new.manager_id and record.department_id_new.manager_id.id
            dept_head_mail = record.department_id_new and record.department_id_new.manager_id and record.department_id_new.manager_id.work_email or ''
            
        return dept_head_name, dept_head_id, dept_head_mail
    
    def get_employee_name_and_id(self, cr, uid, record_id, context=None):
        if not context:
            context={}
        
        model_pool = self.pool.get('vhr.working.record')
        if context.get('model'):
            model_pool = self.pool.get(context['model'])
        emp_name = ''
        emp_id = False
        emp_mail = ''
        if record_id:
            record = model_pool.browse(cr, uid, record_id, fields_process=['employee_id'])
            emp_name = record.employee_id and record.employee_id.login or ''
            emp_id = record.employee_id and record.employee_id.id
            emp_mail = record.employee_id and record.employee_id.work_email or ''
            
        return emp_name, emp_id, emp_mail
    
    def get_old_hrbp_name_and_id(self, cr, uid, record_id, context=None):
        if not context:
            context = {}
        
        model_pool = self.pool.get('vhr.working.record')
        if context.get('model'):
            model_pool = self.pool.get(context['model'])
        hrbp_names = []
        hrbp_ids = []
        hrbp_mails = []
        if record_id:
            record = model_pool.read(cr, uid, record_id, ['department_id_old','employee_id'])
            employee_id = record.get('employee_id',False) and record['employee_id'][0] or False
            department_id = record.get('department_id_old',False) and record['department_id_old'][0] or False
            if department_id:
                
                department = self.pool.get('hr.department').browse(cr, uid, department_id, fields_process=['hrbps'])
                employees = department.hrbps
                for employee in employees:
                    #Check if have permission location
                    if employee_id:
                        res, res_employee_ids = self.get_domain_based_on_permission_location(cr, uid, [employee.id], context)
                        if res and employee_id not in res_employee_ids:
                            continue
                    
                    hrbp_ids.append(employee.id)
                    hrbp_names.append(employee.login)
                    hrbp_mails.append(employee.work_email)
                    
        return hrbp_names, hrbp_ids, hrbp_mails
    
    def get_old_assist_hrbp_name_and_id(self, cr, uid, record_id, context=None):
        if not context:
            context = {}
        
        model_pool = self.pool.get('vhr.working.record')
        if context.get('model'):
            model_pool = self.pool.get(context['model']) 
        hrbp_names = []
        hrbp_ids = []
        hrbp_mails = []
        if record_id:
            record = model_pool.read(cr, uid, record_id, ['department_id_old','employee_id'])
            employee_id = record.get('employee_id',False) and record['employee_id'][0] or False
            department_id = record.get('department_id_old',False) and record['department_id_old'][0] or False
            if department_id:
                department = self.pool.get('hr.department').browse(cr, uid, department_id, fields_process=['ass_hrbps'])
                employees = department.ass_hrbps
                for employee in employees:
                    #Check if have permission location
                    if employee_id:
                        res, res_employee_ids = self.get_domain_based_on_permission_location(cr, uid, [employee.id], context)
                        if res and employee_id not in res_employee_ids:
                            continue
                    
                    hrbp_ids.append(employee.id)
                    hrbp_names.append(employee.login)
                    hrbp_mails.append(employee.work_email)
                    
        return hrbp_names, hrbp_ids, hrbp_mails
    
    def get_new_assist_hrbp_name_and_id(self, cr, uid, record_id, context=None):
        if not context:
            context = {}
        
        model_pool = self.pool.get('vhr.working.record')
        if context.get('model'):
            model_pool = self.pool.get(context['model']) 
        hrbp_names = []
        hrbp_ids = []
        hrbp_mails = []
        if record_id:
            record = model_pool.read(cr, uid, record_id, ['department_id_new','employee_id'])
            employee_id = record.get('employee_id',False) and record['employee_id'][0] or False
            department_id = record.get('department_id_new',False) and record['department_id_new'][0] or False
            if department_id:
                department = self.pool.get('hr.department').browse(cr, uid, department_id, fields_process=['ass_hrbps'])
                employees = department.ass_hrbps
                for employee in employees:
                    #Check if have permission location
                    if employee_id:
                        res, res_employee_ids = self.get_domain_based_on_permission_location(cr, uid, [employee.id], context)
                        if res and employee_id not in res_employee_ids:
                            continue
                    
                    hrbp_ids.append(employee.id)
                    hrbp_names.append(employee.login)
                    hrbp_mails.append(employee.work_email)
                    
        return hrbp_names, hrbp_ids, hrbp_mails
    
    def get_new_hrbp_name_and_id(self, cr, uid, record_id, context=None):
        if not context:
            context = {}
        
        model_pool = self.pool.get('vhr.working.record')
        if context.get('model'):
            model_pool = self.pool.get(context['model']) 
        hrbp_names = []
        hrbp_ids = []
        hrbp_mails = []
        if record_id:
            record = model_pool.read(cr, uid, record_id, ['department_id_new','employee_id'])
            employee_id = record.get('employee_id',False) and record['employee_id'][0] or False
            department_id = record.get('department_id_new',False) and record['department_id_new'][0] or False
            if department_id:
                department = self.pool.get('hr.department').browse(cr, uid, department_id, fields_process=['hrbps'])
                employees = department.hrbps
                for employee in employees:
                    #Check if have permission location
                    if employee_id:
                        res, res_employee_ids = self.get_domain_based_on_permission_location(cr, uid, [employee.id], context)
                        if res and employee_id not in res_employee_ids:
                            continue
                    
                    hrbp_ids.append(employee.id)
                    hrbp_names.append(employee.login)
                    hrbp_mails.append(employee.work_email)
                    
        return hrbp_names, hrbp_ids, hrbp_mails
    
    def get_cb_name_and_id(self, cr, uid, context=None):
        if not context:
            context = {}
        names = []
        emp_ids = []
        mails = []
        employee_ids = self.pool.get('vhr.working.record').get_employee_ids_belong_to_group(cr, uid, 'vhr_cb_working_record', context)
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
    
    def get_dept_hr_name_and_id(self, cr, uid, context=None):
        names = []
        emp_ids = []
        mails = []
        employee_ids = self.pool.get('vhr.working.record').get_employee_ids_belong_to_group(cr, uid, 'vhr_hr_dept_head', context)
        if employee_ids:
            employees = self.pool.get('hr.employee').read(cr, uid, employee_ids, ['login','work_email'])
            for employee in employees:
                emp_ids.append(employee.get('id',False))
                names.append(employee.get('login',''))
                mails.append(employee.get('work_email',''))
        
        return names, emp_ids, mails
    
    def get_af_executor_name_and_id(self, cr, uid, record_id, context=None):
        names = []
        emp_ids = []
        mails = []
        try:
            record = self.browse(cr, uid, record_id)
            company_id = record.company_id and record.company_id.id or False
            city_id = record.office_id_new and record.office_id_new.city_id and record.office_id_new.city_id.id or False
            af_pool = self.pool.get('vhr.af.executor')
            domain = [('company_id','=',company_id),
                      ('active','=', True)]
            
            s_domain = domain[:]
            s_domain.append(('city_id','=',city_id))
            af_ids = af_pool.search(cr, uid, s_domain)
            if not af_ids:
                af_ids = af_pool.search(cr, uid, domain)
                if not af_ids:
                    af_ids = af_pool.search(cr, uid, [('active','=', True),
                                                      ('company_id','=', False)])
            
            if af_ids:
                af = af_pool.browse(cr, uid, af_ids[0], fields_process=['employee_id'])
                emp_ids.append(af.employee_id and af.employee_id.id or False)
                names.append(af.employee_id and af.employee_id.login or '')
                mails.append(af.employee_id and af.employee_id.work_email or '')
        
        except Exception as e:
            pass
        
        return names, emp_ids, mails
        
            
    #Return list login user(in string) can do action in record
    def get_login_users_waiting_for_action(self, cr, uid, ids, object, context=None):
        """
        This function run correctly for working record and mass movement because these two objects are similar and use this function for same purpose
        Object must have fields: division_id_old, department_id_old, department_id_new
        """
        if not context:
            context = {}
            
        res = {}
        result_ids = {}
        if ids and object:
            object_pool = self.pool.get(object)
            context['model'] = object
            login = context.get('login',False)
            for item in object_pool.browse(cr, uid, ids):
                vals = ''
                vals_id = []
                state = item.state
                record_id = item.id
                employee_id = False
                if object == 'vhr.working.record':
                    employee_id = item.employee_id and item.employee_id.id or False
                if context.get('state_for_get_login_users',False):
                    state = context['state_for_get_login_users']
                if state == 'draft':
                    requester_name, requester_id, mail = self.get_requester_name_and_id(cr, uid, record_id, context)
                    if requester_name and requester_id:
                        vals = '%s' % (requester_name)
                        vals_id.append(requester_id)
                    else:
                        vals = 'None'
                
                elif state == 'new_hrbp':
                    hrbp_names, hrbp_ids, mail = self.get_new_hrbp_name_and_id(cr, uid, record_id, context)
                    vals_id.extend(hrbp_ids)
                    vals = '; '.join(hrbp_names)
                    
                elif state == 'dept_hr':
                    names, emp_ids, mail = self.get_dept_hr_name_and_id(cr, uid, context)
                    vals_id.extend(emp_ids)
                    vals = '; '.join(names)
#                     
                elif state == 'cb':
                    context['active_employee_id'] = employee_id
                    names, emp_ids, mail = self.get_cb_name_and_id(cr, uid, context)
                    names = list(set(names))
                    
                    vals_id.extend(emp_ids)
                    vals = '; '.join(names)
                
                elif state == 'cb2':
                    group_cb2 = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_human_resource_group_cb2_working_record') or ''
                    group_cb2 = group_cb2.split(',') or ''
                    
                    emp_cb2_ids = self.pool.get('hr.employee').search(cr, uid, [('login','in',group_cb2)])
                    
                    vals_id.extend(emp_cb2_ids)
                    vals = '; '.join(group_cb2)
                
                res[item.id] = {'is_waiting_for_action': False}
                res[item.id]['waiting_for'] = vals
                if login in vals:
                    res[item.id]['is_waiting_for_action'] = True
                
                result_ids[item.id] = vals_id
        
        return res,result_ids
    
    def get_list_employee_can_use(self, cr, uid, context=None):
        """
        Return: list employee_ids, login user can choose to create Working Record
        Will return 'all_employees' if don't filter
        """
        employee_ids = []
        groups = self.get_groups(cr, uid)
        login_employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=',uid)])
        #Read all record if belong to these group
        if set(['hrs_group_system','vhr_cb_working_record','vhr_cnb_manager','vhr_hr_dept_head','vhr_af_admin']).intersection(set(groups)):
            domain, filter_employee_ids = self.get_domain_based_on_permission_location(cr, uid, login_employee_ids, context)
            if domain:
                return filter_employee_ids
            return 'all_employees'
        
        #Thay nhung record co employee_id thuoc ve department ma user la HRBP/ assistant HRBP
        elif set(['vhr_hrbp','vhr_assistant_to_hrbp']).intersection(set(groups)) and login_employee_ids:
            department_hrbp = self.get_department_of_hrbp(cr, uid, login_employee_ids[0], context)
            department_ass_hrbp = self.get_department_of_ass_hrbp(cr, uid, login_employee_ids[0], context)
            department_ids = department_hrbp + department_ass_hrbp
            
            employee_ids_hrbp = self.pool.get('hr.employee').search(cr, uid, [('department_id','in',department_ids)])
            employee_ids.extend(employee_ids_hrbp)
        
        if login_employee_ids:
            employee_ids_dept_admin = self.get_list_employees_of_dept_admin(cr, uid, login_employee_ids[0], context)
            employee_ids.extend(employee_ids_dept_admin)
            
            #Filter list contract based on permisison location
            domain, filter_employee_ids = self.get_domain_based_on_permission_location(cr, uid, login_employee_ids, context)
            if domain:
                employee_ids = list( set(employee_ids).intersection( set(filter_employee_ids) ) )
        
        return employee_ids
    
    #Cannot create record which effect_from overlap with date range effect_from -effect_to of record with same employee_id, company_id:
    def check_overlap_date(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        if ids:
            working_info = self.browse(cr, uid, ids[0], context)
            employee_id = working_info.employee_id and working_info.employee_id.id or False
            company_id = working_info.company_id and working_info.company_id.id or False
            effect_from = working_info.effect_from
            effect_to = working_info.effect_to or False
            
            if employee_id and company_id:
                args = [('employee_id', '=', employee_id), 
                        ('company_id', '=', company_id),
                        ('state','in',[False,'finish']),
                        '|', ('active','=', False),
                             ('active','=', True)]
                
                #When create or write effect_from of staff movement, only check effect_from of movement with effect_from of other WR
                #(because when create in middle then effect_from of staff must different with effect_from of other)
                if context.get('state', False) not in [False,'finish']:
                    args.insert(0,('effect_from','=',effect_from))
                    working_ids = self.search(cr, uid, args, order='effect_from desc')
                    working_ids = [x for x in working_ids if x not in ids]
                    if working_ids:
                        employee_name = working_info.employee_id and working_info.employee_id.code or ''
                        company_name = working_info.company_id and working_info.company_id.name_en or ''
                        raise osv.except_osv('Validation Error !', 'The effective duration in Working Records of employee "%s" at "%s" is overlapped. Please check again '%(employee_name, company_name))

                else:
                    working_ids = self.search(cr, uid, args)
                    if not working_ids:
                        return True
                    
                    not_overlap_args = [('effect_to', '<', effect_from)] + args
                    if effect_to:
                        not_overlap_args.insert(0,'|')
                        not_overlap_args.insert(1,('effect_from', '>', effect_to))
                    
#                     not_overlap_args = ['|',('effect_from', '>', effect_to),('effect_to', '<', effect_from)] + args
                    not_overlap_working_ids = self.search(cr, uid, not_overlap_args)
                    #Record not overlap is the record link to employee
                    if len(working_ids) == len(not_overlap_working_ids):
                        return True
                    else:
                        #Get records from working_ids not in not_overlap_working_ids
                        overlap_ids = [x for x in working_ids if x not in not_overlap_working_ids]
                        #Get records from working_ids are not working_id
                        overlap_ids = [x for x in overlap_ids if x not in ids]
                        if overlap_ids:
                            employee_name = working_info.employee_id and working_info.employee_id.code or ''
                            company_name = working_info.company_id and working_info.company_id.name_en or ''
                            raise osv.except_osv('Validation Error !', 'The effective duration in Working Records of employee "%s" at "%s" is overlapped. Please check again '%(employee_name, company_name))

        return True
    
        
    #Return True if need to invisible Group Change Salary
    #With dept_code in restrict_dept_code_list, only c&b manager can see change salary
    def set_invisible_change_salary(self, cr, uid, department_id, dept_code, context=None):
        '''
           Mass movement call this function
        '''
        if not context:
            context = {}
        if dept_code and department_id:
            config_parameter = self.pool.get('ir.config_parameter')
            restrict_dept_code = config_parameter.get_param(cr, uid, 'vhr_human_resource_dept_for_restrict_cb_manager_see_salary_in_working_record') or ''
            restrict_dept_code_list = restrict_dept_code.split(',')
            if dept_code in restrict_dept_code_list and 'vhr_cnb_manager' not in self.get_groups(cr, uid):
                return True
            
            employee_login_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=', uid)], context={'active_test':False})
            
            #Dept head can see salary
            department = self.pool.get('hr.department').read(cr, uid, department_id, ['manager_id','hrbps','ass_hrbps'])
            manger_id = department.get('manager_id', False) and department['manager_id'][0]
            if manger_id in employee_login_ids:
                return False
            
            #HRBP and Assistant of department can see salary
            hrbps = department.get('hrbps',[])
            ass_hrbps = department.get('ass_hrbps', [])
            
            hrbps += ass_hrbps
            if set(employee_login_ids).intersection(set(hrbps)):
                return False
        
        #If user not in groups: c&b, HRD: dont allow to see salary
        groups = self.get_groups(cr, uid)
        if not set(['vhr_cb_working_record','vhr_hr_dept_head','vhr_cnb_manager','vhr_cb_working_record_readonly']).intersection(set(groups)):
            return True
        
        return False
    
    def onchange_keep_authority_fcnt(self, cr, uid, ids, keep_authority_fcnt, context=None):
        res = {}
        
        res['keep_authority'] = True if keep_authority_fcnt =='yes' else False
        
        return {'value': res}
        
    def onchange_employee_id(self, cr, uid, ids, employee_id, old_company_id, is_change_employee_from_copy_data, context=None):
        if context is None:
            context={}
        if context.get('default_contract_id') or context.get('termination_id',False) or is_change_employee_from_copy_data:
            return {'value': {'is_change_employee_from_copy_data': False}}
        res = {'contract_id': False,
               'effect_from': False,
               'employee_code': False,
               }
        domain = {'company_id': [('id', 'in', [])] }
        if employee_id:
            employee = self.pool.get('hr.employee').browse(cr, uid, employee_id, fields_process=['code','department_id'])
            
            department_id = employee.department_id and employee.department_id.id
            department_code = employee.department_id and employee.department_id.code or ''
            
            res['invisible_change_salary'] = self.set_invisible_change_salary(cr, uid, department_id, department_code, context)
            res['update_salary_in_create'] = res['invisible_change_salary']
            
            res['update_mask_data_in_create'] = True
            
            employee_code = employee.code or ''
            res['employee_code'] = employee_code
            res['company_id'] = False
#             company_id, company_ids = self.get_company_ids(cr, uid, employee_id)
#             domain['company_id'] = [('id', 'in', company_ids)]
#             if old_company_id != company_id:
#                 res['company_id'] = company_id
        return {'value': res, 'domain': domain}
    
    def onchange_change_form_ids(self, cr, uid, ids, change_form_ids, gross_salary_old, salary_percentage_old, basic_salary_old, 
                                 kpi_amount_old, general_allowance_old, v_bonus_salary_old, fields_affect_by_change_form, fields_not_update, context=None):
        if not context:
            context = {}
        res = {'is_change_form_adjust_salary': False, 'gross_salary_new': gross_salary_old,'salary_percentage_new': salary_percentage_old,
               'basic_salary_new': basic_salary_old,'kpi_amount_new':kpi_amount_old,'general_allowance_new':general_allowance_old,
               'v_bonus_salary_new': v_bonus_salary_old, 'fields_affect_by_change_form': ''}
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
            
        fields_not_update = fields_not_update and fields_not_update.split(',') or []
        if fields_affect_by_change_form:
            old_fields_affect = fields_affect_by_change_form.split(',')
            old_fields_affect = [item.strip() for item in old_fields_affect]
            fail_fields = [item for item in old_fields_affect if item not in fields_name]
            if fail_fields:
                fields_not_update.extend(fail_fields)
        
        fields_not_update = [item for item in fields_not_update if item not in fields_name]
        fields_not_update = ','.join(fields_not_update)
        res['fields_not_update'] = fields_not_update
                    
        fields_name = list(set(fields_name))
        if fields_affect_by_change_form and res.get('gross_salary_new', False):
            old_fields_affect = fields_affect_by_change_form.split(',')
            old_fields_affect = [item.strip() for item in old_fields_affect]
            if 'basic_salary_new' in old_fields_affect and 'basic_salary_new' not in fields_name \
             and basic_salary_old != context.get('basic_salary_new',0):
                
                res['is_change_basic_salary_by_hand'] = False
            if 'gross_salary_new' in old_fields_affect and 'gross_salary_new' not in fields_name \
             and gross_salary_old != context.get('gross_salary_new',0):
                
                res['is_change_gross_salary_by_hand'] = False
            if 'salary_percentage_new' in old_fields_affect and 'salary_percentage_new' not in fields_name \
             and salary_percentage_old != context.get('salary_percentage_new',0):
                
                res['is_change_salary_percentage_by_hand'] = False
            
        res['fields_affect_by_change_form'] = ', '.join(fields_name)
                    
        return {'value': res}
    
    
    def get_company_ids(self, cr, uid, employee_id, context=None):
        '''
        @return: default company_id from earliest main active contract and 
                 list company from active contract or contract active at context['effect_date']
        '''
        if not context:
            context = {}
            
        contract_pool = self.pool.get('hr.contract')
        
        company_ids = []
        default_company_id = False
        if employee_id:
            #Get list contract of employee
            date_compare = datetime.today().date()
            if context.get('effect_date', False):
                date_compare = context['effect_date']
            
            domain = [('employee_id','=',employee_id),
                      ('date_start', '<=', date_compare),
              #        ('state', '=', 'signed'),
                      '|', '|',
                      ('liquidation_date', '>', date_compare),
                      '&', ('date_end', '>=', date_compare), ('liquidation_date', '=', False),
                      '&', ('date_end', '=', False), ('liquidation_date', '=', False),
                    ]
            
            if context.get('include_not_signed_contract', False):
                domain.insert(0, ('state','!=','cancel'))
            else:
                domain.insert(0, ('state','=','signed'))
                
            contract_ids = contract_pool.search(cr, uid, domain, order='date_start desc')
            if contract_ids:
                contracts = contract_pool.read(cr, uid, contract_ids, ['company_id','is_main'], context=context)
                for contract in contracts:
                    company_id = contract.get('company_id',False) and contract['company_id'][0]
                    company_ids.append(company_id)
                    # Mặc định field "Contract to Company" lấy theo HĐ có "is_main"=True và đang hiệu lực
                    if contract.get('is_main', False):
                        default_company_id = company_id
        
        if not default_company_id and company_ids:
            default_company_id = company_ids[0]
        return default_company_id, list(set(company_ids))
    
    def onchange_company_id(self, cr, uid, ids, effect_from, employee_id, company_id, contract_id, 
                            department_id, team_id, job_title_id_new, is_new, is_change_effect_from_copy_data, 
                            nearest_working_record_id, invisible_change_salary, is_change_company_from_copy_data, context=None):
        '''
        If onchange company call onchange_effect_from again, 
        '''
        
        if context is None:
            context={}
        if context.get('default_contract_id') or context.get('termination_id', False) or is_change_company_from_copy_data:
            return {'value': {'is_change_company_from_copy_data': False}}
        
        if company_id:
            res = self.onchange_effect_from(cr, uid, ids, effect_from, employee_id, company_id, contract_id, 
                                            department_id, team_id, job_title_id_new, is_new, is_change_effect_from_copy_data, 
                                            nearest_working_record_id, invisible_change_salary, context)
            return res
        
        return {'value': {}}
    
    
    def get_contract_type(self, cr, uid, contract_type_group_id, context=None):
        contract_type = False
        if contract_type_group_id:
            contract_type_group = self.pool.get('hr.contract.type.group').read(cr, uid, contract_type_group_id, ['code','is_offical'])
            contract_type_group_code = contract_type_group.get('code', False)
            is_offical = contract_type_group.get('is_offical', False)
            
            
            if is_offical:
                contract_type = CT_OFFICIAL
            elif contract_type_group_code == 'CTG-008':
                contract_type = CT_DVCTV
            else:
                contract_type = CT_CTV
            
            #offer contract type group code
            if contract_type_group_code == '1':
                contract_type = CT_PROBATION
        
        return contract_type
    
        
    def onchange_effect_from(self, cr, uid, ids, effect_from, employee_id, company_id, contract_id, department_id, 
                             team_id, job_title_id_new, is_new, is_change_effect_from_copy_data, nearest_working_record_id, 
                             invisible_change_salary, context=None):
        """
        Get contract have effect_from >= date_start and effect_from <= date_end of company contract and largest date_start 
        If dont have any contract, raise warning
        
        If change domain change_form_ids, you need to check code vefified change_form_ids in temination request, contract, working record mass movement, mass movement to create working record
        """
        if context is None:
            context={}
        if context.get('default_contract_id'):
            return {'value': {}}
        
        if is_change_effect_from_copy_data:
            return {'value': {'is_change_effect_from_copy_data': False}}
        
        if isinstance(ids, (int, long)):
            ids = [ids]
        
        contract_pool = self.pool.get('hr.contract')
        
        res = {'contract_id': False, 'contract_start_date': False,
               'nearest_working_record_id': False, 'signer_id': '', 
               'signer_job_title_id': '','country_signer': False}
        
        warning = False
        
        domain_change_form_id = self.get_domain_for_change_form(cr, uid, context)
        domain = {'change_form_ids': domain_change_form_id }
        
        state = False
        if ids:
            record = self.read(cr, uid, ids[0], ['state'])
            state = record.get('state', False)
                    
        if effect_from and employee_id:
            mcontext = {'effect_date': effect_from, 'include_not_signed_contract': context.get('include_not_signed_contract', False)}
            new_company_id, company_ids = self.get_company_ids(cr, uid, employee_id, mcontext)
            domain['company_id'] = [('id', 'in', company_ids)]
            if company_id not in company_ids:
                #Raise error if change effect_from so company does not effect anymore, only check for created WR have state in [False,finish]
                if ids and state in [False, 'finish']:
                    effect_from = datetime.strptime(effect_from,DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y")
                    
                    company = self.pool.get('res.company').read(cr, uid, company_id, ['name'])
                    company_name = company.get('name', '')
                    warning = {
                                'title': 'Validation Error!',
                                'message' : "This employee doesn't work at company '%s' on %s !" % (company_name, effect_from)
                                 }
                    return {'value': res, 'warning': warning, 'domain': domain}
                else:
                    res['is_change_company_from_copy_data'] = True
                    company_id = new_company_id
                    res['company_id'] = new_company_id
                
            if not new_company_id:
                warning = {
                        'title': 'Validation Error!',
                        'message' : "This employee doesn't have any active main contract.\
                                    \n Please contact to C&B team to set main contract for him/her !"
                         }
                return {'value': res, 'warning': warning, 'domain': domain}
        
        field_news = []
        if not (ids and state in [False, 'finish']):
            for fields in dict_fields_update:
                res[fields[0]] = False
                res[fields[1]] = False
                field_news.append(fields[1])
                
        if effect_from and employee_id and company_id:
            
            #If onchange effect_from when edit working record(not when create)
            if not is_new and contract_id and ids:
                contract = contract_pool.read(cr, uid, contract_id, ['first_working_record_id'])
                first_working_record_id = contract.get('first_working_record_id', False) and contract['first_working_record_id'][0]
                #If this working record is first working record, do not change contract_id, to update date_start_contract when write
                if first_working_record_id in ids:
                    return {'value': {}}
            
            #Get contract have effect_from >= date_start and effect_from <= date_end(or liquidation_date if liquidation_date!=False) of company contract and largest date_start 
            domain_contract = [('company_id','=',company_id),
                               ('employee_id','=',employee_id),
                               ('date_start','<=',effect_from),
#                                                          ('state','=','signed'),
                               '|','|',
                                   ('liquidation_date','>=',effect_from),
                               '&',('date_end','>=',effect_from),('liquidation_date','=',False),
                               '&',('date_end','=',False),('liquidation_date','=',False),
                             ]
            if context.get('include_not_signed_contract', False):
                domain_contract.insert(0,('state','!=','cancel'))
            else:
                domain_contract.insert(0,('state','=','signed'))
                
            contract_ids = contract_pool.search(cr, uid, domain_contract, order='date_start desc') 
            if contract_ids:
                res['contract_id'] = contract_ids[0]
                contract = contract_pool.read(cr, uid, contract_ids[0], ['department_id','date_start','contract_type_group_id'])
                #'info_signer','title_signer','country_signer',
#                 res['signer_id'] = contract.get('info_signer','')
#                 res['signer_job_title_id'] = contract.get('title_signer','')
#                 res['country_signer'] = contract.get('country_signer',False) and contract['country_signer'][0] or False
                res['contract_start_date'] = contract.get('date_start',False)
                
                contract_type_group_id = contract.get('contract_type_group_id', False) and contract['contract_type_group_id'][0] or False
                res['contract_type'] = self.get_contract_type(cr, uid, contract_type_group_id, context)
                
                department_from_contract = contract.get('department_id', False) and contract['department_id'][0] or False
                
                #If WR is created and state in [False, finish], can only onchange from effect_from of nearest lower WR to effect_from of larger greater WR
                #so dont need to refresh data  (base on function check_if_update_effect_from_out_of_box to check rule)
                if ids and state in [False, 'finish']:
                    if 'nearest_working_record_id' in res:
                        del res['nearest_working_record_id'] 
                else:
                    #Get data from older WR
                    context['field_news'] = field_news
                    res_contract,n_domain,working_record_id = self.get_data_from_nearest_working_record(cr, uid, employee_id, company_id, 
                                                                                                        effect_from, res['contract_id'], context)
                    if n_domain:
                        domain = n_domain
                    if working_record_id not in ids:
                        #Only update data if working_record_id we get data different with working_record_id we got data in the past
                        if nearest_working_record_id != working_record_id or (nearest_working_record_id == working_record_id and working_record_id == False):
                            res.update(res_contract)
                            
                            
                            if context.get('update_mask_data_in_create', False):
                                log.info("Mask data in onchange_effect_from")
                                #Mask data for some invisible field for case, user cheat to get info
                                groups = self.get_groups(cr, uid, context)
                                if 'vhr_assistant_to_hrbp' in groups and 'vhr_hrbp' not in groups:
                                    groups.append('vhr_hrbp')
                                for field in ['job_level_person_id_old','job_level_person_id_new']:
                                    args_readonly, args_invisible = self.build_args_for_field(cr, uid, field, groups, context)
                                    if args_invisible:
                                        res[field] = 1
                            
                            res['nearest_working_record_id'] = working_record_id
                            if department_id and department_id == res.get('department_id_new',False):
                                res['is_change_from_contract'] = False
                            if team_id and team_id == res.get('team_id_new', False):
                                res['is_change_team_from_contract'] = False
                                
                            if job_title_id_new and job_title_id_new == res.get('job_title_id_new', False):
                                res['is_change_title_from_copy_data'] = False
                            
                            exist_wrs_ids = self.search(cr, uid, [('employee_id','=',employee_id),
                                                                  ('state','in',[False,'finish']),
                                                                  ('id','not in',ids),
                                                                  '|',('active','=',True),
                                                                      ('active','=',False)])
                            if not exist_wrs_ids and department_from_contract:
                                initial_data_from_department = self.get_initial_data_from_department(cr, uid, department_from_contract, context)
                                res.update(initial_data_from_department)
                            
                        else:
                            res = {'contract_id': contract_ids[0],'contract_start_date':res.get('contract_start_date',False)}
                            if domain:
                                res['change_form_ids'] = res_contract.get('change_form_ids',False)
                    else:
                        res = {}
                
                #Only Get data about salary from nearest Payroll Salary if invisible_change_salary = False
                if invisible_change_salary:
                    res.update({'invisible_change_salary': True})
                else:
                    working_id = ids and ids[0] or False
                    res_salary = self.get_data_from_nearest_payroll_salary(cr, SUPERUSER_ID, working_id, employee_id, company_id, effect_from, context)
                    if res_salary:
                        res.update(res_salary)
                    
                    if res_salary:
                        if res.get('salary_percentage_new', False):
                            res['is_change_salary_percentage_by_hand'] = False
                        if res.get('basic_salary_new', False):
                            res['is_change_basic_salary_by_hand'] = False
                        if res.get('gross_salary_new', False):
                            res['is_change_gross_salary_by_hand'] = False
                    
                    
                    #Get allowance_data
                    context['get_list_for_form'] = True
                    res_allowance = self.get_data_from_nearest_allowance(cr, SUPERUSER_ID, working_id, employee_id, company_id, effect_from, context)
                    res['old_allowance_ids'] = res_allowance
                    res['new_allowance_ids'] = res_allowance
                     
                    #Get new allowance data if new level != old level
                    if not res.get('job_level_person_id_new', False) \
                      and context.get('job_level_new_id', False) != context.get('job_level_old_id', False):
                        mcontext = {'employee_id': employee_id,
                                    'effect_from': effect_from,
                                    'company_id': company_id,
                                    'allowance_new_ids': res_allowance or []}
                         
                        res_onchange_job_level = self.onchange_job_level_person_id_new(cr, uid, ids, 
                                                  context.get('job_level_new_id', False), context.get('job_level_old_id', False), mcontext)
                        new_allowance_ids = res_onchange_job_level.get('value',{}).get('new_allowance_ids',False)
                        res['new_allowance_ids'] = new_allowance_ids
                    
                    
#                         res.update(res_allowance)
                                
                #Dont get data from employee timesheet when got it earlier, case get from department in contract when dont have any WR(join company)
                if not res.get('timesheet_id_new', False):
                    #Case change effect_from in created WR (state in False/finish) have create employee timesheet
                    val_timesheet = {}
                    if ids and state in [False, 'finish']:
                        record = self.read(cr, uid, ids[0], ['timesheet_id_new','ts_emp_timesheet_id'])
                        ts_emp_timesheet_id = record.get('ts_emp_timesheet_id', False) and record['ts_emp_timesheet_id'][0] or False
                        if ts_emp_timesheet_id:
                            context['current_ts_emp_timesheet_id'] = ts_emp_timesheet_id
                            timesheet_id_new = record.get('timesheet_id_new', False) and record['timesheet_id_new'][0] or False
                            val_timesheet['timesheet_id_new'] = timesheet_id_new
                            
                    #Get data about timesheet from nearest Employee Timesheet
                    res_timesheet = self.get_data_from_nearest_ts_emp_timesheet(cr, uid, employee_id, company_id, effect_from, context)
                    if res_timesheet:
                        res.update(res_timesheet)
                    
                    if val_timesheet:
                        res.update(val_timesheet)
                        
                    
                    
                  
            else:
                res['effect_from'] = False
                effect_from = datetime.strptime(effect_from,DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y")
                warning = {
                            'title': 'Validation Error!',
                            'message' : "Can't find any available contract on %s" % effect_from
                             }
                
        return {'value': res, 'warning': warning, 'domain': domain}
    
    
    def get_data_from_nearest_payroll_salary(self, cr, uid, working_id, employee_id, company_id, effect_from, context=None):
        """
        This function will be rewrite in module vhr_payroll
        """
        return {}
    
    def get_data_from_nearest_ts_emp_timesheet(self, cr, uid, employee_id, company_id, effect_from, context=None):
        """
        This function will be rewrite in module vhr_timesheet
        """
        return {}
    
    def get_data_from_nearest_ts_ws_employee(self, cr, uid, employee_id, company_id, effect_from, context=None):
        """
        This function will be rewrite in module vhr_timesheet
        """
        return {}
    
    def get_data_from_nearest_allowance(self, cr, uid, working_id, employee_id, company_id, effect_from, context=None):
        """
        This function will be rewrite in module vhr_payroll
        """
        return {}
    
    def get_initial_data_from_department(self, cr, uid, department_id, context=None):
        res = {}
        if department_id:
            department = self.pool.get('hr.department').read(cr, uid, department_id, ['salary_setting_id'])
            salary_setting_id = department.get('salary_setting_id', False) and department['salary_setting_id'][0] or False
            if salary_setting_id:
                res['salary_setting_id_new'] = salary_setting_id
        
        return res
    
    def get_domain_for_change_form(self, cr, uid, context=None):
        if not context:
            context = {}
        groups = self.get_groups(cr, uid)
        domain_change_form_id = [('id', 'not in', [])]
        
        if context.get('record_type', False) == 'request':
            domain_change_form_id = [('show_hr_rotate', '=', True)]
            
        elif context.get('record_type', False) == 'record':
            domain_change_form_id = []
            if 'vhr_cb_working_record' in groups:
                domain_change_form_id = []
            else:
                if set(['vhr_assistant_to_hrbp','vhr_hrbp']).intersection(set(groups)):
                    domain_change_form_id.append( ('show_qltv_hrbp', '=', True) )
                
                if set(['vhr_dept_admin']).intersection(set(groups)):
                    domain_change_form_id.append( ('show_qltv_admin', '=', True) )
                
                if set(['vhr_af_admin']).intersection(set(groups)):
                    domain_change_form_id.append( ('show_qltv_af_admin', '=', True) )
                
                if domain_change_form_id and len(domain_change_form_id) >1:
                    for index in range(len(domain_change_form_id)-1):
                        domain_change_form_id.insert(0,'|')
                        
                    
        #only using change form "input data into iRHP" from contract
        
        code_list = self.get_code_change_form_new_to_company(cr, uid, context)
        
        config_parameter = self.pool.get('ir.config_parameter')
        
        dismiss_code = config_parameter.get_param(cr, uid, 'vhr_master_data_dismiss_change_form_code') or ''
        dismiss_code_list = dismiss_code.split(',')
        
        dismiss_local_comp_code = config_parameter.get_param(cr, uid, 'vhr_master_data_dismiss_local_company') or ''
        dismiss_local_comp_code_list = dismiss_local_comp_code.split(',')
        
        code_list = code_list + dismiss_code_list + dismiss_local_comp_code_list
        
        if code_list:
            input_change_form_ids = self.pool.get('vhr.change.form').search(cr, uid, [('code','in',code_list)])
            domain_change_form_id = [('id','not in', input_change_form_ids)] + domain_change_form_id
        
        
        return domain_change_form_id
    
    def get_data_from_nearest_working_record(self, cr, uid, employee_id, company_id, effect_from, contract_id, context={}):
        '''
        If change domain change_form_ids, you need to check code vefified change_form_ids in temination request, contract, 
        working record mass movement, mass movement to create working record
        '''
        if not context:
            context = {}
        
        res = {}
        
        domain = {}
        latest_working_record_id = False
        field_news = context.get('field_news', False)
        if employee_id and company_id and contract_id and effect_from:
            
            
            #Get info from nearest working record when create from termination to get correct info
            if context.get('termination_id', False):
                latest_working_record_ids = self.search(cr, uid, [('effect_from','<',effect_from),
                                                                 ('employee_id','=',employee_id), 
                                                                 ('company_id','=',company_id), 
                                                                 ('state','in',[False,'finish']),
                                                                 '|',('active','=',True),
                                                                     ('active','=',False)], order='effect_from desc')
                if latest_working_record_ids:
                    latest_working_record_id = latest_working_record_ids[0]
            
            else:
                context['effect_from'] = effect_from
                latest_working_record_id, is_same_contract = self.get_latest_working_record(cr, uid, employee_id, company_id, contract_id, context)
            
            if latest_working_record_id:
                #read data from latest working record to append to currently record
                get_fields = ['change_form_ids','termination_id']
                if field_news:
                    get_fields += field_news
                else:
                    for fields in dict_fields_update:
                        get_fields.append(fields[1])
                
                latest_working_record = self.read(cr, SUPERUSER_ID, latest_working_record_id, get_fields, context)
                
                for fields in dict_fields_update:
                    field_data = latest_working_record.get(fields[1], None)
#                     if isinstance(field_data, (list,tuple)):
#                         field_data = field_data[0]
                    
                    res[fields[0]] = field_data
                    res[fields[1]] = field_data
                
                #set value and domain for change form if latest working record is termination
                change_form_ids = latest_working_record.get('change_form_ids',[]) or []
                if change_form_ids:
                    
                    config_parameter = self.pool.get('ir.config_parameter')
                    dismiss_code = config_parameter.get_param(cr, uid, 'vhr_master_data_dismiss_change_form_code') or ''
                    dismiss_code_list = dismiss_code.split(',')
                    if dismiss_code_list:
                        dismiss_change_form_ids = self.pool.get('vhr.change.form').search(cr, uid, [('code','in',dismiss_code_list)])
                        if list(set(change_form_ids).intersection(set(dismiss_change_form_ids))):
                            termination_id = latest_working_record.get('termination_id',False) and latest_working_record['termination_id'][0] or False
                            is_change_contract_type = False
                            back_code_list = []
                            if termination_id:
                                termination = self.pool.get('vhr.termination.request').read(cr, uid, termination_id, ['is_change_contract_type'])
                                is_change_contract_type = termination.get('is_change_contract_type', False)
                            
                            if is_change_contract_type:
                                back_code = config_parameter.get_param(cr, uid, 'vhr_master_data_change_type_of_contract')
                                back_code_list = back_code.split(',')
                            else:
                                #Set change form for new WR is back to work if latest is dismiss and not change contract type
                                back_code = config_parameter.get_param(cr, uid, 'vhr_master_data_back_to_work_change_form_code')
                                back_code_list = back_code.split(',')
                            back_work_change_form_ids = self.pool.get('vhr.change.form').search(cr, uid, [('code','in',back_code_list)])
                            if back_work_change_form_ids:
                                if not context.get('termination_id', False):
                                    res['change_form_ids'] = [[6,False,[back_work_change_form_ids[0]]]]
                                domain.update( {'change_form_ids': [('id', 'in', back_work_change_form_ids)]} )
            
            #Two these fields use for onchange department and onchange team after complete onchange effect_to, 
            #it's doesn't need to appear if create/update from other model
            if not context.get('create_from_outside', False):
                res['is_change_from_contract'] = True
                res['is_change_team_from_contract'] = True
                res['is_change_title_from_copy_data'] = True
                    
        return res,domain,latest_working_record_id
    
    def onchange_division_id_new(self, cr, uid, ids, division_id, department_group_id_new, department_id_new, is_change_from_contract, context=None):
        if not context:
            context = {}
        res = {'department_id_new': False, 'department_group_id_new': False}
        
        dept_obj = self.pool.get('hr.department')
        
        if division_id:
            child_department_group_ids = dept_obj.get_department_unit_level(cr, uid, division_id, 2, None, None, context)
            if department_group_id_new:
                child_department_ids = dept_obj.get_department_unit_level(cr, uid, department_group_id_new, 3, None, None, context)
            else:
                child_department_ids = dept_obj.get_department_unit_level(cr, uid, division_id, 3, None, None, context)
                child_department_ids = dept_obj.filter_to_get_direct_child_department(cr, uid, child_department_ids, 1, context)
            
            if (department_group_id_new and department_group_id_new in child_department_group_ids and department_id_new in child_department_ids) or \
               (not department_group_id_new and department_id_new in child_department_ids):
                res = {}
        
        return {'value': res}   
    
    def onchange_department_group_id_new(self, cr, uid, ids, division_id, department_group_id_new, department_id, is_change_from_contract, context=None):
        if not context:
            context = {}
        res = {'department_id_new': False}
        
        dept_obj = self.pool.get('hr.department')
        if division_id and department_id:
            if department_group_id_new:
                child_department_group_ids = dept_obj.get_department_unit_level(cr, uid, department_group_id_new, 3, None, None, context)
                if department_id in child_department_group_ids:
                    return {}
            else:
                child_division_ids = dept_obj.get_department_unit_level(cr, uid, division_id, 3, None, None, context)
                child_division_ids = dept_obj.filter_to_get_direct_child_department(cr, uid, child_division_ids, 1, context)
            
                if department_id in child_division_ids:
                    res = {}
        
        return {'value': res}   
    
    def onchange_department_id_new(self, cr, uid, ids, department_id, team_id, is_change_from_contract, department_id_old, context=None):
        """
        Get data when onchange department
        
        Case get data (timesheet_id, salary_setting_id) from department in contract when create first WR for employee--> did in onchange_effect_from
        Note if have change in operation create first WR for employee (function get data: get_initial_data_from_department() )
        """
        if not context:
            context = {}
        
        res = {'manager_id_new': False, 'team_id_new': False, 'report_to_new': False, 'is_change_from_contract': False}
        if department_id and not is_change_from_contract:
            department_info = self.pool.get('hr.department').read(cr, uid, department_id, ['manager_id'])
            manager_id = department_info.get('manager_id', False) and department_info['manager_id'][0] or False   
            res['manager_id_new'] = manager_id
            res['report_to_new'] = manager_id
        
            if team_id:
                child_team_ids = self.pool.get('hr.department').get_department_unit_level(cr, uid, department_id, 4, None, None, context)
                if team_id in child_team_ids:
                    del(res['team_id_new'])
            
        elif is_change_from_contract:
            res = {'is_change_from_contract': False}
            
#         if department_id != department_id_old:
#             res['mentor_id_new'] = False
#             res['timesheet_id_new'] = False 
            
        return {'value': res}
    
    def onchange_team_id_new(self, cr, uid, ids, team_id, is_change_team_from_contract, context=None):
        if not context:
            context = {}
        
        res = {'is_change_team_from_contract': False}
        if team_id and not is_change_team_from_contract:
            department_info = self.pool.get('hr.department').read(cr, uid, team_id, ['manager_id'])
            manager_id = department_info.get('manager_id', False) and department_info['manager_id'][0] or False   
            res['report_to_new'] = manager_id
            
        return {'value': res}
    
    def onchange_pro_job_family_id_new(self, cr, uid, ids, pro_job_family_id_new, pro_job_group_id_new, context=None):
        if not context:
            context = {}
        res = {'pro_job_group_id_new': False}  #,'pro_sub_group_id_new': False
        
        if pro_job_family_id_new and pro_job_group_id_new:
            job_group = self.pool.get('vhr.job.group').read(cr, uid, pro_job_group_id_new, ['job_family_id'])
            job_family_id = job_group.get('job_family_id', False) and job_group['job_family_id'][0] or False
            if job_family_id == pro_job_family_id_new:
                res = {}
            
        return {'value': res}
    
    def onchange_pro_job_group_id_new(self, cr, uid, ids, pro_job_group_id_new, pro_sub_group_id_new, context=None):
        if not context:
            context = {}
        res = {'pro_sub_group_id_new': False}
        
        if pro_job_group_id_new and pro_sub_group_id_new:
            sub_group = self.pool.get('vhr.sub.group').read(cr, uid, pro_sub_group_id_new, ['job_group_id'])
            job_group_id = sub_group.get('job_group_id', False) and sub_group['job_group_id'][0] or False
            if job_group_id == pro_job_group_id_new:
                res = {}
            
        return {'value': res}
    
    def onchange_pro_ranking_level_id_new(self, cr, uid, ids, pro_ranking_level_id_new, pro_grade_id_new, context=None):
        if not context:
            context = {}
        res = {'pro_grade_id_new': False}
        
        if pro_ranking_level_id_new and pro_grade_id_new:
            grade = self.pool.get('vhr.grade').read(cr, uid, pro_grade_id_new, ['ranking_level_id'])
            ranking_level_id = grade.get('ranking_level_id', False) and grade['ranking_level_id'][0] or False
            if ranking_level_id == pro_ranking_level_id_new:
                res = {}
            
        return {'value': res}
    
    
    def onchange_mn_job_family_id_new(self, cr, uid, ids, mn_job_family_id_new, mn_job_group_id_new, context=None):
        if not context:
            context = {}
        res = {'mn_job_group_id_new': False,'mn_sub_group_id_new': False}
        
        if mn_job_family_id_new and mn_job_group_id_new:
            job_group = self.pool.get('vhr.job.group').read(cr, uid, mn_job_group_id_new, ['job_family_id'])
            job_family_id = job_group.get('job_family_id', False) and job_group['job_family_id'][0] or False
            if job_family_id == mn_job_family_id_new:
                res = {}
            
        return {'value': res}
    
    def onchange_mn_job_group_id_new(self, cr, uid, ids, mn_job_group_id_new, mn_sub_group_id_new ,context=None):
        if not context:
            context = {}
        res = {'mn_sub_group_id_new': False}
        
        if mn_job_group_id_new and mn_sub_group_id_new:
            sub_group = self.pool.get('vhr.sub.group').read(cr, uid, mn_sub_group_id_new, ['job_group_id'])
            job_group_id = sub_group.get('job_group_id', False) and sub_group['job_group_id'][0] or False
            if job_group_id == mn_job_group_id_new:
                res = {}
            
        return {'value': res}
    
    def onchange_mn_ranking_level_id_new(self, cr, uid, ids, mn_ranking_level_id_new, mn_grade_id_new, context=None):
        if not context:
            context = {}
        res = {'mn_grade_id_new': False}
        
        if mn_ranking_level_id_new and mn_grade_id_new:
            grade = self.pool.get('vhr.grade').read(cr, uid, mn_grade_id_new, ['ranking_level_id'])
            ranking_level_id = grade.get('ranking_level_id', False) and grade['ranking_level_id'][0] or False
            if ranking_level_id == mn_ranking_level_id_new:
                res = {}
            
        return {'value': res}
    
    def onchange_job_title_id(self, cr, uid, ids, job_title_id, job_level_id, pro_sub_group_id_new, is_change_title_from_copy_data, context=None):
        if not context:
            context = {}
        res = {    
#                    'pro_job_family_id_new': False,
#                    'pro_job_group_id_new': False,
#                    'pro_sub_group_id_new': False,
                   }
        
#         domain = {'pro_job_family_id_new': [('id', 'in', [])],
#                   'pro_job_group_id_new': [('id', 'in', [])],
#                   'pro_sub_group_id_new': [('id', 'in', [])]
#                   } 
        
        #If change job title from onchange effect_from, don't check to update other
        if is_change_title_from_copy_data:
            res = {'is_change_title_from_copy_data': False}
            return {'value': res}  #,'domain':domain
                    
        return {'value': res}  #,'domain':domain
    
    def onchange_job_level_person_id_new(self, cr, uid, ids, job_level_person_id_new, job_level_person_id_old, context=None):
        res = {'value': {'is_change_job_level_person': False}}
        if job_level_person_id_new != job_level_person_id_old:
            res['value']['is_change_job_level_person'] = True
        
        return res
    
    def onchange_gross_salary(self, cr, uid, ids, gross_salary, basic_salary_new, kpi_amount, salary_percentage, is_change_gross_salary_by_hand, context=None):
        res = {}
        warning = {}
        if gross_salary and salary_percentage:
            
                
            new_basic_salary_new = gross_salary / 100.00 * salary_percentage
            new_basic_salary_new = float("{0:.0f}".format(new_basic_salary_new))
            if basic_salary_new != new_basic_salary_new and is_change_gross_salary_by_hand:
                geo_salary = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_payroll_salary_need_to_be_divided_to_basic_and_bonus') or 0
                try:
                    geo_salary = int(geo_salary)
                except:
                    geo_salary = 0
                
                #Nếu mức lương nhỏ hơn 6.000.000 : không tách lương
                if geo_salary and gross_salary  < geo_salary:
                    salary_percentage = 100
                elif salary_percentage == 100:
                    salary_percentage = self.pool.get('ir.config_parameter').get_param(cr, uid, 'percentage_split_salary') or 0
                    salary_percentage = float(salary_percentage)
                
                res['salary_percentage_new'] = salary_percentage
                
                new_basic_salary_new = gross_salary / 100.00 * salary_percentage
                new_basic_salary_new = float("{0:.0f}".format(new_basic_salary_new))
            
                basic_salary_new = new_basic_salary_new
                res['basic_salary_new'] = new_basic_salary_new
                res['is_change_basic_salary_by_hand'] = False
            res['is_change_gross_salary_by_hand'] = True
            
            if is_change_gross_salary_by_hand:
                res['v_bonus_salary_new'] = gross_salary - basic_salary_new
                if kpi_amount:
                    res['v_bonus_salary_new'] = res['v_bonus_salary_new'] - kpi_amount
                    if res['v_bonus_salary_new'] < 0:
                        res['v_bonus_salary_new'] = 0
                        warning = {
                                    'title': 'Validation Error!',
                                    'message' : "Summarize of V_Bonus, KPI and Basic salary must equal to Gross Salary"
                                     }
                
        return {'value': res, 'warning': warning}
    
    def onchange_salary_percentage(self, cr, uid, ids, gross_salary, basic_salary_new, kpi_amount, salary_percentage, 
                                   is_change_salary_percentage_by_hand, context=None):
        res = {}
        warning = {}
        if gross_salary and salary_percentage is not None:
            salary_percentage = salary_percentage or 0
            basic_salary_new = basic_salary_new or 0
            if salary_percentage < 0:
                warning = {
                            'title': 'Validation Error!',
                            'message' : "% Basic Salary must be greater than or equal to 0, lower than or equal to 100"
                             }
                return {'value': res, 'warning': warning}
            
            new_basic_salary_new = gross_salary / 100.00 * salary_percentage
            new_basic_salary_new = float("{0:.0f}".format(new_basic_salary_new))
            if basic_salary_new != new_basic_salary_new and is_change_salary_percentage_by_hand:
                basic_salary_new = new_basic_salary_new
                res['basic_salary_new'] = new_basic_salary_new
                res['is_change_basic_salary_by_hand'] = False
            res['is_change_salary_percentage_by_hand'] = True
            
            if is_change_salary_percentage_by_hand:
                res['v_bonus_salary_new'] = gross_salary - basic_salary_new
                if kpi_amount:
                    res['v_bonus_salary_new'] = res['v_bonus_salary_new'] - kpi_amount
                    if res['v_bonus_salary_new'] < 0:
                        res['v_bonus_salary_new'] = 0
                        warning = {
                                    'title': 'Validation Error!',
                                    'message' : "Summarize of V_Bonus, KPI and Basic salary must equal to Gross Salary"
                                     }
                
        return {'value': res, 'warning': warning}
        
     
    
    def onchange_basic_salary(self, cr, uid, ids, gross_salary, basic_salary, kpi_amount, salary_percentage, is_change_basic_salary_by_hand, context=None):
        res = {}
        warning = {}
        if gross_salary and basic_salary:
            if basic_salary> gross_salary:
                raise osv.except_osv('Validation Error !', 'Basic Salary must be lower Gross Salary')
            
            new_salary_percentage= float(basic_salary)/ gross_salary * 100.00
            if new_salary_percentage != salary_percentage and is_change_basic_salary_by_hand:
                new_salary_percentage = float("{0:.0f}".format(new_salary_percentage))
                res['salary_percentage_new'] = new_salary_percentage
                res['is_change_salary_percentage_by_hand'] = False
            res['is_change_basic_salary_by_hand'] = True
            
            if is_change_basic_salary_by_hand:
                res['v_bonus_salary_new'] = gross_salary - basic_salary
                if kpi_amount:
                    res['v_bonus_salary_new'] = res['v_bonus_salary_new'] - kpi_amount
                    if res['v_bonus_salary_new'] < 0:
                        res['v_bonus_salary_new'] = 0
                        warning = {
                                    'title': 'Validation Error!',
                                    'message' : "Summarize of V_Bonus, KPI and Basic salary must equal to Gross Salary"
                                     }
                
        return {'value': res, 'warning': warning}
    
    def onchange_kpi_amount(self, cr, uid, ids, gross_salary, basic_salary, kpi_amount, context=None):
        res = {}
        warning = {}
        if gross_salary and basic_salary:
            res['v_bonus_salary_new'] = gross_salary - basic_salary
            if kpi_amount:
                res['v_bonus_salary_new'] = res['v_bonus_salary_new'] - kpi_amount
                if res['v_bonus_salary_new'] < 0:
                    res['v_bonus_salary_new'] = 0
                    warning = {
                                'title': 'Validation Error!',
                                'message' : "Summarize of V_Bonus, KPI and Basic salary must equal to Gross Salary"
                                 }
                
        return {'value': res, 'warning': warning}
    
    def onchange_general_allowance(self, cr, uid, ids, gross_salary, basic_salary, kpi_amount, general_allowance, context=None):
        res = {}
        warning = {}
        if gross_salary and basic_salary:
            sum = basic_salary
            if kpi_amount:
                sum +=  kpi_amount 
            if general_allowance:
                sum += general_allowance 
            if sum != gross_salary:
                warning = {
                                'title': 'Validation Error!',
                                'message' : "Summarize of general allowance, KPI and Basic salary must equal to Gross Salary"
                                 }
                
        return {'value': res, 'warning': warning}
    
    def onchange_v_bonus_salary(self, cr, uid, ids, gross_salary, basic_salary, kpi_amount, v_bonus_salary, context=None):
        res = {}
        warning = {}
        if gross_salary and basic_salary:
            sum = basic_salary
            if kpi_amount:
                sum +=  kpi_amount 
            if v_bonus_salary:
                sum += v_bonus_salary 
            if sum != gross_salary:
                warning = {
                                'title': 'Validation Error!',
                                'message' : "Summarize of V_Bonus, KPI and Basic salary must equal to Gross Salary"
                                 }
                
        return {'value': res, 'warning': warning}
        

#     def onchange_signer_id(self, cr, uid, ids, signer_id, context=None):
#         if not context:
#             context = {}
#         value = {}
#         if signer_id:
#             signer_info = self.pool.get('hr.employee').read(cr, uid, signer_id, ['title_id'])
#             title_id = signer_info.get('title_id', False) and signer_info['title_id'][0] or False
#             value['signer_job_title_id'] = title_id
#         
#         return {'value': value}
            
    
    def name_get(self, cr, uid, ids, context=None):
        if not ids or False in ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        
        reads = self.read(cr, uid, ids, ['employee_id'], context=context)
        res = []
        for record in reads:
                name = record.get('employee_id',False) and record['employee_id'][1]
                res.append((record['id'], name))
        return res
    
    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        args_new = [('name', operator, name)] + args
        ids = self.search(cr, uid, args_new)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(vhr_working_record, self).name_search(cr, uid, name, args, operator, context, limit)
    
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        #Search rule in staff movement
        if not context:
            context = {}
        
        try:
            args, context = self.get_search_argument(cr, uid, args, offset, limit, order, context, count)
        except Exception as e:
            log.exception(e)
            error_message = ''
            try:
                error_message = e.message
                if not error_message:
                    error_message = e.value
            except:
                error_message = ""
            raise osv.except_osv('Validation Error !', 'Have error during filter list record:\n %s!' % error_message)
        
        res =  super(vhr_working_record, self).search(cr, uid, args, offset, limit, order, context, count)
        return res
    
    def read(self, cr, user, ids, fields=None, context=None, load='_classic_read'):
        if not context:
            context = {}
        
        if 'active_test' not in context:
            context['active_test'] = False
        
        if context.get('get_department_name_by_code', False) and len(fields) > 1:
            if not ('division_id_new' in fields and 'department_id_new' in fields):
                context['get_department_name_by_code'] = False
        
        groups = self.get_groups(cr, user)
        
        allow_fields = ['employee_id','company_id','effect_from','effect_to']
        self.prevent_normal_emp_read_data_of_other_emp(cr, user, ids, groups, allow_fields, fields, context)
        
        if not set(groups).intersection(['hrs_group_system','vhr_cb_working_record']) and 'audit_log_ids' in fields:
            fields.remove('audit_log_ids')
            
            
        if context.get('validate_read_vhr_working_record',False):
            context['check_to_return_none_value'] = True
            log.info('\n\n validate_read_vhr_working_record')
            if not context.get('record_type', False):
                context['record_type'] = 'record'
            result_check = self.validate_read(cr, user, ids, context)
            if not result_check:
                raise osv.except_osv('Validation Error !', 'You don’t have permission to access this data !')
            
            del context['validate_read_vhr_working_record']
        
        res =  super(vhr_working_record, self).read(cr, user, ids, fields, context, load)
        
        
        res = self.parse_department_code_in_read(cr, user, ids, res, fields, context, load)
        
        res = self.mask_field_data_based_on_other_fields(cr, user, ids, res, groups, fields, context, load)
        
        return res
    
    def parse_department_code_in_read(self, cr, user, ids, res, fields=None, context=None, load='_classic_read'):
        if not context:
            context = {}
            
        department_old_fields = ['division_id_old','department_group_id_old','department_id_old','team_id_old']
        
        update_old_fields = set(department_old_fields).intersection(set(fields))
        if update_old_fields and context.get('get_department_name_by_code', False):
            for data in res:
                if 'effect_from' in data:

                    effect_from = data['effect_from']
                    effect_from_by1 = datetime.strptime(effect_from, DEFAULT_SERVER_DATE_FORMAT) - relativedelta(days=1)
                    effect_from_by1 = effect_from_by1.strftime(DEFAULT_SERVER_DATE_FORMAT)
                    mcontext = {'dept_effect_from_in_history': effect_from_by1}
                    for field in update_old_fields:
                        if isinstance(data[field], tuple):
                            code = self.pool.get('hr.department').get_history_code_of_department(cr, user, data[field][0], mcontext)
                            if code:
                                data[field] = (data[field][0], code)
        
        department_new_fields = ['division_id_new','department_group_id_new','department_id_new','team_id_new']
        
        update_new_fields = set(department_new_fields).intersection(set(fields))
        if update_new_fields and (context.get('get_department_name_by_code', False) or context.get('record_type', False)):
            for data in res:
                if 'effect_from' in data:
                    mcontext = {'dept_effect_from_in_history': data['effect_from']}
                    for field in update_new_fields:
                        if isinstance(data[field], tuple):
                            if context.get('get_department_name_by_code', False):
                                code = self.pool.get('hr.department').get_history_code_of_department(cr, user, data[field][0], mcontext)
                            else:
                                code = self.pool.get('hr.department').name_get(cr, user, [data[field][0]], mcontext)[0][1]
                            if code:
                                data[field] = (data[field][0], code)
        
        return res
    
    
    def mask_field_data_based_on_other_fields(self, cr, user, ids, res, groups, fields=None, context=None, load='_classic_read'):
        vhr_human_resource_group_hr = self.pool.get('ir.config_parameter').get_param(cr, user, 'vhr_human_resource_group_hr') or ''
        vhr_human_resource_group_hr = vhr_human_resource_group_hr.split(',')
        if res and set(SALARY_FIELDS).intersection(fields):
            #If user dont have right to see salary, return  them all zero 
            change_to_element = False
            if not isinstance(res, list):
                res = [res]
                change_to_element = True
            for data in res:
                if data.get('invisible_change_salary', False):
                    for field in SALARY_FIELDS:
                        data[field] = 0
            
            if change_to_element:
                res = res[0]
        
        
        """
        Nếu có luân chuyển phòng ban, requester : 
        - Không thấy được thông tin lương mới, job title, job level, position level, person level, job family, job group
        - Trên eform của requester cũng chỉ hiển thị loại thay đổi là "Luân chuyển phòng ban"
        """
        #dont allow old hrbp, old dept head see change form dieu chinh luong
        if res and len(res) == 1 and res[0].get('is_change_form_adjust_salary',False) and \
          res[0].get('invisible_change_salary', False) and not res[0].get('is_person_do_action', False):
            change_form_ids = res[0].get('change_form_ids', [])
            form_ids = []
            names = []
            for form in self.pool.get('vhr.change.form').read(cr, user, change_form_ids, ['name','access_field_ids','is_salary_adjustment']):
                if not form.get('is_salary_adjustment', False):
                    access_fields_ids = form.get('access_field_ids', [])
                    field_ids = self.pool.get('ir.model.fields').search(cr, SUPERUSER_ID, [('id','in',access_fields_ids),
                                                                                  ('name','=','department_id_new')])
                    if field_ids:
                        form_ids.append(form['id'])
                        names.append(form['name'])
            
            res[0]['change_form_ids'] = form_ids
            res[0]['change_form_name'] = ' - '.join(names)
        
        if res and len(res) == 1 and 'job_level_person_id_new' in fields and not set(groups).intersection(vhr_human_resource_group_hr):
            res[0]['job_level_person_id_new'] = 1
            res[0]['job_level_person_id_old'] = 1
        
        #invisible data when working record have change form transfer department and login user is requester/old hrbp/old dept head
        invisible_fields = ['job_title_id_new','pro_job_family_id_new','pro_job_group_id_new','pro_sub_group_id_new','mn_job_family_id_new',
                            'mn_job_group_id_new','mn_sub_group_id_new','job_level_id_new','job_level_person_id_new']
        
        if res and len(res) == 1 and res[0].get('is_invisible_data_when_transfer_department', False) and res[0].get('state',False) !='draft':
            for field in invisible_fields:
                res[0][field] = False
        
        return res
    
    def validate_read(self, cr, uid, ids, context=None):
        user_groups = self.get_groups(cr, uid)
        if set(['hrs_group_system', 'vhr_hr_dept_head','vhr_cnb_manager']).intersection(set(user_groups)):
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
    
    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False,
                   lazy=True):
        """
        Get the list of records in list view grouped by the given ``groupby`` fields
        """
        
        domain, context = self.get_search_argument(cr, uid, domain, 0, 0, 0, context, False)

        res = super(vhr_working_record, self).read_group(cr, uid, domain, fields, groupby, offset, limit, context, orderby,
                                                   lazy)
        return res
    
    
    
    
    def get_search_argument(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        
        if 'active_test' not in context:
            context['active_test'] = False
        if context.get('record_type', False) == 'request':
#             context['filter_employee_id'] = True
            #In staff movement, user can only see record is waiting action of that user
            args = self.build_condition_menu_for_staff_movement(cr, uid, args, offset, limit, order, context, count)
            
        elif context.get('record_type',False) or context.get('force_search_vhr_working_record',False):
            if context.get('force_search_vhr_working_record', False):
                del context['force_search_vhr_working_record']
                if not context.get('record_type',False):
                    context['record_type'] = 'record'
                
            if not context.get('public_WR', True):
                #Show WR in "Waiting for Publish"
                args.extend([('state','in',[False,'finish']), ('is_public','=',False)])
            else:
                args.extend([('state','in',[False,'finish'])])
            
            args = self.build_condition_menu_for_working_record(cr, uid, args, offset, limit, order, context, count)
        
        return args, context
    
    #Get list group name of user
    def get_groups(self, cr, uid, context={}):
        """
        Cheat nếu user thuộc group vhr_cnb_manager thì coi như nó cũng thuộc group vhr_cb_working_record,
        bởi vì user muôn cnb_manager cũng full quyền như cb_working_record(ko có time để tìm và sửa) . 
        """
        if not context:
            context = {}
            
        groups = []
        groups = self.pool.get('res.users').get_groups(cr, uid)
        
        #TODO: remove later
        groups.extend(['vhr_requestor'])
        
        if 'vhr_cnb_manager' in groups and not context.get('get_correct_cb', False):
            groups.append('vhr_cb_working_record')
            
        return groups
    
    #Build condition to search ids for specific menu of staff movement
    def build_condition_menu_for_staff_movement(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        '''
            Add permission for HRBP, Assistant HRBP, Dept Head, CB, HR Dept Head
        '''
        employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=', uid)], context={'active_test':False})
        new_args = []
        if employee_ids:
            department_ids = self.pool.get('hr.department').search(cr, SUPERUSER_ID, [('manager_id', 'in', employee_ids)], 0,None,None,context)
            
            department_hrbp_ids     = self.get_department_of_hrbp(cr, uid, employee_ids[0], context)
            department_ass_hrbp_ids = self.get_department_of_ass_hrbp(cr, uid, employee_ids[0], context)
            department_hrbp_ids     = department_hrbp_ids + department_ass_hrbp_ids
            
#             change_form_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_human_resource_change_form_code_for_mix_case_dcl_lcpb') or ''
#             change_form_code = change_form_code.split(',')
#             special_change_form_ids = self.pool.get('vhr.change.form').search(cr, uid, [('code', 'in', change_form_code)],context=context)
            
            user_groups = self.get_groups(cr, uid)
            
            #Domain for  Old/New HRBP, Old/New Assist HRBP, Old/New Dept Head
            new_args.extend(['|','|','|','|',
                                             ('department_id_new','in',department_hrbp_ids),#For new HRBP ,new Assist HRBP
                                         '&',('create_uid','=',uid),('state','!=',False),#For state draft
                                         '&',('department_id_old','in',department_hrbp_ids),('state','not in',['draft',False]),#For state HRBP
                                         
                                         '&',('manager_id_old','=',employee_ids[0]),('state','not in',['draft',False]),    #Old Dept Head
                                         '&',('manager_id_new','=',employee_ids[0]),('state','not in',['draft',False])    #New Dept Head
                            ])
            
                    
#             if context.get('filter_employee_id',False):
#                 new_args.insert(1, '|')
#                 new_args.append(('employee_id','in',employee_ids))
                
            if set(['hrs_group_system','vhr_hr_dept_head','vhr_cb_working_record','vhr_cb_contract','vhr_cb_termination']).intersection(set(user_groups)):
                 new_args = [('state','!=',False)]
        
        else:
            new_args.append(('id','in',[]))         
            
        new_args.insert(0,('state','!=',False))
        
        #Check if login employee have permission location
        if context.get('model', self._name) == self._name:
            res, res_employee_ids = self.get_domain_based_on_permission_location(cr, uid, employee_ids, context)
            if res:
                new_args.extend(res)
            
        args += new_args    
        
        return args
    
    def build_condition_menu_for_working_record(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        new_args = []
        groups = self.get_groups(cr, uid)
        employee_pool = self.pool.get('hr.employee')
        context['search_all_employee'] = True
        context['active_test'] = False
        login_employee_ids = employee_pool.search(cr, uid, [('user_id','=',uid)], 0, None, None, context)
        if set(['hrs_group_system','vhr_cb_contract','vhr_cb_working_record','vhr_cb_working_record_readonly',
                'vhr_cb_termination','vhr_hr_dept_head','vhr_cnb_manager']).intersection(set(groups)):
            
            #Filter list contract based on permisison location
            domain, employee_ids = self.get_domain_based_on_permission_location(cr, uid, login_employee_ids, context)
            if domain:
                args.extend(domain)
            return args
        
        elif set(['vhr_hrbp','vhr_assistant_to_hrbp']).intersection(set(groups)):
            if login_employee_ids:
                #Get list department which user is hrbp or assist_hrbp
                department_hrbp = self.get_department_of_hrbp(cr, uid, login_employee_ids[0], context)
                department_ass_hrbp = self.get_department_of_ass_hrbp(cr, uid, login_employee_ids[0], context)
                department_ids = department_hrbp + department_ass_hrbp
                department_ids.append(0)
                #Show all working record of current employee in department of hrbp/ assist hrbp
                sql = """
                        SELECT employee_id FROM vhr_working_record 
                        WHERE active = True and department_id_new in %s
                      """
                cr.execute(sql% str(tuple(department_ids)).replace(',)', ')'))
                
                res = cr.fetchall()
                employee_ids = [item[0] for item in res]
                
                new_args += [('employee_id','in',employee_ids)]
        
        if login_employee_ids:
            department_ids = self.get_hierachical_department_from_manager(cr, uid, login_employee_ids[0], context)
            if department_ids:
                
                working_record_ids = self.search(cr, uid, ['|',('department_id_old','in',department_ids),
                                                               ('department_id_new','in',department_ids)])
                
                if working_record_ids:
                    if new_args:
                        new_args.insert(0,'|')
                    new_args += [('id','in',working_record_ids)]
            
            #Get all WR record by employee using timesheet of admin dept at present have change form.show_qltv_admin = True
            employee_ids = self.get_list_employees_of_dept_admin(cr, uid, login_employee_ids[0], context)
            dept_object_ids = self.search(cr, uid, [('employee_id','in',employee_ids)])
            if dept_object_ids:
                change_form_for_admin_dept_ids = self.pool.get('vhr.change.form').search(cr, uid, [('show_qltv_admin','=',True)])
                if new_args:
                    new_args.insert(0,'|')
                new_args.extend(['&',('id','in',dept_object_ids),('change_form_ids','in',change_form_for_admin_dept_ids)])
            
            #Get all WR record for AF admin ave change form.show_qltv_af_admin = True
            if 'vhr_af_admin' in groups:
                change_form_for_af_admin_ids = self.pool.get('vhr.change.form').search(cr, uid, [('show_qltv_af_admin','=',True)])
                if new_args:
                    new_args.insert(0,'|')
                new_args.extend([('change_form_ids','in',change_form_for_af_admin_ids)])
            
            #Allow user to see his/her record
#             object_ids = self.search(cr, uid, [('employee_id','in',login_employee_ids)])
#             if object_ids:
#                 if new_args:
#                     new_args.insert(0,'|')
#                 new_args.extend([('id','in',object_ids)])
            
            #Filter list contract based on permisison location
            domain, employee_ids = self.get_domain_based_on_permission_location(cr, uid, login_employee_ids, context)
            if domain:
                new_args.extend(domain)
                
        if not new_args:
            new_args += [('id','in',[])]
        
        args += new_args    
        
        return args
    
    def get_domain_based_on_permission_location(self, cr, uid, employee_ids, context=None):
        """
        return domain to search employee based on permission location
        """
        res = []
        res_employee_ids = []
        if employee_ids:
            if not isinstance(employee_ids, list):
                employee_ids = [employee_ids]
            permission_obj = self.pool.get('vhr.permission.location')
            record_ids = permission_obj.search(cr, uid, [('employee_id','in',employee_ids)])
            if record_ids:
                record = permission_obj.read(cr, uid, record_ids[0], ['company_ids','office_ids'])
                company_ids = record.get('company_ids',[])
                office_ids = record.get('office_ids',[])
                
                domain = []
                if company_ids:
                    domain.append(('company_id','in', company_ids))
                
                if office_ids:
                    domain.append(('office_id_new','in', office_ids))
                
                #Search employee in company or office at active working record
                if domain:
                    domain.extend([('active','=',True),('state','in',[False,'finish'])])
                    working_ids = self.search(cr, uid, domain, context={'active_test': False})
                    if working_ids:
                        workings = self.read(cr, uid, working_ids, ['employee_id'])
                        res_employee_ids = [wr.get('employee_id', False) and wr['employee_id'][0] for wr in workings]
                        res.append(('employee_id','in',res_employee_ids))
                        
        return res, res_employee_ids
    
    #Get all department which have hrbp is employee_id
    def get_department_of_hrbp(self, cr, uid, employee_id, context=None):
        department_ids = []
        if employee_id:
            department_ids = self.pool.get('hr.department').search(cr, uid, [('hrbps','=',employee_id)])
        
        return department_ids
    
    #Get all department which have ass_hrbp is employee_id
    def get_department_of_ass_hrbp(self, cr, uid, employee_id, context=None):
        department_ids = []
        if employee_id:
            department_ids = self.pool.get('hr.department').search(cr, uid, [('ass_hrbps','=',employee_id)])
        
        return department_ids
    
    
    #Get latest working record or nearest the latest record
    def get_latest_working_record(self, cr, uid, employee_id, company_id, contract_id, context=None):
        """
        Return record_id, is_same_contract
        
        *** record_id is last working record in same contract or in same company(when dont have working record in same contract)
        *** is_same_contract indicates that record_id is record of same contract or not
        """
        if employee_id and company_id and contract_id:
            args = [('employee_id','=',employee_id), 
                    ('company_id','=',company_id), 
                    ('state','in',[False,'finish']),
                    '|',('active','=',True),
                        ('active','=',False)]
            
            #Search for working record have effect_from < effect_from of current edit WR
            if context.get('effect_from', False):
                args.insert(1, ('effect_from','<',context['effect_from']) )
            
            latest_record_id = self.get_latest_working_record_from_args(cr, uid, args, context)
            is_same_contract = False
            if latest_record_id:
                latest_record = self.read(cr, uid, latest_record_id, ['contract_id'])
                latest_contract_id = latest_record.get('contract_id', False) and latest_record['contract_id'][0] or False
                if contract_id == latest_contract_id:
                    is_same_contract = True
            
            return latest_record_id, is_same_contract
            
        return False,False
    
    def get_latest_working_record_from_args(self, cr, uid, args, context=None):
        exist_working_record_ids = self.search(cr, uid, args, order='effect_from desc')
        if exist_working_record_ids:
            #Exception when call function in latest record we will get record nearest the latest record
            if context.get('editing_record', False) and context['editing_record'] in exist_working_record_ids:
                exist_working_record_ids.remove(context['editing_record'])
                
            latest_working_record_id = exist_working_record_ids and exist_working_record_ids[0]
            return latest_working_record_id
        
        return False
        
    
    def update_nearest_working_record_info(self, cr, uid, ids, context={}):
        """
         Update  effect_to of nearest record if satisfy condition
        """
        if not context:
            context = {}
        if ids:
            
            dismiss_form_ids = self.get_dismiss_change_form_ids(cr, uid, context)
            for record_id in ids:
                record = self.browse(cr, uid, record_id, {})
                effect_from = datetime.strptime(record.effect_from, DEFAULT_SERVER_DATE_FORMAT).date()
                
                context['editing_record'] = record_id
#                 if context.get('get_nearest_working_record', False):
                context['effect_from'] = record.effect_from
                context['do_not_check_to_update_and_pus_data_to_hr_employee'] = True
                context['do_not_update_nearest_larger_wr'] = True
                context['do_not_create_update_pr_salary'] = True
                #Put editing_record into context to get nearest record of record have record_id
                latest_working_record_id, is_same_contract = self.get_latest_working_record(cr, uid, record.employee_id.id, record.company_id.id, 
                                                                                            record.contract_id.id, context)
                latest_vals = {}
                
                if latest_working_record_id:
                    wr = self.read(cr, uid, latest_working_record_id, ['change_form_ids'])
                    form_ids = wr.get('change_form_ids',[])
                    #Dont update effect_to of nearest WR, if nearest WR is termination
                    if set(form_ids).intersection(set(dismiss_form_ids)):
                        continue
                    
                    mcontext = context.copy()
                    mcontext['do_not_update_employee_instance'] = True
                    if 'effect_from' in mcontext:
                        del mcontext['effect_from']
                    #If have latest working record, update effect_to of latest working record
                    latest_working_record_effect_to = effect_from - relativedelta(days=1)
                    latest_working_record_effect_to = latest_working_record_effect_to.strftime(DEFAULT_SERVER_DATE_FORMAT)
                    latest_vals['effect_to'] = latest_working_record_effect_to
#                     latest_vals['is_latest'] = False
                    self.write(cr, uid, latest_working_record_id, latest_vals, mcontext)
                
        return True
    
    def update_working_record_state(self, cr, uid, working_record_ids, context=None):
        """
         Update state of all working record link to employee-company of input working_record_ids
         One employee at a company only have one working record is active
         Return list working record just active
        """
        if not context:
            context = {}
        result = []
        list_unique = []
        if working_record_ids:
            working_records = self.read(cr, uid, working_record_ids, ['employee_id','company_id'])
            for working_record in working_records:
                company_id = working_record.get('company_id', False) and working_record['company_id'][0] or False
                employee_id = working_record.get('employee_id', False) and working_record['employee_id'][0] or False
                
                if (employee_id,company_id) not in list_unique:
                    list_unique.append( (employee_id,company_id) )
                    
        if list_unique:
            context['do_not_check_to_update_and_pus_data_to_hr_employee'] = True
                        
            add_do_not_update_nearest_larger_wr = False
            if not context.get('do_not_update_nearest_larger_wr', False):
                context['do_not_update_nearest_larger_wr'] = True
                add_do_not_update_nearest_larger_wr = True
            
            today = datetime.today().date()
            for unique_item in list_unique:
                 #Get WR have active=False need to update active=True
                active_record_ids = self.search(cr, uid, [('employee_id','=',unique_item[0]),
                                                          ('company_id','=',unique_item[1]),
                                                          ('active','=',False),
                                                          ('state','in',[False,'finish']),
                                                          ('effect_from','<=',today),
                                                          '|',('effect_to','=',False),
                                                              ('effect_to','>=',today)])
                
                 #Get WR have active=True need to update active=False
                inactive_record_ids = self.search(cr, uid, [('employee_id','=',unique_item[0]),
                                                            ('company_id','=',unique_item[1]),
                                                            ('active','=',True),
                                                            ('state','in',[False,'finish']),
                                                              '|',('effect_to','<',today),
                                                                  ('effect_from','>',today)])
        
#                 working_record_ids = inactive_record_ids + active_record_ids
#                 if working_record_ids:
#                     dict_result = self.update_active_of_record_cm(cr, uid, 'vhr.working.record', working_record_ids, context)
                
                if active_record_ids:
#                     context['disable_check_allowance'] = True
                    result = self.set_active_record(cr, uid, active_record_ids, context)
                    
                if inactive_record_ids:
                    super(vhr_working_record, self).write(cr, uid, inactive_record_ids, {'active': False})
                        
            if add_do_not_update_nearest_larger_wr:
                context['do_not_update_nearest_larger_wr'] = False
        return result
                
    #Push data to employee if contract is erliest main contract and record are active
    #if employee dont have any valid contract at root company and record are active, push data
    def push_data_to_employee(self, cr, uid, ids, context=None):
        if not context:
            context = {}
            
        context['user_id'] = uid
        uid = SUPERUSER_ID
        if ids:
            parameter_obj = self.pool.get('ir.config_parameter')
            change_form_obj = self.pool.get('vhr.change.form')
            emp_obj = self.pool.get('hr.employee')
            
            terminated_code = parameter_obj.get_param(cr, uid, 'vhr_master_data_dismiss_change_form_code') or ''
            terminated_code = terminated_code.split(',')
            dismiss_change_form_ids = change_form_obj.search(cr, uid, [('code', 'in', terminated_code)],context=context)
            
            
            back_to_work_code = parameter_obj.get_param(cr, uid, 'vhr_master_data_back_to_work_change_form_code') or ''
            back_to_work_code = back_to_work_code.split(',')
            back_work_form_ids = change_form_obj.search(cr, uid, [('code','in',back_to_work_code)])
            
            input_data_code = parameter_obj.get_param(cr, uid, 'vhr_master_data_input_data_into_iHRP') or ''
            input_data_code = input_data_code.split(',')
            input_data_form_ids = change_form_obj.search(cr, uid, [('code','in',input_data_code)])
            
            change_type_code = parameter_obj.get_param(cr, uid, 'vhr_master_data_change_type_of_contract') or ''
            change_type_code = change_type_code.split(',')
            change_type_form_ids = change_form_obj.search(cr, uid, [('code','in',change_type_code)])
            
            join_company_form_ids = back_work_form_ids + input_data_form_ids + change_type_form_ids
            
            active_employee_ids = []
            inactive_employee_ids = []
            update_employee_ids = []
            wr_join_company_ids = []
            records = self.browse(cr, uid, ids, context)
            
            today = datetime.today().date()
            
            for record in records:
                #Only push data if record are active
                if record.active:
                    employee_id = record.employee_id and record.employee_id.id or False
                    company_id = record.company_id and record.company_id.id or False
                    #Update employee instance
#                     self.pool.get('vhr.employee.instance').update_employee_instance(cr, uid, record.id, context)
                    mcontext = {'effect_date': record.effect_from}
                    if employee_id:
                        default_comp_id, comp_ids = self.get_company_ids(cr, uid, employee_id, mcontext)
                        if default_comp_id == company_id:
                            update_employee_ids.append(employee_id)

                    #Check to active, inactive employee
                    change_form_ids = [form.id for form in record.change_form_ids]
                    if change_form_ids:
                        if set(change_form_ids).intersection(set(join_company_form_ids)):
                            wr_join_company_ids.append(record.id)
                                
                        #Inactive employee when have WR with change form dismiss and termination_id.is_change_contract_type = False
                        if set(change_form_ids).intersection(set(dismiss_change_form_ids)) and not record.is_change_contract_type:
                            instance_ids = self.pool.get('vhr.employee.instance').search(cr, uid, [('employee_id','=',employee_id),
                                                                                                   ('date_start','<=',today),
                                                                                                   '|',('date_end','=',False),
                                                                                                       ('date_end','>',today)])
                            if not instance_ids:
                                inactive_employee_ids.append(employee_id)
                        
                        #Active employee when WR have
                        elif set(change_form_ids).intersection(set(join_company_form_ids)) and record.employee_id and not record.employee_id.active:
                            active_employee_ids.append(employee_id)
                            
            if update_employee_ids:
                context['wr_join_company_ids'] = wr_join_company_ids
                emp_obj.update_employee(cr, uid, update_employee_ids, context)
            
            if active_employee_ids:
                emp_obj.write_with_log(cr, uid, active_employee_ids, {'active': True}, context)
                
                active_emps = emp_obj.read(cr, uid, active_employee_ids, ['user_id'])
                active_user_ids = [emp.get('user_id', False) and emp['user_id'][0] for emp in active_emps]
                active_user_ids = [item for item in active_user_ids if item ]
                self.pool.get('res.users').write(cr, SUPERUSER_ID, active_user_ids, {'active': True})
            
            if inactive_employee_ids:
                emp_obj.write_with_log(cr, uid, inactive_employee_ids, {'active': False}, context)
                
                inactive_emps = emp_obj.read(cr, uid, inactive_employee_ids, ['user_id'])
                inactive_user_ids = [emp.get('user_id', False) and emp['user_id'][0] for emp in inactive_emps]
                inactive_user_ids = [item for item in inactive_user_ids if item ]
                self.pool.get('res.users').write(cr, SUPERUSER_ID, inactive_user_ids, {'active': False})
        
        return True

    def cron_update_working_record_state(self, cr, uid, context=None):
        """
        Update state of record if satisfy condition of active
            set = True: effect_from <= today <= effect_to; contract.state=signed
        Push data to employee from record just active
        
        """
        if not context:
            context = {}
            
        log.info('start cron update WR state')
        today = datetime.today().date()
        working_record_ids = []
        #Get WR have active=False need to update active=True
        active_record_ids = self.search(cr, uid, [('active','=',False),
                                                  ('state','in',[False,'finish']),
                                                  ('effect_from','<=',today),
                                                  '|',('effect_to','=',False),
                                                       ('effect_to','>=',today)])
        
        #Get WR have active=True need to update active=False
        inactive_record_ids = self.search(cr, uid, [('active','=',True),
                                                    ('state','in',[False,'finish']),
                                                      '|',('effect_to','<',today),
                                                           ('effect_from','>',today)])
        
        #Find Termination WR should be active, effect_from < today, lead(effect_from) > today
        sql = """
                SELECT temp_table.id, temp_table.employee_id,temp_table.effect_from, temp_table.effect_to FROM 

                    (SELECT id, employee_id,state,effect_from,effect_to,active,
                            lead(effect_from) over (partition by employee_id, company_id order by effect_from asc) as ftr_effect_from
                     FROM vhr_working_record where state is null or state='finish') temp_table 
                                               INNER JOIN working_record_change_form_rel rel on temp_table.id=rel.working_id 
                                               
                WHERE (temp_table.state = 'finish' or temp_table.state is Null) and temp_table.effect_from = temp_table.effect_to 
                    and temp_table.effect_from < '{0}' and (temp_table.ftr_effect_from > '{0}' or temp_table.ftr_effect_from is null ) 
                    and rel.change_form_id = 6
                    and temp_table.effect_from > '{1}'
              """
              
        two_month_ago = today - relativedelta(months=3)
        
        cr.execute(sql.format(today,two_month_ago))
        res = cr.fetchall()
        active_terminate_wr_ids = [item[0] for item in res]
        active_record_ids.extend(active_terminate_wr_ids)
        inactive_record_ids = list( set(inactive_record_ids).difference(set(active_terminate_wr_ids)) )
        
        #Do not active again with termination WR actived before
        if active_terminate_wr_ids:
            do_not_need_to_active_more_ids = self.search(cr, uid, [('id','in',active_terminate_wr_ids),
                                                                   ('active','=',True)])
            
            active_record_ids = list(set(active_record_ids).difference(set(do_not_need_to_active_more_ids)))
        
        
        working_record_ids = active_record_ids + inactive_record_ids
        if working_record_ids:
            context['do_not_check_to_update_and_pus_data_to_hr_employee'] = True
            context['disable_check_allowance'] = True
            import time
            time1=time.time()
            active_ids = self.set_active_record(cr, uid, active_record_ids, context)
            log.info('Active working record::' +str(active_ids))
            
            super(vhr_working_record, self).write(cr, uid, inactive_record_ids, {'active': False})
            time2 = time.time()
            if active_ids:
                self.push_data_to_employee(cr, uid, active_ids, context)
            time3 = time.time()
            
            self.update_other_data_with_active_record(cr, uid, active_ids, context)
            
            
            log.info("Time to run cron WR: %s, %s"%(time2-time1,time3-time2))
            log.info("Active WR: %s, Inactive WR:%s"%(len(active_ids),len(inactive_record_ids)))
        
        
        log.info('end cron update WR state')
        return True
    
    def update_other_data_with_active_record(self, cr, uid, active_ids, context=None):
        pass
    
    def cron_push_data_to_employee(self, cr, uid, codes=[], context=None):
        """
        codes is tuple employee to add into domain find active working record for push data to employee
        """
        if not context:
            context = {}
            
        employee_obj = self.pool.get('hr.employee')
        today = datetime.today().date()
        
        domain = [('active','=',True),
                  ('state','in',[False,'finish']),
                  ('effect_from','<=',today),
                  '|',('effect_to','=',False),
                       ('effect_to','>=',today)]
        
        domain_emp = [('active','=',True)]
        if codes:
            domain_emp.append(('code','in', codes))
        
        if context.get('division_id', False):
            domain_emp.append(('division_id','in', context['division_id']))
        elif context.get('department_id', False):
            domain_emp.append(('department_id','in', context['department_id']))
            
        employee_ids = employee_obj.search(cr, uid, domain_emp)
        domain.insert(0, ('employee_id','in', employee_ids))
            
        log.info('start cron push data to employee')
        active_ids = self.search(cr, uid, domain)
        active_ids = active_ids
        import time
        time1=time.time()
        if active_ids:
            self.push_data_to_employee(cr, uid, active_ids)
        
        time2 = time.time()
        log.info("Time to run cron push data to employee: %s"%(time2-time1))
        log.info("Number of WR active: %s"% len(active_ids))
            
        log.info('end cron push data to employee')
        return True
    
    def cron_update_effect_to_of_dismiss_wr(self, cr, uid, *args):
        """
        Update effect_to  = effect_from of dismiss WR have effect_from != effect_to
        """
        dismiss_change_form_ids = self.get_dismiss_change_form_ids(cr, uid, context={})
        sql = """
                SELECT wr1.id from vhr_working_record wr1 inner join vhr_working_record wr2 ON wr1.id=wr2.id
                                                     inner join working_record_change_form_rel rel ON wr1.id=rel.working_id
                WHERE     (wr1.state = 'finish' or wr1.state is null)
                      and  ( wr1.effect_from != wr2.effect_to or wr2.effect_to is null)  
              """
        
        extend = ""
        for form_id in dismiss_change_form_ids:
            if extend:
                extend += ' or '
            extend += " rel.change_form_id = " + str(form_id)
        
        sql += " and (" + extend + ")"
        
        cr.execute(sql)
        
        res = cr.fetchall()
        wr_ids = [item[0] for item in res]
        
        if wr_ids:
            for wr_id in wr_ids:
                wr = self.read(cr, uid, wr_id, ['effect_from'])
                super(vhr_working_record, self).write(cr, uid, wr_id, {'effect_to': wr.get('effect_from', False)})
        
        return True
        
        
    
    def set_active_record(self, cr, uid, ids, context=None):
        '''
        Set active = True if record in ids have contract.state=signed
        '''
        res = []
        
        record_id = False
        try:
            for record in self.browse(cr, uid, ids, fields_process=['contract_id']):
                record_id = record.id
                state_contract = record.contract_id and record.contract_id.state or False
                if state_contract == 'signed':
                    self.write(cr, uid, record.id, {'active': True}, context)
                    res.append(record.id)
        except Exception as e:
            log.exception(e)
            error_message = ''
            try:
                error_message = e.message
                if not error_message:
                    error_message = e.value
            except:
                error_message = ""
            
            description = traceback.format_exc()
            parameter = "Cron update_working_record_state:: Write to record %s with parameter: %s"%(record_id, str({'active':True}))
            self.pool.get('vhr.log.error.system').create_from_data(cr, uid, 'vhr_human_resource', 'vhr.working.record', description, parameter)
             
            raise osv.except_osv('Error !', 'Error when active Working Record: \n\n %s' % error_message)
        
        return res

    
    def check_dates(self, cr, uid, ids, context=None):
        for record in self.read(cr, uid, ids, ['effect_from', 'effect_to'], context=context):
            if record.get('effect_from',False) and record.get('effect_to',False) and record['effect_from'] > record['effect_to']:
#                 return False
                raise osv.except_osv('Validation Error !', 'Effect To must be greater than Effect From !')

        return True
    
    #Can not create movement or working record when employee still have a movement does not finish
    def check_staff_movement_on_effect_from(self, cr, uid, vals, context=None):
        if not context:
            context = {}
        
        current_record_id = False
        if context.get('current_check_record', False):
            current_record_id = context['current_check_record']
            
        if vals and vals.get('employee_id', False) and vals.get('company_id', False) and vals.get('effect_from',False):
            employee = self.pool.get('hr.employee').read(cr, uid, vals['employee_id'], ['login'])
            effect_from_str = datetime.strptime(vals['effect_from'],DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y")
            
            args =  [('employee_id','=',vals['employee_id']), 
                     ('company_id','=',vals['company_id']), 
                     ('effect_from','=',vals['effect_from'])]
            
            #Search for record in flow 
            wr_args = args + [('state','in',[False,'finish'])]
            wr_ids = self.search(cr, uid, wr_args)
            if current_record_id in wr_ids:
                wr_ids.remove(current_record_id)
            if wr_ids:
                
                raise osv.except_osv('Validation Error !', 
                                     '%s has a working record on %s '% (employee.get('login'),effect_from_str) )
            
            #Search for record in step to be working record (staff movement)s
            st_args = [('employee_id','=',vals['employee_id']), 
                       ('company_id','=',vals['company_id']),
                       ('state','not in',[False,'cancel','finish'])]
            
            movement_ids = self.search(cr, uid, st_args)
            if current_record_id in movement_ids:
                movement_ids.remove(current_record_id)
            if movement_ids:
                dup_record = self.read(cr, uid, movement_ids[0], ['effect_from'])
                effect_from_str = datetime.strptime(dup_record.get('effect_from',False),DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y")
                
                raise osv.except_osv('Validation Error !', 
                                     '%s has a staff movement does not finish on %s '% (employee.get('login'),effect_from_str) )
            else:
                mass_movement_ids = self.pool.get('vhr.mass.movement').search(cr, uid, [('company_id','=',vals['company_id']),
                                                                                        ('employee_ids','=',vals['employee_id']),
                                                                                        ('state','not in',['cancel','finish'])])
                
                #Fix bug, call create working record when not complete write in mass movement
                if context.get('create_from_fin_mass_movement',False):
                    finish_mass_movement = context['create_from_fin_mass_movement']
                    mass_movement_ids = [record_id for record_id in mass_movement_ids if record_id not in finish_mass_movement]
                if mass_movement_ids:
                    dup_record = self.pool.get('vhr.mass.movement').read(cr, uid, mass_movement_ids[0], ['effect_from'])
                    effect_from_str = datetime.strptime(dup_record.get('effect_from',False),DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y")
                    
                    raise osv.except_osv('Validation Error !', 
                                     '%s has a mass request does not finish on %s '% (employee.get('login'),effect_from_str) )
        
        return True

    def check_change_data(self, cr, uid, ids, context=None):
        #Raise warning if dont have any change between old and new
        if not context:
            context = {}
        if ids:
            if not isinstance(ids, list):
                ids = [ids]
            
            fields = []
            for item in dict_fields:
                fields.append(item[0])
                fields.append(item[1])
            fields.append('change_form_ids')
            fields.append('termination_id')
            records = self.read(cr, uid, ids, fields)
            
            parameter_obj = self.pool.get('ir.config_parameter')
            change_form_obj = self.pool.get('vhr.change.form')
            
            code_list = self.get_code_change_form_new_to_company(cr, uid, context)
            
            dismiss_local_comp_code = parameter_obj.get_param(cr, uid, 'vhr_master_data_dismiss_local_company') or ''
            dismiss_local_comp_code = dismiss_local_comp_code.split(',')
            
            not_need_change_form_list = code_list + dismiss_local_comp_code
            not_need_change_form_ids = change_form_obj.search(cr, uid, [('code','in',not_need_change_form_list)])
            
            context['not_need_change_form_ids'] = not_need_change_form_ids
            for record in records:
                is_change = self.check_change_data_in_record(cr, uid, record, dict_fields, context)
                
                if not is_change:
                    raise osv.except_osv('Validation Error !', 
                                         'There is nothing change in page Detail !')
        return True
    
    def check_change_data_in_record(self, cr, uid, record, dict_fields, context=None):
        """
        Return False if record.termination_id != False or context['create_from_contract']!= None
        Return False if change_form in dismiss_local, new_company
        """
        if not context:
            context = {}
        
        not_need_change_form_ids = context.get('not_need_change_form_ids', [])
        is_change = False
        if record:
             #Do not check if working record is create from termination or create from contract
            if record.get('termination_id',False) or context.get('create_from_contract',False):
                return True
            
            #Neu change form la quay lai lam viec hoac input to iHRP thi khong check change data
            change_form_ids = record.get('change_form_ids',[])
            if len(change_form_ids) == 1 and change_form_ids[0] in not_need_change_form_ids:
                return True
             
            is_change = False
            for item in dict_fields:
                if record.get(item[0], False) != record.get(item[1], False):
                    is_change = True
        
        return is_change
    
    
    #Return list WR have same emp-comp and have effect_from >input_effect_from
    def get_larger_working_record(self, cr, uid, employee_id, company_id, effect_from, context=None):
        nearest_larger_working_ids = []
        if employee_id and company_id and effect_from:
            nearest_larger_working_ids = self.search(cr, uid, [('employee_id','=',employee_id),
                                                               ('company_id','=',company_id),
                                                               ('effect_from','>',effect_from),
                                                               ('state','in',[False,'finish'])], order='effect_from asc')
            
        return nearest_larger_working_ids
    
    def get_nearest_lower_working_record(self, cr, uid, employee_id, company_id, effect_from, context=None):
        nearest_lower_working_ids = []
        if employee_id and company_id and effect_from:
            nearest_lower_working_ids = self.search(cr, uid, [('employee_id','=',employee_id),
                                                               ('company_id','=',company_id),
                                                               ('effect_from','<',effect_from),
                                                               ('state','in',[False,'finish'])], order='effect_from desc')
            
        return nearest_lower_working_ids
    
    #Update data old-new of nearest larger WR in same emp-comp
    def update_data_of_future_working_record(self, cr, uid, record_id, vals, context=None):
        if not context:
            context = {}    
        if record_id and (vals or context.get('update_all_data_from_old_record',False)):
            nearest_larger_working_ids = []
            if context.get('nearest_larger_working_ids', False):
                nearest_larger_working_ids = context['nearest_larger_working_ids']
            else:
                record = self.read(cr, uid, record_id, ['employee_id','company_id','effect_from'])
                
                employee_id = record.get('employee_id', False) and record['employee_id'][0]
                company_id = record.get('company_id', False) and record['company_id'][0]
                effect_from = record.get('effect_from', False)
                
                if employee_id and company_id and effect_from:
                    #Search WR have effect_from > edit/create WE
                    nearest_larger_working_ids = self.get_larger_working_record(cr, uid, employee_id, company_id, effect_from, context)
                
            if nearest_larger_working_ids:
                translate_dict = {}
                fields_new = []
                #Get list of all field new
                for item in dict_fields:
                    translate_dict[item[1]] = item[0]
                    fields_new.append(item[1])
                        
                data_for_larger_wr = {}
                #These code for case: `1.You have a movement on day 10,
                                      #2.You create a WR on day 8 and day 12
                                      #3.When movement finish, we need to get data from "New" in WR day 8  to "Old" of finish movement on day 10
                                      #4.Get data from "New" of movement on day 10 to "Old" of WR on day 12
                if context.get('update_all_data_from_old_record', False):
                    data = self.read(cr, uid, record_id, fields_new)
                    for field in fields_new:
                        if isinstance(data[field], tuple):
                            data[field] = data[field][0]
                        
                        data_for_larger_wr[translate_dict[field]] = data[field]
                        #Update "New" data from nearest WR to "Old"-"New" data of termination WR
                        if context.get('termination_id', False):
                            data_for_larger_wr[field] = data[field]
                else:
                    for field in vals.keys():
                        if field in fields_new:
                            data_for_larger_wr[translate_dict[field]] = vals[field]
                
                if data_for_larger_wr:
                    super(vhr_working_record, self).write(cr, uid, nearest_larger_working_ids[0], data_for_larger_wr, context)
                    
        return True
    
    def update_effect_to_of_current_wr(self, cr, uid, record_id, employee_id, company_id, effect_from, context=None ):
        if employee_id and company_id and effect_from:
            nearest_larger_working_ids = self.get_larger_working_record(cr, uid, employee_id, company_id, effect_from, context)
            #if nearest_larger_working_ids have data, its mean user is create WR in middle of flow WRs
            if nearest_larger_working_ids:
                #If WR is termination, dont need to update effect_to
                is_terminate_wr = self.is_terminate_wr(cr, uid, record_id, [], context)
                if is_terminate_wr:
                    return nearest_larger_working_ids
                
                #Update effect_to of current WR = effect_from_of_larger_WR - 1
                nearest_larger_working_id = nearest_larger_working_ids[0]
                nearest_larger_working = self.read(cr, uid, nearest_larger_working_id, ['effect_from'])
                
                effect_from = datetime.strptime(nearest_larger_working['effect_from'], DEFAULT_SERVER_DATE_FORMAT).date()
                create_working_effect_to = effect_from - relativedelta(days=1)
                create_working_effect_to = create_working_effect_to.strftime(DEFAULT_SERVER_DATE_FORMAT)
                
                update_vals = {'effect_to': create_working_effect_to}
#                 context['do_not_check_to_update_and_pus_data_to_hr_employee'] = True
#                 context['do_not_update_nearest_larger_wr'] = True
                super(vhr_working_record, self).write(cr, uid, record_id, update_vals, context)
                return nearest_larger_working_ids
            
        return []
        
    def check_promotion_demotion_change_form(self, cr, uid, ids, context=None):
        '''
        Nếu SM có chứa loại "Tăng chức" hoặc "Giáng chức" thì khi lưu cần kiểm tra chức vụ thay đổi có phù hợp theo không
        (Nếu "Giáng chức" thì chức vụ mới phải cao hơn chức vụ cũ và ngược lại)
        '''
        if ids:
            promotion_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_human_resource_change_form_code_promotion') or ''
            promotion_code = promotion_code.split(',')
            promotion_change_form_ids = self.pool.get('vhr.change.form').search(cr, uid, [('code','in',promotion_code)])
            
            demotion_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_human_resource_change_form_code_demotion') or ''
            demotion_code = demotion_code.split(',')
            demotion_change_form_ids = self.pool.get('vhr.change.form').search(cr, uid, [('code','in',demotion_code)])
            
#             job_level_obj = self.pool.get('vhr.job.level')
            for record in self.read(cr, uid, ids, ['change_form_ids','job_level_person_id_new','job_level_person_id_old']):
                change_form_ids = record.get('change_form_ids',[])
                job_level_old = record.get('job_level_person_id_old',False) and record['job_level_person_id_old'][1] or 0
                
                job_level_new = record.get('job_level_person_id_new',False) and record['job_level_person_id_new'][1] or 0
                
                #Have change form promotion in change_form_ids
                if set(change_form_ids).intersection(set(promotion_change_form_ids)) and job_level_old >= job_level_new:
                    raise osv.except_osv('Validation Error !', 
                                         'With change form "Promotion", Level of new Person Level must be greater than Level of old Person Level ')
                elif set(change_form_ids).intersection(set(demotion_change_form_ids)) and job_level_new >= job_level_old:
                    raise osv.except_osv('Validation Error !', 
                                         'With change form "Demotion", Level of new Person Level must be lower than Level of old Person Level ')
                
        return True
    
    def onchange_attachment_ids(self, cr, uid, ids, attachment_temp_ids, context=None):
        res = {'attachment_count': 0}
        if attachment_temp_ids:
            attachment_count = 0
            for attachment in attachment_temp_ids:
                attachment_count += 1
                
            res['attachment_count'] = attachment_count
            
        return {'value': res}
    
    def salary_validation(self, cr, uid, data, context=None):
        if data:
            sum = 0
            if 'salary_percentage_new' in data and data['salary_percentage_new'] <0:
                raise osv.except_osv('Validation Error !', "% Basic Salary must be greater than or equal to 0, lower than or equal to 100")
            
            if data.get('basic_salary_new',0):
                sum += data.get('basic_salary_new',0)
            if data.get('kpi_amount_new',0):
                sum += data.get('kpi_amount_new',0)
            
            v_bonus = data.get('v_bonus_salary_new', 0)
            if not v_bonus:
                v_bonus = data.get('general_allowance_new',0)
            
            if v_bonus:
                sum += v_bonus
                
            if sum != data.get('gross_salary_new',0):
                raise osv.except_osv('Validation Error !', "Summarize of V_Bonus, KPI and Basic salary must equal to Gross Salary")
            
            basic_salary_new = data.get('basic_salary_new', 0) or 0
            gross_salary_new = data.get('gross_salary_new', 0) or 0
            if basic_salary_new > gross_salary_new:
                    raise osv.except_osv('Validation Error !', 'Basic Salary must be lower than Gross Salary')
        
        return True
    
    
    def create(self, cr, uid, vals, context={}):
        try:
            if not context:
                context = {}
            
            if vals.get('force_to_insert_last', False) and not vals.get('state',False):
                greater_ids = self.search(cr, uid, [('employee_id','=', vals.get('employee_id', False)),
                                                    ('company_id','=',vals.get('company_id', False)),
                                                    ('state','in', [False, 'finish']),
                                                    ('effect_from','>', vals.get('effect_from', False))])
                if greater_ids:
                    raise osv.except_osv('Validation Error !', 
                                         'You are not allowed to insert Working Record at the middle of WR flow with option "Force To Insert At Last" equal True') 
            
            change_form_pool = self.pool.get('vhr.change.form')
            change_form_ids = vals['change_form_ids'][0][2]
             #Can not create movement or working record when employee still have a movement does not finish
            self.check_staff_movement_on_effect_from(cr, uid, vals, context)
            
            dismiss_local_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_master_data_dismiss_local_company') or ''
            dismiss_local_code_list = dismiss_local_code.split(',')
            dismiss_local_code_ids = change_form_pool.search(cr, uid, [('code','in',dismiss_local_code_list)])
        
            #Special case when create working record from termination
            #Delete other created record after effect_from of termination working record
            if context.get('termination_id', False) or set(dismiss_local_code_ids).intersection(set(change_form_ids)):
                self.delete_others_after_current_record(cr, uid, vals.get('employee_id',False), vals.get('company_id', False), vals.get('effect_from', False), context )
            
            if vals.get('update_mask_data_in_create', False):
                log.info("Update mask data in create WR")
                groups = self.get_groups(cr, uid, context)
                if 'vhr_assistant_to_hrbp' in groups and 'vhr_hrbp' not in groups:
                    groups.append('vhr_hrbp')
                    
                nearest_wr_data,domain,latest_working_record_id= self.get_data_from_nearest_working_record(cr, uid, vals.get('employee_id',False), vals.get('company_id',False), 
                                                                                                           vals.get('effect_from', False), vals.get('contract_id', False), context)
                #Get correct data, when mask data in onchange_effect if user dont have power to read these fields
                
                for field in ['job_level_person_id_old','job_level_person_id_new']:
                    args_readonly, args_invisible = self.build_args_for_field(cr, uid, field, groups, context)
                    if args_invisible:
                        vals[field] = nearest_wr_data.get(field, False)
                        if isinstance(vals[field], tuple):
                            vals[field] = vals[field][0]
                                    
                                    
            vals.update({'is_new': False})
            if vals.get('state', False):
                vals['current_state'] = vals['state']
            
            vals = self.update_correct_new_data_in_wr_based_on_change_form(cr, uid, [], vals, context)
            
            contract_id = vals.get('contract_id', False)
            if contract_id:
                contract = self.pool.get('hr.contract').read(cr, uid, contract_id, ['contract_type_group_id'])
                type_group_id = contract.get('contract_type_group_id', False) and contract['contract_type_group_id'][0]
                if type_group_id:
                    contract_type = self.get_contract_type(cr, uid, type_group_id, context)
            
                
            if vals.get('update_salary_in_create', False):
                res_salary = self.get_data_from_nearest_payroll_salary(cr, SUPERUSER_ID, False, vals.get('employee_id',False), 
                                                                       vals.get('company_id', False), vals.get('effect_from', False), context)
                if res_salary:
                    vals.update(res_salary)
            
            elif vals.get('gross_salary_new',0) and contract_type in [CT_OFFICIAL, CT_PROBATION] \
               and set(['kpi_amount_new','v_bonus_salary_new','basic_salary_new']).intersection(vals.keys()):
                
                self.salary_validation(cr, uid, vals, context)
                    
            
            vals = self.check_to_update_effect_to_of_termination_wr(cr, uid, [], vals, context)
            
            res = super(vhr_working_record, self).create(cr, uid, vals, context)
            
            
            #Raise error if nothing change between Old and New collumn
            if not context.get('do_not_check_change_data', False):
                self.check_change_data(cr, uid, [res], context)
            
            self.check_promotion_demotion_change_form(cr, uid, [res], context)
            
            #Create appendix contract if change salary in WR
            if vals.get('state', False) == False and (
                vals.get('gross_salary_old', False) != vals.get('gross_salary_new', False) or \
                vals.get('salary_percentage_old', False) != vals.get('salary_percentage_new', False) or \
                vals.get('collaborator_salary_old', False) != vals.get('collaborator_salary_new', False) or \
                vals.get('type_of_salary_old', False) != vals.get('type_of_salary_new', False) ):
                self.check_to_create_update_appendix_contract(cr, uid, [res], context)
                
            #TODO: check again with create_in_middle
            if res and vals.get('effect_from', False):
                    
                self.check_dates(cr, uid, [res], context)
                #Only update effect_to of latest working record when not create in movement
                if vals.get('state', False) in ['finish',False] :
                    #Update nearest WR
                    self.update_nearest_working_record_info(cr, uid, [res], context)
                
                #Update effect_to of current record if have larger WR
                nearest_larger_working_ids = self.update_effect_to_of_current_wr(cr, uid, res, vals['employee_id'], vals['company_id'], vals['effect_from'], context)
                #Update data of future WR if create WR have state=False
                if nearest_larger_working_ids and not vals.get('state',False):
                    context['nearest_larger_working_ids'] =  nearest_larger_working_ids
                    self.update_data_of_future_working_record(cr, uid, res, vals, context)
                
                context['state'] = vals.get('state', False)
                self.check_overlap_date(cr, uid, [res], context)
                
                context['check_employee_instance'] = True
                active_ids = self.update_working_record_state(cr, uid, [res], context)
                if active_ids:
                    self.push_data_to_employee(cr, uid, active_ids, context)
#                     self.update_other_data_with_active_record(cr, uid, active_ids, context)
                    
                elif res and vals.get('state', False) in [False,'finish']:
                    #update liquidation date in contract from Terminate WR when create new WR if new WR is inactive
                    record = self.read(cr, uid, res, ['employee_id','effect_from','change_form_ids','contract_id'])
                    self.update_liquidation_date_of_contract(cr, uid, record, context)
                    
            #update employee instance
            emp_instance = self.pool.get('vhr.employee.instance')
            emp_instance.update_employee_instance(cr, uid, res, context)
            return res
        
        except Exception as e:
            log.exception(e)
            error_message = ''
            try:
                error_message = e.message
                if not error_message:
                    error_message = e.value
            except:
                error_message = ""
            
            remove_message = 'Have error during update working record:'
            if remove_message in error_message:
                error_message = error_message.replace(remove_message, '')
            #when remove '\n' out of raise message, need to check again raise message at function create_working_record in hr_contrac
            raise osv.except_osv('Validation Error !', 'Have error during create working record:\n %s!' % error_message)
        
    def write(self, cr, uid, ids, vals, context={}):
        try:
            if not context:
                context = {}
            
            if not isinstance(ids, list):
                ids = [ids]
            
            change_form_pool = self.pool.get('vhr.change.form')
            
            #If only update active = False, I dont think its need to check or update anything
            if len(vals) == 1 and 'active' in vals and vals.get('active', False) == False:
                res = super(vhr_working_record, self).write(cr, uid, ids, vals, context)
                return res
            
            
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
            
            vals = self.update_correct_new_data_in_wr_based_on_change_form(cr, uid, ids, vals, context)
#                 
            
            if vals.get('effect_from', False):
                
                records = self.read(cr, uid, ids, ['effect_from'])
                context['old_effect_from'] = records[0].get('effect_from', False)
                self.check_if_update_effect_from_out_of_box(cr, uid, ids, vals, context)
                self.check_to_update_effect_to_of_termination_wr(cr, uid, ids, vals, context)
                
            res = super(vhr_working_record, self).write(cr, uid, ids, vals, context)
            
            records = self.read(cr, uid, ids,['state','change_form_ids','contract_id','effect_from','active','employee_id','company_id','salary_percentage_new',
                                              'termination_id','gross_salary_new','basic_salary_new','kpi_amount_new','v_bonus_salary_new','general_allowance_new'])
            if res:
                
                #TODO: check again Raise error if nothing change between Old and New collumn
                is_check_change_data = False
                for field in vals.keys():
                    if 'old' in field or 'new' in field:
                        is_check_change_data = True
                        break
                
                if is_check_change_data or vals.get('change_form_ids',False):
                    self.check_change_data(cr, uid, ids, context)
                
                dismiss_local_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_master_data_dismiss_local_company') or ''
                dismiss_local_code_list = dismiss_local_code.split(',')
                dismiss_local_code_ids = change_form_pool.search(cr, uid, [('code','in',dismiss_local_code_list)])
            
                for record in records:
                    record_id = record.get('id',False)
                    state = record.get('state', False)
                    active = record.get('active', False)
                    employee_id = record.get('employee_id',False) and record['employee_id'][0] or False
                    company_id = record.get('company_id',False) and record['company_id'][0] or False
                    effect_from = record.get('effect_from',False) or False
                    updated_liquidation = False
                    
                    change_form_ids = record.get('change_form_ids', [])
                    
                    contract_type = False
                    contract_id = vals.get('contract_id', False)
                    if contract_id:
                        contract = self.pool.get('hr.contract').read(cr, uid, contract_id, ['contract_type_group_id'])
                        type_group_id = contract.get('contract_type_group_id', False) and contract['contract_type_group_id'][0]
                        if type_group_id:
                            contract_type = self.get_contract_type(cr, uid, type_group_id, context)
                    
                    #Special case when update working record from termination
                    #Delete other created record after effect_from of termination working record(except wr with change form gia nhap cty,back to work)
                    if context.get('update_from_termination', False) or (set(dismiss_local_code_ids).intersection(set(change_form_ids)) and vals.get('effect_from', False)):
                        context.update({'current_working_record_id': record_id})
                        self.delete_others_after_current_record(cr, uid, employee_id, company_id, effect_from, context)
                        context['update_from_termination'] = False
    
                    
                    if set(['gross_salary_new','basic_salary_new','kpi_amount_new','v_bonus_salary_new',
                            'salary_percentage_new']).intersection(set(vals.keys())) and contract_type in [CT_OFFICIAL, CT_PROBATION]:
                        self.salary_validation(cr, uid, record, context)
                        
                    #If have change in state, effect_from, effect_to, active 
    
                    if set(['state','effect_from','effect_to','active']).intersection(set(vals.keys())):
                        
                        if vals.get('effect_from',False):
                            rvals = {'employee_id':employee_id, 'company_id':company_id,'effect_from':effect_from}
                            context.update({'current_check_record': record_id})
                            self.check_staff_movement_on_effect_from(cr, uid, rvals, context)
                        
    #                   If change state in staff movement to finish or change effect_from in WR dont have state, update effect_from of latest WR, effect_to of current WR if need
                        if vals.get('state',False) == 'finish' or (vals.get('effect_from',False) and state in [False, 'finish']):
                                        
                            self.update_effect_to_of_current_wr(cr, uid, record_id, employee_id, company_id, effect_from, context)
                            self.update_nearest_working_record_info(cr, uid, [record_id], context)
                            context['do_not_check_to_update_and_pus_data_to_hr_employee'] = False
                            context['do_not_update_nearest_larger_wr'] = False
                            context['do_not_create_update_pr_salary'] = False
                            #If edit date_end_working of termination, when update effect_from of WR, try to update liquidation_date of contract
#                             if active or vals.get('active', False):
                            self.update_liquidation_date_of_contract(cr, uid, record, context)
                            updated_liquidation = True
                            
                            
                        #If change state,effect_from,effect_to, then change date(effect_from must lower/equal effect_to) 
                                                                    #check overlap with other record, if record is movement, then only check with effect_from of latest WR
                        if vals.get('state',False) or vals.get('effect_from',False) or vals.get('effect_to',False):
                            self.check_dates(cr, uid, [record_id], context)
                            context['state'] = state
                            self.check_overlap_date(cr, uid, [record_id], context)
                        
                        #If 'do_not_check_to_update_and_pus_data_to_hr_employee' dont have in context, update WR state and push if have change state
                        if not context.get('do_not_check_to_update_and_pus_data_to_hr_employee', False) and state in [False,'finish']:
                            active_ids = self.update_working_record_state(cr, uid, [record_id], context)
                            
                            new_active = False
                            if not active_ids:
                                record = self.read(cr, uid, record_id, ['active'])
                                new_active = record.get('active', False)
                                
                            if active_ids or new_active:
                                self.push_data_to_employee(cr, uid, active_ids, context)
#                                 self.update_other_data_with_active_record(cr, uid, active_ids, context)
                        
                        #Update date_end of contract when active working record with change form = termination
                        if vals.get('active', False) and not updated_liquidation:
                            self.update_liquidation_date_of_contract(cr, uid, record, context)
                        
                                
                    elif active and not context.get('do_not_push_data_to_employee',False):
                        #Update info in employee, if edit active record
                        self.push_data_to_employee(cr, uid, [record_id], context)
#                         self.update_other_data_with_active_record(cr, uid, [record_id], context)
                        #Update employee instance, if edit information in active record
                        self.pool.get('vhr.employee.instance').update_employee_instance(cr, uid, record_id, context)
                        
                    #Try to update data of nearest larger effect_from WR of same emp-comp
                    if not context.get('nearest_larger_working_ids', False) and not context.get('do_not_update_nearest_larger_wr',False)\
                     and (vals.get('state',False) == 'finish' or not state):
                        #Update "Old" of movement or Terminate WR from "New" of nearest WR
                        if vals.get('state',False) == 'finish' or (record.get('termination_id',False) and vals.get('effect_from',False)):
                            context['update_all_data_from_old_record'] = True
                            context['editing_record'] = record_id
                            context['effect_from'] = effect_from
                            latest_working_record_id, is_same_contract = self.get_latest_working_record(cr, uid, employee_id, company_id, True, context)
                            
                            if latest_working_record_id:
                                context['termination_id'] = record.get('termination_id', False)
                                self.update_data_of_future_working_record(cr, uid, latest_working_record_id, {}, context)
                                context['termination_id'] = False
                        
                        #Update 'Old' of Larger WR from "New" of current WR
                        self.update_data_of_future_working_record(cr, uid, record_id, vals, context)
                    
                    if set(['job_title_id_new','job_level_person_id_new','change_form_ids']).intersection(set(vals.keys())):
                        self.check_promotion_demotion_change_form(cr, uid, [record_id], context)
            
            if set(['gross_salary_new','basic_salary_new','kpi_amount_new','general_allowance_new','v_bonus_salary_new','collaborator_salary_new',
                    'salary_percentage_new','type_of_salary','state','effect_from','job_title_id_new']).intersection(set(vals.keys())):
                self.check_to_create_update_appendix_contract(cr, uid, ids, context)
                
             #Update to contract, if WR is first_wr of contract
            if not context.get('update_from_contract', False) and not context.get('do_not_update_to_contract',False):
                self.update_data_to_contract(cr, uid, ids, vals, context)
                
            #update employee instance
            if not context.get('do_not_update_employee_instance', False):
                emp_instance = self.pool.get('vhr.employee.instance')
                emp_instance.update_employee_instance(cr, uid, ids, context)
                
            return res
        
        except Exception as e:
            log.exception(e)
            error_message = ''
            try:
                error_message = e.message
                if not error_message:
                    error_message = e.value
            except:
                error_message = ""
            
            raise osv.except_osv('Validation Error !', 'Have error during update working record:\n %s!' % error_message)
    
    
    def update_correct_new_data_in_wr_based_on_change_form(self, cr, uid, ids, vals, context=None):
        """
        Cập nhật lại đúng data new trong WR dựa vào các field được sửa theo Change form
        vd: Chọn change form cho đổi department-team: đổi lại team.
            Sau đó chọn lại change form chỉ cho đổi department
            Khi lưu lại new team sẽ được cập nhật lại bằng giá trị old team vì Change Form hiện tại không cho sửa Team
        """
        if vals:
            if vals.get('fields_not_update',False):
                model_field_pool = self.pool.get('ir.model.fields')
                change_form_pool = self.pool.get('vhr.change.form')
                    
                change_form_ids = vals['change_form_ids'][0][2]
                fields_update = []
                #Get list of field user can change
                if change_form_ids:
                    change_forms = change_form_pool.read(cr, uid, change_form_ids, ['access_field_ids'])
                    for change_form in change_forms:
                        access_field_ids = change_form.get('access_field_ids', [])
                        if access_field_ids:
                            access_fields = model_field_pool.read(cr, uid, access_field_ids, ['name'])
                            for access_field in access_fields:
                                name = access_field.get('name','')
                                if name:
                                    fields_update.append(name)
                                
                            
                fields_not_update = vals['fields_not_update']
                fields_not_update = fields_not_update.split(',')
                fields_affect = []
                #add field to list reserve field if field is readonly and affect by edit field
                for field in FIELDS_ONCHANGE:
                    if field in fields_not_update:
                        for field_affect in FIELDS_ONCHANGE[field]:
                            if field_affect not in fields_update:
                                fields_affect.append(field_affect)
                
                fields_not_update += fields_affect
                
                #dict_fields = {new_data_1:old_data_1}
                dict_field = {}
                old_fields = []
                for item in dict_fields_update:
                    dict_field[item[1]] = item[0]
                    old_fields.append(item[0])
                
                if ids:
                    record = self.read(cr, uid, ids[0],old_fields)
                else:
                    record = {}
                    
                for field in fields_not_update:
                    if dict_field.get(field, False):
                        old_data = record.get(dict_field[field], vals.get(dict_field[field]))
                        if isinstance(old_data, tuple):
                            old_data = old_data[0]
                        vals[field] = vals.get(dict_field[field], old_data)
                
                vals['fields_not_update'] = ''
        
        return vals
    
    def check_to_update_effect_to_of_termination_wr(self, cr, uid, ids, vals, context=None):
        """
        Set vals['effect_from'] = effect_to of Termination WR if vals have effect_from
        """
        
        if not isinstance(ids, list):
            ids = [ids]
        
        change_form_ids = []
        effect_from = False
        if ids and len(ids) == 1:
            record = self.read(cr, uid, ids[0], ['change_form_ids','effect_from'])
            change_form_ids = record.get('change_form_ids', [])
            effect_from = record.get('effect_from', False)
        if 'change_form_ids' in vals:
            change_form_ids = vals.get('change_form_ids', [])
            if len(change_form_ids)  == 1 and isinstance(change_form_ids[0], list):
                change_form_ids = change_form_ids[0][2]
        
        if 'effect_from' in vals:
            effect_from = vals.get('effect_from', False)
        
        if change_form_ids:
            is_terminate_wr = self.is_terminate_wr(cr, uid, False, change_form_ids, context)
            if is_terminate_wr:
                vals['effect_to'] = effect_from
        
        return vals
    
    def is_terminate_wr(self, cr, uid, record_id, change_form_ids, context=None):
        if change_form_ids or record_id:
            if not change_form_ids:
                record = self.read(cr, uid, record_id, ['change_form_ids'])
                change_form_ids = record.get('change_form_ids', [])
            
            if change_form_ids:
            
                dismiss_form_ids = self.get_dismiss_change_form_ids(cr, uid, context)
                if set(dismiss_form_ids).intersection(set(change_form_ids)):
                    return True
                
                return False
            
        return None
    
    def get_dismiss_change_form_ids(self, cr, uid, context=None):
        dismiss_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_master_data_dismiss_change_form_code') or ''
        dismiss_code_list = dismiss_code.split(',')
        
        dismiss_local_comp_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_master_data_dismiss_local_company') or ''
        dismiss_local_comp_code_list = dismiss_local_comp_code.split(',')
        
        dismiss_code_list.extend(dismiss_local_comp_code_list)
    
        dismiss_form_ids = self.pool.get('vhr.change.form').search(cr, uid, [('code','in',dismiss_code_list)])
        
        return dismiss_form_ids
                
    
    def check_to_create_update_appendix_contract(self, cr, uid, ids, context=None):
        """
        Tạo 1 phụ lục hợp đồng khi có 1 WR tiến hành giảm lương của nhân viên, không check các WR tạo mới instance 
        va WR cos effect_from =effect-from cua contrat
        """
        if ids:
            if not isinstance(ids, list):
                ids = [ids]
            
            if not context:
                context = {}
            
            parameter_obj = self.pool.get('ir.config_parameter')
            contract_obj = self.pool.get('hr.contract')
            append_contract_obj = self.pool.get('vhr.appendix.contract')
            append_contract_type_obj = self.pool.get('vhr.appendix.contract.type')
            company_obj = self.pool.get('res.company')
            #N
            is_allow = parameter_obj.get_param(cr, uid, 'vhr_human_resource_is_allow_to_create_appendix_contract_when_decrease_salary') or ''
            if is_allow == 'FALSE':
                return True
            
            context['prevent_gen_salary'] = True
            
            for record in self.read(cr, uid, ids, ['state', 'effect_from','employee_id', 'contract_id','gross_salary_old','change_form_ids',
                                                   'gross_salary_new','basic_salary_new','salary_percentage_new','kpi_amount_new','v_bonus_salary_new',
                                                   'general_allowance_new','type_of_salary_new','is_special_change_form',
                                                   'job_title_id_old','job_title_id_new','company_id','salary_percentage_old',
                                                   'collaborator_salary_old','collaborator_salary_new']):
                if record.get('state', False) in [False,'finish'] and record.get('change_form_ids',[]) \
                  and record.get('is_special_change_form', False) != True \
                  and ( record.get('gross_salary_old',False) != record.get('gross_salary_new', False) or \
                         record.get('collaborator_salary_old',False) != record.get('collaborator_salary_new', False) or \
                         record.get('salary_percentage_old',False) != record.get('salary_percentage_new', False) ):
                    
                    vals = {}
                    vals['wr_id'] = record['id']
                    vals['is_create_code'] = True
                    vals['employee_id'] = record.get('employee_id', False) and record['employee_id'][0]
                    vals['contract_id'] = record.get('contract_id', False) and record['contract_id'][0]
                    vals['company_id'] = record.get('company_id', False) and record['company_id'][0]
                    vals['date_start'] = record.get('effect_from', False)
                    vals['sign_date'] = record.get('effect_from', False)
                    
                    vals['gross_salary'] = record.get('gross_salary_new', 0)
                    vals['basic_salary'] = record.get('basic_salary_new', 0)
                    vals['salary_percentage'] = record.get('salary_percentage_new', 0)
                    vals['kpi_amount'] = record.get('kpi_amount_new', 0)
#                     vals['general_allowance'] = record.get('general_allowance_new', 0)
                    vals['v_bonus_salary'] = record.get('v_bonus_salary_new', 0)
                    vals['type_of_salary'] = record.get('type_of_salary_new', 0)
                    vals['collaborator_salary'] = record.get('collaborator_salary_new', 0)
                    vals['description'] = 'Created from Working Record'
                    
                    contract_ids = contract_obj.search(cr, uid, [('state','=','signed'),
                                                                 ('date_start','=', vals.get('date_start', False)),
                                                                 ('employee_id','=',vals.get('employee_id', False)),
                                                                 ('company_id','=', vals.get('company_id', False))])
                    if contract_ids:
                        continue
                    
                    if record.get('job_title_id_old', False) != record.get('job_title_id_new', False):
                        vals['job_title'] = record.get('job_title_id_new', False) and record['job_title_id_new'][0]
                    
                    #Get current sign info
                    if record.get('company_id', False):
                        res_read = company_obj.read(cr, uid, record['company_id'][0], ['sign_emp_id','job_title_id','country_signer'])
                        if res_read['sign_emp_id']:
                            vals.update({'info_signer': res_read['sign_emp_id'],
                                          'title_signer': res_read.get('job_title_id',''),
                                          'country_signer': res_read.get('country_signer',False) and res_read['country_signer'][0] or False,
                                          })
                                    
                    appendix_contract_type_code = parameter_obj.get_param(cr, uid, 'vhr_human_resource_appendix_contract_type_change_info') or ''
                    type_ids = append_contract_type_obj.search(cr, uid, [('code','=',appendix_contract_type_code)])
                    if len(type_ids) != 1:
                        raise osv.except_osv('Validation Error !', 
                                                 "Can't find appendix contract type change collaboration info/ salary/ allowances")
                    
                    vals['appendix_type_id'] = type_ids[0]
                    
                    old_date_start = vals.get('date_start', False)
                    if context.get('old_effect_from', False):
                        old_date_start = context['old_effect_from']
                    append_contract_ids = append_contract_obj.search(cr, uid, [('employee_id','=',vals['employee_id']),
                                                                               ('date_start','=',old_date_start),
                                                                               ('appendix_type_id','=',vals['appendix_type_id'])])
                    if append_contract_ids:
                        append_contract_obj.write(cr, uid, append_contract_ids, vals, context)
                    elif record.get('gross_salary_old',False) != record.get('gross_salary_new', False) or \
                         record.get('collaborator_salary_old',False) != record.get('collaborator_salary_new', False) or \
                         record.get('salary_percentage_old',False) != record.get('salary_percentage_new', False) :
                        append_contract_obj.create(cr, uid, vals, context)
        
        return True
                    
        
        
    def check_if_update_effect_from_out_of_box(self, cr, uid, ids, vals, context=None):
        """
            If Working Record has state False/finish, 
            when change effect_from < effect_from of nearest (lower) WR or  > effect_from of nearest (greater) WR
            ==> Raise error
            
            Also check if change effect_from of created WR(state in [False,finish]), then company doest not effect on effect_from, raise error
        """
        if ids and vals.get('effect_from', False):
            new_effect_from = vals.get('effect_from', False)
            records = self.read(cr, uid, ids, ['effect_from','employee_id','company_id','state'])
            for record in records:
                state = vals.get('state',record.get('state', False))
                employee_id = record.get('employee_id', False) and record['employee_id'][0] or False
                company_id = record.get('company_id', False) and record['company_id'][0] or False
                effect_from = record.get('effect_from', False)
                if state in [False, 'finish'] and employee_id and company_id and effect_from:
                    larger_wr_ids = self.get_larger_working_record(cr, uid, employee_id, company_id, effect_from, context)
                    lower_wr_ids = self.get_nearest_lower_working_record(cr, uid, employee_id, company_id, effect_from, context)
                    
                    #Compare effect_from with effect_from of nearest lower WR
                    if lower_wr_ids:
                        lower_wr = self.read(cr, uid, lower_wr_ids[0], ['effect_from'])
                        lower_effect_from = lower_wr.get('effect_from', False)
                        if lower_effect_from and self.compare_day(new_effect_from, lower_effect_from) >0:
                            raise osv.except_osv('Validation Error !', 
                                                 "You cannot update effective date less than previous record's effective date ")
                    
                    #Compare effect_from with effect_from of nearest larger WR
                    if larger_wr_ids:
                        larger_wr = self.read(cr, uid, larger_wr_ids[0], ['effect_from'])
                        larger_effect_from = larger_wr.get('effect_from', False)
                        if larger_effect_from and self.compare_day(larger_effect_from, new_effect_from) >0:
                            raise osv.except_osv('Validation Error !', 
                                                 "You cannot update effective date greater than next record's effective date ")
                    mcontext = context.copy()
                    mcontext['effect_date'] = new_effect_from
                    #If company not effect on new_effect_from
                    new_company_id, company_ids = self.get_company_ids(cr, uid, employee_id, mcontext)
                    if company_id not in company_ids:
                        company = self.pool.get('res.company').read(cr, uid, company_id, ['name'])
                        company_name = company.get('name', '')
                        new_effect_from = datetime.strptime(new_effect_from,DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y")
                        raise osv.except_osv('Validation Error !', 
                                                "This employee doesn't work at company '%s' on %s " % (company_name,new_effect_from))
        return True
                        
    
    #Update data to contract if WR is first WR of contract
    def update_data_to_contract(self, cr, uid, ids, vals, context=None):
        if not context:
            context = {}
        
        if ids and vals:
            records = self.browse(cr, uid, ids, fields_process = ['contract_id'])
            for record in records:
                #Update info if record if first_working_record of contract
                first_wr_id_of_contract = record.contract_id and record.contract_id.first_working_record_id and record.contract_id.first_working_record_id.id or False
                if first_wr_id_of_contract and record.id == first_wr_id_of_contract:
                    contract_vals = {}
                    contract_id = record.contract_id.id 
                    
                    if vals.get('effect_from', False):
                        contract_type_id = record.contract_id.type_id and record.contract_id.type_id.id or False
                        res = self.pool.get('hr.contract').get_date_end_and_life_of_contract(cr, uid, ids, contract_type_id, vals['effect_from'], context)
                        
                        contract_vals.update({'date_start': vals['effect_from'], 'date_end': res.get('date_end',False)})
                    
                    for field in vals.keys():
                        if field in ['effect_from']:
                            continue
                        if field in translate_contract_to_wr_dict.values():
                            key = translate_contract_to_wr_dict.keys()[translate_contract_to_wr_dict.values().index(field)]
                            contract_vals[key] = vals[field]
                            if field == 'change_form_ids':
                                change_form_id = vals.get(field,False) and vals[field][0][2] and vals[field][0][2][0] or False
                                contract_vals[key] = change_form_id
                    try:
                        if contract_vals:
                            self.pool.get('hr.contract').write(cr, uid, [contract_id], contract_vals, {'update_from_working_record': True})
                    except Exception as e:
                        log.exception(e)
                        raise osv.except_osv('Validation Error !', 'Have error when update working record(s) as first working record(s) of contract !')
        return True
    
    #Update liquidation_date in contract if WR is active and have type= termination
    def update_liquidation_date_of_contract(self, cr, uid, record, context=None):
        if not context:
            context = {}
        
        contract_pool = self.pool.get('hr.contract')
        context['update_from_working_record'] = True
        if record:
            dismiss_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_master_data_dismiss_change_form_code') or ''
            dismiss_code_list = dismiss_code.split(',')
            
            dismiss_local_comp_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_master_data_dismiss_local_company') or ''
            dismiss_local_comp_code_list = dismiss_local_comp_code.split(',')
            
            dismiss_code_list += dismiss_local_comp_code_list
            termination_change_form_ids = self.pool.get('vhr.change.form').search(cr, uid, [('code','in',dismiss_code_list)])
            change_form_ids = record.get('change_form_ids', False) or []
            if termination_change_form_ids and list(set(change_form_ids).intersection(set(termination_change_form_ids))) :
                #Update contract date_end when create working record with type termination
                #contract.liquidation_date = effect_from + 1
                contract_id = record.get('contract_id', False) and record['contract_id'][0] or False
                if contract_id:
                    
                    effect_from = record.get('effect_from', False)
                    effect_from = datetime.strptime(effect_from, DEFAULT_SERVER_DATE_FORMAT).date()
                    liquidation_date = effect_from + relativedelta(days=1)
                    liquidation_date = liquidation_date.strftime(DEFAULT_SERVER_DATE_FORMAT)
                    
                    contract_pool.update_liquidation_date(cr, uid, contract_id, liquidation_date, context)
                    
        return True
    
    def delete_others_after_current_record(self, cr, uid, employee_id, company_id, effect_from, context=None):
        """
        Cancel all staff movement does not finish
        
        """
        
        if employee_id and company_id and effect_from:
            
            code_list = self.get_code_change_form_new_to_company(cr, uid, context)
            
            check_change_form_ids = self.pool.get('vhr.change.form').search(cr, uid, [('code','in',code_list)])
            
            
            #Can not delete working record with change form back to work/input data into iHRP to create another working record same emp-com
#             fix_record_ids = self.search(cr, uid, [('employee_id','=', employee_id), 
#                                                       ('company_id','=', company_id), 
#                                                       ('effect_from','>=',effect_from),
#                                                       ('change_form_ids','in',check_change_form_ids),
#                                                       ('state','in',[False,'finish']),
#                                                       '|',('active','=',True),
#                                                           ('active','=',False)])
#             if fix_record_ids:
#                 company = self.pool.get('res.company').read(cr, uid, company_id, ['name'])
#                 company_name = company.get('name','')
#                 raise osv.except_osv('Validation Error !', 
#                                      'You can not create working record from termination request with Approved last working date greater or equal Start Date at Company "%s" !'% company_name)
            
            #Cancel all staff movement does not finish
            not_fin_sm_ids = self.search(cr, uid, [('employee_id','=', employee_id), 
                                                   ('company_id','=', company_id),
                                                   ('state','not in',[False,'finish','cancel'])])
            if not_fin_sm_ids:
                #Log state change
                context['ACTION_COMMENT'] = 'Reject by termination'
                list_dict_states = {item[0]: item[1] for item in STATES_ALL}
                for record in self.read(cr, uid, not_fin_sm_ids, ['state']):
                    old_state = record.get('state', False)
                    self.write_log_state_change(cr, uid, record['id'], list_dict_states[old_state], list_dict_states['cancel'], context)
                
                super(vhr_working_record, self).write(cr, uid, not_fin_sm_ids, {'state': 'cancel'}, context)
            
            
            greater_record_ids = self.search(cr, uid, [('employee_id','=', employee_id), 
                                                      ('company_id','=', company_id), 
                                                      ('effect_from','>=',effect_from),
                                                      ('state','in',[False,'finish']),
                                                      '|',('active','=',True),
                                                          ('active','=',False)])
            if context.get('current_working_record_id',False) and context['current_working_record_id'] in greater_record_ids:
                greater_record_ids.remove(context['current_working_record_id'])
            if greater_record_ids:
                initial_instance_wr_ids = self.search(cr, uid, [('id','in',greater_record_ids),
                                                                '|',('change_form_ids','in',check_change_form_ids),
                                                                    ('change_form_ids','=',False),
                                                               ])
                if len(greater_record_ids) != len(initial_instance_wr_ids):
                    raise osv.except_osv('Validation Error !', 
                                     'You can not create working record from termination request with Approved last working date lower effective date of another Working Record !')
            
#             if delete_record_ids:
#                 self.unlink_record(cr, SUPERUSER_ID, delete_record_ids, context)
        
        return True
    
    def unlink_working_record_in_the_middle_of_flow(self, cr, uid, ids, context=None):
        """LuanNG:
        Delete working record.
        Update effect_to of lower WR = effect_to of delete WR.
        If delete WR is active, set active for lower WR.
        If delete WR is latest, set latest for lower WR
        ===> Can only use this function for WR Termination because old and new data in this WR is the same, it will not affect so much to lower and greater WR
        Be carefull to use this function, this function do not go to in any flow so it can lead to unsuspicious dangerous situation if you dont understant.
        """
        if ids:
            for record in self.browse(cr, uid, ids):
                employee_id = record.employee_id and record.employee_id.id or False
                company_id = record.company_id and record.company_id.id or False
                effect_from = record.effect_from
                effect_to = record.effect_to
#                 is_latest = record.is_latest
                active = record.active
                
                lower_wr_ids = self.get_nearest_lower_working_record(cr, uid, employee_id, company_id, effect_from, context)
                
                vals = {}
                if active:
                    vals['active'] = active
                
#                 if is_latest:
#                     vals['is_latest'] = is_latest
                
                vals['effect_to'] = effect_to
                
                self.unlink_record(cr, uid, [record.id], context)
                
                if lower_wr_ids:
                    self.write(cr, uid, lower_wr_ids[0], vals)
        
        return True
                    
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        
        if not isinstance(ids,list):
            ids = [ids]
        res = False
        if ids:
            change_form_pool = self.pool.get('vhr.change.form')
            check_input_change_form_ids = []
            
            code_list = self.get_code_change_form_new_to_company(cr, uid, context)
            
            check_input_change_form_ids = change_form_pool.search(cr, uid, [('code','in',code_list)])
            
            update_from_termination =  context.get('update_from_termination', False)
            context['update_from_termination'] = False
            context['disable_check_allowance'] = True
                
            dismiss_local_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_master_data_dismiss_local_company') or ''
            dismiss_local_code_list = dismiss_local_code.split(',')
            dismiss_local_code_ids = change_form_pool.search(cr, uid, [('code','in',dismiss_local_code_list)])
                
            records = self.browse(cr, uid, ids)
            for record in records:
                
                if not record.employee_id or not record.company_id or not record.contract_id:
                    res = self.unlink_record(cr, uid, [record.id], context)
                
                if record.state not in [False, 'draft']:
                    raise osv.except_osv('Validation Error !', 'You can only delete records which are at state Draft !')
                
                #Only allow to delete record create from termination by cancel termination
                elif record.termination_id and not update_from_termination:
                    raise osv.except_osv('Validation Error !', 'You can not delete records create from termination request !')
                    
                elif record.state == 'draft':
                    res = self.unlink_record(cr, uid, ids, context)
                
                #Only allow delete latest record
                #Update nearest record to active and effect_to =False
                elif record.is_latest:
                    
#                     if record.termination_id:
#                         #Update liquidation_date = False of contract when cancel finish termination 
#                         contract_id = record.contract_id and record.contract_id.id or False
#                         if contract_id:
#                             self.pool.get('hr.contract').write(cr, uid, contract_id, {'liquidation_date': False})
                        
                    context['editing_record'] = record.id
                    latest_working_record_id, is_same_contract = self.get_latest_working_record(cr, uid, record.employee_id.id, record.company_id.id, record.contract_id.id, context)
                    
                    #If record is unlink from contract, and this record is first record of contract and latest record, delete it
                    if context.get('update_from_contract', False):
                        
                        res = self.unlink_record(cr, uid, [record.id], context)
                        
                        if latest_working_record_id:
                            #If WR is termination, dont need to update effect_to
                            is_terminate_wr = self.is_terminate_wr(cr, uid, latest_working_record_id, [], context)
                            if not is_terminate_wr:
                                self.write(cr, uid, latest_working_record_id, {'effect_to': None}, context)  #, 'is_latest': True
                                active_ids = self.update_working_record_state(cr, uid, [latest_working_record_id], context)
                                if active_ids:
                                    self.push_data_to_employee(cr, uid, active_ids, context)
#                                     self.update_other_data_with_active_record(cr, uid, active_ids, context)
                                
                        continue
                    
                    
                    is_input_change_form = False
                    change_forms = record.change_form_ids
                    change_form_ids = [change_form.id for change_form in change_forms]
                    if set(check_input_change_form_ids).intersection(set(change_form_ids)):
                        is_input_change_form = True
                    
                    is_dismiss_local_company = set(dismiss_local_code_ids).intersection(set(change_form_ids)) and True or False
                    
                    #If the contract only have one record and that record have change_form:gia nhap cty,back to work, 
                    #don't allow to delete it(exception with WR create by termination)
                    if latest_working_record_id and (not is_input_change_form or record.termination_id or is_dismiss_local_company):
                        if record.termination_id or is_dismiss_local_company:
                            #Set liquidation of contract to null if set in past
#                             if record.active:
                            contract_id = record.contract_id and record.contract_id.id or False
                            if contract_id:
                                self.pool.get('hr.contract').write(cr, uid, contract_id, {'liquidation_date': False})
                            
                            #When unlink Termination WR, set active=True for employee
                            employee_id = record.employee_id and record.employee_id.id or False
                            if employee_id:
                                self.pool.get('hr.employee').write(cr, uid, employee_id, {'active': True})
                                
                            contract_start_date = record.contract_start_date or False
                            if contract_start_date:
                                larger_contract_ids = self.pool.get('hr.contract').search(cr, uid, [('employee_id','=',record.employee_id.id),
                                                                              ('company_id','=',record.company_id.id),
                                                                              ('date_start','>',contract_start_date),
                                                                              ('state','=','signed')])
                                if larger_contract_ids:
                                    raise osv.except_osv('Validation Error !', 'You cannot delete records which are references to old contracts !')
                        
                        #Delete object create by WR: vhr.pr.salary/ vhr.ts.emp.timesheet/ vhr.ts.ws.employee
                        self.unlink_other_link_object(cr, uid, record, context)
                        res = self.unlink_record(cr, uid, [record.id], context)
                        
                        
                        self.write(cr, uid, latest_working_record_id, {'effect_to': None}, context)  #, 'is_latest': True
                        active_ids = self.update_working_record_state(cr, uid, [latest_working_record_id], context)
                        if active_ids:
                            self.push_data_to_employee(cr, uid, active_ids, context)
#                             self.update_other_data_with_active_record(cr, uid, active_ids, context)
                    else:
                        raise osv.except_osv('Validation Error !', 'You cannot delete first working record link to contract which initial with one company !')
                else:
                    raise osv.except_osv('Validation Error !', 'You cannot delete records which are not last working records !')
        
        return res
    
    #Unlink vhr.pr.salary  vhr.ts.emp.timesheet  vhr.ts.ws.employee
    def unlink_other_link_object(self, cr, uid, record, context=None):
        if not context:
            context = {}
        
        salary_pool = self.pool.get('vhr.pr.salary')
        emp_ts_pool = self.pool.get('vhr.ts.emp.timesheet')
        appendix_contract_pool = self.pool.get('vhr.appendix.contract')
        #TODO: These code can be move to correct module, if have errors in future. I put here for run quickly and i am lazy :D
        #If have payroll_salary created by Working Record, when delete WR, delete payroll salary
        if salary_pool and record.payroll_salary_id and not context.get('unlink_from_payroll_salary',False):
            try:
                payroll_salary_id = record.payroll_salary_id.id
                super(vhr_working_record, self).write(cr, uid, record.id, {"payroll_salary_id": False})
                salary_pool.unlink(cr, SUPERUSER_ID, payroll_salary_id, {'unlink_from_wr':True,'user_id': uid})
            except Exception as e:
                log.exception(e)
                error_message = ''
                try:
                    error_message = e.message
                    if not error_message:
                        error_message = e.value
                except:
                    error_message = ""
                raise osv.except_osv('Have error when delete Payroll Salary link to Working Record:', '%s' % error_message)
        
        #If have ts_emp_timesheet_id created by Working Record, when delete WR, delete ts_emp_timesheet_id
        if emp_ts_pool and record.ts_emp_timesheet_id and not context.get('unlink_from_ts_emp_timesheet',False):
            try:
                ts_emp_timesheet_id = record.ts_emp_timesheet_id.id
                super(vhr_working_record, self).write(cr, uid, record.id, {"ts_emp_timesheet_id": False})
                emp_ts_pool.unlink(cr, SUPERUSER_ID, ts_emp_timesheet_id, {'unlink_from_wr':True,'user_id': uid})
            except Exception as e:
                log.exception(e)
                error_message = ''
                try:
                    error_message = e.message
                    if not error_message:
                        error_message = e.value
                except:
                    error_message = ""
                raise osv.except_osv('Have error when delete Employee Timesheet link to Working Record:', '%s' % error_message)
        
        
        
        appendix_ids = appendix_contract_pool.search(cr, uid, [('wr_id','=',record.id)])
        if appendix_ids:
            appendix_contract_pool.write(cr, uid, appendix_ids, {'wr_id': False})
            appendix_contract_pool.unlink(cr, uid, appendix_ids)
            
#         if record.ts_ws_employee_id and not context.get('unlink_from_ts_ws_employee',False):
#             try:
#                 self.pool.get('vhr.ts.ws.employee').unlink(cr, uid, record.ts_ws_employee_id.id, {'unlink_from_wr':True})
#             except Exception as e:
#                 log.exception(e)
#                 error_message = ''
#                 try:
#                     error_message = e.message
#                     if not error_message:
#                         error_message = e.value
#                 except:
#                     error_message = ""
#                 raise osv.except_osv('Have error when delete Working Schedule link to Working Record:', '%s' % error_message)
            
        return True
    
    def unlink_record(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        res = False
        try:
            #update employee instance
            emp_instance = self.pool.get('vhr.employee.instance')
            ncontext = context.copy()
            ncontext.update({'unlink_wr': True})
            emp_instance.update_employee_instance(cr, uid, ids, ncontext)
            res = super(vhr_working_record, self).unlink(cr, uid, ids, ncontext)
            return res
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        
        return res
    
    #Roll back process create WR, update latest WR if have
    def roll_back_working_record(self, cr, uid, ids, context=None):
        try:
            log.info("Try to roll back create WR from Mass Record/ Mass Request/ Multi Requests")
            if ids:
                records = self.browse(cr, uid, ids, fields_process=['employee_id','company_id','contract_id','effect_from'])
                for record in records:
                    context['editing_record'] = record.id
                    nearest_working_record_id, is_same_contract = self.get_latest_working_record(cr, uid, record.employee_id.id, record.company_id.id, record.contract_id.id, context)
                    
                    self.unlink_other_link_object(cr, uid, record, context)
                    res = self.unlink_record(cr, uid, [record.id], context)
                    if nearest_working_record_id:
                        vals = {'effect_to': None}  #,'is_latest': True
                        larger_working_ids = self.search(cr, uid, [('employee_id','=', record.employee_id.id), 
                                                                                  ('company_id','=', record.company_id.id), 
                                                                                  ('effect_from','>=',record.effect_from),
                                                                                  ('state','in',[False,'finish']),
                                                                                  '|',('active','=',True),
                                                                                      ('active','=',False)], order='effect_from asc')
                        if larger_working_ids:
                            self.update_nearest_working_record_info(cr, uid, [larger_working_ids[0]], context)
                            self.update_data_of_future_working_record(cr, uid, nearest_working_record_id, {}, context)
                        else:
                            self.write(cr, uid, nearest_working_record_id, vals, context)
        except Exception as e:
            log.info("Error when try to roll back create WR from Mass Record/ Mass Request/ Multi Requests")
            log.exception(e)
            
        return True
    
    #Get employee belong to department_id_new have hrbp or ass_hrbp consist uid(user login) 
                        #or parent/grand parent... department have hrbp or ass_hrbp consist uid(user login) 
    def get_employee_of_hrbp_ass_hrbp(self, cr, uid, context=None):
        employee_ids = []
        login_employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=',uid)])
        if login_employee_ids:
            department_hrbp_ids = self.get_department_of_hrbp(cr, uid, login_employee_ids[0], context)
            department_ass_hrbp_ids = self.get_department_of_ass_hrbp(cr, uid, login_employee_ids[0], context)
            department_ids = department_hrbp_ids + department_ass_hrbp_ids
            #We dont need to get child because now all child department have hrbp of parent
            if department_ids:
                #Get all active working record have department in department_ids
                record_ids = self.search(cr, uid, [('department_id_new','in',department_ids),
                                                   ('active','=',True)])
                if record_ids:
                    records = self.read(cr, uid, record_ids, ['employee_id'])
                    employee_ids = [record['employee_id'][0] for record in records]
            
            if login_employee_ids[0] not in employee_ids:
                employee_ids.append(login_employee_ids[0])
        
        return employee_ids
    
    def fields_view_get(self, cr, uid, view_id = None, view_type = 'form', context = None, toolbar = False, submenu = False):
        res = super(vhr_working_record, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar = toolbar, submenu = submenu)
        if context is None:
            context = {}
        if view_type == 'form':
            res = self.add_attrs_for_field(cr, uid, res, context)
        elif view_type == 'tree':
            doc = etree.XML(res['arch'])
            if res['type'] == 'tree':
                groups = self.get_groups(cr, uid)
                #These code copy from check_is_able_to_create_request: Only hrbp/assistant/cb working record can create staff movement
                if context.get('record_type', False) == 'request' and not set(['vhr_assistant_to_hrbp','vhr_hrbp','vhr_cb_working_record']).intersection(groups):
                    for node in doc.xpath("//tree"):
                        node.set('create',  '0')
                elif context.get('record_type', False) == 'record' and \
                 not set(['vhr_assistant_to_hrbp','vhr_hrbp','vhr_cb_working_record','vhr_dept_admin','vhr_af_admin']).intersection(groups):
                    for node in doc.xpath("//tree"):
                        node.set('create',  '0')
                
            res['arch'] = etree.tostring(doc)
        return res
    
    def add_attrs_for_field(self, cr, uid, res, context=None):
        if not context:
            context = {}
            
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
            
            groups = self.get_groups(cr, uid)
            #Assistant to HRBP va HRBP trong working record co cung quyen create, edit field
            if 'vhr_assistant_to_hrbp' in groups and 'vhr_hrbp' not in groups:
                groups.append('vhr_hrbp')
            
            #These code copy from check_is_able_to_create_request: Only hrbp/assistant/cb working record can create staff movement
            if context.get('record_type', False) == 'request' and not set(['vhr_assistant_to_hrbp','vhr_hrbp','vhr_cb_working_record']).intersection(groups):
                for node in doc.xpath("//form"):
                    node.set('create',  '0')
            elif context.get('record_type', False) == 'record' and \
             not set(['vhr_assistant_to_hrbp','vhr_hrbp','vhr_cb_working_record','vhr_dept_admin','vhr_af_admin']).intersection(groups):
                for node in doc.xpath("//form"):
                    node.set('create',  '0')
            
            #Temporary add group vhr_dept_head for permission of dept head
            employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=',uid)])
            if employee_ids:
                department_ids = self.pool.get('hr.department').search(cr, uid, [('manager_id','in',employee_ids)])
                if department_ids:
                    groups.append('vhr_dept_head')
                    
            
            fields = fields_permission.keys()
            #Loop for field in file vhr_working_record_permission
            for field in fields:
                for node in doc.xpath("//field[@name='%s']" %field):
                    modifiers = json.loads(node.get('modifiers'))
                    args_readonly, args_invisible = self.build_args_for_field(cr, uid, field, groups, context)
                    
                    #Only edit these field when create
                    if field in ['employee_id', 'company_id', 'contract_id']:
                        args_readonly = [('is_new','=', False)]
                        modifiers['required'] = [('is_new','=', True)]
                    #Only edit effect_from on latest record
                    elif field == 'effect_from':
                        if context.get('termination_id', False):
                            #Readonly when create from termination, to prevent user change effect_from
                            args_readonly = True
                        elif not args_readonly:
                            args_readonly = [
                                            '|','|',('termination_id','!=',False),
                                                    '&',('is_new','=', False),('state','not in',[False,'finish']),
                                                     '&',('state','!=',False),('is_person_do_action','=', False)]
                        modifiers['required'] = True
                        
              
                    elif field == 'change_form_ids':
                        if context.get('termination_id', False):
                        #Readonly when create from termination, to prevent user change change_form_id
                            args_readonly = True
                        elif not args_readonly:
                            #Do not allow to change change_form_id in staff movement when state not in draft
                            #Do not allow to edit if change_form_ids belong to gia nhap cty, quay lai lam viec
                            args_readonly = ['|','|','|',
                                                ('termination_id','!=',False),
                                                ('is_special_change_form','=',True),
                                                '&',('is_new','=', False),('state','not in',['draft','new_hrbp',False,'finish']),
#                                                 '&',('state','=','finish'),('is_person_do_action','=', False),
                                                '&',('state','!=',False),('is_person_do_action','=', False)]
                    
                    elif not args_readonly:
                        args_readonly = [
                                         '|','|',('termination_id','!=',False),
                                                 ('state','not in', [False,'draft','new_hrbp','cb','cb2','finish']),
                                                 '&',('state','!=',False),('is_person_do_action','=', False)]
                        
                        if field not in ['note','is_public','keep_authority','keep_authority_fcnt',
                                         'ts_working_group_id_new','timesheet_id_new','salary_setting_id_new']:
                            args_readonly.insert(0, '|')
                            args_readonly.append(('fields_affect_by_change_form','not indexOf',field))
                    
                    #Set required=False for field are readonly or invisible
                    elif modifiers.get('required', False) and (args_readonly or args_invisible):
                        modifiers['required'] = False
                        
                    if field in dict_salary_fields.keys():
                        if isinstance(args_readonly, list):
                            args_readonly.append(('is_change_form_adjust_salary','=',False))
                            args_readonly.insert(0,'|')
                    
                    if field == 'probation_salary_new':
                        if isinstance(args_readonly, list):
                            args_readonly.append(('contract_type','!=',CT_PROBATION))
                            args_readonly.insert(0,'|')
                        elif not args_readonly:
                            args_readonly = [('contract_type','!=',CT_PROBATION)]
                            
                    elif field in ['collaborator_salary_old','collaborator_salary_new','is_salary_by_hours_new']:
                        if isinstance(args_invisible, list):
                            args_invisible.append(('contract_type','not in',[CT_CTV,CT_DVCTV]))
                            args_invisible.insert(0,'|')
                        elif not args_invisible:
                            args_invisible = [('contract_type','not in',[CT_CTV,CT_DVCTV])]
                    
                    elif field in ['gross_salary_new','basic_salary_new','salary_percentage_new',
                                 'kpi_amount_new','v_bonus_salary_new','general_allowance_new','probation_salary_new',
                                 'gross_salary_old','basic_salary_old','salary_percentage_old',
                                 'kpi_amount_old','v_bonus_salary_old','general_allowance_old','probation_salary_old']:
                        if isinstance(args_invisible, list):
                            args_invisible.append(('contract_type','in',[CT_CTV,CT_DVCTV]))
                            args_invisible.insert(0,'|')
                        elif not args_invisible:
                            args_invisible = [('contract_type','in',[CT_CTV,CT_DVCTV])]
                    
                    
                    if field in ['probation_salary_old','probation_salary_new']:
                        args = [('probation_salary_old','=',''),('probation_salary_new','=','')]
                        if isinstance(args_invisible, list):
                            args_invisible.extend(args)
                        elif not args_invisible:
                            args_invisible = args
                    
                        
                    if 'salary_by_hours_timeline' in field and not args_invisible:
                        if 'new' in field:
                            args_invisible = [('is_salary_by_hours_new','=',False)]
                        else:
                            args_invisible = [('is_salary_by_hours_old','=',False)]
                    
                    #TODO: these fields will be visible in future
                    if field in ['work_for_company_id_old','work_for_company_id_new']:
                        args_invisible= True
                    
                    #these field can not invisible by domain in view xml
                    if field in ['job_title_id_old','job_title_id_new','job_level_id_old','job_level_id_new',
                                 'job_level_person_id_new','career_track_id_new','job_level_person_id_old',
                                 'general_allowance_old','general_allowance_new']:
                        if not args_invisible:
                            args_invisible = modifiers.get('invisible', False)
                        
                        elif isinstance(args_invisible, list) and isinstance(modifiers.get('invisible',False), list):
                            index = 0
                            for item in modifiers.get('invisible',False):
                                args_invisible.insert(index, item)
                                index +=1
                            
                            args_invisible.insert(0, '|')
                    
                    #Or between condition readonly in view and condition readonly in code
                    if field in ['job_level_person_id_new','career_track_id_new']:
                            
                        args_readonly_view = modifiers.get('readonly',False)
                        if not args_readonly:
                            args_readonly = args_readonly_view
                        if isinstance(args_readonly, list) and isinstance(args_readonly_view, list):
                            index = 0
                            for item in args_readonly_view:
                                args_readonly.insert(index, item)
                                index +=1
                            
                            args_readonly.insert(0, '|')
                        
                    
                    # Field company_id "Contract to Company" chỉ cho user thuộc group "vhr_cb_working_record" được edit, các user khác chỉ view thôi
                    elif field == 'company_id' and 'vhr_cb_working_record' not in groups:
                        args_readonly = True
                    
                    
                    modifiers.update({'readonly' : args_readonly, 'invisible' : args_invisible})
                    node.set('modifiers', json.dumps(modifiers))
                #Add domain for change_form_id
                #only show change_form which show_qltv_admin=False in hr (records for cb and cb manager)
                #only show change_form which show_qltv_admin=True in admin(records for other)
                #only show change_form which show_hr_rotate=True in staff movement
                if field == 'change_form_ids':
                    domain = self.get_domain_for_change_form(cr, uid, context)        
                    for node in doc.xpath("//field[@name='%s']" %field):
                        node.set('domain', str(domain))
                
                elif field == 'employee_id':
                    for node in doc.xpath("//field[@name='%s']" %field):
                        modifiers = json.loads(node.get('modifiers'))
                        
                        domain = []
                        employee_ids = self.get_list_employee_can_use(cr, uid, context)
                        if employee_ids:
                            if employee_ids != 'all_employees':
                                domain = [('id','in',employee_ids)]
                        else:
                            modifiers.update({'readonly': True})
                            
                        node.set('domain', str(domain))
                        node.set('modifiers', json.dumps(modifiers))
                
#             if not set(['vhr_cb','vhr_assistant_to_hrbp','vhr_hrbp']).intersection(set(groups)):
#                 #Invisible for group name Change Salary  when user not in group cb, hrbp, vhr_assistant_to_hrbp
#                 for node in doc.xpath('//group[@name="change_salary"]'):
#                     node.set('modifiers', json.dumps({'invisible': True}))

        res['arch'] = etree.tostring(doc)
        return res
    
    
    def build_args_for_field(self, cr, uid, field, groups, context=None):
        write_permissions = []
        show_permissions = []
        for group in fields_permission.get(field, {}):
            if group == 'all_group':
                write_permissions.extend( fields_permission[field][group].get('write',[]))
                show_permissions.extend(  fields_permission[field][group].get('read',[]))
            elif group in groups:
                write_permissions.extend( fields_permission[field][group].get('write',[]))
                show_permissions.extend(  fields_permission[field][group].get('read',[]))
                
        #if context.get('record_type') in write_permissions then readonly = False
        #if context.get('record_type') in show_permissions then invisible = False
        args_readonly = context.get('record_type', False) not in write_permissions
        args_invisible = context.get('record_type', False) not in show_permissions
        
        if 'vhr_cb' in groups and args_invisible:
            args_invisible = False
        
        return args_readonly, args_invisible
    
    def is_special_case_for_change_form(self, cr, uid, change_form_ids, context=None):
        '''
        Change Form have both type: Dieu chinh luong and Luan Chuyen Phong Ban
        is_salary_adjustment = True and access_field_ids contain department_id_new
        '''
        if change_form_ids:
#             change_form_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_human_resource_change_form_code_for_mix_case_dcl_lcpb') or ''
#             change_form_code = change_form_code.split(',')
#             special_change_form_ids = self.pool.get('vhr.change.form').search(cr, uid, [('code', 'in', change_form_code)],context=context)    
            
            change_form_obj = self.pool.get('vhr.change.form')
            field_obj = self.pool.get('ir.model.fields')
            #Search if change form have salary_adjustment
            change_form_adjust_salary_ids = change_form_obj.search(cr, uid, [('id','in',change_form_ids),
                                                               ('is_salary_adjustment','=',True)])
            
            #Check if change form have field department_id_new
            if change_form_adjust_salary_ids:
                for change_form in change_form_obj.read(cr, uid, change_form_ids, ['access_field_ids']):
                    field_ids = change_form.get('access_field_ids', [])
                    if field_ids:
                        fields_department_ids = field_obj.search(cr, uid, [('id','in',field_ids),
                                                                           ('name','=','department_id_new')])
                        if fields_department_ids:
                            return True
         
        return False
    
    def is_person_do_action(self, cr, uid, ids, context=None):
        if ids:
            groups = self.get_groups(cr, uid, {'get_correct_cb': True})
            
            record = self.read(cr, uid, ids[0], ['state'])
            state = record.get('state', False)
            
            group_cb2 = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_human_resource_group_cb2_working_record') or ''
            group_cb2 = group_cb2.split(',') or ''
            is_cb2 = self.pool.get('hr.employee').search(cr, uid, [('login','in',group_cb2),
                                                                   ('user_id','=',uid)])
            
            
            if  (state == 'draft' and self.is_creator(cr, uid, ids, context) 
                 and set(['vhr_assistant_to_hrbp','vhr_hrbp','vhr_cb_working_record']).intersection(groups) )\
             or (state == 'new_hrbp' and self.is_new_hrbp(cr, uid, ids, context) )\
             or (state == 'dept_hr' and 'vhr_hr_dept_head' in groups)\
             or (state in ['cb','finish'] and 'vhr_cb_working_record' in groups)\
             or (state == 'cb2' and is_cb2):
                return True
        
            log.info("User with uid %s don't have right to do action in record %s at state %s" % (uid,ids[0],state ))
        else:
            log.info('ids not exist for check is_person_do_action')
        return False
    
    
#     def is_able_to_do_action_reject(self, cr, uid, ids, context=None):
#         """
#         #Default button Reject invisible when is_person_do_action = False
#         #When is_person_do_action=True, button Reject depend on is_able_to_do_action_reject
#         #In other case if is_person_do_action=True, 
#         #    button Reject will visible in state ["new_hrbp","dept_hr","cb"] 
#         #Button reject only show at state finish if record is latest working record of emp-comp 
#         """
#         if not context:
#             context = {}
#             
#         pass_state = ["new_hrbp","dept_hr",'cb']
#         value = False
#         if ids:
#             record_id = ids[0]
#             record = self.read(cr, uid, record_id, ['state','change_form_ids','employee_id','company_id','effect_from'])
#             state = record.get('state', False)
#             if state in pass_state:
#                 value = True
#             elif state == 'finish':
#                 employee_id = record.get('employee_id', False) and record['employee_id'][0] or False
#                 company_id = record.get('company_id', False) and record['company_id'][0] or False
#                 effect_from = record.get('effect_from', False)
#                 future_ids = self.search(cr, uid, [('employee_id','=',employee_id),
#                                                    ('company_id','=',company_id),
#                                                    ('effect_from','>',effect_from),
#                                                    ('state','in',[False,'finish'])])
#                 if future_ids:
#                     value = False
#                 else:
#                     value = True
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
                employee_id = record.employee_id and record.employee_id.id or False
                if next_state == 'new_hrbp':
                    hrbps = record.department_id_new and record.department_id_new.hrbps or []
                    
                    rm_hrbps = []
                    for hrbp in hrbps:
                        #Check if have permission location
                        res, res_employee_ids = self.get_domain_based_on_permission_location(cr, uid, [hrbp.id], context)
                        if res and employee_id not in res_employee_ids:
                            rm_hrbps.append(hrbp)
                    
                    if rm_hrbps:
                        hrbps = list( set(hrbps).difference(set(rm_hrbps))  )
#                     ass_hrbps = record.department_id_new.ass_hrbps
#                     hrbps += ass_hrbps
                    count_hrbp = len(hrbps)
                    if count_hrbp == 0:
                        raise osv.except_osv('Validation Error !', "Don't have any HRBP at department %s "% (record.department_id_new.complete_code or ''))
                    
                    non_user_ids = 0
                    for hrbp in hrbps:
                        user_id = hrbp.user_id
                        if user_id:
                            break
                        else:
                            non_user_ids += 1
                            error_employees += "\n" + hrbp.name_related + " - " + hrbp.code
                    if non_user_ids != count_hrbp:
                        error_employees = ""
                
                elif next_state in  dict_state_group.keys():
                    employee_ids = self.get_employee_ids_belong_to_group(cr, uid, dict_state_group[next_state], context)
                    
                    not_emp_ids = []
                    non_user_ids = 0
                    if employee_ids:
                        employees = self.pool.get('hr.employee').read(cr, uid, employee_ids, ['user_id','name','code'])
                        for employee in employees:
                            
                            #Check if have permission location
                            res, res_employee_ids = self.get_domain_based_on_permission_location(cr, uid, [employee['id']], context)
                            if res and employee_id not in res_employee_ids:
                                not_emp_ids.append(employee)
                            
                            user_id = employee.get('user_id', False)
                            if user_id:
                                break
                            else:
                                non_user_ids += 1
                                error_employees += "\n" + hrbp.name_related + " - " + hrbp.code
                    
                    #IF dont find any employee belong to group, or all employee in group dont have permision location to read info of employee
                    if not employee_id or (len(not_emp_ids) ==len(employee_ids)):
                        group_name = 'Dept HR'
                        if next_state == 'cb':
                            group_name = "CB Working Record"
                        raise osv.except_osv('Validation Error !', "Don't have any employee belong to group %s "% group_name)
                    
                    if non_user_ids != len(employee_ids):
                        error_employees = ""
                            
            if error_employees:
                raise osv.except_osv('Validation Error !', 'The following employees do not have account domain: %s' % error_employees)
            
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
                record = self.read(cr, uid, record_id, ['state','is_required_attachment','is_change_form_adjust_salary'])
                state = record.get('state', False)
                is_required_attachment = record.get('is_required_attachment',[])
                
                if state in ['finish','cancel']:
                    return True
                
                STATES = self.get_state_dicts(cr, uid, record_id, mcontext)
                list_state = [item[0] for item in STATES]
                
                if is_required_attachment:
                    
                    attachment_ids = self.pool.get('ir.attachment').search(cr, uid, [('res_model','=','vhr.working.record'),
                                                                                     ('res_id','=',record_id)])
                    if not attachment_ids:
                        raise osv.except_osv('Validation Error !', 'You have to attach file before approval')
                
                #Change something in changeform related to staff movement not finish, so movement change workflow,
                #but state is in old workflow, so we have to get new state in new workflow
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
                
                
                #Nếu staff movement có điều chỉnh lương, qua bước c&b phải tới bước c&b2 để chị nhahtt duyệt lương.   bad requirement
                if record.get('is_change_form_adjust_salary', False) and state =='cb' and vals['state'] == 'finish':
                    vals['state'] = 'cb2'
                    
                    
                self.check_exist_action_user_for_next_state(cr, uid, ids, vals['state'], mcontext)
                if vals.get('state', False) == 'finish':
                    self.check_to_send_mail_announce_allowance(cr, uid, record_id)
                res = self.write(cr, uid, [record_id], vals, mcontext)
                
                if res:
                    if already_validate_user:
                        mcontext['ACTION_COMMENT'] = "already validate by: " + already_validate_user
                        context['action_user'] = already_validate_user
                    list_dict_states = {item[0]: item[1] for item in STATES_ALL}
                    self.write_log_state_change(cr, uid, record_id, list_dict_states[state], list_dict_states[vals['state']], mcontext)
                    
                    #Cẩn thận đổi list state dưới đây, vì working record có thể tạo ra employee timesheet/pr.salary và dùng quyền của user để tạo ra
                    #nếu đổi list state này thì khi đó, user cuối cùng finish WR phải có quyền để tạo ra employee timesheet/pr.salary
                    if vals['state'] not in  ['cb','finish']:
                        mcontext['state'] = vals['state']
                        
                        self.action_next(cr, uid, ids, context=mcontext)
                        
                return True
        
        return False
    
    def check_to_send_mail_announce_allowance(self, cr, uid, record_id, context=None):
        if not context:
            context = {}
        record = self.read(cr, uid, record_id,['job_level_person_id_old','job_level_person_id_new','new_allowance_data'])
        job_level_person_id_old = record.get('job_level_person_id_old', False) and record['job_level_person_id_old'][0] or False
        job_level_person_id_new = record.get('job_level_person_id_new', False) and record['job_level_person_id_new'][0] or False
        if job_level_person_id_old != job_level_person_id_new and record.get('new_allowance_data', False):
            new_allowance_data = json.loads(record['new_allowance_data'])
            if new_allowance_data:
                for data in new_allowance_data:
                    if data[2] and data[2].get('amount',0) != data[2].get('temp_amount', 0 ):
                        name, id, mail = self.get_af_executor_name_and_id(cr, uid, context)
                        context['action_user'] = name[0]
                        context['link_email'] = '/mysite/benefit_history'
                        self.send_mail(cr, uid, record_id, 'step_to_finish_to_emp', 'finish', context)
                        
                        context['link_email'] = '/web?#page=0&limit=80&view_type=list&model=vhr.pr.allowance&menu_id=1042&action=1516'
                        self.send_mail(cr, uid, record_id, 'step_to_finish_to_af', 'finish', context)
                        return True
        
        return True
            
    
    def action_reject(self, cr, uid, ids, context=None):
        log.info('Change status to cancel state')
        if ids:
            record_id = ids[0]
            if self.is_person_do_action(cr, uid, [record_id], context):# and self.is_able_to_do_action_reject(cr, uid, [record_id], context)
                record = self.read(cr, uid, record_id, ['state','employee_id','company_id','contract_id'])
                state = record.get('state', False)
                super(vhr_working_record, self).write(cr, uid, [record_id], {'state': 'cancel','active': False}, context)
                
                if state == 'finish':
                    employee_id = record.get('employee_id', False) and record['employee_id'][0] or False
                    company_id = record.get('company_id', False) and record['company_id'][0] or False
                    contract_id = record.get('contract_id', False) and record['contract_id'][0] or False
                    latest_working_record_id, is_same_contract = self.get_latest_working_record(cr, uid, employee_id, company_id, contract_id, context)
                    
                    if latest_working_record_id:
                        self.write(cr, uid, latest_working_record_id, {'effect_to': None}, context)  #, 'is_latest': True
                        active_ids = self.update_working_record_state(cr, uid, [latest_working_record_id], context)
                    
                    #Delete employee timesheet, pr.salary created from WR
                    record = self.browse(cr, uid, record_id)
                    self.unlink_other_link_object(cr, uid, record, context=None)
                
                return True
        
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
                new_state = ''
                passed_state = filter(None, map(lambda x: x.strip(), record.get('passed_state','').split(',')))
                STATES = self.get_state_dicts(cr, uid, record_id, context)
                list_state = [item[0] for item in STATES]
                    
                if passed_state and passed_state[-1] in list_state:
                    new_state = passed_state[-1]
                else:
                    #For old data dont have data in passed_state, we can remove these code if data is empty
                    
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
                vals['passed_state'] = new_state
                vals['users_validated'] = str(uid)
                context['return_to_previous_state'] = True
                self.write(cr, uid, [record_id], vals, context)
#                 super(vhr_working_record, self).write(cr, uid, [record_id], vals, context)
                
                return True
               
        
        return False
    
    def send_mail(self, cr, uid, record_id, state, new_state, context=None):
        if not context:
            context = {}
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
            mail_process = mail_process_of_staff_movement
            
#             record = self.read(cr, uid, record_id, ['change_form_ids'])
#             change_form_ids = record.get('change_form_ids',[])
#             is_mixed = self.is_special_case_for_change_form(cr, uid, change_form_ids, context)
            
            promotion_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_human_resource_change_form_code_promotion') or ''
            promotion_code = promotion_code.split(',')
            promotion_change_form_ids = self.pool.get('vhr.change.form').search(cr, uid, [('code','in',promotion_code)])
            
            demotion_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_human_resource_change_form_code_demotion') or ''
            demotion_code = demotion_code.split(',')
            demotion_change_form_ids = self.pool.get('vhr.change.form').search(cr, uid, [('code','in',demotion_code)])
                            
            log.info("Send mail in Staff Movement from old state %s to new state %s"% ( state, new_state))
            if state in mail_process.keys():
                data = mail_process[state]
                is_have_process = False
                for mail_data in data:
                    if new_state == mail_data[0]:
                        is_have_process = True
                        mail_detail = mail_data[1]
                        vals = {'action_user':action_user, 
                                'wr_id': record_id, 
                                'reason': context.get('ACTION_COMMENT', False),
                                'request_code': 'WR ' + str(record_id)}
                        
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
                        
                        
                        if context.get('link_email', False):
                            vals['link_email'] = context.get('link_email', False)
                        else:
                            link_email = self.get_url(cr, uid, record_id, context)
                            vals['link_email'] = link_email
                            
                        context = {'action_from_email': mail_detail.get('action_from_email','') }
                        self.pool.get('vhr.sm.email').send_email(cr, uid, mail_detail['mail_template'], vals, context)
                
                if not is_have_process:
                    log.info("Staff movement don't have mail process from old state %s to new state %s "%(state, new_state))
            
        return True
                        
                        
                        
    
    def get_email_to_send(self, cr, uid, record_id, list, context=None):
        """
        Returl list email from list
        """
        res = []
        res_cc = []
        if list and record_id:
            for item in list:
                if item == 'old_depthead':
                    name, dh_id, mail = self.get_old_dept_head_name_and_id(cr, uid, record_id, context)
                    if mail:
                        res.append(mail)
                elif item == 'new_depthead':
                    name, dh_id, mail = self.get_new_dept_head_name_and_id(cr, uid, record_id, context)
                    if mail:
                        res.append(mail)
                elif item == 'requester':
                    name, id, mail = self.get_requester_name_and_id(cr, uid, record_id, context)
                    if mail:
                        res.append(mail)
                
                elif item == 'employee':
                    name, id, mail = self.get_employee_name_and_id(cr, uid, record_id, context)
                    if mail:
                        res.append(mail) 
                        
                elif item == 'old_hrbp':
                    name, id, mail = self.get_old_hrbp_name_and_id(cr, uid, record_id, context)
                    if mail:
                        res.extend(mail)
                elif item == 'old_assist_hrbp':
                    name, id, mail = self.get_old_assist_hrbp_name_and_id(cr, uid, record_id, context)
                    if mail:
                        res.extend(mail)
                elif item == 'new_hrbp':
                    name, id, mail = self.get_new_hrbp_name_and_id(cr, uid, record_id, context)
                    if mail:
                        res.extend(mail)
                elif item == 'new_assist_hrbp':
                    name, id, mail = self.get_new_assist_hrbp_name_and_id(cr, uid, record_id, context)
                    if mail:
                        res.extend(mail)
                elif item == 'dept_hr':
                    name, id, mail = self.get_dept_hr_name_and_id(cr, uid, context)
                    if mail:
                        res.extend(mail)
                
                elif item == 'af_executor':
                    name, id, mail = self.get_af_executor_name_and_id(cr, uid, context)
                    if mail:
                        res.extend(mail)
                
#                 elif item == 'SM_C&B':
#                     name ,id, mail = self.get_cb_name_and_id(cr, uid, context)
#                     if mail:
#                         res.extend(mail)
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
                
    #TODO: check lai
    def get_url(self, cr, uid, res_id, context=None):
        if isinstance(res_id, list):
            res_id = res_id[0]
        model_data = self.pool.get('ir.model.data')
        action_id = model_data.xmlid_lookup(cr, uid, 'vhr_human_resource.act_vhr_working_record_staff_movement')[2]
        
        url = ''
        config_parameter = self.pool.get('ir.config_parameter')
        base_url = config_parameter.get_param(cr, uid, 'web.base.url') or ''
        if base_url:
            url = base_url
        url += '/web#id=%s&view_type=form&model=vhr.working.record&action=%s' % (res_id, action_id)
        return url
    
    def open_window(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        
        
        context['validate_read_vhr_working_record'] = False
        view_open = 'view_vhr_working_record_submit_form'
        if context.get('view_open',False):
            view_open = context['view_open']
        
        attachment_obj = self.pool.get('ir.attachment')
        
        is_require_data_for_submit = False
        if context.get('action', False) in ['submit','approve']:
            records = self.read(cr, uid, ids, ['attachment_ids','is_required_attachment','state','is_person_do_action'])
            for record in records:
                
                if (not record.get('attachment_ids',[]) or record['state'] == 'new_hrbp') and record.get('is_required_attachment', False):
                    is_require_data_for_submit = True
                    if record['state'] =='new_hrbp':
                        context['dont_show_created_attachment'] = True
                        #Check if have attach file outside submit box
                        if record.get('is_person_do_action', False):
                            file_ids = attachment_obj.search(cr, uid, [('res_model','=',self._name),
                                                                       ('res_id','=',record['id']),
                                                                       ('attach_note','=',record['state'])])
                            if file_ids:
                                files = self.pool.get('ir.attachment').read(cr, uid, file_ids, ['user_id'])
                                user_ids = [file.get('user_id', False) and file['user_id'][0] for file in files]
                                if uid in user_ids:
                                    context['dont_show_created_attachment'] = False
                                    is_require_data_for_submit = False
                    
                    break
                
#         elif context.get('action', False) == 'reject':
#             #Require attachment when reject at cb/finish
#             records = self.read(cr, uid, ids, ['state'])
#             for record in records:
#                 if record.get('state', False) in ['cb','finish']:
#                     is_require_data_for_submit = True
#                     context['dont_show_created_attachment'] = True
#                     break
        
        context['is_require_data_for_submit'] = is_require_data_for_submit
        action = {
            'name': 'Notes',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.pool.get('ir.model.data').get_object_reference(cr, uid, 'vhr_human_resource', view_open)[1],
            'res_model': 'vhr.working.record',
            'context': context,
            'type': 'ir.actions.act_window',
            #'nodestroy': True,
            'target': 'new',
            #'auto_refresh': 1,
            'res_id': ids[0],
        }
        return action
    
    def execute_workflow(self, cr, uid, ids, context=None):
        
        if isinstance(ids, (int, long)):
            ids = [ids]
        if context is None: context = {}
        context['call_from_execute'] = True
        for record_id in ids:
            try:
                action_result = False
                action_next_result = False
                record = self.read(cr, uid, record_id, ['state'])
                old_state = record.get('state', False)
                
                if old_state:
                    
                    if old_state in ['cancel']:
                        raise osv.except_osv('Validation Error !', "You don't have permission to do this action")
                    
                    if old_state == 'finish' and context.get('action', False) in ['submit','approve','return']:
                        raise osv.except_osv('Validation Error !', "You don't have permission to do this action")
                    
                    elif old_state == 'finish' and context.get('action', False) == 'reject' and context.get('multi_record', False):
                        raise osv.except_osv('Validation Error !', "You can only reject finish staff movement by button Reject in request form")
                        
                    if context.get('action', False) in ['submit','approve']:
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
    
    def open_confirm_form(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        context['view_open'] = 'view_vhr_working_record_confirm_form'
        return self.open_window(cr, uid, ids, context)
   
   #This function will be call from menu More/Execute, to get all ids can be choosen in tree from context['active_ids']
    def execute_public_working_record(self, cr, uid, ids, context=None):
        if not isinstance(ids, list):
            ids = [ids]
        active_ids = context.get('active_ids',ids)
        return self.public_working_record(cr, uid, active_ids, context)
    
    def public_working_record(self, cr, uid, ids, context=None):
        if not isinstance(ids, list):
            ids = [ids]
        
        self.write(cr, uid, ids, {'is_public': True})
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
        
    def thread_import_working_record(self, cr, uid, import_status_id, rows, context=None):
        log.info('Begin: thread_import_working_record')
        try:
            import openerp
            db = openerp.sql_db.db_connect(cr.dbname)
            cr = db.cursor()
            mcr = db.cursor()
            import_obj = self.pool.get('vhr.import.status')
            detail_obj = self.pool.get('vhr.import.detail')
            employee_obj = self.pool.get('hr.employee')
            change_form_pool = self.pool.get('vhr.change.form')
            parameter_obj = self.pool.get('ir.config_parameter')
            
            model_ids = self.pool.get('ir.model').search(cr, uid, [('model','=',self._name)])
            model_id = model_ids and model_ids[0] or False
            mapping_fields = {
                  'Employee Code': 'employee_id', 'Company': 'company_id', 'Effective Date': 'effect_from', 'Change Form': 'change_form_ids',
                  'Is Publish': 'is_public', 'New Office': 'office_id_new', 'New Division': 'division_id_new', 'New Department': 'department_id_new',
                  'New Team': 'team_id_new', 'New Title': 'job_title_id_new', 'New Level': 'job_level_id_new', 'New Position Level': 'job_level_position_id_new',
                  'New Person Level': 'job_level_person_id_new', 'New Job Family': 'pro_job_family_id_new','New Job Group': 'pro_job_group_id_new',
                  'New Sub Group': 'pro_sub_group_id_new','New Reporting Line': 'report_to_new', 'New Working Group': 'ts_working_group_id_new',
                  'New Timesheet': 'timesheet_id_new', 'New Salary Setting': 'salary_setting_id_new', 'New Seat No': 'seat_new', 'New Ext': 'ext_new',
                  'New % Split Salary': 'salary_percentage_new', 'New Gross Salary': 'gross_salary_new', 'New Basic Salary': 'basic_salary_new',
                  'New KPI': 'kpi_amount_new', 'New General Allowance': 'general_allowance_new','New Type Of Salary': 'type_of_salary_new',
                  'New Probation Salary': 'probation_salary_new', 'New Collaborator Salary': 'collaborator_salary_new', 'Is Salary By Hours': 'is_salary_by_hours_new',
                  'Salary By Hours Timeline 1': 'salary_by_hours_timeline_1_new','Salary By Hours Timeline 2': 'salary_by_hours_timeline_2_new',
                  'Salary By Hours Timeline 3': 'salary_by_hours_timeline_3_new','New V_Bonus':'v_bonus_salary_new',
                  'Force To Insert At Last': 'force_to_insert_last',"Level Comments":'job_level_person_comment','New Career Track': 'career_track_id_new',
                              }
            
            required_fields = ['employee_id','company_id','effect_from']
            fields_order = []
            fields_search_by_name = []
            working_record_fields = self._columns.keys()
            
            import_obj.write(mcr, uid, [import_status_id], {'state': 'processing', 'num_of_rows':rows.nrows-2, 'current_row':0,'model_id': model_id})
            mcr.commit()
            #Dont count two round describe data
            row_counter = 0
            success_row = 0
            for row in rows._cell_values:
                auto_break_thread_monthly_gen = parameter_obj.get_param(cr, uid, 'vhr_human_resource_auto_break_thread') or ''
                try:
                    auto_break_thread_monthly_gen = int(auto_break_thread_monthly_gen)
                except:
                    auto_break_thread_monthly_gen = False
                if auto_break_thread_monthly_gen:
                    break
                
                if row_counter == 0:
                    fields_order = row
                    
                row_counter += 1
                if row_counter > 2:
                    vals_detail = {}
                    data = row[:]
                    vals, error = self.parse_data_from_excel_row(cr, uid, row, mapping_fields, fields_search_by_name, fields_order, context)
                    warning = ''
                    if not error:
                        try:
                            #Check if missing required fields
                            vals_field = vals.keys()
                            input_required_fields = list(set(required_fields).intersection(set(vals_field)))
                            if len(required_fields) != len(input_required_fields):
                                missing_fields = list(set(required_field).difference(set(input_required_fields)))
                                missing_name_fields = []
                                for key, value in mapping_fields.iteritems():
                                    if value in missing_fields:
                                        missing_name_fields.append(key)
                                
                                error = "You have to input data in %s" % str(missing_name_fields)
                            
                            else:    
                                record_vals = self.default_get(cr, uid, working_record_fields, context)
                                record_vals['employee_id'] = vals.get('employee_id', False)
                                #Get data from onchange_effect_from
                                onchange_effect_from_data = self.onchange_effect_from(cr, uid, [], vals.get('effect_from'), vals.get('employee_id'), vals.get('company_id'), False, False, False, False, True, False, False, False, context)
                                if onchange_effect_from_data.get('warning', False):
                                    error = onchange_effect_from_data['warning']
                                else:
                                    change_form_ids = vals.get('change_form_ids', []) and vals['change_form_ids'][0][2] or []
                                    if change_form_ids:
                                        onchange_effect_from_value = onchange_effect_from_data['value']
                                        for field in onchange_effect_from_value.keys():
                                            if isinstance(onchange_effect_from_value[field], tuple):
                                                onchange_effect_from_value[field] = onchange_effect_from_value[field][0]
                                        
                                        if onchange_effect_from_data.get('domain', False):
                                            #Raise error if WR near WR create by Termination have change form=termination
                                            domain_effect_from = onchange_effect_from_data['domain']
                                            if 'change_form_ids' in domain_effect_from:
                                                domain_change_form = domain_effect_from['change_form_ids']
                                                
                                                avalable_change_form_ids = change_form_pool.search(cr, uid, domain_change_form, order='id asc')
                                                if not set(avalable_change_form_ids).intersection(set(change_form_ids)):
                                                    error = "Change Form not satisfy domain %s" % (str(domain_change_form))
                                    
                                    if not error:
                                        update_ids = self.search(cr, uid, [('employee_id','=',vals.get('employee_id', False)),
                                                                           ('company_id','=',vals.get('company_id',False)),
                                                                           ('effect_from','=',vals.get('effect_from',False)),
                                                                           ('state','in', [False, 'finish'])
                                                                           ])
                                        
                                        #Raise error when create with no change form
                                        if not change_form_ids and not update_ids:
                                                error = "You have to input data in %s" % str(missing_name_fields)
                                        
                                        if update_ids:
                                            if 'effect_from' in vals:
                                                del vals['effect_from']
                                                
                                            self.write_with_log(cr, uid, update_ids, vals, context)
                                            warning = 'Update data in working record'
                                        else:
                                            record_vals.update( onchange_effect_from_value )
                                            record_vals.update(vals )
                                            res = self.create_with_log(cr, uid, record_vals, context)
                                        
                                        if not error:
                                            success_row += 1
                                            
                        except Exception as e:
                            log.exception(e)
                            try:
                                error = e.message
                                if not error:
                                    error = e.value
                            except:
                                error = ""
                    if error:
                        vals_detail = {'import_id': import_status_id, 'row_number' : row_counter -2, 'message':error,'status':'fail'}
                        detail_obj.create(mcr, uid, vals_detail)
                        mcr.commit() 
                        cr.rollback()
                    else:
                        if warning:
                            vals_detail = {'import_id': import_status_id, 'row_number' : row_counter -2, 'message':warning,'status':'success'}
                            detail_obj.create(mcr, uid, vals_detail)
                            mcr.commit() 
                        cr.commit()
                    
                import_obj.write(mcr, uid, [import_status_id], {'current_row':row_counter - 2, 'success_row':success_row})
                mcr.commit()
            import_obj.write(mcr, uid, [import_status_id], {'state': 'done'})
            mcr.commit()
        except Exception as e:
            log.exception(e)
            import_obj.write(mcr, uid, [import_status_id], {'state': 'error'})
            mcr.commit()
            log.info(e)
            cr.rollback()
        finally:    
            cr.close()
            mcr.close()
        log.info('End: thread_import_working_record')
        return True
    
    def parse_data_from_excel_row(self, cr, uid, row, mapping_fields, fields_search_by_name, fields_order, context=None):
        res = {}
        error = ""
        if row and mapping_fields and fields_order:
            for index, item in enumerate(row):
                #If item in row does not appear in mapping fields, by pass   50, 36, 52, 37
                field_name = mapping_fields.get(fields_order[index])
                if field_name:
                    field_obj = self._all_columns.get(field_name)
                    field_obj = field_obj and field_obj.column
                    if field_obj and field_obj._type == 'many2one':
                        
                        model = field_obj._obj
                        value = str(item).strip()
                        if value:
                            
                            #Assign False to field_name if value == 'false'
                            if value in ['false','0']:
                                res[field_name] = False
                                continue
                            
                            domain = ['|',('code','=ilike', value),('name','=ilike', value)]
                            if field_name in fields_search_by_name:
                                domain = [('name','=ilike', value)]
                            
                            if field_obj._domain:
                                domain.extend(field_obj._domain)
                            record_ids = self.pool.get(model).search(cr, uid, domain)
                            
                            #Try one more time with inactive record
                            if not record_ids:
                                domain.insert(0,('active','=', False))
                                record_ids = self.pool.get(model).search(cr, uid, domain)
                                
                            #Have wrong data in hr.department, so we have to use complete code to query
                            if model == 'hr.department':
                                record_ids = self.search_department_with_complete_code(cr, uid, value, context)
                                
                            if len(record_ids) == 0:
                                error = "Can't find record of '%s' with input data '%s' for field '%s'" % (model, value, field_obj.string)
                                return res, error
                            elif len(record_ids) ==1:
                                res[field_name] = record_ids[0]
                                
                            else:#len >=2
                                error = "Have %s record of '%s' with input data '%s' for field '%s'" % (len(record_ids), model, value, field_obj.string)
                                return res, error
                    elif item and field_obj and field_obj._type == 'many2many':
                        model = field_obj._obj
                        list_value = str(item).strip().split(',')
                        value = ','.join(list_value)
                        if list_value:
                            record_ids = self.pool.get(model).search(cr, uid, [('code','in',list_value)])
                            if record_ids:
                                res[field_name] = [[6, False, record_ids]]
                                if len(record_ids) != len(list_value):
                                    error = "Can't find enough record of '%s' with input data '%s' for field '%s'" % (model, value, field_obj.string)
                                    return res, error
                            else:
                                error = "Can't find record of '%s' with input data '%s' for field '%s'" % (model, value, field_obj.string)
                                return res, error
                            
                    elif item and field_obj and field_obj._type == 'date':
                        try:
                            item = str(item)
                            value = datetime.strptime(item,"%d/%m/%Y").strftime(DEFAULT_SERVER_DATE_FORMAT)
                            res[field_name] = value
                        except Exception as e:
                            error = "Field %s have to input correct date format dd/mm/YYYY" % field_obj.string 
                            
                    elif item and field_obj and field_obj._type == 'boolean':
                        value = str(item).lower()
                        if value == 'true' or value == '1':
                            res[field_name] = True
                        elif value == 'false' or value == '0':
                            res[field_name] = False
                    
                    elif item and field_obj and field_obj._type == 'selection':
                        selection = field_obj.selection
                        select_list = [s[0] for s in selection]
                        value = str(item).lower().strip()
                        if value in select_list:
                            res[field_name] = value
                        else:
                            error = "Field '%s' have to input data in selection '%s'" % (field_obj.string, str(select_list))
                            return res, error
                    
                    elif item and field_obj and field_obj._type in ['char', 'text']:
                        if isinstance(item, float):
                            item = int(item)
                        res[field_name] = str(item)
                    
                    elif item and field_obj and field_obj._type == 'float':
                        try:
                            res[field_name] = item and float(item) or 0
                        except Exception as e:
                            error = "Field '%s' have to input number" % field_obj.string 
                    
                    elif item and field_obj and field_obj._type == 'int':
                        try:
                            res[field_name] = item and int(item) or 0
                        except Exception as e:
                            error = "Field '%s' have to input number" % field_obj.string 
                    
                    elif item and field_name == 'force_to_insert_last':
                        value = str(item).lower()
                        if value == 'true' or value == '1':
                            res[field_name] = True
                        else:
                            res[field_name] = False
                    elif item:
                        res[field_name] = item
                
        
        return res, error
    
    def search_department_with_complete_code(self, cr, uid, complete_code, context=None):
        department_ids = []
        if complete_code:
            department_pool = self.pool.get('hr.department')
            parent_code = ''
            dept_code = complete_code
            if '/' in complete_code:
                index = complete_code.rindex('/')
                dept_code = complete_code[index+1:].strip()
                parent_code = complete_code[:index]
                parent_code = '/'.join(map(str.strip, parent_code.split('/')))
            
            dept_ids = department_pool.search(cr, uid, [('code','=ilike',dept_code),('active','=',True)])
            #Search inactive department in case cant find active department
            if not dept_ids:
                dept_ids = department_pool.search(cr, uid, [('code','=ilike',dept_code), ('active','=',False)])
            
            if len(dept_ids) >1 and parent_code:
                for dept in department_pool.read(cr, uid, dept_ids, ['parent_id']):
                    parent_dept_code = dept.get('parent_id', False) and str(dept['parent_id'][1]) or ''
                    parent_dept_code = '/'.join(map(str.strip, parent_dept_code.split('/')))
                    if parent_code.lower() == parent_dept_code.lower():
                        department_ids.append(dept['id'])
            else:
                department_ids = dept_ids
        
        return department_ids
    
    def get_code_change_form_new_to_company(self, cr, uid, context=None):
        """
        Trả về danh sách code các change form thể hiện nhân viên mới vào công ty
        """
        config_parameter = self.pool.get('ir.config_parameter')
        input_code = config_parameter.get_param(cr, uid, 'vhr_master_data_input_data_into_iHRP') or ''
        input_code_list = input_code.split(',')
        
        back_code = config_parameter.get_param(cr, uid, 'vhr_master_data_back_to_work_change_form_code') or ''
        back_code_list = back_code.split(',')
        
        change_type_code = config_parameter.get_param(cr, uid, 'vhr_master_data_change_type_of_contract') or ''
        change_type_code_list = change_type_code.split(',')
        
        change_local_comp_code = config_parameter.get_param(cr, uid, 'vhr_master_data_change_local_company') or ''
        change_local_comp_code_list = change_local_comp_code.split(',')
        
        code_list = input_code_list + back_code_list + change_type_code_list + change_local_comp_code_list
        return code_list
    
        
    def action_print_multi_privacy_statement(self, cr, uid, ids, context=None):
        if not context:
            context = {}
            
        result = {}
        list_data = []
        appendix_contract_pool = self.pool.get('vhr.appendix.contract')
        param_pool = self.pool.get('ir.config_parameter')
        wz_pool = self.pool.get('vhr.wizard.privacy.statement')
        
        
        adjust_sal_code = param_pool.get_param(cr, uid, 'vhr_human_resource_code_change_form_for_template_adjust_salary') or ''
        adjust_sal_code = adjust_sal_code.split(',')
        promote_code = param_pool.get_param(cr, uid, 'vhr_human_resource_code_change_form_for_template_promotion') or ''
        promote_code = promote_code.split(',')
        
        file_name = "Privacy Statement - "
        
        for record_id in ids:
            record = self.read(cr, uid, record_id, ['change_form_ids','employee_id'])
            change_form_ids = record.get('change_form_ids', [])
            change_forms = self.pool.get('vhr.change.form').read(cr, uid, change_form_ids, ['code'])
            change_form_codes = [form.get('code','') for form in change_forms]
            
            employee_id = record.get('employee_id', False) and record['employee_id'][1]
            file_name += ' ' + employee_id
            
            if set(change_form_codes).intersection(promote_code):
                report_name = 'letter_promotion'
                context['force_report_name'] = 'appendix_contract_promotion_review_map_with_privacy_statement'
            elif set(change_form_codes).intersection(adjust_sal_code):
                report_name = 'letter_salary_adjust'
                context['force_report_name'] = 'appendix_contract_salary_review_map_with_privacy_statement'
                
            res = wz_pool.get_data_of_each_employee(cr, uid, record_id, report_name, file_name,context)
            if not result:
                result = res
                
            datas = res.get('datas', False)
            if datas:
                data = datas.get('form')
                if isinstance(data, dict):
                    list_data.append({'report.'+ report_name : data})
                else:
                    list_data.extend(data)
            
            appendix_ids = appendix_contract_pool.search(cr, uid, [('wr_id','=',record_id)])
            if appendix_ids:
                
                res = appendix_contract_pool.print_appendix_contract(cr, uid, appendix_ids, context)
                
                
                if res:
                    datas = res.get('datas', False)
                    if datas:
                        data = datas.get('form')
                        if isinstance(data, dict):
                            list_data.append({'report.'+ res['report_name'] : data})
                        else:
                            list_data.extend(data)
        
        log.info("Leng of list="+str(len(list_data)))
        result['datas'] = {
                     'ids': ids,
                     'model': 'vhr.working.record',
                    'form': list_data,
                     'merge_multi_report': True,
                     'parse_condition': True
                     }
        
        return result
    
    
vhr_working_record()