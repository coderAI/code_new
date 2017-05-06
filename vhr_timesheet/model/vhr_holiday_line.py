# -*- coding: utf-8 -*-
import logging
from openerp.osv import osv, fields
from openerp.tools.translate import _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp import SUPERUSER_ID

from openerp.addons.vhr_common.model.vhr_common import vhr_common

STATUS = [('full', _('Full day')), ('morning', _('First haft day/shift')),
          ('afternoon', _('Last haft day/shift'))]


log = logging.getLogger(__name__)

class vhr_holiday_line(osv.osv, vhr_common):
    _name = 'vhr.holiday.line'
    _description = 'VHR Holiday Detail'
    _columns = {
        'holiday_id': fields.many2one('hr.holidays', 'Holiday', ondelete='cascade'),
        'holiday_status_id': fields.related('holiday_id', 'holiday_status_id', type='many2one',
                                            relation='hr.holidays.status', string="Leave Type",
                                            store=True),
        'holiday_multi_id': fields.many2one('vhr.holidays.multi', 'Holiday', ondelete='cascade'),
        'date': fields.date('Date'),
        'status': fields.selection(STATUS, 'Status'),
        'is_edit_status': fields.boolean('Is Edit Status'),
        'number_of_days_temp': fields.float('Number of days', digits=(3, 2)),
        'number_of_hours': fields.float('Number of hours', digits=(3, 1)),
        'number_of_hours_in_shift': fields.float('Number of hours in shift', digits=(3, 1)),
        'employee_id': fields.related('holiday_id', 'employee_id', type='many2one',
                                      relation='hr.employee', string='Employee', store=True),
        'company_id': fields.related('holiday_id', 'company_id', type='many2one',
                                     relation='res.company', string='Company', store=True),
    }
    
    _order = 'date desc'

    _defaults = {
        'status': 'full',
        'number_of_days_temp': 1.0,
        'is_edit_status': True,
    }

    def onchange_number_of_days_temp(self, cr, uid, ids, status, number_of_days_temp, number_of_hours, 
                                                        number_of_hours_in_shift = 0, context=None):
        res = {'value': {'number_of_days_temp': 0, 'number_of_hours':0}}
        
        if not number_of_hours_in_shift:
            number_of_hours_in_shift = 0
        if status:
            if status == 'full':
                res['value']['number_of_days_temp'] = number_of_hours_in_shift/ (number_of_hours/float(number_of_days_temp))
                res['value']['number_of_hours'] = number_of_hours_in_shift
            else:
                res['value']['number_of_days_temp'] = number_of_hours_in_shift/ (number_of_hours/float(number_of_days_temp)) *0.5
                res['value']['number_of_hours'] = number_of_hours_in_shift * 0.5
        return res

    def name_get(self, cr, user, ids, context=None):
        if not ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        result = self.browse(cr, user, ids, context=context)
        res = []
        for rs in result:
            date = rs.date
            name = "%s/%s/%s" % (date[8:10], date[5:7], date[:4])
            res += [(rs.id, name)]
        return res
    
    def check_if_date_not_in_generated_monthly(self, cr, uid, employee_id, daterange, context=None):
        '''
        Dont allow to create if date appear in record ts.monthly at state sent/approve
        input date may be just a date string or an array of date string
        '''
        if not context:
            context = {}
        
        if not isinstance(daterange, list):
            daterange = [daterange]
            
        if employee_id and daterange:
            model_name = context.get('model_name','leave request')
            #Case employee had been generated with type is_last_payment
            #Read terminate change form code
            wr_obj = self.pool.get('vhr.working.record')
            ts_detail_obj = self.pool.get('vhr.ts.timesheet.detail')
            
            change_form_terminated_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_master_data_dismiss_change_form_code') or ''
            change_form_terminated_code = change_form_terminated_code.split(',')
            change_form_ids = self.pool.get('vhr.change.form').search(cr, uid, [('code', 'in', change_form_terminated_code)],context=context)
            
            #Save date can by pass in list
            list_date_by_pass = []
            for date in daterange:
                is_continue = False
                #Check if date in couple[0] to couple[1] is checked
                if list_date_by_pass:
                    for couple_date in list_date_by_pass:
                        if self.compare_day(couple_date[0],date) >=0 and self.compare_day(date, couple_date[1]) >= 0:
                            is_continue = True
                            continue
                
                if is_continue:
                    continue
                
                ts_detail_ids = ts_detail_obj.search(cr, uid, [('from_date','<=',date),
                                                               ('to_date','>=',date)], order='from_date asc')
                
                if ts_detail_ids:
                    ts_detail = ts_detail_obj.read(cr, uid, ts_detail_ids[0], ['from_date','to_date'])
                    list_date_by_pass.append( (ts_detail['from_date'],ts_detail['to_date']) )
                else:
                    #Incase khong co timesheet detail với  from_date <= date<= to_date
                    #Thêm vào list date by pass, couple từ to_date của ts_detail lớn nhất tới 10 năm sau :))
                    latest_ts_detail_ids = ts_detail_obj.search(cr, uid, [], order='to_date desc',limit=1)
                    latest_ts_detail = ts_detail_obj.read(cr, uid, latest_ts_detail_ids[0], ['to_date'])
                    latest_ts_detail_date_to = latest_ts_detail.get('to_date', False)
                    if latest_ts_detail_date_to:
                        latest_ts_detail_date_to = datetime.strptime(latest_ts_detail_date_to, DEFAULT_SERVER_DATE_FORMAT)
                        latest_ts_detail_date_to_plus = (latest_ts_detail_date_to + relativedelta(days=1)).strftime(DEFAULT_SERVER_DATE_FORMAT)
                        latest_ts_detail_date_to_plus10 = (latest_ts_detail_date_to + relativedelta(years=10)).strftime(DEFAULT_SERVER_DATE_FORMAT)

                        list_date_by_pass.append((latest_ts_detail_date_to_plus, latest_ts_detail_date_to_plus10))
                        continue
                    
                
                ts_detail_ids.append(0)
                
                sql = '''
                        SELECT monthly.id, monthly.is_last_payment FROM vhr_ts_monthly monthly 
                        WHERE
                            monthly.timesheet_detail_id in %s AND
                            monthly.employee_id = %s AND
                            monthly.state in ('sent','approve')
                        ORDER BY monthly.date desc limit 1
                      '''
                cr.execute(sql%(str(tuple(ts_detail_ids)).replace(',)', ')'),employee_id))
                res = cr.fetchall()
                monthlys = [[item[0],item[1]] for item in res]
                
                if monthlys:
                    is_last_payment = monthlys[0][1]
                    
                    monthly = self.pool.get('vhr.ts.monthly').browse(cr, uid, monthlys[0][0], fields_process=['timesheet_detail_id'])
                    
                    timesheet_detail_effect_from = monthly.timesheet_detail_id and monthly.timesheet_detail_id.from_date or False
                    timesheet_detail_effect_to = monthly.timesheet_detail_id and monthly.timesheet_detail_id.to_date or False
                    #If generated timesheet detail on month-year have date
                    if not is_last_payment:
                        if context.get('return_boolean',False):
                            return False
                        raise osv.except_osv('Validation Error !', 
                                             "You can't create/edit %s when detail timesheet already sent.\nPlease check again or contact to C&B for support" % model_name)
                    
                    else:
                        dismiss_wr_ids = wr_obj.search(cr, uid, [('employee_id','=',employee_id),
                                                                 '|',('active','=',True),('active','=',False),
                                                                 ('state', 'in', (False, 'finish')),
                                                                 ('effect_from','>=',timesheet_detail_effect_from),
                                                                 ('effect_from','<=', timesheet_detail_effect_to),
                                                                 ('change_form_ids','in', change_form_ids)], order='effect_from desc')
                        if dismiss_wr_ids:
                            dismiss_wr = wr_obj.read(cr, uid, dismiss_wr_ids[0], ['effect_from'])
                            date_end_working = dismiss_wr.get('effect_from')
                            
                            #Remove couple date just append
                            list_date_by_pass.pop()
                            
                            #Add new couple date from date_end_working +1 to ts detail effect to
                            date_end_working_plus = (datetime.strptime(date_end_working, DEFAULT_SERVER_DATE_FORMAT) + relativedelta(days=1)).strftime(DEFAULT_SERVER_DATE_FORMAT)
                            list_date_by_pass.append((date_end_working_plus, timesheet_detail_effect_to))
                            
                            if self.compare_day(date, date_end_working) >= 0:
                                if context.get('return_boolean',False):
                                    return False
                                raise osv.except_osv('Validation Error !', 
                                             "You can't create/edit %s when detail timesheet already sent.\nPlease check again or contact to C&B for support" % model_name)
        
        return True
                        
    def check_if_date_after_summary_timesheet(self, cr, uid, employee_id, daterange, context=None):
        '''
        Dont allow to create/edit if date(of daterange) lower or equal to_date of latest generated timesheet detail(record ts.monthly at state draft/sent/approve
        input date may be just a date string or an array of date string.
        This function use to test employee timesheet and working schedule employee
        '''
        if not context:
            context = {}
        
        if not isinstance(daterange, list):
            daterange = [daterange]
            
        if employee_id and daterange:
            name_object = 'leave request'
            if context.get('name_object',False):
                name_object = context['name_object']
                
            monthly_obj = self.pool.get('vhr.ts.monthly')
            wr_obj = self.pool.get('vhr.working.record')
            monthly_ids = monthly_obj.search(cr, uid, [('employee_id','=',employee_id),
                                                       ('state','in',['draft','sent','approve','reject'])], context={'get_all': True}, limit=1, order='date desc')
            if monthly_ids:
                monthly = monthly_obj.browse(cr, uid, monthly_ids[0], fields_process=['timesheet_detail_id','is_last_payment'])
                timesheet_detail_effect_from = monthly.timesheet_detail_id and monthly.timesheet_detail_id.from_date or False
                timesheet_detail_effect_to = monthly.timesheet_detail_id and monthly.timesheet_detail_id.to_date or False
                is_last_payment = monthly.is_last_payment
                
                #Register before timesheet_detail.effect_to
                if not is_last_payment:
                    for date in daterange:
                        if self.compare_day(date, timesheet_detail_effect_to) >= 0:
                            if context.get('return_boolean',False):
                                return False
                            raise osv.except_osv('Validation Error !', "You can't create/edit %s when detail timesheet already created.\nPlease check again or contact to C&B for support" % name_object)
                elif is_last_payment:
                    #Case employee had been generated with type is_last_payment
                    #Read terminate change form code
                    change_form_terminated_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_master_data_dismiss_change_form_code') or ''
                    change_form_terminated_code = change_form_terminated_code.split(',')
                    change_form_ids = self.pool.get('vhr.change.form').search(cr, uid, [('code', 'in', change_form_terminated_code)],context=context)
                    
                    dismiss_wr_ids = wr_obj.search(cr, uid, [('employee_id','=',employee_id),
                                                             '|',('active','=',True),('active','=',False),
                                                             ('state', 'in', (False, 'finish')),
                                                             ('effect_from','>=',timesheet_detail_effect_from),
                                                             ('effect_from','<=', timesheet_detail_effect_to),
                                                             ('change_form_ids','in', change_form_ids)])
                    if dismiss_wr_ids:
                        dismiss_wr = wr_obj.read(cr, uid, dismiss_wr_ids[0], ['effect_from'])
                        date_end_working = dismiss_wr.get('effect_from')
                        for date in daterange:
                            if self.compare_day(date, date_end_working) >= 0:
                                if context.get('return_boolean',False):
                                    return False
                                raise osv.except_osv('Validation Error !', "You can't create/edit %s when detail timesheet already created.\nPlease check again or contact to C&B for support" % name_object)
        
        return True
    
    def create_data_monthly(self, cr, uid, record_id, vals, context=None):
        '''
        Create update data ts.monthly when new day line is create when that day is generated in ts.monthly at state draft
        Case: 1. dont have leave request on that day.
              2. Have leave request on that day
        '''
        if not context:
            context = {}
        if record_id and vals:
            record = self.browse(cr, uid, record_id)
            date = vals.get('date', False)
            employee_id = vals.get('employee_id',False)
            number_of_days_temp = vals.get('number_of_days_temp',0)
            if date:
                monthly_obj = self.pool.get('vhr.ts.monthly')
                shift_obj = self.pool.get('vhr.ts.working.shift')
                
                #Find record ts.monthly at date of employee
                monthly_ids = monthly_obj.search(cr, uid, [('employee_id','=',employee_id),('date','=',date)], context={'get_all': True})
                if monthly_ids:
                    monthlys = monthly_obj.browse(cr, uid, monthly_ids)
                    
                    data = monthly_obj.copy_data(cr, uid, monthlys[0].id, context=context)
                    holiday_status = record.holiday_id.state
                    holiday_name = record.holiday_id.holiday_status_id.code
                    if number_of_days_temp != 1:
                        holiday_name += '/2'
                    data['holiday_line_id'] = record_id
                    data['holiday_name'] = holiday_name
                    
                    shift_id = data.get('shift_id',False)
                    if shift_id:
                        shift = shift_obj.read(cr, uid, shift_id, ['code'])
                        data['shift_name'] = shift.get('code','')
                        data['name'] = data['shift_name']
                    
                    #is_offline=True==> name=holiday_name
                    if context.get('ignore_send', False) or holiday_status in  ['validate']:
                        data['name'] = holiday_name
                    
                    #Only agree with case have a leave request = 0.5 day
                    if monthlys[0].holiday_line_id and monthlys[0].holiday_line_id.number_of_days_temp == number_of_days_temp\
                      and number_of_days_temp == 0.5:
                        data['parking_coef'] = 0
                        if record.holiday_id.holiday_status_id.coefsal == 1:
                            coef = 1 * number_of_days_temp
                        else:
                            coef = 0
                        data['coef'] = coef
                        data['meal_coef'] = 0
                        
                        monthly_obj.create(cr, uid, data)
                        
                        vals = {'parking_coef':0, 'meal_coef':0,'shift_name': data['shift_name']}
                        if monthlys[0].coef == 1:
                            vals['coef'] = 0.5
                        else:
                            vals['coef'] = 0
                        monthly_obj.write(cr, uid, monthlys[0].id, vals)
                    elif not monthlys[0].holiday_line_id and len(monthlys) == 1:
                        if record.holiday_id.holiday_status_id.coefsal == 1:
                            coef = 1
                        else:
                            coef = 1 - number_of_days_temp
                        
                        if data['meal_coef']:
                            data['meal_coef'] = data['meal_coef'] - number_of_days_temp
                        data['coef'] = coef
                        if number_of_days_temp == 1 and data['parking_coef']:
                            data['parking_coef'] = 0
                        
                        monthly_obj.write(cr, uid, monthlys[0].id, data)
        
        return True
    
    def update_data_monthly(self, cr, uid, ids, context=None):
        '''
        Update when change status full/half day of holiday line.
        User can only change when only have 1 record ts.monthly at date of employee
        '''
        if ids:
            monthly_obj = self.pool.get('vhr.ts.monthly')
            wr_obj = self.pool.get('vhr.working.record')
            parameter_obj = self.pool.get('ir.config_parameter')
            change_form_obj = self.pool.get('vhr.change.form')
            shift_obj = self.pool.get('vhr.ts.working.shift')
            
            #Read terminate change form code
            change_form_terminated_code = parameter_obj.get_param(cr, uid, 'vhr_master_data_dismiss_change_form_code') or ''
            change_form_terminated_code = change_form_terminated_code.split(',')
            change_form_ids = change_form_obj.search(cr, uid, [('code', 'in', change_form_terminated_code)], context=context)
            
            for record in self.browse(cr, uid, ids, context):
                employee_id = record.employee_id and record.employee_id.id or False
                number_of_days_temp = record.number_of_days_temp
                date = record.date
                if employee_id and date:
                    is_parking = 0
                    is_meal = 0
                    one_day_before_date = datetime.strptime(date, DEFAULT_SERVER_DATE_FORMAT) - relativedelta(days=1)
                    one_day_before_date  = one_day_before_date.strftime(DEFAULT_SERVER_DATE_FORMAT)
                    wr_domain = [('employee_id', '=', employee_id),
                                 ('state', 'in', (False, 'finish')),
                                 '|', ('active', '=', False),
                                 ('active', '=', True),
                                 ('effect_from', '<=', date), '|', ('effect_to', '>=', one_day_before_date),
                                 ('effect_to', '=', False)]
                    if change_form_ids:
                        for change_form_id in change_form_ids:
                            wr_domain.append(('change_form_ids', '!=', change_form_id))

                    wr_ids = wr_obj.search(cr, uid, wr_domain)
                    for wr in wr_obj.browse(cr, uid, wr_ids, fields_process=['office_id_new','salary_setting_id_new']):
                        if wr.office_id_new:
                            if wr.office_id_new.is_parking:
                                is_parking += 1
                        if wr.salary_setting_id_new:
                            if wr.salary_setting_id_new.is_meal:
                                is_meal += 1
                                    
                    monthly_ids = monthly_obj.search(cr, uid, [('employee_id','=',employee_id),('date','=',date)], context={'get_all': True})
                    if len(monthly_ids) == 1:
                        data = monthly_obj.copy_data(cr, uid, monthly_ids[0], context=context)
                        
                        old_name = data.get('name',False)
                            
                        holiday_name = record.holiday_id.holiday_status_id.code
                        if number_of_days_temp != 1:
                            holiday_name += '/2'
                        data['holiday_line_id'] = record['id']
                        data['holiday_name'] = holiday_name
                        data['name'] = data['holiday_name']
                        
                        shift_id = data.get('shift_id',False)
                        if shift_id:
                            shift = shift_obj.read(cr, uid, shift_id, ['code'])
                            data['shift_name'] = shift.get('code','')
                            if old_name == data['shift_name']:
                                data['name'] = data['shift_name']
                        
                        if record.holiday_id.holiday_status_id.coefsal == 1:
                            coef = 1
                        else:
                            coef = 1 - number_of_days_temp
                        
                        data['meal_coef'] = 0
                        if is_meal:
                            data['meal_coef'] = 1 - number_of_days_temp
                        data['coef'] = coef
                        
                        data['parking_coef'] = 0
                        if is_parking and number_of_days_temp != 1:
                            data['parking_coef'] = 1
                            
                        monthly_obj.write(cr, uid, monthly_ids[0], data)
        
        return True
                        
    
    def delete_data_monthly(self, cr, uid, ids, context=None):
        '''
        delete data ts.monthly when a holiday day line is update/delete when that day is generated in ts.monthly at state draft
        '''
        if ids:
            monthly_obj = self.pool.get('vhr.ts.monthly')
            shift_obj = self.pool.get('vhr.ts.working.shift')
            wr_obj = self.pool.get('vhr.working.record')
            holiday_obj = self.pool.get('hr.holidays')
            parameter_obj = self.pool.get('ir.config_parameter')
            change_form_obj = self.pool.get('vhr.change.form')
            
            #Read terminate change form code
            change_form_terminated_code = parameter_obj.get_param(cr, uid, 'vhr_master_data_dismiss_change_form_code') or ''
            change_form_terminated_code = change_form_terminated_code.split(',')
            change_form_ids = change_form_obj.search(cr, uid, [('code', 'in', change_form_terminated_code)], context=context)
                
            for record in self.browse(cr, uid, ids):
                employee_id = record.employee_id and record.employee_id.id or False
                number_of_days_temp = record.number_of_days_temp
                date = record.date
                if employee_id and date:
                    monthly_ids = monthly_obj.search(cr, uid, [('employee_id','=',employee_id),('date','=',date)], context={'get_all': True})
                    if monthly_ids:
                        monthlys = monthly_obj.browse(cr, uid, monthly_ids)
                        
                        is_parking = 0
                        is_meal = 0
                        one_day_before_date = datetime.strptime(date, DEFAULT_SERVER_DATE_FORMAT) - relativedelta(days=1)
                        one_day_before_date  = one_day_before_date.strftime(DEFAULT_SERVER_DATE_FORMAT)
                        wr_domain = [('employee_id', '=', employee_id),
                                     ('state', 'in', (False, 'finish')),
                                     '|', ('active', '=', False),
                                     ('active', '=', True),
                                     ('effect_from', '<=', date), '|', ('effect_to', '>=', one_day_before_date),
                                     ('effect_to', '=', False)]
                        if change_form_ids:
                            for change_form_id in change_form_ids:
                                wr_domain.append(('change_form_ids', '!=', change_form_id))

                        wr_ids = wr_obj.search(cr, uid, wr_domain)
                        for wr in wr_obj.browse(cr, uid, wr_ids, fields_process=['office_id_new','salary_setting_id_new']):
                            if wr.office_id_new:
                                if wr.office_id_new.is_parking:
                                    is_parking += 1
                            if wr.salary_setting_id_new:
                                if wr.salary_setting_id_new.is_meal:
                                    is_meal += 1
                            
                        #Remove holiday data
                        if len(monthlys) == 1:
                            data = monthly_obj.copy_data(cr, uid, monthlys[0].id, context=context)
                            data['holiday_name'] = ''
                            data['holiday_line_id'] = False
                            if is_meal:
                                data['meal_coef'] = 1
                            else:
                                data['meal_coef'] = 0
                            
                            if is_parking:
                                data['parking_coef'] = 1
                            else:
                                data['parking_coef'] = 0
                            
                            shift_id = data.get('shift_id',False)
                            if shift_id:
                                shift = shift_obj.browse(cr, uid, shift_id, fields_process=['type_workday_id','code'])
                                data['coef'] = shift.type_workday_id and shift.type_workday_id.coef
                                data['name'] = shift.code
                            
                            monthly_obj.write(cr, uid, monthlys[0].id, data)
                        
                        elif len(monthlys) == 2:
                            delete_ids = monthly_obj.search(cr, uid, [('id','in',monthly_ids),
                                                                      ('holiday_line_id','=',record.id)], context={'get_all': True})
                            if delete_ids:
                                monthly_obj.unlink(cr, uid, delete_ids)
                            
                            remain_ids = [record_id for record_id in monthly_ids if record_id not in delete_ids]
                            data = {}
                            if remain_ids:
                                data = monthly_obj.copy_data(cr, uid, remain_ids[0], context=context)
                            
                            number_of_days_temp = 0
                            holiday_line_id = data.get('holiday_line_id',False)
                            holiday_line = False
                            if holiday_line_id:
                                holiday_line = self.browse(cr, uid, holiday_line_id)
                                number_of_days_temp = holiday_line.number_of_days_temp
                                
                            data['parking_coef'] = 0
                            if is_parking and number_of_days_temp != 1:
                                data['parking_coef'] = 1
                            
                            data['meal_coef'] = 0
                            shift_id = data.get('shift_id',False)
                            if shift_id:
                                shift = shift_obj.browse(cr, uid, shift_id, fields_process=['type_workday_id','name'])
                                data['coef'] = shift.type_workday_id and shift.type_workday_id.coef
                                
                                if is_meal:
                                    data['meal_coef'] = data['coef'] - number_of_days_temp
                                
                                if holiday_line and holiday_line.holiday_id.holiday_status_id.coefsal != 1:
                                    data['coef'] -= number_of_days_temp
                            
                            monthly_obj.write(cr, uid, remain_ids, data)
                            
        return True
                                
                            
                            
                
    
    def create(self, cr, uid, vals, context=None):
        if not context:
            context = {}
        try:
            if not vals.get('employee_id', False) and context.get('employee_id', False):
                vals['employee_id'] = context['employee_id']
            res = super(vhr_holiday_line, self).create(cr, uid, vals, context)
    
            if res:
                self.check_if_date_not_in_generated_monthly(cr, uid, vals.get('employee_id'), vals.get('date'), context)
                
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
            raise osv.except_osv('Validation Error !', error_message)
        
        
    def write(self, cr, uid, ids, vals, context=None):
        if not context:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]
        try:
            if not ids:
                return True
            
            if not vals.get('employee_id', False) and context.get('employee_id', False):
                vals['employee_id'] = context['employee_id']
            
            leave = self.read(cr, uid, ids[0], ['date'])
            date = leave.get('date',False)
            if not vals.get('date',False):
                vals['date'] = date
            
            res = super(vhr_holiday_line, self).write(cr, uid, ids, vals, context)
    
            if res:
                self.check_if_date_not_in_generated_monthly(cr, uid, vals.get('employee_id'), vals.get('date'), context)
                
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
            raise osv.except_osv('Validation Error !', error_message)
    

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        try:
            
            delete_ids = []
            for record in self.read(cr, uid, ids, ['employee_id','date']):
                employee_id = record.get('employee_id',False) and record['employee_id'][0]
                date = record.get('date',False)
                is_created_monthly = self.pool.get('vhr.ts.monthly').search(cr, uid, [('employee_id','=',employee_id),('date','=',date)])
                if is_created_monthly:
                    delete_ids.append(record['id'])
            if delete_ids:
                self.delete_data_monthly(cr, SUPERUSER_ID, delete_ids, context)
            
            return super(vhr_holiday_line, self).unlink(cr, uid, ids, context)
        
        except Exception as e:
            log.exception(e)
            error_message = ''
            try:
                error_message = e.message
                if not error_message:
                    error_message = e.value
            except:
                error_message = ""
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')



vhr_holiday_line()