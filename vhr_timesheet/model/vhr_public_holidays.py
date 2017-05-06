# -*- coding: utf-8 -*-

from datetime import datetime

from openerp.osv import osv, fields
from openerp.tools.translate import _


class vhr_public_holidays(osv.osv):
    _name = 'vhr.public.holidays'
    _description = 'VHR Public Holidays'
    _order = 'date asc'

    def _get_day_of_week(self, cr, uid, ids, field_name, arg, context=None):
        """Returns day of week of this holiday."""
        res = {}
        for i in ids:
            hday = self.browse(cr, uid, i, context=context)
            res[i] = datetime.strptime(hday.date, "%Y-%m-%d").strftime('%A')
        return res

    def _get_year(self, cr, uid, ids, field_name, arg, context=None):
        """Returns day of week of this holiday."""
        res = {}
        for i in ids:
            res[i] = {'year': '', 'month': ''}
            hday = self.browse(cr, uid, i, context=context)
            res[i]['year'] = datetime.strptime(hday.date, "%Y-%m-%d").year
            res[i]['month'] = datetime.strptime(hday.date, "%Y-%m-%d").month
        return res

    _columns = {
        'name': fields.char('Name', size=64),
        'date': fields.date('Date', required=1),
        'company_id': fields.many2one('res.company', 'Company'),
        'country_id': fields.many2one('res.country', 'Country'),
        'template_holidays': fields.boolean('Template Holidays'),
        'color_name': fields.related('type_id', 'color_name', string='Color in report'),
        'weekday': fields.function(_get_day_of_week,
                                   type='char',
                                   method=True,
                                   string='Day of the Week'),
        'year': fields.function(_get_year,
                                type='integer',
                                method=True,
                                string='Year of Holiday',
                                store=True,
                                multi='date'),
        'month': fields.function(_get_year,
                                 type='integer',
                                 method=True,
                                 string='Month of Holiday',
                                 store=True,
                                 multi='date'),
        'type_id': fields.many2one('vhr.public.holidays.type', 'Public Holiday Type', ondelete='restrict'),

    }

    _defaults = {
        'country_id': lambda self, cr, uid, context:
        self.pool.get('res.country').search(cr, uid, [('code', '=', 'VN')])[0]
    }

    _sql_constraints = [
        ('company_holiday_by_country_unique', 'unique(date,company_id,country_id)',
         _("You cannot have two holidays in same date of company by country in a year!")),
    ]

    def default_get(self, cr, uid, fields, context=None):
        res = super(vhr_public_holidays, self).default_get(cr, uid, fields, context=context)
        country_ids = self.pool.get('res.country').search(cr, uid, [('code', '=', 'VN')])
        if country_ids:
            res['country_id'] = country_ids[0]
        company_ids = self.pool.get('res.company').search(cr, uid, [('is_member', '=', False)], order="id asc")
        if company_ids:
            res['company_id'] = company_ids[0]
        return res

    def create(self, cr, uid, vals, context=None):
        return super(vhr_public_holidays, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        return super(vhr_public_holidays, self).write(cr, uid, ids, vals, context=context)


vhr_public_holidays()
