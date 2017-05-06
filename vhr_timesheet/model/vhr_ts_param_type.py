# -*- coding: utf-8 -*-

import logging

from openerp.osv import osv, fields

log = logging.getLogger(__name__)


class vhr_ts_param_type(osv.osv):
    _name = 'vhr.ts.param.type'
    _description = 'VHR TS Parameter Type'
    _columns = {
        'code': fields.char('Code', size=64),
        'name': fields.char('Vietnamese Name', size=128),
        'name_en': fields.char('English Name', size=128),
        'group_id': fields.many2one('vhr.ts.param.type.group', 'Group', ondelete='restrict'),
        'description': fields.text('Description'),
        'active': fields.boolean('Active'),

        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                         domain=[('object_id.model', '=', _name),
                                                 ('field_id.name', 'not in', ['write_date', 'audit_log_ids'])]),

    }

    _defaults = {
        'active': True,
    }

    _unique_insensitive_constraints = [{'code': "Parameter Type's Code is already exist!"},
                                       {'name': "Parameter Type's Vietnamese Name is already exist!"}]

    def get_group_id(self, cr, uid, group_code, context=None):
        group_ids = self.pool.get('vhr.ts.param.type.group').search(cr, uid, [('code', '=', group_code)],
                                                                    context=context)
        if group_ids:
            return group_ids[0]
        return False

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        res = super(vhr_ts_param_type, self).default_get(cr, uid, fields, context=context)
        if context.get('param_type_group', False):
            group_code = context['param_type_group']
            res['group_id'] = self.get_group_id(cr, uid, group_code, context=context)
        return res

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}

        args_new = ['|', '|', ('name', operator, name), ('code', operator, name), ('name_en', operator, name)] + args

        if context.get('param_type_group', False):
            group_id = self.get_group_id(cr, uid, context['param_type_group'], context)
            args_new.append(('group_id', '=', group_id))

        ids = self.search(cr, uid, args_new)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(vhr_ts_param_type, self).name_search(cr, uid, name, args_new, operator, context, limit)

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_ts_param_type, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res


vhr_ts_param_type()