# -*- coding: utf-8 -*-

import logging

from openerp.osv import osv, fields


log = logging.getLogger(__name__)


class vhr_salary_setting(osv.osv):
    _name = 'vhr.salary.setting'
    _description = 'VHR Salary Setting'

    _columns = {
        'code': fields.char('Code', size=64),
        'name': fields.char('Name', size=128),
        'salary_type_id': fields.many2one('vhr.dimension', 'Salary Type', ondelete='restrict',
                                     domain=[('dimension_type_id.code', '=', 'SALARY_TYPE'), ('active','=',True)]),
        'note': fields.text('Note'),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                          domain=[('object_id.model', '=', _name),
                                                  ('field_id.name', 'not in',
                                                   ['write_date', 'audit_log_ids'])]),
        'active': fields.boolean('Active'),
        'is_meal': fields.boolean("Is Meal"),
    }
    
    _order = 'name asc'
    
    _defaults = {
        'active': True
    }

    _unique_insensitive_constraints = [{'code': "Salary Setting's Code is already exist!"},
                                       {'name': "Salary Setting's Name is already exist!"}]

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        args_new = ['|', ('name', operator, name), ('code', operator, name)] + args
        ids = self.search(cr, uid, args_new)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(vhr_salary_setting, self).name_search(cr, uid, name, args, operator, context, limit)

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_salary_setting, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res

vhr_salary_setting()