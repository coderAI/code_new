# -*- coding: utf-8 -*-
import logging
from openerp.osv import osv, fields
from openerp.addons.vhr_common.model.vhr_common import vhr_common
from datetime import datetime
from lxml import etree
import simplejson as json


log = logging.getLogger(__name__)


class vhr_ts_overtime_summarize(osv.osv, vhr_common):
    _name = 'vhr.ts.overtime.summarize'
    
    def compute_total(self, cr, uid, ids, field_name, arg, context=None):
        res = {id: {'total_hours_register': 0, 'total_hours_approve': 0, 'compensation_leave': 0,
                    'total_ot_day_approve': 0, 'total_ot_night_approve': 0, 'ot_normal_days': 0,
                    'ot_days_off': 0, 'ot_holidays': 0,'total_hours_pay': 0} for id in ids}
        log.info('\n start compute_total in OT Summary--')
        for ot_sum in self.browse(cr, uid, ids):
            for ot_line in ot_sum.overtime_detail_ids:
                res[ot_sum.id]['total_hours_register'] += ot_line.total_hours_register
                if ot_line.state == 'finish':
                    res[ot_sum.id]['total_hours_approve']       += ot_line.total_hours_approve or 0
                    
                    if ot_line.is_compensation_leave:
                        total_ot_day_comp_result = ot_line.total_ot_day_approve * ot_line.day_coef_compensation or 0
                        
                        night_coef_compend = ot_line.day_coef_compensation + ot_line.night_coef_compensation + ot_line.day_coef_compensation * ot_line.allowance_night_coef_compensation
                        total_ot_night_comp_result = ot_line.total_ot_night_approve * night_coef_compend
                        res[ot_sum.id]['compensation_leave']       += total_ot_day_comp_result + total_ot_night_comp_result
                    else:
                        res[ot_sum.id]['total_hours_pay']       += ot_line.total_hours_approve or 0
                    
            res[ot_sum.id]['total_ot_day_approve']      += ot_sum.ot_normal_days_day + ot_sum.ot_days_off_day + ot_sum.ot_holidays_day
            res[ot_sum.id]['total_ot_night_approve']    += ot_sum.ot_normal_days_night + ot_sum.ot_days_off_night + ot_sum.ot_holidays_night
            
            res[ot_sum.id]['ot_normal_days']    += ot_sum.ot_normal_days_day + ot_sum.ot_normal_days_night
            res[ot_sum.id]['ot_days_off']    += ot_sum.ot_days_off_day + ot_sum.ot_days_off_night
            res[ot_sum.id]['ot_holidays']    += ot_sum.ot_holidays_day + ot_sum.ot_holidays_night
        
        log.info('\n end compute_total in OT Summary--')
        return res
                
        
        
        
    _columns = {
                'name': fields.char('Name', size=128),
                'employee_id': fields.many2one('hr.employee', 'Employee', ondelete='restrict'),
                'employee_code': fields.related('employee_id', 'code', type="char", string="Employee Code", store=True),
                'employee_login': fields.related('employee_id', 'login', type="char", string="Employee Domain"),
                'employee_name': fields.related('employee_id', 'name_related', type="char", string="Employee Name"),
                
                'department_id': fields.related('employee_id', 'department_id', type='many2one',
                                        relation='hr.department', string='Department', store=True),
                
                'company_id': fields.many2one('res.company', 'Company', ondelete='restrict'),
                'overtime_detail_ids': fields.one2many('vhr.ts.overtime.detail', 'overtime_sum_id', 
                                                    'Overtime Detail', ondelete = 'cascade'),                
                'date_from': fields.date('From Date'),
                'date_to': fields.date('To Date'),
                'is_saved': fields.boolean('Is Saved'),
                
                'total_hours_register': fields.function(compute_total, type='float', string="Total hours register",
                                      multi="compute_total", digits=(2, 1)),
                'total_hours_approve': fields.function(compute_total, type='float', string="Total hours approve",
                                      multi="compute_total", digits=(2, 1)),
                'compensation_leave': fields.function(compute_total, type='float', string="Compensation Leave Result (hours)",
                                      multi="compute_total", digits=(2, 1)),
                'total_hours_pay': fields.function(compute_total, type='float', string="Total Hours To Pay (hours)",
                                      multi="compute_total", digits=(2, 1)),
                
                'total_ot_day_approve': fields.function(compute_total, type='float', string="OT Days (hours)",
                                      multi="compute_total", digits=(2, 1)),
                'total_ot_night_approve': fields.function(compute_total, type='float', string="OT Nights (hours)",
                                      multi="compute_total", digits=(2, 1)),
                'ot_normal_days': fields.function(compute_total, type='float', string="OT Normal Days (hours)",
                                      multi="compute_total", digits=(2, 1)),
                'ot_days_off': fields.function(compute_total, type='float', string="OT Days Off (hours)",
                                      multi="compute_total", digits=(2, 1)),
                'ot_holidays': fields.function(compute_total, type='float', string="OT Holidays (hours)",
                                      multi="compute_total", digits=(2, 1)),
                
                'ot_normal_days_day': fields.float('OT Day In Normal Days (hours)', digits=(16, 2)),
                'ot_normal_days_day_result': fields.float('OT Day In Normal Days Result (hours)', digits=(16, 2)),
                
                'ot_normal_days_night': fields.float('OT Night In Normal Days (hours)', digits=(16, 2)),
                'ot_normal_days_night_result': fields.float('OT Night In Normal Days Result (hours)', digits=(16, 2)),
                
                'ot_days_off_day': fields.float('OT Day In Days Off (hours)', digits=(16, 2)),
                'ot_days_off_day_result': fields.float('OT Day In Days Off Result (hours)', digits=(16, 2)),
                
                'ot_days_off_night': fields.float('OT Night In Days Off (hours)', digits=(16, 2)),
                'ot_days_off_night_result': fields.float('OT Night In Days Off Result (hours)', digits=(16, 2)),
                
                'ot_holidays_day': fields.float('OT Day In Holidays (hours)', digits=(16, 2)),
                'ot_holidays_day_result': fields.float('OT Day In Holidays Result (hours)', digits=(16, 2)),
                
                'ot_holidays_night': fields.float('OT Night In Holidays (hours)', digits=(16, 2)),
                'ot_holidays_night_result': fields.float('OT Night In Holidays Result (hours)', digits=(16, 2)),
                
                #OT Money
                'ot_money_normal_days_day': fields.float('OT Day Money In Normal Days (hours)', digits=(16, 2)),
                'ot_money_normal_days_night': fields.float('OT Night Money In Normal Days (hours)', digits=(16, 2)),
                
                'ot_money_days_off_day': fields.float('OT Day Money In Days Off (hours)', digits=(16, 2)),
                'ot_money_days_off_night': fields.float('OT Night Money In Days Off (hours)', digits=(16, 2)),
                
                'ot_money_holidays_day': fields.float('OT Day Money In Holidays (hours)', digits=(16, 2)),
                'ot_money_holidays_night': fields.float('OT Night Money In Holidays (hours)', digits=(16, 2)),
                
                'month_ot': fields.selection([(1,'1'),(2,'2'),(3,'3'),(4,'4'),
                                            (5,'5'),(6,'6'),(7,'7'),(8,'8'),
                                            (9,'9'),(10,'10'),(11,'11'),(12,'12')], 'Month OT'),
                'year_ot': fields.integer('Year OT'),
                'month_pay_ot': fields.selection([(1,'1'),(2,'2'),(3,'3'),(4,'4'),
                                            (5,'5'),(6,'6'),(7,'7'),(8,'8'),
                                            (9,'9'),(10,'10'),(11,'11'),(12,'12')], 'Month Pay OT'),
                'year_pay_ot': fields.integer('Year Pay OT'),
                
                'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                         domain=[('object_id.model', '=', _name),
                                                 ('field_id.name', 'not in',
                                                  ['write_date', 'audit_log_ids'])]),
    }           
    
    _order = "year_ot desc, month_pay_ot desc"
    
    _defaults = {
        'total_hours_register': 0.00,
        'total_hours_approve': 0.00,
        'compensation_leave': 0.0,
        'total_ot_day_approve': 0.0,
        'total_ot_night_approve': 0.0,
        'ot_normal_days': 0.0,
        'ot_days_off': 0.0,
        'ot_holidays': 0.0,
    }
    
    
    def name_get(self, cr, uid, ids, context=None):
        if not ids or False in ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        reads = self.read(cr, uid, ids, ['employee_id'], context=context)
        res = []
        for record in reads:
            name = record.get('employee_id', False) and record['employee_id'][1]
            res.append((record['id'], name))
        return res
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        # Search rule for specific menu
        if not context:
            context = {}
        context['search_all_employee'] = True
        
        if context.get('filter_by_permission_ot_summarize',False):
            new_args = []   
            groups = self.pool.get('res.users').get_groups(cr, uid)
                
            if not set(['hrs_group_system','vhr_cb_timesheet','vhr_cnb_manager']).intersection(set(groups)):
                new_args = [('id','in',[])]
                args += new_args

        return super(vhr_ts_overtime_summarize, self).search(cr, uid, args, offset, limit, order, context, count)
    
    def onchange_year_pay_ot(self, cr, uid, ids, year, year_ot, context=None):
        res = {}
        warning = {}
        this_year = datetime.today().date().year
        if year and ( year < this_year - 100 or year > this_year + 100):
            res['year_pay_ot'] = year_ot
            warning = {
                            'title': 'Validation Error!',
                            'message' : "You have to input available Year Pay OT !"
                             }
        
        return {'value': res, 'warning': warning}
            
    #Calculate summarize info when have change value of detail line or delete detail line
    def calculate_value_from_overtime_detail(self, cr, uid, ids, context=None):
        if ids:
            if not isinstance(ids, list):
                ids = [ids]
                
            records = self.browse(cr, uid, ids)
            for record in records:
                
                details = record.overtime_detail_ids
                overtime_detail_ids, vals = self.compute_summary_data_from_overtime_details(cr, uid, record, details, {'re_calculate': True})
                
                self.write(cr, uid, record.id, vals)
        
        return True
    
        
    def compute_summary_data_from_overtime_details(self, cr, uid, ot_sum, details, context=None):
        """
        Return vals of ot summary to write
        If you want to recalculate info in ot_summarize set context['re_calculate'] = True
        Set context= {'re_calculate': True} to recalculate ot_sum from details
        """
        if not context:
            context = {}
        vals = {}
        overtime_detail_ids = []
        #Do not put overtime_detail_ids in this vals
        vals = {
                'ot_money_holidays_day' : ot_sum and ot_sum.ot_money_holidays_day or 0,
                'ot_money_holidays_night' : ot_sum and ot_sum.ot_money_holidays_night or 0,
                'ot_money_normal_days_day' : ot_sum and ot_sum.ot_money_normal_days_day or 0,
                'ot_money_normal_days_night' : ot_sum and ot_sum.ot_money_normal_days_night or 0,
                'ot_money_days_off_day' : ot_sum and ot_sum.ot_money_days_off_day or 0,
                'ot_money_days_off_night' : ot_sum and ot_sum.ot_money_days_off_night or 0,
                
#                 'ot_holidays': ot_sum and ot_sum.ot_holidays or 0,
                'ot_holidays_day' : ot_sum and ot_sum.ot_holidays_day or 0,
                'ot_holidays_day_result': ot_sum and ot_sum.ot_holidays_day_result or 0,
                'ot_holidays_night' : ot_sum and ot_sum.ot_holidays_night or 0,
                'ot_holidays_night_result': ot_sum and ot_sum.ot_holidays_night_result or 0,
                
#                 'ot_normal_days': ot_sum and ot_sum.ot_normal_days or 0,
                'ot_normal_days_day' : ot_sum and ot_sum.ot_normal_days_day or 0,
                'ot_normal_days_day_result': ot_sum and ot_sum.ot_normal_days_day_result or 0,
                'ot_normal_days_night' : ot_sum and ot_sum.ot_normal_days_night or 0,
                'ot_normal_days_night_result': ot_sum and ot_sum.ot_normal_days_night_result or 0,


#                 'ot_days_off': ot_sum and ot_sum.ot_days_off or 0,
                'ot_days_off_day' : ot_sum and ot_sum.ot_days_off_day or 0,
                'ot_days_off_day_result': ot_sum and ot_sum.ot_days_off_day_result or 0,
                'ot_days_off_night' : ot_sum and ot_sum.ot_days_off_night or 0,
                'ot_days_off_night_result': ot_sum and ot_sum.ot_days_off_night_result or 0,
                }
        
        if context.get('re_calculate', False):
            for key in vals.keys():
                vals[key] = 0
        if details:
            for detail in details:
                employee_id = detail.employee_id and detail.employee_id.id or False
