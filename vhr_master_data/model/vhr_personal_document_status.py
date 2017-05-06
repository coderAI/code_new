# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields



log = logging.getLogger(__name__)


class vhr_personal_document_status(osv.osv):
    _name = 'vhr.personal.document.status'
    _description = 'VHR Personal Document Status'

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
    }

    _defaults = {
        'active': True,
    }

    _unique_insensitive_constraints = [{'code': "Personal Document Status's Code is already exist!"},
                                       {'name': "Personal Document Status's Vietnamese Name is already exist!"}]
    
    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        if context.get('search_by_document_type_id', False):
            document_type_id = context['search_by_document_type_id']
            document_type = self.pool['vhr.personal.document.type'].browse(cr, uid, document_type_id, context=context)
            if document_type:
                status_ids = [status.id for status in document_type.status_ids]
                args.append(('id', 'in', status_ids))
        args_new = ['|', '|', ('name', operator, name), ('code', operator, name), ('name_en', operator, name)] + args
        ids = self.search(cr, uid, args_new)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(vhr_personal_document_status, self).name_search(cr, uid, name, args, operator, context, limit)

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context = {}
        if context.get('search_by_document_type_id', False):
            document_type_id = context['search_by_document_type_id']
            document_type = self.pool['vhr.personal.document.type'].browse(cr, uid, document_type_id, context=context)
            if document_type:
                status_ids = [status.id for status in document_type.status_ids]
                args.append(('id', 'in', status_ids))
        return super(vhr_personal_document_status, self).search(cr, uid, args, offset=offset, limit=limit, order=order, context=context, count=count)
    
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_personal_document_status, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res


vhr_personal_document_status()