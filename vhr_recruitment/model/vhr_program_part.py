# -*- coding: utf-8 -*-

import logging

from openerp.osv import osv, fields


log = logging.getLogger(__name__)


class vhr_program_part(osv.osv):
    _name = 'vhr.program.part'
    _description = 'VHR Program Part'

    _columns = {
        'program_event_id': fields.many2one('vhr.program.event', 'Program event'), 
        'code': fields.char('Code', size=64),
        'name': fields.char('Vietnamese Name', size=128),
        'name_en': fields.char('English Name', size=128),
        'group': fields.char('Group', size=64),
        'description': fields.text('Description VN'),
        'description_en': fields.text('Description EN'),
        'question_ids': fields.one2many('vhr.program.question', 'program_part_id','Questions'),
    }
    
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_program_part, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res


vhr_program_part()