# -*-coding:utf-8-*-
import logging
from openerp.osv import osv, fields

log = logging.getLogger(__name__)

class vhr_ts_working_schedule_employee_wizard(osv.osv):
    _name = 'vhr.ts.working.schedule.employee.wizard'
    _description = 'Working Schedule Employee Wizard'
    
        
    _columns = {
        'name': fields.char('Name'),
        'ts_ws_employee_ids': fields.one2many('vhr.ts.ws.employee', 'ts_working_schedule_employee_wizard_id', 'Working Schedule Employee'),
    }
    
    
    
    def onchange_name(self, cr, uid, ids, context=None):
        res = {}
        res['ts_ws_employee_ids'] = self.get_ts_ws_employee_ids(cr, uid, context)
        
        return {'value': res}
    
    def get_ts_ws_employee_ids(self, cr, uid, context=None):
        """
        Only get employee belong to working group CT-BT,  CT-CL, CTV-BCC
        """
        ts_ws_employee_ids = []
        employee_ids = self.get_list_active_employee_doesn_have_working_schedule(cr, uid, context)
        if employee_ids:
            ts_emp_pool = self.pool.get('vhr.ts.emp.timesheet')
            wr_pool = self.pool.get('vhr.working.record')
            allow_working_group_code = (self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_timesheet_working_group_check_for_create_ts_ws_employee')or '').split(',')
            allow_working_group_ids = self.pool.get('vhr.ts.working.group').search(cr, uid, [('code','in',allow_working_group_code)])
            employees = self.pool.get('hr.employee').read(cr, uid, employee_ids, ['code','department_id','join_date','company_id'])
            number_index = 1
            for employee in employees:
                company_id = employee.get('company_id', False) and employee['company_id'][0] or False
                effect_date_ws = employee.get('join_date',False)
                
                wr_ids = wr_pool.search(cr, uid, [('employee_id','=',employee['id']),
                                                  ('company_id','=', company_id),
                                                  ('effect_from','>=',employee.get('join_date',False)),
                                                  ('ts_working_group_id_new','in',allow_working_group_ids),
                                                  ('ts_working_group_id_old','not in',allow_working_group_ids)],order='effect_from desc')
                if wr_ids:
                    wr = wr_pool.read(cr, uid, wr_ids[0], ['effect_from'])
                    effect_date_ws = wr.get('effect_from', False)
                
                val = {'employee_code': employee.get('code',''),
                       'department_id': employee.get('department_id', False),
                       'effect_from': effect_date_ws,
                       'employee_id': employee['id'],
                       'number_index': number_index,
                       }
                active_ts_emp_ids = ts_emp_pool.search(cr, uid, [('employee_id','=',employee['id']),('active','=',True)])
                if active_ts_emp_ids:
                    ts_emp = ts_emp_pool.read(cr, uid, active_ts_emp_ids[0], ['timesheet_id'])
                    timesheet_id = ts_emp.get('timesheet_id',False)
                    val['current_timesheet_id'] = timesheet_id
                    
                working_group_id, working_group_code, working_group_name_tuple = self.pool.get('hr.holidays').get_current_working_group_of_employee(cr, uid, employee['id'], context)
                if working_group_code not in allow_working_group_code:
                    continue
                val['ts_working_group_id'] = working_group_name_tuple
                number_index += 1
                ts_ws_employee_ids.append([0,False,val])
                
        return ts_ws_employee_ids
        
    def get_list_active_employee_doesn_have_working_schedule(self, cr, uid, context=None):
        """
        Get list employee dont have active working schedule employee, have employee instance with date_end = False
        """
        #Get list employee having working schedule
        cr.execute('SELECT employee_id FROM vhr_ts_ws_employee WHERE active = True')
        res = cr.fetchall()
        connect_employee_ids = [item[0] for item in res]
        #Filter list employee dont have working schedule
        unconnect_employee_ids = self.pool.get('hr.employee').search(cr, uid, [('active','=',True),
                                                                               ('id','not in',connect_employee_ids)], order="join_date desc")
        
        unconnect_employee_ids.append(0)
        #Get list employee have instance with date_end = False (still working)
        sql = "SELECT employee_id FROM vhr_employee_instance WHERE employee_id in %s AND date_end is null"
        cr.execute(sql% str(tuple(unconnect_employee_ids)).replace(',)', ')'))
        res = cr.fetchall()
        unconnect_employee_ids = list( set([item[0] for item in res]))
        
        unconnect_employee_ids.append(0)
        #Only choose employee had signed contract
        sql = "SELECT employee_id FROM hr_contract WHERE employee_id in %s AND state = 'signed' "
        cr.execute(sql% str(tuple(unconnect_employee_ids)).replace(',)', ')'))
        res = cr.fetchall()
        unconnect_employee_ids = list( set([item[0] for item in res]))
        
        temp_unconnect_employee_ids = unconnect_employee_ids[:]
        temp_unconnect_employee_ids.append(0)
        #Remove if have not signed contract
        sql = "SELECT employee_id FROM hr_contract WHERE employee_id in %s AND state in ('draft','waiting')"
        cr.execute(sql% str(tuple(temp_unconnect_employee_ids)).replace(',)', ')'))
        res = cr.fetchall()
       
        connected_employee_ids = list( set([item[0] for item in res]))
        
        unconnect_employee_ids = list(set(unconnect_employee_ids).difference(connected_employee_ids))
        
        
        if unconnect_employee_ids:
            allow_working_group_code = (self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_timesheet_working_group_check_for_create_ts_ws_employee')or '').split(',')
            working_group_ids = self.pool.get('vhr.ts.working.group').search(cr, uid, [('code','in',allow_working_group_code)])
            working_group_ids.append(0)
            #Get list employee currently have 1 working record effect at now() and working group not belong to allow working group
            sql = """
                    SELECT employee_id from vhr_working_record 
                    WHERE     effect_from <= date(now()) 
                         and  (  effect_to is null or effect_to >= date(now())  ) 
                         and  ts_working_group_id_new not in %s
                         and  employee_id in %s
                         and (state = 'finish' or state is null)
                    GROUP BY employee_id 
                    HAVING count(employee_id) =1
                  """
            cr.execute(sql% (str(tuple(working_group_ids)).replace(',)', ')'), str(tuple(unconnect_employee_ids)).replace(',)', ')')))
            res = cr.fetchall()
            remove_emp_ids = [item[0] for item in res]
            #Remove employee currently have working group not belong to allow working group list
            unconnect_employee_ids = list (  set(unconnect_employee_ids).difference(set(remove_emp_ids)) )
        
        return unconnect_employee_ids
            
    
    def view_input_form(self, cr, uid, ids, context=None):
        ir_model_pool = self.pool.get('ir.model.data')
        view_form_result = ir_model_pool.get_object_reference(cr, uid, 'vhr_timesheet', 'view_vhr_ts_working_schedule_employee_wizard_input')
        view_form_id = view_form_result and view_form_result[1] or False
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Working Schedule Employee Wizard',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'views': [(view_form_id or False, 'form')],
            'res_model': 'vhr.ts.working.schedule.employee.wizard',
            'context': {"default_name": 'Wizard','hide_form_view_button':True},
            'target': 'current',
        }
        
    def execute(self, cr, uid, ids, context=None):
        
        record_ids = self.search(cr, uid, [])
        self.unlink(cr, uid, record_ids)
        
        ir_model_pool = self.pool.get('ir.model.data')
        view_tree_result = ir_model_pool.get_object_reference(cr, uid, 'vhr_timesheet', 'view_vhr_ts_ws_employee_tree')
        view_tree_id = view_tree_result and view_tree_result[1] or False
         
        view_form_result = ir_model_pool.get_object_reference(cr, uid, 'vhr_timesheet', 'view_vhr_ts_ws_employee_form')
        view_form_id = view_form_result and view_form_result[1] or False
         
        view_search_result = ir_model_pool.get_object_reference(cr, uid, 'vhr_timesheet', 'view_vhr_ts_ws_employee_search')
        view_search_id = view_search_result and view_search_result[1] or False
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Working Schedule Employee',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'views': [(view_tree_id or False, 'tree'),
                      (view_form_id or False, 'form')],
            'search_view_id': view_search_id,
            'res_model': 'vhr.ts.ws.employee',
            'context': context,
            'limit': 20,
            'target': 'current',
        }
        
    def create(self, cr, uid, vals, context=None):
        
        if vals.get('ts_ws_employee_ids', False):
            #Dont save row dont input working group
            ts_ws_employee_ids = vals['ts_ws_employee_ids']
            truth_ts_ws_employee_ids = []
            for data in ts_ws_employee_ids:
                if len(data) == 3 and data[2].get('ws_id', False):
                    truth_ts_ws_employee_ids.append(data)
            vals['ts_ws_employee_ids'] = truth_ts_ws_employee_ids
            
        res = super(vhr_ts_working_schedule_employee_wizard, self).create(cr, uid, vals)
        
        return res

vhr_ts_working_schedule_employee_wizard()