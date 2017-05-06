# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields

log = logging.getLogger(__name__)


class vhr_program_answer(osv.osv):
    _name = 'vhr.program.answer'
    _description = 'VHR Program Answer'

    _columns = {
        'name': fields.char('Vietnamese Name', size=128),
        'name_en': fields.char('English Name', size=128),
        'question_id': fields.many2one('vhr.program.question', 'Question', ondelete='cascade'),
        'description': fields.text('Description'),
        'is_result': fields.boolean('Result'),
        'active': fields.boolean('Active')
    }

    _defaults = {
        'active': True,
    }

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_program_answer, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res

vhr_program_answer()
