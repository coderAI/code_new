from openerp.osv import osv, fields
import logging

log = logging.getLogger(__name__)


class vhr_send_email_liability_confirmation_wizard(osv.osv_memory):
    _name = 'vhr.send.email.liability.confirmation.wizard'

    def btn_send(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        liability_ids = context.get('active_ids', [])
        return self.pool['vhr.liability'].send_email(cr, uid, liability_ids, context=context)
