# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields
from lxml import etree
import simplejson as json

log = logging.getLogger(__name__)

PROGRAM_QUESTION_TYPE = [('dimension_type_id.code', '=', 'RR_PROGRAM_QUESTION'), ('active', '=', True)]
QUESTION_PART_TYPE = [('dimension_type_id.code', '=', 'RR_QUESTION_PART'), ('active', '=', True)]


class vhr_program_question(osv.osv):
    _name = 'vhr.program.question'
    _description = 'VHR Program Question'

    
    _columns = {
        'name': fields.char('Vietnamese Name', size=128),
        'name_en': fields.char('English Name', size=128),
        'program_event_id': fields.related('program_part_id', 'program_event_id', type='many2one',
                                           relation='vhr.program.event', string='Event', store=True),
        # requestion type
        'question_type_id': fields.many2one('vhr.dimension', 'Question type', ondelete='restrict',
                                            domain=PROGRAM_QUESTION_TYPE),
        'program_part_id': fields.many2one('vhr.program.part', 'Question Part', ondelete='restrict'),
        
        # LUAN TODO : remove field next build 
        'question_part_id': fields.many2one('vhr.dimension', 'Question part', ondelete='restrict',
                                            domain=QUESTION_PART_TYPE),
        'is_required': fields.boolean('Question required'),
        'answer_ids': fields.one2many('vhr.program.answer', 'question_id', 'Answers'),
        'description': fields.text('Description'),
        'active': fields.boolean('Active'),        
    }

    _defaults = {
        'active': True,
    }
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False):        
        if context is None:
            context = {}
        res = super(vhr_program_question, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar)
        if view_type == 'form':
            doc = etree.XML(res['arch'])
            if context.get('program_event_id'):
                event = self.pool.get('vhr.program.event').read(cr, uid, context.get('program_event_id'), ['part_ids'], context=context)                                 
                domain = [('id', 'in', event.get('part_ids'))]
                for node in doc.xpath("//field[@name='program_part_id']"):
                    node.set('domain', json.dumps(domain))
            res['arch'] = etree.tostring(doc)
        return res


    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_program_question, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res

vhr_program_question()
