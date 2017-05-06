# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import thread
import logging
import sys
import time

from openerp.addons.vhr_common.model.vhr_common import vhr_common
from dateutil.relativedelta import relativedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.osv import osv, fields
from openerp.tools.translate import _
from openerp.osv import osv, fields
from openerp.sql_db import Cursor
from openerp.sql_db import ConnectionPool
from openerp import tools
from openerp import SUPERUSER_ID

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

log = logging.getLogger(__name__)


class vhr_ts_monthly_gen(osv.osv, vhr_common):
    _name = 'vhr.ts.monthly.gen'

    _columns = {
        'employee_id': fields.many2one('hr.employee', 'Employee'),
        'waiting_approve_ids': fields.many2many('hr.holidays', 'monthly_gen_holiday_rel', 'gen_id', 'holiday_id',
                                                'Waiting For Approvals'),
        'admin_id': fields.many2one('hr.employee', 'Admin'),
        'timesheets': fields.many2many('vhr.ts.timesheet', 'ts_monthly_gen_rel', 'ts_monthly_id',
                                       'timesheet_id', 'Timesheet'),
        'month': fields.selection(MONTH, 'Month'),
        'year': fields.integer('Year'),
        'run_sql': fields.boolean('Run SQL'),
        #These fields to prevent run loop onchange
        'run_onchange_month': fields.boolean('Run Onchange Month'),
        'run_onchange_year': fields.boolean('Run Onchange Year'),
        'run_onchange_admin_id': fields.boolean('Run Onchange Admin'),
        'run_onchange_timesheet_ids': fields.boolean('Run Onchange Timesheet'),
        'run_onchange_employee_id': fields.boolean('Run Onchange Employee'),
        'is_last_payment': fields.boolean('For Last Payment'),
        'lock_emp_ids': fields.many2many('vhr.ts.lock.timesheet.detail', 'monthly_gen_lock_emp_rel', 'gen_id','lock_id', 'Lock Employee'),
        'lock_emp_text': fields.text('Lock Emp', size=256),
    }
    
    def _get_default_admin_id(self, cr, uid, context=None):
        '''
         If user does not belong to vhr_cb_timesheet, set admin_id = login_user(because field admin_id only use by vhr_cb_timesheet
        '''
        return self.get_default_admin_id(cr, uid, context)
    

    _defaults = {
        'month': datetime.now().month,
        'year': datetime.now().year,
        'run_sql': True,
        'run_onchange_timesheet_ids': True,
        'run_onchange_employee_id': True,
        'run_onchange_admin_id': True,
        'run_onchange_month': False,
        'run_onchange_year': False,
        'admin_id': _get_default_admin_id,
        'is_last_payment': False,
    }
    
    def get_default_admin_id(self, cr, uid, context=None):
        '''
         If user does not belong to hrs_group_system, return login employee_id
        '''
        user_groups = self.pool.get('res.users').get_groups(cr, uid)
        special_groups = ['hrs_group_system']
        if not set(special_groups).intersection(set(user_groups)):
            employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', uid)])
            if employee_ids:
                return employee_ids[0]

        return False
        

    def get_leave_reques_waiting_approve(self, cr, uid, timesheet_ids, employee_ids, month, year, context=None):
        if not timesheet_ids or not employee_ids:
            return []
        timesheet_ids = str(tuple(timesheet_ids)).replace(',)', ')')
        employee_ids = str(tuple(employee_ids)).replace(',)', ')')
        sql = """
                SELECT
                  DISTINCT
                  HL.id
                FROM vhr_ts_emp_timesheet a
                  INNER JOIN (SELECT
                                timesheet_id,
                                to_date,
                                from_date
                              FROM vhr_ts_timesheet_detail
                              WHERE month = %s AND year = %s) AS b ON a.timesheet_id = b.timesheet_id
                  INNER JOIN
                  (SELECT
                     HH.id,
                     LL.date,
                    HH.employee_id
                   FROM vhr_holiday_line LL
                     INNER JOIN (SELECT
                                   id, employee_id
                                 FROM hr_holidays
                                 WHERE state IN ('confirm', 'validate1'))
                                HH ON LL.holiday_id = HH.id) AS HL
                    ON HL.employee_id = a.employee_id
                WHERE
                  a.timesheet_id IN %s
                  AND a.employee_id IN %s
                  AND HL.date <= b.to_date
                  AND HL.date >= b.from_date
                  AND a.effect_from <= b.to_date
                  AND (a.effect_to IS NULL OR a.effect_to >= b.from_date)
                  AND a.employee_id IN (SELECT
                                        employee_id
                                      FROM vhr_employee_instance
                                      WHERE date_end IS NULL OR date_end >= b.from_date)
        """ % (month, year, timesheet_ids, employee_ids)
        cr.execute(sql)
        res = cr.fetchall()
        res = [item[0] for item in res]
        return res
    
    
    def onchange_admin_timesheet_emp(self, cr, uid, ids, admin_id, timesheets, employee_id, month, year, 
                                     run_onchange_admin_id, run_onchange_timesheet_ids, run_onchange_employee_id, context=None):
        if not context:
            context = {}
        
        res = {'value': {'lock_emp_ids': [(6, 0, [])],'lock_emp_text': '', 'waiting_approve_ids': [(6, 0, [])]}, 'domain': {}}
        timesheet_ids = timesheets and timesheets[0]  and timesheets[0][2] or []
        waiting_approve_ids = []
        
        if not run_onchange_admin_id:
            res['value'] = {'run_onchange_admin_id': True}
            return res
        elif not run_onchange_timesheet_ids:
            res['value'] = {'run_onchange_timesheet_ids': True}
            return res
        elif not run_onchange_employee_id:
            res['value'] = {'run_onchange_employee_id': True}
            return res
        
        if month and year:
            list_timesheet_ids = []
            list_emp_ids = []
            
            if employee_id and not context.get('onchange_timesheet', False) and not context.get('onchange_admin', False):
                if not timesheet_ids:
                    timesheet_ids = self.get_employee_timesheet(cr, uid, employee_id, [], month, year)
                    
                values = self.get_data_waiting_approve_lock_emp(cr, uid, [employee_id], timesheet_ids, month, year, context)
                res['value'].update(values)
            
            elif timesheet_ids and not context.get('onchange_admin', False):
                #Load list leave request waiting for approve when change timesheet
                employee_ids = self.get_timesheet_employee(cr, uid, timesheet_ids, month, year)
    #             res['domain']['employee_id'] = [('id', 'in', employee_ids)]
                if context.get('onchange_timesheet', False):
                    if employee_id:
                        if employee_id not in employee_ids:
                            res['value']['employee_id'] = False
                            res['value']['run_onchange_employee_id'] = False
                        else:
                            employee_ids = [employee_id]
                
                values = self.get_data_waiting_approve_lock_emp(cr, uid, employee_ids, timesheet_ids, month, year, context)
                res['value'].update(values)
                
            #In case change admin
            elif admin_id:
                """
                if admin_id has then domain timesheet and employee_id
                if admin_id
                """
                timesheet_detail_obj = self.pool.get('vhr.ts.timesheet.detail')
                detail_ids = timesheet_detail_obj.search(cr, uid, [('admin_id', '=', admin_id), 
                                                                   ('year', '=', year),
                                                                   ('month', '=', month)])
                list_timesheet_ids = [item['timesheet_id'][0] for item in
                                       timesheet_detail_obj.read(cr, uid, detail_ids, ['timesheet_id'])
                                       if item.get('timesheet_id')]
    
                if list_timesheet_ids:
                    #Load list leave request waiting for approve when change admin
                    list_emp_ids = self.get_timesheet_employee(cr, uid, list_timesheet_ids, month, year)
                    
                    values = self.get_data_waiting_approve_lock_emp(cr, uid, list_emp_ids, list_timesheet_ids, month, year, context)
                    res['value'].update(values)
                
                if not context.get('onchange_timesheet', False):
                    res['value']['timesheets'] = [(6, 0, list_timesheet_ids)]
                
                if timesheet_ids:
                    res['value']['run_onchange_timesheet_ids'] = False
                if employee_id:
                    res['value']['run_onchange_employee_id'] = False
                res['value']['employee_id'] = False
            
        
            if not admin_id and not timesheets and not employee_id:
                res['value']['timesheets'] = [(6, 0, [])]
                
                context['all_employees'] = True
                lock_emp_ids = self.get_lock_employee_from_list(cr, uid, month, year, [], context)
                if lock_emp_ids:
                    res['value']['lock_emp_ids'] = [(6, 0, lock_emp_ids)]
                    res['value']['lock_emp_text'] = str(lock_emp_ids)
        
        return res
    
    
    def get_lock_employee_from_list(self, cr, uid, month, year, employee_ids, context=None):
        if not context:
            context = {}
            
        emp_ids = []
#         if month and year and (employee_ids or context.get('all_employees', False)):
#             domain =  [('month','=',month),
#                        ('year','=',year),
#                        ('state','=','lock')]
#             
#             if employee_ids:
#                 domain.append(('employee_id','in',employee_ids))
#             emp_ids = self.pool.get('vhr.ts.lock.timesheet.detail').search(cr, uid, domain)
        
        return emp_ids
    
    def onchange_month(self, cr, uid, ids, month, year, admin_id, timesheets, employee_id, run_onchange_month, context=None):
        res = {'value': {}, 'domain': {}}
        if not run_onchange_month:
            res['value']['run_onchange_month'] = True
            return res
        
        return self.onchange_month_year(cr, uid, ids, month, year, admin_id, timesheets, employee_id, context)
        
    def onchange_year(self, cr, uid, ids, month, year, admin_id, timesheets, employee_id, run_onchange_year, context=None):
        res = {'value': {}, 'domain': {}}
        if not run_onchange_year:
            res['value']['run_onchange_year'] = True
            return res
        
        return self.onchange_month_year(cr, uid, ids, month, year, admin_id, timesheets, employee_id, context)
        
    def onchange_month_year(self, cr, uid, ids, month, year, admin_id, timesheets, employee_id, context=None):
        if not context:
            context = {}
            
        res = {'value': {'waiting_approve_ids': [(6, 0, [])], 'lock_emp_ids': [(6, 0, [])],'lock_temp_text': ''}, 'domain': {}}
        if month and year:
            new_admin_id = admin_id
            old_timesheet_ids = []
            new_timesheet_ids = []
            if admin_id:
                list_admin_ids = self.pool.get('hr.employee').search(cr, uid, [], context={"admin_timesheet": True, 'context_month':month, 'context_year': year})
                if admin_id not in list_admin_ids:
                    #Assign admin_id = loin employee_id if login user is vhr_dept_admin
                    default_admin_id = self.get_default_admin_id(cr, uid, context)
                    new_admin_id = default_admin_id
                    res['value']['admin_id'] = default_admin_id
                    
            if timesheets and timesheets[0] and timesheets[0][2]:
                old_timesheet_ids = timesheets[0][2] or []
                mcontext={'timesheet_admin': 1, 'month':month, 'year': year}
#                 if new_admin_id:
                mcontext['filter_by_admin_id'] = new_admin_id
                new_timesheet_ids = self.pool.get('vhr.ts.timesheet').search(cr, uid, [], context=mcontext)
