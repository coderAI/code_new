# -*-coding:utf-8-*-
import thread
import logging
import sys
import time

from openerp.osv import osv, fields
from openerp.sql_db import Cursor
from openerp.sql_db import ConnectionPool
from openerp import tools
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import datetime, timedelta, date

log = logging.getLogger(__name__)

MONTH = [(1, 'January'),
         (2, 'February'),
         (3, 'March'),
         (4, 'April'),
         (5, 'May'),
         (6, 'June'),
         (7, 'July'),
         (8, 'August'),
         (9, 'September'),
         (10, 'October'),
         (11, 'November'),
         (12, 'December')]

class vhr_ts_lock_timesheet_detail_wizard(osv.osv):
    _name = 'vhr.ts.lock.timesheet.detail.wizard'
    _description = 'Lock Timesheet Detail'

    _columns = {
#                 'calculation_date': fields.date('Calculation Date'),
                'department_ids': fields.many2many('hr.department', 'lock_ts_detail_department_rel', 'lock_id', 'department_id', 'Department'),
                'employee_ids': fields.many2many('hr.employee', 'lock_ts_detail_employee_rel', 'lock_id', 'employee_id', 'Employee'),
                'month': fields.selection(MONTH, 'Month'),
                'year': fields.integer('Year'),

    }
    
    _defaults = {
        'month': datetime.now().month,
        'year': datetime.now().year,
    }
    
    def action_generate(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        
        mass_status_id = False
        try:
            log.info('Start running execute Lock Timesheet Detail wizard')
            mass_status_id = self.create_mass_status(cr, uid, context)
            thread.start_new_thread(vhr_ts_lock_timesheet_detail_wizard.thread_execute, (self, cr, uid, ids, mass_status_id, context))
        except Exception as e:
            log.exception(e)
            log.info('Error: Unable to start thread execute Lock Timesheet Detail wizard')
        
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        result_context = {}
        if context is None:
            context = {}
        result = mod_obj.get_object_reference(cr, uid, 'vhr_timesheet', 'act_tracking_vhr_ts_lock_timesheet_detail_wizard')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        
        result['res_id'] = mass_status_id
        result['view_type'] = 'form'
        result['view_mode'] = 'form,tree'
        result['views'].sort()
        return result
        
    def create_mass_status(self, cr, uid, context=None):
        _pool = ConnectionPool(int(tools.config['db_maxconn']))
        tcr = Cursor(_pool, cr.dbname, True)
        vals = {'state': 'new'}

        employee_ids = self.pool.get('hr.employee').search(tcr, uid, [('user_id', '=', uid)], context={'active_test':False})
        if employee_ids:
            vals['requester_id'] = employee_ids[0]

        module_ids = self.pool.get('ir.module.module').search(tcr, uid, [('name', '=', 'vhr_timesheet')])
        if module_ids:
            vals['module_id'] = module_ids[0]

        model_ids = self.pool.get('ir.model').search(tcr, uid, [('model', '=', 'vhr.ts.lock.timesheet.detail')])
        if model_ids:
            vals['model_id'] = model_ids[0]

        mass_status_id = self.pool.get('vhr.mass.status').create(tcr, uid, vals)
        tcr.commit()
        tcr.close()
        return mass_status_id
        
    def thread_execute(self, cr, uid, ids, mass_status_id, context=None):
        if not context:
            context = {}
        log.info('Start execute  vhr.ts.lock.timesheet.detail wizard')
        
        ts_period_pool = self.pool.get('vhr.ts.timesheet.period')
        lock_pool = self.pool.get('vhr.ts.lock.timesheet.detail')
        mass_status_pool = self.pool.get('vhr.mass.status')
        mass_status_detail_pool = self.pool.get('vhr.mass.status.detail')
        holiday_pool = self.pool.get('hr.holidays')
        emp_pool = self.pool.get('hr.employee')
        
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
            if ids:
                if not isinstance(ids, list):
                    ids = [ids]

                record_id = ids[0]
                data = self.read(cr, uid, record_id, ['department_ids','employee_ids','month','year'])
                department_ids = data.get('department_ids',[])
                employee_ids = data.get('employee_ids',[])
                lock_month = data.get('month', False)
                lock_year = data.get('year', False)
#                 calculation_date = data.get('calculation_date',False)
                
                request_date = date.today().strftime(DEFAULT_SERVER_DATE_FORMAT)
                if not employee_ids:
                    emp_domain = [('active','=',True)]
                    if department_ids:
                        emp_domain.append(('department_id','in',department_ids))
                
                    employee_ids = emp_pool.search(cr, uid, emp_domain)
                
                # if mass_status_id and company_id and holiday_status_id:
                if mass_status_id and employee_ids:
                    
                    list_error = []
                    num_count = 0
                    
                    parameter_obj = self.pool.get('ir.config_parameter')
                    lock_leave_type_code = parameter_obj.get_param(cr, uid, 'vhr_timesheet_leave_type_check_to_lock_ts_detail_gen') or ''
                    lock_leave_type_code = lock_leave_type_code.split(',')
                    leave_type_ids = self.pool.get('hr.holidays.status').search(cr, uid, [('code','in',lock_leave_type_code)])
                    
                    #Get timesheet period to check
                    ts_period_ids = ts_period_pool.search(cr, uid, [('month','=',lock_month),
                                                                    ('year','=',lock_year)])
                    
                    if ts_period_ids:
                        ts_period = ts_period_pool.read(cr, uid, ts_period_ids[0], ['from_date','to_date'])
                        from_date = ts_period.get('from_date', False)
                        to_date = ts_period.get('to_date', False)
                        
                        #Find all finish leave request with special holiday status end in month of timesheet period
                        all_leave_ids = holiday_pool.search(cr, uid,[('type','=','remove'),
                                                                 ('holiday_status_id','in',leave_type_ids),
                                                                 ('date_to','>=',from_date),
                                                                 ('date_to','<=',to_date),
                                                                 ('employee_id','in',employee_ids),
                                                                 ('state','=','validate')], context={"get_all": True})
                        if all_leave_ids:
                            leaves = holiday_pool.read(cr, uid, all_leave_ids, ['employee_id'])
                            employee_ids = [leave.get('employee_id', False) and leave['employee_id'][0] for leave in leaves]
                            employee_ids = list(set(employee_ids))
                        else:
                            employee_ids = []
                        
                        mass_status_pool.write(t_cr, uid, [mass_status_id], {'state': 'running',
                                                                         'number_of_record': len(employee_ids),
                                                                         'number_of_execute_record': 0,
                                                                         'number_of_fail_record': 0})
                        t_cr.commit()
                    
                        for employee_id in employee_ids:
                            employee = self.pool.get('hr.employee').read(cr, uid, employee_id, ['department_id'])
                            department_id = employee.get('department_id',False) and employee['department_id'][0]
                            
                            num_count += 1
                            mass_status_pool.write(t_cr, uid, [mass_status_id], {'number_of_execute_record': num_count})
                            error_item = ''
                            try:
                                vals = {
                                        'employee_id': employee_id,
                                        'lock_date': request_date,
                                        'department_id': department_id,
                                        'month': lock_month,
                                        'year': lock_year,
                                        'state': 'lock',
                                        }
                                
                                #Find all leave request with special leave type in month
                                leave_ids = holiday_pool.search(cr, uid,[('id','in',all_leave_ids),
                                                                         ('employee_id','=',employee_id)], context={"get_all": True})
                                if leave_ids:
                                    vals['holiday_ids'] = [(6, 0, leave_ids)]
                                
                                #Dont create record lock ts detail if find another record in same month - year
                                lock_ids = lock_pool.search(cr, uid, [('employee_id','=',employee_id),
                                                                      ('month','=',lock_month),
                                                                      ('year','=',lock_year)])
                                if not lock_ids:
                                    res = lock_pool.create(cr, uid, vals, context)
                                    if res:
                                        create_ids.append(res)
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
                                # if dont have error, then commit
                                t_cr.commit()
                                cr.commit()
    
                        if list_error:
                            mass_status_pool.write(t_cr, uid, [mass_status_id],
                                                   {'state': 'error', 'number_of_fail_record': len(list_error)})
    
                        else:
                            mass_status_pool.write(t_cr, uid, [mass_status_id], {'state': 'finish'})

        except Exception as e:
            log.exception(e)
            try:
                error_message = e.message
                if not error_message:
                    error_message = e.value
            except:
                error_message = ""

            # If have error with first try, then rollback to clear all created holiday
            cr.rollback()
            if create_ids:
                ot_payment_pool.write(cr, uid, create_ids, {'state': 'draft'}, context)
                ot_payment_pool.unlink(cr, uid, create_ids, context)
            log.info('Error occur while compensation ot payment!')

        if error_message:
            # Use cr in here because InternalError if use t_cr
            mass_status_pool.write(cr, uid, [mass_status_id], {'state': 'fail', 'error_message': error_message})

        # Delete all record to fresh database, dont use osv_memory because it's take so many times to reupgrade
        record_ids = self.search(cr, uid, [])
        self.unlink(cr, uid, record_ids, context)
        cr.commit()
        cr.close()

        t_cr.commit()
        t_cr.close()
        log.info('End execute compensation ot payment')
        return True
                    

vhr_ts_lock_timesheet_detail_wizard()