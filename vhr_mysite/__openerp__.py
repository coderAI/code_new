{
    'name': 'Mysite',
    'category': 'Website',
    'summary': 'The Users own page',
    'version': '1.0',
    'description': """
The Users own page
=============

        """,
    'author': 'MIS',
    'depends': ['website', 'hr',
                'vhr_human_resource',
                # 'vhr_payroll',
                'vhr_timesheet'
                ],
    'demo': [
    ],
    'data': [
         # security
        'security/vhr_mysite_security.xml',
        'security/ir.model.access.csv',

        # data
        'data/website_menu_data.xml',
        'data/ir_sequence/total_income_sequence.xml',
        'data/ir_sequence/vhr_payslip_sequence.xml',
        'data/ir_sequence/year_end_bonus_sequence.xml',
        'data/ir_cron_data.xml',
        'data/email_template/update_employee_info_email.xml',
        'data/ir_config_parameter.xml',
        'data/email_template/vhr_insurance_registration_email.xml',
        'data/email_template/notify_employee_liabilities_email.xml',
        'data/report/report_bootstrap_style_data.xml',
        'data/report/report_paper_format_data.xml',

        # wizard

        # view
        'view/vhr_employee_temp_view.xml',
        'view/vhr_employee_temp_quick_edit_view.xml',
        'view/vhr_total_income_view.xml',
        'view/vhr_payslip_view.xml',
        'view/update_employee_info.xml',
        'view/vhr_year_end_bonus_view.xml',
        'view/vhr_tax_settlement_view.xml',

        'view/insurance/vhr_insurance_period_view.xml',
        'view/insurance/vhr_insurance_registration_view.xml',
        'view/insurance/vhr_insurance_package_view.xml',
        'view/insurance/vhr_insurance_employee_family_view.xml',

        'view/vhr_employee_coordinate_view.xml',

        'view/account/vhr_liability_view.xml',

        # views
        'views/personal/vhr_mysite_extra_info_template.xml',
        'views/personal/vhr_mysite_temp_info_template.xml',
        'views/personal/vhr_mysite_history_template.xml',
        'views/personal/vhr_mysite_quick_edit_template.xml',
        'views/personal/update_employee_info.xml',

        'views/salary/vhr_mysite_total_income.xml',
        'views/salary/vhr_mysite_payslip.xml',
        'views/salary/vhr_mysite_year_end_bonus.xml',
        'views/salary/vhr_mysite_benefit.xml',

        'views/tax/vhr_mysite_tax_settlement_template.xml',

        'views/recruitment/vhr_mysite_recruitment_request_template.xml',

        'views/timesheet/vhr_mysite_leave.xml',
        'views/timesheet/vhr_mysite_leave_registration.xml',
        'views/timesheet/vhr_mysite_ot.xml',
        'views/timesheet/vhr_mysite_ot_registration.xml',

        'views/hr/vhr_mysite_termination.xml',
        'views/hr/vhr_mysite_termination_list.xml',
        'views/hr/vhr_mysite_insurance_registration.xml',

        # 'views/hr/vhr_mysite_orgchart.xml',

        # 'views/loan/vhr_mysite_loan.xml',
        # 'views/loan/vhr_mysite_loan_form.xml',

        'views/account/vhr_mysite_liability.xml',
        'views/account/vhr_mysite_liability_form.xml',

        'views/payroll/modal_template.xml',
        'views/payroll/vhr_mysite_collaborator_assessment.xml',
        'views/allowance/vhr_mysite_allowance_request.xml',        

        'views/vhr_mysite_employee_coordinate.xml',
        'views/vhr_mysite_coordinate_summary.xml',

        'views/vhr_mysite_sidebar_template.xml',
        'views/vhr_mysite_search_template.xml',
        'views/vhr_mysite_login_template.xml',
        'views/vhr_mysite_templates.xml',

        'views/salary/vhr_mysite_benefit_salary.xml',

        # menu
        'menu/ir_ui_menu.xml',

        # wizard
        'wizard/account/vhr_send_email_liability_confirmation_wizard_view.xml',

        # security view
        'security/view/vhr_mysite_view_security.xml',
        'security/audittrail_rule.xml',
        # report
        'report/tax_settlement/tax_settlement_report.xml',
        'report/tax_settlement/tax_settlement_docx_report.xml',
        'report/payslip/payslip_report.xml',
    ],
    'qweb': ['static/src/xml/base.xml'],
    'installable': True,
}
