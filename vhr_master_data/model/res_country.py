# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields

log = logging.getLogger(__name__)


class res_country(osv.osv):
    _name = 'res.country'
    _inherit = 'res.country'
    _description = 'Country'

    _unique_insensitive_constraints = [{'code': "Country's Code is already exist!"},
                                       {'name': "Country's Name is already exist!"}]

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        args_new = ['|', ('name', operator, name), ('code', operator, name)] + args
        ids = self.search(cr, uid, args_new)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(res_country, self).name_search(cr, uid, name, args, operator, context, limit)

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(res_country, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res


res_country()