#                 company_id = detail.company_id and detail.company_id.id or False
                date = detail.date_off
                is_compensation_leave = detail.is_compensation_leave
                day_coef = detail.day_coef or 0
                night_coef = detail.day_coef + detail.night_coef + detail.day_coef * detail.allowance_night_coef
#                 vals['total_hours_register'] += detail.total_hours_register
                if detail.state == 'finish':
#                     vals['total_hours_approve']  += detail.total_hours_approve or 0
#                     vals['total_ot_day_approve']         += detail.total_ot_day_approve or 0
#                     vals['total_ot_night_approve']       += detail.total_ot_night_approve or 0
                        
#                     total_hours_approve = detail.total_hours_approve or 0
                    total_ot_day_approve = detail.total_ot_day_approve or 0
                    total_ot_night_approve = detail.total_ot_night_approve or 0
                    total_ot_day_result = total_ot_day_approve* day_coef
                    total_ot_night_result = total_ot_night_approve* night_coef
                    
#                     total_ot_day_comp_result = total_ot_day_approve * detail.day_coef_compensation or 0
#                     total_ot_night_comp_result = total_ot_night_approve * detail.night_coef_compensation or 0
                    check = self.check_whether_day_is_weekday_or_off_day(cr, uid, employee_id, date, context)
                    if check == 1:
