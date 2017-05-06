# -*- coding: utf-8 -*-

import logging
from datetime import datetime

from openerp.osv import osv, fields
from openerp.tools.translate import _


log = logging.getLogger(__name__)


class vhr_ts_ws_detail(osv.osv):
    _name = 'vhr.ts.ws.detail'
    _description = 'VHR TS Working Schedule Detail'

    def _get_day_of_week(self, cr, uid, ids, field_name, arg, context=None):
        """Returns day of week of this holiday."""
        res = {}
        for i in ids:
            hday = self.browse(cr, uid, i, context=context)
            res[i] = datetime.strptime(hday.date, "%Y-%m-%d").strftime('%A')
        return res

    def _get_year(self, cr, uid, ids, field_name, arg, context=None):
        """Returns day of week of this holiday."""
        res = {}
        for i in ids:
            res[i] = {'year': '', 'month': ''}
            hday = self.browse(cr, uid, i, context=context)
            res[i]['year'] = datetime.strptime(hday.date, "%Y-%m-%d").year
            res[i]['month'] = datetime.strptime(hday.date, "%Y-%m-%d").month
        return res

    _columns = {
        'name': fields.char('Name', size=64),
        'ws_id': fields.many2one('vhr.ts.working.schedule', 'Working Schedule', ondelete='restrict'),
        'shift_id': fields.many2one('vhr.ts.working.shift', 'Shift', ondelete='restrict'),
        'date': fields.date('Date'),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                         domain=[('object_id.model', '=', _name),
                                                 ('field_id.name', 'not in', ['write_date', 'audit_log_ids'])]),
        'weekday': fields.function(_get_day_of_week,
                                   type='char',
                                   method=True,
                                   string='Day of the Week'),
        'year': fields.function(_get_year,
                                type='integer',
                                method=True,
                                string='Year of Holiday',
                                store=True,
                                multi='date'),
        'month': fields.function(_get_year,
                                 type='integer',
                                 method=True,
                                 string='Month of Holiday',
                                 store=True,
                                 multi='date'),
        'type_id': fields.many2one('vhr.public.holidays.type', 'Public Holiday Type', ondelete='restrict'),

    }

    _sql_constraints = [
        ('date_unique', 'unique(date, ws_id)',
         _("Working Schedule has been already set shift for this date!")),
    ]

    _order = "date desc"
    
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        # Search rule for specific menu
        if not context:
            context = {}
        
        if 'active_test' not in context:
            context['active_test'] = False
        
        if uid and context.get('filter_by_group_for_ws_detail',False):
            groups = self.pool.get('res.users').get_groups(cr, uid)
            if not set(['hrs_group_system','vhr_cb_admin','vhr_cb_timesheet']).intersection(set(groups)):
                log.info("Filter vhr.ts.ws.detail by ts.working.schedule.permission")
                all_ws_ids = []
                login_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=',uid)], context=context)
                if login_ids:
                    ws_permission = self.pool.get('vhr.ts.working.schedule.permission')
                    ws_per_ids = ws_permission.search(cr, uid, [('active','=',True),
                                                            ('employee_ids','=',login_ids[0])])
                    if ws_per_ids:
                        ws_pers = ws_permission.read(cr, uid, ws_per_ids, ['ws_ids'])
                        for ws_per in ws_pers:
                            ws_ids = ws_per.get('ws_ids',[])
                            all_ws_ids.extend(ws_ids)
                    
                args.append(('ws_id','in',all_ws_ids))
                    
            
        res =  super(vhr_ts_ws_detail, self).search(cr, uid, args, offset, limit, order, context, count)
        return res
    
    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        args_new = [('name', operator, name)] + args
        ids = self.search(cr, uid, args_new)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(vhr_ts_ws_detail, self).name_search(cr, uid, name, args, operator, context, limit)
    
    def create(self, cr, uid, vals, context=None):
        res =  super(vhr_ts_ws_detail, self).create(cr, uid, vals, context)
#         raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        try:
            return super(vhr_ts_ws_detail, self).unlink(cr, uid, ids, context=context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')


vhr_ts_ws_detail()