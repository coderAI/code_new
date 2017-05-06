# -*-coding:utf-8-*-
from openerp.osv import osv, fields

class vhr_working_record_mass_movement(osv.osv_memory):
    _name = 'vhr.working.record.mass.movement'
    _description = 'Mass Movement Working Record'
    _inherit = 'vhr.working.record.mass.movement'

    _columns = {
        'timesheet_id_new': fields.many2one('vhr.ts.timesheet', 'Timesheet', ondelete='restrict'),
        'ts_working_group_id_new': fields.many2one('vhr.ts.working.group', 'Working Group', ondelete='restrict'),
#         'ts_working_schedule_id_new': fields.many2one('vhr.ts.working.schedule', 'Working Schedule', ondelete='cascade'),
    }
    
#     def onchange_working_schedule_id(self, cr, uid, ids, ts_working_schedule_id_new, context=None):
#         return self.pool.get('vhr.working.record').onchange_working_schedule_id(cr, uid, ids, ts_working_schedule_id_new, context)


vhr_working_record_mass_movement()