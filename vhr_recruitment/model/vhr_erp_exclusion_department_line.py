# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from dateutil import relativedelta

log = logging.getLogger(__name__)

class vhr_erp_exclusion_department_line(osv.osv):
    _name = 'vhr.erp.exclusion.department.line'
    _description = 'VHR ERP Exclusion Department'
    
    _columns = {
        'department_line_id': fields.many2one('vhr.erp.bonus.exclusion','Line Dept'),
        'department_id': fields.many2one('hr.department','Value Dept',domain="[('organization_class_id.level','in',[3,6])]"),
                
        'department_team_ids': fields.many2many('hr.department', 'erp_bonus_exclusion_department_team_rel',
                                           'exclusion_team_id', 'department_id', 'Value Team',
                                           domain="[('parent_id','in',[3,6])]"),
    }

    _defaults = {
    }

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_erp_exclusion_department_line, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res

vhr_erp_exclusion_department_line()
