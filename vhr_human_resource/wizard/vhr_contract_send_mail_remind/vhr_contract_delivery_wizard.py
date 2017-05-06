# -*-coding:utf-8-*-
from openerp.osv import osv, fields
from datetime import datetime

class vhr_contract_delivery_wizard(osv.osv):
    _name = 'vhr.contract.delivery.wizard'
    _description = 'Delivery to Employee'

    _columns = {
                'contract_ids': fields.one2many('hr.contract', 'delivery_wizard_id', 'Detail', ondelete='restrict')
    }
    
    def create(self, cr, uid, vals, context=None):
        contract_ids = []
        if vals.get('contract_ids', False):
            for item in vals.get('contract_ids', []):
                if len(item) == 3 and item[0] == 2:
                    vals['contract_ids'].remove(item)
                elif len(item) ==3:
                    contract_ids.append(item[1])
                    
        res = super(vhr_contract_delivery_wizard, self).create(cr, uid, vals, context)
        
        if res and contract_ids:
            self.pool.get('hr.contract').write(cr, uid, contract_ids, {'delivery_wizard_id': res})
            
        return res
    
    def default_get(self, cr, uid, flds, context=None):
        if context is None:
            context = {}
        
        res = super(vhr_contract_delivery_wizard, self).default_get(cr, uid, flds, context=context)
        
        if context.get('active_ids', False):
            contract_obj = self.pool.get('hr.contract')
            res['contract_ids'] = []
            for contract_id in context['active_ids']:   
                contract = contract_obj.browse(cr, uid, contract_id)
                emp_id = contract.employee_id and contract.employee_id.id or False
                res['contract_ids'].append([1,contract_id, {'holder_id': emp_id}])
        
        return res
        
    def execute_delivery(self, cr, uid, ids, context=None):
        if not context:
            context = {}
            
        if not isinstance(ids, list):
            ids = [ids]
        
        today = datetime.today().date()
        contract_obj = self.pool.get('hr.contract')
        record = self.read(cr, uid, ids[0], ['contract_ids'])
        contract_ids = record.get('contract_ids', [])
        if contract_ids:
#             not_allow_ids = contract_obj.search(cr, uid, [('id','in', contract_ids),
#                                                           ('is_invited','=',False),
#                                                       ]) 
#             if not_allow_ids:
#                 not_allows = contract_obj.read(cr, uid, not_allow_ids, ['emp_code'])
#                 emp_codes = [item.get('emp_code','') for item in not_allows]
#                 emp_codes = ', '.join(emp_codes)
#                 raise osv.except_osv('Error !', "Contracts of these employee are not invite: "+ emp_codes) 
                
            employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=', uid)], context={'active_test':False})
            self.pool.get('hr.contract').write_with_log(cr, uid, contract_ids, {'is_delivered': True,
                                                                                'delivery_id': employee_ids and employee_ids[0] or False,
                                                                                'delivery_date': today
                                                                       })
        
        return {'type': 'ir.actions.act_window_close'}
    
    
    
    def cron_delete(self, cr, uid):
        contract_obj = self.pool.get('hr.contract')
        contract_ids = contract_obj.search(cr, uid, [('delivery_wizard_id','!=', False)])
        if contract_ids:
            contract_obj.write(cr, uid, contract_ids, {'delivery_wizard_id': False})
            ids = self.search(cr, uid, [])
            self.unlink(cr, uid, ids)
        
        return True
            

vhr_contract_delivery_wizard()


class hr_contract(osv.osv):
    _name = 'hr.contract'
    _inherit = 'hr.contract'

    _columns = {
                
                'delivery_wizard_id': fields.many2one('vhr.contract.delivery.wizard', 'Delivery', ondelete='restrict')
                }
    

hr_contract()