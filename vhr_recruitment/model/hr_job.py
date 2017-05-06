# -*-coding:utf-8-*-
import logging
from lxml import etree
from openerp.osv import osv, fields
from datetime import date, datetime
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
import time
import simplejson as json
import threading
from vhr_job_applicant import SIGNAL_JA
from vhr_applicant import STATE_APP
from vhr_recruitment_constant import EMAIL_DEPTHEAD_APPROVE
from vhr_recruitment_abstract import vhr_recruitment_abstract, HRBP,\
    RECRUITER, MANAGER, ADMIN, CANDB_ROLE, COLLABORATER, COLLABORATER2, RRHRBP

from openerp import SUPERUSER_ID
from openerp.tools.translate import _


max_connections = 60
semaphore = threading.BoundedSemaphore(max_connections)

log = logging.getLogger(__name__)

# define state workflow
DRAFT = 'draft'
WAITING_HRBP = 'waiting_hrbp'
WAITING_DEPT = 'waiting_dept'
WAITING_RRM = 'waiting_rrm'
IN_PROGRESS = 'in_progress'
DONE = 'done'
CLOSE = 'close'
CANCEL = 'cancel'

STATE_NAME = [
    (DRAFT, 'Draft'),
    (WAITING_HRBP, 'Waiting HRBP'),
    (WAITING_DEPT, 'Waiting DEPT'),
    (WAITING_RRM, 'Waiting RRM'),
    (IN_PROGRESS, 'In progress'),
    (DONE, 'Done'),
    (CLOSE, 'Close'),
    (CANCEL, 'Cancel')
]

SIGNAL = {
    'draft_waiting_hrbp':
        {'old_state': DRAFT, 'new_state': WAITING_HRBP},
    'waiting_hrbp_waiting_dept':
        {'old_state': WAITING_HRBP, 'new_state': WAITING_DEPT},
    'waiting_hrbp_waiting_rrm':
        {'old_state': WAITING_HRBP, 'new_state': WAITING_RRM},
    'waiting_hrbp_draft':
        {'old_state': WAITING_HRBP, 'new_state': DRAFT},
    'waiting_dept_waiting_rrm':
        {'old_state': WAITING_DEPT, 'new_state': WAITING_RRM},
    'waiting_dept_waiting_hrbp':
        {'old_state': WAITING_DEPT, 'new_state': WAITING_HRBP},
    'waiting_rrm_waiting_hrbp':
        {'old_state': WAITING_RRM, 'new_state': WAITING_HRBP},
    'waiting_rrm_in_progress':
        {'old_state': WAITING_RRM, 'new_state': IN_PROGRESS},
    'in_progress_done':
        {'old_state': IN_PROGRESS, 'new_state': DONE},
    'in_progress_close':
        {'old_state': IN_PROGRESS, 'new_state': CLOSE},
    'in_progress_cancel':
        {'old_state': IN_PROGRESS, 'new_state': CANCEL},
    'done_in_progress':
        {'old_state': DONE, 'new_state': IN_PROGRESS}
}

# signal for trigger workflow
# Xóa sau khi hết giai đoạn migrate data
SIGNAL_TRIGGER = {
    'draft_waiting_hrbp':
        {'old_state': DRAFT, 'new_state': WAITING_HRBP},
    'draft_waiting_rrm':
        {'old_state': DRAFT, 'new_state': WAITING_RRM},
    'waiting_hrbp_waiting_dept':
        {'old_state': WAITING_HRBP, 'new_state': WAITING_DEPT},
    'waiting_hrbp_waiting_rrm':
        {'old_state': WAITING_HRBP, 'new_state': WAITING_RRM},
    'waiting_dept_waiting_rrm':
        {'old_state': WAITING_DEPT, 'new_state': WAITING_RRM},
    'waiting_rrm_in_progress':
        {'old_state': WAITING_RRM, 'new_state': IN_PROGRESS},
    'in_progress_done':
        {'old_state': IN_PROGRESS, 'new_state': DONE},
    'in_progress_close':
        {'old_state': IN_PROGRESS, 'new_state': CLOSE},
    'in_progress_cancel':
        {'old_state': IN_PROGRESS, 'new_state': CANCEL},
}

class hr_job(osv.osv, vhr_recruitment_abstract):
    _name = 'hr.job'
    _inherit = 'hr.job'

    def _get_dept_head_approve(self, cr, uid, ids, fields, args, context=None):
        """ Kiểm tra có cần depthead approve request hay không
            #1 : Nếu request bình thường depthead đã approve thì không cần approve lại lên thẳng rrm
            #2 : Nếu request tuyển CTV/Intern/Fresher thì cũng không cần tới depthead approve
        """
        log.debug('start _get_dept_head_approve')
        result = {}
        state_change_obj = self.pool.get('vhr.state.change')
        for item in self.browse(cr, uid, ids, context=context):
            result[item.id] = False
