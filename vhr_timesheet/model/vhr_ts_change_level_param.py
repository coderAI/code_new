# -*- coding: utf-8 -*-
from openerp.osv import osv, fields
from openerp.tools.translate import _


class vhr_ts_change_level_param(osv.osv):
    _name = 'vhr.ts.change.level.param'
    _description = 'VHR TS Change Level Parameter'

    _columns = {
        'name': fields.char('Name', size=128),
        'ts_gen_param_id': fields.many2one('vhr.ts.general.param', 'General Parameter'),
        'from_date': fields.integer('From Date'),
        'to_date': fields.integer('To Date'),
        'coef': fields.float('Coef', digits=(16, 2)),
        'description': fields.text('Description')
    }

    def _validation(self, from_date, to_date, coef):
        if from_date and from_date not in xrange(1, 32) \
                or to_date and to_date not in xrange(1, 32):
            raise osv.except_osv(_('Validation Error !'),
                                 _('(E) From Date and To Date must in range of [1-31]!'))
        if from_date and to_date:
            if from_date > to_date:
                raise osv.except_osv(_('Validation Error !'),
                                     _('(E) From Date must be less than To Date!'))
        if coef:
            if coef < 0 or coef > 1:
                raise osv.except_osv('Validation Error !',
                                     '(E) Coef must be in range of [0, 1]!')

    def create(self, cr, uid, vals, context=None):
        self._validation(vals.get('from_date'), vals.get('to_date'), vals.get('coef'))

        return super(vhr_ts_change_level_param, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        self._validation(vals.get('from_date'), vals.get('to_date'), vals.get('coef'))
        for record in self.browse(cr, uid, ids, context=context):
            if vals.get('from_date') and vals['from_date'] > record.to_date \
                    or vals.get('to_date') and vals['to_date'] < record.from_date:
                raise osv.except_osv(_('Validation Error !'),
                                     _('(E) From Date must be less than To Date!'))
        return super(vhr_ts_change_level_param, self).write(cr, uid, ids, vals, context=context)


vhr_ts_change_level_param()