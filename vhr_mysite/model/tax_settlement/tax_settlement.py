# -*- coding: utf-8 -*-

from openerp.osv import osv, fields
import datetime

from openerp import SUPERUSER_ID


class tax_settlement_auth(osv.osv):
    _name = "vhr.tax.settlement.auth"
    
    def _get_tax_settlement_name(self, cr, uid, ids, field_name, arg, context=None):
        if context is None:
            context = {}
        res = {}
        for item in self.browse(cr, uid, ids, context=context):
            period = ''
            name = 'SETTLEMENT_AUTH-YEAR-'

            if item.year:
                name = name.replace('YEAR', item.year)
                
            if item.employee_id:
                code = item.employee_id.code or ''
                login = item.employee_id.login or ''
                name = name + code.upper() + (login and '-' + login.upper() or '')
            res[item.id] = {
                'name': name,
            }
        return res
    
    _columns = {
        'name': fields.function(_get_tax_settlement_name, string='Name', type="char", multi="tax_settlement_name"),
        'year': fields.char(string="Year"),
        'employee_id': fields.many2one('hr.employee', string="Employee"),
        'employee_code': fields.char('Employee Code'),
        'selection': fields.selection([('only_hrs', 'Only HRS'),
                                       ('not_over_10', 'Not Over 10m'),
                                       ('not_over_20', 'Not Over 20m'),
                                       ], 'Selection', select=True),
        'id_number': fields.char('ID Number'),
        'pit_number': fields.char('PIT Number'),
        'nation': fields.char('Nation'),
    }
    
    def create_update_tax_settlement(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        res = {}
        # Search tax settlement for selected year
        tax_ids = self.search(cr, uid, [('year', '=', vals.get('year')),
                                        ('employee_id', '=', vals.get('employee_id', ''))])
        if tax_ids:
            self.write(cr, uid, tax_ids, vals, context=context)
            tax_id = tax_ids[0]
        else:
            tax_id = self.create(cr, uid, vals, context=context)
        
        return ['vhr_mysite.report_tax_settlement_template', tax_id, vals.get('employee_code', 'Report')]

    def get_current_year(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        now = datetime.datetime.now()
        return now.year

class tax_settlement(osv.osv):
    _name = "vhr.tax.settlement"
    
    def _get_tax_settlement_name(self, cr, uid, ids, field_name, arg, context=None):
        if context is None:
            context = {}
        res = {}
        name = 'SETTLEMENT-YEAR-'
        for item in self.browse(cr, uid, ids, context=context):
            if item.year:
                name = name.replace('YEAR', item.year)
                
            if item.employee_id:
                code = item.employee_id.code or ''
                login = item.employee_id.login or ''
                name = name + code.upper() + (login and '-' + login.upper() or '')
            res[item.id] = {
                'name': name,
            }
        return res
    
    _columns = {
        'name': fields.function(_get_tax_settlement_name, string='Name', type="char", multi="tax_settlement_name"),
        'year': fields.char(string="Year"),
        'active': fields.boolean('Active'),
        'employee_id': fields.many2one('hr.employee', string="Employee"),
        'employee_code': fields.char('Employee Code'),
        'is_settlement_by_company': fields.boolean('Is Auth'),
        'year_total_income': fields.float('Total Income'),
        'year_total_income_sub_tax': fields.float('NET Total Income'),
        'year_temp_tax': fields.float('TEMP Total Income'),
        'no_month_family_sub': fields.float('No Month Family Sub'),
        'period_01': fields.float('Period 1'),
        'period_02': fields.float('Period 2'),
        'year_self_total_sub': fields.float('Total Self Deduction'),
        'year_total_tax_income': fields.float('Total Tax Income'),
        'tax_avg': fields.float('Average Tax'),
        'tax_avg_linear': fields.float('Average Linear Tax'),
        'year_tax': fields.float('Total Tax in Year'),
        'total_money_pay': fields.float('Total Addition Money Pay'),
        'total_money_return': fields.float('Total Return Money'),
        
        'total_deduction_tax': fields.float('Total Deduction Tax'),
        'cb_info': fields.text('C&B Info'),
        'dealine_update': fields.char('Deadline Update'),
        'month_update': fields.char('Month Update'),
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
            # Tim kiem employee tuong ung, sau do tim nhung tax_ids cua nguoi do
            if emp_ids:
                tax_ids = self.search(cr, uid, [('employee_id', 'in', emp_ids)])
                if tax_ids:
                    unexpected_ids = [_id for _id in ids if _id not in tax_ids]
                    # nếu user cố tình đọc những tax_ids ko thuộc quyền sở hữu của mình
                    if unexpected_ids:
                        return []
                    else:
                        return super(tax_settlement, self).read(cr, uid, ids, fields=fields, context=context, load=load)
                else:
                    return []
            return []
        else:
            return super(tax_settlement, self).read(cr, uid, ids, fields=fields, context=context, load=load)

    def _update_employee_values(self, cr, uid, values, context=None):
        if context is None:
            context = {}
        # Check employee code for field employee_id
        if values.get('employee_code', False):
            employee = self.pool['hr.employee'].get_emloyee_from_code(cr, uid, values['employee_code'], context=context)
            if employee:
                values.update({
                    'employee_id': employee.id
                })
            else:
                values.update({
                    'active': False,
                })
        return values

    def create(self, cr, uid, values, context=None):
        if context is None:
            context = {}
        values = self._update_employee_values(cr, uid, values, context)

        return super(tax_settlement, self).create(cr, uid, values, context=context)

    def write(self, cr, uid, ids, values, context=None):
        if context is None:
            context = {}
        values = self._update_employee_values(cr, uid, values, context)
                
        return super(tax_settlement, self).write(cr, uid, ids, values, context=context)
