{
    'name': 'VHR Web Calendar',
    'version': '1.0',
    'category': 'web',
    'complexity': "easy",
    'description': """
Extra web feature
=================
* Calendar
usage:

# Views
<record model="ir.ui.view" id="view_vhr_public_holiday_calendar_extra">
    <field name="name">view.vhr.public.holidays.line.calendar</field>
    <field name="model">vhr.public.holidays</field>
    <field name="type">hrs_calendar</field>
    <field name="arch" type="xml">
        <hrs_calendar is_display_sun="true" is_display_sat="false" field_date="date" message="Message Ex" >
            <field name="type_id"/>
        </hrs_calendar>
    </field>
</record>

# Action View
<record model="ir.actions.act_window.view" id="action_open_public_holidays_calendar_extra">
            <field name="sequence" eval="1"/>
            <field name="view_mode">hrs_calendar</field>
            <field name="view_id" ref="view_vhr_public_holiday_calendar_extra"/>
            <field name="act_window_id" ref="action_open_public_holidays_this_year"/>
</record>

Note:
is_display_sun: Display color to indicate Sunday
is_display_sat: Display color to indicate Saturday
field_date: field name type date in object
message: message you want user to notice when action.

*** <field name="type_id"/> input field will be mark in calendar
    object of this field must contain some field below:
        - name
        - code
        - color_name

*** Should write default_get method.

    """,
    'author': 'hrs - MIS',
    'website': 'http://openerp.com',
    'depends': ['web',
                'vhr_master_data',],
    'data': [],
    'installable': True,
    'active': False,
    'data': ['views/templates.xml', ],
    'qweb': [
        "static/src/xml/*.xml",
    ],
}