# -*-coding:utf-8-*-
import logging
import simplejson as json
import unicodedata
from openerp.osv import osv, fields
from lxml import etree
from datetime import date, datetime, timedelta
from openerp.addons.audittrail  import audittrail
from openerp import SUPERUSER_ID
from vhr_applicant import STATE_APP
from vhr_recruitment_constant import RE_ERP_UpdateInfo, RE_ERP_Fail,\
    EMAIL_DEPTHEAD_NONE_OFFICAL,RE_SEND_CV_TO_CONFIRM,RE_FinishInterviewReport,\
    RE_Sending_Interview, RE_ERP_PASS_CANCEL, RE_ERP_PASS_CANCEL_NEW
from vhr_recruitment_abstract import vhr_recruitment_abstract,\
    HRBP, RECRUITER, MANAGER, ADMIN, CANDB_ROLE, COLLABORATER, COLLABORATER2, RRHRBP

from openerp.tools.translate import _
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from dateutil import relativedelta

log = logging.getLogger(__name__)

DRAFT = 'draft'
CONFIRM = 'confirm'
INTERVIEW = 'interview'
OFFER = 'offer'
DONE = 'done'
CLOSE = 'close'

SIGNAL_DRAFT_CONFIRM = 'trans_draft_confirm'
SIGNAL_DRAFT_INTERVIEW = 'trans_draft_interview'
SIGNAL_DRAFT_DONE = 'trans_draft_done'
SIGNAL_DRAFT_CLOSE = 'trans_draft_close'
SIGNAL_CONFIRM_INTERVIEW = 'trans_confirm_interview'
SIGNAL_CONFIRM_CLOSE = 'trans_confirm_close'
SIGNAL_CONFIRM_DONE = 'trans_confirm_done'
SIGNAL_INTERVIEW_OFFER = 'trans_interview_offer'
SIGNAL_INTERVIEW_CLOSE = 'trans_interview_close'
SIGNAL_OFFER_CLOSE = 'trans_offer_close'
SIGNAL_OFFER_DONE = 'trans_offer_done'
SIGNAL_DONE_CLOSE = 'trans_done_close'
SIGNAL_CLOSE_DRAFT = 'trans_close_draft'
SIGNAL_CLOSE_CONFIRM = 'trans_close_confirm'
SIGNAL_CLOSE_INTERVIEW = 'trans_close_interview'
SIGNAL_CLOSE_OFFER = 'trans_close_offer'
SIGNAL_CLOSE_DONE = 'trans_close_done'


SIGNAL_JA = {
      SIGNAL_DRAFT_CONFIRM:     {'old_state': DRAFT, 'new_state': CONFIRM},
      SIGNAL_DRAFT_INTERVIEW:   {'old_state': DRAFT, 'new_state': INTERVIEW},
      SIGNAL_DRAFT_DONE:        {'old_state': DRAFT, 'new_state': DONE},
      SIGNAL_DRAFT_CLOSE:       {'old_state': DRAFT, 'new_state': CLOSE},
      SIGNAL_CONFIRM_INTERVIEW: {'old_state': CONFIRM, 'new_state': INTERVIEW},
      SIGNAL_CONFIRM_CLOSE:   {'old_state': CONFIRM, 'new_state': CLOSE},
      SIGNAL_CONFIRM_DONE:    {'old_state': CONFIRM, 'new_state': DONE},
      SIGNAL_INTERVIEW_OFFER: {'old_state': INTERVIEW, 'new_state': OFFER},
      SIGNAL_INTERVIEW_CLOSE: {'old_state': INTERVIEW, 'new_state': CLOSE},
      SIGNAL_OFFER_CLOSE:     {'old_state': OFFER, 'new_state': CLOSE},
      SIGNAL_OFFER_DONE:      {'old_state': OFFER, 'new_state': DONE},
      SIGNAL_DONE_CLOSE:      {'old_state': DONE, 'new_state': CLOSE},
      SIGNAL_CLOSE_DRAFT:     {'old_state': CLOSE, 'new_state': DRAFT},
      SIGNAL_CLOSE_CONFIRM:   {'old_state': CLOSE, 'new_state': CONFIRM},
      SIGNAL_CLOSE_INTERVIEW: {'old_state': CLOSE, 'new_state': INTERVIEW},
      SIGNAL_CLOSE_OFFER:     {'old_state': CLOSE, 'new_state': OFFER},
      SIGNAL_CLOSE_DONE:      {'old_state': CLOSE, 'new_state': DONE},
}
# Xóa sau khi hết giai đoạn migrate data
SIGNAL_JA_TRIGGER = {
      SIGNAL_DRAFT_CONFIRM:     {'old_state': DRAFT, 'new_state': CONFIRM},
      SIGNAL_DRAFT_INTERVIEW:   {'old_state': DRAFT, 'new_state': INTERVIEW},
      SIGNAL_DRAFT_DONE:        {'old_state': DRAFT, 'new_state': DONE},
      SIGNAL_DRAFT_CLOSE:       {'old_state': DRAFT, 'new_state': CLOSE},
      SIGNAL_CONFIRM_INTERVIEW: {'old_state': CONFIRM, 'new_state': INTERVIEW},
      SIGNAL_CONFIRM_CLOSE:   {'old_state': CONFIRM, 'new_state': CLOSE},
      SIGNAL_CONFIRM_DONE:    {'old_state': CONFIRM, 'new_state': DONE},
      SIGNAL_INTERVIEW_OFFER: {'old_state': INTERVIEW, 'new_state': OFFER},
      SIGNAL_INTERVIEW_CLOSE: {'old_state': INTERVIEW, 'new_state': CLOSE},
      SIGNAL_OFFER_CLOSE:     {'old_state': OFFER, 'new_state': CLOSE},
      SIGNAL_OFFER_DONE:      {'old_state': OFFER, 'new_state': DONE},
      SIGNAL_DONE_CLOSE:      {'old_state': DONE, 'new_state': CLOSE},
}

ROUND_INTER = [('round1', 'ROUND1'), ('round2', 'ROUND2'), ('round3', 'ROUND3')]
RE_FIR = 'RE_FinishInterviewReport'

CANDIDATE_EMPLOYEE = {
    'first_name': 'first_name',
    'last_name': 'last_name',
    'gender': 'gender',
    'birthday': 'birthday',
    'mobile': 'mobile_phone',
    'marital': 'marital',
    'country_id': 'country_id',
    'partner_id': 'address_home_id',
}
OFFER_APPLICANT_EMPLOYEE = {
    'id': 'job_applicant_id',
    'offer_office_id': 'office_id',
    'contract_type_id': 'type_id',
    'join_date': 'date_start',
    'offer_division_id': 'division_id',
    'offer_department_group_id': 'department_group_id',
    'offer_department': 'department_id',
    'offer_manager_id': 'parent_id',
    'offer_company_id': 'company_id',
    'offer_com_group_id': 'company_group_id',
    'offer_job_title_id': 'title_id',
    'offer_job_level_id': 'job_level_id',
    'offer_job_level_position_id': 'job_level_person_id',
    'offer_job_type': 'job_type_id',
    'offer_report_to': 'report_to',
    # salary
    'offer_probation_salary': 'probation_salary',
    'offer_gross_salary': 'gross_salary',
    'offer_team_id': 'team_id',
    # use for ldap
    'is_create_account': 'is_create_account',
    'is_asset': 'is_asset',
    #job family, group, sub group
    'offer_job_family_id': 'job_family_id',
    'offer_job_group_id': 'job_group_id',
    'offer_sub_group_id': 'sub_group_id',
    'offer_career_track_id': 'career_track_id',
#     'change_form_id': 'change_form_id',
#     'position_class_apply_ex': 'position_class_id'    
}


