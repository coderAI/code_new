# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields

log = logging.getLogger(__name__)


class vhr_candidate_test_result(osv.osv):#should name vhr_program_test_result
    _name = 'vhr.candidate.test.result'
    _description = 'VHR Candidate Test Result'

    _columns = {
        'temp_candidate_id': fields.many2one('vhr.temp.applicant', 'Temp Candidate', ondelete='cascade'),
        'program_event_id': fields.many2one('vhr.program.event', 'Program Event', ondelete='restrict'),
        'program_question_id': fields.many2one('vhr.program.question', 'Question', ondelete='restrict'),
        'answer': fields.text('Answer'),
    }

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_candidate_test_result, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res

vhr_candidate_test_result()
