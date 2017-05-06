# -*- coding: utf-8 -*-

from openerp.osv import osv, fields


class vhr_ts_type_workday(osv.osv):
    _name = 'vhr.ts.type.workday'

    _columns = {
        'code': fields.char('Code', size=64),
        'name': fields.char('Name', size=64),
        'coef': fields.float('Coef', digits=(16, 1)),
    }


_unique_insensitive_constraints = [{'code': "Workday Type's Code is already exist!"},
                                   {'name': "Workday Type's Vietnamese Name is already exist!"}]

vhr_ts_type_workday()