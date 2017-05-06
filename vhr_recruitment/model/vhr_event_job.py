# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields



log = logging.getLogger(__name__)


class vhr_event_job(osv.osv):
    _name = 'vhr.event.job'
    _description = 'VHR Event Job'

    _columns = {
        'event_id': fields.many2one('vhr.program.event', 'Event', ondelete='restrict'),
        'name': fields.char('Name VN', size=128),
        'name_en': fields.char('Name EN', size=128),
        'code': fields.char('Code', size=128),
        'email_cc': fields.text('Cc Email'),
        'active': fields.boolean('Active'),
    }

    _defaults = {
        'active': True
    }


vhr_event_job()
