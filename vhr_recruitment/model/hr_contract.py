# -*-coding:utf-8-*-
import logging
import datetime

import simplejson as json

from openerp.addons.vhr_common.model.vhr_common import vhr_common
from openerp.osv import osv, fields
from lxml import etree
from openerp import SUPERUSER_ID
from dateutil.relativedelta import relativedelta

from vhr_job_applicant import SIGNAL_OFFER_DONE
from vhr_job_applicant import SIGNAL_OFFER_CLOSE
from vhr_job_applicant import SIGNAL_DONE_CLOSE
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT

from openerp.addons.vhr_human_resource.model.vhr_termination_request import STATES as STATES_TERMINATE

log = logging.getLogger(__name__)

OFFER_EMPLOYEE_APPLICANT = {
    'office_id': 'offer_office_id',
    'type_id': 'contract_type_id',
    'date_start': 'join_date',
    'company_id': 'offer_company_id',
    'company_group_id': 'offer_com_group_id',
    'title_id': 'offer_job_title_id',
    'job_level_id': 'offer_job_level_id',
    
    'division_id': 'offer_division_id',
    'department_id': 'offer_department',
    'manager_id': 'offer_manager_id',
    'report_to': 'offer_report_to',
    'job_type_id': 'offer_job_type',
#     'position_class_id': 'position_class_apply_ex',
    'seat_no': 'seat_no_test',#dòng này chỉ nhằm mục đích lấy ra vals để truyền vào employee, 
}


