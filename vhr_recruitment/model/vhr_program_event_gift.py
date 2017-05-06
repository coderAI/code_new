# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields

log = logging.getLogger(__name__)


class vhr_program_event_gift(osv.osv):
    _name = 'vhr.program.event.gift'
    _description = 'VHR Program Event Gift'

    def _get_used_quantity(self, cr, uid, ids, fields, args, context=None):
        result = {}
        temp_applicant_obj = self.pool.get('vhr.temp.applicant')
        for item in self.read(cr, uid, ids, ['quantity', 'unlimited']):
            result[item['id']] = {"used": 0, "remain": 0}
            used_ids = temp_applicant_obj.search(cr, uid, [('gift_id', '=', item['id']), ('is_spin', '=', True)],
                                                 context=context)
            result[item['id']]['used'] = len(used_ids)
            if not item.get("unlimited", False) and item.get("quantity", 0) and item['quantity'] - len(used_ids) > 0:
                result[item['id']]['remain'] = item['quantity'] - len(used_ids)
        return result

    _columns = {
        'name': fields.char('Vietnamese Name', size=128),
        'name_en': fields.char('English Name', size=128),
        'event_id': fields.many2one('vhr.program.event', 'Program Event', ondelete='cascade'),
        'event_code': fields.related('event_id', 'code', type='char', string='Event Code'),
        'quantity': fields.integer('Quantity'),
        'unlimited': fields.boolean('Unlimited'),
        'used': fields.function(_get_used_quantity, type='integer', string='Used Quantity', multi="used"),
        'remain': fields.function(_get_used_quantity, type='integer', string='Remain', multi="used"),
        'is_lucky': fields.boolean("Lucky Gift"),
        'weight': fields.integer('Weight'),
        'description': fields.text('Description'),
        'active': fields.boolean('Active')
    }

    _defaults = {
        'active': True,
    }

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_program_event_gift, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res

vhr_program_event_gift()