class vhr_job_applicant(osv.osv, vhr_recruitment_abstract):
    _name = 'vhr.job.applicant'
    _description = 'VHR Job Applicant'

    def onchange_job_title_id(self, cr, uid, ids, offer_job_title_id, offer_job_level_id, context=None):
        domain = {'offer_job_level_id': [('id', 'not in', [])], 'sub_group_id': [('id', 'in', [])]}
        res = {'offer_job_level_id': False, 'offer_sub_group_id': False, 'offer_job_group_id': False, 'offer_sub_family_id': False}
        # job group - sub group
        if offer_job_title_id:
            group_title_obj = self.pool.get('vhr.subgroup.jobtitle')
            lst_item = group_title_obj.search(cr, uid, [('job_title_id', '=', offer_job_title_id), ('active', '=', True)], context=context)
            lst_sub_group = []
            for item in group_title_obj.browse(cr, uid, lst_item, context=context):
                temp = item.sub_group_id
                if temp:
                    lst_sub_group.append(temp.id)
            if len(lst_sub_group) > 0:
                res['offer_sub_group_id'] = lst_sub_group[0]
                domain['offer_sub_group_id'] = [('id', 'in', list(set(lst_sub_group)))]
            # job title -level
            job_level_ids = []
            title_level_ids = self.pool.get('vhr.jobtitle.joblevel').search(cr, uid, [('job_title_id', '=', offer_job_title_id)], context=context)
            if title_level_ids:
                title_level_infos = self.pool.get('vhr.jobtitle.joblevel').read(cr, uid, title_level_ids, ['job_level_id'], context=context)
                for title_level_info in title_level_infos:
                    if title_level_info.get('job_level_id', False):
                        job_level_ids.append(title_level_info['job_level_id'][0])

            if job_level_ids:
                if (offer_job_level_id and offer_job_level_id in job_level_ids) or not offer_job_level_id:
                    res['offer_job_level_id'] = job_level_ids[0]
            domain['offer_job_level_id'] = [('id', 'in', job_level_ids)]
        return {'value': res, 'domain': domain}

    def onchange_job_level_id(self, cr, uid, ids, offer_job_title_id, offer_job_level_id, context=None):
        domain = {'offer_job_title_id': [('id', 'not in', [])]}
        res = {}
        if offer_job_level_id:
            job_title_ids = []
            title_level_ids = self.pool.get('vhr.jobtitle.joblevel').search(cr, uid, [('job_level_id', '=', offer_job_level_id)], context=context)
            if title_level_ids:
                title_level_infos = self.pool.get('vhr.jobtitle.joblevel').read(cr, uid, title_level_ids, ['job_title_id'])
                for title_level_info in title_level_infos:
                    if title_level_info.get('job_title_id', False):
                        job_title_ids.append(title_level_info['job_title_id'][0])
            if offer_job_title_id and offer_job_title_id not in job_title_ids:
                res['offer_job_title_id'] = False
            domain['offer_job_title_id'] = [('id', 'in', job_title_ids)]
        return {'value': res, 'domain': domain}
    
    def onchange_job_family_id(self, cr, uid, ids, job_family_id, job_group_id, context=None):
        if not context:
            context = {}
        res = {'offer_job_group_id': False}  
        
        if job_family_id and job_group_id:
            job_group = self.pool.get('vhr.job.group').read(cr, uid, job_group_id, ['job_family_id'])
            p_job_family_id = job_group.get('job_family_id', False) and job_group['job_family_id'][0] or False
            if job_family_id == p_job_family_id:
                res = {}
            
        return {'value': res}
    
    def onchange_job_group_id(self, cr, uid, ids, job_group_id, sub_group_id, context=None):
        if not context:
            context = {}
        res = {'offer_sub_group_id': False}
        
        if job_group_id and sub_group_id:
            sub_group = self.pool.get('vhr.sub.group').read(cr, uid, sub_group_id, ['job_group_id'])
            s_job_group_id = sub_group.get('job_group_id', False) and sub_group['job_group_id'][0] or False
            if s_job_group_id == job_group_id:
                res = {}
            
        return {'value': res}
    
    def onchange_mapping_job_title_id(self, cr, uid, ids, offer_job_title_id, offer_job_level_id, context=None):
        domain = {'hrs_job_level_id': [('id', 'not in', [])]}
        res = {'hrs_job_level_id': False}
        # job group - sub group
        if offer_job_title_id:
            # job title -level
            job_level_ids = []
            title_level_ids = self.pool.get('vhr.jobtitle.joblevel').search(cr, uid, [('job_title_id', '=', offer_job_title_id)], context=context)
            if title_level_ids:
                title_level_infos = self.pool.get('vhr.jobtitle.joblevel').read(cr, uid, title_level_ids, ['job_level_id'], context=context)
                for title_level_info in title_level_infos:
                    if title_level_info.get('job_level_id', False):
                        job_level_ids.append(title_level_info['job_level_id'][0])

            if job_level_ids:
                if (offer_job_level_id and offer_job_level_id in job_level_ids) or not offer_job_level_id:
                    res['hrs_job_level_id'] = job_level_ids[0]
            domain['hrs_job_level_id'] = [('id', 'in', job_level_ids)]
        return {'value': res, 'domain': domain}

    def onchange_mapping_job_level_id(self, cr, uid, ids, offer_job_title_id, offer_job_level_id, context=None):
        domain = {'hrs_job_title_id': [('id', 'not in', [])]}
        res = {}
        if offer_job_level_id:
            job_title_ids = []
            title_level_ids = self.pool.get('vhr.jobtitle.joblevel').search(cr, uid, [('job_level_id', '=', offer_job_level_id)], context=context)
            if title_level_ids:
                title_level_infos = self.pool.get('vhr.jobtitle.joblevel').read(cr, uid, title_level_ids, ['job_title_id'])
                for title_level_info in title_level_infos:
                    if title_level_info.get('job_title_id', False):
                        job_title_ids.append(title_level_info['job_title_id'][0])
            if offer_job_title_id and offer_job_title_id not in job_title_ids:
                res['hrs_job_title_id'] = False
            domain['hrs_job_title_id'] = [('id', 'in', job_title_ids)]
        return {'value': res, 'domain': domain}

    def onchange_job_reason_cancel_type_id(self, cr, uid, ids, reason_cancel_type_id, context=None):
        res = {}
        res['reason_cancel_ids'] = False
        return {'value': res}

    def onchange_sub_group_id(self, cr, uid, ids, offer_sub_group_id, context=None):
        res = {'offer_job_group_id': False, 'offer_job_family_id': False}
        if offer_sub_group_id:
            sub_group_obj = self.pool.get('vhr.sub.group').browse(cr, uid, offer_sub_group_id, context=context)
            job_group_obj = sub_group_obj.job_group_id
            if job_group_obj:
                res['offer_job_group_id'] = job_group_obj.id
                res['offer_job_family_id'] = job_group_obj.job_family_id.id
        return {'value': res}

    def onchange_date(self, cr, uid, ids, current_row, start_time, end_time, change_end=None):
        value = {}
        domain = {}
        partern = '%Y-%m-%d %H:%M:%S'
        if current_row:
            if current_row == ROUND_INTER[0][0]:
                value_end = 'end_time_round1'
            elif current_row == ROUND_INTER[1][0]:
                value_end = 'end_time_round2'
            else:
                value_end = 'end_time_round3'
            # if none official and has start_time and starttime less current time
            if start_time and not end_time:
                endtime = datetime.strptime(start_time, partern) + timedelta(hours=1)
                return {'value': {value_end: '%s'%(endtime)}}
            if change_end:
                if start_time and end_time:
                    if datetime.strptime(start_time, partern) > datetime.strptime(end_time, partern):
                        endtime = datetime.strptime(start_time, partern) + timedelta(hours=1)
                        return {'value': {value_end: '%s'%(endtime)}}
            else:
                if start_time and end_time:
                    endtime = datetime.strptime(start_time, partern) + timedelta(hours=1)
                    return {'value': {value_end: '%s'%(endtime)}}                             
        return {'value': value, 'domain': domain}

    def onchange_salary(self, cr, uid, ids, offer_gross_salary, offer_probation_salary,  context=None):
        # TODO : compute new values from the db/system
        job_app_obj = self.browse(cr, uid, ids[0], context=context)
        if job_app_obj.contract_type_id and job_app_obj.contract_type_id.contract_type_group_id:
            if job_app_obj.contract_type_id.contract_type_group_id.code not in ['1']:
                if not isinstance(offer_gross_salary, bool) and not isinstance(offer_probation_salary, bool):
                    percent = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr.rr.percent.gross.config')
                    percent = float(percent) if percent else 0.85
                    ogs_probation = offer_gross_salary*percent
                    if offer_probation_salary < ogs_probation or offer_probation_salary > offer_gross_salary:
                        warning = {'title': 'User Alert!', 'message': '%s * gross salary <= Probation salary <= gross salary' % (percent)}
                        return {'value': {'offer_probation_salary': ''}, 'warning': warning}
        return {'value': {}, 'domain': {}}

    def onchange_ex_employee(self, cr, uid, ids, ex_employee, applicant_id, context=None):
        value = {}
        domain = {'emp_id': [('id', 'not in', [])]}
        res = {}
        if ex_employee is False:
            res['value'] = {'emp_id': None}
        else:
            emp_obj = self.pool.get('hr.employee')
            hr_app = self.pool.get('hr.applicant')
            applicant_obj = hr_app.browse(cr, uid, applicant_id, context=context)
            if applicant_obj and applicant_obj.name and applicant_obj.birthday and applicant_obj.gender:
                
                res = hr_app.on_change_ex_employee(cr, uid, [applicant_id],
                                                   ex_employee, applicant_obj.email,
                                                   applicant_obj.mobile, applicant_obj.name,
                                                   applicant_obj.birthday, applicant_obj.gender)
                
                emp_search = emp_obj.search(cr, uid, [('name', '=', applicant_obj.name), ('gender', '=', applicant_obj.gender),
                                                      ('birthday', '=', applicant_obj.birthday)], context={'active_test': False})
                if emp_search:
                    domain['emp_id'] = [('id', 'in', emp_search)]
        
        res['domain'] = domain
        return res

    def onchange_com_group_id(self, cr, uid, ids, offer_com_group_id, context=None):
        res = {}
        if offer_com_group_id:
            lst = self.pool.get('res.company').search(cr, uid, [('com_group_id', '=', offer_com_group_id), ('active', '=', True)], context=context)
            if lst:
                res['offer_company_id'] = lst[0]
            else:
                res['offer_company_id'] = False
        else:
            res['offer_company_id'] = False
        return {'value': res}
    
    def onchange_keep_in_view(self, cr, uid, ids, keep_in_view, current_row, context=None):
        res = {}
        if current_row:
            if current_row == ROUND_INTER[0][0]:
                value_end = 'decision_id1'
            elif current_row == ROUND_INTER[1][0]:
                value_end = 'decision_id2'
            else:
                value_end = 'decision_id3'
            if keep_in_view:
                res[value_end] = False
        return {'value': res}

    def onchange_contract_type(self, cr, uid, ids, contract_type_id, context=None):
        if context is None:
            context = {}
        
        res = {}
        contract_type = self.pool['hr.contract.type'].browse(cr, uid, contract_type_id)
        res['is_official'] = contract_type and contract_type.contract_type_group_id and contract_type.contract_type_group_id.is_offical or False
        if not res['is_official']:
            res['offer_job_level_position_id'] = False
            res['offer_career_track_id'] = False
            
        if contract_type and contract_type.contract_type_group_id:
            if contract_type.contract_type_group_id.code in ['1']:
                res['not_probation'] = False
            else:
                res['not_probation'] = True
                res['offer_probation_salary'] = 0.0
        return {'value': res}

    def action_generate_contract(self, cr, uid, ids, context=None):  # note for delete if not used
        contract_obj = self.pool.get('hr.contract')
        if ids:
            job_app_obj = self.browse(cr, uid, ids[0], context=context)
            if job_app_obj:
                employee_id = job_app_obj.applicant_id and job_app_obj.applicant_id.emp_id or job_app_obj.applicant_id.emp_id.id or None
                return contract_obj.create_contract(cr, uid, ids, employee_id, context=context)
        return False

    def _check_editable(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        roles = self.recruitment_get_group_array(cr, uid, uid)
        for item in self.browse(cr, uid, ids, context=context):
            result[item.id] = False          
            if RECRUITER not in roles or (item.hr_process and item.join_date and 
                datetime.strptime(item.join_date, '%Y-%m-%d').date() < date.today()):                
                result[item.id] = True
        return result
    
    def _is_depthead(self, cr, uid, ids, field_name, arg, context=None):
        # 23/12/2014 show current salary and expected salary for depthead and rectuiter
        res = {}
        if context is None: context = {}
        roles = self.recruitment_get_group_array(cr, uid, uid)
        for item in self.browse(cr, uid, ids, context=context):
            # recruiter
            if RECRUITER in roles:
                res[item.id] = True
                continue
            manager_user_id = item.department_id.manager_id.user_id.id if item.department_id and item.department_id.manager_id else 0
            res[item.id] = True if manager_user_id == uid else False
            
        return res
    
    def _is_keep_in_view(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if context is None: context = {}
        for item in self.read(cr, SUPERUSER_ID, ids, ['keep_in_view_1','keep_in_view_2','keep_in_view_3'],context=context):
            res[item.get('id')] = item.get('keep_in_view_1') or item.get('keep_in_view_2') or item.get('keep_in_view_3')
        return res    
    
        
    def _is_reporter(self, cr, uid, ids, field_name, arg, context=None):
        '''
            Kiểm tra tại state interview reporter tại bước đó sẽ được điền giá trị và decision tương ứng
        '''
        res = {}
        roles = self.recruitment_get_group_array(cr, uid, uid)        
        for item in self.browse(cr, uid, ids, context=context):
            res[item.id] = False
            if item.state == INTERVIEW:
                if RECRUITER in roles :
                    res[item.id] = True
                elif item.current_row and item.current_row == ROUND_INTER[0][0]:
                    reporter_user_id = item.reporter1.user_id.id if item.reporter1.user_id else 0
                    if reporter_user_id == uid:
                        res[item.id] = True
                elif item.current_row and item.current_row == ROUND_INTER[1][0]:
                    reporter_user_id = item.reporter2.user_id.id if item.reporter2.user_id else 0
                    if reporter_user_id == uid:
                        res[item.id] = True
                elif item.current_row and item.current_row == ROUND_INTER[2][0]:
                    reporter_user_id = item.reporter3.user_id.id if item.reporter3.user_id else 0
                    if reporter_user_id == uid:
                        res[item.id] = True
        return res
    
    def _get_cancel_date(self, cr, uid, ids, field_name, args, context=None):
        result = {}
        state_change_obj = self.pool.get('vhr.state.change')
        for job_app_item in self.read(cr, uid, ids, ['offer_date'], context=context):
            item = job_app_item.get('id')
            result[item] = False
            result_search = state_change_obj.search(cr, uid, [('res_id', '=', item), ('model', '=', self._name),
                                                              ('old_state', '=', OFFER), ('new_state', '=', CLOSE)],
                                                    limit=1, order='id desc', context=context)
            if result_search:
                result[item] = state_change_obj.browse(cr, uid, result_search[0], context=context).create_date
            else:
                if job_app_item.get('offer_date',False):
                    last_state = state_change_obj.get_last_state(cr, uid, item, self._name)
                    if last_state and last_state['new_state'] == CLOSE:
                        data_migrate = state_change_obj.search(cr, uid, [('res_id', '=', item), ('model', '=', self._name),
                                                                      ('new_state', '=', CLOSE)], limit=1, order='id desc', context=context)
                        if data_migrate:
                            result[item] = state_change_obj.browse(cr, uid, data_migrate[0], context=context).create_date
        return result

    def action_get_attachment_tree_view(self, cr, uid, ids, context=None):
        # open attachments of job and related applicantions.
        job_ids = []
        applicant_ids = []
        for job_app in self.browse(cr, uid, ids, context=context):
            if job_app.job_id:
                job_ids.append(job_app.job_id.id)
            if job_app.applicant_id:
                applicant_ids.append(job_app.applicant_id.id)
        model, action_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'base', 'action_attachment')
        action = self.pool.get(model).read(cr, uid, action_id, context=context)
        action['context'] = {'default_res_model': 'hr.applicant', 'default_res_id': applicant_ids[0]}
        action['domain'] = str(['&', ('res_model', '=', 'hr.applicant'),
                                ('res_id', 'in', applicant_ids)])
        return action

    def action_print_offer_report(self, cr, uid, ids, context=None):
        app_obj = self.pool.get('hr.applicant')
        emp_obj = self.pool.get('hr.employee')
        contract_obj = self.pool.get('hr.contract')
        contract_type_obj = self.pool.get('hr.contract.type')
        department_obj = self.pool.get('hr.department')
        
        pt_obj = self.pool.get('vhr.ts.param.type')
        pt_by_lv_obj = self.pool.get('vhr.ts.param.job.level')
        
        data = self.read(cr, uid, ids, [], context=context)[0]
        app_id = data.get('applicant_id', False) and data.get('applicant_id')[0] or []
        app_data = app_obj.read(cr, uid, app_id, [], context=context)
        if app_data:
            data = dict(app_data.items() + data.items())
        report_id = data.get('offer_report_to', False) and data.get('offer_report_to')[0] or []
        if report_id:
            reporter = emp_obj.read(cr, uid, report_id, ['name'], context=context)
            data.update({'offer_report_to': reporter.get('name', '')})

        division_id = data.get('offer_division_id', False) and data.get('offer_division_id')[0] or []
        if division_id:
            division = department_obj.read(cr, uid, division_id, ['name'], context=context)
            data.update({'offer_division_id': division.get('name', '')})
        
        
        department_group_id = data.get('offer_department_group_id', False) and data.get('offer_department_group_id')[0] or []
        if department_group_id:
            group = department_obj.read(cr, uid, department_group_id, ['name','organization_class_id'], context=context)
            data.update({'offer_department_group_id': group.get('name', '')})
            
            organization_class_id = group.get('organization_class_id', False) and group['organization_class_id'][0] or False
            if organization_class_id:
                organization_class = self.pool.get('vhr.organization.class').read(cr, uid, organization_class_id, ['level'])
                level = organization_class.get('level',0)
                if level == 1:
                    data.update({'offer_division_id': group.get('name', '')})
            
            
        department_id = data.get('offer_department', False) and data.get('offer_department')[0] or []
        if department_id:
            department = department_obj.read(cr, uid, department_id, ['name'], context=context)
            data.update({'offer_department': department.get('name', '')})

        start_date = data.get('join_date', False) and data.get('join_date') or False
        type_id = data.get('contract_type_id', False) and data.get('contract_type_id')[0] or False
        if type_id:
            contract_type = contract_type_obj.browse(cr, uid, type_id, context=context)
            duration = contract_type and contract_type.contract_type_group_id and \
                       contract_type.contract_type_group_id.code == '1' and contract_type.life_of_contract or 2
            data.update({'duration': duration})
        emp_id = data.get('emp_id', []) and data['emp_id'][0] or []
        if start_date and type_id:
            code = contract_obj.generate_code(cr, uid, type_id, emp_id, start_date)
            data.update({'contract_code': code})

        report_name = data.get('job_id')[1] + '_' + data.get('applicant_id')[1]
        if data.get('offer_gross_salary', False):
            salary = data.get('offer_gross_salary')
            standard_salary = salary * 0.65
            extra_salary = salary - standard_salary
            data['standard_salary'] = standard_salary
            data['extra_salary'] = extra_salary
        
        
        # Số ngày nghỉ theo cấp bậc
        data['days_off'] = 0
        if data.get('offer_job_level_id', False) or data.get('offer_job_level_position_id', False):
            today = date.today()
            
            job_level_position_id = data.get('offer_job_level_position_id',False) and data['offer_job_level_position_id'][0]
            job_level_id =data.get('offer_job_level_id',False) and data['offer_job_level_id'][0]
            pt_ids = pt_obj.search(cr, uid, [('code', '=', '1')], context=context)
            domain=[('param_type_id', 'in', pt_ids),
                      ('active','=',True),
                      ('effect_from','<=',today),
                      '|',('effect_to','=',False),
                          ('effect_to','>=',today)]
            
            if job_level_position_id:
                domain.insert(0,('job_level_new_id', '=', job_level_position_id))
            elif job_level_id:
                domain.insert(0,('job_level_id', '=', job_level_id))
            
            
            pt_lv_ids = pt_by_lv_obj.search(cr, uid, domain, order='effect_from desc',context=context)
            if pt_lv_ids:
                pt = pt_by_lv_obj.browse(cr, uid, pt_lv_ids[0], context=context)
                data['days_off'] = pt and pt.value or ''
                
        
        datas = {
            'ids': ids,
            'model': 'vhr.job.applicant',
            'form': data
        }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'offer_report',
            'datas': datas,
            'name': report_name
        }
        
    def action_print_offer_contract_definite_report(self, cr, uid, ids, context=None):
        app_obj = self.pool.get('hr.applicant')
        emp_obj = self.pool.get('hr.employee')
        contract_obj = self.pool.get('hr.contract')
        contract_type_obj = self.pool.get('hr.contract.type')
        department_obj = self.pool.get('hr.department')
        company_obj = self.pool.get('res.company')
        country_obj = self.pool.get('res.country')
        partner_obj = self.pool.get('res.partner')
        office_obj = self.pool.get('vhr.office')
        pt_obj = self.pool.get('vhr.ts.param.type')
        pt_by_lv_obj = self.pool.get('vhr.ts.param.job.level')
        
        data = self.read(cr, uid, ids, [], context=context)[0]
        app_id = data.get('applicant_id', False) and data.get('applicant_id')[0] or []
        app_data = app_obj.read(cr, uid, app_id, [], context=context)
        if app_data:
            data = dict(app_data.items() + data.items())
        gender_app = data.get('gender_app',False)
        if gender_app == 'male':
            data.update({'gender_app_contract':'Male'})
        if gender_app == 'female':
            data.update({'gender_app_contract':'Female'})
        if gender_app == 'other':
            data.update({'gender_app_contract':'Other'})
            
        report_id = data.get('offer_report_to', False) and data.get('offer_report_to')[0] or []
        if report_id:
            reporter = emp_obj.read(cr, uid, report_id, ['name'], context=context)
            data.update({'offer_report_to': reporter.get('name', '')})
            
        company_id = data.get('offer_company_id', False) and data.get('offer_company_id')[0] or []
        if company_id:
            company = company_obj.read(cr, uid, company_id, ['name'], context=context)
            data.update({'offer_company_id': company.get('name', '')})
        
        country_signer = data.get('com_country_signer',False) and data.get('com_country_signer')[0] or []
        if country_signer:
            country = country_obj.read(cr, uid, country_signer, ['name'], context=context)
            data.update({'com_country_signer': country.get('name', '')})
            
        partner_id = data.get('com_partner_id',False) and data.get('com_partner_id')[0] or []
        if partner_id:
                partner = partner_obj.read(cr, uid, partner_id, ['street','fax'], context=context)
                data.update({'com_street': partner.get('street', '')})
                data.update({'com_fax': partner.get('fax', '')}) 
                
        offer_office_id = data.get('offer_office_id', False) and data.get('offer_office_id')[0] or []
        if offer_office_id:
            office = office_obj.read(cr, uid, offer_office_id, ['name'], context=context)
            data.update({'offer_office_id': office.get('name', '')})
            
        division_id = data.get('offer_division_id', False) and data.get('offer_division_id')[0] or []
        if division_id:
            division = department_obj.read(cr, uid, division_id, ['name'], context=context)
            data.update({'offer_division_id': division.get('name', '')})
        
        
        department_group_id = data.get('offer_department_group_id', False) and data.get('offer_department_group_id')[0] or []
        if department_group_id:
            group = department_obj.read(cr, uid, department_group_id, ['name','organization_class_id'], context=context)
            data.update({'offer_department_group_id': group.get('name', '')})
            
            organization_class_id = group.get('organization_class_id', False) and group['organization_class_id'][0] or False
            if organization_class_id:
                organization_class = self.pool.get('vhr.organization.class').read(cr, uid, organization_class_id, ['level'])
                level = organization_class.get('level',0)
                if level == 1:
                    data.update({'offer_division_id': group.get('name', '')})
            
        department_id = data.get('offer_department', False) and data.get('offer_department')[0] or []
        if department_id:
            department = department_obj.read(cr, uid, department_id, ['name'], context=context)
            data.update({'offer_department': department.get('name', '')})

        start_date = data.get('join_date', False) and data.get('join_date') or False
        type_id = data.get('contract_type_id', False) and data.get('contract_type_id')[0] or False
        date_end_contract = False
        if type_id:
            contract_type = contract_type_obj.browse(cr, uid, type_id, context=context)
            if contract_type and contract_type.contract_type_group_id and \
                contract_type.contract_type_group_id.code == '3':
                
                date_start_contract = datetime.strptime(start_date, '%Y-%m-%d')
                life_of_contract = contract_type.life_of_contract if contract_type.life_of_contract else 0
                if life_of_contract > 0:
                    date_end_contract_temp = date_start_contract + relativedelta.relativedelta(months=life_of_contract)
                    date_end_contract  = date_end_contract_temp.strftime('%Y-%m-%d')
                    data.update({'date_end_contract': date_end_contract})
                    
            if contract_type and contract_type.contract_type_group_id and \
                contract_type.contract_type_group_id.code  == '4':
                data.update({'date_end_contract': False})
                
        emp_id = data.get('emp_id', []) and data['emp_id'][0] or []
        employee_ids = self.pool.get('hr.employee').search(cr, uid,[('id','=',emp_id)])
        emp_code = ''
        if employee_ids:
            employee = self.pool.get('hr.employee').browse(cr, uid, employee_ids[0], context = context)
            emp_code = employee.code
            data.update({'employee_code_definite': emp_code})
        if start_date and type_id:
            code = contract_obj.generate_code(cr, uid, type_id, emp_id, start_date)
            data.update({'contract_code': code})
        report_name = data.get('job_id')[1] + '_' + data.get('applicant_id')[1]
        #get contract
        #contract_ids = contract_obj.search(cr, uid,[('job_applicant_id','=',ids[0])])
        offer_gross_salary = data.get('offer_gross_salary',0)
