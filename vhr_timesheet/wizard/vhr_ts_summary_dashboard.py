# -*- coding: utf-8 -*-

from openerp.osv import osv, fields


class vhr_ts_summary_dashboard(osv.osv):
    _name = 'vhr.ts.summary.dashboard'

    _columns = {
        'year': fields.integer('Year'),
        'month': fields.integer('Month'),
        'department_id': fields.many2one('hr.department', 'Department'),
        'number_of_employee': fields.integer('Number of Employee'),
        'generated': fields.integer('Generated'),
        'unsaved': fields.integer('Unsaved'),
        'saved': fields.integer('Saved'),
        'state': fields.selection([('unfinish', 'Unfinished'), ('finish', 'Finished')], 'State'),

    }

    _defaults = {
        'state': 'unfinish'
    }

    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False,
                   lazy=True):
        if 'year' in fields:
            fields.remove('year')
        if 'month' in fields:
            fields.remove('month')
        return super(vhr_ts_summary_dashboard, self).read_group(cr, uid, domain, fields, groupby, offset, limit,
                                                                context, orderby, lazy)


vhr_ts_summary_dashboard()