#                         vals['ot_holidays'] += total_hours_approve
                        vals['ot_holidays_day'] += total_ot_day_approve
                        vals['ot_holidays_night'] += total_ot_night_approve
                        vals['ot_holidays_day_result']   +=  total_ot_day_result
                        vals['ot_holidays_night_result'] +=  total_ot_night_result
                        if not detail.is_compensation_leave:
                            vals['ot_money_holidays_day'] += total_ot_day_approve
                            vals['ot_money_holidays_night'] += total_ot_night_approve
                            
                    elif check == 2:
#                         vals['ot_days_off'] += total_hours_approve
                        vals['ot_days_off_day'] += total_ot_day_approve
                        vals['ot_days_off_night'] += total_ot_night_approve
                        vals['ot_days_off_day_result']   +=  total_ot_day_result
                        vals['ot_days_off_night_result'] +=  total_ot_night_result
                        if not detail.is_compensation_leave:
                            vals['ot_money_days_off_day'] += total_ot_day_approve
                            vals['ot_money_days_off_night'] += total_ot_night_approve
                        
                    elif check == 3:
#                         vals['ot_normal_days'] += total_hours_approve
                        vals['ot_normal_days_day'] += total_ot_day_approve
                        vals['ot_normal_days_night'] += total_ot_night_approve
                        vals['ot_normal_days_day_result']   +=  total_ot_day_result
                        vals['ot_normal_days_night_result'] +=  total_ot_night_result
                        if not detail.is_compensation_leave:
                            vals['ot_money_normal_days_day'] += total_ot_day_approve
                            vals['ot_money_normal_days_night'] += total_ot_night_approve
                
                overtime_detail_ids.append(detail.id)
        
        return overtime_detail_ids, vals
    
    def add_new_ot_detail_into_ot_summary(self, cr, uid, ot_sum_id, ot_detail_ids, context=None):
        if ot_sum_id and ot_detail_ids:
            record = self.browse(cr, uid, ot_sum_id)
            ot_detail_pool = self.pool.get('vhr.ts.overtime.detail')
            detail_ids = ot_detail_pool.search(cr, uid, [('overtime_sum_id','=',ot_sum_id)])
            detail_ids += ot_detail_ids
            
            details = ot_detail_pool.browse(cr, uid, detail_ids)
            overtime_detail_ids, vals = self.compute_summary_data_from_overtime_details(cr, uid, record, details, {'re_calculate': True})
                    
            self.write(cr, uid, record.id, vals)
            ot_detail_pool.write(cr, uid, ot_detail_ids, {'overtime_sum_id': ot_sum_id}, {'update_from_ot_sum': True})
        
        return True
            
        
    def update_overtime_detail_ids(self, cr, uid, ids, context=None):
        '''
            Can only use it to migrate data, becase new rule for pay money check at datetime
        '''
        #Update summarize info when have new detail line link to it
        if ids:
            overtime_detail_pool = self.pool.get('vhr.ts.overtime.detail')
            records = self.browse(cr, uid, ids)
            for record in records:
                employee_id = record.employee_id and record.employee_id.id or False
