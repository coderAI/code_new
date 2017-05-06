# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields



log = logging.getLogger(__name__)


class vhr_appendix_contract_type(osv.osv):
    _name = 'vhr.appendix.contract.type'
    _description = 'Appendix Contract Type'

    _columns = {
                'code': fields.char('Code', size=64),
                'name': fields.char('Vietnamese Name', size=128),
                'name_en': fields.char('English Name', size=128),
                'contract_sub_type_id': fields.many2one('hr.contract.sub.type', 'Contract Sub Type', ondelete='restrict'),
                'description': fields.text('Description'),
                'active': fields.boolean('Active'),
                'is_extension_appendix': fields.boolean('Is Extension Appendix'),
                'is_change_mission': fields.boolean('Is Change Mission'),
                'is_change_salary': fields.boolean('Is Change Salary'),
                'is_change_allowance': fields.boolean("Is Change Allowance"),
                
                'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                      domain=[('object_id.model', '=', _name), \
                                              ('field_id.name', 'not in', ['write_date', 'audit_log_ids'])]),

    }

    _defaults = {
        'active': True,
    }

    _unique_insensitive_constraints = [{'code': "Appendix Contract Type's Code is already exist!"},
                                       {'name': "Appendix Contract Type's Vietnamese Name is already exist!"}
    ]


    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        
        if 'contract_sub_type_id' in context:
            args.extend(['|',('contract_sub_type_id','=',False),
                             ('contract_sub_type_id','=',context['contract_sub_type_id'])])
        
        args_new = ['|', '|', ('name', operator, name), ('code', operator, name), ('name_en', operator, name)] + args
        ids = self.search(cr, uid, args_new)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(vhr_appendix_contract_type, self).name_search(cr, uid, name, args, operator, context, limit)

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_appendix_contract_type, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res


vhr_appendix_contract_type()