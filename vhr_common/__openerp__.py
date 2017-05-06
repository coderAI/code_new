# -*- encoding: utf-8 -*-

{
    "name": "HRS Common",
    "version": "1.0",
    "author": "MIS",
    "category": "HRS",
    'summary': 'HR Common',
    "depends": [
        'base',
        'vhr_base',
    ],
    'description': """
HR Common
===========================================================================

This module will include utilities functions using for all HR module.
""",
    "init_xml": [],
    "demo_xml": [],
    "data": [
             
             #views
             'views/vhr_mass_status_detail_view.xml',
             'views/vhr_mass_status_view.xml',
             'views/vhr_import_status.xml',
             
             
             #security
             'security/ir.model.access.csv',
             ],
    "active": True,
    "installable": True,
}
