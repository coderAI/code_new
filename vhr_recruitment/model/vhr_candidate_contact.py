# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields

log = logging.getLogger(__name__)


class vhr_candidate_contact(osv.osv):#should name vhr_program_test_result
    _name = 'vhr.candidate.contact'
    _description = 'VHR candidate contact'

    _columns = {
        'candidate_id': fields.many2one('hr.applicant', 'Candidate', ondelete='cascade'),
        'contact_type_id': fields.many2one('vhr.dimension', 'Contact type', ondelete='restrict',
                                     domain=[('dimension_type_id.code', '=', 'RR_CANDIDATE_CONTACT'), ('active', '=', True)]),
        'create_uid': fields.many2one('res.users', 'Create User'),
        'create_date': fields.datetime('Create time'),
        'contact': fields.char('contact'),
    }

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_candidate_contact, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res

vhr_candidate_contact()
