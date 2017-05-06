# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields

log = logging.getLogger(__name__)

class vhr_program_recruitment(osv.osv):
    _name = 'vhr.program.recruitment'
    _description = 'VHR Program Recruitment'
    _inherits = {'vhr.dimension': 'dimension_id'}

    _columns = {
                'dimension_id' : fields.many2one('vhr.dimension', 'Dimension', ondelete="cascade", required='1'),
                'image': fields.binary("Photo", help="Icon for program"),
                'short_description': fields.text('Short description'),
                'short_description_en': fields.text('Short description'),
                'menu_event': fields.char('Menu event'),
                'menu_event_en': fields.char('Menu event EN'),
                'website_name': fields.char('Website name'),
                'website_name_en': fields.char('Website name EN'),
                'program_content_ids': fields.one2many('vhr.program.content', 'program_id',
                                                       'Program Contents'),
                'program_event_ids': fields.one2many('vhr.program.event', 'program_id', 'Program Events'),
                'menu_face': fields.char('Menu face'),
                'menu_face_en': fields.char('Menu face EN'),
                'face_typical_ids': fields.many2many('vhr.typical.face', 'program_typical_face_rel',
                                                     'program_id', 'typical_face_id', 'Face typical'),
                'sequence': fields.integer('Sequence')
            }

    _defaults = {
        'active': True,
        'sequence': 1,
    }
    
    _order = 'sequence asc'
    
    def create(self, cr, uid, vals, context={}):
        res_id = super(vhr_program_recruitment, self).create(cr, uid, vals, context)
        self.pool.get('vhr.recruitment.interface').notify_change(cr, uid, context=context)
        return res_id 
    
    def write(self, cr, uid, ids, vals, context=None):
        #TODO: process before updating resource
        if context is None:
            context = {}
        student_program_obj = self.pool.get('vhr.temp.applicant')
        res = super(vhr_program_recruitment, self).write(cr, uid, ids, vals, context)
        self.pool.get('vhr.recruitment.interface').notify_change(cr, uid, context=context)
        if vals.get('sequence'):
            sequence = vals.get('sequence')
            for program in self.browse(cr, uid, ids, context=context):
                program_name = program.name
                program_sequence = str(sequence) +'-'+program_name
                for event in program.program_event_ids:
                    program_event_id = event.id
                    if program_event_id:
                        context.update({'active_test': False})
                        lst_student_program_ids = student_program_obj.search(cr, uid, [('program_event_id', '=', program_event_id)], context=context)
                        if len(lst_student_program_ids)>0:
                            student_program_obj.write(cr, uid, lst_student_program_ids, {'sequence_program':program_sequence},context)
        return res 
    
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            dimension_ids = []  
            for program in self.browse(cr, uid, ids, context=context):
                dimension_ids.append(program.dimension_id.id)
            return self.pool.get('vhr.dimension').unlink(cr, uid, dimension_ids, context=context)
            self.pool.get('vhr.recruitment.interface').notify_change(cr, uid, context=context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res

vhr_program_recruitment()
