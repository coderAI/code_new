# -*-coding:utf-8-*-
import logging
import thread
import sys
import time

from lxml import etree
import simplejson as json
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta, date
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.osv import osv, fields
from openerp.tools.translate import _
from openerp.addons.vhr_timesheet.model.vhr_holiday_line import STATUS
from openerp.sql_db import Cursor
from openerp.sql_db import ConnectionPool
from openerp import tools
from openerp import SUPERUSER_ID
from openerp.addons.vhr_common.model.vhr_common import vhr_common
from vhr_holidays_email_process import mail_process


log = logging.getLogger(__name__)
STATES = [('refuse', 'Cancelled'),('draft', 'Draft'),  ('confirm', 'Waiting LM'), ('cancel', 'Cancelled'),
          ('validate1', 'Waiting DH'), ('validate2', 'Waiting CB'),('validate', 'Finish')]
DICT_STATES = {'refuse': 'Cancelled','draft': 'Draft', 'confirm': 'Waiting LM', 
               'validate1': 'Waiting DH', 'validate2': 'Waiting CB','validate': 'Finish'}


class vhr_holidays(osv.osv, vhr_common):
    _name = 'hr.holidays'
    _inherit = 'hr.holidays'
    _order = 'create_date desc, year desc, date_from desc'
    
    submiting_ids = []
    
    # TODO: can be improved using resource calendar method
    def _get_number_of_days(self, date_from, date_to):
        """Returns a float equals to the delta between two dates given as string."""

        from_dt = datetime.strptime(date_from, DEFAULT_SERVER_DATE_FORMAT)
        to_dt = datetime.strptime(date_to, DEFAULT_SERVER_DATE_FORMAT)
        delta = to_dt - from_dt
        diff_day = delta.days + float(delta.seconds) / 86400
        return diff_day

    def _is_show_leave_full_information(self, cr, uid, ids, name, arg, context=None):
        if not context:
            context = {}

        result = dict.fromkeys(ids, False)
        code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'ts.leave.type.show.full.info.code').split(',')
        for holiday in self.browse(cr, uid, ids, fields_process=['holiday_status_id', 'type'], context=context):
            if holiday.type == 'remove' and holiday.holiday_status_id:
                if holiday.holiday_status_id.code in code:
                    result[holiday.id] = 'full'
                elif holiday.holiday_status_id.limit:
                    result[holiday.id] = 'limit'
        return result

    def _get_can_approve(self, cr, uid, ids, name, arg, context=None):
        """ """
        result = dict.fromkeys(ids, {'can_approve': False, 'can_validate': False, 'can_refuse': False,'can_validate_cb': False,'is_cb': False})
        groups = self.pool.get('res.users').get_groups(cr, uid)
        special_groups = ['vhr_cb_timesheet']
        if not context:
            context = {}
        
        for holiday in self.browse(cr, uid, ids, context=context):
            if 'vhr_cb_timesheet' in groups:
                result[holiday.id]['is_cb'] = True
            if holiday.type != 'remove':
                continue
            
            department_id = holiday.department_id and holiday.department_id.id or False
            
            if set(special_groups).intersection(set(groups)):
                result[holiday.id] = {'can_approve': True, 'can_validate': True, 'can_refuse': True,'can_validate_cb': True}
                
            elif set(['vhr_dept_admin']).intersection(set(groups)) and holiday.state in ['confirm','validate']:
                
                is_permission = self.is_have_admin_permission_approve_reject_on_leave_request(cr, uid, holiday.id, context)
                if is_permission:
                    result[holiday.id]['can_approve'] = True
                    result[holiday.id]['can_refuse'] = True
                    
                    
#             time2 = time.time()
            if holiday.report_to_id \
                    and  ( (holiday.report_to_id.user_id and holiday.report_to_id.user_id.id == uid) 
                        or self.is_delegate_from(cr, uid, uid, holiday.report_to_id.id, department_id)  ):
                if holiday.state in ['confirm']:
                    result[holiday.id]['can_approve'] = True
                    result[holiday.id]['can_refuse'] = True

            if holiday.department_id and holiday.department_id.manager_id \
                    and (   (holiday.department_id.manager_id.user_id and holiday.department_id.manager_id.user_id.id == uid)
                          or  self.is_delegate_from(cr, uid, uid, holiday.department_id.manager_id.id, department_id)  ):
                if holiday.state in ['validate1']:
                    result[holiday.id]['can_validate'] = True
                    result[holiday.id]['can_refuse'] = True

            #Hide button reject when a date in Detail is generated monthly and monthly record in state confirm/validate

            lines = holiday.holiday_line_ids
            date_range = [line.date for line in lines]
            employee_id = holiday.employee_id and holiday.employee_id.id or False
            ok_to_work = self.pool.get('vhr.holiday.line').check_if_date_not_in_generated_monthly(cr, uid, employee_id, date_range, context={"return_boolean": True})
            if not ok_to_work:
                result[holiday.id]['can_refuse'] = False
        
        return result
    
    def is_have_admin_permission_approve_reject_on_leave_request(self, cr, uid, leave_id, context=None):
        """
        Kiểm tra nếu uid là admin của employee trong leave_id và có quyền approve/reject khi leave_id tại bước waiting lm/finish
        """
        if not context:
            context = {}
        if leave_id:
            sql = """
                SELECT
                  DISTINCT HH.id
                FROM hr_holidays HH
                  INNER JOIN vhr_holiday_line LL ON HH.id = LL.holiday_id
                  INNER JOIN vhr_ts_emp_timesheet ET ON ET.employee_id = HH.employee_id
                  INNER JOIN vhr_ts_timesheet_detail TD
                    ON TD.timesheet_id = ET.timesheet_id --AND current_date BETWEEN TD.from_date AND TD.to_date
                  INNER JOIN hr_employee HE ON HE.id = TD.admin_id
                  INNER JOIN resource_resource RR ON RR.id = HE.resource_id
                  INNER JOIN res_users UU ON UU.id = RR.user_id
                WHERE HH.state in ('confirm','validate','{0}')
                      AND HH.id = {1}
                      AND UU.id = {2}
                      AND LL.date BETWEEN TD.from_date AND TD.to_date
                      AND ET.effect_from <= TD.to_date
                            AND (ET.effect_to IS NULL OR ET.effect_to >= TD.from_date)
            """.format(context.get('to_new_state',''),leave_id, uid)
            cr.execute(sql)
            holiday_ids = [holiday_id[0] for holiday_id in cr.fetchall()]
            if holiday_ids:
                return True
        
        return False

    def compute_total_taken_remain_pre_days(self, cr, uid, ids, name, arg, context=None):
        if not context:
            context = {}
        res = {id: {'total_days_pre_year': 0, 'destroy_days_of_pre_year': 0,
                    'total_taken_days_pre_year': 0, 'days_of_pre_year': 0}
               for id in ids}
        log.info('  start compute total taken remain pre_days---')
        context['get_all'] = True
        for holiday in self.browse(cr, uid, ids, context):
            holiday_id = holiday.id
            employee_id = holiday.employee_id and holiday.employee_id.id or False
            # company_id = holiday.company_id and holiday.company_id.id or False
            holiday_status_id = holiday.holiday_status_id and holiday.holiday_status_id.id or False
            year = holiday.year

            if employee_id and holiday_status_id and year:
                # Search for annual Leave previous year nếu đã chuyển phép dồn bù từ năm trước qua
                annual_leave_previous_ids = osv.osv.search(self, cr, uid, [('employee_id', '=', employee_id),
                                                                           # ('company_id', '=', company_id),
                                                                           ('holiday_status_id', '=',
                                                                            holiday_status_id),
                                                                           ('year', '=', (year - 1)),
                                                                           ('type', '=', 'add')], context=context)
                if annual_leave_previous_ids:
                    annual_leave_previous = self.read(cr, uid, annual_leave_previous_ids[0],
                                                      ['total_days', 'total_destroy_days',
                                                       'move_days_of_pre_year',
                                                       'total_taken_days', 'remain_days_of_year'])
                    res[holiday_id]['total_days_pre_year'] = annual_leave_previous.get('total_days', 0)
                    if annual_leave_previous.get('move_days_of_pre_year', False):
                        res[holiday_id]['destroy_days_of_pre_year'] = annual_leave_previous.get(
                            'total_destroy_days', 0)

                    res[holiday_id]['total_taken_days_pre_year'] = annual_leave_previous.get('total_taken_days', 0)

                    res[holiday_id]['days_of_pre_year'] = annual_leave_previous.get('remain_days_of_year', 0)

        log.info(' end compute total taken remain pre_days---')
        return res
    
    def get_date_start_of_earliest_active_employee_instance(self, cr, uid, employee_id, context=None):
        if not context:
            context = {}
        
        first_date_of_year_ins = context.get('first_date_of_year_ins', False)
        date_start_ins = False
        if employee_id:
            change_comp_ids = []
            change_comp_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_master_data_change_local_company') or ''
            if change_comp_code:
                change_comp_ids = self.pool.get('vhr.change.form').search(cr, uid, [('code','=',change_comp_code)])
            
            if context.get('is_ot_annual_leave', False):
                change_type_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_master_data_change_type_of_contract') or ''
                if change_type_code:
                    change_type_ids = self.pool.get('vhr.change.form').search(cr, uid, [('code','=',change_type_code)])
                    change_comp_ids.extend(change_type_ids)
            
            instance_obj = self.pool.get('vhr.employee.instance')
            #Find active employee instance
            today = date.today().strftime(DEFAULT_SERVER_DATE_FORMAT)
            instance_ids = instance_obj.search(cr, uid, [('employee_id','=',employee_id),
                                                                    ('date_start','<=',today),
                                                                    '|',('date_end','>=',today),
                                                                        ('date_end','=',False)], order='date_start asc')
            if instance_ids:
                index = 0
                while True and index < 5:
                    index += 1
                    instance = instance_obj.read(cr, uid, instance_ids[0], ['date_start','start_wr_id'])
                    date_start_ins = instance.get('date_start', False)
                    if first_date_of_year_ins and self.compare_day(date_start_ins, first_date_of_year_ins) >0:
                        break
                    #If start_wr_id.change_form_ids = "chuyen doi cong ty", get nearest instance
                    start_wr_id = instance.get('start_wr_id', False) and instance['start_wr_id'][0]
                    if start_wr_id:
                        wr = self.pool.get('vhr.working.record').read(cr, uid, start_wr_id, ['change_form_ids'])
                        change_form_ids = wr.get('change_form_ids', [])
                        if set(change_comp_ids).intersection(change_form_ids):
                            instance_ids = instance_obj.search(cr, uid, [('employee_id','=',employee_id),
                                                                        ('date_start','<',date_start_ins)], order='date_start desc')
                            if instance_ids:
                                instance = instance_obj.read(cr, uid, instance_ids[0], ['date_start','start_wr_id'])
                                date_start_ins = instance.get('date_start', False)
                            else:
                                break
        
        return date_start_ins

    def compute_days_taken_days_remain_days_of_year(self, cr, uid, ids, name, arg, context=None):
        if not context:
            context = {}
        res = {id: {'days_taken_of_pre_year': 0, 'remain_days_of_pre_year': 0,
                    'days_of_year': 0, 'days_taken_of_year': 0, 'remain_days_of_year': 0,
                    'total_days': 0, 'total_taken_days': 0, 'total_remain_days': 0, 'total_destroy_days': 0}
               for id in ids}
        log.info(' start compute_days_taken_days_remain_days_of_year---')

        holiday_line_pool = self.pool.get('vhr.holiday.line')
        context['get_all'] = True
        today = date.today()
        
        config_parameter = self.pool.get('ir.config_parameter')
        holiday_status_code = config_parameter.get_param(cr, uid, 'ts.leave.type.overtime.code')
        holiday_status_ids = []
        if holiday_status_code:
            holiday_status_code_list = holiday_status_code.split(',')
            holiday_status_ids = self.pool.get('hr.holidays.status').search(cr, uid, [
                                                                ('code', 'in', holiday_status_code_list)])
        for holiday in self.browse(cr, uid, ids, context):
            holiday_id = holiday.id
            employee_id = holiday.employee_id and holiday.employee_id.id or False
            # company_id = holiday.company_id and holiday.company_id.id or False
            holiday_status_id = holiday.holiday_status_id and holiday.holiday_status_id.id or False
            year = holiday.year

            if employee_id and holiday_status_id and year:
                first_date_of_year_ins = date(year, 1, 1).strftime(DEFAULT_SERVER_DATE_FORMAT)
                last_date_of_year = date(year, 12, 31).strftime(DEFAULT_SERVER_DATE_FORMAT)
                
                #If earliest active employee timesheet have date_start > first date of year, 
                #get employee_timesheet.date_start to filter list leave request, ot copensation\
                context['is_ot_annual_leave'] = holiday_status_id in holiday_status_ids
                context['first_date_of_year_ins'] = first_date_of_year_ins
                date_start_ins = self.get_date_start_of_earliest_active_employee_instance(cr, uid, employee_id, context)
                if date_start_ins:
                    is_ins_bigger = self.compare_day(first_date_of_year_ins, date_start_ins)
                    if is_ins_bigger > 0:
                        first_date_of_year_ins = date_start_ins
                            
                # Search for annual Leave this year to get value of days_of_year
                annual_leave_ids = osv.osv.search(self, cr, uid, [('employee_id', '=', employee_id),
                                                                  # ('company_id', '=', company_id),
                                                                  ('holiday_status_id', '=', holiday_status_id),
                                                                  ('year', '=', year),
                                                                  ('type', '=', 'add')], context=context)

                if annual_leave_ids:
                    annual_leave_infos = self.read(cr, uid, annual_leave_ids,
                                                   ['number_of_days_temp', 'seniority_leave'])
                    for annual_leave_info in annual_leave_infos:
                        res[holiday_id]['days_of_year'] += annual_leave_info.get('number_of_days_temp', 0)

                    # Add with seniority leave
                    seniority_leave = annual_leave_infos[0].get('seniority_leave', 0) or 0
                    res[holiday_id]['days_of_year'] += seniority_leave

                    # Cong gio nghi bu cho loai nghi bu
                    if holiday_status_ids and holiday_status_id in holiday_status_ids:
                        context['first_date_of_year_ins'] = first_date_of_year_ins
                        ot_day = self.get_compensatory_time_to_leave(cr, uid, employee_id, year, context)
                        minus_ot_day = self.get_compensation_ot_payment(cr, uid, employee_id, year, context)
                        res[holiday_id]['days_of_year'] += (ot_day - minus_ot_day)

                # Search for finish leave request this year to compute days_taken_of_year (have date >= current_employee_instance.date_start)
                
                finish_holiday_ids = osv.osv.search(self, cr, uid, [('employee_id', '=', employee_id),
                                                                    # ('company_id', '=', company_id),
                                                                    ('holiday_status_id', '=', holiday_status_id),
                                                                    ('type', '=', 'remove'),
                                                                    ('state', '=', 'validate')], context=context)

                vals_holiday_line = [('holiday_id', 'in', finish_holiday_ids),
                                     ('date', '>=', first_date_of_year_ins),
                                     ('date', '<=', last_date_of_year)]

                actual_days_of_pre_year = holiday.actual_days_of_pre_year or 0

                # Nếu có ngày dồn phép từ năm trước qua
                res[holiday_id]['remain_days_of_pre_year'] = actual_days_of_pre_year
                res[holiday_id]['remain_days_of_year'] = res[holiday_id]['days_of_year']

                expiry_date_of_days_pre_year = holiday.expiry_date_of_days_pre_year
                if expiry_date_of_days_pre_year and holiday.move_days_of_pre_year:
                    # Search các finish holiday line dùng trong năm nay trước khi hết hạn ngày phép dồn
                    nvals_leave = vals_holiday_line[:]
                    nvals_leave.append((('date', '<=', expiry_date_of_days_pre_year)))
                    leave_ex_ids = holiday_line_pool.search(cr, uid, nvals_leave)
                    if leave_ex_ids:
                        leaves = holiday_line_pool.read(cr, uid, leave_ex_ids, ['number_of_days_temp','number_of_hours'])
                        days_taken_first_season_of_year = 0
                        for leave in leaves:
#                             number_of_hours = leave.get('number_of_hours', 0)
#                             if number_of_hours:
#                                 days_taken_first_season_of_year += number_of_hours / 8.0
#                             else:
                            days_taken_first_season_of_year += leave.get('number_of_days_temp', 0)
                        
                        days_taken_first_season_of_year = float("{0:.1f}".format(days_taken_first_season_of_year))
                        
                        if days_taken_first_season_of_year <= actual_days_of_pre_year:
                            res[holiday_id]['days_taken_of_pre_year'] = days_taken_first_season_of_year
                            res[holiday_id][
                                'remain_days_of_pre_year'] = actual_days_of_pre_year - days_taken_first_season_of_year
                        else:
                            res[holiday_id]['days_taken_of_pre_year'] = actual_days_of_pre_year
                            res[holiday_id]['remain_days_of_pre_year'] = 0

                            res[holiday_id][
                                'days_taken_of_year'] = days_taken_first_season_of_year - actual_days_of_pre_year
                            res[holiday_id]['remain_days_of_year'] = res[holiday_id]['days_of_year'] - (
                                days_taken_first_season_of_year - actual_days_of_pre_year)

                nvals_leave = vals_holiday_line[:]
                # If expiry_date_of_days_pre_year và đã chuyển dồn bù, tính từ sau ngày hết hạn của dồn bù
                if expiry_date_of_days_pre_year and holiday.move_days_of_pre_year:
                    nvals_leave.append((('date', '>', expiry_date_of_days_pre_year)))

                leave_ex_ids = holiday_line_pool.search(cr, uid, nvals_leave)
                if leave_ex_ids:
                    leaves = holiday_line_pool.read(cr, uid, leave_ex_ids, ['number_of_days_temp','number_of_hours'])
                    days_taken_this_year = 0
                    for leave in leaves:
