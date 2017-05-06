# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields



log = logging.getLogger(__name__)


class vhr_resignation_reason(osv.osv):
    _name = 'vhr.resignation.reason'
    _description = 'VHR Termination Reason'

    _columns = {
        'code': fields.char('Code', size = 64),
        'name': fields.char('Vietnamese Name', size=512),
        'name_en': fields.char('English Name', size=512),
        'resignation_type_id': fields.many2one('vhr.resignation.type', 'Termination Type', ondelete='restrict'),
        'reason_group_id': fields.many2one('vhr.resignation.reason.group', 'Termination Reason Group', ondelete='restrict'),
        'is_hrbp': fields.boolean('HRBP'),
        'description': fields.text('Description'),
        'active': fields.boolean('Active'),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                          domain=[('object_id.model', '=', _name),
                                                  ('field_id.name', 'not in',
                                                   ['write_date', 'audit_log_ids'])]),
    }

    _defaults = {
        'is_hrbp': True,
        'active': True,
    }

    _unique_insensitive_constraints = [{'code': "Termination Reason's Code is already exist!"},
                                       {'name': "Termination Reason's Vietnamese Name - Reason Group - Termination Type are already exist!",
                                        'reason_group_id':"Termination Reason's Vietnamese Name - Reason Group - Termination Type are already exist!",
                                        'resignation_type_id': "Termination Reason's Vietnamese Name - Reason Group - Termination Type are already exist!"}]
    
    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        res = super(vhr_resignation_reason, self).default_get(cr, uid, fields, context=context)
        if context.get('reason_group', False):
            res['reason_group_id'] = context['reason_group']
        return res
    
    def name_get(self, cr, uid, ids, context=None):
        if not context:
            context = {}
            
        if not ids or False in ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        
        if context.get('get_resign_reason_name_en', False):
            reads = self.read(cr, uid, ids, ['name_en'], context=context)
            res = []
            for record in reads:
                    name = record.get('name_en','')
                    res.append((record['id'], name))
            return res
        else:
            return super(vhr_resignation_reason, self).name_get(cr, uid, ids, context)
        
        
    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        args_new = ['|', '|', ('name', operator, name), ('code', operator, name), ('name_en', operator, name)] + args
        
            
        ids = self.search(cr, uid, args_new, context=context)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(vhr_resignation_reason, self).name_search(cr, uid, name, args_new, operator, context, limit)
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if not context:
            context = {}

        if 'reason_group' in context:
            
            new_args =[('reason_group_id','=',context.get('reason_group',False))]
            
            if 'resignation_type' in context:
                new_args.insert(0,('resignation_type_id','=',context.get('resignation_type',False)))
                new_args.insert(0,'&')
            
            reason_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_human_resource_exception_resign_reason_termination') or ''
            reason_code_list = reason_code.split(',')
            if reason_code_list:
                other_ids = super(vhr_resignation_reason, self).search(cr, uid, 
                                            [('code','in',reason_code_list),
                                              '|','|',
                                                '&',('resignation_type_id','=',False),('reason_group_id','=',False),\
                                                '&',('resignation_type_id','=',context.get('resignation_type',False)),('reason_group_id','=',False),
                                                '&',('resignation_type_id','=',False),('reason_group_id','=',context.get('reason_group',False))])
                if other_ids:
                    new_args.insert(0, ('id','in',other_ids))
                    new_args.insert(0,'|')
            
            args.extend(new_args)
            

        return super(vhr_resignation_reason, self).search(cr, uid, args, offset, limit, order, context, count)
    
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_resignation_reason, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res


vhr_resignation_reason()