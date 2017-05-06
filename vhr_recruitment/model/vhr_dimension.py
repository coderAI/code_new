# -*- coding: utf-8 -*-

from openerp.osv import osv


class vhr_dimension(osv.osv):
    _inherit = 'vhr.dimension'

    def get_dimension_type_notify_change(self, cr, uid, context=None):
        lst_dimension_type = self.pool.get('ir.config_parameter').get_param(cr, uid, 'update_cache_dimension_type')
        if lst_dimension_type:
            lst_dimension_type = filter(None, map(lambda a: a and a.strip() or '', lst_dimension_type.split(',')))
            dimension_type_ids = self.pool.get('vhr.dimension.type').search(cr, uid,
                                                                            [('code', 'in', lst_dimension_type)], context=context)
            return dimension_type_ids
        return []

    def create(self, cr, uid, vals, context=None):
        res = super(vhr_dimension, self).create(cr, uid, vals, context=context)
        # notify change
        dimension_type_ids = self.get_dimension_type_notify_change(cr, uid)
        if vals.get('dimension_type_id') in dimension_type_ids and vals.get('active'):
            self.pool.get('vhr.recruitment.interface').notify_change(cr, uid, context=context)
        return res

    def write(self, cr, uid, ids, vals, context=None):
        res = super(vhr_dimension, self).write(cr, uid, ids, vals, context=context)
        # notify change
        dimension_type_ids = self.get_dimension_type_notify_change(cr, uid)
        current_dimension_type_ids = filter(None,
                                            map(lambda x: x and x.dimension_type_id and x.dimension_type_id.id or '',
                                                self.browse(cr, uid, ids, fields_process=['dimension_type_id'],
                                                            context=context)))
        is_dimension_to_notify_change = filter(lambda x: x in dimension_type_ids, current_dimension_type_ids)
        if vals.get('dimension_type_id') in dimension_type_ids or is_dimension_to_notify_change:
            self.pool.get('vhr.recruitment.interface').notify_change(cr, uid, context=context)
        return res

    def unlink(self, cr, uid, ids, context=None):
        res = super(vhr_dimension, self).unlink(cr, uid, ids, context=context)
        # notify change
        self.pool.get('vhr.recruitment.interface').notify_change(cr, uid, context=context)
        return res


vhr_dimension()