#                 new_timesheet_ids = [id for id in old_timesheet_ids if id in list_timesheet_ids]
                if not set(new_timesheet_ids).intersection(set(old_timesheet_ids)):
                    res['value']['run_onchange_timesheet_ids'] = False
                res['value']['timesheets'] = [(6, 0, new_timesheet_ids)]
            if employee_id:
                mcontext = {"employee_timesheet": True, 'context_month':month, 'context_year': year}
                if new_admin_id:
                    mcontext['admin_id'] = new_admin_id
                if new_timesheet_ids:
                    mcontext['timesheet'] = [(6, 0, new_timesheet_ids)]
                list_emp_ids = self.pool.get('hr.employee').search(cr, uid, [], context= mcontext)
                if employee_id not in list_emp_ids:
                    res['value']['run_onchange_employee_id'] = False
                    res['value']['employee_id'] = False
                    res['value']['waiting_approve_ids'] = [(6, 0, [])]
            
            
            if res['value'].get('employee_id',False):
                #If have employee in res['value'], it's mean that we use employee_id from input
                if not new_timesheet_ids:
                    new_timesheet_ids = self.get_employee_timesheet(cr, uid, employee_id, [], month, year)
                
                values = self.get_data_waiting_approve_lock_emp(cr, uid, [employee_id], new_timesheet_ids, month, year, context)
                res['value'].update(values)
                
            elif new_timesheet_ids:
                employee_ids = self.get_timesheet_employee(cr, uid, new_timesheet_ids, month, year)
                values = self.get_data_waiting_approve_lock_emp(cr, uid, employee_ids, new_timesheet_ids, month, year, context)
                res['value'].update(values)
            
            elif new_admin_id:
                timesheet_detail_obj = self.pool.get('vhr.ts.timesheet.detail')
                detail_ids = timesheet_detail_obj.search(cr, uid, [('admin_id', '=', admin_id), 
                                                                   ('year', '=', year),
                                                                   ('month', '=', month)])
                new_timesheet_ids = [item['timesheet_id'][0] for item in
                                       timesheet_detail_obj.read(cr, uid, detail_ids, ['timesheet_id'])
                                       if item.get('timesheet_id')]
                
                employee_ids = self.get_timesheet_employee(cr, uid, new_timesheet_ids, month, year)
                
                values = self.get_data_waiting_approve_lock_emp(cr, uid, employee_ids, new_timesheet_ids, month, year, context)
                res['value'].update(values)
            
            else:
                context['all_employees'] = True
                lock_emp_ids = self.get_lock_employee_from_list(cr, uid, month, year, [], context)
                if lock_emp_ids:
                    res['value']['lock_emp_ids'] = [(6, 0, lock_emp_ids)]
                    res['value']['lock_emp_text'] = str(lock_emp_ids)

        return res
    
    def get_data_waiting_approve_lock_emp(self, cr, uid, employee_ids, timesheet_ids, month, year, context=None):
        values = {}
        if employee_ids and timesheet_ids and month and year:
            waiting_approve_ids = self.get_leave_reques_waiting_approve(cr, uid, timesheet_ids, employee_ids, month, year)
            values['waiting_approve_ids'] = [(6, 0, waiting_approve_ids)]
            
            lock_emp_ids = self.get_lock_employee_from_list(cr, uid, month, year, employee_ids, context)
            if lock_emp_ids:
                values['lock_emp_ids'] = [(6, 0, lock_emp_ids)]
                values['lock_emp_text'] = str(lock_emp_ids)
        
        return values
        

    def date_range(self, start_date, end_date):
        start_date = datetime.strptime(start_date, DEFAULT_SERVER_DATE_FORMAT)
        end_date = datetime.strptime(end_date, DEFAULT_SERVER_DATE_FORMAT)
        for n in range(int((end_date - start_date).days + 1)):
            yield (start_date + timedelta(n)).strftime(DEFAULT_SERVER_DATE_FORMAT)
            
    def check_in_date_range(self, date, start_date, end_date):
        date = datetime.strptime(date, DEFAULT_SERVER_DATE_FORMAT)
        start_date = datetime.strptime(start_date, DEFAULT_SERVER_DATE_FORMAT)
        end_date = end_date and datetime.strptime(end_date, DEFAULT_SERVER_DATE_FORMAT)
        
        return date >= start_date and (not end_date or date <= end_date)

    def get_employee_timesheet(self, cr, uid, emp_id, list_timesheet_ids, month, year):
        '''
            Get timesheet from employee
        '''
        sql = """
                SELECT
                  DISTINCT
                  a.timesheet_id
                FROM vhr_ts_emp_timesheet a
                  INNER JOIN (SELECT
                    timesheet_id,
                    to_date,
                    from_date
                  FROM vhr_ts_timesheet_detail
                  WHERE month = %s AND year = %s) AS b ON a.timesheet_id = b.timesheet_id

                WHERE
                  a.employee_id = %s
                  AND a.effect_from <= b.to_date
                  AND (a.effect_to IS NULL OR a.effect_to >= b.from_date)
                  AND employee_id IN (SELECT
                                        employee_id
                                      FROM vhr_employee_instance
                                      WHERE date_end IS NULL OR date_end >= b.from_date)
        """ % (month, year, emp_id)
        if list_timesheet_ids:
            sql += ' AND a.timesheet_id in %s' % str(tuple(list_timesheet_ids)).replace(',)', ')')
        cr.execute(sql)
        res = cr.fetchall()
        res = [item[0] for item in res]
        return res

    def get_timesheet_employee(self, cr, uid, list_timesheet_ids, month, year):
        return self.pool.get('hr.employee').get_employee_from_timesheet(cr, uid, list_timesheet_ids, month, year)

    def validate_input(self, cr, uid, ids, context):
        '''
            Return admin, create_uid, month, year, list timesheet, employee_id, is_last_payment filter by user selection in Detail Generation
            If user do not select any employee, admin, timesheet: 
                    - User run from Detail Generation: Only special_groups can gen for all timesheet in month-year
                    - User run from Summary Generation: special_groups and C&B_Timesheet can gen for all timesheet in month-year
                    - Other case, raise error
        '''
        if not context:
            context = {}
        context['active_test'] = False
        wz_obj = self.browse(cr, uid, ids[0], context=context)
        admin_id = wz_obj.admin_id and wz_obj.admin_id.id or False
        month = wz_obj.month
        year = wz_obj.year
        run_sql = wz_obj.run_sql
        emp_id = wz_obj.employee_id and wz_obj.employee_id.id or False
        is_last_payment = wz_obj.is_last_payment
        timesheet_detail_obj = self.pool.get('vhr.ts.timesheet.detail')
        timesheet_obj = self.pool.get('vhr.ts.timesheet')
        list_timesheet = wz_obj.timesheets
        
        list_lock_emp_ids = wz_obj.lock_emp_ids
        
        user_groups = self.pool.get('res.users').get_groups(cr, uid)
        special_groups = ['hrs_group_system', 'vhr_cb_timesheet']
        list_timesheet_ids = []
        #If user dont input employee, admin, timsheet and user do not belong to special_groups
        if not list_timesheet and not set(special_groups).intersection(set(user_groups)) and not emp_id and not admin_id:   
            timesheet_sum_group = ['vhr_cb_timesheet']         
            #Run from Detail Generation
            if not context.get('timesheet_summary_gen', False):
                raise osv.except_osv(_('Warning!'),
                                     _('You must select at least Admin or Employee or Timesheet to continue!'))
            #Run from Summary Generation, if user do not belong to timesheet_sum_group, raise error.
            #                                if user belong to timesheet_sum_group, add add_timesheet_sum_group into special group to get all timesheet
            elif context.get('timesheet_summary_gen', False):
                special_groups.extend(timesheet_sum_group)
                if not set(special_groups).intersection(set(user_groups)):
                    raise osv.except_osv(_('Warning!'),
                                 _('You must select at least Employee or Timesheet to continue!'))
        if emp_id:
            # find timesheet of employee in month - year
            list_timesheet_ids = self.get_employee_timesheet(cr, uid, emp_id, [], month, year)
            
        elif list_timesheet:
            list_timesheet_ids = [timesheet.id for timesheet in list_timesheet]
            
        elif admin_id:
            domain = [('admin_id', '=', admin_id), ('month', '=', month), ('year', '=', year)]
            if list_timesheet_ids:
                domain.append(('timesheet_id', 'in', list_timesheet_ids))
            timesheet_detail_ids = timesheet_detail_obj.search(cr, uid, domain)
            list_timesheet = timesheet_detail_obj.read(cr, uid, timesheet_detail_ids, ['timesheet_id'])
            list_timesheet_ids = [x['timesheet_id'][0] for x in list_timesheet if x and x.get('timesheet_id')]
        
        #If user dont input employee, timesheet, admin, check if user belong to special group to gen for all timesheet
        elif set(special_groups).intersection(set(user_groups)):
            list_timesheet_detail = timesheet_detail_obj.search(cr, uid, [('month', '=', month), ('year', '=', year)])
            list_timesheet_data = timesheet_detail_obj.read(cr, uid, list_timesheet_detail, ['timesheet_id'])
            list_timesheet_ids = [x['timesheet_id'][0] for x in list_timesheet_data if x and x.get('timesheet_id')]
            list_timesheet = [timesheet for timesheet in timesheet_obj.browse(cr, uid, list_timesheet_ids, context=context)]
            list_timesheet_ids = [timesheet.id for timesheet in list_timesheet]
        

        return emp_id, list_timesheet_ids, month, year, admin_id, run_sql, is_last_payment, list_lock_emp_ids

    def create_mass_detail(self, t_cr, uid, mass_status_id, emp_id, list_error, error_message):
        mass_status_detail_pool = self.pool.get('vhr.mass.status.detail')
        list_error.append((emp_id, error_message))
        mass_status_detail_pool.create(t_cr, uid, {'mass_status_id': mass_status_id,
                                                   'employee_id': list_error[-1][0],
                                                   'message': list_error[-1][1]})
        t_cr.commit()
        
    
    def get_employee_timesheet_of_timesheet_in_period(self, cr, uid, input_emp_id, timesheet_id, ts_detail_from_date, ts_detail_to_date, change_form_ids, context=None):
        emp_ts_ids = []
        if timesheet_id and  ts_detail_from_date and ts_detail_to_date and change_form_ids:
            tuple_change_form_ids = str(tuple(change_form_ids)).replace(',)', ')')
                        
            #Search in Working record before one day, because on date effect_from of WR have dismiss change form, employee still work
            one_day_before_ts_detail_from_date = datetime.strptime(ts_detail_from_date, DEFAULT_SERVER_DATE_FORMAT) - relativedelta(days=1)
            one_day_before_ts_detail_from_date  = one_day_before_ts_detail_from_date.strftime(DEFAULT_SERVER_DATE_FORMAT)
            sql = """
                SELECT
                  id
                FROM vhr_ts_emp_timesheet
                WHERE timesheet_id = %s AND effect_from <= '%s'
                      AND (effect_to IS NULL OR effect_to >= '%s')
                      AND employee_id IN (SELECT
                                            employee_id
                                          FROM vhr_employee_instance
                                          WHERE date_end IS NULL
                                          OR date_end >= '%s')
                      AND employee_id IN (SELECT
                                            employee_id
                                          FROM vhr_working_record R
                                            INNER JOIN working_record_change_form_rel RR
                                                ON R.id = RR.working_id
                                          WHERE (R.state IS NULL OR R.state = 'finish')
                                                AND R.effect_from <= '%s'
                                                AND (R.effect_to IS NULL OR R.effect_to >= '%s')
                                                AND RR.change_form_id NOT IN %s)
                      AND employee_id IN (SELECT
                                            employee_id
                                          FROM vhr_ts_ws_employee
                                          WHERE effect_from <= '%s'
                                                AND (effect_to IS NULL
                                                        OR effect_to >= '%s'))
                      AND employee_id NOT IN (SELECT DISTINCT
                                                (employee_id)
                                              FROM vhr_ts_monthly
                                              WHERE state IN ('approve', 'sent')
                                                    AND date BETWEEN '%s' AND '%s')
            """ % (
                timesheet_id, ts_detail_to_date, ts_detail_from_date,
                ts_detail_from_date,
                ts_detail_to_date, one_day_before_ts_detail_from_date,
                tuple_change_form_ids,
                ts_detail_to_date, ts_detail_from_date,
                ts_detail_from_date, ts_detail_to_date)
            if input_emp_id:
                sql += " AND employee_id = %s" % input_emp_id
            cr.execute(sql)

            # emp_ts_ids = emp_ts_obj.search(cr, uid, emp_ts_domain)
            emp_ts_ids = cr.fetchall()
            emp_ts_ids = [emp_ts_id[0] for emp_ts_id in emp_ts_ids]
            
        
        return emp_ts_ids
    
    
    
    def monthly_thread_execute(self, cr, uid, ids, mass_status_id, pool_obj, input_emp_id, list_timesheet_ids, month, year, is_last_payment, context=None):
        '''
            Create record of vhr.ts.monthly for employees
        '''
        if context is None:
            context = {}
        log.info('monthly thread_execute start()')
        mass_status_pool = self.pool.get('vhr.mass.status')
        mass_status_detail_pool = self.pool.get('vhr.mass.status.detail')
        _pool = ConnectionPool(int(tools.config['db_maxconn']))
        # cr used to create WR
        cr = Cursor(_pool, cr.dbname, True)
        # t_cr used to create/write Mass Status/ Mass Status Detail
        t_cr = Cursor(_pool, cr.dbname, True)  # Thread's cursor

        # clear old thread in cache to free memory
        reload(sys)
        error_message = ""
        create_ids = []
        list_error = []
        number_of_record = 0
        list_employee_execute = []
        list_employee_count = []
        context['get_all'] = 1
        context['dont_check_state'] = 1
        try:
            mass_status_pool.write(t_cr, uid, [mass_status_id], {'state': 'running',
                                                                 'number_of_record': number_of_record,
                                                                 'number_of_execute_record': 0,
                                                                 'number_of_fail_record': 0})
            t_cr.commit()
            if mass_status_id and list_timesheet_ids:
                ws_emp_obj = self.pool.get('vhr.ts.ws.employee')
                ts_detail_obj = self.pool.get('vhr.ts.timesheet.detail')
                ws_detail_obj = self.pool.get('vhr.ts.ws.detail')
                wr_obj = self.pool.get('vhr.working.record')
                holiday_line_obj = self.pool.get('vhr.holiday.line')
                ts_monthly_obj = self.pool.get('vhr.ts.monthly')
                parameter_obj = self.pool.get('ir.config_parameter')
                emp_ts_obj = self.pool.get('vhr.ts.emp.timesheet')
                change_form_obj = self.pool.get('vhr.change.form')
                
                #Read terminate change form code
                change_form_terminated_code = parameter_obj.get_param(cr, uid, 'vhr_master_data_dismiss_change_form_code').split(',')
                change_form_ids = change_form_obj.search(cr, uid, [('code', 'in', change_form_terminated_code)],context=context)
                
                #Get Working Group Code of WGroup chính thức, bình thường và CTV vp
                ct_bt_working_group_code = parameter_obj.get_param(cr, uid, 'ts.working.group.ct.bt').split(',')
                error_item = ''
                number_of_record = 0
                for timesheet_id in list_timesheet_ids:
                    #Get all available employee timesheet in month - year - timesheet
                    #Dont get employees generated and at state approve/sent  in month-year
                    ts_detail_ids = ts_detail_obj.search(cr, uid, [('month', '=', month), ('year', '=', year),
                                                                   ('timesheet_id', '=', timesheet_id)], context=context)
                    if ts_detail_ids:
                        ts_detail = ts_detail_obj.read(cr, uid, ts_detail_ids[0], ['from_date', 'to_date'], context=context)
                        ts_detail_from_date = ts_detail.get('from_date')
                        ts_detail_to_date = ts_detail.get('to_date')
                        
                        emp_ts_ids = self.get_employee_timesheet_of_timesheet_in_period(cr, uid, input_emp_id, timesheet_id, ts_detail_from_date, ts_detail_to_date, change_form_ids, context)
                        
                        log.info('monthly thread_execute %s employee of timesheet %s' % (len(emp_ts_ids),timesheet_id))
                        number_of_record += len(emp_ts_ids)
                        mass_status_pool.write(t_cr, uid, [mass_status_id], {'number_of_record': number_of_record})
                        t_cr.commit()
                        
                        #Loop for each received employee timesheet
                        for emp_ts in emp_ts_obj.browse(cr, uid, emp_ts_ids, fields_process=['employee_id', 'effect_to', 'effect_from'], context=context):
                            
                            auto_break_thread_monthly_gen = parameter_obj.get_param(cr, uid, 'vhr_timesheet_auto_break_thread_monthly_gen') or ''
                            try:
                                auto_break_thread_monthly_gen = int(auto_break_thread_monthly_gen)
                            except:
                                auto_break_thread_monthly_gen = False
                            if auto_break_thread_monthly_gen:
                                break
                            #Carefull with from_date when search in Working Record
                            from_date = ts_detail_from_date
                            to_date = ts_detail_to_date
                            employee_id = emp_ts.employee_id and emp_ts.employee_id.id or None
                            employee_code = emp_ts.employee_id and emp_ts.employee_id.code or ''
                            department_id = emp_ts.employee_id and emp_ts.employee_id.department_id \
                                            and emp_ts.employee_id.department_id.id or False
                            # com_id = emp_ts.company_id and emp_ts.company_id.id or None
                            parking_coef = 0
                            meal_coef = 0

                            # check monthly is in sent or approve then ignore
                            monthly_ids = ts_monthly_obj.search(cr, uid, [ ('employee_id', '=', employee_id),
                                                                            ('year', '=', year),
                                                                            ('month', '=', month),
                                                                            ('state', 'in', ('sent', 'approve')),
                                                                            ('timesheet_id', '=', timesheet_id)
                                                                        ], limit=1, context=context)
                            if monthly_ids:
                                continue
                            is_meal = 0
                            is_parking = 0
                            #Choose range date timesheet effect in month-year
                            # check employee_timesheet is effect in timesheet period if not change it!
                            #function compare_day(day1,day2) = date(day2)-date(day1)
                            if emp_ts.effect_to and self.compare_day(emp_ts.effect_to, to_date) >0:
                                to_date = emp_ts.effect_to
                            if self.compare_day(from_date ,emp_ts.effect_from) >0:
                                from_date = emp_ts.effect_from
                                
                            
                            date_range_last_payment = []
                            #If is_last_payment = True, only gen for employee have termination in month - year, and limit date_range
                            #Search working record with change form dismiss in timesheet detail
                            dismiss_wr_ids = wr_obj.search(cr, uid, [('employee_id','=',employee_id),
                                                                     '|',('active','=',True),('active','=',False),
                                                                     ('state', 'in', (False, 'finish')),
                                                                     ('effect_from','>=',ts_detail_from_date),
                                                                     ('effect_from','<=', ts_detail_to_date),
                                                                     ('change_form_ids','in', change_form_ids)], order="effect_from asc")
                            if dismiss_wr_ids:
                                dismiss_wrs = wr_obj.read(cr, uid, dismiss_wr_ids, ['effect_from'])
                                test_from_date = from_date
                                test_to_date = to_date
                                for dismiss_wr in dismiss_wrs:
                                    date_end_working = dismiss_wr.get('effect_from')
                                    
                                    if self.check_in_date_range(date_end_working, test_from_date, test_to_date):#date_end_working in date_range (from_date,to_date)
                                        date_range_last_payment.append( [test_from_date, date_end_working])
                                        
                                        test_from_date = datetime.strptime(date_end_working, DEFAULT_SERVER_DATE_FORMAT) + relativedelta(days=1)
                                        test_from_date = test_from_date.strftime(DEFAULT_SERVER_DATE_FORMAT)
                                        
                                        if is_last_payment:
                                            to_date = date_end_working
                                    elif len(dismiss_wr_ids) == 1 and self.compare_day(date_end_working, test_from_date) > 0:#from_date > date_end_working
                                        if is_last_payment:
                                            to_date = date_end_working  #Trick to get date_range = []
                            
                            elif is_last_payment:
                                #If dont have terminate between from_date and to_date, and is_last_payment=True, move to next employee timesheet
                                continue
                                
                            #Check if employee work in office support meal,parking
                            # find all working record effect in this date range
                            #Search in Working record before one day, because on date effect_from of WR have dismiss change form, employee still work
                            one_day_before_from_date = datetime.strptime(from_date, DEFAULT_SERVER_DATE_FORMAT) - relativedelta(days=1)
                            one_day_before_from_date  = one_day_before_from_date.strftime(DEFAULT_SERVER_DATE_FORMAT)
                            wr_domain = [('employee_id', '=', employee_id),
                                         ('state', 'in', (False, 'finish')),
                                         # ('company_id', '=', com_id),
                                         '|', ('active', '=', False),
                                         ('active', '=', True),
                                         ('effect_from', '<=', to_date), '|', ('effect_to', '>=', one_day_before_from_date),
                                         ('effect_to', '=', False)]
                            if change_form_ids:
                                for change_form_id in change_form_ids:
                                    wr_domain.append(('change_form_ids', '!=', change_form_id))

                            wr_ids = wr_obj.search(cr, uid, wr_domain)

                            # check for some case
                            if not wr_ids:
                                continue
                            
                            range_date_parking = []
                            range_date_meal = []
                            
                            for wr in wr_obj.browse(cr, uid, wr_ids):
                                if wr.office_id_new:
                                    if wr.office_id_new.is_parking:
                                        range_date_parking.append((wr.effect_from, wr.effect_to))
                                if wr.salary_setting_id_new:
                                    if wr.salary_setting_id_new.is_meal:
                                        range_date_meal.append((wr.effect_from, wr.effect_to))
                            try:
                                #Find Working Schedule effect in timesheet day
                                ws_emp_ids = ws_emp_obj.search(cr, uid,
                                                               [('employee_id', '=', employee_id),
                                                                # ('company_id', '=', com_id),
                                                                '|',
                                                                ('active', '=', False),
                                                                ('active', '=', True),
                                                                ('effect_from', '<=', to_date),
                                                                '|', ('effect_to', '>=', from_date),
                                                                ('effect_to', '=', False)])
                                if ws_emp_ids:
                                    for ws_emp in ws_emp_obj.browse(cr, uid, ws_emp_ids, context=context):
                                        ws_emp_effect_from = ws_emp.effect_from
                                        ws_emp_effect_to = ws_emp.effect_to
                                        ts_working_group_code = ws_emp.ts_working_group_id and ws_emp.ts_working_group_id.code or ''
                                        if not ws_emp_effect_to:
                                            ws_emp_effect_to = to_date
                                        #Get range date of same timesheet - working schedule
                                        date_range = [date for date in self.date_range(from_date, to_date) if
                                                      date in self.date_range(ws_emp_effect_from, ws_emp_effect_to)]
                                        
                                        #Find active working date from employee instance
                                        if date_range:
                                            instance_obj = self.pool.get('vhr.employee.instance')
                                            #if date_range in (date_start,date_end) of instance bypass
                                            instance_ids = instance_obj.search(cr, uid, [('employee_id','=',employee_id),
                                                                                            ('date_start','<=',date_range[0]),
                                                                                                        '|',('date_end','>=',date_range[0]),
                                                                                                            ('date_end','=',False),
                                                                                            ('date_start','<=',date_range[-1]),
                                                                                                        '|',('date_end','>=',date_range[-1]),
                                                                                                            ('date_end','=',False),
                                                                                        ])
                                            if not instance_ids:
                                                instance_ids = instance_obj.search(cr, uid, [('employee_id','=',employee_id),
                                                                                            '|',
                                                                                                '&',('date_start','<=',date_range[0]),
                                                                                                            '|',('date_end','>=',date_range[0]),
                                                                                                                ('date_end','=',False),
                                                                                                '&',('date_start','<=',date_range[-1]),
                                                                                                            '|',('date_end','>=',date_range[-1]),
                                                                                                                ('date_end','=',False),
                                                                                            ])
                                                if instance_ids:
                                                    instances = instance_obj.read(cr, uid, instance_ids, ['date_start','date_end'])
                                                    couple_dates = [(a.get('date_start'), a.get('date_end') or to_date)  for a in instances]
                                                    new_date_range = []
                                                    for couple_date in couple_dates:
                                                        tmp_date_range = [date for date in date_range if self.check_in_date_range(date, couple_date[0],couple_date[1])]
                                                        new_date_range.extend(tmp_date_range)
                                                    date_range = new_date_range
                                                else:
                                                    date_range = []
                                            
                                        # find all previous
                                        unlink_monthly_ids = ts_monthly_obj.search(cr, uid, [
                                            ('employee_id', '=', employee_id),
                                            ('date', 'not in', date_range),
                                            ('year', '=', year), ('month', '=', month),
                                            ('timesheet_id', '=', timesheet_id)
                                        ], context=context)
                                        
                                        #Dont delete monthly record, we have just created
                                        unlink_monthly_ids = list(set(unlink_monthly_ids).difference(set(create_ids)))

                                        for date in date_range:
                                            ws_id = ws_emp.ws_id and ws_emp.ws_id.id or False
                                            monthly_ids = ts_monthly_obj.search(cr, uid, [
                                                ('employee_id', '=', employee_id),
                                                ('date', '=', date),
                                                ('timesheet_id', '=', timesheet_id)
                                            ], context=context)
                                            
                                            val = {'employee_id': employee_id,
                                                   'employee_code': employee_code,
                                                   'timesheet_id': timesheet_id,
                                                   'department_id': department_id,
                                                   'timesheet_detail_id': ts_detail_ids[0],
                                                   'ts_ws_employee_id': ws_emp.id,
                                                   'working_schedule_id': ws_id,
                                                   'state': 'draft',
                                                   'month': month,
                                                   'date': date,
                                                   'year': year}
                                            
                                            #If date in date_range_last_payment, check is_last_payment = True
                                            for range in date_range_last_payment:
                                                if range and self.check_in_date_range(date, range[0], range[1]):
                                                    val['is_last_payment'] = True
                                                    val['termination_date'] = range[1]
                                                    break
                                                
                                            if ws_emp.ts_working_group_id:
                                                val['ws_group_id'] = ws_emp.ts_working_group_id.id
                                            
                                            #Search working schedule detail on date of Working SChedule
                                            ws_detail_ids = ws_detail_obj.search(cr, uid,
                                                                                 [('ws_id', '=', ws_id),
                                                                                  ('date', '=', date),
                                                                                  ('shift_id','!=',False)],
                                                                                 context=context)
                                            coef = 0
                                            
                                            is_meal = False
                                            is_parking = False
                                            
                                            for range in range_date_parking:
                                                if range and self.check_in_date_range(date, range[0], range[1]):
                                                    is_parking = True
                                                    break
                                            
                                            for range in range_date_meal:
                                                if range and self.check_in_date_range(date, range[0], range[1]):
                                                    is_meal = True
                                                    break
                                            
                                            
