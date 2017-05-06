# -*- coding: utf-8 -*-

from openerp.osv import osv, fields

def str2tuple(s):
    return eval('tuple(%s)' % (s or ''))


class ir_cron(osv.osv):
    _inherit = "ir.cron"
    
    _columns = {
                'description': fields.text('Description'),
                }
    
    def btn_run_schedule(self, cr, uid, ids, context=None):
        for scheduler in self.browse(cr, uid, ids, context):
            args = str2tuple(scheduler.args)
            model = self.pool.get(scheduler.model)
            if model and hasattr(model, scheduler.function):
                method = getattr(model, scheduler.function)
                method(cr, uid, *args)
        return True


ir_cron()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
