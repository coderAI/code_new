# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields
from openerp import tools
from datetime import datetime, timedelta
from openerp import SUPERUSER_ID

import sys  


class vhr_human_resource_abstract(osv.AbstractModel):
    _name = 'vhr.human.resource.abstract'
    _description = 'VHR Human Resource Abstract'
    
    def get_delegator(self, cr, uid, record_id, employee_id, context=None):
        '''
        Check if have record delegate detail with employee 
        Return list delegate_ids of record if have
        '''
        if not context:
            context = {}
        if employee_id and record_id:
                
            record = self.read(cr, uid, record_id, ['department_id'])
            
            department_id = record.get('department_id', False) and record['department_id'][0]
            
            detail_obj = self.pool.get('vhr.delegate.detail')
            
            module_ids = self.pool.get("ir.module.module").search(cr, uid, [('name','=','vhr_human_resource')])
            
            model_ids = self.pool.get('ir.model').search(cr, uid, [('model','=',self._name)])
            delegate_model_ids = self.pool.get('vhr.delegate.model').search(cr, uid, [('model_id','in',model_ids),
                                                                                     ('active','=',True)])
            
            if delegate_model_ids and module_ids and department_id:
                domain = [('employee_id','=',employee_id),
                         ('module_id','in',module_ids),
                         ('model_ids','=',delegate_model_ids[0]),
                         ('department_ids','=',department_id),
                         ('active','=',True)]
                
                detail_ids = detail_obj.search(cr, uid, domain)
                
                if detail_ids:
                    details = detail_obj.read(cr, uid, detail_ids, ['delegate_id'])
                    delegate_ids = [detail.get('delegate_id', False) and detail['delegate_id'][0] for detail in details]
                    
                    return delegate_ids
        
        return []
        
    
    def get_emp_make_delegate_by_process(self, cr, uid, delegate_id, context=None):
        '''
        Return dict {employee: delegate_from} make delegate for delegate_id in Termination
        '''
        if not context:
            context = {}
        res = {}
        if delegate_id:
#             
            delegate_obj = self.pool.get('vhr.delegate.by.process')
            
            model_name = self._name
            if context.get('a_model_name', False):
                model_name = context['a_model_name']
            
            module_ids = self.pool.get("ir.module.module").search(cr, uid, [('name','=','vhr_human_resource')])
            
            model_ids = self.pool.get('ir.model').search(cr, uid, [('model','=',model_name)])
            delegate_model_ids = self.pool.get('vhr.delegate.model').search(cr, uid, [('model_id','in',model_ids),
                                                                                     ('active','=',True)])
            
            if delegate_model_ids and module_ids:
                domain = [('delegate_id','=',delegate_id),
                         ('module_id','in',module_ids),
                         ('model_ids','=',delegate_model_ids[0]),
                         ('active','=',True)]
                
                delegate_ids = delegate_obj.search(cr, uid, domain)
                
                if delegate_ids:
                    details = delegate_obj.read(cr, uid, delegate_ids, ['employee_id','delegate_from_id'])
                    
                    for detail in details:
                        employee_id = detail.get('employee_id', False) and detail['employee_id'][0]
                        
                        delegate_from_id = detail.get('delegate_from_id', False) and detail['delegate_from_id'][0]
                    
                        res[employee_id] = delegate_from_id
                    
        return res
    
    def get_delegator_by_process(self, cr, uid, record_id, delegate_from_id, context=None):
        '''
        Check if have record delegate detail with employee 
        Return list delegate_ids of record if have
        '''
        if not context:
            context = {}
        if delegate_from_id and record_id:
                
            record = self.read(cr, uid, record_id, ['employee_id'])
            
            employee_id = record.get('employee_id', False) and record['employee_id'][0]
            
            delegate_obj = self.pool.get('vhr.delegate.by.process')
            
            module_ids = self.pool.get("ir.module.module").search(cr, uid, [('name','=','vhr_human_resource')])
            
            model_ids = self.pool.get('ir.model').search(cr, uid, [('model','=',self._name)])
            delegate_model_ids = self.pool.get('vhr.delegate.model').search(cr, uid, [('model_id','in',model_ids),
                                                                                     ('active','=',True)])
            
            if delegate_model_ids and module_ids and employee_id:
                domain = [('delegate_from_id','=',delegate_from_id),
                         ('module_id','in',module_ids),
                         ('model_ids','=',delegate_model_ids[0]),
                         ('employee_id','=',employee_id),
                         ('active','=',True)]
                
                delegate_ids = delegate_obj.search(cr, uid, domain)
                print 'domain=',domain
                if delegate_ids:
                    delegates = delegate_obj.read(cr, uid, delegate_ids, ['delegate_id'])
                    delegate_ids = [delegate.get('delegate_id', False) and delegate['delegate_id'][0] for delegate in delegates]
                    
                    return delegate_ids
        
        return []
    
    def get_emp_make_delegate(self, cr, uid, delegate_id, context=None):
        '''
        Return dict {employee: dept} make delegate for delegate_id in Termination
        '''
        if not context:
            context = {}
        res = {}
        if delegate_id:
#             
            detail_obj = self.pool.get('vhr.delegate.detail')
            
            model_name = self._name
            if context.get('a_model_name', False):
                model_name = context['a_model_name']
            
            module_ids = self.pool.get("ir.module.module").search(cr, uid, [('name','=','vhr_human_resource')])
            
            model_ids = self.pool.get('ir.model').search(cr, uid, [('model','=',model_name)])
            delegate_model_ids = self.pool.get('vhr.delegate.model').search(cr, uid, [('model_id','in',model_ids),
                                                                                     ('active','=',True)])
            
            if delegate_model_ids and module_ids:
                domain = [('delegate_id','=',delegate_id),
                         ('module_id','in',module_ids),
                         ('model_ids','=',delegate_model_ids[0]),
                         ('active','=',True)]
                
                detail_ids = detail_obj.search(cr, uid, domain)
                
                if detail_ids:
                    details = detail_obj.read(cr, uid, detail_ids, ['employee_id','department_ids'])
                    
                    for detail in details:
                        employee_id = detail.get('employee_id', False) and detail['employee_id'][0]
                        
                        department_ids = detail.get('department_ids', [])
                    
                        res[employee_id] = department_ids
                    
        return res

vhr_human_resource_abstract()