#                         number_of_hours = leave.get('number_of_hours', 0)
#                         if number_of_hours:
#                             days_taken_this_year += number_of_hours / 8.0
#                         else:
                        days_taken_this_year += leave.get('number_of_days_temp', 0)

                    days_taken_this_year = float("{0:.1f}".format(days_taken_this_year))
                    res[holiday_id]['days_taken_of_year'] += days_taken_this_year
                    res[holiday_id]['remain_days_of_year'] -= days_taken_this_year


                # Compute total
                res[holiday_id]['total_days'] = res[holiday_id]['days_of_year']
                res[holiday_id]['total_taken_days'] = res[holiday_id]['days_taken_of_pre_year'] + res[holiday_id][
                    'days_taken_of_year']
                res[holiday_id]['total_remain_days'] = res[holiday_id]['remain_days_of_year']

                if expiry_date_of_days_pre_year and holiday.move_days_of_pre_year:
                    expiry_date_of_days_pre_year = datetime.strptime(expiry_date_of_days_pre_year,
                                                                     DEFAULT_SERVER_DATE_FORMAT).date()
                    res[holiday_id]['total_days'] += actual_days_of_pre_year
                    if today <= expiry_date_of_days_pre_year:
                        res[holiday_id]['total_remain_days'] += res[holiday_id]['remain_days_of_pre_year']
                    else:
                        res[holiday_id]['total_destroy_days'] = res[holiday_id]['remain_days_of_pre_year']

        log.info(' end compute_days_taken_days_remain_days_of_year---')
        return res

    def get_compensatory_time_to_leave(self, cr, uid, employee_id, year, context=None):
        if not context:
            context = {}
        days = 0
        if employee_id and year:
            ot_detail_pool = self.pool.get('vhr.ts.overtime.detail')
            first_date_of_year = date(year, 1, 1).strftime(DEFAULT_SERVER_DATE_FORMAT)
            last_date_of_year = date(year, 12, 31).strftime(DEFAULT_SERVER_DATE_FORMAT)
            
            if context.get('first_date_of_year_ins', False):
                first_date_of_year = context['first_date_of_year_ins']
                
            ot_detail_ids = ot_detail_pool.search(cr, uid, [('employee_id', '=', employee_id),
                                                            ('state', '=', 'finish'),
                                                            ('is_compensation_leave', '=', True),
                                                            ('date_off', '>=', first_date_of_year),
                                                            ('date_off', '<=', last_date_of_year)])
            if ot_detail_ids:
                ot_details = ot_detail_pool.browse(cr, uid, ot_detail_ids)
                hours = 0
                for ot_detail in ot_details:
                    total_ot_day_comp_result = ot_detail.total_ot_day_approve * ot_detail.day_coef_compensation or 0

                    night_coef_compend = ot_detail.day_coef_compensation + ot_detail.night_coef_compensation + ot_detail.day_coef_compensation * ot_detail.allowance_night_coef_compensation
                    total_ot_night_comp_result = ot_detail.total_ot_night_approve * night_coef_compend
                    hours += total_ot_day_comp_result + total_ot_night_comp_result

                if hours:
                    general_param_pool = self.pool.get('vhr.ts.general.param')
                    general_param_ids = general_param_pool.search(cr, uid, [])
                    if general_param_ids:
                        param = general_param_pool.read(cr, uid, general_param_ids[0],
                                                        ['compensation_off_hour', 'compensation_off_day'])
                        compen_hour = param.get('compensation_off_hour', 0)
                        compen_day = param.get('compensation_off_day', 0)
                        if compen_day and compen_hour:
                            days = hours / compen_hour * compen_day
                            days = float("{0:.1f}".format(days))
        return days
    
    def get_compensation_ot_payment(self, cr, uid, employee_id, year, context=None):
        compensation_ot_day = 0
        compent_ot_pool = self.pool.get('vhr.compensation.ot.payment')
        
        compent_ot_ids = compent_ot_pool.search(cr, uid, [('employee_id','=',employee_id),
                                                          ('year','=',year),
                                                          ('state','=','close')])
        if compent_ot_ids:
            compent_ots = compent_ot_pool.read(cr, uid, compent_ot_ids, ['compensation_ot_day'])
            compensation_ot_day = [cp.get('compensation_ot_day',0) for cp in compent_ots]
            compensation_ot_day = sum(compensation_ot_day)
        
        return compensation_ot_day

    def _is_person_able_to_do_offline(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if not ids:
            return True
        if not isinstance(ids, list):
            ids = [ids]

        is_person_able_to_do_offline = self.is_person_able_to_do_offline(cr, uid, context)
        for record_id in ids:
            res[record_id] = is_person_able_to_do_offline

        return res

    def _get_can_reset(self, cr, uid, ids, name, arg, context=None):
        result = dict.fromkeys(ids, False)
        for holiday in self.browse(cr, uid, ids, context=context):
            if holiday.create_uid and holiday.create_uid.id == uid \
                    or holiday.employee_id and holiday.employee_id.user_id \
                            and holiday.employee_id.user_id.id == uid:
                result[holiday.id] = True
        return result

    def _user_left_days(self, cr, uid, ids, name, args, context=None):
        leave_type_obj = self.pool.get('hr.holidays.status')
        res = dict.fromkeys(ids, {'leaves_taken': 0, 'leaves_submitted': 0,
                                  'remaining_leaves': 0, 'max_leaves': 0,
                                  'total_leaves': 0, 'leaves_expired': 0,
                                  'remain_accum_leave': 0,'moved_accum_leave': 0,
                                  'annual_leaves_in_year_by_level':0,
                                  'annual_leaves_in_year_by_seniority':0
                                  
                                  })

        for request in self.browse(cr, uid, ids, fields_process=['employee_id', 'company_id', 'holiday_status_id'],
                                   context=context):
            if request.employee_id and request.holiday_status_id:
                # if request.company_id and request.employee_id and request.holiday_status_id:
                res[request.id] = leave_type_obj.get_days(cr, SUPERUSER_ID, [request.holiday_status_id.id],
                                                          request.employee_id.id,
                                                          request.company_id.id, date_from=request.date_from,
                                                          context=context).get(request.holiday_status_id.id,
                                                                               {'leaves_taken': 0,
                                                                                'remaining_leaves': 0,
                                                                                'max_leaves': 0,
                                                                                'total_leaves': 0,
                                                                                'leaves_expired': 0,
                                                                                'remain_accum_leave':0})
        return res

    def _get_update_annual_holiday_ids(self, cr, uid, ids, context=None):
        '''
        When have change of state, total_days, total_taken_days,  then check if have next year annual leave of record, update that annual leave
        '''
        if not context:
            context = {}
        context['get_all'] = True
        res = []
        for record in self.browse(cr, uid, ids):
            res_item = []
            if record.state == 'validate':
                employee_id = record.employee_id and record.employee_id.id or False
                # company_id = record.company_id and record.company_id.id or False
                holiday_status_id = record.holiday_status_id and record.holiday_status_id.id or False
                year = record.year

                vals = [('employee_id', '=', employee_id),
                        # ('company_id', '=', company_id),
                        ('holiday_status_id', '=', holiday_status_id),
                        ('type', '=', 'add'),
                        ('year', 'in', [year, year + 1])]

                res_item = osv.osv.search(self, cr, uid, vals, order='year asc', context=context)
            res.extend(res_item)

        return list(set(res))
    
    def _get_waiting_for(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for request in self.browse(cr, uid, ids, fields_process=['state', 'report_to_id', 'dept_head_id']):
            if request.type == 'remove' and request.state == 'draft' and request.requester_id:
                result[request.id] = request.requester_id.id
            elif request.type == 'remove' and request.state == 'confirm' and request.report_to_id:
                result[request.id] = request.report_to_id.id
            elif request.type == 'remove' and request.state == 'validate1' and request.dept_head_id:
                result[request.id] = request.dept_head_id.id
        return result
    
    def _get_note(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, '')
        return result
    
    def _is_change_value_by_hand(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, True)
        return result
    
    def _check_is_register_next_year(self, cr, uid, ids, name, args, context=None):
        """
        Mark True if have register next year and leave type allow to register next year
        """
        result = {}
        for record in self.browse(cr, uid, ids):
            date_from = record.date_from
            date_to = record.date_to
            is_allow_to_register_next_year = record.holiday_status_id and record.holiday_status_id.is_allow_to_register_from_now_to_next_year
            register_to_next_year = self.is_register_from_this_year_to_next_year(cr, uid, date_from, date_to, context)
            result[record.id] = is_allow_to_register_next_year and register_to_next_year
        
        return result
            
        
    def _get_update_annual_holiday_ids_from_ot(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        context['get_all'] = True
        res = []
        ot_detail_pool = self.pool.get('vhr.ts.overtime.detail')
        for record in ot_detail_pool.browse(cr, uid, ids):
            res_item = []
            if record.state == 'finish' and record.is_compensation_leave:
                year = datetime.strptime(record.date_off, DEFAULT_SERVER_DATE_FORMAT).year
                employee_id = record.employee_id and record.employee_id.id or False
                holiday_status_id = False

                config_parameter = self.pool.get('ir.config_parameter')
                holiday_status_code = config_parameter.get_param(cr, uid, 'ts.leave.type.overtime.code')
                if holiday_status_code:
                    holiday_status_code_list = holiday_status_code.split(',')
                    holiday_status_ids = self.pool.get('hr.holidays.status').search(cr, uid, [
                        ('code', 'in', holiday_status_code_list)])
                    if holiday_status_ids:
                        holiday_status_id = holiday_status_ids[0]

                if year and employee_id and holiday_status_id:
                    vals = [('employee_id', '=', employee_id),
                            # ('company_id', '=', company_id),
                            ('holiday_status_id', '=', holiday_status_id),
                            ('type', '=', 'add'),
                            ('year', 'in', [year, year + 1])]

                    res_item = self.pool.get('hr.holidays').search(cr, uid, vals, order='year asc', context=context)
            res.extend(res_item)

        return list(set(res))
    
    def _get_update_annual_holiday_ids_from_compen_ot(self, cr, uid, ids, context=None):
        compen_obj = self.pool.get('vhr.compensation.ot.payment')
        ids = compen_obj.search(cr, uid, [('state','=','close'),
                                          ('id','in', ids)])
        ids.append(0)
        parameter_obj = self.pool.get('ir.config_parameter')
        ot_leave_type_code = parameter_obj.get_param(cr, uid, 'ts.leave.type.overtime.code') or ''
        ot_leave_type_code = ot_leave_type_code.split(',')
        ot_leave_type_ids = self.pool.get('hr.holidays.status').search(cr, uid, [('code','in',ot_leave_type_code)])
                    
        compens = compen_obj.read(cr, uid, ids, ['employee_id', 'year','state','compensation_ot_day'])
        sql = """
                SELECT annual.id from hr_holidays annual INNER JOIN vhr_compensation_ot_payment ot 
                                                                ON annual.employee_id=ot.employee_id and annual.year=ot.year
                WHERE annual.type='add' and
                      annual.state='validate' and
                      annual.holiday_status_id in %s and
                      ot.id in %s
              """
        cr.execute(sql% (str(tuple(ot_leave_type_ids)).replace(',)', ')'),str(tuple(ids)).replace(',)', ')')  ))
        res = cr.fetchall()
        annual_ids = [item[0] for item in res]
        
        return annual_ids

    _columns = {
        'create_date': fields.datetime('Request Date'),
        'write_date': fields.datetime('Update Date'),
        'create_uid': fields.many2one('res.users', 'Create User'),
        'requester_id': fields.many2one('hr.employee', 'Requester'),
        'company_id': fields.many2one('res.company', 'Company'),
        'employee_code': fields.related('employee_id', 'code', type="char", string="Employee Code"),
        'employee_name': fields.related('employee_id', 'name', type="char", string="Employee Name"),
        'dept_code': fields.related('department_id', 'code', type="char", string="Dept Code"),
        'to_date_insurance': fields.date('To Date Insurance', readonly=True, select=True),
        'date_from': fields.date('From Date', readonly=True,
                                 states={'draft': [('readonly', False)]},
                                 select=True),
        'date_to': fields.date('To Date', readonly=True,
                               states={'draft': [('readonly', False)]}),

        'holiday_line_ids': fields.one2many('vhr.holiday.line', 'holiday_id', 'Detail'),
        'report_to_id': fields.many2one('hr.employee', 'Reporting Line'),
        'dept_head_id': fields.many2one('hr.employee', 'Dept Head'),
        'waiting_for_id': fields.function(_get_waiting_for, string='Waiting For', type='many2one',
                                          relation='hr.employee'),
        'remain_accum_leave': fields.function(_user_left_days, string='Remain Accum Leave',
                                      multi='user_left_days', digits=(16, 1)),
        'moved_accum_leave': fields.function(_user_left_days, string='Moved Accum Leave',
                                      multi='user_left_days', digits=(16, 1)),
        'leaves_expired': fields.function(_user_left_days, string='Expired Days',
                                          multi='user_left_days', digits=(16, 1)),
        
        'annual_leaves_in_year': fields.function(_user_left_days, string='Annual Leave In Year',
                                      multi='user_left_days', digits=(16, 1)),
        'annual_leaves_in_year_by_level': fields.function(_user_left_days, string='Annual Leave In Year By Level',
                                      multi='user_left_days', digits=(16, 1)),
        'annual_leaves_in_year_by_seniority': fields.function(_user_left_days, string='Annual Leave In Year By Seniority',
                                      multi='user_left_days', digits=(16, 1)),
                
        'max_leaves': fields.function(_user_left_days, string='Max Days Allow To Resgister',
                                      multi='user_left_days', digits=(16, 1)),
        'total_leaves': fields.function(_user_left_days, string='Total Of Days',
                                        multi='user_left_days', digits=(16, 1)),
        
        'total_current_leaves': fields.function(_user_left_days, string='Current Total Of Days',
                                                multi='user_left_days', digits=(16, 1)),
        'leaves_taken': fields.function(_user_left_days, string='Taken Days',
                                        multi='user_left_days', digits=(16, 1)),
        'leaves_submitted': fields.function(_user_left_days, string='Registered Days',
                                            multi='user_left_days', digits=(16, 1)),
        'remaining_leaves': fields.function(_user_left_days, string='Remaining Days',
                                            help='Maximum Leaves Allowed - Leaves Already Taken',
                                            multi='user_left_days', digits=(16, 1)),
        'virtual_remaining_leaves': fields.function(_user_left_days, string='Virtual Remaining Leaves',
                                                    help='Maximum Leaves Allowed - Leaves Already Taken - Leaves Waiting Approval',
                                                    multi='user_left_days', digits=(16, 1)),
        'double_validation': fields.boolean('Dept Head Validation',
                                            help="When selected, the Allocation/Leave Requests"
                                                 "require a Dept Head validation to be approved."),

        'holiday_status_description': fields.text('Leave\'s Description'),
        'state': fields.selection(STATES, 'Status', readonly=True, track_visibility='onchange',
                                  help='The status is set to \'Draft\', when a holiday request is created.\
            \nThe status is \'Submitted\', when holiday request is confirmed by user.\
            \nThe status is \'Rejected\', when holiday request is refused by manager.\
            \nThe status is \'Approved\', when holiday request is approved by manager.'),
        'can_approve': fields.function(_get_can_approve, type='boolean', multi="can_approve"),
        'can_validate': fields.function(_get_can_approve, type='boolean', multi="can_approve"),
        'can_refuse': fields.function(_get_can_approve, type='boolean', multi="can_approve"),
        'can_validate_cb': fields.function(_get_can_approve, type='boolean', multi="can_approve"),
        'is_cb': fields.function(_get_can_approve, type='boolean', multi="can_approve"),
        'can_reset': fields.function(_get_can_reset, type='boolean'),
        'is_show_full_leave_information': fields.function(_is_show_leave_full_information, type='char',
                                                          string='Is Show Full Leave Information'),
        'holiday_type': fields.selection([('employee', 'By Employee'), ('level', 'By Job Level')],
                                         'Allocation Mode', readonly=True,
                                         states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
                                         help='By Employee: Allocation/Request for individual Employee, '
                                              'By Employee Job Level: '
                                              'Allocation/Request for group of employees in job level',
                                         required=True),
        'job_level_type_id': fields.many2one('vhr.job.level.type', 'Job Level Type', ondelete='restrict'),
        'job_level_id': fields.many2one('vhr.job.level', 'Job Level',
                                        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]}),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                         domain=[('object_id.model', '=', _name),
                                                 ('field_id.name', 'not in', ['write_date', 'audit_log_ids'])]),
        'is_offline': fields.boolean('Is Offline'),
        'check_to_date_insurance': fields.related('holiday_status_id', 'check_to_date_insurance', type='boolean',
                                                  string='Check To Date(Insurance)?'),
        'holiday_status_name': fields.related('holiday_status_id', 'name', type='char', string='Leave Type'),
        'year': fields.integer('Year', states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]}),
        'is_person_able_to_do_offline': fields.function(_is_person_able_to_do_offline, type='boolean',
                                                        string='Is Person Able To Do Offline'),
        'state_log_ids': fields.one2many('vhr.state.change', 'res_id', 'History', domain=[('model', '=', _name)]),

        # Số ngày nghỉ được công thêm theo thâm niên
        'seniority_leave': fields.float('Leave Days By Seniority', digits=(2, 1)),

        # Fields total_days_pre_year, destroy_days_of_pre_year, total_taken_days_pre_year, days_of_pre_year,days_of_year only save in annual leave: type=add
        # Tổng số ngày phép của năm trước(phép dồn, phép thường, thâm niên)
        'total_days_pre_year': fields.function(compute_total_taken_remain_pre_days, type='float',
                                               string="Total Days (Prev. Year)",
                                               multi="compute_total_taken_remain_pre_days", digits=(2, 1)),

        # Tổng số ngày dồn bị hủy của năm trước(số ngày dồn của năm -2 bị hủy khi hết hạn mà vẫn còn ngày- chính là remain_days_of_pre_year của năm trước đó)
        'destroy_days_of_pre_year': fields.function(compute_total_taken_remain_pre_days, type='float',
                                                    string="Expired Days (Prev. Year)",
                                                    multi="compute_total_taken_remain_pre_days", digits=(2, 1)),

        # Số ngày phép đã sử dụng của năm trước
        'total_taken_days_pre_year': fields.function(compute_total_taken_remain_pre_days, type='float',
                                                     string="Total Taken Days (Prev. Year)",
                                                     multi="compute_total_taken_remain_pre_days", digits=(2, 1)),

        # Số ngày dồn phép năm từ năm trước chuyển qua
        'days_of_pre_year': fields.function(compute_total_taken_remain_pre_days, type='float',
                                            string="Days (Prev. Year)",
                                            multi="compute_total_taken_remain_pre_days", digits=(2, 1)),

        'move_days_of_pre_year': fields.boolean('Moved', help="Check if leave days already moved to next year."),

        # Số ngày dồn phép năm thực tế từ năm trước chuyển qua
        'temp_actual_days_of_pre_year': fields.float('Days (Prev. Year)', digits=(2, 1)),  # This if temporary field
        'actual_days_of_pre_year': fields.float('Days (Prev. Year)', digits=(2, 1)),
        # Số ngày sử dụng trong năm nay bị trừ vào ngày dồn phép
        'days_taken_of_pre_year': fields.function(compute_days_taken_days_remain_days_of_year, type='float',
                                                  string="Taken Days (Prev. Year)", multi="compute_taken_remain_days"
                                                  , store={'hr.holidays':
                                                               (_get_update_annual_holiday_ids,
                                                                ['actual_days_of_pre_year',
                                                                 'expiry_date_of_days_pre_year',
                                                                 'employee_id', 'company_id', 'days_of_year',
                                                                 'seniority_leave', 'state','holiday_status_id',
                                                                 'number_of_days_temp', 'move_days_of_pre_year'], 10)},
                                                  digits=(2, 1)),
        # Số ngày còn lại trong năm nay của ngày dồn phép năm trước
        'remain_days_of_pre_year': fields.function(compute_days_taken_days_remain_days_of_year, type='float',
                                                   string="Remaining Days (Prev. Year)", multi="compute_taken_remain_days"
                                                   , store={'hr.holidays':
                                                                (_get_update_annual_holiday_ids,
                                                                 ['actual_days_of_pre_year',
                                                                  'expiry_date_of_days_pre_year',
                                                                  'employee_id', 'company_id', 'days_of_year',
                                                                  'seniority_leave', 'state','holiday_status_id',
                                                                  'number_of_days_temp', 'move_days_of_pre_year'], 10)},
                                                   digits=(2, 1)),
        # Thời hạn sử dụng của ngày dồn phép từ năm trước chuyển qua
        'expiry_date_of_days_pre_year': fields.date('Expiry Date'),

        # Số ngày phép được cấp trong năm hiện tại
        'days_of_year': fields.function(compute_days_taken_days_remain_days_of_year, type='float', string="Num Of Days",
                                        multi="compute_taken_remain_days"
                                        , store={'hr.holidays':
                                                     (_get_update_annual_holiday_ids,
                                                      ['actual_days_of_pre_year', 'expiry_date_of_days_pre_year',
                                                       'employee_id', 'company_id', 'days_of_year','holiday_status_id',
                                                       'seniority_leave', 'state', 'number_of_days_temp',
                                                       'move_days_of_pre_year'], 10),
                                                 'vhr.ts.overtime.detail':
                                                     (_get_update_annual_holiday_ids_from_ot,
                                                      ['state', 'total_hours_approve', 'is_compensation_leave'], 20),
                                                 'vhr.compensation.ot.payment':
                                                     (_get_update_annual_holiday_ids_from_compen_ot,
                                                      ['state','compensation_ot_day'], 20)
                                                 },
                                        digits=(2, 1)),
        # Số ngày nghỉ trong năm bị trừ vào ngày phép
        'days_taken_of_year': fields.function(compute_days_taken_days_remain_days_of_year, type='float',
                                              string="Taken Days", multi="compute_taken_remain_days"
                                              , store={'hr.holidays':
                                                           (_get_update_annual_holiday_ids,
                                                            ['actual_days_of_pre_year', 'expiry_date_of_days_pre_year',
                                                             'employee_id', 'company_id', 'days_of_year','holiday_status_id',
                                                             'seniority_leave', 'state', 'number_of_days_temp',
                                                             'move_days_of_pre_year'], 10),
                                                       'vhr.ts.overtime.detail':
                                                           (_get_update_annual_holiday_ids_from_ot,
                                                            ['state', 'total_hours_approve', 'is_compensation_leave'],
                                                            20),
                                                       'vhr.compensation.ot.payment':
                                                             (_get_update_annual_holiday_ids_from_compen_ot,
                                                              ['state','compensation_ot_day'], 20)
                                                       }, digits=(2, 1)),
        # Số ngày phép còn lại của năm hiện tại
        'remain_days_of_year': fields.function(compute_days_taken_days_remain_days_of_year, type='float',
                                               string="Remaining Days", multi="compute_taken_remain_days"
                                               , store={'hr.holidays':
                                                            (_get_update_annual_holiday_ids,
                                                             ['actual_days_of_pre_year', 'expiry_date_of_days_pre_year',
                                                              'employee_id', 'company_id', 'days_of_year','holiday_status_id',
                                                              'seniority_leave', 'state', 'number_of_days_temp',
                                                              'move_days_of_pre_year'], 10),
                                                        'vhr.ts.overtime.detail':
                                                            (_get_update_annual_holiday_ids_from_ot,
                                                             ['state', 'total_hours_approve', 'is_compensation_leave'],
                                                             20),
                                                        'vhr.compensation.ot.payment':
                                                         (_get_update_annual_holiday_ids_from_compen_ot,
                                                          ['state','compensation_ot_day'], 20)
                                                        }, digits=(2, 1)),
        'notes_of_accumulation': fields.text('Notes of Accumulation'),

        # Tổng số ngày phép trong năm: = tổng ngày dồn phép, ngày phép, số ngày phép theo thâm niên
        'total_days': fields.function(compute_days_taken_days_remain_days_of_year, type='float',
                                      string="Total Of Days", multi="compute_taken_remain_days"
                                      , store={'hr.holidays':
                                                   (_get_update_annual_holiday_ids,
                                                    ['actual_days_of_pre_year', 'expiry_date_of_days_pre_year',
                                                     'employee_id', 'company_id', 'days_of_year','holiday_status_id',
                                                     'seniority_leave', 'state', 'number_of_days_temp',
                                                     'move_days_of_pre_year'], 10),
                                               'vhr.ts.overtime.detail':
                                                   (_get_update_annual_holiday_ids_from_ot,
                                                    ['state', 'total_hours_approve', 'is_compensation_leave'],
                                                    20),
                                               'vhr.compensation.ot.payment':
                                                     (_get_update_annual_holiday_ids_from_compen_ot,
                                                      ['state','compensation_ot_day'], 20)
                                               }, digits=(2, 1)),

        # Tổng số ngày phép đã sử dụng trong năm
        'total_taken_days': fields.function(compute_days_taken_days_remain_days_of_year, type='float',
                                            string="Total Taken Days", multi="compute_taken_remain_days"
                                            , store={'hr.holidays':
                                                         (_get_update_annual_holiday_ids,
                                                          ['actual_days_of_pre_year', 'expiry_date_of_days_pre_year',
                                                           'employee_id', 'company_id', 'days_of_year','holiday_status_id',
                                                           'seniority_leave', 'state', 'number_of_days_temp',
                                                           'move_days_of_pre_year'], 10),
                                                     'vhr.ts.overtime.detail':
                                                         (_get_update_annual_holiday_ids_from_ot,
                                                          ['state', 'total_hours_approve', 'is_compensation_leave'],
                                                          20),
                                                     'vhr.compensation.ot.payment':
                                                     (_get_update_annual_holiday_ids_from_compen_ot,
                                                      ['state','compensation_ot_day'], 20)
                                                     }, digits=(2, 1)),

        # Tổng số ngày phép có thể nghỉ trong năm (sau khi trừ đi taken vào total_days)
        'total_remain_days': fields.function(compute_days_taken_days_remain_days_of_year, type='float',
                                             string="Total Remaining Days", multi="compute_taken_remain_days"
                                             , store={'hr.holidays':
                                                          (_get_update_annual_holiday_ids,
                                                           ['actual_days_of_pre_year', 'expiry_date_of_days_pre_year',
                                                            'employee_id', 'company_id', 'days_of_year','holiday_status_id',
                                                            'seniority_leave', 'state', 'number_of_days_temp',
                                                            'move_days_of_pre_year'], 10),
                                                      'vhr.ts.overtime.detail':
                                                          (_get_update_annual_holiday_ids_from_ot,
                                                           ['state', 'total_hours_approve', 'is_compensation_leave'],
                                                           20),
                                                      'vhr.compensation.ot.payment':
                                                         (_get_update_annual_holiday_ids_from_compen_ot,
                                                          ['state','compensation_ot_day'], 20)
                                                      }, digits=(2, 1)),

        # Số ngày phép bị hủy tại thời điểm hiện tại, thường lấy từ số ngày dồn phép còn lại hết hạn
        'total_destroy_days': fields.function(compute_days_taken_days_remain_days_of_year, type='float',
                                              string="Total Expired Days", multi="compute_taken_remain_days"
                                              , store={'hr.holidays':
                                                           (_get_update_annual_holiday_ids,
                                                            ['actual_days_of_pre_year', 'expiry_date_of_days_pre_year',
                                                             'employee_id', 'company_id', 'days_of_year','holiday_status_id',
                                                             'seniority_leave', 'state', 'number_of_days_temp',
                                                             'move_days_of_pre_year'], 10),
                                                       'vhr.ts.overtime.detail':
                                                           (_get_update_annual_holiday_ids_from_ot,
                                                            ['state', 'total_hours_approve', 'is_compensation_leave'],
                                                            20),
                                                       'vhr.compensation.ot.payment':
                                                         (_get_update_annual_holiday_ids_from_compen_ot,
                                                          ['state','compensation_ot_day'], 20)
                                                       }, digits=(2, 1)),
        
        'alert_note': fields.function(_get_note, type='char',string="Note Form"),
        #This field is for save message You still remain x compensatory days. You should to use out of it before using annual leave
        #Use this field for save time for compute should we show that message
        'alert_note_temp': fields.function(_get_note, type='char',string="Note Form"),
        'is_register_next_year': fields.function(_check_is_register_next_year, type='boolean',string="Is Register Next Year ?"),
        #This field is only use to determine record is new or created, to show delete button in leave registration
        'is_created': fields.boolean('Is Created'),
        'is_change_from_employee': fields.boolean('Is Change From Employee'),
        'number_of_hours': fields.float('Number of hours', digits=(3, 1)),
        'is_change_date_to_by_hand': fields.function(_is_change_value_by_hand, type='boolean', string="Is Change Date To"),
        
        'is_missing_holiday_line': fields.boolean('Is Missing Holiday Line'),
                
        'lock_ts_detail_id': fields.many2one('vhr.ts.lock.timesheet.detail', 'Lock TS Detail', ondelete='restrict'),
    }
    
    _sql_constraints = [
        ('date_check', "CHECK ( 1 )", "The number of days must be greater than 0."),
    ]

    def _is_person_able_to_do_offline_default(self, cr, uid, context=None):
        return self.is_person_able_to_do_offline(cr, uid, context)

    def get_overtime_allocation(self, cr, uid, employee_id, company_id=False, date_from=False, context=None):
        if context is None:
            context = {}
        context['get_all'] = 1
        parameter_obj = self.pool.get('ir.config_parameter')
        code = parameter_obj.get_param(cr, uid, 'ts.leave.type.overtime.code').split(',')
        leave_type_obj = self.pool.get('hr.holidays.status')
        status_ids = leave_type_obj.search(cr, uid, [('code', 'in', code)])
        holiday_ids = osv.osv.search(self, cr, uid, [('employee_id', '=', employee_id),
                                                     # ('company_id', '=', company_id),
                                                     ('type', '=', 'add'),
                                                     ('state', 'in',
                                                      ['confirm', 'validate1', 'validate']),
                                                     ('holiday_status_id', 'in', status_ids)],
                                     context=context)
        if status_ids and employee_id:
                
            leave_days = leave_type_obj.get_days(cr, uid, status_ids, employee_id, company_id, date_from, context=context)[status_ids[0]]
            if leave_days.get('remaining_leaves') > 0:
                return holiday_ids, status_ids
        return [], status_ids

    def _get_default_holiday_status(self, cr, uid, employee_id=False, company_id=False, is_collaborator=None,
                                    context=None):
        if not context:
            context = {}
        
        if employee_id:
            # Collaborator
            res = self.get_default_holiday_status_by_type_for_employee(cr, uid, employee_id, context)
            
            if context.get('update_for_leave', False):
                return res and res[0] or False
            
            # check co nghi bu
            today = date.today().strftime(DEFAULT_SERVER_DATE_FORMAT)
            holiday_ids, status_ids = self.get_overtime_allocation(cr, uid, employee_id, company_id, today, context)
            if holiday_ids:
                res = status_ids
        
            
        
        return res and res[0] or False
    

    def _requester_get(self, cr, uid, context=None):
        ids = self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', uid)], context={"search_all_employee":True})
        if ids:
            return ids[0]
        return False

    def _employee_get(self, cr, uid, context=None):
        if context.get('default_is_offline'):
            return False
        else:
            ids = self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', uid)], context={"search_all_employee":True})
            if ids:
#                 self.is_collaborator(cr, uid, employee_id=ids[0], company_id=False, context=context)
                return ids[0]
        return False

    def _get_default_today(self, cr, uid, context=None):
        logging.info('_get_default_today current %s' % datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT))
        logging.info('_get_default_today date today %s' % date.today().strftime(DEFAULT_SERVER_DATE_FORMAT))
        logging.info('_get_default_today field today %s' % fields.date.today())
        logging.info('_get_default_today field context today %s' % fields.date.context_today(self, cr, uid))
        return date.today().strftime(DEFAULT_SERVER_DATE_FORMAT)

    def _get_default_year(self, cr, uid, context=None):
        return date.today().year

    _defaults = {
        'is_show_full_leave_information': False,
        'state': 'draft',
        'date_from': fields.datetime.now,
        # 'date_from': fields.date.context_today,
        'requester_id': _requester_get,
        'employee_id': _employee_get,
        'is_person_able_to_do_offline': _is_person_able_to_do_offline_default,
#         'holiday_status_id': _get_default_holiday_status,
        'year': _get_default_year,
        'actual_days_of_pre_year': 0,
        'move_days_of_pre_year': False,
        'expiry_date_of_days_pre_year': False,
        'is_created': False,
        'can_refuse': False,
        'is_change_date_to_by_hand': True,
    }


    # Just override from parent class
    def _check_date(self, cr, uid, ids):
        return True

    _check_holidays = lambda self, cr, uid, ids, context=None: self._check_date(cr, uid, ids)

    _constraints = [
        (_check_date, _('You can not have 2 leaves which is overlap!'), ['date_from', 'date_to']),
        (_check_holidays, _('The number of remaining days is not sufficient for this leave type!'),
         ['state', 'number_of_days_temp'])
    ]

    def init(self, cr):
        cr.execute("ALTER TABLE hr_holidays DROP CONSTRAINT IF EXISTS hr_holidays_type_value")
        cr.commit()
        
    def get_default_holiday_status_by_type_for_employee(self, cr, uid, employee_id, context=None):
        if not context:
            context = {}
        res = False
        if employee_id:
            parameter_obj = self.pool.get('ir.config_parameter')
            leave_type_obj = self.pool.get('hr.holidays.status')
            # NV Chinh Thuc
            code = parameter_obj.get_param(cr, uid, 'ts.leave.type.default.code').split(',')
            res = self.pool.get('hr.holidays.status').search(cr, uid, [('code', 'in', code)])
            try:
                is_collaborator,is_probation = self.is_collaborator_or_probation(cr, uid, employee_id=employee_id, company_id=False, context=context)
            except Exception as e:
                log.exception(e)
                return False
            
            if is_probation:
                code = parameter_obj.get_param(cr, uid, 'ts.leave.type.probation.default.code').split(',')
                res = self.pool.get('hr.holidays.status').search(cr, uid, [('code', 'in', code)])
            elif is_collaborator:
                emp_ids = self.get_colla_emp_satisfy_condition_to_gen_annual_leave(cr, uid, [employee_id], context)
                if emp_ids:
                    leave_type_code = parameter_obj.get_param(cr, uid, 'ts.leave.type.default.code').split(',')

                    res = leave_type_obj.search(cr, uid, [('code', 'in', leave_type_code)])
                else:
                    code = parameter_obj.get_param(cr, uid, 'ts.leave.type.collaborator.default.code').split(',')
                    res = self.pool.get('hr.holidays.status').search(cr, uid, [('code', 'in', code)])
            
            #Neu xuat hien tu menu Update For Leave, mac dinh luon chon leave type cua loai nhan vien
