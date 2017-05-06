# -*- coding: utf-8 -*-

from openerp.osv import osv, fields


class vhr_employee_timesheet_summary(osv.osv):
    _name = 'vhr.employee.timesheet.summary'

    _columns = {
        'name': fields.char('Name', size=64),
        'company_id': fields.many2one('res.company', 'Company'),
        'employee_id': fields.many2one('hr.employee', 'Employee', ondelete='restrict'),
        'employee_code': fields.related('employee_id', 'code', type="char", string="Employee Code"),
        'employee_login': fields.related('employee_id', 'login', type="char", string="Employee Domain"),
        'employee_name': fields.related('employee_id', 'name_related', type="char", string="Employee Name"),
        'department_id': fields.related('employee_id', 'department_id', type='many2one',
                                        relation='hr.department', string='Department', store=True),
        'timesheet_id': fields.many2one('vhr.ts.timesheet', 'Current Timesheet', ondelete='restrict'),
        'working_days': fields.float('Working Days', digits=(3, 1)),
        'night_shift_allowance_hours': fields.float('Night shift allowance hours', digits=(3, 1)),
        'haft_day_paid_leave': fields.float('Haft day paid leave', digits=(3, 1)),
        'adjust_haft_day_paid_leave': fields.float('Adjustment Haft day paid leave', digits=(3, 1)),
        'paid_leave': fields.float('Paid leave', digits=(3, 1)),
        'adjust_paid_leave': fields.float('Adjust paid leave', digits=(3, 1)),
        'total_paid_leave': fields.float('Total paid leave', digits=(3, 1)),
        'haft_day_unpaid_leave': fields.float('Haft day unpaid leave', digits=(3, 1)),
        'adjust_haft_day_unpaid_leave': fields.float('Adjust Haft day unpaid leave', digits=(3, 1)),
        'unpaid_leave': fields.float('Unpaid leave', digits=(3, 1)),
        'adjust_unpaid_leave': fields.float('Adjust unpaid leave', digits=(3, 1)),
        'total_unpaid_leave': fields.float('Total unpaid leave', digits=(3, 1)),
        'maternity_leave': fields.float('Maternity leave', digits=(3, 1)),
        'sick_leave_short': fields.float('Sick leave (SHORT) ', digits=(3, 1)),
        'sick_leave_long': fields.float('Sick leave (LONG)', digits=(3, 1)),
        'pregnancy_leave': fields.float('ST/KT Leave', digits=(3, 1)),
        'relax_leave': fields.float('Relax Leave', digits=(3, 1)),
        'other_leave': fields.float('Other Leave', digits=(3, 1)),
        'paid_days': fields.float('Paid days', digits=(3, 1)),
        'meal_days': fields.float('Meal days', digits=(3, 1)),
        'parking_days': fields.float('Parking days', digits=(3, 1)),
        'total_hours_working': fields.float('Total Working Hours', digits=(16, 1)),
        'month': fields.integer('Month'),
        'year': fields.integer('Year'),
        'state': fields.selection([('saved', 'Saved'), ('unsaved', 'Unsaved')], 'Status'),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                         domain=[('object_id.model', '=', _name),
                                                 ('field_id.name', 'not in', ['write_date', 'audit_log_ids'])]),
        
        'is_last_payment': fields.boolean('For Last Payment'),
        'termination_date': fields.date('Termination Date'),

    }

    _order = 'year desc, month desc, timesheet_id, employee_id desc'
    
    _defaults = {
        'state': 'unsaved',
    }

    def btn_save(self, cr, uid, context=None):
        active_ids = context.get('active_ids', False)
        if active_ids:
            self.write(cr, uid, active_ids, {'state': 'saved'}, context)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def build_domain_filter_timesheet(self, cr, uid, args, context):
        if context.get('filter_timesheet') and context.get('vhr_timesheet_ids'):
            args.append(('timesheet_id', 'in', context['vhr_timesheet_ids']))
        return args
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if not context:
            context = {}      
        #tuannh3: Fix return after gen summary
        args = self.build_domain_filter_timesheet(cr, uid, args, context) 
        if 'active_test' not in context:
            context['active_test'] = False
        ts_summary_ids = super(vhr_employee_timesheet_summary, self).search(cr, uid, args, offset=offset, limit=limit, order=order,context=context, count=count)
        return ts_summary_ids
    
    def _generate_m2o_order_by(self, order_field, query):
        """
        NG: Fix lại để order theo id của field many2one
        Add possibly missing JOIN to ``query`` and generate the ORDER BY clause for m2o fields,
        either native m2o fields or function/related fields that are stored, including
        intermediate JOINs for inheritance if required.

        :return: the qualified field name to use in an ORDER BY clause to sort by ``order_field``
        """
        import re
        regex_order = re.compile('^( *([a-z0-9:_]+|"[a-z0-9:_]+")( *desc| *asc)?( *, *|))+$', re.I)

        if order_field not in self._columns and order_field in self._inherit_fields:
            # also add missing joins for reaching the table containing the m2o field
            qualified_field = self._inherits_join_calc(order_field, query)
            order_field_column = self._inherit_fields[order_field][2]
        else:
            qualified_field = '"%s"."%s"' % (self._table, order_field)
            order_field_column = self._columns[order_field]

        assert order_field_column._type == 'many2one', 'Invalid field passed to _generate_m2o_order_by()'
        if not order_field_column._classic_write and not getattr(order_field_column, 'store', False):
            _logger.debug("Many2one function/related fields must be stored " \
                "to be used as ordering fields! Ignoring sorting for %s.%s",
                self._name, order_field)
            return

        # figure out the applicable order_by for the m2o
        dest_model = self.pool[order_field_column._obj]
