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

class vhr_compensation_ot_payment_wizard(osv.osv):
    _name = 'vhr.compensation.ot.payment.wizard'
    _description = 'Compensation OT Payment'

    _columns = {
                'calculation_date': fields.date('Calculation Date'),
                'department_ids': fields.many2many('hr.department', 'compensation_ot_department_rel', 'compen_department_id', 'department_id', 'Department',
                                                    domain=[('organization_class_id.level','=', '3')]),
                'employee_ids': fields.many2many('hr.employee', 'compensation_ot_employee_rel', 'compen_emp_id', 'employee_id', 'Employee'),

    }
    
    _defaults={
        'calculation_date': fields.datetime.now}
    
    def action_generate(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        
        mass_status_id = False
        try:
            log.info('Start running execute  compensation ot payment wizard')
            mass_status_id = self.create_mass_status(cr, uid, context)
            thread.start_new_thread(vhr_compensation_ot_payment_wizard.thread_execute, (self, cr, uid, ids, mass_status_id, context))
        except Exception as e:
            log.exception(e)
            log.info('Error: Unable to start thread execute compensation ot payment wizard')
        
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        result_context = {}
        if context is None:
            context = {}
        result = mod_obj.get_object_reference(cr, uid, 'vhr_timesheet', 'act_tracking_vhr_compensation_ot_payment_wizard')
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

        model_ids = self.pool.get('ir.model').search(tcr, uid, [('model', '=', 'vhr.compensation.ot.payment')])
        if model_ids:
            vals['model_id'] = model_ids[0]

        mass_status_id = self.pool.get('vhr.mass.status').create(tcr, uid, vals)
        tcr.commit()
        tcr.close()
        return mass_status_id
        
    def thread_execute(self, cr, uid, ids, mass_status_id, context=None):
        if not context:
            context = {}
        log.info('Start execute  compensation ot payment wizard')

        ot_payment_pool = self.pool.get('vhr.compensation.ot.payment')
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
                data = self.read(cr, uid, record_id, ['department_ids','employee_ids','calculation_date'])
                department_ids = data.get('department_ids',[])
                employee_ids = data.get('employee_ids',[])
                calculation_date = data.get('calculation_date',False)
                
                if not employee_ids:
                    print 'department_ids=',department_ids
                    employee_ids = emp_pool.search(cr, uid, [], context={'department_ids_for_compen_ot_payment': department_ids})

                # if mass_status_id and company_id and holiday_status_id:
                if mass_status_id and employee_ids:
                    mass_status_pool.write(t_cr, uid, [mass_status_id], {'state': 'running',
                                                                         'number_of_record': len(employee_ids),
                                                                         'number_of_execute_record': 0,
                                                                         'number_of_fail_record': 0})
                    t_cr.commit()
                    list_error = []
                    num_count = 0
                    request_date = date.today().strftime(DEFAULT_SERVER_DATE_FORMAT)
                    current_year = date.today().year
                    
                    parameter_obj = self.pool.get('ir.config_parameter')
                    ot_leave_type_code = parameter_obj.get_param(cr, uid, 'ts.leave.type.overtime.code') or ''
                    ot_leave_type_code = ot_leave_type_code.split(',')
                    ot_leave_type_ids = self.pool.get('hr.holidays.status').search(cr, uid, [('code','in',ot_leave_type_code)])
                    
                    compen_hour = 0
                    compen_day = 0
                    general_param_pool = self.pool.get('vhr.ts.general.param')
                    general_param_ids = general_param_pool.search(cr, uid, [('active','=',True)])
                    if general_param_ids:
                        param = general_param_pool.read(cr, uid, general_param_ids[0], ['compensation_off_hour', 'compensation_off_day'])
                        compen_hour = param.get('compensation_off_hour', 0)
                        compen_day = param.get('compensation_off_day', 0)
                    
                    for employee_id in employee_ids:
                        employee = self.pool.get('hr.employee').read(cr, uid, employee_id, ['department_id'])
                        department_id = employee.get('department_id',False) and employee['department_id'][0]
                        
                        num_count += 1
                        mass_status_pool.write(t_cr, uid, [mass_status_id], {'number_of_execute_record': num_count})
                        error_item = ''
                        try:
                            vals = {
                                    'employee_id': employee_id,
                                    'request_date': request_date,
                                    'calculation_date': calculation_date,
                                    'department_id': department_id,
                                    'state': 'draft',
                                    'year': current_year,
                                    }
                            
                            compensation_ot_hour = 0
                            remain_ot_days = 0
                            annual_leave_ids = holiday_pool.search(cr, uid, [('type','=','add'),
                                                                             ('holiday_status_id','in',ot_leave_type_ids),
                                                                             ('year','=',current_year),
                                                                             ('employee_id','=',employee_id),
                                                                             ('state','=','validate')], context={"get_all": True})
                            if annual_leave_ids:
                                annual_leave = holiday_pool.read(cr, uid, annual_leave_ids[0], ['total_remain_days'])
                                remain_ot_days += annual_leave.get('total_remain_days',0)
                                
                                if compen_day and compen_hour and remain_ot_days:
                                    compensation_ot_hour = remain_ot_days / compen_day * compen_hour
                                    
                                    vals['compensation_ot_hour'] = compensation_ot_hour
                                    vals['initial_compensation_ot_hour'] = compensation_ot_hour
                                    vals['compensation_ot_day'] = remain_ot_days
                                    vals['coef_hour_day'] = compen_hour / compen_day

                            res = ot_payment_pool.create(cr, uid, vals, context)
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
                    

vhr_compensation_ot_payment_wizard()