# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields


log = logging.getLogger(__name__)


class res_city(osv.osv):
    _name = 'res.city'
    _description = 'City'
    _order = 'sequence, name asc'

    _columns = {
        'code': fields.char('Code', size=64),
        'name': fields.char('Vietnamese Name', size=128),
        'name_en': fields.char('English Name', size=128),
        'country_id': fields.many2one('res.country', 'Country', ondelete='restrict'),
        'description': fields.text('Description'),
        'active': fields.boolean('Active'),

        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                         domain=[('object_id.model', '=', _name),
                                                 ('field_id.name', 'not in', ['write_date', 'audit_log_ids'])]),
        'sequence': fields.integer('Sequence'),
    }

    def _get_default_country_id(self, cr, uid, context=None):
        m = self.pool.get('ir.model.data')
        return m.get_object(cr, uid, 'base', 'vn').id
    
    _defaults = {
        'active': True,
        'country_id': _get_default_country_id
    }

    _unique_insensitive_constraints = [{'code': "City's Code is already exist!"},
                                       {'name': "City's Vietnamese Name is already exist!"}]

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        args_new = ['|', '|', ('name', operator, name), ('code', operator, name), ('name_en', operator, name)] + args
        ids = self.search(cr, uid, args_new)
        # TODO: add accent mapping to postgres
        if ids:
            sql = " SELECT id, name FROM res_city" \
                  " WHERE "\
                  " ( unaccent(name) ilike unaccent('%s%%') " \
                  " OR unaccent(code) ilike unaccent('%s%%') " \
                  " OR unaccent(name_en) ilike unaccent('%s%%') )" \
                  " AND id in (%s)" \
                  " AND active = True" \
                  " ORDER BY %s" % (name, name, name, ', '.join(str(i) for i in ids), self._order)
                
            cr.execute(sql)
            res = cr.fetchall()
            if res:
                return res
            return self.name_get(cr, uid, ids, context=None)
        return super(res_city, self).name_search(cr, uid, name, args, operator, context, limit)

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(res_city, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res


res_city()