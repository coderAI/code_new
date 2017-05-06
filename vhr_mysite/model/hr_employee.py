# -*- coding: utf-8 -*-

from openerp.osv import osv, fields
from datetime import datetime


class hr_employee(osv.osv):
    _inherit = 'hr.employee'
    _columns = {
        'website_published': fields.boolean('Available in the website'),
        'public_info': fields.text('Public Info'),
    }
    _defaults = {
        'website_published': True
    }
    
    def get_today_email(self, cr, uid, context=None):
        if context is None:
            context = {}
        return datetime.today().strftime("%d/%m/%Y")

    '''
    Check group C&B Payroll
    '''
    def check_group_payroll(self, cr, uid, context=None):
        if context is None:
            context = {}
        res_group_obj = self.pool['res.groups']
        model_data_obj = self.pool['ir.model.data']
        payroll_group_id = model_data_obj.xmlid_to_res_id(
            cr, uid, 'vhr_payroll.vhr_cnb_payroll')
        
        if payroll_group_id:
            payroll_group = res_group_obj.read(cr, uid, payroll_group_id, ['users'], context=context)
            if payroll_group and uid in payroll_group.get('users', []):
                return True
        return False

    '''
    Get Employee from code
    '''
    def get_emloyee_from_code(self, cr, uid, employee_code, context=None):
        if context is None:
            context = {}
        if employee_code:
            employee_code = employee_code.replace(" ", "")
            resource_resource = self.pool['resource.resource']

            resource_ids = resource_resource.search(cr, uid, [('code', '=', employee_code),])
            if resource_ids:
                employee_ids = self.search(cr, uid, [('resource_id', '=', resource_ids[0])])
                if employee_ids:
                    employee = self.browse(cr, uid, employee_ids[0], context)
                    return employee
        return False

    ''' CHECK ZALO Group'''
    def _check_zalo_group(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        employee_ids = self.search(
            cr, uid, [('user_id', '=', uid)], context=context)
        if employee_ids:
            hr_dept_obj = self.pool['hr.department']
            zalo_ids = hr_dept_obj.search(cr, uid, [['organization_class_id', 'in', [2, 5]], ['code', '=', 'Zalo']])
            employee = self.browse(cr, uid, employee_ids[0])
            if employee.division_id and employee.division_id.id in zalo_ids:
                return True
        return False
