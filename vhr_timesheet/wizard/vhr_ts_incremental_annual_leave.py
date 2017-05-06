# -*- coding: utf-8 -*-
from datetime import datetime, date
import thread
import logging
import sys

from lxml import etree
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.osv import osv, fields
from openerp.sql_db import Cursor
from openerp.sql_db import ConnectionPool
from openerp import tools

log = logging.getLogger(__name__)


class vhr_ts_incremental_annual_leave(osv.osv_memory):
    _name = 'vhr.ts.incremental.annual.leave'

    _columns = {
        'employee_id': fields.many2one('hr.employee', 'Employee'),
        'admin_id': fields.many2one('hr.employee', 'Admin'),
        'job_level_type_id': fields.many2one('vhr.job.level.type', 'Job Level Type'),
        'job_level_person_id': fields.many2one('vhr.job.level.new', 'Job Level Person'),
        'timesheet_id': fields.many2one('vhr.ts.timesheet', 'Timesheet'),
        'holiday_status_id': fields.many2one('hr.holidays.status', 'Leave Type'),
        'year': fields.integer('Year'),
        'is_only_update_expiry_date': fields.boolean('Is Only Update Expiry Date'),
        'state': fields.selection([('all','All'),('moved','Moved'),('not_move','Not Move')], string="Status"),
    }
    
    def get_holiday_status_id(self, cr, uid, context=None):
        if not context:
            context = {}
        
        if context.get('holiday_status_config_name',False):
            config_parameter = self.pool.get('ir.config_parameter')
            holiday_status_code = config_parameter.get_param(cr, uid, context['holiday_status_config_name'])
            if holiday_status_code:
                holiday_status_code_list = holiday_status_code.split(',')
                holidays_status_ids = self.pool.get('hr.holidays.status').search(cr, uid, [('code','in',holiday_status_code_list)])
            
                if holidays_status_ids:
                    return holidays_status_ids[0]
        return False
        
    _defaults = {
        'year': datetime.now().year,
        'state': 'all',
        'holiday_status_id': get_holiday_status_id,
        'is_only_update_expiry_date': False 
    }
    
    def gen_annual_leave(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        log.info('Start execute gen_annual_leave')
        if ids:
            timesheet_detail_pool = self.pool.get('vhr.ts.timesheet.detail')
            employee_pool = self.pool.get('hr.employee')
            timesheet_pool = self.pool.get('vhr.ts.timesheet')
            emp_timesheet_pool = self.pool.get('vhr.ts.emp.timesheet')
            record = self.browse(cr, uid, ids[0])
            get_employee_ids = []
            get_timesheet_ids = []
            timesheet_ids = []
            year = record.year
            
            admin_id = record.admin_id and record.admin_id.id or False
            timesheet_id = record.timesheet_id and record.timesheet_id.id or False
            employee_id = record.employee_id and record.employee_id.id or False
            job_level_type_id = record.job_level_type_id and record.job_level_type_id.id or False
            job_level_person_id = record.job_level_person_id and record.job_level_person_id.id or False
            holiday_status_id = record.holiday_status_id and record.holiday_status_id.id or False
            state = record.state
            
            month = date.today().month
            #Get active timsheet of admin 
            if year and admin_id:
                employee = employee_pool.read(cr, uid, admin_id, ['name'])
                admin_name = employee.get('name','') and employee['name'][1]
                    
                timesheet_detail_ids = timesheet_detail_pool.search(cr, uid, [('admin_id','=',admin_id),
                                                                              ('year','=',year),
                                                                              ('month','=',month)])
                
                timesheet_details = timesheet_detail_pool.read(cr, uid, timesheet_detail_ids, ['timesheet_id'])
                
                timesheet_ids = [item.get('timesheet_id',False) and item['timesheet_id'][0] for item in timesheet_details]
            
            #Get timesheet_ids from admin, timesheet_id, year
            if timesheet_id and timesheet_ids and timesheet_id in timesheet_ids:
                get_timesheet_ids.append(timesheet_id)
            
            elif not timesheet_id and timesheet_ids:
                get_timesheet_ids.extend(timesheet_ids)
            
            elif timesheet_id and not timesheet_ids:
                get_timesheet_ids.append(timesheet_id)
            
            
            
            
            if get_timesheet_ids:
                #If have list get_timesheet_ids, get all active employee timesheet 
                domain_emp_timesheet = [('timesheet_id','in',get_timesheet_ids),('active','=',True)]
                
                emp_timesheet_ids = emp_timesheet_pool.search(cr, uid, domain_emp_timesheet)
                emp_timesheets = emp_timesheet_pool.read(cr, uid, emp_timesheet_ids, ['employee_id'])
                    
                employee_ids = [item.get('employee_id',False) and item['employee_id'][0] for item in emp_timesheets]
            else:
                #Get list active employee
                employee_ids = employee_pool.search(cr, uid, [('active','=',True)])
            
            if job_level_person_id:
                filter_emp_ids = employee_pool.search(cr, uid, [('active','=',True),
                                                                ('job_level_person_id','=',job_level_person_id)])
                employee_ids = list(set(employee_ids).intersection(filter_emp_ids))
                
            if not employee_id and employee_ids:
                get_employee_ids.extend(employee_ids)
                
            elif employee_id and employee_ids and employee_id in employee_ids:
                get_employee_ids.append(employee_id)
            
            elif employee_id and not employee_ids:
                get_employee_ids.append(employee_id)
            
            #Only run for employee have active working record
            if get_employee_ids:
                sql = """
                        SELECT employee_id from vhr_working_record where employee_id in {} and active=True
                      """
                cr.execute(sql.format(str(tuple(get_employee_ids)).replace(',)', ')')))
                res = cr.fetchall()
                get_employee_ids = [item[0] for item in res]
            
            #Filter list employee from job_level_type_id
            if job_level_type_id and get_employee_ids:
                working_record_pool =self.pool.get('vhr.working.record')
                working_ids = working_record_pool.search(cr, uid, [('employee_id','in',get_employee_ids),
                                                                   ('active','=',True)])
                if working_ids:
                    workings = working_record_pool.browse(cr, uid, working_ids, fields_process=['job_level_id_new'])
                    job_level_type_ids = [item.job_level_id_new and item.job_level_id_new.job_level_type_id and item.job_level_id_new.job_level_type_id.id for item in workings]
                     
                    if job_level_type_id not in job_level_type_ids:
                        get_employee_ids = []
            
            mass_status_id = self.create_mass_status(cr, uid, context)
            
            if get_employee_ids:
                try:
                    log.info('Start running execute  Incremental Annual Leave')
        
                    thread.start_new_thread(vhr_ts_incremental_annual_leave.thread_execute, (self, cr, uid, ids, get_employee_ids, mass_status_id, context) )
                except Exception as e:
                    log.exception(e)
                    log.info('Error: Unable to start thread execute  Incremental Annual Leave')
            elif mass_status_id:
                cr.commit()
                self.pool.get('vhr.mass.status').write(cr, uid, mass_status_id, {'state': 'finish',
                                                                                 'number_of_record': 0})
            
            mod_obj = self.pool.get('ir.model.data')
            act_obj = self.pool.get('ir.actions.act_window')
            result_context = {}
            if context is None:
                context = {}
            result = mod_obj.get_object_reference(cr, uid, 'vhr_timesheet', 'act_tracking_vhr_ts_incremental_annual_leave')
            id = result and result[1] or False
            result = act_obj.read(cr, uid, [id], context=context)[0]
            
            result['res_id'] = mass_status_id
            result['view_type'] = 'form'
            result['view_mode'] = 'form,tree'
            result['views'].sort()
            return result
    
    def create_mass_status(self, cr, uid, context=None):
        if not context:
            context = {}
            
        _pool = ConnectionPool(int(tools.config['db_maxconn']))
        tcr = Cursor(_pool, cr.dbname, True)
        
        vals = {'state': 'new'}
        if context.get('type',False):
            vals['type'] = context['type']

        employee_ids = self.pool.get('hr.employee').search(tcr, uid, [('user_id', '=', uid)], context={'search_all_employee': True,'active_test':False})
        if employee_ids:
            vals['requester_id'] = employee_ids[0]

        module_ids = self.pool.get('ir.module.module').search(tcr, uid, [('name', '=', 'vhr_timesheet')])
        if module_ids:
            vals['module_id'] = module_ids[0]

        model_ids = self.pool.get('ir.model').search(tcr, uid, [('model', '=', 'hr.holidays')])
        if model_ids:
            vals['model_id'] = model_ids[0]
        
        if context.get('mass_status_info', False):
            vals['mass_status_info'] = context['mass_status_info']
            
        mass_status_id = self.pool.get('vhr.mass.status').create(tcr, uid, vals)
        tcr.commit()
        tcr.close()
        return mass_status_id
    
    
    def thread_execute(self, cr, uid, ids, employee_ids, mass_status_id, context=None):
        if not context:
            context = {}
        log.info('Start execute incremental annual leave')

        holiday_pool = self.pool.get('hr.holidays')
        mass_status_pool = self.pool.get('vhr.mass.status')
        config_pool = self.pool.get('ir.config_parameter')
        mass_status_detail_pool = self.pool.get('vhr.mass.status.detail')
        employee_obj = self.pool.get('hr.employee')
        _pool = ConnectionPool(int(tools.config['db_maxconn']))
        # cr used to create WR
        cr = Cursor(_pool, cr.dbname, True)
        # t_cr used to create/write Mass Status/ Mass Status Detail
        t_cr = Cursor(_pool, cr.dbname, True)  # Thread's cursor

        # clear old thread in cache to free memory
        reload(sys)
        create_ids = []
        error_message = ""
        try:
            if ids and employee_ids:
                if not isinstance(ids, list):
                    ids = [ids]

                record_id = ids[0]
                data = self.browse(cr, uid, record_id, context)
                holiday_status_id = data.holiday_status_id and data.holiday_status_id.id or False
                holiday_status_code = data.holiday_status_id and data.holiday_status_id.code or ''
                year = data.year
                is_only_update_expiry_date = data.is_only_update_expiry_date
                
                leave_off_code = ''
                
                config_ids = config_pool.search(t_cr, uid, [('key','=','ts.leave.type.default.code')])
                if config_ids:
                    config = config_pool.read(t_cr, uid, config_ids[0], ['value'])
                    leave_off_code = config.get('value','')
                
                leave_off_ot_code = ''
                config_ids = config_pool.search(t_cr, uid, [('key','=','ts.leave.type.overtime.code')])
                if config_ids:
                    config = config_pool.read(t_cr, uid, config_ids[0], ['value'])
                    leave_off_ot_code = config.get('value','')
                
                param_type_code = 0
                if holiday_status_code == leave_off_code:
                    param_type_code = 6
                elif holiday_status_code == leave_off_ot_code:
                    param_type_code = 9
#                 company_id = data.company_id and data.company_id.id or False
#                 holiday_status_id = data.holiday_status_id and data.holiday_status_id.id or False
#                 mass_status_id = self.create_mass_status(t_cr, uid, context)
                t_cr.commit()
                if mass_status_id and year and holiday_status_id:
                    mass_status_pool.write(t_cr, uid, [mass_status_id], {'state': 'running',
                                                                         'number_of_record': len(employee_ids),
                                                                         'number_of_execute_record': 0,
                                                                         'number_of_fail_record': 0})
                    t_cr.commit()
                    list_error = []
                    num_count = 0
                    for employee_id in employee_ids:
                        
#                         try:
#                             #CTV thi khong can don phep nam
#                             is_colla, is_prob = holiday_pool.is_collaborator_or_probation(cr, uid, employee_id, False, context)
#                             if is_colla:
#                                 num_count += 1
#                                 
#                                 mass_status_detail_pool.create(t_cr, uid, {'mass_status_id': mass_status_id,
#                                                                                'employee_id': employee_id,
#                                                                                'message': "Don't create accumulate for colla emp",
#                                                                                'status': 'success'})
#                                 continue
#                         except Exception as e:
#                             log.error(e)
#                             continue
                        
                        num_count += 1
                        mass_status_pool.write(t_cr, uid, [mass_status_id], {'number_of_execute_record': num_count})
                        error_item = ''
                        try:
                            
                            
                            vals = {}
                            context['get_all'] = True
                            annual_leave_previous_ids = holiday_pool.search(cr, uid, [('employee_id','=',employee_id),
                                                                                 ('holiday_status_id','=',holiday_status_id),
                                                                                 ('type','=','add'),
                                                                                 ('year','=',year -1)], context=context)
                            #Check if dont have remain days in pre year, continue
                            if annual_leave_previous_ids:
                                annual_leaves = holiday_pool.read(cr, uid, annual_leave_previous_ids, ['total_remain_days'])
                                is_go_to_next_emp = True
                                for annual_leave in annual_leaves:
                                    if annual_leave.get('total_remain_days',0) >0:
                                        is_go_to_next_emp = False
                                        break
                                if is_go_to_next_emp:
                                    mass_status_detail_pool.create(t_cr, uid, {'mass_status_id': mass_status_id,
                                                                               'employee_id': employee_id,
                                                                               'message': "Employee doesn't have any remain days of pre year",
                                                                               'status': 'success'})
                                    t_cr.commit()
#                                     cr.commit()
                                    continue
                            else:
                                holiday_status = self.pool.get('hr.holidays.status').read(cr, uid, holiday_status_id,['name'])
                                holiday_status_name = holiday_status.get('name', '')
                                continue
                                raise osv.except_osv('Validation Error !',
                                                    'Employee dont have annual leave with leave type "%s" in year %s !' % (holiday_status_name, year-1)) 
                            
                            annual_leave_emp_ids = holiday_pool.search(cr, uid, [('employee_id','=',employee_id),
                                                                                 ('holiday_status_id','=',holiday_status_id),
                                                                                 ('type','=','add'),
                                                                                 ('year','=',year)], context=context) 
                            
                            create_id = False
                            #Only create new annual leave if dont have annual leave for that year
                            if not annual_leave_emp_ids:
                                vals = {'employee_id': employee_id,
                                        'holiday_status_id': holiday_status_id,
                                        'type': 'add',
                                        'state': 'validate',
                                        'is_offline': True,
                                        'year': year}
                                
                                employee_instance = employee_obj.browse(cr, uid, employee_id, fields_process=['name', 'code','department_id','report_to'])
                                vals['name'] = employee_instance.name or ''
                                vals['employee_code'] = employee_instance.code or ''
                                
                                vals['department_id'] = employee_instance.department_id and employee_instance.department_id.id or False
                                vals['dept_head_id'] = employee_instance.department_id and employee_instance.department_id.manager_id\
                                                        and employee_instance.department_id.manager_id.id or False
                                                        
                                vals['report_to_id'] = employee_instance.report_to and employee_instance.report_to.id or False
            
                                create_id = holiday_pool.create(cr, uid, vals)
                                if create_id:
                                    create_ids.append(create_id)
                                    
                            log.info('Update Actual days pre, expiry days!')
                            if create_id or annual_leave_emp_ids:
                                record_id = create_id or annual_leave_emp_ids[0]
                                record = holiday_pool.read(cr, uid, record_id, ['days_of_pre_year','move_days_of_pre_year'])
                                vals = {'temp_actual_days_of_pre_year': record.get('days_of_pre_year',0)}
                                
                                if vals['temp_actual_days_of_pre_year'] == 0:
                                    vals['move_days_of_pre_year'] = True
                                    vals['actual_days_of_pre_year'] = 0
                                    
                                if record['move_days_of_pre_year']:
                                    vals['actual_days_of_pre_year'] = record.get('days_of_pre_year',0)
                                
                                employee = employee_obj.browse(cr, uid, employee_id, fields_process=['job_level_person_id'])
                                job_level_person_id = employee.job_level_person_id and employee.job_level_person_id.id or False
                                if job_level_person_id:
                                    
                                    param_job_level_pool = self.pool.get('vhr.ts.param.job.level')
                                    param_type_pool = self.pool.get('vhr.ts.param.type')
                                    
                                    param_type_ids = param_type_pool.search(cr, uid, [('code','=',param_type_code)])
                                    if not param_type_ids:
                                        raise osv.except_osv('Validation Error !', 
                                                         "Don't have any parameter with code [%s] !"% param_type_code)
                                        
                                    param_job_ids = param_job_level_pool.search(cr, uid, [('param_type_id','in',param_type_ids),
                                                                                          ('job_level_new_id','=',job_level_person_id)])
                                    
                                    if not param_job_ids:
                                        param_type = param_type_pool.read(cr, uid, param_type_ids[0], ['name'])
                                        param_type_name = param_type.get('name','')
                                        job_level = self.pool.get('vhr.job.level.new').read(cr, uid, job_level_person_id, ['name'])
                                        job_level_name = job_level.get('name','')
                                        
                                        raise osv.except_osv('Validation Error !', 
                                                         "Don't have any parameter by Job Level New [%s] for [%s]!" % (job_level_name, param_type_name))
                                    
                                    param_job =  param_job_level_pool.read(cr, uid, param_job_ids[0], ['value'])
                                    param_job_value = param_job.get('value','31/12')
                                    if param_job_value == '0':
                                        param_job_value = '31/12'
                                
                                else:
                                    param_job_value = '31/12'
                                
                                expire_date = datetime.strptime(param_job_value+ "/"+ str(year), '%d/%m/%Y')
                                    
                                expire_date = expire_date.strftime(DEFAULT_SERVER_DATE_FORMAT)
                                
                                vals['expiry_date_of_days_pre_year'] = expire_date
                                if is_only_update_expiry_date:
                                    vals = {'expiry_date_of_days_pre_year': expire_date}
                                
                                holiday_pool.write(cr, uid, [record_id], vals)
                                
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

                            list_error.append((employee_id, error_item))

                        if error_item:
                            mass_status_pool.write(t_cr, uid, [mass_status_id],
                                                   {'number_of_fail_record': len(list_error)})
                            mass_status_detail_pool.create(t_cr, uid, {'mass_status_id': mass_status_id,
                                                                       'employee_id': list_error[-1][0],
                                                                       'message': list_error[-1][1]})
                            t_cr.commit()
                            cr.rollback()
                        else:
                            #if dont have error, then commit 
                            t_cr.commit()
                            cr.commit()

                    if list_error:
                        mass_status_pool.write(t_cr, uid, [mass_status_id],
                                               {'state': 'error', 'number_of_fail_record': len(list_error)})

                    else:
                        mass_status_pool.write(t_cr, uid, [mass_status_id], {'state': 'finish'})
                        
#                 if create_ids:
#                     holiday_pool.signal_confirm(cr, uid, create_ids)
#                     holiday_pool.signal_validate(cr, uid, create_ids)
        except Exception as e:
            log.exception(e)
            try:
                error_message = e.message
                if not error_message:
                    error_message = e.value
            except:
                error_message = ""

            #If have error with first try, then rollback to clear all created holiday 
            cr.rollback()
            if create_ids:
                holiday_pool.write(cr, uid, create_ids, {'state': 'draft'}, context)
                holiday_pool.unlink(cr, uid, create_ids, context)
            log.info('Error occur while Incremental Annual Leave!')

        if error_message:
            #Use cr in here because InternalError if use t_cr
            mass_status_pool.write(cr, uid, [mass_status_id], {'state': 'fail', 'error_message': error_message})

        #Delete all mullti holiday to fresh database, dont use osv_memory because it's take so many times to reupgrade
#         multi_holiday_ids = self.search(cr, uid, [])
#         self.unlink(cr, uid, multi_holiday_ids, context)
        cr.commit()
        cr.close()

        t_cr.commit()
        t_cr.close()
        log.info('End execute incremental annual leave')
        return True
            
    

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context:
            context = {}
        res = super(vhr_ts_incremental_annual_leave, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar=toolbar, submenu=submenu)
        
        if view_type == 'form':
            doc = etree.XML(res['arch'])
            if res['type'] == 'form':
                holidays_status_ids = []
                if context.get('holiday_status_config_name',False):
                    config_parameter = self.pool.get('ir.config_parameter')
                    holiday_status_code = config_parameter.get_param(cr, uid, context['holiday_status_config_name'])
                    if holiday_status_code:
                        holiday_status_code_list = holiday_status_code.split(',')
                        holidays_status_ids = self.pool.get('hr.holidays.status').search(cr, uid, [('code','in',holiday_status_code_list)])
                        
                for node in doc.xpath("//field[@name='holiday_status_id']"):
                    domain = [('id','in',holidays_status_ids)]
                    node.set('domain', str(domain))
            
            res['arch'] = etree.tostring(doc)
        return res
                    
vhr_ts_incremental_annual_leave()