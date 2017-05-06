# -*-coding:utf-8-*-
import logging
from openerp.osv import osv, fields
from datetime import date, datetime
import openerp

log = logging.getLogger(__name__)

class vhr_student_event(osv.osv):
    _name = 'vhr.student.event'
    _description = 'VHR Student Event'
    
    _columns = {
        'code': fields.char('Code', size = 64),
        'name': fields.char('Vietnamese Name'),
        'name_en': fields.char('English Name'),
        'description': fields.text('Description'),
        'active': fields.boolean('Active'),
    }

    _defaults = {
        'active': True,
    }

class vhr_student_organization_unit(osv.osv):
    _name = 'vhr.student.organization.unit'
    _description = 'VHR Student Organization Unit'
    
    _columns = {
        'code': fields.char('Code', size = 64),
        'name': fields.char('Vietnamese Name'),
        'name_en': fields.char('English Name'),
        'description': fields.text('Description'),
        'active': fields.boolean('Active'),
    }

    _defaults = {
        'active': True,
    }
