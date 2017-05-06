# -*- coding: utf-8 -*-

import logging

from openerp.osv import osv, fields

from openerp.tools.translate import _

log = logging.getLogger(__name__)


class vhr_salary_level_detail(osv.osv):
    _name = 'vhr.salary.level.detail'
    _description = 'VHR Salary Level Detail'
    
    _columns = {
        'name': fields.char('Name', size=128),
        'salary_level_id': fields.many2one('vhr.salary.level', 'Salary Level', ondelete='restrict'),
        'salary_from': fields.float('Salary From'),
        'salary_to': fields.float('Salary To'),
        'effective_date': fields.date('Effective Date'),
        'active': fields.boolean('Active'),
        'description': fields.text('Description'),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                          domain=[('object_id.model', '=', _name),
                                                  ('field_id.name', 'not in',
                                                   ['write_date', 'audit_log_ids'])]),
    }

    _defaults = {
        'active': True,
    }
    
    _unique_insensitive_constraints = [{'salary_level_id': "Salary Level and Effective Date already exist!",
                                        'effective_date': "Salary Level and Effective Date already exist!"
                                        }]

    def create(self, cr, uid, vals, context=None):
        if not 'salary_from' in vals or not 'salary_to' in vals:
            raise osv.except_osv(_('Error!'), _('Missing value for Salary From or Salary To'))
        if vals['salary_from'] < 0 or vals['salary_to'] < 0:
            raise osv.except_osv(_('Validate Error!'), _('Salary must be greater than 0!'))
        if vals['salary_from'] >= vals['salary_to']:
            raise osv.except_osv(_('Validate Error!'), _('Salary From must be lower than Salary To!'))

        return super(vhr_salary_level_detail, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        for res_id in ids:
            if 'salary_from' in vals:
                salary_from = vals['salary_from']
            else:
                salary_from = self.browse(cr, uid, res_id, fields_process=['salary_from']).salary_from
            if 'salary_to' in vals:
                salary_to = vals['salary_to']
            else:
                salary_to = self.browse(cr, uid, res_id, fields_process=['salary_to']).salary_to
            if salary_from < 0 or salary_to < 0:
                raise osv.except_osv(_('Validate Error!'), _('Salary must be greater than 0!'))
            if salary_from >= salary_to:
                raise osv.except_osv(_('Validate Error!'), _('Salary From must be lower than Salary To!'))

        return super(vhr_salary_level_detail, self).write(cr, uid, ids, vals, context=context)

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_salary_level_detail, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', _('You cannot delete the record(s) which reference to others !'))
        return res

    def copy_data(self, cr, uid, id, default, context=None):
        """
        Handle when user duplicate record constraints unique will raise message.
        We del effective_date in data it will be alright.
        :param cr:
        :param uid:
        :param id:
        :param default:
        :param context:
        :return: dictionary of data without 'effective_date' key
        """
        data = super(vhr_salary_level_detail, self).copy_data(cr, uid, id, default, context=context)
        if 'effective_date' in data:
            del data['effective_date']
        return data


vhr_salary_level_detail()