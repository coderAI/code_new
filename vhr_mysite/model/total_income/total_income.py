# -*- coding: utf-8 -*-

from openerp.osv import osv, fields
from openerp import SUPERUSER_ID

    
class vhr_total_income(osv.osv):
    _name = "vhr.total.income"
    
    def _get_total(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = {
                'total_allowance': obj.bonus_tet +
                    obj.allowance_lunch +
                    obj.allowance_packing +
                    obj.allowance_petrol +
                    obj.allowance_duty +
                    obj.allowance_house_rent +
                    obj.allowance_other,
                'total_salary_by_work': obj.incentive +
                    obj.bonus_kpi,
                'total_benefit': obj.allowance_tel +
                    obj.allowance_taxi +
                    obj.allowance_team_building +
                    obj.allowance_party +
                    obj.insurance_compulsory +
                    obj.insurance_24h +
                    obj.insurance_health +
                    obj.yearly_health_check +
                    obj.gym_cost +
                    obj.benefit_training +
                    obj.total_leave_money,
                'total_support_benefit': obj.allowance_tel +
                    obj.allowance_taxi +
                    obj.allowance_team_building +
                    obj.allowance_party +
                    obj.insurance_compulsory,
                'total_health_benefit': obj.insurance_24h +
                    obj.insurance_health +
                    obj.yearly_health_check +
                    obj.gym_cost,
                'total_training_benefit': obj.benefit_training,
                'total_leave': obj.entitled_leave +
                    obj.entitled_leave_holiday,
                'total': obj.gross_salary +
                    obj.bonus_13 +
                    obj.bonus_tet +
                    obj.allowance_lunch +
                    obj.allowance_packing +
                    obj.allowance_petrol +
                    obj.allowance_duty +
                    obj.allowance_house_rent +
                    obj.allowance_other +
                    obj.incentive +
                    obj.bonus_kpi +
                    obj.total_from_esop,
                'total_allowance_actual': obj.bonus_tet_actual +
                    obj.allowance_lunch_actual +
                    obj.allowance_packing_actual +
                    obj.allowance_petrol_actual +
                    obj.allowance_duty_actual +
                    obj.allowance_house_rent_actual +
                    obj.allowance_other_actual,
                'total_salary_by_work_actual': obj.incentive_actual +
                    obj.bonus_kpi_actual,
                'total_benefit_actual': obj.allowance_tel_actual +
                    obj.allowance_taxi_actual +
                    obj.allowance_team_building_actual +
                    obj.allowance_party_actual +
                    obj.insurance_compulsory_actual +
                    obj.insurance_24h_actual +
                    obj.insurance_health_actual +
                    obj.yearly_health_check_actual +
                    obj.gym_cost_actual +
                    obj.benefit_training_actual +
                    obj.total_leave_money_actual,
                'total_support_benefit_actual': obj.allowance_tel_actual +
                    obj.allowance_taxi_actual +
                    obj.allowance_team_building_actual +
                    obj.allowance_party_actual +
                    obj.insurance_compulsory_actual,
                'total_health_benefit_actual': obj.insurance_24h_actual +
                    obj.insurance_health_actual +
                    obj.yearly_health_check_actual +
                    obj.gym_cost_actual,
                'total_training_benefit_actual': obj.benefit_training_actual,
                'total_leave_actual': obj.entitled_leave_actual +
                    obj.entitled_leave_holiday_actual,
                'total_actual': obj.gross_salary_actual +
                    obj.bonus_13_actual +
                    obj.bonus_tet_actual +
                    obj.allowance_lunch_actual +
                    obj.allowance_packing_actual +
                    obj.allowance_petrol_actual +
                    obj.allowance_duty_actual +
                    obj.allowance_house_rent_actual +
                    obj.allowance_other_actual +
                    obj.incentive_actual +
                    obj.bonus_kpi_actual +
                    obj.total_from_esop_actual,
            }
        return result
    
    _columns = {
        'name': fields.char('Name'),
        'period': fields.char(string="Period"),
        'employee_id': fields.many2one('hr.employee', string="Employee"),
        'employee_code': fields.char('Employee Code'),
        'active': fields.boolean('Active'),
        
        'gross_salary': fields.float('Gross Salary'),
        'gross_salary_actual': fields.float('Gross Salary Actual'),
        
        'bonus_13': fields.float('13th Bonus'),
        'bonus_13_actual': fields.float('13th Bonus Actual'),
        
        'bonus_tet': fields.float('Tet Bonus'),
        'bonus_tet_actual': fields.float('Tet Bonus Actual'),
        
        'incentive': fields.float('Incentive'),
        'incentive_actual': fields.float('Incentive Actual'),
        
        'bonus_kpi': fields.float('KPI Bonus'),
        'bonus_kpi_actual': fields.float('KPI Bonus Actual'),
        
        'allowance_lunch': fields.float('Lunch Allowance'),
        'allowance_lunch_actual': fields.float('Lunch Allowance Actual'),
        
        'allowance_packing': fields.float('Packing Allowance'),
        'allowance_packing_actual': fields.float('Packing Allowance Actual'),
        
        'allowance_petrol': fields.float('Petrol Allowance'),
        'allowance_petrol_actual': fields.float('Petrol Allowance Actual'),
        
        'allowance_duty': fields.float('Duty Allowance'),
        'allowance_duty_actual': fields.float('Duty Allowance Actual'),
        
        'allowance_house_rent': fields.float('House Rent Allowance'),
        'allowance_house_rent_actual': fields.float('House Rent Allowance Actual'),
        
        'allowance_tel': fields.float('Telephone Allowance'),
        'allowance_tel_actual': fields.float('Telephone Allowance Actual'),
        
        'allowance_taxi': fields.float('Taxi Allowance'),
        'allowance_taxi_actual': fields.float('Taxi Allowance Actual'),
        
        'allowance_team_building': fields.float('Team building Allowance'),
        'allowance_team_building_actual': fields.float('Team building Allowance Actual'),
        
        'allowance_party': fields.float('Party Allowance'),
        'allowance_party_actual': fields.float('Party Allowance Actual'),
        
        'allowance_other': fields.float('Other Allowance'),
        'allowance_other_actual': fields.float('Other Allowance Actual'),
        
        'total_esop': fields.integer('Total ESOP'),
        
        'total_esop_executable': fields.float('Total ESOP Executable'),
        'total_esop_executable_actual': fields.float('Total ESOP Executable Actual'),
        
        'insurance_compulsory': fields.float('Compulsory Social Insurance'),
        'insurance_compulsory_actual': fields.float('Compulsory Social Insurance Actual'),
        
        'insurance_24h': fields.float('24/24 Insurance'),
        'insurance_24h_actual': fields.float('24/24 Insurance Actual'),
        
        'insurance_health': fields.float('Health Insurance'),
        'insurance_health_actual': fields.float('Health Insurance Actual'),
        
        'yearly_health_check': fields.float('Yearly Health Check'),
        'yearly_health_check_actual': fields.float('Yearly Health Check Actual'),
        
        'gym_cost': fields.float('Gym Cost'),
        'gym_cost_actual': fields.float('Gym Cost Actual'),
        
        'benefit_training': fields.float('Training Benefit'),
        'benefit_training_actual': fields.float('Training Benefit Actual'),
        
        'entitled_leave': fields.float('Entitled Leave'),
        'entitled_leave_actual': fields.float('Entitled Leave Actual'),
        
        'entitled_leave_holiday': fields.float('Holiday Entitled Leave'),
        'entitled_leave_holiday_actual': fields.float('Holiday Entitled Leave Actual'),
        
        'entitled_leave_money': fields.float('Entitled Leave Money'),
        'entitled_leave_money_actual': fields.float('Entitled Leave Money Actual'),
        
        'entitled_leave_holiday_money': fields.float('Holiday Entitled Leave Money'),
        'entitled_leave_holiday_money_actual': fields.float('Holiday Entitled Leave Money Actual'),
        
        'total_allowance': fields.function(_get_total, string='Total Allowance', type='float', multi='_get_total'),
        'total_allowance_actual': fields.function(_get_total, string='Total Allowance Actual', type='float', multi='_get_total'),
        
        'total_salary_by_work': fields.function(_get_total, string='Total Salary by Working', type='float', multi='_get_total'),
        'total_salary_by_work_actual': fields.function(_get_total, string='Total Salary by Working Actual', type='float', multi='_get_total'),
        
        'total_from_esop': fields.float(string='Total by ESOP'),
        'total_from_esop_actual': fields.float(string='Total by ESOP Actual'),
        
        'total_benefit': fields.function(_get_total, string='Total Benefit', type='float', multi='_get_total'),
        'total_benefit_actual': fields.function(_get_total, string='Total Benefit Actual', type='float', multi='_get_total'),
        
        'total_support_benefit': fields.function(_get_total, string='Total Support Benefit', type='float', multi='_get_total'),
        'total_support_benefit_actual': fields.function(_get_total, string='Total Support Benefit Actual', type='float', multi='_get_total'),
        
        'total_health_benefit': fields.function(_get_total, string='Total Health Benefit', type='float', multi='_get_total'),
        'total_health_benefit_actual': fields.function(_get_total, string='Total Health Benefit Actual', type='float', multi='_get_total'),
        
        'total_training_benefit': fields.function(_get_total, string='Total Training Benefit', type='float', multi='_get_total'),
        'total_training_benefit_actual': fields.function(_get_total, string='Total Training Benefit Actual', type='float', multi='_get_total'),
        
        'total_leave': fields.function(_get_total, string='Total Leave', type='float', multi='_get_total'),
        'total_leave_actual': fields.function(_get_total, string='Total Leave Actual', type='float', multi='_get_total'),
        
        'total_leave_money': fields.float(string='Total Leave Money'),
        'total_leave_money_actual': fields.float(string='Total Leave Money Actual'),
        
        'total': fields.function(_get_total, string='Total', type='float', multi='_get_total'),
        'total_actual': fields.function(_get_total, string='Total Actual', type='float', multi='_get_total'),
    }
    
    _defaults = {
        'active': True,
        'gross_salary': 0,
        'bonus_13': 0,
        'bonus_tet': 0,
        'incentive': 0,
        'bonus_kpi': 0,
        'allowance_lunch': 0,
        'allowance_packing': 0,
        'allowance_petrol': 0,
        'allowance_duty': 0,
        'allowance_house_rent': 0,
        'allowance_tel': 0,
        'allowance_taxi': 0,
        'allowance_team_building': 0,
        'allowance_party': 0,
        'allowance_other': 0,
        'total_esop': 0,
        'total_esop_executable': 0,
        'insurance_compulsory': 0,
        'insurance_24h': 0,
        'insurance_health': 0,
        'yearly_health_check': 0,
        'gym_cost': 0,
        'benefit_training': 0,
        'entitled_leave': 0,
        'entitled_leave_holiday': 0,
    }
    
    def create(self, cr, uid, values, context=None):
        if context is None:
            context = {}
        name = self.pool.get('ir.sequence').get(cr, uid, 'total.income')
        period = ''
        # Check period
        if values.get('period', False):
            period = values['period']
            name = name.replace('PERIOD', period)

        # Check employee code for field employee_id and name
        if values.get('employee_code', False):
            code = values['employee_code']
            employee = self.pool['hr.employee'].get_emloyee_from_code(cr, uid, code, context=context)
            if employee:
                values.update({
                    'employee_id': employee.id
                })
                if employee.login:
                    code = code + '-' + employee.login
            else:
                values.update({
                    'active': False
                })
            name = name.replace(name[-5:], code.upper())
        values.update({
            'name': name,
            'period': period,
        })
        return super(vhr_total_income, self).create(cr, uid, values, context=context)
    
    def write(self, cr, uid, ids, values, context=None):
        if context is None:
            context = {}
        # Check employee code for field employee_id and name
        if values.get('employee_code', False):
            employee = self.pool['hr.employee'].get_emloyee_from_code(cr, uid, values['employee_code'], context=context)
            if employee:
                values.update({
                    'employee_id': employee.id
                })
            else:
                values.update({
                    'active': False
                })
                
        return super(vhr_total_income, self).write(cr, uid, ids, values, context=context)

    # Prevent user not in group payroll read the records
    def read(self, cr, uid, ids, fields=None, context=None, load='_classic_read'):
        if context is None:
            context = {}
        hr_emp_obj = self.pool['hr.employee']
        # Neu ko phai la admin va cung ko thuoc group payroll
        if uid != SUPERUSER_ID and not hr_emp_obj.check_group_payroll(cr, uid, context=context):
            emp_ids = hr_emp_obj.search(
                cr, uid, [['user_id', '=', uid]], context=context)
            # Tim kiem employee tuong ung, sau do tim nhung total_income_ids cua nguoi do
            if emp_ids:
                total_income_ids = self.search(cr, uid, [('employee_id', 'in', emp_ids)])
                if total_income_ids:
                    unexpected_ids = [_id for _id in ids if _id not in total_income_ids]
                    # nếu user cố tình đọc những total_income_ids ko thuộc quyền sở hữu của mình
                    if unexpected_ids:
                        return []
                    else:
                        return super(vhr_total_income, self).read(cr, uid, ids, fields=fields, context=context, load=load)
                else:
                    return []
            return []
        else:
            return super(vhr_total_income, self).read(cr, uid, ids, fields=fields, context=context, load=load)
