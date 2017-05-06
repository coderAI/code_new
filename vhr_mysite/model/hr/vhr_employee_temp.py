# -*- coding: utf-8 -*-
import logging
import simplejson as json

from openerp.osv import osv, fields
from lxml import etree
# from datetime import datetime
# from openerp.tools import DEFAULT_SERVER_DATE_FORMAT


log = logging.getLogger(__name__)

STATES = [
    ('draft', 'Draft'),
    ('waiting', 'Waiting Verification'),
    ('verified', 'Verified')]


class vhr_employee_temp(osv.osv):
    _name = 'vhr.employee.temp'

    def _get_address(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for id in ids:
            vhr_employee_temp = self.read(cr, uid, id, ['street', 'city_id', 'district_id'])

            street = vhr_employee_temp.get('street',"")
            if vhr_employee_temp['district_id']:
                district = vhr_employee_temp['district_id']
            else:
                district = ''
            if vhr_employee_temp['city_id']:
                city = vhr_employee_temp['city_id']
            else:
                city = ''
            res[id] = street + ', ' + district + ', ' + city
        return res

    def _get_temporary_address(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for id in ids:
            vhr_employee_temp = self.read(cr, uid, id, ['temp_address', 'temp_city_id', 'temp_district_id'])
            if vhr_employee_temp['temp_address']:
                street = vhr_employee_temp['temp_address']
            else:
                street = ''
            if vhr_employee_temp['temp_district_id']:
                district = vhr_employee_temp['temp_district_id']
            else:
                district = ''
            if vhr_employee_temp['temp_city_id']:
                city = vhr_employee_temp['temp_city_id']
            else:
                city = ''
            res[id] = street + ', ' + district + ', ' + city
        return res

    _columns = {
        'request_date': fields.date('Request Date'),
        'employee_id': fields.many2one('hr.employee', 'Employee', required=True),
        'employee_code': fields.related('employee_id', 'code', type="char", string="Employee Code"),
        #These fields use to set color for field if data is different with data in hr.employee
        'employee_birthday': fields.related('employee_id', 'birthday', type="date", string="Employee Birthday"),
        'employee_gender': fields.related('employee_id', 'gender', type="selection", string="Employee Gender"),
        'employee_birth_city_id': fields.related('employee_id', 'birth_city_id', type="many2one", relation="res.city",string="Employee Place of Birth"),
        'employee_phone': fields.related('employee_id', 'phone', type="char", string="Employee Phone"),
        'employee_email': fields.related('employee_id', 'email', type="char", string="Employee email"),
        'employee_marital': fields.related('employee_id', 'marital', type="char", string="Employee marital"),
        'employee_nation_id': fields.related('employee_id', 'nation_id', type="many2one", relation="vhr.dimension",string="Employee Ethnic"),
        'employee_religion_id': fields.related('employee_id', 'religion_id', type="many2one", relation="vhr.dimension",string="Employee Religion"),
        'employee_mobile_phone': fields.related('employee_id', 'mobile', type="char", string="Employee mobile_phone"),
        'employee_street': fields.related('employee_id', 'street', type="char", string="Employee street"),
        'employee_city_id': fields.related('employee_id', 'city_id', type="many2one",relation="res.city", string="Employee street"),
        'employee_district_id': fields.related('employee_id', 'district_id', type="many2one",relation="res.district", string="Employee district_id"),
        'employee_temp_address': fields.related('employee_id', 'temp_address', type="char", string="Employee temp_address"),
        'employee_temp_city_id': fields.related('employee_id', 'temp_city_id', type="many2one",relation="res.city", string="Employee temp_city"),
        'employee_temp_district_id': fields.related('employee_id', 'temp_district_id', type="many2one",relation="res.district", string="Employee district_id"),
        'employee_image_medium': fields.related('employee_id', 'image_medium', type='binary'),
        'employee_children': fields.related('employee_id', 'children', type="integer"),
        'employee_country_id': fields.related('employee_id', 'country_id', type="many2one", relation="res.country", string="Nationality"),
        'employee_certificate_ids': fields.related('employee_id','certificate_ids', type='one2many',
                                                   relation='vhr.certificate.info', string='Certificates', readonly=True),
        'employee_personal_document': fields.related('employee_id','personal_document', type='one2many',
                                                   relation='vhr.personal.document', string='Certificates', readonly=True),
        'employee_relation_partners': fields.related('employee_id','relation_partners', type='one2many',
                                                   relation='vhr.employee.partner', string='Certificates', readonly=True),
        'employee_partner_banks': fields.related('employee_id','bank_ids', type='one2many',
                                                   relation='res.partner.bank', string='Bank Account', readonly=True),
        
        
        'birthday': fields.date('Date of Birth'),
        'gender': fields.selection([('male', 'Nam'), ('female', 'Nữ')], 'Gender'),
        'birth_city_id': fields.many2one('res.city', 'Place of Birth'),
        'phone': fields.char('Home Phone', size=32),
        'email': fields.char('Personal Email', size=128),
        'marital': fields.selection([('single', 'Độc Thân'), ('married', 'Đã Lập Gia Đình'), ('divorced', 'Đã Ly Hôn'),
                                     ('widowed', 'Góa Vợ/Chồng')], 'Marital Status'),
        'nation_id': fields.many2one('vhr.dimension', 'Ethnic', ondelete='restrict',
                                     domain=[('dimension_type_id.code', '=', 'NATION'), ('active', '=', True)]),
        'religion_id': fields.many2one('vhr.dimension', 'Religion', ondelete='restrict',
                                       domain=[('dimension_type_id.code', '=', 'RELIGION'), ('active', '=', True)]),
        'mobile': fields.char('Mobile Phone', size=32),
        'street': fields.char('Home Street', size=256),
        'city_id': fields.many2one('res.city', 'City'),
        'district_id': fields.many2one('res.district', 'District'),
        'country_id': fields.many2one('res.country', 'Nationality'),
        'temp_address': fields.char('Temp Street', size=256),
        'temp_city_id': fields.many2one('res.city', 'City'),
        'temp_district_id': fields.many2one('res.district', 'District'),
        'personal_document_temp_ids': fields.one2many('vhr.personal.document.temp', 'employee_temp_id',
                                                      'Changing Documents'),
        'relation_partner_temp_ids': fields.one2many('vhr.employee.partner.temp', 'employee_temp_id',
                                                     'Changing Relationships'),
        'certificate_ids': fields.one2many('vhr.certificate.info.temp', 'employee_temp_id',
                                           'Changing Certificates'),
        'bank_ids': fields.one2many('vhr.res.partner.bank.temp', 'employee_temp_id',
                                           'Changing Bank Account'),
        'state': fields.selection(STATES, 'Status', readonly=True),
        'name': fields.related('employee_id', 'name', type='char'),
        'image': fields.binary("Photo",
                               help="This field holds the image used as photo for the employee, limited to 1024x1024px."),
        'address': fields.function(_get_address, type='char', string='Adress'),
        'temporary_address': fields.function(_get_temporary_address, type='char', string='Temporary Address'),
        'state_log_ids': fields.one2many('vhr.state.change', 'res_id', 'History', domain=[('model', '=', _name)]),
        'return_reason_note': fields.text('Return Reason'),#When cb return update employee form
        'show_message': fields.boolean('Show message'),
        'children': fields.integer('Number of Children'),
    }

    _defaults = {
        'state': 'draft',
        'request_date': fields.datetime.now,
        'show_message': False,
    }
    
    _order = "id desc"

    def open_window(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        
#         if context.get('hide_form_view_button', False):
#             context['hide_form_view_button'] = False
        view_open = 'view_vhr_employee_temp_submit_form'
        action = {
            'name': 'Notes',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.pool.get('ir.model.data').get_object_reference(cr, uid, 'vhr_mysite', view_open)[1],
            'res_model': 'vhr.employee.temp',
            'context': context,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': ids[0],
        }
        return action
    
    def execute_workflow(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        action_result = True
        if ids:
            for record_id in ids:
                record = self.read(cr, uid, record_id, ['state'])
                old_state = record.get('state', False)
                
                if context.get('action', False) == 'submit':
                    action_result = self.state_verified(cr, uid, [record_id], context)
                elif context.get('action',False) == 'return':
                    action_result = self.return_draft(cr, uid, [record_id], context)
                
                if context.get('action') and action_result:
                    state_vals = {}
                    list_states = {item[0]: item[1] for item in STATES}
                    
                    record = self.read(cr, uid, record_id, ['state'])
                    new_state = record.get('state', False)
                    state_vals['old_state'] = list_states[ old_state]
                    state_vals['new_state'] = list_states[new_state]
#                     state_vals['create_uid'] = uid
  
                    state_vals['res_id'] = record_id
                    state_vals['model'] = self._name
                    if 'ACTION_COMMENT' in context:
                        state_vals['comment'] = context['ACTION_COMMENT']
                    self.pool.get('vhr.state.change').create(cr, uid, state_vals)
                        
        return action_result

    def _get_mapping_data(self, object, mapping_fields, res_id):
        val = {}
        for field in mapping_fields:
            if object[field]:
                if isinstance(object[field], tuple):
                    val.update({
                        field: object[field][0]
                    })
                elif not isinstance(object[field], list):
                    val.update({
                        field: object[field]
                    })

        # A special case for boolean fields
        boolean_fields = ['is_emergency', 'is_main']
        intersect_field = list(set(mapping_fields) & set(boolean_fields))
        for field in intersect_field:
            val.update({
                field: object[field]
            })

        res_id = isinstance(object[res_id], tuple) and object[res_id][0] or object[res_id]
        val.pop(res_id, None)
        return res_id, val

    def _update_origin_data(self, cr, uid, employee_id,pool, temp_pool, target_ids, mapping_fields, context=None):
        if context is None:
            context = {}
        temp_objs = temp_pool.read(
            cr, uid, target_ids, mapping_fields, context=context)
        for temp_obj in temp_objs:
            origin_id, pool_val = self._get_mapping_data(
                temp_obj, mapping_fields, 'origin_id')
            # Update origin
            if origin_id != 0:
                pool.write(cr, uid, [origin_id], pool_val, context=context)
            else:
                pool_val.update({
                    'employee_id': employee_id
                })
                
                # special case for bank account
                if pool == self.pool['res.partner.bank'] and 'is_main' not in pool_val.keys():
                    pool_val.update({
                        'is_main': False
                    })
                pool.create(cr, uid, pool_val, context=context)

    def state_verified(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        try:
            emp_pool = self.pool['hr.employee']
            emp_temp_pool = self.pool['vhr.employee.temp']
            cer_temp_pool = self.pool['vhr.certificate.info.temp']
            partner_temp_pool = self.pool['vhr.employee.partner.temp']
            doc_temp_pool = self.pool['vhr.personal.document.temp']
            bank_temp_pool = self.pool['vhr.res.partner.bank.temp']
            
            certificate_pool = self.pool['vhr.certificate.info']
            document_pool = self.pool['vhr.personal.document']
            partner_pool = self.pool['vhr.employee.partner']
            bank_pool = self.pool['res.partner.bank']

            mapping_emp_fields = ['employee_id', 'gender', 'birthday', 'marital',
                                  'children', 'nation_id', 'religion_id',
                                  'country_id', 'email', 'street', 'district_id', 'city_id',
                                  'temp_address', 'temp_district_id', 'temp_city_id', 'mobile',
                                  'certificate_ids', 'personal_document_temp_ids',
                                  'relation_partner_temp_ids', 'bank_ids']
            mapping_certificate_fields = ['origin_id', 'school_id', 'recruitment_degree_id',
                                          'speciality_id', 'faculty_id']
            mapping_document_fields = ['origin_id', 'document_type_id', 'number', 'issue_date',
                                       'expiry_date', 'city_id', 'country_id', 'state']
            mapping_partner_fields = ['origin_id', 'name', 'relationship_id',
                                      'mobile', 'phone', 'street', 'city_id',
                                      'district_id', 'is_emergency']
            mapping_bank_fields = ['origin_id', 'owner_name', 'acc_number',
                                   'bank', 'bank_branch', 'is_main']
            temp_employee_objs = self.read(
                cr, uid, ids, mapping_emp_fields, context=context)
            for temp_employee_obj in temp_employee_objs:
                # Get one2many ids
                temp_certificate_ids = temp_employee_obj['certificate_ids']
                temp_document_ids = temp_employee_obj['personal_document_temp_ids']
                temp_partner_ids = temp_employee_obj['relation_partner_temp_ids']
                temp_bank_ids = temp_employee_obj['bank_ids']

                employee_id, employee_val = self._get_mapping_data(
                    temp_employee_obj, mapping_emp_fields, 'employee_id')

                # Update the origin employee
                emp_pool.write(cr, uid, [employee_id], employee_val, context=context)
                
                # Update certificate:
                if temp_certificate_ids:
                    self._update_origin_data(
                        cr, uid, employee_id,
                        certificate_pool, cer_temp_pool, temp_certificate_ids,
                        mapping_certificate_fields, context=context)
                # Update Document:
                if temp_document_ids:
                    self._update_origin_data(
                        cr, uid, employee_id,
                        document_pool, doc_temp_pool, temp_document_ids,
                        mapping_document_fields, context=context)
                # Update Partner:
                if temp_partner_ids:
                    self._update_origin_data(
                        cr, uid, employee_id,
                        partner_pool, partner_temp_pool, temp_partner_ids,
                        mapping_partner_fields, context=context)
                # Update Bank Account:
                if temp_bank_ids:
                    self._update_origin_data(
                        cr, uid, employee_id,
                        bank_pool, bank_temp_pool, temp_bank_ids,
                        mapping_bank_fields, context=context)
#             Update the state
            self.write(cr, uid, ids, {'state': 'verified',
                                      'show_message': True})
        except Exception, e:
            log.exception(e)
            try:
                error_message = e.message
                if not error_message:
                    error_message = e.value
            except:
                error_message = ""
            raise osv.except_osv('Validation Error !', 'Have error during verify:\n %s '% error_message)
            return False

    def prepare_return_draft(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Quick Edit Employee Request',
            'res_model': 'vhr.employee.temp.quick.edit',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'nodestroy': True,
            'context': str(context),
        }
        
    def return_draft(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        ir_model_pool = self.pool.get('ir.model.data')
        view_tree_result = ir_model_pool.get_object_reference(cr, uid, 'vhr_mysite',
                                                              'tree_updating_employee')
        view_tree_id = view_tree_result and view_tree_result[1] or False
        view_search = ir_model_pool.get_object_reference(cr, uid, 'vhr_mysite',
                                                              'filter_updating_employee')
        view_search_id = view_search and view_search[1] or False
        
        # Create log
        state_vals = {}
        state_vals['old_state'] = 'waiting'
        state_vals['new_state'] = 'draft'
        # state_vals['create_uid'] = uid
        
        state_vals['res_id'] = ids[0]
        state_vals['model'] = self._name
        if 'ACTION_COMMENT' in context:
            state_vals['comment'] = context['ACTION_COMMENT']
        self.pool.get('vhr.state.change').create(cr, uid, state_vals)
        
        self.write(cr, uid, ids,
                   {'state': 'draft',
                    # Update reason note and is show message or not
                    'return_reason_note': context.get('ACTION_COMMENT',''),
                    'show_message': True})
        return {
            'type': 'ir.actions.act_window',
            'name': "Updating employees",
            'view_type': 'form',
            'view_mode': 'tree',
            'view_id': view_tree_id,
            'search_view_id': view_search_id,
            'res_model': 'vhr.employee.temp',
            'context': context,
            'domain': [('state', '=', 'waiting')],
        }

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        for employee_tmp in self.browse(cr, uid, ids, context=context):
            if employee_tmp.state != 'draft':
                raise osv.except_osv('Validation Error !', 'You can only delete record(s) with draft state!')
        try:
            res = super(vhr_employee_temp, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res
    
    
    def fields_view_get(self, cr, uid, view_id = None, view_type = 'form', context = None, toolbar = False, submenu = False):
        res = super(vhr_employee_temp, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar = toolbar, submenu = submenu)
        if context is None:
            context = {}
        if view_type == 'form':
            doc = etree.XML(res['arch'])
            if res['type'] == 'form':
                 #When view view_vhr_mass_movement_submit_form
                if context.get('action',False):
                    node = doc.xpath("//form/separator")
                    if node:
                        node = node[0].getparent()
                        if context.get('required_comment', False):
                            node_notes = etree.Element('field', name="action_comment", colspan="4", modifiers=json.dumps({'required' : True}))
                        else:
                            node_notes = etree.Element('field', name="action_comment", colspan="4")
                        node.append(node_notes)
                        res['arch'] = etree.tostring(doc)
                        res['fields'].update({'action_comment': {'selectable': True, 'string': 'Action Comment', 'type': 'text', 'views': {}}})
        
            res['arch'] = etree.tostring(doc)
        return res 
    
    def create(self, cr, uid, vals, context=None):
        if not context:
            context = {}
        
        if vals.get('request_date',False) and len(vals['request_date']) > 10:
            vals['request_date'] = vals['request_date'][:10]
        
        res = super(vhr_employee_temp, self).create(cr, uid, vals, context)


        return res
    
    def check_verified(self, cr, uid, employee_id, context=None):
        if not context:
            context = {}
        
        return self.search(cr, uid, [['employee_id', '=', employee_id],
                                     ['state', 'not in', ['verified', 'waiting']]],
                               context=context)
    
    def check_editable(self, cr, uid, employee_id, context=None):
        if not context:
            context = {}
        
        exist_ids = self.search(cr, uid, [['employee_id', '=', employee_id]], context)

        if not exist_ids:
            return True
        else:
            draft_ids = self.search(cr, uid, [['id', 'in', exist_ids],
                                              ['state', '=', 'draft']],
                                    context=context)
            if draft_ids:
                return True
            else:
                waiting_ids = self.search(cr, uid, [['id', 'in', exist_ids],
                                                    ['state', '=', 'waiting']],
                                          context=context)
                if not waiting_ids:
                    return True
        return False

vhr_employee_temp()