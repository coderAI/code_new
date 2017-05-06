# -*- coding: utf-8 -*-
import time
import logging

from openerp.osv import osv, fields

log = logging.getLogger(__name__)

class hr_department(osv.osv):
    _inherit = 'hr.department'
    
    _columns = {
                'timesheet_id': fields.many2one('vhr.ts.timesheet', 'Timesheet', ondelete='restrict'),
                }   


hr_department()