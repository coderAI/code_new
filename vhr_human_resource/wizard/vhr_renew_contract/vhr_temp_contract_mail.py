# -*-coding:utf-8-*-
from openerp.osv import osv, fields
from openerp.addons.vhr_common.model.vhr_common import vhr_common


class vhr_temp_contract_mail(osv.osv_memory, vhr_common):
    _name = 'vhr.temp.contract.mail'
    _description = 'VHR Temp Contract Mail'

    def _get_employee_gender(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for item in self.browse(cr, uid, ids):
            res[item.id] = 'Mr./Ms.'
            if item.employee_id:
                if item.employee_id.gender == 'male':
                    res[item.id] = 'Mr.'
                elif item.employee_id.gender == 'female':
                    res[item.id] = 'Ms.'
        return res

    _columns = {
        'employee_id': fields.many2one('hr.employee', 'Contracts'),
        'name': fields.related('employee_id', 'name_related', readonly=True, type='char', string="Name"),
        'email_to': fields.related('employee_id', 'work_email', readonly=True, type='char', string="Email To"),
        'gender': fields.function(_get_employee_gender, type='char', string='Gender'),
        'contracts': fields.many2many('hr.employee', 'temp_contract_mail_employee_rel',
                                      'temp_mail_id', 'employee_id', 'Contracts'),
    }

    _defaults = {
    }

vhr_temp_contract_mail()