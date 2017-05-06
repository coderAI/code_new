# -*- coding: utf-8 -*-

import logging

from openerp.osv import osv, fields


log = logging.getLogger(__name__)


class vhr_delegate_master(osv.osv):
    _name = 'vhr.delegate.master'
    _description = 'VHR Delegate Master'
    
    _columns = {
        'name': fields.char('Name',size=32),
        'employee_id': fields.many2one('hr.employee','Employee', ondelete='restrict'),
        'employee_code': fields.related('employee_id', 'code', type='char', string='Employee Code'),
        'detail_ids': fields.one2many('vhr.delegate.detail', 'delegate_master_id', 'Detail', ondelete='cascade'),
        'module_id': fields.many2one('ir.module.module', 'Module', ondelete='restrict'),
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
    _unique_insensitive_constraints = [{'module_id': "Employee - Module is already exist!",
                                        'employee_id':"Employee - Module is already exist!"}]
    
    def onchange_employee_id(self, cr, uid, ids, employee_id, context=None):
        res = {'employee_code': ''}
        if employee_id:
            employee = self.pool.get('hr.employee').read(cr, uid, employee_id, ['code'])
            res['employee_code'] = employee.get('code','')
        
        return {'value': res}
            
    def name_get(self, cr, uid, ids, context=None):
        if not ids or False in ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        
        reads = self.read(cr, uid, ids, ['employee_id'], context=context)
        res = []
        for record in reads:
                name = record.get('employee_id',False) and record['employee_id'][1]
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
        
        res =  super(vhr_delegate_master, self).search(cr, uid, args, offset, limit, order, context, count)
        return res
    
    
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_delegate_master, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !',
                                 'You cannot delete the record(s) which reference to others !')
        return res
    
    def create(self, cr, uid, vals, context=None):
        if not context:
            context = {}
        
        context['check_unique_detail_later'] = True
        res = super(vhr_delegate_master, self).create(cr, uid, vals, context)
        
        if res:
            record = self.read(cr, uid, res, ['detail_ids'])
            detail_ids = record.get('detail_ids',[])
            self.pool.get('vhr.delegate.detail').check_unique_record(cr, uid, detail_ids)
                
            if not vals.get('active', False):
                self.update_active_delegate_detail(cr, uid, [res], vals.get('active', False), context)
            
        return res
    
    def write(self, cr, uid, ids, vals, context=None):
        if not context:
            context = {}
        context['check_unique_detail_later'] = True
        res = super(vhr_delegate_master, self).write(cr, uid, ids, vals, context)
        
        if res:
            if 'detail_ids' in vals:
                records = self.read(cr, uid, ids, ['detail_ids'])
                for record in records:
                    detail_ids = record.get('detail_ids',[])
                    self.pool.get('vhr.delegate.detail').check_unique_record(cr, uid, detail_ids)
                    
            if 'active' in vals:
                self.update_active_delegate_detail(cr, uid, ids, vals.get('active', False), context)
        
        return res
    
    def update_active_delegate_detail(self, cr, uid, ids, active, context=None):
        if not isinstance(ids, list):
            ids = [ids]
        
        detail_pool = self.pool.get('vhr.delegate.detail')
        for record in self.read(cr, uid, ids, ['detail_ids']):
            detail_ids = record.get('detail_ids', [])
            if detail_ids:
                detail_pool.write(cr, uid, detail_ids, {'active': active})
        
        return True
            

vhr_delegate_master()