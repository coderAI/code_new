# -*-coding:utf-8-*-

from openerp.osv import osv, fields


class vhr_mass_status_detail(osv.osv):
    _name = 'vhr.mass.status.detail'
    _description = 'VHR Mass Status Detail'
    _order = 'status'
    _columns = {
        'mass_status_id': fields.many2one('vhr.mass.status', 'Mass Status'),
        'employee_id': fields.many2one('hr.employee', 'Employee'),
        'message': fields.char('Detail Message', size=2000),
        'status': fields.selection([('fail', 'Failed'), ('success', 'Success')], 'Status'),
    }

    _defaults = {
        'status': 'fail'
    }


vhr_mass_status_detail()