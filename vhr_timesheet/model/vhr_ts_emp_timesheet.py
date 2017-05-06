# -*-coding:utf-8-*-
import logging

import simplejson as json

from datetime import datetime
from lxml import etree
from openerp.osv import osv, fields
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from dateutil.relativedelta import relativedelta
from openerp import SUPERUSER_ID
from openerp.addons.vhr_common.model.vhr_common import vhr_common

log = logging.getLogger(__name__)


class vhr_ts_emp_timesheet(osv.osv, vhr_common):
    _name = 'vhr.ts.emp.timesheet'
    _description = 'VHR TS Employee TimeSheet'
    
    
#     def is_create_from_working_record(self, cr, uid, ids, field_name, arg, context=None):
#         res = {}
#         if not isinstance(ids, list):
#             ids = [ids]
#             
#         for record_id in ids:
#             working_record_ids = self.pool.get('vhr.working.record').search(cr, uid, [('ts_emp_timesheet_id','=',record_id)])
#             if working_record_ids:
#                 res[record_id] = True
#             else:
#                 res[record_id] = False
#             
#         return res
    
    def _is_new_record(self, cr, uid, ids, field_name, arg, context=None):
        if not isinstance(ids, list):
            ids = [ids]
        res = {}
        for record_id in ids:
            res[record_id] = False
            
        return res
    
    def _get_contract_type(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        working_pool = self.pool.get('vhr.working.record')
        for record in self.read(cr, uid, ids, ['employee_id']):
            employee_id = record.get('employee_id', False) and record['employee_id'][0] or False
            if employee_id:
                contract_type_id = self.get_active_contract_type_of_employee(cr, uid, employee_id, context)
                result[record['id']] = contract_type_id
        
        return result
    
    def _get_update_employee(self, cr, uid, ids, context=None):
        '''Return list record of employees have new active working record'''
        res = []
        employee_ids = []
        for record in self.pool.get('vhr.working.record').read(cr, uid, ids, ['employee_id','active']):
            if record.get('active', False) and record.get('employee_id',False):
                employee_ids.append(record['employee_id'][0])
            
        if employee_ids:
            res = self.pool.get('vhr.ts.emp.timesheet').search(cr, uid, [('employee_id','in',employee_ids)])
        
        return res
    
    def _get_current_ws(self, cr, uid, ids, field_name, arg, context=None):
        if not isinstance(ids, list):
            ids = [ids]
        ts_ws_pool = self.pool.get('vhr.ts.ws.employee')
        res = {}
        for record in self.read(cr, uid, ids, ['employee_id']):
            res[record['id']] = False
            employee_id = record.get('employee_id', False) and record['employee_id'][0] or False
            if employee_id:
                active_ts_emp_ids = ts_ws_pool.search(cr, uid, [('employee_id','=',employee_id),('active','=',True)])
                if active_ts_emp_ids:
                    ts_emp = ts_ws_pool.read(cr, uid, active_ts_emp_ids[0], ['ws_id'])
                    ws_id = ts_emp.get('ws_id',False) and ts_emp['ws_id'][0] or False
                    res[record['id']] = ws_id
        
        return res
    
    _columns = {
               'name': fields.char('Name', size=128),
               'employee_id': fields.many2one('hr.employee', 'Employee', ondelete='restrict'),
               'employee_code': fields.related('employee_id', 'code', type="char", string="Employee Code"),
               'department_id': fields.related('employee_id', 'department_id', type='many2one', relation="hr.department", string="Department"),
               'company_id': fields.many2one('res.company', 'Company', ondelete='restrict'),
               'contract_type_id': fields.function(_get_contract_type, string='Contract Type', type='many2one',
                                          relation='hr.contract.type',store={'vhr.working.record':
                                                                (_get_update_employee,
                                                                 ['active'], 10)}),
               # 'department_id': fields.many2one('hr.department', 'Department', domain=[('organization_class_id.level','=', '3')], ondelete='restrict'),
               # 'ts_working_group_id': fields.many2one('vhr.ts.working.group', 'Working Group', ondelete='restrict'),
               'timesheet_id': fields.many2one('vhr.ts.timesheet', 'Timesheet', ondelete='restrict'),
               'is_movement': fields.boolean('Is Movement'),
#                'working_record_id': fields.many2one('vhr.working.record', 'Working Record', ondelete='cascade'),
               'effect_from': fields.date('Effective From'),
               'effect_to': fields.date('Effective To'),
               'active': fields.boolean('Active'),
               'current_working_schedule_id': fields.function(_get_current_ws, type='many2one', relation='vhr.ts.working.schedule', string="Current Working Schedule"),
               'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                          domain=[('object_id.model', '=', _name),
                                                  ('field_id.name', 'not in',
                                                   ['write_date', 'audit_log_ids'])]),
                
                'is_new': fields.function(_is_new_record, type='boolean',string="Is New"),
