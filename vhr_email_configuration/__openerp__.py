{
    "name": "VHR Email Configuration",
    "version": "1.0",
    "author": "MIS",
    "category": "VHR",
    "summary": "Email Configuration",
    "depends": [
        "email_template",
    ],
    "website": "http://www.hrs.com.vn",
    "init_xml": [],
    "demo_xml": [],
    "data": [
        # security
        # data
        # wizard
        # view
        "views/email_template_view.xml",
        "views/vhr_email_group_view.xml",

        'security/ir.model.access.csv',
        # menu
    ],
    "css": ["static/src/css/style.css"],
    "active": True,
    "installable": True,
}
