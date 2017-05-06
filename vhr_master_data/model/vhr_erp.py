# -*- coding: utf-8 -*-

import logging

from openerp.osv import osv, fields


log = logging.getLogger(__name__)


class vhr_erp(osv.osv):
    _name = 'vhr.erp'
    _description = 'VHR Erp'

    _columns = {
        'name': fields.char('Name', size=128),
        'job_level_id': fields.many2one('vhr.job.level', 'Job Level', ondelete='restrict'),
        'effect_date': fields.date('Effect Date'),
        'erp_detail_ids': fields.one2many('vhr.erp.detail', 'erp_id', 'ERP Detail', ),
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

    _unique_insensitive_constraints = [{'job_level_id': "Job level and Effect Date are already exist!",
                                        'effect_date': "Job level and Effect Date are already exist!"
                                        }]

    def name_get(self, cr, uid, ids, context=None):
        if not ids or False in ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        reads = self.read(cr, uid, ids, ['job_level_id'], context=context)
        res = []
        for record in reads:
            if 'job_level_id' in record and isinstance(record['job_level_id'], tuple):
                name = record['job_level_id'][1]
                res.append((record['id'], name))
        return res

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        args_new = ['|', ('name', operator, name)] + args
        ids = self.search(cr, uid, args_new)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(vhr_erp, self).name_search(cr, uid, name, args, operator, context, limit)

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_erp, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res

vhr_erp()