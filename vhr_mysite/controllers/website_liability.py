# -*- coding: utf-8 -*-
import logging

from openerp import http
from openerp.addons.web import http
from openerp.addons.web.http import request
from datetime import datetime
import time
import ast
import json
import werkzeug.utils

log = logging.getLogger(__name__)

class website_liability_controller(http.Controller):

    @http.route(['/liability'], methods=['GET', 'POST'], type='http', auth='user', website=True)
    def liability(self, **kwargs):
        cr = request.cr
        uid = request.uid
        context = dict(request.context, show_address=True, no_tag_br=True)
        liability_pool = request.registry['vhr.liability']
        values = {
            'header': '',
            'liability_datas': [],
            'document_no': kwargs.get('document_no', ''),
            'date_from': kwargs.get('date_from', ''),
            'date_to': kwargs.get('date_to', ''),
        }
        domain = kwargs.get('domain', False) and eval(kwargs['domain']) or []
        if kwargs.get('ids', []):
            liability_ids = eval(kwargs['ids'])
            domain.append(('id', 'in', liability_ids))
        try:
            liability_datas = liability_pool.get_liability_datas(cr, uid, domain, context=context)
            values.update({
                'header': 'Công Nợ Của Nhân Viên',
                'liability_datas': liability_datas
            })
        except Exception, e:
            message = e.message
            log.info('Liability Error %s' % message)
        return request.render("vhr_mysite.liability", values)

    @http.route(['/liability/form'], methods=['GET', 'POST'], type='http', auth='user', website=True)
    def liability_form(self, **kwargs):
        cr = request.cr
        uid = request.uid
        context = dict(request.context, show_address=True, no_tag_br=True)
        liability_pool = request.registry['vhr.liability']
        values = {
            'error': '',
        }
        try:
            liability_id = kwargs.get('id', False) and int(kwargs['id']) or False
            if liability_id:
                liability_datas = liability_pool.get_liability_datas(cr, uid, [('id', '=', liability_id)], context=context)
                if liability_datas:
                    values.update(liability_datas[0])
                else:
                    values.update({
                        'error': u"Không tìm thấy công nợ",
                    })
            else:
                values.update({
                    'error': u"Không tìm thấy công nợ",
                })
        except Exception, e:
            message = e.message
            log.info('Liability Error %s' % message)
        return request.render("vhr_mysite.liability_form", values)
