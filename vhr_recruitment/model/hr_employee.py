# -*-coding:utf-8-*-
import logging
import datetime

from openerp.osv import osv, fields
import simplejson as json
from openerp import SUPERUSER_ID
from lxml import etree
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.addons.vhr_common.model.vhr_common import vhr_common

log = logging.getLogger(__name__)


class hr_employee(osv.osv, vhr_common):
    _inherit = 'hr.employee'
    _description = 'HR Employee'
    
    def _is_candidate(self, cr, uid, ids, prop,unknow_none, context=None):
        """
        RR Candidate là nhân viên được chuyển từ bên RR và không có hd với state != signed/cancel
        HR Candidate là nhân viên không được tạo từ bên RR và không có hợp đồng nào hoặc có ít nhất 1 hợp đồng khác signed/cancel
        """
        res = {}
        contract_obj = self.pool.get('hr.contract')
        today = datetime.datetime.today().date().strftime(DEFAULT_SERVER_DATE_FORMAT)
        
        for record_id in ids:
            res[record_id] = {'is_candidate':False,'is_hr_candidate':False}
            
            employee = self.read(cr, uid, record_id, ['is_transfer_from_rr'])
            is_transfer_from_rr = employee.get('is_transfer_from_rr', False)
            if is_transfer_from_rr:
                #Search contract ko thuộc state signed/cancel có change_form_id và có job_applicant_id, hd kết thúc trong tương lại
                #TODO: Check lại tất cả các case có thể xảy ra 
                contract_ids = self.pool.get('hr.contract').search(cr, uid, [
                                                              ('employee_id', '=', record_id),
                                                              ('state', 'not in', ['signed','cancel']),
                                                              ('change_form_id','!=',False),
                                                              ('job_applicant_id','!=', False),
                                                              '|',('date_end','=',False),
                                                                  ('date_end','>',today)
                                                              ], order='date_start asc')
                if contract_ids:
                    res[record_id]['is_candidate'] = True
            else:
                contract_ids = self.pool.get('hr.contract').search(cr, uid, [
                                                                  ('employee_id', '=', record_id),
#                                                                   '|',('date_end','=',False),
#                                                                       ('date_end','>',today)
                                                                  ], order='date_start asc')
                
                if not contract_ids:
                    res[record_id]['is_hr_candidate'] = True
                else:
                    contract_ids = self.pool.get('hr.contract').search(cr, uid, [
                                                                  ('employee_id', '=', record_id),
                                                                  ('state', 'not in', ['signed','cancel']),
                                                                  ('change_form_id','!=',False),
                                                                  ('job_applicant_id','=', False),
                                                                  '|',('date_end','=',False),
                                                                      ('date_end','>',today)
                                                                  ], order='date_start asc')
                    if contract_ids:
                        res[record_id]['is_hr_candidate'] = True
        
        return res
    
    def search_candidate(self, cr, uid, obj, name, args, context=None):
        if not args:
            return []
        employee_ids = []
        
        from_rr_ids = self.search(cr, uid, [('is_transfer_from_rr','=',True)])
        if from_rr_ids:
            contract_obj = self.pool.get('hr.contract')
            today = datetime.datetime.today().date().strftime(DEFAULT_SERVER_DATE_FORMAT)
            contract_ids =contract_obj.search(cr, uid, [
                                                       ('employee_id', 'in', from_rr_ids),
                                                       ('state', 'not in', ['signed','cancel']),
                                                       ('change_form_id','!=',False),
                                                       ('job_applicant_id','!=', False),
                                                       '|',('date_end','=',False),
                                                           ('date_end','>',today)
                                                       ], order='date_start asc')
            contracts = contract_obj.read(cr, uid, contract_ids, ['employee_id'])
            employee_ids = [contract.get('employee_id', False) and contract['employee_id'][0] for contract in contracts]
            employee_ids = list(set(employee_ids))
        
        operator = 'in'
        for field, oper, value in args:
            if oper == '!=' and value == True:
                operator = 'not in'
                break
            elif oper == '=' and value == False:
                operator = 'not in'
                break
            
        return [('id', operator, employee_ids)]
    
    def search_hr_candidate(self, cr, uid, obj, name, args, context=None):
        if not args:
            return []
        employee_ids = []
        
        from_rr_ids = self.search(cr, uid, [('is_transfer_from_rr','=',False)])
        if from_rr_ids:
            contract_obj = self.pool.get('hr.contract')
            today = datetime.datetime.today().date().strftime(DEFAULT_SERVER_DATE_FORMAT)
            #Search employee have at least one contract at state not in (signed, cancel)
            contract_ids =contract_obj.search(cr, uid, [
                                                       ('employee_id', 'in', from_rr_ids),
                                                       ('state', 'not in', ['signed','cancel']),
                                                       ('change_form_id','!=',False),
                                                       ('job_applicant_id','=', False),
                                                       '|',('date_end','=',False),
                                                           ('date_end','>',today)
                                                       ], order='date_start asc')
            contracts = contract_obj.read(cr, uid, contract_ids, ['employee_id'])
            employee_ids = [contract.get('employee_id', False) and contract['employee_id'][0] for contract in contracts]
            employee_ids = list(set(employee_ids))
            
            #Search employee dont have any contract, and not transfer from RR
            other_emp_ids = self.search(cr, uid, [('active','=',True),
                                                  ('is_transfer_from_rr','=',False),
                                                  ('id','not in', employee_ids)])
            if other_emp_ids:
                contract_ids = contract_obj.search(cr, uid, [('employee_id','in', other_emp_ids)])
                contracts = contract_obj.read(cr, uid, contract_ids, ['employee_id'])
                employee_have_contract_ids = [contract.get('employee_id', False) and contract['employee_id'][0] for contract in contracts]
                employee_have_contract_ids = list(set(employee_have_contract_ids))
                employee_dont_have_contract_ids = list(  set(other_emp_ids).difference(set(employee_have_contract_ids))  )
                employee_ids += employee_dont_have_contract_ids
        
        operator = 'in'
        for field, oper, value in args:
            if oper == '!=' and value == True:
                operator = 'not in'
                break
            elif oper == '=' and value == False:
                operator = 'not in'
                break
            
        return [('id', operator, employee_ids)]
    
    _columns = {
        'is_transfer_from_rr': fields.boolean('Is Transfer From RR'),
        'is_candidate': fields.function(_is_candidate, type='boolean', string='Candidate', fnct_search=search_candidate, multi='search_candidate'),#Overide this field in vhr_master_data
        'is_hr_candidate': fields.function(_is_candidate, type='boolean', string='Candidate', fnct_search=search_hr_candidate, multi='search_candidate')
    }
    
    _defaults = {
        'is_hr_candidate': True
    }
    
    
    
    def fields_view_get(self, cr, uid, view_id = None, view_type = 'form', context = None, toolbar = False, submenu = False):
        """
        Do not allow to edit employee when join_date >= today (Employee transfer from RR to CB)
        Some field are prevent to edit even when today > join_date (transfer from RR), only allow user edit in contract: division,department,...
        """
        res = super(hr_employee, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar = toolbar, submenu = submenu)
        if context is None:
            context = {}
        if view_type == 'form':
            doc = etree.XML(res['arch'])
            if res['type'] == 'form':
                
                fields = self._columns.keys()
                
                no_update_fields = ['join_date','office_id','division_id','department_id','team_id','title_id','gender_fcnt','birthday_fcnt',
                                    'job_level_id','report_to','job_level_person_id','job_family_id','job_group_id','sub_group_id',]
                
                not_check_fields = ['street','city_id','district_id','partner_country_id','birthday','birth_city_id','personal_document',
                                    'native_city_id','nation_id','mobile','native_place','religion_id','temp_address','temp_city_id',
                                    'temp_district_id','phone','email','duty_free','health_care','relation_partners','bank_ids',
                                    'certificate_ids','working_background']
                today = datetime.datetime.today().date().strftime(DEFAULT_SERVER_DATE_FORMAT)
                
                fields = list(set(fields)-set(not_check_fields))
                for field in fields:
                    for node in doc.xpath("//field[@name='%s']" %field):
                        modifiers = json.loads(node.get('modifiers'))
                        #inherit args_readonly
                        args_readonly = modifiers.get('readonly',False)
                        
                        if isinstance(args_readonly, list):
                            args_readonly.insert(0,('is_candidate','=',True))
                            if field not in no_update_fields:
                                args_readonly.insert(0,('join_date','>=',today))
                                args_readonly.insert(0,'&'),
                            args_readonly.insert(0,'|'),
                        elif not args_readonly:
                            args_readonly = [('is_candidate','=',True)]
                            if field not in no_update_fields:
                                args_readonly.append(('join_date','>=',today))
                                args_readonly.insert(0,'&')
                        
                        if field == 'is_asset':
                            #Field is_asset chi readonly khi employee  dang co 1 hop dong transfer tu RR sang khac signed/cancel va join_date >= today
                            args_readonly = [('is_candidate','=',True),('join_date','>=',today)]
                        
                            
                        modifiers.update({'readonly' : args_readonly})
                        node.set('modifiers', json.dumps(modifiers))
                        

                    
            res['arch'] = etree.tostring(doc)
        return res
    
    
    def create_employee_from_candidate(self, cr, uid, value, context=None):
        if context is None:
            context = {}
        res = False
        resource_obj = self.pool.get('resource.resource')
        contract_obj = self.pool.get('hr.contract')
        instance_obj = self.pool.get('vhr.employee.instance')
        
        for field in ['job_family_id','job_group_id', 'sub_group_id']:
            context[field] = value.get(field, False)
            
        try:
            today = datetime.datetime.today().date().strftime(DEFAULT_SERVER_DATE_FORMAT)
            log.info("--- ---- Create Employee From Candidate")
            if value.get('is_create_account', False):
                is_create_account = value['is_create_account']
                context.update({'is_create_account': is_create_account})
                value['is_create_account'] = True if is_create_account == 'yes' else False
    #             del value['is_create_account']
    
            if value.get('is_asset', False):
                is_asset = value['is_asset']
                context.update({'is_asset': is_asset})
                value['is_asset'] = True if is_asset == 'yes' else False
    #             del value['is_asset']
            if value.get('date_start', False):
                date_start = value['date_start']
                context.update({'date_start': date_start})
                
            #When create contract for employee when transfer from candidate, it's main contract
            contract_val = {'is_main': True}
            contract_val.update(value)
            emp_id = False
            if value.get('employee_id', False):
                emp_id = value.get('employee_id') and value['employee_id'][0]
                emp_data = self.read(cr, uid, emp_id, ['active'])
                is_emp_active = emp_data.get('active', False)
                if not is_emp_active:
                    contract_ids = contract_obj.search(cr, uid, [('state','=','signed'),
                                                                 ('employee_id','=',emp_id)])
                    if contract_ids:
                        contract_val['change_form_code'] = 'vhr_master_data_back_to_work_change_form_code'
                    else:
                        #Employee dont have any signed contract
                        contract_val['change_form_code'] = 'vhr_master_data_input_data_into_iHRP'
                