#        v_bonus = False
#        basic_salary = False
#        if contract_ids:
#            contract = contract_obj.browse(cr, uid, contract_ids[0], context = context)
#            v_bonus = contract.v_bonus_salary
#            offer_gross_salary = contract.gross_salary
#            basic_salary =  contract.basic_salary
#            data.update({'v_bonus_contract': v_bonus})
#            data.update({'basic_salary_contract': basic_salary})
        data.update({'gross_salary_contract': offer_gross_salary})
        data.update({'basic_salary_contract': offer_gross_salary*0.7})
        data.update({'v_bonus_contract': offer_gross_salary*0.3})
        # Số ngày nghỉ theo cấp bậc
        data['days_off'] = 0
        if data.get('offer_job_level_id', False) or data.get('offer_job_level_position_id', False):
            today = date.today()
            
            job_level_position_id = data.get('offer_job_level_position_id',False) and data['offer_job_level_position_id'][0]
            job_level_id =data.get('offer_job_level_id',False) and data['offer_job_level_id'][0]
            pt_ids = pt_obj.search(cr, uid, [('code', '=', '1')], context=context)
            domain=[('param_type_id', 'in', pt_ids),
                      ('active','=',True),
                      ('effect_from','<=',today),
                      '|',('effect_to','=',False),
                          ('effect_to','>=',today)]
            
            if job_level_position_id:
                domain.insert(0,('job_level_new_id', '=', job_level_position_id))
            elif job_level_id:
                domain.insert(0,('job_level_id', '=', job_level_id))
            
            
            pt_lv_ids = pt_by_lv_obj.search(cr, uid, domain, order='effect_from desc',context=context)
            if pt_lv_ids:
                pt = pt_by_lv_obj.browse(cr, uid, pt_lv_ids[0], context=context)
                data['days_off'] = pt and pt.value or ''
                
        
        datas = {
            'ids': ids,
            'model': 'vhr.job.applicant',
            'form': data
        }
        return {
            'type': 'ir.actions.report.xml',
            'report_name':'offer_report_contract_definite',
            'datas': datas,
            'name': report_name
        }


    def action_print_report(self, cr, uid, ids, context=None):
        data = self.read(cr, uid, ids, [], context=context)[0]
        report_name = data.get('job_id')[1] + '_' + data.get('applicant_id')[1]
        for k, v in self._columns.iteritems():
            if v._type == 'many2many':
                temp_obj = self.pool.get(self._columns[k]._obj)
                if temp_obj and data[k]:
                    temp_name = temp_obj.read(cr, SUPERUSER_ID, data[k], ['name'], context=context)
                    new_name = ''
                    for item in temp_name:
                        if not new_name:
                            new_name = item.get('name', '')
                        else:
                            new_name = new_name + '; ' + item.get('name', '')
                    data[k] = new_name
            elif v._type == 'one2many':
                temp_obj = self.pool.get(self._columns[k]._obj)
                if temp_obj and data[k]:
                    if k in ('evaluation_details1', 'evaluation_details2', 'evaluation_details3'):
                        temp_data = [['Evaluation', 'Note']]
                        list_item = temp_obj.read(cr, SUPERUSER_ID, data[k], ['evaluation_id', 'note'], context=context)
                        for item in list_item:
                            note = item.get('note') if item.get('note') else ''
                            temp_data.append([item.get('evaluation_id')[1], note])
                        data[k] = temp_data
                    else:
                        data[k] = temp_obj.read(cr, SUPERUSER_ID, data[k], [], context=context)
        datas = {
            'ids': ids,
            'model': 'vhr.job.applicant',
            'form': data
        }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'interview_report',
            'datas': datas,
            'name': report_name
        }

    def action_open_window_ex(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        action_type = context.get('ACTION_TYPE', '')
        view_type = context.get('VIEW_TYPE', 'form')
        view_id = context.get('VIEW_ID', '')
        view_name = context.get('VIEW_NAME', '')
        target = context.get('TARGET', 'new')
        res_model = context.get('MODEL', self._name)
        res_id = False
        try:
            view_module = view_id.split(".")
            if view_module and len(view_module) == 2:
                if action_type == 'CLOSE' or action_type == 'SEND_CV':
                    res_id = ids[0]
                elif action_type == 'REOPEN':
                    res_id = ids[0]
                    app_job = self.browse(cr, uid, res_id, context=context)
                    job_item = app_job.job_id  # auto update vhr job
                    app_item = app_job.applicant_id  #
                    if job_item.no_of_recruitment <= job_item.no_of_hired_recruitment:
                        raise osv.except_osv('Validation Error !', 'Please check recruited Qty < Request quantity')
                    elif app_item.state != 'opening':
                        raise osv.except_osv('Validation Error !', 'Please check state of candidate must be opening')
                    else:
                        state_change_obj = self.pool.get('vhr.state.change')
                        last_state = state_change_obj.get_last_state(cr, uid, res_id, self._name)
                        if last_state:
                            job_app_signal = [k for k, v in SIGNAL_JA.iteritems() if v['old_state'] == last_state['new_state'] \
                                              and v['new_state'] == last_state['old_state']]
                            if job_app_signal:
                                context['ACTION'] = job_app_signal[0]
                        else:
                            raise osv.except_osv('Validation Error !', 'Could not find last state')
                return {
                    'name': view_name,
                    'view_type': view_type,
                    'view_mode': 'form',
                    'view_id': self.pool.get('ir.model.data').get_object_reference(cr, uid, view_module[0], view_module[1])[1],
                    'res_model': res_model,
                    'context': context,
                    'type': 'ir.actions.act_window',
                    'nodestroy': True,
                    'target': target,
                    'res_id': res_id,
                }
        except ValueError:  # ignore if views are missing
            log.error('VHR.JOB.APPLICANT : can not search view')
            pass
        return True

    def transfer_candidate_to_employee_remind(self, cr, uid, ids, context=None):
        if not context:
            context = {}

        view_id = self.pool['ir.model.data'].get_object_reference(
            cr, uid, 'vhr_recruitment', 'vhr_transfer_remind_view')[1]
        res_id = self.pool['ir.model.data'].get_object_reference(
            cr, uid, 'vhr_recruitment', 'vhr_transfer_remind_message')[1]

        return {
            'type': 'ir.actions.act_window',
            'name': _('Transfer Remind'),
            'res_model': 'vhr.transfer.remind',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'res_id': res_id,
            'target': 'new',
            'nodestroy': True,
            'context': str(context),
        }

    def transfer_candidate_to_employee(self, cr, uid, ids, context=None):
        emp_obj = self.pool.get('hr.employee')
        app_obj = self.pool.get('hr.applicant')
        hr_job_obj = self.pool.get('hr.job')
        if not context: context = {}

        context.update({'update_from_candidate': True})
        # check số lượng tranfer <= số lượng request
        job_app = self.browse(cr, uid, ids[0], context=context)
        job_item = job_app.job_id
        # Count số lượng người tranfer và state là done và offer
        hired_soon = self.search(cr, uid, [('job_id', '=', job_item.id), ('state', 'in', ['done', 'offer']),
                                           ('hr_process', '=', True)], count=True, context=context)
        
        miss_info_app_ids = self.search(
                cr, uid, [['job_id', '=', job_item.id],
                          ['state', 'in', ['confirm', 'interview', 'draft']]])
        
        if hired_soon >= job_item.no_of_recruitment:
            raise osv.except_osv('Validation Error !', 'Please check request quantity and number candidate offer and done')
        
        #BinhNX: Check before transfer the lasted job headcount -> make sure finish all of interview report
        if job_item.no_of_recruitment - hired_soon == 1 and miss_info_app_ids:
            raise osv.except_osv('Validation Error !',
                                 "Please finish all of current job's interview report after Transfer C&B")
        # End
        offer_data = self.read(cr, uid, ids[0], [], context=context)
        res_emp = {}
        if offer_data:
            if offer_data.get('ex_employee', False):
                if not offer_data.get('emp_id', False):
                    raise osv.except_osv('Validation Error !', 'Please choose employee or uncheck ex_employee')
                else:
                    res_emp['employee_id'] = offer_data['emp_id']
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

            columns = self._columns
            for offer_key, emp_key in OFFER_APPLICANT_EMPLOYEE.iteritems():
                type_column = offer_key != 'id' and columns[offer_key]._type or ''
                if type_column == 'many2one':
                    res_emp[emp_key] = offer_data.get(offer_key, False) and offer_data[offer_key][0] or False
                else:
                    res_emp[emp_key] = offer_data.get(offer_key, False)
                
                #Get for level by person
                if offer_key == 'id':
                    res_emp['job_applicant_id']= res_emp[emp_key]
                if offer_key == 'offer_job_level_position_id':
                    res_emp['job_level_person_id']= res_emp[emp_key]
                    
            if res_emp.get('last_name', False) and res_emp.get('first_name', False):
                res_emp['name'] = u'%s %s' % (res_emp['last_name'], res_emp['first_name'])            
            
            
            transfer_id = False
            
            is_new_employee = True
            #Chỉ lưu vào bảng tạm khi transfer nhân viên đang làm việc
            if res_emp.get('employee_id', False):
                ex_emp_id = res_emp.get('employee_id', False) and res_emp['employee_id'][0] or False
                if ex_emp_id:
                    emp_data = emp_obj.read(cr, uid, ex_emp_id, ['end_date','active'])
                    end_date = emp_data.get('end_date', False)
                    if emp_data.get('active', False):
                        is_new_employee = False
                    elif end_date:
                        end_date = datetime.strptime(end_date, '%Y-%m-%d')
                        today = datetime.strptime( datetime.today().strftime('%Y-%m-%d'), '%Y-%m-%d')
                        if (end_date-today).days >= 0:
                            is_new_employee = False
            
            
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
                
            if self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_recruitment_transfer_employee') and not is_new_employee:
                transfer_id = self.pool.get('vhr.rr.transfer.employee').create(cr, uid, {'job_applicant_id': ids[0]})
            else:
                emp_id = emp_obj.create_employee_from_candidate(cr, uid, res_emp, context=context)
                if not emp_id:
                    raise osv.except_osv('Validation Error !', 'Can not create employee, please check input data!')
                if not offer_data.get('ex_employee', False) and not offer_data.get('emp_id', False):
                    app_obj.write(cr, uid, [applicant_id], {'emp_id': emp_id}, context=context)
            #END: Uncommand when go-live HR to transfer employee to C&B
            # bonus mail
            bonus_payment_reruitment_mail_id = self.pool.get('vhr.erp.bonus.payment.reruitment.mail').create_erp_bonus_payment(cr, uid, ids[0])
            self.write(cr, uid, ids,
                       {'hr_process': True,
                        'transfer_id': transfer_id,
                        'transfer_canb': date.today(),
                        'user_transfer': uid,
                        'offer_date': date.today(),
                        'business_impact_id': job_item and job_item.business_impact_id and job_item.business_impact_id.id or False,
                        'bonus_payment_reruitment_mail_id':bonus_payment_reruitment_mail_id
                        })
            #BinhNX: Check before transfer the lasted job headcount -> there is no job app in state ('confirm', 'interview', 'draft')
            if job_item.no_of_recruitment - hired_soon == 1 and not miss_info_app_ids:
                hr_job_obj.vhr_job_execute_workflow(cr, uid, job_item.id, 'done')
                
            # note : email offer
            self.recruitment_send_email(cr, uid, 'RE_OfferInforSend', self._name, ids[0], context=context)
            # note : send email for candidate
            self.recruitment_send_email(cr, uid, 'RE_Sending_Candidate', self._name, ids[0], context=context)
        
        return {'type': 'ir.actions.act_window_close'}
    
    def update_candidate_to_employee(self, cr, uid, ids, context=None):
        update_data = self.read(cr, uid, ids[0], [], context=context)
        
        # BEGIN: Uncommand when go-live HR to transfer employee to C&B
        if update_data:
            if update_data.get('transfer_id', False):
                transfer_id = update_data['transfer_id'][0]
                transfer = self.pool.get('vhr.rr.transfer.employee').read(cr, uid, transfer_id, ['state'])
                if transfer.get('state',False) == 'finish':
                    self.update_candidate_to_employee_detail(cr, uid, ids, update_data, context)
            else:
                self.update_candidate_to_employee_detail(cr, uid, ids, update_data, context)
        # END: Uncommand when go-live HR to transfer employee to C&B
        if update_data.get('change_offer_email'):
            self.recruitment_send_email(cr, uid, 'RR_ChangeCanInfo_C&B', self._name, ids[0], context=context)
        
        if update_data.get('is_send_email_erp_bonus_schedue'):
            job_applicant = self.browse(cr, uid, ids[0], context=context)
            bonus_payment_reruitment_mail_id = job_applicant.bonus_payment_reruitment_mail_id.id if job_applicant.bonus_payment_reruitment_mail_id else False
            if bonus_payment_reruitment_mail_id:
                send_success = self.pool.get('vhr.erp.bonus.payment.reruitment.mail').update_erp_bonus_payment_mail(cr, uid, bonus_payment_reruitment_mail_id, context = context)
                if send_success:
                    self.write(cr, uid, ids, {'is_send_email_erp_bonus_schedue':False}, context)
        return True
    
    
    def update_candidate_to_employee_detail(self, cr, uid, ids, update_data, context=None):
        if not update_data:
            update_data = {}
        
        contract_obj = self.pool.get('hr.contract')
        update_val = {}      
        update_val['employee_id'] = update_data.get('emp_id', False) and update_data['emp_id'] or False
        if not update_data.get('emp_id', False):
            raise osv.except_osv('Validation Error !', 'Employee field cannot be blank!')

        columns = self._columns
        for offer_key, emp_key in OFFER_APPLICANT_EMPLOYEE.iteritems():
            type_column = offer_key != 'id' and columns[offer_key]._type or ''
            if type_column == 'many2one':
                update_val[emp_key] = update_data.get(offer_key, False) and update_data[offer_key][0] or False
            else:
                update_val[emp_key] = update_data.get(offer_key, False)
            
            #Get for level by person
            if offer_key == 'offer_job_level_position_id':
                update_val['job_level_person_id']= update_val[emp_key]
        
        department_group_id = update_val.get('department_group_id', False)
        if department_group_id:
            group = self.pool.get('hr.department').read(cr, uid, department_group_id, ['name','organization_class_id'], context=context)
            
            organization_class_id = group.get('organization_class_id', False) and group['organization_class_id'][0] or False
            if organization_class_id:
                organization_class = self.pool.get('vhr.organization.class').read(cr, uid, organization_class_id, ['level'])
                level = organization_class.get('level',0)
                if level == 1:    
                    update_val['division_id'] = update_val['department_group_id']
                    update_val['department_group_id'] = False
                    
        contract_obj.update_data_from_candidate(cr, uid, update_val, context=context)
        return True

    def update_offer_from_contract(self, cr, uid, ids, data, context=None):
        for job_app_item in self.browse(cr, uid, ids, context=context):
            if job_app_item.state == 'offer':
                self.execute_write(cr, uid, job_app_item.id, data, context)
        return True

    def cancel_offer_from_contract(self, cr, uid, ids, context=None):
        for job_app_item in self.browse(cr, uid, ids, context=context):
            if job_app_item.state == 'offer':
                self.execute_workflow(cr, uid, job_app_item.id, {'ACTION': SIGNAL_OFFER_CLOSE})
        return True
    
    def sign_offer_from_contract(self, cr, uid, ids, context=None):
        if not isinstance(ids, list):
            ids = [ids]
        #done employee
        state_candidate_new = 'employee'
        job_app_item = self.browse(cr, uid, ids[0], context=context)
        applicant_id = job_app_item.applicant_id and job_app_item.applicant_id.id or False
        emp_id = job_app_item.emp_id and job_app_item.emp_id.id or False
        if job_app_item.state == 'offer':
            self.execute_workflow(cr, uid, job_app_item.id, {'ACTION': SIGNAL_OFFER_DONE})
            if applicant_id and job_app_item.applicant_id.state == 'offered':
                cr.execute('update hr_applicant set state = %s\
                        where id = %s',(state_candidate_new,applicant_id))
       
        if applicant_id and emp_id:
            self.pool.get('hr.applicant').write(cr, uid, [applicant_id], {'ex_employee': True}, context=context)
            #update working background
            working_background = self.pool.get('vhr.working.background')
            lst_wb = working_background.search(cr, uid, [('applicant_id','=', applicant_id)])
            if lst_wb: 
                working_background.write(cr, uid, lst_wb, {'employee_id': emp_id})
            #update certificate information
            certificate_info = self.pool.get('vhr.certificate.info')
            lst_ci = certificate_info.search(cr, uid, [('applicant_id','=', applicant_id)])
            if lst_ci: 
                certificate_info.write(cr, uid, lst_ci, {'employee_id': emp_id})
                
        #generate ERP
        self.pool.get('vhr.erp.bonus.payment').create_erp_bonus_payment(cr, uid, ids[0])
        
        return True

    def signal_workflow_ex(self, cr, uid, id_signal, signal, context=None):
        self.signal_workflow(cr, uid, [id_signal], signal)
        state = self.browse(cr, uid, id_signal, context=context).state
        signal_newstate = SIGNAL_JA[signal]['new_state']
        if state == signal_newstate:
            return True
        return False

    def execute_workflow(self, cr, uid, ids, context=None):
        if not isinstance(ids, list): ids = [ids]
        if context is None: context = {}
        result = False
        if 'ACTION' in context and context['ACTION']:
            job_app_id = ids[0]
            hr_job_obj = self.pool['hr.job']
            job_item = self.browse(cr, uid, job_app_id, context=context).job_id
            # kiem tra so luong nguoi offer & transfer phai bang so luong nguoi tuyen dung
            if context['ACTION'] == SIGNAL_CLOSE_OFFER:
                transfer_candb = self.search(cr, uid, [('job_id', '=', job_item.id), ('state', 'in', ['done', 'offer']),
                                                   ('hr_process', '=', True)], count=True, context=context)
                if transfer_candb >= job_item.no_of_recruitment:
                    raise osv.except_osv('Validation Error !', 'Please check request quantity and number candidate offer and done')
            # từ done -> close khi reopen chuyển về lại offer
            if context['ACTION'] == SIGNAL_CLOSE_DONE:
                context['ACTION'] = SIGNAL_CLOSE_OFFER
            result = self.signal_workflow_ex(cr, uid, job_app_id, context['ACTION'])
            if result:
                self.write_change_state(cr, uid, job_app_id, context['ACTION'], context.get('ACTION_COMMENT', ''))
                # kiểm tra cứ mỗi match cv tới trạng thái cuối done request
                if context['ACTION'] in [SIGNAL_DRAFT_CLOSE, SIGNAL_CONFIRM_CLOSE, SIGNAL_INTERVIEW_CLOSE]:
                    if job_item.no_of_recruitment == job_item.no_of_hired_recruitment:
                        job_app_end_step_count = self.search(cr, uid, [('job_id', '=', job_item.id),'|',
                                                                       ('state', 'in', ['close', 'done']),
                                                                       '&',('state', '=', 'offer'),('hr_process','=',True)],
                                                             count=True, context=context)
                        #browse again reload from database
                        job_item = hr_job_obj.browse(cr, uid, job_item.id, context=context)
                        if len(job_item.job_applicant_ids)==job_app_end_step_count:
                            hr_job_obj.execute_workflow(cr, uid, job_item.id, {'ACTION': 'in_progress_done'})
                # kiểm tra close một match cv thì reopen request
                if context['ACTION'] in [SIGNAL_OFFER_CLOSE, SIGNAL_DONE_CLOSE]:
                    job_item = hr_job_obj.browse(cr, uid, job_item.id, context=context)
                    if job_item.state == 'done':
                        hr_job_obj.execute_workflow(cr, uid, job_item.id, {'ACTION': 'done_in_progress'})
                if context['ACTION'] in [SIGNAL_CLOSE_OFFER]:
                    super(vhr_job_applicant, self).write(cr, uid, ids, {'join_date': None}, context)
                if context['ACTION'] in [SIGNAL_CLOSE_DRAFT,SIGNAL_CLOSE_CONFIRM,SIGNAL_CLOSE_INTERVIEW]:
                    job_app = self.browse(cr, uid, job_app_id, context=context)
                    if job_app.applicant_id.state == 'opening':
                        self.pool.get('hr.applicant').write(cr, uid, job_app.applicant_id.id,{'state':'processing'}, context)
                        state = job_app.applicant_id.state
        return result

    def vhr_job_applicant_workflow(self, cr, uid, ids, action, context=None):
        res = self.write(cr, uid, ids, {'state': action})
        if action == OFFER and res:
            hr_job = self.pool.get('hr.job')
            for job_app_item in self.browse(cr, uid, ids, context=context):
                if job_app_item.none_official and (not job_app_item.no_depthead_approval):
                    job_obj = job_app_item.job_id
                    depthead = job_obj.department_id.manager_id if job_obj.department_id else False
                    if depthead:
                        rr_email_obj = self.pool['vhr.recruitment.email'] 
                        lst_approvers = self.pool['vhr.delegate.by.depart'].get_delegate(
                            cr, uid, depthead.id, {'delegate': True, 'department_id': job_obj.department_id.id})
                        link_email = hr_job.get_url(cr, uid, job_obj.id, context)
                        for approver in self.pool['hr.employee'].browse(cr, uid, lst_approvers, context=context):
                            if approver.work_email:
                                rr_email_obj.send_email(cr, uid, EMAIL_DEPTHEAD_NONE_OFFICAL,
                                        {'email_to': approver.work_email.lower(), 'link_email': link_email,
                                         'approver': approver.id, 'job_id': job_obj.id, 'request_code': job_obj.code},
                                        context={'APPROVE_EMAIL': True})
                    else:
                        log.error('vhr_job_applicant : vhr_job_applicant_workflow : fail at job_applicant_id %s' % (job_app_item.id)) 

        return res

    def write_change_state(self, cr, uid, ids, signal, comment="", context=None):
        if not isinstance(ids, list):
            ids = [ids]
        state_change_obj = self.pool['vhr.state.change']
        applicant_obj = self.pool['hr.applicant']
        job_app_obj = self.pool['vhr.job.applicant']
        change_state_ids = []
        for item in ids:
            state_vals = SIGNAL_JA[signal]
            state_vals['model'] = self._name
            state_vals['res_id'] = item
            state_vals['comment'] = comment
            if state_vals['new_state'] == OFFER or state_vals['new_state'] == CLOSE:
                applicant_id = job_app_obj.browse(cr, uid, item, context=context).applicant_id.id
                if state_vals['new_state'] == OFFER:
                    applicant_obj.write_change_state(cr, uid, applicant_id, STATE_APP[2][0], u'Candidate offer',context)
                elif state_vals['new_state'] == CLOSE:
                    applicant_obj.write_change_state(cr, uid, applicant_id, STATE_APP[0][0], u' ', context)
            state_change_id = state_change_obj.create(cr, uid, state_vals)
            change_state_ids.append(state_change_id)
        return change_state_ids
    def _is_contract_definite(self, cr, uid, ids, fields, args, context=None):
        result = {}
        check = False
        for data in self.browse(cr, uid, ids, context=context):
            result[data.id]={
             'is_contract_definite':False,
             }
            if data.contract_type_id and data.contract_type_id.contract_type_group_id\
            and data.contract_type_id.contract_type_group_id.code in ('3','4'):
                result[data.id]['is_contract_definite'] =  True
        return result
    
    _columns = {
        # Job information
        'job_id': fields.many2one('hr.job', 'Job Name', ondelete='restrict'),
        'job_code': fields.related('job_id', 'code', readonly=True, type='char', relation='hr.job',string='Code'),
        'requestor_id': fields.related('job_id', 'requestor_id', readonly=True, type='many2one', relation='hr.employee',
                                       string='Requester'),
        'handle_by': fields.related('job_id', 'handle_by', readonly=True, type='many2one', relation='hr.employee',
                                    string='Handle by'),
        'share_handle_by': fields.related('job_id', 'share_handle_by', readonly=True, type='many2one', relation='hr.employee',
                                          string='Share Handle by'),
        'requestor_dept': fields.related('job_id', 'requestor_dept', readonly=True, type='many2one',
                                         relation='hr.department', string='Department'),
        'job_title_id': fields.related('job_id', 'job_title_id', readonly=True, type='many2one',
                                       relation='vhr.job.title', string='Title/Role'),
        'job_level_id': fields.related('job_id', 'job_level_id', readonly=True, type='many2one',
                                       relation='vhr.job.level', string='Level'),
        #New Job Level
        'job_level_position_id': fields.related('job_id', 'job_level_position_id', readonly=True, type='many2one',
                                       relation='vhr.job.level.new', string='Person Level'),
                
        'sub_group_id': fields.related('job_id', 'sub_group_id', readonly=True, type='many2one',
                                       relation='vhr.sub.group', string='Sub Group'),
        'job_group_id': fields.related('job_id', 'job_group_id', readonly=True, type='many2one',
                                       relation='vhr.job.group', string='Job Group'),
        'job_family_id': fields.related('job_id', 'job_family_id', readonly=True, type='many2one',
                                       relation='vhr.job.family', string='Job Family'),
        'career_track_id': fields.related('job_id', 'career_track_id', readonly=True, type='many2one',
                                       relation='vhr.dimension', string='Career Track'),
        'gender': fields.related('job_id', 'gender', readonly=True, type='selection',
                                 selection=[('male', 'Male'), ('female', 'Female'), ('any', 'Any')],
                                 string='Gender'),
        'no_of_recruitment': fields.related('job_id', 'no_of_recruitment', readonly=True, type='char',
                                            relation='hr.job', string='Expected New Employees'),
        'report_to': fields.related('job_id', 'report_to', readonly=True, type='many2one', relation='hr.employee',
                                    string='Report To'),
        'department_id': fields.related('job_id', 'department_id', readonly=True, type='many2one',
                                        relation='hr.department', string='Department'),
        'degree_id': fields.related('job_id', 'degree_id', readonly=True, type='many2one',
                                    relation='vhr.certificate.level', string='Education Level'),
        'reason_id': fields.related('job_id', 'reason_id', readonly=True, type='many2one', relation='vhr.dimension',
                                    string='Reason'),
        'office_id': fields.related('job_id', 'office_id', readonly=True, type='many2one', relation='vhr.office',
                                    string='Working Place'),
        'job_type_id': fields.related('job_id', 'job_type_id', readonly=True, type='many2one', relation='vhr.dimension',
                                      string='Job Type'),
        'position_class_standard': fields.related('job_id', 'position_class_standard', readonly=True, type='char',
                                                  relation='hr.job', string='Position class standard'),
        'position_class_standard_ex': fields.related('job_id', 'position_class_standard_ex', readonly=True, type='many2many',
                                                     relation='vhr.position.class', string='Position class standard'),
        'categ_ids_job': fields.related('job_id', 'categ_ids', readonly=True, type='many2many',
                                        relation='hr.applicant_category', string='Skills'),
        'none_official': fields.related('job_id', 'none_official', readonly=True, type='boolean',
                                                  relation='hr.job', string='None Official'),
        'no_depthead_approval': fields.related('job_id', 'no_depthead_approval', readonly=True, type='boolean',
                                               relation='hr.job', string='Depthead Approval'),
        'job_state': fields.related('job_id', 'state', readonly=True, type='char',
                                    relation='hr.job', string='Job State'),
        'department_dept': fields.related('job_id', 'department_dept', readonly=True, type='many2one',
                                          relation='hr.employee', string='Request Depthead'),
        'department_hrbps': fields.related('job_id', 'department_hrbps', type="many2many", relation='hr.employee',
                                           string='HRBPs'),
        'company_id': fields.related('job_id', 'company', type="many2one", relation='res.company',
                                     string='Request for company*'),
        # Applicant information
        'applicant_id': fields.many2one('hr.applicant', 'Applicant Info', ondelete='restrict', context={'FROM_VIEW': 'CAND_INTERVIEW'}),
        'applicant_name': fields.related('applicant_id', 'name', readonly=True, type='char', relation='hr.applicant', string="Name"),
        'email': fields.related('applicant_id', 'email', readonly=True, type='char', relation='hr.applicant',
                                string="Email"),
        'mobile': fields.related('applicant_id', 'mobile', readonly=True, type='char', relation='hr.applicant',
                                 string="Mobile"),
        'birthday_app': fields.related('applicant_id', 'birthday', readonly=True, type='date', relation='hr.applicant',
                                       string="DOB"),
        'gender_app': fields.related('applicant_id', 'gender', readonly=True, type='selection',
                                     selection=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')],
                                     relation='hr.applicant', string="Gender"),
        'job_type_id_app': fields.related('applicant_id', 'job_type_id', readonly=True, type='many2one',
                                          relation='vhr.dimension', string='Job Type'),
        'source_id_app': fields.related('applicant_id', 'source_id', readonly=True, type='many2one',
                                        relation='hr.recruitment.source', string='Source'),
        'source_type_id_app': fields.related('applicant_id', 'source_type_id', readonly=True, type='many2one',
                                        relation='vhr.recruitment.source.type', string='Source Type'),
        'recommender_id_app': fields.related('applicant_id', 'recommender_id', readonly=True, type='many2one',
                                        relation='hr.employee', string='Recommender'),
        'office_id_app': fields.related('applicant_id', 'office_id', readonly=True, type='many2one',
                                        relation='vhr.office', string='Location'),
        'willing_location_app': fields.related('applicant_id', 'willing_location', readonly=True, type='boolean',
                                               relation='hr.applicant', string='Willing location'),
        'title_ids_app': fields.related('applicant_id', 'title_ids', readonly=True, type='many2many',
                                        relation='vhr.job.title', string='Titles'),
        'categ_ids_app': fields.related('applicant_id', 'categ_ids', readonly=True, type='many2many',
                                        relation='hr.applicant_category', string='Skills'),
        'note_erp_app': fields.related('applicant_id', 'note_erp', readonly=True, type='text', relation='hr.applicant',
                                       string='Note for ERP'),
        'emp_receive_cvs': fields.many2many('hr.employee', 'job_applicant_employee_rel', 'job_applicant_id', 'employee_id', 'Send CV To'),
        'emp_cc_cvs': fields.many2many('hr.employee', 'job_applicant_cc_emp_rel', 'candidate_id', 'employee_id', 'CC To'),
        # other
        'state': fields.selection([('draft', 'Matching'),
                                   ('confirm', 'Confirm'),
                                   ('interview', 'Interview'),
                                   ('offer', 'Offer'),
                                   ('done', 'Done'),
                                   ('close', 'Close'),
                                   ], 'Status'),
        # move from interview
        'current_salary': fields.related('applicant_id', 'current_salary', type='float', digits=(12,3),
                                         relation='hr.applicant', string='Current salary'),
        'expected_salary': fields.related('applicant_id', 'expected_salary', type='float', digits=(12,3),
                                          relation='hr.applicant', string='Expected salary'),
        'longterm_commit': fields.selection([('high', 'High'), ('medium', 'Medium'), ('low', 'Low')], string="Long-term commitment",
                                            help="Long-term commitment to work with the company"),
        'ability_overtime': fields.selection([('high', 'High'), ('medium', 'Medium'), ('low', 'Low')], string="Ability to work overtime"),
        'received_working_date': fields.date('Received working date'),
        # 'interview1'
        'interview_round_id1': fields.many2one('vhr.dimension', 'Interview Round',
                                               domain=[('dimension_type_id.code', '=', 'INTERVIEW_ROUND'), ('active', '=', True)]),
        'dept_interviewer1': fields.many2many('hr.employee', 'employee_dept_interviewer1_rel', 'dept_interviewer_id',
                                              'emp_id', 'Department Interviewer'),
        'rr_interviewer1': fields.many2many('hr.employee', 'employee_rr_interviewer1_rel', 'rr_interviewer_id', 'emp_id',
                                            'RR Interviewer'),
        'reporter1': fields.many2one('hr.employee', 'Reporter'),
        'involved_persons1': fields.many2many('hr.employee', 'interview_employee_involved1_rel', 'interview_id', 'emp_id',
                                              'Involved persons'),
        'start_time_round1': fields.datetime('Start Time'),
        'end_time_round1': fields.datetime('End Time'),
        'room_id1': fields.many2one('vhr.room', 'Room'),
        'evaluation_details1': fields.one2many('vhr.interview.round.evaluation', 'job_applicant_id',
                                               'Evaluation Details', domain=[('evaluation_id.interview_round_id.code', '=', 'R1')]),
        'note1': fields.text('Note'),
        'send_mail1': fields.selection([('mail_msg', 'Mail Message'), ('mail_calendar', 'Mail Calendar')]),
        'decision_id1': fields.many2one('vhr.dimension', 'Decision',
                                        help="Next interview : Phỏng vấn vòng tiếp theo\nPass and offer : Ứng viên phù hợp với vị trí tiến hành offer\
                                        \nPass and none offer : Ứng viên phù hợp với vị trí, nhưng đã tuyển được ứng viên thích hợp hơn\nFail : Ứng viên không phù hợp với vị trí",
                                        domain=[('dimension_type_id.code', '=', 'DECISION_STATUS'), ('active', '=', True)]),
        # 'interview2'
        'interview_round_id2': fields.many2one('vhr.dimension', 'Interview Round',
                                               domain=[('dimension_type_id.code', '=', 'INTERVIEW_ROUND'), ('active', '=', True)]),
        'dept_interviewer2': fields.many2many('hr.employee', 'employee_dept_interviewer2_rel', 'dept_interviewer_id',
                                              'emp_id', 'Department Interviewer'),
        'rr_interviewer2': fields.many2many('hr.employee', 'employee_rr_interviewer2_rel', 'rr_interviewer_id', 'emp_id',
                                            'RR Interviewer'),
        'reporter2': fields.many2one('hr.employee', 'Reporter'),
        'involved_persons2': fields.many2many('hr.employee', 'interview_employee_involved2_rel', 'interview_id', 'emp_id',
                                              'Involved persons'),
        'start_time_round2': fields.datetime('Start Time'),
        'end_time_round2': fields.datetime('End Time'),
        'room_id2': fields.many2one('vhr.room', 'Room'),
        'evaluation_details2': fields.one2many('vhr.interview.round.evaluation', 'job_applicant_id',
                                               'Evaluation Details', domain=[('evaluation_id.interview_round_id.code', '=', 'R2')]),
        'note2': fields.text('Note'),
        'send_mail2': fields.selection([('mail_msg', 'Mail Message'), ('mail_calendar', 'Mail Calendar')]),
        'decision_id2': fields.many2one('vhr.dimension', 'Decision',
                                        help="Next interview : Phỏng vấn vòng tiếp theo\nPass and offer : Ứng viên phù hợp với vị trí tiến hành offer\
                                        \nPass and none offer : Ứng viên phù hợp với vị trí, nhưng đã tuyển được ứng viên thích hợp hơn\nFail : Ứng viên không phù hợp với vị trí",
                                        domain=[('dimension_type_id.code', '=', 'DECISION_STATUS'), ('active', '=', True)]),
        # 'interview3'
        'interview_round_id3': fields.many2one('vhr.dimension', 'Interview Round',
                                               domain=[('dimension_type_id.code', '=', 'INTERVIEW_ROUND'), ('active', '=', True)]),
        'dept_interviewer3': fields.many2many('hr.employee', 'employee_dept_interviewer3_rel', 'dept_interviewer_id',
                                              'emp_id', 'Department Interviewer'),
        'rr_interviewer3': fields.many2many('hr.employee', 'employee_rr_interviewer3_rel', 'rr_interviewer_id', 'emp_id',
                                            'RR Interviewer'),
        'reporter3': fields.many2one('hr.employee', 'Reporter'),
        'involved_persons3': fields.many2many('hr.employee', 'interview_employee_involved3_rel', 'interview_id', 'emp_id',
                                              'Involved persons'),
        'start_time_round3': fields.datetime('Start Time'),
        'end_time_round3': fields.datetime('End Time'),
        'room_id3': fields.many2one('vhr.room', 'Room'),
        'evaluation_details3': fields.one2many('vhr.interview.round.evaluation', 'job_applicant_id',
                                               'Evaluation Details', domain=[('evaluation_id.interview_round_id.code', '=', 'R3')]),
        'note3': fields.text('Note'),
        'send_mail3': fields.selection([('mail_msg', 'Mail Message'), ('mail_calendar', 'Mail Calendar')]),
        'decision_id3': fields.many2one('vhr.dimension', 'Decision',
                                        help="Pass and offer : Ứng viên phù hợp với vị trí tiến hành offer\
                                        \nPass and none offer : Ứng viên phù hợp với vị trí, nhưng đã tuyển được ứng viên thích hợp hơn\nFail : Ứng viên không phù hợp với vị trí",
                                        domain=[('dimension_type_id.code', '=', 'DECISION_STATUS'), ('active', '=', True)]),
        # control show/ hide page
        'is_pass': fields.boolean('Is Pass'),
        # recruitment info
        'offer_department': fields.many2one('hr.department', 'Department', ondelete='restrict',
                                            domain="[('organization_class_id.level','in',[3,6])]"),
        'offer_team_id': fields.many2one('hr.department', 'Team', ondelete='restrict',
                                            domain="[('parent_id','=', offer_department)]"),
        'offer_department_group_id': fields.related('offer_department', 'parent_id', readonly=True, type='many2one',
                                            relation='hr.department', string='Offer for Department Group'),
        'offer_division_id': fields.related('offer_department_group_id', 'parent_id', readonly=True, type='many2one',
                                            relation='hr.department', string='Offer for Business Unit'),
        'offer_manager_id': fields.related('offer_department', 'manager_id', readonly=True, type='many2one',
                                           relation='hr.employee', string='Manager'),
        'offer_report_to': fields.many2one('hr.employee', 'Report to', ondelete='restrict'),
        'offer_mentor': fields.many2one('hr.employee', 'Mentor', ondelete='restrict'),
        'offer_job_type': fields.many2one('vhr.dimension', 'Job Type', ondelete='restrict',
                                          domain=[('dimension_type_id.code', '=', 'JOB_TYPE'), ('active', '=', True)]),
        'offer_office_id': fields.many2one('vhr.office', 'Working Place', ondelete='restrict'),

        'offer_date': fields.date('Offer date'),
        'offer_job_level_id': fields.many2one('vhr.job.level', 'Level Offer', ondelete="restrict"),
        #New Job Level
        'offer_job_level_position_id': fields.many2one('vhr.job.level.new', 'Person Level Offer', ondelete='restrict'),
        
        'offer_job_title_id': fields.many2one('vhr.job.title', 'Title Offer', ondelete="restrict"),
        'offer_sub_group_id': fields.many2one('vhr.sub.group', 'Sub Group', ondelete='restrict'),
        'offer_job_group_id': fields.many2one('vhr.job.group', string='Job Group', ondelete='restrict'),
        'offer_job_family_id': fields.many2one('vhr.job.family', string='Job Family Offer', ondelete='restrict'),
        'offer_career_track_id': fields.many2one('vhr.dimension', 'Career Track', domain=[('dimension_type_id.code','=','CAREER_TRACK')], ondelete='restrict'),
        
#         'offer_job_group_id': fields.related('offer_sub_group_id', 'job_group_id', type="many2one", store=True,
#                                              relation='vhr.job.group', string='Job Group'),
#         'offer_job_family_id': fields.related('offer_job_group_id', 'job_family_id', type="many2one", store=True,
#                                               relation='vhr.job.family', string='Job Family Offer'),
        'offer_gross_salary': fields.float('Salary (Gross)', digits=(12, 3)),
        'offer_probation_salary': fields.float('Probation Salary', digits=(12, 3)),
        'offer_company_id': fields.many2one('res.company', 'Working for',
                                            domain="[('com_group_id', '=', offer_com_group_id)]"),
        'offer_com_group_id': fields.many2one('vhr.company.group', 'Company group'),
        'contract_type_id': fields.many2one('hr.contract.type', 'Probationary type'),
        'position_class_apply': fields.char('Position Class Apply'),
         #LuanNG: Remove this field in future version of vHRS
        'position_class_apply_ex': fields.many2one('vhr.position.class'),
        'note_for_asset': fields.text('Noted For Special Asset'),
        'join_date': fields.date('Join date'),
        # current row
        'current_row': fields.selection(ROUND_INTER, string="Interview"),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'History',
                                         domain=[('object_id.model', '=', _name), ('field_id.name', 'not in', ['write_date', 'audit_log_ids'])]),
        # get currency
        'company_currency_id': fields.related('job_id', 'company', 'currency_id', type='many2one', relation='res.currency', string='Currency'),
        # state log
        'state_log_ids': fields.one2many('vhr.state.change', 'res_id', 'History', domain=[('model', '=', _name)]),
        # ex employee
        'ex_employee': fields.related('applicant_id', 'ex_employee', type='boolean', relation='hr.applicant', string='Ex-employee'),
        'is_new_emp': fields.boolean('is new Emp'), #  first time update employee
        'emp_id': fields.related('applicant_id', 'emp_id', type='many2one', relation='hr.employee', string='Employee'),
        'is_create_account': fields.selection([('yes', 'Yes'), ('no', 'No')], 'Create account'),
        'is_asset': fields.selection([('yes', 'Yes'), ('no', 'No')], 'Asset'),
        'hr_process': fields.boolean('Hr Process'),
        'finish_interviewer': fields.many2one('hr.employee', 'Employees'),
        'reason_cancel_type_id': fields.many2one('vhr.dimension', 'Reason Cancel Type',
                                                 domain=[('dimension_type_id.code', '=', 'CANCEL_OFFER_TYPE'), ('active', '=', True)]),
        # remove next build
        'reason_cancel_id': fields.many2one('vhr.close.reason', 'Reason Cancel', domain="[('reason_type_id', '=', reason_cancel_type_id)]"),
        'reason_cancel_ids': fields.many2many('vhr.close.reason', 'jobapllicant_reasoncancel_rel', 'job_id', 'reason_id', 'Reasons',
                                              domain="[('reason_type_id', '=', reason_cancel_type_id)]"),
        'transfer_canb': fields.date('Transfer C&B'),
        # check if start date less than current date lock offer tab
        'is_offer_edit': fields.function(_check_editable, method=True, type='boolean', string='offer editable'),
        'cancel_offer_date': fields.function(_get_cancel_date, method=True, type='date', string='Cancel Offer Date'),
        'is_reporter': fields.function(_is_reporter, method=True, type="boolean", string="Is Reporter"),
        # Show for depthead
        'is_depthead': fields.function(_is_depthead, method=True, type="boolean", string="Is Depthead"),
        'change_offer_email': fields.text('Change offer email'),
        'keep_in_view_1': fields.boolean('Keep in view 1'),
        'keep_in_view_2': fields.boolean('Keep in view 2'),
        'keep_in_view_3': fields.boolean('Keep in view 3'),
        'is_keep_in_view': fields.function(_is_keep_in_view, method=True, type="boolean", string="Keep in view"),
        #25/5/2015
        'hrs_job_level_id': fields.many2one('vhr.job.level', 'Level Mapping', ondelete="restrict"),
        #New Job Level
        'hrs_job_level_position_id': fields.many2one('vhr.job.level.new', 'Person Level Mapping', ondelete='restrict'),
        
        'hrs_job_title_id': fields.many2one('vhr.job.title', 'Title Mapping', ondelete="restrict"),
        'create_date': fields.datetime('Create date'),
        'not_probation': fields.boolean('is not Probation Contract'),
        #22/5/2015
        
#         'change_form_id': fields.many2one('vhr.change.form', 'Change Form', ondelete='restrict'),

        # BinhNX: Add new field business_impact_id for RR Report in 2016
        # Change name from Business Impact to Urgency
        'business_impact_id':  fields.many2one('vhr.business.impact', 'Urgency', ondelete='restrict',
                                               domain=[('active', '=', True)]),
                
        'is_official': fields.boolean(string='Is Official'),
        
        'transfer_id': fields.many2one('vhr.rr.transfer.employee', 'Transfer Employee', ondelete="restrict"),
        
        'bonus_payment_reruitment_mail_id': fields.many2one('vhr.erp.bonus.payment.reruitment.mail', 'Bonus Payment For Send Mail', ondelete="restrict"),
        
        #Print Offer Definite
        'com_signer':fields.related('offer_company_id','sign_emp_id',readonly=True, type='char', relation='res.company', string="Signer"),
        'com_title_signer':fields.related('offer_company_id','job_title_id',readonly=True, type='char', relation='res.company', string="Title Signer"),
        'com_phone':fields.related('offer_company_id','phone',readonly=True, type='char', relation='res.company', string="Phone"),
        'com_street': fields.char('Company Street'),
        'com_fax': fields.char('Company Fax'),
        'gender_app_contract': fields.char('Gender'),
        'com_authorization_date':fields.related('offer_company_id','authorization_date',readonly=True, type='date', relation='res.company', string="Authorization Date"),
        'com_country_signer':fields.related('offer_company_id','country_signer',readonly=True, type='many2one', relation='res.country', string="country signer"),
        'com_partner_id':fields.related('offer_company_id','partner_id',readonly=True, type='many2one', relation='res.partner', string="Partner"),
        'date_end_contract': fields.date('Date End'),
        'v_bonus_contract': fields.float('V Bonus Contract'),
        'gross_salary_contract': fields.float('Gross Salary Contract'),
        'basic_salary_contract': fields.float('Gross Basic Contract'),
        'employee_code_definite': fields.char('Employee Code Definite'),
        'department_code_definite': fields.related('offer_department','code',readonly=True, type='char', relation='hr.department', string="Department Code"),
        'is_contract_definite': fields.function(_is_contract_definite, type='boolean', string='Is Contract Definite',
                    multi="is_contract_definite"),
                
        'is_send_email_erp_bonus_schedue': fields.boolean(string='Is Schedue'),
        'user_transfer': fields.many2one('res.users', 'User Transfer'),
        
        'share_handle_bys': fields.related('job_id', 'share_handle_bys', readonly=True, type='many2many', relation='hr.employee',
                                    string='Share Handle by'),
    }

    _defaults = {
        'state': 'draft',
        'is_new_emp': True,
        'hr_process': False,
        'not_probation': False,
        'is_official': True, 
        'is_send_email_erp_bonus_schedue':False,
    }
    _order = 'id desc'

    # Note : will change to task and code
    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        reads = super(vhr_job_applicant, self).read(cr, uid, ids, ['job_id', 'applicant_id'], context=context)
        res = []
        for record in reads:
            job = ''
            applicant = ''
            if record.get('job_id', ''):
                job = record['job_id'][1]
            if record.get('applicant_id', ''):
                applicant = record['applicant_id'][1]
            name = job + ' / ' + applicant
            res.append((record['id'], name))
        return res

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if context is None:
            context = {}
        res = super(vhr_job_applicant, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar=toolbar, submenu=submenu)
        if view_type == 'form':
            doc = etree.XML(res['arch'])
            roles = self.recruitment_get_group_array(cr, uid, uid)
            if 'ACTION' in context and context.get('active_id', False):
                node = doc.xpath("//form/separator")[0].getparent()
                if node:
                    if 'required_comment' in context and context['required_comment']:
                        node_notes = etree.Element('field', name="action_comment", colspan="4", modifiers=json.dumps({'required': True}))
                    else:
                        node_notes = etree.Element('field', name="action_comment", colspan="4")
                    node.append(node_notes)
                    res['arch'] = etree.tostring(doc)
                    res['fields'].update(
                        {'action_comment': {'selectable': True, 'string': 'Action Comment', 'type': 'text', 'views': {}}})
            if 'FROM_VIEW' in context and context['FROM_VIEW'] == 'APPLICANT':
                nodes = doc.xpath("//sheet/button")
                for node in nodes:
                    node.set('modifiers', json.dumps({'invisible': True}))
            if RECRUITER not in roles:
                # round 1
                nodes = doc.xpath("//field[@name='dept_interviewer1']")
                for node in nodes:
                    node.set('modifiers', json.dumps({'readonly': True, 'required': [('state', '=', 'interview')]}))
                nodes = doc.xpath("//field[@name='rr_interviewer1']")
                for node in nodes:
                    node.set('modifiers', json.dumps({'readonly': True, 'required': [('state', '=', 'interview')]}))
                nodes = doc.xpath("//field[@name='reporter1']")
                for node in nodes:
                    node.set('modifiers', json.dumps({'readonly': True, 'required': [('state', '=', 'interview')]}))
                nodes = doc.xpath("//field[@name='start_time_round1']")
                for node in nodes:
                    node.set('modifiers', json.dumps({'readonly': True}))
                nodes = doc.xpath("//field[@name='end_time_round1']")
                for node in nodes:
                    node.set('modifiers', json.dumps({'readonly': True}))
                nodes = doc.xpath("//field[@name='room_id1']")
                for node in nodes:
                    node.set('modifiers', json.dumps({'readonly': True}))
                nodes = doc.xpath("//field[@name='involved_persons1']")
                for node in nodes:
                    node.set('modifiers', json.dumps({'readonly': True}))
                # round 2
                nodes = doc.xpath("//field[@name='dept_interviewer2']")
                for node in nodes:
                    node.set('modifiers', json.dumps({'readonly': True, 'required': ['&', ('state', '=', 'interview'),
                                                                                     ('current_row', '=', 'round2')]}))
                nodes = doc.xpath("//field[@name='rr_interviewer2']")
                for node in nodes:
                    node.set('modifiers', json.dumps({'readonly': True, 'required': ['&', ('state', '=', 'interview'),
                                                                                     ('current_row', '=', 'round2')]}))
                nodes = doc.xpath("//field[@name='reporter2']")
                for node in nodes:
                    node.set('modifiers', json.dumps({'readonly': True, 'required': ['&', ('state', '=', 'interview'),
                                                                                     ('current_row', '=', 'round2')]}))
                nodes = doc.xpath("//field[@name='start_time_round2']")
                for node in nodes:
                    node.set('modifiers', json.dumps({'readonly': True}))
                nodes = doc.xpath("//field[@name='end_time_round2']")
                for node in nodes:
                    node.set('modifiers', json.dumps({'readonly': True}))
                nodes = doc.xpath("//field[@name='room_id2']")
                for node in nodes:
                    node.set('modifiers', json.dumps({'readonly': True}))
                nodes = doc.xpath("//field[@name='involved_persons2']")
                for node in nodes:
                    node.set('modifiers', json.dumps({'readonly': True}))
                # round 3
                nodes = doc.xpath("//field[@name='dept_interviewer3']")
                for node in nodes:
                    node.set('modifiers', json.dumps({'readonly': True, 'required': ['&', ('state', '=', 'interview'),
                                                                                     ('current_row', '=', 'round3')]}))
                nodes = doc.xpath("//field[@name='rr_interviewer3']")
                for node in nodes:
                    node.set('modifiers', json.dumps({'readonly': True, 'required': ['&', ('state', '=', 'interview'),
                                                                                     ('current_row', '=', 'round3')]}))
                nodes = doc.xpath("//field[@name='reporter3']")
                for node in nodes:
                    node.set('modifiers', json.dumps({'readonly': True, 'required': ['&', ('state', '=', 'interview'),
                                                                                     ('current_row', '=', 'round3')]}))
                nodes = doc.xpath("//field[@name='start_time_round3']")
                for node in nodes:
                    node.set('modifiers', json.dumps({'readonly': True}))
                nodes = doc.xpath("//field[@name='end_time_round3']")
                for node in nodes:
                    node.set('modifiers', json.dumps({'readonly': True}))
                nodes = doc.xpath("//field[@name='room_id3']")
                for node in nodes:
                    node.set('modifiers', json.dumps({'readonly': True}))
                nodes = doc.xpath("//field[@name='involved_persons3']")
                for node in nodes:
                    node.set('modifiers', json.dumps({'readonly': True}))
            dicti = {}
            self.view_factory(cr, uid, doc, dicti, roles, context)
            res['arch'] = etree.tostring(doc)
        return res

    def check_interview_data(self, cr, uid, vals, job_app_obj, context=None):
        '''
           điều kiện : nếu có decision bắt buộc phải nhập toàn bộ evaluation
        '''
        if vals.get('decision_id1', False) or vals.get('decision_id2', False) or vals.get('decision_id3', False):
            if vals.get('decision_id1', False):
                evaluation = 'evaluation_details1'
                eval_obj = job_app_obj.evaluation_details1
            elif vals.get('decision_id2', False):
                evaluation = 'evaluation_details2'
                eval_obj = job_app_obj.evaluation_details2
            else:
                evaluation = 'evaluation_details3'
                eval_obj = job_app_obj.evaluation_details3

            if evaluation in vals:
                for item in vals[evaluation]:
                    if isinstance(item[2], dict):
                        if 'note' in item[2] and not item[2]['note']:
                            raise osv.except_osv('Validation Error !', 'Please input note for evaluation details')
                    else:
                        round_evaluation = self.pool.get('vhr.interview.round.evaluation').browse(cr, uid, item[1], context=context).note
                        if not round_evaluation:
                            raise osv.except_osv('Validation Error !', 'Please input note for evaluation details')
            else:
                for job_item in eval_obj:
                    if not job_item.note:
                        raise osv.except_osv('Validation Error !', 'Please input note for evaluation details')

        return True

    def execute_create(self, cr, uid, data, context=None):
        kw = None
        result = False
        try:
            log.debug("Execute create")
            result = audittrail.execute_cr(cr, uid, self._name, 'create', data, kw)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', '%s' % (e))
        return result
    
    def create(self, cr, uid, vals, context={}):
        res_id = super(vhr_job_applicant, self).create(cr, uid, vals, context)
        if vals.get('applicant_id'):
            app = self.pool.get('hr.applicant').browse(cr, uid, vals.get('applicant_id'), context=context)
            if app.is_erp_mail and app.recommender_id and app.source_id and app.source_id.code == 'ERP':
                self.recruitment_send_email(cr, uid, RE_ERP_UpdateInfo, self._name, res_id, context=context)
        return res_id
    
    def write(self, cr, uid, ids, vals, context=None):
        if context is None: context = {}
        if vals is None: vals = {}
        if not isinstance(ids, list):ids = [ids]
        dimension_obj = self.pool.get('vhr.dimension')
        round_eval_obj = self.pool.get('vhr.interview.round.evaluation')
        eval_obj = self.pool.get('vhr.evaluation')
        contract_type_obj = self.pool.get('hr.contract.type')

        if 'expected_salary' in vals or 'current_salary' in vals:
            if vals.has_key('expected_salary')  and vals['expected_salary'] == 0 and type( vals['expected_salary'])==int:
                vals['expected_salary'] = 0.001
            if vals.has_key('current_salary') and vals['current_salary'] == 0 and type( vals['current_salary'])==int:
                vals['current_salary'] = 0.001
                
        if vals.get('join_date') or vals.get('offer_job_level_position_id') or vals.get('offer_job_family_id') or\
            vals.get('offer_job_group_id') or vals.get('contract_type_id'): 
            vals['is_send_email_erp_bonus_schedue'] = True
            
        for job_app in self.browse(cr, uid, ids, context=context):
            if 'ex_employee' in vals and not job_app.hr_process:
                vals['is_new_emp'] = not vals['ex_employee']
            # update for interview1
            if 'state' in vals and vals['state'] == INTERVIEW:  # nếu chưa có inteview thì mới tạo ( trường hợp reopen)
                if not job_app.evaluation_details1 and not job_app.evaluation_details2 and not job_app.evaluation_details3:
                    vals_up = {}
                    if job_app.report_to.id:
                        dept_inter = [job_app.report_to.id]
                        vals_up['dept_interviewer1'] = [(6, 0, dept_inter)]
                    if job_app.handle_by.id:
                        vals_up['rr_interviewer1'] = [(6, 0, [job_app.handle_by.id])]
                    vals_up['current_row'] = ROUND_INTER[0][0]
                    super(vhr_job_applicant, self).write(cr, uid, [job_app.id], vals_up, context)
                    # create evaluation
                    eval_lst = eval_obj.search(cr, uid, [('active', '=', True)], context=context)
                    for eval_id in eval_lst:
                        vals_round_eval = {'job_applicant_id': job_app.id, 'evaluation_id': eval_id}
                        round_eval_obj.create(cr, uid, vals_round_eval)
            # 14/01 for send email change offer
            if job_app.hr_process and (vals.get('offer_job_title_id') or vals.get('offer_job_level_id') or vals.get('join_date')
                                       or vals.get('offer_report_to') or vals.get('offer_department')):
                content = u""
                if vals.get('offer_job_title_id'):
                    job_title = self.pool['vhr.job.title'].browse(cr, uid, vals['offer_job_title_id'], context=context).name
                    content = content + u'Title: <strong style="color:red">%s.</strong><br>' % (job_title)
                else:
                    content = content + u'Title: <strong>%s.</strong><br>' % (job_app.offer_job_title_id.name)