#             if context.get('update_for_leave', False):
#                 return res and res[0] or False
        
        return res

    def check_holidays(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        for record in self.browse(cr, uid, ids, fields_process=['holiday_status_id', 'type',
                                                                'holiday_type', 'date_from', 'state'], context=context):
            if record.state in ['refuse', 'cancel']:
                continue
            if record.holiday_type != 'employee' or record.type != 'remove' \
                    or not record.employee_id \
                    or record.holiday_status_id.limit:
                continue
            
            context['current_check_holiday_ids'] = [record.id]
            leave_days = self.pool.get('hr.holidays.status').get_days(cr, uid,
                                                                      [record.holiday_status_id.id],
                                                                      record.employee_id.id,
                                                                      record.company_id.id,
                                                                      date_from=record.date_from,
                                                                      context=context)[record.holiday_status_id.id]
            if leave_days['max_leaves'] < 0 or leave_days['remaining_leaves'] < 0 or \
                            leave_days['virtual_remaining_leaves'] < 0:
                log.info('max_leaves: %s;;;remaining_leaves: %s;;virtual_remaining_leaves:%s '% 
                         (leave_days['max_leaves'],leave_days['remaining_leaves'],leave_days['virtual_remaining_leaves']))
                raise osv.except_osv(_('Warning!'),
                                     _('Số ngày đăng ký vượt quá số ngày được cho phép, vui lòng kiểm tra lại!'))
        return True

    def is_person_able_to_do_offline(self, cr, uid, context=None):
        groups = self.pool.get('res.users').get_groups(cr, uid)
        special_groups = ['vhr_cb_timesheet', 'vhr_dept_admin']
        if set(special_groups).intersection(set(groups)):
            return True
        return False

    def get_date_list_from_ws_detail(self, cr, uid, employee_id, company_id=False, date_from=False, date_to=False):
        list_date = []
        dict_hours = {}
        dict_type_workday = {}
        ws_detail_obj = self.pool.get('vhr.ts.ws.detail')
        ws_employee_obj = self.pool.get('vhr.ts.ws.employee')
        # get working schedule employee has in date range
        ws_employee_ids = ws_employee_obj.search(cr, uid, [('employee_id', '=', employee_id),
                                                           # ('company_id', '=', company_id),
                                                           '|',
                                                           ('active', '=', False),
                                                           ('active', '=', True),
                                                           ('effect_from', '<=', date_to),
                                                           '|', ('effect_to', '>=', date_from),
                                                           ('effect_to', '=', False)])
        if ws_employee_ids:
            for ws_id in ws_employee_obj.read(cr, uid, ws_employee_ids, ['ws_id', 'effect_from', 'effect_to']):
                date_start = ws_id['effect_from']
                date_end = ws_id['effect_to']
                if date_start < date_from:
                    date_start = date_from
                if not date_end or date_end > date_to:
                    date_end = date_to
                if ws_id and ws_id.get('ws_id', False):
                    ws_id = ws_id['ws_id'][0]
                    ws_detail_ids = ws_detail_obj.search(cr, uid,
                                                         [('ws_id', '=', ws_id), ('date', '<=', date_end),
                                                          ('date', '>=', date_start), ('shift_id','!=',False)])
                    ws_details = ws_detail_obj.browse(cr, uid, ws_detail_ids)
                    
                    list_date_temp = filter(None, map(lambda x: x.date, ws_details))
                    dict_ws_hours = {x.date: x.shift_id and x.shift_id.work_hour for x in ws_details}
                    
                    list_date.extend(list_date_temp)
                    dict_hours.update(dict_ws_hours)
                    
                    dict_type_workday.update({ x.date: x.shift_id and x.shift_id.type_workday_id and x.shift_id.type_workday_id.coef
                                                         for x in ws_details })
        list_date = list(set(list_date))
        list_date.sort()
        return list_date, dict_hours, dict_type_workday
    
    def generate_date(self, cr, uid, employee_id, company_id=False, date_from=False, date_to=False):
        '''
        Get list date employee have working shift(go to work)
        '''
        list_date = []
        dict_hours = {}
        dict_type_workday = {}
        if date_to and date_from:
            list_date, dict_hours, dict_type_workday = self.get_date_list_from_ws_detail(cr, uid, employee_id, company_id, date_from, date_to)
        return list_date, dict_hours, dict_type_workday

    def onchange_number_of_days_temp(self, cr, uid, ids, employee_id, company_id, holiday_status_id, date_to, date_from,
                                     is_offline, number_of_days_temp, max_leaves, holiday_line_ids, context=None):

        result = {'value': {}, 'warning': {}}
        if not max_leaves:
            max_leaves = 0
        if number_of_days_temp > max_leaves:
            result = self.onchange_date_range(cr, uid, ids, employee_id, company_id, holiday_status_id,
                                              date_to, date_from, holiday_line_ids, is_offline, False, False, context=context)
        return result
    
    
    def remove_taken_days(self, cr, ids, employee_id, list_date):
        '''
            Remove days employee had taken leave
        '''
        sql = """
                            SELECT
                              A.date
                            FROM vhr_holiday_line A
                                INNER JOIN hr_holidays C on A.holiday_id = C.id
                            WHERE C.employee_id = %s
                                AND C.state NOT IN ('cancel', 'refuse')
                                AND A.date in %s
                                %s
                            GROUP BY 1
                            HAVING sum(A.number_of_days_temp) > 0
                        """ % (employee_id, str(tuple(list_date)).replace(',)', ')'),
                               ids and "AND C.id NOT IN %s" % str(tuple(ids)).replace(',)', ')') or '')
        cr.execute(sql)
        list_date_taken = [item[0] for item in cr.fetchall()]
        list_date = [date for date in list_date if date not in list_date_taken]
        return list_date, list_date_taken
    
    def remove_duplicate_days(self, cr, ids, employee_id, list_date):
        '''
            Remove days employee had taken leave full day
        '''
        sql = """
                            SELECT
                              A.date
                            FROM vhr_holiday_line A
                                INNER JOIN hr_holidays C on A.holiday_id = C.id
                            WHERE C.employee_id = %s
                                AND C.state NOT IN ('cancel', 'refuse')
                                AND A.date in %s
                                %s
                            GROUP BY 1
                            HAVING sum(A.number_of_days_temp) = 1
                        """ % (employee_id, str(tuple(list_date)).replace(',)', ')'),
                               ids and "AND C.id NOT IN %s" % str(tuple(ids)).replace(',)', ')') or '')
        cr.execute(sql)
        list_date_duplicate = [item[0] for item in cr.fetchall()]
        list_date = [date for date in list_date if date not in list_date_duplicate]
        return list_date, list_date_duplicate

    def get_haft_date_info(self, cr, uid, ids, employee_id, list_date):
        '''Get days employee has leave a half of day/work for only half of day'''
        holiday_line_ids = []
        list_date_must_full_leave = []
        if ids:
            if not isinstance(ids, list):
                ids = [ids]
            holiday_line_ids = self.read(cr, uid, ids[0], ['holiday_line_ids']).get('holiday_line_ids',[])
            
        holiday_line_obj = self.pool.get('vhr.holiday.line')
        ws_emp_obj = self.pool.get('vhr.ts.ws.employee')
        ws_detail_obj = self.pool.get('vhr.ts.ws.detail')
        
        sql_list_date = list(list_date)
        if not sql_list_date:
            sql_list_date = '(null)'
        else:
            sql_list_date = str(tuple(sql_list_date)).replace(',)', ')')
        sql = '''
                SELECT line.id 
                FROM hr_holidays hr inner join vhr_holiday_line line ON hr.id = line.holiday_id
                WHERE 
                         line.status != 'full' 
                    AND  hr.employee_id = %s
                    AND hr.state not in ('cancel','refuse')
                    AND date in %s
                    
              '''% (employee_id, sql_list_date)
        
        cr.execute(sql)
        res = cr.fetchall()
        line_dup_ids = [item[0] for item in res if item[0] not in holiday_line_ids]
        
#         line_dup_ids = holiday_line_obj.search(cr, uid, [('status', '!=', 'full'),
#                                                          ('holiday_id.employee_id', '=', employee_id),
#                                                          ('holiday_id.state', 'not in',
#                                                           ('cancel', 'refuse')),
#                                                          ('date', 'in', list_date)], context={'get_all': True})
        
        date_dup_not_full = holiday_line_obj.read(cr, uid, line_dup_ids, ['date', 'status'])
        list_date_duplicate = [date_item['date'] for date_item in date_dup_not_full if
                               date_item.get('date')]
        
        
        #Get days employee only work for half of day, support they are off in last half of day
        for date in list_date:
            #Get working schedule on date
            ts_ws_ids = ws_emp_obj.search(cr, uid, [('employee_id','=',employee_id),
                                                   ('effect_from',"<=",date),
                                                  '|',('effect_to','>=',date),('effect_to','=',False)])
            if ts_ws_ids:
                ws_emp = ws_emp_obj.read(cr, uid, ts_ws_ids[0], ['ws_id'])
                ws_id = ws_emp.get('ws_id',False) and ws_emp['ws_id'][0] or False
                if ws_id:
                    ws_detail_ids = ws_detail_obj.search(cr, uid, [('ws_id','=',ws_id),('date','=',date)])
                    #Get shift at date
                    if ws_detail_ids:
                        ws_detail = ws_detail_obj.browse(cr, uid, ws_detail_ids[0], fields_process=['shift_id'])
                        type_of_work_day = ws_detail.shift_id and ws_detail.shift_id.type_workday_id and ws_detail.shift_id.type_workday_id.coef or 0
                        if type_of_work_day <= 0.5:
                            #If employee had left on that day, add signal to onchange_date_range dont show that days anymore
                            if date in list_date_duplicate:
                                index = 0
                                for date_data in date_dup_not_full:
                                    if date_data['date'] == date:
                                        break
                                    index += 1
                                del date_dup_not_full[index]
                                date_dup_not_full.append({'date':date,'status': 'afternoon', 'do_not_show': True})
                            else:    
                                list_date_must_full_leave.append(date)
#                                 list_date_duplicate.append(date)
#                                 date_dup_not_full.append({'date':date,'status': 'afternoon'})
        
        
        return date_dup_not_full, list_date_duplicate, list_date_must_full_leave
    
    def update_data_for_leave_type_insurance(self, cr, uid, result, employee_id, company_id, date_from, holiday_status_id, context):
        #Nếu leave type có check_to_date_insurance = True, gán to_date_insurance = date_to = date_from + timelines days
        check_to_date_insurance = False
        to_date_insurance = False
        if date_from and holiday_status_id:
            check_to_date_insurance, to_date_insurance = self.update_insurance_date(cr, uid, employee_id, company_id, date_from, holiday_status_id, context=context)
        
        result['value']['check_to_date_insurance'] = check_to_date_insurance
        result['value']['to_date_insurance'] = to_date_insurance and to_date_insurance.strftime(DEFAULT_SERVER_DATE_FORMAT) or False
        if to_date_insurance:
            date_to = to_date_insurance.strftime(DEFAULT_SERVER_DATE_FORMAT)
            result['value']['date_to'] = date_to
        
        return result
    
    def check_if_take_correct_leave_request_on_leave_type_holiday(self, cr, uid, holiday_status_id, date_from, date_to, context=None):
        """
        Nếu leave type là loại nghỉ tết thì chỉ được xin nghỉ ngày lễ tết thôi
        """
        if holiday_status_id and date_from and date_to:
            holiday_status_letet_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'holiday_status_letet_cs_calich') or ''
            holiday_status_letet_code = holiday_status_letet_code.split(',')
            holiday_status_letet_codep_ids = self.pool.get('hr.holidays.status').search(cr, uid, [('code','in',holiday_status_letet_code)])
            #Choose leave type loai nghi tet cs ca lich
            if holiday_status_id in holiday_status_letet_codep_ids:
                start_date = datetime.strptime(date_from, DEFAULT_SERVER_DATE_FORMAT)
                end_date = datetime.strptime(date_to, DEFAULT_SERVER_DATE_FORMAT)
                gap = (end_date - start_date).days
                if gap >=0:
                    list_date = [(start_date + relativedelta(days=x)).strftime(DEFAULT_SERVER_DATE_FORMAT) for x in range(0,gap+1)]
                    holiday_ids = self.pool.get('vhr.public.holidays').search(cr, uid, [('date','in',list_date)])
                    if len(list_date) != len(holiday_ids):
                        return False
        return True
    
    def is_over_leave_from_before_to_after_expire_pre_days(self, cr, uid, holiday_status_id, employee_id, company_id, date_from, expiry_date, date_to, remain_days_of_pre_year, context=None):
        """
        divide into 2 part:
        - date_from to expiry_date
        - expiry_date + 1 to date_to:
        
        Just check if request leave days is over max leave
        """
        leave_type_obj = self.pool.get('hr.holidays.status')
        if expiry_date and date_to > expiry_date >= date_from:
            list_date_, dict_hours, dict_type_workday = self.generate_date(cr, uid, employee_id, company_id, date_from[:10], expiry_date)
            date_from_ = (datetime.strptime(expiry_date, DEFAULT_SERVER_DATE_FORMAT) + timedelta(days=1)).strftime(DEFAULT_SERVER_DATE_FORMAT)
            
            days_need_to_minus_after_using_remain_days_pre_year = len(list_date_) - remain_days_of_pre_year
            if days_need_to_minus_after_using_remain_days_pre_year < 0:
                days_need_to_minus_after_using_remain_days_pre_year = 0
            
            leave_days_next = leave_type_obj.get_days(cr, uid, [holiday_status_id], employee_id, company_id, date_from_).get(holiday_status_id, {})
            
            max_leaves = leave_days_next['max_leaves'] - days_need_to_minus_after_using_remain_days_pre_year
            if max_leaves >= 0:
                list_date_x, dict_hours_x, dict_type_workday = self.generate_date(cr, uid, employee_id, company_id, date_from_, date_to)
                remain_leaves = max_leaves - len(list_date_x)
                if remain_leaves < 0:
                    return True
            else:
                return True
        
        return False
    
    def check_if_take_birth_leave_on_leave_date(self, cr, uid, ids, employee_id, holiday_status_id, date_from, date_to, context=None):
        """
        Ràng buộc: Nếu đk nghỉ phép trước rồi mới đk nghỉ sinh con mà thời gian nghỉ phép trùng với thời gian nghỉ sinh con 
        thì yc hủy ngày phép thì mới cập nhật nghỉ sinh con được.: "Bạn đã đăng ký nghỉ phép ngày….trùng với thời gian nghỉ sinh. 
        Vui lòng báo Admin cancel ngày nghỉ phép để cập nhật nghỉ Sinh con"
        """
        list_date = []
        if employee_id and holiday_status_id and date_to and date_from:
            parameter_obj = self.pool.get('ir.config_parameter')
            leave_type_obj = self.pool.get('hr.holidays.status')
            holiday_line_obj = self.pool.get('vhr.holiday.line')
            
            #Parameter chua code cua cac leave type sinh con
            leave_type_code = parameter_obj.get_param(cr, uid, 'vhr_timesheet_leave_type_check_to_lock_if_take_leave_before') or ''
            leave_type_code = leave_type_code.split(',')
            leave_type_ids = leave_type_obj.search(cr, uid, [('code','in',leave_type_code)])
            
            if holiday_status_id in leave_type_ids:
                #Search holiday line have date in date_from -- date_to
                domain = [('employee_id','=',employee_id),
                          ('date','>=',date_from),
                          ('date','<=',date_to),
                          ]
                if ids:
                    domain.append(('holiday_id','not in',ids))
                    
                line_ids = holiday_line_obj.search(cr, uid, domain, order='date asc')
                if line_ids:
                    #Check if line ids belong to confirm-validate holiday
                    lines = holiday_line_obj.read(cr, uid, line_ids, ['date','holiday_id'])
                    for line in lines:
                        date = line.get('date', False)
                        date = datetime.strptime(date, DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%m-%Y')
                        holiday_id = line.get('holiday_id', False) and line['holiday_id'][0]
                        if holiday_id:
                            search_ids = self.search(cr, uid, [('id','=',holiday_id),
                                                               ('state','!=','refuse')])
                            if search_ids:
                                list_date.append(date)
        
        if list_date:
            list_date = sorted(list_date, key=lambda x: datetime.strptime(x, '%d-%m-%Y'))
        return list_date

    def onchange_date_range(self, cr, uid, ids, employee_id, company_id, holiday_status_id, date_to, date_from,
                            holiday_line_ids, is_offline=True, is_change_from_employee=False, check_to_date_insurance=False, context=None):
        # date_to has to be greater than date_from
        if not context:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]
        
        
            
        if 'is_change_date_to_by_hand' in context and not context.get('is_change_date_to_by_hand', False):
            return {'value': {'is_change_date_to_by_hand': True}}
        
        result = {'value': {'holiday_line_ids':[(6, 0, [])]}, 'warning': {}}
        
        holiday_line_obj = self.pool.get('vhr.holiday.line')
        leave_type_obj = self.pool.get('hr.holidays.status')
        leave_type_group_obj = self.pool.get('hr.holidays.status.group')
        parameter_obj = self.pool.get('ir.config_parameter')
        result['value']['alert_note'] = ''
        special_holiday_status_ids = []
        
        current_year = datetime.now().year
        
        if is_change_from_employee:
            result['value']['is_change_from_employee'] = False
            return result
        
        state = False
        if ids:
            record = self.read(cr, uid, ids[0], ['state'])
            state = record.get('state', False)
        
        leave_type_code_for_cut_off_detail = parameter_obj.get_param(cr, uid, 'vhr_timesheet_leave_type_only_remove_out_of_day_when_onchange_date_range') or ''
        leave_type_code_for_cut_off_detail = leave_type_code_for_cut_off_detail.split(',')
        leave_type_for_cut_off_detail_ids = leave_type_obj.search(cr, uid, [('code','in',leave_type_code_for_cut_off_detail)])
        
        #Check nếu trừ số phép bằng số ca nghỉ hay không (không dựa vào số ngày công của ca nghỉ)
#         is_by_day_of_leave = True
#         leave_group_follow_rule_workday = parameter_obj.get_param(cr, uid, 'vhr_timesheet_leave_type_code_follow_rule_workday') or ''
#         leave_group_follow_rule_workday = special_holiday_status_code.split(',')
#         leave_group_follow_rule_workday_ids = leave_type_group_obj.search(cr, uid, [('code','in',leave_group_follow_rule_workday)])
#         leave_follow_rule_workday_ids = self.search(cr, uid, [('holiday_status_group_id','in',leave_group_follow_rule_workday_ids)])
#         if set(ids).intersection(set(leave_follow_rule_workday_ids)):
#             is_by_day_of_leave = False
            
        if date_from and len(date_from) > 10:
            date_from = date_from[:10]
        if not is_offline and state not in ['validate','validate2']:
            current_date = fields.date.today()
            if date_from < current_date:
                result['value']['date_from'] = current_date
                result['warning'] = {'title': _('Warning!'),
                                     'message': _('You can\'t create/update a leave request in the past!')}
                return result
        
        #Update to date insurance and date_to if leave type belong to group sinh con and employee change date_from
        if context.get('change_date_from', False):
            #Nếu leave type có check_to_date_insurance = True, gán to_date_insurance = date_to = date_from + timelines days
            result = self.update_data_for_leave_type_insurance(cr, uid, result, employee_id, company_id, date_from, holiday_status_id, context)
            if 'date_to' in result.get('value',{}):
                date_to = result['value']['date_to']
        
        if date_from and date_to:
            if date_from > date_to:
                result['value']['date_to'] = date_from
                date_to = date_from
#                 return result
            
#             if check_to_date_insurance:
#                 result['value']['to_date_insurance'] = date_to
        
            #Test if choose leave type loai nghi tet, employee can only choose date range consist ngay le tet
            is_correct = self.check_if_take_correct_leave_request_on_leave_type_holiday(cr, uid, holiday_status_id, date_from, date_to, context)
            if not is_correct:
                result['value']['alert_note'] = _('Leave days which you submit not be holidays. \n\
                                                 Please try to choose other leave type!')
                return result
            
            #OT and annual leave
            special_holiday_status_code = parameter_obj.get_param(cr, uid, 'leave_type_code_for_accumulation') or ''
            special_holiday_status_code = special_holiday_status_code.split(',')
            special_holiday_status_ids = leave_type_obj.search(cr, uid, [('code','in',special_holiday_status_code)])
            
            #If have ot day compensation, default will show that message if holiday_status is annual leave
            code = parameter_obj.get_param(cr, uid, 'ts.leave.type.default.code').split(',')
            default_leave_type_ids = self.pool.get('hr.holidays.status').search(cr, uid, [('code', 'in', code)])
            
            if holiday_status_id in default_leave_type_ids and context.get('alert_note_temp',False):
                result['value']['alert_note'] = context.get('alert_note_temp','')
            
        if not employee_id or not holiday_status_id:
            return result
        
        holiday_status = leave_type_obj.browse(cr, uid, holiday_status_id)
        
        is_allow_register_next_year = False
        limit = leave_type_obj.read(cr, uid, holiday_status_id, ['limit']).get('limit', False)
        
        if date_from and date_to:
            date_from_year = datetime.strptime(date_from, DEFAULT_SERVER_DATE_FORMAT).year
            date_to_year = datetime.strptime(date_to, DEFAULT_SERVER_DATE_FORMAT).year
            #Only allow to register from this year to next year if is_allow_to_register_from_now_to_next_year = True
            if date_from_year != date_to_year:
                if not holiday_status.is_allow_to_register_from_now_to_next_year:
                    result['value']['date_to'] = '%s-12-31' % date_from_year
                    result['warning'] = {'title': _('Warning!'),
                                         'message': _('Date From and Date To must be in a year!')}
                    return result
                else:
                    is_allow_register_next_year = True
                    
            elif date_from_year == current_year + 1 and holiday_status.is_allow_to_register_from_now_to_next_year:
                is_allow_register_next_year = True
        
        result['value']['is_register_next_year'] = is_allow_register_next_year
        
        number_of_days_temp = 0
        # Compute and update the number of days
        holiday_line_ids = []
        list_date_duplicate = []
        
        maintain_line_ids = []
        if date_from:
            list_date = []
            dict_hours = {}
            dict_type_workday = {}
            # delete all before generate
            if holiday_status_id:
                leave_days = leave_type_obj.get_days(cr, uid, [holiday_status_id], employee_id, company_id, date_from).get(holiday_status_id, {})
                result['value'].update(leave_days)
                max_leaves = leave_days['max_leaves']
                remain_days_of_pre_year = leave_days['remain_days_of_pre_year']
                expiry_date_of_days_pre_year = leave_days['expiry_date_of_days_pre_year']
                max_leaves_rounded = int(round(max_leaves))
                if date_to:
                    
                    list_overlap_date = self.check_if_take_birth_leave_on_leave_date(cr, uid, ids, employee_id, holiday_status_id, date_from, date_to, context)
                    if list_overlap_date:
                        result['value']['holiday_line_ids'] = [(6, 0, [])]
                        result['value']['number_of_days_temp'] = 0
                        #Change to english later (lazy)
                        str_overlap_date = str(list_overlap_date)
                        str_overlap_date = str_overlap_date.replace("'", "").replace('[', '').replace(']', '')
                        result['value']['alert_note'] = _('Bạn đã đăng ký nghỉ phép ngày %s trùng với thời gian nghỉ sinh. \
                                                           Vui lòng báo Admin cancel ngày nghỉ phép để cập nhật nghỉ Sinh con') % str_overlap_date
                        return result
                    
                    
                    list_date, dict_hours, dict_type_workday = self.generate_date(cr, uid, employee_id, company_id, date_from[:10], date_to[:10])
                    if list_date:
                        list_date, list_date_duplicate = self.remove_duplicate_days(cr, ids, employee_id, list_date)
                    result['value']['number_of_days_duplicate'] = len(list_date_duplicate)

                    ''' Raise message if list_date = null '''
                    if not list_date and not is_allow_register_next_year:
                        result['value']['holiday_line_ids'] = [(6, 0, [])]
                        result['value']['number_of_days_temp'] = 0
                        result['value']['alert_note'] = _('Không tìm thấy lịch làm việc trong khoảng thời gian chọn.\n\
                                                          Vui lòng chọn lại ngày hoặc liên hệ C&B để được hỗ trợ!')
                        if list_date_duplicate:
                            result['value']['alert_note'] = _('Ngày nghỉ này đã được đăng ký, vui lòng cập nhật ngày nghỉ khác')
                            result['warning'] = {}
                        return result
                    
                    '''Compare list_date with max_leaves_rounded(max days can register)  '''
                    if limit:
                        pass
                    else:
                        #For case edit leave request in waiting lm/finish, that time max leave should consist of number of days temp to get real max leave
                        check_max_leaves = max_leaves_rounded
                        if ids:
                            records = self.read(cr, uid, ids, ['state','number_of_days_temp'])
                            if records[0].get('state') in ['draft','confirm','validate']:
                                check_max_leaves += records[0].get('number_of_days_temp')
                            
                        if leave_days['remaining_leaves'] < 0 or leave_days['virtual_remaining_leaves'] < 0 or (not list_date and not is_allow_register_next_year):
                            result['value']['number_of_days_temp'] = 0
                            result['value']['alert_note'] = _('The number of remaining days is not sufficient for this leave type.\n\
                                                             Please try to choose other leave type!')

                    '''Get days employee has leave a half of day/work for only half of day'''
                    list_haft_date_info, list_haft_date_name,list_date_must_full_leave = self.get_haft_date_info(cr, uid, ids, employee_id, list_date)
#                     total_leave_hours = 0
                    print 'dict_hours=',dict_hours
                    for val in list_date:
                        status = 'full'
                        line_number_of_days = dict_type_workday.get(val,1)
                        is_edit_status = True
                        do_not_show_date = False
                        if val in list_haft_date_name:
                            line_number_of_days = line_number_of_days * 0.5
                            for item in list_haft_date_info:
                                if item['date'] == val:
                                    status = item['status'] == 'morning' and 'afternoon' or 'morning'
                                    is_edit_status = False
                                    do_not_show_date = item.get('do_not_show', False)
                        
                        elif val in list_date_must_full_leave:
                            is_edit_status = False
                        
                        number_of_days_temp += line_number_of_days
                        #Case: at date val, employee have shift = 0.5 day and employee had leave request on that day, so employee don't have any working time on that day to take leave
                        if do_not_show_date:
                            continue
                        line_data = {'date': val,
                                     'status': status,
                                     'number_of_days_temp': line_number_of_days,
                                     'is_edit_status': is_edit_status,
                                     'number_of_hours_in_shift': val in dict_hours and dict_hours[val] or 0,
                                     'number_of_hours': (val in dict_hours and dict_hours[val] or 0) * line_number_of_days 
                                                                                                / dict_type_workday.get(val,1)}
#                         total_leave_hours += line_data.get('number_of_hours',0)
                        is_append = True
                        #Đối với các loại phép như nghỉ sinh con, nếu sửa lại date range tại state!=draft 
                        #mà các detail cũ nếu giống detail mới thì không xóa đi
                        if state != 'draft' and holiday_status_id in leave_type_for_cut_off_detail_ids:
                            line_ids = holiday_line_obj.search(cr, uid, [('date','=',val),
                                                                         ('status','=',status),
#                                                                          ('number_of_days_temp','=',line_number_of_days),
                                                                         ('employee_id','=',employee_id)])
                            if line_ids:
                                holiday_line_ids.append((4, line_ids[0], False))
                                maintain_line_ids.append(line_ids[0])
                                is_append = False
                            
                        if is_append:
                            holiday_line_ids.append((0, 0, line_data))
                    
#                     if total_leave_hours:
#                         number_of_days_temp = float("{0:.1f}".format(total_leave_hours / 8.0))
                            
                    if not limit:
                        
#                         if max_leaves < number_of_days_temp and holiday_line_ids:
#                             holiday_line_ids[-1][2]['status'] = 'morning'
#                             holiday_line_ids[-1][2]['number_of_days_temp'] = 0.5
#                             holiday_line_ids[-1][2]['number_of_hours'] = (val in dict_hours and dict_hours[val] or 0) * 0.5
#                             total_leave_hours -= (val in dict_hours and dict_hours[val] or 0) * 0.5
                        
                        if number_of_days_temp > check_max_leaves: # and not result['value']['alert_note']:
                            result['value']['alert_note'] = _("Số ngày đăng ký vượt quá số ngày được cho phép, vui lòng kiểm tra lại!")
                
                is_over = self.is_over_leave_from_before_to_after_expire_pre_days(cr, uid, holiday_status_id, employee_id, company_id, date_from, expiry_date_of_days_pre_year, date_to, remain_days_of_pre_year, context)
                if is_over:
                    result['value']['alert_note'] = _("Số ngày đăng ký vượt quá số ngày được cho phép, vui lòng kiểm tra lại!")
                    
        result['value']['number_of_days_temp'] = number_of_days_temp
        
        holiday_line_obj = holiday_line_obj
        temp_holiday_line_ids = holiday_line_obj.search(cr, uid, [('holiday_id', 'in', ids)])
        
        temp_holiday_line_ids = set(temp_holiday_line_ids).difference(maintain_line_ids)
        for line_id in temp_holiday_line_ids:
            holiday_line_ids.append([2, line_id, False])
        result['value']['holiday_line_ids'] = holiday_line_ids
        
        
        if not holiday_line_ids and date_from and date_to and not result['warning'] and not is_allow_register_next_year:
            if list_date_duplicate:
                result['value']['alert_note'] = _('Ngày nghỉ này đã được đăng ký, vui lòng cập nhật ngày nghỉ khác!')
            else:
                result['value']['alert_note'] = _('Không tìm thấy lịch làm việc trong khoảng thời gian chọn, \n Vui lòng chọn lại ngày hoặc liên hệ C&B để được hỗ trợ!')
        
        if result['value'].get('date_to', False):
            result['value']['is_change_date_to_by_hand'] = False    
        
        return result

    def is_empty_line(self, cr, uid, holiday_line_ids, context=None):
        result = True
        if holiday_line_ids:
            for line in holiday_line_ids:
                if line and line[0] != 2:
                    result = False
                    break
        
        return result

    def onchange_holiday_line(self, cr, uid, ids, holiday_line_ids, holiday_status_id, max_leaves, context=None):
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]
            
        alert_number_of_days_are_over_max_leave = _("Số ngày đăng ký vượt quá số ngày được cho phép, vui lòng kiểm tra lại!")
        res = {'value': {'number_of_days_temp': 0, 'number_of_hours': 0}}
        holiday_line_obj = self.pool.get('vhr.holiday.line')
        parameter_obj = self.pool.get('ir.config_parameter')
        
        code = parameter_obj.get_param(cr, uid, 'ts.leave.type.default.code').split(',')
        default_leave_type_ids = self.pool.get('hr.holidays.status').search(cr, uid, [('code', 'in', code)])
        
        employee_id = context.get('employee_id', False)
        date_from = context.get('date_from', False)
        date_to = context.get('date_to', False)
        
        #Compute to get correct date_from if user delete row holiday line
        date_from, greatest_date = self.get_lowest_date_and_greatest_date_from_holiday_line(cr, uid, holiday_line_ids, date_from, date_to, context)
        
        is_register_to_next_year = False
        is_date_range_include_rest_date = False
        #Nếu holiday status có tính cả thứ 7 chủ nhật hoặc đăng ký sang năm sau thì tính number_of_days_temp = date_to - date_from + 1
        if date_from and date_to:
            holiday_status = self.pool.get('hr.holidays.status').browse(cr, uid, holiday_status_id)
            is_register_to_next_year = holiday_status.is_allow_to_register_from_now_to_next_year
            if is_register_to_next_year:
                is_register_to_next_year = self.is_register_from_this_year_to_next_year(cr, uid, date_from, date_to, context)
            
            is_date_range_include_rest_date = holiday_status.is_date_range_include_rest_date
                
        if self.is_empty_line(cr, uid, holiday_line_ids, context):
            if context.get('alert_note',False) == alert_number_of_days_are_over_max_leave:
                res['value']['alert_note'] = ''
            
            if (not context.get('alert_note',False) or ('alert_note' in res['value'] and not res['value'].get('alert_note',False))) \
              and not is_register_to_next_year:
                res['value']['date_to'] = False
        
        #If have ot day compensation, default will show that message if holiday_status is annual leave
        if holiday_status_id and holiday_status_id in default_leave_type_ids \
          and not context.get('alert_note',False) and context.get('alert_note_temp',False):
            res['value']['alert_note'] = context.get('alert_note_temp','')
                
        if not max_leaves:
            max_leaves = 0
        
        if holiday_line_ids:
            
            number_of_days_temp, number_of_hours, number_of_leave_days = self.get_total_days_hours_of_holiday_line(cr, uid, holiday_line_ids, context)
            
            m_date_to = date_to
            only_register_next_year = False
            gap_first_date_and_date_to_next_year = 0
            if is_register_to_next_year:
                date_from_dt = datetime.strptime(date_from, DEFAULT_SERVER_DATE_FORMAT)
                
                #Only check if request from current year to next year
                if date_from_dt.year == datetime.now().year:
                    #get first_date_of_next_year if date_from at current year
                    new_date_from = self.recompute_date_start_leave_request(cr, uid, date_from, context)
                    
                    m_date_to = date(datetime.now().year, 12, 31).strftime(DEFAULT_SERVER_DATE_FORMAT)
                    
                    gap_first_date_and_date_to_next_year = self.compare_day(new_date_from, date_to) + 1
                    if self.compare_day(new_date_from, date_from) == 0:
                        #not need to check later condition
                        only_register_next_year = True
                
            
            number_of_days_temp_current_year = number_of_days_temp
            #Case tính cả ngày nghỉ vào number_of_days_temp và có đăng ký phép của năm nay
            if is_date_range_include_rest_date and not only_register_next_year:
                number_of_days_temp_current_year = self.compare_day(date_from, m_date_to) + 1
                number_of_days_temp_current_year -= (number_of_leave_days - number_of_days_temp)#Nếu có line là half day thì phải trừ ra
                
                #Tìm những dòng đã đăng ký phép full ngày để loại ra (dòng half days đã bị remove ở dòng trên)
                if employee_id:
                    line_ids = holiday_line_obj.search(cr, uid, [('employee_id','=',employee_id),
                                                                 ('date','>=',date_from),
                                                                 ('date','<=',m_date_to),
                                                                 ('number_of_days_temp','=',1),
                                                                 ('holiday_id','not in',ids)])
                    if line_ids:
                        rm_days = 0
                        lines = holiday_line_obj.read(cr, uid, line_ids, ['number_of_days_temp','holiday_id'])
                        for line in lines:
                            holiday_id = line.get('holiday_id', False) and line['holiday_id'][0]
                            holiday = self.read(cr, uid, holiday_id, ['state'])
                            if holiday.get('state', False) not in ['cancel','refuse']:
                                rm_days += line.get('number_of_days_temp', 0)
                        
                        number_of_days_temp_current_year -= rm_days
                    
                
            elif not is_date_range_include_rest_date:
                #Trong trường hợp không tính ngày nghỉ thì số ngày xin nghỉ của năm sau không thể xác định được
                gap_first_date_and_date_to_next_year = 0
            
            number_of_days_temp = gap_first_date_and_date_to_next_year + number_of_days_temp_current_year
            
                    
            res['value']['number_of_days_temp'] = number_of_days_temp
            res['value']['number_of_hours'] = number_of_hours
            if context.get('multi'):
                return res
            if holiday_status_id:
                record = self.pool.get('hr.holidays.status').read(cr, uid, holiday_status_id, ['limit'])
                limit = record.get('limit', False)
                if not limit:
                    #For case edit leave request in waiting lm/finish, that time max leave should consist of number of days temp to get real max leave
                    check_max_leaves = max_leaves
                    if ids:
                        records = self.read(cr, uid, ids, ['state','number_of_days_temp','number_of_hours'])
                        if records[0].get('state',False) in ['draft','confirm','validate']:
