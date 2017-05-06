# -*- coding: utf-8 -*-
from datetime import datetime
import logging

from openerp.osv import osv, fields

from openerp.tools.translate import _


log = logging.getLogger(__name__)


class vhr_ts_employee_annual_leave_gen(osv.osv_memory):
    _name = 'vhr.ts.employee.annual.leave.gen'

    _columns = {
        'employee_ids': fields.many2many('hr.employee', 'ts_employee_annual_leave_gen', 'gen_id', 'employee_id',
                                         'Employee'),
        'is_gen_for_collaborator': fields.boolean('For collaborator'),
        'year': fields.integer('Year', required=1),
    }

    _defaults = {
        'year': datetime.now().year,
    }
    
    def onchange_is_gen_for_collaborator(self, cr, uid, ids, is_gen_for_collaborator, context=None):
        return {'value': {'employee_ids': [[6,False,[]]]}}
    
    def gen_employee_annual_leave(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        context['get_all'] = 1
        log.info('Start execute gen_employee_annual_leave')
        if ids:
            log.info('Start execute gen_employee_annual_leave')
            gen_obj = self.browse(cr, uid, ids[0])
            year = gen_obj.year
            is_gen_for_collaborator = gen_obj.is_gen_for_collaborator
            employee_ids = [res.id for res in gen_obj.employee_ids]
            if is_gen_for_collaborator:
                self.pool.get('hr.holidays').cron_generate_annual_leave_balance_for_colla(cr, uid, employee_ids, year,
                                                                                context=context)
            elif employee_ids:
                self.pool.get('hr.holidays').cron_generate_annual_leave_balance(cr, uid, employee_ids, year,
                                                                                context=context)
            
            # view
            ir_model_pool = self.pool.get('ir.model.data')
            view_tree_open = 'view_holiday_allocation_tree_readonly'
            view_form_open = 'edit_holiday_new'
            view_tree_result = ir_model_pool.get_object_reference(cr, uid, 'vhr_timesheet', view_tree_open)
            view_form_result = ir_model_pool.get_object_reference(cr, uid, 'vhr_timesheet', view_form_open)
            view_tree_id = view_tree_result and view_tree_result[1] or False
            view_form_id = view_form_result and view_form_result[1] or False

            domain = [('employee_id', 'in', employee_ids), ('type', '=', 'add'), ('year', '=', year)]
            return {
                'name': _('Annual Leave Balance'),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'hr.holidays',
                'domain': domain,
                'views': [(view_tree_id, 'tree'), (view_form_id, 'form')],
                'type': 'ir.actions.act_window',
                'target': 'current',
                'context': context,
            }


vhr_ts_employee_annual_leave_gen()