#                 if vals.get('offer_job_level_id'):
#                     job_level = self.pool['vhr.job.level'].browse(cr, uid, vals['offer_job_level_id'], context=context).name
#                     content = content + u'Level: <strong style="color:red">%s.</strong><br>' % (job_level)
#                 else:
#                     content = content + u'Level: <strong>%s.</strong><br>' % (job_app.offer_job_level_id.name)

                if vals.get('join_date'):
                    join_date = self.format_date(cr, uid, job_app.id, vals.get('join_date'), type='US', context=None)
                    content = content + u'Start day: <strong style="color:red">%s.</strong><br>' % (join_date)
                else:
                    join_date = self.format_date(cr, uid, job_app.id, job_app.join_date, type='US', context=None)
                    content = content + u'Start day: <strong>%s.</strong><br>' % (join_date)

                if vals.get('offer_report_to'):
                    report_to = self.pool['hr.employee'].browse(cr, uid, vals['offer_report_to'], context=context).name
                    content = content + u'Report to: <strong style="color:red">%s.</strong><br>' % (report_to)
                else:
                    content = content + u'Report to: <strong>%s.</strong><br>' % (job_app.offer_report_to.name)
                if vals.get('offer_department'):
                    offer_department = self.pool['hr.department'].browse(cr, uid, vals['offer_department'], context=context)
                    content = content + u'Dept/Div: <strong style="color:red">%s/%s</strong><br>' % (offer_department.name_en,
                                                                                                    offer_department.parent_id.name_en)
                else:
                    content = content + u'Dept/Div: <strong>%s/%s.</strong><br>' % (job_app.offer_department.name_en,
                                                                           job_app.offer_department.parent_id.name_en)
                content = content + '<br>'
                vals['change_offer_email'] = content

            # update other interview
            #26/12/2015 phai co expected salary va current salary thi moi di tiep duoc
            check_expected_salary = False
            check_current_salary = False
            #kiem tra 2 dieu kien - co key expected salary va kieu int hoac float 
            #                     - khong co current salary khi luu va chua tung luu truoc do
            current_emp = self.pool['hr.employee'].search(cr, uid, [('user_id.id', '=', uid)], context=context)
            if vals.get('decision_id1', False) or vals.get('decision_id2', False) or vals.get('decision_id3', False):
                self.check_interview_data(cr, uid, vals, job_app)
                vals['finish_interviewer'] = current_emp[0] if current_emp else False
            if (vals.has_key('expected_salary') and (type(vals['expected_salary']) in [int, float]))\
                or (not vals.has_key('expected_salary') and job_app.expected_salary):
                check_expected_salary = True
            if (vals.has_key('current_salary') and (type(vals['current_salary']) in [int, float]))\
                or (not vals.has_key('current_salary') and job_app.current_salary):
                check_current_salary = True
            if check_expected_salary and check_current_salary:
                code = ''   
                if job_app.state == INTERVIEW:             
                    current_row = job_app.current_row
                    if current_row and current_row == ROUND_INTER[0][0] and vals.get('decision_id1', job_app.decision_id1.id):                    
                        decision_id1 = vals.get('decision_id1', job_app.decision_id1.id)
                        decision_rec = dimension_obj.browse(cr, uid, decision_id1, context=context)
                        code = decision_rec and decision_rec.code or ''
                        if code == 'NEXT':
                            vals['current_row'] = ROUND_INTER[1][0]
                            dept_interview = []
                            if job_app.department_dept: dept_interview.append(job_app.department_dept.id)
                            for hrbp in job_app.department_hrbps:dept_interview.append(hrbp.id)
                            vals['dept_interviewer2'] = [(6, 0, list(set(dept_interview)))]
                            vals['rr_interviewer2'] = not job_app.rr_interviewer2 and vals.get('rr_interviewer1', False)\
                                                    or [(4, job.id) for job in job_app.rr_interviewer1]
                    if current_row and current_row == ROUND_INTER[1][0] and vals.get('decision_id2', job_app.decision_id2.id):
                        
                        decision_id2 = vals.get('decision_id2', job_app.decision_id2.id)
                        decision_rec = dimension_obj.browse(cr, uid, decision_id2, context=context)
                        code = decision_rec and decision_rec.code or ''
                        if code == 'NEXT':
                            vals['current_row'] = ROUND_INTER[2][0]
                            vals['dept_interviewer3'] = not job_app.dept_interviewer3 and vals.get('dept_interviewer2', False) \
                                                            or [(4, job.id) for job in job_app.dept_interviewer2]
                            vals['rr_interviewer3'] = not job_app.rr_interviewer3 and vals.get('rr_interviewer2', False) \
                                                            or [(4, job.id) for job in job_app.rr_interviewer2]
                    if current_row and current_row == ROUND_INTER[2][0] and vals.get('decision_id3', job_app.decision_id3.id):                    
                        decision_rec = dimension_obj.browse(cr, uid, vals.get('decision_id3'), context=context)
                        code = decision_rec and decision_rec.code or ''
        
                    vals['is_pass'] = (code == 'PASS') and True or False
                    if vals['is_pass']:
                        self.execute_workflow(cr, uid, job_app.id, {'ACTION': SIGNAL_INTERVIEW_OFFER})
                        id_type_2_month = contract_type_obj.search(cr, uid, ['|', ('code', '=', ' 2.0'), ('code', '=', '2')], context=context)
                        vals['offer_department'] = job_app.department_id.id
                        vals['offer_report_to'] = job_app.report_to.id
                        vals['offer_mentor'] = job_app.report_to.id
                        vals['offer_job_type'] = job_app.job_type_id.id
                        vals['offer_office_id'] = job_app.office_id.id
                        vals['offer_job_title_id'] = job_app.job_title_id.id
                        vals['offer_job_level_id'] = job_app.job_level_id and job_app.job_level_id.id or False
                        vals['offer_sub_group_id'] = job_app.sub_group_id.id
                        vals['offer_job_group_id'] = job_app.job_group_id.id
                        vals['offer_job_family_id'] = job_app.job_family_id.id
                        
                        vals['offer_career_track_id'] = job_app.career_track_id and job_app.career_track_id.id or False
                        
                        vals['offer_company_id'] = job_app.company_id.id
                        vals['offer_com_group_id'] = job_app.company_id.com_group_id.id
                        vals['join_date'] = job_app.received_working_date
                        vals['offer_date'] = date.today()
                        
                        #new job level
                        vals['offer_job_level_position_id'] = job_app.job_level_position_id.id
                        
                        if id_type_2_month:
                            vals['contract_type_id'] = id_type_2_month[0]
                    elif code in ['FAIL', 'PASS_NONE_OFFER']:
                        self.execute_workflow(cr, uid, job_app.id, {'ACTION':SIGNAL_INTERVIEW_CLOSE})
        if 'action_comment' in vals:
            del vals['action_comment']
        result = super(vhr_job_applicant, self).write(cr, uid, ids, vals, context=context)
        # send email when close candidate
        # clicker co the thuc hien nen browse can context
        state_current = job_app.state
        if vals.get('state') and vals.get('state')==CLOSE:
            '''
                05/08/2015 - binhnx
                Close job (request) when job (request) has:
                    - Remain = 0
                    - There is no Match CV in state confirm, interview, offer transfer to HR
            '''
            hr_job_obj = self.pool.get('hr.job')
            job_applicants = self.browse(cr, uid, ids, context=context)
            for job_applicant in job_applicants:
                job_item = job_applicant.job_id or False
                # Only check when remain = 0
                if job_item and job_item.no_of_remain_recruitment == 0:
                    # Unlink all of matching CVs
                    applicant_matching_ids = self.search(
                        cr, uid, [['job_id', '=', job_item.id],
                                  ['state', '=', 'draft']])
                    if applicant_matching_ids:
                        self.unlink(cr, uid, applicant_matching_ids)
                    # Search confirm, interview, offer state
                    applicant_pass_ids = self.search(
                        cr, uid, [['job_id', '=', job_item.id],
                                  '|', ['state', 'in', ['confirm', 'interview']],
                                  '&', ['state', '=', 'offer'], ['hr_process', '=', False]])
                    if not applicant_pass_ids:
                        hr_job_obj.vhr_job_execute_workflow(cr, uid, job_item.id, 'done')
                            
            for item in self.browse(cr, uid, ids, context={'CAND_INTERVIEW':True}):
                template_email = RE_ERP_Fail
                if state_current == 'offer':
                    template_email = RE_ERP_PASS_CANCEL_NEW 
                app = item.applicant_id
                if app.is_erp_mail and app.recommender_id and app.source_id and app.source_id.code in ('ERP','SR-100'):
                    self.recruitment_send_email(cr, uid, template_email, self._name, item.id, context=context)
        if vals.get('decision_id1', False) or vals.get('decision_id2', False) or vals.get('decision_id3', False):
            for item in ids:
                self.recruitment_send_email(cr, uid, RE_FinishInterviewReport, self._name, item, context=context)
        
        # done job when transfer
        if vals.get('hr_process') and vals.get('hr_process')==True:
            hr_job_obj = self.pool.get('hr.job')
            job_item = self.browse(cr, uid, ids[0]).job_id
            if job_item.no_of_recruitment == job_item.no_of_hired_recruitment:
                job_app_end_step_count = self.search(cr, uid, [('job_id', '=', job_item.id),'|',
                                                               ('state', 'in', ['close', 'done']),
                                                               '&',('state', '=', 'offer'),('hr_process','=',True)],
                                                     count=True, context=context)
                if len(job_item.job_applicant_ids)==job_app_end_step_count:
                    hr_job_obj.execute_workflow(cr, uid, job_item.id, {'ACTION': 'in_progress_done'})

