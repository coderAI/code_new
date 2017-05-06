group_system            = 'base.group_system'
group_user              = 'base.group_user'
vhr_assistant_to_hrbp   = 'vhr_master_data.vhr_assistant_to_hrbp'
vhr_cb                  = 'vhr_human_resource.vhr_cb'
vhr_cb_profile          = 'vhr_human_resource.vhr_cb_profile'
vhr_cb_contract         = 'vhr_human_resource.vhr_cb_contract'
vhr_cb_working_record   = 'vhr_human_resource.vhr_cb_working_record'
vhr_cb_termination      = 'vhr_human_resource.vhr_cb_termination'
vhr_cnb_manager         = 'vhr_human_resource.vhr_cnb_manager'

vhr_hr_dept_head        = 'vhr_master_data.vhr_hr_dept_head'
vhr_dept_head           = 'vhr_master_data.vhr_dept_head'
vhr_dept_admin          = 'vhr_master_data.vhr_dept_admin'
vhr_af_admin            = 'vhr_master_data.vhr_af_admin'
vhr_hr_admin            = 'vhr_master_data.vhr_hr_admin'
vhr_fa                  = 'vhr_master_data.vhr_fa'
vhr_update_fa_hrbp_viewer = 'vhr_master_data.vhr_update_fa_hrbp_viewer'
vhr_cb_working_record_readonly = 'vhr_human_resource.vhr_cb_working_record_readonly'