#                             if records[0].get('number_of_hours',False):
#                                 check_max_leaves += records[0].get('number_of_hours') / 8.0
#                             else:
                            check_max_leaves += records[0].get('number_of_days_temp')
                    
                        
#                     if number_of_hours and number_of_hours / 8.0 > check_max_leaves:
#                         res['value']['alert_note'] = alert_number_of_days_are_over_max_leave
                        
                    if number_of_days_temp > check_max_leaves:
                        res['value']['alert_note'] = alert_number_of_days_are_over_max_leave
                    else:
                        res['value']['alert_note'] = ''
                        
                        if holiday_status_id and holiday_status_id in default_leave_type_ids and context.get('alert_note_temp',False):
                            res['value']['alert_note'] = context.get('alert_note_temp','')
                            
        elif is_date_range_include_rest_date and is_register_to_next_year:
            #Tạm thời chỉ có thể xác định số ngày nghỉ phép dăng ký vào năm sau nếu loại leave type là nghỉ cả ngày t7, cn
            new_date_from = self.recompute_date_start_leave_request(cr, uid, date_from, context)
                
            gap_first_date_and_date_to_next_year = self.compare_day(new_date_from, date_to) + 1
            res['value']['number_of_days_temp'] = gap_first_date_and_date_to_next_year
        
        return res
    
    def get_total_days_hours_of_holiday_line(self, cr, uid, holiday_line_ids, context=None):
        holiday_line_obj = self.pool.get('vhr.holiday.line')
        number_of_days_temp = 0
        number_of_hours = 0
        #This field only count how many days user take leave
        number_of_leave_days = 0
        #This field to prevent user cb try to change holiday line with old data leave request dont have number of hours
        is_number_of_hours_in_line = True
        
        for detail in holiday_line_ids:
            if detail[0] == 0:
                number_of_leave_days += 1
                line_number_of_days_temp = detail[2]['number_of_days_temp']
                number_of_days_temp += line_number_of_days_temp
                
                if is_number_of_hours_in_line:
                    is_number_of_hours_in_line = detail[2].get('number_of_hours',0)
                    number_of_hours_temp = detail[2].get('number_of_hours',0)
                    number_of_hours += number_of_hours_temp
                
            if detail[0] == 1:
                number_of_leave_days += 1
#                 status = detail[2].get('status')
#                 if status:
#                     if status == 'full':
#                         number_of_days_temp += 1
#                     else:
#                         number_of_days_temp += 0.5
                
                number_of_days_temp_line = detail[2].get('number_of_days_temp', 0)
                number_of_days_temp +=number_of_days_temp_line
                
                if is_number_of_hours_in_line:
                    is_number_of_hours_in_line = detail[2].get('number_of_hours',0)
                    number_of_hours += detail[2].get('number_of_hours',0)
                
        existing_line_ids = map(lambda x: x[1], filter(lambda x: x[0] == 4, holiday_line_ids))
        for line in holiday_line_obj.read(cr, uid, existing_line_ids, ['number_of_days_temp', 'date','number_of_hours']):
            number_of_leave_days += 1
            number_of_days_temp += line['number_of_days_temp']
            
            if is_number_of_hours_in_line:
                is_number_of_hours_in_line = line.get('number_of_hours',0)
                number_of_hours += line.get('number_of_hours',0)
        
        if not is_number_of_hours_in_line:
            number_of_hours = 0
        
        return number_of_days_temp, number_of_hours, number_of_leave_days
    
    def get_lowest_date_and_greatest_date_from_holiday_line(self, cr, uid, holiday_line_ids, date_from, date_to, context=None):
        holiday_line_obj = self.pool.get('vhr.holiday.line')
        
        existing_line_ids = map(lambda x: x[1], filter(lambda x: x[0] in [1,4], holiday_line_ids))
        lowest_date = (datetime.now() + relativedelta(years=12)).strftime(DEFAULT_SERVER_DATE_FORMAT)
        greatest_date = date_to
        if existing_line_ids:
            
            existing_line_ids = holiday_line_obj.search(cr, uid, [('id','in',existing_line_ids)], order = 'date asc')
            lowest_line = holiday_line_obj.read(cr, uid, existing_line_ids[0], ['date'])
            lowest_date = lowest_line.get('date', False)
            
            greatest_line = holiday_line_obj.read(cr, uid, existing_line_ids[-1], ['date'])
            greatest_date = greatest_line.get('date', False)
        
        for detail in holiday_line_ids:
            if detail[0] == 0:
                if self.compare_day(lowest_date, detail[2]['date'])<0:
                    lowest_date = detail[2]['date']
                
                if self.compare_day(greatest_date, detail[2]['date']) >0:
                    greatest_date = detail[2]['date']
        
        #If dont have any change wih lowest_date, set lowest_date = date_from
        if date_to and self.compare_day(date_to, lowest_date) > 0:
            lowest_date = date_from
        
        return lowest_date, greatest_date
    
    def get_current_working_group_of_employee(self, cr, uid, employee_id, context=None):
        '''
            Base on current working record of main contract to get current working group
        '''
        working_group_id = False
        working_group_code = ''
        working_group_name_tuple = False
        if employee_id:
            date = datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT)
            working_record_obj = self.pool.get('vhr.working.record')
            #Get all WR effect on public date
            wr_ids = working_record_obj.search(cr, uid, [('employee_id','=',employee_id),
                                                         ('state','in',[False,'finish']),
                                                         '|',('active','=',False),('active','=',True),
                                                        ('effect_from','<=',date),
                                                        '|',('effect_to','>=',date),('effect_to','=',False)])
            if wr_ids:
                main_wr_id = wr_ids[0]
                #If employee have more than 1 WR on public date, choose WR from main company or company emp worked early or first company
                if len(wr_ids) >1:
                    #Get main company to get working group from
                    main_wr_id = False
                    main_contract_date_start = False
                    workings = working_record_obj.browse(cr, uid, wr_ids, fields_process=['contract'])
                    for working in workings:
                        if working.contract_id and working.contract_id.is_main:
                            if not main_wr_id:
                                main_wr_id = working['id']
                                main_contract_date_start = working.contract_id.date_start
                            else:
                                #Change to other contract if that contract have date_start < current date_start
                                is_greater = self.compare_day(main_contract_date_start, working.contract_id.date_start)
                                if is_greater < 0:
                                    main_wr_id = working['id']
                                    main_contract_date_start = working.contract_id.date_start
                    
                    if not main_wr_id:
                        main_wr_id = wr_ids[0]
                
                working = working_record_obj.browse(cr, uid, main_wr_id, fields_process=['ts_working_group_id_new'])  
                working_group_name_tuple = working_record_obj.read(cr, uid, main_wr_id, ['ts_working_group_id_new']).get('ts_working_group_id_new', False)
                working_group_id = working.ts_working_group_id_new and working.ts_working_group_id_new.id or False
                working_group_code = working.ts_working_group_id_new and working.ts_working_group_id_new.code or False
        
        return working_group_id, working_group_code, working_group_name_tuple

    def onchange_employee_id(self, cr, uid, ids, employee_id, holiday_status_id, date_from=False, date_to=False,
                             holiday_line_ids=False, number_of_days_temp=0, is_offline = False, context=None):
        res = {'value': {}, 'domain': {}, 'warning': {}}
        log.info('call onchange employee-----')
        if employee_id:
            if date_from and len(date_from) > 10:
                date_from = date_from[:10]
                res['value']['date_from'] = date_from
            holiday_status_id = False
            res['value']['holiday_status_id'] = False
            if date_to:
                date_to = False
                res['value']['date_to'] = False
                res['value']['is_change_from_employee'] = True
                res['value']['number_of_days_temp'] = 0
                
            employee_obj = self.pool.get('hr.employee')
            
            company_id = False
            # company_id, company_ids = employee_obj.get_company_ids(cr, uid, employee_id)
            # res['value']['company_id'] = company_id
            # res['domain']['company_id'] = [('id', 'in', company_ids)]
            employee_instance = employee_obj.browse(cr, uid, employee_id, fields_process=['name', 'code', 'gender'])
            res['value']['employee_code'] = employee_instance.code or ''
            # still use onchange_company for good
            res_company = self.onchange_company_id(cr, uid, ids, employee_id, company_id, holiday_status_id, date_from,
                                                   date_to, holiday_line_ids, number_of_days_temp, is_offline, context=context)
            res['value'].update(res_company.get('value', {}))
            if 'holiday_status_id' in res['value'] == holiday_status_id:
                del res['value']['holiday_status_id']
            
            res['domain'].update(res_company.get('domain', {}))
            res['warning'].update(res_company.get('warning', {}))
            
            
        return res
    
    def get_domain_of_holiday_status_id(self, cr, uid, employee_id, context=None):
        domain = []
        if employee_id:
            parameter_obj = self.pool.get('ir.config_parameter')
            holiday_status_obj = self.pool.get('hr.holidays.status')
            working_group_id, working_group_code, tuple = self.get_current_working_group_of_employee(cr, uid, employee_id, context)
            working_group_show_lt_code = parameter_obj.get_param(cr, uid, 'working_group_show_leave_type_letet_cs_cl') or ''
            working_group_show_lt_code = working_group_show_lt_code.split(',')
            if not working_group_code in working_group_show_lt_code:
                letet_leave_type_code = parameter_obj.get_param(cr, uid, 'holiday_status_letet_cs_calich') or ''
                letet_leave_type_code = letet_leave_type_code.split(',')
                letet_leave_type_ids = holiday_status_obj.search(cr, uid, [('code','in',letet_leave_type_code)])
                domain.append(('id','not in', letet_leave_type_ids))
            
            #Dont show leave type have "is_require_children=True" if employee dont have children
            children_ids = []
            type_ids = self.pool.get('vhr.relationship.type').search(cr, uid, [('active','=',True),
                                                                                '|','|',('name','in',['Son','Girl']),
                                                                                        ('name_en','in',['Son','Girl']),
                                                                                       ('name','ilike','Con')
                                                                                    ])
            if type_ids:
                children_ids = self.pool.get('vhr.employee.partner').search(cr, uid, [('employee_id','=',employee_id),
                                                                                     ('active','=',True),
                                                                                     ('relationship_id','in',type_ids)])
            if not children_ids:
                domain.append(('is_require_children','=',False))
            
        return domain
        

    def is_collaborator_or_probation(self, cr, uid, employee_id, company_id, context=None):
        """
        If user has all contract type is collaborator then user is collaborator
        or not
        :param cr:
        :param uid:
        :param employee_id:
        :param company_id:
        :return:
        """
        if not context:
            context = {}
        
        is_collaborator = False
        is_probation = False
        
        param_obj = self.pool.get('ir.config_parameter')
        collaborator_contact_type_group_code = param_obj.get_param(cr, uid, 'vhr.human.resource.ts.param.contract.type.group.collaborator') or ''
        collaborator_contact_type_group_code = collaborator_contact_type_group_code.split(',')
        
        probation_contact_type_group_code = param_obj.get_param(cr, uid, 'vhr_human_resource_probation_contract_type_group_code') or ''
        probation_contact_type_group_code = probation_contact_type_group_code.split(',')
        
        colla_service_contact_type_group_code = param_obj.get_param(cr, uid, 'vhr_human_resource_colla_service_contract_type_group_code') or ''
        colla_service_contact_type_group_code = colla_service_contact_type_group_code.split(',')
        
        contract_obj = self.pool.get('hr.contract')
        today = datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT)
        active_contract_domain = [('employee_id', '=', employee_id),
                                  # ('company_id', '=', company_id),
                                  ('state', '=', 'signed'),
                                  '|', '|',
                                  '&', '&',
                                  ('date_end', '=', False),
                                  ('liquidation_date', '=', False),
                                  ('date_start', '<=', today),
                                  '&', '&',
                                  ('liquidation_date', '=', False),
                                  ('date_start', '<=', today),
                                  ('date_end', '>=', today),
                                  '&', '&',
                                  ('liquidation_date', '!=', False),
                                  ('date_start', '<=', today),
                                  ('liquidation_date', '>=', today)]
        contract_ids = contract_obj.search(cr, uid, active_contract_domain)
        count_collaborator = 0
        count_probation = 0

        if not contract_ids:
            #Search for latest contract before today
            nearest_contract_domain = [('employee_id', '=', employee_id),
                                       ('state', '=', 'signed'),
                                       ('date_start', '<=', today)]
            contract_ids = contract_obj.search(cr, uid, nearest_contract_domain, order='date_start desc', limit=1)
            
            #For case create annual leave for employee when active first working record, because of thread, can not find contract with state signed
            if not contract_ids and context.get('signed_contract', False):
                contract_ids = [context['signed_contract']]
            
            if not contract_ids:
                log.info('Can not find any active contract for employee %s'% employee_id)
                raise osv.except_osv(_('Warning!'),
                                     _('You don\'t have any contract until today!'
                                       '\nPlease contact to C&B to renew your contract before create leave request!'))

        for contract in contract_obj.browse(cr, SUPERUSER_ID, contract_ids, fields_process=['type_id']):
            contract_type_group_code = contract.type_id  and contract.type_id.contract_type_group_id and contract.type_id.contract_type_group_id.code or False
            if contract_type_group_code in collaborator_contact_type_group_code:
                count_collaborator += 1
                
            if contract_type_group_code in probation_contact_type_group_code or contract_type_group_code in colla_service_contact_type_group_code:
                count_probation += 1
                
                    
        if count_collaborator == len(contract_ids):
            is_collaborator = True
        
        if count_probation == len(contract_ids):
            is_probation = True
            
        return is_collaborator, is_probation

    def onchange_company_id(self, cr, uid, ids, employee_id, company_id, holiday_status_id, date_from=False,
                            date_to=False, holiday_line_ids=False, number_of_days_temp=0, is_offline=False, context=None):
        if not context:
            context = {}
        res = {'value': {}, 'domain': {}, 'warning': {}}
        if employee_id:
            if date_from and len(date_from) > 10:
                date_from = date_from[:10]
            employee_info = self.pool.get('hr.employee').browse(cr, uid, employee_id,
                                                                fields_process=['department_id', 'report_to'])
            res['value']['department_id'] = employee_info.department_id and employee_info.department_id.id or False
            res['value']['report_to_id'] = employee_info.report_to and employee_info.report_to.id or False
            res['value']['dept_head_id'] = employee_info.department_id and employee_info.department_id.manager_id \
                                           and employee_info.department_id.manager_id.id or False
            #
            holiday_ids, status_ids = self.get_overtime_allocation(cr, uid, employee_id, company_id, date_from,
                                                                   context=context)
            if holiday_ids:
                #If from menu Update For Leave, dont automatic change default leave type
                if context.get('update_for_leave', False):
                    status_ids = []
                holiday_status_id = status_ids and status_ids[0] or False
                res['value']['holiday_status_id'] = holiday_status_id
            if not holiday_status_id:
                 holiday_status_id = self._get_default_holiday_status(cr, uid, employee_id,
                                                                                     company_id=company_id,
                                                                                     context=context)
                 res['value']['holiday_status_id'] = holiday_status_id
            if holiday_status_id:
                res_status = self.onchange_holiday_status_id(cr, uid, ids, employee_id, company_id, holiday_status_id,
                                                             date_from, date_to, holiday_line_ids, number_of_days_temp,
                                                             is_offline, context=context)
                res['value'].update(res_status.get('value', {}))
                res['domain'].update(res_status.get('domain', {}))
                res['warning'].update(res_status.get('warning', {}))
                
        return res

    # not used at the time because get department from hr.employee
    def get_employee_department(self, cr, uid, employee_id, company_id=False, context=None):
        lst_dep = []
        working_record_obj = self.pool.get('vhr.working.record')
        record_ids = working_record_obj.search(cr, uid, [('employee_id', '=', employee_id),
                                                         ('company_id', '=', company_id),
                                                         ('state','in',[False,'finish']),
                                                         ('active', '=', True)])
        if record_ids:
            for wr in working_record_obj.read(cr, uid, record_ids, ['department_id_new', 'report_to_new'],
                                              context=context):
                lst_dep.append(wr)
        return lst_dep

    def update_insurance_date(self, cr, uid, employee_id, company_id, date_from, holiday_status_id, context=None):
        '''
            Update and show insurance to date if leave type has check_to_date_insurance = True
        '''
#         parameter_obj = self.pool.get('ir.config_parameter')
#         leave_type_insurance_group_code = parameter_obj.get_param(cr, uid, 'leave_type_group_code_show_insurance_day') or ''
#         leave_type_insurance_group_code = leave_type_insurance_group_code.split(',')
        
        holiday_status_instance = self.pool.get('hr.holidays.status').browse(cr, uid, holiday_status_id, context=context)
        
        instance_timelines = int(holiday_status_instance.timelines)
        check_to_date_insurance = False
        to_date_insurance = False
        
        holiday_status_group_code = holiday_status_instance.holiday_status_group_id and holiday_status_instance.holiday_status_group_id.code or False
        is_date_range_include_rest_date = holiday_status_instance.is_date_range_include_rest_date
        
        if holiday_status_instance.check_to_date_insurance and date_from and instance_timelines and holiday_status_instance.date_type:
            check_to_date_insurance = holiday_status_instance.check_to_date_insurance
            date_from = datetime.strptime(date_from, DEFAULT_SERVER_DATE_FORMAT)
            if holiday_status_instance.date_type == 'month':
                to_date_insurance = date_from + relativedelta(months=instance_timelines) - timedelta(days=1)
            elif holiday_status_instance.date_type == 'year':
                to_date_insurance = date_from + relativedelta(years=instance_timelines) - timedelta(days=1)
            else:
                
                to_date_insurance = date_from + timedelta(days=instance_timelines) - timedelta(days=1)
                
                if not is_date_range_include_rest_date and employee_id:
                    count_timelines = 0
                    index = -1
                    date_check = False
                    list_date = []
                    while count_timelines < instance_timelines:
                        index +=1
                        date_check = date_from + timedelta(days=index)
                        
                        is_working_date = self.is_date_in_working_schedule_employee(cr, uid, employee_id, company_id, date_check, context)
                        
                        if is_working_date:
                            number_of_day = self.get_number_of_days_can_register_on_day(cr, uid, employee_id, company_id, date_check, context)
                            add = 1 - number_of_day
                            count_timelines += add
                            if add > 0:
                                list_date.append(date_check.strftime(DEFAULT_SERVER_DATE_FORMAT))
                            
                    
                    if date_check:
                        to_date_insurance = date_check
                        
                
        return check_to_date_insurance, to_date_insurance
    
    def is_date_in_working_schedule_employee(self, cr, uid, employee_id, company_id = False, date=False, context=None):
        ws_detail_obj = self.pool.get('vhr.ts.ws.detail')
        ws_employee_obj = self.pool.get('vhr.ts.ws.employee')
        if employee_id and date:
            ws_employee_ids = ws_employee_obj.search(cr, uid, [('employee_id', '=', employee_id),
                                                           # ('company_id', '=', company_id),
                                                           '|',
                                                           ('active', '=', False),
                                                           ('active', '=', True),
                                                           ('effect_from', '<=', date),
                                                           '|', ('effect_to', '>=', date),
                                                           ('effect_to', '=', False)])
            #Khong choi voi employee lam tai 2 congty va co 2 working schedule employee khac nhau===> khong biet tinh sao
            if ws_employee_ids:
                ws_emp = ws_employee_obj.read(cr, uid, ws_employee_ids[0], ['ws_id'])
                ws_id = ws_emp.get('ws_id', False) and ws_emp['ws_id'][0]
                if ws_id:
                    ws_detail_ids = ws_detail_obj.search(cr, uid,[('ws_id', '=', ws_id), ('date', '=', date),('shift_id','!=',False)])
                    
                    if ws_detail_ids:
                        return True
        
        return False
    def get_number_of_days_can_register_on_day(self, cr, uid, employee_id, company_id, date, context=None):
        '''
        return number of days can register on day 
        return 1 of day is not register
        return 0.5 if a half of day is registered
        return 0 if day is registered
        '''
        registered_day = 0
        if employee_id and date:
            line_obj = self.pool.get('vhr.holiday.line')
            line_ids = line_obj.search(cr, uid, [('date','=',date),('employee_id','=',employee_id)])
            if line_ids:
                lines = line_obj.browse(cr, uid, line_ids, fields_process = ['number_of_days_temp','holiday_id'])
                registered_day = sum([line.number_of_days_temp for line in lines if line.holiday_id and line.holiday_id.state not in ['refuse','cancel']])
        
        return registered_day
                

    def onchange_holiday_status_id(self, cr, uid, ids, employee_id, company_id, holiday_status_id, date_from, date_to,
                                   holiday_line_ids, number_of_days_temp, is_offline, context=None):
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]
            
        res = {
            'value': {'holiday_status_description': 0, 'max_leaves': 0,
                      'leaves_taken': 0, 'remaining_leaves': 0,
                      'total_leaves': 0, 'virtual_remaining_leaves': 0},
            'domain': {},
            'warning': {}}
        res['value']['check_to_date_insurance'] = False
        res['value']['to_date_insurance'] = False
        
        leave_type_obj = self.pool.get('hr.holidays.status')
        config_obj = self.pool.get('ir.config_parameter')
        parameter_obj = config_obj
            
        check_to_date_insurance, to_date_insurance = False, False
        holiday_ids = []
        status_ids = []
        if employee_id:
            
            if date_from and len(date_from) > 10:
                date_from = date_from[:10]
            employee_obj = self.pool.get('hr.employee')
            employee_instance = employee_obj.browse(cr, uid, employee_id, fields_process=['name', 'code', 'gender'])
            
            res['domain']['holiday_status_id'] = [('holiday_status_group_id.gender', 'in',
                                                   ['both', employee_instance.gender])]
            
            #Only show leave type nghi le tet for employee belong to working group theo ca lich
            holiday_status_domain = self.get_domain_of_holiday_status_id(cr, SUPERUSER_ID, employee_id, context)
            if holiday_status_domain:
                res['domain']['holiday_status_id'].extend(holiday_status_domain)
                if isinstance(holiday_status_domain[0][2], list) and holiday_status_id in holiday_status_domain[0][2]:
                    res['value']['holiday_status_id'] = False
                    holiday_status_id = False
                
            # if company_id:
            is_collaborator, is_probation = self.is_collaborator_or_probation(cr, uid, employee_id, company_id, context)
            if is_collaborator:
                sub_domain = [('is_collaborator', '=', True)]
                emp_ids = self.get_colla_emp_satisfy_condition_to_gen_annual_leave(cr, uid, [employee_id], context)
                if emp_ids:
                    leave_type_code = parameter_obj.get_param(cr, uid, 'ts.leave.type.default.code').split(',')

                    status_id = leave_type_obj.search(cr, uid, [('code', 'in', leave_type_code)])
                    if status_id:
                        sub_domain.append(('id','=',status_id[0]))
                        sub_domain.insert(0,'|')
                
                res['domain']['holiday_status_id'].extend(sub_domain)
            elif is_probation:
                #Case nhan vien thu viec khong duoc dang ky outing - teambuilding - nghi phep nam, mac du la official
#                 leave_type_outing_teambuilding_code = parameter_obj.get_param(cr, uid, 'ts_leave_type_outing_teambuilding') or ''
#                 leave_type_outing_teambuilding_code = leave_type_outing_teambuilding_code.split(',')
                
                leave_type_annual_leave_code = parameter_obj.get_param(cr, uid, 'ts.leave.type.in.advance.code') or ''
                leave_type_annual_leave_code = leave_type_annual_leave_code.split(',')
                leave_type_domain = leave_type_annual_leave_code
#                 leave_type_domain.extend(leave_type_outing_teambuilding_code)
                res['domain']['holiday_status_id'].append(('code', 'not in', leave_type_domain))
                    
            # check user has overtime allocation or not
            if not context.get('forced_get_default_holiday_status'):
                holiday_ids, status_ids = self.get_overtime_allocation(cr, uid, employee_id, company_id, date_from, context=context)
            # NV Chinh Thuc
            code = parameter_obj.get_param(cr, uid, 'ts.leave.type.default.code').split(',')
            default_leave_type_ids = self.pool.get('hr.holidays.status').search(cr, uid, [('code', 'in', code)])
            if holiday_ids and holiday_status_id in default_leave_type_ids:
                # if user has overtime allocation and it still remain raise warning when user select other leave type.
                if holiday_status_id not in status_ids:
                    leave_type_name = leave_type_obj.read(cr, uid, status_ids[0], ['name']).get('name')
                    _holiday_status_id = status_ids and status_ids[0] or False
                    # res['value']['holiday_status_id'] = holiday_status_id
                    detail_holidays_status = leave_type_obj.get_days(cr, uid, [_holiday_status_id], employee_id,
                                                                     company_id, date_from,
                                                                     context=context).get(_holiday_status_id, {})

                    remaining_leaves = detail_holidays_status.get('remaining_leaves', 0)
                    #Only show message if have more than 0.5 day of ot work
                    if remaining_leaves >= 0.5:
                        res['value']['alert_note'] = _('Bạn vẫn còn %s ngày phép bù.\
                                                          \nBạn nên sử dụng hết trước khi sử dụng ngày phép năm !') % remaining_leaves
                        
                        #Use this to show message when change date range,
                        res['value']['alert_note_temp'] = res['value']['alert_note']
                   
            if holiday_status_id:
                holiday_status_instance = self.pool.get('hr.holidays.status').browse(cr, uid, holiday_status_id,
                                                                                     fields_process=[
                                                                                         'code',
                                                                                         'holiday_status_group_id',
                                                                                         'is_collaborator',
                                                                                         'check_to_date_insurance',
                                                                                         'timelines',
                                                                                         'date_type'],
                                                                                     context=context)
                # check leave type by gender of employee or is_collaborator
                if holiday_status_instance.holiday_status_group_id:
                    if holiday_status_instance.holiday_status_group_id.gender in ['both', employee_instance.gender] \
                            or is_collaborator \
                                    and holiday_status_instance.is_collaborator == is_collaborator:
                        pass
                    else:
                        new_context = context.copy()
                        new_context['offline'] = 1
                        holiday_status_id = self._get_default_holiday_status(cr, uid, employee_id, company_id,
                                                                             is_collaborator=is_collaborator,
                                                                             context=new_context)
                        res['value']['holiday_status_id'] = holiday_status_id
                detail_holidays_status = leave_type_obj.get_days(cr, uid, [holiday_status_id], employee_id,
                                                                 company_id, date_from,
                                                                 context=context).get(holiday_status_id, {})
                res['value'].update(detail_holidays_status)
                data = leave_type_obj.browse(cr, uid, holiday_status_id,
                                             fields_process=['description', 'limit'],
                                             context=context)
                
                # if leave type has insurance day - get it and put it in form.
                check_to_date_insurance, to_date_insurance = self.update_insurance_date(cr, uid, employee_id, company_id, date_from, holiday_status_id, context=context)
                to_date_insurance = to_date_insurance and to_date_insurance.strftime(DEFAULT_SERVER_DATE_FORMAT) or False
                res['value']['to_date_insurance'] = to_date_insurance
                res['value']['check_to_date_insurance'] = check_to_date_insurance
                if to_date_insurance:
                    res['value']['date_to'] = to_date_insurance
                    if (date_to and self.compare_day(date_to, to_date_insurance) != 0) or (not date_to and to_date_insurance):
                        res['value']['is_change_date_to_by_hand'] = False
                    date_to = to_date_insurance
                    
                
                #Get data from onchange date_range, to update Details
                state = False
                if ids:
                    records = self.read(cr, uid, ids, ['state'])
                    for record in records:
                        state = record.get('state', False)
                
                res_onchange = {}
                if state != 'validate':
                    res_onchange = self.onchange_date_range(cr, uid, ids, employee_id, company_id, holiday_status_id,
                                                            date_to,
                                                            date_from, holiday_line_ids, is_offline, False, False, context=context)
                
                res['value']['holiday_status_description'] = data.description
                
                #If have alert note from holiday status and not have alert note from  onchange date range
                if res['value'].get('alert_note') and res_onchange.get('value',{}) and not res_onchange['value'].get('alert_note'):
                    del res_onchange['value']['alert_note']
                    
                res['value'].update(res_onchange.get('value', {}))
                res['domain'].update(res_onchange.get('domain', {}))
                res['warning'].update(res_onchange.get('warning', {}))
                # check leave type is legal leaves
                show_full_info_code = config_obj.get_param(cr, uid, 'ts.leave.type.show.full.info.code').split(',')
                if holiday_status_instance.code in show_full_info_code:
                    res['value']['is_show_full_leave_information'] = True
                else:
                    res['value']['is_show_full_leave_information'] = data.limit and 'limit' or False
                
        
        # if not employee_id:
        # res['warning'] = {'message': _('Please select employee and company!'), 'title': _('Warning!')}
        return res

    # not used just override
    def onchange_type(self, cr, uid, ids, holiday_type, employee_id=False, context=None):
        result = {'value': {}}
        return result

    def _validate_number_of_days_temp(self, cr, uid, employee_id, company_id, number_of_days_temp, holiday_status_id, date_from):
        """
        
        :param cr:
        :param uid:
        :param employee_id:
        :param company_id:
        :param number_of_days_temp:
        :param holiday_status_id:
        :param date_from:
        :return: double_validation (this field used to define should the leave request move to dept head validate)
        Leave <= 5 ngày: chỉ cần LM duyệt

-       Leave > 5 ngày: Sau khi LM duyệt thì đi tiếp sang DH duyệt
        """
        res = {}
