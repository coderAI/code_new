# -*- coding: utf-8 -*-
import json
import uuid
from urlparse import urljoin
import time

from openerp.osv import osv, fields
from openerp.addons.website.models.website import slug
from lxml import etree


class vhr_employee_temp_quick_edit(osv.osv):
    _name = 'vhr.employee.temp.quick.edit'

    def _get_emp_temp_field_domain(self):
        emp_temp_pool = self.pool['vhr.employee.temp']
        field_not_show = ['request_date', 'employee_id',
                          'state', 'name', 'image', 'return_reason_note',
                          'show_message', 'state_log_ids']
        res = []
        
        for field in emp_temp_pool._columns:
            if not isinstance(emp_temp_pool._columns[field], fields.related) and \
                not isinstance(emp_temp_pool._columns[field], fields.many2many):
                res.append(field)
        return [x for x in res if x not in field_not_show]

    _columns = {
        'name': fields.char('Name'),
        'employee_temp_id': fields.many2one('vhr.employee.temp',
                                            'Employee',
                                            ondelete='cascade'),
        'active': fields.boolean('Active'),
        'emp_field_ids': fields.many2many('ir.model.fields',
                                          'ir_model_fields_quick_edit_rel',
                                          'temp_quick_edit_id', 'field_id',
                                          'Fields'),
        # When cb return update employee form
        'return_reason_note': fields.text('Return Reason'),
        'token': fields.char("Identification token",
                             readonly=1, required=1),

    }
    _defaults = {
        'employee_temp_id': lambda self, cr, uid, context=None: context.get('active_id'),
        'active': True,
        'token': lambda s, cr, uid, c: uuid.uuid4().__str__(),
        'name': lambda s, cr, uid, c: uuid.uuid4().__str__(),
    }
    
    _order = "id desc"

    def get_public_url(self, cr, uid, ids, context=None):
        return ''
        """ Computes a public URL for the quick edit """
        base_url = self.pool.get('ir.config_parameter').get_param(cr, uid,
            'web.base.url')
        url = ''
        request = self.browse(cr, uid, ids[0], context=context)
        url = urljoin(base_url, "mysite/quick_edit/%s/%s" % (slug(request), request.token))
        
        # We hide this funcion
#         return '<a href="%s">%s</a>' % (url, u"Click vào đây để chỉnh sửa nhanh")

    def fields_view_get(self, cr, uid, view_id=None, view_type='form',
                        context=None, toolbar=False, submenu=False):
        if context is None: 
            context = {}
        res = super(vhr_employee_temp_quick_edit, self).fields_view_get(
            cr, uid, view_id=view_id, view_type=view_type,
            context=context, toolbar=toolbar, submenu=submenu)
        doc = etree.XML(res['arch'])
 
        emp_domain = "[('name', 'in', " + str(self._get_emp_temp_field_domain()) + "), \
        ('readonly', '=', False), ('model', '=', 'vhr.employee.temp')]"
        nodes = doc.xpath("//field[@name='emp_field_ids']")
        for node in nodes:
            node.set('domain', emp_domain)
        res['arch'] = etree.tostring(doc)
        return res

    def return_draft(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        active_ids = context.get('active_ids', [])
        emp_temp_pool = self.pool['vhr.employee.temp']
        
        quick_edit_obj = self.browse(cr, uid, ids[0])
        if quick_edit_obj and quick_edit_obj.return_reason_note:
#             url = '<br />' + self.get_public_url(cr, uid, ids, context)
            url = self.get_public_url(cr, uid, ids, context)
            context.update({'ACTION_COMMENT': quick_edit_obj.return_reason_note + url})
        
        return emp_temp_pool.return_draft(cr, uid, active_ids, context=context)
