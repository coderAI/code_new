# -*- coding: utf-8 -*-

import logging

from openerp.osv import osv, fields
from vhr_recruitment_abstract import vhr_recruitment_abstract, ADMIN


log = logging.getLogger(__name__)


class vhr_school(osv.osv,vhr_recruitment_abstract):
    _inherit = 'vhr.school'
    
    def _is_group_addmin_rr(self, cr, uid, ids, fields, args, context=None):
        result = {}
        if context is None:
            context = {}
        roles = self.recruitment_get_group_array(cr, uid, uid)
        current_emp = self.pool.get('hr.employee').search(cr, uid, [('user_id.id', '=', uid)], context={'active_test': False})
        if current_emp:
            for item in self.browse(cr, uid, ids, context=context):
                result[item.id] =  False
                if ADMIN in roles:
                    result[item.id] = True
        return result

    _columns = {
    
        'speciality_ids': fields.many2many('vhr.dimension','speciality_school_rel','speciality_id' ,'school_id','Speciality', domain=[('dimension_type_id.code','=','SPECIALITY')],),
        'is_group_addmin_rr': fields.function(_is_group_addmin_rr, type="boolean", string="Is Addmin"),

    }

    _defaults = {
      
    }
vhr_school()