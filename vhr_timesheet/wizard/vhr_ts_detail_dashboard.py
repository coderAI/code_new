# -*- coding: utf-8 -*-

from openerp.osv import osv, fields


class vhr_ts_detail_dashboard(osv.osv):
    _name = 'vhr.ts.detail.dashboard'

    _columns = {
        'year': fields.integer('Year'),
        'month': fields.integer('Month'),
        'timesheet_id': fields.many2one('vhr.ts.timesheet', 'Timesheet'),
        'number_of_employee': fields.integer('Number of Employee'),
        'generated': fields.integer('Generated'),
        'draft': fields.integer('Draft'),
        'sent': fields.integer('Sent'),
        'approve': fields.integer('Approved'),
        'reject': fields.integer('Rejected'),
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
        return super(vhr_ts_detail_dashboard, self).read_group(cr, uid, domain, fields, groupby, offset, limit, context,
                                                               orderby, lazy)


vhr_ts_detail_dashboard()