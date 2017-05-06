# -*- coding: utf-8 -*-

MULTIPLE = 0.5
import logging
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from openerp.osv import osv, fields
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp import SUPERUSER_ID
from openerp.addons.vhr_common.model.vhr_common import vhr_common

log = logging.getLogger(__name__)


class vhr_holidays_status(osv.osv, vhr_common):
    _name = 'hr.holidays.status'
    _inherit = 'hr.holidays.status'
    _description = 'VHR Holiday Status'

    _order = 'sequence, name'

    def get_days_by_param_by_job_level(self, cr, uid, employee_id, company_id=False, code=False, job_level_person_id=False,
                                       effect_from=False, effect_to=False, context=None):
        if not context:
            context = {}
        
        #Nếu lấy thông số loại phép năm theo level, vói các employee thuộc bảng vhr.ts.employee.expat mặc định lấy 20 ngày phép năm
        parameter_obj = self.pool.get('ir.config_parameter')
        stipulated_permit_code = parameter_obj.get_param(cr, uid, 'ts.param.type.stipulated.permit').split(',')
        if employee_id and stipulated_permit_code == code:
            expat_ids = self.pool.get('vhr.ts.employee.expat').search(cr, uid, [('employee_id','=',employee_id),
                                                                                ('active','=', True)])
            if expat_ids:
                
                annual_leave = parameter_obj.get_param(cr, uid, 'vhr_timesheet_annual_leave_of_expat_group') or ''
                try:
                    annual_leave = float(annual_leave)
                except:
                    annual_leave = 0
            
                return annual_leave
            
        code = [str(co) for co in code]
        code = str(tuple(code)).replace(',)', ')')
        sql = """
            SELECT
              coalesce(CAST(PJ.value AS float), 0)
            FROM vhr_ts_param_job_level PJ
              INNER JOIN vhr_ts_param_type PT ON PT.id = PJ.param_type_id
              INNER JOIN hr_employee HE ON HE.job_level_person_id = PJ.job_level_new_id
            WHERE PT.code IN {0} AND PJ.active IS True
        """.format(code)
        if not job_level_person_id:
            sql = '%s %s' % (sql, ' AND HE.id = {0} '.format(employee_id))
        else:
            sql = '%s %s' % (sql, ' AND PJ.job_level_new_id= {0} '.format(job_level_person_id))
        if effect_from and effect_to:
            sql = '%s %s' % (sql,
                             " AND (PJ.effect_to IS null OR PJ.effect_from <= '{0}' AND effect_to >= '{1}') ".format(
                                 effect_to,
                                 effect_from))
        sql = '%s %s' % (sql, ' GROUP BY 1;')

        cr.execute(sql)
        value = cr.fetchone()
        
        if context.get('get_correct_value', False):
            value = value and value[0] or None
        else:
            value = value and value[0] or 0
        return value

    def get_days_depend_on_leave_type(self, cr, uid, ids, employee_id, company_id, date_from, result, context={}):
        """
        max_leaves: phép tối đa được đăng ký
        total_leaves: tổng số phép tới 31/12 = phép tồn còn hiệu lực + phép năm
        total_current_leaves: tổng số phép có tới hiện tại = phép tồn còn hiệu lực + phép năm /12 x tháng hiện tại
        leaves_taken: phép đã finish
        leaves_submitted: phép đã submit
        leaves_expired: phép tồn bị hủy
        remaining_leaves: phép còn lại = total_current_leaves - leaves_submitted
        
        add new:
        1.1 phép tồn đã chuyển: annual balance.actual_days_of_pre_year
        1.2 phép tồn đã hủy:    annual balance.total_destroy_days
        1 phép tồn còn hiệu lực:  1.1 - 1.2
        2 phép năm:  annual balance.days_of_year
        3. phép có đến hiện tại: 1 + 2/12 * month
        4. total_leaves = 1 +2
        5. leaves_submitted
        6. remaining_leaves
        7. max_leaves
        """
        if not context:
            context = {}
            
        parameter_obj = self.pool.get('ir.config_parameter')
        general_param_obj = self.pool.get('vhr.ts.general.param')
        termination_param_obj = self.pool.get('vhr.ts.termination.param')
        join_param_obj = self.pool.get('vhr.ts.new.staff.param')
        contract_obj = self.pool.get('hr.contract')
        leave_obj = self.pool.get('hr.holidays')
                    
        leave_type_in_advance_code = parameter_obj.get_param(cr, uid, 'ts.leave.type.in.advance.code').split(',')
        leave_type_in_overtime_code = parameter_obj.get_param(cr, uid, 'ts.leave.type.overtime.code').split(',')
        leave_type_in_advance_code = [code.strip() for code in leave_type_in_advance_code]
        leave_type_in_overtime_code = [code.strip() for code in leave_type_in_overtime_code]
        for holiday_status in self.browse(cr, uid, ids, fields_process=['code', 'date_type', 'timelines', 'limit'], context=context):
            status_dict = result[holiday_status.id]
            leaves_submitted = status_dict['leaves_submitted']
            #Case nghi phep nam
            if holiday_status.code in leave_type_in_advance_code:
                advance_days_code = parameter_obj.get_param(cr, uid, 'ts.param.type.be.advanced.days.code').split(',')
                value = self.get_days_by_param_by_job_level(cr, uid, employee_id, company_id, code=advance_days_code,
                                                            context=context)
                #Khong tam ung phep nam cho CTV
                is_collaborator,is_probation = leave_obj.is_collaborator_or_probation(cr, uid, employee_id=employee_id, company_id=False, context=context)
                if is_collaborator:
                    value = 0
                
                current_date = date.today().day
                current_month = date.today().month
                    
                if date_from:
                    dfrom = datetime.strptime(date_from, DEFAULT_SERVER_DATE_FORMAT)
                    #If register for previous year, pretend that today is last day of last year
                    if dfrom.year < date.today().year:
                        current_date = 31
                        current_month = 12
                        
                total_month_work_in_year = 12
                month_worked_in_year = current_month
                
                if context.get('check_on_date', False):
                    check_date = datetime.strptime(context['check_on_date'], DEFAULT_SERVER_DATE_FORMAT)
                    current_date = check_date.day
                    current_month = check_date.month
                    month_worked_in_year = current_month
                
                #Check if employee is offer or dont have any active contract ==> dont add value into max_leaves
                if employee_id:
                    today = date.today()
                    active_contract_ids = contract_obj.search(cr, uid, [('employee_id','=',employee_id),
                                                                        ('state','=','signed'),
                                                                        ('date_start','<=',today),
                                                                         '|','|', '&',('date_end','=',False),('liquidation_date','=',False),
                                                                                  '&',('date_end','>=',today),('liquidation_date','=',False),
                                                                                      ('liquidation_date','>=',today),
                                                                                   ], order='is_main desc')
                    if active_contract_ids:
                        parameter_obj = self.pool.get('ir.config_parameter')
                        offer_contract_code = parameter_obj.get_param(cr, uid, 'vhr_human_resource_probation_contract_type_group_code') or ''
                        offer_contract_code = offer_contract_code.split(',')
            
                        contract = contract_obj.browse(cr, SUPERUSER_ID, active_contract_ids[0])
                        contract_type_group_code = contract.type_id and contract.type_id.contract_type_group_id and contract.type_id.contract_type_group_id.code or ''
                        
                        if contract_type_group_code in offer_contract_code:
                            value = 0
                    else:
                        value = 0
                
                #Get join date of employee to get total_month_employee have been working in this year
                employee = self.pool.get('hr.employee').read(cr, uid, employee_id, ['join_date','end_date'])
                join_date = employee.get('join_date',False)
                end_date = employee.get('end_date',False)
                if join_date:
                    join_date = datetime.strptime(join_date, DEFAULT_SERVER_DATE_FORMAT)
                    if join_date.year == date.today().year:
                        month_worked_in_year = current_month - join_date.month #Dont count join month, join month will be check later
                        total_month_work_in_year = 12 - join_date.month + 1
                        date_join_company = join_date.day
                        
                        #If join before 16, count month employee join company
                        #If join at 16 or after 16, dont count month employee join company
                        general_param_ids = general_param_obj.search(cr, uid, [('active','=',True)])
                        if general_param_ids:
                            general_param = general_param_obj.read(cr, uid, general_param_ids[0],['new_staff_param_ids'])
                            join_param_ids = general_param.get('new_staff_param_ids',[])
                            join_ids = join_param_obj.search(cr, uid, [('id','in',join_param_ids),
                                                                      ('from_date','<=',date_join_company),
                                                                      ('to_date','>=',date_join_company)])
                            if join_ids:
                                join = join_param_obj.read(cr, uid, join_ids[0], ['coef'])
                                coef = join.get('coef',0) or 0
                                
                                month_worked_in_year += coef
                
                #Nếu ngày hiện tại >= 15 thì tính ngay phép cho tháng hiện tại
                #Ngược lại, nếu ngày hiện tại < 15 thì tính 0 ngày phép cho tháng hiện tại
                dayline_to_add_leave_in_month = parameter_obj.get_param(cr, uid, 'dayline_to_add_leave_in_month') or ''
                dayline_to_add_leave_in_month = dayline_to_add_leave_in_month.split(',')
                try:
                    dayline_to_add_leave_in_month = int(dayline_to_add_leave_in_month[0])
                except Exception as e:
                    log.exception(e)
                    raise osv.except_osv('Validation Error !', 'Can not convert value to integer from ir_config_parameter with key "dayline_to_add_leave_in_month" !')
                 
                if current_date < dayline_to_add_leave_in_month:
                    month_worked_in_year -= 1
                
                
                if end_date and current_date >= dayline_to_add_leave_in_month:
                    #Only check if end_date.month == current_month and employee have leave on that month
                    #Get coef termination from General Parameter
                    #Current rule at 3/2015, if terminate before day 15 of month, dont allow leave of that month
                    coef_termination = 0
                    end_date = datetime.strptime(end_date, DEFAULT_SERVER_DATE_FORMAT)
                    date_of_end_date = end_date.day
                    month_of_end_date = end_date.month
                    
                    if month_of_end_date == current_month:
                        general_param_ids = general_param_obj.search(cr, uid, [('active','=',True)])
                        if general_param_ids:
                            general_param = general_param_obj.read(cr, uid, general_param_ids[0],['termination_param_ids'])
                            termination_param_ids = general_param.get('termination_param_ids',[])
                            termination_ids = termination_param_obj.search(cr, uid, [('id','in',termination_param_ids),
                                                                                                         ('from_date','<=',date_of_end_date),
                                                                                                         ('to_date','>=',date_of_end_date)])
                            if termination_ids:
                                termination = termination_param_obj.read(cr, uid, termination_ids[0], ['coef'])
                                coef = termination.get('coef',0) or 0
                                coef_termination = 1- coef
                        
                                month_worked_in_year -= coef_termination
                     
                #So ngay phep duoc tinh bang so phep cua cac thang + so phep tinh toi thoi diem trong thang
