# -*- coding: utf-8 -*-

from openerp.osv import osv, fields


class vhr_holidays_status_group(osv.osv):
    _name = 'vhr.holidays.status.group'
    _description = 'VHR Holiday Status Group'

    _columns = {
        'name': fields.char('Vietnamese Name', size=128),
        'name_en': fields.char('English Name', size=128),
        'code': fields.char('Code', size=64),
        'active': fields.boolean('Active'),
        'gender': fields.selection([('both', 'Both'), ('male', 'Male'), ('female', 'Female')], string='Gender'),
        'is_allow_to_register_from_now_to_next_year': fields.boolean('Is Allow To Register From Now To Next Year ?'),
        'is_check_remain_day_on_current_registration': fields.boolean('Is Only Check Remain days by current registration ?'),
    }

    _defaults = {
        'active': True,
        'gender': 'both',
    }

    _unique_insensitive_constraints = [{'name': "Vietnamese Holiday Group's name is already exist!"},
                                       {'code': "Holiday Group's code is already exist!"}, ]

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        try:
            return super(vhr_holidays_status_group, self).unlink(cr, uid, ids, context)
        except Exception as e:
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')


vhr_holidays_status_group()