# -*- coding: utf-8 -*-
import logging
import math
import time

from openerp.osv import osv, fields
from openerp.addons.vhr_common.model.vhr_common import vhr_common
from datetime import datetime
from vhr_ts_overtime import STATES as STATES
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT,DEFAULT_SERVER_DATETIME_FORMAT
from openerp import SUPERUSER_ID
from dateutil.relativedelta import relativedelta
from openerp.tools.translate import _

log = logging.getLogger(__name__)


class vhr_ts_overtime_detail(osv.osv, vhr_common):
    _name = 'vhr.ts.overtime.detail'
    
    def _get_state(self, cr, uid, context):
        return STATES
    
    def _get_is_cb_timesheet(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        groups = self.pool.get('res.users').get_groups(cr, uid)
        is_cb_timesheet = 'vhr_cb_timesheet' in groups
        for record_id in ids:
            res[record_id] = is_cb_timesheet
        
        return res
    
    def _get_correct_data(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if not isinstance(ids, list):
            ids = [ids]
        
        records = self.read(cr, uid, ids, ['date_off','notes'])
        for record in records:
            res[record['id']] =  {'correct_date_off':'','fit_notes':''}
            if record.get('date_off'):
                date_approve = datetime.strptime(record['date_off'], DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y")
                res[record['id']]['correct_date_off'] = date_approve
            if record.get('notes',''):
                notes = record.get('notes','')
                res_notes = notes[:20]
                if len(notes) > 20:
                    res_notes += '...'
                res[record['id']]['fit_notes'] = res_notes
                
        return res
    
    def _get_correct_time(self, cr, uid, ids, fields_name, arg, context=None):
        res = {}
        if not isinstance(ids, list):
            ids = [ids]
        
        for record in self.read(cr, uid, ids, ['start_time', 'end_time','total_hours_register']):
            correct_start_time = self.convert_from_float_to_float_time(record.get('start_time',''), context)
            correct_end_time = self.convert_from_float_to_float_time(record.get('end_time',''), context)
            correct_total_hours_register = self.convert_from_float_to_float_time(record.get('total_hours_register',''), context)
            
            res[record['id']] =  {'correct_start_time':           correct_start_time,
                                  'correct_end_time'  :           correct_end_time , 
                                  'correct_total_hours_register': correct_total_hours_register}
            
        return res

    _columns = {
                'employee_id': fields.many2one('hr.employee', 'Employee', ondelete='restrict'),
                'company_id': fields.many2one('res.company', 'Company', ondelete='restrict'),
                'date_off': fields.date('Date OT'),
                'approve_date': fields.datetime('Approve Date'),
                'start_time': fields.float('Start Time (hh:mm)'),
                'end_time': fields.float('End Time (hh:mm)'),
                'break_time': fields.float('Break Time (min)'),
                'total_hours_register': fields.float('Total Hours Register'),
                'is_compensation_leave': fields.boolean('Compensation Leave'),
                'is_compensation_leave_by_default': fields.boolean('Compensation Leave By Default'),#Get from job level, this field is invisible
                'total_ot_day_register': fields.float('OT Days Register (hh:mm)'),
                'total_ot_night_register': fields.float('OT Nights Register (hh:mm)'),
                
                'total_ot_day_approve': fields.float('OT Days Approve (hh:mm)'),
                'total_ot_night_approve': fields.float('OT Nights Approve (hh:mm)'),
                'total_hours_approve': fields.float('Total Hours Approve (hh:mm)'),
                'notes': fields.text('Reason For OT'),
                'overtime_id': fields.many2one('vhr.ts.overtime', 'Overtime', ondelete='cascade'),
                'overtime_sum_id': fields.many2one('vhr.ts.overtime.summarize', 'Overtime Summarize', ondelete='cascade'),
                'state': fields.selection(_get_state, 'Status', readonly=True),
                'request_date': fields.date('Request Date'),
                
                'day_coef':fields.float('OT Day Coef', digits=(2, 2)),
                'night_coef':fields.float('OT Night Coef', digits=(2, 2)),
                'allowance_night_coef':fields.float('OT Allowance Night Coef', digits=(2, 2)),
                
                'day_coef_compensation':fields.float('OT Day Coef Compensation leave', digits=(2, 2)),
                'night_coef_compensation':fields.float('OT Night Coef Compensation leave', digits=(2, 2)),
                'allowance_night_coef_compensation':fields.float('OT Allowance Night Coef Compensation leave', digits=(2, 2)),
                
                'overtime_multi_id': fields.many2one('vhr.ts.overtime.multi', 'Overtime', ondelete='cascade'),
                'correct_date_off': fields.function(_get_correct_data, type='date', string='Correct Date',multi="get_data_for_mail"),
                'fit_notes': fields.function(_get_correct_data, type='text', string='Fit Notes',multi="get_data_for_mail"),
                'is_cb_timesheet': fields.function(_get_is_cb_timesheet, type='boolean', string="Is CB Timesheet"),
                
                'correct_start_time': fields.function(_get_correct_time, type='char', string="Get Correct Start Time", multi='get_time'),
                'correct_end_time':   fields.function(_get_correct_time, type='char', string="Get Correct End Time", multi='get_time'),
                'correct_total_hours_register': fields.function(_get_correct_time, type='char', string="Get Correct Total Hours Register", multi='get_time'),
    }
    
    _order = "date_off asc"
    
    def get_is_cb_timesheet(self, cr, uid, context=None):
        groups = self.pool.get('res.users').get_groups(cr, uid)
        return 'vhr_cb_timesheet' in groups
        
    _defaults = {
                 'state': 'draft',
                 'is_compensation_leave': False,
                 'total_ot_day_register': 0, 'total_ot_night_register': 0,
                 'total_ot_day_approve': 0, 'total_ot_night_approve': 0,
                 'day_coef': 0, 'night_coef': 0, 'allowance_night_coef': 0,
                 'day_coef_compensation': 0, 'night_coef_compensation': 0,
                 'allowance_night_coef_compensation': 0,
                 'is_cb_timesheet': get_is_cb_timesheet
    }
    
    def get_total_hours(self, cr, uid, start_time, end_time, break_time, context=None):
        total = 0
        if not start_time: start_time = 0
        if end_time:
            total = end_time - start_time
            if break_time:
                total -= float(break_time) / 60
        
        return total
    
    def onchange_emp_comp(self, cr, uid, ids, employee_id, context=None):
        res = {}
#         if employee_id:
#             is_compensation_leave = self.is_compensation_leave(cr, uid, employee_id, context)
#             res['is_compensation_leave'] = is_compensation_leave
        
        return {'value': res}
    
    def onchange_date(self, cr, uid, ids, employee_id, date, context=None):
        res = {}
        warning = {}
        if employee_id and date:
            employee = self.pool.get('hr.employee').read(cr, uid, employee_id, ['name','code'])
            employee_name = employee.get('name','') + ' - ' + employee.get('code','')
            date_str = datetime.strptime(date,DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y")
            
            ts_emp_ids, timesheet_id, timesheet_name, timesheet_detail_ids = self.get_timesheet_detail_of_employee_on_date(cr, uid, employee_id, date, context)
            if ts_emp_ids:
                if not timesheet_detail_ids:
                    res['date_off'] = False
                    warning = {
                            'title': _('Error!'),
                            'message' :_("Timesheet %s of employee %s on %s doesn't belong to any period. Please check again!")% (timesheet_name, employee_name, date_str)
                             }
#                 else:
                    #Check if timesheet_detail_ids is old, raise warning
#                     ts_detail = self.pool.get('vhr.ts.timesheet.detail').read(cr, uid, timesheet_detail_ids[0], ['to_date'])
#                     to_date = ts_detail.get('to_date', False)
#                     if to_date:
#                         to_date = datetime.strptime(to_date,DEFAULT_SERVER_DATE_FORMAT).date()
#                         today = datetime.today().date()
#                         if today > to_date:
#                             res['date_off'] = False
#                             warning = {
#                                     'title': 'Error!',
#                                     'message' :'Can not choose date (%s) in old timesheet detail' % date_str
#                                      }
            else:
                res['date_off'] = False
                warning = {
                            'title': _('Error!'),
                            'message' :_("Employee %s doesn't belong to any timesheet on %s. Please check again!")% (employee_name, date_str)
                             }
        
        return {'value': res, 'warning':warning}
    
    def get_timesheet_detail_of_employee_on_date(self, cr, uid, employee_id, date, context=None):
        ts_emp_ids = False
        timesheet_id = False
        timesheet_name = ''
        timesheet_detail_ids = False
        if employee_id and date:
            ts_emp_pool = self.pool.get('vhr.ts.emp.timesheet')
            #Get employee timesheet  cua nhan vien hop le tai date
            ts_emp_ids = ts_emp_pool.search(cr, uid, [('employee_id','=',employee_id),
#                                                                                ('company_id','=',company_id),
                                                                               '|',('active','=', True),
                                                                                   ('active','=', False),
                                                                                ('effect_from','<=',date),
                                                                                '|',('effect_to','=',False),
                                                                                    ('effect_to','>=',date)
                                                                               ])
            if ts_emp_ids:
                ts_emp = ts_emp_pool.read(cr, uid, ts_emp_ids[0], ['timesheet_id'])
                timesheet_id = ts_emp.get('timesheet_id', False) and ts_emp['timesheet_id'][0]
                timesheet = self.pool.get('vhr.ts.timesheet').read(cr, uid, timesheet_id, ['name'])
                timesheet_name = timesheet.get('name','')
                timesheet_detail_ids = self.pool.get('vhr.ts.timesheet.detail').search(cr, uid, [('timesheet_id','=',timesheet_id),
                                                                                                  ('from_date','<=',date),
                                                                                                  ('to_date','>=',date)])
        
        return ts_emp_ids, timesheet_id, timesheet_name, timesheet_detail_ids

            
    def onchange_start_end_time(self, cr, uid, ids, start_time, end_time, break_time, context=None):
        if not context:
            context = {}
            
        res = {}
        warning = {}
        if not end_time:
            end_time = 0
            break_time = 0
            res['break_time'] = 0
            res['total_hours_register'] = 0
        if not break_time:
            break_time = 0            
        if end_time:            
            if end_time <= start_time:
                warning = {
                            'title': _('Error!'),
                            'message' :_('End Time must be greater than Start Time!')
                             }
                end_time = 0
                res['end_time'] = 0                
            elif end_time-start_time-float(break_time)/60 <= 0:
                warning = {
                            'title': _('Error!'),
                            'message' :_('Break Time must be lower Total OT Hours!')
                             }
                break_time = 0
                res['break_time'] = 0
            
            elif end_time - 8 >= start_time and not break_time and not context.get('is_change_break_time', False):
                res['break_time'] = 60
                break_time = 60
            
            
            total_hours = self.get_total_hours(cr, uid, start_time, end_time, break_time, context)
            res['total_hours_register'] = total_hours
        
        return {'value': res, 'warning': warning}
    
    def onchange_ot_time(self, cr, uid, ids, ot_day_regis, ot_night_regis, ot_day_app, ot_night_app, context=None):
        res = {}
        warning = {}
        if not ot_night_regis: ot_night_regis = 0
        if not ot_night_app: ot_night_app = 0
        if not ot_night_app: ot_night_app = 0
        if not ot_day_regis: ot_day_regis = 0
        if not ot_night_regis: ot_night_regis = 0
        
        total_approve = 0
        if ot_day_app:
            if ot_day_app < 0 or ot_day_app > ot_day_regis:
                 res['total_ot_day_approve'] = ot_day_regis
                 warning = {
                            'title': _('Error!'),
                            'message' :_('OT Days approve can not lower 0 and greater OT Days register: %s !') % ot_day_regis
                             }
            total_approve += ot_day_app
        
        if ot_night_app:
            if ot_night_app < 0 or ot_night_app > ot_night_regis:
                 res['total_ot_night_approve'] = ot_night_regis
                 warning = {
                            'title': _('Error!'),
                            'message' :_('OT Nights approve can not lower 0 and greater OT Nights register: %s !') % ot_night_regis
                             }
            total_approve += ot_night_app
        
        res['total_hours_approve'] = total_approve
        
        return {'value': res, 'warning': warning}
            
    def convert_from_float_to_float_time(self, number, context=None):
        result = ''
        if number:
            floor_number = int(math.floor(number))
            result += str(floor_number)
            gap = number - floor_number
            if gap > 0:
                minute = int(round(gap * 60))
                if minute < 10:
                    minute = '0' + str(minute)
                else:
                    minute = str(minute)
                result += ':' + minute
            else:
                result += ':00'

        return result
    
    def get_working_schedule_and_shift_of_employee(self, cr, uid, employee_id, date, context=None):
        shift_id = False
        working_schedule_id = False
        if employee_id and date:
            #Search in Working Schedule Employee to get active Working schedule
            ts_ws_ids = self.pool.get('vhr.ts.ws.employee').search(cr, uid, [('employee_id','=',employee_id),
#                                                                              ('company_id','=',company_id),
                                                                             '|',('active','=', True),
                                                                                 ('active','=', False),
                                                                                 ('effect_from','<=',date),
                                                                            '|',('effect_to','=',False),
                                                                                ('effect_to','>=',date)])
            
            if ts_ws_ids:
                ts_ws = self.pool.get('vhr.ts.ws.employee').read(cr, uid, ts_ws_ids[0], ['ws_id'])
                
                working_schedule_id = ts_ws.get('ws_id', False) and ts_ws['ws_id'][0]
                if working_schedule_id:
                    #Search in WS Details to get shift on date of Working Schedule
                    ws_detail_ids = self.pool.get('vhr.ts.ws.detail').search(cr, uid, [('date','=',date),
                                                                                        ('ws_id','=',working_schedule_id)])
                    #Get shift id
                    if ws_detail_ids:
                        ws_detail = self.pool.get('vhr.ts.ws.detail').read(cr, uid, ws_detail_ids[0],['shift_id'])
                        shift_id = ws_detail.get('shift_id', False) and ws_detail['shift_id'][0]
        
        return working_schedule_id, shift_id
    
    def check_ot_time(self, cr, uid, employee_id, date_off, start_time, end_time, break_time, context=None):
    	res = {}
        if employee_id and date_off and end_time:
            working_shift_pool = self.pool.get('vhr.ts.working.shift')
            employee = self.pool.get('hr.employee').read(cr, uid, employee_id, ['name','code'])
            employee_name = employee.get('name','') + ' - ' + employee.get('code','')
            date_str = datetime.strptime(date_off,DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y")
            
            working_schedule_id, shift_id = self.get_working_schedule_and_shift_of_employee(cr, uid, employee_id, date_off, context)
            
            #Check for shift have time in two days: for ex: 23:00 - 6:00
            previous_days_off = datetime.strptime(date_off,DEFAULT_SERVER_DATE_FORMAT) - relativedelta(days=1)
            previous_days_off = previous_days_off.strftime(DEFAULT_SERVER_DATE_FORMAT)
            previous_working_schedule_id,  previous_shift_id = self.get_working_schedule_and_shift_of_employee(cr, uid, employee_id, previous_days_off, context)
            is_night_shift = False
            if previous_shift_id:
                previous_shift = working_shift_pool.read(cr, uid, previous_shift_id, ['is_night_shift'])
                is_night_shift = previous_shift.get('is_night_shift', False)
                
            if shift_id or is_night_shift:
                check_gap = []
                range1 = []
                range2 = []
                
                message_shift = {}
                
                #Get time of previous day shift in this day
                if is_night_shift:
                    previous_shift = working_shift_pool.browse(cr, uid, previous_shift_id)
                    pre_shift_name = previous_shift.name
                    pre_begin_work_time = previous_shift.begin_work_time
                    pre_end_work_time = previous_shift.end_work_time
                    
                    if pre_begin_work_time > pre_end_work_time:
                        range2 = [(0, pre_end_work_time)]
                    
                    check_gap.extend(range2)
                    pre_begin_work_time = self.convert_from_float_to_float_time(pre_begin_work_time, context)
                    pre_end_work_time = self.convert_from_float_to_float_time(pre_end_work_time, context)
                    message_shift[previous_shift_id] = ' %s:  %s (hh:mm) - %s (hh:mm)'% (pre_shift_name, pre_begin_work_time, pre_end_work_time)
                
                #Get time of this day shift
                if shift_id:
                    shift = working_shift_pool.browse(cr, uid, shift_id)
                    shift_name = shift.name
                    begin_work_time = shift.begin_work_time
                    end_work_time = shift.end_work_time
                    
                    #We only get time of the day testing, do not take the time in the next day
                    if begin_work_time > end_work_time:
                        range1 = [(begin_work_time, 23.98)]
                    else:
                        range1 = [(begin_work_time, end_work_time)]
                        
                    check_gap.extend(range1)
                    begin_work_time = self.convert_from_float_to_float_time(begin_work_time, context)
                    end_work_time = self.convert_from_float_to_float_time(end_work_time, context)
                    message_shift[shift_id] = ' %s:  %s (hh:mm) - %s (hh:mm)'% (shift_name, begin_work_time, end_work_time)
                
                overlap_shift = []
                overlap_time = 0
                for gap in check_gap:
                    begin = gap[0]
                    end = end_time
                    if start_time >= gap[0]:
                        begin = start_time
                    if end_time > gap[1]:
                        end = gap[1]
                    
                    if end - begin > 0:
                        overlap_time += (end-begin)
                        if gap in range1:
                            overlap_shift.append(shift_id)
                        else:
                            overlap_shift.append(previous_shift_id)
                        
                if overlap_time:
                    message = ''
                    for shift_id in overlap_shift:
                        message += '\n' + message_shift[shift_id]
                    raise osv.except_osv(_('Error !'), _('Đăng ký ngoài giờ ngày %s trùng với lịch làm việc: %s ')%(date_str, message))
            
            if working_schedule_id:
                #Search for parameter thoi gian quy dinh ot dem
                #TODO: change sang search bang sequence code
                working_schedule = self.pool.get('vhr.ts.working.schedule').read(cr, uid, working_schedule_id, ['name'])
                working_schedule_name = working_schedule.get('name','')
                
                param_type_ids, param_ws_ids = self.get_param_ws_by_company_param_code(cr, uid, working_schedule_id, 15, context)
                if param_type_ids:
                    if param_ws_ids:
                    	param_ws = self.pool.get('vhr.ts.param.working.schedule').read(cr, uid, param_ws_ids[0],['time_from','time_to'])
                        time_from = param_ws.get('time_from',0)
                        time_to = param_ws.get('time_to',0)
                        check_gap = [(time_from, time_to)]
                        if time_from > time_to:
                            check_gap = [(time_from, 23.98), (0, time_to)]
                        
                        ot_night = 0
                        for gap in check_gap:
                            begin = gap[0]
                            end = end_time
                            if start_time > gap[0]:
                                begin = start_time
                            if end_time > gap[1]:
                                end = gap[1]
                            
                            if end - begin > 0:
                                ot_night += (end-begin)
                           
                     	total_hours = self.get_total_hours(cr, uid, start_time, end_time, break_time, context)
                         #Case nghỉ phép dạng: 0-6h, break_time=1min, hoặc 0-7h, break-time>60min
                        if ot_night > total_hours:
                            ot_night = total_hours
                            
                        ot_day = total_hours - ot_night
                        res['total_ot_day_register'] = ot_day
                        res['total_ot_night_register'] = ot_night   
                        
                        res['total_ot_day_approve'] = ot_day
                        res['total_ot_night_approve'] = ot_night   
                        res['total_hours_approve'] = total_hours
                    else:
             			raise osv.except_osv(_('Error !'), _("Don't have any parameter by working schedule with value [Thời gian quy định giờ đêm]!"))
                else:
               		raise osv.except_osv(_('Error !'), _("Don't have parameter type [Thời gian quy định giờ đêm]!"))
            else:
                raise osv.except_osv(_('Error !'), _("Employee %s don't have any active working schedule!") %(employee_name))
        
        return res
    
    
    #Return True if duoc nghi bu, get job_level tu Working record active
    def is_compensation_leave(self, cr, uid, employee_id, context=None):
        if employee_id:
            working_record_ids = self.pool.get('vhr.working.record').search(cr, uid,[('employee_id','=',employee_id),
#                                                                                      ('company_id','=',company_id),
                                                                                     ('active','=',True)])
            if working_record_ids:
                working_record = self.pool.get('vhr.working.record').read(cr, uid, working_record_ids[0], ['job_level_person_id_new'])
                job_level_person_id_new =  working_record.get('job_level_person_id_new', False) and working_record['job_level_person_id_new'][0]
                if job_level_person_id_new:
                    #Search for id cua tham cap bac duoc nghi bu
                    #TODO: lam theo sequence code
                    param_type_ids = self.pool.get('vhr.ts.param.type').search(cr, uid, [('code','=',11)])
                    if param_type_ids:
                        param_job_ids = self.pool.get('vhr.ts.param.job.level').search(cr, uid, [('job_level_new_id','=',job_level_person_id_new),
                                                                                                 ('param_type_id','=',param_type_ids[0]),
                                                                                                 ('active','=',True)])
                        if param_job_ids:
                            param_job = self.pool.get('vhr.ts.param.job.level').read(cr, uid, param_job_ids[0],['value'])
                            value =param_job.get('value', 0)
                            if value:
                                return True
        return False
    
    def check_overlap_ot_date(self, cr, uid, ids, context=None):
        if not isinstance(ids, list):
            ids = [ids]
        if ids:
            records = self.browse(cr, uid, ids)
            for record in records:
                employee_id = record.employee_id and record.employee_id.id or False
#                 company_id = record.company_id and record.company_id.id or False
                
                date = record.date_off
                start_time = record.start_time
                end_time = record.end_time
                
                same_day_ot_ids = self.search(cr, uid, [('employee_id','=',employee_id),
                                                        ('state','!=','cancel'),
#                                                       ('company_id','=',company_id),
                                                        ('date_off','=',date)])
                
                if same_day_ot_ids:
                    if record.id in same_day_ot_ids:
                        same_day_ot_ids.remove(record.id)
                    same_day_ots = self.read(cr, uid, same_day_ot_ids, ['start_time','end_time'])
                    
                    for same_day_ot in same_day_ots:
                        begin_time = same_day_ot.get('start_time',False)
                        fin_time = same_day_ot.get('end_time',False)
                        
                        gap = (begin_time, fin_time)
                        overlap_count_time = 0
                        begin = gap[0]
                        end = end_time
                        if start_time >= gap[0]:
                            begin = start_time
                        if end_time > gap[1]:
                            end = gap[1]
                        
                        if end - begin > 0:
                            overlap_count_time += (end-begin)
                        
                        if overlap_count_time:
                            date_str = datetime.strptime(date,DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y")
                            raise osv.except_osv(_('Validation Error !'), _('Đăng ký ngoài giờ ngày %s đã được đăng ký. Vui lòng chọn lại ngày!') % date_str)
        return True
    
    def check_valid_ot_time(self, cr, uid, start_time, end_time, context=None):
        if end_time and start_time < end_time:
                return True
        
        raise osv.except_osv(_('Error !'), _('Start Time must lower End Time'))
    
    def get_day_night_coef(self, cr, uid, ids, context=None):
        res = {}
        if ids:
            if not isinstance(ids, list):
                ids = [ids]
            
            ot_sum_pool = self.pool.get('vhr.ts.overtime.summarize')
            param_ws_pool = self.pool.get('vhr.ts.param.working.schedule')
            records = self.browse(cr, uid, ids)
            for record in records:
                vals = {'day_coef': 0, 'night_coef': 0, 'allowance_night_coef': 0,
                        'day_coef_compensation': 0, 'night_coef_compensation': 0,
                        'allowance_night_coef_compensation': 0
                        }
                employee_id = record.employee_id and record.employee_id.id or False
#                 company_id = record.company_id and record.company_id.id or False
                date = record.date_off
                
                ts_ws_ids = self.pool.get('vhr.ts.ws.employee').search(cr, uid, [('employee_id','=',employee_id),
#                                                                              ('company_id','=',company_id),
                                                                             '|',('active','=', True),('active','=', False),
                                                                                 ('effect_from','<=',date),
                                                                            '|',('effect_to','=',False),('effect_to','>=',date)])
            
                if ts_ws_ids:
                    ts_ws = self.pool.get('vhr.ts.ws.employee').read(cr, uid, ts_ws_ids[0], ['ws_id'])
                    
                    working_schedule_id = ts_ws.get('ws_id', False) and ts_ws['ws_id'][0]
                    if working_schedule_id:
                        #Lấy giá trị hệ số OT đêm
                        coef_night, coef_comp_night = self.get_specific_coef_for_working_schedule(cr, uid, working_schedule_id, 21, context)
                        vals['night_coef'] = coef_night
                        vals['night_coef_compensation'] = coef_comp_night
                        
                        #Lấy giá trị hệ số phụ cấp đêm
                        coef_night_allowance, coef_comp_night_allowance = self.get_specific_coef_for_working_schedule(cr, uid, working_schedule_id, 23, context)
                        vals['allowance_night_coef'] = coef_night_allowance
                        vals['allowance_night_coef_compensation'] = coef_comp_night_allowance
                        
                        type_date = ot_sum_pool.check_whether_day_is_weekday_or_off_day(cr, uid, employee_id, date, context)
                        if type_date == 1:
                            #OT ngày lễ        =Số giờ * HS OT lễ
                            #OT đêm lễ         =Số giờ*(HS OT lễ + HS OT đêm) + Số giờ*   (HS OT lễ)* (HS phụ cấp đêm)
                                            #  = so gio * (hs OT le + hs OT dem + hr OT le * hs phu cap dem)
                            #Get param by ws cho hệ số OT lễ ban ngày
                            day_coef, day_coef_comp = self.get_specific_coef_for_working_schedule(cr, uid, working_schedule_id, 14, context)
                            vals['day_coef'] = day_coef
                            vals['day_coef_compensation'] = day_coef_comp
                            
                        elif type_date == 2:
                            #Get param by ws cho hệ số OT nghỉ
                            day_coef, day_coef_comp = self.get_specific_coef_for_working_schedule(cr, uid, working_schedule_id, 13, context)
                            vals['day_coef'] = day_coef
                            vals['day_coef_compensation'] = day_coef_comp
                        
                        elif type_date == 3:
                            #Get param by ws cho hệ số OT thường
                            day_coef, day_coef_comp = self.get_specific_coef_for_working_schedule(cr, uid, working_schedule_id, 12, context)
                            vals['day_coef'] = day_coef
                            vals['day_coef_compensation'] = day_coef_comp
                if vals:
                    res[record.id] = vals
        
        return res
                
                            
    
    def get_specific_coef_for_working_schedule(self, cr, uid, working_schedule_id, param_code, context=None):
        day_coef = 0
        day_coef_comp = 0
        
        if working_schedule_id and param_code:
            param_type_ids, param_ws_day_ids = self.get_param_ws_by_company_param_code(cr, uid, working_schedule_id, param_code, context)
            if not param_ws_day_ids:
                raise osv.except_osv(_('Error !'), _("Don't have any parameter by working schedule with code [%s]!") % param_code)
            
            param = self.pool.get('vhr.ts.param.working.schedule').read(cr, uid, param_ws_day_ids[0], ['coef','coef_compensation_leave'])
            day_coef = param.get('coef', 0)
            day_coef_comp = param.get('coef_compensation_leave', 1)
        
        return day_coef, day_coef_comp
    
    def get_param_ws_by_company_param_code(self, cr, uid, working_schedule_id, param_code, context=None):
        param_ws_ids = False
        param_type_ids = False
        if working_schedule_id and param_code:
            ws_pool = self.pool.get('vhr.ts.working.schedule')
            param_ws_pool = self.pool.get('vhr.ts.param.working.schedule')
            param_type_ids = self.pool.get('vhr.ts.param.type').search(cr, uid, [('code','=',param_code)])
            if param_type_ids:
                #Lay thong tin time_from time_to cuar thoi gian quy dinh gio den de tinh ot_night , ot_day
                param_ws_ids = param_ws_pool.search(cr, uid, [
#                                                               ('company_id','=',company_id),
                                                              ('working_schedule_id','=',working_schedule_id),
                                                              ('param_type_id','=',param_type_ids[0]),
                                                              ('active','=',True)])
                
                #Check if have config group working schedule
                if not param_ws_ids:
                    ws = ws_pool.read(cr, uid, working_schedule_id, ['group_schedule_id'])
                    group_schedule_id = ws.get('group_schedule_id', False) and ws['group_schedule_id'][0] or False
                    if group_schedule_id:
                        param_ws_ids = param_ws_pool.search(cr, uid, [
                                                                      ('working_schedule_group_id','=',group_schedule_id),
                                                                      ('param_type_id','=',param_type_ids[0]),
                                                                      ('active','=',True)])
                
                
                if not param_ws_ids:
                    
                    config_parameter = self.pool.get('ir.config_parameter')
                    general_ws_code = config_parameter.get_param(cr, uid, 'general_working_schedule_code')
                    general_ws_code_list = general_ws_code.split(',')
                    #neu khong co param_ws_ids cho working_schedule_id, lay param_wd_ids cua working schedule :lich lam viecn chinh
                    main_working_schedule_ids = self.pool.get('vhr.ts.working.schedule').search(cr, uid, [('code','in',general_ws_code_list)])
                    
                    if main_working_schedule_ids:
                        param_ws_ids = param_ws_pool.search(cr, uid, [
#                                                                       ('company_id','=',company_id),
                                                                      ('working_schedule_id','=',main_working_schedule_ids[0]),
                                                                      ('param_type_id','=',param_type_ids[0]),
                                                                      ('active','=',True)])
                        
        return param_type_ids, param_ws_ids
    
    def update_day_night_coef(self, cr, uid, ids, context=None):
        if ids:
            if not isinstance(ids, list):
                ids = [ids]
            res = self.get_day_night_coef(cr, uid, ids, context)
            for record_id in ids:
                super(vhr_ts_overtime_detail, self).write(cr, uid, ids, res[record_id], context)
        
        return True
    
                    
    
    def create(self, cr, uid, vals, context=None):
        if not context:
            context = {}
        
        if not context.get('create_from_multi', False):
            self.check_valid_ot_time(cr, uid, vals.get('start_time'), vals.get('end_time'), context)
            nvals = self.check_ot_time(cr, uid, vals.get('employee_id'), vals.get('date_off'), vals.get('start_time'), vals.get('end_time'), vals.get('break_time'), context)
            vals.update(nvals)
        
        vals['approve_date'] = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        res = super(vhr_ts_overtime_detail, self).create(cr, uid, vals, context)
        
        if res and not context.get('create_from_multi', False):
            if not context.get('action_from_ot', False):
                self.check_overlap_ot_date(cr, uid, [res], context)
            self.update_day_night_coef(cr, uid, [res], context)
            self.create_update_to_ot_sum(cr, uid, [res], context)
            
            if vals.get('is_compensation_leave', False):
                self.create_annual_leave(cr, uid, [res], context)
            
        return res
    
    
    def write(self, cr, uid, ids, vals, context=None):
        if not context:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]
        if ids:
            if set(['start_time','end_time','break_time','date_off','state','is_compensation_leave']).intersection(set(vals.keys())):
                record = self.read(cr, uid, ids[0],['employee_id','date_off','start_time','end_time','break_time','is_compensation_leave'])
                old_employee_id = record.get('employee_id', False) and record['employee_id'][0]
#                 old_company_id = record.get('company_id', False) and record['company_id'][0]
                
                employee_id = vals.get('employee_id', old_employee_id)
#                 company_id = vals.get('company_id', old_company_id)
                date_off = vals.get('date_off', record.get('date_off',False))
                start_time = vals.get('start_time', record.get('start_time',False))
                end_time = vals.get('end_time', record.get('end_time',False))
                break_time = vals.get('break_time', record.get('break_time',False))
                is_compensation_leave = vals.get('is_compensation_leave', record.get('is_compensation_leave',False))
                
                
                if set(['start_time','end_time','break_time','date_off']).intersection(set(vals.keys())):
                    self.check_valid_ot_time(cr, uid, start_time, end_time, context)
                    nvals = self.check_ot_time(cr, uid, employee_id, date_off, start_time, end_time, break_time, context)
                    vals.update(nvals)
            
            if vals.get('state', False):
                vals['approve_date'] = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        
        res = super(vhr_ts_overtime_detail, self).write(cr, uid, ids, vals, context)
        
        if res:
            if (vals.get('start_time', False) or vals.get('end_time', False) or vals.get('state',False)) and not context.get('action_from_ot', False):
                self.check_overlap_ot_date(cr, uid, ids, context)
            
            if vals.get('date_off', False):
                self.update_day_night_coef(cr, uid, ids, context)
            
            if vals.get('state', False):
                self.check_if_can_submit(cr, uid, ids)
                
            if not context.get('update_from_ot_sum', False) and\
             set(['state','date_off','total_ot_night_register','total_ot_day_register','total_ot_day_approve','total_ot_night_approve','is_compensation_leave']).intersection(set(vals.keys())):
                self.create_update_to_ot_sum(cr, uid, ids, context)
            
            if vals.get('is_compensation_leave', False) or vals.get('state', False):
                self.create_annual_leave(cr, uid, ids, context)
            
        return res
    
    def unlink(self, cr, uid, ids, context=None):
        overtime_sum_ids = []
        if ids:
            records = self.read(cr, uid, ids, ['overtime_sum_id'])
            for record in records:
                overtime_sum_id = record.get('overtime_sum_id', False) and record['overtime_sum_id'][0]
                if overtime_sum_id:
                    overtime_sum_ids.append(overtime_sum_id)
                    
        res = super(vhr_ts_overtime_detail, self).unlink(cr, uid, ids, context)
        if res and overtime_sum_ids:
            self.pool.get('vhr.ts.overtime.summarize').calculate_value_from_overtime_detail(cr, SUPERUSER_ID, overtime_sum_ids, context)
        return res
    
    def check_if_can_submit(self, cr, uid, ids, context=None):
        """
        Nếu tạo OT trả lương, submit trễ sang tháng khác, cập nhật lại ot_summary_id, làm trong create_update_to_ot_sum
        Chỉ cho submit trễ nhất là 1 tháng 
        """
        if ids:
            ot_summary_pool = self.pool.get('vhr.ts.overtime.summarize')
            records = self.read(cr, uid, ids, ['date_off','is_compensation_leave','employee_id','overtime_sum_id'])
            for record in records:
                employee_id = record.get('employee_id', False) and record['employee_id'][0] or False
                overtime_sum_id = record.get('overtime_sum_id',False) and record['overtime_sum_id'][0] or False
                date_off = record.get('date_off', False)
                
                is_compensation_leave = record.get('is_compensation_leave', False)
                #Nếu tạo OT trả lương, chỉ cho submit trễ nhất là 1 tháng: today <= date_off + 1 months
                if employee_id and not is_compensation_leave:
                    date = datetime.strptime(date_off,DEFAULT_SERVER_DATE_FORMAT).date()
                    today = time.strftime(DEFAULT_SERVER_DATE_FORMAT)
                    
                    date_next_month = date + relativedelta(months=1)
                    today_time = datetime.strptime(today,DEFAULT_SERVER_DATE_FORMAT).date()
                    gaps = date_next_month - today_time
                    if gaps.days < 0:
                        date = date.strftime('%d-%m-%Y')
                        raise osv.except_osv(_('Validation Error !'), _('You can not submit/approve OT later than one month'))
                    
        return True
        
    def create_update_to_ot_sum(self, cr, uid, ids, context=None):
        try:
            if not context:
                context = {}
            if ids:
                records = self.browse(cr, uid, ids, fields_process=['date_off','approve_date','is_compensation_leave','employee_id','overtime_sum_id','overtime_id'])
                overtime_sum_pool = self.pool.get('vhr.ts.overtime.summarize')
                update_ot_sum_dict = {}
                recalcu_overtime_sum_ids = []
                for record in records:
                    update_ot_sum_ids, recalcu_overtime_sum_ids = self.check_update_ot_sum(cr, uid, record, [], recalcu_overtime_sum_ids, context)
                    if update_ot_sum_ids:
                        if update_ot_sum_ids[0] in update_ot_sum_dict:
                            update_ot_sum_dict[update_ot_sum_ids[0]].append(record.id)
                        else:
                            update_ot_sum_dict[update_ot_sum_ids[0]] = [record.id]
                    
                if update_ot_sum_dict:
                    for ot_sum_id in update_ot_sum_dict:
                        overtime_sum_pool.add_new_ot_detail_into_ot_summary(cr, SUPERUSER_ID, ot_sum_id, update_ot_sum_dict[ot_sum_id])
                
                if recalcu_overtime_sum_ids:
                    overtime_sum_pool.calculate_value_from_overtime_detail(cr, SUPERUSER_ID, recalcu_overtime_sum_ids)
                
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
            raise osv.except_osv(_('Validation Error !'), _('Have error during create-update to Overtime Summarize:\n %s!') % error_message)   
        
    def check_update_ot_sum(self, cr, uid, record, update_overtime_sum_ids, recalcu_overtime_sum_ids, context):
        if record:
            overtime_sum_pool = self.pool.get('vhr.ts.overtime.summarize')
            date_off = record.date_off
            approve_date = record.approve_date
            is_compensation_leave = record.is_compensation_leave
            date = datetime.strptime(date_off,DEFAULT_SERVER_DATE_FORMAT)
            ot_line_state = record.state
            ot_state = record.overtime_id and record.overtime_id.state
            ot_summary_effect_from = record.overtime_sum_id and record.overtime_sum_id.date_to or False
            ot_summary_effect_from = ot_summary_effect_from and datetime.strptime(ot_summary_effect_from,DEFAULT_SERVER_DATE_FORMAT)
#                     date_str = date.strftime("%d-%m-%Y")
            
            employee_id = record.employee_id and record.employee_id.id or False
#                     company_id = record.company_id and record.company_id.id or False
            employee_code = record.employee_id and record.employee_id.code or ''
            employee_name = record.employee_id and record.employee_id.name or ''
            
            if is_compensation_leave or not approve_date:
            #Type compensation, OT summary go with date_off
                date_fin_ot = date
                ot_sum_ids = overtime_sum_pool.search(cr, uid, [('employee_id','=',employee_id),
#                                                                    ('company_id','=',company_id),
                                                                ('date_from','<=',date_off),
                                                                ('date_to','>=',date_off),
                                                               ])
                
            else:
                #Type pay money, OT summary go with approve_date if approve date > date_off
        #                           go with date_off if date_off >= approve_date
                approve_date_strp = datetime.strptime(approve_date,DEFAULT_SERVER_DATETIME_FORMAT)
                date_fin_ot = date
                if approve_date_strp > date:
                    date_fin_ot = approve_date_strp.date()
                    
                    #Must compare with close_date + 12h(submit) / 17h(approve) to know that should we move to OT sum of next period
                    param = 'hours_check_submit_ot_late'
                    if ot_state == 'finish' or ot_line_state == 'finish':
                        param = 'hours_check_approve_ot_late'
                        
                    gap_hours = self.pool.get('ir.config_parameter').get_param(cr, uid, param)or ''
                    gap_hours = gap_hours.split(',')
                    try:
                        gap_hours = gap_hours and gap_hours[0]
                        gap_hours = int(gap_hours) - 7
                    except Exception as e:
                        raise osv.except_osv('Validation Error !', 'Can not convert value to integer from ir_config_parameter with key "%s" !'%param)
            
                    #Get close date of timesheet period where date belong to
                    sql = '''
                            SELECT ts_detail.close_date, ts_detail.to_date
                                                     FROM vhr_ts_timesheet_detail ts_detail INNER JOIN
                                                          vhr_ts_emp_timesheet  emp_ts 
                                                      ON ts_detail.timesheet_id =emp_ts.timesheet_id
                                                      
                            WHERE emp_ts.employee_id = %s AND 
                                  emp_ts.effect_from <= '%s' AND 
                                  ( emp_ts.effect_to >= '%s' OR emp_ts.effect_to is null  ) AND
                                  ts_detail.from_date <= '%s' AND 
                                  ts_detail.to_date >= '%s'
                          '''
                    cr.execute(sql%(employee_id, date,date,date,date))
                    res = cr.fetchall()
                    ts_details = [[item[0],item[1]] for item in res]
                    if ts_details:
                        close_date = ts_details[0][0]
                        ts_detail_to_date = ts_details[0][1]
                        if close_date:
                            close_date = datetime.strptime(close_date, DEFAULT_SERVER_DATE_FORMAT) 
                            
                            close_datetime = close_date + relativedelta(hours=gap_hours)
                            if approve_date_strp <= close_datetime:
                                date_fin_ot = date
                            else:
                                #We should check to ot_sum have date range consist (ts_detail_to_date +1) of next timesheet period, not approve date
                                #(because approve_date is datetime, and we compare approve_date by datetime (12h/17h)
                                ts_detail_to_date = datetime.strptime(ts_detail_to_date, DEFAULT_SERVER_DATE_FORMAT) 
                                ts_detail_to_date += relativedelta(days=1)
                                date_fin_ot = ts_detail_to_date
                            
                            #Dont allow to move from ot_summary of month x to month x-y (y in [1,2,...]
                            if ot_summary_effect_from and ot_summary_effect_from > date_fin_ot:
                                date_fin_ot = ot_summary_effect_from
                                
                            ot_sum_ids = overtime_sum_pool.search(cr, uid, [('employee_id','=',employee_id),
    #                                                                    ('company_id','=',company_id),
                                                                    ('date_from','<=',date_fin_ot),
                                                                    ('date_to','>=',date_fin_ot),
                                                                   ])
                    else:
                        date_str = date.strftime("%d-%m-%Y")
                        raise osv.except_osv('Validation Error !', 'Employee don\'t have any active timesheet/ timesheet detail at %s !' % date_str)

                    
                else:
                    ot_sum_ids = overtime_sum_pool.search(cr, uid, [('employee_id','=',employee_id),
    #                                                                    ('company_id','=',company_id),
                                                                    ('date_from','<=',date_fin_ot),
                                                                    ('date_to','>=',date_fin_ot),
                                                                   ])
            #Update overtime_detail_ids of ot summarize
            if ot_sum_ids:
                overtime_sum_id = record.overtime_sum_id and record.overtime_sum_id.id or False
                #If ot_line link to new ot_sum, update ot line, calculate old ot sum
                if overtime_sum_id and overtime_sum_id not in ot_sum_ids:
                    update_overtime_sum_ids.extend(ot_sum_ids)
#                             overtime_sum_pool.update_overtime_detail_ids(cr, SUPERUSER_ID, ot_sum_ids)
                    recalcu_overtime_sum_ids.append(overtime_sum_id)
#                             overtime_sum_pool.calculate_value_from_overtime_detail(cr, SUPERUSER_ID, [overtime_sum_id])
                
                #If ot line still link to old ot sum, update info in data sum
                elif overtime_sum_id:
                    recalcu_overtime_sum_ids.append(overtime_sum_id)
#                             overtime_sum_pool.calculate_value_from_overtime_detail(cr, SUPERUSER_ID, [overtime_sum_id])
                
                #If ot line does not link to any ot sum, link to new ot sum
                else:
                    update_overtime_sum_ids.extend(ot_sum_ids)
#                             overtime_sum_pool.update_overtime_detail_ids(cr, SUPERUSER_ID, ot_sum_ids)
            else:
                self.create_ot_sum(cr, uid, record, employee_id, date_fin_ot, employee_name, employee_code, context)
        
        return update_overtime_sum_ids, recalcu_overtime_sum_ids
    
    def create_ot_sum(self, cr, uid, record, employee_id, date, employee_name, employee_code, context=None):
        #Create OT Summary from data: record, employee_id, date, employee_code
        #Carefull with record because record is using .browse(...fields_process=[])
        try:
            overtime_sum_pool = self.pool.get('vhr.ts.overtime.summarize')
            if record and employee_id and date and employee_code and employee_name:
                date_str = date.strftime("%d-%m-%Y")
                    
                vals = {'employee_id'         : employee_id, 
                        'employee_code'       : employee_code,
    #                                 'company_id'          : company_id,
                        'overtime_detail_ids' : [[6,False, [record.id]]],
                        }
                
                detail_ids, nvals = overtime_sum_pool.compute_summary_data_from_overtime_details(cr, uid, False, [record], context)
                vals.update(nvals)
                
                ts_emp_ids, timesheet_id, timesheet_name, timesheet_detail_ids = self.get_timesheet_detail_of_employee_on_date(cr, uid, employee_id, date, context)
                
                if ts_emp_ids:
                    if timesheet_detail_ids:
                        timesheet_detail = self.pool.get('vhr.ts.timesheet.detail').read(cr, uid, timesheet_detail_ids[0], ['from_date','to_date','month','year'] )
                        vals['date_from'] = timesheet_detail.get('from_date', False)
                        vals['date_to'] = timesheet_detail.get('to_date', False)
                        vals['month_ot'] = timesheet_detail.get('month', False)
                        vals['year_ot'] = timesheet_detail.get('year', False)
                        vals['month_pay_ot'] = timesheet_detail.get('month', False)
                        vals['year_pay_ot'] = timesheet_detail.get('year', False)
                        
                        context['update_from_ot_sum'] = True
                        overtime_sum_pool.create(cr, SUPERUSER_ID, vals, context)
                        
                    else:
                        raise osv.except_osv('Error !', "Timesheet %s of employee %s on %s doesn't belong to any period. Please check again!"% (timesheet_name, employee_name, date_str))
                else:
                    raise osv.except_osv('Error !', "Employee %s doesn't belong to any timesheet on %s. Please check again!"% (employee_name, date_str))
                
        except Exception as e:
            log.exception(e)
            try:
                error_message = e.message
                if not error_message:
                    error_message = e.value
            except:
                error_message = ""
            raise osv.except_osv('Validation Error !', ' %s!' % error_message)    
        
        return True
            
    
    #Create new annual leave with type nghi bu if not have
    def create_annual_leave(self, cr, uid, ids, context=None):
        if ids:
            if not isinstance(ids, list):
                ids = [ids]
            
            holiday_status_pool = self.pool.get('hr.holidays.status')
            holiday_pool = self.pool.get('hr.holidays')
            records = self.read(cr, uid, ids, ['employee_id', 'date_off'])
            
            for record in records:
                employee_id = record.get('employee_id', False) and record['employee_id'][0] or False
                date_off = record.get('date_off', False)
                year = datetime.strptime(date_off, DEFAULT_SERVER_DATE_FORMAT).year
                
                config_parameter = self.pool.get('ir.config_parameter')
                config_holiday_status_code = config_parameter.get_param(cr, uid, 'ts.leave.type.overtime.code')
                if not config_holiday_status_code:
                    raise osv.except_osv('Validation Error !', "Don't have parameter define leave type of leave off because to work overtime !")
                
                holiday_status_code_list = config_holiday_status_code.split(',')
                holiday_status_ids = holiday_status_pool.search(cr, uid, [('code','in',holiday_status_code_list)])
                if not holiday_status_ids:
                    raise osv.except_osv('Validation Error !', "Can not find any leave types with code %s !" % holiday_status_code_list)
                
                if employee_id and year and holiday_status_ids:
                    holiday_ids = holiday_pool.search(cr, uid, [('employee_id', '=', employee_id),
                                                                ('holiday_status_id', 'in', holiday_status_ids),
                                                                ('type', '=', 'add'),
                                                                ('state', '=', 'validate'),
                                                                ('year', '=', year)], context={'get_all': 1})
                    
                    #if dont have annual leave with type overtime, create it
                    if not holiday_ids:
                        vals = {'employee_id': employee_id,
                                'holiday_status_id': holiday_status_ids[0],
                                'type': 'add',
                                'state': 'validate',
                                'is_offline': True,
                                'year': year}
                        
                        employee_instance = self.pool.get('hr.employee').browse(cr, uid, employee_id, fields_process=['name', 'code','department_id','report_to'])
                        vals['employee_code'] = employee_instance.code or ''
                        vals['department_id'] = employee_instance.department_id and employee_instance.department_id.id or False
                        vals['dept_head_id'] = employee_instance.department_id and employee_instance.department_id.manager_id\
                                                and employee_instance.department_id.manager_id.id or False
                                                
                        vals['report_to_id'] = employee_instance.report_to and employee_instance.report_to.id or False
                        
                        holiday_pool.create(cr, uid, vals)
                else:
                    log.info("Error when create_annual_leave: employee_id and year and holiday_status_ids == False")
                    
        return True
    
            
            
    def btn_approve(self, cr, uid, ids, context=None):
        if ids:
            
            self.write(cr, uid, ids, {'state': 'finish'})
        
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
    
    def btn_reject(self, cr, uid, ids, context=None):
        if ids:
            self.write(cr, uid, ids, {'state': 'cancel'})
        
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
                

vhr_ts_overtime_detail()