# -*-coding:utf-8-*-
import logging
from openerp.osv import osv, fields

log = logging.getLogger(__name__)

#TODO : move to master data when build master data

class vhr_note(osv.osv):
    _name = 'vhr.note'
    _description = 'VHR Note'

    _columns = {
        'create_date': fields.datetime('Create Date'),
        'create_uid': fields.many2one('res.users', 'Created By', readonly=True),
        'write_uid': fields.many2one('res.users', 'Update By', readonly=True),
        'write_date': fields.datetime('Write Date'),
        'message': fields.text('Message'),
        'res_id': fields.integer('Resource id'),
        'model': fields.char('Model'),
    }
    
    def create(self, cr, uid, vals, context={}):
        res_id = super(vhr_note, self).create(cr, uid, vals, context)
        return res_id 
    
vhr_note()
