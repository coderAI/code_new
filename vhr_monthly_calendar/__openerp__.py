{
    'name': 'VHR Web Month Calendar',
    'version': '1.0',
    'category': 'web',
    'complexity': "easy",
    'description': """
Extra web feature
=================
* Calendar
usage:

    """,
    'author': 'HRS - MIS',
    'website': 'http://openerp.com',
    'depends': ['vhr_web_calendar',
                ],
    'data': [],
    'installable': True,
    'active': False,
    'data': ['views/templates.xml', ],
    'qweb': [
        "static/src/xml/*.xml",
    ],
}