#                 temp_month_leave_allow = current_month - 1 + percentage_leave_receive_this_month
                
                #Force to prevent case month_worked_in_year < 0
                if month_worked_in_year < 0:
                    month_worked_in_year = 0
                    
                value = min(value, total_month_work_in_year - month_worked_in_year)
                days_of_year = status_dict['days_of_year']
                #Lấy tổng số ngày có thể nghỉ phép của nhân viên từ đầu năm tới nay(ko tính số ngày đã nghỉ phép)
                days_of_year = (round(  float(days_of_year)/total_month_work_in_year * month_worked_in_year * 2     )) /2 + status_dict['remain_days_of_pre_year']
                
                remaining_leaves = status_dict['remaining_leaves']
#                 log.info('remaining_leaves %s' % remaining_leaves)
                status_dict['max_leaves'] = min(
                    days_of_year + value - leaves_submitted + status_dict['days_taken_of_pre_year'],
                    remaining_leaves)
                
                status_dict['current_remain_leave'] = min( days_of_year - leaves_submitted + status_dict['days_taken_of_pre_year'], 
                                                           remaining_leaves)
#                 log.info('max_leaves %s' % status_dict['max_leaves'])
                status_dict['total_current_leaves'] = (round(  float(status_dict['days_of_year'])/total_month_work_in_year * month_worked_in_year * 2     )) /2 + status_dict['remain_accum_leave']
                
                status_dict['advance_leaves'] = value