#                 #When user choose ex_employee, need to check if have to create termination before create contract
#                 if value.get('change_form_id', False):
#                     contract_obj.check_to_create_termination_based_on_change_form(cr, uid, emp_id, value['change_form_id'], value.get('job_applicant_id', False), value['date_start'],context)
                
                not_update_fields = ['first_name','last_name','name','address_home_id','company_group_id']
                for field in not_update_fields:
                    if field in value:
                        del value[field]
                    
                    if field in contract_val:
                        del contract_val[field]
                        
                    
                contract_val.update({'employee_id': emp_id})
    
                context.update({'return_emp_from_candidate': True})
                value['is_transfer_from_rr'] = True
                value['active'] = True
                value['is_reject'] = False
                
                #Check if renew join_date of employee
                instance_ids = instance_obj.search(cr, uid, [('employee_id','=',emp_id),
                                                            ('date_start','<=',today),
                                                            '|',('date_end','>=',today),
                                                                ('date_end','=',False)], order='date_start asc')
                
                if not instance_ids and emp_id and value.get('date_start', False):
                    emp_data = self.read(cr, uid, emp_id, ['join_date'])
                    old_join_date = emp_data.get('join_date', False)
                    if old_join_date:
                        is_renew_join_date = self.compare_day(old_join_date,value['date_start'])
                    else:
                        is_renew_join_date = 1
                    if is_renew_join_date > 0:
                        value['join_date'] = value['date_start']
                        value['end_date'] = False
                        
