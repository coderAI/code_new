# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields



log = logging.getLogger(__name__)


class vhr_resignation_reason_group(osv.osv):
    _name = 'vhr.resignation.reason.group'
    _description = 'VHR Termination Reason Group'

    _columns = {
        'code': fields.char('Code', size = 64),
        'name': fields.char('Vietnamese Name', size=512),
        'name_en': fields.char('English Name', size=512),
        'resignation_type_id': fields.many2one('vhr.resignation.type', 'Termination Type', ondelete='restrict'),
#         'is_hrbp': fields.boolean('HRBP'),
        'description': fields.text('Description'),
        'active': fields.boolean('Active'),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                          domain=[('object_id.model', '=', _name),
                                                  ('field_id.name', 'not in',
                                                   ['write_date', 'audit_log_ids'])]),
    }

    _defaults = {
        'active': True,
    }

    _unique_insensitive_constraints = [{'code': "Termination Reason Group's Code is already exist!"},
                                       {'name': "Termination Reason Group's Vietnamese Name and Termination Type are already exist!",
                                        'resignation_type_id': "Termination Reason Group's Vietnamese Name and Termination Type are already exist!"}]
    
    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        res = super(vhr_resignation_reason_group, self).default_get(cr, uid, fields, context=context)
        if context.get('resignation_type', False):
            res['resignation_type_id'] = context['resignation_type']
        return res
    
    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        args_new = ['|', '|', ('name', operator, name), ('code', operator, name), ('name_en', operator, name)] + args
        
            
        ids = self.search(cr, uid, args_new, context=context)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(vhr_resignation_reason_group, self).name_search(cr, uid, name, args_new, operator, context, limit)
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if not context:
            context = {}

        if 'resignation_type' in context:
            args.append( ('resignation_type_id','=',context['resignation_type']))

        return super(vhr_resignation_reason_group, self).search(cr, uid, args, offset, limit, order, context, count)
    
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_resignation_reason_group, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res


vhr_resignation_reason_group()