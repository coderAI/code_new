# -*- coding: utf-8 -*-

import logging

from openerp.osv import osv, fields


log = logging.getLogger(__name__)


class vhr_resign_reason_detail(osv.osv):
    _name = 'vhr.resign.reason.detail'
    _description = 'VHR Resign Reason Detail'

    _columns = {
                'termination_request_id': fields.many2one('vhr.termination.request', 'Termination Request', ondelete='cascade'),
                'resignation_reason_id': fields.many2one('vhr.resignation.reason','Termination Reason', ondelete='restrict'),
                'percentage': fields.float('Percentage(%)'),
                'description': fields.text('Description'),
                
                'resignation_type_id': fields.related('resignation_reason_id','resignation_type_id', type="many2one", relation='vhr.resignation.type', string="Termination Type"),
                
                }

    _defaults = {
        'percentage': 100,
    }
    
    def onchange_percentage(self, cr, uid, ids, percentage, context=None):
        res = {}
        warning = {}
        if percentage and isinstance(percentage, (float,int))\
         and percentage < 0  or percentage > 100:
            res['percentage'] = 0.0
            warning = {'title': 'Validation Error!',
                       'message': 'Percentage (%) of Termination Reason must be from 0 to 100 !'}

        return {'value': res,'warning': warning}
    
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_resign_reason_detail, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res

vhr_resign_reason_detail()