class hr_contract(osv.osv, vhr_common):
    _inherit = 'hr.contract'
    _description = 'HR Contract'
    
    def _is_date_start_greater_today(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        today = datetime.datetime.today().date().strftime(DEFAULT_SERVER_DATE_FORMAT)
        for record in self.read(cr, uid, ids, ['date_start']):
            res[record['id']] = False
            date_start = record.get('date_start',False)
            if date_start:
                is_greater = self.compare_day(today, date_start)
                if is_greater >= 0:
                    res[record['id']] = True
                

        return res
    
    
    _columns = {
        'job_applicant_id': fields.many2one('vhr.job.applicant', 'Job Applicant'),
        'is_date_start_greater_today': fields.function(_is_date_start_greater_today, type='boolean', string='Is Date Start Greater Today'),
    }

    
    def onchange_date(self, cr, uid, ids, date_start, date_end, liquidation, contract_duration,
                      employee_id=None, type_id=None, company_id=None, date_start_temp=False, context=None):
        
        res = super(hr_contract, self).onchange_date(cr, uid, ids, date_start, date_end, liquidation, contract_duration, employee_id, type_id, company_id, date_start_temp, context)
        
        res['value']['is_date_start_greater_today'] = False
        if date_start or res['value'].get('date_start',False):
            today = datetime.datetime.today().date().strftime(DEFAULT_SERVER_DATE_FORMAT)
            date_start = res['value'].get('date_start', date_start)
            if date_start:
                is_greater = self.compare_day(today, date_start)
                if is_greater >= 0:
                    res['value']['is_date_start_greater_today'] = True
        
        return res
            
        
    def write(self, cr, uid, ids, vals, context=None):
        if not context:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]
        lst_update = {}
        job_obj = self.pool.get('vhr.job.applicant')
        salary_pool = self.pool.get('vhr.pr.salary')
        
        #Get list salary_ids before update contract to get correct effect_salary_ids
        salary_ids   = []
        if salary_pool:
            for contract_item in self.read(cr, uid, ids, ['job_applicant_id','effect_salary_id']):
                salary_id = contract_item.get('effect_salary_id',False) and contract_item['effect_salary_id'][0] or False
                job_applicant_id = contract_item.get('job_applicant_id',False) and contract_item['job_applicant_id'][0] or False
                if salary_id and job_applicant_id:
                    salary_ids.append(salary_id)
                
        res = super(hr_contract, self).write(cr, uid, ids, vals, context)
        
        for key, value in vals.iteritems():
            if key in OFFER_EMPLOYEE_APPLICANT:
                lst_update[OFFER_EMPLOYEE_APPLICANT[key]] = value
        if lst_update and not context.get('update_from_candidate', False):
            lst_candidate = []
            employee_ids = []
            for contract_item in self.browse(cr, uid, ids, context=context):
                if contract_item.state in ['draft', 'waiting'] and contract_item.job_applicant_id:
                    lst_candidate.append(contract_item.job_applicant_id.id)
                    employee_id = contract_item.employee_id and contract_item.employee_id.id or False
                    #Only update for employee if employee dont have any instance
                    if employee_id:
                        instance_ids = self.pool.get('vhr.employee.instance').search(cr, uid, [('employee_id','=',employee_id),('date_end','=',False)])
                        if not instance_ids:
                            employee_ids.append(employee_id)
                            
            if lst_candidate:
                job_obj.update_offer_from_contract(cr, uid, lst_candidate, lst_update)     
            #Update data employee(dont have any instance) from contract if contract created from transfer RR
            if employee_ids:
                update_fields = ['join_date','office_id','seat_no','division_id','department_id','team_id','title_id','job_level_id','report_to']
                emp_vals = {}
                for field in update_fields:
                    if field in vals:
                        emp_vals[field] = vals[field]
                    elif field == 'join_date' and 'date_start' in vals:
                        emp_vals[field] = vals['date_start']
                
                if emp_vals:
                    self.pool.get('hr.employee').execute_write(cr, uid, employee_ids, emp_vals)
            
                if salary_ids:
                    #If employee and contract are created during transfer from RR, try to update employee-company-effect_from in pr.salary 
                    #(salary is created during transfer from RR)
                    val_salary = {}
                    update_fields = ['employee_id', 'company_id','effect_from','payment_date']
                    for field in update_fields:
                        if field in vals:
                            val_salary[field] = vals[field]
                        elif field in ['effect_from','payment_date'] and 'date_start' in vals:
                            val_salary[field] = vals['date_start']
                    
                    if val_salary:
                        salary_pool.execute_write(cr, uid, salary_ids, val_salary)
        
        return res

    def button_set_to_signed(self, cr, uid, ids, context=None):
        job_app_obj = self.pool.get('vhr.job.applicant')
        res = super(hr_contract, self).button_set_to_signed(cr, uid, ids, context=context)
        job_app_ids = []
        for item in self.browse(cr, uid, ids, context=context):
            if item.job_applicant_id:
                job_app_ids.append(item.job_applicant_id.id)
        if job_app_ids:
            job_app_obj.sign_offer_from_contract(cr, uid, job_app_ids, context)
        return res

    def button_set_to_cancel_waiting(self, cr, uid, ids, context=None):
        job_app_obj = self.pool.get('vhr.job.applicant')
        resource_obj = self.pool.get('resource.resource')
        instance_obj = self.pool.get('vhr.employee.instance')
        
        res = super(hr_contract, self).button_set_to_cancel_waiting(cr, uid, ids, context=context)
        res_contract = self.browse(cr, uid, ids[0], context=context)
        if res_contract:
            if res_contract.job_applicant_id:
                job_app_ids = [res_contract.job_applicant_id.id]
                #Cancel offer from contract
                job_app_obj.cancel_offer_from_contract(cr, uid, job_app_ids, context)
                
                #Update join_date and end_date of employee
                employee_id = res_contract.employee_id and res_contract.employee_id.id or False
                instance_obj.update_join_date_employee(cr, uid, employee_id, context)
                
            if res_contract.employee_id:
                all_ids = self.search(cr, uid, [
                    ('employee_id', '=', res_contract.employee_id.id),
                    ('id', 'not in', ids), ('state', 'not in', ['cancel']),
                ], context=context)
                if not all_ids:
                    resource_ids = res_contract.employee_id.resource_id and [res_contract.employee_id.resource_id.id] or []
                    resource_obj.write(cr, uid, resource_ids, {'active': False}, context=context)
        return res

    def button_set_to_cancel_signed(self, cr, uid, ids, context=None):
        job_app_obj = self.pool.get('vhr.job.applicant')
        resource_obj = self.pool.get('resource.resource')
        res = super(hr_contract, self).button_set_to_cancel_signed(cr, uid, ids, context=context)
        res_contract = self.browse(cr, uid, ids[0], context=context)
        if res_contract:
            if res_contract.job_applicant_id:
                job_app_ids = [res_contract.job_applicant_id.id]
                #Cancel offer from contract
                job_app_obj.cancel_offer_from_contract(cr, uid, job_app_ids, context)
            if res_contract.employee_id:
                all_ids = self.search(cr, uid, [
                    ('employee_id', '=', res_contract.employee_id.id),
                    ('id', 'not in', ids), ('state', 'not in', ['cancel']),
                ], context=context)
                if not all_ids:
                    resource_ids = res_contract.employee_id.resource_id and [res_contract.employee_id.resource_id.id] or []
                    resource_obj.write(cr, uid, resource_ids, {'active': False}, context=context)
        return res
    
    def create_contract_from_candidate(self, cr, uid, value, context=None):
        if not context:
            context = {}
            
        config_obj = self.pool.get('ir.config_parameter')
        change_form_obj = self.pool.get('vhr.change.form')
        bank_obj = self.pool.get('res.partner.bank')
        currency_obj = self.pool.get('res.currency')
        if value.get('parent_id', False):
            value.update({'manager_id': value['parent_id']})
            del value['parent_id']
        if value.get('change_form_code', False):
            change_form_code = config_obj.get_param(cr, uid, value['change_form_code']) or ''
            change_form_id = change_form_obj.search(cr, uid, [('code', '=', change_form_code)], context=context)
            value['change_form_id'] = change_form_id and change_form_id[0] or None
            del value['change_form_code']
        bank_ids = bank_obj.search(cr, uid, [('employee_id', '=', value['employee_id']), ('is_main', '=', True)])
        bank_contract = []
        if bank_ids:
            currency_ids = currency_obj.search(cr, uid, [('name', '=', 'VND')])
            currency_id = currency_ids and currency_ids[0] or False
            bank_contract.append([0, False, {'bank_id': bank_ids[0], 'weight': 100, 'currency': currency_id,
                                             'value_type': 'percent', 'employee_id': value['employee_id']}])
            value.update({'bank_account_ids': bank_contract})
        
        if 'state' not in value:
            value['state'] = 'draft'
        
        context['force_create_working_record'] = True
