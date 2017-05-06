# -*-coding:utf-8-*-
import logging
import thread
import sys
import re
import simplejson as json

from openerp import SUPERUSER_ID
from openerp.osv import osv, fields
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from lxml import etree
from openerp import tools
from openerp.addons.vhr_human_resource.model.vhr_working_record import dict_fields
from openerp.addons.vhr_human_resource.model.vhr_working_record import dict_salary_fields

log = logging.getLogger(__name__)

FIELD_PARENT_AFFECTS = {'team_id_new':              ['department_id_new','division_id_new'],
                        'department_id_new':        ['division_id_new'],
                        'department_group_id_new':  ['division_id_new'],
                        'pro_sub_group_id_new':     ['pro_job_family_id_new','pro_job_group_id_new'],
                        'pro_job_group_id_new':     ['pro_job_family_id_new'],
                        'pro_grade_id_new':         ['pro_ranking_level_id_new'],
                        'mn_sub_group_id_new':      ['mn_job_family_id_new','mn_job_group_id_new'],
                        'mn_job_group_id_new':      ['mn_job_family_id_new'],
                        'mn_grade_id_new':          ['mn_ranking_level_id_new'],
                        'salary_percentage_new':    ['gross_salary_new','basic_salary_new'],
                        'basic_salary_new':         ['gross_salary_new'],
                        'kpi_amount_new':           ['gross_salary_new','basic_salary_new'],
#                         'general_allowance_new':    ['gross_salary_new','basic_salary_new'],
                        'v_bonus_salary_new':    ['gross_salary_new','basic_salary_new'],
                        'collaboration_salary_new': ['gross_salary_new','basic_salary_new'],
                 }

