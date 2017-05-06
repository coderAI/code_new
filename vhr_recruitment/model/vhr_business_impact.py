# -*-coding:utf-8-*-
from openerp.osv import osv, fields
from openerp import SUPERUSER_ID


class vhr_business_impact(osv.osv):
    _name = "vhr.business.impact"
    
    _columns = {
        'name': fields.char('Name', size=256),
        'code': fields.char('Code', size=256),
        'active': fields.boolean('Active'),
    }
    
    _defaults = {
        'active': True
    }