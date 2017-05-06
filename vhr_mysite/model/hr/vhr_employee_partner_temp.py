# -*- coding: utf-8 -*-

from openerp.osv import osv, fields


class vhr_employee_partner_temp(osv.osv):
    _name = 'vhr.employee.partner.temp'
    _columns = {
        'employee_temp_id': fields.many2one('vhr.employee.temp', 'Employee', ondelete='cascade'),
        'relation_partner_id': fields.many2one('vhr.employee.partner', 'Relation Partner'),
        #These fields are used to compare if have change data with data in employee
        
        'ep_name': fields.related('relation_partner_id', 'name', type="char", string="Ep name"),
        'ep_relationship_id': fields.related('relation_partner_id', 'relationship_id', type="many2one", relation="vhr.relationship.type", string="Pd Relationship Type"),
        'ep_mobile': fields.related('relation_partner_id', 'mobile', type="char", string="Ep mobile"),
        'ep_phone': fields.related('relation_partner_id', 'phone', type="char", string="Ep phone"),
        'ep_street': fields.related('relation_partner_id', 'street', type="char", string="Ep street"),
        'ep_city_id': fields.related('relation_partner_id', 'city_id', type="many2one", relation="res.city", string="Ep city"),
        'ep_district_id': fields.related('relation_partner_id', 'district_id', type="many2one", relation="res.district", string="Ep district"),
        'ep_is_emergency': fields.related('relation_partner_id', 'is_emergency', type="boolean", string="Ep is_emergency"),
        'ep_is_referee': fields.related('relation_partner_id', 'is_referee', type="boolean", string="Ep is_referee"),
        
        
        'name': fields.char('Name', size=128),
        'relationship_id': fields.many2one('vhr.relationship.type', 'Relationship Type'),
        'mobile': fields.char('Mobile', size=128),
        'phone': fields.char('Phone', size=128),
        'street': fields.char('Street', size=128),
        'city_id': fields.many2one('res.city', 'City'),
        'district_id': fields.many2one('res.district', 'District'),
        'is_emergency': fields.boolean('Emergency'),
        'is_referee': fields.boolean('Reference'),
        'active': fields.boolean('Active'),
        'origin_id': fields.integer('OID', readonly=True),
        'mode': fields.selection([('new', 'Tạo mới'), ('update', 'Cập nhật')], 'Request', readonly=True, required=True),
    }
    _defaults = {
        'is_emergency': False,
        'active': True
    }
    
    _order = "id desc"
