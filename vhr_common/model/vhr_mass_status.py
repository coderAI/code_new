# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields


log = logging.getLogger(__name__)


class vhr_mass_status(osv.osv):
    _name = 'vhr.mass.status'
    _description = 'VHR Mass Status'
    
    def _count_success(self, cr, uid, ids, prop, unknow_none, context=None):
        res = {}
        for record in self.read(cr, uid, ids, ['number_of_execute_record','number_of_fail_record']):
            number = record.get('number_of_execute_record', 0) - record.get('number_of_fail_record', 0)
            res[record['id']] = number
        return res
    
    _columns = {
        'requester_id': fields.many2one('hr.employee', 'Requester'),
        'create_date': fields.datetime('Mass Time'),
        'state': fields.selection([('new', 'New'),
                                   ('error', 'Error'),
                                   ('running', 'Running'),
                                   ('finish', 'Finish'),
                                   ('fail', 'Fail')], \
                                  'Status', readonly=True),
        'mass_status_detail_ids': fields.one2many('vhr.mass.status.detail', 'mass_status_id', 'Details'),
        'number_of_record': fields.integer('Number Of Record'),
        'number_of_execute_record': fields.integer('Number Of Executed Records'),
        'number_of_success_record': fields.function(_count_success, type='integer', string='Number Of Successful Records',help="This is function field compute from number of execute record and number of fail record"),
        'number_of_fail_record': fields.integer('Number Of Fail Records'),
        'module_id': fields.many2one('ir.module.module', 'Module'),
        'model_id': fields.many2one('ir.model', 'Object'),
        'type': fields.char('Type', size=32),
        'mass_status_info': fields.text('Mass Status Info'),
        # This field to show error message of Mass Process
        'error_message': fields.text('Error'),
    }

    _order = 'id desc'

    def name_get(self, cr, uid, ids, context=None):
        res = []
        for item in ids:
            res.append((item,"Mass Status " + str(item)))
        return res


vhr_mass_status()