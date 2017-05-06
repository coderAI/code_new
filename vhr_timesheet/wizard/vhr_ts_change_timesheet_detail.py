# -*- coding: utf-8 -*-

from datetime import datetime
from dateutil.relativedelta import relativedelta

from openerp.osv import osv, fields
from openerp.tools.translate import _


class vhr_ts_change_timesheet_detail(osv.osv_memory):
    _name = 'vhr.ts.change.timesheet.detail'

    _columns = {
        'timesheet_id': fields.many2one('vhr.ts.timesheet', 'Timesheet'),
        'current_admin_id': fields.many2one('hr.employee', 'Current Admin'),
        'current_approve_id': fields.many2one('hr.employee', 'Current Approver'),
        'new_admin_id': fields.many2one('hr.employee', 'New Admin'),
        'new_approve_id': fields.many2one('hr.employee', 'New Approve'),
        'from_month_year': fields.char('From month/year', size=32),
        'to_month_year': fields.char('To month/year', size=32),
        'year': fields.integer('Year'),
        'is_salary_calculation': fields.boolean('Is Salary Calculation'),
    }

    _defaults = {
        'from_month_year': '%s' % datetime.now().strftime("%m/%Y"),
        'to_month_year': '%s' % datetime.now().strftime("12/%Y"),
        'is_salary_calculation': True,
    }

    def onchange_timesheet(self, cr, uid, ids, timesheet_id, from_month_year, context=None):
        res = {'value': {'current_admin_id': False, 'current_approve_id': False}}
        detail_obj = self.pool.get('vhr.ts.timesheet.detail')
        today = datetime.now()

        month = today.month
        year = today.year
        if from_month_year:
            month, year = self.validate_month_year(from_month_year, 'From')
        if timesheet_id:
            detail_ids = detail_obj.search(cr, uid,
                                           [('timesheet_id', '=', timesheet_id),
                                            ('month', '=', month),
                                            ('year', '=', year)])

            if detail_ids:
                data = detail_obj.browse(cr, uid, detail_ids[0])
                res['value']['current_admin_id'] = data.admin_id and data.admin_id.id or False
                res['value']['current_approve_id'] = data.approve_id and data.approve_id.id or False
            else:
                res['value']['timesheet_id'] = False
                res['warning'] = {'title': _('Validation Error !'),
                                  'message': _('Timesheet haven\'t set any Timesheet Period in %s !' % from_month_year)}
        return res

    def validate_month_year(self, month_year, message='From'):
        try:
            month_year = month_year.split('/')
            month = int(month_year[0])
            year = int(month_year[1])
        except Exception, e:
            raise osv.except_osv(_('Validation Error !'),
                                 _(
                                     'Please input %s format mm/yyyy, month in 1 - 12 and year must be > 2003 !' % message))
        if month > 12 or month < 1 or year < 2004:
            raise osv.except_osv(_('Validation Error !'),
                                 _(
                                     'Please input %s format mm/yyyy, month in 1 - 12 and year must be > 2003 !' % message))
        return month, year

    def execute(self, cr, uid, ids, context=None):
        if not ids:
            return True
        obj = self.browse(cr, uid, ids[0])
        from_month_year = obj.from_month_year
        to_month_year = obj.to_month_year
        is_salary_calculation = obj.is_salary_calculation
        detail_obj = self.pool.get('vhr.ts.timesheet.detail')

        from_month, from_year = self.validate_month_year(from_month_year, 'From')
        to_month, to_year = self.validate_month_year(to_month_year, 'To')
        if not obj.new_admin_id and not obj.new_approve_id:
            raise osv.except_osv(_('Validation Error !'),
                                 _('Please select either New Admin or New Approve!'))
        to_date = datetime(to_year, to_month, 1)
        from_date = datetime(from_year, from_month, 1)
        if to_date < from_date:
            raise osv.except_osv(_('Validation Error !'),
                                 _('To month/year must be >= From month/year!'))
        all_detail_ids = []
        while from_date <= to_date:
            detail_ids = detail_obj.search(cr, uid,
                                           [('timesheet_id', '=', obj.timesheet_id.id),
                                            ('month', '=', from_date.month),
                                            ('year', '=', from_date.year)])
            if detail_ids:
                all_detail_ids.extend(detail_ids)
                admin_id = obj.new_admin_id and obj.new_admin_id.id or False
                approve_id = obj.new_approve_id and obj.new_approve_id.id or False
                vals = {'is_salary_calculation': is_salary_calculation}
                if admin_id:
                    vals['admin_id'] = admin_id
                if approve_id:
                    vals['approve_id'] = approve_id
                detail_obj.write(cr, uid, detail_ids, vals)
            from_date += relativedelta(months=1)
        if not all_detail_ids:
            raise osv.except_osv(_('Validation Error !'),
                                 _('Timesheet haven\'t set any Timesheet Period in %s - %s !' % (
                                     obj.from_month_year, obj.to_month_year)))
        return {
            'name': 'Timesheet Detail',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'vhr.ts.timesheet.detail',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', all_detail_ids)],
            'context': context,
        }