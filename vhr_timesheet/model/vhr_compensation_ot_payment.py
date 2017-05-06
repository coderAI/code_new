# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import datetime
from openerp import SUPERUSER_ID
from openerp.tools.translate import _
from openerp.addons.vhr_common.model.vhr_common import vhr_common

log = logging.getLogger(__name__)

STATES = [('draft','Draft'),
          ('confirm','Confirm'),
          ('close','Close'),
          ('cancel','Cancel')]

class vhr_compensation_ot_payment(osv.osv, vhr_common):
    _name = 'vhr.compensation.ot.payment'
    _description = 'Compensation OT Payment'
    
    
    def _is_person_do_action(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for item in self.browse(cr, uid, ids):
            res[item.id] = self.is_person_do_action(cr, uid, ids, context)

        return res
    
    def _get_fcnt_compensation_ot_hour(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for item in self.read(cr, uid, ids, ['compensation_ot_hour']):
            res[item['id']] = item.get('compensation_ot_hour',0)
        return res
    
    _columns = {
        'name': fields.text('Name', size=64),
        'request_date': fields.date('Request Date'),
        'calculation_date': fields.date('Calculation Date'),
        'employee_id': fields.many2one('hr.employee', 'Employee'),
        'employee_code': fields.related('employee_id', 'code', type="char", string="Employee Code"),
        'department_id': fields.many2one('hr.department', 'Department'),
        'year': fields.integer('Year'),
        'compensation_ot_hour': fields.float('Compensation OT Hour'),
        'compensation_ot_day': fields.float('Compensation OT Day'),
        'initial_compensation_ot_hour': fields.float('Initital Compensation OT Hour'),
        'coef_hour_day': fields.float('Coef'),
        'state': fields.selection(STATES, 'Status', readonly=True),
        'is_person_do_action': fields.function(_is_person_do_action, type='boolean', string='Is Person Do Action'),
        'fcnt_compensation_ot_hour': fields.function(_get_fcnt_compensation_ot_hour, type='integer', string='Get old value of compenation ot hour'),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                          domain=[('object_id.model', '=', _name),
                                                  ('field_id.name', 'not in',
                                                   ['write_date','audit_log_ids'])]),
        }
    
    _defaults = {
                 'state': 'draft',
                 }
    
    def onchange_compensation_ot_hour(self, cr, uid, ids, compensation_ot_hour, fcnt_compensation_ot_hour, 
                                                          initial_compensation_ot_hour, coef_hour_day, context=None):
        res = {}
        warning = {}
        if compensation_ot_hour:
            if compensation_ot_hour <= 0:
                warning = {
                            'title': 'Validation Error!',
                            'message' : "Compensation OT Hour must be greater 0 !"
                             }
                compensation_ot_hour = fcnt_compensation_ot_hour
                res['compensation_ot_hour'] = compensation_ot_hour
            elif compensation_ot_hour > initial_compensation_ot_hour:
                warning = {
                            'title': 'Validation Error!',
                            'message' : "Compensation OT Hour  must be lower or equal total remain OT hours of employee!"
                             }
                compensation_ot_hour = fcnt_compensation_ot_hour
                res['compensation_ot_hour'] = compensation_ot_hour
            
            if compensation_ot_hour:
                res['compensation_ot_day'] = compensation_ot_hour / float(coef_hour_day)
                
        return {'value': res, 'warning': warning}
        
        
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
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        # Search rule for specific menu
        if not context:
            context = {}
        
        if context.get('filter_by_permission_ot_compensation',False):
            new_args = []   
            groups = self.pool.get('res.users').get_groups(cr, uid)
                
            if not set(['hrs_group_system','vhr_cb_timesheet','vhr_cnb_manager']).intersection(set(groups)):
                if 'vhr_dept_head' in groups:
                    login_employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=',uid)], 0, None, None, context)
                    if login_employee_ids:
                        department_ids = self.get_hierachical_department_from_manager(cr, uid, login_employee_ids[0], context)
                        employee_ids = self.pool.get('hr.employee').search(cr, uid, [('department_id','in',department_ids)])
                        new_args = [('employee_id','in',employee_ids)]
                else:
                    new_args = [('id','in',[])]
                args += new_args
         
        return super(vhr_compensation_ot_payment, self).search(cr, uid, args, offset, limit, order, context, count)
    
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
                try:
                    if context.get('action', False) in ['submit','close']:
                        action_result = self.action_next(cr, uid, [record_id], context)
    
                    elif context.get('action', False) == 'set_to_draft':
                        action_result = self.action_return(cr, uid, [record_id], context)
                
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
    
    
    def action_next(self, cr, uid, ids, context=None):
        log.info('Change status to next state')
        if not context:
            context = {}
        if ids:
            record_id = ids[0]
            mcontext = context
            if self.is_person_do_action(cr, uid, [record_id], mcontext):
                holiday_pool = self.pool.get('hr.holidays')
                
                vals = {}
                record = self.read(cr, uid, record_id, ['state','request_date','compensation_ot_hour','employee_id'])
                state = record.get('state', False)
                compensation_ot_hour = record.get('compensation_ot_hour',0)
                employee_id = record.get('employee_id',False) and record['employee_id'][0]
                request_date = record.get('request_date',False)
                request_date = request_date and datetime.strptime(request_date, DEFAULT_SERVER_DATE_FORMAT)
                request_year = request_date.year
                
                if state and state != 'close':
    
                    list_state = [item[0] for item in STATES]
                    index_new_state = list_state.index(state) + 1
                    
                    vals['state'] = list_state[index_new_state]
                    res = self.write(cr, uid, [record_id], vals, mcontext)

                    return True
            
        return False
    
    def action_return(self, cr, uid, ids, context=None):
        log.info('Change status to previous state')
        if not context:
            context = {}
        if ids:
            record_id = ids[0]
            if self.is_person_do_action(cr, uid, [record_id], context):
                holiday_pool = self.pool.get('hr.holidays')
                
                vals = {}
                record = self.read(cr, uid, record_id, ['state','compensation_ot_hour','request_date','employee_id'])
                state = record.get('state', False)
                compensation_ot_hour = record.get('compensation_ot_hour',0)
                employee_id = record.get('employee_id',False) and record['employee_id'][0]
                request_date = record.get('request_date',False)
                request_date = request_date and datetime.strptime(request_date, DEFAULT_SERVER_DATE_FORMAT)
                request_year = request_date.year
                if state == 'confirm':
                    vals['state'] = 'draft'
                    
                    #Addition ot days pay money move to compensation
                    compensation_days = 0
                    parameter_obj = self.pool.get('ir.config_parameter')
                    ot_leave_type_code = parameter_obj.get_param(cr, uid, 'ts.leave.type.overtime.code') or ''
                    ot_leave_type_code = ot_leave_type_code.split(',')
                    ot_leave_type_ids = self.pool.get('hr.holidays.status').search(cr, uid, [('code','in',ot_leave_type_code)])
                
                    general_param_pool = self.pool.get('vhr.ts.general.param')
                    general_param_ids = general_param_pool.search(cr, uid, [])
                    if general_param_ids:
                        param = general_param_pool.read(cr, uid, general_param_ids[0], ['compensation_off_hour', 'compensation_off_day'])
                        compen_hour = param.get('compensation_off_hour', 0)
                        compen_day = param.get('compensation_off_day', 0)
                        compensation_days = compensation_ot_hour / compen_hour * compen_day
                    
                    annual_leave_ids = holiday_pool.search(cr, uid, [('type','=','add'),
                                                                     ('holiday_status_id','in',ot_leave_type_ids),
                                                                     ('year','=',request_year),
                                                                     ('employee_id','=',employee_id),
                                                                     ('state','=','validate')], context={'get_all': True})
                    if annual_leave_ids:
                        leave = holiday_pool.read(cr, uid, annual_leave_ids[0], ['number_of_days_temp'])
                        number_of_days_temp = leave.get('number_of_days_temp', 0)
                        number_of_days_temp = number_of_days_temp + compensation_days
                        holiday_pool.write(cr, uid, annual_leave_ids, {'number_of_days_temp': number_of_days_temp})
                
                if vals:
                    self.write(cr, uid, [record_id], vals, context)

                return True

        return False
    
    def check_if_can_not_create(self, cr, uid, employee_id, context=None):
        if employee_id:
            exist_ids = self.search(cr, uid, [('employee_id','=',employee_id),
                                              ('state','in', ['draft','confirm'])])
            if exist_ids:
                employee = self.pool.get('hr.employee').read(cr, uid, employee_id, ['login'])
                raise osv.except_osv(_('Validation Error!'),
                                     _('Employee %s has a "Compensation OT Payment" does not close !'% employee.get('login','')))
        
        return True
        
    def create(self, cr, uid, vals, context=None):
        
        self.check_if_can_not_create(cr, uid, vals.get('employee_id',False), context=None)
        res = super(vhr_compensation_ot_payment, self).create(cr, uid, vals, context)
        return res
    
    def unlink(self, cr, uid, ids, context=None):
        overtime_sum_ids = []
        if ids:
            records = self.read(cr, uid, ids, ['state'])
            for record in records:
                if record.get('state',False) != 'draft':
                    raise osv.except_osv('Validation Error !', "You can only delete Compensation OT Payment at state 'Draft' !")

        res = super(vhr_compensation_ot_payment, self).unlink(cr, uid, ids, context)
        return res



vhr_compensation_ot_payment()