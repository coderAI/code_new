# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields



log = logging.getLogger(__name__)


class vhr_personal_document_type(osv.osv):
    _name = 'vhr.personal.document.type'
    _description = 'VHR Personal Document Type'

    _columns = {
        'code': fields.char('Code', size = 64),
        'name': fields.char('Vietnamese Name', size=128),
        'name_en': fields.char('English Name', size=128),
        'description': fields.text('Description'),
        'active': fields.boolean('Active'),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                          domain=[('object_id.model', '=', _name),
                                                  ('field_id.name', 'not in',
                                                   ['write_date', 'audit_log_ids'])]),
        'status_ids': fields.many2many('vhr.personal.document.status', 'document_type_document_status_rel',
                                          'document_type_id',
                                          'document_status_id', 'Status'),
        'has_expiry_date': fields.boolean('Has Expiry Date')
    }

    _defaults = {
        'active': True,
    }

    _unique_insensitive_constraints = [{'code': "Personal Document Type's Code is already exist!"},
                                       {'name': "Personal Document Type's Vietnamese Name is already exist!"}]
    
    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        args_new = ['|', '|', ('name', operator, name), ('code', operator, name), ('name_en', operator, name)] + args
        ids = self.search(cr, uid, args_new)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(vhr_personal_document_type, self).name_search(cr, uid, name, args, operator, context, limit)
    
    
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_personal_document_type, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res


vhr_personal_document_type()