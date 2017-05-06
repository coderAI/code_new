
group_system            = 'base.group_system'
group_user              = 'base.group_user'
hrs_group_system        = 'vhr_base.hrs_group_system'
vhr_assistant_to_hrbp   = 'vhr_master_data.vhr_assistant_to_hrbp'
vhr_cb                  = 'vhr_human_resource.vhr_cb'
vhr_cb_timesheet        = 'vhr_timesheet.vhr_cb_timesheet'
vhr_cb_timesheet_readonly = 'vhr_timesheet.vhr_cb_timesheet_readonly'
vhr_dept_head           = 'vhr_master_data.vhr_dept_head'
vhr_dept_admin          = 'vhr_master_data.vhr_dept_admin'
vhr_ts_approver         = 'vhr_timesheet.vhr_ts_approver'
vhr_cb_admin            = 'vhr_human_resource.vhr_cb_admin'
vhr_cb_manager            = 'vhr_human_resource.vhr_cnb_manager'
vhr_hr_admin            = 'vhr_master_data.vhr_hr_admin'

view_security = {
    #Leave Request
    'vhr_timesheet.view_hr_holidays_submit_form':                                [group_user],
    'vhr_timesheet.view_hr_holidays_new_form':                                [group_user],
    'vhr_timesheet.view_tree_holiday':                              [group_user],
    'vhr_timesheet.view_tree_holiday_to_approve':                    [group_user],
    'vhr_timesheet.view_hr_holidays_filter':                    [group_user],
    'vhr_timesheet.view_hr_holidays_filter_new':                    [group_user],
    'vhr_timesheet.view_holiday_simple':                    [group_user],
    #Overtime
    'vhr_timesheet.view_vhr_ts_overtime_submit_form':                    [group_user],
    'vhr_timesheet.view_vhr_ts_overtime_tree':                    [group_user],
    'vhr_timesheet.view_vhr_ts_overtime_list_tree':                    [group_user],
    'vhr_timesheet.view_vhr_ts_overtime_form':                    [group_user],
    'vhr_timesheet.view_vhr_ts_overtime_search':                    [group_user],
    'vhr_timesheet.view_vhr_ts_overtime_detail_tree':                    [group_user],
    'vhr_timesheet.view_vhr_ts_overtime_detail_form':                    [group_user],
    'vhr_timesheet.view_vhr_ts_overtime_detail_search':                 [group_user],
    'vhr_timesheet.view_vhr_ts_overtime_search':                    [group_user],
    #Multi OT/Leave
    'vhr_timesheet.view_vhr_ts_overtime_multi':                    [hrs_group_system],
    'vhr_timesheet.view_vhr_holidays_multi':                    [vhr_dept_admin, vhr_cb_timesheet],
    #Overtime Summary
    'vhr_timesheet.view_vhr_ts_overtime_summarize_tree':                    [vhr_cb_timesheet,vhr_cb_manager],
    'vhr_timesheet.view_vhr_ts_overtime_summarize_form':                    [vhr_cb_timesheet,vhr_cb_manager],
    'vhr_timesheet.view_vhr_ts_overtime_summarize_search':                    [vhr_cb_timesheet,vhr_cb_manager],
    #Annual Leave/Accumulation
    'vhr_timesheet.view_holiday_allocation_tree_readonly':                    [group_user],
    'vhr_timesheet.edit_holiday_new':                    [group_user],
    'vhr_timesheet.view_annual_leave_filter':                    [group_user],
    'vhr_timesheet.view_annual_leave_accumulation':             [group_user],
    'vhr_timesheet.view_accumulation_filter':             [group_user],
    #Annual Leave Balance/Acumulation Generation
    'vhr_timesheet.vhr_ts_employee_annual_leave_gen_view':      [vhr_cb_timesheet],
    'vhr_timesheet.vhr_ts_incremental_annual_leave_view':      [vhr_cb_timesheet],
    #Update OT Summary
    'vhr_timesheet.vhr_ts_update_ot_summary_view':      [vhr_cb_timesheet],
    #Compensation OT Payment
    'vhr_timesheet.view_vhr_compensation_ot_payment_form':      [vhr_cb,vhr_dept_head],
    'vhr_timesheet.view_vhr_compensation_ot_payment_search':      [vhr_cb,vhr_dept_head],
    'vhr_timesheet.view_vhr_compensation_ot_payment_tree':      [vhr_cb,vhr_dept_head],
    'vhr_timesheet.view_vhr_compensation_ot_payment_wizard':    [vhr_cb,vhr_dept_head],
    #Detail Generation/Summary Generation
    'vhr_timesheet.vhr_ts_monthly_gen_view':                            [vhr_dept_admin, vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_ts_view_result_detail_form':                [vhr_dept_admin, vhr_cb_timesheet],
    'vhr_timesheet.vhr_ts_employee_timesheet_summary_gen_view':         [vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_ts_view_result_summary_form':               [vhr_cb_timesheet],
    #Detail
    'vhr_timesheet.view_vhr_ts_monthly_form':      [vhr_dept_admin, vhr_cb_timesheet, vhr_ts_approver,vhr_cb_manager,vhr_dept_head],
    'vhr_timesheet.view_vhr_ts_monthly_monthly_calendar':      [vhr_dept_admin, vhr_cb_timesheet, vhr_ts_approver,vhr_cb_manager,vhr_dept_head,vhr_cb_timesheet_readonly],
    'vhr_timesheet.view_vhr_ts_monthly_search':      [vhr_dept_admin, vhr_cb_timesheet, vhr_ts_approver,vhr_cb_manager,vhr_dept_head,vhr_cb_timesheet_readonly],
    'vhr_timesheet.view_vhr_ts_monthly_tree':    [vhr_dept_admin, vhr_cb_timesheet, vhr_ts_approver,vhr_cb_manager,vhr_dept_head,vhr_cb_timesheet_readonly],
    #Summary
    'vhr_timesheet.view_vhr_employee_timesheet_summary_tree':      [vhr_cb_timesheet, vhr_cb_manager],
    'vhr_timesheet.view_vhr_employee_timesheet_summary_form':      [vhr_cb_timesheet, vhr_cb_manager],
    'vhr_timesheet.view_vhr_employee_timesheet_summary_search':      [vhr_cb_timesheet, vhr_cb_manager],
    #Working Group
    'vhr_timesheet.view_vhr_ts_working_group_tree':      [vhr_cb_admin,vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_ts_working_group_form':      [vhr_cb_admin,vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_ts_working_group_search':      [vhr_cb_admin,vhr_cb_timesheet],
    #Working Shift
    'vhr_timesheet.view_vhr_ts_working_shift_tree':      [vhr_cb_admin,vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_ts_working_shift_form':      [vhr_cb_admin,vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_ts_working_shift_search':      [vhr_cb_admin,vhr_cb_timesheet],
    #Type Of Workday
    'vhr_timesheet.view_vhr_ts_type_workday_tree':      [vhr_cb_admin,vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_ts_type_workday_form':      [vhr_cb_admin,vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_ts_type_workday_search':      [vhr_cb_admin,vhr_cb_timesheet],
    #Type Of Cs Shift
    'vhr_timesheet.view_vhr_ts_type_cs_shift_tree':      [vhr_cb_admin,vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_ts_type_cs_shift_form':      [vhr_cb_admin,vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_ts_type_cs_shift_search':      [vhr_cb_admin,vhr_cb_timesheet],
    #Parameter Type
    'vhr_timesheet.view_vhr_ts_param_type_tree':      [vhr_cb_admin,vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_ts_param_type_form':      [vhr_cb_admin,vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_ts_param_type_search':      [vhr_cb_admin,vhr_cb_timesheet],
    #Parameter Type Group
    'vhr_timesheet.view_vhr_ts_param_type_group_tree':      [vhr_cb_admin,vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_ts_param_type_group_form':      [vhr_cb_admin,vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_ts_param_type_group_search':      [vhr_cb_admin,vhr_cb_timesheet],
    #General Parameter
    'vhr_timesheet.view_vhr_ts_general_param_tree':      [vhr_cb_admin,vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_ts_general_param_form':      [vhr_cb_admin,vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_ts_general_param_search':      [vhr_cb_admin,vhr_cb_timesheet],
    #Parameter By Job Level
    'vhr_timesheet.view_vhr_ts_param_job_level_tree':      [vhr_cb_admin,vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_ts_param_job_level_form':      [vhr_cb_admin,vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_ts_param_job_level_search':      [vhr_cb_admin,vhr_cb_timesheet],
    #Parameter By Working Schedule
    'vhr_timesheet.view_vhr_ts_param_working_schedule_tree':      [vhr_cb_admin,vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_ts_param_working_schedule_form':      [vhr_cb_admin,vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_ts_param_working_schedule_search':      [vhr_cb_admin,vhr_cb_timesheet],
    #Working Schedule
    'vhr_timesheet.view_vhr_ts_working_schedule_tree':      [vhr_cb_admin,vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_ts_working_schedule_form':      [vhr_cb_admin,vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_ts_working_schedule_search':      [vhr_cb_admin,vhr_cb_timesheet],
    
    #Working Schedule Group
    'vhr_timesheet.view_vhr_ts_working_schedule_group_tree':      [vhr_cb_admin,vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_ts_working_schedule_group_form':      [vhr_cb_admin,vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_ts_working_schedule_group_search':      [vhr_cb_admin,vhr_cb_timesheet],
    #Working Schedule Detail
    'vhr_timesheet.view_vhr_ts_ws_detail_tree':      [vhr_cb_admin, vhr_dept_admin,vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_ts_ws_detail_form':      [vhr_cb_admin, vhr_dept_admin,vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_ts_ws_detail_search':     [vhr_cb_admin, vhr_dept_admin,vhr_cb_timesheet],
     'vhr_timesheet.view_vhr_ts_ws_detail_calendar_extra':     [vhr_cb_admin, vhr_dept_admin,vhr_cb_timesheet],
    #Working Schedule Employee
    'vhr_timesheet.view_vhr_ts_ws_employee_tree':      [vhr_cb_admin,vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_ts_ws_employee_form':      [vhr_cb_admin,vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_ts_ws_employee_search':      [vhr_cb_admin,vhr_cb_timesheet],
    #Working Schedule-Working Group
    'vhr_timesheet.view_vhr_ts_working_schedule_working_group_form':      [vhr_cb_admin,vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_ts_working_schedule_working_group_tree':      [vhr_cb_admin,vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_ts_working_schedule_working_group_search':      [vhr_cb_admin,vhr_cb_timesheet],
     #Working Schedule Permission
    'vhr_timesheet.view_vhr_ts_working_schedule_permission_tree':      [vhr_cb_admin,vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_ts_working_schedule_permission_form':      [vhr_cb_admin,vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_ts_working_schedule_permission_search':      [vhr_cb_admin,vhr_cb_timesheet],
    #Timesheet
    'vhr_timesheet.view_vhr_ts_timesheet_form':      [vhr_cb_admin,vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_ts_timesheet_tree':      [vhr_cb_admin,vhr_hr_admin,vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_ts_timesheet_search':      [vhr_cb_admin,vhr_hr_admin,vhr_cb_timesheet],
    #Timesheet Period
    'vhr_timesheet.view_vhr_ts_timesheet_period_form':      [vhr_cb_admin,vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_ts_timesheet_period_tree':      [vhr_cb_admin,vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_ts_timesheet_period_search':      [vhr_cb_admin,vhr_cb_timesheet],
    #Timesheet Detail
    'vhr_timesheet.view_vhr_ts_timesheet_detail_form':      [vhr_cb_admin,vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_ts_timesheet_detail_tree':      [vhr_cb_admin,vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_ts_timesheet_detail_search':      [vhr_cb_admin,vhr_cb_timesheet],
    #Change Admin/Approve Timesheet Period
    'vhr_timesheet.vhr_ts_change_timesheet_detail_view':    [vhr_cb_admin,vhr_cb_timesheet],
    #Timesheet Employee
    'vhr_timesheet.view_vhr_ts_emp_timesheet_form':      [vhr_cb_admin,vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_ts_emp_timesheet_tree':      [vhr_cb_admin,vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_ts_emp_timesheet_search':      [vhr_cb_admin,vhr_cb_timesheet],
    #Leaves Type
    'vhr_timesheet.view_holidays_status_filter':      [group_user],
    'vhr_timesheet.edit_holiday_status_form':      [vhr_cb_admin, vhr_cb_timesheet],
    'vhr_timesheet.view_holiday_status_tree':      [group_user],
    'vhr_timesheet.view_holiday_status_tree_simple': [group_user],
    'hr_holidays.view_holidays_status_filter':     [group_user],
    'hr_holidays.view_holiday_status_normal_tree': [group_user],
    'hr_holidays.view_hr_holidays_status_search':  [group_user],
    
    #Leaves Type Group
    'vhr_timesheet.edit_holiday_status_group_form':      [vhr_cb_admin, vhr_cb_timesheet],
    'vhr_timesheet.view_holiday_status_group_tree':      [vhr_cb_admin, vhr_cb_timesheet],
    'vhr_timesheet.view_hr_holidays_status_group_search':      [vhr_cb_admin, vhr_cb_timesheet],
    #Public Holiday
    'vhr_timesheet.view_vhr_public_holiday_tree':      [vhr_cb_admin, vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_public_holiday_form':      [vhr_cb_admin, vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_public_holiday_calendar':      [vhr_cb_admin, vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_public_holiday_search':      [vhr_cb_admin, vhr_cb_timesheet],
    #Public Holiday Type
    'vhr_timesheet.view_vhr_public_holidays_type_filter':      [vhr_cb_admin, vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_public_holidays_type_form':      [vhr_cb_admin, vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_public_holidays_type_tree':      [vhr_cb_admin, vhr_cb_timesheet],
    #Public Holiday Template
    'vhr_timesheet.view_vhr_public_holiday_tree_template':      [vhr_cb_admin, vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_public_holiday_form_template':      [vhr_cb_admin, vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_public_holiday_calendar_extra':      [vhr_cb_admin, vhr_cb_timesheet],
    #Meeting Type
    'calendar.view_calendar_event_type_tree':                   [vhr_cb_admin],
    #Other wizard view
    'vhr_timesheet.account_vhr_holidays_execute_workflow_view':               [group_user],
    
    #Timesheet Detail Progress
    'vhr_timesheet.view_vhr_ts_detail_dashboard_tree':               [vhr_dept_admin, vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_ts_detail_dashboard_form':               [vhr_dept_admin, vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_ts_detail_dashboard_search':             [vhr_dept_admin, vhr_cb_timesheet],
    #Timesheet Detail Progress
    'vhr_timesheet.view_vhr_ts_summary_dashboard_tree':               [vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_ts_summary_dashboard_form':               [vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_ts_summary_dashboard_search':             [vhr_cb_timesheet],
    
    'vhr_timesheet.view_vhr_ts_working_schedule_employee_wizard_access':             [vhr_cb_admin,vhr_cb_timesheet],
    'vhr_timesheet.view_vhr_ts_working_schedule_employee_wizard_input':             [vhr_cb_admin,vhr_cb_timesheet],
    
    'vhr_timesheet.view_vhr_ts_timesheet_period_copy_form':         [group_user],
    'vhr_timesheet.vhr_ts_generate_timesheet_detail_view':          [group_user],
    
    'vhr_master_data.view_vhr_delegate_model_view_form':                                       [vhr_cb_timesheet],
    'vhr_master_data.view_vhr_delegate_model_view_tree':                                       [vhr_cb_timesheet],
    'vhr_master_data.view_vhr_delegate_model_view_search':                                [vhr_cb_timesheet],
        }




