# -*- coding: utf-8 -*-

from openerp.osv import osv, fields
from datetime import datetime
from openerp.addons.vhr_mysite.controllers.main import Mysite

import logging

log = logging.getLogger(__name__)


class vhr_insurance_period(osv.osv):
    _name = 'vhr.insurance.period'
    _description = 'VHR Insurance Period'
    
    def _get_insurance_period_name(self, cr, uid, ids, field_name, arg, context=None):
        if context is None:
            context = {}
        res = {}
        
        for item in self.browse(cr, uid, ids, context=context):
            name = 'INS-PER-'
            from_date = item.from_date and datetime.strptime(item.from_date, '%Y-%m-%d').date() or ''
            to_date = item.to_date and datetime.strptime(item.to_date, '%Y-%m-%d').date() or ''

            name = name + str(from_date and from_date.year or '') + '-' + str(to_date and to_date.year or '')
            res[item.id] = {'name': name}
        return res
    
    _columns = {
        'name': fields.function(_get_insurance_period_name, string='Name', type="char", multi="insurance_name"),
        'from_date' : fields.date('From Date', required = True),
        'to_date' : fields.date('To Date', required = True),
        'note' : fields.text('Note'),
        'active': fields.boolean('Active', help='There is only one period is active at the moment'),
    }
    
    _defaults = {
        'active': True,
    }    
    _order = "from_date desc"

class vhr_insurance_registration(osv.osv):
    _name = 'vhr.insurance.registration'
    
    def _get_insurance_registration_name(self, cr, uid, ids, field_name, arg, context=None):
        if context is None:
            context = {}
        res = {}
        
        for item in self.browse(cr, uid, ids, context=context):
            name = 'INS-REG-'
            if item.employee_id:
                code = item.employee_id.code or ''
                login = item.employee_id.login or ''
                name = name + code.upper() + (login and '-' + login.upper() or '')
            res[item.id] = {'name': name}
        return res
    
    _columns = {
        'name': fields.function(_get_insurance_registration_name, string='Name', type="char", multi="insurance_registration_name"),
        'period_id': fields.many2one('vhr.insurance.period', 'Insurance Period', ondelete='restrict'),
        'employee_id' : fields.many2one('hr.employee', 'Employee', required=True),
        'family_ids': fields.one2many('vhr.insurance.employee.family', 'insurance_id', 'Buy for Family'),
        'is_buy': fields.boolean('Is Buy'),
        'active': fields.boolean('Active'),
    }
    
    _defaults = {
        'is_buy': False,
        'active': True
    }
    
    def create_update_reg(self, cr, uid, vals, emp_id, context=None):
        if context is None:
            context = {}
        # get current period
        ins_per_obj = self.pool['vhr.insurance.period']
        today = datetime.today().strftime('%Y-%m-%d')
        ins_per_ids = ins_per_obj.search(cr, uid, [('from_date', '<=', today),
                                                   ('to_date', '>=', today)])
        
        ins_reg_ids = self.search(cr, uid, [('employee_id', '=', emp_id),
                                            ('period_id', 'in', ins_per_ids)])
        if ins_reg_ids: # Update
            return self.write(cr, uid, ins_reg_ids, vals, context=context)
        else:
            return self.create(cr, uid, vals, context=context)

    def convert_date_email(self, cr, uid, ids, date):
        if date:
            date = datetime.strptime(date , '%Y-%m-%d')
            return date.strftime('%d-%m-%Y')
        return False

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        res = super(vhr_insurance_registration, self).create(cr, uid, vals, context=context)
        # Send email
        template_id = self.pool['ir.model.data'].xmlid_to_res_id(cr, uid, 'vhr_mysite.email_insurance_registration_complete')
        self.pool['email.template'].send_mail(
            cr, uid, template_id, res, force_send=True, raise_exception=False, context=context)
        log.info('Send email Insurance Registration Complete for : %s' % (vals.get('employee_id', False)))
        
        return res

    ''' RETURN OFFICIAL '''
    def check_contract_official(self, cr, uid, user_id, context=None):
        if not user_id:
            return False
        if context is None:
            context = {}
        contract_obj = self.pool['hr.contract']
        contract_type_obj = self.pool['hr.contract.type']
        
        # Get contract type Official
        official_type_ids = contract_type_obj.search(cr, uid, [('contract_type_group_id.is_offical', '=', True)])
        
        ins_reg = self.browse(cr, uid, user_id[0], context=context)
        if ins_reg:
            employee_id = ins_reg.employee_id and ins_reg.employee_id.id or False
            if employee_id:
                # Get current contract
                today = datetime.today().strftime('%Y-%m-%d')
                curent_contract_ids = contract_obj.search(
                    cr, uid,[('employee_id', '=', employee_id),
                             ('is_main', '=', True),
                             ('date_start', '<=', today),
                             ('state', '=', 'signed'),
                             # Get hop dong ko phai la fresher
                            ('type_id', 'in', official_type_ids),
                             '|', '|', ('liquidation_date', '>=', today),
                             '&', ('date_end', '>=', today), ('liquidation_date', '=', False),
                             '&', ('date_end', '=', False), ('liquidation_date', '=', False)
                             ], order='date_start desc')
                if curent_contract_ids:
                    return True # official = True
        return False # official = False

    ''' RETURN Collaborator 1'''
    def check_contract_collaborator_by_title(self, cr, uid, user_id, context=None):
        if not user_id:
            return False
        if context is None:
            context = {}
        ins_reg = self.browse(cr, uid, user_id[0], context=context)
        if ins_reg:
            employee = ins_reg.employee_id or False
            if employee and employee.title_id and employee.title_id.name == 'Collaborator 1':
                return True
        return False
        
class vhr_insurance_package(osv.osv):
    _name = "vhr.insurance.package"

    _columns = {
        'name' : fields.char('Name', size=255, required=True),
        'code' : fields.char('Code', size=255),
        'description':fields.text('Description'),
        'active': fields.boolean('Active'),
    }
    
    _defaults = {
        'active': True
    }


class vhr_insurance_employee_family(osv.osv):
    _name = "vhr.insurance.employee.family"

    _columns = {
        'insurance_id': fields.many2one('vhr.insurance.registration', 'Insurance Reg Code'),
        'name' : fields.char('Name', size=255, required=True),
        'id_number' : fields.char('ID Number',size=255, required=True),
        'birth_date':fields.date('Date of Birth'),
        'relation_id': fields.many2one('vhr.relationship.type', 'Relationship', ondelete="restrict"),
        'package_id':fields.many2one('vhr.insurance.package', 'Insurance Package', ondelete="restrict"),
    }
