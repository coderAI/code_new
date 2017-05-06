# -*- coding: utf-8 -*-

import logging

from openerp.osv import osv, fields


log = logging.getLogger(__name__)


class vhr_dimension(osv.osv):
    _name = 'vhr.dimension'
    _description = 'VHR Dimension'

    _columns = {
        'code': fields.char('Code', size=64),
        'name': fields.char('Vietnamese Name', size=128),
        'name_en': fields.char('English Name', size=128),
        'dimension_type_id': fields.many2one('vhr.dimension.type', 'Dimension Type', ondelete='restrict'),
        'level': fields.integer('Level'),
        'is_show_level': fields.related('dimension_type_id','is_show_level',type='boolean', string="Is Show Level"),
        'description': fields.text('Description'),
        'description_en': fields.text('English Description'),
        'is_published': fields.boolean('Published ?'),
        'active': fields.boolean('Active'),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'History', \
                                      domain=[('object_id.model', '=', _name),
                                              ('field_id.name', 'not in', ['write_date', 'audit_log_ids'])]),
    }

    _defaults = {
        'active': True
    }

    _unique_insensitive_constraints = [{'code': "Dimension's code and Dimension's Type are already exist!",
                                        'dimension_type_id': "Dimension's code and Dimension's Type are already exist!"},
                                       {'name': "Dimension's Vietnamese Name and Dimension's Type are already exist!",
                                        'dimension_type_id': "Dimension's Vietnamese Name and Dimension's Type are already exist!"}]

    def get_dimension_type_id(self, cr, uid, dimension_type, context=None):
        type_ids = self.pool.get('vhr.dimension.type').search(cr, uid, [('code', '=', dimension_type)], context=context)
        if type_ids:
            return type_ids[0]
        return False
    
    def onchange_dimension_type_id(self, cr, uid, ids, dimension_type_id, context=None):
        res = {'is_show_level': False}
        if dimension_type_id:
            dimension_info = self.pool.get('vhr.dimension.type').read(cr, uid, dimension_type_id, ['is_show_level'])
            res['is_show_level'] = dimension_info.get('is_show_level',False)
        
        return {'value': res}

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        res = super(vhr_dimension, self).default_get(cr, uid, fields, context=context)
        if context.get('dimension_type', False):
            dimension_type = context['dimension_type']
            res['dimension_type_id'] = self.get_dimension_type_id(cr, uid, dimension_type, context=context)
        return res

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        args_new = ['|', '|', ('name', operator, name), ('code', operator, name), ('name_en', operator, name)] + args
        ids = self.search(cr, uid, args_new)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        args.extend(self._get_domain_to_find_by_dimension_type_xml_id(
            cr, uid, context=context))
        return super(vhr_dimension, self).name_search(cr, uid, name, args, operator, context, limit)

    def create(self, cr, uid, values, context=None):
        if context is None:
            context = {}
        if context.get('dimension_type'):
            dimension_type = context['dimension_type']
            values['dimension_type_id'] = self.get_dimension_type_id(cr, uid, dimension_type, context=context)
        return super(vhr_dimension, self).create(cr, uid, values, context=context)

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_dimension, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res

    def _get_domain_to_find_by_dimension_type_xml_id(
            self, cr, uid, context=None):
        """
        :param cr:
        :param uid:
        :param context: context must have the key "search_by_type_xml_id" with value is a dictionary with 2 keys:
            module_name
            xml_id
        to get the object by function get_object_reference
        Example: in view file
        <field name="dimension_id"
        context="{'search_by_type_xml_id': {'module_name': 'vhr_master_data', 'xml_id': 'data_dimension_type_LOAN_TYPE'}}" />
        :return: list domain
        """
        if context is None:
            context = {}
        domain = []
        key_context = 'search_by_type_xml_id'
        if key_context in context and context[key_context]:
            module_name = context[key_context]['module_name']
            xml_id = context[key_context]['xml_id']
            type = self.pool['ir.model.data'].get_object_reference(
                cr, uid, module_name, xml_id)
            if type:
                domain.extend([
                    ('active', '=', True),
                    ('dimension_type_id', '=', type[1])
                ])
        return domain

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context = {}
        args.extend(self._get_domain_to_find_by_dimension_type_xml_id( cr, uid, context=context))
        return super(vhr_dimension, self).search(cr, uid, args, offset=offset,
                                                 limit=limit, order=order, context=context, count=count)

vhr_dimension()