#         contract_id = self.create(cr, uid, value, context=context)
        contract_id = self.create_with_log(cr, uid, value, context=context)
        
        #Create Working Record when create contract from transfer RR
#         self.create_working_record_from_rr(cr, uid, contract_id, context)
        
        return contract_id
    
    def create_working_record_from_rr(self, cr, uid, contract_id, context=None):
        """
        Create First Working Record for contract in case contract dont have first_working_record_id
        """
        if not context:
            context = {}
        if contract_id:
            config_parameter = self.pool.get('ir.config_parameter')
            change_local_comp_code = config_parameter.get_param(cr, uid, 'vhr_master_data_change_local_company') or ''
            change_local_comp_code = change_local_comp_code.split(',')
                       
            record = self.browse(cr, uid, contract_id)
            if not record.first_working_record_id:
                if record.change_form_id and record.change_form_id.code in change_local_comp_code:
                    context['do_not_update_annual_day'] = True
                       
#                 if record.change_form_id:#Even when dont have change_form_id , have to create WR, -_-
                context['signed_contract'] = record.id
                context['include_not_signed_contract'] = True
                self.create_working_record(cr, uid, [record.id], {}, context)
         
        return True
    
    def update_data_from_candidate(self, cr, uid, value, context=None):
        if not context:
            context = {}
        
        context.update({'update_from_candidate': True, 
#                         'do_not_create_update_salary': True,
                        'include_not_signed_contract': True,
                        'force_create_working_record': True,
                        })
        
        for field in ['job_family_id','job_group_id', 'sub_group_id']:
            context[field] = value.get(field, False)
            
        emp_obj = self.pool.get('hr.employee')
        salary_pool = self.pool.get('vhr.pr.salary')
        instance_obj = self.pool.get('vhr.employee.instance')
        working_obj = self.pool.get('vhr.working.record')
        
        today = datetime.datetime.today().date().strftime(DEFAULT_SERVER_DATE_FORMAT)
        
        if value.get('is_asset', False) and value['is_asset'] in ['yes','no']:
            value['is_asset'] = True if value['is_asset'] == 'yes' else False
        
        if value.get('is_create_account', False) and value['is_create_account'] in ['yes','no']:
            value['is_create_account'] = True if value['is_create_account'] == 'yes' else False
            
        not_update_fields = ['first_name','last_name','name','address_home_id','company_group_id']
        for field in not_update_fields:
            if field in value:
                del value[field]
            
        if not value.get('job_applicant_id', False):
            raise osv.except_osv('Validation Error !', 'Cannot find job applicant id!')
        job_applicant_id = value['job_applicant_id']

        contract_ids = self.search(cr, uid, [('job_applicant_id', '=', job_applicant_id), 
                                             ('state', 'not in', ['signed'])], order='date_start desc', limit=1, context=context)
        if not contract_ids:
            raise osv.except_osv('Validation Error !', 'Cannot find available contract to update!')
        
        #Check if contract/employee is isactive/cancel
        contract = self.read(cr, uid, contract_ids[0], ['employee_id','date_start','company_id','change_form_id'])
        employee_id = contract.get('employee_id', False) and contract['employee_id'][0] or False
        date_start = contract.get('date_start', False)
        
        old_company_id = contract.get('company_id', False) and contract['company_id'][0] or False
        change_form_id = contract.get('change_form_id', False) and contract['change_form_id'][0] or False
        
        is_employee_active = True
        
        if value.get('employee_id', False) and isinstance(value['employee_id'], tuple):
            value['employee_id'] = value['employee_id'][0]
        
        old_employee_id = False
        if employee_id and employee_id != value['employee_id']:
          #Case change employee_id in hr.job.applicant
          old_employee_id = employee_id
          employee_id = value['employee_id']
          
          #Find active employee instance
          instance_ids = instance_obj.search(cr, uid, [('employee_id','=',old_employee_id),
                                                                ('date_start','<=',today),
                                                                '|',('date_end','>=',today),
                                                                    ('date_end','=',False)], order='date_start asc')
          #Check to inactive old_employee and remove working record, pr.salary of old_employee
          if not instance_ids:
              emp_obj.write(cr, uid, old_employee_id, {'active': False})
        
        if employee_id:
                    
            employee = emp_obj.read(cr, uid, employee_id, ['active','user_id'])
            is_employee_active = employee.get('active', False)
            
            user_id = employee.get('user_id', False) and employee['user_id'][0]
            if user_id:
                self.pool.get('res.users').write(cr, SUPERUSER_ID, user_id, {'active': True})
                
            #If employee is inactive, active it and set state contract = 'waiting', create pr.salary
            if not is_employee_active:
                emp_obj.write(cr, uid, employee_id, {'active': True,'is_reject': False})
                val_contract = {'state': 'draft'}
