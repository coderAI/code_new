# -*- coding: utf-8 -*-

import logging
from datetime import datetime
from openerp.osv import osv, fields
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.addons.vhr_common.model.vhr_common import vhr_common

log = logging.getLogger(__name__)


class vhr_employee_partner(osv.osv, vhr_common):
    _name = 'vhr.employee.partner'
    _description = 'VHR Employee Partner'

    def _get_day_of_month(self, cr, uid, context=None):
        return (
            ('1', '01'), ('2', '02'), ('3', '03'), ('4', '04'),
            ('5', '05'), ('6', '06'), ('7', '07'), ('8', '08'),
            ('9', '09'), ('10', '10'), ('11', '11'), ('12', '12'),
            ('13', '13'), ('14', '14'), ('15', '15'), ('16', '16'),
            ('17', '17'), ('18', '18'), ('19', '19'), ('20', '20'),
            ('21', '21'), ('22', '22'), ('23', '23'), ('24', '24'),
            ('25', '25'), ('26', '26'), ('27', '27'), ('28', '28'),
            ('29', '29'), ('30', '30'), ('31', '31')
        )
        
    def _get_age(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if not ids:
            return True
        if not isinstance(ids, list):
            ids = [ids]
        
        today = datetime.today().date()
        current_year = today.year
        records = self.read(cr, uid, ids, ['year_of_birth'])
        for record in records:
            res[record.get('id', False)] = 0
            year = record.get('year_of_birth',current_year)
            if year:
                try:
                    year = int(year)
                    res[record.get('id', False)] = current_year - year
                except Exception as e:
                    res[record.get('id', False)] = 0
            
        return res

    _columns = {
        'employee_id': fields.many2one('hr.employee', 'Employee ID'),
        'relation_employee_id': fields.many2one('hr.employee', 'Employee'),
        'name': fields.char('Name', size=128),
        'mobile': fields.char('Mobile', size=128),
        'phone': fields.char('Phone', size=128),
        'status': fields.selection([('alive', 'Alive'), ('dead', 'Dead')], string="Status"),
        'identity_number': fields.char("Identity Number", size=128),
        'career_id': fields.many2one("vhr.dimension", "Career",
                                     domain=[('dimension_type_id.code', '=', 'CAREER'), ('active', '=', True)]),
        'working_place': fields.char("Working Place", size=128),
        'notes': fields.text("Notes"),
        'day_of_birth': fields.selection(_get_day_of_month, string="Day of Birth"),
        'month_of_birth': fields.selection([('1', '01'), ('2', '02'), ('3', '03'), ('4', '04'),
                                            ('5', '05'), ('6', '06'), ('7', '07'), ('8', '08'),
                                            ('9', '09'), ('10', '10'), ('11', '11'), ('12', '12')],
                                           string="Month of Birth"),
        'year_of_birth': fields.char("Year of Birth", size=64),
#         'age': fields.integer("Age"),
        'age': fields.function(_get_age, type='integer', string='Age'),
        'city_id': fields.many2one("res.city", "City"),
        'district_id': fields.many2one("res.district", "District"),
        'street': fields.char("Street", size=128),
        'use_parent_address': fields.boolean('Use Company Address'),

        'relationship_id': fields.many2one('vhr.relationship.type', 'Relationship'),
        'is_emergency': fields.boolean('Emergency'),
        'is_referee': fields.boolean('Reference'),
        'is_employee': fields.boolean('Is Employee?'),
        'active': fields.boolean('Active'),

        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                         domain=[('object_id.model', '=', _name),
                                                 ('field_id.name', 'not in',
                                                  ['write_date', 'audit_log_ids'])]),

    }
    _unique_insensitive_constraints = [{'employee_id': "This relation are already exist!",
                                        'name': "This relation are already exist!",
                                        'relationship_id': "This relation are already exist!",
                                        'mobile': "This relation are already exist!"}]
    _defaults = {
        'active': True,
        'status': 'alive'
    }
    
    def read(self, cr, user, ids, fields=None, context=None, load='_classic_read'):
        if not context:
            context = {}
        
        self.prevent_normal_emp_read_data_of_other_emp(cr, user, ids, [], [], [], context=context)
        
        res =  super(vhr_employee_partner, self).read(cr, user, ids, fields, context, load)
            
        return res
    
    # Pay attention when override onchange_birthday in res.partner
    def onchange_birthday(self, cr, uid, ids, day, month, year, context=None):
        res = self.pool.get('res.partner').onchange_birthday(cr, uid, ids, day, month, year, context)

        return res

    def onchange_employee(self, cr, uid, ids, relation_employee_id, is_employee, context=None):
        res = {'value': {}}
        if not is_employee:
            res['value']['relation_employee_id'] = False
        if relation_employee_id:
            address_home_id = self.pool.get('hr.employee').read(cr, uid, relation_employee_id, ['address_home_id'])
            address_home_id = address_home_id['address_home_id'] and address_home_id['address_home_id'][0] or False
            val = {'gender': False,
                   'identity_number': False,
                   'career_id': False,
                   'working_place': False,
                   'notes': False,
                   'day_of_birth': False,
                   'month_of_birth': False,
                   'year_of_birth': False,
                   'age': False,
                   'street': False,
                   'city_id': False,
                   'district_id': False,
                   'phone': False,
                   'mobile': False}

            partner = self.pool.get('res.partner').browse(cr, uid, address_home_id)
            val['name'] = partner.name or False
            val['gender'] = partner.gender or False
            val['identity_number'] = partner.identity_number or False
            val['career_id'] = partner.career_id and partner.career_id.id or False
            val['working_place'] = partner.working_place or False
            val['notes'] = partner.notes or False
            val['day_of_birth'] = partner.day_of_birth or False
            val['month_of_birth'] = partner.month_of_birth or False
            val['year_of_birth'] = partner.year_of_birth or False
            val['street'] = partner.street or False
            val['city_id'] = partner.city and partner.city.id or False
            val['district_id'] = partner.district_id and partner.district_id.id or False
            val['phone'] = partner.phone or False
            val['mobile'] = partner.mobile or False
            res['value'] = val

        return res

    def onchange_relationship_type_id(self, cr, uid, ids, relationship_type_id, context=None):
        res = {'gender': False}
        if relationship_type_id:
            relationship_type = self.pool.get('vhr.relationship.type').read(cr, uid, relationship_type_id, ['gender'])
            res['gender'] = relationship_type.get('gender', False)

        return {'value': res}

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if not context:
            context = {}

        return super(vhr_employee_partner, self).search(cr, uid, args, offset, limit, order, context, count)

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        try:
            return super(vhr_employee_partner, self).unlink(cr, uid, ids, context=context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')

    def create(self, cr, uid, vals, context=None):
        res = super(vhr_employee_partner, self).create(cr, uid, vals, context)
        if res:
            self.check_emergency_data(cr, uid, res, context)
        return res

    def write(self, cr, uid, ids, vals, context=None):
        res = super(vhr_employee_partner, self).write(cr, uid, ids, vals, context)
        if res:
            self.check_emergency_data(cr, uid, ids, context)
        return res

    # When is_mergency =True, at least one of these field must have data: phone','mobile','street','city_id','district_id
    def check_emergency_data(self, cr, uid, ids, context=None):
        if ids:
            if not isinstance(ids, list):
                ids = [ids]
            emp_partners = self.browse(cr, uid, ids,
                                       fields_process=['is_emergency', 'phone', 'mobile', 'street',
                                                       'city_id', 'district_id', 'name'])
            for emp_partner in emp_partners:
                if emp_partner.is_emergency and not emp_partner.phone and not emp_partner.mobile \
                        and not emp_partner.street and not emp_partner.city_id and not emp_partner.district_id:
                    raise osv.except_osv('Validation Error !',
                                         'You have to input one of these fields: Phone/ Mobile/ Address of Relation Partner: %s !' % emp_partner.name)
        return True


vhr_employee_partner()