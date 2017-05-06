# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT



log = logging.getLogger(__name__)


class vhr_duty_free(osv.osv):
    _name = 'vhr.duty.free'
    _description = 'VHR Duty Free'

    _columns = {
        'name': fields.char('Name', size=128),
        'employee_id': fields.many2one('hr.employee', 'Employee'),
        'department_id': fields.related('employee_id', 'department_id', type='many2one',
                                        relation='hr.department', string='Department'),
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

    def _check_dates(self, cr, uid, ids, context=None):
        for period in self.read(cr, uid, ids, ['from_date', 'to_date'], context=context):
            if period['from_date'] and period['to_date'] and period['from_date'] > period['to_date']:
                return False
        return True

    def _check_span_date(self, cr, uid, ids, context=None):
        duty_obj = self.pool.get('vhr.duty.free')
        cur_duty = duty_obj.browse(cr, uid, ids[0])
        emp_id = cur_duty and cur_duty.employee_id.id or -1
        duty_ids = duty_obj.search(cr, uid, [('employee_id', 'in', [emp_id])])
        if ids[0] in duty_ids:
            duty_ids.remove(ids[0])

        from_date = cur_duty.from_date
        to_date = cur_duty.to_date
        all_duty_frees = self.read(cr, uid, duty_ids, ['from_date', 'to_date'])
        for item in all_duty_frees:
            if (item['from_date'] <= to_date and item['from_date'] >= from_date or
                            item['to_date'] <= to_date and item['to_date'] >= from_date):
                return False
        return True

    _constraints = [
        (_check_dates, '\n\nTo date must be greater than or equal to From date !', ['from_date', 'to_date']),
        (_check_span_date, '\n\nOverlap time: From date - To Date !', ['from_date', 'to_date']),
    ]

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        args_new = args
        ids = self.search(cr, uid, args_new, 0, None, None, context)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(vhr_duty_free, self).name_search(cr, uid, name, args, operator, context, limit)
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if not context:
            context = {}
              
        return super(vhr_duty_free, self).search(cr, uid, args, offset, limit, order, context, count)

    def name_get(self, cr, uid, ids, context=None):
        if not ids or False in ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        reads = self.read(cr, uid, ids, ['employee_id'], context=context)
        res = []
        for record in reads:
            if 'employee_id' in record and isinstance(record['employee_id'], tuple):
                name = record['employee_id'][1]
                res.append((record['id'], name))
        return res

    def onchange_employee_id(self, cr, uid, ids, employee_id, context=None):
        res = {}
        if employee_id:
            employee = self.pool.get('hr.employee').read(cr, uid, employee_id, ['department_id'])
            department_id = employee.get('department_id', False)
            res['department_id'] = department_id and department_id[0] or False

        return {'value': res}

    def onchange_selected_date(self, cr, uid, ids, from_date, to_date, context=None):
        if from_date and to_date:
            time_delta = datetime.strptime(to_date, DEFAULT_SERVER_DATE_FORMAT) - datetime.strptime(from_date, DEFAULT_SERVER_DATE_FORMAT)
            day_delta = time_delta.days
            if day_delta < 0:
                warning = {'title': 'Validation Error!', 'message': 'To date must be greater than or equal to From date!'}
                return {'value': {'to_date': None}, 'warning': warning}
        return {'value': {}}

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_duty_free, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res


vhr_duty_free()