#                                            old_code when have mapping working schedule-working_group(comment to view in future)
#                                            is_ct_bt = self.pool.get('vhr.ts.working.schedule.working.group').search(cr, uid, 
#                                                  [('ts_working_schedule_id', '=', ws_id),('ts_working_group_id.code', 'in', ct_bt_working_group_code)])
                                            is_ct_bt = ts_working_group_code in ct_bt_working_group_code
                                            if ws_detail_ids:
                                                ws_detail = ws_detail_obj.browse(cr, uid, ws_detail_ids[0],
                                                                                 fields_process=['shift_id', 'type_id'])
                                                #when employee belong to Working Group chính thức, bình thường và CTV vp and work in public holiday:coef = 1
                                                if ws_detail.type_id and is_ct_bt:
                                                    val['type_id'] = ws_detail.type_id.id
                                                    val['coef'] = 1
                                                    create_id = ts_monthly_obj.create(cr, uid, val, context=context)
                                                    create_ids.append(create_id)
                                                    continue
                                                
                                                #Search if employee have leave request on date
                                                shift_id = ws_detail.shift_id and ws_detail.shift_id.id or False
                                                sql = """
                                                    SELECT
                                                      A.id
                                                    FROM vhr_holiday_line AS A
                                                      INNER JOIN (SELECT
                                                                    id
                                                                  FROM hr_holidays
                                                                  WHERE state in  ('confirm','validate')
                                                                        AND employee_id = %s) AS B
                                                        ON A.holiday_id = B.id
                                                    WHERE A.date = '%s'
                                                """ % (employee_id, date)
                                                cr.execute(sql)
                                                holiday_line_ids = cr.fetchall()
                                                holiday_line_ids = [holiday_line_id[0] for holiday_line_id in
                                                                    holiday_line_ids]
                                                
                                                sql = """
                                                    SELECT
                                                      A.id
                                                    FROM vhr_holiday_line AS A
                                                      INNER JOIN (SELECT
                                                                    id
                                                                  FROM hr_holidays
                                                                  WHERE state = 'confirm'
                                                                        AND employee_id = %s) AS B
                                                        ON A.holiday_id = B.id
                                                    WHERE A.date = '%s'
                                                """ % (employee_id, date)
                                                cr.execute(sql)
                                                not_fin_holiday_line_ids = cr.fetchall()
                                                not_fin_holiday_line_ids = [holiday_line_id[0] for holiday_line_id in
                                                                    not_fin_holiday_line_ids]
                                                
                                                if shift_id:
                                                    if is_meal:
                                                        #So tien com nhan dc trong 1 ngay bang loai ngay lam viec cua ca trong ngay
                                                        #neu lam vao ngay co ca lam viec co type = 0.5 ngay, thi chi dc nhan 0.5 ngay tien an
                                                        #neu lam vao ngay co ca lamf viec co type =  1 ngay, thi nhan dc 1 ngay tien an
                                                        meal_coef =  ws_detail.shift_id.type_workday_id.coef
                                                    if is_parking:
                                                        parking_coef = 1
                                                    val['name'] = ws_detail.shift_id.code
                                                    val['shift_id'] = shift_id
                                                    val['shift_name'] = ws_detail.shift_id.code
                                                    holidays = holiday_line_obj.browse(cr, uid,
                                                                                       holiday_line_ids,
                                                                                       fields_process=['number_of_days_temp',
                                                                                                       'holiday_status_id'])
                                                    #Get he so luong cua ngay tu ca 
                                                    coef = ws_detail.shift_id.type_workday_id.coef
                                                    if len(holiday_line_ids) == 1:
                                                        val['holiday_line_id'] = holiday_line_ids[0]
                                                            
                                                        name = holidays[0].holiday_id.holiday_status_id.code
                                                        if holidays[0].number_of_days_temp == 1:
                                                            if holidays[0].holiday_id.holiday_status_id.coefsal == 1:
                                                                coef = 1
                                                            else:
                                                                coef = 0
                                                        else:
                                                            #Take leave request on half of day
                                                            #neu nghi co luong nua ngay, thi coef = ws_detail.shift_id.type_workday_id.coef
                                                            #neu nghi ko luong nua ngay, thi coef = ws_detail.shift_id.type_workday_id.coef - 0.5
                                                            name = holidays[0].holiday_id.holiday_status_id.code + '/2'
                                                            if not holidays[0].holiday_id.holiday_status_id.coefsal == 1:
                                                                coef = coef - 0.5
                                                        if is_meal:
                                                            meal_coef = ws_detail.shift_id.type_workday_id.coef - holidays[0].number_of_days_temp
                                                        else:
                                                            meal_coef = 0
                                                        if is_parking and holidays[0].number_of_days_temp != 1:
                                                            parking_coef = 1
                                                        if holidays[0].number_of_days_temp == 1:
                                                            parking_coef = 0
