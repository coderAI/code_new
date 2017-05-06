# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields


log = logging.getLogger(__name__)

RR_GROUP_FACE_DOMAIN = [('dimension_type_id.code', '=', 'RR_PROGRAM_GROUP_FACE'), ('active', '=', True)]

class vhr_typical_face(osv.osv):
    _name = 'vhr.typical.face'
    _description = 'VHR Typical Face'

    _columns = {
        'create_date': fields.datetime('Create date'),
        'create_uid': fields.many2one('res.users', 'Created By', readonly=True),
        'name': fields.char('Name', size=256),
        'name_en': fields.char('English Name', size=256),
        'content': fields.text('Content'),
        'content_en': fields.text('Content English'),
        'image': fields.binary("Photo"),
        'face_type_id':fields.many2one('vhr.dimension', 'Face type', ondelete='restrict',
                                      domain=RR_GROUP_FACE_DOMAIN),
        'active': fields.boolean('Active'),
    }

    _defaults = {
        'active': True
    }


vhr_typical_face()
