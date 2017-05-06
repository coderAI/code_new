# -*- encoding: utf-8 -*-

{
    "name": "HRS Human Resource",
    "version": "1.0",
    "author": "MIS",
    "category": "HRS",
    'summary': 'Human Resource',
    "depends": [
        'vhr_master_data',
        'hr_contract',
        'extra_quickadd',
        'report_xlsx',
    ],
    'description': """
HRS Human Resource
===========================================================================

This module will include functions/feature apply for human resource information. Such as: Employee, Contract, ...
""",
    "init_xml": [],
    "demo_xml": [],
    "data": [
             
        # security
        'security/vhr_human_resource_security.xml',
        'security/ir.model.access.csv',
        'security/audittrail.rule.xml',
        
        # wizard
        # view
        #Employee        
        'view/hr_employee.xml',
        'view/hr_department.xml',
        # Working records
        'view/vhr_working_record_view.xml',
        'view/vhr_mass_movement.xml',
        'view/vhr_mass_status_view.xml',

        #Contract
        'view/hr_contract.xml',
        'view/hr_contract_type_group_view.xml',
        'view/hr_contract_type_view.xml',
        'view/vhr_bank_contract.xml',
        'view/vhr_mission_collaborator_contract.xml',
        'view/vhr_result_collaborator_contract.xml',
        'view/vhr_salary_contract.xml',

        # Renew Contract
        'view/vhr_multi_renew_contract.xml',
        'view/vhr_multi_renew_contract_detail.xml',
 
        
        #Termination Request
        'view/vhr_termination_request_view.xml',
        'view/vhr_resignation_type_view.xml',
        'view/vhr_resignation_reason_view.xml',
        'view/vhr_resign_reason_detail_view.xml',
        'view/vhr_resignation_reason_group_view.xml',
        
        'view/vhr_exit_checklist_request_view.xml',
        'view/vhr_exit_checklist_detail_view.xml',
        'view/vhr_human_resource_template_view.xml',
        'view/vhr_family_deduct_view.xml',
        'view/vhr_delegate_view.xml',
        'view/vhr_permission_location_view.xml',
        'view/vhr_log_error_system_view.xml',
        'view/hr_contract_sub_type_view.xml',
        'view/vhr_appendix_contract_type_view.xml',
        'view/vhr_appendix_contract_view.xml',
        'view/vhr_termination_agreement_contract_view.xml',
        'view/vhr_resignation_link_exit_survey_view.xml',
        'view/vhr_dimension_view.xml',
        'view/vhr_hr_test_result_view.xml',
        
        'view/ir_attachment.xml',
        'view/vhr_exit_checklist_department_fa_view.xml',
        'view/vhr_import_tax_code_view.xml',
        'view/vhr_multi_renew_contract_setting_view.xml',
        'view/vhr_import_pit_view.xml',

        
        'wizard/vhr_working_record_mass_movement.xml',
        'wizard/vhr_working_record_execute_workflow.xml',
        'wizard/vhr_mass_movement_execute_workflow.xml',
        'wizard/vhr_multi_renew_contract_execute_workflow.xml',
        'wizard/vhr_renew_contract/vhr_renew_contract.xml',
#         'wizard/vhr_mass_change_state_exit_checklist.xml',
        
        'wizard/vhr_import_assessment_result_status.xml',
        'wizard/vhr_import_working_record_status.xml',
        'wizard/vhr_import_appendix_contract_status.xml',
        'wizard/vhr_import_partner_bank_status.xml',
        'wizard/vhr_hr_export_hrbp_department.xml',
        'wizard/vhr_wizard_privacy_statement_view.xml',
        'wizard/vhr_wizard_employment_confirmation_view.xml',
        'wizard/vhr_contract_send_mail_remind/vhr_contract_send_mail_remind.xml',
        'wizard/vhr_contract_send_mail_remind/vhr_contract_delivery_wizard.xml',
        'wizard/vhr_contract_send_mail_remind/vhr_contract_receive_hard_copy.xml',
        'wizard/vhr_import_deliver_hr_contract.xml',
        'wizard/vhr_import_personal_document_status.xml',
        'wizard/vhr_wizard_print_low_salary_confirmation.xml',
        

        # menu
        'menu/vhr_human_resource_menu.xml',
        
        # data
        'data/data_vhr_sequence.xml',
        'data/data_vhr_email_group.xml',
        'data/data_ir_config_parameter.xml',
        'data/vhr_sm_fetch_mail.xml',
        
        'data/vhr_mass_movement_email_template_not_adjust_salary.xml',
#         'data/vhr_mass_movement_email_template.xml',
        'data/vhr_working_record_staff_movement_email_template.xml',
#         'data/vhr_working_record_staff_movement_email_template_not_adjust_salary.xml',
        'data/vhr_termination_request_email_template_termination_offline.xml',
        'data/vhr_termination_request_email_template_termination_online.xml',
#         'data/vhr_multi_renew_contract_email_template_official.xml',
#         'data/vhr_multi_renew_contract_email_template_collaborator.xml',
        'data/vhr_multi_renew_contract_email_template.xml',
        'data/vhr_exit_checklist_request_email_template.xml',
        'data/data_ir_cron.xml',
        'data/data_template_report_docx.xml',
        'data/data_function_migrate.xml',
        'data/data_hr_contract_sub_type.xml',
        'data/data_vhr_appendix_contract_type.xml',
        'data/hr_contract_email_template.xml',
        
        
        'data/data_vhr_dimension_type.xml',
        'data/data_vhr_dimension.xml',
    ],
    "css": ["static/src/css/style.css"],
    "qweb": [
             "view/hr_contract_quick_add_view.xml",
             "view/hr_employee_quick_search_view.xml",
             
             ],
    "active": True,
    "installable": True,
}
