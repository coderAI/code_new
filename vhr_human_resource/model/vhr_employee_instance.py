# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import datetime
from openerp import SUPERUSER_ID

log = logging.getLogger(__name__)


class vhr_employee_instance(osv.osv):
    _inherit = 'vhr.employee.instance'
    _description = 'VHR Employee Instance'

    _columns = {
        'start_wr_id': fields.many2one('vhr.working.record', 'Start Working Record'),
        'end_wr_id': fields.many2one('vhr.working.record', 'End Working Record'),
    }

    _unique_insensitive_constraints = [{'start_wr_id': "Start Working Record is already exist!"},
                                       {'end_wr_id': "End Working Record is already exist!"},
    ]

    @staticmethod
    def get_position_info(obj_working):
        return {'division_id': obj_working.division_id_new and obj_working.division_id_new.id or False,
                'department_group_id': obj_working.department_group_id_new and obj_working.department_group_id_new.id or False,
                'department_id': obj_working.department_id_new and obj_working.department_id_new.id or False,
                'team_id': obj_working.team_id_new and obj_working.team_id_new.id or False,
                'title_id': obj_working.job_title_id_new and obj_working.job_title_id_new.id or False,
#                 'job_level_id': obj_working.job_level_id_new and obj_working.job_level_id_new.id or False,
                
                #New job level
#                 'job_level_position_id': obj_working.job_level_position_id_new and obj_working.job_level_position_id_new.id or False,
                'job_level_person_id': obj_working.job_level_person_id_new and obj_working.job_level_person_id_new.id or False,
                'manager_id': obj_working.manager_id_new and obj_working.manager_id_new.id or False,
                'report_to': obj_working.report_to_new and obj_working.report_to_new.id or False}

    def check_instance_exit(self, cr, uid, change_form, obj_working, dismiss_code_list, start_code_list, context=None):
        """
        Cập nhật date_start, date_end cho employee instance khi obj_working là working record đầu tiên hoặc cuối cùng gắn với instance đó
        @return: True khi obj_working là start_wr_id hoặc end_wr_id
                 False với các trường hợp khác
        """
        ids = self.search(cr, uid, [('start_wr_id', '=', obj_working.id)])
        position_info = self.get_position_info(obj_working)
        if ids:
            if change_form.code in start_code_list:
                update_data = {'date_start': obj_working.effect_from}
                update_data.update(position_info)
                self.write(cr, uid, ids, update_data)
