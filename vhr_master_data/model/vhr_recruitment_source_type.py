# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields



log = logging.getLogger(__name__)


class vhr_recruitment_source_type(osv.osv):
    _name = 'vhr.recruitment.source.type'
    _description = 'VHR Recruitment Source Type'

    def _check_is_full_send_email(self, cr, uid, ids, field_name, arg, context=None):
        if context is None:
            context = {}
        res = {}
        for type_id in ids:
            # Seach all off source have current source type ids
            source_pool = self.pool['hr.recruitment.source']
            source_ids = source_pool.search(cr, uid, [('source_type_id', '=', type_id)], context=context)
            source_ids_check = source_pool.search(cr, uid, [('source_type_id', '=', type_id),
                                                            ('auto_send_email', '=', True)], context=context)
            if len(source_ids) == len(source_ids_check):
                res[type_id] = True
            else:
                res[type_id] = False
        return res

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
        'full_auto_send_email': fields.function(_check_is_full_send_email, type='boolean', string='Full Auto Send Email', ),
        'auto_send_email': fields.boolean('Auto Send Email'),
    }

    _defaults = {
        'active': True,
    }

    _unique_insensitive_constraints = [{'code': "Recruitment Source Type's Code is already exist!"},
                                       {'name': "Recruitment Source Type's Vietnamese Name is already exist!"}]
    
    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        args_new = ['|', '|', ('name', operator, name), ('code', operator, name), ('name_en', operator, name)] + args
        ids = self.search(cr, uid, args_new)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(vhr_recruitment_source_type, self).name_search(cr, uid, name, args, operator, context, limit)
    
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_recruitment_source_type, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res

    def write(self, cr, uid, ids, values, context=None):
        if context is None:
            context = {}
        if 'auto_send_email' in values:
            # Seach all off source have current source type ids
            source_pool = self.pool['hr.recruitment.source']
            source_ids = source_pool.search(cr, uid, [('source_type_id', 'in', ids)], context=context)
            # Update auto_send_email source as same as type
            source_pool.write(cr, uid, source_ids, {'auto_send_email': values['auto_send_email']}, context=context)
        return super(vhr_recruitment_source_type, self).write(cr, uid, ids, values, context=context)

vhr_recruitment_source_type()