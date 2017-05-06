# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields


log = logging.getLogger(__name__)


class vhr_bank_contract(osv.osv):
    _name = 'vhr.bank.contract'
    _description = 'VHR Bank Contract'
    
    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        res = super(vhr_bank_contract, self).default_get(cr, uid, fields, context=context)
        currency = self.pool.get('res.currency')
        ids = currency.search(cr, uid, [('name', '=', 'VND')])
        if ids and len(ids) == 1:
            res.update({'currency': ids[0]})
        return res
    
    _columns = {
        'name': fields.char('Name', size=128),
        'contract_id': fields.many2one('hr.contract', 'Contract'),
        'employee_id': fields.many2one('hr.employee', string='Partner'),
        'bank_id': fields.many2one('res.partner.bank', 'Bank', ondelete='restrict', domain="[('employee_id','=',employee_id)]"),
        'currency': fields.many2one('res.currency', 'Currency'),
        'weight': fields.float('Value'), #Change display name base new request of user
        'value_type': fields.selection([
            ('amount', 'Amount'),
            ('percent', 'Percent'),
        ], 'Type'),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                         domain=[('object_id.model', '=', _name),
                                                 ('field_id.name', 'not in',
                                                  ['write_date', 'audit_log_ids'])]),
    }

    _unique_insensitive_constraints = [{'bank_id': "Bank account must be unique per Contract!",
                                        'contract_id': "Bank account must be unique per Contract!"
                                        }]

    _defaults = {
        'value_type': 'percent',
        'weight': 100,
    }

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        args_new = [('name', operator, name)] + args
        ids = self.search(cr, uid, args_new)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(vhr_bank_contract, self).name_search(cr, uid, name, args, operator, context, limit)

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_bank_contract, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res


vhr_bank_contract()