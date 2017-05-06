# -*- coding: utf-8 -*-

import logging

from openerp.osv import osv, fields


log = logging.getLogger(__name__)


class vhr_job_level_position_class(osv.osv):
    _name = 'vhr.job.level.position.class'
    _description = 'VHR Job Level - Position Class'

    _columns = {
        'job_level_id': fields.many2one('vhr.job.level', 'Job Level', ondelete='restrict'),
        'position_class_from': fields.many2one('vhr.position.class', 'Position Class From', ondelete='restrict'),
        'position_class_to': fields.many2one('vhr.position.class', 'Position Class To', ondelete='restrict'),
        'effect_date': fields.date('Effect Date'),
        'description': fields.text('Description'),
        'active': fields.boolean('Active'),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                          domain=[('object_id.model', '=', _name),
                                                  ('field_id.name', 'not in',
                                                   ['write_date', 'audit_log_ids'])]),
    }

    _defaults = {
        'active': True
    }

    _unique_insensitive_constraints = [{'job_level_id': "Job Level and Effect Date are already exist!",
                                        'effect_date': "Job Level and Effect Date are already exist!"}]

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        args_new = args
        ids = self.search(cr, uid, args_new)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(vhr_job_level_position_class, self).name_search(cr, uid, name, args, operator, context, limit)

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_job_level_position_class, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res

vhr_job_level_position_class()