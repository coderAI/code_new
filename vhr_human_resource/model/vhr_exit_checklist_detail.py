# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields



log = logging.getLogger(__name__)


class vhr_exit_checklist_detail(osv.osv):
    _name = 'vhr.exit.checklist.detail'
    _description = 'Exit Checklist Detail'

    _columns = {
                'name': fields.char('Name', size=128),
                'exit_id': fields.many2one('vhr.exit', 'Exit', ondelete='restrict'),
                'property_management_id': fields.many2one('vhr.property.management', 'Asset Management', ondelete='restrict'),
                'exit_checklist_id': fields.many2one('vhr.exit.checklist.request','Exit Checklist Request', ondelete='cascade'),
                'money_included_in_the_settlement': fields.char('Amount Included In Last Payment', size=64),
                'allocation_date': fields.date('Allocation Date'),
                'withdraw_date': fields.date('Withdraw Date'),
                'note': fields.text('Notes'),
                'type_exit': fields.char('Type Exit'),
    }


    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_exit_checklist_detail, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res
    
    def onchange_exit_id(self, cr, uid, exit_id, context=None):
        res = {'name': ''}
        if exit_id:
            exit = self.pool.get('vhr.exit').read(cr, uid, exit_id, ['name'])
            name = exit['name']
            res['name'] = name
        return {'value': res}


vhr_exit_checklist_detail()