# -*- encoding: utf-8 -*-

{
    "name": "HRS Recruitment Management",
    "version": "1.0",
    "author": "MIS",
    "category": "VHR",
    'sequence': 19,
    'summary': 'HRS Recruitment Management',
    "depends": [
        "vhr_master_data",
        "vhr_human_resource",
    ],
    "description": "",
    "init_xml": [],
    "demo_xml": [],
    "data": [
        #data
        'data/data_vhr_erp_level.xml',
        'data/data_dimension_type.xml',
        'data/data_dimension.xml',
        'data/data_ir_config_parameter.xml',
        'data/data_vhr_program_recruitment.xml',
        'data/data_vhr_program_content.xml',
        'data/data_vhr_sequence.xml',
        'data/data_ir_actions_report.xml',
        'data/data_vhr_program_field.xml',
        'data/data_vhr_erp.xml',
        'data/data_vhr_evaluation.xml',
        'data/data_vhr_post_location.xml',
        'data/data_ir_sequence.xml',
        'data/data_vhr_rr_com_channel.xml',
        'data/data_vhr_transfer_remind.xml',
        'data/data_ir_attachment.xml',
        'data/data_vhr_business_impact.xml',

        #view
        'view/vhr_erp_level_view.xml',
        'view/vhr_erp_bonus_scheme_match.xml',
        'view/vhr_recruitment.xml',
        'security/vhr_recruitment_security.xml',
        'security/ir.model.access.csv',
        'view/vhr_test_result.xml',
        'view/hr_job.xml',
        'view/vhr_applicant.xml',   
        'view/vhr_cv_attachment.xml',
        'view/hr_recruitment_stage.xml',
        'view/vhr_temp_applicant.xml',
        'view/vhr_job_applicant.xml',
        'view/vhr_evaluation.xml',
        'view/vhr_interview_round_evaluation.xml',
        'view/vhr_program_event.xml',
        'view/vhr_email_news.xml',
        'view/vhr_typical_face.xml',
        'view/vhr_post_job.xml',
        'view/vhr_event_job_view.xml',
        'view/vhr_post_location.xml',
        'view/vhr_dimension_view.xml',
        'view/vhr_send_multi_cvs.xml',
        'view/vhr_close_reason_view.xml',
        'view/hr_contract.xml',
        'view/hr_employee.xml',
        'view/vhr_working_record.xml',
        'view/vhr_recruitment_source_online.xml',
        'view/vhr_delegate_by_depart.xml',
        'view/hr_applicant_category.xml',
        'view/vhr_transfer_remind_view.xml',
        'view/vhr_business_impact_view.xml',
        # Program
        'view/vhr_program_question.xml',
        'view/vhr_program_answer.xml',
        'view/vhr_candidate_test_result.xml',      
        'view/vhr_program_recruitment.xml',
        'view/vhr_program_content.xml',
        'view/vhr_program_field.xml',
        'view/vhr_program_part.xml',
        'view/vhr_rr_key_student.xml',
        'view/vhr_rr_talent.xml',
        'view/vhr_import_status.xml',
        'view/vhr_recruitment_wizard.xml',
        'view/vhr_program_event_gift.xml',
        # Student
        'view/vhr_student_view.xml',
        #ERP    
        'view/vhr_erp_bonus_exclusion.xml',
        'view/vhr_erp_bonus_payment.xml',
        'view/vhr_erp_bonus_rate_by_dept.xml',
        'view/vhr_erp_bonus_scheme.xml',
        'view/vhr_erp_payment_time.xml',
        'view/vhr_erp_bonus_payment_line.xml', 
        'view/vhr_erp_exclusion_department_line.xml',       
        
        #System
        'view/res_group.xml',
        'view/email_template.xml',
        'view/ir_config_parameter.xml',
        
        # Talent pool
        'view/vhr_rr_com_channel.xml',
        'view/vhr_rr_recom_rel_type.xml',
        'view/vhr_rr_talent_award.xml',
        'view/vhr_rr_talent_communi.xml',
        'view/vhr_rr_talent_expertise.xml',
        'view/vhr_rr_talent_recom.xml',
        
        #school
         'view/vhr_school_view.xml',
         
         # Recommender CV
         'view/vhr_rr_reccommender_cv.xml',
         'security/view/security_vhr_rr_recommeder_cv_view.xml',
        
         #Survey
        'data/data_vhr_recruitment_survey.xml',
        'view/vhr_recruitment_survey.xml',
        'view/vhr_recruitment_temp_survey.xml',
        
        # hrbp
        'view/hr_department.xml',
        'view/vhr_applicant_job_track_view.xml',
        'view/vhr_rr_transfer_employee_view.xml',
        
        # security
        'security/audittrail.rule.xml',
        
        # wizard

        # workflow
        'workflows/wkf_job.xml',
        'workflows/wkf_job_applicant.xml',
        
        #email template
        'data/vhr_recruitment_email_template.xml',
        
        'menu/vhr_recruitment_menu.xml',
        
        # security view
        'security/view/security_vhr_transfer_remind_view.xml',
        'security/view/security_vhr_applicant_job_track_view.xml',
        'security/view/security_vhr_erp_bonus_view.xml',
        'security/view/security_vhr_recruitment_survey_view.xml',
        'security/view/security_vhr_program_field_view.xml',
        # migrate data


    ],
    'qweb': [
        'view/vhr_applicant_search_view.xml',
    ],
    "active": False,
    "installable": True,
}
