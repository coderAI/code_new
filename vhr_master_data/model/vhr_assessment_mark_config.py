# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields



log = logging.getLogger(__name__)


class vhr_assessment_mark_config(osv.osv):
    _name = 'vhr.assessment.mark.config'
    _description = 'Assessment Mark Configuration'
    _columns = {
        'name': fields.char('Name', size=128),
        'from_rating_percent': fields.float('From Percent'),
        'to_rating_percent': fields.float('To Percent'),
        'from_rating_score': fields.float('From Score'),
        'to_rating_score': fields.float('To Score'),
        'a_value': fields.float('a', digits=(16, 3)),
        'b_value': fields.float('b', digits=(16, 3)),
    }
    
    _unique_insensitive_constraints = [{'name': "Assessment Mark Config's Name is already exist!"}]


    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        args_new = [('name', operator, name)] + args
        ids = self.search(cr, uid, args_new)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(vhr_assessment_mark_config, self).name_search(cr, uid, name, args, operator, context, limit)

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_assessment_mark_config, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res


vhr_assessment_mark_config()
