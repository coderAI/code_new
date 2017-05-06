# -*- coding: utf-8 -*-
import logging
import time
from datetime import datetime
from lxml import etree
import simplejson as json

from openerp.osv import osv, fields
from openerp.addons.vhr_common.model.vhr_common import vhr_common
from openerp import SUPERUSER_ID
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from vhr_ts_overtime_email_process import mail_process
from dateutil.relativedelta import relativedelta
from openerp.tools.translate import _

log = logging.getLogger(__name__)

STATES = [('draft', 'Draft'),
          ('approve','Waiting LM'),
          ('finish', 'Finish'),
          ('cancel', 'Cancel')]


class vhr_ts_overtime(osv.osv, vhr_common):
    _name = 'vhr.ts.overtime'
    _inherit = ['ir.needaction_mixin']

#     def _get_state(self, cr, uid, context):
#         return STATES

    def _is_person_do_action(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for item in self.browse(cr, uid, ids):
            res[item.id] = self.is_person_do_action(cr, uid, ids, context)

        return res
    
    def _is_person_do_action_edit(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for item in self.browse(cr, uid, ids):
            res[item.id] = self.is_person_do_action_edit(cr, uid, ids, context)

        return res
    
    def _check_waiting_for(self, cr, uid, ids, prop, unknow_none, context = None):
        if not context:
            context= {}
        
        res = {}
        for record in self.browse(cr, uid, ids, fields_process=['report_to','state']):
            record_id = record.id
            res[record_id] = ''
            if record.state == 'draft':
                meta_datas = self.perm_read(cr, uid, [record_id], context)
                create_uid = meta_datas and meta_datas[0] and meta_datas[0].get('create_uid', False)
                if isinstance(create_uid, tuple):
                    create_uid = create_uid[0]
                if create_uid:
                    context['search_all_employee'] = True
                    context['active_test'] = False
                    employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', create_uid)], context=context)
                    if employee_ids:
                        employee = self.pool.get('hr.employee').read(cr, uid, employee_ids[0], ['login'])
                        requester_name =employee.get('login', '')
                        res[record_id] = requester_name
            elif record.state == 'approve':
                report_to = record.report_to and record.report_to.login or ''
                res[record_id] = report_to
        
        return res

    _columns = {
        'name': fields.char('Name', size=128),
        'employee_id': fields.many2one('hr.employee', 'Employee', ondelete='restrict'),
        'employee_code': fields.related('employee_id', 'code', type="char", string="Employee Code", store=True),
        'requester_id': fields.many2one('hr.employee', 'Requester', ondelete='restrict'),
        'company_id': fields.many2one('res.company', 'Company', ondelete='restrict'),
        'report_to': fields.related('employee_id', 'report_to', type='many2one', relation='hr.employee',
                                    string='Reporting line', readonly='1', store=True),
        'department_id': fields.related('employee_id', 'department_id', type='many2one', relation='hr.department',
                                        string='Department', readonly='1', store=True),
        'dept_head_id': fields.related('employee_id', 'parent_id', type='many2one', relation='hr.employee',
                                    string='Dept Head', readonly='1'),        
        'overtime_detail_ids': fields.one2many('vhr.ts.overtime.detail', 'overtime_id',
                                               'Overtime Detail', ondelete='cascade'),
        'state': fields.selection(STATES, 'Status', readonly=True),
        'state_log_ids': fields.one2many('vhr.state.change', 'res_id', 'History', domain=[('model', '=', _name)]),
        'is_person_do_action': fields.function(_is_person_do_action, type='boolean', string='Is Person Do Action'),
        'is_person_do_action_edit': fields.function(_is_person_do_action_edit, type='boolean', string='Is Person Do Action Edit'),
        'waiting_for': fields.function(_check_waiting_for, type='char', string='Waiting For', readonly = 1),
        'request_date': fields.date('Request Date'),
        'is_created': fields.boolean('Is Created'),
        'is_compensation_leave_job_level': fields.boolean('Is Compensation Leave By Job Level'),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                         domain=[('object_id.model', '=', _name),
                                                 ('field_id.name', 'not in',
                                                  ['write_date', 'audit_log_ids'])]),
        
        'is_offline': fields.boolean('Is Offline'),

    }

    _order = "request_date desc"

    # def _get_default_company_id(self, cr, uid, context=None):
    # company_ids = self.pool.get('res.company').search(cr, uid, [('is_member', '=', False)], order="id asc")
    #         if company_ids:
    #             return company_ids[0]
    #
    #         return False

    def _get_requester_id(self, cr, uid, context=None):
        employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', uid)], context={'search_all_employee': True,'active_test':False})
        if employee_ids:
            return employee_ids[0]

        return False


    _defaults = {
        # 'company_id': _get_default_company_id,
        'state': 'draft',
        'request_date': fields.datetime.now,
        'employee_id': _get_requester_id,
        'requester_id': _get_requester_id,
        'is_person_do_action': True,
        'is_person_do_action_edit': True,
    }

    def is_creator(self, cr, uid, ids, context=None):
        if not isinstance(ids,list):
            ids = [ids]
        if ids:
            meta_datas = self.perm_read(cr, uid, ids, context)
            create_uid = meta_datas and meta_datas[0] and meta_datas[0].get('create_uid', False)
            if isinstance(create_uid, tuple):
                create_uid = create_uid[0]
            if  create_uid == uid:
                return True

        return False

    def is_person_do_action(self, cr, uid, ids, context=None):
        if ids:
            leave_obj = self.pool.get('hr.holidays')
            state = context.get('state', False)
            groups = self.pool.get('res.users').get_groups(cr, uid)
            record = self.browse(cr, uid, ids[0])
            employee_id = record.employee_id and record.employee_id.id or False
            report_to = record.report_to and record.report_to.user_id and record.report_to.user_id.id or False
            
            report_to_emp_id = record.report_to and record.report_to.id or False
            department_id = record.department_id and record.department_id.id or False
            if not state:
                state = record.state or False
            
            ot_lines = record.overtime_detail_ids
            

            if (state == 'draft' and self.is_creator(cr, uid, ids, context)) \
                    or (state == 'approve' and (report_to == uid  or leave_obj.is_delegate_from(cr, uid, uid, report_to_emp_id, department_id, 
                                                                                                self._name)  )):
                return True

            if set(['vhr_cb_timesheet','vhr_cb_admin']).intersection(groups):
                return True

        return False
    
    def is_person_do_action_edit(self, cr, uid, ids, context=None):
        if ids:
            leave_obj = self.pool.get('hr.holidays')
            state = context.get('state', False)
            groups = self.pool.get('res.users').get_groups(cr, uid)
            record = self.browse(cr, uid, ids[0])
            employee_id = record.employee_id and record.employee_id.id or False
            department_id = record.department_id and record.department_id.id or False
            report_to_emp_id = record.report_to and record.report_to.id or False
            
            report_to = record.report_to and record.report_to.user_id and record.report_to.user_id.id or False
            
            if not state:
                state = record.state or False
            
            ot_lines = record.overtime_detail_ids
            
            if (state == 'draft' and self.is_creator(cr, uid, ids, context)) \
                    or (state == 'approve' and  ( report_to == uid   or leave_obj.is_delegate_from(cr, uid, uid, report_to_emp_id, department_id,
                                                                                                   self._name) )):
                return True

            if 'vhr_cb_timesheet' in groups:
                return True

        return False

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        # Search rule for specific menu
        if not context:
            context = {}
        
        context['search_all_employee'] = True
        args = self.build_condition_menu(cr, uid, args, offset, limit, order, context, count)

        return super(vhr_ts_overtime, self).search(cr, uid, args, offset, limit, order, context, count)

    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False,
                   lazy=True):
        """
        Get the list of records in list view grouped by the given ``groupby`` fields
        """
        if not context:
            context = {}
        context['search_all_employee'] = True
        args = self.build_condition_menu(cr, uid, domain, 0, 0, 0, context, False)

        res = super(vhr_ts_overtime, self).read_group(cr, uid, domain, fields, groupby, offset, limit, context, orderby,
                                                      lazy)
        return res
    
    def read(self, cr, user, ids, fields=None, context=None, load='_classic_read'):
        if not context:
            context = {}
        
        if 'active_test' not in context:
            context['active_test'] = False
            
        if context.get('validate_read_vhr_ts_overtime',False):
            log.info('\n\n validate_read_vhr_ts_overtime')
            if not context.get('type', False):
                context['type'] = 'my_list'
            result_check = self.validate_read(cr, user, ids, context)
            if not result_check:
                raise osv.except_osv(_('Validation Error !'), _('You don’t have permission to access this data !'))
            
            del context['validate_read_vhr_ts_overtime']
        
        res =  super(vhr_ts_overtime, self).read(cr, user, ids, fields, context, load)
            
        return res
    
    def validate_read(self, cr, uid, ids, context=None):
        user_groups = self.pool.get('res.users').get_groups(cr, uid)
        if set(['hrs_group_system', 'vhr_cnb_manager','vhr_cb_timesheet']).intersection(set(user_groups)):
            return True
        if isinstance(ids, (int, long)) or (isinstance(ids, list) and len(ids)) == 1:
            check_id = ids
            if isinstance(ids, list):
                check_id = ids[0]
            new_context = context and context.copy() or {}
            
            lst_check = self.search(cr, uid, [], context=new_context)
            if check_id not in lst_check:
                return False
        return True

    def build_condition_menu(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if not context:
            context = {}
        new_args = []
        groups = self.pool.get('res.users').get_groups(cr, uid)
        mcontext = {'search_all_employee': True, 'active_test': False}
        employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', uid)],context=mcontext)

        if context.get('type', False) == 'request':
            #My Requests
            new_args = ['|', ('requester_id', 'in', employee_ids), ('employee_id', 'in', employee_ids)]

        elif context.get('type', False) == 'task':
            # My Tasks
            #             if set(['hrs_group_system','vhr_cb']).intersection(set(groups)):
            #                 new_args = [('state','in',['draft','approve'])]
            new_args = ['|',
                        '&', ('state', '=', 'draft'), ('requester_id', 'in', employee_ids),
                        '&', ('state', '=', 'approve'), ('report_to', 'in', employee_ids)
            ]
            
            dict = self.pool.get('hr.holidays').get_emp_make_delegate(cr, uid, employee_ids[0], self._name, context)
            if dict:
                emp_ids = []
                for employee_id in dict:
                    emp_ids.append(employee_id)
                new_args.extend(['&',('report_to','in',emp_ids),('state', '=', 'approve')])
                new_args.insert(0,'|')
                    
        elif context.get('type', False) == 'my_list':
            if set(['hrs_group_system', 'vhr_cnb_manager', 'vhr_cb_timesheet']).intersection(set(groups)):
                new_args = []
            else:
                
                if employee_ids:
                    search_department_ids = []
                    #Get department of hrbp/assist_hrbp
#                     department_hrbp = self.get_department_of_hrbp(cr, uid, employee_ids[0])
#                     department_ass_hrbp = self.get_department_of_ass_hrbp(cr, uid, employee_ids[0])
#                     search_department_ids = department_hrbp + department_ass_hrbp
    
                    #Get department and child department of dept head
                    department_ids = self.pool.get('hr.department').search(cr, uid, [('manager_id', '=', employee_ids[0])])
                    if department_ids:
                        child_department_ids = self.get_child_department(cr, uid, department_ids)
                        search_department_ids += child_department_ids + department_ids
                    
                     # Filter by Dept Admin
                    if set(['vhr_dept_admin']).intersection(set(groups)):
                        employee_ids_belong_to_dept_admin = self.get_list_employees_of_dept_admin(cr, uid, employee_ids[0], context)
                        employee_ids.extend(employee_ids_belong_to_dept_admin)
                        
                    new_args = ['|', '|',
                                ('employee_id', 'in', employee_ids),  # User is employee
                                ('report_to', 'in', employee_ids),  #user is reporting line
                                ('department_id', 'in', search_department_ids),  #user id hrbp/assist_hrbp/dept head
                    ]
                    
                    dict = self.pool.get('hr.holidays').get_emp_make_delegate(cr, uid, employee_ids[0], self._name, context)
                    if dict:
                        emp_ids = []
                        for employee_id in dict:
                            emp_ids.append(employee_id)
                        new_args.extend([('report_to','in',emp_ids)])
                        new_args.insert(0,'|')
                
                else:
                    new_args = [('id','in',[])]
                
                


        args += new_args

        return args

    def name_get(self, cr, uid, ids, context=None):
        if not ids or False in ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        reads = self.read(cr, uid, ids, ['employee_id'], context=context)
        res = []
        for record in reads:
            name = record.get('employee_id', False) and record['employee_id'][1]
            res.append((record['id'], name))
        return res

    def onchange_employee_id(self, cr, uid, ids, employee_id, context=None):
        res = {'employee_code': '', 'report_to': False}
        domain = {}
        if employee_id:
            employee_obj = self.pool.get('hr.employee')
            employee = employee_obj.browse(cr, uid, employee_id, fields_process=['code', 'report_to'])
            res['employee_code'] = employee.code or ''
            res['report_to'] = employee.report_to and employee.report_to.id or False
            res['dept_head_id'] = employee.parent_id and employee.parent_id.id or False
            res['department_id'] = employee.department_id and employee.department_id.id or False
            
            res['is_compensation_leave_job_level'] = self.get_is_compensation_leave_of_employee(cr, uid, employee_id, context)

        #             company_id, company_ids = employee_obj.get_company_ids(cr, uid, employee_id)
        # res['company_id'] = company_id
        #             domain['company_id'] = [('id', 'in', company_ids)]

        return {'value': res, 'domain': domain}
    
    def get_is_compensation_leave_of_employee(self, cr, uid, employee_id, context=None):
        '''
        Mac dinh la nghi bu
        '''
        if employee_id:
            job_level_obj = self.pool.get('vhr.job.level.new')
            job_level_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_timesheet_job_level_start_is_compensation_leave') or ''
            job_level_code = job_level_code.split(',')
            job_level_ids = job_level_obj.search(cr, uid, [('code', 'in', job_level_code)], context=context)
            if job_level_ids:
                job_level = job_level_obj.read(cr, uid, job_level_ids[0], ['name'])
                ground_level = job_level.get('name',0)
                
                employee = self.pool.get('hr.employee').browse(cr, uid, employee_id, fields_process=['job_level_person_id'])
                employee_level = employee.job_level_person_id and employee.job_level_person_id.name or 0
                
                if employee_level >= ground_level:
                    return True
        
        return False

    def create(self, cr, uid, vals, context=None):
        if not context:
            context = {}
        
        if vals.get('request_date', False) and len(vals['request_date']) > 10:
            vals['request_date'] = vals['request_date'][:10]
        
                
        context['action_from_ot'] = True
        vals['is_created'] = True
        
        
        res = super(vhr_ts_overtime, self).create(cr, uid, vals, context)

        if res:
            record = self.read(cr, uid, res, ['overtime_detail_ids'])
            overtime_detail_ids = record.get('overtime_detail_ids', [])
            if overtime_detail_ids:
                self.pool.get('vhr.ts.overtime.detail').check_overlap_ot_date(cr, uid, overtime_detail_ids)
            
            if vals.get('is_offline', False):
                mvals = {'state': 'finish'}
                self.write(cr, uid, res, mvals)

        return res

    def write(self, cr, uid, ids, vals, context=None):
        if not context:
            context = {}
        context['action_from_ot'] = True
        if not isinstance(ids, list):
            ids = [ids]
        
            
        record = self.read(cr, uid, ids[0], ['state'])
        old_state = record.get('state','')
        
        res = super(vhr_ts_overtime, self).write(cr, uid, ids, vals, context)
        #Update state for overtime detail
        if res:
            if vals.get('overtime_detail_ids'):
                overtime_detail_ids = []
                records = self.read(cr, uid, ids, ['overtime_detail_ids'])
                for record in records:
                    overtime_detail_ids.extend(record.get('overtime_detail_ids', []))
                if overtime_detail_ids:
                    self.pool.get('vhr.ts.overtime.detail').check_overlap_ot_date(cr, uid, overtime_detail_ids)

            if vals.get('state', False):
                list_state = [item[0] for item in STATES]
                overtime_detail_pool = self.pool.get('vhr.ts.overtime.detail')
                detail_ids = overtime_detail_pool.search(cr, uid, [('overtime_id', 'in', ids)])
                if detail_ids:
                    details = overtime_detail_pool.read(cr, uid, detail_ids, ['state'])
                    if not context.get('force_to_update_state_ot_detail', False):
                        for detail in details:
                            if list_state.index(vals['state']) <= list_state.index(detail['state']):
                                detail_ids.remove(detail.get('id', False))

                    if detail_ids:
                        mcontext = {}
                        if context.get('action_from_ot_reject', False):
                            mcontext['action_from_ot'] = True
                            
                        overtime_detail_pool.write(cr, uid, detail_ids, {'state': vals['state']}, context=mcontext)
                
                #Only send mail when have action move to next state        
                if list_state.index(old_state) <= list_state.index(vals['state']):
                    self.check_send_mail_late(cr, uid, ids, vals, {'old_state': old_state})
        
        return res
    
    def check_send_mail_late(self, cr, uid, ids, vals, context=None):
        '''
        Check to send mail with OT pay money in case submit/approve late to next timesheet period
        '''
        if not context:
            context = {}
        if ids and vals:
            if not isinstance(ids, list):
                ids = [ids]
            
            old_state = context.get('old_state','')
            #Check if date_off in a period and submit/approve in next period, send mail to notice
            approve_time = datetime.strptime(time.strftime(DEFAULT_SERVER_DATETIME_FORMAT), DEFAULT_SERVER_DATETIME_FORMAT) 
            log.info('\n\n\n Current time is :%s' % approve_time)
            
            param = 'hours_check_submit_ot_late'
            if vals.get('state',False) == 'finish':
                param = 'hours_check_approve_ot_late'
                
            gap_hours = self.pool.get('ir.config_parameter').get_param(cr, uid, param)or ''
            gap_hours = gap_hours.split(',')
            try:
                gap_hours = gap_hours and gap_hours[0]
                gap_hours = int(gap_hours) - 7
            except Exception as e:
                log.exception(e)
                raise osv.except_osv(_('Validation Error !'), _("Can not convert value to integer from ir_config_parameter with key '%s' !")%param)
            
            for record in self.browse(cr, uid, ids):
                employee_id = record.employee_id and record.employee_id.id or False
                ot_lines = record.overtime_detail_ids
                
                is_send_mail = False
                for ot_line in ot_lines:
                    if ot_line.is_compensation_leave:
                        continue
                    date = ot_line.date_off
                    sql = '''
                            SELECT ts_detail.close_date
                                                     FROM vhr_ts_timesheet_detail ts_detail INNER JOIN
                                                          vhr_ts_emp_timesheet  emp_ts 
                                                      ON ts_detail.timesheet_id =emp_ts.timesheet_id
                                                      
                            WHERE emp_ts.employee_id = %s AND 
                                  emp_ts.effect_from <= '%s' AND 
                                  ( emp_ts.effect_to >= '%s' OR emp_ts.effect_to is null  ) AND
                                  ts_detail.from_date <= '%s' AND 
                                  ts_detail.to_date >= '%s'
                          '''
                    cr.execute(sql%(employee_id, date,date,date,date))
                    res = cr.fetchall()
                    ts_details = [item[0] for item in res]
                    if ts_details:
                        close_date = ts_details[0]
                        if close_date:
                            close_date = datetime.strptime(close_date, DEFAULT_SERVER_DATE_FORMAT) 
                            
                            close_datetime = close_date + relativedelta(hours=gap_hours)
                            if approve_time > close_datetime:
                                is_send_mail = True
                                break
                            
                if is_send_mail:
                    self.send_mail(cr, uid, record.id, old_state, 'approve_late', context)
        
        return True



    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(vhr_ts_overtime, self).fields_view_get(cr, uid, view_id, view_type, context,
                                                           toolbar=toolbar, submenu=submenu)
        if context is None:
            context = {}
        if view_type == 'form':
            doc = etree.XML(res['arch'])
            if res['type'] == 'form':
                # When view view_vhr_working_record_submit_form
                # To add field text action_comment
                if context.get('action', False) and context.get('active_id', False):
                    node = doc.xpath("//form/separator")
                    if node:
                        node = node[0].getparent()
                        if context.get('required_comment', False):
                            node_notes = etree.Element('field', name="action_comment", colspan="4",
                                                       modifiers=json.dumps({'required': True}))
                        else:
                            node_notes = etree.Element('field', name="action_comment", colspan="4")
                        node.append(node_notes)
                        res['arch'] = etree.tostring(doc)
                        res['fields'].update({
                            'action_comment': {'selectable': True, 'string': 'Action Comment', 'type': 'text',
                                               'views': {}}})
                
                if context.get('ot_registration', False):
                    #Button Delete in Leave Registration
                    btn_del = doc.xpath("//button[@name='delete_record']")
                    if btn_del:
                        modifiers = json.loads(btn_del[0].get('modifiers') or '{}')
                        modifiers.update({'invisible': ['|',('is_created', '=', False),('state','!=','draft')]})
                        btn_del[0].set('modifiers', json.dumps(modifiers))

                res['arch'] = etree.tostring(doc)
        return res
    
    def delete_record(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        self.unlink(cr, uid, ids, context)
        context = {'search_default_active_employee':1, 'type':'request','ot_registration':1,
                    'rule_for_tree_form': True,'delete':False}
        
        view_form_open = 'view_vhr_ts_overtime_form'
        ir_model_pool = self.pool.get('ir.model.data')
        view_form_result = ir_model_pool.get_object_reference(cr, uid, 'vhr_timesheet', view_form_open)
        view_form_id = view_form_result and view_form_result[1] or False
        
        return {
                'type': 'ir.actions.act_window',
                'name': "Overtime Registration",
                'view_type': 'form',
                'view_mode': 'form',
                'views': [(view_form_id or False, 'form')],
                'res_model': 'vhr.ts.overtime',
                'context': context,
                'target': 'current',
            }

    def open_window(self, cr, uid, ids, context=None):
        view_open = 'view_vhr_ts_overtime_submit_form'
        action = {
            'name': 'Notes',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.pool.get('ir.model.data').get_object_reference(cr, uid, 'vhr_timesheet', view_open)[1],
            'res_model': 'vhr.ts.overtime',
            'context': context,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': ids[0],
        }
        return action

    def execute_workflow(self, cr, uid, ids, context=None):

        if isinstance(ids, (int, long)):
            ids = [ids]
        if context is None: context = {}
        #         context['call_from_execute'] = True
        for record_id in ids:
            try:
                action_result = False
                record = self.read(cr, uid, record_id, ['state'])
                old_state = record.get('state', False)

                if old_state:
                    if context.get('action', False) in ['submit', 'approve']:
                        action_result = self.action_next(cr, uid, [record_id], context)

                    elif context.get('action', False) == 'return':
                        action_result = self.action_return(cr, uid, [record_id], context)

                    elif context.get('action', False) == 'reject':
                        action_result = self.action_reject(cr, uid, [record_id], context)
                    
                    if action_result:
                        record = self.read(cr, uid, record_id, ['state'])
                        new_state = record.get('state', False)
                        if old_state != new_state:
                            self.send_mail(cr, uid, record_id, old_state, new_state, context)
                    else:
                        raise osv.except_osv(_('Validation Error !'), _("You don't have permission to do this action"))
                            
                    if context.get('action') and action_result:
                        list_states = {item[0]: item[1] for item in STATES}
                        state_vals = {}

                        record = self.read(cr, uid, record_id, ['state'])
                        new_state = record.get('state', False)
                        state_vals['old_state'] = list_states[old_state]
                        state_vals['new_state'] = list_states[new_state]
#                         state_vals['create_uid'] = uid
                        state_vals['res_id'] = record_id
                        state_vals['model'] = self._name
                        if 'ACTION_COMMENT' in context:
                            state_vals['comment'] = context['ACTION_COMMENT']
                        self.pool.get('vhr.state.change').create(cr, uid, state_vals)

            except Exception as e:
                log.exception(e)
                try:
                    error_message = e.message
                    if not error_message:
                        error_message = e.value
                except:
                    error_message = ""
                raise osv.except_osv(_('Validation Error !'), _('Have error during execution record:\n %s!') % error_message)

        return True

    def action_next(self, cr, uid, ids, context=None):
        log.info('Change status to next state')
        if not context:
            context = {}
        if ids:
            record_id = ids[0]
            mcontext = context
            if self.is_person_do_action(cr, uid, [record_id], mcontext):
                vals = {}
                record = self.read(cr, uid, record_id, ['state'])
                state = record.get('state', False)

                list_state = [item[0] for item in STATES]
                index_new_state = list_state.index(state) + 1

                vals['state'] = list_state[index_new_state]
                res = self.write(cr, uid, [record_id], vals, mcontext)

                return True
            
        return False

    def action_reject(self, cr, uid, ids, context=None):
        if not context:
            context = {}
            
        log.info('Change status to cancel state')
        if ids:
            record_id = ids[0]
            if self.is_person_do_action(cr, uid, [record_id], context):
                context['action_from_ot_reject']=True
                self.write(cr, uid, [record_id], {'state': 'cancel'}, context)
                return True

        return False

    def action_return(self, cr, uid, ids, context=None):
        log.info('Change status to previous state')
        if not context:
            context = {}
        if ids:
            record_id = ids[0]
            if self.is_person_do_action(cr, uid, [record_id], context):
                vals = {}
                record = self.read(cr, uid, record_id, ['state'])
                state = record.get('state', False)

                list_state = [item[0] for item in STATES]

                index_new_state = list_state.index(state) - 1

                vals['state'] = list_state[index_new_state]
                #                 context['return_to_previous_state'] = True
                context['force_to_update_state_ot_detail'] = True
                self.write(cr, uid, [record_id], vals, context)

                return True

        return False

    def unlink(self, cr, uid, ids, context=None):
        overtime_sum_ids = []
        if ids:
            overtimes = self.browse(cr, uid, ids, fields_process=['overtime_detail_ids', 'state'])
            for overtime in overtimes:
                if overtime.state != 'draft':
                    raise osv.except_osv(_('Validation Error !'), _("You can only delete OT at state 'Requester' !"))
                overtime_details = overtime.overtime_detail_ids
                for overtime_detail in overtime_details:
                    overtime_sum_id = overtime_detail.overtime_sum_id and overtime_detail.overtime_sum_id.id or False
                    if overtime_sum_id:
                        overtime_sum_ids.append(overtime_sum_id)

        res = super(vhr_ts_overtime, self).unlink(cr, uid, ids, context)
        if res and overtime_sum_ids:
            self.pool.get('vhr.ts.overtime.summarize').calculate_value_from_overtime_detail(cr, SUPERUSER_ID,
                                                                                            overtime_sum_ids, context)
        return res
    
    def send_mail(self, cr, uid, record_id, state, new_state, context=None):
        if not context:
            context = {}
        context["search_all_employee"] = True
        if record_id and state and new_state:
            action_user = ''
            if context.get('action_user', False):
                action_user = context['action_user']
            else:
                user = self.pool.get('res.users').read(cr, uid, uid, ['login'])
                if user:
                    action_user = user.get('login','')
            
            log.info("Send mail in TS Overtime from old state %s to new state %s"% (state, new_state))
            if state in mail_process.keys():
                data = mail_process[state]
                is_have_process = False
                for mail_data in data:
                    if new_state == mail_data[0]:
                        is_have_process = True
                        mail_detail = mail_data[1]
                        vals = {'action_user':action_user, 'ot_id': record_id, 'reason': context.get('ACTION_COMMENT','')}
                        list_group_mail_to = mail_detail['to']
                                
                        list_mail_to, list_mail_cc_from_group_mail_to = self.get_email_to_send(cr, uid, record_id, list_group_mail_to, context)
                        mail_to = ';'.join(list_mail_to)
                        vals['email_to'] = mail_to
                        
                        if 'cc' in mail_detail:
                            list_group_mail_cc = mail_detail['cc']
                            
                            list_mail_cc, list_mail_cc_from_group_mail_cc = self.get_email_to_send(cr, uid, record_id, list_group_mail_cc, context)
                            list_mail_cc += list_mail_cc_from_group_mail_cc + list_mail_cc_from_group_mail_to
                            list_mail_cc = list(set(list_mail_cc))
                            mail_cc = ';'.join(list_mail_cc)
                            vals['email_cc'] = mail_cc
                        
                        link_email = self.get_url(cr, uid, record_id, context)
                        vals['link_email'] = link_email
                        context = {'action_from_email': mail_detail.get('action_from_email','') }
                        self.pool.get('vhr.sm.email').send_email(cr, uid, mail_detail['mail_template'], vals, context)
                
                if not is_have_process:
                    log.info("TS Overtime don't have mail process from old state %s to new state %s "%(state, new_state))
            
        return True
    
    def get_email_to_send(self, cr, uid, record_id, list, context=None):
        """
        Returl list email from list
        """
        res = []
        res_cc = []
        if list and record_id:
            for item in list:
                if item == 'requester':
                    mail = self.get_requester_mail(cr, uid, record_id, context)
                    if mail:
                        res.append(mail)
                elif item == 'lm':
                    mail = self.get_lm_mail(cr, uid, record_id, context)
                    if mail:
                        res.append(mail)
                    
                    #Send to delegator
                    record = self.browse(cr, uid, record_id, fields_process=['report_to'])
                    delegator_ids = self.pool.get('hr.holidays').get_delegator(cr, uid, record_id, record.report_to.id, self._name, context)
                    if delegator_ids:
                        delegators = self.pool.get('hr.employee').read(cr, uid, delegator_ids, ['work_email'])
                        delegate_mails = [delegator.get('work_email','') for delegator in delegators]
                        res.extend(delegate_mails)
                
                else:
                    mail_group_pool = self.pool.get('vhr.email.group')
                    mail_group_ids = mail_group_pool.search(cr, uid, [('code','=',item)])
                    if mail_group_ids:
                        mail_group = mail_group_pool.read(cr, uid, mail_group_ids[0], ['to_email','cc_email'])
                        to_email = mail_group.get('to_email','') or ''
                        cc_email = mail_group.get('cc_email','') or ''
                        mail_to  = to_email.split(';')
                        mail_cc  = cc_email.split(';')
                        res.extend(mail_to)
                        res_cc.extend(mail_cc)
                    
                    else:
                        log.info("Can't find mail for " + item)
        return res, res_cc
    
    def get_url(self, cr, uid, res_id, context=None):
        if isinstance(res_id, list):
            res_id = res_id[0]
        model_data = self.pool.get('ir.model.data')
        action_id = model_data.xmlid_lookup(cr, uid, 'vhr_timesheet.act_my_list_vhr_ts_overtime')[2]
        
        url = ''
        config_parameter = self.pool.get('ir.config_parameter')
        base_url = config_parameter.get_param(cr, uid, 'web.base.url')
        if base_url:
            url = base_url
        url += '/overtime/registration?ot_id=%s' % (res_id)
        return url
    
    def get_requester_mail(self, cr, uid, record_id, context=None):
        if not context:
            context = {}
        
        requester_mail = ''
        if record_id:
            meta_datas = self.perm_read(cr, SUPERUSER_ID, [record_id], context)
            user_id =  meta_datas and meta_datas[0] and meta_datas[0].get('create_uid', False) and meta_datas [0]['create_uid'][0] or False
            if user_id:
                context['search_all_employee'] = True
                employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', user_id)], 0, None, None,
                                                                   context)
                if employee_ids:
                    employee = self.pool.get('hr.employee').read(cr, uid, employee_ids[0], ['work_email'])
                    requester_mail = employee.get('work_email','')
        
        return requester_mail
    
    def get_lm_mail(self, cr, uid, record_id, context=None):
        
        mail = ''
        if record_id:
            record = self.browse(cr, uid, record_id, fields_process=['report_to'])
            mail = record.report_to and record.report_to.work_email or ''
         
        return mail
    
    
    def _needaction_domain_get(self, cr, uid, context=None):
        if not context:
            context = {}
        
        dom = False
        if context.get('type', False) == 'task':
            context['search_all_employee'] = True
            emp_obj = self.pool.get('hr.employee')
            empids = emp_obj.search(cr, uid, [('user_id', '=', uid)], context=context)
            dom = ['|','&', ('state', '=', 'draft'), ('requester_id', 'in', empids),
                       '&', ('state', '=', 'approve'), ('report_to', 'in', empids)]
        return dom

    def get_overtime_history(self, cr, uid, context=None):
        data = []
        if context is None:
            context = {}
        fields_lst = ['request_date', 'employee_code', 'employee_id', 'state', 'department_id']
        if uid:
            args = [('employee_id.user_id', '=', uid)]
            ot_ids = self.search(cr, uid, args, order='request_date desc', context=context)
            for item in self.read(cr, uid, ot_ids, fields_lst, context=context):
                item['department'] = item.get('department_id', False) and item['department_id'][1] or ''
                item['employee_name'] = item.get('employee_id', False) and item['employee_id'][1] or ''
                data.append(item)
        return data

    def get_overtime_approval(self, cr, uid, context=None):
        data = []
        if context is None:
            context = {}
        fields_lst = ['request_date', 'employee_code', 'employee_id', 'state', 'department_id']
        if uid:
            context.update({'type': 'task'})
            ot_ids = self.search(cr, uid, [], order='request_date desc', context=context)
            for item in self.read(cr, uid, ot_ids, fields_lst, context=context):
                item['department'] = item.get('department_id', False) and item['department_id'][1] or ''
                item['employee_name'] = item.get('employee_id', False) and item['employee_id'][1] or ''
                data.append(item)
        return data
    
    

vhr_ts_overtime()