# -*- coding: utf-8 -*-

import logging

from openerp.osv import osv, fields


log = logging.getLogger(__name__)


class vhr_delegate_by_process(osv.osv):
    _name = 'vhr.delegate.by.process'
    _description = 'VHR Delegate By Process'
    
    _columns = {
        'name': fields.char('Name',size=32),
        'employee_id': fields.many2one('hr.employee', string='Employee Of Request'),
        'employee_code': fields.related('employee_id', 'code', type='char', string='Employee Code'),
        
        
        #Người delegate
        'delegate_from_id': fields.many2one('hr.employee','Person Delegate', ondelete='restrict'),
        'delegate_from_code': fields.related('delegate_from_id', 'code', type='char', string='Person Delegate Code'),
        
        #Người được delegate
        'delegate_id': fields.many2one('hr.employee','Delegate', ondelete='restrict'),
        'delegate_code': fields.related('delegate_id', 'code', type='char', string='Delegate Code'),
        
        'module_id': fields.many2one('ir.module.module', string='Module'),
        'model_ids':fields.many2many('vhr.delegate.model','delegate_process_model','delegate_detail_id','model_id','Model'),
        'active': fields.boolean('Active'),
    }

    def _get_default_module_id(self, cr, uid, context=None):
        if not context:
            context = {}
        
        if context.get('default_module', False):
            module_ids = self.pool.get("ir.module.module").search(cr, uid, [('name','=',context['default_module'])])
            return module_ids and module_ids[0] or False
        
        return False
    
    _defaults = {
        'active': True,
        'module_id': _get_default_module_id,
    }
    _unique_insensitive_constraints = [{'employee_id': "Employee-Delegate-Person Delegate is already exist!",
                                        'delegate_id': "Employee-Delegate-Person Delegate is already exist!",
                                        'delegate_from_id': "Employee-Delegate-Person Delegate is already exist!" }]
    
    def onchange_employee_id(self, cr, uid, ids, employee_id, context=None):
        res = {'employee_code': ''}
        if employee_id:
            emp = self.pool.get('hr.employee').read(cr, uid, employee_id, ['code'])
            res['employee_code'] = emp.get('code','')
        
        return {'value': res}
    
    def onchange_delegate_id(self, cr, uid, ids, delegate_id, context=None):
        res = {'delegate_code': ''}
        if delegate_id:
            delegate = self.pool.get('hr.employee').read(cr, uid, delegate_id, ['code'])
            res['delegate_code'] = delegate.get('code','')
        
        return {'value': res}
    
    def onchange_delegate_from_id(self, cr, uid, ids, delegate_from_id, context=None):
        res = {'delegate_from_code': ''}
        if delegate_from_id:
            delegate = self.pool.get('hr.employee').read(cr, uid, delegate_from_id, ['code'])
            res['delegate_from_code'] = delegate.get('code','')
        
        return {'value': res}
    
    def name_get(self, cr, uid, ids, context=None):
        if not ids or False in ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        
        reads = self.read(cr, uid, ids, ['delegate_id'], context=context)
        res = []
        for record in reads:
                name = record.get('delegate_id',False) and record['delegate_id'][1]
                res.append((record['id'], name))
        return res
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if not context:
            context = {}
        
        if 'active_test' not in context:
            context['active_test'] = False
        
        if context.get('default_module', False):
            module_ids = self.pool.get("ir.module.module").search(cr, uid, [('name','=',context['default_module'])])
            args.append(('module_id','in',module_ids))
        
        res =  super(vhr_delegate_by_process, self).search(cr, uid, args, offset, limit, order, context, count)
        return res
    

    
    def create(self, cr, uid, vals, context=None):
        res = super(vhr_delegate_by_process, self).create(cr, uid, vals, context)
        
        return res
    
    def write(self, cr, uid, ids, vals, context=None):
        if not context:
            context = {}
        
        res = super(vhr_delegate_by_process, self).write(cr, uid, ids, vals, context)
        
        return res
    
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_delegate_by_process, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !',
                                 'You cannot delete the record(s) which reference to others !')
        return res


vhr_delegate_by_process()