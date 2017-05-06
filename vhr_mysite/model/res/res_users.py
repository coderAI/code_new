# -*- coding: utf-8 -*-

from openerp.osv import osv
from openerp.osv import fields


class res_users(osv.osv):
    _inherit = 'res.users'
    
    _columns = {
        'allow_backend': fields.boolean('Allow Login Backen')
    }
    
    _defaults = {
        'allow_backend': False
    }
