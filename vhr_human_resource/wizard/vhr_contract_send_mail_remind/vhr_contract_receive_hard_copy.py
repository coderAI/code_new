# -*-coding:utf-8-*-
from openerp.osv import osv, fields
from datetime import datetime

class vhr_contract_receive_hard_copy(osv.osv):
    _name = 'vhr.contract.receive.hard.copy'
    _description = 'Receive Hard Copy'

    _columns = {
                'contract_ids': fields.one2many('hr.contract', 'receive_hard_copy_wizard_id', 'Detail', ondelete='restrict')
    }
    
    
    def create(self, cr, uid, vals, context=None):
        contract_ids = []
        if vals.get('contract_ids', False):
            for item in vals.get('contract_ids', []):
                if len(item) == 3 and item[0] == 2:
                    vals['contract_ids'].remove(item)
                elif len(item) ==3:
                    contract_ids.append(item[1])
                    
        res = super(vhr_contract_receive_hard_copy, self).create(cr, uid, vals, context)
        
        if res and contract_ids:
            self.pool.get('hr.contract').write(cr, uid, contract_ids, {'receive_hard_copy_wizard_id': res})
            
        return res
    
    def default_get(self, cr, uid, flds, context=None):
        if context is None:
            context = {}
        
        res = super(vhr_contract_receive_hard_copy, self).default_get(cr, uid, flds, context=context)
        
        if context.get('active_ids', False):
            contract_obj = self.pool.get('hr.contract')
            res['contract_ids'] = []
            for contract_id in context['active_ids']:   
                res['contract_ids'].append([1,contract_id, {'is_signed_by_emp': True}])
        
        return res
    
    def execute_receive(self, cr, uid, ids, context=None):
        if not context:
            context = {}
            
        if not isinstance(ids, list):
            ids = [ids]
        
        if not context:
            context = {}
        if ids:
            contract_obj = self.pool.get('hr.contract')
            record = self.read(cr, uid, ids[0], ['contract_ids'])
            contract_ids = record.get('contract_ids', [])
            if contract_ids:
#                 not_allow_ids = contract_obj.search(cr, uid, [('id','in', contract_ids),
#                                                       '|',('is_invited','=',False),
#                                                           ('is_delivered','=', False)
#                                                       ]) 
#                 if not_allow_ids:
#                     not_allows = contract_obj.read(cr, uid, not_allow_ids, ['emp_code'])
#                     emp_codes = [item.get('emp_code','') for item in not_allows]
#                     emp_codes = ', '.join(emp_codes)
#                     raise osv.except_osv('Error !', "Contracts of these employee are not invite or delivery: "+ emp_codes) 
                    
                employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=', uid)], context={'active_test':False})
                
                today = datetime.today().date()
                contract_obj.write_with_log(cr, uid, contract_ids, {'is_received': True,
                                                   'receiver_id': employee_ids and employee_ids[0] or False,
                                                   'received_date': today
                                                     })
            
        return True
    
    
    def cron_delete(self, cr, uid):
        contract_obj = self.pool.get('hr.contract')
        contract_ids = contract_obj.search(cr, uid, [('receive_hard_copy_wizard_id','!=', False)])
        if contract_ids:
            contract_obj.write(cr, uid, contract_ids, {'receive_hard_copy_wizard_id': False})
            ids = self.search(cr, uid, [])
            self.unlink(cr, uid, ids)
        
        return True
            

vhr_contract_receive_hard_copy()

class hr_contract(osv.osv):
    _name = 'hr.contract'
    _inherit = 'hr.contract'

    _columns = {
                
                'receive_hard_copy_wizard_id': fields.many2one('vhr.contract.receive.hard.copy', 'Receive Hard Copy', ondelete='restrict')
                }
    

hr_contract()