class vhr_working_record_mass_movement(osv.osv):
    _name = 'vhr.working.record.mass.movement'
    _description = 'Mass Movement Working Record'
    
    def _is_able_to_create(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if not ids:
            return True
        if not isinstance(ids, list):
            ids = [ids]
        
        for record_id in ids:
            res[record_id] = True
        return res
    
    def _get_data_from_change_form(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for record in self.browse(cr, uid, ids, fields_process=['change_form_ids']):
            fields_name = []
            if record.change_form_ids:
                for change_form in record.change_form_ids:
                    access_field_ids = change_form.access_field_ids
                    if access_field_ids:
                        for field in access_field_ids:
                            fields_name.append(field.name or '')
            fields_name = list(set(fields_name))
            res[record.id] = ', '.join(fields_name)
        return res
    
    def is_change_salary_percentage_by_hand(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if not isinstance(ids, list):
            ids = [ids]
        
        for record_id in ids:
            res[record_id] = True
        
        return res
    
    def _get_is_change_team(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if not isinstance(ids, list):
            ids = [ids]
        
        for record_id in ids:
            res[record_id] = False
        
        return res
    
    def _get_is_required_attachment(self, cr, uid, ids, field_name, arg, context=None):
        '''
            Bắt buộc attach file khi submit đối với Multi Request
        '''
        res = {}
        if not isinstance(ids, list):
            ids = [ids]
        
        for record_id in ids:
            res[record_id] = True
        
        return res
    
    _columns = {
                'name': fields.char('Name', size=64),
                'company_id': fields.many2one('res.company', 'Entity', ondelete='restrict'),
                'effect_from': fields.date('Effective From'),
                'decision_no': fields.char('Decision No', size=128),
                'sign_date': fields.date('Signing Date'),
                'signer_id': fields.char('Signer',size=64),
                'signer_job_title_id': fields.char("Signer Job Title", size=128),
                'note': fields.text('Note'),
                'division_id_old': fields.many2one('hr.department', 'Division', domain=[('organization_class_id.level','=', '1')], ondelete='restrict'),
                'department_group_id_old': fields.many2one('hr.department', 'Department Group', domain=[('organization_class_id.level','=', '2')], ondelete='restrict'), 
                'department_id_old': fields.many2one('hr.department', 'Department', domain=[('organization_class_id.level','=', '3')], ondelete='restrict'),

                'work_for_company_id_new': fields.many2one('res.company', 'Work for Company', ondelete='restrict'),
                'office_id_new': fields.many2one('vhr.office', 'Office', ondelete='restrict'),
                'division_id_new': fields.many2one('hr.department', 'Business Unit', domain=[('organization_class_id.level','=', '1')], ondelete='restrict'),
                'department_group_id_new': fields.many2one('hr.department', 'Department Group', domain=[('organization_class_id.level','=', '2')], ondelete='restrict'), 
                'department_id_new': fields.many2one('hr.department', 'Department', domain=[('organization_class_id.level','=', '3')], ondelete='restrict'),
                'team_id_new': fields.many2one('hr.department', 'Team', domain=[('organization_class_id.level','>=', '4')], ondelete='restrict'),
                'job_title_id_new': fields.many2one('vhr.job.title', 'Title', ondelete='restrict'),
                'job_level_id_new': fields.many2one('vhr.job.level', 'Level', ondelete='restrict'),
                
                #new job level
                'job_level_position_id_new': fields.many2one('vhr.job.level.new', 'Position Level', ondelete='restrict'),
                'job_level_person_id_new': fields.many2one('vhr.job.level.new', 'Person Level', ondelete='restrict'),
                
                 #LuanNG: Remove this field in future version of vHRS
                'position_class_id_new': fields.many2one('vhr.position.class', 'Position Class', ondelete='restrict'),
                'report_to_new': fields.many2one('hr.employee', 'Reporting Line', ondelete='restrict'),
#                 'approver_id_new': fields.many2one('hr.employee', 'Approver', ondelete='restrict'),
#                 'mentor_id_new': fields.many2one('hr.employee', 'Mentor', ondelete='restrict'),
                'manager_id_new': fields.many2one('hr.employee', 'Dept Head', ondelete='restrict'),
                
                'employee_ids': fields.many2many('hr.employee', 'working_record_mass_movement_employee_rel', 'wr_mass_movement_id', 'employee_id', 'Employees'),
                
                'salary_setting_id_new': fields.many2one('vhr.salary.setting', 'Type of salary', ondelete='restrict'),
                
                'seat_new': fields.char('Seat No', size=32),
                'ext_new': fields.char('Ext', size=32),
                'work_phone_new': fields.char('Office phone', size=32),
                'work_email_new': fields.char('Working email', size=32),
                'mobile_phone_new': fields.char('Cell phone', size=32),
                
                'pro_job_family_id_new': fields.many2one('vhr.job.family','Pro Job Family',ondelete='restrict',domain=[('track_id.code','=', 'Professional')]),
                'pro_job_group_id_new': fields.many2one('vhr.job.group','Pro Job Group',ondelete='restrict'),
                'pro_sub_group_id_new': fields.many2one('vhr.sub.group','Pro Sub Group',ondelete='restrict'),
                'pro_ranking_level_id_new': fields.many2one('vhr.ranking.level','Pro Level',ondelete='restrict'),
                'pro_grade_id_new': fields.many2one('vhr.grade','Pro Grade',ondelete='restrict'),
                
                'mn_job_family_id_new': fields.many2one('vhr.job.family','Management Job Family',ondelete='restrict',domain=[('track_id.code','=', 'Management')]),
                'mn_job_group_id_new': fields.many2one('vhr.job.group','Management Job Group',ondelete='restrict'),
                'mn_sub_group_id_new': fields.many2one('vhr.sub.group','Management Sub Group',ondelete='restrict'),
                'mn_ranking_level_id_new': fields.many2one('vhr.ranking.level','Management Level',ondelete='restrict'),
                'mn_grade_id_new': fields.many2one('vhr.grade','Management Grade',ondelete='restrict'),
        
                'gross_salary_new': fields.float('Gross Salary'),
                'basic_salary_new': fields.float('Basic Salary'),
                'kpi_amount_new': fields.float('KPI'),
                'general_allowance_new': fields.float('General Allowance'),
                'v_bonus_salary_new': fields.float('V_Bonus'),
                'salary_percentage_new': fields.float('% Split Salary'),
                'collaboration_salary_new': fields.float('Collaboration Salary'),
        
                'is_public': fields.boolean('Is Public'),
                
                'change_form_ids':fields.many2many('vhr.change.form','working_mass_change_form_rel','working_mass_id','change_form_id','Change Form'),
                'is_able_to_create': fields.function(_is_able_to_create, type='boolean', string='Is Able To Create'),
                'is_change_form_adjust_salary': fields.boolean('Is Change Form Adjust Salary'),
                'fields_affect_by_change_form': fields.function(_get_data_from_change_form, type='text', string="Fields Affect By Change Form"),
                'is_change_salary_percentage_by_hand': fields.function(is_change_salary_percentage_by_hand, type='boolean', string='Is Change Salary Percentage By Hand'),
                'is_change_basic_salary_by_hand': fields.function(is_change_salary_percentage_by_hand, type='boolean', string='Is Change Basic Salary By Hand'),
                'attachment_ids': fields.one2many('ir.attachment', 'res_id', 'Attachment', domain=[('res_model', '=', _name)]),
                'is_required_attachment': fields.function(_get_is_required_attachment, type='boolean', string="Is Require Attachment"),
                'is_change_team': fields.function(_get_is_change_team, type='boolean', string="Is Change Team"),

    }
    
    def _get_default_company_id(self, cr, uid, context=None):
        company_ids = self.pool.get('res.company').search(cr, uid, [('is_member', '=', False)], order="id asc")
        if company_ids:
            return company_ids[0]

        return False
    
    def _get_is_able_to_create(self, cr, uid, context=None):
        """
        Only allow 'vhr_assistant_to_hrbp','vhr_hrbp','vhr_cb_working_record' to create request, multi request, mass request
        """
        if not context:
            context = {}
        
        context['title_request'] = 'Multi Request'
        return self.pool.get('vhr.working.record').check_is_able_to_create_request(cr, uid, context)
    
    _defaults = {
        'name': 'Mass',
        'is_public': True,
        'company_id': _get_default_company_id,
        'salary_percentage_new': 0,
        'is_able_to_create': _get_is_able_to_create,
        'is_change_salary_percentage_by_hand': True,
        'is_change_basic_salary_by_hand': True,
        'is_change_team': False
    }
    
    def is_hrbp_assistant_hrbp(self, cr, uid, context=None):
        groups = self.pool.get('vhr.working.record').get_groups(cr, uid)
        if set(['vhr_hrbp','vhr_assistant_to_hrbp']).intersection(set(groups)):
            return True
        
        return False
    
    def onchange_company_id(self, cr, uid, ids, company_id, effect_from, context=None):
        res = {'employee_ids': []}
#         domain = {'employee_ids': [('id', 'in', [])]}
#         if company_id and effect_from:
#             employee_ids = self.get_list_employee_belong_to_company_can_choose(cr, uid, company_id, effect_from, context)
#             domain = {'employee_ids': [('id', 'in', employee_ids)]}
        
        return {'value': res}
    
    def onchange_effect_from(self, cr, uid, ids, company_id, effect_from, context=None):
        res = {'employee_ids': []}
#         domain = {'employee_ids': [('id', 'in', [])]}
#         if company_id and effect_from:
#             employee_ids = self.get_list_employee_belong_to_company_can_choose(cr, uid, company_id, effect_from, context)
#             domain = {'employee_ids': [('id', 'in', employee_ids)]}
        
        return {'value': res}
    
    
#     def get_list_employee_belong_to_company_can_choose(self, cr, uid, company_id, effect_from, context=None):
#         """
#         Return list employee have contract effect on company_id at effect_from, login user can choose
#         """
#         employee_ids = []
#         if company_id and effect_from:
#             contract_obj = self.pool.get('hr.contract')
#             contract_ids = contract_obj.search(cr, uid, [('company_id', '=', company_id),
#                                                          ('date_start','<=',effect_from),
#                                                          ('state','=','signed'),
#                                                          '|','|',
#                                                              ('liquidation_date','>=',effect_from),
#                                                          '&',('date_end','>=',effect_from),('liquidation_date','=',False),
#                                                          '&',('date_end','=',False),('liquidation_date','=',False)])
#             
#             if contract_ids:
#                 contracts = contract_obj.read(cr, uid, contract_ids, ['employee_id'], context=context)
#                 for contract in contracts:
#                     employee_id = contract.get('employee_id',False) and contract['employee_id'][0]
#                     employee_ids.append(employee_id)
#             
#             #Get list employee can choose base on permission of employee
#             use_employee_ids = self.pool.get('vhr.working.record').get_list_employee_can_use(cr, uid, context)
#             if use_employee_ids:
#                 if use_employee_ids != 'all_employees':
#                     employee_ids = list( set(employee_ids).intersection(set(use_employee_ids)) )
#             else:
#                 employee_ids =  []
#         
#         return employee_ids
    
#     def onchange_signer_id(self, cr, uid, ids, signer_id, context=None):
#         value = {}
#         if signer_id:
#             signer_info = self.pool.get('hr.employee').read(cr, uid, signer_id, ['title_id'])
#             title_id = signer_info.get('title_id', False) and signer_info['title_id'][0] or False
#             value['signer_job_title_id'] = title_id
#         
#         return {'value': value}
    
    def onchange_division_id_old(self, cr, uid, ids, division_id, context=None):
        res = {'department_id_old': False,'employee_ids': [], 'department_group_id_old': False}
        
        res['division_id_new'] = division_id
        
        return {'value': res}
    
    def onchange_department_group_id_old(self, cr, uid, ids, department_group_id_old, context=None):
        res = {'department_id_old': False,'employee_ids': []}
        
        res['department_group_id_new'] = department_group_id_old
        
        return {'value': res} 
    
    def onchange_department_id_old(self, cr, uid, ids, department_id_old, division_id_old,division_id_new, context=None):
        res = {'employee_ids': []}
        
        if division_id_old and division_id_new and division_id_old == division_id_new:
            res['department_id_new'] = department_id_old
        
        return {'value': res}
    
    def onchange_office_id_new(self, cr, uid, ids, context=None):
        return {'value': {'division_id_new': False} }
        
    def onchange_division_id_new(self, cr, uid, ids, context=None):
        res = {'department_group_id_new': False,
               'department_id_new': False,
               'manager_id_new': False,
               'team_id_new': False
               }
        
        return {'value': res}   
    
    def onchange_department_group_id_new(self, cr, uid, ids, context=None):
        res = {'department_id_new': False,
               'manager_id_new': False,
               'team_id_new': False
               }
        
        return {'value': res}   
    
    def onchange_department_id_new(self, cr, uid, ids, department_id, context=None):
        res = {'manager_id_new': False, 'team_id_new': False, 'report_to_new': False}
        if department_id:
            department_info = self.pool.get('hr.department').read(cr, uid, department_id, ['manager_id'])
            manager_id = department_info.get('manager_id', False) and department_info['manager_id'][0] or False   
            res['manager_id_new'] = manager_id
            res['report_to_new'] = manager_id
        return {'value': res}
    
    def onchange_team_id_new(self, cr, uid, ids, team_id, context=None):
        res = {}
        if team_id:
            department_info = self.pool.get('hr.department').read(cr, uid, team_id, ['manager_id'])
            manager_id = department_info.get('manager_id', False) and department_info['manager_id'][0] or False   
            res['report_to_new'] = manager_id
            
        return {'value': res}
    
    def onchange_change_form_ids(self, cr, uid, ids, change_form_ids, fields_affect_by_change_form, division_id_old, department_group_id_old, department_id_old, context=None):
        res = {'is_change_form_adjust_salary': False, 'gross_salary_new': 0,'salary_percentage_new': 0,
               'basic_salary_new': 0,'kpi_amount_new':0,'general_allowance_new':0,'v_bonus_salary_new':0,
               'fields_affect_by_change_form': '','is_change_team': False,'division_id_old': False,'department_group_id_old': False,
               'department_id_old': False}
        fields_name  = []
        
        config_parameter = self.pool.get('ir.config_parameter')
        code_change_team = config_parameter.get_param(cr, uid, 'vhr_human_resource_change_form_code_internal_department_move') or ''
        code_change_team_list = code_change_team.split(',')
                
        if change_form_ids and change_form_ids[0] and len(change_form_ids[0]) == 3 and change_form_ids[0][2]:
            change_form_ids = change_form_ids[0][2]
            change_forms = self.pool.get('vhr.change.form').browse(cr, uid, change_form_ids)
            for change_form in change_forms:
                access_field_ids = change_form.access_field_ids
                if access_field_ids:
                    for field in access_field_ids:
                        fields_name.append(field.name or '')
                if change_form.is_salary_adjustment:
                    res = {'is_change_form_adjust_salary': True}
                
                if change_form.code in code_change_team_list:
                    res['is_change_team'] = True
                    if 'division_id_old' in res:
                        del res['division_id_old']
                        del res['department_group_id_old']
                        del res['department_id_old']
#                     return {'value': res}
            
        if fields_affect_by_change_form:
            old_fields_affect = fields_affect_by_change_form.split(',')
            old_fields_affect = [item.strip() for item in old_fields_affect]
            fail_fields = [item for item in old_fields_affect if item not in fields_name]
            for field in fail_fields:
                res[field] = False
                if field == 'division_id_new' and res['is_change_team']:
                    res[field] = division_id_old
                
                elif field == 'department_group_id_new' and res['is_change_team']:
                    res[field] = department_group_id_old
                    
                elif field == 'department_id_new' and res['is_change_team']:
                    res[field] = department_id_old
            
        fields_name = list(set(fields_name))
        res['fields_affect_by_change_form'] = ', '.join(fields_name)
                    
        return {'value': res}
    
    def onchange_job_title_id_new(self, cr, uid, ids, job_title_id, job_level_id, pro_sub_group_id_new, context=None):
        return self.pool.get('vhr.working.record').onchange_job_title_id(cr, uid, ids, job_title_id, job_level_id, pro_sub_group_id_new, False, context)
    
    def onchange_pro_job_family_id_new(self, cr, uid, ids, pro_job_family_id_new, pro_job_group_id_new, context=None):
        return self.pool.get('vhr.working.record').onchange_pro_job_family_id_new(cr, uid, ids, pro_job_family_id_new, pro_job_group_id_new, context)
    
    def onchange_pro_job_group_id_new(self, cr, uid, ids, pro_job_group_id_new, pro_sub_group_id_new, context=None):
        return self.pool.get('vhr.working.record').onchange_pro_job_group_id_new(cr, uid, ids, pro_job_group_id_new, pro_sub_group_id_new, context)
    
    def onchange_pro_ranking_level_id_new(self, cr, uid, ids, pro_ranking_level_id_new, pro_grade_id_new, context=None):
        return self.pool.get('vhr.working.record').onchange_pro_ranking_level_id_new(cr, uid, ids, pro_ranking_level_id_new, pro_grade_id_new, context)

    def onchange_mn_job_family_id_new(self, cr, uid, ids, mn_job_family_id_new, mn_job_group_id_new, context=None):
        return self.pool.get('vhr.working.record').onchange_mn_job_family_id_new(cr, uid, ids, mn_job_family_id_new, mn_job_group_id_new, context)
    
    def onchange_mn_job_group_id_new(self, cr, uid, ids, mn_job_group_id_new, mn_sub_group_id_new ,context=None):
        return self.pool.get('vhr.working.record').onchange_mn_job_group_id_new(cr, uid, ids, mn_job_group_id_new, mn_sub_group_id_new, context)

    def onchange_mn_ranking_level_id_new(self, cr, uid, ids, mn_ranking_level_id_new, mn_grade_id_new, context=None):
        return self.pool.get('vhr.working.record').onchange_mn_ranking_level_id_new(cr, uid, ids, mn_ranking_level_id_new, mn_grade_id_new, context)
    
    
    def onchange_gross_salary(self, cr, uid, ids, gross_salary, basic_salary, kpi_amount, salary_percentage, is_change_salary_percentage_by_hand, context=None):
        return self.pool.get('vhr.working.record').onchange_gross_salary(cr, uid, ids, gross_salary, basic_salary, kpi_amount, salary_percentage, is_change_salary_percentage_by_hand, context)
    
    def onchange_salary_percentage(self, cr, uid, ids, gross_salary, basic_salary, kpi_amount, salary_percentage, is_change_salary_percentage_by_hand, context=None):
        return self.pool.get('vhr.working.record').onchange_salary_percentage(cr, uid, ids, gross_salary, basic_salary, kpi_amount, salary_percentage, is_change_salary_percentage_by_hand, context)
   
    def onchange_basic_salary(self, cr, uid, ids, gross_salary, basic_salary, kpi_amount, salary_percentage, is_change_basic_salary_by_hand,context=None):
        return self.pool.get('vhr.working.record').onchange_basic_salary(cr, uid, ids, gross_salary, basic_salary, kpi_amount, salary_percentage, is_change_basic_salary_by_hand,context)
    
    def onchange_kpi_amount(self, cr, uid, ids, gross_salary, basic_salary, kpi_amount, context=None):
        return self.pool.get('vhr.working.record').onchange_kpi_amount(cr, uid, ids, gross_salary, basic_salary, kpi_amount, context)
    
    def onchange_general_allowance(self, cr, uid, ids, gross_salary, basic_salary, kpi_amount, general_allowance, context=None):
        return self.pool.get('vhr.working.record').onchange_general_allowance(cr, uid, ids, gross_salary, basic_salary, kpi_amount, general_allowance, context)
    
    def onchange_v_bonus_salary(self, cr, uid, ids, gross_salary, basic_salary, kpi_amount, v_bonus_salary, context=None):
        return self.pool.get('vhr.working.record').onchange_v_bonus_salary(cr, uid, ids, gross_salary, basic_salary, kpi_amount, v_bonus_salary, context)
     
        
    def open_window(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        
        if context.get('hide_form_view_button', False):
            context['hide_form_view_button'] = False
        if context.get('record_type',False) == 'request':
            
            is_require_data_for_submit = False
            records = self.read(cr, uid, ids, ['is_required_attachment'])
            for record in records:
                if record.get('is_required_attachment', False):
                    is_require_data_for_submit = True
                    break
            
            context['is_require_data_for_submit'] = is_require_data_for_submit
            
            view_open = 'view_vhr_working_record_mass_movement_submit_form'
            action = {
                'name': 'Notes',
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': self.pool.get('ir.model.data').get_object_reference(cr, uid, 'vhr_human_resource', view_open)[1],
                'res_model': 'vhr.working.record.mass.movement',
                'context': context,
                'type': 'ir.actions.act_window',
                #'nodestroy': True,
                'target': 'new',
                #'auto_refresh': 1,
                'res_id': ids[0],
            }
            return action
        
        return self.execute_workflow(cr, uid, ids, context)
    
    def create_mass_status(self, cr, uid, context=None):
        
        vals = { 'state' : 'new' }
        
        employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', uid)])
        if employee_ids:
            vals['requester_id'] = employee_ids[0]
            
        module_ids = self.pool.get('ir.module.module').search(cr, uid, [('name','=','vhr_human_resource')])
        if module_ids:
            vals['module_id'] = module_ids[0]
            
        model_ids = self.pool.get('ir.model').search(cr, uid, [('model','=','vhr.working.record')])
        if model_ids:
            vals['model_id'] = model_ids[0]
        
        mass_status_id = self.pool.get('vhr.mass.status').create(cr, uid, vals)
        
        return mass_status_id
    
    
    def execute_workflow(self, cr, uid, ids, context=None):
        
        try:
            thread.start_new_thread(vhr_working_record_mass_movement.thread_execute, (self,cr, uid, ids, context) )
        except Exception as e:
            log.exception(e)
            log.info('Error: Unable to start thread execute Mass HR/Admin/Movement')
        log.info('End running function execute_workflow of Mass HR/Admin/Movement')
        
        if context.get('record_type', False) == 'request':
            name_action = "Mass Requests"
            view_tree_open = 'view_vhr_working_record_staff_movement_tree'
            view_form_open = 'view_vhr_working_record_form'
            view_search_open = 'view_vhr_working_record_movement_search'
         
        else:
            name_action = "Mass Records"
            view_tree_open = 'view_vhr_working_record_tree'
            view_form_open = 'view_vhr_working_record_form'
            view_search_open = 'view_vhr_working_record_search'
            context.update({'rule_for_tree_form': True,'approve':False,'return':False,'reject':False})
        
        ir_model_pool = self.pool.get('ir.model.data')
        view_tree_result = ir_model_pool.get_object_reference(cr, uid, 'vhr_human_resource', view_tree_open)
        view_tree_id = view_tree_result and view_tree_result[1] or False
         
        view_form_result = ir_model_pool.get_object_reference(cr, uid, 'vhr_human_resource', view_form_open)
        view_form_id = view_form_result and view_form_result[1] or False
         
        view_search_result = ir_model_pool.get_object_reference(cr, uid, 'vhr_human_resource', view_search_open)
        view_search_id = view_search_result and view_search_result[1] or False
         
        return {
            'type': 'ir.actions.act_window',
            'name': name_action,
            'view_type': 'form',
            'view_mode': 'tree,form',
            'views': [(view_tree_id or False, 'tree'),
                      (view_form_id or False, 'form')],
            'search_view_id': view_search_id,
            'res_model': 'vhr.working.record',
            'context': context,
            'target': 'current',
        }
        
    
    def thread_execute(self, mcr, uid, ids, context=None):
        if not context:
            context = {}
        log.info('Start thread_execute staff movement')
        mass_status_pool = self.pool.get('vhr.mass.status')
        mass_status_detail_pool = self.pool.get('vhr.mass.status.detail')
        working_record_pool = self.pool.get('vhr.working.record')
        change_form_pool = self.pool.get('vhr.change.form')
        parameter_obj = self.pool.get('ir.config_parameter')
        
        #cr used to create WR
        #t_cr used to create/write Mass Status/ Mass Status Detail
        cr = self.pool.cursor()
        t_cr = self.pool.cursor()
        
        #clear old thread in cache to free memory
        reload(sys)
        
        error_employees = ""
        if ids:
            if not isinstance(ids, list):
                ids = [ids]
            mass_movement = self.browse(cr, uid, ids[0], fields_process=['employee_ids','change_form_ids'])
            columns =  self._columns
            fields = columns.keys()
            fields.remove('employee_ids')
            fields.remove('attachment_ids')
            #read data in wizard form for create working record
            data = self.read(cr, uid, ids[0], fields)
            del data['id']
            #remove data[field] = False, change data[field] from tuple (id, name) to id 
            for field in fields:
                if not data.get(field) and field not in ['is_public']:
                    delete = True
                    if field in FIELD_PARENT_AFFECTS.keys():
                        for parent_field in FIELD_PARENT_AFFECTS[field]:
                            if data.get(parent_field, False):
                                delete = False
                                break
                    
                    if delete:
                        del data[field]
                elif isinstance(data[field], tuple):
                    data[field] = data[field][0]
            
            effect_from = data.get('effect_from',False)
            company_id = data.get('company_id',False)
            
            change_form_ids = []
            if data.get('change_form_ids',False):
                change_form_ids = data['change_form_ids']
                data['change_form_ids'] = [[6,False,data['change_form_ids']]]
            else:
                data['change_form_ids'] = [[6,False,[]]]
                
            working_record_columns = working_record_pool._columns
            working_record_fields = working_record_columns.keys()
            employees = mass_movement.employee_ids
            change_forms = mass_movement.change_form_ids
            
            mass_status_id = self.create_mass_status(t_cr, uid, context)
            t_cr.commit()
            if mass_status_id:
                mass_status_pool.write(t_cr, uid, [mass_status_id], {'state': 'running',
                                                                     'type': context.get('record_type',''),
                                                                     'number_of_record': len(employees), 
                                                                     'number_of_execute_record': 0,
                                                                     'number_of_fail_record': 0})
                error_message = ""
                create_ids = []
                try:
                    list_error = []
                    num_count = 0
                    list_state_change = {}
                    list_state_raw_change = {}
                    for employee in employees:
                        if employee:
                            employee_id = employee.id
                            error_item = False
                            try:
                                num_count += 1
                                mass_status_pool.write(t_cr, uid, [mass_status_id], {'number_of_execute_record': num_count})
                                
                                record_vals = working_record_pool.default_get(cr, SUPERUSER_ID, working_record_fields, context)
                                
                                record_vals.update({'employee_id': employee_id} )
                                #get data when onchange effect_from
                                context['create_from_outside'] = True
                                onchange_effect_from_data = working_record_pool.onchange_effect_from(cr, uid, [], effect_from, employee_id, company_id, False, False, False, False, True, False, False, False, context)
                                #Raise error when can not find contract for employee on effect_from
                                if onchange_effect_from_data.get('warning', False):
                                    error_item = onchange_effect_from_data['warning']
                                    list_error.append( (employee_id, error_item) )
    
                                else:
                                    onchange_effect_from_value = onchange_effect_from_data['value']
                                    for field in onchange_effect_from_value.keys():
                                        if isinstance(onchange_effect_from_value[field], tuple):
                                            onchange_effect_from_value[field] = onchange_effect_from_value[field][0]
                                    
                                    error = False
                                    if onchange_effect_from_data.get('domain', False):
                                        #Raise error if WR near WR create by Termination have change form=termination
                                        domain_effect_from = onchange_effect_from_data['domain']
                                        if 'change_form_ids' in domain_effect_from:
                                            domain_change_form = domain_effect_from['change_form_ids']
                                            
                                            avalable_change_form_ids = change_form_pool.search(cr, uid, domain_change_form, order='id asc')
                                            if not set(avalable_change_form_ids).intersection(set(change_form_ids)):
                                                error_item = "Change Form not satisfy domain %s" % (str(domain_change_form))
                                                list_error.append( (employee_id, error_item) )
                                                error = True
                                    
                                    if not error:
                                        record_vals.update( onchange_effect_from_value )
                                        
                                        record_vals.update(data )
                                        del record_vals['name']
                                        
                                        list_state = []
                                        list_dict_states = {}
                                        #If is mass movement, update state= next state after draft
                                        if context.get('record_type',False) == 'request':
                                            STATES = working_record_pool.get_state_dicts_for_movement(cr, uid, change_forms, context)
                                            list_state = [item[0] for item in STATES]
                                            list_dict_states = {item[0]: item[1] for item in STATES}
                                            if list_state:
                                                fullname_state = list_dict_states[list_state[1]]
                                                record_vals['state'] = list_state[1]
                                                new_state = list_state[1]
                                            else:
                                                fullname_state = 'Draft'
                                                record_vals['state'] = 'draft'
                                                new_state = 'draft'
                                                
                                            record_vals['requester_id'] = self.get_requester_id(cr, uid, context)
                                        
                                        #Update user_validate to save user login for function is_person_already_validated
                                        record_vals['users_validated'] = str(uid)
                                        
                                        res = working_record_pool.create(cr, uid, record_vals, context)
                                        if res:
                                            create_ids.append(res)
                                            
                                            #Nếu employee có quyền tại state mới, thì update lại state sang state kế tiếp
                                            #Case user vừa là HRBP vừa là New HRBP
                                            #Fail khi list state chi co 2 state :))
                                            if context.get('record_type',False) == 'request' and working_record_pool.is_person_do_action(cr, uid, [res]):
                                                if list_state and list_dict_states:
                                                    fullname_state = list_dict_states[list_state[2]]
                                                    new_state = list_state[2]
                                                    working_record_pool.write(cr, uid, res, {'state': new_state})
                                                    
                                            mass_status_detail_pool.create(t_cr, uid, {'mass_status_id': mass_status_id,
                                                                                   'employee_id': employee_id,
                                                                                   'message': '',
                                                                                   'status': 'success'})
                                            if context.get('record_type', False) == 'request':
                                                list_state_change[res] = fullname_state
                                                list_state_raw_change[res] = new_state
                                        
                            except Exception as e:
                                log.exception(e)
                                try:
                                    error_item = e.message
                                    if not error_item:
                                        error_item = e.value
                                except:
                                    error_item = ""
                                    
                                list_error.append( (employee_id, error_item) )
                            #If have error during the task with employee_id, then roll back to revert action create new working record
                            if error_item:
                                mass_status_pool.write(t_cr, uid, [mass_status_id], {'number_of_fail_record': len(list_error)})
                                mass_status_detail_pool.create(t_cr, uid, {'mass_status_id': mass_status_id,
                                                                           'employee_id' : list_error[-1][0],
                                                                           'message':list_error[-1][1]})
                                t_cr.commit()
                                cr.rollback()
                            else:
                                #if dont have error with employee_id, then commit to action with next employee_id wont affect to new WR of current employee_id
                                t_cr.commit()
                                cr.commit()
                                
                    if list_error:
                        mass_status_pool.write(t_cr, uid, [mass_status_id], {'state': 'error','number_of_fail_record': len(list_error)})
                            
                    else:
                        mass_status_pool.write(t_cr, uid, [mass_status_id], {'state': 'finish'})
                    #If is mass movement, update log state change
                    if create_ids and context.get('record_type',False) == 'request':
                        vals = {'old_state': 'Requester', 
                                'model': 'vhr.working.record',
                                'comment': context.get('ACTION_COMMENT','')
                                }
                        for create_id in create_ids:
                            vals['res_id'] = create_id
                            vals['new_state'] = list_state_change[create_id]
                            self.pool.get('vhr.state.change').create(cr, uid, vals)
                            
                            #Send mail
#                             thread.start_new_thread(working_record_pool.send_mail, (cr, uid, create_id, 'draft',list_state_raw_change[create_id], {}))
                            
                            working_record_pool.send_mail(cr, uid, create_id, 'draft',list_state_raw_change[create_id])
                        
                        attachment_pool = self.pool.get('ir.attachment')
                        attachment_ids = attachment_pool.search(cr, uid, [('res_model','=','vhr.working.record.mass.movement'),
                                                                          ('res_id','=',ids[0])])
                        if attachment_ids:
                            for attachment_id in attachment_ids:
                                attachment_data = attachment_pool.copy_data(cr, uid, attachment_id)
                                for create_id in create_ids: 
                                    attachment_data['res_model'] = 'vhr.working.record'
                                    attachment_data['res_id'] = create_id
                                    attachment_pool.create(cr, uid, attachment_data)
                
                except Exception as e:
                    log.exception(e)
                    try:
                        error_message = e.message
                        if not error_message:
                            error_message = e.value
                    except:
                        error_message = ""
                        
                    #If have error with first try, then rollback to clear all created WR
                    cr.rollback()
                    self.pool.get('vhr.working.record').roll_back_working_record(cr, uid, create_ids, context)
                    log.info('Error occur while Mass HR/ Admin/ Movement!')
                
                if error_message:
                    #Use cr in here because InternalError if use t_cr
                    mass_status_pool.write(cr, uid, [mass_status_id], {'state': 'fail','error_message': error_message})
                
                
                mass_ids = self.search(cr, uid, [])
                self.unlink(cr, uid, mass_ids, context)
                cr.commit()
                cr.close()
                
                t_cr.commit()
                t_cr.close()
                log.info('End thread_execute staff movement')
                return True
        
        return True
    
    def get_requester_id(self, cr, uid, context=None):
        employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=',uid)])
        if employee_ids:
            return employee_ids[0]
        
    def fields_view_get(self, cr, uid, view_id = None, view_type = 'form', context = None, toolbar = False, submenu = False):
        res = super(vhr_working_record_mass_movement, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar = toolbar, submenu = submenu)
        
        if context is None:
            context = {}
        if view_type == 'form':
            doc = etree.XML(res['arch'])
            if res['type'] == 'form':
                 #When view view_vhr_working_record_mass_movement_submit_form
                #To add field text action_comment 
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
                
                groups = self.pool.get('vhr.working.record').get_groups(cr, uid)
                #Assistant to HRBP va HRBP trong working record co cung quyen create, edit field
                if 'vhr_assistant_to_hrbp' in groups and 'vhr_hrbp' not in groups:
                    groups.append('vhr_hrbp')
                
                domain = []
                if context.get('record_type', False) == 'request':
                    domain = [('show_hr_rotate', '=', True),('is_salary_adjustment','=', False)]
                    
                elif context.get('record_type', False) == 'record':
                    domain = []
                    if 'vhr_cb_working_record' in groups:
                        domain = []
                    else:
                        if set(['vhr_assistant_to_hrbp','vhr_hrbp']).intersection(set(groups)):
                            domain.append( ('show_qltv_hrbp', '=', True) )
                        
                        if set(['vhr_dept_admin']).intersection(set(groups)):
                            domain.append( ('show_qltv_admin', '=', True) )
                        
                        if set(['vhr_af_admin']).intersection(set(groups)):
                            domain.append( ('show_qltv_af_admin', '=', True) )
                        
                        if domain and len(domain) >1:
                            for index in range(len(domain)-1):
                                domain.insert(0,'|')
                
                config_parameter = self.pool.get('ir.config_parameter')
                input_code = config_parameter.get_param(cr, uid, 'vhr_master_data_input_data_into_iHRP') or ''
                input_code_list = input_code.split(',')
                
                adjust_salary_code = config_parameter.get_param(cr, uid, 'vhr_human_resource_change_form_code_adjust_salary') or ''
                adjust_salary_code_list = adjust_salary_code.split(',')
                input_code_list += adjust_salary_code_list
                
                dismiss_code = config_parameter.get_param(cr, uid, 'vhr_master_data_dismiss_change_form_code') or ''
                input_code_list += dismiss_code.split(',')
                
                back_code = config_parameter.get_param(cr, uid, 'vhr_master_data_back_to_work_change_form_code') or ''
                input_code_list += back_code.split(',')
                
                change_type_code = config_parameter.get_param(cr, uid, 'vhr_master_data_change_type_of_contract') or ''
                input_code_list += change_type_code.split(',')
                
                change_local_comp_code = config_parameter.get_param(cr, uid, 'vhr_master_data_change_local_company') or ''
                input_code_list += change_local_comp_code.split(',')
                
                dismiss_local_comp_code = config_parameter.get_param(cr, uid, 'vhr_master_data_dismiss_local_company') or ''
                input_code_list += dismiss_local_comp_code.split(',')
                
                if input_code_list:
                    input_change_form_ids = self.pool.get('vhr.change.form').search(cr, uid, [('code','in',input_code_list)])
                    domain += [('id','not in', input_change_form_ids)]
                    
                for node in doc.xpath("//field[@name='change_form_ids']"):
                    node.set('domain', str(domain))
                
                all_fields = self._columns.keys()
                remove_fields = ['employee_ids','company_id','effect_from','manager_id_new','change_form_ids','attachment_ids',
                                 'division_id_old','department_group_id_old','department_id_old']
                fields = [x for x in all_fields if x not in remove_fields]
                #Loop for field in vhr_working_record_mass_movement
                for field in fields:
                    for node in doc.xpath("//field[@name='%s']" %field):
                        modifiers = json.loads(node.get('modifiers'))
                        args_readonly, args_invisible = self.pool.get('vhr.working.record').build_args_for_field(cr, uid, field, groups, context)
                        
#                         if context.get('record_type', False) == 'request' and field in ['division_id_new','department_id_new']:
#                             modifiers['required'] =  [('fields_affect_by_change_form','indexOf',field)]
                            
                        if modifiers.get('required', False) and args_invisible:
                            modifiers['required'] = False
                        
                        args_invisible = args_invisible or args_readonly
                        
                        if field == 'department_id_new' and args_invisible:
                            for node_manager in doc.xpath("//field[@name='manager_id_new']"):
                                modifiers_mng = json.loads(node_manager.get('modifiers'))
                                modifiers_mng.update({'invisible' : True})
                                node_manager.set('modifiers', json.dumps(modifiers_mng))
                        
#                         elif field == 'ts_working_schedule_id_new' and args_invisible:
#                             for node_manager in doc.xpath("//field[@name='ts_working_group_id_new']"):
#                                 modifiers_mng = json.loads(node_manager.get('modifiers'))
#                                 modifiers_mng.update({'invisible' : True})
#                                 node_manager.set('modifiers', json.dumps(modifiers_mng))
                        
                        elif field == 'pro_job_family_id_new' and args_invisible:
                            for node_group in doc.xpath('//group[@name="Professional Structure"]'):
                                node_group.set('modifiers', json.dumps({'invisible': True}))
                        elif field == 'mn_job_family_id_new' and args_invisible:
                            for node_group in doc.xpath('//group[@name="Management Structure"]'):
                                node_group.set('modifiers', json.dumps({'invisible': True}))
                        
                        elif field in dict_salary_fields.keys():
                            args_readonly =[('is_change_form_adjust_salary','=',False)]
                            if 'salary_by_hours_timeline' in field and not args_invisible:
                                args_invisible = [('is_salary_by_hours_new','=',False)]
                        
                            args_invisible = args_invisible or args_readonly
                        
                        if not args_invisible and field not in ['note','is_public','keep_authority','employee_ids',
                                                                'ts_working_group_id_new','timesheet_id_new']:
                            args_invisible = [('fields_affect_by_change_form','not indexOf',field)]
                                
                        modifiers.update({'invisible' : args_invisible})
                        node.set('modifiers', json.dumps(modifiers))
                    
            res['arch'] = etree.tostring(doc)
        return res   
    
    def create(self, cr, uid, vals, context=None):
        
        fields = [item[1] for item in dict_fields]
        
        #Raise error if dont edit any thing in group New
        cr_vals = {key:vals[key] for key in vals.keys() if vals[key]}
        
        if not set(fields).intersection(set(cr_vals.keys())):
            raise osv.except_osv('Validation Error !', 
                                         'You need to edit at least one field in group New !')
        return super(vhr_working_record_mass_movement, self).create(cr, uid, vals, context)
        


vhr_working_record_mass_movement()