#                 'is_create_from_working_record': fields.function(is_create_from_working_record, type='boolean', string='Is Create From Working Record'),
    }
    
    _order = "effect_from desc"
    
#     def _get_default_company_id(self, cr, uid, context=None):
#         company_ids = self.pool.get('res.company').search(cr, uid, [('is_member', '=', False)], order="id asc")
#         if company_ids:
#             return company_ids[0]
# 
#         return False
    

    _defaults = {
#         'company_id': _get_default_company_id,
        'active': False,
        'is_new': True
    }
    
    _unique_insensitive_constraints = [{'employee_id': "Employee - Effective Date are already exist!",
#                                         'company_id': "Employee - Company - Effective Date are already exist!",
                                        'effect_from': "Employee - Effective Date are already exist!"
                                        }]
    
    def get_active_contract_type_of_employee(self, cr, uid, employee_id, context=None):
        contract_type_id = False
        working_pool = self.pool.get('vhr.working.record')
        working_ids = working_pool.search(cr, uid, [('employee_id','=',employee_id), ('active','=',True)])
        if working_ids:
            workings = working_pool.browse(cr, uid, working_ids, fields_process=['contract_id','company_id'])
            for working in workings:
                if contract_type_id and working.company_id and not working.company_id.is_member:
                    contract_type_id = working.contract_id and working.contract_id.type_id and working.contract_id.type_id.id or False
                elif not contract_type_id:
                    contract_type_id = working.contract_id and working.contract_id.type_id and working.contract_id.type_id.id or False
        
        return contract_type_id
        
    def onchange_employee_id(self, cr, uid, ids, employee_id, context=None):
        res = {'employee_code': False, 'contract_type_id': False, 'department_id': False}
        if employee_id:
            employee = self.pool.get('hr.employee').read(cr, uid, employee_id, ['code','department_id'])
            employee_code = employee.get('code','')
            res['employee_code'] = employee_code
            res['department_id'] = employee.get('department_id',False) and employee['department_id'][0] or False
            res['contract_type_id'] = self.get_active_contract_type_of_employee(cr, uid, employee_id, context)
        
        return {'value': res}
    
    def cron_update_ts_emp_timesheet_state(self, cr, uid, context=None):
        """
        Update state of record if satisfy condition of active
        Push data to employee from record just active
        """
        log.info("Start run cron: Update VHR TS Employee Timesheet ")
        active_record_ids, inactive_record_ids = self.update_active_of_record_in_object_cm(cr, uid, 'vhr.ts.emp.timesheet')
        
        if inactive_record_ids:
            check_timesheet_ids = []
            #Get timesheet from inactive emp timesheet
            for record in self.read(cr, uid, inactive_record_ids, ['timesheet_id']):
                timesheet_id = record.get('timesheet_id', False) and record['timesheet_id'][0] or False
                if timesheet_id and timesheet_id not in check_timesheet_ids:
                    check_timesheet_ids.append(timesheet_id)
            #Check if timesheet doesnt have any active emp timesheet, inactive that timeshet
            if check_timesheet_ids:
                inactive_timesheet_ids = []
                for timesheet_id in check_timesheet_ids:
                    active_timesheet_ids = self.search(cr, uid, [('timesheet_id','=',timesheet_id),('active','=',True)])
                    if not active_timesheet_ids:
                        inactive_timesheet_ids.append(timesheet_id)
                if inactive_timesheet_ids:
                    today = datetime.today().strftime(DEFAULT_SERVER_DATE_FORMAT)
                    self.pool.get('vhr.ts.timesheet').write(cr, uid, inactive_timesheet_ids, {'active': False, 'effect_to':today})
        
        log.info("End run cron: Update VHR TS Employee Timesheet ")
        return True
    
    def update_ts_emp_timesheet_state(self, cr, uid, ts_emp_ids, context=None):
        """
         Update state of all employee timesheet link to employee-company of input employee timesheet
         One employee at a company only have one employee timesheet is active
         Return list employee timesheet just active
        """
        if not context:
            context = {}
        context['do_not_update_ts_emp_timesheet_state'] = True
        dict_result = []
        list_unique = []
        if ts_emp_ids:
            ts_emp_records = self.read(cr, uid, ts_emp_ids, ['employee_id'])
            for ts_emp_record in ts_emp_records:
