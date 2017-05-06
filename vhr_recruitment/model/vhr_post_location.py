# -*-coding:utf-8-*-
import logging


from openerp.osv import osv, fields

log = logging.getLogger(__name__)


class vhr_post_location(osv.osv):#should name vhr_rr_post_location
    _name = 'vhr.post.location'
    _description = 'VHR Post Location'

    _columns = {
        'name': fields.char('Name', size=256),
        'code': fields.char('Code', size=64),
        'name_en': fields.char('English Name', size=256),
        'content': fields.text('Content'),
        'internal': fields.boolean("Internal"),
        'active': fields.boolean('Active'),
    }

    _defaults = {
        'active': True,
        'internal': True
    }
    
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_post_location, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res

vhr_post_location()
