# -*- encoding: utf-8 -*-

{
    "name": "VHR Timesheet",
    "version": "1.0",
    "author": "MIS",
    "category": "VHR",
    'sequence': 19,
    'summary': 'Timesheet, Holidays, Allocation and Leave Requests',
    "depends": [
        'hr_holidays',
        'vhr_base',
        'vhr_master_data',
        'vhr_human_resource',
        'vhr_web_calendar',
        'vhr_monthly_calendar',
    ],
    "website": "http://www.hrs.com.vn",
    'description': """
Manage leaves and allocation requests
===========================================================================
""",
    "init_xml": [],
    "demo_xml": [],
    "data": [
        # security
        'security/vhr_timesheet_security.xml',
        'security/audittrail.rule.xml',
        # data
        'data/vhr_timehsheet_data.xml',
        'data/data_ir_rule.xml',
        'data/data_ir_cron.xml',
        'data/data_vhr_sequence.xml',
        'data/data_vhr_ts_param_type.xml',
        #'data/data_ir_config_parameter.xml',
        'data/vhr_timesheet_email_template.xml',
        'data/vhr_timesheet_fetch_mail.xml',
        'data/vhr_ts_overtime_email_template.xml',
        
        # views
        'views/vhr_holidays_view.xml',
        'views/vhr_holidays_annual_leave_view.xml',
        'views/vhr_holidays_status_view.xml',
        'views/vhr_holidays_status_group_view.xml',
        'views/vhr_public_holidays_view.xml',
        'views/vhr_public_holidays_type_view.xml',
        'views/vhr_ts_general_param_view.xml',
        'views/vhr_ts_param_type_group_view.xml',
        'views/vhr_ts_param_type_view.xml',
        'views/vhr_ts_param_job_level_view.xml',
        'views/vhr_ts_working_group_view.xml',
        'views/vhr_ts_working_schedule_group_view.xml',
        'views/vhr_ts_working_schedule_view.xml',
        'views/vhr_ts_param_working_schedule_view.xml',
        'views/vhr_ts_working_shift_view.xml',
        'views/vhr_ts_timesheet_view.xml',
        'views/vhr_ts_timesheet_period_view.xml',
        'views/vhr_ts_timesheet_detail_view.xml',

        'views/vhr_ts_overtime_detail_view.xml',
        'views/vhr_ts_overtime_view.xml',
        'views/vhr_ts_emp_timesheet_view.xml',

        'views/vhr_working_record_view.xml',
        'views/vhr_mass_movement_view.xml',
        'views/vhr_ts_ws_employee.xml',
        'views/vhr_ts_monthly_view.xml',
        'views/vhr_ts_ws_detail_view.xml',
        'views/vhr_ts_overtime_summarize_view.xml',
        'views/vhr_employee_timesheet_summary_view.xml',
        'views/vhr_ts_type_workday_view.xml',
        'views/vhr_ts_type_cs_shift_view.xml',
        'views/vhr_ts_working_schedule_working_group_view.xml',
        'views/vhr_timesheet_template_view.xml',
        'views/vhr_ts_working_schedule_permission_view.xml',
        'views/vhr_compensation_ot_payment_view.xml',
        'views/vhr_ts_lock_timesheet_detail_view.xml',
        'views/hr_department_view.xml',
        'views/hr_contract_view.xml',
        'views/vhr_delegate_view.xml',
        'views/vhr_ts_employee_expat_view.xml',
        
        # wizard
        'wizard/vhr_working_record_mass_movement_view.xml',
        'wizard/vhr_holidays_multi_view.xml',
        'wizard/vhr_ts_overtime_multi_view.xml',
        'wizard/vhr_ts_incremental_annual_leave_view.xml',
        'wizard/vhr_ts_employee_annual_leave_gen_view.xml',
        'wizard/vhr_ts_change_timesheet_detail_view.xml',
        'wizard/vhr_ts_detail_dashboard_view.xml',
        'wizard/vhr_ts_summmary_dashboard_view.xml',
        'wizard/vhr_ts_view_result_detail_view.xml',
        'wizard/vhr_ts_update_ot_summary_view.xml',
        'wizard/vhr_holidays_execute_workflow_view.xml',
        'wizard/vhr_ts_timesheet_period_copy_view.xml',
        'wizard/vhr_compensation_ot_payment_wizard_view.xml',
        'wizard/vhr_ts_working_schedule_employee_wizard.xml',
        'wizard/vhr_ts_lock_timesheet_detail_wizard_view.xml',
        'wizard/vhr_ts_monthly_gen_view.xml',
        
        # menu
        'menu/vhr_timesheet_menu.xml',
        'workflows/vhr_holidays_workflow.xml',
        # security apply for objects in wizard too
        'security/ir.model.access.csv',
        
        'data/data_function_migrate.xml',

    ],
    "qweb": ['static/src/xml/vhr_holidays_quick_search_view.xml', ],
    "active": False,
    "installable": True,
}
