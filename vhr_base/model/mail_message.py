# -*- coding: utf-8 -*-

import logging

from openerp.osv import osv

log = logging.getLogger(__name__)


class mail_message(osv.osv):
    _inherit = 'mail.message'

    def _find_allowed_model_wise(self, cr, uid, doc_model, doc_dict, context=None):
        doc_ids = doc_dict.keys()
        allowed_doc_ids = self.pool[doc_model].search(cr, uid, [('id', 'in', doc_ids)], context=context)
        return set([message_id for allowed_doc_id in allowed_doc_ids if allowed_doc_id in doc_dict for message_id in
                    doc_dict[allowed_doc_id]])