#                 if old_employee_id:
#                     #When change employee, employee in contract will be changed
#                     val_contract['employee_id'] = employee_id
                
                self.write_with_log(cr, uid, contract_ids, val_contract, context=context)
        
        if value.get('employee_id', False):
            employee_id = value['employee_id']
#             del value['employee_id']
            #add value join_date for employee
            if value.get('date_start', False):
                instance_ids = instance_obj.search(cr, uid, [('employee_id','=',employee_id),
                                                                ('date_start','<=',today),
                                                                '|',('date_end','>=',today),
                                                                    ('date_end','=',False)], order='date_start asc')
                #Only update join date of employee if employee dont have any active instance
                if not instance_ids:
                    value['join_date'] = value['date_start']
                    value['end_date'] = False
            
            value['is_transfer_from_rr'] = True
            
                
#             emp_obj.write(cr, uid, [employee_id], value, context=context)
            emp_obj.write_with_log(cr, uid, [employee_id], value, context=context)

        new_date_start = value.get('date_start', False)
        type_id = value.get('type_id', False)
        if new_date_start and type_id:
            value.update(self.get_date_end_and_life_of_contract(cr, uid, [], type_id, new_date_start))

        if value.get('parent_id', False):
            value.update({'manager_id': value['parent_id']})
            del value['parent_id']
        
        val_contract = value.copy() or {}
        
        if set(['gross_salary','probation_salary','employee_id','company_id','date_start']).intersection(set(val_contract.keys())) and salary_pool:
            default_salary_percentage = self.pool.get('ir.config_parameter').get_param(cr, uid, 'percentage_split_salary')
            try:
                default_salary_percentage = int(default_salary_percentage)
            except:
                default_salary_percentage = 0
            
            is_official = False
            if val_contract.get('type_id', False):
                type = self.pool.get('hr.contract.type').browse(cr, uid, val_contract['type_id'])
                is_official = type.contract_type_group_id and type.contract_type_group_id.is_offical or False
            
            if is_official:
                
                val_contract['salary_percentage'] = default_salary_percentage
                val_contract['collaborator_salary'] = 0
                val_contract = salary_pool.auto_split_salary_from_gross_salary(cr, uid, val_contract, context)
            else:
                val_contract['collaborator_salary'] = val_contract.get('gross_salary',0)
                val_contract.update({'gross_salary':0,
                                     'basic_salary':0,
                                     'salary_percentage':0,
                                     'v_bonus_salary':0})
                
                
            val_contract['salary_by_hours_timeline_1_new'] = 0
            val_contract['salary_by_hours_timeline_2_new'] = 0
            val_contract['salary_by_hours_timeline_3_new'] = 0
            val_contract['kpi_amount'] = 0
            
        
        #Cheat, because in HR, when change company --> change change_form_id --> delete old WR, create new WR
        #So in RR, when change company, employee, try to update change_form_id to go in workflow
        if old_employee_id or old_company_id != val_contract.get('company_id', False):
            val_contract['change_form_id'] = change_form_id
        
