# -*- coding: utf-8 -*-

import logging

from openerp.osv import osv, fields


log = logging.getLogger(__name__)


class vhr_delegate_model(osv.osv):
    _name = 'vhr.delegate.model'
    _description = 'VHR Delegate Model'
    
    _columns = {
        'module_id': fields.many2one('ir.module.module','Module'),
        'model_id': fields.many2one('ir.model','Model'),
        'name': fields.char('Name', size=128),
        'active': fields.boolean('Active'),
        'description': fields.text('Description'),
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
    _unique_insensitive_constraints = [{'model_id': "Model is already exist!"}]
    
    
    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
            
        ids = self.search(cr, uid, args, context = context)
        return super(vhr_delegate_model, self).name_search(cr, uid, name, args, operator, context, limit)
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if not context:
            context = {}
        
        if 'active_test' not in context:
            context['active_test'] = False
            
        if context.get('default_module', False):
            module_ids = self.pool.get("ir.module.module").search(cr, uid, [('name','=',context['default_module'])])
            args.append(('module_id','in',module_ids))
        
        if context.get('module_id', False):
             args.append(('module_id','=',context['module_id']))
        
        res =  super(vhr_delegate_model, self).search(cr, uid, args, offset, limit, order, context, count)
        return res
    
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_delegate_model, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !',
                                 'You cannot delete the record(s) which reference to others !')
        return res


vhr_delegate_model()