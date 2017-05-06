# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields


log = logging.getLogger(__name__)


class hr_contract_type_group(osv.osv):
    _name = 'hr.contract.type.group'
    _description = 'Contract Type Group'

    _columns = {
        'code'  : fields.char('Code', size=64),
        'name': fields.char('Vietnamese Name', size=128),
        'name_en': fields.char('English Name', size=128),
        'number_of_day_to_prepare_terminate': fields.integer('LWD by Labour Law'),
        'prefix': fields.char('Prefix', size=64, help="Prefix value of the record for the sequence"),
        'suffix': fields.char('Suffix', size=64, help="Suffix value of the record for the sequence"),
        'is_offical': fields.boolean('Official'),
        'description': fields.text('Description'),
        'active': fields.boolean('Active'),
        
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                      domain=[('object_id.model', '=', _name), \
                                              ('field_id.name', 'not in', ['write_date', 'audit_log_ids'])]),
    }
 
    _defaults = {
        'active': True,
    }
    
    _unique_insensitive_constraints = [{'code': "Contract Type Group's Code is already exist!"},
                                       {'name': "Contract Type Group's Vietnamese Name is already exist!"}]


    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        args_new = ['|', '|', ('name', operator, name), ('code', operator, name), ('name_en', operator, name)] + args
        ids = self.search(cr, uid, args_new)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(hr_contract_type_group, self).name_search(cr, uid, name, args, operator, context, limit)
    
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(hr_contract_type_group, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res


hr_contract_type_group()
