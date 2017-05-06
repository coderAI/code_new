# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import datetime
from openerp import SUPERUSER_ID

log = logging.getLogger(__name__)


class vhr_employee_instance(osv.osv):
    _name = 'vhr.employee.instance'
    _inherit = 'vhr.employee.instance'
    
    
    def update_to_model_in_module_timesheet(self, cr, uid, employee_id, old_date_end, date_end, context=None):
        emp_timesheet_pool = self.pool.get('vhr.ts.emp.timesheet')
        ws_emp_pool = self.pool.get('vhr.ts.ws.employee')
        
        self.update_to_selected_model_in_timesheet(cr, uid, employee_id, old_date_end, date_end, emp_timesheet_pool, context)
        self.update_to_selected_model_in_timesheet(cr, uid, employee_id, old_date_end, date_end, ws_emp_pool, context)
        
        self.remove_expired_leave_request(cr, uid, employee_id, date_end, context)
        return True
    
    def remove_expired_leave_request(self, cr, uid, employee_id, date_end, context=None):
        """
        ** Dont remove expire leave if updated instance with end_wr_id from termination had is_change_contract_type=True
        Cancel leave request have date >= date_end
        Delete holiday line have date > date_end and have holiday_id not in list leave request have date >= date_end (case leave request have date_from < date_end and date_to > date_end)
        """
        if not context:
            context = {}
        
        if context.get('instance_ids', False):
            instance_ids = context.get('instance_ids', [])
            if not isinstance(instance_ids, list):
                instance_ids = [instance_ids]
            
            instances = self.browse(cr, uid, instance_ids, fields_process=['end_wr_id'])
            end_wr_id = instances[0].end_wr_id
            if end_wr_id:
                termination = end_wr_id.termination_id
                if termination:
                    is_change_contract_type = termination.is_change_contract_type
                    if is_change_contract_type:
                        return True
            
        if employee_id and date_end:
            holidays_obj = self.pool.get('hr.holidays')
            line_obj = self.pool.get('vhr.holiday.line')
            
            holiday_ids = holidays_obj.search(cr, uid, [('employee_id','=',employee_id),
                                                        ('state','not in',['refuse','cancel']),
                                                          ('date_from','>',date_end)])
            if holiday_ids:
                holidays_obj.execute_workflow(cr, uid, holiday_ids, context={'action': 'reject','ACTION_COMMENT': "Reject by termination",'force_to_do_action': True})
            
            all_holiday_ids = holidays_obj.search(cr, uid, [('employee_id','=',employee_id),
                                                          ('date_from','>',date_end)])
            
            line_ids = line_obj.search(cr, uid, [('employee_id','=',employee_id),
                                                 ('holiday_id','not in',all_holiday_ids),
                                                 ('date','>',date_end)])
            if line_ids:
                lines = line_obj.read(cr, uid, line_ids, ['holiday_id'])
                rm_holiday_ids = [line.get('holiday_id',False) and line['holiday_id'][0] for line in lines]
                rm_holiday_ids = list(set(rm_holiday_ids))
                
                cancel_leave_ids = holidays_obj.search(cr, uid, [('id','in',rm_holiday_ids),
                                                                 ('state','in',['refuse','cancel'])])
                if cancel_leave_ids:
                    rm_holiday_ids = set(rm_holiday_ids).difference(cancel_leave_ids)
                    rm_holiday_ids = list(rm_holiday_ids)
                    
                    cancel_line_ids = line_obj.search(cr, uid, [('id','in',line_ids),
                                                                ('holiday_id','in',cancel_leave_ids)])
                    if cancel_line_ids:
                        line_ids = set(line_ids).difference(cancel_line_ids)
                        line_ids = list(line_ids)
                
                line_obj.unlink(cr, uid, line_ids, context)
                if rm_holiday_ids:
                    self.recompute_number_of_days_temp_of_leave_request(cr, uid, rm_holiday_ids, context)
            
        return True
    
    def recompute_number_of_days_temp_of_leave_request(self, cr, uid, rm_holiday_ids, context=None):
        if rm_holiday_ids:
            holiday_obj = self.pool.get('hr.holidays')
            for holiday in holiday_obj.read(cr, uid, rm_holiday_ids, ['holiday_line_ids']):
                holiday_line_ids = holiday.get('holiday_line_ids', [])
                holiday_obj.write(cr, uid, holiday['id'], {'number_of_days_temp': len(holiday_line_ids)})
        
        return True
        
    def update_to_selected_model_in_timesheet(self, cr, uid, employee_id, old_date_end, date_end, model, context=None):
        '''
        Only Update for vhr.ts.emp.timesheet -- vhr.ts.ws.employee
        Remove record have effect_from > date_end, update nearest record set effect_to = date_end
        
        if date_end = False: its mean, revert a termination, so delete working record, and set effect_to = False for latest employee timesheet/ ws employee
        '''
        if employee_id and model:
            
            if date_end:
                date_end_p = datetime.strptime(date_end, DEFAULT_SERVER_DATE_FORMAT)
                contract_pool = self.pool.get('hr.contract')
                
                rm_ids = model.search(cr, uid, [('employee_id','=',employee_id),
                                                ('effect_from','>',date_end)])
                if rm_ids:
                    #Case when update back to old employee instance, check if have employee instance with greater effect_from ==> ignore
                    greater_instance_ids = self.search(cr, uid, [('employee_id','=',employee_id),
                                                                 ('date_start','>',date_end)])
                    
                    if not greater_instance_ids:
                        #Check if have contract create in future have date_start = rm_ids.effect_from, dont delete anything
                        for record in model.read(cr, uid, rm_ids, ['effect_from']):
                            record_effect_from = record.get('effect_from', False)
                            contract_ids = contract_pool.search(cr, uid, [('employee_id','=',employee_id),
                                                                          ('date_start','=',record_effect_from),
                                                                          ('state','not in',['cancel'])])
                            
                            if contract_ids:
                                return True
                        
                        if rm_ids:
                            model.unlink_record(cr, uid, rm_ids)
                
                active_ids = model.search(cr, uid, [('employee_id','=',employee_id),
                                                    ('effect_from','<=',date_end)], limit=1,order='effect_from desc')
                
                #Update effect_to for employee timesheet nearest date_end if:
                #     - effect_to of nearest emp timesheet is null 
                #     -or greater date_end
                #     - equal old date_end of employee instance 
                if active_ids:
                    record = model.read(cr, uid, active_ids[0], ['effect_to'])
                    record_effect_to = record.get('effect_to', False)
                    record_effect_to = record_effect_to and datetime.strptime(record_effect_to, DEFAULT_SERVER_DATE_FORMAT)
                    
                    if not record_effect_to or record_effect_to > date_end_p or record_effect_to == old_date_end:
                        model.write(cr, SUPERUSER_ID, active_ids, {'effect_to':date_end})
                
            else:
                instance_no_effect_to_ids = self.search(cr, uid, [('employee_id','=',employee_id),
                                                                  ('date_end','=',False)])
                
                #remove instance create when contract is not sign
                instance_no_effect_to_ids, rm_instance_ids = self.filter_ghost_instance(cr, uid, instance_no_effect_to_ids, context)
                #If only one instance have date_end=False
                if len(instance_no_effect_to_ids) == 1:
                    #If dont have any instance created with contract.state!=signed and created record of model, update the latest.effect_to=False
                    is_have_record_in_duration_of_rm_instace = False
                    if rm_instance_ids:
                        for instance in self.read(cr, uid, rm_instance_ids, ['date_start','date_end']):
                            date_start = instance.get('date_start', False)
                            date_end = instance.get('date_end', False)
                            domain = [('employee_id','=',employee_id),('effect_from','>=',date_start)]
                            if date_end:
                                domain.append(('effect_from','<=',date_end))
                            record_ids = model.search(cr, uid, domain)
                            if record_ids:
                                is_have_record_in_duration_of_rm_instace = True
                                break
                            
                    update_ids = model.search(cr, uid, [('employee_id','=',employee_id)], limit=1, order='effect_from desc')
                    if not is_have_record_in_duration_of_rm_instace and update_ids:
                        model.write(cr, uid, update_ids[0], {'effect_to': False})
        
        return True


vhr_employee_instance()