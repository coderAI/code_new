# -*- coding: utf-8 -*-


from openerp.osv import osv, fields


class vhr_holidays_execute_workflow(osv.osv_memory):
    _name = 'vhr.holidays.execute.workflow'
    _description = 'Execute Workflow Holidays'

    _columns = {
        'comment': fields.text('Comment'),

    }

    def execute_workflow(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        context['multi'] = 1

        if context.get('active_ids', False):
            self.pool.get('hr.holidays').execute_workflow(cr, uid, context['active_ids'], context)

        return {'type': 'ir.actions.act_window_close'}


vhr_holidays_execute_workflow()