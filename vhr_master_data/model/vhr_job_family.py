# -*- coding: utf-8 -*-

import logging

from openerp.osv import osv, fields


log = logging.getLogger(__name__)


class vhr_job_family(osv.osv):
    _name = 'vhr.job.family'
    _description = 'VHR Job Family'

    _columns = {
        'code': fields.char('Code', size=64),
        'name': fields.char('Vietnamese Name', size=128),
        'name_en': fields.char('English Name', size=128),
        'track_id': fields.many2one('vhr.dimension', 'Track', ondelete='restrict', domain=[('dimension_type_id.code', '=', 'TRACK'), ('active','=',True)]),
        'effect_date': fields.date('Effect Date'),
        'description': fields.text('Description'),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'History',
                                      domain=[('object_id.model', '=', _name),
                                              ('field_id.name', 'not in', ['write_date', 'audit_log_ids'])]),
        'active': fields.boolean('Active')
    }

    _defaults = {
        'active': True
    }

    _unique_insensitive_constraints = [{'code': "Job Family's Code is already exist!"},
                                       {'name': "Job Family's Vietnamese Name is already exist!"}]

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        args_new = ['|', '|', ('name', operator, name), ('code', operator, name), ('name_en', operator, name)] + args
        ids = self.search(cr, uid, args_new)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(vhr_job_family, self).name_search(cr, uid, name, args, operator, context, limit)

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_job_family, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res

vhr_job_family()

