# -*- coding: utf-8 -*-

import logging

from openerp.osv import osv, fields
from openerp.addons.vhr_common.model.vhr_common import vhr_common
from openerp.tools.translate import _


log = logging.getLogger(__name__)


class vhr_family_deduct_line(osv.osv, vhr_common):
    _name = 'vhr.family.deduct.line'
    _description = 'VHR Family Deduct Line'

    _order = 'id desc'

    _columns = {
        'family_deduct_id': fields.many2one('vhr.family.deduct', 'Family Deduct', ondelete='cascade'),
        'employee_partner_id': fields.many2one('vhr.employee.partner', 'Employee Relation'),
        'employee_id': fields.related('employee_partner_id', 'employee_id', type='many2one', relation='hr.employee',
                                      string='Employee'),
        'name': fields.related('employee_partner_id', 'name', type='char', string='Name', size=128, store=True),
        'from_date': fields.date("From Date"),
        'effect_payroll_date': fields.date("Payroll Date"),
        'to_date': fields.date('To Date'),
        'notes': fields.text('Notes'),
        'attached_file': fields.binary('Attached File'),
        'name_data': fields.char('Name Data', size=255),
    }

    # Raise error if have record of same employee have overlap effect_from-effect_to
    def check_overlap_date(self, cr, uid, ids, context=None):
        if ids:
            for data in self.read(cr, uid, ids, ['employee_id', 'employee_partner_id', 'effect_payroll_date', 'to_date']):

                employee_id = data.get('employee_id', False) and data['employee_id'][0]
                employee_partner_id = data.get('employee_partner_id', False) and data['employee_partner_id'][0]
                effect_payroll_date = data.get('effect_payroll_date', False)
                to_date = data.get('to_date', False)

                all_deduct_ids = self.search(cr, uid, [('employee_id', '=', employee_id),
                                                       ('employee_partner_id', '=', employee_partner_id)])
                if not all_deduct_ids:
                    return True

                if not to_date:
                    not_overlap_deduct_ids = self.search(cr, uid, [('employee_id', '=', employee_id),
                                                                   ('employee_partner_id', '=', employee_partner_id),
                                                                   ('to_date', '<', effect_payroll_date)])
                else:
                    not_overlap_deduct_ids = self.search(cr, uid, [('employee_id', '=', employee_id),
                                                                   ('employee_partner_id', '=', employee_partner_id),
                                                                   '|', ('effect_payroll_date', '>', to_date),
                                                                   ('to_date', '<', effect_payroll_date)])
                # Record not overlap is the record link to employee
                if len(all_deduct_ids) == len(not_overlap_deduct_ids):
                    return True
                else:
                    # Get records from working_ids not in not_overlap_working_ids
                    overlap_ids = [x for x in all_deduct_ids if x not in not_overlap_deduct_ids]
                    # Get records from working_ids are not working_id
                    overlap_ids = [x for x in overlap_ids if x != data.get('id')]
                    # If have record overlap with current record
                    if overlap_ids:
                        raise osv.except_osv('Validation Error !',
                                             'The date duration of %s is overlapped. Please check again !'
                                             % (employee_partner_id and data['employee_partner_id'][1] or ''))
            return True

    def check_dates(self, cr, uid, ids, context=None):
        if ids:
            for period in self.read(cr, uid, ids, ['from_date', 'to_date'], context=context):
                if period['from_date'] and period['to_date'] and period['from_date'] > period['to_date']:
                    raise osv.except_osv('Validation Error !',
                                         'In Family Deduct, To Date must be greater than or equal to From Date !')

        return True

    def onchange_date(self, cr, uid, ids, from_date, effect_payroll_date, to_date, context=None):
        res = {'value': {}}
        if from_date and not effect_payroll_date:
            res['value']['effect_payroll_date'] = from_date
        if from_date and to_date:
            compare = self.compare_day(from_date, to_date)
            if compare < 0:
                res['warning'] = {'title': _('Warning'),
                                  'message': _('To Date must be greater than or equal to From Date !')}
                res['value'] = {'to_date': False}
        if from_date and effect_payroll_date:
            compare = self.compare_day(from_date, effect_payroll_date)
            if compare < 0:
                res['warning'] = {'title': _('Warning'),
                                  'message': _('Payroll Date must be greater than or equal to From Date !')}
                res['value'] = {'effect_payroll_date': False}
        if to_date and effect_payroll_date:
            compare = self.compare_day(effect_payroll_date, to_date)
            if compare < 0:
                res['warning'] = {'title': _('Warning'),
                                  'message': _('To Date must be greater than or equal to Payroll Date !')}
                res['value'] = {'to_date': False}

        return res

    def create(self, cr, uid, vals, context=None):
        res = super(vhr_family_deduct_line, self).create(cr, uid, vals, context)

        if res:
            self.check_dates(cr, uid, [res], context)

        return res

    def write(self, cr, uid, ids, vals, context=None):
        res = super(vhr_family_deduct_line, self).write(cr, uid, ids, vals, context)

        if res and vals.get('from_date', False) or vals.get('to_date', False) or vals.get('employee_partner_id', False):
            self.check_dates(cr, uid, ids, context)

        return res

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_family_deduct_line, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res


vhr_family_deduct_line()