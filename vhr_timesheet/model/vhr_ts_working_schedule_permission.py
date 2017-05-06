# -*- coding: utf-8 -*-

from openerp.osv import osv, fields


class vhr_ts_working_schedule_permission(osv.osv):
    _name = 'vhr.ts.working.schedule.permission'

    _columns = {
                'name': fields.char('Name', size=64),
                'employee_ids': fields.many2many('hr.employee', 'ts_working_schedule_permission_employee', 'ts_ws_permission_id',
                                       'employee_id', 'Employees'),
                'ws_ids': fields.many2many('vhr.ts.working.schedule', 'ts_working_schedule_permission_ws', 'ts_ws_permission_id',
                                       'ws_id', 'Working Schedules'),
                'active': fields.boolean('Active'),
                'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                         domain=[('object_id.model', '=', _name), \
                                                 ('field_id.name', 'not in', ['write_date', 'audit_log_ids'])]),
    }
    
    _defaults = {
                 'active': True,
    }



vhr_ts_working_schedule_permission()