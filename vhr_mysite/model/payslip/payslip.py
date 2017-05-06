# -*- coding: utf-8 -*-

from openerp.osv import osv, fields
from openerp import SUPERUSER_ID

    
class vhr_payslip(osv.osv):
    _name = "vhr.payslip"
    
    def _get_payslip_name_period(self, cr, uid, ids, field_name, arg, context=None):
        if context is None:
            context = {}
        res = {}
        for item in self.browse(cr, uid, ids, context=context):
            name = 'PAYSLIP-YEAR/MONTH-'
            period = ''

            if item.year and item.month:
                name = name.replace('YEAR', item.year)
                name = name.replace('MONTH', item.month)
                
                period = item.month + '/' + item.year
            if item.employee_id:
                code = item.employee_id.code or ''
                login = item.employee_id.login or ''
                name = name + code.upper() + (login and '-' + login.upper() or '')
            res[item.id] = {
                'name': name,
                'period': period
            }
        return res
    
    def _get_total_addition(self, cr, uid, ids, field_name, arg, context=None):
        if context is None:
            context = {}
        res = {}
        for item in self.browse(cr, uid, ids, context=context):
            res[item.id] = {
                'total_addition': item.meal_allowance +
                    item.parking_allowance +
                    item.holiday_bonus +
                    item.other_income +
                    item.overtime_pay +
                    item.performance_salary,
            }
        return res

    _columns = {
        'name': fields.function(_get_payslip_name_period, string='Name', type="char", multi="get_payslip_name_period"),
        'year': fields.char(string="Year"),
        'month': fields.char(string="Month"),
        'employee_id': fields.many2one('hr.employee', string="Employee"),
        'employee_code': fields.char('Employee Code'),
        'active': fields.boolean('Active'),
        'period': fields.function(_get_payslip_name_period, string='Period', type="char", multi="get_payslip_name_period"),
        
        'department_id': fields.many2one('hr.department', string="Department"),
        
        # basic information
        'gross_salary': fields.float('Gross Salary'),
        'prev_gross_salary': fields.float('Prev Gross Salary'),
        
        'basic_salary': fields.float('Basic Salary'),
        'prev_basic_salary': fields.float('Prev Basic Salary'),
        
        'allowance_salary': fields.float('Allowance Salary'),
        'prev_allowance_salary': fields.float('Prev Allowance Salary'),
        
        'allowance_special_salary': fields.float('Special Allowance Salary'),
        'prev_allowance_special_salary': fields.float('Prev Special Allowance Salary'),
        
        # in month information
        'standard_day': fields.float('Standard Day'),
        
        'actual_wds': fields.float('Actual Work Day'),
        'prev_actual_wds': fields.float('Prev Actual Work Day'),
        
        'unpaid_leave': fields.float('Unpaid Leave'),
        'paid_leave': fields.float('Paid Leave'),
        'leave_75_si': fields.float('Leave 70%'),
        'leave_100_si': fields.float('Leave 100%'),
        'ot_normal_day': fields.float('Normal OT Day'),
        'ot_normal_night': fields.float('Normal OT Night'),
        'ot_dayoff_day': fields.float('Day Off OT Day'),
        'ot_dayoff_night': fields.float('Day Off OT Night'),
        'ot_holiday_day': fields.float('Holiday OT Day'),
        'ot_holiday_money': fields.float('Holiday Money OT Day'),
        
        # Total income in month
        'total_gross_income': fields.float('Total Gross Income'),
        'actual_salary': fields.float('Actual Salary'),
        
        'actual_basic_salary': fields.float('Actual Basic Salary'),
        'prev_actual_basic_salary': fields.float('Prev Actual Basic Salary'),
        
        'actual_general_allowance': fields.float('Actual General Allowance'),
        'prev_actual_general_allowance': fields.float('Prev Actual General Allowance'),
        
        'actual_allowance_special_salary': fields.float('Actual Allowance Special Salary'),
        'meal_allowance': fields.float('Lunch Allowance'),
        'parking_allowance': fields.float('Packing Allowance'),
        'holiday_bonus': fields.float('Holiday Bonus'),
        'other_income': fields.float('Other Income'),
        'overtime_pay': fields.float('Overtime Salary'),
        'performance_salary': fields.float('Performance Salary'),
        'total_addition': fields.function(_get_total_addition, string='Total Addition', type="float", multi="total_addtion"),
        
        # Total sub
        'total_sub': fields.float('Total Sub'),
        'insurance_required': fields.float('Insurance Required'),
        'pit': fields.float('Personal Income Tax'),
        'other_tax_income': fields.float('Other Income Tax'),
        'meal_allowance_no_tax': fields.float('Meal Allowance no Tax'),
        'ot_money_no_tax': fields.float('OT Salary no Tax'),
        'self_deduction': fields.float('Self Deduction'),
        'dependent_deduction': fields.float('Dependent Deduction'),
        'taxable_income': fields.float('Taxable Income'),
        
        # NET Income
        'net_salary': fields.float('Net Salary'),
        'federation_fee': fields.float('Federation Fee'),
        'company_advance': fields.float('Company Advance'),
        'other_adjust': fields.float('Other Adjustment'),
        'advance_salary': fields.float('Salary Advance'),
        'remain_net_income': fields.float('Remain Net Income'),
        
        # Explain
        'explain1': fields.text('Other Explain 1'),
        'explain2': fields.text('Other Explain 2'),
        
        'v_bonus': fields.float('V Bonus'),
        'prev_v_bonus': fields.float('Prev V Bonus'),
        
        'actual_general_v_bonus': fields.float('Actual General V Bonus'),
        'prev_actual_general_v_bonus': fields.float('Prev Actual General V Bonus'),
        
        # Note
        'note': fields.text('Note'),
        
        # From date - To date
        'from_date': fields.date('From Date'),
        'to_date': fields.date('To Date'),
    }
    
    _defaults = {
        'active': True,
    }
    
    # Prevent user not in group payroll read the record
    def read(self, cr, uid, ids, fields=None, context=None, load='_classic_read'):
        if context is None:
            context = {}
        hr_emp_obj = self.pool['hr.employee']
        # Neu ko phai la admin va cung ko thuoc group payroll
        if uid != SUPERUSER_ID and not hr_emp_obj.check_group_payroll(cr, uid, context=context):
            emp_ids = hr_emp_obj.search(
                cr, uid, [['user_id', '=', uid]], context=context)
            # Tim kiem employee tuong ung, sau do tim nhung payslip cua nguoi do
            if emp_ids:
                payslip_ids = self.search(cr, uid, [('employee_id', 'in', emp_ids)])
                if payslip_ids:
                    unexpected_ids = [_id for _id in ids if _id not in payslip_ids]
                    # nếu user cố tình đọc những payslip ko thuộc quyền sở hữu của mình
                    if unexpected_ids:
                        return []
                    else:
                        return super(vhr_payslip, self).read(cr, uid, ids, fields=fields, context=context, load=load)
                else:
                    return []
            return []
        else:
            return super(vhr_payslip, self).read(cr, uid, ids, fields=fields, context=context, load=load)

    def get_employee_bank_number(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        for payslip in self.browse(cr, uid, ids, context=context):
            # Kiem tra bank account
            employee = payslip.employee_id or False
            if employee and employee.bank_ids:
                for account in employee.bank_ids:
                    if account.is_main:
                        return account.acc_number or ''
        return ''

    def get_employee_tax_number(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        for payslip in self.browse(cr, uid, ids, context=context):
            # Kiem tra ma so thue ca nhan
            employee = payslip.employee_id or False
            if employee and employee.personal_document:
                for document in employee.personal_document:
                    if document.document_type_id and document.document_type_id.code == 'TAXID':
                        return document.number or ''
        return ''

    def format_money(self, cr, uid, ids, money, context=None):
        if context is None:
            context = {}
        if money:
            return '{:,.0f}'.format(money)
        return money
    
    def format_number(self, cr, uid, ids, number, context=None):
        if context is None:
            context = {}
        if number:
            return '{:,.2f}'.format(number)
        return number