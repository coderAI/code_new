# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields


log = logging.getLogger(__name__)


class vhr_rr_talent_recom(osv.osv):
    _name = 'vhr.rr.talent.recom'
    _description = 'VHR RR Talent Recommend'

    _columns = {
        'name': fields.char('Reference\'s name'),
        'company': fields.char('Company'),
        'position': fields.char('Position'),
        'contact': fields.char('Mobile/Email'),
        'recom_rel_type_id': fields.many2one('vhr.rr.recom.rel.type','Relation', ondelete='cascade'),
        'comment': fields.text('Comment'),
        'applicant_id': fields.many2one('hr.applicant', 'Candidate')
    }

vhr_rr_talent_recom()
