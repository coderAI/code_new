# -*- coding: utf-8 -*-
import time
import logging

from openerp.osv import osv, fields
from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT

log = logging.getLogger(__name__)

class hr_contract(osv.osv):
    _inherit = 'hr.contract'
    
    _columns = {
                'ts_working_group_id': fields.many2one('vhr.ts.working.group', 'Working Group', ondelete='restrict'),
                'timesheet_id': fields.many2one('vhr.ts.timesheet', 'Timesheet', ondelete='restrict'),
                }
    
    def onchange_change_form_id(self, cr, uid, ids, change_form_id, context=None):
        res = {}
        if not change_form_id:
            res.update({'salary_setting_id': False,'timesheet_id': False,
                        'ts_working_group_id': False})
            
        return {'value': res}
    
    def delete_object_when_cancel_signed_contract(self, cr, uid, employee_id, date_start, date_end, context=None):
        '''
        This function is called from button_set_to_cancel_signed
        To delete employee timesheet, working schedule employee in module timesheet and payroll salary in module payroll
        '''
        super(hr_contract, self).delete_object_when_cancel_signed_contract(cr, uid, employee_id, date_start, date_end, context)
        if employee_id and date_start:
            domain = [('employee_id','=',employee_id),('effect_from','>=',date_start)]
            if date_end:
                domain.append(('effect_from','<=',date_end))
                
            emp_timesheet_pool = self.pool.get('vhr.ts.emp.timesheet')
            ws_employee_pool = self.pool.get('vhr.ts.ws.employee')
            
            emp_ts_ids = emp_timesheet_pool.search(cr, uid, domain)
            if emp_ts_ids:
                try:
                    emp_timesheet_pool.unlink(cr, uid, emp_ts_ids, context)
                except Exception as e:
                    log.exception(e)
                    try:
                        error_message = e.message
                        if not error_message:
                            error_message = e.value
                    except:
                        error_message = ""
                    raise osv.except_osv('Error !',
                        'Error when delete employee timesheet(s) effect in contract duration: \n %s'% error_message)
            
            ws_emp_ids = ws_employee_pool.search(cr, uid, domain)
            if ws_emp_ids:
                try:
                    ws_employee_pool.unlink(cr, uid, ws_emp_ids, context)
                except Exception as e:
                    log.exception(e)
                    try:
                        error_message = e.message
                        if not error_message:
                            error_message = e.value
                    except:
                        error_message = ""
                    raise osv.except_osv('Error !',
                        'Error when delete working schedule employee(s) effect in contract duration: \n %s'% error_message)
        
        return True


hr_contract()