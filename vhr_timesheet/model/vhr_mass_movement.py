# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields
from openerp import SUPERUSER_ID

class vhr_mass_movement(osv.osv):
    _name = 'vhr.mass.movement'
    _inherit = 'vhr.mass.movement'

    _columns = {
        'timesheet_id_new': fields.many2one('vhr.ts.timesheet', 'Timesheet', ondelete='restrict'),
        'ts_working_group_id_new': fields.many2one('vhr.ts.working.group', 'Working Group', ondelete='restrict'),
    }
    


vhr_mass_movement()