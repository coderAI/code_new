# -*-coding:utf-8-*-
from openerp.osv import osv, fields
import logging

log = logging.getLogger(__name__)


class vhr_close_reason(osv.osv):
    _name = 'vhr.close.reason'
    _description = 'VHR RR Close Reason'

    _columns = {
        'name': fields.char('Vietnamese Name', size=256),
        'name_en': fields.char('English Name', size=256),
        'code': fields.char('Code', size=256),
        'active': fields.boolean('Active'),
        'description': fields.text('Description'),
        'reason_type_id': fields.many2one('vhr.dimension', 'Close reason type', ondelete='restrict',
                                          domain=[('dimension_type_id.code', '=', 'CANCEL_OFFER_TYPE'), ('active', '=', True)]),

        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                         domain=[('object_id.model', '=', _name),
                                                 ('field_id.name', 'not in', ['write_date', 'audit_log_ids'])]),
        }

    _defaults = {
        'active': True,
    }

    _unique_insensitive_constraints = [{'code': "Recruitment Source's Code is already exist!"},
                                       {'name': "Recruitment Source's Vietnamese Name is already exist!"}]

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        args_new = ['|', '|', ('name', operator, name), ('code', operator, name), ('name_en', operator, name)] + args
        ids = self.search(cr, uid, args_new, context=context)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(vhr_close_reason, self).name_search(cr, uid, name, args, operator, context, limit)

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_close_reason, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res

vhr_close_reason()
