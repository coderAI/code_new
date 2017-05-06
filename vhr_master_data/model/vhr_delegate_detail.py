# -*- coding: utf-8 -*-

import logging

from openerp.osv import osv, fields


log = logging.getLogger(__name__)


class vhr_delegate_detail(osv.osv):
    _name = 'vhr.delegate.detail'
    _description = 'VHR Delegate Detail'
    
    _columns = {
        'name': fields.char('Name',size=32),
        'delegate_master_id': fields.many2one('vhr.delegate.master','Delegate Master', ondelete='cascade'),
        'employee_id': fields.related('delegate_master_id', 'employee_id', type='many2one', relation='hr.employee', string='Employee', store=True),
        'employee_code': fields.related('delegate_master_id', 'employee_code', type='char', string='Employee Code'),
        'delegate_id': fields.many2one('hr.employee','Delegate', ondelete='restrict'),
        'delegate_code': fields.related('delegate_id', 'code', type='char', string='Delegate Code'),
        'department_ids':fields.many2many('hr.department','delegate_detail_department','delegate_detail_id','department_id','Department', domain=[('organization_class_id.level','=', '3')]),
        'module_id': fields.related('delegate_master_id', 'module_id', type='many2one', relation='ir.module.module', string='Module', store=True),
        'model_ids':fields.many2many('vhr.delegate.model','delegate_detail_model','delegate_detail_id','model_id','Model'),
        'active': fields.boolean('Active'),
    }

    _defaults = {
        'active': True,
    }
#     _unique_insensitive_constraints = [{'delegate_master_id': "Employee-Delegate-Module is already exist!",
#                                         'employee_id': "Employee-Delegate-Module is already exist!",
#                                         'delegate_id': "Employee-Delegate-Module is already exist!" }]
    
    def onchange_delegate_id(self, cr, uid, ids, delegate_id, context=None):
        res = {'delegate_code': ''}
        if delegate_id:
            delegate = self.pool.get('hr.employee').read(cr, uid, delegate_id, ['code'])
            res['delegate_code'] = delegate.get('code','')
        
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
        
        res =  super(vhr_delegate_detail, self).search(cr, uid, args, offset, limit, order, context, count)
        return res
    
    def check_unique_record(self, cr, uid, ids, context=None):
        """
        We only check unique delegate_master_id - delegate_id because vhr_delegate_master checked unique employee_id-module_id
        """
        if ids:
            if not isinstance(ids, list):
                ids = [ids]
            
            for record in self.read(cr, uid, ids, ['delegate_master_id','delegate_id']):
                delegate_id = record.get('delegate_id', False) and record['delegate_id'][0] or False
                delegate_master_id = record.get('delegate_master_id', False) and record['delegate_master_id'][0] or False
                duplicate_ids = self.search(cr, uid, [('delegate_master_id','=',delegate_master_id),
                                                      ('delegate_id','=',delegate_id),
                                                      ('id','!=',record['id'])])
                if duplicate_ids:
                    raise osv.except_osv('Warning !', "Employee-Delegate-Module is already exist!")
        
        return True

    
    def create(self, cr, uid, vals, context=None):
        res = super(vhr_delegate_detail, self).create(cr, uid, vals, context)
        
        if res:
            if not context.get('check_unique_detail_later', False):
                self.check_unique_record(cr, uid, [res], context)
            
        return res
    
    def write(self, cr, uid, ids, vals, context=None):
        if not context:
            context = {}
        
        res = super(vhr_delegate_detail, self).write(cr, uid, ids, vals, context)
        
        if res:
            if not context.get('check_unique_detail_later', False) and 'delegate_id' in vals.keys():
                self.check_unique_record(cr, uid, ids, context)
        
        return res
    
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_delegate_detail, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !',
                                 'You cannot delete the record(s) which reference to others !')
        return res


vhr_delegate_detail()