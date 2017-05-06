# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields


log = logging.getLogger(__name__)

class vhr_erp_payment_time(osv.osv):
    _name = 'vhr.erp.payment.time'
    _description = 'VHR ERP Payment Time'

    _columns = {
        'name': fields.char('Name', size=128),
        'payment_time': fields.char('Payment Time', size=128),
        'period_days': fields.integer('Period Days'),
        'description': fields.text('Description'),
        'active': fields.boolean('Active'),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                         domain=[('object_id.model', '=', _name),
                                                 ('field_id.name', 'not in', ['write_date', 'audit_log_ids'])]),
    }
    
    _unique_insensitive_constraints = [{'name': "Payment time's name is already exist!"},
                                       {'payment_time': "Payment time is already exist!"}]
    _defaults = {
        'active': True,
    }
    
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_erp_payment_time, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res

vhr_erp_payment_time()