#                 res = self.write(cr, uid, emp_id, value, context=context)
                res = self.write_with_log(cr, uid, emp_id, value, context=context)
                res_emp = self.browse(cr, uid, emp_id, context=context)
                if res_emp:
                    resource_ids = res_emp.resource_id and [res_emp.resource_id.id] or []
                    resource_obj.write(cr, uid, resource_ids, {'active': True}, context=context)
                    
                    user_id = res_emp.user_id and res_emp.user_id.id or False
                    if user_id:
                        self.pool.get('res.users').write(cr, SUPERUSER_ID, user_id, {'active': True})
                    
                    contract_val['work_email'] = res_emp.work_email or ''
                    contract_val['work_phone'] = res_emp.work_phone or ''
            else:
                context.update({'create_emp_from_candidate': True})
                if not value.get('bank_ids', False):
                    banks = self.get_unknown_bank(cr, uid, context=context)
                    if banks:
                        value.update({'bank_ids': banks})
                
                if value.get('last_name', False) and value.get('first_name', False):
                    value['name'] = value['last_name'] + ' ' + value['first_name']
                
                #add value join_date for employee
                if value.get('date_start', False):
                    value['join_date'] = value['date_start']
                
                value['is_transfer_from_rr'] = True
                
#                 emp_id = self.create(cr, uid, value, context=context)
                emp_id = self.create_with_log(cr, uid, value, context=context)
                if emp_id:
                    contract_val['employee_id'] = emp_id
                    contract_val['change_form_code'] = 'vhr_master_data_input_data_into_iHRP'
                    res = emp_id
                    
