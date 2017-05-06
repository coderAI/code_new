# -*- encoding: utf-8 -*-

{
    "name": "HRS Base",
    "version": "1.0",
    "author": "MIS",
    "category": "HRS",
    'sequence': 19,
    'summary': 'HRS Base',
    "depends": [
        "base",
        "audittrail",
        "pentaho_reports",
        'hr'
    ],
    'description': """
VHR Base
=======================================================================================

This module will inherit from base module. This is built to use for all module in HRS.
All customize modules should be inherited it.

Add option "validate_number" to validate field char in view with accept char 0 1 2 3 4 5 6 7 8 9 , ; - + () 
  example: options="{'validate_number': True}"
  
Add option "validate_email" to validate email in view of field char  
  example: options="{'validate_email': True}"
  
Add option "validate_phone" to validate email in view of field char  
  example: options="{'validate_phone': True}"

Add option "validate_date_number" to validate date number in range 1- 31
  example: options="{'validate_date_number': True}"
  
Add option "validate_mm_yyyy" to validate string like mm/yyyy :  12/2014
  example: options="{'validate_mm_yyyy': True}"

Add option "integer_number" to validate email in view of field Integer  
  example: options="{'integer_number': True}"
  
Add option "name_by_file" to dowload correct file name with binary field when save in tree view of field one2many
  example: name_by_file = '1'
  
Add to context: hide_form_view_button to hide button Save/Create/Discard.. in form view.
  example: In ir.actions.act_window, add <field name="context">{'hide_form_view_button':True}</field> 

Add option "show_zero" in float field to show value zero like 0, 0.0, 0.00 ...

Add option duplicate to hide default duplicate button in Section <More> of form view
  example: <form string="Test" version="7.0" duplicate='false'>

Add option to context in action_window to have similar attribute like <form string="" create="false" edit="false" delete="false">
In action to open view add context, remember to add 'rule_for_tree_form': True first
    <field name="context">{'rule_for_tree_form': True, 'create': False, 'edit': False, 'delete': False}</field>
    
Add option to context for disable some item in menu More: Execute/ Approve/ Return /Reject
In action to open view add context, remember to add 'rule_for_tree_form': True first
    <field name="context">{'rule_for_tree_form': True, 'approve': False, 'return': False, 'execute': False}</field>

Add new operator for domain in xml: not indexOf, indexOf
example:
attrs="{'readonly': [('check_text', 'indexOf', 'pro_ranking_level_id_new')]}"

==> fields contain above attrs will be readonly when field 'check_text' have string 'pro_ranking_level_id_new'

Add option for context for disable some item in Sidebar (More/Attachment/Print)
In action to open view add context, remember to add 'rule_for_tree_form': True first
----------------Remember to config in javascript first::: call function remove_toolbar_section(option,name)
    <field name="context">{'rule_for_tree_form': True, 'attachment': False}</field>
    
    
Add new widget limit_float_time:
    Allow to input 1,2,4 number, then function will auto convert to type hh:mm.
                 *     1 number: ex 1 = 01:00
                 *  2 number: ex 12 = 12:00
                 *  4 number: ex 1221 = 12:21
                 * Allow to input with type hh:mm
                 *Auto check time must in range 00:00 -- 23:59
                 
Make link download with field data  options='{"file_download": 1, "field_data": "datas"}' 
    + field_data : field binary save in database

NG: Add option to set color value of field in form view and list view based on condition. Option syntax is similar like option set color for tree view:
    Ex:    colors="blue:job_level_id_new !=job_level_id_old"
    Watch form view of vhr.employee.temp and vhr.working.record for more information.

Add  widget="number_separator" to auto separator number 

Add class for header of Listview with colclass
    Ex:  <tree>
            <field name='field_name' colclass='className'/>
            ...
        </tree>

Trigger change_field for field one2many ir.attachment by set option trigger_on_change='True' for field 'datas'
""",
    "init_xml": [],
    "demo_xml": [],
    "data": [
        # security
        'security/vhr_base_security.xml',
        'security/ir.model.access.csv',
        # data
        'data/audittrail_data.xml',
        # wizard
        # view
        'views/base/ir_cron_view.xml',
        'views/base/ir_module_view.xml',
        'views/audittrail_view.xml',
        'views/ir_config_parameter_view.xml',
        'views/pentaho_reports/report_prompt.xml',
        'views/email_template_view.xml',

        'static/src/xml/vhr_base.xml',
        # menu
    ],
    'qweb': [
        'static/src/xml/templates.xml',
    ],
    "active": False,
    "installable": True,
}
