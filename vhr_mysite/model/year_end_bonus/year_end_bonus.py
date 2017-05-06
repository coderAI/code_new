# -*- coding: utf-8 -*-

from openerp.osv import osv, fields
from openerp import SUPERUSER_ID


class year_end_bonus(osv.osv):
    _name = "vhr.year.end.bonus"
    
    _columns = {
        'name': fields.char('Name'),
        'year': fields.char(string="Year"),
        'employee_id': fields.many2one('hr.employee', string="Employee"),
        'employee_code': fields.char('Employee Code'),
        'active': fields.boolean('Active'),
        'department_id': fields.many2one('hr.department', string="Department"),
        
        'gross_salary': fields.float('Gross Salary'),
        'total_bonus_income': fields.float('Total Bonus Income'),
        'salary13': fields.float('Salary 13'),
        'number_working_month13': fields.float('Number of Working Month 13'),
        
        'year_end_bonus': fields.float('Year End Bonus'),
        'number_working_month_year_end': fields.float('Number Working Month In Year'),
        'number_month_year_end_bonus': fields.float('Number of Bonus Month In Year'),
        'year_end_bonus2011': fields.float('Year End Bonus in 2011'),
        
        'bonus_money': fields.float('Bonus Money'),
        
        'total_sub': fields.float('Total Sub'),
        'pit': fields.float('Personal Income Tax'),
        'total_tax_income': fields.float('Total Tax Income'),
        'number_month_cal_tax': fields.float('Number of Month Calculate Tax'),
        'tax_income_avg': fields.float('Income Tax Average'),
        'pit_with_salary13_bonus': fields.float('PIT with Salary 13 Bonus'),
        'pit_not_salary13_bonus': fields.float('PIT without Salary 13 Bonus'),
        'pit_income': fields.float('PIT Income'),
        'other_sub': fields.float('Other Sub'),
        'advance_money': fields.float('Advance Money'),
        
        'total_net_take_home': fields.float('Total Net')
    }
    
    _defaults = {
        'active': True,
    }
    
    def create(self, cr, uid, values, context=None):
        if context is None:
            context = {}
        name = self.pool.get('ir.sequence').get(cr, uid, 'year.end.bonus')
        year = ''
        # Check year
        if values.get('year', False):
            year = values['year']
        name = name.replace('YEAR', year)

        # Check employee code for field employee_id and name
        if values.get('employee_code', False):
            code = values['employee_code']
            code = values['employee_code'] = code.upper()
            employee = self.pool['hr.employee'].get_emloyee_from_code(cr, uid, code, context=context)
            if employee:
                values.update({
                    'employee_id': employee.id,
                    'department_id': employee.department_id and employee.department_id.id or False
                })
                if employee.login:
                    code = code + '-' + employee.login
            else:
                values.update({
                    'active': False
                })
            name = name.replace(name[-5:], code)
        values.update({
            'name': name,
        })
        return super(year_end_bonus, self).create(cr, uid, values, context=context)
    
    def write(self, cr, uid, ids, values, context=None):
        if context is None:
            context = {}
        # Check employee code for field employee_id and name
        if values.get('employee_code', False):
            employee = self.pool['hr.employee'].get_emloyee_from_code(cr, uid, values['employee_code'], context=context)
            if employee:
                values.update({
                    'employee_id': employee.id,
                    'department_id': employee.department_id and employee.department_id.id or False
                })
            else:
                values.update({
                    'active': False
                })
                
        return super(year_end_bonus, self).write(cr, uid, ids, values, context=context)

    # Prevent user not in 
    def read(self, cr, uid, ids, fields=None, context=None, load='_classic_read'):
        if context is None:
            context = {}
        hr_emp_obj = self.pool['hr.employee']
        # Neu ko phai la admin va cung ko thuoc group payroll
        if uid != SUPERUSER_ID and not hr_emp_obj.check_group_payroll(cr, uid, context=context):
            emp_ids = hr_emp_obj.search(
                cr, uid, [['user_id', '=', uid]], context=context)
            # Tim kiem employee tuong ung, sau do tim nhung bonus_ids cua nguoi do
            if emp_ids:
                year_end_ids = self.search(cr, uid, [('employee_id', 'in', emp_ids)])
                if year_end_ids:
                    unexpected_ids = [_id for _id in ids if _id not in year_end_ids]
                    # nếu user cố tình đọc những bonus_ids ko thuộc quyền sở hữu của mình
                    if unexpected_ids:
                        return []
                    else:
                        return super(year_end_bonus, self).read(cr, uid, ids, fields=fields, context=context, load=load)
                else:
                    return []
            return []
        else:
            return super(year_end_bonus, self).read(cr, uid, ids, fields=fields, context=context, load=load)
        