#         10/11/2014 : user tạm thời không sài
#         if vals.get('start_time_round1', False) or vals.get('start_time_round2', False) or vals.get('start_time_round3', False):
#             start_time = vals.get('start_time_round1', False) or vals.get('start_time_round2', False) or vals.get('start_time_round3', False)
#             start_time = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
# 
#             timezone = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr.default.timezone.config')
#             timezone = int(timezone) if timezone else 0
#             time_sendemail = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr.rr.hour.send.email.config')
#             time_sendemail = int(time_sendemail) if time_sendemail else 0
# 
#             if datetime.today() + timedelta(hours=time_sendemail) <= start_time + timedelta(hours=timezone):
#                 template = 'VHR_RR_INVITE_JOIN_INTERVIEW'
#                 email_ids = email_template.search(cr, uid, [('model', '=', self._name), ('name', '=', template)])
#                 if email_ids:
#                     self.vhr_send_mail(cr, uid, email_ids[0], ids[0], context=context)
        return result

    def execute_write(self, cr, uid, ids, data, context=None):
        result = False
        try:
            log.debug("Execute write")
            result = audittrail.execute_cr(cr, uid, self._name, 'write', ids, data, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', '%s' % (e))
        return result

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context = {}
        args = self.get_args(cr, uid, args, context)
        return super(vhr_job_applicant, self).search(cr, uid, args, offset, limit, order, context, count)

    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False, lazy=True):
        if context is None:
            context = {}
        domain = self.get_args(cr, uid, domain, context)
        return super(vhr_job_applicant, self).read_group(cr, uid, domain, fields, groupby, offset, limit, context, orderby, lazy)

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]
        context['CAND_INTERVIEW'] =  True # pass check security
        res = False
        try:
            lst_candidate = []
            for item in self.browse(cr, uid, ids, context):
                if item.applicant_id:
                    lst_candidate.append(item.applicant_id.id)
            res = super(vhr_job_applicant, self).unlink(cr, uid, ids, context)
            if res:
                applicant_obj = self.pool['hr.applicant'] 
                if lst_candidate:               
                    applicant_obj.write_change_state(cr, uid, lst_candidate, STATE_APP[0][0], u'Xóa inteview cho candidate', context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res

    def read(self, cr, user, ids, fields=None, context=None, load='_classic_read'):
        if context is None:
            context = {}
        # validate read
        result_check = self.check_read_access(cr, user, ids, context)
        if not result_check:
            raise osv.except_osv('Validation Error !', 'You don’t have permission to access this data !')
        # end validate read
        return super(vhr_job_applicant, self).read(cr, user, ids, fields, context, load)
        
    def validate_read(self, cr, uid, ids, context=None):
        """
            Các view liên quan :
                - hr.job - vhr_job_applicant - hr.applicant
            Các role được view
                - HRBP, CANDB, ADMIN, MANAGER, RECRUITER (Done)
                - RAMS, DEPTHEAD (Done)
                - Reporter1,2,3 ( Done )
                - emp_receive_cvs (Done)
                - thằng được delegate
                - thằng tạo request (Done)
                - thằng approve request tại bước send CV (Done)
            - view của candidate có context là FROM_VIEW APPLICANTS ( bất kì role nào )    
            Các role được view:
                - tại sao HRBP, CANDB, ADMIN, MANAGER, RECRUITER được view ?
                -> đứng tại view candidate đi qua ko xem được chắc chớt
                -> nếu thay đổi nhớ add thêm điều kiện cho temp_args
        """
        if uid == 1:
            return True
        log.info('validate_read : %s'%(uid))
        if context is None: context = {}
        if context.get('FROM_VIEW') and context.get('FROM_VIEW') == 'APPLICANT':
            return True
        roles = self.recruitment_get_group_array(cr, uid, uid, context)
        if ADMIN in roles or MANAGER in roles or CANDB_ROLE in roles or\
            RECRUITER in roles or HRBP in roles or COLLABORATER in roles or COLLABORATER2 in roles or RRHRBP in roles:
            return True
        if not isinstance(ids, list): ids = [ids]
        current_emp = self.pool.get('hr.employee').search(cr, uid, [('user_id.id', '=', uid)], context={'active_test': False})
        if current_emp:
            temp_args = ['&']
            temp_args.append(('id', 'in', ids))
            temp_args.extend(['|', '|', '|', '|', '|', '|', '|', '|'])
            temp_args.append(('requestor_id', '=', current_emp[0]))
            temp_args.append(('reporter1', '=', current_emp[0]))
            temp_args.append(('reporter2', '=', current_emp[0]))
            temp_args.append(('reporter3', '=', current_emp[0]))
            temp_args.append(('emp_receive_cvs', '=', current_emp[0]))  # thằng approve request tại bước send CV
            temp_args.append(('department_id.manager_id.id', '=', current_emp[0]))  # depthead xem
            temp_args.append(('offer_department.manager_id.id', '=', current_emp[0]))  # depthead offer department xem
            temp_args.append(('department_id.rams', '=', current_emp[0]))  # ram
            job_deledate_ids = self.get_delegate_department(cr, uid, current_emp[0], context)  # delegate user
            temp_args.append(('job_id', 'in', job_deledate_ids))
            lst_job = super(vhr_job_applicant, self).search(cr, uid, temp_args, count=True, context=context)
            if len(ids) == lst_job:
                return True
        return False

    def get_url(self, cr, uid, res_id, context=None):
        if isinstance(res_id, list):
            res_id = res_id[0]
        model_data = self.pool.get('ir.model.data')
        parameter_obj = self.pool.get('ir.config_parameter')
        base_url = parameter_obj.get_param(cr, uid, 'web.base.url')
        action_id = model_data.xmlid_lookup(cr, uid, 'vhr_recruitment.action_vhr_job_applicant')[2]
        url = '%s/web#id=%s&view_type=form&model=vhr.job.applicant&action=%s' % (base_url, res_id, action_id)
        return url

    def get_args(self, cr, uid, args, context=None):
        if context is None:
            context = {}
        hr_obj = self.pool.get('hr.employee')
        current_emp = hr_obj.search(cr, uid, [('user_id.id', '=', uid)], context={'active_test': False})
        roles = self.recruitment_get_group_array(cr, uid, uid)
        temp_args = args
        if 'CAND_INTERVIEW' in context and current_emp:
            if ADMIN not in roles:
                temp_args.append('|')
                temp_args.append('|')
                temp_args.append('|')
                temp_args.append('&')
                temp_args.append('&')
                temp_args.append(('reporter1', '=', current_emp[0]))
                temp_args.append(('current_row', '=', ROUND_INTER[0][0]))
                temp_args.append(('state', '=', 'interview'))
                temp_args.append('&')
                temp_args.append('&')
                temp_args.append(('reporter2', '=', current_emp[0]))
                temp_args.append(('current_row', '=', ROUND_INTER[1][0]))
                temp_args.append(('state', '=', 'interview'))
                temp_args.append('&')
                temp_args.append('&')
                temp_args.append(('reporter3', '=', current_emp[0]))
                temp_args.append(('current_row', '=', ROUND_INTER[2][0]))
                temp_args.append(('state', '=', 'interview'))
                lst_job_app = self.get_list_job_app_approve(cr, uid, current_emp[0])
                temp_args.append(('id', 'in', lst_job_app))
        return temp_args

    def get_list_job_app_approve(self, cr, uid, current_emp):
        sql = '''select a.id from vhr_job_applicant a
                 INNER JOIN job_applicant_employee_rel b on (a.id = b.job_applicant_id)
                 WHERE a.state = 'confirm' and b.employee_id = %s''' % (current_emp)
        cr.execute(sql)
        temp = cr.fetchall()
        lstid = [x[0] for x in temp]
        return lstid

    def view_factory(self, cr, uid, doc, dicti, roles=None, context=None):  # Reflect me => me = get from xml + domain
        if context is None:
            context = {}
        if not((ADMIN in roles) or (MANAGER in roles)):
            hr_employee = self.pool.get('hr.employee')
            employee = hr_employee.search(cr, uid, [('user_id', '=', uid)], context={'active_test': False})
            emp = employee and employee[0] or 0
            
            domain = ['&', ('handle_by', '!=', emp), ('share_handle_bys', 'not child_of', emp)]
            for node in doc.xpath("//button[@code_execute='PRINT_REPORT']"):
                node.set('modifiers', json.dumps({'invisible': domain}))
            
            # Default chỉ có bên C&B RRADMIN và RRManager có quyền xem ( xem trong view )
            # HRBP và AssHRBP xem được những phòng ban mình phụ trách
            # RR xem được phòng ban mình handle và share handle
            attrs = ['|', '|', ('state', 'in', ['draft', 'confirm', 'interview']), ('is_pass', '!=', True)]
            if (HRBP in roles and CANDB_ROLE not in roles) or RECRUITER in roles:
                if HRBP in roles:
                    lst_dept1 = self.get_department_hrbps(cr, uid, emp, context)
                    lst_dept2 = self.get_department_ass_hrbps(cr, uid, emp)
                    lst_dept1.extend(lst_dept2)
                    attrs = ['|'] + attrs + [('department_id','not in', lst_dept1), ('offer_department','not in', lst_dept1)]
                if RECRUITER in roles: 
                    ['|'].extend(attrs)
                    attrs = attrs + domain
                for node in doc.xpath("//page[@name='Offer']"):
                    node.set('modifiers', json.dumps({'invisible': attrs}))
            
            attrs = ['|', ('state', '!=', 'draft')] + domain
            for node in doc.xpath("//button[@states='draft']"):
                node.set('modifiers', json.dumps({'invisible': attrs}))
            attrs = ['|', ('state', '!=', 'interview')] + domain
            for node in doc.xpath("//button[@states='interview']"):
                node.set('modifiers', json.dumps({'invisible': attrs}))
            attrs = ['|', ('state', '!=', 'offer')] + domain
            for node in doc.xpath("//button[@states='offer']"):
                node.set('modifiers', json.dumps({'invisible': attrs}))
            attrs = ['|', '|', '|', ('state', '!=', 'offer'), '&', ('none_official', '=', True),
                     ('no_depthead_approval', '=', False), ('hr_process', '=', True)] + domain
            for node in doc.xpath("//button[@code_execute='TRANSFER_CANDB']"):
                node.set('modifiers', json.dumps({'invisible': attrs}))
            
            attrs = ['|', '|',('state','!=','offer'),('is_offer_edit', '=', True)] + domain
            for node in doc.xpath("//button[@code_execute='CANCEL_OFFER']"):
                node.set('modifiers', json.dumps({'invisible': attrs}))
            
            attrs = ['|', '|', '|', ('state', '!=', 'offer'), '&', ('none_official', '=', True),
                     ('no_depthead_approval', '=', False), ('hr_process', '=', False)] + domain
            for node in doc.xpath("//button[@code_execute='UPDATE_CANDB']"):
                node.set('modifiers', json.dumps({'invisible': attrs}))
            attrs = ['|', '|', '|', ('job_state', '!=', 'in_progress'), ('is_offer_edit', '=', True), ('state', '!=', 'close')] + domain
            for node in doc.xpath("//button[@code_execute='RE_OPEN']"):
                node.set('modifiers', json.dumps({'invisible': attrs}))
            if (CANDB_ROLE in roles):
                attrs = ['|',('state', '!=', 'offer'),('is_contract_definite', '=', True)]
                for node in doc.xpath("//button[@name='action_print_offer_report']"):
                    node.set('modifiers', json.dumps({'invisible': attrs}))
                attrs = ['|',('state', '!=', 'offer'),('is_contract_definite', '=', False)]
                for node in doc.xpath("//button[@name='action_print_offer_contract_definite_report']"):
                    node.set('modifiers', json.dumps({'invisible': attrs}))  

    def get_last_finish_round(self, cr, uid, res_id, context=None):
        if isinstance(res_id, list):
            res_id = res_id[0]
        currrent_interview = self.browse(cr, uid, res_id, context=context)
        current_row = currrent_interview.current_row
        if current_row:
            if (current_row == ROUND_INTER[0][0] and currrent_interview.decision_id1) or \
               (current_row == ROUND_INTER[1][0] and not currrent_interview.decision_id2):
                return ROUND_INTER[0][0]
            elif (current_row == ROUND_INTER[2][0] and not currrent_interview.decision_id3) or\
                 (current_row == ROUND_INTER[1][0] and currrent_interview.decision_id2):
                return ROUND_INTER[1][0]
            elif currrent_interview.decision_id3:
                return ROUND_INTER[2][0]
        return ''

    def get_email_recruiter(self, cr, uid, res_id, context=None):
        log.debug('VHR RR: Start get_email_recruiter')
        if isinstance(res_id, list):
            res_id = res_id[0]
        currrent_interview = self.browse(cr, uid, res_id, context=context)
        current_row = currrent_interview.current_row
        result = ''
        if current_row:
            rr_interviewer = None
            if (current_row == ROUND_INTER[0][0] and currrent_interview.decision_id1) or \
               (current_row == ROUND_INTER[1][0] and not currrent_interview.decision_id2):
                rr_interviewer = currrent_interview.rr_interviewer1
            elif (current_row == ROUND_INTER[2][0] and not currrent_interview.decision_id3) or\
                 (current_row == ROUND_INTER[1][0] and currrent_interview.decision_id2):
                rr_interviewer = currrent_interview.rr_interviewer2
            elif currrent_interview.decision_id3:
                rr_interviewer = currrent_interview.rr_interviewer3
            if rr_interviewer:
                for item in rr_interviewer:
                    if item.work_email:
                        result += item.work_email + ';'
        log.debug('VHR RR: End get_email_recruiter: %s' % (result))
        return result

    def get_name_recruiter(self, cr, uid, res_id, context=None):
        log.debug('VHR RR: Start get_name_recruiter')
        if isinstance(res_id, list):
            res_id = res_id[0]
        currrent_interview = self.browse(cr, uid, res_id, context=context)
        current_row = currrent_interview.current_row
        result = ''
        if current_row:
            rr_interviewer = None
            if (current_row == ROUND_INTER[0][0] and currrent_interview.decision_id1) or \
               (current_row == ROUND_INTER[1][0] and not currrent_interview.decision_id2):
                rr_interviewer = currrent_interview.rr_interviewer1
            elif (current_row == ROUND_INTER[2][0] and not currrent_interview.decision_id3) or\
                 (current_row == ROUND_INTER[1][0] and currrent_interview.decision_id2):
                rr_interviewer = currrent_interview.rr_interviewer2
            elif currrent_interview.decision_id3:
                rr_interviewer = currrent_interview.rr_interviewer3
            if rr_interviewer:
                for item in rr_interviewer:
                    if item.name:
                        result += item.name + ','
        log.debug('VHR RR: End get_name_recruiter: %s' % (result))
        return result

    def get_name_reporter(self, cr, uid, res_id, context=None):
        log.debug('VHR RR: Start get_name_reporter')
        if isinstance(res_id, list):
            res_id = res_id[0]
        currrent_interview = self.browse(cr, uid, res_id, context=context)
        current_row = currrent_interview.current_row
        result = ''
        if current_row:
            if (current_row == ROUND_INTER[0][0] and currrent_interview.decision_id1) or \
               (current_row == ROUND_INTER[1][0] and not currrent_interview.decision_id2):
                if currrent_interview.reporter1.name:
                    result = currrent_interview.reporter1.name
            elif (current_row == ROUND_INTER[2][0] and not currrent_interview.decision_id3) or\
                 (current_row == ROUND_INTER[1][0] and currrent_interview.decision_id2):
                if currrent_interview.reporter2.name:
                    result = currrent_interview.reporter2.name
            elif currrent_interview.decision_id3:
                if currrent_interview.reporter3.name:
                    result = currrent_interview.reporter3.name
        log.debug('VHR RR: End get_name_reporter: %s' % (result))
        return result

    def get_email_reporter(self, cr, uid, res_id, context=None):
        log.debug('VHR RR: Start get_email_reporter')
        if isinstance(res_id, list):
            res_id = res_id[0]
        currrent_interview = self.browse(cr, uid, res_id, context=context)
        current_row = currrent_interview.current_row
        result = ''
        if current_row:
            if (current_row == ROUND_INTER[0][0] and currrent_interview.decision_id1) or \
               (current_row == ROUND_INTER[1][0] and not currrent_interview.decision_id2):
                if currrent_interview.reporter1.work_email:
                    result = currrent_interview.reporter1.work_email
            elif (current_row == ROUND_INTER[2][0] and not currrent_interview.decision_id3) or\
                 (current_row == ROUND_INTER[1][0] and currrent_interview.decision_id2):
                if currrent_interview.reporter2.work_email:
                    result = currrent_interview.reporter2.work_email
            elif currrent_interview.decision_id3:
                if currrent_interview.reporter3.work_email:
                    result = currrent_interview.reporter3.work_email
        log.debug('VHR RR: End get_email_reporter: %s' % (result))
        return result

    def get_email_interviewer(self, cr, uid, res_id, context=None):
        log.debug('VHR RR: Start get email interviewer')
        if isinstance(res_id, list):
            res_id = res_id[0]
        currrent_interview = self.browse(cr, uid, res_id, context=context)
        current_row = currrent_interview.current_row
        result = ''
        if current_row:
            interviewer = None
            if (current_row == ROUND_INTER[0][0] and currrent_interview.decision_id1) or \
               (current_row == ROUND_INTER[1][0] and not currrent_interview.decision_id2):
                interviewer = currrent_interview.dept_interviewer1
            elif (current_row == ROUND_INTER[2][0] and not currrent_interview.decision_id3) or\
                 (current_row == ROUND_INTER[1][0] and currrent_interview.decision_id2):
                interviewer = currrent_interview.dept_interviewer2
            elif currrent_interview.decision_id3:
                interviewer = currrent_interview.dept_interviewer3
            if interviewer:
                for item in interviewer:
                    if item.work_email:
                        result += item.work_email + ';'
        log.debug('VHR RR: End get email interviewer: %s' % (result))
        return result

    def get_current_name_reporter(self, cr, uid, res_id, context=None):
        log.debug('VHR RR: Start get_current_name_reporter')
        if isinstance(res_id, list):
            res_id = res_id[0]
        currrent_interview = self.browse(cr, uid, res_id, context=context)
        current_row = currrent_interview.current_row
        result = ''
        if current_row:
            if current_row == ROUND_INTER[0][0]:
                if currrent_interview.reporter1.work_email:
                    result = currrent_interview.reporter1.name
            elif current_row == ROUND_INTER[1][0]:
                if currrent_interview.reporter2.name:
                    result = currrent_interview.reporter2.name
            elif current_row == ROUND_INTER[2][0]:
                if currrent_interview.reporter3.name:
                    result = currrent_interview.reporter3.name
        log.debug('VHR RR: End get_current_name_reporter: %s' % (result))
        return result

    def get_current_email_reporter(self, cr, uid, res_id, context=None):
        log.debug('VHR RR: Start get_current_email_reporter')
        if isinstance(res_id, list):
            res_id = res_id[0]
        currrent_interview = self.browse(cr, uid, res_id, context=context)
        current_row = currrent_interview.current_row
        result = ''
        if current_row:
            if current_row == ROUND_INTER[0][0]:
                if currrent_interview.reporter1.work_email:
                    result = currrent_interview.reporter1.work_email
            elif current_row == ROUND_INTER[1][0]:
                if currrent_interview.reporter2.work_email:
                    result = currrent_interview.reporter2.work_email
            elif current_row == ROUND_INTER[2][0]:
                if currrent_interview.reporter3.work_email:
                    result = currrent_interview.reporter3.work_email
        log.debug('VHR RR: End get_current_email_reporter: %s' % (result))
        return result

    def get_current_email_interviewer(self, cr, uid, res_id, context=None):
        log.debug('VHR RR: Start get current email interviewer')
        if isinstance(res_id, list):
            res_id = res_id[0]
        res_candidate = self.browse(cr, uid, res_id, context=context)
        current_row = res_candidate.current_row
        result = ''
        if current_row:
            interviewers = None
            if current_row == ROUND_INTER[0][0]:
                interviewers = res_candidate.dept_interviewer1
            elif current_row == ROUND_INTER[1][0]:
                interviewers = res_candidate.dept_interviewer2
            elif current_row == ROUND_INTER[2][0]:
                interviewers = res_candidate.dept_interviewer3
            if interviewers:
                for emp in interviewers:
                    if emp.work_email:
                        result += emp.work_email + ';'
        log.debug('VHR RR: End get current email interviewer: %s' % (result))
        return result

    def get_current_interview_start_date(self, cr, uid, res_id, context=None):
        if isinstance(res_id, list):
            res_id = res_id[0]
        currrent_interview = self.browse(cr, uid, res_id, context=context)
        current_row = currrent_interview.current_row
        result = ''
        if current_row:
            if current_row == ROUND_INTER[0][0]:
                if currrent_interview.start_time_round1:
                    result = currrent_interview.start_time_round1
            elif current_row == ROUND_INTER[1][0]:
                if currrent_interview.start_time_round2:
                    result = currrent_interview.start_time_round2
            elif current_row == ROUND_INTER[2][0]:
                if currrent_interview.start_time_round3:
                    result = currrent_interview.start_time_round3
        return result

    def get_current_interview_room(self, cr, uid, res_id, context=None):
        if isinstance(res_id, list):
            res_id = res_id[0]
        currrent_interview = self.browse(cr, uid, res_id, context=context)
        current_row = currrent_interview.current_row
        result = ''
        if current_row:
            if current_row == ROUND_INTER[0][0]:
                if currrent_interview.room_id1:
                    result = currrent_interview.room_id1.name
            elif current_row == ROUND_INTER[1][0]:
                if currrent_interview.room_id2:
                    result = currrent_interview.room_id2.name
            elif current_row == ROUND_INTER[2][0]:
                if currrent_interview.room_id3:
                    result = currrent_interview.room_id3.name
        return result

    def get_current_name_recruiter(self, cr, uid, res_id, context=None):
        log.debug('VHR RR: Start get current name recruiter')
        if isinstance(res_id, list):
            res_id = res_id[0]
        res_candidate = self.browse(cr, uid, res_id, context=context)
        current_row = res_candidate.current_row
        result = ''
        if current_row:
            rr_interviewers = None
            if current_row == ROUND_INTER[0][0]:
                rr_interviewers = res_candidate.rr_interviewer1
            elif current_row == ROUND_INTER[1][0]:
                rr_interviewers = res_candidate.rr_interviewer2
            elif current_row == ROUND_INTER[2][0]:
                rr_interviewers = res_candidate.rr_interviewer3
            if rr_interviewers:
                for emp in rr_interviewers:
                    if emp.name:
                        result += emp.name + ';'
        log.debug('VHR RR: End get current name recruiter: %s' % (result))
        return result

    def get_current_name_interviewer(self, cr, uid, res_id, context=None):
        log.debug('VHR RR: Start get current name interviewer')
        if isinstance(res_id, list):
            res_id = res_id[0]
        res_candidate = self.browse(cr, uid, res_id, context=context)
        current_row = res_candidate.current_row
        result = ''
        if current_row:
            dept_interviewers = None
            if current_row == ROUND_INTER[0][0]:
                dept_interviewers = res_candidate.dept_interviewer1
            elif current_row == ROUND_INTER[1][0]:
                dept_interviewers = res_candidate.dept_interviewer2
            elif current_row == ROUND_INTER[2][0]:
                dept_interviewers = res_candidate.dept_interviewer3
            if dept_interviewers:
                for emp in dept_interviewers:
                    if emp.name:
                        result += emp.name + ';'
        log.debug('VHR RR: End get current name recruiter: %s' % (result))
        return result

    def get_hrbp_information(self, cr, uid, res_id, context=None):
        '''
            Get assistant HRBP
        '''
        if isinstance(res_id, list):
            res_id = res_id[0]
        result = ''
        job_applicant_obj = self.browse(cr, uid, res_id, context=context)
        city_code = job_applicant_obj.offer_office_id.city_id.code
        if city_code and city_code == '01':
            result = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr.rr.recruitment.hanoi.contact.config')
            if not result:
                result = u'Đinh Thị Điệp - C&B Executive - 0936317489'
        else:
            # Check config param for Division
            result = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr.rr.hrbp.information.for.division')
            if result:
                import ast
                result = ast.literal_eval(result)
                if type(result) == dict and job_applicant_obj.offer_division_id and job_applicant_obj.offer_division_id.code in result.keys():
                    return result[job_applicant_obj.offer_division_id.code]

            ass_hrbps = job_applicant_obj.offer_department.ass_hrbps
            if ass_hrbps:
                for hrbp in ass_hrbps:
                    if hrbp.name_related and hrbp.mobile_phone and hrbp.resource_id and hrbp.resource_id.active:
                        return '%s - Assistant to HRBP - %s' % (hrbp.name_related, hrbp.mobile_phone)
            hrbps = self.browse(cr, uid, res_id, context=context).offer_department.hrbps
            if hrbps:
                for hrbp in hrbps:
                    if hrbp.name_related and hrbp.mobile_phone and hrbp.resource_id and hrbp.resource_id.active:
                        return '%s - HRBP - %s' % (hrbp.name_related, hrbp.mobile_phone)
        return result

    def cron_send_mail_remind_finish_report(self, cr, uid, context=None):
        log.info('VHR RR: Start send email remind finish report')
        now = datetime.now()
        today = now.strftime('%Y-%m-%d') + ' 00:00:00'
        tomorrow = (now + timedelta(days=1)).strftime('%Y-%m-%d') + ' 00:00:00'
        ids = self.search(cr, uid, [
            '|', '|',
            '&', '&', ('decision_id1', '=', None), ('start_time_round1', '>', today), ('start_time_round1', '<', tomorrow),
            '&', '&', '&', ('decision_id2', '=', None), ('decision_id1', '!=', None), ('start_time_round2', '>', today), ('start_time_round2', '<', tomorrow),
            '&', '&', '&', ('decision_id3', '=', None), ('decision_id2', '!=', None), ('start_time_round2', '>', today), ('start_time_round3', '<', tomorrow)
        ], context=context)
        for item in self.browse(cr, uid, ids, context=context):
            if item.state == 'interview':
                self.recruitment_send_email(cr, uid, RE_Sending_Interview, self._name, item.id, context=context)
        log.info('VHR RR: End send email remind finish report')
        return True
    
    def cron_unmatch_job_applicant(self, cr, uid, hour_check, context=None):
        log.info('VHR RR: Start unmatch job applicant')
        now = datetime.now()
        now = now - timedelta(hours=hour_check)
        lst_unmatch = self.search(cr, uid, [('create_date','<=', str(now)), ('state','=','draft')])
        for item in lst_unmatch:
            try:
                self.unlink(cr, uid, item, context)
            except Exception as e:
                pass
        log.info('VHR RR: End unmatch job applicant')
        return True

    def workflow_for_vhr_job_applicant(self, cr, uid):
        log.info('VHR_JOB_APPLICANT: Begin Create workflow')
        sql = """select id, trim(state) as state, trim(state_note) as state_note
                from vhr_job_applicant
                where
                    (state <> 'close' and state <> state_note) or (state = 'draft' and state_note is NULL)
                order by id"""
        cr.execute(sql)
        res_trigger = cr.dictfetchall()
        for item in res_trigger:
            sql = """
                select sc.id
                from wkf_instance wkf join vhr_job_applicant sc on sc.id = wkf.res_id
                where  sc.id = %s and wkf.res_type = 'vhr.job.applicant' """ % (item['id'])
            cr.execute(sql)
            res = cr.dictfetchone()
            if not res:
                log.info('VHR_JOB_APPLICANT: %s' % (item))
                self.create_workflow(cr, uid, [item['id']])
            job_app_signal = [k for k, v in SIGNAL_JA_TRIGGER.iteritems() if v['old_state'] == item['state'] and v['new_state'] == item['state_note']]
            if job_app_signal:
                log.info('Signal : %s' % (job_app_signal))
                #self.signal_workflow(cr, uid, [item['id']], job_app_signal[0])
                try:
                    self.execute_workflow(cr, uid, [item['id']], {'ACTION': job_app_signal[0]})
                except Exception as e:
                    log.exception(e)
            else:
                log.info('Can\'t search signal')
        log.info('VHR_JOB_APPLICANT: End create workflow')
        return True

    def workflow_for_trigger(self, cr, uid, ids, signal):
        log.info('VHR_JOB_APPLICANT: workflow_for_trigger')
        if not isinstance(ids, list):
            ids = [ids]
        self.signal_workflow(cr, uid, ids, signal)
        log.info('VHR_JOB_APPLICANT:workflow_for_trigger')
        return True

    def action_send_email_invitation(self, cr, uid, ids, context=None):
        return self.recruitment_send_email(cr, uid, 'rr_interview_invitation_email', self._name, ids[0])
    
    def action_send_email_thankyou(self, cr, uid, ids, context=None):
        return self.recruitment_send_email(cr, uid, 'rr_interview_thankyou_letter_email', self._name, ids[0])

vhr_job_applicant()
