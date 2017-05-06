# -*-coding:utf-8-*-
import logging
import simplejson as json

from lxml import etree
from openerp.osv import osv, fields
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import datetime
from openerp import SUPERUSER_ID
from openerp.tools.translate import _
from openerp.addons.vhr_common.model.vhr_common import vhr_common

log = logging.getLogger(__name__)

STATES = [('lock','Lock'),
          ('unlock','Unlock')]

class vhr_ts_lock_timesheet_detail(osv.osv, vhr_common):
    _name = 'vhr.ts.lock.timesheet.detail'
    _description = 'Lock Timesheet Detail Generation'
    
    
    def _is_person_do_action(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for item in self.browse(cr, uid, ids):
            res[item.id] = self.is_person_do_action(cr, uid, ids, context)

        return res
    
    
    _columns = {
        'name': fields.text('Name', size=64),
        'lock_date': fields.date('Generation Date'),
        'year': fields.integer('Year'),
        'month': fields.integer('Month'),
        'employee_id': fields.many2one('hr.employee', 'Employee'),
        'employee_code': fields.related('employee_id', 'code', type="char", string="Employee Code"),
        'department_id': fields.many2one('hr.department', 'Department'),
        'state': fields.selection(STATES, 'Status', readonly=True),
        'holiday_ids': fields.one2many('hr.holidays', 'lock_ts_detail_id', 'Leave Request'),
        'is_person_do_action': fields.function(_is_person_do_action, type='boolean', string='Is Person Do Action'),
        'state_log_ids': fields.one2many('vhr.state.change', 'res_id', 'History', domain=[('model', '=', _name)]),

#         'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
#                                           domain=[('object_id.model', '=', _name),
#                                                   ('field_id.name', 'not in',
#                                                    ['write_date','audit_log_ids'])]),
        }
    
    _defaults = {
                 'state': 'lock',
                 }
    
    def name_get(self, cr, uid, ids, context=None):
        if not ids or False in ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        
        reads = self.read(cr, uid, ids, ['employee_id'], context=context)
        res = []
        for record in reads:
                name = record.get('employee_id',False) and record['employee_id'][1]
                res.append((record['id'], name))
        return res
    
    
    def is_person_do_action(self, cr, uid, ids, context=None):
        if ids:
            groups = self.pool.get('res.users').get_groups(cr, uid)
            
            if 'vhr_cb_timesheet' in groups:
                return True
        
        return False
    
    def execute_workflow(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        if ids:
            for record_id in ids:
                
                action_result = False
                record = self.read(cr, uid, record_id, ['state'])
                old_state = record.get('state', False)
                try:
                    if context.get('action', False) in ['unlock']:
                        action_result = self.action_unlock(cr, uid, [record_id], context)
    
                    elif context.get('action', False) == 'lock':
                        action_result = self.action_lock(cr, uid, [record_id], context)
                    
                    if action_result:
                        list_states = {item[0]: item[1] for item in STATES}
                        record = self.read(cr, uid, record_id, ['state'])
                        new_state = record.get('state', False)
                        
                        self.write_log_state_change(cr, uid, record_id, list_states[old_state], list_states[new_state], context)
                        
                except Exception as e:
                    log.exception(e)
                    try:
                        error_message = e.message
                        if not error_message:
                            error_message = e.value
                    except:
                        error_message = ""
                    raise osv.except_osv('Validation Error !', 'Have error during execute record:\n %s!' % error_message)

        return True
    
    
    def action_unlock(self, cr, uid, ids, context=None):
        log.info('Change status to next state')
        if not context:
            context = {}
        if ids:
            record_id = ids[0]
            if self.is_person_do_action(cr, uid, [record_id], context):
                
                record = self.read(cr, uid, record_id, ['state'])
                state = record.get('state', False)
                if state and state == 'lock':
                    vals = {'state':'unlock'}
                    res = self.write_with_log(cr, uid, [record_id], vals, context)
                    return True
            
        return False
    
    def action_lock(self, cr, uid, ids, context=None):
        log.info('Change status to previous state')
        if not context:
            context = {}
        if ids:
            record_id = ids[0]
            if self.is_person_do_action(cr, uid, [record_id], context):
                
                record = self.read(cr, uid, record_id, ['state'])
                state = record.get('state', False)
                record = self.read(cr, uid, record_id, ['state'])
                if state and state == 'unlock':
                    vals = {'state':'lock'}
                    res = self.write_with_log(cr, uid, [record_id], vals, context)
                    return True

        return False
    
    def write_log_state_change(self, cr, uid, record_id, old_state, new_state, context=None):
        if not context:
            context = {}
        state_vals = {}
        state_vals['old_state'] = old_state
        state_vals['new_state'] = new_state
        state_vals['create_uid'] = uid
        state_vals['res_id'] = record_id
        state_vals['model'] = self._name
        if 'ACTION_COMMENT' in context:
            state_vals['comment'] = context['ACTION_COMMENT']
        self.pool.get('vhr.state.change').create(cr, uid, state_vals)
        return True
    
    def check_if_can_not_create(self, cr, uid, employee_id, context=None):
        if employee_id:
            exist_ids = self.search(cr, uid, [('employee_id','=',employee_id),
                                              ('state','in', ['lock'])])
            if exist_ids:
                employee = self.pool.get('hr.employee').read(cr, uid, employee_id, ['login'])
                raise osv.except_osv(_('Validation Error!'),
                                     _('Employee %s has a "Lock Timesheet Detail" does not unlock !'% employee.get('login','')))
        
        return True
        
    def create(self, cr, uid, vals, context=None):
        
        self.check_if_can_not_create(cr, uid, vals.get('employee_id',False), context=None)
        res = super(vhr_ts_lock_timesheet_detail, self).create(cr, uid, vals, context)
        return res
    
    def unlink(self, cr, uid, ids, context=None):
        if ids:
            groups = self.pool.get('res.users').get_groups(cr, uid)
            if 'hrs_group_system' not in groups:
                raise osv.except_osv('Validation Error !', "You don't have permission to delete Lock Timesheet Detail !")
        
            #Break connection between lock timesheet detail and leave request
            holiday_ids = self.pool.get('hr.holidays').search(cr, uid, [('lock_ts_detail_id','in',ids)])
            if holiday_ids:
                self.pool.get('hr.holidays').write(cr, uid, holiday_ids, {'lock_ts_detail_id': False},context)
        
        res = super(vhr_ts_lock_timesheet_detail, self).unlink(cr, uid, ids, context)
        return res
    
    
    def open_window(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        
        view_open = 'view_vhr_ts_lock_timesheet_detail_submit_form'
        action = {
            'name': 'Notes',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.pool.get('ir.model.data').get_object_reference(cr, uid, 'vhr_timesheet', view_open)[1],
            'res_model': 'vhr.ts.lock.timesheet.detail',
            'context': context,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': ids[0],
        }
        return action
    
    
    def fields_view_get(self, cr, uid, view_id = None, view_type = 'form', context = None, toolbar = False, submenu = False):
        res = super(vhr_ts_lock_timesheet_detail, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar = toolbar, submenu = submenu)
        if context is None:
            context = {}
        if view_type == 'form':
            doc = etree.XML(res['arch'])
            if res['type'] == 'form':
                 #When view view_vhr_ts_lock_timesheet_detail_submit_form
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
                        
        return res  



vhr_ts_lock_timesheet_detail()