#                 company_id = ts_emp_record.get('company_id', False) and ts_emp_record['company_id'][0] or False
                employee_id = ts_emp_record.get('employee_id', False) and ts_emp_record['employee_id'][0] or False
                
                if employee_id not in list_unique:
                    list_unique.append( employee_id)
                    
        if list_unique:
            today = datetime.today().date()
            for unique_item in list_unique:
                
                 #Get Salary have active=False need to update active=True
                active_record_ids = self.search(cr, uid, [('employee_id','=',unique_item),
#                                                           ('company_id','=',unique_item[1]),
                                                          ('active','=',False),
                                                          ('effect_from','<=',today),
                                                          '|',('effect_to','=',False),
                                                              ('effect_to','>=',today)])
                
                 #Get Salary have active=True need to update active=False
                inactive_record_ids = self.search(cr, uid, [('employee_id','=',unique_item),
#                                                             ('company_id','=',unique_item[1]),
                                                            ('active','=',True),
                                                              '|',('effect_to','<',today),
                                                                  ('effect_from','>',today)])
        
                ts_emp_ids = inactive_record_ids + active_record_ids
                
                if ts_emp_ids:
                    self.update_active_of_record_cm(cr, uid, 'vhr.ts.emp.timesheet', ts_emp_ids)
                        
        return dict_result
    
    def update_nearest_ts_emp_timesheet(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        
        if not isinstance(ids, list):
            ids = [ids]
        
        if ids:
            context['do_not_update_ts_emp_timesheet_state'] = True
            context['do_not_update_nearest_ts_emp_timesheet'] = True
            records = self.read(cr, uid, ids, ['employee_id','effect_from'])
            for record in records:
                employee_id = record.get('employee_id',False) and record['employee_id'][0] or False
#                 company_id = record.get('company_id',False) and record['company_id'][0] or False
                current_effect_from = record.get('effect_from', False)
                if current_effect_from:
                    
                    #Update 
                    nearest_ts_emp_ids = self.search(cr, uid, [('employee_id','=',employee_id),
#                                                           ('company_id','=',company_id),
                                                          ('effect_from','<',current_effect_from)], 
                                                 order="effect_from desc")
                    
                    if nearest_ts_emp_ids:
                        current_effect_from = datetime.strptime(current_effect_from, DEFAULT_SERVER_DATE_FORMAT).date()
                        update_effect_to = current_effect_from - relativedelta(days=1)
                        update_effect_to = update_effect_to.strftime(DEFAULT_SERVER_DATE_FORMAT)
                        self.write_with_log(cr, uid, nearest_ts_emp_ids[0], {'effect_to':update_effect_to}, context)
            
            context['do_not_update_ts_emp_timesheet_state'] = False              
        return True
    
    def update_from_future_ts_emp_timesheet(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        
        if not isinstance(ids, list):
            ids = [ids]
        
        if ids:
            context['do_not_update_ts_emp_timesheet_state'] = True
            context['do_not_update_nearest_ts_emp_timesheet'] = True
            records = self.read(cr, uid, ids, ['employee_id','effect_from'])
            for record in records:
                employee_id = record.get('employee_id',False) and record['employee_id'][0] or False
#                 company_id = record.get('company_id',False) and record['company_id'][0] or False
                current_effect_from = record.get('effect_from', False)
                if current_effect_from:
                    #update effect_to of edit record if edit record in the past
                    larger_pr_ids = self.search(cr, uid, [('employee_id','=',employee_id),
#                                                           ('company_id','=',company_id),
                                                          ('effect_from','>',current_effect_from)], 
                                                 order="effect_from asc")
                    if larger_pr_ids:
                        larger_pr = self.read(cr, uid, larger_pr_ids[0],['effect_from'])
                        larger_effect_from = larger_pr.get('effect_from',False)
                        if larger_effect_from:
                            larger_effect_from = datetime.strptime(larger_effect_from, DEFAULT_SERVER_DATE_FORMAT).date()
                            update_effect_to = larger_effect_from - relativedelta(days=1)
                            update_effect_to = update_effect_to.strftime(DEFAULT_SERVER_DATE_FORMAT)
                            self.write(cr, uid, record.get('id',False), {'effect_to':update_effect_to}, context)
                            
        context['do_not_update_ts_emp_timesheet_state'] = False              
        return True
        
    #Cannot create record which effect_from overlap with date range effect_from -effect_to of record with same employee_id, company_id:
    def check_overlap_date(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        if ids:
            ts_emp = self.browse(cr, uid, ids[0], context)
            employee_id = ts_emp.employee_id and ts_emp.employee_id.id or False
#             company_id = ts_emp.company_id and ts_emp.company_id.id or False
            effect_from = ts_emp.effect_from
            effect_to = ts_emp.effect_to or False
            
            if employee_id:
                args = [('employee_id', '=', employee_id), 
#                         ('company_id', '=', company_id),
                        '|', ('active','=', False),
                             ('active','=', True)]
                
                ts_emp_ids = self.search(cr, uid, args)
                
                if not ts_emp_ids:
                    return True
                
                not_overlap_args = [('effect_to', '<', effect_from)] + args
                if effect_to:
                    not_overlap_args.insert(0,'|')
                    not_overlap_args.insert(1,('effect_from', '>', effect_to))
                
                not_overlap_ts_emp_ids = self.search(cr, uid, not_overlap_args)
                #Record not overlap is the record link to employee
                if len(ts_emp_ids) == len(not_overlap_ts_emp_ids):
                    return True
                else:
                    #Get records from working_ids not in not_overlap_working_ids
                    overlap_ids = [x for x in ts_emp_ids if x not in not_overlap_ts_emp_ids]
                    #Get records from working_ids are not working_id
                    overlap_ids = [x for x in overlap_ids if x not in ids]
                    if overlap_ids:
                        raise osv.except_osv('Validation Error !', 'The effective duration is overlapped. Please check again !')

        return True
    
    def check_dates(self, cr, uid, ids, context=None):
        for record in self.read(cr, uid, ids, ['effect_from', 'effect_to'], context=context):
            if record.get('effect_from',False) and record.get('effect_to',False) and record['effect_from'] > record['effect_to']:
                log.info("Record vhr.ts.emp.timesheet error: %s" % record['id'])
                raise osv.except_osv('Validation Error !', 'Effect To must be greater Effect From !')

        return True
    
    def create(self, cr, uid, vals, context=None):
        try:
            if not context:
                context = {}
            #When create record not update from rr, get probation salary from nearest record same emp-comp
            if context.get('create_from_movement',False):
                vals['is_movement'] = True
            res =  super(vhr_ts_emp_timesheet, self).create(cr, uid, vals, context)
            
            if res:
                context['name_object'] = 'employee timesheet'
                self.pool.get('vhr.holiday.line').check_if_date_after_summary_timesheet(cr, uid, vals['employee_id'], vals['effect_from'], context)
                self.update_nearest_ts_emp_timesheet(cr, uid, [res], context)
                self.update_from_future_ts_emp_timesheet(cr, uid, [res], context)
                self.check_overlap_date(cr, uid, [res], context)
                self.update_ts_emp_timesheet_state(cr, uid, [res], context)
            
            return res
        except Exception as e:
            log.exception(e)
            error_message = ''
            try:
                error_message = e.message
                if not error_message:
                    error_message = e.value
            except:
                error_message = ""
            raise osv.except_osv('Validation Error !', 'Have error during create employee timesheet:\n %s!' % error_message)
        
    def write(self, cr, uid, ids, vals, context=None):
        try:
            if not context:
                context = {}
            if not isinstance(ids, list):
                ids = [ids]
            
            if vals.get('effect_from', False):
                self.check_if_update_effect_from_out_of_box(cr, uid, ids, vals, context)
            
            old_datas = self.read(cr, uid, ids, ['timesheet_id','effect_from','effect_to'])
            
            res = super(vhr_ts_emp_timesheet, self).write(cr, uid, ids, vals, context)
            
            if res:
                if vals.get('effect_from',False) or vals.get('timesheet_id', False):
                    records = self.read(cr, uid, ids, ['employee_id','effect_from','timesheet_id'])
                    context['name_object'] = 'employee timesheet'
                    for record in records:
                        old_data = {}
                        for item in old_datas:
                            if item['id'] == record['id']:
                                old_data = item
                        old_timesheet_id = old_data.get('timesheet_id', False) and old_data['timesheet_id'][0]
                        new_timesheet_id = record.get('timesheet_id', False) and record['timesheet_id'][0]
                        employee_id = record.get('employee_id',False) and record['employee_id'][0]
                        effect_from = record.get('effect_from',False)
                        
                        if vals.get('effect_from', False) != old_data.get('effect_from', False) or old_timesheet_id != new_timesheet_id:
                            self.pool.get('vhr.holiday.line').check_if_date_after_summary_timesheet(cr, uid, employee_id, effect_from, context)
                    
                if vals.get('effect_to', False) or vals.get('effect_from',False):
                    self.check_dates(cr, uid, ids, context)
                    if vals.get('effect_from',False) and not context.get('do_not_update_nearest_ts_emp_timesheet', False):
                        self.update_nearest_ts_emp_timesheet(cr, uid, ids, context)
                        
                    self.check_overlap_date(cr, uid, ids, context)
                
#                 context['update_from_ts_empt_timesheet'] = True
#                 context['do_not_update_to_contract'] = True
                            
                if not context.get('do_not_update_ts_emp_timesheet_state', False):
                    self.update_ts_emp_timesheet_state(cr, uid, ids, context)
            return res
        
        except Exception as e:
            log.exception(e)
            error_message = ''
            try:
                error_message = e.message
                if not error_message:
                    error_message = e.value
            except:
                error_message = ""
            raise osv.except_osv('Validation Error !', 'Have error during update employee timesheet:\n %s!' % error_message)
    
    def check_if_update_effect_from_out_of_box(self, cr, uid, ids, vals, context=None):
        """
            when change effect_from < effect_from of nearest (lower) ET or  > effect_from of nearest (greater) ET
            ==> Raise error
        """
        if ids and vals.get('effect_from', False):
            new_effect_from = vals.get('effect_from', False)
            records = self.read(cr, uid, ids, ['effect_from','employee_id'])
            
            for record in records:
                employee_id = record.get('employee_id', False) and record['employee_id'][0] or False
                effect_from = record.get('effect_from', False)
                
                if employee_id and effect_from:
                    larger_ids = self.get_nearest_larger_record(cr, uid, employee_id, effect_from, context)
                    lower_ids = self.get_nearest_lower_record(cr, uid, employee_id, effect_from, context)
                    
                    #Compare effect_from with effect_from of nearest lower record
                    if lower_ids:
                        lower_record = self.read(cr, uid, lower_ids[0], ['effect_from'])
                        lower_effect_from = lower_record.get('effect_from', False)
                        if lower_effect_from and self.compare_day(new_effect_from, lower_effect_from) >0:
                            raise osv.except_osv('Validation Error !', 
                                                 "You cannot update effective date less than previous record's effective date ")
                    
                    #Compare effect_from with effect_from of nearest larger WR
                    if larger_ids:
                        larger_record = self.read(cr, uid, larger_ids[0], ['effect_from'])
                        larger_effect_from = larger_record.get('effect_from', False)
                        if larger_effect_from and self.compare_day(larger_effect_from, new_effect_from) >0:
                            raise osv.except_osv('Validation Error !', 
                                                 "You cannot update effective date greater than next record's effective date ")
                
        return True
    
    def get_nearest_larger_record(self, cr, uid, employee_id, effect_from, context=None):
        nearest_larger_record_ids = []
        if employee_id and effect_from:
            nearest_larger_record_ids = self.search(cr, uid, [('employee_id','=',employee_id),
                                                               ('effect_from','>',effect_from)], order='effect_from asc')
            
        return nearest_larger_record_ids
    
    def get_nearest_lower_record(self, cr, uid, employee_id, effect_from, context=None):
        nearest_lower_record_ids = []
        if employee_id and effect_from:
            nearest_lower_record_ids = self.search(cr, uid, [('employee_id','=',employee_id),
                                                               ('effect_from','<',effect_from)], order='effect_from desc')
            
        return nearest_lower_record_ids
            
            
    def name_get(self, cr, uid, ids, context=None):
        if not ids or False in ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        reads = self.read(cr, uid, ids, ['employee_id'], context=context)
        res = []
        for record in reads:
            name = record.get('employee_id',False) and record['employee_id'][1]
            res.append((record['id'], name))
        return res
    
    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        args_new = [('name', operator, name)] + args
        ids = self.search(cr, uid, args_new)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(vhr_ts_emp_timesheet, self).name_search(cr, uid, name, args, operator, context, limit)
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if not context:
            context = {}
            
        if 'active_test' not in context:
            context['active_test'] = False
        
        res =  super(vhr_ts_emp_timesheet, self).search(cr, uid, args, offset, limit, order, context, count)
        return res
    
    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False,
                   lazy=True):
        """
        Get the list of records in list view grouped by the given ``groupby`` fields
        """
        
        if not context:
            context = {}
        context['active_test'] = False

        res = super(vhr_ts_emp_timesheet, self).read_group(cr, uid, domain, fields, groupby, offset, limit, context, orderby,
                                                   lazy)
        
        return res

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        
        if not isinstance(ids, list):
            ids = [ids]
            
        res = False
        if ids:
            ts_detail_obj = self.pool.get('vhr.ts.timesheet.detail')
            records = self.read(cr, uid, ids, ['employee_id','effect_from','timesheet_id'])
            for record in records:
                employee_id = record.get('employee_id',False) and record['employee_id'][0] or False
                timesheet_id = record.get('timesheet_id',False) and record['timesheet_id'][0] or False
#                 company_id = record.get('company_id',False) and record['company_id'][0] or False
                effect_from = record.get('effect_from',False)
                
                if employee_id and effect_from:
                    
                    #Dont allow to delete if generated from effect_from
                    monthly_ids = self.pool.get('vhr.ts.monthly').search(cr, uid, [('employee_id','=',employee_id),
                                                                                   ('timesheet_id','=',timesheet_id),
                                                                                   ('date','>=',effect_from),
                                                                                   ('state','in',['sent','approve'])], context={'get_all': True})
                    if monthly_ids:
                        raise osv.except_osv('Error !',
                                         "You can't delete these records which related to Monthly records!")
                    
                    larger_pr_ids = self.search(cr, uid, [('employee_id','=',employee_id),
#                                                           ('company_id','=',company_id),
                                                          ('effect_from','>',effect_from)])
                
                    if larger_pr_ids:
                        raise osv.except_osv('Error !', 'You cannot delete records which are not last employee timesheets !')
                    
                    lower_pr_ids = self.search(cr, uid, [('employee_id','=',employee_id),
#                                                           ('company_id','=',company_id),
                                                          ('effect_from','<',effect_from)],order="effect_from desc")
                    
                    if not context.get('unlink_from_wr',False):
                        working_record_ids = []
#                         try:
                        working_pool = self.pool.get('vhr.working.record')
                        working_record_ids = working_pool.search(cr, uid, [('ts_emp_timesheet_id','=',record.get('id',False))])
                        if working_record_ids:
                            raise osv.except_osv('Validation Error !', 'You cannot delete records which related to Working Records !')
#                             working_pool.unlink(cr, uid, working_record_ids, {'unlink_from_ts_emp_timesheet':True})
#                         except Exception as e:
#                             log.exception(e)
#                             raise osv.except_osv('Error !',
#                                 'You cannot delete the record(s) which reference to Other Working Records %s'% str(working_record_ids))

                        
                    res = self.unlink_record(cr, uid, [record.get('id',False)], context)
                     
                    if lower_pr_ids:
                        #update effect_to of lower pr_salary
                        self.write_with_log(cr, uid, lower_pr_ids[0],{'effect_to': False}, context)
                    
        return res
    
    def fields_view_get(self, cr, uid, view_id = None, view_type = 'form', context = None, toolbar = False, submenu = False):
        res = super(vhr_ts_emp_timesheet, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar = toolbar, submenu = submenu)
        if context is None:
            context = {}
        if view_type == 'form':
            doc = etree.XML(res['arch'])
            if res['type'] == 'form':
                
                fields = self._columns.keys()
                cons_fields = ['employee_code', 'department_id','active', 'is_movement', 'audit_log_ids', 'contract_type_id']
                fields = [x for x in fields if x not in cons_fields]
                today = datetime.today().date()
                today = today.strftime(DEFAULT_SERVER_DATE_FORMAT)
                for field in fields:
                    for node in doc.xpath("//field[@name='%s']" %field):
                        modifiers = json.loads(node.get('modifiers'))
                        #Readonly record if create by working record or effect_to < today
                        args_readonly = [('is_new','=',False)]
#                         args_readonly = ['|',
#                                          ('is_create_from_working_record','=',True),
#                                          '&',('effect_to','!=',False),('effect_to','<',today)]
                        
                        modifiers.update({'readonly' : args_readonly})
                        node.set('modifiers', json.dumps(modifiers))
                    
            res['arch'] = etree.tostring(doc)
        return res
    
    def unlink_record(self, cr, uid, ids, context=None):
        res = False
        try:
            res = super(vhr_ts_emp_timesheet, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        
        return res



vhr_ts_emp_timesheet()