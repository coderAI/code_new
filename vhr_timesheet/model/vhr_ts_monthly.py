# -*- coding: utf-8 -*-
import logging
from openerp.osv import osv, fields
from openerp.tools.translate import _
# from openerp.addons.vhr_timesheet.model.vhr_holiday_line import STATUS
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import datetime
from openerp import SUPERUSER_ID
from dateutil.relativedelta import relativedelta
from openerp.addons.vhr_common.model.vhr_common import vhr_common


STATES = [('draft', 'Draft'), ('sent', 'Sent'), ('approve', 'Approved'), ('reject', 'Rejected')]

log = logging.getLogger(__name__)

class vhr_ts_monthly(osv.osv, vhr_common):
    _name = 'vhr.ts.monthly'

    _columns = {
        'name': fields.char('Name', size=64),
        'holiday_name': fields.char('Holiday Name', size=64),#This field for case have leave request not validate
        'shift_name': fields.char('Shift Name', size=64),
        'employee_id': fields.many2one('hr.employee', 'Employee', ondelete='restrict'),
        'employee_code': fields.related('employee_id', 'code', type='char', string='Employee Code', store=True),
        'date': fields.date('Date'),
        'year': fields.integer('Year'),
        'month': fields.integer('Month'),
        'timesheet_id': fields.many2one('vhr.ts.timesheet', 'Timesheet', ondelete='restrict'),
        'timesheet_detail_id': fields.many2one('vhr.ts.timesheet.detail', 'Timesheet Detail', ondelete='restrict'),
        'working_schedule_id': fields.many2one('vhr.ts.working.schedule', 'Working Schedule', ondelete='restrict'),
        'ts_ws_employee_id': fields.many2one('vhr.ts.ws.employee', 'Employee Working', ondelete='restrict'),
        'ws_group_id': fields.many2one('vhr.ts.working.group', string='Working Group', ondelete='restrict'),
        'department_id': fields.many2one('hr.department', 'Department', ondelete='restrict'),
        'shift_id': fields.many2one('vhr.ts.working.shift', 'Working Shift', ondelete='restrict'),
        'holiday_line_id': fields.many2one('vhr.holiday.line', 'Holiday Line', ondelete='restrict'),
        'type_id': fields.many2one('vhr.public.holidays.type', 'Public Holidays', ondelete='restrict'),
        'leave_type_id': fields.related('holiday_line_id', 'holiday_id', 'holiday_status_id', type='many2one',
                                        relation='hr.holidays.status', string='Leave Type', ondelete='restrict'),
        'coef': fields.float('Coef'),
        'admin_id': fields.many2one('hr.employee', 'Admin', ondelete='restrict'),
        'parking_coef': fields.float('Parking Coef'),
        'meal_coef': fields.float('Meal Coef'),
        'state': fields.selection(STATES, string='State'),
        'is_last_payment': fields.boolean('For Last Payment'),
        'termination_date': fields.date('Termination Date'),
    }
    
    _order = 'employee_code desc, timesheet_id desc'

    _defaults = {
    }
    
        
    def build_domain_filter_timesheet(self, cr, uid, args, context):
        if context.get('filter_timesheet') and context.get('vhr_timesheet_ids'):
            args.append(('timesheet_id', 'in', context['vhr_timesheet_ids']))
        return args
        
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        # Search rule for specific menu
        if context is None:
            context = {}
        context.update({'active_test': False})
        #tuannh3: Fix return after gen detail
        args = self.build_domain_filter_timesheet(cr, uid, args, context)
        if context.get('search_timesheet_id'):
            args.append(('timesheet_id', 'in', context['search_timesheet_id']))
            del context['search_timesheet_id']
        if not limit:
            limit = 500
        if not context.get('get_all'):
            groups = self.pool.get('res.users').get_groups(cr, uid)
            special_groups = ['hrs_group_system', 'vhr_cb_timesheet','vhr_cnb_manager','vhr_cb_timesheet_readonly']
            if not set(special_groups).intersection(set(groups)):