#                 log.info('end status_dict %s' % status_dict)
            elif holiday_status.code in leave_type_in_overtime_code:
                status_dict['max_leaves'] = status_dict['remaining_leaves']
            else:
                n_days = holiday_status.timelines
                if date_from:
                    dfrom = datetime.strptime(date_from, DEFAULT_SERVER_DATE_FORMAT)
                    if holiday_status.date_type == 'month':
                        date_from_new = dfrom + relativedelta(months=int(n_days))
                        n_days = (date_from_new - dfrom).days
                    elif holiday_status.date_type == 'year':
                        date_from_new = dfrom + relativedelta(year=int(n_days))
                        n_days = (date_from_new - dfrom).days
                    # no limit in this leave type
                    if holiday_status.limit:
                        status_dict['remaining_leaves'] = 0
                        status_dict['virtual_remaining_leaves'] = 0
                        status_dict['max_leaves'] = 0
                        status_dict['total_leaves'] = n_days
                        status_dict['total_current_leaves'] = n_days
                        continue
                if not holiday_status.limit or holiday_status.date_type == 'day':
                    status_dict['remaining_leaves'] = n_days - leaves_submitted
                    status_dict['virtual_remaining_leaves'] = n_days - leaves_submitted
                    status_dict['max_leaves'] = status_dict['remaining_leaves']
                    status_dict['total_leaves'] = n_days
                    status_dict['total_current_leaves'] = n_days
        return result

    def get_days(self, cr, uid, ids, employee_id, company_id=False, date_from=False, context=None):
        if context is None:
            context = {}
        current_year = date.today().year
        leave_obj = self.pool.get('hr.holidays')
        leave_type_group_obj = self.pool.get('hr.holidays.status.group')
        parameter_obj = self.pool.get('ir.config_parameter')
        
        #Check nếu trừ số phép bằng số ca nghỉ hay không (không dựa vào số ngày công của ca nghỉ)
