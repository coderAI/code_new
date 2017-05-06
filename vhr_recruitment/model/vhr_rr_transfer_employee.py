# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields
from vhr_job_applicant import CANDIDATE_EMPLOYEE, OFFER_APPLICANT_EMPLOYEE
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
import simplejson as json
from lxml import etree
from datetime import datetime

log = logging.getLogger(__name__)


class vhr_rr_transfer_employee(osv.osv):
    _name = 'vhr.rr.transfer.employee'
    _description = 'VHR RR Transfer Employee'
    
    
    def _is_person_do_action(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if not ids:
            return True
        if not isinstance(ids, list):
            ids = [ids]
        if not context:
            context = {}
        for record_id in ids:
            res[record_id] = self.is_person_do_action(cr, uid, [record_id], context)
            
        return res
    
    _columns = {
        'name': fields.char('Vietnamese Name', size=512),
        'job_applicant_id': fields.many2one('vhr.job.applicant', 'Job Applicant', ondelete='restrict'),
        
        'applicant_id': fields.related('job_applicant_id', 'applicant_id', readonly=True, type='many2one', relation='hr.applicant',
                                       string='Candidate Name'),
        'offer_job_type': fields.related('job_applicant_id', 'offer_job_type', readonly=True, type='many2one', relation='vhr.dimension',
                                       string='Job Type'),
        'offer_com_group_id': fields.related('job_applicant_id', 'offer_com_group_id', readonly=True, type='many2one', relation='vhr.company.group',
                                       string='Group Company'),
        'offer_company_id': fields.related('job_applicant_id', 'offer_company_id', readonly=True, type='many2one', relation='res.company',
                                       string='Working For'),
        'offer_department': fields.related('job_applicant_id', 'offer_department', readonly=True, type='many2one', relation='hr.department',
                                       string='Department'),
        'offer_team_id': fields.related('job_applicant_id', 'offer_team_id', readonly=True, type='many2one', relation='hr.department',
                                       string='Team'),
        'contract_type_id': fields.related('job_applicant_id', 'contract_type_id', readonly=True, type='many2one', relation='hr.contract.type', 
                                           string='Probationary type'),
        'join_date': fields.related('job_applicant_id', 'join_date', readonly=True, type='date',
                                           string='Start Date'),
        'offer_gross_salary': fields.related('job_applicant_id', 'offer_gross_salary', readonly=True, type='float',
                                           string='Salary (Gross)'),
        'offer_probation_salary': fields.related('job_applicant_id', 'offer_probation_salary', readonly=True, type='float',
                                           string='Probation Salary'),
        
        'offer_job_title_id': fields.related('job_applicant_id', 'offer_job_title_id', readonly=True, type='many2one', relation='vhr.job.title', 
                                           string='Title Offer'),
        'offer_job_level_id': fields.related('job_applicant_id', 'offer_job_level_id', readonly=True, type='many2one', relation='vhr.job.level', 
                                           string='Level Offer'),
        'emp_id': fields.related('job_applicant_id', 'emp_id', readonly=True, type='many2one', relation='hr.employee', 
                                           string='Employee'),
        'employee_code': fields.related('emp_id', 'code', readonly=True, type='char',
                                           string='Employee Code'),
        'ex_employee': fields.related('job_applicant_id', 'ex_employee', readonly=True, type='boolean', string='Ex-employee'),
        
        'is_create_account': fields.selection([('yes', 'Yes'), ('no', 'No')], 'Create account'),
        'is_asset': fields.selection([('yes', 'Yes'), ('no', 'No')], 'Asset'),
                
                
        'state': fields.selection([('draft', 'Waiting'),
                                   ('finish', 'Transfered'),
                                   ], 'Status'),
        'is_person_do_action': fields.function(_is_person_do_action, type='boolean', string='Is Person Do Action'),
        'state_log_ids': fields.one2many('vhr.state.change', 'res_id', 'History', domain=[('model', '=', _name)]),

    }

    _defaults = {
                 'state': 'draft',
                 'is_person_do_action': True
    }
    
    def name_get(self, cr, uid, ids, context=None):
        if not ids or False in ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        
        reads = self.read(cr, uid, ids, ['applicant_id'], context=context)
        res = []
        for record in reads:
                name = record.get('applicant_id',False) and record['applicant_id'][1]
                res.append((record['id'], name))
        return res
    
    def open_window(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        
        view_open = 'view_vhr_rr_transfer_employee_submit_form'
        if context.get('view_open',False):
            view_open = context['view_open']
        
        action = {
            'name': 'Notes',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.pool.get('ir.model.data').get_object_reference(cr, uid, 'vhr_recruitment', view_open)[1],
            'res_model': 'vhr.rr.transfer.employee',
            'context': context,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': ids[0],
        }
        return action
    
    def is_person_do_action(self, cr, uid, ids, context=None):
        if ids:
            groups = self.pool.get('res.users').get_groups(cr, uid)
            
            record = self.read(cr, uid, ids[0], ['state'])
            state = record.get('state', False)
            
            if  (state == 'draft' and set(['vhr_cb']).intersection(groups) ):
                return True
        
            log.info("User with uid %s don't have right to do action in record %s at state %s" % (uid,ids[0],state ))
        else:
            log.info('ids not exist for check is_person_do_action')
        return False
    
    def execute_workflow(self, cr, uid, ids, context=None):
        if ids:
            emp_obj = self.pool.get('hr.employee')
            app_obj = self.pool.get('hr.applicant')
            job_app_obj = self.pool.get('vhr.job.applicant')
            working_obj = self.pool.get('vhr.working.record')
            
            for record in self.read(cr, uid, ids, ['job_applicant_id']):
                job_applicant_id = record.get('job_applicant_id', False) and record['job_applicant_id'][0]
                if job_applicant_id:
                    offer_data = job_app_obj.read(cr, uid, job_applicant_id, [], context=context)
                    res_emp = {}
                    if offer_data:
                        if offer_data.get('ex_employee', False):
                            if not offer_data.get('emp_id', False):
                                raise osv.except_osv('Validation Error !', 'Please choose employee or uncheck ex_employee')
                            else:
                                res_emp['employee_id'] = offer_data['emp_id']
                                
                                #Raise error if submit with employee still have active WR at join_date
                                join_date = offer_data.get('join_date', False)
                                if isinstance(res_emp['employee_id'], tuple):
                                    employee_id = res_emp.get('employee_id', False) and res_emp['employee_id'][0]
                                
                                offer_company_id = offer_data.get('offer_company_id', False)
                                if isinstance(offer_company_id, tuple):
                                    offer_company_id = offer_company_id and offer_company_id[0]
                                dismiss_form_ids = working_obj.get_dismiss_change_form_ids(cr, uid)
                                active_wr_ids = working_obj.search(cr, uid, [('employee_id','=',employee_id),
                                                                             ('company_id','=',offer_company_id),
                                                                             ('change_form_ids','not in',dismiss_form_ids),
                                                                             ('effect_from','<=', join_date),
                                                                             '|',
                                                                                ('effect_to','=', False),
                                                                                ('effect_to','>=',join_date),
                                                                             ])
                                if active_wr_ids:
                                    join_date = datetime.strptime(join_date, DEFAULT_SERVER_DATE_FORMAT)
                                    join_date = join_date.strftime('%d-%m-%Y')
                                    raise osv.except_osv('Validation Error !', 'Employee(s) still have active Working Record on %s' % join_date)
                        
                        applicant_id = []
                        if offer_data.get('applicant_id', False):
                            applicant_id = offer_data['applicant_id'][0]
                            app_data = app_obj.read(cr, uid, applicant_id, [], context=context)
                            if app_data:
                                app_obj_columns = app_obj._columns
                                for can_key, emp_key in CANDIDATE_EMPLOYEE.iteritems():
                                    type_column = app_obj_columns[can_key]._type
                                    if type_column == 'many2one':
                                        res_emp[emp_key] = app_data.get(can_key, False) and app_data[can_key][0] or False
                                    else:
                                        res_emp[emp_key] = app_data.get(can_key, False)
            
                        columns = job_app_obj._columns
                        for offer_key, emp_key in OFFER_APPLICANT_EMPLOYEE.iteritems():
                            type_column = offer_key != 'id' and columns[offer_key]._type or ''
                            if type_column == 'many2one':
                                res_emp[emp_key] = offer_data.get(offer_key, False) and offer_data[offer_key][0] or False
                            else:
                                res_emp[emp_key] = offer_data.get(offer_key, False)
                            
                            #Get for level by person
                            if offer_key == 'offer_job_level_position_id':
                                res_emp['job_level_person_id']= res_emp[emp_key]
                                
                        if res_emp.get('last_name', False) and res_emp.get('first_name', False):
                            res_emp['name'] = u'%s %s' % (res_emp['last_name'], res_emp['first_name'])   
                    
                    department_group_id = res_emp.get('department_group_id', False)
                    if department_group_id:
                        group = self.pool.get('hr.department').read(cr, uid, department_group_id, ['name','organization_class_id'], context=context)
                        
                        organization_class_id = group.get('organization_class_id', False) and group['organization_class_id'][0] or False
                        if organization_class_id:
                            organization_class = self.pool.get('vhr.organization.class').read(cr, uid, organization_class_id, ['level'])
                            level = organization_class.get('level',0)
                            if level == 1:    
                                res_emp['division_id'] = res_emp['department_group_id']
                                res_emp['department_group_id'] = False
                                
                    emp_id = emp_obj.create_employee_from_candidate(cr, uid, res_emp, context=context)
                    if not emp_id:
                        raise osv.except_osv('Validation Error !', 'Can not create employee, please check input data!')
                    if not offer_data.get('ex_employee', False) and not offer_data.get('emp_id', False):
                        app_obj.write(cr, uid, [applicant_id], {'emp_id': emp_id, 'ex_employee': True}, context=context)
                
                self.write_log_state_change(cr, uid, record['id'], 'draft', 'finish', context)
                self.write(cr, uid, record['id'], {'state': 'finish'})
                
    
    def write_log_state_change(self, cr, uid, record_id, old_state, new_state, context=None):
        if not context:
            context = {}
        state_vals = {}
        state_vals['old_state'] = old_state
        state_vals['new_state'] = new_state
#         state_vals['create_uid'] = uid
        state_vals['res_id'] = record_id
        state_vals['model'] = self._name
        if 'ACTION_COMMENT' in context:
            state_vals['comment'] = context['ACTION_COMMENT']
        self.pool.get('vhr.state.change').create(cr, uid, state_vals)
        return True
    
    def create(self, cr, uid, vals, context=None):
        log.info("Create transfer Employee")
        res = super(vhr_rr_transfer_employee, self).create(cr, uid, vals)
        if res:
            self.pool.get('vhr.job.applicant').write(cr, uid, vals.get('job_applicant_id', False), {'transfer_id': res})
        
        return res
        
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_rr_transfer_employee, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res
    
    def fields_view_get(self, cr, uid, view_id = None, view_type = 'form', context = None, toolbar = False, submenu = False):
        res = super(vhr_rr_transfer_employee, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar = toolbar, submenu = submenu)
        if context is None:
            context = {}
        if view_type == 'form':
            res = self.add_attrs_for_field(cr, uid, res, context)
        return res
    
    def add_attrs_for_field(self, cr, uid, res, context=None):
        doc = etree.XML(res['arch'])
        if res['type'] == 'form':
            #When view view_vhr_working_record_submit_form
            #To add field text action_comment 
            if context.get('action',False) and context.get('active_id', False):
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


vhr_rr_transfer_employee()