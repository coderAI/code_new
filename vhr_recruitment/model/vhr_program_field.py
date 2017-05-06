# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields
from openerp.addons.audittrail  import audittrail
from vhr_recruitment_abstract import vhr_recruitment_abstract, ADMIN

log = logging.getLogger(__name__)

class vhr_program_field(osv.osv, vhr_recruitment_abstract):
    _name = 'vhr.program.field'
    _description = 'VHR Program Field'
        
    def _is_group_program_field_addmin(self, cr, uid, ids, fields, args, context=None):
        result = {}
        if context is None:
            context = {}
        roles = self.recruitment_get_group_array(cr, uid, uid)
        current_emp = self.pool.get('hr.employee').search(cr, uid, [('user_id.id', '=', uid)], context={'active_test': False})
        if current_emp:
            for item in self.browse(cr, uid, ids, context=context):
                result[item.id] =  False
                if ADMIN in roles:
                    result[item.id] = True
        return result
    
    _columns = {
                'model': fields.char('Model', size=128),
                'name': fields.char('Name', size=128),
                'name_en': fields.char('Name EN', size=128),
                'field_model': fields.char('Model field', size=64),
                'sequence': fields.integer('Sequence'),
                'field_type': fields.selection([
                                                ('many2many', 'many2many'),
                                                ('many2one', 'many2one'),
                                                ('one2many', 'one2many'),
                                                ('selection', 'selection'),
                                                ('char', 'char'),
                                                ('text', 'text'),
                                                ('float', 'float'),
                                                ('integer', 'integer'),
                                                ('datetime', 'datetime'),
                                                ('time', 'time'),
                                                ('binary', 'binary'),
                                                 ], 'Field type', select=True),
                'placeholder': fields.char('Placeholder'),
                'placeholder_en': fields.char('Placeholder EN'),
                'description': fields.char('Description'),
                'description_en': fields.char('Description EN'),
                'error': fields.char('Error'),
                'error_en': fields.char('Error EN'),
                'attribute': fields.selection([
                                                ('email', 'Email'),
                                                ('number', 'Number'),
                                                ('phone', 'Phone'),
                                                ('link', 'Link'),
                                                 ], 'Attribute', select=True),
                'filter': fields.char('Filter'),
                'limit_size': fields.integer('Limit size'),  # only for binary
                'default': fields.char('Default value'),
                'is_required': fields.boolean('Is required'),
                'is_public': fields.boolean('Is public'),
                'is_group_addmin': fields.function(_is_group_program_field_addmin, type="boolean", string="Is Addmin"),
            }
    _defaults = {  
        'is_required': True,
        'is_public': False,
        'sequence': 100
        }
    

vhr_program_field()