#         is_by_day_of_leave = True
#         leave_group_follow_rule_workday = parameter_obj.get_param(cr, uid, 'vhr_timesheet_leave_type_code_follow_rule_workday') or ''
#         leave_group_follow_rule_workday = special_holiday_status_code.split(',')
#         leave_group_follow_rule_workday_ids = leave_type_group_obj.search(cr, uid, [('code','in',leave_group_follow_rule_workday)])
#         leave_follow_rule_workday_ids = self.search(cr, uid, [('holiday_status_group_id','in',leave_group_follow_rule_workday_ids)])
#         if set(ids).intersection(set(leave_follow_rule_workday_ids)):
#             is_by_day_of_leave = False
            
        # indicate year of leave request base on date_from
        if date_from:
            current_year = datetime.strptime(date_from, DEFAULT_SERVER_DATE_FORMAT).year
            
        result = dict(
            (res_id, dict(leaves_expired=0, max_leaves=0, leaves_taken=0, leaves_submitted=0, remaining_leaves=0,
                          total_leaves=0, expiry_date_of_days_pre_year=False, remain_days_of_pre_year=0,
                          days_of_year=0, days_taken_of_pre_year=0,remain_accum_leave=0,moved_accum_leave=0,
                          total_current_leaves=0, virtual_remaining_leaves=0, advance_leaves=0,annual_leaves_in_year=0,
                          annual_leaves_in_year_by_level=0, annual_leaves_in_year_by_seniority=0,
                          )) for res_id in ids)
        
        
        
        
        year_last_day = '%s-12-31' % current_year
        year_first_day = '%s-01-01' % current_year
        
        is_restrict = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_timesheet_restrict_start_day_in_get_day_leave_status') or ''
        if not is_restrict:
            context['first_date_of_year_ins'] = year_first_day
            date_start_ins = leave_obj.get_date_start_of_earliest_active_employee_instance(cr, uid, employee_id, context)
            if date_start_ins and self.compare_day(year_first_day, date_start_ins) >0:
                year_first_day = date_start_ins
            
        new_context = context.copy()
        new_context['get_all'] = 1
        
        #If is_check_remain_day_on_current_registration = False, check taken day in year
        #else: check taken day by current check holiday
        leave_type_ids = self.search(cr, uid, [('id','in', ids),
                                               ('is_check_remain_day_on_current_registration','=',False),
                                               ('is_check_remain_day_on_current_registration_local','=', False)
                                                   ])
        
        if leave_type_ids:
            holiday_ids = leave_obj.search(cr, SUPERUSER_ID, [
                                                                ('holiday_status_id', 'in', leave_type_ids),
                                                                ('state', 'in', ['draft', 'confirm', 'validate1', 'validate']),
                                                                ('employee_id', '=', employee_id),
                                                                '|', '&', ('type', '=', 'add'),
                                                                          ('year', '=', current_year),
                                                                    '&', '&', '&', '&',
                                                                    ('type', '=', 'remove'),
                                                                    ('date_from', '>=', year_first_day),
                                                                    ('date_from', '<=', year_last_day),
                                                                    ('date_to', '>=', year_first_day),
                                                                    ('date_to', '<=', year_last_day),
                                                                # ('company_id', '=', company_id),
                                                            ], context=new_context)
        else:
            holiday_ids = context.get('current_check_holiday_ids',[])
            
