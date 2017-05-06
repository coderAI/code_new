# -*- coding: utf-8 -*-

import logging

from openerp.osv import osv, fields

log = logging.getLogger(__name__)


class vhr_ts_working_schedule(osv.osv):
    _name = 'vhr.ts.working.schedule'
    _description = 'VHR TS Working Schedule'
    
    def _get_employees(self, cr, uid, ids, name, args, context=None):
        result = {}
        emp_sheet_pool = self.pool.get('vhr.ts.ws.employee')
        for ws_id in ids:
            lines = []
            emp_timesheet_ids = emp_sheet_pool.search(cr, uid, [('active','=',True),('ws_id','=',ws_id)])
            if emp_timesheet_ids:
                emp_timesheets = emp_sheet_pool.read(cr, uid, emp_timesheet_ids, ['employee_id'])
                for emp in emp_timesheets:
                    employee_id = emp.get('employee_id', False) and emp['employee_id'][0] or False
                    if employee_id:
                        lines.append(employee_id)
            result[ws_id] = lines
        return result
    
    _columns = {
        'code': fields.char('Code', size=64),
        'name': fields.char('Vietnamese Name', size=128),
        'name_en': fields.char('English Name', size=128),
        'description': fields.text('Description'),
        
        'group_schedule_id': fields.many2one('vhr.ts.working.schedule.group','Working Schedule Group'),
        
#         'employees': fields.many2many('hr.employee', 'vhr_ts_ws_employee', 'ws_id',
#                                       'employee_id', 'Employees'),
        'employees': fields.function(_get_employees, relation='hr.employee', type="many2many", string='Employees'),    
#         'ts_working_group_id': fields.many2one('vhr.ts.working.group','Working Group'),
        
        'active': fields.boolean('Active'),

        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                         domain=[('object_id.model', '=', _name), \
                                                 ('field_id.name', 'not in', ['write_date', 'audit_log_ids'])]),

    }

    _defaults = {
        'active': True,
    }

    _unique_insensitive_constraints = [{'code': "Working Schedule's Code is already exist!"},
                                       {'name': "Working Schedule's Vietnamese Name is already exist!"}]
    
    
    
    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        args_new = ['|', '|', ('name', operator, name), ('code', operator, name), ('name_en', operator, name)] + args
        ids = self.search(cr, uid, args_new, context=context)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(vhr_ts_working_schedule, self).name_search(cr, uid, name, args, operator, context, limit)
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if not context:
            context = {}
        if context.get('filter_by_ws_permission',False):
            #Filter In Working SChedule Detail
            ws_permission_obj = self.pool.get('vhr.ts.working.schedule.permission')
            new_args = [('id','in',[])]
            
            groups = self.pool.get('res.users').get_groups(cr, uid)
            if not set(['hrs_group_system','vhr_cb_admin','vhr_cb_timesheet']).intersection(set(groups)):
                employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=',uid)], context={'search_all_employee':True,'active_test':False})

                ws_permission_ids = ws_permission_obj.search(cr, uid, [('employee_ids','=',employee_ids),
                                                                       ('active','=',True)])
                if ws_permission_ids:
                    ws_permissions = ws_permission_obj.read(cr, uid, ws_permission_ids, ['ws_ids'])
                    ws_ids = []
                    for ws_permission in ws_permissions:
                        ws_ids.extend(ws_permission.get('ws_ids',[]))
                    
                    new_args = [('id','in',ws_ids)]
            else:
                new_args = []
            args.extend(new_args)
            
        res = super(vhr_ts_working_schedule, self).search(cr, uid, args, offset, limit, order, context, count)
        return res

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_ts_working_schedule, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res
    
    def write(self, cr, uid, ids, vals, context=None):
        if not isinstance(ids, list):
            ids = [ids]
        res = super(vhr_ts_working_schedule, self).write(cr, uid, ids, vals, context)
        
#         if res and 'active' in vals:
#             working_schedule_group_obj = self.pool.get('vhr.ts.working.schedule.working.group')
#             wsg_ids = working_schedule_group_obj.search(cr, uid, [('ts_working_schedule_id','in',ids),('active','!=',vals['active'])])
#             if wsg_ids:
#                 wsgs = working_schedule_group_obj.browse(cr, uid, wsg_ids)
#                 inactive_wsg = []
#                 active_wsg = []
#                 for wsg in wsgs:
#                     active_ws = wsg.ts_working_schedule_id and wsg.ts_working_schedule_id.active or False
#                     active_wg = wsg.ts_working_group_id and wsg.ts_working_group_id.active or False
#                     active = wsg.active
#                     
#                     if active_ws and active_wg and not active:
#                         active_wsg.append(wsg.id)
#                     elif not (active_ws and active_wg) and active:
#                         inactive_wsg.append(wsg.id)
#                         
#                 if inactive_wsg:
#                     working_schedule_group_obj.write(cr, uid, inactive_wsg, {'active': False})
#                 if active_wsg:
#                     working_schedule_group_obj.write(cr, uid, active_wsg, {'active': True})
                
        return res


vhr_ts_working_schedule()