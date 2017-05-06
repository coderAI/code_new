# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields



log = logging.getLogger(__name__)


class res_partner_bank(osv.osv):
    _inherit = 'res.partner.bank'
    
    def get_state(self, cr, uid, context=None):
        bank_type = self.pool.get('res.partner.bank.type')
        ids = bank_type.search(cr, uid, [])
        res = False
        if ids:
            res = bank_type.read(cr, uid, ids[0], ['code'])
            res = res['code']
        return res
    
    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        res = super(res_partner_bank, self).default_get(cr, uid, fields, context=context)
        if context.get('partner_id'):
            res.update({'partner_id': context['partner_id']})
        return res
    
    _columns = {
                'city': fields.many2one('res.city', 'City'),
                'district_id': fields.many2one('res.district', 'District', ondelete='restrict'),
                'bank_branch': fields.many2one('res.branch.bank','Bank Branch', domain="[('bank_id','=', bank)]"),
                'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                      domain=[('object_id.model', '=', _inherit), \
                                              ('field_id.name', 'not in', ['write_date', 'audit_log_ids'])]),
                'partner_id': fields.many2one('res.partner', 'Account Owner', ondelete='cascade', select=True),
                'employee_id': fields.many2one('hr.employee', 'Employee'),
                'is_main': fields.boolean('Is Main'),
                'active': fields.boolean('Active'),
                'effect_from': fields.date('Effective Date'),
                'employee_code': fields.related('employee_id', 'code', type="char", string="Employee Code"),
                }
    
    def _get_default_bank(self, cr, uid, context=None):
        parameter_obj = self.pool.get('ir.config_parameter')
        bank_code = parameter_obj.get_param(cr, uid, 'vhr_master_data_default_bank') or ''
        bank_code = bank_code.split(',')
        bank_ids = self.pool.get('res.bank').search(cr, uid, [('code','in',bank_code)])
        if bank_ids:
            return bank_ids[0]
        
        return False
        
    _defaults = {
        'state': lambda self, cr, uid, context: self.get_state(cr, uid, context),
        'is_main': True,
        'active': True,
        'bank': _get_default_bank,
    }
    
    _unique_insensitive_constraints = [{'acc_number': "Account Number of Bank is duplicate !",
                                        'bank': "Account Number of Bank is duplicate !"},
    ]

    def onchange_employee(self, cr, uid, ids, employee_id):
        res = {}
        if employee_id:
            hr_employee = self.pool.get('hr.employee')
            res.update({'owner_name': hr_employee.browse(cr, uid, employee_id).name})
            
        return {'value': res}
    
    def onchange_active(self, cr, uid, ids, active, context=None):
        res = {}
        if not active:
            res.update({'is_main': False})
        
        return {'value': res}
    
    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        args_new = ['|', ('name', operator, name), ('acc_number', operator, name)] + args
        ids = self.search(cr, uid, args_new, context=context)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(res_partner_bank, self).name_search(cr, uid, name, args, operator, context, limit)
    
    def create(self, cr, uid, vals, context=None):
        res = super(res_partner_bank, self).create(cr, uid, vals, context=context)
        
        if vals.get('is_main', False) and res:
            res_bank = self.browse(cr, uid, res, context=context)
            employee_id = res_bank.employee_id and res_bank.employee_id.id or None
            bank_ids = self.search(cr, uid, [('employee_id', '=', employee_id), ('id', 'not in', [res])], context=context)
            self.write(cr, uid, bank_ids, {'is_main': False}, context=context)
        
        return res
    
    def write(self, cr, uid, ids, vals, context=None):
        if vals.get('is_main', False) and ids:
            res_bank = self.browse(cr, uid, ids[0], context=context)
            employee_id = res_bank.employee_id and res_bank.employee_id.id or None
            bank_ids = self.search(cr, uid, [('employee_id', '=', employee_id), ('id', 'not in', ids)], context=context)
            self.write(cr, uid, bank_ids, {'is_main': False}, context=context)
        return super(res_partner_bank, self).write(cr, uid, ids, vals, context=context)

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        for bank in self.browse(cr, uid, ids, context=context):
            if bank.is_main == True:
                raise osv.except_osv('Validation Error !', 'You can not delete main bank account !')
        try:
            res = super(res_partner_bank, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res
    
res_partner_bank()