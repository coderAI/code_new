# -*-coding:utf-8-*-
import logging
from openerp.osv import osv, fields
from openerp import SUPERUSER_ID
from vhr_recruitment_abstract import EMP_XML,COLLABORATOR_XML, RECRUITER_XML, ADMIN_XML, MANAGER_XML,\
ERP_XML,HRBP_XML, ASST_HRBP_XML, REPORT_XML, CB_XML, COLLABORATOR2_XML, RRHRBP_XML

view_security = {
            'vhr_recruitment.view_vhr_job_applicant_form':          [EMP_XML],
            'vhr_recruitment.view_vhr_job_applicant_search':        [EMP_XML],
            'vhr_recruitment.view_vhr_job_applicant_tree':          [EMP_XML],
            'vhr_recruitment.view_vhr_resource_request_tree':       [EMP_XML],
            'vhr_recruitment.view_vhr_resource_request_search':     [EMP_XML],
            'vhr_recruitment.view_vhr_resource_request_form':       [EMP_XML],
            'vhr_recruitment.view_vhr_job_submit_form':             [EMP_XML],
            'vhr_recruitment.view_vhr_applicant_search':            [EMP_XML],
            'vhr_recruitment.view_vhr_applicant_tree':              [EMP_XML],
            'vhr_recruitment.view_vhr_applicant_form':              [EMP_XML],
            'vhr_recruitment.vhr_rr_talent_award_tree_view':        [EMP_XML],
            'vhr_recruitment.vhr_rr_talent_recom_tree_view':        [EMP_XML],
            'vhr_recruitment.vhr_rr_talent_communi_tree_view':      [EMP_XML],
            'vhr_recruitment.view_vhr_cv_attachment_tree':          [EMP_XML],
            'vhr_recruitment.view_vhr_job_applicant_close_form':    [EMP_XML],
            'vhr_master_data.view_vhr_job_title_search':            [EMP_XML],
            'vhr_master_data.view_vhr_company_search':              [EMP_XML],
            'vhr_master_data.view_vhr_state_change_tree':           [EMP_XML],
            'vhr_master_data.view_vhr_certificate_level_search':    [EMP_XML],
            'vhr_master_data.view_vhr_certificate_level_tree':      [EMP_XML],
            'vhr_master_data.view_vhr_office_search':               [EMP_XML],
            'vhr_master_data.view_vhr_office_tree':                 [EMP_XML],
            'vhr_master_data.view_vhr_state_change_form':           [EMP_XML],
            'vhr_master_data.view_vhr_working_background_form':     [EMP_XML],
            'vhr_master_data.view_vhr_certificate_info_form':       [EMP_XML],
            'vhr_recruitment.vhr_rr_talent_communi_form_view':      [EMP_XML],
            'vhr_recruitment.vhr_rr_talent_recom_form_view':        [EMP_XML],
            'vhr_recruitment.vhr_rr_talent_award_form_view':        [EMP_XML],
            'vhr_master_data.view_vhr_job_title_tree':              [EMP_XML],
            'vhr_master_data.view_vhr_job_level_search':            [EMP_XML],
        
            'hr.view_employee_filter':                              [EMP_XML],
            'hr.view_employee_tree':                                [EMP_XML],
            'hr.view_department_filter':                            [EMP_XML],
            'hr.view_department_tree':                              [EMP_XML],
            'hr.view_hr_job_form':                                  [EMP_XML],
            'hr.view_job_filter':                                   [EMP_XML],
            'hr_recruitment.crm_case_form_view_job':                [EMP_XML],
            'hr_recruitment.view_crm_case_jobs_filter':             [EMP_XML],
        
            'website.http_error':                                   [EMP_XML],
            'website.layout':                                       [EMP_XML],
            'website.assets_frontend':                              [EMP_XML],
            'website.theme':                                        [EMP_XML],
            'website.submenu':                                      [EMP_XML],
        
            'vhr_mysite.personal':                                  [EMP_XML],
            'vhr_mysite.lookup':                                    [EMP_XML],
        
            'survey.notopen':                                       [EMP_XML],
        
            'web.assets_common':                                    [EMP_XML],
            'web.assets_backend':                                   [EMP_XML],
            'web.jqueryui_conflict':                                [EMP_XML],
        
            'vhr_master_data.view_vhr_dimension_tree':              [COLLABORATOR_XML, RECRUITER_XML, COLLABORATOR2_XML, RRHRBP_XML],
            'vhr_recruitment.view_vhr_cv_attachment_search':        [COLLABORATOR_XML, RECRUITER_XML, COLLABORATOR2_XML, RRHRBP_XML],
            'vhr_recruitment.view_vhr_cv_attachment_form':          [COLLABORATOR_XML, RECRUITER_XML, COLLABORATOR2_XML, RRHRBP_XML],
            'vhr_recruitment.view_search_cvonline_filter':          [COLLABORATOR_XML, RECRUITER_XML, COLLABORATOR2_XML, RRHRBP_XML],
            'vhr_recruitment.view_vhr_temp_applicant_cv_tree':      [COLLABORATOR_XML, RECRUITER_XML, COLLABORATOR2_XML, RRHRBP_XML],
            'vhr_recruitment.view_vhr_temp_applicant_cv_form':      [COLLABORATOR_XML, RECRUITER_XML, COLLABORATOR2_XML, RRHRBP_XML],
            'vhr_recruitment.view_search_fresher_filter':           [COLLABORATOR_XML, RECRUITER_XML, COLLABORATOR2_XML, RRHRBP_XML],
            'vhr_recruitment.view_vhr_temp_applicant_fresher_tree': [COLLABORATOR_XML, RECRUITER_XML, COLLABORATOR2_XML, RRHRBP_XML],
            'vhr_recruitment.view_vhr_temp_applicant_fresher_form': [COLLABORATOR_XML, RECRUITER_XML, COLLABORATOR2_XML, RRHRBP_XML],
            'vhr_recruitment.view_vhr_candidate_test_result_tree':  [COLLABORATOR_XML, RECRUITER_XML, COLLABORATOR2_XML, RRHRBP_XML],
            'vhr_recruitment.view_search_internship_filter':        [COLLABORATOR_XML, RECRUITER_XML, COLLABORATOR2_XML, RRHRBP_XML],
            'vhr_recruitment.view_vhr_rr_talentform':               [COLLABORATOR_XML, RECRUITER_XML, COLLABORATOR2_XML, RRHRBP_XML],
            'vhr_recruitment.view_vhr_program_event_form':          [COLLABORATOR_XML, RECRUITER_XML, COLLABORATOR2_XML, RRHRBP_XML],
            'vhr_recruitment.view_vhr_candidate_test_result_form':  [COLLABORATOR_XML, RECRUITER_XML, COLLABORATOR2_XML, RRHRBP_XML],
            'vhr_recruitment.view_vhr_temp_applicant_internship_tree':    [COLLABORATOR_XML, RECRUITER_XML, COLLABORATOR2_XML, RRHRBP_XML],
            'vhr_recruitment.view_vhr_temp_applicant_internship_form':    [COLLABORATOR_XML, RECRUITER_XML, COLLABORATOR2_XML, RRHRBP_XML],
            'vhr_recruitment.view_search_tour_filter':                    [COLLABORATOR_XML, RECRUITER_XML, COLLABORATOR2_XML, RRHRBP_XML],
            'vhr_recruitment.view_vhr_temp_applicant_tour_form':          [COLLABORATOR_XML, RECRUITER_XML, COLLABORATOR2_XML, RRHRBP_XML],
            'vhr_recruitment.view_vhr_temp_applicant_tour_tree':          [COLLABORATOR_XML, RECRUITER_XML, COLLABORATOR2_XML, RRHRBP_XML],
            'vhr_recruitment.view_vhr_temp_applicant_seminar_filter':     [COLLABORATOR_XML, RECRUITER_XML, COLLABORATOR2_XML, RRHRBP_XML],
            'vhr_recruitment.view_vhr_temp_applicant_seminar_form':       [COLLABORATOR_XML, RECRUITER_XML, COLLABORATOR2_XML, RRHRBP_XML],
            'vhr_recruitment.view_vhr_temp_applicant_seminar_tree':       [COLLABORATOR_XML, RECRUITER_XML, COLLABORATOR2_XML, RRHRBP_XML],
            
            'vhr_recruitment.view_vhr_temp_applicant_student_search':     [COLLABORATOR_XML, RECRUITER_XML, COLLABORATOR2_XML, RRHRBP_XML],
            'vhr_recruitment.view_vhr_temp_applicant_student_form':       [COLLABORATOR_XML, RECRUITER_XML, COLLABORATOR2_XML, RRHRBP_XML],
            'vhr_recruitment.view_vhr_temp_applicant_student_tree':       [COLLABORATOR_XML, RECRUITER_XML, COLLABORATOR2_XML, RRHRBP_XML],
            
            'vhr_recruitment.view_vhr_rr_key_student_search':             [COLLABORATOR_XML, RECRUITER_XML, COLLABORATOR2_XML, RRHRBP_XML],
            'vhr_recruitment.view_vhr_rr_key_student_tree':               [COLLABORATOR_XML, RECRUITER_XML, COLLABORATOR2_XML, RRHRBP_XML],
            'vhr_recruitment.view_vhr_rr_key_student_form':               [COLLABORATOR_XML, RECRUITER_XML, COLLABORATOR2_XML, RRHRBP_XML],
            'vhr_recruitment.view_vhr_rr_talent_search':                  [COLLABORATOR_XML, RECRUITER_XML, COLLABORATOR2_XML, RRHRBP_XML],
            'vhr_recruitment.view_vhr_rr_talent_tree':                    [COLLABORATOR_XML, RECRUITER_XML, COLLABORATOR2_XML, RRHRBP_XML],
            'vhr_recruitment.view_email_news_filter':                     [COLLABORATOR_XML, RECRUITER_XML, COLLABORATOR2_XML, RRHRBP_XML],
            'vhr_recruitment.view_vhr_vhr_program_tree':                  [COLLABORATOR_XML, RECRUITER_XML, COLLABORATOR2_XML, RRHRBP_XML],
            'vhr_recruitment.view_email_news_form':                       [COLLABORATOR_XML, RECRUITER_XML, COLLABORATOR2_XML, RRHRBP_XML],
            'vhr_recruitment.view_vhr_program_event_search':              [COLLABORATOR_XML, RECRUITER_XML, COLLABORATOR2_XML, RRHRBP_XML],
            'vhr_recruitment.view_vhr_program_event_tree':                [COLLABORATOR_XML, RECRUITER_XML, COLLABORATOR2_XML, RRHRBP_XML],
            'vhr_recruitment.vhr_program_part_tree_view':                 [COLLABORATOR_XML, RECRUITER_XML, COLLABORATOR2_XML, RRHRBP_XML],
            'vhr_recruitment.view_vhr_program_question_tree':             [COLLABORATOR_XML, RECRUITER_XML, COLLABORATOR2_XML, RRHRBP_XML],
            'vhr_recruitment.vhr_program_field_tree_view':                [COLLABORATOR_XML, RECRUITER_XML, COLLABORATOR2_XML, RRHRBP_XML],
            'vhr_recruitment.view_vhr_recruitment_source_online_form':    [COLLABORATOR_XML, RECRUITER_XML, COLLABORATOR2_XML, RRHRBP_XML],
            'vhr_recruitment.vhr_program_field_form_view':                [COLLABORATOR_XML, RECRUITER_XML, COLLABORATOR2_XML, RRHRBP_XML],
            'vhr_recruitment.vhr_program_part_form_view':                 [COLLABORATOR_XML, RECRUITER_XML, COLLABORATOR2_XML, RRHRBP_XML],
            'vhr_recruitment.view_vhr_program_question_form':             [COLLABORATOR_XML, RECRUITER_XML, COLLABORATOR2_XML, RRHRBP_XML],
            'vhr_recruitment.view_vhr_program_answer_tree':               [COLLABORATOR_XML, RECRUITER_XML, COLLABORATOR2_XML, RRHRBP_XML],
            'vhr_recruitment.view_vhr_post_job_search':                   [COLLABORATOR_XML, RECRUITER_XML, COLLABORATOR2_XML, RRHRBP_XML],
            'vhr_recruitment.view_vhr_post_job_form':                     [COLLABORATOR_XML, RECRUITER_XML, COLLABORATOR2_XML, RRHRBP_XML],
            'vhr_recruitment.view_vhr_post_location_tree':                [COLLABORATOR_XML, RECRUITER_XML, COLLABORATOR2_XML, RRHRBP_XML],
            'vhr_recruitment.view_vhr_post_location_form':                [COLLABORATOR_XML, RECRUITER_XML, COLLABORATOR2_XML, RRHRBP_XML],
            'vhr_recruitment.view_vhr_rr_send_multi_cvs_hr_job':          [COLLABORATOR_XML, RECRUITER_XML, COLLABORATOR2_XML, RRHRBP_XML],
            'pentaho_reports.wiz_pentaho_report_prompt':                  [COLLABORATOR_XML, RECRUITER_XML, HRBP_XML, ASST_HRBP_XML, COLLABORATOR2_XML, RRHRBP_XML],
        
            'vhr_recruitment.view_vhr_erp_bonus_payment_tree':            [ADMIN_XML, ERP_XML],
            'vhr_recruitment.view_vhr_erp_bonus_payment_search':          [ADMIN_XML, ERP_XML],
            'vhr_recruitment.view_vhr_erp_bonus_payment_form':            [ADMIN_XML, ERP_XML],
            'vhr_recruitment.view_vhr_erp_bonus_scheme_tree':             [ADMIN_XML, ERP_XML],
            'vhr_recruitment.view_vhr_erp_bonus_scheme_search':           [ADMIN_XML, ERP_XML],
            'vhr_recruitment.view_vhr_erp_bonus_scheme_form':             [ADMIN_XML, ERP_XML],
            'vhr_recruitment.view_vhr_erp_bonus_rate_by_dept_tree':       [ADMIN_XML, ERP_XML],
            'vhr_recruitment.view_vhr_erp_bonus_rate_by_dept_form':       [ADMIN_XML, ERP_XML],
            'vhr_recruitment.view_vhr_erp_payment_time_tree':             [ADMIN_XML, ERP_XML],
            'vhr_recruitment.view_vhr_erp_payment_time_search':           [ADMIN_XML, ERP_XML],
            'vhr_recruitment.view_vhr_erp_payment_time_form':             [ADMIN_XML, ERP_XML],
            'vhr_recruitment.view_vhr_erp_bonus_exclusion_tree':          [ADMIN_XML, ERP_XML],
            'vhr_recruitment.view_vhr_erp_bonus_exclusion_search':        [ADMIN_XML, ERP_XML],
            'vhr_recruitment.view_vhr_erp_bonus_exclusion_form':          [ADMIN_XML, ERP_XML],
            'vhr_recruitment.view_vhr_erp_bonus_payment_line_tree':       [ADMIN_XML, ERP_XML],
            'vhr_recruitment.view_vhr_erp_bonus_payment_line_search':     [ADMIN_XML, ERP_XML],
            'vhr_recruitment.view_vhr_erp_bonus_payment_line_form':       [ADMIN_XML, ERP_XML],
            
            'vhr_recruitment.view_vhr_recruitment_wizard_update_payment': [ADMIN_XML, ERP_XML],
            
            'vhr_common.view_vhr_import_status_search':                   [ADMIN_XML, MANAGER_XML],
            'vhr_common.view_vhr_import_status_tree':                     [ADMIN_XML, MANAGER_XML],
            'vhr_common.view_vhr_import_status_form':                     [ADMIN_XML, MANAGER_XML],
        
            'base.view_groups_search':                                    [ADMIN_XML, MANAGER_XML],
            'base.view_users_search':                                     [ADMIN_XML, MANAGER_XML],
            'base.view_users_tree':                                       [ADMIN_XML, MANAGER_XML],
        
            'audittrail.view_audittrail_log_search':                      [ADMIN_XML, MANAGER_XML],
            'audittrail.view_audittrail_log_tree':                        [ADMIN_XML, MANAGER_XML],
            'audittrail.view_audittrail_log_form':                        [ADMIN_XML, MANAGER_XML],
        
            'hr.view_department_form':                                    [ADMIN_XML, MANAGER_XML],
        
            'vhr_master_data.view_vhr_dimension_search':                  [ADMIN_XML, MANAGER_XML],
            'vhr_master_data.view_vhr_dimension_form':                    [ADMIN_XML, MANAGER_XML],
            'vhr_master_data.view_vhr_job_category_tree':                 [ADMIN_XML, MANAGER_XML],
            'vhr_master_data.view_vhr_job_category_search':               [ADMIN_XML, MANAGER_XML],
            'vhr_master_data.view_vhr_job_category_form':                 [ADMIN_XML, MANAGER_XML],
            'vhr_master_data.view_vhr_job_tree':                          [ADMIN_XML, MANAGER_XML],
            'vhr_master_data.view_vhr_job_search':                        [ADMIN_XML, MANAGER_XML],
            'vhr_master_data.view_vhr_job_form':                          [ADMIN_XML, MANAGER_XML],
            'vhr_master_data.view_vhr_school_tree':                       [ADMIN_XML, MANAGER_XML],
            'vhr_master_data.view_vhr_school_form':                       [ADMIN_XML, MANAGER_XML],
            'vhr_master_data.view_vhr_school_search':                     [ADMIN_XML, MANAGER_XML],
            'vhr_master_data.view_vhr_certificate_level_form':            [ADMIN_XML, MANAGER_XML],
            'vhr_master_data.view_hr_recruitment_degree_search':          [ADMIN_XML, MANAGER_XML],
            'vhr_master_data.view_hr_recruitment_degree_tree':            [ADMIN_XML, MANAGER_XML],
            'vhr_master_data.view_vhr_recruitment_degree_form':           [ADMIN_XML, MANAGER_XML],
            'vhr_master_data.view_vhr_self_development_tree':             [ADMIN_XML, MANAGER_XML],
            'vhr_master_data.view_vhr_self_development_form':             [ADMIN_XML, MANAGER_XML],
            'vhr_master_data.view_vhr_self_development_search':           [ADMIN_XML, MANAGER_XML],
            'vhr_master_data.view_hr_department_tree':                    [ADMIN_XML, MANAGER_XML],
            'vhr_master_data.view_hr_department_search':                  [ADMIN_XML, MANAGER_XML],
            'vhr_master_data.view_vhr_recruitment_source_type_tree':      [ADMIN_XML, MANAGER_XML],
            'vhr_master_data.view_vhr_recruitment_source_type_form':      [ADMIN_XML, MANAGER_XML],
            'vhr_master_data.view_vhr_recruitment_source_type_search':    [ADMIN_XML, MANAGER_XML],
            'vhr_master_data.view_hr_recruitment_source_tree':            [ADMIN_XML, MANAGER_XML],
            'vhr_master_data.view_hr_recruitment_source_form':            [ADMIN_XML, MANAGER_XML],
            'vhr_master_data.view_hr_recruitment_source_search':          [ADMIN_XML, MANAGER_XML],
            'vhr_master_data.view_vhr_equipment_tree':                    [ADMIN_XML, MANAGER_XML],
            'vhr_master_data.view_vhr_equipment_search':                  [ADMIN_XML, MANAGER_XML],
            'vhr_master_data.view_vhr_room_tree':                         [ADMIN_XML, MANAGER_XML],
            'vhr_master_data.view_vhr_room_search':                       [ADMIN_XML, MANAGER_XML],
            'vhr_master_data.view_vhr_room_form':                         [ADMIN_XML, MANAGER_XML],
            'vhr_master_data.view_vhr_working_background_tree':           [ADMIN_XML, MANAGER_XML],
            'vhr_master_data.view_vhr_working_background_search':         [ADMIN_XML, MANAGER_XML],
            'vhr_master_data.view_vhr_task_type_tree':                    [ADMIN_XML, MANAGER_XML],
            'vhr_master_data.view_vhr_task_type_search':                  [ADMIN_XML, MANAGER_XML],
            'vhr_master_data.view_vhr_task_type_form':                    [ADMIN_XML, MANAGER_XML],
        
            'hr_recruitment.hr_recruitment_source_form':                  [ADMIN_XML, MANAGER_XML],
        
            'vhr_recruitment.vhr_rr_talent_expertise_tree_view':          [ADMIN_XML, MANAGER_XML],
            'vhr_recruitment.vhr_rr_talent_expertise_search_view':        [ADMIN_XML, MANAGER_XML],
            'vhr_recruitment.vhr_rr_talent_expertise_form_view':          [ADMIN_XML, MANAGER_XML],
            'vhr_recruitment.vhr_rr_com_channel_tree_view':               [ADMIN_XML, MANAGER_XML],
            'vhr_recruitment.vhr_rr_com_channel_search_view':             [ADMIN_XML, MANAGER_XML],
            'vhr_recruitment.vhr_rr_com_channel_form_view':               [ADMIN_XML, MANAGER_XML],
            'vhr_recruitment.vhr_rr_recom_rel_type_tree_view':            [ADMIN_XML, MANAGER_XML],
            'vhr_recruitment.vhr_rr_recom_rel_type_search_view':          [ADMIN_XML, MANAGER_XML],
            'vhr_recruitment.vhr_rr_recom_rel_type_form_view':            [ADMIN_XML, MANAGER_XML],
            'vhr_recruitment.view_vhr_dimension_search':                  [ADMIN_XML, MANAGER_XML, CB_XML],
            'vhr_recruitment.view_dimension_is_public_tree':              [ADMIN_XML, MANAGER_XML],
            'vhr_recruitment.view_dimension_is_public_form':              [ADMIN_XML, MANAGER_XML],
            'vhr_recruitment.view_vhr_recruitment_source_online_tree':    [ADMIN_XML, MANAGER_XML],
            'vhr_recruitment.view_vhr_recruitment_source_online_search':  [ADMIN_XML, MANAGER_XML],
            'vhr_recruitment.view_vhr_delegate_by_depart_search':         [ADMIN_XML, MANAGER_XML],
            'vhr_recruitment.view_vhr_delegate_by_depart_tree':           [ADMIN_XML, MANAGER_XML],
            'vhr_recruitment.view_vhr_close_reason_tree':                 [ADMIN_XML, MANAGER_XML],
            'vhr_recruitment.view_vhr_close_reason_search':               [ADMIN_XML, MANAGER_XML],
            'vhr_recruitment.view_vhr_delegate_by_depart_form':           [ADMIN_XML, MANAGER_XML],
            'vhr_recruitment.view_vhr_evaluation_tree':                   [ADMIN_XML, MANAGER_XML],
            'vhr_recruitment.view_vhr_evaluation_search':                 [ADMIN_XML, MANAGER_XML],
            'vhr_recruitment.view_vhr_evaluation_form':                   [ADMIN_XML, MANAGER_XML],
            'vhr_recruitment.view_vhr_applicant_category':                [ADMIN_XML, MANAGER_XML],
            'vhr_recruitment.view_typical_face_search':                   [ADMIN_XML, MANAGER_XML],
            'vhr_recruitment.view_vhr_typical_face_tree':                 [ADMIN_XML, MANAGER_XML],
            'vhr_recruitment.view_typical_face_form':                     [ADMIN_XML, MANAGER_XML],
            'vhr_recruitment.view_dimension_friendly_tree':               [ADMIN_XML, MANAGER_XML],
            'vhr_recruitment.view_dimension_friendly_form':               [ADMIN_XML, MANAGER_XML],
            'vhr_recruitment.vhr_program_recruitment_tree_view':          [ADMIN_XML, MANAGER_XML],
            'vhr_recruitment.vhr_program_recruitment_search_view':        [ADMIN_XML, MANAGER_XML],
            'vhr_recruitment.vhr_program_recruitment_form_view':          [ADMIN_XML, MANAGER_XML],
            'vhr_recruitment.vhr_program_content_tree_view':              [ADMIN_XML, MANAGER_XML],
            'vhr_recruitment.vhr_program_content_form_view':              [ADMIN_XML, MANAGER_XML],
            'vhr_recruitment.vhr_program_field_form_search':              [ADMIN_XML, MANAGER_XML],
            'vhr_recruitment.view_vhr_import_status_key_student':         [ADMIN_XML, MANAGER_XML],
            'vhr_recruitment.view_vhr_import_status_talent':              [ADMIN_XML, MANAGER_XML],
            'vhr_recruitment.view_vhr_recruitment_res_groups_tree':       [ADMIN_XML, MANAGER_XML],
            'vhr_recruitment.view_vhr_recruitment_res_groups_form':       [ADMIN_XML, MANAGER_XML],
            'vhr_recruitment.view_vhr_post_job_tree':                     [ADMIN_XML, MANAGER_XML],
            'vhr_recruitment.view_vhr_close_reason_form':                 [ADMIN_XML, MANAGER_XML],

            'vhr_recruitment.vhr_transfer_remind_view_form1':             [ADMIN_XML, MANAGER_XML],
            'vhr_recruitment.vhr_transfer_remind_view':                   [EMP_XML],
        }
    
