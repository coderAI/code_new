# -*- coding: utf-8 -*-

import logging
import time

from openerp.osv import osv, fields
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT


log = logging.getLogger(__name__)


class vhr_company(osv.osv):
    _name = 'res.company'
    _inherit = 'res.company'

    _columns = {
        'name_en': fields.char('English Name', size=128),
        'suffix_email': fields.char('Suffix Email', size=128),
        'code': fields.char('Code', size=64),
        'description': fields.text('Description'),
        'active': fields.boolean('Active'),
        'ceo_id': fields.many2one('hr.employee', 'CEO', ondelete='restrict'),
        'office_id': fields.many2one('vhr.office', 'Head Office', domain=[('is_head_office', '=', True)],
                                     ondelete='restrict'),
        'com_group_id': fields.many2one('vhr.company.group', 'Company Group', ondelete='restrict'),
        'is_member': fields.boolean('Is member'),
        'city_id': fields.many2one('res.city', 'City', ondelete='restrict'),
        'district_id': fields.many2one('res.district', 'District', ondelete='restrict'),
        'authorization_date': fields.date('Authorization Date'),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                         domain=[('object_id.model', '=', _name),
                                                 ('field_id.name', 'not in',
                                                  ['write_date', 'audit_log_ids'])]),
        'sign_emp_id': fields.char('Signer', size=64),
        'job_title_id': fields.char("Signer's Title", size=128),
        'country_signer': fields.many2one('res.country', "Signer's Nationality"),
        'security_lead': fields.float(
            'Security Days',
            help="Margin of error for dates promised to customers. "\
                 "Products will be scheduled for procurement and delivery "\
                 "that many days earlier than the actual promised date, to "\
                 "cope with unexpected delays in the supply chain."),
        
        'establish_license': fields.text('Establish License'),
    }

    _order = "com_group_id"
    
    def _get_default_country_id(self, cr, uid, context=None):
        m = self.pool.get('ir.model.data')
        return m.get_object(cr, uid, 'base', 'vn').id

    _defaults = {
        'active': True,
        'is_member': True,
        'country_id': _get_default_country_id
    }

    _unique_insensitive_constraints = [{'code': "Company's Code is already exist!"},
                                       {'name': "Company's Vietnamese Name is already exist!"}]

    def find_and_check_is_member(self, cr, uid, context=None):
        try:
            ids = self.search(cr, uid, [('is_member', '=', False)])
            if ids:
                self.write(cr, uid, ids, {'is_member': True}, context)
        except Exception as e:
            log.info(e)
            return False
        return True

    def onchange_is_member(self, cr, uid, ids, is_member, context=None):
        res = {}
        if not is_member:
            res['parent_id'] = False

        return {'value': res}

    def create(self, cr, uid, vals, context=None):
        if not vals.get('partner_id'):
            partner_data = {
                'is_company': True,
                'image': vals.get('logo', False),
                'name': vals.get('name', False),
                'email': vals.get('email', False),
                'street': vals.get('street', False),
                'street2': vals.get('street2', False),
                'city': vals.get('city_id', False),
                'district_id': vals.get('district_id', False),
                'country_id': vals.get('country_id', False),
                'website': vals.get('website', False),
                'phone': vals.get('phone', False),
                'vat': vals.get('vat', False),
            }
            vals['partner_id'] = self.pool.get('res.partner').create(cr, uid, partner_data, context=context)
        if 'is_member' in vals and not vals['is_member']:
            self.find_and_check_is_member(cr, uid, context)
        return super(vhr_company, self).create(cr, uid, vals, context)

    def write(self, cr, uid, ids, vals, context=None):
        if 'is_member' in vals and not vals['is_member']:
            self.find_and_check_is_member(cr, uid, context)
        return super(vhr_company, self).write(cr, uid, ids, vals, context)

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}

        if context.get('employee_id', False):
            company_ids = self.get_company_ids(cr, uid, context['employee_id'], context)
            args.append(('id', 'in', company_ids))

        args_new = ['|', '|', ('name', operator, name), ('code', operator, name), ('name_en', operator, name)] + args
        ids = self.search(cr, uid, args_new, 0, None, None, context)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(vhr_company, self).name_search(cr, uid, name, args, operator, context, limit)

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if not context:
            context = {}

        return super(vhr_company, self).search(cr, uid, args, offset, limit, order, context, count)

        # get list company, employee belong to in contract

    def get_company_ids(self, cr, uid, employee_id, context=None):
        company_ids = []
        if employee_id:
            today = time.strftime(DEFAULT_SERVER_DATE_FORMAT)
            contract_obj = self.pool.get('hr.contract')
            # Get list contract of employee
            contract_ids = contract_obj.search(cr, uid, [('employee_id', '=', employee_id)])
            if contract_ids:
                contracts = contract_obj.read(cr, uid, contract_ids, ['company_id'], context=context)
                for contract in contracts:
                    company_id = contract.get('company_id', False) and contract['company_id'][0]
                    company_ids.append(company_id)

        return list(set(company_ids))

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_company, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res


vhr_company()