#         m2o_order = dest_model._order
        m2o_order = 'id desc'
        if not regex_order.match(m2o_order):
            # _order is complex, can't use it here, so we default to _rec_name
            m2o_order = dest_model._rec_name
        else:
            # extract the field names, to be able to qualify them and add desc/asc
            m2o_order_list = []
            for order_part in m2o_order.split(","):
                m2o_order_list.append(order_part.strip().split(" ", 1)[0].strip())
            m2o_order = m2o_order_list

        # Join the dest m2o table if it's not joined yet. We use [LEFT] OUTER join here
        # as we don't want to exclude results that have NULL values for the m2o
        src_table, src_field = qualified_field.replace('"', '').split('.', 1)
        dst_alias, dst_alias_statement = query.add_join((src_table, dest_model._table, src_field, 'id', src_field), implicit=False, outer=True)
        qualify = lambda field: '"%s"."%s"' % (dst_alias, field)
        return map(qualify, m2o_order) if isinstance(m2o_order, list) else qualify(m2o_order)
    
    def open_logs(self, cr, uid, ids, context=None):
        model_obj = self.pool.get('ir.model')
        audit_log_obj = self.pool.get('audittrail.log')
        
        model_ids = model_obj.search(cr, uid, [('model','=',self._name)])
        audit_log_ids = audit_log_obj.search(cr, uid, [('res_id','in',ids),
                                                       ('object_id','in',model_ids)])
        
        return {
            'type': 'ir.actions.act_window',
            'name': "Logs",
            'view_type': 'form',
            'view_mode': 'tree,form',
            'views': [(False, 'tree'),
                      (False, 'form')],
            'res_model': 'audittrail.log',
            'context': context,
            'domain': [('id','in',audit_log_ids)],
            'target': 'current',
        }
        

    # for group by view
    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False, lazy=True):
        
        if 'year' in fields and 'year' not in groupby:
            fields.remove('year')
        if 'month' in fields and 'month' not in groupby:
            fields.remove('month')
        return super(vhr_employee_timesheet_summary, self).read_group(cr, uid, domain, fields, groupby, offset, limit, context,
                                                               orderby, lazy)
    
vhr_employee_timesheet_summary()