#         new_change_form_id = val_contract.get("change_form_id", False)
#         if isinstance(new_change_form_id, tuple):
#             new_change_form_id = new_change_form_id[0]
#         
#         #if dont change change_form_id and change date_start in offer form, try to update approve_last_working_day in Termination
#         if not old_employee_id and new_change_form_id == change_form_id and change_form_id and self.compare_day(date_start, val_contract['date_start']) < 0:
#             self.update_termination_date_end_working_approve(cr, uid, val_contract.get('job_applicant_id'), val_contract['date_start'], context)
            
#         self.write(cr, uid, contract_ids, val_contract, context=context)
        self.write_with_log(cr, uid, contract_ids, val_contract, context=context)
        
        #In case cb cancel contract and rr transfer again, need to recreate WR
        self.create_working_record_from_rr(cr, uid, contract_ids[0], context)
        
#         if old_employee_id or (new_change_form_id and new_change_form_id != change_form_id):
#             self.check_to_cancel_old_termination(cr, uid, val_contract.get('job_applicant_id'), context)
#         
#          #if dont change change_form_id and change date_start in offer form, try to update approve_last_working_day in Termination
#         if not old_employee_id and new_change_form_id == change_form_id and change_form_id and self.compare_day(date_start, val_contract['date_start']) >= 0:
#             self.update_termination_date_end_working_approve(cr, uid, val_contract.get('job_applicant_id'), val_contract['date_start'], context)
#         
#         self.check_to_create_termination_based_on_change_form(cr, uid, value.get('employee_id', False), value.get('change_form_id', False), value.get('job_applicant_id', False), value['date_start'], context)
#         #Cheat to update working record of contract to create instance
#         self.write(cr, uid, contract_ids, {'job_level_id': val_contract.get('job_level_id', False)}, context)
        
            
        
    def check_to_create_termination_based_on_change_form(self, cr, uid, employee_id, change_form_id, job_applicant_id, date_start, context=None):
        """
        If user choose change form "change type of contract" ===> Create termination for old contract
        """
        if not context:
            context = {}
        
        try:
            if employee_id and change_form_id and date_start:
                if isinstance(employee_id, tuple):
                    employee_id  = employee_id[0]
                change_type_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_master_data_change_type_of_contract')
                change_type_code_list = change_type_code.split(',')
                
                change_type_code_ids = self.pool.get('vhr.change.form').search(cr, uid, [('code','in',change_type_code_list)])
                
                if change_form_id in change_type_code_ids:
                    #Check to create termination
                    date_start = datetime.datetime.strptime(date_start,DEFAULT_SERVER_DATE_FORMAT)
                    last_working_day = (date_start - relativedelta(days=1)).strftime(DEFAULT_SERVER_DATE_FORMAT)
                    
                    vals = {'is_change_contract_type': True,
                            'is_offline': True,
                            'job_applicant_id'       : job_applicant_id}
                    
                    self.create_termination_request(cr, uid, employee_id, last_working_day, vals, context)
        except Exception as e:
            log.exception(e)
            try:
                error_message = e.message
                if not error_message:
                    error_message = e.value
            except:
                error_message = ""
            error_message = ' '.join(error_message.split())
            if 'Trace Log' in error_message:
                index = error_message.index('Trace Log')
                error_message = error_message[:index] + '\n' + error_message[index:]
            raise osv.except_osv('Error !', 'Having error during create Termination offline for employee: \n\n\n Trace: %s '% error_message)
        
        return True

    def check_to_cancel_old_termination(self, cr, uid, job_applicant_id, context=None):
        """
        Cancel Termination create from transfer RR
        """
        if job_applicant_id:
            termination_obj = self.pool.get('vhr.termination.request')
            working_obj = self.pool.get('vhr.working.record')
            termination_ids = termination_obj.search(cr, uid, [('job_applicant_id','=',job_applicant_id),
                                                               ('state','!=','cancel')])
            if termination_ids:
                termination = termination_obj.read(cr, uid, termination_ids[0], ['state','contract_id'])
                current_state = termination.get('state','')
                contract_id = termination.get('contract_id', False) and termination['contract_id'][0] or False
                list_states = {item[0]: item[1] for item in STATES_TERMINATE}
                
                context = {'ACTION_COMMENT': 'Cancel Termination When RR change employee/change form to transfer'}
                termination_obj.write_log_state_change(cr, uid, termination_ids[0], list_states[current_state], list_states['cancel'], context)
                
                termination_obj.write(cr, uid, termination_ids, {'state':'cancel'})
                
                working_ids = working_obj.search(cr, uid, [('termination_id','=',termination_ids[0])])
                if working_ids:
                    working_obj.unlink_working_record_in_the_middle_of_flow(cr, uid, working_ids, context)
                
                if contract_id:
                    self.pool.get('hr.contract').write(cr, uid, {'liquidation_date': False})
                    
        
        return True
    
    def update_termination_date_end_working_approve(self, cr, uid, job_applicant_id, new_contract_date_start, context=None):
        if job_applicant_id and new_contract_date_start:
            termination_obj = self.pool.get('vhr.termination.request')
            contract_obj = self.pool.get('hr.contract')
            
            termination_ids = termination_obj.search(cr, uid, [('job_applicant_id','=',job_applicant_id),
                                                               ('state','!=','cancel')])
            
            new_contract_date_start = datetime.datetime.strptime(new_contract_date_start,DEFAULT_SERVER_DATE_FORMAT)
            new_date_end_working_approve = (new_contract_date_start - relativedelta(days=1)).strftime(DEFAULT_SERVER_DATE_FORMAT)
                    
            update_termination_ids = []
            contract_ids = []
            if termination_ids:
                for termination in termination_obj.read(cr, uid, termination_ids, ['date_end_working_approve','date_end_contract','contract_id']):
                    date_end_working_approve = termination.get('date_end_working_approve', False)
                    date_end_contract = termination.get('date_end_contract', False)
                    contract_id = termination.get('contract_id', False) and termination['contract_id'][0]
                    #Update Termination if: new_date_end_working_approve <= date_end_contract
                    if date_end_contract and self.compare_day(date_end_contract, new_date_end_working_approve) > 0:
                        new_date_end_working_approve = date_end_contract
                    update_termination_ids.append(termination['id'])
                    if contract_id:
                        contract_ids.append(contract_id)
            
            if contract_ids:
                last_working_day = datetime.datetime.strptime(new_date_end_working_approve, DEFAULT_SERVER_DATE_FORMAT).date()
                liquidation_date = last_working_day + relativedelta(days=1)
                liquidation_date = liquidation_date.strftime(DEFAULT_SERVER_DATE_FORMAT)
                for contract_id in contract_ids:
                    is_update = contract_obj.update_liquidation_date(cr, uid, contract_id, liquidation_date, context)
                    if not is_update:#In case new liquidation date >date_end:: do not need to update liquidation date
                        contract_obj.write(cr, uid, contract_id, {'liquidation_date':False})
                        
            if update_termination_ids:
                termination_obj.write(cr, uid, update_termination_ids, {'date_end_working_approve': new_date_end_working_approve})
            
            
        return True
                
    
    def create_termination_request(self, cr, uid, employee_id, last_working_day, vals = {}, context=None):
        if employee_id and last_working_day:
            termination_obj = self.pool.get('vhr.termination.request')
            termination_fields = termination_obj._columns.keys()
            record_vals = termination_obj.default_get(cr, uid, termination_fields, context)
            record_vals.update(vals)
            record_vals['employee_id'] = employee_id
            
            onchange_emp_data = termination_obj.onchange_employee_id(cr, uid, [], employee_id, True)
            onchange_emp_value = onchange_emp_data.get('value', {})
            
            record_vals.update(onchange_emp_value)
            if onchange_emp_value.get('date_end_contract', False):
                date_end_contract = onchange_emp_value['date_end_contract']
                gap = self.compare_day(date_end_contract, last_working_day)
                if gap > 0:
                    last_working_day = date_end_contract
                
            record_vals['date_end_working_approve'] = last_working_day
            record_vals['date_end_working_expect'] = last_working_day
            created_termination = self.check_if_have_created_termination(cr, uid, employee_id, record_vals.get('company_id', False), record_vals.get('contract_id', False), context=None)
            #If have created Termination, do not create termination anymore
            if created_termination:
                return True
            
            termination_id = termination_obj.create(cr, uid, record_vals, context)
            if termination_id:
