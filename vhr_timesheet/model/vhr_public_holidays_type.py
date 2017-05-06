# -*- coding: utf-8 -*-
from openerp.osv import osv, fields


class vhr_public_holidays_type(osv.osv):
    _name = 'vhr.public.holidays.type'

    _columns = {
        'name': fields.char('Vietnamese Name', size=128),
        'name_en': fields.char('English Name', size=128),
        'code': fields.char('Code', size=64),
        'active': fields.boolean('Active'),
        'color_name': fields.selection(
            [('red', 'Red'), ('#E74C3C', 'Alizarin'), ('blue', 'Blue'), ('lightgreen', 'Light Green'), ('lightblue', 'Light Blue'), ('yellow', 'Yellow'),
             ('lightyellow', 'Light Yellow'), ('magenta', 'Magenta'), ('lightcyan', 'Light Cyan'), ('black', 'Black'),
             ('lightpink', 'Light Pink'), ('brown', 'Brown'), ('violet', 'Violet'), ('lightcoral', 'Light Coral'),
             ('lightsalmon', 'Light Salmon'), ('lavender', 'Lavender'), ('wheat', 'Wheat'), ('ivory', 'Ivory')],
            'Color in Report', required=True,
            help='This color will be used in the leaves summary located in Reporting\Leaves by Department.'),
        'description': fields.text('Description'),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                         domain=[('object_id.model', '=', _name),
                                                 ('field_id.name', 'not in', ['write_date', 'audit_log_ids'])]),
    }

    _defaults = {
        'active': True
    }

    _unique_insensitive_constraints = [{'code': "Public Holidays Type's Code is already exist!"},
                                       {'name': "Public Holidays Type's Name is already exist!"}]

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}

        args_new = ['|', '|', ('name', operator, name), ('code', operator, name), ('name_en', operator, name)] + args

        ids = self.search(cr, uid, args_new)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(vhr_public_holidays_type, self).name_search(cr, uid, name, args_new, operator, context, limit)

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        try:
            return super(vhr_public_holidays_type, self).unlink(cr, uid, ids, context)
        except Exception as e:
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')


vhr_public_holidays_type()