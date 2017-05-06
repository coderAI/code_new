# -*- coding: utf-8 -*-
from openerp.osv import osv, fields


class vhr_res_partner_bank_temp(osv.osv):
    _name = 'vhr.res.partner.bank.temp'
    _columns = {
        'employee_temp_id': fields.many2one('vhr.employee.temp', 'Employee', ondelete='cascade'),
        'res_bank_id': fields.many2one('res.partner.bank', 'Personal Document'),
        
        'rpb_owner_name': fields.related('res_bank_id', 'owner_name', type="char"),
        'rpb_acc_number': fields.related('res_bank_id', 'acc_number', type="char"),
        'rpb_bank': fields.related('res_bank_id', 'bank', type="many2one", relation="res.bank"),
        'rpb_bank_branch': fields.related('res_bank_id','bank_branch',
                                          type="many2one", relation="res.branch.bank"),
        'rpb_is_main': fields.related('res_bank_id', 'is_main', type="boolean"),
        #'rpb_effect_from': fields.related('res_bank_id', 'effect_from', type="date"),
        
        'owner_name': fields.char('Account Owner Name', size=128),
        'acc_number': fields.char('Account Number', size=64, required=True),
        'bank': fields.many2one('res.bank', 'Bank'),
        'bank_branch': fields.many2one('res.branch.bank','Bank Branch',
                                       domain="[('bank_id', '=', bank)]"),
        'is_main': fields.boolean('Is Main'),
        #'effect_from': fields.date('Effective Date'),
        
        'origin_id': fields.integer('OID', readonly=True),
        'mode': fields.selection([('new', 'Tạo mới'), ('update', 'Cập nhật')],
                                 'Request', readonly=True, required=True),
    }
    
    _order = "id desc"
