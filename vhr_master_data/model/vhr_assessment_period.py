# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields



log = logging.getLogger(__name__)


class vhr_assessment_period(osv.osv):

    _name = 'vhr.assessment.period'
    _description = 'Assessment Period'
    _order = 'from_date desc'
    _columns = {
        'name': fields.char('Name', size=64),
        'from_date': fields.date('From Date'),
        'to_date': fields.date('To Date'),
        'description': fields.text('Description'),
        'active': fields.boolean('Active'),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                          domain=[('object_id.model', '=', _name),
                                                  ('field_id.name', 'not in',
                                                   ['write_date', 'audit_log_ids'])]),
    }
    
    _defaults = {
        'active': True,
    }
    
    _unique_insensitive_constraints = [{'name': "Assessment Period's Name is already exist!"}]


    def _check_span_date(self, cr, uid, ids, context=None):
        period_obj = self.pool.get('vhr.assessment.period')
        period_ids = period_obj.search(cr, uid, [])
        if ids[0] in period_ids:
            period_ids.remove(ids[0])
        cur_period = period_obj.browse(cr, uid, ids[0])
        from_date = cur_period.from_date
        to_date = cur_period.to_date
        all_period_dates = self.read(cr, uid, period_ids, ['from_date', 'to_date'])
        for period in all_period_dates:
            if to_date >= period['from_date'] >= from_date or to_date >= period['to_date'] >= from_date:
                return False
        return True

    _constraints = [
        (_check_span_date, "Error ! The duration in period is overlapped. Please check again !", "")
    ]

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        args_new = [('name', operator, name)] + args
        ids = self.search(cr, uid, args_new)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(vhr_assessment_period, self).name_search(cr, uid, name, args, operator, context, limit)

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_assessment_period, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res


vhr_assessment_period()