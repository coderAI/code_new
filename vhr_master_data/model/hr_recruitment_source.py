# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields



log = logging.getLogger(__name__)


class hr_recruitment_source(osv.osv):
    _name = 'hr.recruitment.source'
    _inherit = 'hr.recruitment.source'
    _description = 'Recruitment Source'

    _columns = {
        'code': fields.char('Code', size = 64),
        'name': fields.char('Vietnamese Name', size=128),
        'name_en': fields.char('English Name', size=128),
        'source_type_id': fields.many2one('vhr.recruitment.source.type', 'Source Type', ondelete='restrict'),
        'description': fields.text('Description'),
        'have_reference': fields.boolean('Having reference'),
        'active': fields.boolean('Active'),
        
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                      domain=[('object_id.model', '=', _inherit), \
                                              ('field_id.name', 'not in', ['write_date', 'audit_log_ids'])]),
        'auto_send_email': fields.boolean('Auto Send Email'),

    }

    _defaults = {
        'have_reference': False,        
        'active': True,
    }
    _sql_constraints = [
                        ('vhr_rr_name_source_type_uniq','unique(name,source_type_id)', 'Name and Source type is already exist!')
                        ]
    _unique_insensitive_constraints = [{'code': "Recruitment Source's Code is already exist!"}]
    

    
    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        args_new = ['|', '|', ('name', operator, name), ('code', operator, name), ('name_en', operator, name)] + args
        ids = self.search(cr, uid, args_new)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(hr_recruitment_source, self).name_search(cr, uid, name, args, operator, context, limit)
    
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(hr_recruitment_source, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res

    def onchange_source_type_id(self, cr, uid, ids, source_type_id, context=None):
        if context is None:
            context = {}
        res = {}
        if source_type_id:
            type_pool = self.pool['vhr.recruitment.source.type']
            type = type_pool.browse(cr, uid, source_type_id, context=context)
            
            res.update({'value': {'auto_send_email': type.auto_send_email}})
        
        return res

hr_recruitment_source()