# -*- coding: utf-8 -*-

import logging

from openerp.osv import osv, fields


log = logging.getLogger(__name__)


class vhr_recruitment_degree(osv.osv):
    _name = 'hr.recruitment.degree'
    _inherit = 'hr.recruitment.degree'

    _columns = {
        'name_en': fields.char('English Name', size=128),
        'code': fields.char('Code', size=64),
        'active': fields.boolean('Active'),
        'certificate_type': fields.selection([('degree', 'Degree'), ('certificate', 'Certificate')], 'Type'),
        'description': fields.text('Description'),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                          domain=[('object_id.model', '=', _name),
                                                  ('field_id.name', 'not in',
                                                   ['write_date', 'audit_log_ids'])]),
    }

    _defaults = {
        'active': True,
        'certificate_type': 'degree'
    }
    _unique_insensitive_constraints = [{'code': "Degree's Code is already exist!"},
                                       {'name': "Degree's Vietnamese Name is already exist!"}]

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        args_new = ['|', '|', ('name', operator, name), ('code', operator, name), ('name_en', operator, name)] + args
        ids = self.search(cr, uid, args_new)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(vhr_recruitment_degree, self).name_search(cr, uid, name, args, operator, context, limit)

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_recruitment_degree, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res


vhr_recruitment_degree()