_logger = logging.getLogger(__name__)

class ir_ui_view(osv.osv):
    _inherit = 'ir.ui.view'
    
    def init(self, cr):
        _logger.info('Start add security for view')
        try:
            ROLES = {EMP_XML: self.xmlid_lookup(cr, SUPERUSER_ID, EMP_XML),
                    COLLABORATOR_XML: self.xmlid_lookup(cr, SUPERUSER_ID, COLLABORATOR_XML),
                    RECRUITER_XML:  self.xmlid_lookup(cr, SUPERUSER_ID, RECRUITER_XML),
                    ADMIN_XML:  self.xmlid_lookup(cr, SUPERUSER_ID, ADMIN_XML),
                    MANAGER_XML:  self.xmlid_lookup(cr, SUPERUSER_ID, MANAGER_XML),
                    ERP_XML:  self.xmlid_lookup(cr, SUPERUSER_ID, ERP_XML),
                    HRBP_XML:  self.xmlid_lookup(cr, SUPERUSER_ID, HRBP_XML),
                    ASST_HRBP_XML:  self.xmlid_lookup(cr, SUPERUSER_ID, ASST_HRBP_XML),
                    REPORT_XML:  self.xmlid_lookup(cr, SUPERUSER_ID, REPORT_XML),
                    CB_XML:  self.xmlid_lookup(cr, SUPERUSER_ID, CB_XML),
                    COLLABORATOR2_XML: self.xmlid_lookup(cr, SUPERUSER_ID, COLLABORATOR2_XML),
                    RRHRBP_XML: self.xmlid_lookup(cr, SUPERUSER_ID, RRHRBP_XML)}
            
            for k, v in view_security.iteritems():
                view_id = self.xmlid_lookup(cr, SUPERUSER_ID, k)
                lst_roles = []
                if view_id:
                    for item in v:
                        role_id = ROLES.get(item, False)
                        if role_id:
                            lst_roles.append(role_id)
                    groups = self.read(cr, SUPERUSER_ID, view_id, ['groups_id'])
                    groups_id = groups.get('groups_id', [])
                    if lst_roles:
                        lst_roles = list( set(lst_roles).difference(set(groups_id)))
                        if lst_roles:
                            lst_roles.extend(groups_id)
                            self.write(cr, SUPERUSER_ID, view_id, {'groups_id' : [(6, 0, list(set(lst_roles)))]})
                    
        except Exception as e:
            _logger.info(e)
        _logger.info('End add security for view')
        return True
    
    def xmlid_lookup(self, cr, uid, XML_ID):
        try:
            model_data = self.pool.get('ir.model.data')
            result = model_data.xmlid_lookup(cr, uid, XML_ID)
            return result[2]
        except Exception as e:
            _logger.info(e)
        return False
ir_ui_view()
