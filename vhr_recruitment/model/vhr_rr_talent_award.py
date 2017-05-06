# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields


log = logging.getLogger(__name__)


class vhr_rr_talent_award(osv.osv):
    _name = 'vhr.rr.talent.award'
    _description = 'VHR RR Talent Award'

    _columns = {
        'applicant_id': fields.many2one('hr.applicant', 'Candidate', ondelete='cascade'),
        'name': fields.char('Award'),
        'ratings': fields.char('Ratings'),
        'year': fields.char('Year'),
        'organization': fields.char('Organization/Company'),   
        'description': fields.text('Description')     
    }

vhr_rr_talent_award()