#                 company_id = record.company_id and record.company_id.id or False
                date_from = record.date_from
                date_to = record.date_to
                
                #Type compensation, OT summary go with date_off
                detail_1_ids = overtime_detail_pool.search(cr, uid, [('employee_id','=',employee_id),
#                                                                      ('company_id','=',company_id),
                                                                    ('date_off','>=',date_from),
                                                                    ('date_off','<=',date_to),
                                                                    ('is_compensation_leave','=',True),
                                                                     ('overtime_sum_id','not in',[record.id])])
                
                #Type pay money, OT summary go with approve_date if approve date > date_off
                #                           go with date_off if date_off >= approve_date
                detail_2_ids = overtime_detail_pool.search(cr, uid, [('employee_id','=',employee_id),
#                                                                      ('company_id','=',company_id),
                                                                     ('overtime_sum_id','not in',[record.id]),
                                                                     ('is_compensation_leave','=',False),
                                                                    '|','|',
                                                                    
                                                                    #Compare with approve_date neu date_off duoi date_from cua timesheet period
                                                                    '&','&',('approve_date','>=',date_from),
                                                                            ('approve_date','<=',date_to),
                                                                            ('date_off','<',date_from),
                                                                            
                                                                            #Compare with date_off if approve_date not over timesheet period
                                                                    '&','&',('date_off','>=',date_from),
                                                                            ('date_off','<=',date_to),
                                                                            ('approve_date','<=',date_to),
                                                                            
                                                                    '&','&',('approve_date','=',False),
                                                                            ('date_off','>=',date_from),
                                                                            ('date_off','<=',date_to),
                                                                     ])
                detail_ids = detail_1_ids + detail_2_ids
                if detail_ids:
                    details = overtime_detail_pool.browse(cr, uid, detail_ids)
                    
                    overtime_detail_ids, vals = self.compute_summary_data_from_overtime_details(cr, uid, record, details, context)
                    
                    self.write(cr, uid, record.id, vals)
                    overtime_detail_pool.write(cr, uid, overtime_detail_ids, {'overtime_sum_id': record.id}, {'update_from_ot_sum': True})
        
        return True
    
    def check_whether_day_is_weekday_or_off_day(self, cr, uid, employee_id, date, context=None):
        """Determine date is holiday or days off or weeks day
        Return 1:  holidays
               2:  days off
               3:  week days
        """
        if employee_id and date:
            #Search if date if public holiday
            holiday_pool = self.pool.get('vhr.public.holidays')
            public_holiday_ids = holiday_pool.search(cr, uid, [
#                                                                ('company_id','=', company_id),
                                                               ('date','=',date)])
            
#             if not public_holiday_ids:
#                 #If company is member company, and we only config public holiday for parent company, search for parent company
#                 company_pool = self.pool.get('res.company')
#                 company_ids = company_pool.search(cr, uid, [('is_member','=',False)])
#                 if company_id not in company_ids:
#                     public_holiday_ids = holiday_pool.search(cr, uid, [('company_id','=', company_ids[0]),
#                                                                        ('date','=',date)])
            
            if public_holiday_ids:
                return 1
            else:
                detail_pool = self.pool.get('vhr.ts.overtime.detail')
                working_schedule_id, shift_id = detail_pool.get_working_schedule_and_shift_of_employee(cr, uid, employee_id, date, context)
                #If not shift_id, it's mean is day off
                if not shift_id:
                    return 2
                return 3
            
        return False
        
        
    def save_ot_summarize(self, cr, uid, ids, context=None):
        if ids:
            self.write(cr, uid, ids, {'is_saved': True})
        
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
                    
    

vhr_ts_overtime_summarize()