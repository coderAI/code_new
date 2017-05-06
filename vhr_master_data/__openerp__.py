# -*- encoding: utf-8 -*-

{
    "name": "HR Master Data",
    "version": "1.0",
    "author": "MIS",
    "category": "VHR",
    'sequence': 19,
    'summary': 'Master Data',
    "depends": [
        'base',
        'hr',
        'hr_holidays',
        'hr_recruitment',
#         'hr_contract',
        "hr_applicant_document",
        'project',
        #
        
        #'users_ldap',
        'resource',
        #
        'vhr_base',
        'vhr_common',
        'vhr_email_configuration',
    ],
    'description': """
HR Master Data
=================================================================

This module include all of master data using for HR module.
""",
    "init_xml": [],
    "demo_xml": [],
    "data": [
        # security
        'security/ir.model.access.csv',
        'security/vhr_master_data_security.xml',
        'security/audittrail.rule.xml',
        
        # wizard

        # view
        'views/vhr_dimension_view.xml',
        'views/vhr_dimension_type_view.xml',
        'views/vhr_sequence.xml',
        'views/hr_employee.xml',
        'views/res_partner.xml',
        'views/vhr_company_group_view.xml',
        'views/vhr_company_view.xml',
        'views/vhr_office_view.xml',
        'views/vhr_employee_instance_view.xml',

        'views/vhr_organization_class_view.xml',
        'views/res_city_view.xml',
        # 12
        'views/vhr_job_family_view.xml',
        'views/vhr_job_group_view.xml',
        'views/vhr_sub_group_view.xml',
        'views/vhr_ranking_level_view.xml',
        'views/vhr_grade_view.xml',
        'views/vhr_job_level_type.xml',
        'views/vhr_job_level.xml',
        'views/vhr_award_form.xml',
        'views/vhr_job_title.xml',

        # 22 - 26
        'views/vhr_award_level_view.xml',
        'views/vhr_bank_view.xml',
        'views/vhr_branch_bank_view.xml',

        'views/vhr_change_form_type_view.xml',
        'views/vhr_change_form_view.xml',        

        # 37
        'views/res_district_view.xml',
        'views/project_project_view.xml',
        'views/vhr_function_view.xml',

        # 32
        'views/vhr_performance_rating_view.xml',
        'views/vhr_collaborator_type_view.xml',
        'views/vhr_certificate_level_view.xml',
        'views/vhr_self_development_view.xml',


        # 42
        'views/vhr_hospital_view.xml',
        'views/vhr_job_role_view.xml',
        'views/vhr_priority_list_view.xml',
        'views/vhr_recruitment_degree_view.xml',
        'views/vhr_project_role_view.xml',

        #47-51
        'views/vhr_project_type_view.xml',
        'views/vhr_property_type_view.xml',
        'views/vhr_property_view.xml',
        'views/vhr_general_rating_view.xml',

        #52
        'views/vhr_school_view.xml',
        'views/vhr_skill_type_view.xml',
        'views/vhr_skill_level_view.xml',
        'views/vhr_seniority_view.xml',
        'views/vhr_skill_view.xml',

        #57   
        'views/vhr_assistance_form_view.xml',
        

        # 62
        'views/vhr_archive_file_view.xml',
        'views/vhr_salary_level_view.xml',
        'views/vhr_salary_level_job_title_view.xml',
        'views/vhr_salary_level_detail_view.xml',
        'views/vhr_cost_center_view.xml',
        'views/vhr_job_level_allowance_policy_view.xml',

        #68
        'views/vhr_position_class_view.xml',
        'views/vhr_job_level_position_class_view.xml',
        'views/vhr_job_category_view.xml',
        'views/vhr_job_view.xml',

        #75
        'views/hr_department_view.xml',
        'views/vhr_recruitment_source_type_view.xml',
        'views/hr_recruitment_source_view.xml',
        'views/vhr_interview_round_view.xml',
        'views/vhr_task_type_view.xml',

        'views/vhr_equipment_view.xml',
        'views/vhr_room_view.xml',
        'views/res_lang_view.xml',
        #86
        'views/vhr_erp_view.xml',
        'views/vhr_erp_detail_view.xml',
        #94
        'views/vhr_relationship_type_view.xml',
        'views/vhr_employee_partner_view.xml',

        #97
        'views/vhr_assessment_mark_config_view.xml',
        'views/vhr_assessment_period_view.xml',
        #         'views/vhr_probation_fail_reason_view.xml',

        'views/vhr_health_care_record_view.xml',
        'views/vhr_property_management_view.xml',
        'views/vhr_duty_free_view.xml',
        'views/vhr_working_background_view.xml',
        'views/vhr_personal_document_type_view.xml',
        'views/vhr_personal_document_view.xml',        
        'views/res_partner_bank.xml',
              
        'views/vhr_salary_setting_view.xml',
        
        'views/vhr_exit_type_view.xml',
        'views/vhr_exit_view.xml',
        'views/vhr_exit_approver_view.xml',
        'views/vhr_core_team_view.xml',
        
        'views/vhr_subgroup_jobtitle.xml',
        'views/vhr_jobtitle_joblevel.xml',
        'views/vhr_family_deduct_view.xml',
        'views/vhr_family_deduct_line_view.xml',
        'views/vhr_certificate_info_view.xml',
        'views/vhr_state_change.xml',  
        'views/vhr_delegate_model_view.xml', 
        'views/vhr_delegate_detail_view.xml',   
        'views/vhr_delegate_master_view.xml',  
        'views/vhr_delegate_by_process_view.xml',  
                  
        'views/vhr_personal_document_status_view.xml',  
        'views/vhr_job_level_new_view.xml',  
        
        'views/vhr_assessment_calibration_view.xml',  
        'views/vhr_employee_assessment_result_view.xml', 
        
        # Student
        'views/vhr_student_view.xml',
        'views/ir_sequence_view.xml', 
        # menu
        'menu/vhr_master_data_root_menu.xml',
        #data
        'data/data_dimension_type.xml',
        'data/data_vhr_assessment_mark_config.xml',
        'data/data_vhr_dimension.xml',
        'data/data_ir_cron.xml',
        'data/data_vhr_sequence.xml',
        'data/data_ir_config_parameter.xml',
        'data/data_bank.xml',
        'data/data_email_server.xml',
        'data/data_vhr_job_level_new.xml',
        'data/data_vhr_assessment_calibration.xml',
        'data/data_function_migrate.xml',
        
    ],
    "active": False,
    "installable": True,
}
