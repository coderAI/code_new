# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields


log = logging.getLogger(__name__)


class vhr_rr_recom_rel_type(osv.osv):
    _name = 'vhr.rr.recom.rel.type'
    _description = 'VHR RR Recom Rel Type'

    _columns = {
        'code': fields.char('Code', size=64),
        'name': fields.char('Vietnamese Name', size=128),
        'name_en': fields.char('English Name', size=128),
        'description': fields.text('Vietnamese Description'),
        'description_en': fields.text('English Description'),
        'active': fields.boolean('Active'),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'History',
                                         domain=[('object_id.model', '=', _name),
                                                 ('field_id.name', 'not in', ['write_date', 'audit_log_ids'])]),
    }

    _defaults = {
        'active': True
    }
    _unique_insensitive_constraints = [{'code': "Channel's code is already exist!"},
                                       {'name': "Channel's Vietnamese Name is already exist!"}]
vhr_rr_recom_rel_type()
