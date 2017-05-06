# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields


log = logging.getLogger(__name__)


class vhr_rr_talent_expertise(osv.osv):
    _name = 'vhr.rr.talent.expertise'
    _description = 'VHR RR Talent Expertise'

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
    _unique_insensitive_constraints = [{'code': "Channel's code is already exist!"},
                                       {'name': "Channel's Vietnamese Name is already exist!"}]
    _defaults = {
        'active': True
    }
    

vhr_rr_talent_expertise()
