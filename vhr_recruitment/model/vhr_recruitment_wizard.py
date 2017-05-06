# -*-coding:utf-8-*-
import logging
from openerp.osv import osv, fields
import simplejson as json
from lxml import etree
    
log = logging.getLogger(__name__)


class vhr_recruitment_wizard(osv.osv_memory):
    _name = "vhr.recruitment.wizard"
    _description = "VHR Recruitment Wizard"

    def func_update_payment(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]
        if context.get('active_ids', False):
            active_ids = context.get('active_ids', [])
            payment_obj = self.pool.get('vhr.erp.bonus.payment')
            for item in active_ids:
                payment_obj.update_erp_bonus_payment(cr, uid, item)
        return True

vhr_recruitment_wizard()
