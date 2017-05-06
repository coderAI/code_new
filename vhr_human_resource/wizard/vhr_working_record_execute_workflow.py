# -*-coding:utf-8-*-
from openerp.osv import osv, fields

class vhr_working_record_execute_workflow(osv.osv_memory):
    _name = 'vhr.working.record.execute.workflow'
    _description = 'Execute Workflow Working Record'

    _columns = {
                'comment': fields.text('Comment'),

    }
    
    def execute_workflow(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        
        if context.get('active_ids', False):
            self.pool.get('vhr.working.record').execute_workflow(cr, uid, context['active_ids'], context)
        
        return {'type': 'ir.actions.act_window_close'}
            

vhr_working_record_execute_workflow()