#                     self.update_change_form_id_for_job_applicant(cr, uid, contract_val.get('job_applicant_id', False), contract_val['change_form_code'], context)
            if res:
                #Get default value for pr.salary
                is_official = False
                if contract_val.get('type_id', False):
                    type = self.pool.get('hr.contract.type').browse(cr, uid, contract_val['type_id'])
                    is_official = type.contract_type_group_id and type.contract_type_group_id.is_offical or False
                
                if is_official:
                    salary_vals = {'type_of_salary': 'gross',
                                   'gross_salary': contract_val.get('gross_salary',0),
                                   }
                    salary_percentage = self.pool.get('ir.config_parameter').get_param(cr, uid, 'percentage_split_salary')
                    try:
                        salary_percentage = int(salary_percentage)
                    except:
                        salary_percentage = 0
                    salary_vals['salary_percentage'] = salary_percentage
                    
                    salary_pool = self.pool.get('vhr.pr.salary')
                    if salary_pool:
                        salary_vals = salary_pool.auto_split_salary_from_gross_salary(cr, uid, salary_vals, context)
                    
                    salary_vals['collaborator_salary'] = 0
                else:
                    salary_vals = {'collaborator_salary': contract_val.get('gross_salary',0),
                                   'gross_salary':0,
                                   'basic_salary':0,
                                   'probation_salary': 0,
                                   'salary_percentage':0,
                                   'v_bonus_salary':0}
                
                
                salary_vals['salary_by_hours_timeline_1_new'] = 0
                salary_vals['salary_by_hours_timeline_2_new'] = 0
                salary_vals['salary_by_hours_timeline_3_new'] = 0
                salary_vals['kpi_amount'] = 0
            
                contract_val.update(salary_vals)
                    
                #Create Contract
                if contract_val.get('date_start', False) and contract_val.get('type_id', False):
                    type_id = contract_val['type_id']
                    date_start = contract_val['date_start']
                    contract_val.update(contract_obj.get_date_end_and_life_of_contract(cr, uid, [], type_id, date_start))
                if contract_val.get('company_id', False):
                    comp_id = contract_val['company_id']
                    res_comp = self.pool.get('res.company').browse(cr, uid, comp_id, context=context)
                    signer_id = res_comp.sign_emp_id or ''
                    signer_title = res_comp.job_title_id or ''
                    signer_country = res_comp.country_signer and res_comp.country_signer.id or False
                    contract_val.update({'info_signer': signer_id,
                                         'title_signer': signer_title,
                                         'country_signer': signer_country})
                 
                contract_obj.create_contract_from_candidate(cr, uid, contract_val, context=context)
                
                log.info("--- ---- End Create Employee From Candidate")
                
                return emp_id
            
            log.info("--- ---- End Create Employee From Candidate")        
        
        except Exception as e:
            log.exception(e)
            try:
                error_message = e.message
                if not error_message:
                    error_message = e.value
            except:
                error_message = ""
            raise osv.except_osv('Error !', 'Error when create update from transfer RR: \n %s'% error_message)
                  
        return False
    
    def update_change_form_id_for_job_applicant(self, cr, uid, job_applicant_id, change_form_code_parameter, context=None):
        if job_applicant_id and change_form_code_parameter:
            applicant_obj = self.pool.get('vhr.job.applicant')
            
            change_form_code = self.pool.get('ir.config_parameter').get_param(cr, uid, change_form_code_parameter) or ''
            change_form_code = change_form_code.split(',')
            change_form_id = self.pool.get('vhr.change.form').search(cr, uid, [('code', 'in', change_form_code)], context=context)
            change_form_id = change_form_id and change_form_id[0] or False
            
            applicant_obj.write(cr, uid, job_applicant_id, {'change_form_id': change_form_id})
        
        return True
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context = {}
        employee_ids = []
        if context.get('is_employee_exlusion'):
            depament_obj = self.pool.get('hr.department')
            department_ids = depament_obj.search(cr, uid, [('organization_class_id.level','in',[1,3])])
            if department_ids:
                for item in depament_obj.browse(cr, uid, department_ids):
                    if item.manager_id:
                        employee_id = item.manager_id.id
                        if employee_id:
                            employee_ids.append(employee_id)
            args.append(('id','in',employee_ids))
        return super(hr_employee, self).search(cr, uid, args, offset=offset, limit=limit, order=order, context=context, count=count)

hr_employee()