#             is_cif_request = self.check_is_cif_request(cr, uid, item.job_title_id.code, item.job_level_id.code)
            is_cif_request = self.check_is_cif_request(cr, uid, item.job_title_id.code, False)
            if is_cif_request:
                result[item.id] = True
            else:
                result_search = state_change_obj.search(cr, uid, [('res_id', '=', item.id), ('model', '=', self._name),
                                                                  ('old_state', '=', WAITING_DEPT), ('new_state', '=', WAITING_RRM)],
                                                        count=True, context=context)
                if result_search:
                    result[item.id] = True
        log.debug('end _get_dept_head_approve')
        return result

    def _get_current_hired_recruitment(self, cr, uid, ids, fields, args, context=None):
        log.debug('start _get_current_hired_recruitment')
        result = {}
        job_app_obj = self.pool.get('vhr.job.applicant')
        for job_item in self.browse(cr, uid, ids, context=context):
            lst_job_applicant = job_app_obj.search(cr, uid, [('job_id', '=', job_item.id),
                                                             ('state', 'in', ['done', 'offer']),
                                                             ('hr_process', '=', True)], count=True, context=context)
            if job_item.no_of_recruitment == lst_job_applicant:
                show_finish_button = 'DONE'
            elif lst_job_applicant == 0:
                show_finish_button = 'CANCEL'
            else:
                show_finish_button = 'CLOSE'

            result[job_item.id] = {'no_of_hired_recruitment': lst_job_applicant,
                                   'show_finish_button': show_finish_button,
                                   'no_of_remain_recruitment': job_item.no_of_recruitment - lst_job_applicant
                                   }
        log.debug('end _get_current_hired_recruitment')
        return result

    def _get_full_code(self, cr, uid, ids, fields, args, context=None):
        result = {}
        for item in self.browse(cr, uid, ids, context=context):
            code = item.code if item.code else 'N/A'
            title = item.job_title_id and item.job_title_id.name or 'N/A'
            if item.post_job_ids:
                result[item.id] = {
                    'code_func': '%s - %s *' % (code, title),
                    'code_func_tree': '%s *' % (code)
                }
            else:
                result[item.id] = {
                    'code_func': code + ' - ' + title,
                    'code_func_tree': code
                }
        return result

    def _update_no_of_hired_recruitment(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        result = set()
        for job_app_item in self.browse(cr, uid, ids, context=context):
            if job_app_item.job_id:
                result.add(job_app_item.job_id.id)
        return list(result)

    def _update_no_of_remain_recruitment(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        return list(ids)

    def _is_depthead(self, cr, uid, ids, fields, args, context=None):
        res = {}
        if context is None: context = {}
        roles = self.recruitment_get_group_array(cr, uid, uid)
        for item in self.browse(cr, uid, ids, context=context):
            manager_user_id = item.department_id.manager_id.user_id.id if item.department_id and item.department_id.manager_id else 0
            res[item.id] = True if manager_user_id == uid else False
            if ADMIN in roles and context.get('REQUEST','')=='ADMIN':
                res[item.id] = True
        return res

    def _get_business_impact(self, cr, uid, ids, fields, args, context=None):
        res = {}
        if context is None: context = {}
        for item in self.browse(cr, uid, ids, context=context):
            res[item.id] = item.business_impact_id.code
        return res

    def _is_depthead_delegate(self, cr, uid, ids, fields, args, context=None):
        res = {}
        if context is None:
            context = {}
        dept_delegate = self.pool.get('vhr.delegate.by.depart')
        for item in self.browse(cr, uid, ids, context=context):
            res[item.id] =  False
            manager_id = item.department_id.manager_id and item.department_id.manager_id.id or False
            if manager_id:
#                 lst = dept_delegate.search(cr, uid, ['&',('emp_del_from_id', '=', manager_id),
#                                                      ('emp_del_to_id.user_id', '=', uid)], count=True, context=context)
#
                # Get employee from user
                emp_ids = self.pool['hr.employee'].search(cr, uid, [['user_id', '=', uid]], context=context)
                if emp_ids:
                    # Current employee is manager -> ok
                    if emp_ids[0] == manager_id:
                        res[item.id] =  True
                    else:
                        # Get list delegate from manager_id
                        lst_approvers = dept_delegate.get_delegate(
                           cr, uid, manager_id, {'delegate': True, 'department_id': item.department_id.id})

                        # Current employee in delegate list -> ok
                        if emp_ids[0] in lst_approvers:
                            res[item.id] =  True
        return res

    def _is_hrbp(self, cr, uid, ids, fields, args, context=None):
        result = {}
        if context is None:
            context = {}
        roles = self.recruitment_get_group_array(cr, uid, uid)
        current_emp = self.pool.get('hr.employee').search(cr, uid, [('user_id.id', '=', uid)], context={'active_test': False})
        if current_emp:
            departments = self.get_department_hrbps(cr, uid, current_emp[0], context)
            for item in self.browse(cr, uid, ids, context=context):
                result[item.id] =  False
                if ADMIN in roles and context.get('REQUEST','')=='ADMIN':
                    result[item.id] = True
                if item.department_id.id in departments:
                    result[item.id] = True
                if RRHRBP in roles:
                    result[item.id] = True
        return result

    def _is_ass_hrbp(self, cr, uid, ids, fields, args, context=None):
        result = {}
        if context is None:
            context = {}
        roles = self.recruitment_get_group_array(cr, uid, uid)
        current_emp = self.pool.get('hr.employee').search(cr, uid, [('user_id.id', '=', uid)], context={'active_test': False})
        if current_emp:
            departments = self.get_department_ass_hrbps(cr, uid, current_emp[0], context)
            for item in self.browse(cr, uid, ids, context=context):
                result[item.id] =  False
                if ADMIN in roles and context.get('REQUEST','')=='ADMIN':
                    result[item.id] = True
                if item.department_id.id in departments:
                    result[item.id] = True
        return result

    def _is_rrm(self, cr, uid, ids, fields, args, context=None):
        if context is None:
            context = {}
        result = set()
        return result

    def _is_send_cv_btn(self, cr, uid, ids, fields, args, context=None):
        '''
            Kiem tra dieu kien job_applicant state is draft thi show button
        '''
        res = {}
        if context is None:
            context = {}
        job_applicant_obj = self.pool.get('vhr.job.applicant')
        roles = self.recruitment_get_group_array(cr, uid, uid)
        for item in ids:
            res[item] =  False
            if ADMIN in roles and context.get('REQUEST','')=='ADMIN':
                res[item] = True
                continue
            condition = job_applicant_obj.search(cr, uid, [('job_id','=',item),('state','=','draft')], count=True, context=context)
            if condition:
                res[item] = True
        return res

    def onchange_requestor(self, cr, uid, ids, requestor_company_id, requestor_id, context=None):
        res = {'requestor_dept': False, 'requestor_dev': False, 'requestor_role': False,
               'department_id': False}
        domain = {'requestor_company_id': [('id', 'in', [])]}
        hr_obj = self.pool.get('hr.employee')
        if requestor_id:
            lst_cpy = hr_obj.get_company_list_of_employee(cr, uid, requestor_id)
            domain['requestor_company_id'] = [('id', 'in', lst_cpy)]
#             if requestor_company_id:
#                 lst_dep = hr_obj.get_working_record_of_employee(cr, uid, requestor_id, requestor_company_id)
#                 if lst_dep:
#                     res['requestor_dept'] = lst_dep[0]['department_id_new']
#                     res['requestor_dev'] = lst_dep[0]['division_id_new']
#                     res['requestor_role'] = lst_dep[0]['job_title_id_new']
#                 res['company'] = requestor_company_id
#                 res['department_id'] = res['requestor_dept']
            requestor = hr_obj.browse(cr, uid, requestor_id, context=context)
            res['requestor_dept'] = requestor.department_id.id
            res['requestor_dev'] = requestor.division_id.id
            res['requestor_role'] = requestor.title_id.id
            #res['company'] = requestor_company_id
            res['department_id'] = res['requestor_dept']
            res['requestor_company_id'] = requestor.company_id.id
        return {'value': res, 'domain': domain}
    
    def get_company_for_request(self, cr, uid, department_id,report_to, context=None):
        company_id = False
        hr_obj = self.pool.get('hr.employee')
        
        is_changed = False
        if department_id:
            dept = self.pool.get('hr.department').browse(cr, uid, department_id, context=context)
            if dept.company_id and dept.company_id.code != 'HRS':
                company_id = dept.company_id.id
                is_changed = True
        
        if report_to and not is_changed:
            report_to = hr_obj.browse(cr, uid, report_to, context=context)
            company_id = report_to.company_id and report_to.company_id.id or False
            
        return company_id
    
    def onchange_report_to_department(self, cr, uid, ids,report_to,department_id, context=None):
        res = {'company': False}
        
        res['company'] = self.get_company_for_request(cr, uid, department_id, report_to, context)
        
        return {'value': res}
    
    def onchange_job_title_id(self, cr, uid, ids, job_title_id, job_level_id, context=None):
        domain = {'job_level_id': [('id', 'not in', [])], 'sub_group_id': [('id', 'in', [])]}
        res = {'job_level_id': False, 'sub_group_id': False, 'job_group_id': False, 'sub_family_id': False}
        # job group - sub group
        if job_title_id:
            group_title_obj = self.pool.get('vhr.subgroup.jobtitle')
            lst_item = group_title_obj.search(cr, uid, [('job_title_id', '=', job_title_id), ('active', '=', True)], context=context)
            lst_sub_group = []
            for item in group_title_obj.browse(cr, uid, lst_item, context=context):
                temp = item.sub_group_id
                if temp:
                    lst_sub_group.append(temp.id)
            if len(lst_sub_group) > 0:
                res['sub_group_id'] = lst_sub_group[0]
                domain['sub_group_id'] = [('id', 'in', list(set(lst_sub_group)))]
            # job title -level
            job_level_ids = []
            title_level_ids = self.pool.get('vhr.jobtitle.joblevel').search(cr, uid, [('job_title_id', '=', job_title_id)], context=context)
            if title_level_ids:
                title_level_infos = self.pool.get('vhr.jobtitle.joblevel').read(cr, uid, title_level_ids, ['job_level_id'], context=context)
                for title_level_info in title_level_infos:
                    if title_level_info.get('job_level_id', False):
                        job_level_ids.append(title_level_info['job_level_id'][0])

            if job_level_ids:
                if (job_level_id and job_level_id in job_level_ids) or not job_level_id:
                    res['job_level_id'] = job_level_ids[0]
            domain['job_level_id'] = [('id', 'in', job_level_ids)]
        return {'value': res, 'domain': domain}

    def onchange_job_level_id(self, cr, uid, ids, job_title_id, job_level_id, context=None):
        domain = {'job_title_id': [('id', 'not in', [])]}
        res = {}
        if job_level_id:
            job_title_ids = []
            title_level_ids = self.pool.get('vhr.jobtitle.joblevel').search(cr, uid, [('job_level_id', '=', job_level_id)], context=context)
            if title_level_ids:
                title_level_infos = self.pool.get('vhr.jobtitle.joblevel').read(cr, uid, title_level_ids, ['job_title_id'], context=context)
                for title_level_info in title_level_infos:
                    if title_level_info.get('job_title_id', False):
                        job_title_ids.append(title_level_info['job_title_id'][0])
            if job_title_id and job_title_id not in job_title_ids:
                res['job_title_id'] = False
            # load pc
#             joblevel_pc_list = self.pool.get('vhr.job.level.position.class').search(cr, uid, [('job_level_id', '=', job_level_id)], context=context)
#             if joblevel_pc_list:
#                 joblevel_pc = self.pool.get('vhr.job.level.position.class').browse(cr, uid, joblevel_pc_list[0], context=context)
#                 try:
#                     class_from = int(joblevel_pc.position_class_from.code)
#                     class_to = int(joblevel_pc.position_class_to.code) + 1
#                     from_to = []
#                     for item in range(class_from, class_to):
#                         from_to.append(str(item))
#                     if from_to:
#                         position_class = self.pool.get('vhr.position.class').search(cr, uid, [('code', 'in', from_to)], context=context)
#                         res['position_class_standard_ex'] = list(set(position_class))
#                 except Exception as e:
#                     log.exception(e)
            domain['job_title_id'] = [('id', 'in', job_title_ids)]
        return {'value': res, 'domain': domain}

    def onchange_sub_group_id(self, cr, uid, ids, sub_group_id, context=None):
        res = {'job_group_id': False, 'job_family_id': False}
        if sub_group_id:
            sub_group_obj = self.pool.get('vhr.sub.group').browse(cr, uid, sub_group_id, context=context)
            job_group_obj = sub_group_obj.job_group_id
            if job_group_obj:
                res['job_group_id'] = job_group_obj.id
                res['job_family_id'] = job_group_obj.job_family_id.id
        return {'value': res}

    def onchange_job_family_id(self, cr, uid, ids, job_family_id, job_group_id, context=None):
        if not context:
            context = {}
        res = {'job_group_id': False}

        if job_family_id and job_group_id:
            job_group = self.pool.get('vhr.job.group').read(cr, uid, job_group_id, ['job_family_id'])
            p_job_family_id = job_group.get('job_family_id', False) and job_group['job_family_id'][0] or False
            if job_family_id == p_job_family_id:
                res = {}

        return {'value': res}
    
    def onchange_job_group_id(self, cr, uid, ids, job_group_id, sub_group_id, context=None):
        if not context:
            context = {}
        res = {'sub_group_id': False}
        
        if job_group_id and sub_group_id:
            sub_group = self.pool.get('vhr.sub.group').read(cr, uid, sub_group_id, ['job_group_id'])
            s_job_group_id = sub_group.get('job_group_id', False) and sub_group['job_group_id'][0] or False
            if s_job_group_id == job_group_id:
                res = {}
            
        return {'value': res}

    def onchange_date(self, cr, uid, ids, request_date, expected_date):
        if expected_date and request_date:
            time_delta = datetime.strptime(expected_date, DEFAULT_SERVER_DATE_FORMAT) - datetime.strptime(request_date, DEFAULT_SERVER_DATE_FORMAT)
            day_delta = time_delta.days
            if day_delta < 0:
                warning = {'title': 'User Alert!', 'message': 'Date expected must be larger request date'}
                return {'value': {'expected_date': None}, 'warning': warning}
        return {'value': {}}

    def on_change_reason(self, cr, uid, ids, reason_id, context=None):
        value = {}
        dimension_obj = self.pool.get('vhr.dimension')
        if reason_id:
            source = dimension_obj.browse(cr, uid, reason_id, context=context)
            value['reason_code'] = source and source.code or ''
        return {'value': value}

    def on_change_request_for_company(self, cr, uid, ids, company, context=None):
        value = {}
        company_obj = self.pool.get('res.company')
        if company:
            company_inst = company_obj.browse(cr, uid, company, context=context)
            value['office_id'] = company_inst.office_id.id if company_inst.office_id.active else False
        return {'value': value}

    def onchange_no_recruitment(self, cr, uid, ids, no_of_recruitment):
        value = {}
        if no_of_recruitment:
            if no_of_recruitment >= 3:
                value['priority_1'] = 1
                value['priority_2'] = 1
                value['priority_3'] = no_of_recruitment - value['priority_2'] - value['priority_1']
            else:
                value['priority_3'] = 1
                value['priority_2'] = 0
                value['priority_1'] = 0
                if no_of_recruitment - value['priority_3'] == 1:
                    value['priority_2'] = 1
        return {'value': value}

    def onchange_no_recruitment_ex(self, cr, uid, ids, no_of_recruitment, context=None):
        value = {'is_change_headcount': False}
        if ids and not isinstance(ids, list):
            ids = [ids]
        if ids:
            current_job = self.browse(cr, uid, ids[0], context=context)
            if no_of_recruitment:
                if current_job.no_of_recruitment != no_of_recruitment and current_job.state != 'draft':
                    value['is_change_headcount'] = True
                else:
                    value['is_change_headcount'] = current_job.is_change_headcount
        return {'value': value}

    def on_change_request_job_type(self, cr, uid, ids, request_job_type, context=None):
        if context is None:
            context = {}
        value = {}
        if request_job_type:
            print "\n request_job_type:",request_job_type
            dimension_obj = self.pool.get('vhr.dimension')
            request_job = dimension_obj.browse(cr, uid, request_job_type, context=context)
            if request_job:
                value['request_job_type_code'] = request_job.code
                if request_job.code not in ('OFFICIAL'):
                    value['job_level_position_id'] = False
                    value['career_track_id'] = False

        return {'value': value}

    def action_open_window_ex(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        action_type = context.get('ACTION_TYPE', '')
        view_type = context.get('VIEW_TYPE', 'form')
        view_id = context.get('VIEW_ID', '')
        view_name = context.get('VIEW_NAME', '')
        target = context.get('TARGET', 'new')
        res_model = context.get('MODEL', self._name)
        action = context.get('ACTION', '')
        res_id = False
        try:
            view_module = view_id.split(".")
            if view_module and len(view_module) == 2:
                if action_type == 'POST_JOB':
                    res_model = 'vhr.post.job'
                    job_item = self.browse(cr, uid, ids, context=context)[0].post_job_ids
                    context['hr_job_active_id'] = ids[0]
                    if job_item:
                        res_id = job_item[0].id
                elif action_type == 'WORKFLOW':
                    res_id = ids[0]
                    if action == 'done_in_progress':
                        self.write(cr, uid, res_id, {'is_send_survey': False})
                elif action_type == 'SEARCH_CV':
                    res_id = ids[0]
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
        
    def dummy_function(self, cr, uid, ids, context=None):
        return True

    def signal_workflow_ex(self, cr, uid, id_signal, signal, context=None):
        self.signal_workflow(cr, uid, [id_signal], signal)
        state = self.browse(cr, uid, id_signal, context=context).state
        signal_newstate = SIGNAL[signal]['new_state']
        if state == signal_newstate:
            return True
        return False

    def execute_workflow(self, cr, uid, ids, context=None):
        semaphore.acquire()
        try:
            if not isinstance(ids, list): ids = [ids]
            if context is None: context = {}
            result = False
            if 'ACTION' in context and context['ACTION']:
                job_id = ids[0]
                job_obj = self.browse(cr, uid, job_id, context=context)
                # kiểm tra đk finish job thì tất cả request phải được đóng
                if context['ACTION'] in ['in_progress_done', 'in_progress_close', 'in_progress_cancel']:
                    job_applicant_obj = self.pool.get('vhr.job.applicant')
                    final_state_domain = [('job_id', '=', job_id),'|',('state', 'in', ['done', 'close']),'&',('state', '=','offer'),('hr_process','=',True)]
                    job_app_end_step_count = job_applicant_obj.search(cr, uid, final_state_domain, count=True)# not pass context
                    if len(job_obj.job_applicant_ids) != job_app_end_step_count:
                        raise osv.except_osv('Validation Error !', 'Please close all interviews')
                    # đóng job thì đóng luôn post job
                    post_job_obj = self.pool.get('vhr.post.job')
                    for item in job_obj.post_job_ids:
                        post_job_obj.write(cr, uid, item.id, {'state': 'done'})
                ids_state = self.write_change_state(cr, uid, ids, context['ACTION'], context.get('ACTION_COMMENT', ''))
                result = self.signal_workflow_ex(cr, uid, job_id, context['ACTION'])
                if not result:  # neu workflow chay ko thanh cong ghi log
                    self.pool.get('vhr.state.change').unlink(cr, SUPERUSER_ID, ids_state)
                    log.error('hr_job : execute_workflow : signal_workflow_ex : fail at job_id %s'%(job_id))
                else:
                    # Send Email depthead and delegate approve
                    if context['ACTION'] == 'waiting_hrbp_waiting_dept':
                        depthead = job_obj.department_id.manager_id if job_obj.department_id else False
                        if depthead:
                            rr_email_obj = self.pool['vhr.recruitment.email']
                            lst_approvers = self.pool['vhr.delegate.by.depart'].get_delegate(
                                cr, uid, depthead.id, {'delegate': True, 'department_id': job_obj.department_id.id})
                            link_email = self.get_url(cr, uid, job_id, context)
                            for approver in self.pool['hr.employee'].browse(cr, uid, lst_approvers, context=context):
                                email_to = approver.work_email.lower() if approver.work_email else ''
                                if email_to:
                                    rr_email_obj.send_email(cr, uid, EMAIL_DEPTHEAD_APPROVE,
                                                        {'email_to': email_to, 'link_email': link_email,
                                                         'approver': approver.id, 'job_id': job_id, 'request_code': job_obj.code},
                                                        context={'APPROVE_EMAIL': True})
                        else:
                            log.error('hr_job : execute_workflow : send_approve_by_email : fail at job_id %s' % (job_id))
        finally:
            semaphore.release()
        return result

    def vhr_job_execute_workflow(self, cr, uid, ids, action, context=None):
        vals = {'state': action}
        if action == WAITING_DEPT:
            vals['hrbp_approve'] = uid
        elif action == WAITING_RRM:
            vals['dept_head_approve'] = uid
        elif action == IN_PROGRESS:
            vals['rrm_approve'] = uid
        res = self.write(cr, uid, ids, vals, context)
        return res
    
    def _is_reject_rrm_approve(self, cr, uid, ids, fields, args, context=None):
        result = {}
        if context is None:
            context = {}
        for item in self.browse(cr, uid, ids, context=context):
            result[item.id] =  False
            request_job_type = item.request_job_type.code
            for change in item.state_log_ids:
                if change.old_state =='waiting_rrm' and change.new_state =='waiting_hrbp' and\
                    request_job_type =='OFFICIAL':
                    result[item.id] = True
        return result   
    
    def _rrm_approve_date(self, cr, uid, ids, fields, args, context=None):
        result = {}
        if context is None:
            context = {}
        for item in self.browse(cr, uid, ids, context=context):
            result[item.id] = False
            for change in item.state_log_ids:
                #print "========change.old_state: ", change.old_state
                #print "========change.new_state: ", change.new_state
                if change.old_state == 'RRM Approved' and change.new_state =='In Progress':
                    date_approve = change.create_date
                    date_temp  = datetime.strptime(date_approve,'%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
                    result[item.id] = date_temp
                    #print "========result: ", result
        return result  
    
    _columns = {
        'name': fields.char('Application Name', size=256),
        'code': fields.char('Code', size=32),
        'code_func': fields.function(_get_full_code, type="char", string="Code", multi="get_job_code"),  # Show button Done Process
        'code_func_tree': fields.function(_get_full_code, type="char", string="Code", multi="get_job_code"),
        'requestor_id': fields.many2one('hr.employee', 'Requester', ondelete='restrict'),
        'requestor_company_id': fields.many2one('res.company', 'Requester Company', ondelete='restrict'),
        'requestor_dept': fields.many2one('hr.department', 'Department', ondelete='restrict',
                                          domain="[('company_id','=',requestor_company_id)]"),
        'requestor_dev': fields.many2one('hr.department', 'Business Unit', ondelete='restrict',
                                         domain="[('company_id','=',requestor_company_id)]"),
        'requestor_role': fields.many2one('vhr.job.title', string='Requester role',  ondelete='restrict'),

        'request_date': fields.date('Request date'),
        'expected_date': fields.date('Expected date'),

        'job_level_id': fields.many2one('vhr.job.level', 'Level', ondelete="restrict"),

        #New Job Level
        #ĐÚng ra tên phải là job_level_person_id
        'job_level_position_id': fields.many2one('vhr.job.level.new', 'Person Level', ondelete='restrict'),

        # 'job_family_id_func'
        'job_title_id': fields.many2one('vhr.job.title', 'Title/Role', ondelete="restrict"),
        'sub_group_id': fields.many2one('vhr.sub.group', 'Sub Group', ondelete='restrict'),
#         'job_group_id': fields.related('sub_group_id', 'job_group_id', type="many2one", store=True,
#                                        relation='vhr.job.group', string='Job Group'),
#         'job_family_id': fields.related('job_group_id', 'job_family_id', type="many2one", store=True,
#                                         relation='vhr.job.family', string='Job Family'),
        'job_group_id': fields.many2one('vhr.job.group', string='Job Group', ondelete='restrict'),
        'job_family_id': fields.many2one('vhr.job.family', string='Job Family', ondelete='restrict'),

        'career_track_id': fields.many2one('vhr.dimension', 'Career Track', domain=[('dimension_type_id.code','=','CAREER_TRACK')], ondelete='restrict'),
        # change to
        'degree_id': fields.many2one('vhr.certificate.level', 'Education Level', ondelete='restrict', domain="[('is_degree','=',True)]"),

        'description': fields.text(u'Mô tả', help=u"Điền thông tin (Mô tả & yêu cầu) or (Description & Requirement)"),
        'requirements': fields.text(u'Yêu Cầu', help=u"Điền thông tin (Mô tả & yêu cầu) or (Description & Requirement)"),
        'description_en': fields.text('Description', help=u"Điền thông tin (Mô tả & yêu cầu) or (Description & Requirement)"),
        'requirement_en': fields.text('Requirement', help=u"Điền thông tin (Mô tả & yêu cầu) or (Description & Requirement)"),
        'preference': fields.text(u'Ưu tiên'),
        'preference_en': fields.text('Preference'),
        'reason_id': fields.many2one('vhr.dimension', 'Reason', ondelete='restrict',
                                     domain=[('dimension_type_id.code', '=', 'RECRUITMENT_REASON'), ('active', '=', True)]),
        'reason_code': fields.related('reason_id', 'code', type='char', relation='vhr.dimension', string='Reason code'),
        'reason_emp': fields.many2many('hr.employee', 'hr_job_reason_emp_rel', 'job_id', 'emp_id', 'For employee'),

        'difficult_level_id':  fields.many2one('vhr.dimension', 'Job Type', ondelete='restrict',
                                               domain=[('dimension_type_id.code', '=', 'DIFFICULT_LEVEL'), ('active', '=', True)]),
        # BinhNX: Add new field business_impact_id for RR Report in 2016
        # Change name from Business Impact to Urgency
        'business_impact_id':  fields.many2one('vhr.business.impact', 'Urgency', ondelete='restrict',
                                               domain=[('active', '=', True)]),
        'business_impact': fields.function(_get_business_impact, type="char", string="Urgency"),

        'office_id': fields.many2one('vhr.office', 'Working Place', ondelete='restrict'),
        'gender': fields.selection([('male', 'Male'), ('female', 'Female'), ('any', 'Any')], 'Gender'),
        'report_to': fields.many2one('hr.employee', 'Report To'),
        'job_type_id': fields.many2one('vhr.dimension', 'Job Type', ondelete='restrict',
                                       domain=[('dimension_type_id.code', '=', 'JOB_TYPE'), ('active', '=', True)]),
        'position_class_standard': fields.char('Position class standard'),
        #LuanNG: Remove this field in future version of vHRS
        'position_class_standard_ex': fields.many2many('vhr.position.class', 'job_position_class_rel', 'job_id',
                                                       'position_class_id', 'Position class standard'),
        'categ_ids': fields.many2many('hr.applicant_category', string='Tags'),  # for suggest candidate
        # request for repartment
        'company': fields.many2one('res.company', 'Request for company'),
        'department_id': fields.many2one('hr.department', 'Request for department', ondelete='restrict',
                                         domain="[('organization_class_id.level','in',[3,6])]"),
        'department_dept': fields.related('department_id', 'manager_id', type="many2one", relation='hr.employee',
                                          string='Request Depthead'),
        'department_hrbps': fields.related('department_id', 'hrbps', type="many2many", relation='hr.employee',
                                           string='Request Depthead'),
        'department_code': fields.related('department_id', 'code', type="char", relation='hr.department',
                                          string='Depart request'),
        'job_applicant_ids': fields.one2many('vhr.job.applicant', 'job_id', 'Match CV'),
        'none_official': fields.boolean('None Official'),
        'no_depthead_approval': fields.boolean('Depthead Approval'),

        'handle_by': fields.many2one('hr.employee', 'Handle By', ondelete='restrict'),
        'share_handle_by': fields.many2one('hr.employee', 'Share Handle By', ondelete='restrict'),
        'is_critical': fields.boolean('Is Critical'),
        # old data change to priority_1,2,3
        'priority_id': fields.many2one('vhr.dimension', 'Priority', ondelete='restrict',
                                       domain=[('dimension_type_id.code', '=', 'PRIORITY_LEVEL'),
                                               ('active', '=', True)]),
        'priority_1': fields.integer('Priority 1', help="Priority 1 + Priority 2 + Priority 3 = Request quantity"),
        'priority_2': fields.integer('Priority 2', help="Priority 1 + Priority 2 + Priority 3 = Request quantity"),
        'priority_3': fields.integer('Priority 3', help="Priority 1 + Priority 2 + Priority 3 = Request quantity"),
        'no_of_hired_recruitment': fields.function(_get_current_hired_recruitment, type="integer", string="Recruited Qty",
                                                   multi="count_recruited", store={'vhr.job.applicant':
                                                                                   (_update_no_of_hired_recruitment, ['state', 'hr_process'], 10)}),
        'no_of_remain_recruitment': fields.function(_get_current_hired_recruitment, type="integer", string="Remain",
                                                    multi="count_recruited", store={'vhr.job.applicant':
                                                                                    (_update_no_of_hired_recruitment, ['state', 'hr_process'], 10),
                                                                                    'hr.job': (_update_no_of_remain_recruitment, ['no_of_recruitment'], 10)}),
        # hrbp
        'in_budget': fields.boolean('In budget'),
        'current_headcount_official': fields.integer('Current headcount (official staff)'),
        'current_headcount_collaborators': fields.integer('Current headcount (collaborators)'),
        'state': fields.selection(STATE_NAME, string='Status', readonly=True, required=True,
                                  track_visibility='always',
                                  help="Done : Request quantity = Recruited quantity \nClose : 0 < Recruited quantity < Request quantity\nCancel : Recruited quantity = 0"),
        # Post job
        'post_job_ids': fields.many2many('vhr.post.job', 'post_job_hr_job_rel', 'hr_job_id', 'post_job_id', 'Post Job'),
        # audittrail
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'History',
                                         domain=[('object_id.model', '=', _name),
                                                 ('field_id.name', 'not in', ['write_date', 'audit_log_ids'])]),
        # state log
        'state_log_ids': fields.one2many('vhr.state.change', 'res_id', 'History', domain=[('model', '=', _name)]),
        # hide_button_close
        'is_show_dh_approve': fields.function(_get_dept_head_approve, method=True, type='boolean', string='DH Approved'),
        'show_finish_button': fields.function(_get_current_hired_recruitment, type="char", string="Button Show",
                                              multi="count_recruited"),
        'is_show_send_cv': fields.function(_is_send_cv_btn, type="boolean", string="Is Send CV"),
        # approve
        'dept_head_approve': fields.many2one('res.users', 'Depthead approve'),
        'hrbp_approve': fields.many2one('res.users', 'HRBP approve'),
        'rrm_approve': fields.many2one('res.users', 'RRM approve'),

        # check role
        'is_depthead': fields.function(_is_depthead, type="boolean", string="Is depthead"),
        'is_depthead_delegate': fields.function(_is_depthead_delegate, type="boolean", string="Is depthead delegate"),
        'is_hrbp': fields.function(_is_hrbp, type="boolean", string="Is Hrbp"),
        'is_ass_hrbp': fields.function(_is_ass_hrbp, type="boolean", string="Is Assis Hrbp"),
        'is_rrm': fields.function(_is_rrm, type="boolean", string="Is Rrm"),
        # change headcount
        'is_change_headcount': fields.boolean('Is change headcount'),
        'change_headcount_comment': fields.text('Reason change'),
        'dept_head_delay': fields.integer('Delay by dept'),
        'reason_delay': fields.text('Reason delay'),
        'reason_close_id': fields.many2one('vhr.dimension', 'Reason Close',
                                           domain=[('dimension_type_id.code', '=', 'CLOSE_REQUEST'), ('active', '=', True)]),
        'reason_content': fields.related('reason_close_id', 'name', type='char', relation='vhr.close.reason', string='Reason Cancel', store=True),
        'request_job_type':  fields.many2one('vhr.dimension', 'Request Type', ondelete='restrict',
                                               domain=[('dimension_type_id.code', '=', 'RR_REQUEST_TYPE'), ('active', '=', True)]),
        'request_job_type_code': fields.related('request_job_type', 'code', type='char', relation='vhr.dimension', string='Request Type Code', store=False),
         'is_specialerp':fields.boolean('Is Special ERP',),
         'special_erp_ids':fields.one2many('vhr.erp.setting.special','special_job_id','Special ERP'),
          'is_bonus_recruiter':fields.boolean('Is Bonus Recruiter',),
         'bonus_recruiter_ids':fields.one2many('vhr.bonus.for.recruiter','bonus_for_recruiter_job_id','Bonus for Recruiter'),
        'is_reject_rrm': fields.function(_is_reject_rrm_approve, type="boolean", string="Is Reject RRM"),
        'job_title_name': fields.related('job_title_id', 'name', type="char", relation='vhr.job.title',
                                          string='Job Title'),
                
        'rrm_approve_date': fields.function(_rrm_approve_date, type="date",
                                            store= True,string="RRM Approve"),
                
        'is_send_survey':fields.boolean('Is Send Survey'),
        }
    _defaults = {
        'state': 'draft',
        'in_budget': False,
        'none_official': False,
        'no_of_recruitment': 1,
        'no_depthead_approval': False,
        'no_of_hired_recruitment': 0,
        'no_of_remain_recruitment': 0,
        'is_specialerp':False,
        'is_send_survey':False,
    }

    _unique_insensitive_constraints = [{'code': "Request's Code is already exist!"}]

    _order = 'rrm_approve_date desc,state desc, request_job_type asc, request_date desc, id desc'

    def init(self, cr):
        cr.execute("ALTER TABLE hr_job DROP CONSTRAINT IF EXISTS hr_job_name_company_uniq")
        cr.execute("ALTER TABLE hr_job DROP CONSTRAINT IF EXISTS name_company_uniq")
        cr.execute("ALTER TABLE hr_job DROP CONSTRAINT IF EXISTS hired_employee_check")
        cr.execute("ALTER TABLE hr_job DROP CONSTRAINT IF EXISTS hr_job_hired_employee_check")
        cr.commit()

    def on_change_is_specialerp(self,cr, uid, ids,is_specialerp,context=None):
        context=context or {}
        special_erp_ids = []
        value = {}
        setting_special_obj = self.pool.get('vhr.erp.setting.special')
        erp_level_obj = self.pool.get('vhr.erp.level')
        if not is_specialerp:
            if ids:
                old_ids = setting_special_obj.search(cr, uid,[('special_job_id','in',ids)])
                setting_special_obj.unlink(cr, uid, old_ids)
        if is_specialerp:
            for job in self.browse(cr, uid, ids):
                job_id = job.id
                job_family_id = job.job_family_id.id if job.job_family_id else False
                job_group_id = job.job_group_id.id if job.job_group_id else False
                level_ids = erp_level_obj.search(cr, uid,[('job_family_id','=',job_family_id),('active','=',True)],order='id asc',context=context)
                if level_ids:
                    for level in erp_level_obj.browse(cr, uid, level_ids):
                        total_bonus = level.total_bonus or 0
                        level_id = level.id
                        total_bonus_specialerp = 0
                        job_level_position_id =  level.job_level_position_id.id if level.job_level_position_id else False
                        vals = {
                                'job_family_id':job_family_id,
                                'job_group_id':job_group_id,
                                'total_bonus':total_bonus,
                                'erp_level_id':level_id,
                                'job_level_position_id':job_level_position_id,
                                'total_bonus_specialerp':total_bonus_specialerp,
                                'special_job_id':job_id,
                                }
                        special_erp_ids.append((0,0,vals))
        value.update(special_erp_ids=special_erp_ids)
                        #setting_special_obj.create(cr, uid, vals)
        return {'value':value}
    
    def on_change_is_bonus_recruiter(self,cr, uid, ids,is_bosnu_recruiter,context=None):
        context=context or {}
        bonus_recruiter_ids = []
        value = {}
        recruiter_obj = self.pool.get('vhr.bonus.for.recruiter')
        erp_level_obj = self.pool.get('vhr.erp.level')
        if not is_bosnu_recruiter:
            if ids:
                old_ids = recruiter_obj.search(cr, uid,[('bonus_for_recruiter_job_id','in',ids)])
                recruiter_obj.unlink(cr, uid, old_ids)
        if is_bosnu_recruiter:
            for job in self.browse(cr, uid, ids):
                job_id = job.id
                job_family_id = job.job_family_id.id if job.job_family_id else False
                job_group_id = job.job_group_id.id if job.job_group_id else False
                level_ids = erp_level_obj.search(cr, uid,[('job_family_id','=',job_family_id),('active','=',True)],order='id asc',context=context)
                if level_ids:
                        for level in erp_level_obj.browse(cr, uid, level_ids):
                            level_id = level.id
                            job_level_position_id =  level.job_level_position_id.id if level.job_level_position_id else False
                            vals = {
                                    'job_family_id':job_family_id,
                                    'job_group_id':job_group_id,
                                    'bonus_for_recruiter':0,
                                    'erp_level_id':level_id,
                                    'job_level_position_id':job_level_position_id,
                                    'bonus_for_recruiter_job_id':job_id,
                                    }
                            bonus_recruiter_ids.append((0,0,vals))
                            #recruiter_obj.create(cr, uid, vals)
        value.update(bonus_recruiter_ids=bonus_recruiter_ids)
        return {'value':value}

    def check_detail_information(self, cr, uid, vals, ids=False, context=None):
        description = vals.get('description', False)
        description_en = vals.get('description_en', False)
        requirements = vals.get('requirements', False)
        requirement_en = vals.get('requirement_en', False)

        def check_infor(description, description_en, requirements, requirement_en):
            if not (description or description_en):
                raise osv.except_osv('Validation Error !', 'Please input description')
            if not (requirements or requirement_en):
                raise osv.except_osv('Validation Error !', 'Please input requirement')
            if not ((description and requirements) or (description_en and requirement_en)):
                raise osv.except_osv('Validation Error !', 'Please input (Mô tả & Yêu cầu) or (Description & Requirement)')

        if not ids:
            check_infor(description, description_en, requirements, requirement_en)
        else:
            for obj in self.browse(cr, uid, ids, context=context):
                if 'description' not in vals:
                    description = obj.description
                if 'description_en' not in vals:
                    description_en = obj.description_en
                if 'requirements' not in vals:
                    requirements = obj.requirements
                if 'requirement_en' not in vals:
                    requirement_en = obj.requirement_en
                check_infor(description, description_en, requirements, requirement_en)
            return True

    def check_is_cif_request(self, cr, uid, title_code, level_code):
        """ Kiểm tra title_code và level_code có phải thuộc CTV/Intern/Fresher
            :param title_code : code title cần kiểm tra
            :param level_code : code level cần kiểm tra
            :returns True : nếu title_code và level_code nằm trong config
        """
        result = False
        if title_code:
            config_param = self.pool.get('ir.config_parameter')
            title_codes = config_param.get_param(cr, uid, 'vhr.rr.title.code')
            title_codes = title_codes.split(',') if title_codes else []
#             level_codes = config_param.get_param(cr, uid, 'vhr.rr.level.code')
#             level_codes = level_codes.split(',') if level_codes else []
            if title_code in title_codes:
                result = True
        return result

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        res = super(hr_job, self).default_get(cr, uid, fields, context=context)
        # execute
        hr_obj = self.pool.get('hr.employee')
        dimension_obj = self.pool.get('vhr.dimension')
        degree_obj = self.pool.get('vhr.certificate.level')

        today = date.today()
        job_type_id = dimension_obj.search(cr, uid,
                                           [('dimension_type_id.code', '=', 'JOB_TYPE'), ('code', '=', 'FULLTIME')], context=context)
        reason_id = dimension_obj.search(cr, uid,
                                         [('dimension_type_id.code', '=', 'RECRUITMENT_REASON'), ('code', '=', 'NEW')], context=context)
        degree_id = degree_obj.search(cr, uid, [('code', '=', '01')], context=context)
        emp_id = hr_obj.search(cr, uid, [('user_id', '=', uid)], context=context)
        # sau khi C&B golive uncomment
#         if emp_id:
#             req_comp_ids = hr_obj.get_company_list_of_employee(cr, uid, emp_id[0])
#             res['requestor_id'] = emp_id
#             res['requestor_company_id'] = list(set(req_comp_ids))
        # sau khi C&B golive comment
        if emp_id:
            emp_inst = hr_obj.browse(cr, uid, emp_id[0], context=context)
            res['requestor_id'] = emp_id[0]
            res['requestor_company_id'] = emp_inst.company_id.id

        if context.get('default_request_job_type_code', False):
            dimension_ids = self.pool.get('vhr.dimension').search(cr, uid, [('code','=', context['default_request_job_type_code'])])
            res['request_job_type'] = dimension_ids and dimension_ids[0] or False

        res.update({'request_date': today.strftime("%Y-%m-%d"),
                    'gender': 'any',
                    'job_type_id': job_type_id,
                    'reason_id': reason_id,
                    'degree_id': degree_id
                    })
        return res

    def create(self, cr, uid, vals, context=None):
        self.check_detail_information(cr, uid, vals)
        if vals.get('department_id', False):
            dept_rec = self.pool.get('hr.department').browse(cr, uid, vals.get('department_id'), context=context)
            dept_code = dept_rec and dept_rec.code or 'N/A'
        if vals.get('no_of_recruitment'):
            vals['no_of_remain_recruitment'] = vals.get('no_of_recruitment')
        vals['code'] = self.generate_code(cr, uid, dept_code, context=context)
        vals['name'] = vals['code']
        log.info('Code hr_job generate %s' % (vals['code']))
        return super(hr_job, self).create(cr, uid, vals, context=context)

    def create_interview(self, cr, uid, ids, applicant_ids, context=None):
        '''
            is_new_emp để làm gì vậy ta ????
        '''
        job_applicant_obj = self.pool.get('vhr.job.applicant')
        applicant_obj = self.pool['hr.applicant']

        hr_job = self.browse(cr, uid, ids[0])
        for applicant in applicant_obj.browse(cr, uid, applicant_ids, context=context):
            match = job_applicant_obj.search(cr, uid, [('job_id', '=', ids[0]), ('applicant_id', '=', applicant.id)], context=context)
            if not match:
                is_new_emp = not applicant.ex_employee
                job_applicant_obj.execute_create(
                    cr, uid,
                    {'job_id': ids[0],
                     'applicant_id': applicant.id,
                     'state': 'draft',
                     'is_new_emp': is_new_emp})
                applicant_obj.write_change_state(cr, uid, applicant.id, STATE_APP[1][0], u'Request Matching')

        return True

    def get_share_handle_by_cc(self, cr, uid, hr_job_ids, context=None):
        if context is None:
            context = {}
        hr_job = False
        if hr_job_ids:
            hr_job = self.browse(cr, uid, hr_job_ids[0], context=context)
        cc = 'admin@hrs;'
        if hr_job:
            if hr_job.handle_by:
                cc += str(hr_job.handle_by.work_email) + ';'
            if hr_job.share_handle_by and hr_job.share_handle_by.report_to and str(hr_job.share_handle_by.report_to.work_email) not in cc:
                cc += str(hr_job.share_handle_by.report_to.work_email)
        return cc


    def write(self, cr, uid, ids, vals, context=None):
        """
            Note 1. override fields candidate_ids (important for maintenance)
            Note 2. action_comment is dynamic field remove it before call super (important for maintenance)
        """
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]
        # check Detail
        job_obj = self.browse(cr, uid, ids[0], context=context)
        if 'description' in vals or 'description_en' in vals or 'requirements'in vals or 'requirement_en' in vals:
            self.check_detail_information(cr, uid, vals, ids)
        # check priority
        if 'priority_1' in vals or 'priority_2' in vals or 'priority_3' in vals or\
            (vals.get('no_of_recruitment', False) and job_obj.state == 'in_progress') or\
            ('state' in vals and vals['state'] == 'waiting_dept') or ('state' in vals and vals['state'] == 'waiting_rrm'):
            if vals.get('no_of_recruitment', job_obj.no_of_recruitment) != vals.get('priority_1', job_obj.priority_1) + \
            vals.get('priority_2', job_obj.priority_2) + vals.get('priority_3', job_obj.priority_3):
                raise osv.except_osv('Validation Error !', 'Priority 1 + Priority 2 + Priority 3 = Request quantity!')
        # 14/01/2015 update khi hrbp reject thi update state_note thanh draft luon
        if vals.get('state') and vals.get('state') == DRAFT:
            self.update_state_note(cr, uid, ids)
        # Note 2
        if ('ACTION' in context and context['ACTION']):
            if 'action_comment' in vals:
                del vals['action_comment']
        # Send email when change vacancy
        if 'no_of_recruitment' in vals and job_obj.state != 'draft':
            email_temp = ''
            if job_obj.state == 'waiting_hrbp':
                email_temp = 'VHR_RR_HRBP_CHANGE_HEADCOUNT'
            elif job_obj.state == 'waiting_rrm' or job_obj.state == 'in_progress':
                email_temp = 'VHR_RR_RRM_CHANGE_HEADCOUNT'
            link_email = self.get_url(cr, uid, job_obj.id, context)
            vhr_email = {'old_data': job_obj.no_of_recruitment, 'new_data': vals['no_of_recruitment'],
                         'note': vals.get('change_headcount_comment', ''),
                         'job_id': job_obj.id, 'request_code': job_obj.code, 'link_email': link_email}
            if email_temp:
                rr_email = self.pool.get('vhr.recruitment.email')
                rr_email.send_email(cr, uid, email_temp, vhr_email)

        result = super(hr_job, self).write(cr, uid, ids, vals, context=context)
        # change handle send email
        if job_obj.state == 'in_progress':
            if 'handle_by' in vals:
                email_ids = self.pool.get('email.template').search(
                    cr, uid, [('model', '=', self._name), ('name', '=', 'RE_K2_SendMail_HandleBy')], context=context)
                if email_ids:
                    self.vhr_send_mail(cr, uid, email_ids[0], job_obj.id, context=context)
            # change share handle send email
            if 'share_handle_by' in vals and vals.get('share_handle_by') not in (None, False):
                email_ids = self.pool.get('email.template').search(
                    cr, uid, [('model', '=', self._name), ('name', '=', 'RE_K2_SendMail_ShareHandleBy')], context=context)
                if email_ids:
                    self.vhr_send_mail(cr, uid, email_ids[0], job_obj.id, context=context)
        return result

    def fields_view_get(self, cr, user, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if context is None:
            context = {}
        res = super(hr_job, self).fields_view_get(cr, user, view_id, view_type, context, toolbar=toolbar, submenu=submenu)
        # Tree khong hien action in more
        if (view_type == 'tree' and toolbar) or (view_type=='form' and context.get('REQUEST') and context.get('REQUEST')!='MY_TASKS'):
            if res.get('toolbar', False) and isinstance(res.get('toolbar', False), dict) and res['toolbar'].get('action', False):
                res['toolbar']['action'] = []
        if view_type == 'form':
            roles = self.recruitment_get_group_array(cr, user, user)
            doc = etree.XML(res['arch'])
            if context.get('ACTION', False) and context.get('active_id', False):
                node = doc.xpath("//form/separator")
                if node:
                    node = node[0].getparent()
                    if 'required_comment' in context and context['required_comment']:
                        node_notes = etree.Element('field', name="action_comment", colspan="4", modifiers=json.dumps({'required': True}))
                    else:
                        node_notes = etree.Element('field', name="action_comment", colspan="4")
                    node.append(node_notes)
                    res['arch'] = etree.tostring(doc)
                    res['fields'].update({'action_comment': {'selectable': True, 'string': 'Action Comment', 'type': 'text', 'views': {}}})
            # phan quyen
            if 'REQUEST' in context:
                if HRBP in roles or RRHRBP in roles or RECRUITER in roles:
                    for node in doc.xpath("//field[@name='none_official']"):
                        node.set('modifiers', json.dumps({'invisible': [('request_job_type_code','!=', 'OFFICIAL')], 'readonly':[('state','not in',['draft'])]}))
                if context['REQUEST'] == 'MY_APPROVALS' or context['REQUEST'] == 'MY_REQUESTS':
                    for node in doc.xpath("//field[@name='post_job_ids']"):
                        node.set('modifiers', json.dumps({'readonly': True}))
                    if context['REQUEST'] == 'MY_REQUESTS':
                        for node in doc.xpath("//button[@my_request='False']"):
                            node.set('modifiers', json.dumps({'invisible': True}))
                    if context['REQUEST'] == 'MY_APPROVALS':
                        for node in doc.xpath("//button"):
                            node.set('modifiers', json.dumps({'invisible': True}))

                elif context['REQUEST'] == 'MY_TASKS' or context['REQUEST'] == 'ADMIN':
                    dicti = {}
                    # menu resouce request thì admin như quyền rrm
                    if context['REQUEST'] == 'ADMIN' and ADMIN in roles:
                        self.modification_view_hrbp(cr, user, dicti)
                        self.modification_view_rrm(cr, user, doc, dicti)
                        self.modification_view_rr_admin(cr, user, dicti)
                    else:
                        if HRBP in roles or RRHRBP in roles:
                            self.modification_view_hrbp(cr, user, dicti)
                        if MANAGER in roles:
                            self.modification_view_rrm(cr, user, doc, dicti)
                        if RECRUITER in roles and MANAGER not in roles:
                            self.modification_view_recruiter(cr, user, doc, dicti, context)
                    self.view_factory(cr, user, doc, dicti, context)
            res['arch'] = etree.tostring(doc)
        return res

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context = {}
        context['active_test'] = False
        args = self.get_args(cr, uid, context.get('REQUEST'), args)
        return super(hr_job, self).search(cr, uid, args, offset, limit, order, context, count)

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(hr_job, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res

    def copy(self, cr, uid, id, default=None, context=None):
        default = {} if default is None else default.copy()
        default.update({
            'rrm_approve': False,
            'dept_head_approve': False,
            'hrbp_approve': False,
            'state_log_ids': [],
            'audit_log_ids': [],
            'post_job_ids': [],
            'in_budget': True,
            'priority_id': False,
            'is_critical': False,
            'handle_by': False,
            'business_impact_id': False,
            'job_applicant_ids': [],
        })
        return super(hr_job, self).copy(cr, uid, id, default=default, context=context)

    def read(self, cr, user, ids, fields=None, context=None, load='_classic_read'):
        if context is None:
            context = {}
        # validate read
        result_check = self.check_read_access(cr, user, ids, context)
        if not result_check:
            raise osv.except_osv('Validation Error !', 'You don’t have permission to access this data !')
        # end validate read
        res = super(hr_job, self).read(cr, user, ids, fields, context, load)
        context.update({'active_test': False})
        if 'reason_emp' in fields:
            res_read = super(hr_job, self).read(cr, user, ids, ['reason_emp'], context, load)
            for item in res:
                for item_read in res_read:
                    if item['id'] == item_read['id']:
                        item.update({'reason_emp': item_read['reason_emp']})
        if 'REQUEST' in context and context['REQUEST'] == 'MY_TASKS':
            context.update({'show_domain': True})
            res_read = super(hr_job, self).read(cr, user, ids, ['handle_by', 'requestor_id', 'report_to'], context, load)
            if 'handle_by' in fields:
                for item in res:
                    for item_read in res_read:
                        if item['id'] == item_read['id']:
                            item.update({'handle_by': item_read['handle_by']})
            if 'requestor_id' in fields:
                for item in res:
                    for item_read in res_read:
                        if item['id'] == item_read['id']:
                            item.update({'requestor_id': item_read['requestor_id']})
            if 'report_to' in fields:
                for item in res:
                    for item_read in res_read:
                        if item['id'] == item_read['id']:
                            item.update({'report_to': item_read['report_to']})
            context.pop('show_domain', None)
        return res

    def validate_read(self, cr, uid, ids, context=None):  # implement
        """
            Các view liên quan :
                - hr.job - vhr_job_applicant - hr.applicant
            Các role được view
                - HRBP, CANDB, ADMIN, MANAGER, RECRUITER (Done)
                - RAMS, DEPTHEAD (Done)
                - thằng được delegate
                - thằng tạo request (Done)
                - Có context = CAND_INTERVIEW : đọc job từ màn hình vhr_job_applicant
            Các role được view:
                - tại sao HRBP, CANDB, ADMIN, MANAGER, RECRUITER được view ?
                -> nếu thay đổi nhớ add thêm điều kiện cho temp_args
        """
        if uid == 1:
            return True
        log.info('validate_read : %s'%(uid))
        if context is None: context = {}
        if context.get('CAND_INTERVIEW'):
            return True
        roles = self.recruitment_get_group_array(cr, uid, uid, context)
        if RECRUITER in roles or CANDB_ROLE in roles:
            return True
        if not isinstance(ids, list):
            ids = [ids]
        current_emp = self.pool.get('hr.employee').search(cr, uid, [('user_id.id', '=', uid)], context={'active_test': False})
        if current_emp:
            # temp_args = ['&']
            # temp_args.append(('id', 'in', ids))
            # temp_args.extend(['|', '|', '|', '|', '|', '|'])
            # temp_args.append(('create_uid', '=', uid))
            # temp_args.append(('requestor_id', '=', current_emp[0]))
            # temp_args.append(('dept_head_approve', '=', uid))
            # # depthead
            # temp_args.append(('department_id.manager_id', '=', current_emp[0]))
            # # ram
            # lst_dept_ram = self.get_department_rams(cr, uid, current_emp[0])
            # temp_args.append('&')
            # temp_args.append(('department_id', 'in', lst_dept_ram))
            # temp_args.append(('state', '!=', 'draft'))
            # # delegate
            # lst_delegate = self.get_delegate_department(cr, uid, current_emp[0])
            # temp_args.append(('id', 'in', lst_delegate))
            # #from job_applicant_view -> co quyen write
            # lst_job_view = self.get_list_job_from_interview(cr, uid, current_emp[0], ids)
            # temp_args.append(('id', 'in', lst_job_view))

            lst_job = self.search(cr, uid, [('id', 'in', ids)], context=context)
            if ids and set(ids).intersection(set(lst_job)):
                return True
        return False

    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False, lazy=True):
        """
        Get the list of records in list view grouped by the given ``groupby`` fields
        """
        # Dont show employee in group system
        if 'REQUEST' in context:
            request = context['REQUEST']
            domain = self.get_args(cr, uid, request, domain)
        if context.get('REQUEST', False) == 'MY_TASKS':
            orderby = 'state asc, request_job_type asc, handle_by asc'

        return super(hr_job, self).read_group(cr, uid, domain, fields, groupby, offset, limit, context, orderby, lazy)

    def write_change_state(self, cr, uid, ids, signal, comment="", context=None):
        if not isinstance(ids, list):
            ids = [ids]
        result = []
        state_change_obj = self.pool['vhr.state.change']
        for item in ids:
            state_vals = {}
            if signal:
                state_vals = SIGNAL[signal]
            state_vals['model'] = self._name
            state_vals['res_id'] = item
            state_vals['comment'] = comment
            if state_vals['old_state'] == 'draft':
                state_vals['old_state'] = 'Submitted'
            state_id = state_change_obj.create(cr, uid, state_vals)
            result.append(state_id)
        return result

    def generate_code(self, cr, uid, dept_code, context=None):
        code = ''
        year = time.strftime('%y')
        sequence = self.pool.get('ir.sequence').next_by_code(cr, uid, 'vhr.job.sequence') or "/"
        if sequence and sequence != "/":
            code = '%s-%s-%s' % (year, dept_code, str('%.4d' % int(sequence)))
        log.info('Code generate %s' % (code))
        return code

    def get_list_emp_cc_hr_job(self, cr, uid, job_id, context=None):
        job_obj = self.browse(cr, uid, job_id, context=context)
        lst_cc_email = []
        if job_obj.handle_by and job_obj.handle_by.resource_id and\
        job_obj.handle_by.resource_id.active:
            lst_cc_email.append(job_obj.handle_by.id)
        if job_obj.share_handle_by and job_obj.share_handle_by.resource_id and\
        job_obj.share_handle_by.resource_id.active:
            lst_cc_email.append(job_obj.share_handle_by.id)
        if job_obj.department_id and job_obj.department_id.hrbps:
            for item in job_obj.department_id.hrbps:
                if item.resource_id and item.resource_id.active:
                    lst_cc_email.append(item.id)
        if job_obj.department_id and job_obj.department_id.rams:
            for item in job_obj.department_id.rams:
                if item.resource_id and item.resource_id.active:
                    lst_cc_email.append(item.id)
        if job_obj.department_id and job_obj.department_id.ass_hrbps:
            for item in job_obj.department_id.ass_hrbps:
                if item.resource_id and item.resource_id.active:
                    lst_cc_email.append(item.id)
        return list(set(lst_cc_email))

    def get_list_emp_to_hr_job(self, cr, uid, job_id, context=None):
        job_obj = self.browse(cr, uid, job_id, context=context)
        lst_emp_send_cv = []
        if job_obj.requestor_id and job_obj.requestor_id.resource_id and\
        job_obj.requestor_id.resource_id.active:
            requestor_id = job_obj.requestor_id.id
            lst_emp_send_cv.append(requestor_id)
        if job_obj.report_to and job_obj.report_to.resource_id and\
        job_obj.report_to.resource_id.active:
            report_to = job_obj.report_to.id
            lst_emp_send_cv.append(report_to)
            
        if job_obj.department_id and job_obj.department_id.manager_id and\
        job_obj.department_id.manager_id.resource_id and \
        job_obj.department_id.manager_id.resource_id.active:
            manager_id = job_obj.department_id.manager_id.id
            lst_emp_send_cv.append(manager_id)
        return list(set(lst_emp_send_cv))
    
    def get_list_emp_to_survey_job(self, cr, uid, job_id, context=None):
        lst_emp_send_cv = []
        job_obj = self.browse(cr, uid, job_id, context=context)
        arg = [('job_id', '=', job_id), ('state', 'in', ['offer','done'])]
        job_app_obj = self.pool.get('vhr.job.applicant')
        job_app_ids = job_app_obj.search(cr, uid, arg, context=context)
        for job_app in job_app_obj.browse(cr, uid, job_app_ids, context=context):
            for interviewer1 in job_app.dept_interviewer1:
                if interviewer1:
                    lst_emp_send_cv.append(interviewer1.id)
            for interviewer2 in job_app.dept_interviewer2:
                if interviewer2:
                    lst_emp_send_cv.append(interviewer2.id)
            for interviewer3 in job_app.dept_interviewer3:
                if interviewer3:
                    lst_emp_send_cv.append(interviewer3.id)
        return list(set(lst_emp_send_cv))
    
    def get_list_emp_cc_survey_job(self, cr, uid, job_id, context=None):
        group_obj = self.pool.get('res.groups')
        employee_obj = self.pool.get('hr.employee')
        job_obj = self.browse(cr, uid, job_id, context=context)
        lst_cc_email = []
        if job_obj.handle_by and job_obj.handle_by.resource_id and\
        job_obj.handle_by.resource_id.active:
            lst_cc_email.append(job_obj.handle_by.id)
        if job_obj.department_id and job_obj.department_id.hrbps:
            for item in job_obj.department_id.hrbps:
                if item.resource_id and item.resource_id.active:
                    lst_cc_email.append(item.id)
        if job_obj.department_id and job_obj.department_id.rams:
            for item in job_obj.department_id.rams:
                if item.resource_id and item.resource_id.active:
                    lst_cc_email.append(item.id)
        lst_group_ids = group_obj.search(cr, uid, [('name','=', 'VHR RR Manager')], context=context)
        if lst_group_ids:
            group = group_obj.browse(cr, uid, lst_group_ids[0], context=context)
            if group:
                for user in group.users:
                    user_id = user.id
                    lst_employee_ids = employee_obj.search(cr, uid, [('user_id','=', user_id),('user_id','!=',1)], context=context)
                    for employee in employee_obj.browse(cr, uid, lst_employee_ids, context=context):
                        lst_cc_email.append(employee.id)
        return list(set(lst_cc_email))

    def get_list_job_from_interview(self, cr, uid, employee_id, ids):
        job_ids = []
        try:
            condition = ids and 'AND a.id in (%s)' % ','.join(map(str, filter(None, ids))) or 'AND False'
            sql ='''select  DISTINCT a.id  from hr_job a
                    INNER JOIN vhr_job_applicant  b on a.id = b.job_id
                    LEFT JOIN job_applicant_employee_rel c on b.id = c.job_applicant_id
                    WHERE (b.reporter1   = %s or b.reporter2 = %s
                           or b.reporter3 = %s or c.employee_id = %s) '''\
                           %(employee_id, employee_id,employee_id, employee_id)

            cr.execute(sql+condition)
            job_ids = map(lambda x: x[0], cr.fetchall())
        except Exception as e:
            log.exception(e)
        return job_ids

    def get_args(self, cr, uid, request, args):
        hr_obj = self.pool.get('hr.employee')
        current_emp = hr_obj.search(cr, uid, [('user_id.id', '=', uid)], context={'active_test': False})
        temp_args = args
        if current_emp:
            roles = self.recruitment_get_group_array(cr, uid, uid)
            if request == 'ADMIN':
                temp_args = args
            elif request == 'MY_REQUESTS':
                temp_args.append('|')
                temp_args.append(('create_uid', '=', uid))
                temp_args.append(('requestor_id', 'in', current_emp))
            elif request == 'MY_APPROVALS':
                temp_args.append('|')
                temp_args.append('|')
                temp_args.append('|')
                temp_args.append(('dept_head_approve', '=', uid))
                temp_args.append(('hrbp_approve', '=', uid))
                temp_args.append(('rrm_approve', '=', uid))
                temp_args.append('&')
                temp_args.append(('handle_by', '=', current_emp[0]))
                temp_args.append(('state', 'in', ['done', 'close', 'cancel']))
            elif request == 'MY_TASKS':
                if MANAGER in roles:
                    temp_args.append(('state', '!=', 'draft'))
                else:
                    # BinhNX: For recruiter same view as RRM but ass state in ['in_progress', 'done', 'close', 'cancel']
                    if RECRUITER in roles:
                        temp_args.append(('state', 'in', ['in_progress', 'done', 'close', 'cancel']))
                        return temp_args
                    temp_args.extend(['|', '|'])
                    temp_args_roles = []
                    # hrbp or hrbp ass
                    if HRBP in roles:
                        temp_args_roles.extend(['|'])
                        temp_args_roles.append('&')
                        lst_dept1 = self.get_department_hrbps(cr, uid, current_emp[0])
                        lst_dept2 = self.get_department_ass_hrbps(cr, uid, current_emp[0])
                        lst_dept1.extend(lst_dept2)
                        temp_args_roles.append(('department_id', 'in', lst_dept1))
                        temp_args_roles.append(('state', '!=', 'draft'))
                    if RRHRBP in roles:
                        temp_args_roles.extend(['|'])
                        temp_args_roles.append('&')
                        lst_dept_rr_hrbp = self.get_department_rr_hrbps(cr, uid, current_emp[0])
                        temp_args_roles.append(('department_id', 'in', lst_dept_rr_hrbp))
                        temp_args_roles.append(('state', '!=', 'draft'))
                    temp_args.extend(temp_args_roles)
                    # BinhNX: Remove just view handle and share handle by
                    # Keep this code for future, maybe user want to rollback.
                    # recruiter and share handle by
#                     if RECRUITER in roles:
#                         return temp_args
#                         temp_args_roles = ['|']+temp_args_roles
#                         temp_args_roles.append('|')
#                         temp_args_roles.append('&')
#                         temp_args_roles.append(('handle_by', '=', current_emp[0]))
#                         temp_args_roles.append(('state', 'in', ['in_progress', 'done', 'close', 'cancel']))
#                         temp_args_roles.append('&')
#                         temp_args_roles.append(('share_handle_by', '=', current_emp[0]))
#                         temp_args_roles.append(('state', 'in', ['in_progress', 'done', 'close', 'cancel']))

                    # depthead
                    temp_args.append('&')
                    temp_args.append(('department_id.manager_id', '=', current_emp[0]))
                    temp_args.append(('state', '!=', 'draft'))
                    # ram
                    lst_dept_ram = self.get_department_rams(cr, uid, current_emp[0])
                    temp_args.append('&')
                    temp_args.append(('department_id', 'in', lst_dept_ram))
                    temp_args.append(('state', '!=', 'draft'))
                    # delegate
                    lst_delegate = self.get_delegate_department(cr, uid, current_emp[0])
                    temp_args.append(('id', 'in', lst_delegate))
            else:
                if uid == 1 or ADMIN in roles or MANAGER in roles or CANDB_ROLE in roles or\
                    RECRUITER in roles or HRBP in roles or COLLABORATER in roles or COLLABORATER2 in roles or RRHRBP in roles:
                    return temp_args
                temp_args.extend(['|', '|', '|', '|', '|'])
                temp_args.append(('create_uid', '=', uid))
                temp_args.append(('requestor_id', 'in', current_emp))
                temp_args.append(('dept_head_approve', '=', uid))
                # depthead
                temp_args.append(('department_id.manager_id', '=', current_emp[0]))
                # ram
                lst_dept_ram = self.get_department_rams(cr, uid, current_emp[0])
                temp_args.append('&')
                temp_args.append(('department_id', 'in', lst_dept_ram))
                temp_args.append(('state', '!=', 'draft'))
                # delegate
                lst_delegate = self.get_delegate_department(cr, uid, current_emp[0])
                temp_args.append(('id', 'in', lst_delegate))
        return temp_args

    def get_url(self, cr, uid, res_id, context=None):
        if isinstance(res_id, list):
            res_id = res_id[0]
        model_data = self.pool.get('ir.model.data')
        parameter_obj = self.pool.get('ir.config_parameter')
        base_url = parameter_obj.get_param(cr, uid, 'web.base.url')
        action_id = model_data.xmlid_lookup(cr, uid, 'vhr_recruitment.action_vhr_resource_request_tasks')[2]
        url = '%s/web#id=%s&view_type=form&model=hr.job&action=%s' % (base_url, res_id, action_id)
        return url

    def modification_view_hrbp(self, cr, uid, dicti):
        if dicti.get('company', False):
            dicti['company'].extend(['waiting_hrbp'])
        else:
            dicti['company'] = ['waiting_hrbp']
        if dicti.get('job_title_id', False):
            dicti['job_title_id'].extend(['waiting_hrbp'])
        else:
            dicti['job_title_id'] = ['waiting_hrbp']
#         if dicti.get('job_level_id', False):
#             dicti['job_level_id'].extend(['waiting_hrbp'])
#         else:
#             dicti['job_level_id'] = ['waiting_hrbp']

#         if dicti.get('job_level_position_id', False):
#             dicti['job_level_position_id'].extend(['waiting_hrbp'])
#         else:
#             dicti['job_level_position_id'] = ['waiting_hrbp']

#         if dicti.get('sub_group_id', False):
#             dicti['sub_group_id'].extend(['waiting_hrbp'])
#         else:
#             dicti['sub_group_id'] = ['waiting_hrbp']
        if dicti.get('no_of_recruitment', False):
            dicti['no_of_recruitment'].extend(['waiting_hrbp'])
        else:
            dicti['no_of_recruitment'] = ['waiting_hrbp']
        if dicti.get('department_id', False):
            dicti['department_id'].extend(['waiting_hrbp'])
        else:
            dicti['department_id'] = ['waiting_hrbp']
        if dicti.get('gender', False):
            dicti['gender'].extend(['waiting_hrbp'])
        else:
            dicti['gender'] = ['waiting_hrbp']
        if dicti.get('degree_id', False):
            dicti['degree_id'].extend(['waiting_hrbp'])
        else:
            dicti['degree_id'] = ['waiting_hrbp']
        if dicti.get('reason_id', False):
            dicti['reason_id'].extend(['waiting_hrbp'])
        else:
            dicti['reason_id'] = ['waiting_hrbp']
        if dicti.get('office_id', False):
            dicti['office_id'].extend(['waiting_hrbp'])
        else:
            dicti['office_id'] = ['waiting_hrbp']
        if dicti.get('job_type_id', False):
            dicti['job_type_id'].extend(['waiting_hrbp'])
        else:
            dicti['job_type_id'] = ['waiting_hrbp']
        if dicti.get('in_budget', False):
            dicti['in_budget'].extend(['waiting_hrbp'])
        else:
            dicti['in_budget'] = ['waiting_hrbp']

#         if dicti.get('position_class_standard_ex', False):
#             dicti['position_class_standard_ex'].extend(['waiting_hrbp'])
#         else:
#             dicti['position_class_standard_ex'] = ['waiting_hrbp']

        if dicti.get('priority_1', False):
            dicti['priority_1'].extend(['waiting_hrbp'])
        else:
            dicti['priority_1'] = ['waiting_hrbp']
        if dicti.get('priority_2', False):
            dicti['priority_2'].extend(['waiting_hrbp'])
        else:
            dicti['priority_2'] = ['waiting_hrbp']
        if dicti.get('priority_3', False):
            dicti['priority_3'].extend(['waiting_hrbp'])
        else:
            dicti['priority_3'] = ['waiting_hrbp']
        if dicti.get('description', False):
            dicti['description'].extend(['waiting_hrbp'])
        else:
            dicti['description'] = ['waiting_hrbp']
        if dicti.get('requirements', False):
            dicti['requirements'].extend(['waiting_hrbp'])
        else:
            dicti['requirements'] = ['waiting_hrbp']
        if dicti.get('preference', False):
            dicti['preference'].extend(['waiting_hrbp'])
        else:
            dicti['preference'] = ['waiting_hrbp']
        if dicti.get('description_en', False):
            dicti['description_en'].extend(['waiting_hrbp'])
        else:
            dicti['description_en'] = ['waiting_hrbp']
        if dicti.get('requirement_en', False):
            dicti['requirement_en'].extend(['waiting_hrbp'])
        else:
            dicti['requirement_en'] = ['waiting_hrbp']
        if dicti.get('preference_en', False):
            dicti['preference_en'].extend(['waiting_hrbp'])
        else:
            dicti['preference_en'] = ['waiting_hrbp']
        if dicti.get('report_to', False):
            dicti['report_to'].extend(['waiting_hrbp'])
        else:
            dicti['report_to'] = ['waiting_hrbp']
        if dicti.get('change_headcount_comment', False):
            dicti['change_headcount_comment'].extend(['waiting_hrbp'])
        else:
            dicti['change_headcount_comment'] = ['waiting_hrbp']
        if dicti.get('reason_emp', False):
            dicti['reason_emp'].extend(['waiting_hrbp'])
        else:
            dicti['reason_emp'] = ['waiting_hrbp']

    def modification_view_rrm(self, cr, uid, doc, dicti):
        # 25/12/2014 : handle_by and share handle_by load nhan vien co role recruiter
        lst_recruiter = self.get_list_recruiter(cr, uid)
        domain = [('id', 'in', lst_recruiter)]
        for node in doc.xpath("//field[@name='handle_by']"):
            node.set('domain', json.dumps(domain))
        domain = [('id', 'in', lst_recruiter)]
        for node in doc.xpath("//field[@name='share_handle_by']"):
            node.set('domain', json.dumps(domain))

#         if dicti.get('position_class_standard_ex', False):
#             dicti['position_class_standard_ex'].extend(['waiting_rrm', 'in_progress'])
#         else:
#             dicti['position_class_standard_ex'] = ['waiting_rrm', 'in_progress']

        if dicti.get('priority_1', False):
            dicti['priority_1'].extend(['waiting_rrm', 'in_progress'])
        else:
            dicti['priority_1'] = ['waiting_rrm', 'in_progress']
        if dicti.get('priority_2', False):
            dicti['priority_2'].extend(['waiting_rrm', 'in_progress'])
        else:
            dicti['priority_2'] = ['waiting_rrm', 'in_progress']
        if dicti.get('priority_3', False):
            dicti['priority_3'].extend(['waiting_rrm', 'in_progress'])
        else:
            dicti['priority_3'] = ['waiting_rrm', 'in_progress']
        if dicti.get('handle_by', False):
            dicti['handle_by'].extend(['waiting_rrm', 'in_progress'])
        else:
            dicti['handle_by'] = ['waiting_rrm', 'in_progress']
        if dicti.get('business_impact_id', False):
            dicti['business_impact_id'].extend(['waiting_rrm', 'in_progress'])
        else:
            dicti['business_impact_id'] = ['waiting_rrm', 'in_progress']
        if dicti.get('difficult_level_id', False):
            dicti['difficult_level_id'].extend(['waiting_rrm', 'in_progress'])
        else:
            dicti['difficult_level_id'] = ['waiting_rrm', 'in_progress']
        if dicti.get('is_critical', False):
            dicti['is_critical'].extend(['waiting_rrm', 'in_progress'])
        else:
            dicti['is_critical'] = ['waiting_rrm', 'in_progress']
        if dicti.get('share_handle_by', False):
            dicti['share_handle_by'].extend(['waiting_rrm', 'in_progress'])
        else:
            dicti['share_handle_by'] = ['waiting_rrm', 'in_progress']
        if dicti.get('no_of_recruitment', False):
            dicti['no_of_recruitment'].extend(['waiting_rrm', 'in_progress'])
        else:
            dicti['no_of_recruitment'] = ['waiting_rrm', 'in_progress']

        if dicti.get('change_headcount_comment', False):
            dicti['change_headcount_comment'].extend(['waiting_rrm', 'in_progress'])
        else:
            dicti['change_headcount_comment'] = ['waiting_rrm', 'in_progress']

    def modification_view_rr_admin(self, cr, uid, dicti):
        # data cu user (aLong) muon sua lai priority
        if dicti.get('priority_1', False):
            dicti['priority_1'].extend(['waiting_rrm', 'in_progress', 'done', 'close', 'cancel'])
        else:
            dicti['priority_1'] = ['waiting_rrm', 'in_progress', 'done', 'close', 'cancel']
        if dicti.get('priority_2', False):
            dicti['priority_2'].extend(['waiting_rrm', 'in_progress', 'done', 'close', 'cancel'])
        else:
            dicti['priority_2'] = ['waiting_rrm', 'in_progress', 'done', 'close', 'cancel']
        if dicti.get('priority_3', False):
            dicti['priority_3'].extend(['waiting_rrm', 'in_progress', 'done', 'close', 'cancel'])
        else:
            dicti['priority_3'] = ['waiting_rrm', 'in_progress', 'done', 'close', 'cancel']

    def modification_view_recruiter(self, cr, uid, doc, dicti, context=None):
        # Cung quyen recruiter dung record handle or share handle
        hr_employee = self.pool.get('hr.employee')
        employee = hr_employee.search(cr, uid, [('user_id', '=', uid)], context={'active_test': False})
        emp = employee and employee[0] or 0
        domain = ['|', '|', ('show_finish_button', '=', 'DONE'), ('state', '!=', 'in_progress'), '&', ('handle_by', '!=', emp),
                  ('share_handle_by', '!=', emp)]
        for node in doc.xpath("//button[@code_execute='MATCHCV']"):
            node.set('modifiers', json.dumps({'invisible': domain}))

        domain = ['|', '|', '|', ('show_finish_button', '=', 'DONE'), ('state', '!=', 'in_progress'),('is_show_send_cv','=',False), '&', ('handle_by', '!=', emp),
                  ('share_handle_by', '!=', emp)]
        for node in doc.xpath("//button[@code_execute='SENDCV']"):
            node.set('modifiers', json.dumps({'invisible': domain}))

        domain = ['|', '|', ('show_finish_button', '!=', 'DONE'), ('state', '!=', 'in_progress'), '&', ('handle_by', '!=', emp),
                  ('share_handle_by', '!=', emp)]
        for node in doc.xpath("//button[@code_execute='DONE_INPROGRESS']"):
            node.set('modifiers', json.dumps({'invisible': domain}))

        domain = ['|', '|', ('show_finish_button', '!=', 'CANCEL'), ('state', '!=', 'in_progress'), '&', ('handle_by', '!=', emp),
                  ('share_handle_by', '!=', emp)]
        for node in doc.xpath("//button[@code_execute='CANCEL_INPROGRESS']"):
            node.set('modifiers', json.dumps({'invisible': domain}))

        domain = ['|', '|', ('show_finish_button', '!=', 'CLOSE'), ('state', '!=', 'in_progress'), '&', ('handle_by', '!=', emp),
                  ('share_handle_by', '!=', emp)]
        for node in doc.xpath("//button[@code_execute='CLOSE_INPROGRESS']"):
            node.set('modifiers', json.dumps({'invisible': domain}))

        domain = ['|', ('state', '!=', 'done'), '&', ('handle_by', '!=', emp), ('share_handle_by', '!=', emp)]
        for node in doc.xpath("//button[@code_execute='REOPEN']"):
            node.set('modifiers', json.dumps({'invisible': domain}))

        domain = ['|', ('state', 'not in', ['in_progress', 'done']), '&', ('handle_by', '!=', emp), ('share_handle_by', '!=', emp)]
        for node in doc.xpath("//button[@code_execute='POST_JOB']"):
            node.set('modifiers', json.dumps({'invisible': domain}))

        domain = ['&', ('handle_by', '!=', emp), ('share_handle_by', '!=', emp)]
        for node in doc.xpath("//field[@name='job_applicant_ids']"):
            node.set('modifiers', json.dumps({'readonly': domain}))
        for node in doc.xpath("//field[@name='dept_head_delay']"):
            node.set('modifiers', json.dumps({'readonly': domain}))

    def view_factory(self, cr, uid, doc, dicti, context=None):
        if context is None:
            context = {}
        if dicti.get('company', False):
            for node in doc.xpath("//field[@name='company']"):
                node.set('modifiers', json.dumps({'required': 'True', 'readonly': [('state', 'not in', list(set(dicti['company'])))]}))
        if dicti.get('job_title_id', False):
            for node in doc.xpath("//field[@name='job_title_id']"):
                node.set('modifiers', json.dumps({'required': 'True', 'readonly': [('state', 'not in', list(set(dicti['job_title_id'])))]}))
#         if dicti.get('job_level_id', False):
#             for node in doc.xpath("//field[@name='job_level_id']"):
#                 node.set('modifiers', json.dumps({'required': 'True', 'readonly': [('state', 'not in', list(set(dicti['job_level_id'])))]}))

#         if dicti.get('job_level_position_id', False):
#             for node in doc.xpath("//field[@name='job_level_position_id']"):
#                 node.set('modifiers', json.dumps({'required': [('state', 'in', list(set(dicti['job_level_position_id'])))], 'readonly': [('state', 'not in', list(set(dicti['job_level_position_id'])))]}))

#         if dicti.get('sub_group_id', False):
#             for node in doc.xpath("//field[@name='sub_group_id']"):
#                 node.set('modifiers', json.dumps({'required': 'True', 'readonly': [('state', 'not in', list(set(dicti['sub_group_id'])))]}))
        if dicti.get('no_of_recruitment', False):
            for node in doc.xpath("//field[@name='no_of_recruitment']"):
                node.set('modifiers', json.dumps({'required': 'True', 'readonly': [('state', 'not in', list(set(dicti['no_of_recruitment'])))]}))
        if dicti.get('department_id', False):
            for node in doc.xpath("//field[@name='department_id']"):
                node.set('modifiers', json.dumps({'required': 'True', 'readonly': [('state', 'not in', list(set(dicti['department_id'])))]}))
        if dicti.get('gender', False):
            for node in doc.xpath("//field[@name='gender']"):
                node.set('modifiers', json.dumps({'required': 'True', 'readonly': [('state', 'not in', list(set(dicti['gender'])))]}))
        if dicti.get('degree_id', False):
            for node in doc.xpath("//field[@name='degree_id']"):
                node.set('modifiers', json.dumps({'required': 'True', 'readonly': [('state', 'not in', list(set(dicti['degree_id'])))]}))
        if dicti.get('reason_id', False):
            for node in doc.xpath("//field[@name='reason_id']"):
                node.set('modifiers', json.dumps({'required': 'True', 'readonly': [('state', 'not in', list(set(dicti['reason_id'])))]}))
        if dicti.get('office_id', False):
            for node in doc.xpath("//field[@name='office_id']"):
                node.set('modifiers', json.dumps({'required': 'True', 'readonly': [('state', 'not in', list(set(dicti['office_id'])))]}))
        if dicti.get('job_type_id', False):
            for node in doc.xpath("//field[@name='job_type_id']"):
                node.set('modifiers', json.dumps({'required': 'True', 'readonly': [('state', 'not in', list(set(dicti['job_type_id'])))]}))
        if dicti.get('in_budget', False):
            for node in doc.xpath("//field[@name='in_budget']"):
                node.set('modifiers', json.dumps({'required': [('state', 'in', list(set(dicti['in_budget'])))],
                                                  'readonly': [('state', 'not in', list(set(dicti['in_budget'])))]}))
#         if dicti.get('position_class_standard_ex', False):
#             for node in doc.xpath("//field[@name='position_class_standard_ex']"):
#                 node.set('modifiers', json.dumps({'required': 'True', 'readonly': [('state', 'not in', list(set(dicti['position_class_standard_ex'])))]}))

        if dicti.get('report_to', False):
            for node in doc.xpath("//field[@name='report_to']"):
                node.set('modifiers', json.dumps({'required': 'True', 'readonly': [('state', 'not in', list(set(dicti['report_to'])))]}))
        if dicti.get('priority_1', False):
            for node in doc.xpath("//field[@name='priority_1']"):
                node.set('modifiers', json.dumps({'readonly': [('state', 'not in', list(set(dicti['priority_1'])))]}))
        if dicti.get('priority_2', False):
            for node in doc.xpath("//field[@name='priority_2']"):
                node.set('modifiers', json.dumps({'readonly': [('state', 'not in', list(set(dicti['priority_2'])))]}))
        if dicti.get('priority_3', False):
            for node in doc.xpath("//field[@name='priority_3']"):
                node.set('modifiers', json.dumps({'readonly': [('state', 'not in', list(set(dicti['priority_3'])))]}))
        if dicti.get('description', False):
            for node in doc.xpath("//field[@name='description']"):
                node.set('modifiers', json.dumps({'readonly': [('state', 'not in', list(set(dicti['description'])))]}))
        if dicti.get('requirements', False):
            for node in doc.xpath("//field[@name='requirements']"):
                node.set('modifiers', json.dumps({'readonly': [('state', 'not in', list(set(dicti['requirements'])))]}))
        if dicti.get('preference', False):
            for node in doc.xpath("//field[@name='preference']"):
                node.set('modifiers', json.dumps({'readonly': [('state', 'not in', list(set(dicti['preference'])))]}))
        if dicti.get('description_en', False):
            for node in doc.xpath("//field[@name='description_en']"):
                node.set('modifiers', json.dumps({'readonly': [('state', 'not in', list(set(dicti['description_en'])))]}))
        if dicti.get('requirement_en', False):
            for node in doc.xpath("//field[@name='requirement_en']"):
                node.set('modifiers', json.dumps({'readonly': [('state', 'not in', list(set(dicti['requirement_en'])))]}))
        if dicti.get('preference_en', False):
            for node in doc.xpath("//field[@name='preference_en']"):
                node.set('modifiers', json.dumps({'readonly': [('state', 'not in', list(set(dicti['preference_en'])))]}))
        if dicti.get('handle_by', False):
            for node in doc.xpath("//field[@name='handle_by']"):
                node.set('modifiers', json.dumps({'required': [('state', 'in', list(set(dicti['handle_by'])))],
                                                  'readonly': [('state', 'not in', list(set(dicti['handle_by'])))]}))
        if dicti.get('business_impact_id', False):
            for node in doc.xpath("//field[@name='business_impact_id']"):
                node.set('modifiers', json.dumps({'required': [('state', 'in', list(set(dicti['business_impact_id'])))],
                                                  'readonly': [('state', 'not in', list(set(dicti['business_impact_id'])))]}))
        if dicti.get('difficult_level_id', False):
            for node in doc.xpath("//field[@name='difficult_level_id']"):
                node.set('modifiers', json.dumps({'readonly': [('state', 'not in', list(set(dicti['difficult_level_id'])))]}))
        if dicti.get('is_critical', False):
            for node in doc.xpath("//field[@name='is_critical']"):
                node.set('modifiers', json.dumps({'readonly': [('state', 'not in', list(set(dicti['is_critical'])))]}))
        if dicti.get('share_handle_by', False):
            for node in doc.xpath("//field[@name='share_handle_by']"):
                node.set('modifiers', json.dumps({'readonly': [('state', 'not in', list(set(dicti['share_handle_by'])))]}))
        if dicti.get('change_headcount_comment', False):
            for node in doc.xpath("//field[@name='change_headcount_comment']"):
                lst_state = list(set(dicti['change_headcount_comment']))
                readonly = ['|', ('is_change_headcount', '=', False)] + [('state', 'not in', lst_state)]
                invisible = ['|', ('is_change_headcount', '=', False)] + [('state', 'not in', lst_state)]
                required = [('is_change_headcount', '=', True)]
                node.set('modifiers', json.dumps({'readonly': readonly, 'invisible': invisible, 'required': required}))
        if dicti.get('reason_emp', False):
            for node in doc.xpath("//field[@name='reason_emp']"):
                lst_state = list(set(dicti['reason_emp']))
                readonly = [('state', 'not in', lst_state)]
                invisible = [('reason_code','not in',['REPLACE','STAFF_MOVEMENT'])]
                required = [('reason_code','in',['REPLACE','STAFF_MOVEMENT'])]
                node.set('modifiers', json.dumps({'readonly': readonly, 'invisible': invisible, 'required': required}))

    def update_state_note(self, cr, uid, ids): # Update lai field state note khi hrbp reject
        try:
            if not isinstance(ids, list):
                ids = [ids]
            sql = '''update hr_job set state_note = 'draft' WHERE id in(
                        select id from hr_job
                        WHERE state_note = 'waiting_hrbp'
                        and id in (%s)
                        )'''%(','.join(str(e) for e in ids))

            cr.execute(sql)
        except Exception as e:
            log.exception(e)
        return True

    def workflow_for_hr_job(self, cr, uid):  # Xóa sau khi hết giai đoạn migrate data
        log.info('HR_JOB: Begin Create workflow')
        sql = """select id, trim(state) as state, trim(state_note) as state_note from hr_job
                where
                    (state not in ('done', 'close', 'cancel') and
                    state <> state_note) or
                    (state = 'draft' and state_note is NULL)
                order by id"""
        cr.execute(sql)
        res_trigger = cr.dictfetchall()
        for item in res_trigger:
            log.info(item)
            sql = """
                select sc.id
                from wkf_instance wkf join hr_job sc on sc.id = wkf.res_id
                where  sc.id = %s and wkf.res_type = 'hr.job' """ % (item['id'])
            cr.execute(sql)
            res = cr.dictfetchone()
            if not res:
                log.info('HR_JOB: %s' % (item))
                self.create_workflow(cr, uid, [item['id']])
            job_app_signal = [k for k, v in SIGNAL_TRIGGER.iteritems() if v['old_state'] == item['state'] and v['new_state'] == item['state_note']]
            if job_app_signal:
                log.info('Signal : %s' % (job_app_signal))
                self.signal_workflow(cr, uid, [item['id']], job_app_signal[0])
                if job_app_signal[0] in ['in_progress_close', 'in_progress_cancel', 'in_progress_done']:
                    sql_job = """update vhr_post_job set state = 'done' WHERE id in (
                                select DISTINCT id from vhr_post_job a
                                LEFT JOIN post_job_hr_job_rel b on a."id" = b.post_job_id
                                WHERE b.hr_job_id = %s)""" % (item['id'])
                    cr.execute(sql_job)
                    cr.commit()
            else:
                log.info('Can\'t search signal %s' % (item))
                if item['state_note'] in ('close', 'cancel') and item['state'] != 'done':
                    sql = """update hr_job set state = '%s' WHERE id = %s""" % (item['state_note'], item['id'])
                    sql_job = """update vhr_post_job set state = 'done' WHERE id in (
                                select DISTINCT id from vhr_post_job a
                                LEFT JOIN post_job_hr_job_rel b on a."id" = b.post_job_id
                                WHERE b.hr_job_id = %s)""" % (item['id'])
                    cr.execute(sql)
                    cr.execute(sql_job)
                    cr.commit()
                if item['state_note'] == 'in_progress':
                    job_app_signal = [k for k, v in SIGNAL_TRIGGER.iteritems() if v['old_state'] == item['state'] and v['new_state'] == 'waiting_rrm']
                    if job_app_signal:
                        log.info('Signal : %s' % (job_app_signal))
                        self.signal_workflow(cr, uid, [item['id']], job_app_signal[0])
                        self.signal_workflow(cr, uid, [item['id']], 'waiting_rrm_in_progress')
                if item['state_note'] == 'done':
                    if item['state'] != 'waiting_rrm':
                        job_app_signal = [k for k, v in SIGNAL_TRIGGER.iteritems() if v['old_state'] == item['state'] and v['new_state'] == 'waiting_rrm']
                        if job_app_signal:
                            log.info('Signal : %s' % (job_app_signal))
                            self.signal_workflow(cr, uid, [item['id']], job_app_signal[0])
                            self.signal_workflow(cr, uid, [item['id']], 'waiting_rrm_in_progress')
                            self.signal_workflow(cr, uid, [item['id']], 'in_progress_done')
                    else:
                        self.signal_workflow(cr, uid, [item['id']], 'waiting_rrm_in_progress')
                        self.signal_workflow(cr, uid, [item['id']], 'in_progress_done')
                    # close job -> close post job
                    sql_job = """update vhr_post_job set state = 'done' WHERE id in (
                                select DISTINCT id from vhr_post_job a
                                LEFT JOIN post_job_hr_job_rel b on a."id" = b.post_job_id
                                WHERE b.hr_job_id = %s)""" % (item['id'])
                    cr.execute(sql_job)
                    cr.commit()
        log.info('HR_JOB: End create workflow')
        return True
hr_job()