#                 if 'vhr_dept_head' in groups:
#                     login_employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=',uid)], 0, None, None, context)
#                     if login_employee_ids:
#                         department_ids = self.get_hierachical_department_from_manager(cr, uid, login_employee_ids[0], context)
#                         employee_ids = self.pool.get('hr.employee').search(cr, uid, [('department_id','in',department_ids)])
#                         args.append(('employee_id','in',employee_ids))
#                 
#                 else:
                args += ['|',
                         ('timesheet_detail_id.admin_id.user_id.id', '=', uid),
                         '&', ('state', 'in', ('sent','approve','reject')),
                         ('timesheet_detail_id.approve_id.user_id.id', '=', uid)]
                # for get totalmenu_vhr_timesheet_timesheet
        if context.get('search_count') or context.get('monthly'):
            month = [arg[2] for arg in args if isinstance(arg, list) and arg[0] == 'month']
            month = month and month[0] or False
            year = [arg[2] for arg in args if arg[0] == 'year']
            year = year and year[0] or False
            holiday_line_id_state = [arg[2] for arg in args if
                                     isinstance(arg, list) and arg[0] == 'holiday_line_id_state']
            if holiday_line_id_state:
                holiday_line_id_state = holiday_line_id_state[0]
                args = [arg for arg in args if
                        not isinstance(arg, list) or isinstance(arg, list) and arg[0] != 'holiday_line_id_state']
            state = [arg[2] for arg in args if isinstance(arg, list) and arg[0] == 'state']
            if state:
                state = state[0]
        if context.get('search_count') and month and year:
            res_ids = super(vhr_ts_monthly, self).search(cr, uid, args=args, offset=False, limit=False, order=order,
                                                         context=context, count=False)
            if not res_ids  or len(res_ids) == 1:
                return res_ids

            sql = """
                SELECT DISTINCT ON (employee_id, timesheet_id) id
                FROM vhr_ts_monthly
                WHERE year = %s and month = %s
                      AND id in %s
            """ % (year, month, tuple(res_ids))

            if state == 'draft' and holiday_line_id_state and holiday_line_id_state != 'all':
                tuple_state = str(tuple(['confirm', 'validate1'])).replace(',)', ')')
                if holiday_line_id_state == 'waiting_approve':
                    sql = """
                        SELECT DISTINCT ON (MM.employee_id, MM.timesheet_id)
                          MM.id
                        FROM vhr_ts_monthly AS MM
                          INNER JOIN vhr_ts_timesheet_detail TT
                                  ON TT.id = MM.timesheet_detail_id
                          INNER JOIN
                          vhr_holiday_line AS LL
                            ON LL.id = MM.holiday_line_id
                            AND LL.date BETWEEN TT.from_date AND TT.to_date
                          INNER JOIN hr_holidays AS HH ON HH.id = LL.holiday_id

                        WHERE MM.year = %s AND MM.month = %s AND HH.state IN %s
                              AND MM.id in %s
                    """ % (year, month, tuple_state, tuple(res_ids))
                elif holiday_line_id_state == 'approved':
                    sql = """
                    SELECT
                      MP.employee_id,
                      MP.timesheet_id
                    FROM vhr_ts_monthly AS MP
                    WHERE MP.month = {0}
                          AND MP.year = {1}
                          AND MP.id in {3}
                          AND (MP.employee_id, MP.timesheet_id) NOT IN (
                            SELECT DISTINCT
                              MP.employee_id,
                              MP.timesheet_id
                            FROM vhr_ts_monthly MP
                              INNER JOIN vhr_ts_timesheet_detail TT ON TT.id = MP.timesheet_detail_id
                              LEFT JOIN vhr_holiday_line LL ON LL.id = MP.holiday_line_id
                              INNER JOIN hr_holidays HH ON HH.id = LL.holiday_id
                            WHERE HH.state IN {2}
                                  AND LL.date BETWEEN TT.from_date AND TT.to_date
                                  AND MP.month = {0} AND MP.year = {1}
                                  OR MP.holiday_line_id IS NULL
                          )
                    GROUP BY 1, 2;
                    """.format(month, year, tuple_state, tuple(res_ids))

            cr.execute(sql)
            res = cr.fetchall()
            res = [res_id[0] for res_id in res]
            return res
        if context.get('monthly') and month and year:
            res_ids = super(vhr_ts_monthly, self).search(cr, uid, args=args, offset=False, limit=False,
                                                         order=order,
                                                         context=context, count=False)
            if not res_ids or len(res_ids) == 1:
                return res_ids
            sql = """
                SELECT
                  id,
                  employee_id,
                  timesheet_id
                FROM vhr_ts_monthly
                WHERE (employee_id, timesheet_id) IN
                      (SELECT DISTINCT ON (employee_id, timesheet_id)
                         employee_id,
                         timesheet_id
                       FROM vhr_ts_monthly
                       WHERE id IN %s
                       LIMIT %s
                       OFFSET %s
                      )
                      AND id IN %s
                ORDER BY timesheet_id, department_id, employee_id
            """ % (tuple(res_ids), limit, offset, tuple(res_ids))
            if state == 'draft':
                if holiday_line_id_state and holiday_line_id_state != 'all':
                    if holiday_line_id_state == 'waiting_approve':
                        tuple_state = str(tuple(['confirm', 'validate1'])).replace(',)', ')')
                        sql = """
                                SELECT
                                  MM.id,
                                  MM.employee_id,
                                  MM.timesheet_id
                                FROM vhr_ts_monthly AS MM
                                INNER JOIN vhr_ts_timesheet_detail TT
                                  ON TT.id = MM.timesheet_detail_id
                                INNER JOIN (SELECT DISTINCT MO.employee_id, MO.timesheet_id
                                       FROM vhr_ts_monthly AS MO
                                       INNER JOIN vhr_ts_timesheet_detail TK ON TK.id = MO.timesheet_detail_id
                                       INNER JOIN vhr_holiday_line LL ON LL.id = MO.holiday_line_id
                                       INNER JOIN hr_holidays HH ON HH.id = LL.holiday_id
                                       WHERE
                                         HH.state IN {3}
                                         AND LL.date BETWEEN TK.from_date AND TK.to_date
                                         AND TK.month = {1}
                                         AND TK.year = {2}
                                       LIMIT {4}
                                       OFFSET {5}
                                      ) MD ON MD.employee_id = MM.employee_id
                                              AND MD.timesheet_id = MM.timesheet_id
                                WHERE TT.month = {1}
                                      AND TT.year = {2}
                                      AND MM.id IN {0}
                                ORDER BY MM.timesheet_id, MM.department_id, MM.employee_id;
                        """.format(tuple(res_ids), month, year, tuple_state, limit, offset)
                    elif holiday_line_id_state == 'approved':
                        tuple_state = str(tuple(['confirm', 'validate1'])).replace(',)', ')')
                        sql = """
                               SELECT
                                  MP.id,
                                  MP.employee_id,
                                  MP.timesheet_id,
                                  MP.department_id
                                FROM vhr_ts_monthly AS MP
                                INNER JOIN (SELECT DISTINCT
                                              employee_id,
                                              timesheet_id
                                            FROM vhr_ts_monthly
                                            WHERE month = {1}
                                                  AND year = {2}
                                            LIMIT {4}
                                            OFFSET {5}) MD on MD.employee_id = MP.employee_id
                                                        AND MD.timesheet_id = MP.timesheet_id
                                WHERE
                                      MP.id in {0}
                                      AND MP.month = {1}
                                      AND MP.year = {2}
                                      AND (MP.employee_id, MP.timesheet_id) NOT IN (
                                            SELECT DISTINCT
                                              MO.employee_id,
                                              MO.timesheet_id
                                            FROM vhr_ts_monthly MO
                                              INNER JOIN vhr_ts_timesheet_detail TT ON TT.id = MO.timesheet_detail_id
                                              LEFT JOIN vhr_holiday_line LL ON LL.id = MO.holiday_line_id
                                              INNER JOIN hr_holidays HH ON HH.id = LL.holiday_id
                                            WHERE HH.state IN {3}
                                                  AND LL.date BETWEEN TT.from_date AND TT.to_date
                                                  AND MO.month = {1} AND MO.year = {2}
                                                  OR MO.holiday_line_id IS NULL
                                  )
                        """.format(tuple(res_ids), month, year, tuple_state, limit, offset)

            cr.execute(sql)
            res = cr.fetchall()
            res = [res_id[0] for res_id in res if res_id[0]]
            return res

        return super(vhr_ts_monthly, self).search(cr, uid, args, offset, limit, order, context, count)

    def set_state(self, cr, uid, ids, state, context=None):
        if context is None:
            context = {}
        if not ids:
            return True
        groups = self.pool.get('res.users').get_groups(cr, uid)
        special_groups = ['vhr_cb_timesheet']
        for item in ids:
            if item == None:
                ids.remove(item)
                
        all_monthly = self.browse(cr, SUPERUSER_ID, ids)
        waiting_for_approve_ids = []
        for date_item in all_monthly:
            #When monthly records at state draft, only CB and admin can do action with these records
            if state == 'sent':
                if date_item.holiday_line_id \
                 and date_item.holiday_line_id.holiday_id \
                 and date_item.holiday_line_id.holiday_id.state in ['confirm', 'validate1']:
                    waiting_for_approve_ids.append(date_item.employee_id and date_item.employee_id.name or '')
                if not set(special_groups).intersection(set(groups)):
                    if date_item.timesheet_detail_id.admin_id \
                     and date_item.timesheet_detail_id.admin_id.user_id \
                     and date_item.timesheet_detail_id.admin_id.user_id.id != uid:
                        raise osv.except_osv(_('Warning!'),
                                             _('Only %s or C&B can send detail of %s !' % (
                                                 self.get_employee_name(cr, uid, date_item.timesheet_detail_id.admin_id),
                                                 date_item.employee_id and self.get_employee_name(cr, uid, date_item.employee_id))))
                    if not date_item.timesheet_detail_id.admin_id:
                        raise osv.except_osv(_('Warning!'),
                                             _('Only C&B can send detail of %s !' % (
                                                 date_item.employee_id and self.get_employee_name(cr, uid, date_item.employee_id))))
            #When change monthly record to state approve, only cb and timesheet can do action with these records 
            elif state == 'approve' or (state == 'reject' and date_item.state == 'sent'):
                if not set(special_groups).intersection(set(groups)):
                    if date_item.timesheet_detail_id and date_item.timesheet_detail_id.approve_id \
                     and date_item.timesheet_detail_id.approve_id.user_id \
                     and date_item.timesheet_detail_id.approve_id.user_id.id != uid:
                        raise osv.except_osv(_('Warning!'),
                                             _('Only %s or C&B can %s detail of %s !' % (
                                                 self.get_employee_name(cr, uid, date_item.timesheet_detail_id.approve_id), state,
                                                 date_item.employee_id and self.get_employee_name(cr, uid, date_item.employee_id))))
                    if not (date_item.timesheet_detail_id and date_item.timesheet_detail_id.approve_id):
                        raise osv.except_osv(_('Warning!'),
                                             _('Only C&B can %s detail of %s !' % (
                                                 state, date_item.employee_id and self.get_employee_name(cr, uid, date_item.employee_id))))
                        
                if date_item.timesheet_detail_id and datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT) > date_item.timesheet_detail_id.close_date:
                    raise osv.except_osv(_('Warning!'),
                                         _('Timesheet\'s period of [%s] already closed. You can\'t approve!'
                                           '\nPlease contract to C&B team for supporting!' % (
                                               date_item.timesheet_id.name)))
            #When change monthly record to state reject, only cb can do action with these records
            elif state == 'reject' and date_item.state == 'approve':
                if not set(special_groups).intersection(set(groups)):
                    raise osv.except_osv(_('Warning!'),
                                             _('Only C&B can %s detail of %s !' % (
                                                 state, date_item.employee_id and self.get_employee_name(cr, uid, date_item.employee_id))))
                
                if date_item.timesheet_detail_id and datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT) > date_item.timesheet_detail_id.close_date:
                    raise osv.except_osv(_('Warning!'),
                                         _('Timesheet\'s period of [%s] already closed. You can\'t reject!'
                                           '\nPlease contract to C&B team for supporting!' % (
                                               date_item.timesheet_id.name)))
                
        if waiting_for_approve_ids:
            waiting_for_approve_ids = list(set(waiting_for_approve_ids))
            msg = ', '.join(waiting_for_approve_ids)
            msg += ' has leave request is waiting for approval!'
            raise osv.except_osv(_('Warning!'), msg)
        first_record = self.read(cr, uid, ids[0], ['state', 'month', 'year'])
        if state == 'reject' and first_record.get('state') == 'approve':
            employee_ids = [employee['employee_id'][0] for employee in self.read(cr, uid, ids, ['employee_id']) if
                            employee.get('employee_id')]

            summary_obj = self.pool.get('vhr.employee.timesheet.summary')
            delete_ids = summary_obj.search(cr, uid,
                                            [('employee_id', 'in', employee_ids),
                                             ('month', '=', first_record.get('month')),
                                             ('year', '=', first_record.get('year'))])
            summary_obj.unlink(cr, uid, delete_ids, context=context)

        self.write(cr, uid, ids, {'state': state})
        return True
    
    def get_employee_name(self, cr, uid, employee, context=None):
        fullname = ''
        if employee:
            code = employee.code or ''
            login = employee.login or ''
            
            fullname =code
            if fullname:
                fullname += " (" + login + ")"
        
        return fullname
    
    def get_leave_request_in_dateRange(self, cr, uid, employee_code, dateRange, context=None):
        res = []
        if employee_code and dateRange:
            dateRange = str(tuple(dateRange)).replace(',)', ')')
            sql = '''
                    SELECT DISTINCT holiday.id
                    FROM
                        (SELECT hr.id FROM hr_employee hr INNER JOIN resource_resource rr ON hr.resource_id = rr.id WHERE rr.code = '%s') as employee
                        INNER JOIN
                        (SELECT hh.id, hh.employee_id FROM hr_holidays hh INNER JOIN vhr_holiday_line hl ON hh.id = hl.holiday_id WHERE hl.date in %s and hh.state != 'refuse') as holiday
                        ON employee.id = holiday.employee_id
            ''' % (employee_code, dateRange)
            
            cr.execute(sql)
            res = cr.fetchall()
            res = [item[0] for item in res]
            return res
        
    def get_form_tree_list_of_leave(self, cr, uid, context=None):
        ir_model_pool = self.pool.get('ir.model.data')
        view_tree_result = ir_model_pool.get_object_reference(cr, uid, 'vhr_timesheet', 'view_holiday_simple')
        view_tree_id = view_tree_result and view_tree_result[1] or False
         
        view_form_result = ir_model_pool.get_object_reference(cr, uid, 'vhr_timesheet', 'view_hr_holidays_new_form')
        view_form_id = view_form_result and view_form_result[1] or False
        
        return view_tree_id, view_form_id

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if not context.get('dont_check_state'):
            for i in self.read(cr, uid, ids, ['state']):
                if i.get('state') in ('approve', 'sent'):
                    raise osv.except_osv(_('Warning!'),
                                         _('You can only delete timesheet\'s detail which is Draft or Reject state!'))
        return super(vhr_ts_monthly, self).unlink(cr, uid, ids, context=context)

    def get_default_state_base_on_uid(self, cr, uid, month, year, context=None):
        groups = self.pool.get('res.users').get_groups(cr, uid)
        special_groups = ['vhr_cb']
        if set(special_groups).intersection(set(groups)):
            return 'draft'
        detail_obj = self.pool.get('vhr.ts.timesheet.detail')
        if detail_obj.search(cr, uid,
                             [('admin_id.user_id.id', '=', uid), ('month', '=', month), ('year', '=', year)]):
            return 'draft'
        elif detail_obj.search(cr, uid,
                               [('approve_id.user_id.id', '=', uid), ('month', '=', month), ('year', '=', year)]):
            return 'sent'
        return 'draft'
    
    def get_list_grey_date(self, cr, uid, employee_code, month, year, list_date_none_data, context=None):
        result = []
        instance_obj = self.pool.get('vhr.employee.instance')
        log.info("\n\nCall get_list_grey_date--------------")
        if employee_code and month and year and list_date_none_data:
            employee_ids = self.pool.get('hr.employee').search(cr, uid, [("code",'=',employee_code)], context={'search_all_employee': True,'active_test': False})
            if employee_ids:
                from datetime import date as date_mdl
                date_of_last_month = (date_mdl(int(year), int(month), 1)  - relativedelta(months=1)) .strftime(DEFAULT_SERVER_DATE_FORMAT)
                
                instance_ids = instance_obj.search(cr, uid, [('employee_id','=',employee_ids[0]),
                                                             '|',('date_end','>=',date_of_last_month),
                                                             ('date_end','=',False)], order='date_start asc')
                
                instances = instance_obj.read(cr, uid, instance_ids, ['date_start', 'date_end'])
                list_date = [[instance.get('date_start',False), instance.get('date_end',False)] for instance in instances]
                list_date_in_working = []
                for date in list_date_none_data:
                    for date_instance in list_date:
                        if self.compare_day(date_instance[0],date) >= 0 and \
                         ( (date_instance[1] and self.compare_day(date, date_instance[1]) >= 0 ) or not date_instance[1]):
                             list_date_in_working.append(date)
                             break
                
                result = list(set(list_date_none_data).difference(set(list_date_in_working)))
        return result
            


vhr_ts_monthly()
