# -*- coding: utf-8 -*-

from datetime import datetime

from openerp.osv import osv, fields


MONTH = [(1, 'January'),
         (2, 'February'),
         (3, 'March'),
         (4, 'April'),
         (5, 'May'),
         (6, 'June'),
         (7, 'July'),
         (8, 'August'),
         (9, 'September'),
         (10, 'October'),
         (11, 'November'),
         (12, 'December')]


class vhr_ts_view_result_detail(osv.osv_memory):
    _name = 'vhr.ts.view.result.detail'

    _columns = {
        'month': fields.selection(MONTH, 'Month'),
        'year': fields.integer('Year'),
    }
    _defaults = {
        'month': datetime.now().month,
        'year': datetime.now().year,
    }

    def onchange_admin(self, cr, uid, ids, admin_id, timesheets, month, year, context=None):
        res = {'value': {}, 'domain': {}}
        timesheet_ids = []
        admin_timesheet_ids = []
        if admin_id and month and year:
            """
            if admin_id has then domain timesheet and employee_id
            if admin_id
            """
            timesheet_detail_obj = self.pool.get('vhr.ts.timesheet.detail')
            detail_ids = timesheet_detail_obj.search(cr, uid, [('admin_id', '=', admin_id), ('year', '=', year),
                                                               ('month', '=', month)])
            admin_timesheet_ids = [item['timesheet_id'][0] for item in
                                   timesheet_detail_obj.read(cr, uid, detail_ids, ['timesheet_id'])
                                   if item.get('timesheet_id')]
            res['domain']['timesheets'] = [('id', 'in', admin_timesheet_ids)]
        if not admin_id:
            res['domain']['timesheets'] = [(1, '=', 1)]
        if timesheets != [[6, False, []]]:
            timesheet_ids = timesheets[0][2]
        if admin_id and timesheet_ids:
            timesheet_ids = [timesheet_id for timesheet_id in timesheet_ids if timesheet_id in admin_timesheet_ids]
            res['domain']['timesheets'] = [('id', 'in', admin_timesheet_ids)]
            res['value']['timesheets'] = [(6, 0, timesheet_ids)]
        return res

    def validate_input(self, cr, uid, ids, context):
        wz_obj = self.browse(cr, uid, ids[0], context=context)
        month = wz_obj.month
        year = wz_obj.year
        timesheet_detail_obj = self.pool.get('vhr.ts.timesheet.detail')
        groups = self.pool.get('res.users').get_groups(cr, uid)
        special_groups = ['vhr_cb', 'hrs_group_system']
        if not set(special_groups).intersection(set(groups)):
            domain = [('admin_id.user_id.id', '=', uid), ('month', '=', month), ('year', '=', year)]
        else:
            domain = [('month', '=', month), ('year', '=', year)]
        timesheet_detail_ids = timesheet_detail_obj.search(cr, uid, domain)
        list_timesheet = timesheet_detail_obj.read(cr, uid, timesheet_detail_ids, ['timesheet_id'])
        list_timesheet_ids = [x['timesheet_id'][0] for x in list_timesheet if x and x.get('timesheet_id')]
        return list_timesheet_ids, month, year

    def view_result_summary(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        wz_obj = self.browse(cr, uid, ids[0], context=context)
        month = wz_obj.month
        year = wz_obj.year
        dashboard_obj = self.pool.get('vhr.ts.summary.dashboard')
        sql = 'select * from fn_ts_summary_dashboard_ins_up(%s, %s, %s);' % (uid, month, year)
        cr.execute(sql)
        res_ids = dashboard_obj.search(cr, uid,
                                       [('month', '=', month),
                                        ('year', '=', year)])
        ir_model_pool = self.pool.get('ir.model.data')
        view_tree_result = ir_model_pool.get_object_reference(cr, uid, 'vhr_timesheet',
                                                              'view_vhr_ts_summary_dashboard_tree')
        view_tree_id = view_tree_result and view_tree_result[1] or False
        context['search_default_group_by_state'] = 1
        return {
            'name': 'Timesheet Summary Progress in %s-%s' % (month, year),
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'vhr.ts.summary.dashboard',
            'view_id': view_tree_id,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', res_ids), ('month', '=', month), ('year', '=', year)],
            'context': context,
        }

    def view_result(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        wz_obj = self.browse(cr, uid, ids[0], context=context)
        month = wz_obj.month
        year = wz_obj.year
        dashboard_obj = self.pool.get('vhr.ts.detail.dashboard')
        groups = self.pool.get('res.users').get_groups(cr, uid)
        special_groups = ['vhr_cb', 'vhr_group_system']
        if not set(special_groups).intersection(set(groups)):
            admin_id = self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', uid)])
            if not admin_id:
                raise
            admin_id = admin_id[0]
        else:
            admin_id = 'null'
            uid = 1

        sql = 'select * from fn_ts_detail_dashboard_ins_up(%s, %s, %s);' % (admin_id, month, year)
        cr.execute(sql)
        res_ids = dashboard_obj.search(cr, uid,
                                       ['|', ('write_uid', '=', uid),
                                        ('create_uid', '=', uid),
                                        ('month', '=', month),
                                        ('year', '=', year)])
        ir_model_pool = self.pool.get('ir.model.data')
        view_tree_result = ir_model_pool.get_object_reference(cr, uid, 'vhr_timesheet',
                                                              'view_vhr_ts_detail_dashboard_tree')
        view_tree_id = view_tree_result and view_tree_result[1] or False
        context['search_default_group_by_state'] = 1
        return {
            'name': 'Timesheet Detail Progress in %s-%s' % (month, year),
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'vhr.ts.detail.dashboard',
            'view_id': view_tree_id,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', res_ids), ('month', '=', month), ('year', '=', year)],
            'context': context,
        }