#                                                         val['name'] = name
                                                        
                                                        if holiday_line_ids[0] in not_fin_holiday_line_ids:
                                                            val['holiday_name'] = name
                                                        else:
                                                            val['name'] = name
                                                    elif len(holiday_line_ids) == 2:
                                                        #Why delete old monthly_ids when len(monthly_ids) >2
                                                        if monthly_ids and len(monthly_ids) > 2:
                                                            unlink_monthly_ids.extend(monthly_ids[2:])
                                                        parking_coef = 0
                                                        if holidays[0].number_of_days_temp == 0.5:
                                                            meal_coef = 0
                                                            parking_coef = 0
                                                            name = holidays[0].holiday_id.holiday_status_id.code + '/2'
                                                            if holidays[0].holiday_id.holiday_status_id.coefsal == 1:
                                                                coef = 1 * holidays[0].number_of_days_temp
                                                            else:
                                                                coef = 0
                                                            vals = {}
                                                            vals.update(val)
                                                            vals['holiday_line_id'] = holiday_line_ids[0]
                                                            vals['coef'] = coef
                                                            vals['meal_coef'] = meal_coef
                                                            vals['parking_coef'] = parking_coef
#                                                             vals['name'] = name
                                                            if holiday_line_ids[0] in not_fin_holiday_line_ids:
                                                                vals['holiday_name'] = name
                                                            else:
                                                                vals['name'] = name
                                                                
                                                            if not monthly_ids:
                                                                create_id = ts_monthly_obj.create(cr, uid, vals,
                                                                                                  context=context)
                                                                create_ids.append(create_id)
                                                            else:
                                                                ts_monthly_obj.write(cr, uid, [monthly_ids[0]],
                                                                                     vals, context=context)
                                                                create_ids.extend(monthly_ids)
                                                        if holidays[1].number_of_days_temp == 0.5:
                                                            name = holidays[1].holiday_id.holiday_status_id.code + '/2'
                                                            if holidays[1].holiday_id.holiday_status_id.coefsal == 1:
                                                                coef = 1 * holidays[1].number_of_days_temp
                                                            else:
                                                                coef = 0
                                                            vals = {}
                                                            vals.update(val)
                                                            vals['holiday_line_id'] = holiday_line_ids[1]
                                                            vals['shift_id'] = shift_id
                                                            vals['coef'] = coef
                                                            vals['meal_coef'] = meal_coef
                                                            vals['parking_coef'] = parking_coef
