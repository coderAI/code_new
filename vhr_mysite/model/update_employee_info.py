# -*- coding: utf-8 -*-

from openerp.osv import osv, fields
import logging

log = logging.getLogger(__name__)

    
class update_employee_info(osv.osv):
    _name = "vhr.update.employee.info"
    
    _columns = {
        'name': fields.char('Name'),
        'employee_id': fields.many2one('hr.employee', string="Employee"),
        'employee_code': fields.char('Employee Code'),
        
        'is_view': fields.boolean('Is Viewed'),
        'is_submit': fields.boolean('Is Submit'),
        
        'current_id_number': fields.char('Current ID Number'),
        'current_date_of_issued': fields.date('Current Date of issue'),
        'current_place_of_issued': fields.char('Current Place of issue'),
        'current_phone': fields.char('Current Phone Number'),
        'current_email': fields.char('Current email'),
        
        'new_id_number': fields.char('New ID Number'),
        'new_date_of_issued': fields.date('New Date of issue'),
        'new_place_of_issued': fields.char('New Place of issue'),
        'new_phone': fields.char('New Phone Number'),
        'new_email': fields.char('New email'),
    }

    def _get_emloyee_from_code(self, cr, uid, employee_code, context=None):
        if context is None:
            context = {}
        if employee_code:
            employee_code = employee_code.replace(" ", "")
            hr_employee = self.pool['hr.employee']
            resource_resource = self.pool['resource.resource']

            resource_ids = resource_resource.search(cr, uid, [('code', '=', employee_code),])
            if resource_ids:
                employee_ids = hr_employee.search(cr, uid, [('resource_id', '=', resource_ids[0])])
                if employee_ids:
                    employee = hr_employee.browse(cr, uid, employee_ids[0], context)
                    return employee
        return False

    def _check_update_info_exists(self, cr, uid, emloyee_code):
        update_ids = self.search(cr, uid, [('employee_code', '=', emloyee_code)])
        return update_ids
            
    def create_update_info(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        if vals and vals.get('employee_code'):
            # Check update info is exists or not
            update_ids = self._check_update_info_exists(cr, uid, vals['employee_code'])
            if update_ids:
                self.write(cr, uid, update_ids, vals, context=context)
                return update_ids
            else:
                employee = self._get_emloyee_from_code(cr, uid, vals['employee_code'], context=context)
                if employee:
                    vals.update({'employee_id': employee.id,
                                 'name': 'UPDATE-' + vals['employee_code']})
                    return [self.create(cr, uid, vals, context=context)]
        return []

    def cron_send_email_remind_update_employee_info(self, cr, uid, context=None):
        log.info('START send email remind update info')
        if context is None:
            context = {}
        hr_employee = self.pool['hr.employee']
        resource_resource = self.pool['resource.resource']
        email_template = self.pool['email.template']
        # Get employees are active
        resource_ids = resource_resource.search(cr, uid, [('active', '=', True)], context=context)
        # Get employee_ids have domain acc
        employee_ids = hr_employee.search(cr, uid, [('resource_id', 'in', resource_ids), ('user_id.login', '!=', None)], context=context)
        emp_update_ids = self.search_read(cr, uid, [('is_submit', '=', True)], ['employee_id'], context=context)
        emp_submit_ids = [emp_update_id['employee_id'][0] for emp_update_id in emp_update_ids]
        
        emp_not_submit_ids = list(set(employee_ids) - set(emp_submit_ids))
        
        template_id = self.pool['ir.model.data'].xmlid_to_res_id(cr, uid, 'vhr_mysite.email_remind_update_employee_info')
        for employee_id in emp_not_submit_ids:
            log.info('Send email remind update info to : %s' % (employee_id))
            email_template.send_mail(cr, uid, template_id, employee_id,
                                     force_send=False, raise_exception=False, context=context)
        
        log.info('END send email remind update info')
        return True

update_employee_info()
