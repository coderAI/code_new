# -*- coding: utf-8 -*-
import logging
from datetime import datetime

from openerp.addons.vhr_common.model.vhr_common import vhr_common
from openerp.osv import osv, fields
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp import SUPERUSER_ID

log = logging.getLogger(__name__)


class vhr_ts_timesheet(osv.osv, vhr_common):
    _name = 'vhr.ts.timesheet'
    
    
    def _get_latest_generation(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        monthly_pool = self.pool.get('vhr.ts.monthly')
        for timesheet_id in ids:
            monthly_ids = monthly_pool.search(cr, uid, [('timesheet_id','=',timesheet_id)],limit=1, order='write_date DESC', context={'get_all': True})
            if monthly_ids:
                meta_datas = monthly_pool.perm_read(cr, SUPERUSER_ID, monthly_ids, context)
                result[timesheet_id] = meta_datas and meta_datas[0].get('write_date', False)
        
        return result
    
    def _get_update_timesheet(self, cr, uid, ids, context=None):
        timesheet_ids = []
        if ids:
            months = self.pool.get('vhr.ts.monthly').read(cr, uid, ids, ['timesheet_id'])
            timesheet_ids = [record['timesheet_id'][0] for record in months]
        
        return timesheet_ids
    
    def _get_employees(self, cr, uid, ids, name, args, context=None):
        result = {}
        emp_sheet_pool = self.pool.get('vhr.ts.emp.timesheet')
        for timesheet_id in ids:
            lines = []
            emp_timesheet_ids = emp_sheet_pool.search(cr, uid, [('active','=',True),('timesheet_id','=',timesheet_id)])
            if emp_timesheet_ids:
                emp_timesheets = emp_sheet_pool.read(cr, uid, emp_timesheet_ids, ['employee_id'])
                for emp in emp_timesheets:
                    employee_id = emp.get('employee_id', False) and emp['employee_id'][0] or False
                    if employee_id:
                        lines.append(employee_id)
            result[timesheet_id] = lines
        return result
        
    _columns = {
        'code': fields.char('Code', size=64),
        'name': fields.char('Vietnamese Name', size=128),
        'name_en': fields.char('English Name', size=128),
        'active': fields.boolean('Active'),
        'effect_from': fields.date('Effective From'),
        'effect_to': fields.date('Effective To'),
        'description': fields.text('Description'),
        'latest_generation': fields.datetime('Last Generation Date'),
        'detail_ids': fields.one2many('vhr.ts.timesheet.detail', 'timesheet_id', 'Details'),
#         'employees': fields.many2many('hr.employee', 'vhr_ts_emp_timesheet', 'timesheet_id',
#                                       'employee_id', 'Employees'),
                
        'employees': fields.function(_get_employees, relation='hr.employee', type="many2many", string='Employees'),   
             
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                         domain=[('object_id.model', '=', _name),
                                                 ('field_id.name', 'not in', ['write_date', 'audit_log_ids'])]),

    }

    _defaults = {
    }

    _order = "name asc, effect_from desc"

    _unique_insensitive_constraints = [{'code': "Timesheet's Code is already exist!"},
                                       {'name': "Timesheet's Vietnamese Name is already exist!"}]

    def onchange_date(self, cr, uid, ids, effect_from, effect_to, context=None):
        res = {'value': {}, 'warning': {}}
        if effect_from and effect_to:
            if effect_from > effect_to:
                res['warning']['title'] = _('Validation Error !'),
                res['warning']['message'] = _('Effect To must be greater than Effect From!')
                res['value']['effect_to'] = ''
        if effect_from <= datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT) and (
                    not effect_to or effect_to >= datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT)):
            res['value']['active'] = True
        else:
            res['value']['active'] = False
        return res

    def cron_active_record(self, cr, uid, context=None):
        log.info('vhr_ts_timesheet cron_active_record start')
        active_record_ids, inactive_record_ids = self.update_active_of_record_in_object_cm(cr, uid, 'vhr.ts.timesheet')
        
        #If have timesheet is inactive, check to remove timesheet detail have effect_from > effect_to of timesheet
#         if inactive_record_ids:
#             self.remove_expire_timesheet_detail(cr, uid, inactive_record_ids, context)
            
        log.info('vhr_ts_timesheet cron_active_record end')
        return True

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if context.get('timesheet_admin'):
            args_new = ['|', '|', ('code', operator, name), ('name_en', operator, name),
                        ('name', operator, name)] + args
            ids = self.search(cr, uid, args_new, offset=0, limit=limit, order=None, context=context, count=False)
            return self.name_get(cr, uid, ids)
        return super(vhr_ts_timesheet, self).name_search(cr, uid, name, args, operator, context, limit)

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        # Search rule for specific menu
        if context is None:
            context = {}
        if context.get('timesheet_admin'):
            context['active_test'] = False
            if context.get('month',False) and context.get('year',False):
                groups = self.pool.get('res.users').get_groups(cr, uid)
                special_groups = ['hrs_group_system', 'vhr_cb']
                
                year = context.get('year',False)
                month = context.get('month',False)
                ts_detail_obj = self.pool.get('vhr.ts.timesheet.detail')
                domain = [  ('month', '=', month), ('year', '=', year) ]
                if context.get('filter_by_admin_id',False):
                    #If context have admin_id filter it
                    domain.append(('admin_id', '=', context['filter_by_admin_id']))
                elif not set(special_groups).intersection(set(groups)):
                    #Filter by login user
                    domain.append(('admin_id.user_id.id', '=', uid))
                    
                detail_ids = ts_detail_obj.search(cr, uid, domain)
                ts_ids = [timesheet.get('timesheet_id')[0] for timesheet in
                          ts_detail_obj.read(cr, uid, detail_ids, ['timesheet_id']) if timesheet.get('timesheet_id')]
                args += [('id', 'in', ts_ids)]
            else:
                args += [('id', 'in', [])]

        return super(vhr_ts_timesheet, self).search(cr, uid, args, offset, limit, order, context, count)
    
    
    def write(self, cr, uid, ids, vals, context=None):
        res = super(vhr_ts_timesheet, self).write(cr, uid, ids, vals, context)
        
        if res and vals.get('effect_from',False) or vals.get('effect_to',False):
            self.remove_expire_timesheet_detail(cr, uid, ids, context)
        
        return res
    
    
    def remove_expire_timesheet_detail(self, cr, uid, ids, context=None):
        '''
        Remove timesheet detail have effect_from > effect_to of timesheet
        '''
        if not isinstance(ids, list):
            ids = [ids]
        ts_detail_pool = self.pool.get('vhr.ts.timesheet.detail')
        for record in self.read(cr, uid, ids, ['effect_to']):
            effect_to = record.get('effect_to', False)
            if effect_to:
                expire_detail_ids = ts_detail_pool.search(cr, uid, [('from_date','>',effect_to),
                                                                    ('timesheet_id','=',record['id'])])
                if expire_detail_ids:
                    ts_detail_pool.unlink(cr, uid, expire_detail_ids)
        
        return True

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        try:
            return super(vhr_ts_timesheet, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        
        
    


vhr_ts_timesheet()