#                 termination_obj.create_simple_audittrail_log(cr, uid, 'create', [termination_id], record_vals, context)
                context = {'action':'submit',
                           'is_offline': True,
                           'is_official': record_vals.get('is_official', False),
                           'ACTION_COMMENT': 'Change contract type when transfer from RR'}
                termination_obj.execute_workflow(cr, uid, termination_id, context)
                
                #Try to update liquidation of contract
                contract_id = record_vals.get('contract_id', False)
                if contract_id:
                    last_working_day = datetime.datetime.strptime(last_working_day, DEFAULT_SERVER_DATE_FORMAT).date()
                    liquidation_date = last_working_day + relativedelta(days=1)
                    liquidation_date = liquidation_date.strftime(DEFAULT_SERVER_DATE_FORMAT)
                    
                    self.pool.get('hr.contract').update_liquidation_date(cr, uid, contract_id, liquidation_date, context)
        
        return True
    
    def check_if_have_created_termination(self, cr, uid, employee_id, company_id, contract_id, context=None):
        termination_ids = []
        if employee_id and company_id and contract_id:
            termination_ids = self.pool.get('vhr.termination.request').search(cr, uid, [('employee_id', '=', employee_id),
                                                                                        ('company_id', '=', company_id),
                                                                                        ('contract_id','=',contract_id),
                                                                                        ('state', '=', 'finish')])
        
        return termination_ids and True or False
            
            
                
    
    def fields_view_get(self, cr, uid, view_id = None, view_type = 'form', context = None, toolbar = False, submenu = False):
        """
         Do not allow to edit contract if date_start >= today, and contract created when transfer employee from RR to HR(except when state='signed')
        """
        res = super(hr_contract, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar = toolbar, submenu = submenu)
        if context is None:
            context = {}
        if view_type == 'form':
            doc = etree.XML(res['arch'])
            if res['type'] == 'form':
                
                fields = self._columns.keys()
                
                today = datetime.datetime.today().date().strftime(DEFAULT_SERVER_DATE_FORMAT)
                not_check_fields = ['sign_date','info_signer','title_signer','country_signer','ts_working_group_id',
                                    'mission_ids','result_ids', 'timesheet_id','salary_setting_id','working_time','appendix_ids',
                                    'working_address','working_salary','contract_terms','change_form_id','job_description',
                                    'job_family_id','job_group_id','sub_group_id','career_track_id','last_date_invited',
                                    'delivery_note','is_delivered','delivery_id','receiver_id','is_received','number_of_invited',
                                    'mail_to_remind']
                fields = list( set(fields).difference(set(not_check_fields)) )
                for field in fields:
                    for node in doc.xpath("//field[@name='%s']" %field):
                        modifiers = json.loads(node.get('modifiers'))
                        #inherit args_readonly
                        args_readonly = modifiers.get('readonly',False)
                         
                        if isinstance(args_readonly, list):
                            args_readonly.insert(0,('is_date_start_greater_today','=',True))
                            args_readonly.insert(0,('job_applicant_id','!=',False))
                            args_readonly.insert(0,('state','!=','signed'))
                            args_readonly.insert(0,'&'),
                            args_readonly.insert(0,'&'),
                            args_readonly.insert(0,'|'),
                        elif not args_readonly:
                            args_readonly = [('is_date_start_greater_today','=',True), ('job_applicant_id','!=',False),('state','!=','signed')]
                        
                        if field == 'job_level_position_id':
                            args_required = args_readonly[:]
                            args_required.insert(0,"!")
                            modifiers.update({'required' : args_required})
                            
                        modifiers.update({'readonly' : args_readonly})
                        node.set('modifiers', json.dumps(modifiers))
                    
            res['arch'] = etree.tostring(doc)
        return res

hr_contract()