view_security = {
    #Employee
    'hr.view_employee_form':                                                [group_user],
    'hr.view_employee_tree':                                                [group_user],
    'hr.view_employee_filter':                                                [group_user],
    'vhr_master_data.view_hr_employee_form':                                [group_user],
    'vhr_master_data.view_hr_employee_tree':                                [group_user],
    'vhr_master_data.view_hr_employee_search':                              [group_user],
    'vhr_master_data.vhr_employee_department_tree_view':                    [group_user],
    
    #Contract
    'vhr_human_resource.view_hr_contract_form':                             [group_user],
    'vhr_human_resource.view_hr_contract_tree':                             [group_user],
    'vhr_human_resource.view_hr_contract_search':                           [group_user],
    'vhr_human_resource.vhr_contract_submit_comment_form':                  [group_user],
    'hr_contract.hr_contract_view_search':                  [group_user],
    'hr_contract.hr_contract_view_tree':                  [group_user],
    'hr_contract.hr_contract_view_form':                  [group_user],
    #Renew Contract
    'vhr_human_resource.view_vhr_multi_renew_contract_submit_form':         [group_user],
    'vhr_human_resource.vhr_multi_renew_contract_view':                     [group_user],
    'vhr_human_resource.view_vhr_multi_renew_contract_tree_official':       [group_user],
    'vhr_human_resource.view_vhr_multi_renew_contract_tree_collaborator':   [group_user],
    'vhr_human_resource.view_vhr_multi_renew_contract_search_official':     [group_user],
    'vhr_human_resource.view_vhr_multi_renew_contract_search_collaborator': [group_user],
    'vhr_human_resource.vhr_multi_renew_contract_detail_view':              [group_user],
    'vhr_human_resource.view_vhr_multi_renew_contract_search_collaborator': [group_user],
    #Working Record
    'vhr_human_resource.view_vhr_working_record_submit_form':               [vhr_assistant_to_hrbp, vhr_cb_contract,vhr_cb_working_record,vhr_cb_termination, vhr_hr_dept_head, vhr_dept_admin, vhr_dept_head, vhr_cnb_manager],
    'vhr_human_resource.view_vhr_working_record_confirm_form':              [vhr_assistant_to_hrbp, vhr_cb_contract,vhr_cb_working_record,vhr_cb_termination, vhr_hr_dept_head, vhr_dept_admin, vhr_dept_head, vhr_cnb_manager],
    'vhr_human_resource.view_vhr_working_record_form':                      [vhr_assistant_to_hrbp, vhr_cb_contract,vhr_cb_working_record,vhr_cb_termination, vhr_hr_dept_head, vhr_dept_admin, vhr_dept_head, vhr_cnb_manager,vhr_cb_working_record_readonly],
    'vhr_human_resource.view_vhr_working_record_tree':                      [vhr_assistant_to_hrbp, vhr_cb_contract,vhr_cb_working_record,vhr_cb_termination, vhr_hr_dept_head, vhr_dept_admin, vhr_dept_head, vhr_cnb_manager,vhr_cb_working_record_readonly],
    'vhr_human_resource.view_vhr_working_record_search':                    [vhr_assistant_to_hrbp, vhr_cb_contract,vhr_cb_working_record,vhr_cb_termination, vhr_hr_dept_head, vhr_dept_admin, vhr_dept_head, vhr_cnb_manager,vhr_cb_working_record_readonly],
    
    'vhr_human_resource.view_vhr_working_record_waiting_for_public_tree':   [vhr_assistant_to_hrbp, vhr_cb_working_record, vhr_cnb_manager],
    'vhr_human_resource.view_vhr_working_record_staff_movement_tree':       [vhr_assistant_to_hrbp, vhr_cb_contract,vhr_cb_working_record,vhr_cb_termination, vhr_hr_dept_head, vhr_dept_head, vhr_cnb_manager],
    'vhr_human_resource.view_vhr_working_record_movement_search':           [vhr_assistant_to_hrbp, vhr_cb_contract,vhr_cb_working_record,vhr_cb_termination, vhr_hr_dept_head, vhr_dept_head, vhr_cnb_manager],
    #Mass Movement
    'vhr_human_resource.view_vhr_mass_movement_submit_form':                [vhr_assistant_to_hrbp, vhr_cb_contract,vhr_cb_working_record,vhr_cb_termination, vhr_hr_dept_head, vhr_dept_head, vhr_cnb_manager],
    'vhr_human_resource.view_vhr_mass_movement_form':                       [vhr_assistant_to_hrbp, vhr_cb_contract,vhr_cb_working_record,vhr_cb_termination, vhr_hr_dept_head, vhr_dept_head, vhr_cnb_manager],
    'vhr_human_resource.view_vhr_mass_movement_tree':                       [vhr_assistant_to_hrbp, vhr_cb_contract,vhr_cb_working_record,vhr_cb_termination, vhr_hr_dept_head, vhr_dept_head, vhr_cnb_manager],
    'vhr_human_resource.view_vhr_mass_movement_search':                     [vhr_assistant_to_hrbp, vhr_cb_contract,vhr_cb_working_record,vhr_cb_termination, vhr_hr_dept_head, vhr_dept_head, vhr_cnb_manager],
    #Mass record/multi request
    'vhr_human_resource.view_vhr_working_record_mass_movement_submit_form': [vhr_assistant_to_hrbp, vhr_cb_working_record, vhr_cnb_manager],
    'vhr_human_resource.view_vhr_working_record_mass_movement':             [vhr_assistant_to_hrbp, vhr_cb_working_record, vhr_cnb_manager],
    #Mass Request/record progress
    'vhr_common.view_vhr_mass_status_form':                                 [vhr_cb],
    'vhr_common.view_vhr_mass_status_tree':                                 [vhr_cb],
    'vhr_common.view_vhr_mass_status_search':                               [vhr_cb],
    'vhr_common.view_vhr_mass_status_form_inherit':                                 [group_user],
    'vhr_common.view_vhr_mass_status_tree_inherit':                                 [group_user],
    #Termination Request
    'vhr_human_resource.view_vhr_termination_request_submit_form':          [group_user],
    'vhr_human_resource.view_vhr_termination_request_form':                 [group_user],
    'vhr_human_resource.view_vhr_termination_request_tree':                 [group_user],
    'vhr_human_resource.view_vhr_termination_request_search':               [group_user],
    #Exit checklist request
    'vhr_human_resource.view_vhr_exit_checklist_request_submit_form':          [group_user],
    'vhr_human_resource.view_vhr_exit_checklist_request_form':                 [group_user],
    'vhr_human_resource.view_vhr_exit_checklist_request_tree':                 [group_user],
    'vhr_human_resource.view_vhr_exit_checklist_request_search':               [group_user],
    'vhr_human_resource.view_vhr_exit_checklist_detail_form':                  [group_user],
    'vhr_human_resource.view_vhr_exit_checklist_detail_tree':                  [group_user],
    #Family Deduct
    'vhr_human_resource.view_vhr_human_resource_vhr_family_deduct_form_inherit':          [vhr_cb],
    'vhr_master_data.view_vhr_family_deduct_form':                                        [vhr_cb],
    'vhr_master_data.view_vhr_family_deduct_tree':                                        [vhr_cb],
    'vhr_master_data.view_vhr_family_deduct_search':                                      [vhr_cb],
    'vhr_master_data.view_vhr_family_deduct_line_form':                                   [vhr_cb],
    'vhr_master_data.view_vhr_family_deduct_line_tree':                                   [vhr_cb],
    #Property management
    'vhr_master_data.view_vhr_property_management_form':                                   [vhr_hr_admin, vhr_af_admin],
    'vhr_master_data.view_vhr_property_management_tree':                                   [vhr_hr_admin, vhr_af_admin],
    'vhr_master_data.view_vhr_property_management_search':                                 [vhr_hr_admin, vhr_af_admin],
    #Company Group
    'vhr_master_data.view_vhr_company_group_form':                                 [vhr_hr_admin],
    'vhr_master_data.view_vhr_company_group_tree':                                 [vhr_hr_admin],
    'vhr_master_data.view_vhr_company_group_search':                                 [vhr_hr_admin],
     #Company
    'vhr_master_data.view_vhr_company_form':                                 [vhr_hr_admin],
    'vhr_master_data.view_vhr_company_tree':                                 [vhr_cb,vhr_hr_admin],
    'vhr_master_data.view_vhr_company_search':                                 [group_user,vhr_hr_admin],
    'base.view_company_form':                                                   [group_user,vhr_hr_admin],
    'base.view_company_tree':                                                   [group_user,vhr_hr_admin],
    #Office
    'vhr_master_data.view_vhr_office_form':                                 [vhr_cb,vhr_hr_admin],
    'vhr_master_data.view_vhr_office_tree':                                 [vhr_cb,vhr_hr_admin],
    'vhr_master_data.view_vhr_office_search':                                 [vhr_cb,vhr_hr_admin],
    #Hierarchical Chart / Ethnic/ Religion
    'vhr_master_data.view_vhr_dimension_form':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_dimension_tree':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_dimension_search':                                 [group_user,vhr_hr_admin],
    #Organization Class
    'vhr_master_data.view_vhr_organization_class_form':                                 [vhr_hr_admin],
    'vhr_master_data.view_vhr_organization_class_tree':                                 [vhr_hr_admin],
    'vhr_master_data.view_vhr_organization_class_search':                                 [vhr_hr_admin],
    #Department
    'hr.view_department_form':                                                  [vhr_hr_admin],
    'vhr_master_data.view_hr_department_form':                                 [vhr_hr_admin],
    'vhr_master_data.view_hr_department_form_fa':                                 [vhr_hr_admin, vhr_fa,vhr_update_fa_hrbp_viewer],
    'vhr_master_data.view_hr_department_tree':                                 [vhr_cb,vhr_hr_admin],
    'vhr_master_data.view_hr_department_fa_tree':                                 [vhr_fa,vhr_update_fa_hrbp_viewer],
    'vhr_master_data.view_hr_department_search':                                 [group_user,vhr_hr_admin, vhr_fa],
     #Country
    'base.view_country_form':                                 [vhr_hr_admin],
    'base.view_country_tree':                                 [group_user,vhr_hr_admin],
    #City
    'vhr_master_data.view_res_city_form':                                 [vhr_hr_admin],
    'vhr_master_data.view_res_city_search':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_res_city_tree':                                 [group_user,vhr_hr_admin],
    #District
    'vhr_master_data.view_res_district_form':                                 [vhr_hr_admin],
    'vhr_master_data.view_res_district_search':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_res_district_tree':                                 [group_user,vhr_hr_admin],
    #Hospital
    'vhr_master_data.view_vhr_hospital_form':                                 [vhr_hr_admin],
    'vhr_master_data.view_vhr_hospital_search':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_hospital_tree':                                 [group_user,vhr_hr_admin],
    #Assistant Form
    'vhr_master_data.view_vhr_assistance_form_form':                                 [vhr_hr_admin],
    'vhr_master_data.view_vhr_assistance_form_search':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_assistance_form_tree':                                 [group_user,vhr_hr_admin],
    #Archive File
    'vhr_master_data.view_vhr_archive_file_form':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_archive_file_search':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_archive_file_tree':                                 [group_user,vhr_hr_admin],
    #Cost Center
    'vhr_master_data.view_vhr_cost_center_view_form':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_cost_center_view_search':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_cost_center_view_tree':                                 [group_user,vhr_hr_admin],
    #Core Team
    'vhr_master_data.view_vhr_core_team_form':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_core_team_search':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_core_team_tree':                                 [group_user,vhr_hr_admin],
    #Job Family
    'vhr_master_data.view_vhr_job_family_form':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_job_family_search':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_job_family_tree':                                 [group_user,vhr_hr_admin],
    #Job Group
    'vhr_master_data.view_vhr_job_group_form':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_job_group_search':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_job_group_tree':                                 [group_user,vhr_hr_admin],
    #Job Group
    'vhr_master_data.view_vhr_job_group_form':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_job_group_search':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_job_group_tree':                                 [group_user,vhr_hr_admin],
    #Sub Group
    'vhr_master_data.view_vhr_sub_group_form':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_sub_group_search':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_sub_group_tree':                                 [group_user,vhr_hr_admin],
    #Sub Group-Job Title
    'vhr_master_data.view_vhr_subgroup_jobtitle_form':                                 [vhr_hr_admin],
    'vhr_master_data.view_vhr_subgroup_jobtitle_search':                                 [vhr_hr_admin],
    'vhr_master_data.view_vhr_subgroup_jobtitle_tree':                                 [vhr_hr_admin],
     #Ranking Level
    'vhr_master_data.view_vhr_ranking_level_form':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_ranking_level_search':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_ranking_level_tree':                                 [group_user,vhr_hr_admin],
    #Grade
    'vhr_master_data.view_vhr_grade_form':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_grade_search':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_grade_tree':                                 [group_user,vhr_hr_admin],
    #Job Title
    'vhr_master_data.view_vhr_job_title_form':                                 [vhr_hr_admin],
    'vhr_master_data.view_vhr_job_title_search':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_job_title_tree':                                 [group_user,vhr_hr_admin],
    
    #Job Level new
    'vhr_master_data.view_vhr_job_level_new_form':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_job_level_new_search':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_job_level_new_tree':                                 [group_user,vhr_hr_admin],
    
    #Job Title - Job Level
    'vhr_master_data.view_vhr_jobtitle_joblevel_form':                                 [vhr_hr_admin],
    'vhr_master_data.view_vhr_jobtitle_joblevel_search':                                 [vhr_hr_admin],
    'vhr_master_data.view_vhr_jobtitle_joblevel_tree':                                 [vhr_hr_admin],
     #Job Level Type
    'vhr_master_data.view_vhr_job_level_type_form':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_job_level_type_search':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_job_level_type_tree':                                 [group_user,vhr_hr_admin],
    #Job Level
    'vhr_master_data.view_vhr_job_level_form':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_job_level_search':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_job_level_tree':                                 [group_user,vhr_hr_admin],
    #Job Level-Policy
    'vhr_master_data.view_vhr_job_level_allowance_policy_form':                                 [vhr_hr_admin],
    'vhr_master_data.view_vhr_job_level_allowance_policy_search':                                 [vhr_hr_admin],
    'vhr_master_data.view_vhr_job_level_allowance_policy_tree':                                 [vhr_hr_admin],
    #Job Level-Position Class
    'vhr_master_data.view_vhr_job_level_position_class_form':                                 [vhr_hr_admin],
    'vhr_master_data.view_vhr_job_level_position_class_search':                                 [vhr_hr_admin],
    'vhr_master_data.view_vhr_job_level_position_class_tree':                                 [vhr_hr_admin],
    #Position Class
    'vhr_master_data.view_vhr_position_class_form':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_position_class_search':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_position_class_tree':                                 [group_user,vhr_hr_admin],
    #Project
    'vhr_master_data.view_project_project_form':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_project_project_search':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_project_project_tree':                                 [group_user,vhr_hr_admin],
    #Project Role
    'vhr_master_data.view_vhr_project_role_form':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_project_role_search':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_project_role_tree':                                 [group_user,vhr_hr_admin],
    #Project Type
    'vhr_master_data.view_vhr_project_type_form':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_project_type_search':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_project_type_tree':                                 [group_user,vhr_hr_admin],
     #Function
    'vhr_master_data.view_vhr_function_form':                                 [vhr_hr_admin],
    'vhr_master_data.view_vhr_function_search':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_function_tree':                                 [group_user,vhr_hr_admin],
    #Job Role
    'vhr_master_data.view_vhr_job_role_form':                                 [vhr_hr_admin],
    'vhr_master_data.view_vhr_job_role_search':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_job_role_tree':                                 [group_user,vhr_hr_admin],
    #Priority List
    'vhr_master_data.view_vhr_priority_list_form':                                 [vhr_hr_admin],
    'vhr_master_data.view_vhr_priority_list_search':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_priority_list_tree':                                 [group_user,vhr_hr_admin],
    #Perfomance Rating
    'vhr_master_data.view_vhr_performance_rating_form':                                 [vhr_hr_admin],
    'vhr_master_data.view_vhr_performance_rating_search':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_performance_rating_tree':                                 [group_user,vhr_hr_admin],
    #Collaborator Type
    'vhr_master_data.view_vhr_collaborator_type_form':                                 [vhr_hr_admin],
    'vhr_master_data.view_vhr_collaborator_type_search':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_collaborator_type_tree':                                 [group_user,vhr_hr_admin],
    #General Rating
    'vhr_master_data.view_vhr_general_rating_form':                                 [vhr_hr_admin],
    'vhr_master_data.view_vhr_general_rating_search':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_general_rating_tree':                                 [group_user,vhr_hr_admin],
    #Termination Type
    'vhr_human_resource.view_vhr_resignation_type_form':                                 [group_user,vhr_hr_admin],
    'vhr_human_resource.view_vhr_resignation_type_search':                                 [group_user,vhr_hr_admin],
    'vhr_human_resource.view_vhr_resignation_type_tree':                                 [group_user,vhr_hr_admin],
    #Termination Reason
    'vhr_human_resource.view_vhr_resignation_reason_form':                                 [group_user,vhr_hr_admin],
    'vhr_human_resource.view_vhr_resignation_reason_search':                                 [group_user,vhr_hr_admin],
    'vhr_human_resource.view_vhr_resignation_reason_tree':                                 [group_user,vhr_hr_admin],
    #Termination Reason Group
    'vhr_human_resource.view_vhr_resignation_reason_group_form':                                 [vhr_hr_admin],
    'vhr_human_resource.view_vhr_resignation_reason_group_search':                                 [vhr_hr_admin],
    'vhr_human_resource.view_vhr_resignation_reason_group_tree':                                 [group_user,vhr_hr_admin],
    #Exit Type
    'vhr_master_data.view_vhr_exit_type_form':                                 [vhr_hr_admin],
    'vhr_master_data.view_vhr_exit_type_search':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_exit_type_tree':                                 [group_user,vhr_hr_admin],
    #Exit
    'vhr_master_data.view_vhr_exit_form':                                 [vhr_hr_admin],
    'vhr_master_data.view_vhr_exit_search':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_exit_tree':                                 [group_user,vhr_hr_admin],
    #Exit Checklist Department FA
    'vhr_human_resource.view_vhr_exit_checklist_department_fa_form':                                 [vhr_hr_admin],
    'vhr_human_resource.view_vhr_exit_checklist_department_fa_tree':                                 [group_user,vhr_hr_admin],
    'vhr_human_resource.view_vhr_exit_checklist_department_fa_search':                                 [group_user,vhr_hr_admin],
    #Exit Approver
    'vhr_master_data.view_vhr_exit_approver_form':                                 [vhr_hr_admin],
    'vhr_master_data.view_vhr_exit_approver_search':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_exit_approver_tree':                                 [vhr_hr_admin],
    #School
    'vhr_master_data.view_vhr_school_form':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_school_search':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_school_tree':                                 [group_user,vhr_hr_admin],
    #Certificate Level
    'vhr_master_data.view_vhr_certificate_level_form':                                 [vhr_hr_admin],
    'vhr_master_data.view_vhr_certificate_level_search':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_certificate_level_tree':                                 [group_user,vhr_hr_admin], 
    #Degree
    'vhr_master_data.view_vhr_recruitment_degree_form':                                 [vhr_hr_admin],
    'vhr_master_data.view_hr_recruitment_degree_search':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_hr_recruitment_degree_tree':                                 [group_user,vhr_hr_admin], 
    #Self Development
    'vhr_master_data.view_vhr_self_development_form':                                 [vhr_hr_admin],
    'vhr_master_data.view_vhr_self_development_search':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_self_development_tree':                                 [group_user,vhr_hr_admin], 
    #Award Form
    'vhr_master_data.view_vhr_award_form_form':                                 [vhr_hr_admin],
    'vhr_master_data.view_vhr_award_form_search':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_award_form_tree':                                 [group_user,vhr_hr_admin],   
    #Award Level
    'vhr_master_data.view_vhr_award_level_form':                                 [vhr_hr_admin],
    'vhr_master_data.view_vhr_award_level_search':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_award_level_tree':                                 [group_user,vhr_hr_admin],   
    #Change Form Type
    'vhr_master_data.view_vhr_change_form_type_form':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_change_form_type_search':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_change_form_type_tree':                                 [group_user,vhr_hr_admin],   
    #Change Form
    'vhr_master_data.view_vhr_change_form_form':                                 [vhr_hr_admin],
    'vhr_master_data.view_vhr_change_form_search':                                 [group_user,group_user],
    'vhr_master_data.view_vhr_change_form_tree':                                 [group_user,group_user],   
    #Relationship Type
    'vhr_master_data.view_vhr_relationship_type_form':                                 [vhr_hr_admin],
    'vhr_master_data.view_vhr_relationship_type_search':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_relationship_type_tree':                                 [group_user,vhr_hr_admin],   
    #Health Care Record
    'vhr_master_data.view_vhr_health_care_record_form':                                 [vhr_hr_admin],
    'vhr_master_data.view_vhr_health_care_record_search':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_health_care_record_tree':                                 [vhr_hr_admin], 
    #Property Type
    'vhr_master_data.view_vhr_property_type_form':                                 [vhr_hr_admin],
    'vhr_master_data.view_vhr_property_type_search':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_property_type_tree':                                 [group_user,vhr_hr_admin], 
    #Property 
    'vhr_master_data.view_vhr_property_form':                                 [vhr_hr_admin],
    'vhr_master_data.view_vhr_property_search':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_property_tree':                                 [group_user,vhr_hr_admin], 
    #Personal Document Type 
    'vhr_master_data.view_vhr_personal_document_type_form':                                 [vhr_hr_admin],
    'vhr_master_data.view_vhr_personal_document_type_search':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_personal_document_type_tree':                                 [group_user,vhr_hr_admin], 
    #Personal Document Status
    'vhr_master_data.view_vhr_personal_document_status_form':                                 [vhr_hr_admin],
    'vhr_master_data.view_vhr_personal_document_status_search':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_personal_document_status_tree':                                 [group_user,vhr_hr_admin], 
    #Personal Document 
    'vhr_master_data.view_vhr_personal_document_form':                                 [vhr_hr_admin],
    'vhr_master_data.view_vhr_personal_document_search':                                 [vhr_hr_admin],
    'vhr_master_data.view_vhr_personal_document_tree':                                 [vhr_hr_admin], 
     #Duty Free
    'vhr_master_data.view_vhr_duty_free_form':                                 [vhr_hr_admin],
    'vhr_master_data.view_vhr_duty_free_search':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_duty_free_tree':                                 [group_user,vhr_hr_admin], 
     #Contract Type Group
    'vhr_human_resource.view_hr_contract_type_group_form':                                 [vhr_hr_admin],
    'vhr_human_resource.view_hr_contract_type_group_search':                                 [group_user,vhr_hr_admin],
    'vhr_human_resource.view_hr_contract_type_group_tree':                                 [group_user,vhr_hr_admin], 
    #Contract Type
    'vhr_human_resource.view_hr_contract_type_form':                                 [vhr_hr_admin],
    'vhr_human_resource.view_hr_contract_type_search':                                 [group_user,vhr_hr_admin],
    'vhr_human_resource.view_hr_contract_type_tree':                                 [group_user,vhr_hr_admin], 
    
    #Contract Sub Type
    'vhr_human_resource.view_hr_contract_sub_type_form':                                 [vhr_hr_admin],
    'vhr_human_resource.view_hr_contract_sub_type_search':                                 [group_user,vhr_hr_admin],
    'vhr_human_resource.view_hr_contract_sub_type_tree':                                 [group_user,vhr_hr_admin], 
    
    #Appendix Contract Type
    'vhr_human_resource.view_vhr_appendix_contract_type_form':                                 [vhr_hr_admin],
    'vhr_human_resource.view_vhr_appendix_contract_type_search':                                 [group_user,vhr_hr_admin],
    'vhr_human_resource.view_vhr_appendix_contract_type_tree':                                 [group_user,vhr_hr_admin], 
    
    #Appendix Contract
    'vhr_human_resource.view_vhr_appendix_contract_form':                                 [vhr_cb],
    'vhr_human_resource.view_vhr_appendix_contract_search':                                 [group_user],
    'vhr_human_resource.view_vhr_appendix_contract_tree':                                 [group_user], 
    
    #Type Of Salary
    'vhr_master_data.view_vhr_salary_setting_form':                                 [vhr_hr_admin],
    'vhr_master_data.view_vhr_salary_setting_search':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_salary_setting_tree':                                 [group_user,vhr_hr_admin], 
    #Salary Progress
#     'vhr_payroll.view_vhr_pr_salary_form':                                 [vhr_hr_admin],
#     'vhr_payroll.view_vhr_pr_salary_search':                                 [vhr_hr_admin],
#     'vhr_payroll.view_vhr_pr_salary_tree':                                 [vhr_hr_admin], 
    #Bank
    'vhr_master_data.view_vhr_bank_form':                                 [vhr_hr_admin],
    'vhr_master_data.view_vhr_bank_search':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_bank_tree':                                 [group_user,vhr_hr_admin], 
    'base.view_res_bank_form':                                 [vhr_hr_admin],
    'base.view_res_bank_tree':                                 [group_user,vhr_hr_admin],
    #Bank's Branch
    'vhr_master_data.view_vhr_branch_bank_form':                                 [vhr_hr_admin],
    'vhr_master_data.view_vhr_branch_bank_search':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_branch_bank_tree':                                 [group_user,vhr_hr_admin], 
    #Sequence
    'vhr_master_data.view_vhr_sequence_form':                                 [vhr_hr_admin],
    'vhr_master_data.view_vhr_sequence_search':                                 [group_user,vhr_hr_admin],
    'vhr_master_data.view_vhr_sequence_tree':                                 [group_user,vhr_hr_admin], 
    #Email Group
    'vhr_email_configuration.view_vhr_email_group_form':                                 [vhr_hr_admin],
    'vhr_email_configuration.view_vhr_email_group_search':                                 [vhr_hr_admin],
    'vhr_email_configuration.view_vhr_email_group_tree':                                 [vhr_hr_admin], 
    
    'vhr_master_data.view_vhr_employee_instance_form_form':                             [vhr_cb],
    'vhr_master_data.view_vhr_employee_instance_form_search':                           [vhr_cb],
    'vhr_master_data.view_vhr_employee_instance_form_tree':                             [group_user],
    
    #Certificates/ Degree
    'vhr_master_data.view_vhr_certificate_info_search':                                 [vhr_hr_admin],
    'vhr_master_data.view_vhr_certificate_info_form':                                   [group_user],
    'vhr_master_data.view_vhr_certificate_info_tree':                                   [group_user],
    
    'vhr_master_data.view_vhr_employee_partner_form':                                   [group_user],
    'vhr_master_data.view_vhr_employee_partner_tree':                                   [group_user],
    'vhr_master_data.view_vhr_employee_partner_search':                                 [group_user],
    
    'vhr_master_data.view_res_partner_bank_form':                                       [vhr_cb],
    'vhr_master_data.view_res_partner_bank_tree':                                       [vhr_cb],
    'vhr_master_data.view_res_partner_bank_search':                                       [vhr_cb],
    'base.view_partner_bank_tree':                                                      [group_user],
    'base.view_partner_bank_form':                                                      [group_user],
    'vhr_human_resource.view_vhr_mission_collaborator_contract_form':                   [group_user],
    'vhr_human_resource.view_vhr_mission_collaborator_contract_search':                    [group_user],
    'vhr_human_resource.view_vhr_mission_collaborator_contract_tree':                   [group_user],
    
    'vhr_human_resource.view_vhr_result_collaborator_contract_form':                    [group_user],
    'vhr_human_resource.view_vhr_result_collaborator_contract_search':                  [group_user],
    'vhr_human_resource.view_vhr_result_collaborator_contract_tree':                   [group_user],
    
    'vhr_human_resource.view_vhr_bank_contract_form':                                   [group_user],
    'vhr_human_resource.view_vhr_bank_contract_tree':                                   [group_user],
    'vhr_human_resource.view_vhr_bank_contract_search':                                 [group_user],
    
    'vhr_human_resource.view_vhr_salary_contract_form':                             [group_user],
    'vhr_human_resource.view_vhr_salary_contract_search':                           [group_user],
    'vhr_human_resource.view_vhr_salary_contract_tree':                             [group_user],
    
    'vhr_human_resource.view_vhr_resign_reason_detail_form':                        [group_user],
    'vhr_human_resource.view_vhr_resign_reason_detail_search':                      [group_user],
    'vhr_human_resource.view_vhr_resign_reason_detail_tree':                        [group_user],
    
    'vhr_common.view_vhr_mass_status_detail_tree':                                   [group_user],
    'vhr_human_resource.view_vhr_mass_status_detail_tree_inherit':                   [group_user],
    'vhr_common.view_vhr_mass_status_detail_form':                                      [group_user],
    'vhr_human_resource.vhr_renew_contract_view':                                       [group_user],
    'email_template.email_template_form':                                       [vhr_hr_admin],
    'email_template.email_template_tree':                                       [vhr_hr_admin],
    'email_template.view_email_template_search':                                [vhr_hr_admin],
    
    'vhr_master_data.view_vhr_delegate_detail_view_form':                                       [vhr_hr_admin],
    'vhr_master_data.view_vhr_delegate_detail_view_tree':                                       [vhr_hr_admin],
    'vhr_master_data.view_vhr_delegate_detail_view_search':                                [vhr_hr_admin],
    
    'vhr_master_data.view_vhr_delegate_model_view_form':                                       [vhr_hr_admin],
    'vhr_master_data.view_vhr_delegate_model_view_tree':                                       [vhr_hr_admin],
    'vhr_master_data.view_vhr_delegate_model_view_search':                                [vhr_hr_admin],
    
    'vhr_master_data.view_vhr_delegate_master_view_form':                                       [vhr_hr_admin],
    'vhr_master_data.view_vhr_delegate_master_view_tree':                                       [vhr_hr_admin],
    'vhr_master_data.view_vhr_delegate_master_view_search':                                [vhr_hr_admin],
    
    'website.login_layout':             [group_user],
    'website.login_layout':             [group_user],
    'website.layout_logo_show':         [group_user],
    'website.footer_default':           [group_user],
    
    'document.view_document_file_tree': [group_user],
    'base.view_attachment_form':        [group_user],
    'base.view_attachment_search':      [group_user],
    'base.view_model_fields_tree':      [group_user],
    'base.view_model_fields_search':    [group_user],
    
    'pentaho_reports.wiz_pentaho_report_prompt': [vhr_cb],
    'vhr_base.view_ir_cron_form_inherit':   [group_user],
    'vhr_base.view_ir_cron_tree_inherit':   [group_user],
    'base.module_form':                     [group_user],
    'vhr_base.view_ir_module_tree_inherit': [group_user],
    
    'vhr_master_data.view_res_partner_form':    [vhr_hr_admin],
    'vhr_master_data.view_partner_tree_inherit': [group_user],
    'vhr_master_data.view_vhr_erp_tree':        [group_user],
    
    'vhr_base.view_audittrail_rule_form_inherit':   [group_user],
    'audittrail.view_audittrail_log_search':        [group_user],
    'audittrail.view_audittrail_log_tree':          [group_user],
    'audittrail.view_audittrail_log_form':          [group_user],
    
#     'vhr_base.view_ir_config_form_inherit':         [group_user],
#     'vhr_base.view_ir_config_list_inherit':         [group_user],
#     'vhr_base.view_ir_config_search_inherit':       [group_user],
    'vhr_master_data.view_vhr_dimension_type_form': [group_user],
    'vhr_master_data.view_vhr_dimension_type_search':   [group_user],
    'vhr_master_data.view_vhr_dimension_type_tree':     [group_user],
    
    'vhr_master_data.view_vhr_skill_type_form':     [group_user],
    'vhr_master_data.view_vhr_skill_type_search':   [group_user],
    'vhr_master_data.view_vhr_skill_type_tree':     [group_user],
    
    'vhr_master_data.view_vhr_skill_level_form':        [group_user],
    'vhr_master_data.view_vhr_skill_level_search':      [group_user],
    'vhr_master_data.view_vhr_skill_level_tree':        [group_user],
    
    'vhr_master_data.view_vhr_seniority_form':          [group_user],
    'vhr_master_data.view_vhr_seniority_search':        [group_user],
    'vhr_master_data.view_vhr_seniority_tree':          [group_user],
    
    'vhr_master_data.view_vhr_skill_form':              [group_user],
    'vhr_master_data.view_vhr_skill_search':            [group_user],
    'vhr_master_data.view_vhr_skill_tree':              [group_user],
    
    'vhr_master_data.view_vhr_salary_level_detail_form':    [group_user],
    'vhr_master_data.view_vhr_salary_level_detail_search':  [group_user],
    'vhr_master_data.view_vhr_salary_level_detail_tree':    [group_user],
    'vhr_master_data.view_vhr_salary_level_form':           [group_user],
    'vhr_master_data.view_vhr_salary_level_job_title_form': [group_user],
    'vhr_master_data.view_vhr_salary_level_job_title_search':    [group_user],
    'vhr_master_data.view_vhr_salary_level_job_title_tree':     [group_user],
    'vhr_master_data.view_vhr_salary_level_search':             [group_user],
    'vhr_master_data.view_vhr_salary_level_tree':               [group_user],
    
    'vhr_master_data.view_vhr_equipment_form':  [vhr_hr_admin],
    'vhr_master_data.view_vhr_equipment_search':    [group_user],
    'vhr_master_data.view_vhr_equipment_tree':  [group_user],
    
    'vhr_master_data.view_res_lang_form':   [group_user],
    'vhr_master_data.view_res_lang_search': [group_user],
    'vhr_master_data.view_res_lang_tree':   [group_user],
    
    'vhr_master_data.view_vhr_erp_form':    [group_user],
    'vhr_master_data.view_vhr_erp_search':  [group_user],
    'vhr_master_data.view_vhr_erp_tree':    [group_user],
    
    'vhr_master_data.view_vhr_erp_detail_form': [group_user],
    'vhr_master_data.view_vhr_erp_detail_search': [group_user],
    'vhr_master_data.view_vhr_erp_detail_tree': [group_user],
    
    'vhr_master_data.view_vhr_assessment_mark_config_form': [vhr_hr_admin],
    'vhr_master_data.view_vhr_assessment_mark_config_search':   [group_user],
    'vhr_master_data.view_vhr_assessment_mark_config_tree': [group_user],
    
    #Assessment Period
    'vhr_master_data.view_vhr_assessment_period_form':  [group_user],
    'vhr_master_data.view_vhr_assessment_period_search':    [group_user],
    'vhr_master_data.view_vhr_assessment_period_tree':  [group_user],
    
    #Assessment Calibration
    'vhr_master_data.view_vhr_assessment_calibration_form':                                 [vhr_hr_admin,vhr_cnb_manager],
    'vhr_master_data.view_vhr_assessment_calibration_search':                                 [group_user,vhr_hr_admin,vhr_cnb_manager],
    'vhr_master_data.view_vhr_assessment_calibration_tree':                                 [group_user,vhr_hr_admin,vhr_cnb_manager],
    
    #Employee Assessment Result
    'vhr_master_data.view_vhr_employee_assessment_result_form':                                 [vhr_cnb_manager],
    'vhr_master_data.view_vhr_employee_assessment_result_search':                                 [vhr_cnb_manager],
    'vhr_master_data.view_vhr_employee_assessment_result_tree':                                 [vhr_cnb_manager],
    
    'vhr_human_resource.view_vhr_import_employee_assessment_result':                            [vhr_hr_admin,vhr_cnb_manager],
    'vhr_human_resource.view_vhr_import_working_record':                                        [vhr_hr_admin,vhr_cnb_manager,vhr_cb_working_record],
    'vhr_human_resource.view_vhr_import_appendix_contract':                                      [vhr_hr_admin,vhr_cnb_manager,vhr_cb_contract],
    'vhr_human_resource.view_vhr_import_partner_bank':                                      [vhr_hr_admin,vhr_cnb_manager,vhr_cb_profile],
    
    'vhr_common.view_vhr_import_status_search':                 [vhr_hr_admin, vhr_cnb_manager,vhr_cb_profile],
    'vhr_common.view_vhr_import_status_form':                   [vhr_hr_admin, vhr_cnb_manager,vhr_cb_profile],
    'vhr_common.view_vhr_import_status_tree':                   [vhr_hr_admin, vhr_cnb_manager,vhr_cb_profile],
    
    'vhr_human_resource.view_vhr_permission_location_form':                                 [vhr_hr_admin,vhr_cnb_manager],
    'vhr_human_resource.view_vhr_permission_location_tree':                                 [vhr_hr_admin,vhr_cnb_manager],
    'vhr_human_resource.view_vhr_permission_location_search':                               [vhr_hr_admin,vhr_cnb_manager],
    
     #Termination Agreement
    'vhr_human_resource.view_vhr_termination_agreement_contract_form':                                 [vhr_cb_contract,vhr_hr_admin,vhr_cnb_manager],
    'vhr_human_resource.view_vhr_termination_agreement_contract_tree':                                 [vhr_cb_contract,vhr_hr_admin,vhr_cnb_manager],
    'vhr_human_resource.view_vhr_termination_agreement_contract_search':                                 [vhr_cb_contract,vhr_hr_admin,vhr_cnb_manager], 
    
    'hr_recruitment.hr_recruitment_degree_tree': [group_user],
    
    'base.view_model_search':       [group_user],
    'base.view_model_tree':         [group_user],
    'base.view_workflow_activity_form': [vhr_hr_admin,group_system,vhr_cb],
    'base.ir_mail_server_form': [vhr_hr_admin,group_system,vhr_cb],
    'base.ir_mail_server_list': [vhr_hr_admin,group_system,vhr_cb],
    'base.view_ir_mail_server_search': [vhr_hr_admin,group_system,vhr_cb],
    'base.act_report_xml_view': [vhr_hr_admin,group_system,vhr_cb],
    'base.act_report_xml_view_tree': [vhr_hr_admin,group_system,vhr_cb],
    'base.act_report_xml_search_view': [vhr_hr_admin,group_system,vhr_cb],
    'vhr_recruitment.view_vhr_recruitment_res_groups_tree':  [vhr_hr_admin,group_system,vhr_cb],
    
    
    'vhr_human_resource.view_vhr_multi_renew_contract_setting_form':                                       [vhr_cb],
    'vhr_human_resource.view_vhr_multi_renew_contract_setting_tree':                                       [vhr_cb],
    'vhr_human_resource.view_vhr_multi_renew_contract_setting_search':                                       [vhr_cb],
    
    'vhr_human_resource.view_vhr_multi_renew_contract_detail_search':                                       [vhr_cb],
    'vhr_human_resource.view_vhr_multi_renew_contract_detail_form':                                       [vhr_cb],
     'vhr_human_resource.view_vhr_multi_renew_contract_detail_tree':                                       [vhr_cb],
    
    'vhr_master_data.view_vhr_delegate_by_process_view_search':                                       [vhr_hr_admin],
    'vhr_master_data.view_vhr_delegate_by_process_view_form':                                       [vhr_hr_admin],
    'vhr_master_data.view_vhr_delegate_by_process_view_tree':                                       [vhr_hr_admin],
       


    'vhr_human_resource.view_vhr_import_deliver_hr_contract':                                     [vhr_cb],


 }
