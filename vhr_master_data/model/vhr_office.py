# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields



log = logging.getLogger(__name__)


class vhr_office(osv.osv):
    _name = 'vhr.office'
    _description = 'VHR Office'

    _columns = {
        'code': fields.char('Code', size=64),
        'name': fields.char('Vietnamese Name', size=128),
        'name_en': fields.char('English Name', size=128),
        'city_id': fields.many2one('res.city', 'City', ondelete='restrict'),
        'address': fields.char('Address', size=512),
        'insurance_group_id': fields.many2one('vhr.dimension', 'Insurance Report Group', domain=[('dimension_type_id.code', '=', 'INSURANCE_REPORT_GROUP'), ('active','=',True)], ondelete='restrict'),
        'phone': fields.char('Phone', size=64),
        'is_parking': fields.boolean('Is Parking'),
        'is_meal': fields.boolean('Is meal'),#This field no longer use, should remove it in future
        'description': fields.text('Description'),
        'is_head_office': fields.boolean('Is Head Office'),
        'active': fields.boolean('Active'),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'History',
                                      domain=[('object_id.model', '=', _name),
                                              ('field_id.name', 'not in', ['write_date', 'audit_log_ids'])]),
    }

    _defaults = {
        'active': True,
    }
    
    _unique_insensitive_constraints = [{'code': "Office's Code is already exist!"},
                                       {'name': "Office's Vietnamese Name is already exist!"}]
    
    
    def name_get(self, cr, uid, ids, context=None):
        if not ids or False in ids:
            return []
    
        if not context:
            context = {}
            
        if isinstance(ids, (int, long)):
            ids = [ids]
        
        if context.get('get_office_name_by_code', False):
            reads = self.read(cr, uid, ids, ['code'], context=context)
            res = []
            for record in reads:
                code = record.get('code',False)
                res.append((record['id'], code))
                
            return res
    
        return super(vhr_office, self).name_get(cr, uid, ids, context=context)
    
    
    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        args_new = ['|', '|', ('name', operator, name), ('code', operator, name), ('name_en', operator, name)] + args
        ids = self.search(cr, uid, args_new)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(vhr_office, self).name_search(cr, uid, name, args, operator, context, limit)
    
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_office, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res

vhr_office()