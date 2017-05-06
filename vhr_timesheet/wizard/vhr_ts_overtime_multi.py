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
from datetime import datetime, timedelta

log = logging.getLogger(__name__)

class vhr_ts_overtime_multi(osv.osv):
    _name = 'vhr.ts.overtime.multi'
    _description = 'Mass Multi Overtime'

    _columns = {
                'company_id': fields.many2one('res.company', 'Company'),
                'overtime_detail_ids': fields.one2many('vhr.ts.overtime.detail', 'overtime_multi_id',
                                                    'Overtime Detail', ondelete = 'cascade'),
                'is_offline': fields.boolean('Is OffLine'),
                'employee_ids': fields.many2many('hr.employee', 'multi_vhr_overtime_employee_rel', 'overtime_multi_id', 'employee_id', 'Employees'),

    }
    
#     def _get_default_company_id(self, cr, uid, context=None):
#         company_ids = self.pool.get('res.company').search(cr, uid, [('is_member', '=', False)], order="id asc")
#         if company_ids:
#             return company_ids[0]
# 
#         return False
    

    _defaults = {
#         'company_id': _get_default_company_id,
        'is_offline': True
    }
    
#     def onchange_company(self, cr, uid, ids, company_id, context=None):
#         res = {'employee_ids': []}
#         domain = {}
#         if company_id:
#             emp_instance_pool = self.pool.get('vhr.employee.instance')
#             emp_instance_ids = emp_instance_pool.search(cr, uid, [('company_id','=',company_id),('date_end','=',False)])
#             if emp_instance_ids:
#                 emp_instances = emp_instance_pool.read(cr, uid, emp_instance_ids, ['employee_id'])
#                 employee_ids = []
#                 for emp_instance in emp_instances:
#                     employee_id = emp_instance.get('employee_id', False) and emp_instance['employee_id'][0] or False
#                     if employee_id:
#                 domain['employee_ids'] = [('id', 'in', employee_ids)]
#         
#         return {'value': res, 'domain': domain}
            
    
    def open_window(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        
        try:
            log.info('Start running execute  Multi Overtime')
            
            thread.start_new_thread(vhr_ts_overtime_multi.thread_execute, (self, cr, uid, ids, context) )
        except Exception as e:
            log.exception(e)
            log.info('Error: Unable to start thread execute Multi Overtime')
        
        view_tree_open = 'view_vhr_ts_overtime_tree'
        view_form_open = 'view_vhr_ts_overtime_form'
        view_search_open = 'view_vhr_ts_overtime_search'
        
        ir_model_pool = self.pool.get('ir.model.data')
        view_tree_result = ir_model_pool.get_object_reference(cr, uid, 'vhr_timesheet', view_tree_open)
        view_tree_id = view_tree_result and view_tree_result[1] or False
         
        view_form_result = ir_model_pool.get_object_reference(cr, uid, 'vhr_timesheet', view_form_open)
        view_form_id = view_form_result and view_form_result[1] or False
         
        view_search_result = ir_model_pool.get_object_reference(cr, uid, 'vhr_timesheet', view_search_open)
        view_search_id = view_search_result and view_search_result[1] or False

        return {
            'type': 'ir.actions.act_window',
            'name': "Overtime",
            'view_type': 'form',
            'view_mode': 'tree,form',
            'views': [(view_tree_id or False, 'tree'),
                      (view_form_id or False, 'form')],
            'search_view_id': view_search_id,
            'res_model': 'vhr.ts.overtime',
            'context': context,
            'target': 'current',
        }
        
    def create_mass_status(self, cr, uid, context=None):
        
        vals = { 'state' : 'new' }
        employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', uid)])
        if employee_ids:
            vals['requester_id'] = employee_ids[0]
        
        module_ids = self.pool.get('ir.module.module').search(cr, uid, [('name','=','vhr_timesheet')])
        if module_ids:
            vals['module_id'] = module_ids[0]
            
        model_ids = self.pool.get('ir.model').search(cr, uid, [('model','=','vhr.ts.overtime')])
        if model_ids:
            vals['model_id'] = model_ids[0]
        
        mass_status_id = self.pool.get('vhr.mass.status').create(cr, uid, vals)
        
        return mass_status_id
        
    def thread_execute(self, cr, uid, ids, context=None):
        log.info('Start execute multi leave request')
        
        overtime_pool = self.pool.get('vhr.ts.overtime')
        mass_status_pool = self.pool.get('vhr.mass.status')
        mass_status_detail_pool = self.pool.get('vhr.mass.status.detail')
        _pool = ConnectionPool(int(tools.config['db_maxconn']))
        #cr used to create WR
        cr = Cursor(_pool, cr.dbname, True)
        #t_cr used to create/write Mass Status/ Mass Status Detail
        t_cr = Cursor(_pool, cr.dbname, True) #Thread's cursor
        
        #clear old thread in cache to free memory
        reload(sys)
        create_ids = []
        error_message = ""
        try:
            if ids:
                if not isinstance(ids, list):
                    ids = [ids]
                    
                record_id = ids[0]
                data = self.browse(cr, uid, record_id, context)
#                 company_id = data.company_id and data.company_id.id or False
                mass_status_id = self.create_mass_status(t_cr, uid, context)
                t_cr.commit()
                if mass_status_id:
                    
                    mass_status_pool.write(t_cr, uid, [mass_status_id], {'state': 'running',
                                                                         'number_of_record': len(data.employee_ids), 
                                                                         'number_of_execute_record': 0,
                                                                         'number_of_fail_record': 0})
                    
                    list_error = []
                    num_count = 0
                    today = time.strftime(DEFAULT_SERVER_DATE_FORMAT)
                    
                    requester_id = False
                    mcontext={'search_all_employee': True}
                    employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', uid)], context=mcontext)
                    if employee_ids:
                        requester_id = employee_ids[0]
                
                    for employee in data.employee_ids:
                        num_count += 1
                        mass_status_pool.write(t_cr, uid, [mass_status_id], { 'number_of_execute_record': num_count})
                        error_item = ''
                        try:
                            employee_id = employee.id
                            vals = {}
                            reserve_vals = {'employee_id'           : employee_id,
#                                             'company_id'            : company_id,
                                            'request_date'          : today,
                                            'requester_id'          : requester_id,
                                            'state'                 : "draft",
                                        }
                            
                            #Get data from onchange employee: company_id, name, employee_code, remaining_leaves
                            vals_employee = overtime_pool.onchange_employee_id(cr, uid, [], employee_id, context)
                            vals.update(vals_employee['value'])
                            
                            
                            #Copy data holiday line in multi holiday
                            vals_holiday_line = self.copy_data_overtime_line_from_multi_overtime(cr, uid, record_id, employee_id, context)
                            if vals_holiday_line['warning']:
                                warning = vals_holiday_line['warning']['message']
                                raise osv.except_osv('Validation Error !', warning)
                            
                            value_holiday_line = vals_holiday_line['value']
                            vals.update( value_holiday_line )

                            vals.update(reserve_vals)
                            res = overtime_pool.create(cr, uid, vals, context)
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
                                
                            list_error.append( (employee_id, error_item) )
                        
                        if error_item:
                            mass_status_pool.write(t_cr, uid, [mass_status_id], {'number_of_fail_record': len(list_error)})
                            mass_status_detail_pool.create(t_cr, uid, {'mass_status_id': mass_status_id,
                                                                       'employee_id' : list_error[-1][0],
                                                                       'message':list_error[-1][1]})
                            t_cr.commit()
                            cr.rollback()
                        else:
                            #if dont have error, then commit 
                            t_cr.commit()
                            cr.commit()
                    
                    if list_error:
                        mass_status_pool.write(t_cr, uid, [mass_status_id], {'state': 'error','number_of_fail_record': len(list_error)})
                            
                    else:
                        mass_status_pool.write(t_cr, uid, [mass_status_id], {'state': 'finish'})
                        
                if create_ids and data.is_offline:
                    overtime_pool.write(cr, uid, create_ids, {'state': 'finish'})   
                    
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
            log.info('Error occur while Multi Overtime!')
            
        if error_message:
            #Use cr in here because InternalError if use t_cr
            mass_status_pool.write(cr, uid, [mass_status_id], {'state': 'fail','error_message': error_message})
        
        #Delete all mullti holiday to fresh database, dont use osv_memory because it's take so many times to reupgrade
        multi_overtime_ids = self.search(cr, uid, [])
        self.unlink(cr, uid, multi_overtime_ids, context)
        cr.commit()
        cr.close()
        
        t_cr.commit()
        t_cr.close()
        log.info('End execute multi overtime')
        return True
    
    def copy_data_overtime_line_from_multi_overtime(self, cr, uid, overtime_multi_id, employee_id, context=None):
        res = {}
        warning = {}
        res_overtime_line = []
        overtime_line_pool = self.pool.get('vhr.ts.overtime.detail')
        overtime_pool = self.pool.get('vhr.ts.overtime')
        today = time.strftime(DEFAULT_SERVER_DATE_FORMAT)
        if overtime_multi_id and employee_id:
            overtime_line_ids = overtime_line_pool.search(cr, uid, [('overtime_multi_id','=',overtime_multi_id)])
            if overtime_line_ids:
                fields = ['date_off','start_time','end_time','break_time','total_hours_register','notes','is_compensation_leave']
                overtime_lines = overtime_line_pool.read(cr, uid, overtime_line_ids, fields)
                
                for overtime_line in overtime_lines:
                    vals = {'employee_id': employee_id, 'request_date': today}
                    for field in fields:
                        vals[field] = overtime_line.get(field, False)
                    
                    #Check if date_off is not correct
                    onchange_date_vals = overtime_line_pool.onchange_date(cr, uid, [], employee_id, vals.get('date_off'))
                    if onchange_date_vals.get('warning',False):
                        warning = onchange_date_vals['warning']
                        return {'value': res, 'warning': warning}
                    
                    res_overtime_line.append([0, False, vals])
                    
                res['overtime_detail_ids'] = res_overtime_line
                    
        return {'value': res, 'warning': warning}
    
    def create(self, cr, uid, vals, context=None):
        if not context:
            context = {}
        
        context = {'create_from_multi': True}
        res = super(vhr_ts_overtime_multi, self).create(cr, uid, vals, context)
        
        
        return res
                    

vhr_ts_overtime_multi()