# -*- coding: utf-8 -*-
from datetime import datetime
from dateutil.relativedelta import relativedelta

from openerp.osv import osv, fields
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT


class vhr_ts_timesheet_period_copy(osv.osv_memory):
    _name = 'vhr.ts.timesheet.period.copy'

    _columns = {
                'copy_to_next_month': fields.boolean('Copy to Next Month'),
                'copy_to_next_year': fields.boolean('Copy to Next Year'),
                'month_from': fields.integer('Month From'),
                'month_to': fields.integer('Month To'),
    }
    
    _defaults = {
        'copy_to_next_month': True,
        'month_from': 1,
        'month_to': 12,
    }
    
    def onchange_copy_to_year(self, cr, uid, ids, next_year, context=None):
        if next_year:
            return {'value': {'copy_to_next_month': False}}
        else:
            return {'value': {'copy_to_next_month': True}}
        return {'value': {}}

    def onchange_copy_to_month(self, cr, uid, ids, next_month, context=None):
        if next_month:
            return {'value': {'copy_to_next_year': False}}
        else:
            return {'value': {'copy_to_next_year': True}}
        return {'value': {}}
    
    def check_correct_month(self, cr, uid, month_from, month_to, context=None):
        if month_from and month_to:
            if month_from <1 or month_from >12 or month_to <1 or month_to >12:
                raise osv.except_osv(_('Validation Error !'),
                                     _('Month have to greater than or equal to 1 and lower or equal 12 !'))
            elif month_to < month_from:
                raise osv.except_osv(_('Validation Error !'),
                                     _('Month To have to greater than or equal to Month From !'))
        return True
                
            
    def btn_copy(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        context['rule_for_tree_form'] = True
        context['duplicate'] = False
        active_model = self.pool.get(context.get('active_model'))
        
        obj = self.browse(cr, uid, ids[0], context=context)
        copy_to_next_month = obj.copy_to_next_month
        copy_to_next_year = obj.copy_to_next_year
        month_from = obj.month_from
        month_to = obj.month_to
        self.check_correct_month(cr, uid, month_from, month_to, context)
        month = 0
        year = 0
        domain = []
        if not copy_to_next_month and not copy_to_next_year:
            raise osv.except_osv(_('Validation Error !'),
                                     _('You need to select at least one option before continuing !'))
        active_ids = context.get('active_ids')
        if active_ids:
            timesheet_ids = []
            for active_id in active_ids:
                data = active_model.copy_data(cr, uid, active_id, context=context)
                if copy_to_next_year:
                    year = data['year'] + 1
                    for month in xrange(month_from, month_to + 1):
                        self.copy_next_month(cr, uid, data, copy_to_next_month, month, year, context)
                else:
                    self.copy_next_month(cr, uid, data, copy_to_next_month, month, year, context)
                    year = data.get('year')
                    month = data.get('month')

            if year:
                domain.append(('year', '=', year))
            if copy_to_next_year:
                new_domain = []
                for month in xrange(month_from, month_to + 1):
                    new_domain.append(('month', '=', month))
                for i in xrange(month_from, month_to):
                    new_domain.insert(0,'|')
                domain.extend(new_domain)
            else:
                domain.append(('month', '=', month))
            return {
                'name': 'Timesheet Period',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': context.get('active_model'),
                'view_id': False,
                'type': 'ir.actions.act_window',
                'domain': domain,
                'context': context,
            }
            
    def copy_next_month(self, cr, uid, data, copy_to_next_month, month, year, context=None):
        active_model = self.pool.get(context.get('active_model'))
        from_date = datetime.strptime(data['from_date'], DEFAULT_SERVER_DATE_FORMAT)
        to_date = datetime.strptime(data['to_date'], DEFAULT_SERVER_DATE_FORMAT)
        
        if not copy_to_next_month:
            if to_date.month < from_date.month:
                diff_month = to_date.month + 12 - from_date.month
            else:
                diff_month = to_date.month - from_date.month
            #from_date = old_from_date.days/month/year - diff_month
            from_date = from_date + relativedelta(month=month, year=year) - relativedelta(months=diff_month)
            #to_date = old_to_date.days/month/year
            to_date = to_date + relativedelta(month=month, year=year)
            data['month'] = month
            data['year'] = year
        else:
            from_date = from_date + relativedelta(months=1)
            to_date = to_date + relativedelta(months=1)
            month = data['month']
            year = data['year']
            data['month'], data['year'] = self.get_next_month_year(month, year)

        data['audit_log_ids'] = []
        data['description'] = ''
        data['from_date'] = from_date.strftime(DEFAULT_SERVER_DATE_FORMAT)
        data['to_date'] = to_date.strftime(DEFAULT_SERVER_DATE_FORMAT)
        data['close_date'] = active_model.get_close_date(cr, uid, data['to_date'])
        data['name'] = active_model.get_period_name(cr, uid, data['from_date'], data['to_date'], context)
        
        if not active_model.search(cr, uid,[('from_date', '=', data['from_date']), ('to_date', '=', data['to_date'])]):
            active_model.create(cr, uid, data, context=context)
        return True

    def get_next_month_year(self, month, year):
        year = 12 < 1 + month and year + 1 or year
        month = 12 < month + 1 and 1 or month + 1
        return month, year


vhr_ts_timesheet_period_copy()
