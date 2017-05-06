# -*-coding:utf-8-*-
import logging
from openerp.osv import osv, fields
from lxml import etree

log = logging.getLogger(__name__)

class vhr_interview_round_evaluation(osv.osv):
    _name = 'vhr.interview.round.evaluation'
    _description = 'VHR Interview Round Evaluation'

    _columns = {
        'job_applicant_id': fields.many2one('vhr.job.applicant', 'Job candidate evaluations'),
        'evaluation_id': fields.many2one('vhr.evaluation', 'Evaluation'),
        'point': fields.selection([('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')], 'Point'),
        'note': fields.text('Note'),
    }

vhr_interview_round_evaluation()