#         context['do_not_validate_read_holiday'] = 1
        cols = ['holiday_status_id', 'type', 'state', 'total_remain_days','seniority_leave',
                  'number_of_days', 'total_days','remain_days_of_pre_year','number_of_hours',
                  'total_taken_days', 'total_destroy_days', 'actual_days_of_pre_year','number_of_days_temp',
                  'days_of_year', 'expiry_date_of_days_pre_year','days_taken_of_pre_year', 'remain_days_of_year',
                  ]
#         if is_by_day_of_leave:
#             cols.append('holiday_line_ids')
            
        for holiday in leave_obj.read(cr, SUPERUSER_ID, holiday_ids, cols , context=context):
            if holiday.get('holiday_status_id'):
                status_dict = result[holiday.get('holiday_status_id')[0]]
#                 holiday_type = 
                state = holiday.get('state')
                if holiday.get('type') == 'add':
                    status_dict['virtual_remaining_leaves'] += holiday.get('total_remain_days',0) + holiday.get('total_taken_days',0)
                    if state == 'validate':
                        status_dict['moved_accum_leave'] = holiday.get('actual_days_of_pre_year', 0)
                        status_dict['total_destroy_days'] = holiday.get('total_destroy_days', 0)
                        status_dict['days_of_year'] = holiday.get('days_of_year', 0)
                        status_dict['days_taken_of_pre_year'] = holiday.get('days_taken_of_pre_year', 0)
                        
                        status_dict['remaining_leaves'] += holiday.get('total_remain_days', 0)
                        status_dict['max_leaves'] += holiday.get('total_remain_days', 0)
                        status_dict['expiry_date_of_days_pre_year'] = holiday.get('expiry_date_of_days_pre_year', False)
                        if holiday.get('expiry_date_of_days_pre_year', False):
                            #Get correct remain_days on date_from
                            if date_from and self.compare_day(date_from,holiday['expiry_date_of_days_pre_year']) >= 0:
                                status_dict['remain_days_of_pre_year'] += holiday.get('remain_days_of_pre_year', 0)
                            elif date_from and self.compare_day(holiday['expiry_date_of_days_pre_year'], date_from) > 0:
                                status_dict['leaves_expired'] = holiday.get('remain_days_of_pre_year', 0)
                                #Incase over expire day, annual leave not yet update destroy date
                                if not holiday.get('total_destroy_days',0) and holiday.get('remain_days_of_pre_year', 0) != 0:
                                    status_dict['remaining_leaves'] -= holiday.get('remain_days_of_pre_year', 0)
                        
                        status_dict['remain_accum_leave'] = status_dict['moved_accum_leave'] - status_dict.get('leaves_expired',0)
                        status_dict['annual_leaves_in_year'] = holiday.get('days_of_year', 0)
                        status_dict['annual_leaves_in_year_by_level'] = holiday.get('number_of_days_temp', 0)
                        status_dict['annual_leaves_in_year_by_seniority'] = holiday.get('seniority_leave', 0)
                        status_dict['total_leaves'] += status_dict['remain_accum_leave'] + status_dict['annual_leaves_in_year']
                        
                elif holiday.get('type') == 'remove':  # number of days is negative
