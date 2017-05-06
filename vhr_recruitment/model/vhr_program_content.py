# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields

log = logging.getLogger(__name__)

class vhr_program_content(osv.osv):
    _name = 'vhr.program.content'
    _description = 'VHR Program Content'
    
    _columns = {
                'code': fields.char('Code', size=64),
                'name': fields.char('Vietnamese Name', size=128),
                'name_en': fields.char('English Name', size=128),
                'short_description': fields.text('Short Description VN'),
                'short_description_en': fields.text('Short Description EN'),
                'description': fields.text('Vietnamese Description'),
                'description_en': fields.text('English Description'),
                'program_id': fields.many2one('vhr.program.recruitment', 
                                              'Recruitment program',  ondelete="cascade"),
            }
    _unique_insensitive_constraints = [{'code': "Program content's code is already exist!"}]

vhr_program_content()