#                                                             vals['name'] = name
                                                            if holiday_line_ids[1] in not_fin_holiday_line_ids:
                                                                vals['holiday_name'] = name
                                                            else:
                                                                vals['name'] = name

                                                            if not monthly_ids or len(monthly_ids) < 2:
                                                                create_id = ts_monthly_obj.create(cr, uid, vals,
                                                                                                  context=context)
                                                                create_ids.append(create_id)
                                                            else:
                                                                ts_monthly_obj.write(cr, uid, [monthly_ids[1]],
                                                                                     vals, context=context)
                                                                create_ids.extend(monthly_ids)
                                                            continue
                                                        
                                                    val['parking_coef'] = parking_coef
                                                    val['coef'] = coef
                                                    val['meal_coef'] = meal_coef
                                                    if len(monthly_ids) > 1:
                                                        unlink_monthly_ids.extend(monthly_ids[1:])
                                                    cr.commit()
                                                    if not monthly_ids:
                                                        create_id = ts_monthly_obj.create(cr, uid, val, context=context)
                                                        create_ids.append(create_id)
                                                    else:
                                                        ts_monthly_obj.write(cr, uid, monthly_ids, val, context=context)
                                                        create_ids.extend(monthly_ids)
                                            #Commit after each date
                                            cr.commit()
                                    if unlink_monthly_ids:
                                        ts_monthly_obj.unlink(cr, uid, unlink_monthly_ids, context=context)

                                else:
                                    error_item = 'Not found any working schedule for employee'
                                    list_error.append((employee_id, error_item))
                            except Exception, e:
                                log.exception(e)
                                try:
                                    error_item = e.message
                                except:
                                    error_item = ""
                                list_error.append((employee_id, error_item))

                            if error_item and list_error:
                                list_employee_error = [item[0] for item in list_error if item]
                                mass_status_pool.write(t_cr, uid, [mass_status_id],
                                                       {'state': 'error',
                                                        'number_of_fail_record': len(set(list_employee_error))})
                                mass_status_detail_pool.create(t_cr, uid, {'mass_status_id': mass_status_id,
                                                                           'employee_id': list_error[-1][0],
                                                                           'message': list_error[-1][1],
                                                                           'status': 'fail'})
                                cr.rollback()
                                log.info('monthly thread_execute mass_status_detail_pool %s!' % list_error)
                            else:
                                # if dont have error, then commit
                                cr.commit()
                                # write log
                                list_employee_count.append(employee_id)
                                if create_ids:
                                    list_employee_execute.append(employee_id)

                                    mass_status_detail_pool.create(t_cr, uid, {'mass_status_id': mass_status_id,
                                                                               'employee_id': employee_id,
                                                                               'message': '',
                                                                               'status': 'success'})

                                mass_status_pool.write(t_cr, uid, [mass_status_id],
                                                       {'number_of_execute_record': len(set(list_employee_execute))})
                            t_cr.commit()
            if list_error:
                mass_status_pool.write(t_cr, uid, [mass_status_id],
                                       {'state': 'error', 'number_of_fail_record': len(list_error)})

            else:
                mass_status_pool.write(t_cr, uid, [mass_status_id],
                                       {'state': 'finish',
                                        'number_of_execute_record': len(set(list_employee_execute))})
        except Exception as e:
            log.exception(e)
            try:
                error_message = e.message
                if not error_message:
                    error_message = e.value
            except:
                error_message = ""

            # If have error with first try, then rollback to clear all created holiday
            cr.rollback()
            if create_ids:
                pool_obj.write(cr, uid, create_ids, {'state': 'draft'}, context)
                pool_obj.unlink(cr, uid, create_ids, context)
            log.info('monthly thread_execute rollback()!')

        if error_message:
            mass_status_pool.write(t_cr, uid, [mass_status_id], {'state': 'fail', 'error_message': error_message})

        cr.commit()
        cr.close()

        t_cr.commit()
        t_cr.close()
        log.info('monthly thread_execute end()')
        return True

    def action_ts_monthly_gen(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        emp_id, list_timesheet_ids, month, year, admin_id, run_sql, is_last_payment, list_lock_emp_ids = self.validate_input(cr, uid, ids, context)
        
        if list_lock_emp_ids:
            raise osv.except_osv('Validation Error !', 'You can not generate timesheet detail because of lock employees !')
        
        today = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        #If close_date < now(), do not allow to generate timesheet detail
        if month and year:
            period_ids = self.pool.get('vhr.ts.timesheet.period').search(cr, uid, [('month','=',month),
                                                                                   ('year','=', year)])
            if period_ids:
                period = self.pool.get('vhr.ts.timesheet.period').read(cr, uid, period_ids[0], ['close_date'])
                close_date = period.get('close_date', False)
                if close_date:
                    close_date = datetime.strptime(close_date, DEFAULT_SERVER_DATE_FORMAT)
                    now = datetime.strptime(today, DEFAULT_SERVER_DATETIME_FORMAT) 
                    
                    if close_date < now:
                        raise osv.except_osv(_('Validation Error !'), _('Timesheet has blocked. You cannot generate, please contact C&B for more information!'))
        
        log.info('action_ts_monthly_gen start() %s' % datetime.now())

        if not context:
            context = {}
            
        
        if list_timesheet_ids:
            self.pool.get('vhr.ts.timesheet').write(cr, SUPERUSER_ID, list_timesheet_ids, {"latest_generation": today})
            
        if run_sql:
            try:

                if not list_timesheet_ids:
                    list_timesheet_ids = [0]
                
                sql = "SELECT * FROM fn_ts_monthly_ins_up({0}, {1}, {2}, {3}, '{4}', {5}, {6});".format(
                    admin_id or 'null', uid, month, year, ','.join(str(i) for i in list_timesheet_ids),
                    emp_id or 'null', is_last_payment)
                cr.execute(sql)
                cr.commit()
                
#                 for timesheet_id in list_timesheet_ids:
#                     thread.start_new_thread(
#                         vhr_ts_monthly_gen.run_sql_gen_monthly,
#                         (self,cr, uid, month, year, admin_id, [timesheet_id], emp_id, is_last_payment, context))
                
            except Exception as e:
                log.exception(e)
                log.info('Error: SQL Function fn_ts_monthly_ins_up generate monthly timesheet detail is unsuccessful. Please check it again!')                
                raise osv.except_osv('Validation Error !', 'Timesheet detail generation is not successful.\n Please try again or contact to administrator !')
        else:
            try:
#                 context['mass_status_info'] = 'Detail Status %s/%s.' % (month, year)
                mass_status_id = self.create_mass_status(cr, uid, 'vhr.ts.monthly', context)
                pool_obj = self.pool.get('vhr.ts.monthly')
                try:
                    thread.start_new_thread(vhr_ts_monthly_gen.monthly_thread_execute, (
                        self, cr, uid, ids, mass_status_id, pool_obj, emp_id, list_timesheet_ids, month, year, is_last_payment, context))
                except Exception as e:
                    log.exception(e)
                    log.info('Error: Unable to start thread execute action_ts_monthly_gen')
                
                mod_obj = self.pool.get('ir.model.data')
                act_obj = self.pool.get('ir.actions.act_window')
                result_context = {}
                if context is None:
                    context = {}
                result = mod_obj.get_object_reference(cr, uid, 'vhr_timesheet', 'act_tracking_vhr_ts_monthly_gen')
                id = result and result[1] or False
                result = act_obj.read(cr, uid, [id], context=context)[0]
                
                result['res_id'] = mass_status_id
                result['view_type'] = 'form'
                result['view_mode'] = 'form,tree'
                result['views'].sort()
                return result
    
            except Exception as e:
                log.exception(e)
                log.info('Error: Unable to start thread execute action_ts_monthly_gen')
                raise osv.except_osv('Validation Error !', 'Timesheet detail generation is not successful.\n Please try again or contact to administrator !')

#         ir_model_pool = self.pool.get('ir.model.data')
#         view_vhr_ts_monthly_search = ir_model_pool.get_object_reference(cr, uid, 'vhr_timesheet','view_vhr_ts_monthly_search')
#         view_vhr_ts_monthly_search = view_vhr_ts_monthly_search and view_vhr_ts_monthly_search[1]
#         view_vhr_ts_monthly_monthly_calendar = ir_model_pool.get_object_reference(cr, uid, 'vhr_timesheet',
#                                                                                   'view_vhr_ts_monthly_monthly_calendar')
#         view_vhr_ts_monthly_monthly_calendar = view_vhr_ts_monthly_monthly_calendar and \
#                                                view_vhr_ts_monthly_monthly_calendar[1] or False
        domain = [('month', '=', month), ('year', '=', year)]
#         domain.append(('timesheet_id', 'in', list_timesheet_ids))
        #tuannh3: Khong su dung domain de visible voi user
        context.update({
                        'search_default_draft': 1,
                        })
        if emp_id:
            context.update({'search_default_employee_id': emp_id})
        if admin_id:
            context.update({'search_default_admin_id': admin_id})
        if list_timesheet_ids and list_timesheet_ids != [0]:
            context.update({'vhr_timesheet_ids': list_timesheet_ids,
                            'search_default_filter_timesheet': 1})
#         return {
#             'name': _('Detail!'),
#             'view_type': 'form',
#             'view_mode': 'monthly_calendar',
#             'res_model': 'vhr.ts.monthly',
#             'domain': domain,
#             'view_ids': (0, 0, {'sequence': 1,
#                                 'view_mode': 'monthly_calendar',
#                                 'view_id': view_vhr_ts_monthly_monthly_calendar}),
#             'search_view_id': view_vhr_ts_monthly_search,
#             'context': context,
#             'type': 'ir.actions.act_window',
#             'target': 'current'
#         }
        
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        result_context = {}
        result = mod_obj.get_object_reference(cr, uid, 'vhr_timesheet', 'act_vhr_ts_monthly')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        
#         result['view_type'] = 'form'
#         result['view_mode'] = 'monthly_calendar'
#         result['views'].sort()
        result['context'] = context
        result['domain'] = domain
        return result
    
    
#     def run_sql_gen_monthly(self, cr, uid, month, year, admin_id, list_timesheet_ids, emp_id, is_last_payment, context):
#         _pool = ConnectionPool(int(tools.config['db_maxconn']))
#         tcr = Cursor(_pool, cr.dbname, True)
#         sql = "SELECT * FROM fn_ts_monthly_ins_up({0}, {1}, {2}, {3}, '{4}', {5}, {6});".format(
#             admin_id or 'null', uid, month, year, ','.join(str(i) for i in list_timesheet_ids),
#             emp_id or 'null', is_last_payment)
#         
# #         sql = """
# #                 SELECT * FROM fn_ts_monthly_ins_up(null, 2270, 9, 2016, '%s', null, False);
# #               """
#         tcr.execute(sql)
#         tcr.commit()
#         tcr.close()
        
    def create_mass_status(self, cr, uid, model, context=None):
        if not context:
            context = {}
            
        mass_status_id = False
        if model:
            _pool = ConnectionPool(int(tools.config['db_maxconn']))
            tcr = Cursor(_pool, cr.dbname, True)
            
            vals = {'state': 'new'}
            employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', uid)], context={'search_all_employee': True})
            if employee_ids:
                vals['requester_id'] = employee_ids[0]
            module_ids = self.pool.get('ir.module.module').search(cr, uid, [('name', '=', 'vhr_timesheet')])
            if module_ids:
                vals['module_id'] = module_ids[0]
    
            model_ids = self.pool.get('ir.model').search(cr, uid, [('model', '=', model)])
            if model_ids:
                vals['model_id'] = model_ids[0]
            
            if context.get('mass_status_info', False):
                vals['mass_status_info'] = context['mass_status_info']
                
            mass_status_id = self.pool.get('vhr.mass.status').create(tcr, uid, vals)
            tcr.commit()
            tcr.close()
        return mass_status_id

    def action_ts_summary_gen(self, cr, uid, ids, context=None):

        if context is None:
            context = {}
        context.update({'timesheet_summary_gen': True})
        emp_id, list_timesheet_ids, month, year, admin_id, run_sql, is_last_payment, list_lock_emp_ids = self.validate_input(cr, uid, ids, context)

        log.info('action_ts_summary_gen start() %s' % datetime.now())

        if not context:
            context = {}
        if run_sql:
            try:
                sql = "SELECT * FROM fn_ts_emp_ts_summary_ins_up({0}, {1}, {2}, {3}, '{4}', {5});".format(
                    admin_id or 'null', uid, month, year, ','.join(str(i) for i in list_timesheet_ids),
                    emp_id or 'null')
                cr.execute(sql)
                cr.commit()
            except Exception as e:
                log.exception(e)
                log.info('Error: SQL Function fn_ts_emp_ts_summary_ins_up generate monthly timesheet summary is unsuccessful. Please check it again!')
                raise osv.except_osv('Validation Error !', 'Timesheet summary generation is not successful.\n Please try again or contact to administrator !')
            context.update({
                            'search_default_month': month,
                            'search_default_year': year
                            })
            if emp_id:
                context.update({'search_default_employee_id': emp_id})
            if list_timesheet_ids and list_timesheet_ids != [0]:
                context.update({'vhr_timesheet_ids': list_timesheet_ids,
                                'search_default_filter_timesheet': 1})
            
            mod_obj = self.pool.get('ir.model.data')
            act_obj = self.pool.get('ir.actions.act_window')
            result_context = {}
            if context is None:
                context = {}
            result = mod_obj.get_object_reference(cr, uid, 'vhr_timesheet', 'act_vhr_employee_timesheet_summary')
            id = result and result[1] or False
            result = act_obj.read(cr, uid, [id], context=context)[0]
            
            result['view_type'] = 'form'
            result['view_mode'] = 'tree'
            result['context'] = context
            result['auto_refresh'] = True
            return result

        try:
#             context['mass_status_info'] = _('Summary Status %s/%s.' % (month, year))
            mass_status_id = self.create_mass_status(cr, uid, 'vhr.employee.timesheet.summary', context)
            pool_obj = self.pool.get('vhr.employee.timesheet.summary')

            thread.start_new_thread(vhr_ts_monthly_gen.summary_thread_execute, (
                self, cr, uid, ids, mass_status_id, pool_obj, emp_id, list_timesheet_ids, month, year, context))
        except Exception as e:
            log.exception(e)
            log.info('Error: Unable to start thread execute action_ts_summary_gen')
            raise osv.except_osv('Validation Error !', 'Timesheet summary generation is not successful.\n Please try again or contact to administrator !')

        
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        result_context = {}
        result = mod_obj.get_object_reference(cr, uid, 'vhr_timesheet', 'act_vhr_employee_timesheet_summary')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        
        result['res_id'] = mass_status_id
        result['view_type'] = 'form'
        result['view_mode'] = 'form,tree'
        result['views'].sort()
        return result

    def summary_thread_execute(self, cr, uid, ids, mass_status_id, pool_obj, emp_id, list_timesheet_ids, month, year,
                               context=None):
        """
        Tạo ra các dòng summary timesheet cho employee, mỗi nhân viên sẽ có 1 dòng, nếu trong chu kỳ công, nhân viên này có nghỉ việc rồi đi làm lại
        thì số dòng được tạo ra của mỗi nhân viên tương ứng với số employee_instance hiệu lực trong chu kỳ công(vd nghỉ rồi vô làm thì sẽ có 2 dòng)
        """
        log.info('summary_thread_execute start()')
        mass_status_pool = self.pool.get('vhr.mass.status')
        mass_status_detail_pool = self.pool.get('vhr.mass.status.detail')

        _pool = ConnectionPool(int(tools.config['db_maxconn']))
        # cr used to create WR
        cr = Cursor(_pool, cr.dbname, True)
        # t_cr used to create/write Mass Status/ Mass Status Detail
        t_cr = Cursor(_pool, cr.dbname, True)  # Thread's cursor

        # clear old thread in cache to free memory
        reload(sys)
        create_ids = []
        error_message = ""
        list_error = []
        try:
            mass_status_pool.write(t_cr, uid, [mass_status_id], {'state': 'running',
                                                                 'number_of_record': 0,
                                                                 'number_of_execute_record': 0,
                                                                 'number_of_fail_record': 0})
            t_cr.commit()
            if list_timesheet_ids and month and year:
                ws_emp_obj = self.pool.get('vhr.ts.ws.employee')
                ws_detail_obj = self.pool.get('vhr.ts.ws.detail')
                parameter_obj = self.pool.get('ir.config_parameter')
                public_holidays_obj = self.pool.get('vhr.public.holidays')
                working_shift_obj = self.pool.get('vhr.ts.working.shift')
                wr_obj = self.pool.get('vhr.working.record')
                instance_obj = self.pool.get('vhr.employee.instance')
                holiday_obj = self.pool.get('hr.holidays')
                
                maternity_leave_code = parameter_obj.get_param(cr, uid, 'ts.maternity.leave.group.code') or ''
                maternity_leave_code = maternity_leave_code.split(',')
                st_kt_code = parameter_obj.get_param(cr, uid, 'ts.leave.type.st.kt.leave.group.code') or ''
                st_kt_code = st_kt_code.split(',')
                sick_leave_long_code = parameter_obj.get_param(cr, uid, 'ts.leave.type.long.term.sick.leave.group.code') or '' 
                sick_leave_long_code = sick_leave_long_code.split( ',')
                sick_leave_short_code = parameter_obj.get_param(cr, uid, 'ts.leave.type.short.term.sick.leave.group.code') or ''
                sick_leave_short_code = sick_leave_short_code.split(',')
                relax_leave_code = parameter_obj.get_param(cr, uid, 'ts.leave.type.relax.leave.group.code') or '' 
                relax_leave_code = relax_leave_code.split(',')
                other_leave_code = parameter_obj.get_param(cr, uid, 'ts.leave.type.other.leave.group.code') or '' 
                other_leave_code = other_leave_code.split(',')
                
                
                leavetype_group_with_public_date_not_add_to_working_date_code = parameter_obj.get_param(cr, uid, 'vhr_timesheet_leave_type_group_not_add_to_total_working_days') or '' 
                leavetype_group_with_public_date_not_add_to_working_date_code = leavetype_group_with_public_date_not_add_to_working_date_code.split(',')
                
                #Get Working Group Code of WGroup chính thức, bình thường và CTV vp
                ct_bt_working_group_code = parameter_obj.get_param(cr, uid, 'ts.working.group.ct.bt') or ''
                ct_bt_working_group_code = ct_bt_working_group_code.split(',')
                
                change_form_terminated_code = parameter_obj.get_param(cr, uid, 'vhr_master_data_dismiss_change_form_code').split(',')
                dismiss_change_form_ids = self.pool.get('vhr.change.form').search(cr, uid, [('code', 'in', change_form_terminated_code)],
                                                         context=context)
                
                official_working_shift_hours = 0
                official_working_shift_code = parameter_obj.get_param(cr, uid, 'official_working_shift') or ''
                official_working_shift_code = official_working_shift_code.split(',')
                shift_ids = working_shift_obj.search(cr, uid, [('code','in',official_working_shift_code)])
                if shift_ids:
                    shift = working_shift_obj.read(cr, uid, shift_ids[0], ['work_hour'])
                    official_working_shift_hours = shift.get('work_hour')
                else:
                    mass_status_pool.write(t_cr, uid, [mass_status_id],
                                   {'state': 'error', 'error_message': 'Can not find any working shift "Ca VP"'})
                    cr.commit()
                    cr.close()
            
                    t_cr.commit()
                    t_cr.close()
                    log.info('summary_thread_execute end()')
                    return True

                timesheet_summary_obj = self.pool.get('vhr.employee.timesheet.summary')
                ts_monthly_obj = self.pool.get('vhr.ts.monthly')
                
                #Get all approved monthly timesheet in month-year
                sql = """
                    SELECT employee_id, id, is_last_payment, termination_date
                    FROM vhr_ts_monthly
                    WHERE month = {0} AND year = {1}
                          AND timesheet_id IN {2}
                          AND state = 'approve'
                """.format(month, year, str(tuple(list_timesheet_ids)).replace(',)', ')'))
                if emp_id:
                    sql += ' AND employee_id = %s' % emp_id
                cr.execute(sql)
                monthly_data = cr.fetchall()
                ts_monthly_ids = [item[1] for item in monthly_data if item]
                employee_ids = [employee_id[0] for employee_id in monthly_data if employee_id]
                employee_ids = list(set(employee_ids))
                
                number_of_record = 0
                number_of_execute_record = 0
                number_of_record += len(employee_ids)
                #Loop for each employee
                for employee_id in employee_ids:
                    
                    auto_break_thread_monthly_gen = parameter_obj.get_param(cr, uid, 'vhr_timesheet_auto_break_thread_monthly_gen') or ''
                    try:
                        auto_break_thread_monthly_gen = int(auto_break_thread_monthly_gen)
                    except:
                        auto_break_thread_monthly_gen = False
                    if auto_break_thread_monthly_gen:
                        break
                    
                    number_of_execute_record += 1
                    mass_status_pool.write(t_cr, uid, [mass_status_id], {'number_of_record': number_of_record,
                                                                         'number_of_execute_record': number_of_execute_record})
                    
                    #Get monthly record if employee in month - year
                    is_have_last_payment = False
                    ts_monthly_not_last_payment_ids = []
                    ts_monthly_list = []
                    ts_monthly_termination_date = {}
                    for monthly in monthly_data:
                        if monthly[1] and monthly[0] == employee_id:
                            if monthly[2]:
                                if monthly[3] in ts_monthly_termination_date:
                                    ts_monthly_termination_date[monthly[3]].append(monthly[1])
                                else:
                                    ts_monthly_termination_date[monthly[3]] = [monthly[1]]
                                is_have_last_payment = True
                            else:
                                ts_monthly_not_last_payment_ids.append(monthly[1])
                    
                    if ts_monthly_termination_date:
                        for terminate_date in ts_monthly_termination_date:
                            ts_monthly_list.append(ts_monthly_termination_date[terminate_date])
                            
                    if ts_monthly_not_last_payment_ids:
                        ts_monthly_list.append(ts_monthly_not_last_payment_ids)
                    t_cr.commit()
                    
                    index_in_monthly_list = -1
                    for ts_monthly_ids in ts_monthly_list:
                        index_in_monthly_list += 1
                        total_hours_working = 0
                        working_days = 0
                        if ts_monthly_ids:
                
                            ncontext = {'maternity_leave_code':maternity_leave_code,'st_kt_code':st_kt_code,
                                        'sick_leave_long_code':sick_leave_long_code,'sick_leave_short_code':sick_leave_short_code,
                                        'relax_leave_code':relax_leave_code, 'other_leave_code': other_leave_code}
                            
                            #Get data from monthly record
                            full_day_paid, haft_day_unpaid, haft_day_paid, full_day_unpaid, \
                            night_shift_allowance_hours, meal_days, parking_days,\
                            sick_leave_long, sick_leave_short, st_kt_leave, maternity_leave,\
                            relax_leave, other_leave, paid_days, is_last_payment, ts_monthly = self.get_total_usefull_data_from_ts_monthly(cr, uid, ts_monthly_ids, ncontext)
                            
                            total_unpaid_leave = full_day_unpaid + haft_day_unpaid * 0.5
                            total_paid_leave =   full_day_paid   + haft_day_paid * 0.5
                            from_date = ts_monthly.timesheet_detail_id.from_date
                            to_date = ts_monthly.timesheet_detail_id.to_date
                            timesheet_id = ts_monthly.timesheet_detail_id.timesheet_id and ts_monthly.timesheet_detail_id.timesheet_id.id or False
                            termination_date = ts_monthly.termination_date or False
                            
                            
                            date_start_working = False
                            date_end_working = False
                            instance_ids = instance_obj.search(cr, uid, [('employee_id','=',employee_id),
                                                                         ('date_end','=',termination_date)], order='date_start asc')
                            
                            if instance_ids:
                                instance = instance_obj.read(cr, uid, instance_ids[0], ['date_start','date_end'])
                                date_start_working = instance.get('date_start',False) or from_date
                                date_end_working = instance.get('date_end',False) or to_date
                            
                            #If in timesheet detail, employee terminated, and go back to work, we need to separate date_range to check for last payment and not last payment
                            #Last Payment will have date rage:     timesheet_detail_from_date --> date_end_working
                            #Not Last Payment will have date range:date_end_working +1 ---> to_date
                            actual_from_date = from_date
                            actual_to_date  = to_date
                            if date_start_working:
                                if self.compare_day(actual_from_date, date_start_working) > 0:
                                    actual_from_date = date_start_working
                                
                                if self.compare_day(date_end_working, actual_to_date) >0:
                                    actual_to_date = date_end_working
                            
                            #If employee A work from x to y then terminate, go back to work from y to z.
                            #Total working days on period x-y will be count based on active Working Schedule at period x-y
                            #Total working days on period y-z will be count based on active Working Schedule at period y-z
                            context = {}
                            if is_have_last_payment:
                                context = {'actual_from_date':actual_from_date, 'actual_to_date': actual_to_date}
                            #Get total working days between from_date - to_date
                            #Search in Working Schedule Employee to get all Workng Schedule of Employee in period from_date - to_date
                            working_days, total_hours_working, working_schedule_ids, expand_date, working_schedule_dict_time = self.get_total_working_days_of_employee_in_date_range(cr, uid, employee_id, from_date, to_date, context)
                                    
                            
                            #Search for public holiday that employee dont have shift and employee belong to WGroup chính thức, bình thường và CTV vp in date range (26 - 25 next month)
                            public_dates = []
                            public_holiday_ids = public_holidays_obj.search(cr, uid, [('date', '>=', actual_from_date),
                                                                                      ('date','<=',actual_to_date)])
                            if public_holiday_ids:
                                public_holidays = public_holidays_obj.read(cr, uid, public_holiday_ids, ['date'])
                                public_dates = [public['date'] for public in public_holidays]
                            
                            for working_schedule_id in working_schedule_dict_time:
                                working_schedule_from = working_schedule_dict_time[working_schedule_id][0]
                                working_schedule_to = working_schedule_dict_time[working_schedule_id][1]
                                
                                domain = [('date','in',public_dates),
                                       ('date','>=',working_schedule_from),
                                       ('ws_id','=',working_schedule_id),
                                       ('shift_id','!=', False)]
                                
                                if working_schedule_to:
                                    domain.append(('date','<=',working_schedule_to))
                                ws_detail_ids = ws_detail_obj.search(cr, uid, domain)
                                if ws_detail_ids:
                                    ws_details = ws_detail_obj.read(cr, uid, ws_detail_ids, ['date'])
                                    for ws_detail in ws_details:
                                        public_dates.remove(ws_detail.get('date'))
                            
                            
                            #Check if employee belong to WG chính thức, bình thường và CTV vp to add into paid day and total_hours_working
                            if public_dates:
                                number_of_public_date_belong_to_ct_wg = 0
                                number_of_adding_paid_day = 0
                                context = {'expand_from':expand_date[0],'expand_to':expand_date[1]}
                                for public_date in public_dates:
                                    is_belong_to_ct_bt_wg, is_adding_paid_day = self.check_if_employee_belong_to_ct_bt_working_group_at_date(cr, uid, employee_id, public_date, ct_bt_working_group_code, context)
                                    if is_belong_to_ct_bt_wg:
                                        number_of_public_date_belong_to_ct_wg += 1
                                        
                                        if is_adding_paid_day and self.compare_day(actual_from_date, public_date) >= 0 and\
                                          self.compare_day(public_date, actual_to_date) >= 0:
                                            number_of_adding_paid_day += 1
                                            
                                            #Một số loại nghỉ dài hạn như: nghỉ thai sản, nghỉ bệnh dài ngày 
                                            #thì công chuẩn sẽ không tính ngày lễ nếu như ngày lễ rơi trong giai đoạn đang nghỉ (do BH trả)
                                            holiday_ids = holiday_obj.search(cr, uid, [('employee_id','=',employee_id),
                                                                                       ('date_from','<=',public_date),
                                                                                       ('date_to','>=',public_date),
                                                                                       ('state','=','validate')], context={'get_all':1})
                                            if holiday_ids:
                                                holiday = holiday_obj.browse(cr, uid, holiday_ids[0])
                                                leave_type_group_code = holiday.holiday_status_id and holiday.holiday_status_id.holiday_status_group_id\
                                                                        and holiday.holiday_status_id.holiday_status_group_id.code or ''
                                                if leave_type_group_code in leavetype_group_with_public_date_not_add_to_working_date_code:
                                                    number_of_adding_paid_day -= 1
                                                
                                
                                working_days += number_of_public_date_belong_to_ct_wg
                                paid_days += number_of_adding_paid_day
                                total_hours_working += official_working_shift_hours * number_of_public_date_belong_to_ct_wg
                            
                                    
                            #meal_days = round(meal_days)
                            timesheet_summary_data = {'employee_id': employee_id,
                                                      # 'company_id': ts_monthly.company_id.id,
                                                      'timesheet_id': timesheet_id,
                                                      'night_shift_allowance_hours': night_shift_allowance_hours,
                                                      'working_days': working_days,
                                                      'haft_day_paid_leave': haft_day_paid,
                                                      'paid_leave': full_day_paid,
                                                      'total_paid_leave': total_paid_leave,
                                                      'haft_day_unpaid_leave': haft_day_unpaid,
                                                      'unpaid_leave': full_day_unpaid,
                                                      'total_unpaid_leave': total_unpaid_leave,
                                                      'maternity_leave': maternity_leave,
                                                      'sick_leave_short': sick_leave_short,
                                                      'pregnancy_leave': st_kt_leave,
                                                      'sick_leave_long': sick_leave_long,
                                                      'relax_leave': relax_leave,
                                                      'other_leave': other_leave,
                                                      'total_hours_working': total_hours_working,
                                                      'paid_days': paid_days,
                                                      'meal_days': meal_days,
                                                      'parking_days': parking_days,
                                                      'month': month,
                                                      'year': year,
                                                      'state': 'unsaved',
                                                      'is_last_payment': is_last_payment,
                                                      'termination_date':termination_date}

                            timesheet_summary_ids = timesheet_summary_obj.search(cr, uid,
                                                                                 [('employee_id', '=',
                                                                                   employee_id),
                                                                                  # ('company_id', '=',
                                                                                  # ts_monthly.company_id.id),
                                                                                  ('month', '=', month),
                                                                                  ('year', '=', year)])
                            
                            timesheet_summary_ids = [x for x in timesheet_summary_ids if x not in create_ids]
                            if timesheet_summary_ids:
                                if len(timesheet_summary_ids) >1:
                                    timesheet_summary_obj.unlink(cr, uid, timesheet_summary_ids)
                                    res_id = timesheet_summary_obj.create(cr, uid, timesheet_summary_data,
                                                                      context=context)
                                    create_ids.append(res_id)
                                else:
                                    
                                    timesheet_summary_obj.write(cr, uid, timesheet_summary_ids,
                                                                timesheet_summary_data,
                                                                context=context)
                                    create_ids.extend(timesheet_summary_ids)
                            else:
                                res_id = timesheet_summary_obj.create(cr, uid, timesheet_summary_data,
                                                                      context=context)
                                create_ids.append(res_id)
                            cr.commit()
                            
                    mass_status_detail_pool.create(t_cr, uid, {'mass_status_id': mass_status_id,
                                                                       'employee_id': employee_id,
                                                                       'message': '',
                                                                       'status': 'success'})
                    t_cr.commit()
                    
        except Exception, e:
            log.exception(e)
            try:
                error_message = e.message
                if not error_message:
                    error_message = e.value
            except:
                error_message = ""

            # If have error with first try, then rollback to clear all created holiday
            cr.rollback()

        if list_error:
            mass_status_pool.write(t_cr, uid, [mass_status_id],
                                   {'state': 'error', 'number_of_fail_record': len(list_error)})

        else:
            mass_status_pool.write(t_cr, uid, [mass_status_id], {'state': 'finish'})

        if error_message:
            mass_status_pool.write(t_cr, uid, [mass_status_id], {'state': 'fail', 'error_message': error_message})

        cr.commit()
        cr.close()

        t_cr.commit()
        t_cr.close()
        log.info('summary_thread_execute end()')
        return True
    
    
    def get_total_usefull_data_from_ts_monthly(self, cr, uid, ts_monthly_ids, context=None):
        '''
        Get total paid day, meal_days, parking_days... from ts_monthly_record
        '''
        if not context:
            context = {}
        ts_monthly_obj = self.pool.get('vhr.ts.monthly')
        full_day_paid = 0
        haft_day_unpaid = 0
        haft_day_paid = 0
        full_day_unpaid = 0
        night_shift_allowance_hours = 0
        meal_days = 0
        parking_days = 0
        sick_leave_long = 0
        sick_leave_short = 0
        st_kt_leave = 0
        maternity_leave = 0
        relax_leave = 0
        other_leave = 0
        paid_days = 0
        ts_monthly = False
        is_last_payment = False
        
        maternity_leave_code = context.get('maternity_leave_code','')
        st_kt_code = context.get('st_kt_code','')
        sick_leave_long_code = context.get('sick_leave_long_code','')
        sick_leave_short_code = context.get('sick_leave_short_code','')
        relax_leave_code = context.get('relax_leave_code','')
        other_leave_code = context.get('other_leave_code','')
        
        for ts_monthly in ts_monthly_obj.browse(cr, uid, ts_monthly_ids, context=context):
            paid_days += ts_monthly.coef
            meal_days += ts_monthly.meal_coef
            parking_days += ts_monthly.parking_coef
            is_last_payment = ts_monthly.is_last_payment
            #If monthly record is from a leave request
            if ts_monthly.holiday_line_id:
                if ts_monthly.leave_type_id:
                    #If leave request with type paid salary, addition to day_paid
                    if ts_monthly.leave_type_id.coefsal == 1:
                        if ts_monthly.holiday_line_id.status == 'full':
                            full_day_paid += 1
                        elif ts_monthly.holiday_line_id.status != 'full':
                            haft_day_paid += 1
                    #If leave request with type paid salary, addition to day_unpaid
                    if ts_monthly.leave_type_id.coefsal == 0:
                        if ts_monthly.holiday_line_id.status == 'full':
                            full_day_unpaid += 1
                        elif ts_monthly.holiday_line_id.status != 'full':
                            haft_day_unpaid += 1
                    
                    #Calculate for sick_leave long/ short
                    if ts_monthly.leave_type_id.holiday_status_group_id:
                        if ts_monthly.leave_type_id.holiday_status_group_id.code in sick_leave_long_code:
                            sick_leave_long += 1 * ts_monthly.holiday_line_id.number_of_days_temp
                        if ts_monthly.leave_type_id.holiday_status_group_id.code in sick_leave_short_code:
                            sick_leave_short += 1 * ts_monthly.holiday_line_id.number_of_days_temp
                        if ts_monthly.leave_type_id.holiday_status_group_id.code in relax_leave_code:
                            relax_leave += 1 * ts_monthly.holiday_line_id.number_of_days_temp
                        if ts_monthly.leave_type_id.holiday_status_group_id.code in st_kt_code:
                            st_kt_leave += ts_monthly.holiday_line_id.number_of_days_temp
                        if ts_monthly.leave_type_id.holiday_status_group_id.code in maternity_leave_code:
                            maternity_leave += ts_monthly.holiday_line_id.number_of_days_temp
                        
                        if ts_monthly.leave_type_id.holiday_status_group_id.code in other_leave_code:
                            other_leave += ts_monthly.holiday_line_id.number_of_days_temp
                
                holiday_status = ts_monthly.holiday_line_id.status
                #Only Addition into night_shift_allowance_hours if leave request dont take all day
                #Base on meal_coef to know if employee worked on that day
                if ts_monthly.meal_coef:
                    if holiday_status == 'morning':
                        if ts_monthly.shift_id:
                            night_shift_allowance_hours += ts_monthly.shift_id.last_shift_hours or 0
                    elif holiday_status == 'afternoon':
                        if ts_monthly.shift_id:
                            night_shift_allowance_hours += ts_monthly.shift_id.first_shift_hours
            else:
                #if monthly record from shift, addition night_shift_allowance_hours from data in shift
                if ts_monthly.shift_id:
                    night_shift_allowance_hours += ts_monthly.shift_id.first_shift_hours + ts_monthly.shift_id.last_shift_hours
        
        
        return full_day_paid, haft_day_unpaid, haft_day_paid, full_day_unpaid, night_shift_allowance_hours, meal_days, parking_days,\
                sick_leave_long, sick_leave_short, st_kt_leave, maternity_leave, relax_leave, other_leave, paid_days, is_last_payment, ts_monthly
    
    
    def get_total_working_days_of_employee_in_date_range(self, cr, uid, employee_id, from_date, to_date, context=None):
        '''
            Get total working days, total working hours of employee in date range base on working schedule employee, working schedule detail
        '''
        if not context:
            context = {}
            
        working_days = 0
        total_hours_working = 0
        working_schedule_ids = []
        ws_emp_obj = self.pool.get('vhr.ts.ws.employee')
        ws_detail_obj = self.pool.get('vhr.ts.ws.detail')
        public_holidays_obj = self.pool.get('vhr.public.holidays')
        working_schedule_dict_time = {}
        expand_to_timesheet_from_ws_emp_id = False
        expand_to_timesheet_to_ws_emp_id   = False
        #If employee A work from x to y then terminate, go back to work from y to z.
        #Total working days on period x-y will be count based on active Working Schedule at period x-y
        #Total working days on period y-z will be count based on active Working Schedule at period y-z
        start_working_date_at_ts_period = from_date
        end_working_date_at_ts_period = to_date
        if context.get('actual_from_date', False):
            start_working_date_at_ts_period = context.get('actual_from_date',False)
            end_working_date_at_ts_period = context.get('actual_to_date',False)
            
        ws_emp_ids = ws_emp_obj.search(cr, uid,
                                       [('employee_id', '=', employee_id),
                                        # ('company_id', '=', ts_monthly.company_id.id),
                                        '|',
                                        ('active', '=', False),
                                        ('active', '=', True),
                                        ('effect_from', '<=', end_working_date_at_ts_period),
                                        '|', ('effect_to', '>=', start_working_date_at_ts_period),
                                        ('effect_to', '=', False)], order="effect_from asc")
        if ws_emp_ids:
            #Compare if employee dont work for all timesheet period to expand working schedule to from_date or to_date of timesheet
            #Check if employee dont work from the beginning of timesheet period
            fist_ws_emp_ids = ws_emp_obj.search(cr, uid, [('employee_id','=', employee_id),
                                                        ('id', 'in', ws_emp_ids),
                                                        '|', ('active', '=', False), ('active', '=', True),
                                                        ('effect_from', '<=', from_date),
                                                        '|', ('effect_to', '>=', from_date), ('effect_to', '=', False)])
            if not fist_ws_emp_ids:
                expand_to_timesheet_from_ws_emp_id = ws_emp_ids[0]
            
            #Check if employee dont work to the end of timesheet period
            last_ws_emp_ids = ws_emp_obj.search(cr, uid, [('employee_id','=', employee_id),
                                                        ('id', 'in', ws_emp_ids),
                                                        '|', ('active', '=', False), ('active', '=', True),
                                                        ('effect_from', '<=', to_date),
                                                        '|', ('effect_to', '>=', to_date), ('effect_to', '=', False)])
            if not last_ws_emp_ids:
                expand_to_timesheet_to_ws_emp_id = ws_emp_ids[-1]
            
            #Loop for all working schedule in date range
            for ws_emp in ws_emp_obj.browse(cr, uid, ws_emp_ids, fields_process=['ws_id', 'effect_to', 'effect_from'], context=context):
                ws_id = ws_emp.ws_id and ws_emp.ws_id.id or False
                working_schedule_ids.append(ws_id)
                ws_emp_to_date = ws_emp.effect_to
                ws_emp_from_date = ws_emp.effect_from
                
                working_schedule_dict_time[ws_id] = [ws_emp_from_date, ws_emp_to_date]
                #Expand Working Schedule in case start working/ termination in the midle of timesheet period
                if expand_to_timesheet_from_ws_emp_id == ws_emp.id:
                    ws_emp_from_date = from_date
                if expand_to_timesheet_to_ws_emp_id == ws_emp.id:
                    ws_emp_to_date = to_date
                    
                if self.compare_day(ws_emp_from_date, from_date) >0:  #from_date > ws_emp_from_date
                    ws_emp_from_date = from_date
                if not ws_emp_to_date or self.compare_day(to_date, ws_emp_to_date) >0:  #ws_emp_to_date > to_date
                    ws_emp_to_date = to_date
                
                
                
                #Search in Working Schedule Detail to get all working day of Working Schedule in period
                ws_detail_ids = ws_detail_obj.search(cr, uid, [('ws_id', '=', ws_id),
                                                               ('shift_id', '!=', False),
                                                               ('date', '>=', ws_emp_from_date),
                                                               ('date', '<=', ws_emp_to_date)],
                                                     context=context)
                #Lay type of work day cua moi ngay co ca lam viec cua Working schedule
                ws_details = ws_detail_obj.browse(cr, uid, ws_detail_ids, fields_process=['shift_id'])
                type_work_day = [ws.shift_id and ws.shift_id.type_workday_id and ws.shift_id.type_workday_id.coef or 0 for ws in ws_details ]
                working_days += sum(type_work_day)
                
                for shift_data in ws_detail_obj.browse(cr, uid, ws_detail_ids):
                    total_hours_working += shift_data.shift_id and shift_data.shift_id.work_hour or 0
            
        return working_days, total_hours_working, working_schedule_ids, [expand_to_timesheet_from_ws_emp_id, expand_to_timesheet_to_ws_emp_id], working_schedule_dict_time
    
    def check_if_employee_belong_to_ct_bt_working_group_at_date(self, cr, uid, employee_id, date, working_group_ct_bt_code, context=None):
        '''
        1. If employee belong to ct_bt_ctv working group at public date (without shift), addition 1 days for paid day and working days
        2. If employee don't have any working record at public date but have nearest working record(below or larger: look at code) belong to ct_bt_ctv working group,
           addition 1 days to working days
        
        Case exception:
        Trước khi chuyển sang HĐ chính thức từ 6/1, nhân viên thuộc nhóm làm việc "CTV - theo phiếu đánh giá" (từ quá khứ tới --5/1)
         Xem như nhân viên mới vào từ đầu nên tính công chuẩn theo full lịch được gán (có tính ngày lễ 1/1)
        '''
        if not context:
            context = {}
        is_adding_paid_day = True
        if employee_id and date and working_group_ct_bt_code:
            working_record_obj = self.pool.get('vhr.working.record')
            #Read terminate change form code
            change_form_terminated_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_master_data_dismiss_change_form_code').split(',')
            change_form_ids = self.pool.get('vhr.change.form').search(cr, uid, [('code', 'in', change_form_terminated_code)],context=context)
            
            working_group_ctv_pdg_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'working_group_ctv_pdg_code') or ''
            working_group_ctv_pdg_code = working_group_ctv_pdg_code.split(',')
            wg_ctv_pdg_ids = self.pool.get('vhr.ts.working.group').search(cr, uid, [('code', 'in', working_group_ctv_pdg_code)],context=context)
            #Get all WR effect on public date dont have working group: CTV - Phieu danh gia
            wr_ids = working_record_obj.search(cr, uid, [('employee_id','=',employee_id),
                                                         ('state','in',['finish',False]),
                                                        ('effect_from','<=',date),
                                                        '|',('effect_to','>=',date),('effect_to','=',False),
                                                        ('change_form_ids','not in', change_form_ids),
                                                        ('ts_working_group_id_new','not in',wg_ctv_pdg_ids)])
            if not wr_ids:
                #Get working record have change form terminate on date, dont have working group: CTV - Phieu danh gia
                wr_ids = working_record_obj.search(cr, uid, [('employee_id','=',employee_id),
                                                         ('state','in',['finish',False]),
                                                        ('effect_from','=',date),
                                                        '|',('effect_to','>=',date),('effect_to','=',False),
                                                        ('change_form_ids','in', change_form_ids),
                                                        ('ts_working_group_id_new','not in',wg_ctv_pdg_ids)])
                
            #Case we need to add public date into total working hours, but not paid day(employee dont work at company at public date)
            if not wr_ids:
                is_adding_paid_day = False
                domain = [('employee_id','=',employee_id),
                          ('change_form_ids','not in', change_form_ids),
                          ('ts_working_group_id_new','not in',wg_ctv_pdg_ids),
                         '|',('active','=',False),('active','=',True)]
                
                order = []
                if not context.get('expand_from', False) and not context.get('expand_to', False):
                    domain.append(('effect_from','>=',date))
                    order.append('effect_from asc')
                if context.get('expand_from', False):
                    domain.insert(0,('effect_from','>=',date))
                    order.append('effect_from asc')
                if context.get('expand_to', False):
                    domain.insert(0,('effect_to','<=',date)) 
                    order.append('effect_to desc')
                
                order = ','.join(order)
                if context.get('expand_from', False) and context.get('effect_to', False):
                    domain.insert(0,'|')
                    
                wr_ids = working_record_obj.search(cr, uid, domain, order=order)
                wr_ids = wr_ids and wr_ids[:1]
            if wr_ids:
                main_wr_id = wr_ids[0]
                #If employee have more than 1 WR on public date, choose WR from main company or company emp worked early or first company
                if len(wr_ids) >1:
                    #Get main company to get working group from
                    main_company_id = False
                    workings = working_record_obj.read(cr, uid, wr_ids, ['company_id','contract_id'])
                    company_ids = [working['company_id'] and working['company_id'][0] for working in workings]
                    companies = self.pool.get('res.company').read(cr, uid, company_ids, ['is_member'])
                    #Choose company which contract.is_main = True
                    for working in workings:
                        contract_id = working.get('contract_id', False) and working['contract_id'][0]
                        if contract_id:
                            contract = self.pool.get('hr.contract').read(cr, SUPERUSER_ID, contract_id, ['is_main'])
                            if contract.get('is_main', False):
                                main_company_id = working['company_id'] and working['company_id'][0]
                                break
                    
                    #Choose company emp worked early
                    if not main_company_id:
                        emp_ins_ids = self.pool.get('vhr.employee.instance').search(cr, uid, [('employee_id','=',employee_id),
                                                                                              '|',('date_end','=',False), ('date_end','>=',date)],
                                                                                    order = 'date_start asc')
                        if emp_ins_ids:
                            emp_ins = self.pool.get('vhr.employee.instance').read(cr, uid, emp_ins_ids[0], ['company_id'])
                            main_company_id = emp_ins.get('company_id',False) and emp_ins['company_id'][0] or False
                    
                    #choose first company
                    if not main_company_id:
                        log.info('Can not find any company related to employee at %s!' % date)
                        main_company_id = companies[0]['id']
                    
                    main_wr_ids = working_record_obj.search(cr, uid, [('id', 'in', wr_ids),
                                                                      ('company_id','=', main_company_id)])
                    if main_wr_ids:
                        main_wr_id = main_wr_ids[0]
                
                working = working_record_obj.browse(cr, uid, main_wr_id, fields_process=['ts_working_group_id_new'])  
                working_group_code = working.ts_working_group_id_new and working.ts_working_group_id_new.code or ''
                if working_group_code in working_group_ct_bt_code:
                    return True, is_adding_paid_day
        
        return False, is_adding_paid_day
    
    
    def read(self, cr, user, ids, fields=None, context=None, load='_classic_read'):
        if not context:
            context = {}
        context['active_test'] = False
        res =  super(vhr_ts_monthly_gen, self).read(cr, user, ids, fields, context, load)
        return res
    
    def create(self, cr, uid, vals, context=None):
#         if vals.get('lock_emp_text', False):
#             vals['lock_emp_ids'] = [(6, False, eval(vals['lock_emp_text']))]
        
        res =  super(vhr_ts_monthly_gen, self).create(cr, uid, vals, context)
        return res
        
    
    
vhr_ts_monthly_gen()    
