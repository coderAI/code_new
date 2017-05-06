# -*- coding: utf-8 -*-

import logging

from openerp.osv import osv, fields


log = logging.getLogger(__name__)

class vhr_dimension_type(osv.osv):
    _name = 'vhr.dimension.type'
    _description = 'VHR Dimension Type'

    _columns = {
        'code': fields.char('Code', size=64),
        'name': fields.char('Name', size=128),
        'description': fields.text('Description'),
        'active': fields.boolean('Active'),
        'is_show_level': fields.boolean('Is Show Level'),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                          domain=[('object_id.model', '=', _name),
                                                  ('field_id.name', 'not in',
                                                   ['write_date', 'audit_log_ids'])]),
    }

    _defaults = {
        'active': True
    }

    _unique_insensitive_constraints = [{'code': "Dimension Type's code is already exist!"},
                                       {'name': "Dimension Type's name is already exist!"}]
    
    
    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        if context.get('code', False):
            args = [('code','=', context['code'])]
            
        args_new = ['|', ('name', operator, name), ('code', operator, name)] + args
        ids = self.search(cr, uid, args_new)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(vhr_dimension_type, self).name_search(cr, uid, name, args, operator, context, limit)

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_dimension_type, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res

vhr_dimension_type()