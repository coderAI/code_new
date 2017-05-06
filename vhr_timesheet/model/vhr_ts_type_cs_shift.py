# -*- coding: utf-8 -*-

from openerp.osv import osv, fields


class vhr_ts_type_cs_shift(osv.osv):
    _name = 'vhr.ts.type.cs.shift'

    _columns = {
        'code': fields.char('Code', size=64),
        'name': fields.char('Name', size=64),
        'coef': fields.float('Coef', digits=(16, 1)),
    }


_unique_insensitive_constraints = [{'code': "Type CS Shift's Code is already exist!"},
                                   {'name': "Type CS Shift's Name is already exist!"}]

vhr_ts_type_cs_shift()