#             else:
#                 self.unlink(cr, uid, ids)
            return True
        ids = self.search(cr, uid, [('end_wr_id', '=', obj_working.id)])
        if ids:
            if change_form.code in dismiss_code_list:
                update_data = {'date_end': obj_working.effect_from}
                update_data.update(position_info)
                self.write(cr, uid, ids, update_data)
            else:
                update_data = {'date_end': False}
                update_data.update(position_info)
                self.write(cr, uid, ids, update_data)
            return True
        return False

    def new_instance(self, cr, uid, change_form, obj_working, dismiss_code_list, start_code_list, context=None):
        """
        Cập nhật lại date_end và end_wr_id khi obj_working có change form là dismiss
        Tạo mới employee instance khi obj_working có change form là gia nhập cty/quay lại làm việc
        """
        
        position_info = self.get_position_info(obj_working)
        if change_form.code in dismiss_code_list:
            args = [('employee_id', '=', obj_working.employee_id.id), ('company_id', '=', obj_working.company_id.id)]
            instance_id = self.search(cr, uid, args, None, None, 'date_start desc', context, False)
            if not instance_id:
                return False
            instance_id = instance_id[0]
            update_data = {'date_end': obj_working.effect_from, 'end_wr_id': obj_working.id}
            update_data.update(position_info)
            return self.write(cr, uid, instance_id, update_data)
        elif change_form.code in start_code_list:
            args = [('employee_id', '=', obj_working.employee_id.id),
                    ('company_id', '=', obj_working.company_id.id),
                    ('date_end', '=', False)]
            instance_id = self.search(cr, uid, args, None, None, 'date_start desc', context, False)
            if instance_id:
                return False

            vals = {'employee_id': obj_working.employee_id.id,
                    'company_id': obj_working.company_id.id,
                    'date_start': obj_working.effect_from,
                    'start_wr_id': obj_working.id,
                    'working_record_id': obj_working.id}
            vals.update(position_info)
            return self.create(cr, uid, vals)
        return False

    def delete_wr(self, cr, uid, obj_working, context=None):
        """
        Xóa employee instance khi obj_working là start_wr_id
        Cập nhật date_end = False khi obj_working là end_wr_id
        """
        ids = self.search(cr, uid, [('start_wr_id', '=', obj_working.id)])
        if ids:
            employee_id = obj_working.employee_id and obj_working.employee_id.id or False
            self.unlink(cr, uid, ids)
            #Cập nhật lại join_date, end_date của employee
            self.update_join_date_employee(cr, uid, employee_id, context)
            return True
        
        ids = self.search(cr, uid, [('end_wr_id', '=', obj_working.id)])
        if ids:
            self.write(cr, uid, ids, {'date_end': False})
            return True
        return False
    
    
    def update_join_date_employee(self, cr, uid, employee_id, context=None):
        """
        Recheck join_date and end_date of employee
        """
        if employee_id:
            today = datetime.today().date()
            #Find active instance
            val = {'end_date': False}
            active_instance_ids = self.search(cr, uid, [('employee_id','=',employee_id),
                                                        ('date_start','<=',today),
                                                        '|',('date_end','=',False),
                                                            ('date_end','>=',today)], order='date_start asc')
            if active_instance_ids:
                #Get join_date = date_start of earliest active instance
                instance = self.read(cr, uid, active_instance_ids[0], ['date_start'])
                date_start = instance.get('date_start', False)
                val['join_date'] = date_start
            else:
                active_instance_ids = self.search(cr, uid, [('employee_id','=',employee_id),
                                                            ('date_end','<=',today)], order='date_end desc')
                if active_instance_ids:
                    instance = self.read(cr, uid, active_instance_ids[0], ['date_start', 'date_end'])
                    val['join_date'] = instance.get('date_start',False)
                    val['end_date'] = instance.get('date_end', False)
                else:
                    val['join_date'] = False
            
            if len(val) > 1:
                self.pool.get('hr.employee').write_with_log(cr, uid, employee_id, val, context)
        
        return True

    def update_employee_instance(self, cr, uid, ids, context=None):
        if isinstance(ids, list):
            ids = ids[0]
        working_record = self.pool.get('vhr.working.record')
        config_parameter = self.pool.get('ir.config_parameter')
        obj_working = working_record.browse(cr, uid, ids)
        dismiss_code = config_parameter.get_param(cr, uid, 'vhr_master_data_dismiss_change_form_code') or ''
        dismiss_code_list = dismiss_code.split(',')
        
        dismiss_local_code = config_parameter.get_param(cr, uid, 'vhr_master_data_dismiss_local_company') or ''
        dismiss_local_code_list = dismiss_local_code.split(',')
        
        dismiss_code_list += dismiss_local_code_list
        
        back_work = config_parameter.get_param(cr, uid, 'vhr_master_data_back_to_work_change_form_code') or ''
        back_work = back_work.split(',')
        
        input_ihrp = config_parameter.get_param(cr, uid, 'vhr_master_data_input_data_into_iHRP') or ''
        input_ihrp = input_ihrp.split(',')
        
        change_type_code = config_parameter.get_param(cr, uid, 'vhr_master_data_change_type_of_contract') or ''
        change_type_code_list = change_type_code.split(',')
        
        change_local_comp_code = config_parameter.get_param(cr, uid, 'vhr_master_data_change_local_company') or ''
        change_local_comp_code_list = change_local_comp_code.split(',')
        
        start_code_list = back_work + input_ihrp + change_type_code_list + change_local_comp_code_list
        
        if context is None:
            context = {}
        if context.get('unlink_wr'):
            #Khi xóa Working Record
            self.delete_wr(cr, uid, obj_working, context)
            return True
        
        change_form_code_list = [form.code for form in obj_working.change_form_ids]
        is_employee_active = obj_working.employee_id and obj_working.employee_id.active or False
        #Only check to create/update employee instance if employee is active or update termination working record
        if is_employee_active or set(change_form_code_list).intersection(set(dismiss_code_list)) or context.get('check_employee_instance',False):
            for change_form in obj_working.change_form_ids:
                flag = self.check_instance_exit(cr, uid, change_form, obj_working, dismiss_code_list, start_code_list, context)
                if not flag:
                    self.new_instance(cr, uid, change_form, obj_working, dismiss_code_list, start_code_list, context)
        return True
    
    def create(self, cr, uid, vals, context=None):
        res = super(vhr_employee_instance, self).create(cr, uid, vals, context)
        
         #When create a new employee instance, update end_date = null for employee
        if res and vals.get('date_start') and vals.get('employee_id')  and vals.get('company_id'):
            employee = self.pool.get('hr.employee')
            val_emp = {'end_date': False}
            
            today = datetime.today().date()
            
            active_ids = self.search(cr, uid, [('employee_id','=', vals.get('employee_id', False)),
                                               ('id','!=', res),
                                               ('date_start','<=',today),
                                               '|',('date_end','=',False),
                                                   ('date_end','>=',today)])
            
            args = [('company_id', '!=', vals.get('company_id')), 
                    ('employee_id', '=', vals.get('employee_id')), 
                    ('date_start', '<=', vals.get('date_start')), 
                    '|',('date_end','=',False),
                        ('date_end', '>=', vals.get('date_start'))]
            
            ids = self.search(cr, uid, args, 0, None, 'id')
            if not ids:
                #Nếu instance cuối cùng có end_wr_id là xử lý nội bộ cty có nghĩa là join_date của employee vẫn đang lấy theo 1 instance trong quá khứ
                # lúc này thì bỏ qua quá trình cập nhật join_date
                nearest_ids = self.search(cr, uid, [('employee_id','=',vals.get('employee_id',False)),
                                                     ('date_end','<=',vals.get('date_start', False))], order='date_end desc')
                if nearest_ids:
                    record = self.browse(cr, uid, nearest_ids[0], fields_process=['end_wr_id'])
                    change_form_ids = record.end_wr_id and record.end_wr_id.change_form_ids or []
                    change_form_code_list = [form.code for form in change_form_ids]
                    
                    change_local_comp_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_master_data_dismiss_local_company') or ''
                    change_local_comp_code_list = change_local_comp_code.split(',')
                    if not set(change_form_code_list).intersection(set(change_local_comp_code_list)):
                        val_emp['join_date'] = vals.get('date_start',False)
                        if active_ids:
                            val_emp = {}
                else:
                    val_emp['join_date'] = vals.get('date_start',False)
            
            if val_emp:
                employee.write_with_log(cr, uid, [vals.get('employee_id')], val_emp, context={})
       
        
        return res
    
    def write(self, cr, uid, ids, vals, context=None):
        if not context:
            context = {}
            
        if not isinstance(ids, list):
            ids = [ids]
        
        old_date_end_list = {}
        if 'date_end' in vals:
            records = self.read(cr, uid, ids, ['date_end'])
            for record in records:
                old_date_end_list[record['id']] = record.get('date_end', False)
                
        res = super(vhr_employee_instance, self).write(cr, uid, ids, vals, context)
        
        if vals.get('date_start'):
            employee = self.pool.get('hr.employee')
            for item in self.browse(cr, uid, ids):
                company_id = vals.get('company_id') or item.company_id.id
                employee_id = vals.get('employee_id') or item.employee_id.id
                
                today = datetime.today().date()
            
                active_ids = self.search(cr, uid, [('employee_id','=', employee_id),
                                                   ('id','not in', ids),
                                                   ('date_start','<=',today),
                                                   '|',('date_end','=',False),
                                                       ('date_end','>=',today)])
                
            
                args = [('company_id', '!=', company_id), ('employee_id', '=', employee_id), \
                        ('date_start', '<=', vals.get('date_start')), 
                        '|',('date_end','=',False),
                            ('date_end', '>=', vals.get('date_start'))]
                ids = self.search(cr, uid, args, 0, None)
                if not ids:
                    #Nếu instance cuối cùng có end_wr_id là xử lý nội bộ cty có nghĩa là join_date của employee vẫn đang lấy theo 1 instance trong quá khứ
                    # lúc này thì bỏ qua quá trình cập nhật join_date
                    val_emp = {'end_date': False}
                    nearest_ids = self.search(cr, uid, [('employee_id','=',employee_id),
                                                         ('date_end','<=',vals.get('date_start', False))], order='date_end desc')
                    if nearest_ids:
                        record = self.browse(cr, uid, nearest_ids[0], fields_process=['end_wr_id'])
                        change_form_ids = record.end_wr_id and record.end_wr_id.change_form_ids or []
                        change_form_code_list = [form.code for form in change_form_ids]
                        
                        change_local_comp_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_master_data_dismiss_local_company') or ''
                        change_local_comp_code_list = change_local_comp_code.split(',')
                        if not set(change_form_code_list).intersection(set(change_local_comp_code_list)):
                            val_emp['join_date'] = vals.get('date_start',False)
                            if active_ids:
                                val_emp = {}
                    else:
                        val_emp['join_date'] = vals.get('date_start',False)
                    
                    if val_emp:
                        employee.write_with_log(cr, uid, [employee_id], val_emp, context={})
                    
        #If update date_end of employee instance, it's mean that employee will terminate after date_end
        #So we will update date_end of hr_employee 
        # Update date_end of active timesheet_employee and active working schedule employee if dont have any else instance with date_end = False
        #and delete timesheet employee and working schedule employee of employee in future
        if res and 'date_end' in vals:
            date_end = vals['date_end']
            for record in self.read(cr, uid, ids, ['employee_id','company_id']):
                old_date_end = old_date_end_list.get(record['id'],False)
                old_date_end = old_date_end and datetime.strptime(old_date_end, DEFAULT_SERVER_DATE_FORMAT)
                
                employee_id = record.get('employee_id',False) and record['employee_id'][0] or False
                company_id = record.get('company_id',False) and record['company_id'][0] or False
                if employee_id:
                    
                    active_instance_ids = self.search(cr, uid, [('employee_id','=',employee_id),
                                                                    ('date_end','=',False)])
                    active_instance_ids = list(set(active_instance_ids).difference(ids))
                    
                    #Remove instance create when transfer RR and contract is not sign
                    active_instance_ids, rm_instance_ids = self.filter_ghost_instance(cr, uid, active_instance_ids, context)
                    if not active_instance_ids:
                        if not rm_instance_ids:
                            self.pool.get('hr.employee').write_with_log(cr, uid, employee_id, {'end_date': date_end}, context={})
                        
                        context['instance_ids'] = ids
                        self.update_to_model_in_module_timesheet(cr, SUPERUSER_ID, employee_id, old_date_end, date_end, context)
                    
                    active_instance_same_comp_ids = self.search(cr, uid, [('employee_id','=',employee_id),
                                                                          ('company_id','=',company_id),
                                                                          ('date_end','=',False)])
                    active_instance_same_comp_ids = list(set(active_instance_same_comp_ids).difference(ids))
                    
                    #Remove instance create when transfer RR and contract is not sign
                    active_instance_same_comp_ids, rm_instance_ids = self.filter_ghost_instance(cr, uid, active_instance_same_comp_ids, context)
                    if not active_instance_same_comp_ids:
                        self.update_to_model_in_module_payroll(cr, SUPERUSER_ID, employee_id, company_id, old_date_end, date_end, context)
                    
        return res
    
    def filter_ghost_instance(self, cr, uid, instance_ids, context=None):
        """
            Remove instance have start_wr_id.contract_id.state != signed. In case instance create from transfer RR
        """
        rm_instance_ids = []
        if instance_ids:
            for instance in self.browse(cr, uid, instance_ids):
                contract_state = instance.start_wr_id and instance.start_wr_id.contract_id and instance.start_wr_id.contract_id.state or False
                if contract_state != 'signed':
                    instance_ids.remove(instance.id)
                    rm_instance_ids.append(instance.id)
        
        return instance_ids, rm_instance_ids
    
    #This function will be rewrite in timesheet
    def update_to_model_in_module_timesheet(self, cr, uid, employee_id, date_end, context=None):
        return True
    
    #This function will be rewrite in payroll
    def update_to_model_in_module_payroll(self, cr, uid, employee_id, company_id, date_end, context=None):
        return True
    

vhr_employee_instance()