#         leave_detail = self.pool.get('hr.holidays.status').get_days(cr,
#                                                                     uid,
#                                                                     [holiday_status_id],
#                                                                     employee_id,
#                                                                     company_id,
#                                                                     date_from).get(holiday_status_id, {})
#         if leave_detail['advance_leaves'] \
#                 and number_of_days_temp - leave_detail['total_current_leaves'] >= leave_detail['advance_leaves']:
    
        param_obj = self.pool.get('ir.config_parameter')
        line_date = param_obj.get_param(cr, uid, 'vhr_timesheet_date_to_get_dh_approve_in_leave_request') or ''
        line_date = int(line_date)#6
        
        if number_of_days_temp >= line_date:
            #Đối với các leave type thuộc loại BHXH, không qua bước DH
            group_code = param_obj.get_param(cr, uid, 'vhr_timesheet_leave_type_group_need_dh_approve') or ''
            group_code = group_code.split(',')
            group_ids = self.pool.get('vhr.holidays.status.group').search(cr, uid, [('code','in',group_code)])
            type_ids = self.pool.get('hr.holidays.status').search(cr, uid, [('holiday_status_group_id','in', group_ids)])
            if holiday_status_id in type_ids:
                res['double_validation'] = True
                
        else:
            res['double_validation'] = False
        return res

    def _check_duplicate_holiday_line(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        holiday_line_ids = []
        for holiday_line in self.read(cr, uid, ids, ['holiday_line_ids']):
            holiday_line_ids.extend(holiday_line.get('holiday_line_ids', []))
        holiday_line_obj = self.pool.get('vhr.holiday.line')
        dict_status = {}
        for status in STATUS:
            dict_status[status[0]] = status[1]
        
        for line in holiday_line_obj.browse(cr, uid, holiday_line_ids):
            if line.employee_id:
                # if holiday.employee_id and holiday.company_id:
                sql = '''
                        SELECT line.id FROM vhr_holiday_line line INNER JOIN hr_holidays hr ON line.holiday_id = hr.id
                        WHERE line.date= '%s' and 
                              line.employee_id = %s and
                              line.id != %s and
                              hr.state not in ('cancel','refuse')
                      '''
                data_sql = [line.date, line.employee_id.id, line.id]
                if line.status != 'full':
                    sql += ''' and (line.status= '%s' or status='full')'''
                    data_sql.append(line.status)
                    
                cr.execute(sql% tuple(data_sql))
                res = cr.fetchall()
                line_ids = [res_id[0] for res_id in res]
                
                if line_ids:
                    message = ''
                    for info in holiday_line_obj.read(cr, uid, line_ids, ['date', 'status']):
                        if not message:
                            message += "%s %s" % (info['date'], dict_status[info['status']])
                        else:
                            message += ",  %s %s " % (info['date'], dict_status[info['status']])

                    raise osv.except_osv(_('Warning!'),
                                         _('Yêu cầu đăng ký nghỉ phép trùng ngày với yêu cầu đã đăng ký.!'
                                           '\nVui lòng kiểm tra lại request của %s ')%
                                         str(line.holiday_id and line.holiday_id.employee_id and line.holiday_id.employee_id.code or ''))

        return True

    def copy_data(self, cr, uid, id, default, context=None):
        if context is None:
            context = {}
        data = super(vhr_holidays, self).copy_data(cr, uid, id, default, context=context)
        if 'date_from' in data:
            del data['date_from']
        if 'date_to' in data:
            del data['date_to']
        if 'number_of_days_temp' in data:
            del data['number_of_days_temp']
        if 'holiday_line_ids' in data:
            del data['holiday_line_ids']
        if 'state_log_ids' in data:
            del data['state_log_ids']
        if 'double_validation' in data:
            del data['double_validation']
        if 'state' in data:
            data['state'] = 'draft'
        if 'audit_log_ids' in data:
            del data['audit_log_ids']
        return data
    
    def is_register_from_this_year_to_next_year(self, cr, uid, date_from, date_to, context=None):
        if date_from and date_to:
            current_year = datetime.now().year
            
            date_from = datetime.strptime(date_from, DEFAULT_SERVER_DATE_FORMAT)
            date_to = datetime.strptime(date_to, DEFAULT_SERVER_DATE_FORMAT)
            
            if date_from.year != date_to.year or date_from.year == current_year +1:
                return True
        return False
    
    def recompute_date_start_leave_request(self, cr, uid, date_from, context=None):
        """
        If date_from in current year, update to first day of next year
        """
        if date_from:
            current_year = datetime.now().year
            m_date_from = datetime.strptime(date_from, DEFAULT_SERVER_DATE_FORMAT)
            
            if m_date_from.year == current_year:
                date_from = date(current_year + 1, 01, 01).strftime(DEFAULT_SERVER_DATE_FORMAT)
        
        return date_from

    def create(self, cr, uid, vals, context=None):
        if not context:
            context = {}
        try:
            if len(vals.get('date_from', '')) > 10:
                vals['date_from'] = vals.get('date_from')[:10]
            
            groups = self.pool.get('res.users').get_groups(cr, uid)
            need_approve = False
            if vals.get('is_offline', False) and vals.get('type', False) !='add':
                context.update({'ignore_send': True})
                #if is_offline = True, auto set record to confirm, and execute workflow
                vals['state'] = 'confirm'
                if 'vhr_cb_timesheet' in groups:
                    vals['state'] = 'validate'
                else:
                    need_approve = True
                    vals['is_offline'] = False
#             import time.
            elif vals.get('is_offline', False) and vals.get('type',False) == 'add':
                context.update({'ignore_send': True})
                vals['state'] = 'validate'
                
            list_overlap_date = self.check_if_take_birth_leave_on_leave_date(cr, uid, [], vals['employee_id'], vals['holiday_status_id'], vals.get('date_from', False), vals.get('date_to', False), context)
            if list_overlap_date:
                str_overlap_date = str(list_overlap_date)
                str_overlap_date = str_overlap_date.replace("'","").replace('[','').replace(']','')
                error_message = _('Bạn đã đăng ký nghỉ phép ngày %s trùng với thời gian nghỉ sinh. \
                                  Vui lòng báo Admin cancel ngày nghỉ phép để cập nhật nghỉ Sinh con') % str_overlap_date
                                  
                raise osv.except_osv('Validation Error !', '%s!' % error_message)
                    
            vals['is_created'] = True
            employee_id = vals.get('employee_id')
            company_id = vals.get('company_id')
            holiday_status_id = vals.get('holiday_status_id', 0) and int(vals['holiday_status_id']) or False
            if vals.get('type') == 'remove':
                context['employee_id'] = employee_id
                number_of_days_temp = vals.get('number_of_days_temp')
                date_from = vals.get('date_from', False)
                date_to = vals.get('date_to', False)
                res_validate = self._validate_number_of_days_temp(cr, uid, employee_id, company_id,
                                                                  number_of_days_temp=number_of_days_temp,
                                                                  holiday_status_id=holiday_status_id, date_from=date_from)
                if 'double_validation' in res_validate:
                    vals['double_validation'] = res_validate['double_validation']
                
                holiday_status = self.pool.get('hr.holidays.status').read(cr, uid, holiday_status_id, ['is_date_range_include_rest_date','is_allow_to_register_from_now_to_next_year'])
                is_allow_to_register_from_now_to_next_year = holiday_status.get('is_allow_to_register_from_now_to_next_year', False)
                if is_allow_to_register_from_now_to_next_year:
                    is_allow_to_register_from_now_to_next_year = self.is_register_from_this_year_to_next_year(cr, uid, date_from, date_to, context)
                
                #if holiday_status have field is_date_range_include_rest_date = True, dont rewrite date_from/date_to value
                if not holiday_status.get('is_date_range_include_rest_date',False) and not is_allow_to_register_from_now_to_next_year:
                    date_list = []
                    if vals.get('holiday_line_ids', False):
                        for line in vals.get('holiday_line_ids',[]):
                            if line[0] == 0 and line[2] and line[2].get('date'):
                                date_list.append(line[2]['date'])
                    date_list.sort()
                    if date_list:
                        vals['date_to'] = date_list[-1]
                        vals['date_from'] = date_list[0]
                elif is_allow_to_register_from_now_to_next_year:
                    #Auto recompute date_start of leave request when date_from in current year, date_end in next year and holiday_line_ids is null
                    vals['is_missing_holiday_line'] = True
                    if not vals.get('holiday_line_ids', False):
                        vals['date_from'] = self.recompute_date_start_leave_request(cr, uid, date_from, context)
                    else:
                        lowest_date, greatest_date = self.get_lowest_date_and_greatest_date_from_holiday_line(cr, uid, vals.get('holiday_line_ids', False), date_from, date_to, context)
                        vals['date_from'] = lowest_date
                        
                date_today = datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT)
                new_context = context.copy()
                new_context['get_all'] = 1
                sequence = osv.osv.search(self, cr, uid, [('create_date', '>=', date_today + ' 00:00:00'),
                                                          ('create_date', '<=', date_today + ' 23:59:59'),
                                                          ('type', '=', 'remove')], context=new_context)
                sequence = "%03d" % (len(sequence) + 1,)
                vals['name'] = 'HR_LR%s%s' % (datetime.now().strftime("%y%m%d"), sequence)
            elif vals.get('type') == 'add':
                year = vals.get('year', '')
                if year and employee_id and holiday_status_id:
                    exist_annual_leave_ids = self.search(cr, uid, [('employee_id', '=', employee_id),
                                                                            ('year', '=', year),
                                                                            ('type', '=', 'add'),
                                                                            ('holiday_status_id', '=', holiday_status_id)], context={'get_all': True})
                    if exist_annual_leave_ids:
                        employee = self.pool.get('hr.employee').read(cr, uid, employee_id, ['name'])
                        employee_name = employee.get('name', '')
                        holiday_status = self.pool.get('hr.holidays.status').read(cr, uid, holiday_status_id, ['name'])
                        holiday_status_name = holiday_status.get('name', '')
                        raise osv.except_osv(_('Warning!'),
                                             _("Employee '%s' already have annual leave with leave type '%s' at %s") % (
                                                 employee_name, holiday_status_name, year))
            
            res = super(vhr_holidays, self).create(cr, uid, vals, context=context)
            if vals.get('type') == 'remove':
                self.check_holidays(cr, uid, [res], context=context)
                self._check_duplicate_holiday_line(cr, uid, [res], context=context)
                if vals.get('is_offline'):
                    self.check_create_update_delete_data_monthly(cr, uid, [res], 'create', context)
            
            if need_approve:
                self.create_stage_log_change(cr, uid, 'draft', vals['state'], res, context=context)
                context['action'] = 'validate'
                context['action_directly'] = True
                context['not_send_if_finish'] = True
                self.action_next(cr, uid, [res], context)
            
            return res
        
        except Exception as e:
            log.exception(e)
            error_message = ''
            try:
                error_message = e.message
                if not error_message:
                    error_message = e.value
            except:
                error_message = ""
            raise osv.except_osv('Validation Error !', '%s!' % error_message)

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}

        if not isinstance(ids, list):
            ids = [ids]
        try:
            if vals.get('is_offline', False):
                vals['state'] = 'validate'
                
            if len(vals.get('date_from','')) > 10:
                vals['date_from'] = vals.get('date_from')[:10]
                    
            for leave in self.browse(cr, uid, ids, fields_process=['number_of_days_temp', 'remaining_leaves']):
                is_offline = 'is_offline' in vals and vals.get(
                    'is_offline') or leave.is_offline and not 'is_offline' in vals
                if is_offline:
                    context.update({'ignore_send': True})
                if leave.type == 'remove' or vals.get('type') == 'remove':
                    employee_id = vals.get('employee_id') or leave.employee_id.id
                    company_id = False
                    context['employee_id'] = employee_id
                    # company_id = vals.get('company_id') or leave.company_id.id
                    holiday_status_id = leave.holiday_status_id and leave.holiday_status_id.id or False
                    is_allow_to_register_from_now_to_next_year = leave.holiday_status_id and leave.holiday_status_id.is_allow_to_register_from_now_to_next_year or False
                    number_of_days_temp = vals.get('number_of_days_temp', False) or leave.number_of_days_temp
                    date_from = vals.get('date_from', False) or leave.date_from
                    date_to = vals.get('date_to', False) or leave.date_to
                    
                    res_validate = self._validate_number_of_days_temp(cr, uid, employee_id, company_id,
                                                                      number_of_days_temp,
                                                                      holiday_status_id, date_from)
                    if 'double_validation' in res_validate:
                        vals['double_validation'] = res_validate['double_validation']
                    
                    if is_allow_to_register_from_now_to_next_year:
                        is_allow_to_register_from_now_to_next_year = self.is_register_from_this_year_to_next_year(cr, uid, date_from, date_to, context)
                    
                    is_date_range_include_rest_date = leave.holiday_status_id and leave.holiday_status_id.is_date_range_include_rest_date or False
                    if not is_date_range_include_rest_date and not is_allow_to_register_from_now_to_next_year:
                        # adjust date range after save form
                        holiday_line_obj = self.pool.get('vhr.holiday.line')
                        temp_holiday_line_ids = holiday_line_obj.search(cr, uid, [('holiday_id', 'in', ids)])
                        date_list_temp = []
                        if vals.get('holiday_line_ids', False):
                            for line in vals.get('holiday_line_ids',[]):
                                if line[0] == 0 and line[2] and line[2].get('date'):
                                    date_list_temp.append(line[2]['date'])
                                if line[0] == 2 and line[1] in temp_holiday_line_ids:
                                    temp_holiday_line_ids.remove(line[1])
    
                        line_data = holiday_line_obj.read(cr, uid, temp_holiday_line_ids, ['date'])
                        date_list = map(lambda x: x['date'], line_data) + date_list_temp
                        date_list.sort()
                        if date_list:
                            vals['date_to'] = date_list[-1]
                            vals['date_from'] = date_list[0]
                            
                            
                    #Update is_finish_leave of created monthly record
                    if vals.get('state',False) == 'validate':
                        monthly_obj = self.pool.get('vhr.ts.monthly')
                        holiday_line_ids = self.pool.get('vhr.holiday.line').search(cr, uid, [('holiday_id','=',leave.id)])
                        if holiday_line_ids:
                            monthly_ids = monthly_obj.search(cr, uid, [('holiday_line_id','in',holiday_line_ids)], context={'get_all': True})
                            if monthly_ids:
                                monthlys = monthly_obj.read(cr, uid, monthly_ids, ['holiday_name'])
                                for monthly in monthlys:
                                    holiday_name = monthly.get('holiday_name','')
                                    if holiday_name:
                                        monthly_obj.write(cr, SUPERUSER_ID, monthly['id'], {'name':holiday_name})
    
                elif (leave.type == 'add' or vals.get('type') == 'add') \
                        and 'move_days_of_pre_year' in vals \
                        and vals['move_days_of_pre_year'] == False:
                    record = self.read(cr, uid, leave.id, ['days_taken_of_pre_year'])
                    if record.get('days_taken_of_pre_year', 0) > 0:
                        raise osv.except_osv(_('Validation Error !'),
                                             _("You can not uncheck 'Move Days Of Pre Year' because 'Taken Days (Prev. Year)' greater 0 !"))
                
                super(vhr_holidays, self).write(cr, uid, [leave.id], vals, context=context)
            self.check_holidays(cr, uid, ids, context=context)
            if not vals.get('state', False) == 'refuse':
                self._check_duplicate_holiday_line(cr, uid, ids, context=context)
    
            # For leave accumulation, when edit actual days
            if 'temp_actual_days_of_pre_year' in vals:
                records = self.read(cr, uid, ids, ['move_days_of_pre_year'])
                update_ids = []
                for record in records:
                    if record['move_days_of_pre_year']:
                        update_ids.append(record['id'])
    
                if update_ids:
                    super(vhr_holidays, self).write(cr, uid, update_ids,
                                                    {'actual_days_of_pre_year': vals['temp_actual_days_of_pre_year']},
                                                    context=context)
            
            
            if set(['date_from','date_to','holiday_status_id']).intersection(vals.keys()):
                record = self.read(cr, uid, ids[0], ['employee_id','holiday_status_id','date_from','date_to'])
                employee_id = record.get('employee_id', False) and record['employee_id'][0]
                holiday_status_id = record.get('holiday_status_id', False) and record['holiday_status_id'][0]
                date_from = record.get('date_from', False)
                date_to = record.get('date_to', False)
                list_overlap_date = self.check_if_take_birth_leave_on_leave_date(cr, uid, ids, employee_id, holiday_status_id, date_from, date_to, context)
                if list_overlap_date:
                    str_overlap_date = str(list_overlap_date)
                    str_overlap_date = str_overlap_date.replace("'","").replace('[','').replace(']','')
                    error_message = _('Bạn đã đăng ký nghỉ phép ngày %s trùng với thời gian nghỉ sinh. \
                                      Vui lòng báo Admin cancel ngày nghỉ phép để cập nhật nghỉ Sinh con') % str_overlap_date
                                      
                    raise osv.except_osv('Validation Error !', '%s!' % error_message)
                
            #Create
            if vals.get('state',False) == 'confirm':
                self.check_create_update_delete_data_monthly(cr, uid, ids, 'create', context)
            #Delete
            elif vals.get('state',False) == 'refuse':
                self.check_create_update_delete_data_monthly(cr, uid, ids, 'delete', context)
            #Update(create if new line is insert)
            elif vals.get('holiday_line_ids',False):
                records = self.read(cr, uid, ids, ['state'])
                update_ids = []
                for record in records:
                    state = record.get('state',False)
                    if state in ['confirm','validate']:
                        update_ids.append(record['id'])
                        
                if update_ids:
                    self.check_create_update_delete_data_monthly(cr, uid, ids, 'update', context)
            
            
            return True
        
        except Exception as e:
            log.exception(e)
            error_message = ''
            try:
                error_message = e.message
                if not error_message:
                    error_message = e.value
            except:
                error_message = ""
            raise osv.except_osv('Validation Error !', '%s!' % error_message)
        
    def check_create_update_delete_data_monthly(self, cr, uid, ids, action, context=None):
        if ids:
            line_obj = self.pool.get('vhr.holiday.line')
            monthly_obj = self.pool.get('vhr.ts.monthly')
            
            records = self.read(cr, uid, ids, ['employee_id','holiday_line_ids'])
            for record in records:
                employee_id = record.get('employee_id', False) and record['employee_id'][0]
                #Search to order line by date
                line_ids = line_obj.search(cr, uid, [('holiday_id','=',record['id'])], order='date asc')
                lines = line_obj.read(cr, uid, line_ids, ['date','number_of_days_temp'])
                
                latest_monthly_ids = monthly_obj.search(cr, uid, [('employee_id','=',employee_id)], limit=1, order='date desc', context={'get_all': True})
                if lines and latest_monthly_ids:
                    earliest_date_line = line_obj.read(cr, uid, line_ids[0], ['date'])
                    latest_monthly = monthly_obj.read(cr, uid, latest_monthly_ids[0], ['date'])
                    latest_monthly_date = latest_monthly.get('date', False)
                    if not latest_monthly_date or self.compare_day(latest_monthly_date, earliest_date_line['date']) >0:
                        return True
                
                else:
                    return True
                
                for line in lines:
                    is_created_monthly_ids = monthly_obj.search(cr, uid, [('employee_id','=',employee_id),('date','=',line.get('date'))], context={'get_all': True})
                    if is_created_monthly_ids:
                        line['employee_id'] = employee_id
                        sql = """
                                SELECT holiday_line_id FROM vhr_ts_monthly
                                WHERE id in %s
                              """
                        cr.execute(sql % str(tuple(is_created_monthly_ids)).replace(',)', ')'))
                        exist_holiday_line_ids = [res_id[0] for res_id in cr.fetchall()]
                        
                        if action == 'create':
                            #Have data monthly record at state draft, dont need to filter by state because dont allow to create leave when have monthly record at other state :confirm/validate
                            line_obj.create_data_monthly(cr, SUPERUSER_ID, line['id'], line, context)
                        elif action == 'update':
                            #Case user change date range, insert new holiday line
                            if line['id'] not in exist_holiday_line_ids:
                                line_obj.create_data_monthly(cr, SUPERUSER_ID, line['id'], line, context)
                            else:
                                line_obj.update_data_monthly(cr, SUPERUSER_ID, [line['id']], context)
                        elif action == 'delete':
                            line_obj.delete_data_monthly(cr, SUPERUSER_ID, [line['id']], context)
        
        return True
    
    def delete_record(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        self.unlink(cr, uid, ids, context)
        context = {'search_default_active_employee':1,
                   'default_type': 'remove','leave_registration':1,'delete':False,
                   'rule_for_tree_form': True, 'move': False, 'approve': False, 'reject': False}
        
        view_form_open = 'view_hr_holidays_new_form'
        ir_model_pool = self.pool.get('ir.model.data')
        view_form_result = ir_model_pool.get_object_reference(cr, uid, 'vhr_timesheet', view_form_open)
        view_form_id = view_form_result and view_form_result[1] or False
        
        return {
                'type': 'ir.actions.act_window',
                'name': "Leave Registration",
                'view_type': 'form',
                'view_mode': 'form',
                'views': [(view_form_id or False, 'form')],
                'res_model': 'hr.holidays',
                'context': context,
                'target': 'current',
            }
        
    def unlink(self, cr, uid, ids, context=None):
        """
        Can remove if is_offline = True and state in Draft
        :param cr:
        :param uid:
        :param ids:
        :param context:
        :return:
        """
        if context is None:
            context = {}
        for rec in self.browse(cr, uid, ids, fields_process=['state', 'is_offline'], context=context):
#             if rec.is_offline:
#                 continue
            if rec.state not in ['draft','cancel'] and context.get('is_not_delete_leave', True):
                raise osv.except_osv(_('Warning!'),
                                     _('You can only delete leave requests which is draft state!'))
        try:
            return  super(vhr_holidays, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv(_('Validation Error !'), _('You cannot delete the record(s) which reference to others !'))

    # for group by view
    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False,
                   lazy=True):
        if not context:
            context = {}
        
        if 'active_test' not in context:
            context['active_test'] = False
            
#         orderby = self._order
        context['search_all_employee'] = True
        if 'year' in fields:
            fields.remove('year')
        if not context.get('get_all'):
            domain = self.build_condition_menu(cr, uid, domain, offset, limit, orderby, context, count=False)
        res = super(vhr_holidays, self).read_group(cr, uid, domain, fields, groupby, offset, limit, context, orderby,
                                                   lazy)
        return res

    def read(self, cr, user, ids, fields=None, context=None, load='_classic_read'):
        if not context:
            context = {}
        import time
        if context.get('validate_read_hr_holidays', False):
            log.info('\n\n validate_read_hr_holidays')
            time1=time.time()
            result_check = self.validate_read(cr, user, ids, context)
            if not result_check:
                raise osv.except_osv(_('Validation Error !'), _('You don’t have permission to access this data !'))
            time2=time.time()
            log.info('Time to read: %s',time2-time1)
            del context['validate_read_hr_holidays']
#         else:
#             del context['do_not_validate_read_holiday']
        return super(vhr_holidays, self).read(cr, user, ids, fields, context, load)

    def validate_read(self, cr, uid, ids, context=None):
        user_groups = self.pool.get('res.users').get_groups(cr, uid)
        if set(['hrs_group_system', 'vhr_cb']).intersection(set(user_groups)):
            return True
        if isinstance(ids, (int, long)) or (isinstance(ids, list) and len(ids)) == 1:
            check_id = ids
            if isinstance(ids, list):
                check_id = ids[0]
            new_context = context and context.copy() or {}
            new_context.update({'leaves_history': 1})
            lst_check = self.search(cr, uid, [], context=new_context)
            if check_id not in lst_check:
                return False
        return True

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        # Search rule for specific menu
        if not context:
            context = {}
        context['search_all_employee'] = True
        if 'active_test' not in context:
            context['active_test'] = False
            
            
        if not context.get('get_all'):
            args = self.build_condition_menu(cr, uid, args, offset, limit, order, context, count)

            if context.get('holiday_status_config_name', False):
                config_parameter = self.pool.get('ir.config_parameter')
                holiday_status_code = config_parameter.get_param(cr, uid, context['holiday_status_config_name'])
                if holiday_status_code:
                    holiday_status_code_list = holiday_status_code.split(',')
                    holidays_status_ids = self.pool.get('hr.holidays.status').search(cr, uid, [
                        ('code', 'in', holiday_status_code_list)])

                    if holidays_status_ids:
                        args.append(('holiday_status_id', 'in', holidays_status_ids))

        return super(vhr_holidays, self).search(cr, uid, args, offset, limit, order, context, count)

    def name_get(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        res = []
        # Fix name for Annual Leave
        if context.get('default_type', False) == 'add':
            reads = self.read(cr, uid, ids, ['employee_id'], context=context)
            for record in reads:
                name = record.get('employee_id', False) and record['employee_id'][1]
                res.append((record['id'], name))
        else:
            res = super(vhr_holidays, self).name_get(cr, uid, ids, context)
        return res

    def build_condition_menu(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        """
        Filter list of leave request on Annual Leave Balance/ List Of Leave/ Leave Approval
        """
        user_groups = self.pool.get('res.users').get_groups(cr, uid)
        employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', uid)], context={'search_all_employee': True,'active_test':False})
        if employee_ids:
            new_args = []
            if context.get('filter_by_permission', False):
                #Annual Leave Balance
                new_args = self.get_domain_base_on_permission(cr, uid, employee_ids[0], user_groups, context)
            elif context.get('leaves_history'):
                #"List Of Leave"
                
                new_args = ['|', '|', '|',
                            '&', ('report_to_id', 'in', employee_ids), 
                                 ('state', '!=', 'draft'),
                            '&', '&', ('dept_head_id', 'in', employee_ids), 
                                      ('state', '!=', 'draft'),
                                      ('double_validation', '=', True),
                            ('employee_id', 'in', employee_ids),
                            ('requester_id', 'in', employee_ids)]
                
                dict = self.get_emp_make_delegate(cr, uid, employee_ids[0], False, context)
                if dict:
                    emp_ids = []
                    for employee_id in dict:
                        emp_ids.append(employee_id)
                        new_args.extend(['&',('dept_head_id','=',employee_id),('department_id','=',dict[employee_id])])
                        new_args.insert(0,'|')
                    
                    new_args.append(('report_to_id','in',emp_ids))
                    new_args.insert(0,'|')
                        
                    

                if set(['hrs_group_system', 'vhr_cnb_manager','vhr_cb_timesheet','vhr_cb_timesheet_readonly']).intersection(set(user_groups)):
                    new_args = []
                else:
                    
#                     if set(['vhr_hrbp','vhr_assistant_to_hrbp']).intersection(set(user_groups)):
#                         #Get department of hrbp/assist_hrbp
#                         department_hrbp = self.get_department_of_hrbp(cr, uid, employee_ids[0])
#                         department_ass_hrbp = self.get_department_of_ass_hrbp(cr, uid, employee_ids[0])
#                         search_department_ids = department_hrbp + department_ass_hrbp
#                         
#                         new_args.insert(0,'|')
#                         new_args.append(('department_id','in',search_department_ids))
                    
                    if set(['vhr_dept_admin']).intersection(set(user_groups)):
                        #Show all record of employee  belong to timesheet, user is currently dept admin
                        sql = """
                            SELECT
                              DISTINCT HH.id
                            FROM hr_holidays HH
                              INNER JOIN vhr_holiday_line LL ON HH.id = LL.holiday_id
                              INNER JOIN vhr_ts_emp_timesheet ET     --on current timesheet employee
                                ON     ET.employee_id = HH.employee_id 
                                  AND  ET.effect_from <= current_date 
                                  AND  ( ET.effect_to >= current_date OR ET.effect_to is null )
                              INNER JOIN vhr_ts_timesheet_detail TD   -- on current timesheet detail
                                ON     TD.timesheet_id = ET.timesheet_id 
                                   AND current_date BETWEEN TD.from_date AND TD.to_date
                              INNER JOIN hr_employee HE ON HE.id = TD.admin_id
                              INNER JOIN resource_resource RR ON RR.id = HE.resource_id
                              INNER JOIN res_users UU ON UU.id = RR.user_id
                            WHERE      UU.id = {0} 
                        """.format(uid)

                        cr.execute(sql)
                        res_ids = [res_id[0] for res_id in cr.fetchall()]
                        
                        new_args.insert(0,'|')
                        new_args.append(('id', 'in', res_ids))

            elif context.get('leave_approval'):
                #Leave Approval
                new_args = ['|','|',
                            '&', ('report_to_id', 'in', employee_ids), ('state', '=', 'confirm'),
                            '&', ('dept_head_id', 'in', employee_ids), ('state', '=', 'validate1'),
                            '&', ('employee_id', 'in', employee_ids), ('state', '=', 'draft')]
                
                if set(['vhr_cb_timesheet','vhr_cb_timesheet_readonly']).intersection(user_groups):
                    new_args.insert(0,'|')
                    new_args.append(('state','=','validate2'))
                
                dict = self.get_emp_make_delegate(cr, uid, employee_ids[0], False, context)
                if dict:
                    emp_ids = []
                    for employee_id in dict:
                        emp_ids.append(employee_id)
                        new_args.extend(['&','&',('dept_head_id','=',employee_id),('department_id','=',dict[employee_id]),('state', '=', 'validate1')])
                        new_args.insert(0,'|')
                    
                    new_args.extend(['&',('report_to_id','in',emp_ids),('state', '=', 'confirm')])
                    new_args.insert(0,'|')
                    

            args += new_args
        
        else:
            if 'hrs_group_system' not in user_groups:
                args.append(('id','in',[]))
        return args

    def get_domain_base_on_permission(self, cr, uid, employee_id, user_groups, context=None):
        new_args = []
        if employee_id and user_groups:
            working_pool = self.pool.get('vhr.working.record')
            department_pool = self.pool.get('hr.department')
            if set(['hrs_group_system', 'vhr_cnb_manager','vhr_cb_timesheet','vhr_cb_timesheet_readonly']).intersection(set(user_groups)):
                new_args = []

            else:
                employee_ids = []
                
                 # Filter by Dept Admin
                if set(['vhr_dept_admin']).intersection(set(user_groups)):
                    employee_ids_belong_to_dept_admin = self.get_list_employees_of_dept_admin(cr, uid, employee_id, context)
                    employee_ids.extend(employee_ids_belong_to_dept_admin)
                
                department_ids = department_pool.search(cr, uid, [('manager_id', '=', employee_id)])
                # Filter by Dept Head
                if department_ids:
                    all_department_ids = self.get_child_department(cr, uid, department_ids)
                    working_ids = working_pool.search(cr, uid, [('department_id_new', 'in', all_department_ids),
                                                                ('state','in',[False,'finish']),
                                                                ('active', '=', True)])
                    if working_ids:
                        workings = working_pool.read(cr, uid, working_ids, ['employee_id'])
                        employee_dh_ids = [working.get('employee_id', False) and working['employee_id'][0] for working in
                                        workings]
                        if employee_dh_ids:
                            employee_ids += employee_dh_ids

                # Filter by LM
                employee_lm_ids = self.pool.get('hr.employee').search(cr, uid, [('report_to','=',employee_id)])
                if employee_lm_ids:
                    employee_ids += employee_lm_ids

                employee_ids.append(employee_id)

                new_args = [('employee_id', 'in', employee_ids)]

        return new_args

    

    # show popup comment when LM or DH approve or reject

    def open_window(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        view_open = 'view_hr_holidays_submit_form'
        if context.get('view_open',False):
            view_open = context['view_open']
        context['validate_read_hr_holidays'] = False
        action = {
            'name': 'Notes',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.pool.get('ir.model.data').get_object_reference(cr, uid, 'vhr_timesheet', view_open)[
                1],
            'res_model': 'hr.holidays',
            'context': context,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': ids[0],
        }
        return action

    def execute_workflow(self, cr, uid, ids, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        if context is None:
            context = {}
        
        time1=time.time()
        
        user_groups = self.pool.get('res.users').get_groups(cr, uid)
        if context.get('action'):
            for record in self.read(cr, uid, ids, ['state','employee_id']):
                emp_name = record.get('employee_id', False) and record['employee_id'][1] or ''
                record_id = record.get('id', False)
                old_state = record.get('state', False)
                if old_state in ['cancel', 'draft','refuse'] and not context.get('force_to_do_action', False):
                    raise osv.except_osv(_('Validation Error !'), _('You can not do this action with record(s) at state draft/cancel !'))
                if old_state == context['action']:
                    raise osv.except_osv(_('Validation Error !'), _('You can not do this action with record(s) at state finish !'))
                
#                 if context.get('action', False) == 'validate' and not record.get('can_approve', False):
#                     raise osv.except_osv('Validation Error !', 'You don’t have permission to do this action !')
#                 
#                 if context.get('action', False) == 'reject' and not record.get('can_refuse', False):
#                     raise osv.except_osv('Validation Error !', 'You don’t have permission to do this action !')
                    
                # for multi approve reject
#                 if context.get('multi'):
#                     if old_state == 'validate1':
#                         context['action'] = 'second_validate'
                
                action_result = False
                if context.get('action', False) == 'validate':
#                     self.signal_validate(cr, uid, ids)
                    action_result = self.action_next(cr, uid, [record_id], context)
#                 elif context.get('action', False) == 'second_validate':
# #                     self.signal_second_validate(cr, uid, [record_id])
#                     self.action_next(cr, uid, ids, context)
                elif context.get('action', False) == 'reject':
#                     self.signal_refuse(cr, uid, [record_id])
                    action_result = self.action_cancel(cr, uid, [record_id], context)
                
                if action_result:
                    record = self.read(cr, uid, record_id, ['state'])
                    new_state = record.get('state', False)
                    if old_state != new_state:
                        self.create_stage_log_change(cr, uid, old_state, new_state, res_id=record_id,
                                                                                        context=context)
                        
                         #If action user is cb_timesheet, and not action from state draft, dont send mail
                        if not( 'vhr_cb_timesheet' in user_groups and old_state !='draft'):
                            self.send_mail(cr, uid, record_id, old_state, new_state, context)
#                         thread.start_new_thread(vhr_holidays.send_mail,(self, cr, uid, record_id, old_state, new_state, context))
                else:
                    raise osv.except_osv(_('Validation Error !'), _("You don't have permission to do this action with leave of %s - %s "%(record['id'],emp_name)))
                    
        log.info('[hr.holidays] Time run execute workflow: %s'%(time.time()-time1))
        return True
    
    
    def action_next(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        
        time1=time.time()
        if ids:
            if not isinstance(ids, list):
                ids = [ids]
            record_id = ids[0]
            
            user_groups = self.pool.get('res.users').get_groups(cr, uid)
            
            #Prevent double click on submit
            if record_id in self.submiting_ids:
                return False
            self.submiting_ids.append(record_id)
            log.info("[hr.holidays] List ids is submitting: %s" %(self.submiting_ids))
            
            record = self.browse(cr, uid, record_id)
            if record.is_offline:#For Annual Leave, Update For Leave Request
                super(vhr_holidays, self).write(cr, uid, record_id, {'state': 'validate'})
                return True
            elif not record.is_offline and record.type == 'remove':#For Leave Request
                state = record.state
                new_state = False
                if state == 'draft':
                    new_state = 'confirm'#Waiting LM
                    
                elif state == 'confirm' and record.can_approve:
                    if record.double_validation:
                        new_state = 'validate1'#Waiting DH
                    elif not record.double_validation and record.holiday_status_id and record.holiday_status_id.is_require_paperwork:
                        new_state = 'validate2'#Waiting CB
                    else:
                        new_state = 'validate'#Finish
                
                elif state == 'validate1' and record.can_validate:
                    if record.holiday_status_id and record.holiday_status_id.is_require_paperwork:
                        new_state = 'validate2'#Waiting CB
                    else:
                        new_state = 'validate'#Finish
                
                elif state == 'validate2' and record.can_validate_cb:
                    new_state = 'validate'
                
                if new_state:
                    self.write(cr, uid, record_id, {'state': new_state})
                    
                    if context.get('action_directly', False) :
                        time11=time.time()
                        self.create_stage_log_change(cr, uid, state, new_state, record_id, context=context)
                        time12= time.time()
                        if (context.get('not_send_if_finish', False) and new_state != 'validate') or not context.get('not_send_if_finish', False):
                            #If action user is cb_timesheet, and not action from state draft, dont send mail
                            if not( 'vhr_cb_timesheet' in user_groups and state !='draft'):
                                self.send_mail(cr, uid, record_id, state, new_state, context)
#                         thread.start_new_thread(vhr_holidays.send_mail,(self, cr, uid, record_id, state, new_state, context))
                        time13=time.time()
                        
                        log.info("[hr.holidays] Time run function in action next: %s;;;%s" %(time12-time11,time13-time12))
                    
                    log.info("[hr.holidays] Time run action next: %s" %(time.time()-time1))
                    self.submiting_ids.remove(record_id)
                    return True
            
            self.submiting_ids.remove(record_id)
        
        log.info("[hr.holidays] Time run action next: %s" %(time.time()-time1))
        return False
    
    def action_cancel(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        if ids:
            if not isinstance(ids, list):
                ids = [ids]
            record_id = ids[0]
            record = self.read(cr, uid, record_id, ['can_refuse'])
            if record.get('can_refuse', False) or context.get('force_to_do_action', False):
                self.write(cr, uid, record_id, {'state': 'refuse'})
                return True
        
        return False
                
            

    def create_stage_log_change(self, cr, uid, old_state, new_state, res_id, context=None):
        if context is None:
            context = {}
        list_states = {item[0]: item[1] for item in STATES}
        state_vals = {'old_state': list_states[old_state], 'new_state': list_states[new_state],
                      'res_id': res_id, 'model': self._name}
        if 'ACTION_COMMENT' in context:
            state_vals['comment'] = context['ACTION_COMMENT']
        self.pool.get('vhr.state.change').create(cr, uid, state_vals)
        
    
    def send_mail(self, cr, uid, record_id, state, new_state, context=None):
        if not context:
            context = {}
        context["search_all_employee"] = True
        if record_id and state and new_state:
#             _pool = ConnectionPool(int(tools.config['db_maxconn']))
#             mcr = Cursor(_pool, cr.dbname, True)
#             reload(sys)
#             mcr.autocommit(True)
            
            record = self.read(cr, uid, record_id, ['name'])
            action_user = ''
            if context.get('action_user', False):
                action_user = context['action_user']
            else:
                user = self.pool.get('res.users').read(cr, uid, uid, ['login'])
                if user:
                    action_user = user.get('login','')
            
            log.info("Send mail in Leave Request from old state %s to new state %s"% (state, new_state))
            if state in mail_process.keys():
                data = mail_process[state]
                is_have_process = False
                
                context['to_new_state'] = new_state
                for mail_data in data:
                    if new_state == mail_data[0]:
                        is_have_process = True
                        mail_detail = mail_data[1]
                        
                        #Mail có check is_by_pass_with_admin và người action là admin thi ko gửi mail nữa
                        if mail_detail.get('is_by_pass_with_admin', False) and \
                          self.is_have_admin_permission_approve_reject_on_leave_request(cr, uid, record_id, context):
                            continue
                        
                        vals = {'action_user':action_user, 'leave_id': record_id,'request_code':record.get('name','')}
                        list_group_mail_to = mail_detail['to']
                                
                        list_mail_to, list_mail_cc_from_group_mail_to = self.get_email_to_send(cr, uid, record_id, list_group_mail_to, context)
                        mail_to = ';'.join(list_mail_to)
                        vals['email_to'] = mail_to
                        
                        if 'cc' in mail_detail:
                            list_group_mail_cc = mail_detail['cc']
                            
                            list_mail_cc, list_mail_cc_from_group_mail_cc = self.get_email_to_send(cr, uid, record_id, list_group_mail_cc, context)
                            list_mail_cc += list_mail_cc_from_group_mail_cc + list_mail_cc_from_group_mail_to
                            list_mail_cc = list(set(list_mail_cc))
                            mail_cc = ';'.join(list_mail_cc)
                            vals['email_cc'] = mail_cc
                        
                        link_email = self.get_url(cr, uid, record_id, context)
                        vals['link_email'] = link_email
                        context = {'action_from_email': mail_detail.get('action_from_email',''),'force_to_do_action': context.get('force_to_do_action',False) }
                        self.pool.get('vhr.ts.leave.email').send_email(cr, uid, mail_detail['mail_template'], vals, context)
                
                if not is_have_process:
                    log.info("TS Overtime don't have mail process from old state %s to new state %s "%(state, new_state))
            
#             mcr.close()
        return True
    
    def get_email_to_send(self, cr, uid, record_id, list, context=None):
        """
        Returl list email from list
        """
        res = []
        res_cc = []
        if list and record_id:
            for item in list:
                if item == 'requester':
                    mail = self.get_requester_mail(cr, uid, record_id, context)
                    if mail:
                        res.append(mail)
                elif item == 'lm':
                    mail = self.get_lm_mail(cr, uid, record_id, context)
                    if mail:
                        res.append(mail)
                    
                    #Send to delegator
                    record = self.browse(cr, uid, record_id, fields_process=['report_to_id'])
                    delegator_ids = self.get_delegator(cr, uid, record_id, record.report_to_id.id, False, context)
                    if delegator_ids:
                        delegators = self.pool.get('hr.employee').read(cr, uid, delegator_ids, ['work_email'])
                        delegate_mails = [delegator.get('work_email','') for delegator in delegators]
                        res.extend(delegate_mails)
                        
                elif item == 'dept_head':
                    mail = self.get_dept_head_mail(cr, uid, record_id, context)
                    if mail:
                        res.append(mail)
                    
                    #Send to delegator
                    record = self.browse(cr, uid, record_id, fields_process=['dept_head_id'])
                    delegator_ids = self.get_delegator(cr, uid, record_id, record.dept_head_id.id, False, context)
                    if delegator_ids:
                        delegators = self.pool.get('hr.employee').read(cr, uid, delegator_ids, ['work_email'])
                        delegate_mails = [delegator.get('work_email','') for delegator in delegators]
                        res.extend(delegate_mails)
#                 
#                 else:
#                     mail_group_pool = self.pool.get('vhr.email.group')
#                     mail_group_ids = mail_group_pool.search(cr, uid, [('code','=',item)])
#                     if mail_group_ids:
#                         mail_group = mail_group_pool.read(cr, uid, mail_group_ids[0], ['to_email','cc_email'])
#                         to_email = mail_group.get('to_email','') or ''
#                         cc_email = mail_group.get('cc_email','') or ''
#                         mail_to  = to_email.split(';')
#                         mail_cc  = cc_email.split(';')
#                         res.extend(mail_to)
#                         res_cc.extend(mail_cc)
                    
                    else:
                        log.info("Can't find mail for " + item)
        return res, res_cc
    
    def get_requester_mail(self, cr, uid, record_id, context=None):
        if not context:
            context = {}
        
        requester_mail = ''
        if record_id:
            record = self.browse(cr, uid, record_id, fields_process=['requester_id'])
            requester_mail = record.requester_id and record.requester_id.work_email or ''
        
        return requester_mail
    
    def get_lm_mail(self, cr, uid, record_id, context=None):
        if not context:
            context = {}
        
        report_to_mail = ''
        if record_id:
            record = self.browse(cr, uid, record_id, fields_process=['report_to_id'])
            report_to_mail = record.report_to_id and record.report_to_id.work_email or ''
        
        return report_to_mail
    
    def get_dept_head_mail(self, cr, uid, record_id, context=None):
        if not context:
            context = {}
        
        dh_mail = ''
        if record_id:
            record = self.browse(cr, uid, record_id, fields_process=['dept_head_id'])
            dh_mail = record.dept_head_id and record.dept_head_id.work_email or ''
        
        return dh_mail

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if context is None:
            context = {}
        res = super(vhr_holidays, self).fields_view_get(cr, uid, view_id, view_type, context,
                                                        toolbar=toolbar, submenu=submenu)

        doc = etree.XML(res['arch'])
        user_groups = self.pool.get('res.users').get_groups(cr, uid)
        
        if res['type'] == 'tree':
            if context.get('filter_by_permission', False):
                #Annual Leave
                if not set(['vhr_cb_timesheet']).intersection(user_groups):
                    for node in doc.xpath("//tree"):
                        node.set('edit',  '0')
                        
        elif res['type'] == 'form':
            # add field comment when show popup when LM or DH approve or reject
            # To add field text action_comment
            if context.get('action', False) and context.get('active_id', False):
                node = doc.xpath("//form/separator")
                if node:
                    node = node[0].getparent()
                    if context.get('required_comment', False):
                        node_notes = etree.Element('field', name="action_comment", colspan="4",
                                                   modifiers=json.dumps({'required': True}))
                    else:
                        node_notes = etree.Element('field', name="action_comment", colspan="4")
                    node.append(node_notes)
                    res['fields'].update({
                        'action_comment': {'selectable': True, 'string': 'Action Comment', 'type': 'text',
                                           'views': {}}})
            
            if context.get('filter_by_permission', False):
                #Annual Leave
                if not set(['vhr_cb_timesheet']).intersection(user_groups):
                    for node in doc.xpath("//form"):
                        node.set('edit',  '0')
                        
        if context.get('leave_registration', False):
            
            #Button Delete in Leave Registration
            btn_del = doc.xpath("//button[@name='delete_record']")
            if btn_del:
                modifiers = json.loads(btn_del[0].get('modifiers') or '{}')
                modifiers.update({'invisible': ['|',('is_created', '=', False),('state','!=','draft')]})
                btn_del[0].set('modifiers', json.dumps(modifiers))
                    
                    # hrs_group_system vhr_cb_timesheet can edit in any state except cancel with these fields ['notes','date_from','date_to','holiday_line_ids']
        elif context.get('leaves_history', False):
            if res['type'] == 'tree':
                doc.xpath("//tree")[0].attrib['create'] = 'false'
            if res['type'] == 'form':
                btn_confirm = doc.xpath("//button[@name='confirm']")
                if btn_confirm:
                    # only requester can submit the request
                    requester_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', uid)], context={'search_all_employee':True})
                    modifiers = json.loads(btn_confirm[0].get('modifiers') or '{}')
                    modifiers.update(
                        {'invisible': ['|', ('requester_id', 'not in', requester_ids), ('state', '!=', 'draft')]})
                    btn_confirm[0].set('modifiers', json.dumps(modifiers))
                    if 'attrs' in btn_confirm[0].attrib:
                        del btn_confirm[0].attrib['attrs']
                
                doc.xpath("//form")[0].attrib['create'] = 'false'
                if set(['hrs_group_system', 'vhr_cb_timesheet']).intersection(set(user_groups)):
                    update_fields = ['date_from','date_to','holiday_line_ids']
                    for field in update_fields:
                        for node in doc.xpath("//field[@name='%s']" %field):
                            # ignore function or readonly fields
                            modifiers = json.loads(node.get('modifiers') or '{}')
                            if modifiers.get('readonly') == 1 or modifiers.get('readonly') == True:
                                continue
                            modifiers.update({'readonly': [('state', '=', 'refuse')]})
                            node.set('modifiers', json.dumps(modifiers))
        
        res['arch'] = etree.tostring(doc)
        return res

    def create_employee_holidays(self, cr, uid, employee_id, company_id=False, holiday_status_id=False,
                                 number_of_days=False, context=None):
#         _pool = ConnectionPool(int(tools.config['db_maxconn']))
#         mcr = Cursor(_pool, cr.dbname, True)
#         reload(sys)
        
#         from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT, ISOLATION_LEVEL_READ_COMMITTED, ISOLATION_LEVEL_REPEATABLE_READ
#         cr._cnx.set_isolation_level(ISOLATION_LEVEL_READ_COMMITTED)
#         mcr.autocommit(True)

        number_of_days = self.rounded_days(number_of_days)
        vals = {
            'employee_id': employee_id,
            'number_of_days_temp': number_of_days,
            'type': 'add',
            'notes': 'Automation created by system. Back work or Newbie',
            'holiday_type': 'employee',
            'is_offline': True,
            'holiday_status_id': holiday_status_id,
        }
        res = self.onchange_employee_id(cr, uid, [], employee_id, holiday_status_id, context=context)
        vals.update(res['value'])
        # res = self.onchange_company_id(cr, uid, [], employee_id, company_id, holiday_status_id)
        # vals['company_id'] = company_id
        
        vals['holiday_status_id'] = holiday_status_id
        year = datetime.now().year
        allocation_ids = osv.osv.search(self, cr, uid,
                                        [('employee_id', '=', employee_id),
                                         # ('company_id', '=', company_id),
                                         ('year', '=', year),
                                         ('type', '=', 'add'), ('state', '=', 'validate'),
                                         ('holiday_status_id', '=', holiday_status_id)], context={'get_all': 1})
        if allocation_ids:
            vals = {'number_of_days_temp': number_of_days,'actual_days_of_pre_year': 0}
            
            if context.get('allocation_for_emp_change_level', False) and 'actual_days_of_pre_year' in vals:
                del vals['actual_days_of_pre_year']
                
            self.create_audittrail_log(cr, uid, allocation_ids, vals, context)

            super(vhr_holidays, self).write(cr, uid, allocation_ids, vals, context=context)
        else:
            if not vals.get('holiday_status_id', False):
                raise osv.except_osv(_('Validation Error !'), _('Can not find leave type to create Annual Leave !'))
            
            self.create_with_log(cr, uid, vals, context)
#         mcr.close()
        return True
    
    
    def create_audittrail_log(self, cr, uid, ids, vals, context=None):
        """
        Create audittrail log when write to record
        Only for log field except one2many,many2many
        """
        log_pool = self.pool.get('audittrail.log')
        log_line_pool = self.pool.get('audittrail.log.line')
        model_pool = self.pool.get('ir.model')
        if ids and vals:
            model_ids = model_pool.search(cr, SUPERUSER_ID, [('model', '=', self._name)])
            model_id = model_ids and model_ids[0] or False
            if model_id:
                model = model_pool.browse(cr, uid, model_id)
                for record_id in ids:
                    lines = self.prepare_log_holiday_line_data(cr, uid, record_id, model, vals, context)
                    val_log = {
                                'method': 'write',
                                'object_id': model_id,
                                'user_id': uid,
                                'res_id': record_id,
                            }
                    log_id = log_pool.create(cr, uid, val_log)
                    for line in lines:
                        val_line = line.copy()
                        val_line['log_id'] = log_id
                        log_line_pool.create(cr, uid, val_line)
        
        return True
    
    def prepare_log_holiday_line_data(self, cr, uid, record_id, model, vals, context=None):
        res = []
        field_pool = self.pool.get('ir.model.fields')
        model_pool = self.pool.get('ir.model')
        if vals and record_id:
            record = self.read(cr, uid, record_id, vals.keys())
            for field_name in vals:
                field_obj = self._all_columns.get(field_name)
                assert field_obj, _("'%s' field does not exist in '%s' model" %(line['name'], model.model))
                field_obj = field_obj.column
                search_models = [model.id]
                if self._inherits:
                    search_models += model_pool.search(cr, uid, [('model', 'in', self._inherits.keys())])
                field_id = field_pool.search(cr, uid, [('name', '=', field_name), ('model_id', 'in', search_models)])
                
                old_value = record.get(field_name,'')
                new_value = vals.get(field_name, '')
                if field_obj._type == 'many2one':
                    old_value = old_value and old_value[1] or old_value
                    new_value = new_value and new_value[1] or new_value
                elif field_obj._type == 'boolean':
                    old_value = str(old_value)
                    new_value = str(new_value)
                
                
                line = {  "field_id": field_id and field_id[0] or False,
#                           "old_value": old_value,
#                           "new_value": new_value,
                          "old_value_text": old_value,
                          "new_value_text": new_value,
                          "field_description": field_obj.string
                      }
                res.append(line)
        
        return res
        
    def create_allocation_for_newbie(self, cr, uid, employee_id, company_id=False, context=None):
        log.info('create allocation_for_newbie start()')
        # log.info('create allocation_for_newbie employee_id %s - company_id %s' % (employee_id, company_id))
        try:
            parameter_obj = self.pool.get('ir.config_parameter')
            leave_type_code = parameter_obj.get_param(cr, uid, 'ts.leave.type.default.code').split(',')
            stipulated_permit_code = parameter_obj.get_param(cr, uid, 'ts.param.type.stipulated.permit').split(',')
            leave_type_obj = self.pool.get('hr.holidays.status')
            holiday_status_id = leave_type_obj.search(cr, uid, [('code', 'in', leave_type_code)])
            if holiday_status_id:
                holiday_status_id = holiday_status_id[0]
            
            #Khong tao phep nam cho CTV trong truong hop binh thuong
            is_colla, is_prob = self.is_collaborator_or_probation(cr, uid, employee_id, company_id, context)
            if is_colla:
                return True

            # general param
            general_param_obj = self.pool.get('vhr.ts.general.param')
            new_staff_param_obj = self.pool.get('vhr.ts.new.staff.param')
            employee_obj = self.pool.get('hr.employee')
            wr_pool = self.pool.get('vhr.working.record')
            general_param_id = general_param_obj.get_latest_param(cr, uid, company_id=company_id, context=context)
            new_staff_param_ids = new_staff_param_obj.search(cr, uid, [('ts_gen_param_id', '=', general_param_id)])

            param_data = new_staff_param_obj.read(cr, uid, new_staff_param_ids, ['from_date', 'to_date', 'coef'],
                                                  context=context)

            employee_data = employee_obj.browse(cr, uid, employee_id, fields_process=['join_date', 'job_level_person_id'])
            job_level_person_id = employee_data and employee_data.job_level_person_id and employee_data.job_level_person_id.id or False
            join_date = employee_data and employee_data.join_date or False
            
            
            if job_level_person_id and join_date:
                value = leave_type_obj.get_days_by_param_by_job_level(cr, uid, employee_id, company_id=False,
                                                                      code=stipulated_permit_code,
                                                                      context=context)
                
                coef = 0
                join_date = datetime.strptime(join_date, DEFAULT_SERVER_DATE_FORMAT)
                for param in param_data:
                    date_range = range(param['from_date'], param['to_date'] +1)
                    effect_from_day = join_date.day
                    if effect_from_day in date_range:
                        coef = float(param['coef'])
                        break
                effect_from_month = join_date.month
                number_of_days = value * (12 - effect_from_month + coef) / 12.0
                number_of_days = float("{0:.1f}".format(number_of_days))
                
                number_of_days = round(number_of_days*2)/2
                    
                    
                self.create_employee_holidays(cr, uid, employee_id, company_id, holiday_status_id, number_of_days, context)
                log.info('create allocation_for_newbie employee_id %s - company_id %s - number_of_days_temp %s' % (
                    employee_id, company_id, value))
            else:
                log.info('create allocation_for_newbie job_level_person_id is False')
        except Exception, e:
            log.exception('create allocation_for_newbie employee_id %s - company_id %s - Exception %s' % (
                employee_id, company_id, e.message))

        log.info('create allocation_for_newbie end()')
        return True
    
    

    @staticmethod
    def rounded_days(number_of_days):
        return round(number_of_days / 0.5) * 0.5

    def cron_check_seniority(self, cr, uid, context=None):
        if not context:
            context = {}
            
        log.info('cron_check_seniority start()')
        parameter_obj = self.pool.get('ir.config_parameter')
        employee_obj = self.pool.get('hr.employee')
        holiday_status_obj = self.pool.get('hr.holidays.status')
        param_job_level_obj = self.pool.get('vhr.ts.param.job.level')
        
        leave_type_code = parameter_obj.get_param(cr, uid, 'ts.leave.type.default.code').split(',')
        holiday_status_ids = holiday_status_obj.search(cr, uid, [('code', 'in', leave_type_code)])
        holiday_status_id = False
        if holiday_status_ids:
            holiday_status_id = holiday_status_ids[0]
                
        today = date.today().strftime(DEFAULT_SERVER_DATE_FORMAT)
        
        plus_one_code = parameter_obj.get_param(cr, uid, 'ts.param.type.seniority.plus.one.day.be.allowed.code') or ''
        plus_one_code = plus_one_code.split(',')
        
        # optimize
        param_job_level_ids = param_job_level_obj.search(cr, uid, [('value', 'not in', ['0', '']),
                                                                   ('param_type_id.code', 'in', plus_one_code),
                                                                   ('effect_from','<=',today),
                                                                   '|',('effect_to','=',False),
                                                                        ('effect_to','>=',today),
                                                                   ], order = 'value asc')
        
        if param_job_level_ids:
            smallest_param = param_job_level_obj.read(cr, uid, param_job_level_ids[0], ['value'])
            smallest_year_for_seniority = smallest_param.get('value', 0)
            try:
                smallest_year_for_seniority = int(smallest_year_for_seniority)
            except Exception as e:
                log.exception(e)
                raise osv.except_osv('Value of Parameter By Job Level with id %s must be integer' %param_job_level_ids[0])
        
            param_job_levels = param_job_level_obj.read(cr, uid, param_job_level_ids, ['job_level_id','job_level_new_id'])
            job_level_new_ids = [param['job_level_new_id'][0] for param in param_job_levels if param.get('job_level_new_id')]
            #Get day of year, if employee work from these can addition seniority
            start_year_day = datetime.now() + relativedelta(years=-smallest_year_for_seniority)
            
            domain = [('join_date', '<=', start_year_day),
                      ('job_level_person_id', 'in', job_level_new_ids)]
            
            if context.get('department_id', False):
                domain.append(('department_id','in',context['department_id']))
            
            if context.get('division_id', False):
                domain.append(('division_id','in',context['division_id']))
            
            check_on_day = False
            if context.get('check_on_day', False):
                check_on_day = True
            
            #Get list employee join before last year
            employee_ids = employee_obj.search(cr, uid, domain, context={'search_all_employee': True})
            
            for employee_info in employee_obj.read(cr, uid, employee_ids, ['join_date','code']):
                #Get number of year to plus one day in annual leave
                value = holiday_status_obj.get_days_by_param_by_job_level(cr,uid, employee_info.get('id'),company_id=False,code=plus_one_code,context=context)
                if value and employee_info.get('join_date'):
                    join_date = employee_info.get('join_date')
                    #Lấy danh sách phép của nhân viên trong thời gian làm việc thuộc leave type trừ thâm niên
                    sql = """
                            SELECT
                              coalesce(sum(number_of_days_temp), 0)
                            FROM hr_holidays
                            WHERE type = 'remove'
                                  AND employee_id = %s
                                  AND state = 'validate'
                                  AND date_from>= '%s'
                                  AND holiday_status_id IN (SELECT
                                                              id
                                                            FROM hr_holidays_status
                                                            WHERE is_seniority IS TRUE)
    
                    """ % (employee_info.get('id'),join_date)
                    cr.execute(sql)
                    seniority_days = cr.fetchone() or 0
                    if seniority_days:
                        seniority_days = seniority_days[0]
                    
                    #Get real join day after minus total leave have leave type is_seniorty
                    join_date = datetime.strptime(join_date, DEFAULT_SERVER_DATE_FORMAT) - timedelta(days=seniority_days)
    
                    delta = relativedelta(datetime.now(), join_date)
                    is_allow_to_create = False
                    
                    if check_on_day:
                        is_allow_to_create = (delta.years%value == 0 and delta.months==0)
                    else:
                        is_allow_to_create = delta.years >= value
                        
                    if is_allow_to_create:
                        res_ids = osv.osv.search(self, cr, uid, [('type', '=', 'add'),
                                                                 ('holiday_status_id','=',holiday_status_id),
                                                                 ('employee_id', '=', employee_info.get('id')),
                                                                 ('year', '=', datetime.now().year),
                                                                 ('state', '=', 'validate')])
                        
                        log.info('cron_check_seniority update employee_id %s - %s days' % (employee_info.get('code'), int(delta.years / value)))
                        if res_ids:
                            self.write(cr, uid, res_ids, {'seniority_leave': int(delta.years / value)})
                    
        log.info('cron_check_seniority end()')
        return True

    def create_allocation_for_employee_change_level(self, cr, uid, employee_id, company_id=False, context=None):
        """
        Update annual day of employee when have change job level
        """
        if not context:
            context = {}
            
        log.info('create allocation_for_employee_change_level start()')
        working_pool = self.pool.get('vhr.working.record')
        general_param_obj = self.pool.get('vhr.ts.general.param')
        change_level_param_obj = self.pool.get('vhr.ts.change.level.param')
        instance_obj = self.pool.get('vhr.employee.instance')
        leave_type_obj = self.pool.get('hr.holidays.status')
        
        #Khong tao phep nam cho CTV trong truong hop binh thuong
        is_colla, is_prob = self.is_collaborator_or_probation(cr, uid, employee_id, company_id, context)
        if is_colla:
            return True
            
        general_param_id = general_param_obj.get_latest_param(cr, uid, company_id=False, context=context)
        # level config
        change_level_ids = change_level_param_obj.search(cr, uid, [('ts_gen_param_id', '=', general_param_id)])
        change_level_data = change_level_param_obj.read(cr, uid, change_level_ids, ['from_date', 'to_date', 'coef'], context=context)
        
        first_year_date = date(datetime.today().year, 1, 1).strftime(DEFAULT_SERVER_DATE_FORMAT)
        last_year_date = date(datetime.today().year, 12, 31).strftime(DEFAULT_SERVER_DATE_FORMAT)

        parameter_obj = self.pool.get('ir.config_parameter')
        leave_type_code = parameter_obj.get_param(cr, uid, 'ts.leave.type.default.code').split(',')
        stipulated_permit_code = parameter_obj.get_param(cr, uid, 'ts.param.type.stipulated.permit').split(',')
        holiday_status_id = leave_type_obj.search(cr, uid, [('code', 'in', leave_type_code)])
        if holiday_status_id:
            holiday_status_id = holiday_status_id[0]
        
        change_local_comp_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_master_data_change_local_company') or ''
        change_local_comp_code_list = change_local_comp_code.split(',')
        
        dismiss_local_comp_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_master_data_dismiss_local_company') or ''
        dismiss_local_comp_code_list = dismiss_local_comp_code.split(',')
        context['change_local_comp_code_list'] = change_local_comp_code_list
        context['dismiss_local_comp_code_list'] = dismiss_local_comp_code_list

        number_of_days = float(0)
        date_start_at_company = last_year_date
        
        context['stipulated_permit_code'] = stipulated_permit_code
        context['change_level_data'] = change_level_data
        number_of_days, date_start_at_company = self.get_annual_leave_base_on_duration(cr, uid, employee_id, company_id, 
                                                                                       first_year_date, last_year_date, date_start_at_company, 
                                                                                       number_of_days, context)
        
        #Nếu nhân viên bắt đầu làm việc trong năm nay, và start_wr_id của instance có change form là chuyển đổi công ty
        #thì cần tính annual leave từ đầu năm tới khi trước 1 ngày của instance mới vì nhân viên chỉ chuyển công ty, vẫn giữ phép cũ
        if self.compare_day(first_year_date,date_start_at_company) > 0:
            count = 0
            context['count'] = count
            number_of_days, date_start_at_company  = self.check_to_get_annual_leave_if_not_cover_all_year(cr, uid, employee_id, company_id, 
                                                                                                          first_year_date, date_start_at_company, number_of_days, context)
            
                            
            
        log.info('create allocation_for_employee_change_level %s' % number_of_days)
        context['allocation_for_emp_change_level'] = True
        self.create_employee_holidays(cr, uid, employee_id, company_id, holiday_status_id, number_of_days, context)
        log.info('create allocation_for_employee_change_level end()')
        
    
    def check_to_get_annual_leave_if_not_cover_all_year(self, cr, uid, employee_id, company_id, first_year_date, date_start_at_company, number_of_days, context=None):
        if not context:
            context = {}
        
        count = context.get('count',0)
        instance_obj = self.pool.get('vhr.employee.instance')
        
        change_local_comp_code_list = context.get('change_local_comp_code_list','')
        dismiss_local_comp_code_list = context.get('dismiss_local_comp_code_list',[])
        
        instance_ids = instance_obj.search(cr, uid, [('employee_id','=',employee_id),
                                                          ('company_id','=',company_id),
                                                          ('date_start','>=',first_year_date)])
        if instance_ids:
        
            instance = instance_obj.browse(cr, uid, instance_ids[0], fields_process=['start_wr_id'])
            start_change_form_ids = instance.start_wr_id and instance.start_wr_id.change_form_ids
            start_change_form_list = [form.code for form in start_change_form_ids]
            if set(change_local_comp_code_list).intersection(set(start_change_form_list)):
                #If new instance create with WR have change form "chuyen doi cong ty", search other company 
                instance_ids = instance_obj.search(cr, uid, [('employee_id','=', employee_id),
                                                             ('company_id','!=',company_id),
                                                             ('date_end','>=',first_year_date),
                                                             ('date_end','<=', date_start_at_company)], order='date_start desc')
                if instance_ids:
                    check_instance = False
                    for instance in instance_obj.browse(cr, uid, instance_ids):
                        end_change_form_ids = instance.end_wr_id and instance.end_wr_id.change_form_ids
                        end_change_form_list = [form.code for form in end_change_form_ids]
                        if set(dismiss_local_comp_code_list).intersection(set(end_change_form_list)):
                            check_instance = instance
                            break
                    
                    if check_instance:
                        company_id = check_instance.company_id and check_instance.company_id.id or False
                        date_end_instance = check_instance.date_end 
                        context['compare_before_last_day_one_day'] = True
                        number_of_days, date_start_at_company = self.get_annual_leave_base_on_duration(cr, uid, employee_id, company_id, 
                                                                                                       first_year_date, date_end_instance, 
                                                                                                       date_start_at_company, number_of_days, context)
                        
                        if self.compare_day(first_year_date,date_start_at_company) > 0 and count < 12:#not loop over 12 time
                            context['count'] = count + 1
                            number_of_days, date_start_at_company  = self.check_to_get_annual_leave_if_not_cover_all_year(cr, uid, employee_id, company_id, 
                                                                                                                          first_year_date, date_start_at_company, number_of_days, context)
        
        return number_of_days, date_start_at_company
        
    def get_annual_leave_base_on_duration(self, cr, uid, employee_id, company_id, first_date_of_duration, last_date_of_duration, 
                                          date_start_at_company, number_of_days, context=None):
        if not context:
            context = {}
        
        stipulated_permit_code = context.get('stipulated_permit_code','')
        change_level_data = context.get('change_level_data', [])
        working_pool = self.pool.get('vhr.working.record')
        leave_type_obj = self.pool.get('hr.holidays.status')
        
        cp_last_date_of_duration = last_date_of_duration
        if context.get('compare_before_last_day_one_day', False):
            cp_last_date_of_duration  = (datetime.strptime(last_date_of_duration, DEFAULT_SERVER_DATE_FORMAT) - relativedelta(days=1)).strftime(DEFAULT_SERVER_DATE_FORMAT)


        wr_ids = working_pool.get_list_working_record_of_employee_in_date_range(cr, uid, employee_id,
                                                                                company_id, first_date_of_duration, cp_last_date_of_duration,
                                                                                context=context)
        
        for wr in working_pool.browse(cr, uid, wr_ids, fields_process=['effect_from', 'effect_to'], context=context):
            log.info('create allocation_for_employee_change_level wr_id %s job_level_id_old %s job_level_person_id_new %s ' % (
                wr.id, wr.job_level_person_id_old and wr.job_level_person_id_old.name or '',
                wr.job_level_person_id_new and wr.job_level_person_id_new.name or ''))
            
            effect_from = wr.effect_from
            effect_to = wr.effect_to
            if self.compare_day(effect_from, date_start_at_company) > 0:
                date_start_at_company = effect_from
            
            job_level_person_id_new = wr.job_level_person_id_new and wr.job_level_person_id_new.id or False
            if not job_level_person_id_new:
                log.info('WR %s dont have job_level_person_id_new' % wr.id)
            
            value = self.get_param_base_on_job_level(cr, uid, stipulated_permit_code, job_level_person_id_new)
            value = float(value)
#             value = leave_type_obj.get_days_by_param_by_job_level(cr, uid, employee_id, company_id=False,
#                                                                   code=stipulated_permit_code,
#                                                                   job_level_person_id=job_level_person_id_new,
#                                                                   effect_from=effect_from,
#                                                                   effect_to=effect_to,
#                                                                   context=context)
            log.info('create allocation_for_employee_change_level job_level %s - value %s days-  %s - %s()' % (
                wr.job_level_person_id_new, value, effect_from, effect_to))
            current_year = datetime.now().year
            if not effect_to or self.compare_day(last_date_of_duration, effect_to) >0:
                effect_to = last_date_of_duration
            
            if self.compare_day(effect_from, first_date_of_duration) > 0:
                effect_from = first_date_of_duration
            
            effect_from = datetime.strptime(effect_from, DEFAULT_SERVER_DATE_FORMAT)
            effect_to = datetime.strptime(effect_to, DEFAULT_SERVER_DATE_FORMAT)
            
            for change_range in change_level_data:
                date_range = [change_range['from_date'], change_range['to_date']]
                coef = 0
                if effect_to.day in date_range:
                    coef = change_range['coef']
            #Get number of days in one year
            tm_yday = float(datetime(current_year, 12, 31).timetuple().tm_yday)
            #Get number of annual days in effect_from - effect_to
            diff = ((effect_to - effect_from).days+1) / tm_yday * 12
            number_of_days += value * (diff + coef) / 12.0
            log.info('create allocation_for_employee_change_level '
                     '\nadjust date range %s - %s - coef %s - month %s() - number_of_days %s' % (
                         effect_from.strftime(DEFAULT_SERVER_DATE_FORMAT),
                         effect_to.strftime(DEFAULT_SERVER_DATE_FORMAT),
                         coef, diff, number_of_days))
        
        return number_of_days, date_start_at_company
        
        
    def cron_generate_annual_leave_balance(self, cr, uid, input_employee_ids=[], input_year=False, context=None):
        if context is None:
            context = {}
        log.info('cron_generate_annual_leave_balance start()')
        print 'input_year=',input_year,';;input_employee_ids=',input_employee_ids
        parameter_obj = self.pool.get('ir.config_parameter')
        employee_obj = self.pool.get('hr.employee')
        leave_type_obj = self.pool.get('hr.holidays.status')
        #
        leave_type_code = parameter_obj.get_param(cr, uid, 'ts.leave.type.default.code').split(',')
        stipulated_permit_code = parameter_obj.get_param(cr, uid, 'ts.param.type.stipulated.permit').split(',')

        holiday_status_id = leave_type_obj.search(cr, uid, [('code', 'in', leave_type_code)])
        if holiday_status_id:
            holiday_status_id = holiday_status_id[0]
        current_year = datetime.now().year
        # check employee is created before.
        year_val = current_year + 1
        # for generate employee annual leave balance generate
        if input_year:
            year_val = input_year
        
        # general param
        general_param_obj = self.pool.get('vhr.ts.general.param')
        new_staff_param_obj = self.pool.get('vhr.ts.new.staff.param')
        general_param_id = general_param_obj.get_latest_param(cr, uid, False, context=context)
        new_staff_param_ids = new_staff_param_obj.search(cr, uid, [('ts_gen_param_id', '=', general_param_id)])

        param_data = new_staff_param_obj.read(cr, uid, new_staff_param_ids, ['from_date', 'to_date', 'coef'],context=context)
            
        employee_domain = []
        if input_employee_ids:
            employee_domain = [('id', 'in', input_employee_ids)]
            
        
        if context.get('division_id', False):
            employee_domain.append(('division_id','in', context['division_id']))
        elif context.get('department_id', False):
            employee_domain.append(('department_id','in', context['department_id']))
        
        employee_ids = employee_obj.search(cr, uid, employee_domain, context={'search_all_employee':True})
        
        context['get_correct_value'] = True
        
        print "\n len employee_ids=",len(employee_ids)
        for employee_info in self.pool.get('hr.employee').browse(cr, uid, employee_ids):
            try:
                log.info('cron_generate_annual_leave_balance employee %s start()' % employee_info.id)
                
                join_date = employee_info and employee_info.join_date or False
                
                is_offical = employee_info.main_working and employee_info.main_working.contract_id \
                                     and employee_info.main_working.contract_id.type_id \
                                     and employee_info.main_working.contract_id.type_id.contract_type_group_id\
                                     and employee_info.main_working.contract_id.type_id.contract_type_group_id.is_offical or False
                
                if not is_offical:
                    continue
                
                value = leave_type_obj.get_days_by_param_by_job_level(cr, uid, employee_info.id, company_id=False,
                                                                      code=stipulated_permit_code,
                                                                      context=context)
                
                #Dont generate for employee dont have paramerter by job level
                if value == None:
                    continue
                
                number_of_days = value
                
                if join_date:
                    join_date = datetime.strptime(join_date, DEFAULT_SERVER_DATE_FORMAT)
                    join_year = join_date.year
                    
                    if join_year == year_val:
                        coef = 0
                        for param in param_data:
                            date_range = range(param['from_date'], param['to_date'] +1)
                            effect_from_day = join_date.day
                            if effect_from_day in date_range:
                                coef = float(param['coef'])
                                break
                            
                        effect_from_month = join_date.month
                        number_of_days = value * (12 - effect_from_month + coef) / 12.0
                        number_of_days = float("{0:.1f}".format(number_of_days))
                        
                        number_of_days = round(number_of_days*2)/2
                        
                    elif join_year > year_val:
                        employee_login = employee_info.login
                        log.exception('Employee "%s" didn\'t work at %s'%(employee_login,year_val))
                        continue
                
                
                vals = {'department_id': employee_info.department_id and employee_info.department_id.id or False,
                        'report_to_id': employee_info.report_to and employee_info.report_to.id or False,
                        'dept_head_id': employee_info.department_id and employee_info.department_id.manager_id
                                        and employee_info.department_id.manager_id.id or False,
                        'employee_id': employee_info.id,
                        'type': 'add',
                        'holiday_type': 'employee',
                        'is_offline': True,
                        'year': year_val,
                        'holiday_status_id': holiday_status_id,
                        'number_of_days_temp': number_of_days}
                context['get_all'] = 1
                already_create_ids = osv.osv.search(self, cr, uid, [('holiday_status_id', '=', holiday_status_id),
                                                                    ('type', '=', 'add'),
                                                                    ('employee_id', '=', employee_info.id),
                                                                    ('year', '=', year_val),
                                                                    ('state', '=', 'validate')],
                                                    context=context)
                if already_create_ids:
#                     print '\n\n\n =====',already_create_ids
                    self.write(cr, uid, already_create_ids, vals, context=context)
                else:
                    self.create(cr, uid, vals, context=context)
                log.info('cron_generate_annual_leave_balance employee_id %s - number_of_days_temp %s' % (
                    employee_info.id, value))
            except Exception, e:
                log.exception('cron_generate_annual_leave_balance exception %s - %s' % (employee_info.id, e.message))
        log.info('cron_generate_annual_leave_balance end()')
        return True
    
    
    def get_colla_emp_satisfy_condition_to_gen_annual_leave(self, cr, uid, employee_ids, context=None):
        
        emp_obj = self.pool.get('hr.employee')
        contract_obj = self.pool.get('hr.contract')
        parameter_obj = self.pool.get('ir.config_parameter')
        
        today = date.today().strftime(DEFAULT_SERVER_DATE_FORMAT)
        point_date = (date.today() - relativedelta(years=1)).strftime(DEFAULT_SERVER_DATE_FORMAT)
        
        office_code = parameter_obj.get_param(cr, uid, 'vhr_timesheet_office_not_gen_annual_leave_for_colla') or ''
        office_code = office_code.split(',')
        office_ids= self.pool.get('vhr.office').search(cr, uid, [('code','in',office_code)])
        
        job_title_code = parameter_obj.get_param(cr, uid, 'vhr_timesheet_job_title_gen_annual_leave_for_colla') or ''
        job_title_code = job_title_code.split(',')
        title_ids= self.pool.get('vhr.job.title').search(cr, uid, [('code','in',job_title_code)])
        
        job_type_ids = self.pool.get('vhr.dimension').search(cr, uid, [('code','=','FULLTIME'),
                                                                   ('dimension_type_id.code','=','JOB_TYPE')])
        
        contract_type_code = parameter_obj.get_param(cr, uid, 'vhr_collaborator_code') or ''
        contract_type_code = contract_type_code.split(',')
        type_ids = self.pool.get('hr.contract.type').search(cr, uid, [('code','in',contract_type_code)])
        
        emp_ids = emp_obj.search(cr, uid, [('join_date','<=', point_date),
                                           ('office_id','not in',office_ids),
                                           ('title_id','in',title_ids),
                                           ])
        res_emp_ids = []
        if employee_ids:
            emp_ids = list(set(emp_ids).intersection(set(employee_ids)))
        if emp_ids:
            #Search current contract to check if type is CTV and fulltime
            contract_ids = contract_obj.search(cr, uid, [('employee_id','in',emp_ids),
                                                         ('job_type_id','in',job_type_ids),
                                                         ('type_id','in',type_ids),
                                                         ('state','=','signed'),
                                                         ('date_start','<=',today),
                                                         "|",('date_end','=',False),
                                                             ('date_end','>=',today)])
            if contract_ids:
                for contract in contract_obj.read(cr, uid, contract_ids, ['employee_id']):
                    employee_id = contract.get('employee_id', False) and contract['employee_id'][0]
                    if employee_id in emp_ids:
                        res_emp_ids.append(employee_id)
        
        return res_emp_ids
    
    def create_annual_leave_for_colla_emp(self,cr, uid, employee_info, year_val, default_number_of_days, param_data, holiday_status_id, context=None):
        try:
            log.info('cron_generate_annual_leave_balance employee CTV %s start()' % employee_info.code)
            number_of_days = default_number_of_days
            
            join_date_plus_one = datetime.strptime(employee_info.join_date, DEFAULT_SERVER_DATE_FORMAT) + relativedelta(years=1)
            join_date_plus_one_year = join_date_plus_one.year
            
            if join_date_plus_one_year == year_val:
                coef = 0
                for param in param_data:
                    date_range = range(param['from_date'], param['to_date'] +1)
                    effect_from_day = join_date_plus_one.day
                    if effect_from_day in date_range:
                        coef = float(param['coef'])
                        break
                    
                effect_from_month = join_date_plus_one.month
                number_of_days = default_number_of_days * (12 - effect_from_month + coef) / 12.0
                number_of_days = float("{0:.1f}".format(number_of_days))
                
                #0<=x<0.25 = 0
                #0.25<=x <0.75 = 0.5
                #x>=.75 = 1
                number_of_days = round(number_of_days*2)/2.0
            
            
            vals = {'department_id': employee_info.department_id and employee_info.department_id.id or False,
                    'report_to_id': employee_info.report_to and employee_info.report_to.id or False,
                    'dept_head_id': employee_info.department_id and employee_info.department_id.manager_id
                                    and employee_info.department_id.manager_id.id or False,
                    'employee_id': employee_info.id,
                    'type': 'add',
                    'holiday_type': 'employee',
                    'is_offline': True,
                    'year': year_val,
                    'holiday_status_id': holiday_status_id,
                    'number_of_days_temp': number_of_days}
            
            context['get_all'] = 1
            already_create_ids = osv.osv.search(self, cr, uid, [('holiday_status_id', '=', holiday_status_id),
                                                                ('type', '=', 'add'),
                                                                ('employee_id', '=', employee_info.id),
                                                                ('year', '=', year_val),
                                                                ('state', '=', 'validate')],
                                                context=context)
            if already_create_ids:
                self.write(cr, uid, already_create_ids, vals, context=context)
            else:
                self.create(cr, uid, vals, context=context)
                
        except Exception, e:
            log.exception('cron_generate_annual_leave_balance exception %s - %s' % (employee_info.code, e.message))
        
    def cron_generate_annual_leave_balance_for_colla(self, cr, uid, employee_ids, year_val, context=None):
        #Search all colla emp satisfy condition to create new annual leave
        '''CTV làm việc toàn thời gian, tại văn phòng, ký HĐ CTV (có trích đóng BH)
        Thâm niên từ 12 tháng liên tục trở lên mới có phép
        '''
        log.info('cron_generate_annual_leave balance CTV start()')
        
        if not context:
            context = {}
            
        emp_obj = self.pool.get('hr.employee')
        parameter_obj = self.pool.get('ir.config_parameter')
        leave_type_obj = self.pool.get('hr.holidays.status')
        
        general_param_obj = self.pool.get('vhr.ts.general.param')
        new_staff_param_obj = self.pool.get('vhr.ts.new.staff.param')
        general_param_id = general_param_obj.get_latest_param(cr, uid, False, context=context)
        new_staff_param_ids = new_staff_param_obj.search(cr, uid, [('ts_gen_param_id', '=', general_param_id)])

        param_data = new_staff_param_obj.read(cr, uid, new_staff_param_ids, ['from_date', 'to_date', 'coef'],context=context)
        
        default_number_of_days = parameter_obj.get_param(cr, uid, 'vhr_timesheet_annual_leave_day_for_CTV') or 0
        try:
            default_number_of_days = int(default_number_of_days)
        except:
            default_number_of_days = 0
            
        
        res_emp_ids = self.get_colla_emp_satisfy_condition_to_gen_annual_leave(cr, uid, employee_ids, context)
        #If employee is CTV and fulltime and joindate <today-1year at office (!= Z0) and level =Temporary
        if res_emp_ids:
            leave_type_code = parameter_obj.get_param(cr, uid, 'ts.leave.type.default.code').split(',')

            holiday_status_id = leave_type_obj.search(cr, uid, [('code', 'in', leave_type_code)])
            if holiday_status_id:
                holiday_status_id = holiday_status_id[0]
            
            for employee_info in emp_obj.browse(cr, uid, res_emp_ids, fields_process=['department_id', 'report_to','join_date']):
                self.create_annual_leave_for_colla_emp(cr, uid, employee_info, year_val, default_number_of_days, 
                                                       param_data, holiday_status_id, context)
                        
        log.info('cron_generate_annual_leave balance CTV end()')
        return True
    
    def cron_generate_annual_leave_for_colla_emp_satisfy_condition(self, cr, uid, input_emp_ids=[], input_year=False, context=None):
        """
        Generate annual leave for colla employee satisfy condition but dont have any annual leave on year
        Note: Only create annual leave employee dont have annual leave
        """
        if not context:
            context = {}
            
        current_year = datetime.now().year
        # check employee is created before.
        year_val = current_year
        # for generate employee annual leave balance generate
        if input_year:
            year_val = input_year
        
        emp_obj = self.pool.get('hr.employee')
        parameter_obj = self.pool.get('ir.config_parameter')
        leave_type_obj = self.pool.get('hr.holidays.status')
        
        general_param_obj = self.pool.get('vhr.ts.general.param')
        new_staff_param_obj = self.pool.get('vhr.ts.new.staff.param')
        general_param_id = general_param_obj.get_latest_param(cr, uid, False, context=context)
        new_staff_param_ids = new_staff_param_obj.search(cr, uid, [('ts_gen_param_id', '=', general_param_id)])

        param_data = new_staff_param_obj.read(cr, uid, new_staff_param_ids, ['from_date', 'to_date', 'coef'],context=context)
        
        default_number_of_days = parameter_obj.get_param(cr, uid, 'vhr_timesheet_annual_leave_day_for_CTV') or 0
        try:
            default_number_of_days = int(default_number_of_days)
        except:
            default_number_of_days = 0
            
        res_emp_ids = self.get_colla_emp_satisfy_condition_to_gen_annual_leave(cr, uid, input_emp_ids, context)
        if res_emp_ids:
            leave_type_code = parameter_obj.get_param(cr, uid, 'ts.leave.type.default.code').split(',')

            holiday_status_id = leave_type_obj.search(cr, uid, [('code', 'in', leave_type_code)])
            if holiday_status_id:
                holiday_status_id = holiday_status_id[0]
            
            already_create_ids = osv.osv.search(self, cr, uid, [('holiday_status_id', '=', holiday_status_id),
                                                                        ('type', '=', 'add'),
                                                                        ('employee_id', 'in', res_emp_ids),
                                                                        ('year', '=', year_val),
                                                                        ('state', '=', 'validate'),
                                                                        ('number_of_days_temp','!=',0)],
                                                        context=context)
            
            if already_create_ids:
                old_leaves = self.read(cr, uid, already_create_ids, ['employee_id'])
                old_emp_ids = [leave.get('employee_id', False) and leave['employee_id'][0] for leave in old_leaves]
                res_emp_ids = list(set(res_emp_ids).difference(set(old_emp_ids)))
            if res_emp_ids:
                for employee_info in emp_obj.browse(cr, uid, res_emp_ids, fields_process=['department_id', 'report_to','join_date']):
                    self.create_annual_leave_for_colla_emp(cr, uid, employee_info, year_val, default_number_of_days, 
                                                           param_data, holiday_status_id, context)
                        
        log.info('cron_generate_annual_leave balance for not update emp end()')
        return True
                    

    def cron_generate_annual_leave_accumulation(self, cr, uid, context=None):
        """
        Should run on the last day of December
        """
        if not context:
            context = {}

        context['type'] = 'annual_leave_accumulation'
        holiday_status_pool = self.pool.get('hr.holidays.status')
        incremental_annual_leave_pool = self.pool.get('vhr.ts.incremental.annual.leave')
        config_parameter = self.pool.get('ir.config_parameter')
        log.info('cron_generate_annual_leave_accumulation start()')
        try:
            holiday_status_ids = []
            holiday_status_code = config_parameter.get_param(cr, uid, 'leave_type_code_for_accumulation')
            if holiday_status_code:
                holiday_status_code_list = holiday_status_code.split(',')
                # holiday_status_code_list = ['NB']
                holiday_status_ids = holiday_status_pool.search(cr, uid, [('code', 'in', holiday_status_code_list)],
                                                                order='id desc')

            current_year = datetime.now().year
            next_year = current_year + 1
            if holiday_status_ids:
                for holiday_status_id in holiday_status_ids:
                    holiday_status = holiday_status_pool.read(cr, uid, holiday_status_id, ['name'])
                    holiday_status_name = holiday_status.get('name', '')
                    context[
                        'mass_status_info'] = "Generate Annual Leave Accumulation for leave type '%s' in year %s" % (
                        holiday_status_name, next_year)
                    vals = {'year': next_year, 'holiday_status_id': holiday_status_id}
                    incremental_id = incremental_annual_leave_pool.create(cr, uid, vals)
                    cr.commit()
                    # Get employee have annual leave with holiday_status_id in current year to generate for next year
                    annual_leave_ids = osv.osv.search(self, cr, uid, [('type', '=', 'add'),
                                                                      ('year', '=', current_year),
                                                                      ('state', '=', 'validate'),
                                                                      ('holiday_status_id', '=', holiday_status_id),
                                                                      ('employee_id.active', '=', True)],context={'get_all': 1})
                    employee_ids = []
                    if annual_leave_ids:
                        annual_leaves = self.read(cr, uid, annual_leave_ids, ['employee_id'])
                        employee_ids = [annual_leave['employee_id'] and annual_leave['employee_id'][0] for annual_leave
                                        in annual_leaves]
                        employee_ids = list(set(employee_ids))
                    incremental_annual_leave_pool.thread_execute(cr, uid, [incremental_id], employee_ids, context)

        except Exception, e:
            log.exception('cron_generate_annual_leave_accumulation exception\n\n %s' % e.message)
        log.info('cron_generate_annual_leave_accumulation end()')
        return True

    def move_days_pre_year_accumulation(self, cr, uid, ids, context=None):
        update_ids = []
        for record in self.read(cr, uid, ids, ['type', 'temp_actual_days_of_pre_year']):
            temp_actual_days_of_pre_year = record['temp_actual_days_of_pre_year']
            super(vhr_holidays, self).write(cr, uid, record['id'], {'move_days_of_pre_year': True,
                                                                    'actual_days_of_pre_year': temp_actual_days_of_pre_year},
                                            context=context)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    # function for mail
    def get_url(self, cr, uid, res_id, context=None):
        if isinstance(res_id, list):
            res_id = res_id[0]
        model_data = self.pool.get('ir.model.data')
        parameter_obj = self.pool.get('ir.config_parameter')
        base_url = parameter_obj.get_param(cr, uid, 'web.base.url')
        action_id = model_data.xmlid_lookup(cr, uid, 'vhr_timesheet.open_leave_summary')[2]
        url = '%s/leave/registration?leave_id=%s' % (base_url, res_id)
        return url

    def get_format_date(self, cr, uid, res_id, date_string, context=None):
        if isinstance(res_id, list):
            res_id = res_id[0]
        if res_id and date_string:
            return datetime.strptime(date_string, DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y")
        return ''

    def get_email_from(self, cr, uid, res_id, context=None):
        email_from = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_master_data_email_system_config')
        return email_from if email_from else 'hr.service@hrs.com.vn'

    def get_last_user(self, cr, uid, res_id, context=None):
        if not context:
            context = {}
        result = self.pool.get('vhr.state.change').get_last_user_id(cr, uid, res_id, self._name)
        result = result if result else ''
        
        if context.get('force_to_do_action', False):
            result = False
        return result


    # -----------------------------
    # OpenChatter and notifications
    # -----------------------------

    def _needaction_domain_get(self, cr, uid, context=None):
        if not context:
            context = {}
        
        dom = False
        if context.get('leave_approval', False):
            context['search_all_employee'] = True
            emp_obj = self.pool.get('hr.employee')
            empids = emp_obj.search(cr, uid, [('user_id', '=', uid)], context=context)
            user_groups = self.pool.get('res.users').get_groups(cr, uid)
            
            dom = ['|','|',
                        '&', ('state', '=', 'confirm'), ('report_to_id', 'in', empids),
                        '&', ('state', '=', 'validate1'), ('dept_head_id', 'in', empids),# if this user is a hr.manager, he should do second validations
                        '&', ('state', '=', 'draft'), ('employee_id', 'in', empids)
                        ]
            
            if 'vhr_cb_timesheet' in user_groups:
                dom.insert(0,'|')
                dom.append(('state','=','validate2'))
        
        return dom


    def cron_update_totay_days(self, cr, uid, context=None):
        """
        Cập nhật lại thông tin total ngày còn lại, ngày hết hạn của annual leave.. khi tới expire day
        """
        year = date.today().year
        today = date.today().strftime(DEFAULT_SERVER_DATE_FORMAT)
        update_ids = self.search(cr, uid, [('type', '=', 'add'),
                                           ('year','=',year),
                                           ('expiry_date_of_days_pre_year', '<=', today),
                                           ('move_days_of_pre_year', '=', True),
                                           ('remain_days_of_pre_year', '>', 0),
                                           ('total_destroy_days', '=', 0)],context={'get_all': 1})

        if update_ids:
            log.info("Update for check expire days of %s annual leave" % len(update_ids))

            sql = 'UPDATE hr_holidays SET total_destroy_days= %s, total_remain_days=%s WHERE id=%s'
            for record in self.read(cr, uid, update_ids, ['remain_days_of_pre_year', 'total_days', 'total_taken_days']):
                vals = {}
                total_destroy_days = record.get('remain_days_of_pre_year', 0) or 0
                total_remain_days = ( record.get('total_days', 0) or 0) - (
                    record.get('total_taken_days', 0) or 0) - total_destroy_days

                cr.execute(sql % (total_destroy_days, total_remain_days, record['id']))

            log.info("End Update for check expire days of %s annual leave" % len(update_ids))

        return True

    def cron_update_all_none_total_holidays_data(self, cr, uid, context=None):
        """
        Cập nhật lại thông tin total ngày dùng/ ngày còn lại, ngày hết hạn của annual leave.. 
        """
        today = date.today()
        update_ids = self.search(cr, uid, [('type', '=', 'add')],context={'get_all': 1})

        log.info("Update for total days of %s annual leave" % len(update_ids))
        index = 0

        if update_ids:
            sql = """
                    UPDATE hr_holidays 
                    SET     total_days= %s, 
                            total_taken_days=%s,
                            total_remain_days=%s,
                            total_destroy_days=%s
                    
                    WHERE id=%s
                """
            for record in self.read(cr, uid, update_ids,
                                    ['days_of_year', 'days_taken_of_pre_year', 'days_taken_of_year',
                                     'remain_days_of_year', 'expiry_date_of_days_pre_year',
                                     'actual_days_of_pre_year',
                                     'remain_days_of_pre_year', 'move_days_of_pre_year']):
                index += 1
                log.info('Updated for total days for %s annual leave' % index)
                total_days = record.get('days_of_year', 0) or 0
                total_taken_days = (record.get('days_taken_of_pre_year', 0) or 0) + (
                    record.get('days_taken_of_year', 0) or 0)
                total_remain_days = record.get('remain_days_of_year', 0) or 0
                total_destroy_days = 0
                if record.get('expiry_date_of_days_pre_year', False) and record.get('move_days_of_pre_year', False):
                    expiry_date_of_days_pre_year = datetime.strptime(record['expiry_date_of_days_pre_year'],
                                                                     DEFAULT_SERVER_DATE_FORMAT).date()
                    total_days += ( record.get('actual_days_of_pre_year', 0) or 0 )
                    if today <= expiry_date_of_days_pre_year:
                        total_remain_days += ( record.get('remain_days_of_pre_year', 0) or 0)
                    else:
                        total_destroy_days = (record.get('remain_days_of_pre_year', 0) or 0)

                result_sql = sql % (total_days, total_taken_days, total_remain_days, total_destroy_days, record['id'])
                cr.execute(result_sql)

        log.info(" End Update for total days of %s annual leave" % len(update_ids))

        return True
    
    def cron_update_leave_request_to_next_year(self, cr, uid, context=None):
        log.info("Start Update Leave Request to Next year")
        holiday_pool = self.pool.get('hr.holidays')
       
        holiday_ids = holiday_pool.search(cr, uid, [('is_missing_holiday_line','=',True), ('state','!=','refuse')])
        if holiday_ids:
            log.info("Ids need to update:" + str(holiday_ids))
            for holiday in holiday_pool.read(cr, uid, holiday_ids, ['employee_id','company_id','date_from','date_to','number_of_days_temp']):
                employee_id = holiday.get('employee_id', False) and holiday['employee_id'][0] or False
                company_id = holiday.get('company_id', False) and holiday['company_id'][0] or False
                date_from = holiday.get('date_from', False)
                date_to = holiday.get('date_to', False)
                number_of_days_temp = holiday.get('number_of_days_temp', 0)
                list_date, dict_hours, dict_type_workday = self.generate_date(cr, uid, employee_id, company_id, date_from, date_to)
                if list_date:
                    list_date, list_date_taken = self.remove_taken_days(cr, [], employee_id, list_date)
                
                #Check if make Working schedule detail for over date_to in leave request
                is_missing_holiday_line = True
                date_to_1  = (datetime.strptime(date_to, DEFAULT_SERVER_DATE_FORMAT) + relativedelta(days=1)).strftime(DEFAULT_SERVER_DATE_FORMAT)
                date_to_10  = (datetime.strptime(date_to, DEFAULT_SERVER_DATE_FORMAT) + relativedelta(days=10)).strftime(DEFAULT_SERVER_DATE_FORMAT)
                
                list_date_check, dict_hours_check, dict_type_workday = self.generate_date(cr, uid, employee_id, company_id, date_to_1, date_to_10)
                if list_date_check:
                    is_missing_holiday_line = False
                
                vals = {'is_missing_holiday_line': is_missing_holiday_line}
                #Have new date generated
                if list_date:
                    log.info("Update Leave Request " + str(holiday['id']))   
                    holiday_line_ids = []
                    list_haft_date_info, list_haft_date_name, list_date_must_full_leave = self.get_haft_date_info(cr, uid, [holiday['id']], employee_id, list_date)
                    new_number_of_days_temp = 0
                    for val in list_date:
                        status = 'full'
                        line_number_of_days = dict_type_workday.get(val,1)
                        is_edit_status = True
                        do_not_show_date = False
                        if val in list_haft_date_name:
                            line_number_of_days = dict_type_workday.get(val,1)* 0.5
                            for item in list_haft_date_info:
                                if item['date'] == val:
                                    status = item['status'] == 'morning' and 'afternoon' or 'morning'
                                    is_edit_status = False
                                    do_not_show_date = item.get('do_not_show', False)
                        
                        elif val in list_date_must_full_leave:
                            is_edit_status = False
                        
                        new_number_of_days_temp += line_number_of_days
                        #Case: at date val, employee have shift = 0.5 day and employee had leave request on that day, so employee don't have any working time on that day to take leave
                        if do_not_show_date:
                            continue
                        line_data = {'date': val,
                                     'status': status,
                                     'number_of_days_temp': line_number_of_days,
                                     'is_edit_status': is_edit_status}
                        
                        holiday_line_ids.append((0, 0, line_data))
                    
                    vals.update({'holiday_line_ids': holiday_line_ids})
                    
                    if number_of_days_temp == 0:
                         vals['number_of_days_temp'] = new_number_of_days_temp
                    
                holiday_pool.write(cr, uid, holiday['id'], vals)
                cr.commit()
        
        log.info("Finish Update Leave Request to Next year")   
        return True
    
    def cron_update_data_annual_leave_balance(self, cr, uid, input_years, context=None):
        """
        Make signal to rerun function update function field
        
        ([2016],{"division_id":[13123,13121,14403,14388,13120]})
        
        """
        if not context:
            context = {}
            
        years = [date.today().year]
        if input_years:
            years = input_years
        
        import time
        time1 = time.time()
        log.info("Start run cron Update annual leave balance")
        
        if years:
            employee_domain = [('active','=',True)]
            if context.get('division_id', False):
                employee_domain.append(('division_id','in', context['division_id']))
            elif context.get('department_id', False):
                employee_domain.append(('department_id','in', context['department_id']))
            
            employee_ids = self.pool.get('hr.employee').search(cr, uid, employee_domain)
            log.info("Update annual leave balance for %s employee" % len(employee_ids))
            update_ids = self.search(cr, uid, [('year','in',years),
                                               ('type','=','add'),
                                               ('employee_id','in',employee_ids),
                                               ('state','=','validate')])
             
            if update_ids:
                self.update_to_state_validate(cr, uid, update_ids, 0)
                    
        
        log.info("Finish run cron Update annual leave balance with %s second"% (time.time()-time1))
    
    
    def update_to_state_validate(self, cr, uid, update_ids, count=0, context=None):
        if update_ids and count <7:
            log.info("update_to_state_validate with index = %s"%count )
            count += 1
            len_chunks = len(update_ids)/30
            if len_chunks ==0:
                len_chunks = len(update_ids)
            index = 0
            update_fail_ids = []
            while index <= len(update_ids):
                next_index = index + len_chunks
                chunk_update_ids = update_ids[index:next_index]
                try:
                    log.info("update_to_state_validate =validate from %s"% index )
                    print 'update state=validate from ',
                    self.write(cr, uid, chunk_update_ids, {'state':'validate'})
                except Exception as e:
                    update_fail_ids.extend(chunk_update_ids)
                    log.exception(e)
                    
                index = next_index
            
            if update_fail_ids:
                self.update_to_state_validate(cr, uid, update_fail_ids, count)
                    
        
        return True
        
    
    def cron_update_data_annual_leave_balance_for_update_leave_in_day(self, cr, uid, *args):
        """
        Make signal to rerun function update function field for annual leave of employee have new leave or update leave in days
        """
        length = 0
        if args:
            length = args[0]
        
        import time
        time1 = time.time()
        log.info("Start run cron Update annual leave balance for employee have create/update leave in day")
        
        ot_detail_obj = self.pool.get('vhr.ts.overtime.detail')
        current_year = date.today().year
        date_start = (datetime.now() - relativedelta(days=length)).strftime(DEFAULT_SERVER_DATE_FORMAT)
        date_to = (datetime.now() + relativedelta(days=1)).strftime(DEFAULT_SERVER_DATE_FORMAT)
        holiday_ids = self.search(cr, uid, [('type','=','remove'),
                                            '|', '&',('create_date','>=',date_start),('create_date','<',date_to),
                                                 '&',('write_date','>=',date_start),('write_date','<',date_to)])
        if holiday_ids:
            holidays = self.read(cr, uid, holiday_ids, ['employee_id'])
            employee_ids = [hr.get('employee_id', False) and hr['employee_id'][0] for hr in holidays]
            log.info("Update annual leave balance for %s employee" % len(employee_ids))
            update_ids = self.search(cr, uid, [('year','=',current_year),
                                               ('type','=','add'),
                                               ('employee_id','in',employee_ids),
                                               ('state','=','validate')])
             
            if update_ids:
                self.write(cr, uid, update_ids, {'state':'validate'})
            
            update_ot_ids = ot_detail_obj.search(cr, uid, [('employee_id','in',employee_ids),
                                                  ('state','=','finish'),
                                                  '|', '&',('create_date','>=',date_start),('create_date','<',date_to),
                                                       '&',('write_date','>=',date_start),('write_date','<',date_to)])
            if update_ot_ids:
                ot_detail_obj.write(cr, uid, update_ot_ids, {'state':'finish'})
        
        log.info("Finish run cron Update annual leave balance with %s second"% (time.time()-time1))
    
#     def cron_update_number_of_days_temp_in_leave(self, cr, uid, employee_ids, context=None):
        
            
    def get_leave_history(self, cr, uid, context=None):
        data = []
        if context is None:
            context = {}
        fields_lst = ['date_from', 'date_to', 'create_date', 'employee_code', 'employee_id',
                      'dept_code', 'holiday_status_name', 'state', 'department_id', 'number_of_days_temp']
        year = datetime.now().year
        if uid:
            min_date = '%s-01-01' % year
            max_date = '%s-12-31' % year
            args = [('employee_id.user_id', '=', uid), ('type', '=', 'remove'), ('create_date', '>=', min_date),
                    ('create_date', '<=', max_date), ('state', 'not in', ['draft'])]
            leave_ids = self.search(cr, uid, args, order='date_from desc', context=context)
            for item in self.read(cr, uid, leave_ids, fields_lst, context=context):
                item['department'] = item.get('department_id', False) and item['department_id'][1] or ''
                item['employee_name'] = item.get('employee_id', False) and item['employee_id'][1] or ''
                data.append(item)
        return data

    def get_leave_approval(self, cr, uid, context=None):
        data = []
        if context is None:
            context = {}
        context.update({'leave_approval': True})
        fields_lst = ['date_from', 'date_to', 'create_date', 'employee_code', 'employee_id',
                      'dept_code', 'holiday_status_name', 'state', 'department_id', 'number_of_days_temp']
        if uid:
            leave_ids = self.search(cr, uid, [], order='date_from desc', context=context)
            for item in self.read(cr, uid, leave_ids, fields_lst, context=context):
                item['department'] = item.get('department_id', False) and item['department_id'][1] or ''
                item['employee_name'] = item.get('employee_id', False) and item['employee_id'][1] or ''
                data.append(item)
        return data
    
    
    def is_delegate_from(self, cr, uid, user_id, employee_id, department_id, model = False, context=None):
        """
        Return True if user_id is delegate from employee_id in department_id in module Leave Request - Vhr Timesheet
        """
        if employee_id and user_id and department_id:
            emp_obj = self.pool.get('hr.employee')
            delegate_obj = self.pool.get('vhr.delegate.detail')
            
            emp_ids = emp_obj.search(cr, uid, [('user_id','=',user_id)])
            if emp_ids:
                module_ids = self.pool.get("ir.module.module").search(cr, uid, [('name','=','vhr_timesheet')])
                
                if not model:
                    model = self._name
                
                model_ids = self.pool.get('ir.model').search(cr, uid, [('model','=',model)])
                delegate_model_id = self.pool.get('vhr.delegate.model').search(cr, uid, [('model_id','in',model_ids),
                                                                                         ('active','=',True)])
                
                delegate_ids = delegate_obj.search(cr, uid, [('employee_id','=',employee_id),
                                                             ('department_ids','=',department_id),
                                                             ('delegate_id','in',emp_ids),
                                                             ('module_id','in',module_ids),
                                                             ('model_ids','=',delegate_model_id),
                                                             ('active','=',True)])
                if delegate_ids:
                    return True
        
        return False
    
    def get_delegator(self, cr, uid, record_id, employee_id, model=False, context=None):
        '''
        Check if have record delegate detail with employee 
        Return list delegate_ids of record if have
        '''
        if employee_id and record_id:
            record = self.read(cr, uid, record_id, ['department_id'])
            
            
            department_id = record.get('department_id', False) and record['department_id'][0]
            
            detail_obj = self.pool.get('vhr.delegate.detail')
            
            module_ids = self.pool.get("ir.module.module").search(cr, uid, [('name','=','vhr_timesheet')])
            
            if not model:
                model = self._name
                
            model_ids = self.pool.get('ir.model').search(cr, uid, [('model','=',model)])
            delegate_model_id = self.pool.get('vhr.delegate.model').search(cr, uid, [('model_id','in',model_ids),
                                                                                     ('active','=',True)])
            
            if delegate_model_id and module_ids and department_id:
                domain = [('employee_id','=',employee_id),
                         ('module_id','in',module_ids),
                         ('model_ids','=',delegate_model_id),
                         ('department_ids','=',department_id),
                         ('active','=',True)]
                
                detail_ids = detail_obj.search(cr, uid, domain)
                
                if detail_ids:
                    details = detail_obj.read(cr, uid, detail_ids, ['delegate_id'])
                    delegate_ids = [detail.get('delegate_id', False) and detail['delegate_id'][0] for detail in details]
                    
                    return delegate_ids
        
        return []
    
    def get_emp_make_delegate(self, cr, uid, delegate_id, model=False, context=None):
        '''
        Return dict {employee: dept} make delegate for delegate_id
        '''
        res = {}
        if delegate_id:
#             
            detail_obj = self.pool.get('vhr.delegate.detail')
            
            module_ids = self.pool.get("ir.module.module").search(cr, uid, [('name','=','vhr_timesheet')])
            
            
            if not model:
                model = self._name
            
            model_ids = self.pool.get('ir.model').search(cr, uid, [('model','=',model)])
            delegate_model_id = self.pool.get('vhr.delegate.model').search(cr, uid, [('model_id','in',model_ids),
                                                                                     ('active','=',True)])
            
            if delegate_model_id and module_ids:
                domain = [('delegate_id','=',delegate_id),
                         ('module_id','in',module_ids),
                         ('model_ids','=',delegate_model_id),
                         ('active','=',True)]
                
                detail_ids = detail_obj.search(cr, uid, domain)
                
                if detail_ids:
                    details = detail_obj.read(cr, uid, detail_ids, ['employee_id','department_ids'])
                    
                    for detail in details:
                        employee_id = detail.get('employee_id', False) and detail['employee_id'][0]
                        
                        department_ids = detail.get('department_ids', [])
                    
                        res[employee_id] = department_ids
                    
        return res
    
    def get_param_base_on_job_level(self, cr, uid, param_code, job_level_person_id, context=None):
        res = 0
        param_obj = self.pool.get('vhr.ts.param.job.level')
        if param_code and job_level_person_id:
            param_type_ids = self.pool.get('vhr.ts.param.type').search(cr, uid, [('code','=',param_code)])
            if param_type_ids:
                today = date.today().strftime(DEFAULT_SERVER_DATE_FORMAT)
                param_ids = param_obj.search(cr, uid, [('param_type_id','in',param_type_ids),
                                                       ('job_level_new_id','=',job_level_person_id),
                                                       ('effect_from','<=',today),
                                                      '|',('effect_to','>=',today),
                                                          ('effect_to','=', False)])
                if param_ids:
                    param = param_obj.read(cr, uid, param_ids[0], ['value'])
                    res = param.get('value', 0)
        
        return res
    
    
    def cron_recalculate_annual_leave(self, cr, uid, context=None):
        """
        Tìm và tính lại annual leave trong năm sai với các kiểu sau:
            actual_days_of_pre_year <> days_taken_of_pre_year + remain_days_of_pre_year
            days_of_year <> days_taken_of_year + remain_days_of_year
            total_days <> actual_days_of_pre_year + days_of_year
            total_days <> total_taken_days + total_destroy_days + total_remain_days
            days_of_year <> COALESCE(seniority_leave,0) + number_of_days_temp
        """
        sql = """
                    select id
                    FROM hr_holidays
                    WHERE 
                    
                    type='add' and year=%s
                    and 
                    (
                    (actual_days_of_pre_year <> days_taken_of_pre_year + remain_days_of_pre_year)
                    or (days_of_year <> days_taken_of_year + remain_days_of_year)
                    or (total_days <> actual_days_of_pre_year + days_of_year)
                    or (total_days <> total_taken_days + total_destroy_days + total_remain_days)
                    or ( (days_of_year <> COALESCE(seniority_leave,0) + number_of_days_temp) and holiday_status_id=85)
                    )
              """
#         return True
        if not context:
            context = {}
        year = date.today().year
        
        cr.execute(sql%year)
        leave_ids = [item[0] for item in cr.fetchall()]
        log.info("cron_recaculate_annual_leave::::: There are %s wrong annual leave"% len(leave_ids))
        log.info('You have to run in %s times'%str(len(leave_ids)/20))
        if leave_ids:
            if context.get('filter_with', False):
                leave_ids = leave_ids[:context['filter_with']]
            else:
                leave_ids = leave_ids[:20]
            self.write(cr, uid, leave_ids, {'state':'validate'})
        
        return True
    
    def cron_recalculate_annual_leave_when_wrong_taken_day(self, cr, uid, context=None):
        """
        Tìm và tính lại annual leave trong năm sai do taken_day tính sai
        """
        if not context:
            context = {}
            
        sql ="""
                select leave.id,rr.code,leave.total_taken_days,total_leave.sum
                    FROM hr_holidays leave inner join hr_employee emp on leave.employee_id=emp.id
                                           inner join resource_resource rr on emp.resource_id=rr.id
                                           inner join vhr_working_record wr on wr.employee_id=emp.id
                                           inner join hr_contract ct on wr.contract_id=ct.id
                                           inner join hr_contract_type ctype on ct.type_id=ctype.id
                                           inner join hr_contract_type_group type_group on ctype.contract_type_group_id=type_group.id
                                           inner join 
                                           
                                           (select 

                    cast( sum(number_of_days_temp) as decimal(16,1)) as "sum",employee_id,holiday_status_id 
                                           from hr_holidays 
                                           where 
                                              type='remove' 
                                              and state='validate'
                                              and date_from>='{0}-01-01' 
                                              and date_to<='{0}-12-31'
                                            group by employee_id,holiday_status_id) as total_leave on total_leave.employee_id=leave.employee_id
                                           
                    WHERE 
                    total_leave.holiday_status_id = leave.holiday_status_id
                    and leave.type='add' and leave.year={0}
                    and (leave.total_taken_days - total_leave.sum) not in (0,0.1,-0.1)
                    and wr.active=True
                    {1}
                    
             """
        
        year = date.today().year
        
        where_extend = ''
        if context.get('get_official', False):
            where_extend = ' and type_group.is_offical = True '
            
        sql = sql.format(year,where_extend)
        cr.execute(sql)
        leave_ids = [item[0] for item in cr.fetchall()]
        log.info("cron_recaculate_annual_leave::::: There are %s wrong annual leave"% len(leave_ids))
        log.info('You have to run in %s times'%str(len(leave_ids)/40))
        if leave_ids:
            if context.get('filter_with', False):
                leave_ids = leave_ids[:context['filter_with']]
            else:
                leave_ids = leave_ids[:40]
            self.write(cr, uid, leave_ids, {'state':'validate'})
        
        return True
    
    
    def cron_recalculate_annual_leave_by_id(self, cr, uid, context=None):
        if not context:
            context  ={}
        
        if context.get('ids', False):
            self.write(cr, uid, context['ids'], {'state': 'validate'})
        
        return True
        
                


vhr_holidays()