#                     if is_by_day_of_leave:
#                         #Nếu leave type thuộc các loại nghỉ bảo hiểm thì trừ số ngày phép dựa vào số ca nghỉ chứ không trừ số ngày công của ca nghi
#                         holiday['number_of_days'] = len(holiday.get('holiday_line_ids',[]))
                    
                    if state not in ['cancel', 'refuse']:
#                         if holiday.get('number_of_hours',0):
#                             status_dict['virtual_remaining_leaves'] -= holiday.get('number_of_hours')/ 8.0
#                             status_dict['leaves_submitted'] += holiday.get('number_of_hours')/ 8.0
#                         else:    
                        status_dict['virtual_remaining_leaves'] += holiday.get('number_of_days')
                        status_dict['leaves_submitted'] -= holiday.get('number_of_days')
                    if state == 'validate':
#                         if holiday.get('number_of_hours',0):
#                             status_dict['leaves_taken'] += holiday.get('number_of_hours') / 8.0
#                         else:
                        status_dict['leaves_taken'] -= holiday.get('number_of_days', 0) 
                    if state in ['draft', 'confirm']:
#                         if holiday.get('number_of_hours',0):
#                             status_dict['remaining_leaves'] -= holiday.get('number_of_hours') / 8.0
#                         else:
                        status_dict['remaining_leaves'] += holiday.get('number_of_days', 0) 
                
        for record_id in result:
            data = result[record_id]
            for key in data:
                if isinstance(data[key], float):
                    data[key] = float("{0:.1f}".format(data[key]))
        result = self.get_days_depend_on_leave_type(cr, uid, ids, employee_id, company_id, date_from, result, context)
        return result

    def _user_left_days(self, cr, uid, ids, name, args, context=None):
        employee_id = False
        company_id = False
        date_from = False
        if context is None:
            context = {}
        context['active_test'] = False
        if 'date_from' in context:
            date_from = context['date_from']
        if 'company_id' in context:
            company_id = context['company_id']

        if 'employee_id' in context:
            employee_id = context['employee_id']
        else:
            employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', uid)], context=context)
            if employee_ids:
                employee_id = employee_ids[0]
        if employee_id:
            # and company_id:
            res = self.get_days(cr, uid, ids, employee_id, company_id, date_from=date_from, context=context)
            # if 'is_advanced' in res:
            # del res['is_advanced']
        else:
            res = dict.fromkeys(ids, {'leaves_taken': 0, 'remaining_leaves': 0, 'max_leaves': 0, 'total_leaves': 0})
        return res

    _columns = {
        'code': fields.char('Code', size=64),
        'holiday_status_group_id': fields.many2one('vhr.holidays.status.group', 'Group', ondelete='restrict'),
        'name': fields.char('Vietnamese Name', size=128),
        'name_en': fields.char('English Name', size=128),
        'company_id': fields.many2one('res.company', 'Company'),
        'description': fields.text('Description'),
        'timelines': fields.float('Timelines', digits=(3, 1)),
        'date_type': fields.selection([('day', 'Day'), ('month', 'Month'), ('year', 'Year')], 'Type'),
        'coefsal': fields.float('Salary Coef', digits=(3, 2)),
        'coefsi': fields.float('Insurance Coef', digits=(3, 2)),
        'insurance_day': fields.float('Insurance Days', digits=(3, 1)),
        'is_seniority': fields.boolean('Seniority?'),
        'is_collaborator': fields.boolean('Is Collaborator?'),
        'is_import': fields.boolean('Can Import?'),
        'is_require_paperwork': fields.boolean('Is required paperwork?'),
        'check_to_date_insurance': fields.boolean('Check To Date(Insurance)?'),
        'sequence': fields.integer('Sequence'),
        'total_leaves': fields.function(_user_left_days, string='Total Allowed',
                                        multi='user_left_days'),
        'total_current_leaves': fields.function(_user_left_days, string='Total Current Allowed',
                                                multi='user_left_days'),
        'max_leaves': fields.function(_user_left_days, string='Maximum Allowed',
                                      multi='user_left_days'),
        'leaves_taken': fields.function(_user_left_days, string='Leaves Already Taken',
                                        multi='user_left_days'),
        'remaining_leaves': fields.function(_user_left_days, string='Remaining Leaves',
                                            help='Maximum Leaves Allowed - Leaves Already Taken',
                                            multi='user_left_days'),
        'virtual_remaining_leaves': fields.function(_user_left_days, string='Virtual Remaining Leaves',
                                                    help='Maximum Leaves Allowed - Leaves Already Taken - Leaves Waiting Approval',
                                                    multi='user_left_days'),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                         domain=[('object_id.model', '=', _name),
                                                 ('field_id.name', 'not in', ['write_date', 'audit_log_ids'])]),
        
        'is_allow_to_register_from_now_to_next_year': fields.related('holiday_status_group_id', 'is_allow_to_register_from_now_to_next_year', type='boolean',
                                                  string='Is Allow To Register From Now To Next Year ?'),
        'is_check_remain_day_on_current_registration': fields.related('holiday_status_group_id', 'is_check_remain_day_on_current_registration', type='boolean',
                                                                string='Is Only Check Remain days by current registration ?'),   
        #Bỏi vì trong 1 số group, có 1 số lọại phép có chọn 1 số ko chọn nên tạo thêm field nữa
        #trong view nếu field trên ko có thì hiện field dưới, để c&B có thể edit
        #Buồn -_-
        'is_check_remain_day_on_current_registration_local': fields.boolean('Is Only Check Remain days by current registration ?'),
         'is_date_range_include_rest_date': fields.boolean('Is Date Range Include Rest Date ?'),
         'is_require_children': fields.boolean('Is Required To Have Children ?'),
    }

    def _get_default_company_id(self, cr, uid, context=None):
        company_ids = self.pool.get('res.company').search(cr, uid, [('is_member', '=', False)], order="id asc")
        if company_ids:
            return company_ids[0]

    _defaults = {
        'date_type': 'day',
        'company_id': _get_default_company_id,
        'coefsal': 0.00,
        'coefsi': 0.00,
        'insurance_day': 0.0,
    }

    _unique_insensitive_constraints = [{'code': "Leave Type's Code is already exist!"},
                                       {'name': "Leave Type's Vietnamese Name is already exist!"}]

    @staticmethod
    def _validation_multiple(vals, multiple, field_name):
        if vals < 0 or vals % multiple > 0:
            raise osv.except_osv(_('Warning!'),
                                 _(" %s must be greater than or equal to 0 and is multiple of %s !" % (
                                     field_name, multiple)))

    @staticmethod
    def _validation_in_range(vals, field_name, start, end):
        if vals < start or vals > end:
            raise osv.except_osv(_('Warning!'),
                                 _(" %s must be in >= %s and <= %s" % (field_name, start, end)))

    def validation_vals(self, vals):
        if vals.get('timelines'):
            self._validation_multiple(vals.get('timelines'), MULTIPLE, 'Timelines')
            if vals.get('timelines') >= 1000:
                raise osv.except_osv(_('Warning!'),
                                     _("Timelines must be lower 1000!"))
        if vals.get('insurance_day'):
            self._validation_multiple(vals.get('timelines'), MULTIPLE, 'Timelines')
            if vals.get('insurance_day') >= 1000:
                raise osv.except_osv(_('Warning!'),
                                     _("Insurance Coef must be lower 1000!"))
        if vals.get('coefsal'):
            self._validation_in_range(vals.get('coefsal'), 'Salary Coef', 0, 1)
        if vals.get('coefsi'):
            self._validation_in_range(vals.get('coefsal'), 'Insurance Coef', 0, 1)

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        args_new = ['|', '|', ('name', operator, name), ('code', operator, name), ('name_en', operator, name)] + args

        if context.get('is_import', False):
            args_new.append(('is_import', '=', context['is_import']))

        ids = self.search(cr, uid, args_new)
        return self.name_get(cr, uid, ids, context=context)

    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        elif 'employee_id' in context:
            del context['employee_id']
        return super(vhr_holidays_status, self).name_get(cr, uid, ids, context=context)

    def create(self, cr, uid, vals, context=None):
        self.validation_vals(vals)

        return super(vhr_holidays_status, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        self.validation_vals(vals)
        return super(vhr_holidays_status, self).write(cr, uid, ids, vals, context=context)

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        try:
            return super(vhr_holidays_status, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')


vhr_holidays_status()