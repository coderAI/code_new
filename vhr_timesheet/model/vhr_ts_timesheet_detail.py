# -*- coding: utf-8 -*-
import logging
from datetime import datetime, timedelta

from openerp.osv import osv, fields
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp import SUPERUSER_ID

log = logging.getLogger(__name__)

class vhr_ts_timesheet_detail(osv.osv):
    _name = 'vhr.ts.timesheet.detail'

    _columns = {
        'name': fields.char('Name', size=128),
        'timesheet_id': fields.many2one('vhr.ts.timesheet', 'Timesheet', ondelete='restrict'),
        'latest_generation': fields.related('timesheet_id', 'latest_generation', type='datetime', string="Last Generation Date"),
        'from_date': fields.date('From Date'),
        'to_date': fields.date('To Date'),
        'close_date': fields.date('Close Date'),
        'month': fields.integer('Month'),
        'year': fields.integer('Year'),
        'admin_id': fields.many2one('hr.employee', 'Admin'),
        'approve_id': fields.many2one('hr.employee', 'Approver'),
        'timesheet_period_id': fields.many2one('vhr.ts.timesheet.period', 'Timesheet Period', ondelete='cascade'),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                         domain=[('object_id.model', '=', _name),
                                                 ('field_id.name', 'not in', ['write_date', 'audit_log_ids'])]),
        
        'is_salary_calculation': fields.boolean('Is Salary Calculation'),

    }
    _order = "from_date desc, admin_id asc"

    _defaults = {
                 'is_salary_calculation': True,
    }

    def _check_overlap(self, cr, uid, res_id, context=None):
        check_date = self.read(cr, uid, res_id, ['from_date', 'to_date', 'timesheet_id', 'close_date'], context=context)
        if check_date['from_date'] >= check_date['to_date']:
            raise osv.except_osv(_('Validation Error!'),
                                 _('To Date must be > From Date !'))
        timesheet = check_date['timesheet_id']
        overlap_ids = self.search(cr, uid,
                                  [
                                      ('id', '!=', res_id), ('timesheet_id', '=', timesheet[0]),
                                      '|', '|', '|',
                                      '&',
                                      ('from_date', '>=', check_date['from_date']),
                                      ('from_date', '<=', check_date['to_date']),
                                      '&',
                                      ('from_date', '<=', check_date['from_date']),
                                      ('to_date', '>=', check_date['from_date']),
                                      '&',
                                      ('to_date', '>=', check_date['from_date']),
                                      ('to_date', '<=', check_date['to_date']),
                                      '&',
                                      ('from_date', '<=', check_date['to_date']),
                                      ('to_date', '>=', check_date['to_date'])
                                  ])
        if overlap_ids:
            from_date = datetime.strptime(check_date['from_date'],DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y")
            to_date = datetime.strptime(check_date['to_date'],DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y")
            raise osv.except_osv('Validation Error!',
                                 'Timesheet setting of %s from %s to %s is overlapped!' % (
                                     timesheet[1], from_date, to_date))

    def get_close_date(self, cr, uid, to_date):
        value = self.pool.get('ir.config_parameter').get_param(cr, uid, 'ts.timesheet.detail.close.date.interval')
        try:
            value = int(value)
        except:
            value = 0
        return (datetime.strptime(to_date, DEFAULT_SERVER_DATE_FORMAT) + timedelta(
            days=value)).strftime(DEFAULT_SERVER_DATE_FORMAT)

    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False,
                   lazy=True):
        orderby = []
        if 'year' in groupby:
            orderby.append('year desc')
        if 'month' in groupby:
            orderby.append('month desc')
        if orderby:
            orderby = ', '.join(orderby)
            
        if 'year' in fields and 'year' not in groupby:
            fields.remove('year')
        if 'month' in fields and 'month' not in groupby:
            fields.remove('month')
        res =  super(vhr_ts_timesheet_detail, self).read_group(cr, uid, domain, fields, groupby, offset, limit, context,
                                                               orderby, lazy)
        
        if res and res[0] and res[0].get('year', False) and not res[0].get('year_count',False):
            for data in res:
                del (data['year'])
        if res and res[0] and res[0].get('month', False) and not res[0].get('month_count',False):
            for data in res:
                del (data['month'])
        
        return res

    def create(self, cr, uid, vals, context=None):
        if not context:
            context = {}
        res = super(vhr_ts_timesheet_detail, self).create(cr, uid, vals, context=context)
        if not context.get('do_not_check_overlap', False):
            self._check_overlap(cr, uid, res, context=context)
            self.update_group(cr, uid, context=context)
        return res

    def write(self, cr, uid, ids, vals, context=None):
        if not context:
            context = {}
        super(vhr_ts_timesheet_detail, self).write(cr, uid, ids, vals, context=context)
        if not context.get('do_not_check_overlap', False):
            for res_id in ids:
                self._check_overlap(cr, uid, res_id, context=context)
            self.update_group(cr, uid, context=context)
        return True

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        try:
            res = super(vhr_ts_timesheet_detail, self).unlink(cr, uid, ids, context=context)
            self.update_group(cr, uid, context=context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res

    def update_group(self, cr, uid, context=None):
        self.update_specific_group(cr, uid, 'vhr_master_data', 'vhr_dept_admin', 'admin_id', context)
        self.update_specific_group(cr, uid, 'vhr_timesheet', 'vhr_ts_approver', 'approve_id', context)
        
        return True
        
    def update_specific_group(self, cr, uid, module_group, group_name, assign_field, context=None):
        if not context:
            context = {}
            
        if module_group and group_name and assign_field:
            if context is None:
                context = {}
            if context.get('ignore', False):
                return True
            current_year = datetime.now().year
            current_month = datetime.now().month
            
            if context.get('month', False):
                current_month = int(context['month'])
            
            if context.get('year', False):
                current_year = int(context['year'])
            
            log.info('current_month = '+ str(current_month))
            log.info('current_year = '+ str(current_year))
            active_ids = self.search(cr, uid, [('year', '>=', current_year), ('month', '>=', current_month)])
            active_ids.append(0)
            sql = """
                SELECT
                  distinct R.user_id
                FROM hr_employee H
                  INNER JOIN vhr_ts_timesheet_detail D ON D.%s = H.id
                  INNER JOIN resource_resource R ON R.id = H.resource_id
                WHERE D.id IN %s
            """ % (assign_field, str(tuple(active_ids)).replace(',)', ')'))
            cr.execute(sql)
            res = cr.fetchall()
            admin_ids = [res_id[0] for res_id in res]

            groups_obj = self.pool.get('res.groups')
            m = self.pool.get('ir.model.data')
            dept_admin_id = m.get_object(cr, uid, module_group, group_name).id
            users = groups_obj.read(cr, SUPERUSER_ID, dept_admin_id, ['users'], context={'active_test': False}).get('users')
    
            remove_ids = [user_id for user_id in users if user_id not in admin_ids]
            add_ids = [user_id for user_id in admin_ids if user_id not in users]
            # just use sql for performance
            sql = ''
            if remove_ids:
                for user_id in remove_ids:
                    sql += '''delete from res_groups_users_rel where uid = %s and gid =%s;''' % (user_id, dept_admin_id)
            if add_ids:
                for user_id in add_ids:
                    sql += '''insert into res_groups_users_rel(uid,gid) values (%s,%s);''' % (user_id, dept_admin_id)
            if sql:
                cr.execute(sql)
            return True
            

    def onchange_close_date(self, cr, uid, ids, date_to, close_date, context=None):
        res = {'value': {}, 'warning': {}}
        if date_to and close_date and close_date < date_to:
            res['warning'] = {'title': _('Validation Error!'),
                              'message': _('Close Date must be >= To Date !')}
            res['value']['close_date'] = self.get_close_date(cr, uid, date_to)
        return res

    def onchange_date(self, cr, uid, ids, date_from, date_to, context=None):
        res = {'value': {}, 'warning': {}}
        if date_from and date_to:
            if date_to <= date_from:
                res['warning'] = {'title': _('Validation Error!'),
                                  'message': _('To Date must be > From Date !')}
        if date_to:
            res['value']['close_date'] = self.get_close_date(cr, uid, date_to)
        return res
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        #Search rule in staff movement
        if not context:
            context = {}
        if 'active_test' not in context:
            context['active_test'] = False
        res =  super(vhr_ts_timesheet_detail, self).search(cr, uid, args, offset, limit, order, context, count)
        return res


vhr_ts_timesheet_detail()