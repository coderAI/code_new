# -*- coding: utf-8 -*-

import logging

from openerp.osv import osv, fields


log = logging.getLogger(__name__)


class vhr_erp_detail(osv.osv):
    _name = 'vhr.erp.detail'
    _description = 'VHR Erp Detail'

    _columns = {
                'name': fields.char('Name', size=128),
                'amount': fields.float('Amount'),
                'erp_payment_time_id': fields.many2one('vhr.dimension', 'Payment Time', ondelete='restrict', domain=[('dimension_type_id.code', '=', 'ERP_PAYMENT_TIME'), ('active','=',True)]),
                'num_of_day': fields.integer('Num Of Day'),
                'erp_id': fields.many2one('vhr.erp', 'ERP', ondelete='restrict'),
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

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        args_new = ['|', ('name', operator, name)] + args
        ids = self.search(cr, uid, args_new)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(vhr_erp_detail, self).name_search(cr, uid, name, args, operator, context, limit)

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_erp_detail, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res

vhr_erp_detail()