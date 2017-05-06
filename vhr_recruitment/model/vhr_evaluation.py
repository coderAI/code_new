# -*-coding:utf-8-*-
import logging
from openerp.osv import osv, fields

log = logging.getLogger(__name__)


class vhr_evaluation(osv.osv):
    _name = 'vhr.evaluation'
    _description = 'VHR Evaluation'

    _columns = {
        'interview_round_id': fields.many2one('vhr.dimension', 'Interview Round',
                                              domain=[('dimension_type_id.code', '=', 'INTERVIEW_ROUND'),
                                                      ('active', '=', True)]),
        'name': fields.char('Vietnamese Name'),
        'name_en': fields.char('English Name'),
        'active': fields.boolean('Active')
    }
    _defaults = {
        'active': True,
    }


vhr_evaluation()
