# -*-coding:utf-8-*-

import thread
import logging
import sys

from datetime import datetime,date
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.osv import osv, fields
from openerp import SUPERUSER_ID
from openerp.osv import osv, fields
from openerp.sql_db import Cursor
from openerp.sql_db import ConnectionPool
from openerp import tools

from openerp.addons.vhr_common.model.vhr_common import vhr_common

log = logging.getLogger(__name__)


class vhr_working_record(osv.osv, vhr_common):
    _name = 'vhr.working.record'
    _inherit = 'vhr.working.record'

    _columns = {
        'timesheet_id_old': fields.many2one('vhr.ts.timesheet', 'Timesheet', ondelete='restrict'),
        'timesheet_id_new': fields.many2one('vhr.ts.timesheet', 'Timesheet', ondelete='restrict'),

        'ts_working_schedule_id_old': fields.many2one('vhr.ts.working.schedule', 'Working Schedule',
                                                      ondelete='restrict'),
        'ts_working_schedule_id_new': fields.many2one('vhr.ts.working.schedule', 'Working Schedule',
                                                      ondelete='restrict'),

        'ts_working_group_id_old': fields.many2one('vhr.ts.working.group', "Working Group", ondelete='restrict'),
        'ts_working_group_id_new': fields.many2one('vhr.ts.working.group', "Working Group", ondelete='restrict'),

        'ts_emp_timesheet_id': fields.many2one('vhr.ts.emp.timesheet', 'Employee Timesheet', ondelete='restrict'),
        'ts_ws_employee_id': fields.many2one('vhr.ts.ws.employee', 'TS Working Schedule', ondelete='restrict'),
    }
    
        
    def create_update_ts_emp_timesheet(self, cr, uid, ids, context=None):
        if not context:
            context = {}

        if not isinstance(ids, list):
            ids = [ids]

        dict_ts_emp_fields = {'timesheet_id_new': 'timesheet_id_old'}
        translate_ts_emp_fields = {'timesheet_id': 'timesheet_id_new'}

        ts_emp_timesheet_pool = self.pool.get('vhr.ts.emp.timesheet')
        list_fields = dict_ts_emp_fields.keys() + dict_ts_emp_fields.values()
        list_fields.append('ts_emp_timesheet_id')

        list_fields_is = ['employee_id', 'effect_from']
        list_fields.extend(list_fields_is)

        records = self.read(cr, uid, ids, list_fields)
        context['create_update_from_working_record'] = True
        context['do_not_update_to_contract'] = True
        
        mcontext = context.copy()
        emp_timesheet_pool = self.pool.get('vhr.ts.emp.timesheet')
        
        for record in records:
            # Write to emp ts, if edit timesheet_id_new in WR
            if record.get('ts_emp_timesheet_id', False):
                ts_emp_id = record.get('ts_emp_timesheet_id', False) and record['ts_emp_timesheet_id'][0]
                vals = {}
                for field_pr in translate_ts_emp_fields.keys():
                    vals[field_pr] = record.get(translate_ts_emp_fields[field_pr], False) and \
                                     record[translate_ts_emp_fields[field_pr]][0]

                for field in list_fields_is:
                    data = record.get(field, False)
                    if isinstance(data, tuple):
                        data = data[0]
                    vals[field] = data
                
                emp_timesheet_pool.write_with_log(cr, uid, ts_emp_id, vals, mcontext)
#      ts_emp_timesheet_pool.write(cr, SUPERUSER_ID, ts_emp_id, vals, context)

            else:
                change_timesheet = False
                # If value of field in check_field different with value of field old, then create ts_emp_timesheet
                check_field = 'timesheet_id_new'
                if record.get(check_field, False) and record.get(check_field, 0) != record.get(dict_ts_emp_fields[check_field], 0):
                    change_timesheet = True
#                     break
                
                if not change_timesheet and record.get(check_field, False):
                     #Case employee back to work, should create new timesheet employee even when old timesheet = new timesheet
                    #But must have at least one field have data
                    employee_id = record.get('employee_id', False) and record['employee_id'][0] or False
                    effect_from = record.get('effect_from', False)
                    
                    domain = [('employee_id', '=', employee_id),
                               ('effect_from', '<=', effect_from),
                             '|', ('effect_to', '>=', effect_from),
                                  ('effect_to', '=', False),
                             '|', ('active', '=', True),
                                  ('active', '=', False)]
                        
                    ts_emp_ids = ts_emp_timesheet_pool.search(cr, uid, domain ,order="effect_from desc")
                    if not ts_emp_ids:
                        change_timesheet = True
                        
                if change_timesheet:
                    vals = {}
                    for field_pr in translate_ts_emp_fields.keys():
                        vals[field_pr] = record.get(translate_ts_emp_fields[field_pr], False) and \
                                         record[translate_ts_emp_fields[field_pr]][0]

                    for field in list_fields_is:
                        data = record.get(field, False)
                        if isinstance(data, tuple):
                            data = data[0]
                        vals[field] = data
                    
                    employee_id = record.get('employee_id',False) and record['employee_id'][0] or False
                    vals['contract_type_id'] = self.pool.get('vhr.ts.emp.timesheet').get_active_contract_type_of_employee(cr, uid, employee_id, context)
                    # vals['working_record_id'] = record.get('id',False)
                    if context.get('create_from_movement', False):
                        vals['is_movement'] = True

#          res = ts_emp_timesheet_pool.create(cr, SUPERUSER_ID, vals, context)
                    res = emp_timesheet_pool.create_with_log(cr, uid, vals, mcontext)
                    if res:
                        super(vhr_working_record,self).write(cr, uid, record.get('id', False), {'ts_emp_timesheet_id': res}, context)

        return True

#     def create_update_ts_ws_employee(self, cr, uid, ids, context=None):
#         if not context:
#             context = {}
# 
#         if not isinstance(ids, list):
#             ids = [ids]
# 
#         dict_ts_ws_emp_fields = {'ts_working_schedule_id_new': 'ts_working_schedule_id_old',
#                                  'ts_working_group_id_new': 'ts_working_group_id_old'}
# 
#         translate_ts_ws_emp_fields = {'ws_id': 'ts_working_schedule_id_new',
#                                       'ts_working_group_id': 'ts_working_group_id_new'}
# 
#         ts_ws_emp_pool = self.pool.get('vhr.ts.ws.employee')
# 
#         list_fields = dict_ts_ws_emp_fields.keys() + dict_ts_ws_emp_fields.values()
#         list_fields.append('ts_ws_employee_id')
# 
#         list_fields_is = ['employee_id', 'effect_from']
#         list_fields.extend(list_fields_is)
# 
#         records = self.read(cr, uid, ids, list_fields)
#         context['create_update_from_working_record'] = True
#         context['do_not_update_to_contract'] = True
#         for record in records:
#             # Write to payroll, if edit salary in WR link to payroll
#             if record.get('ts_ws_employee_id', False):
#                 ts_emp_id = record.get('ts_ws_employee_id', False) and record['ts_ws_employee_id'][0]
#                 vals = {}
#                 for field_pr in translate_ts_ws_emp_fields.keys():
#                     vals[field_pr] = record.get(translate_ts_ws_emp_fields[field_pr], False) and \
#                                      record[translate_ts_ws_emp_fields[field_pr]][0]
# 
#                 for field in list_fields_is:
#                     data = record.get(field, False)
#                     if isinstance(data, tuple):
#                         data = data[0]
#                     vals[field] = data
# 
#                 ts_ws_emp_pool.write(cr, SUPERUSER_ID, ts_emp_id, vals, context)
# 
#             else:
#                 change = False
#                 # If value of field in check_field different with value of field old, then create ts_emp_timesheet
#                 check_fields = translate_ts_ws_emp_fields.values()
#                 for field in check_fields:
#                     if record.get(field, 0) != record.get(dict_ts_ws_emp_fields[field], 0):
#                         change = True
#                         break
# 
#                 if change:
#                     vals = {}
#                     for field_pr in translate_ts_ws_emp_fields.keys():
#                         vals[field_pr] = record.get(translate_ts_ws_emp_fields[field_pr], False) and \
#                                          record[translate_ts_ws_emp_fields[field_pr]][0]
# 
#                     for field in list_fields_is:
#                         data = record.get(field, False)
#                         if isinstance(data, tuple):
#                             data = data[0]
#                         vals[field] = data
# 
#                     # vals['working_record_id'] = record.get('id',False)
#                     res = ts_ws_emp_pool.create(cr, SUPERUSER_ID, vals, context)
#                     if res:
#                         self.write(cr, uid, record.get('id', False), {'ts_ws_employee_id': res}, context)
# 
#         return True

    def get_data_from_nearest_ts_emp_timesheet(self, cr, uid, employee_id, company_id, effect_from, context=None):
        res = {'timesheet_id_new': False, 'timesheet_id_old': False}
        if not context:
            context = {}
            
        if employee_id and company_id and effect_from:
            emp_timesheet_pool = self.pool.get('vhr.ts.emp.timesheet')
            domain = [('employee_id', '=', employee_id),
                     # ('company_id','=',company_id),
                       ('effect_from', '<=', effect_from),
                     '|', ('effect_to', '>=', effect_from),
                          ('effect_to', '=', False),
                     '|', ('active', '=', True),
                          ('active', '=', False)]
            
            if context.get('current_ts_emp_timesheet_id', False):
                domain.append(('id','!=',context['current_ts_emp_timesheet_id']))
                
            ts_emp_ids = emp_timesheet_pool.search(cr, uid, domain ,order="effect_from desc")
            is_update_new_data = True
            if not ts_emp_ids:
                #Case quay lai lam viec, do ko co employee timesheet dang active, luc nay nen lay thong tin employee timesheet gan nhat
                is_update_new_data = False
                ts_emp_ids = emp_timesheet_pool.search(cr, uid, [('employee_id', '=', employee_id),
                                                                ('effect_to', '<=', effect_from),
                                                                '|', ('active', '=', True),
                                                                     ('active', '=', False)],
                                                       order="effect_from desc")
                
            if ts_emp_ids:
                ts_emp = emp_timesheet_pool.read(cr, uid, ts_emp_ids[0], ['timesheet_id'])
                
                if is_update_new_data:
                    res['timesheet_id_new'] = ts_emp.get('timesheet_id', False)
                
                if not context.get('update_old_timesheet_from_old_emp_timesheet', False):
                    res['timesheet_id_old'] = ts_emp.get('timesheet_id', False)
            
            #Case change employee-company in contract have WR and employee timesheet, old_timesheet in WR need to get from old emp_timesheet
            if context.get('update_old_timesheet_from_old_emp_timesheet', False):
                ts_emp_ids = emp_timesheet_pool.search(cr, uid, [('employee_id','=',employee_id),
                                                                    ('effect_to','<',effect_from)], order="effect_from desc",
                                                                                            context={'active_test': False})
                if ts_emp_ids:
                    ts_emp = emp_timesheet_pool.read(cr, uid, ts_emp_ids[0], ['timesheet_id'])
                    res['timesheet_id_old'] = ts_emp.get('timesheet_id', False)
                

        return res

#     def get_data_from_nearest_ts_ws_employee(self, cr, uid, employee_id, company_id, effect_from, context=None):
#         res = {'ts_working_schedule_id_new': False, 'ts_working_schedule_id_old': False,
#                'ts_working_group_id_new': False, 'ts_working_group_id_old': False}
#         if employee_id and company_id and effect_from:
#             ws_employee_pool = self.pool.get('vhr.ts.ws.employee')
#             ts_emp_ids = ws_employee_pool.search(cr, uid, [('employee_id', '=', employee_id),
#                                                            # ('company_id','=',company_id),
#                                                            ('effect_from', '<=', effect_from),
#                                                            '|', ('effect_to', '>=', effect_from),
#                                                            ('effect_to', '=', False),
#                                                            '|', ('active', '=', True),
#                                                            ('active', '=', False)], order="effect_from desc")
#             
#             is_update_new_data = True
#             if not ts_emp_ids:
#                 #Case quay lai lam viec, do ko co employee timesheet dang active, luc nay nen lay thong tin employee timesheet gan nhat
#                 is_update_new_data = False
#                 ts_emp_ids = ws_employee_pool.search(cr, uid, [('employee_id', '=', employee_id),
#                                                                 ('effect_to', '<=', effect_from),
#                                                                 '|', ('active', '=', True),
#                                                                      ('active', '=', False)],
#                                                            order="effect_from desc")
#                 
#             if ts_emp_ids:
#                 ts_emp = ws_employee_pool.read(cr, uid, ts_emp_ids[0], ['ws_id', 'ts_working_group_id'])
#                 working_schedule_id = ts_emp.get('ws_id', False) and ts_emp['ws_id'][0]
#                 
#                 if is_update_new_data:
#                     res['ts_working_schedule_id_new'] = working_schedule_id
#                 res['ts_working_schedule_id_old'] = working_schedule_id
# 
#                 ts_working_group_id = ts_emp.get('ts_working_group_id', False) and ts_emp['ts_working_group_id'][0]
#                 if is_update_new_data:
#                     res['ts_working_group_id_new'] = ts_working_group_id
#                 res['ts_working_group_id_old'] = ts_working_group_id
# 
#         return res

#     def onchange_working_schedule_id(self, cr, uid, ids, ts_working_schedule_id_new, ts_working_group_id_new,
#                                      context=None):
#         res = {'ts_working_group_id_new': False}
#         if ts_working_schedule_id_new:
#             ws_wg_pool = self.pool.get('vhr.ts.working.schedule.working.group')
#             ws_wg_ids = ws_wg_pool.search(cr, uid, [('ts_working_schedule_id', '=', ts_working_schedule_id_new)])
#             ts_working_group_ids = []
#             if ws_wg_ids:
#                 ws_wgs = ws_wg_pool.read(cr, uid, ws_wg_ids, ['ts_working_group_id'])
#                 for ws_wg in ws_wgs:
#                     ts_working_group_id = ws_wg.get('ts_working_group_id', False) and ws_wg['ts_working_group_id'][
#                         0] or False
#                     if ts_working_group_id and ts_working_group_id not in ts_working_group_ids:
#                         ts_working_group_ids.append(ts_working_group_id)
# 
#             if (ts_working_group_id_new and ts_working_group_id_new not in ts_working_group_ids) \
#                     or not ts_working_group_id_new:
#                 res['ts_working_group_id_new'] = False
#                 if ts_working_group_ids:
#                     res['ts_working_group_id_new'] = ts_working_group_ids[0]
#             else:
#                 res = {}
# 
#         return {'value': res}
    
    def get_initial_data_from_department(self, cr, uid, department_id, context=None):
        res = super(vhr_working_record, self).get_initial_data_from_department(cr, uid, department_id, context)
        if department_id:
            department = self.pool.get('hr.department').read(cr, uid, department_id, ['timesheet_id'])
            timesheet_id = department.get('timesheet_id', False) and department['timesheet_id'][0] or False
            if timesheet_id:
                res['timesheet_id_new'] = timesheet_id
        
        return res

    def create(self, cr, uid, vals, context=None):
        if not context:
            context = {}
            
        context['do_not_check_to_create_update_annual_leave'] = True
        res = super(vhr_working_record, self).create(cr, uid, vals, context)

        # Create ts.emp.timesheet when finish staff movement and have change timesheet
        if res:
            record = self.read(cr, uid, res, ['state','active'])
            is_active = record.get('active', False)
            state = record.get('state',False)
            if state in [False, 'finish'] and is_active:
                if vals.get('state', False) == 'finish':
                    context['create_from_movement'] = True
                self.create_update_ts_emp_timesheet(cr, uid, [res], context)
#                 self.create_update_ts_ws_employee(cr, uid, [res], context)
            
            if is_active:
                self.check_to_create_update_annual_leave(cr, uid, res, context)
            
            
            self.check_to_unlink_next_year_annual_leave(cr, uid, res, context)
            
            if vals.get('timesheet_id_new', False) != vals.get('timesheet_id_old', False) and vals.get('state', False) in [False,'finish']:
                context['name_object'] = 'employee timesheet'
                self.raise_error_if_create_update_wr_on_date_created_ts_detail(cr, uid, [res], context)

        return res
    
    def write(self, cr, uid, ids, vals, context=None):
        if not context:
            context = {}

        if not isinstance(ids, list):
            ids = [ids]

        res = super(vhr_working_record, self).write(cr, uid, ids, vals, context)
        # Create ts.emp.timesheet when finish staff movement and have change timesheet
        if res:
            records = self.read(cr, uid, ids, ['state','active'])
            for record in records:
                state = record.get('state',False)
                active = record.get('active', False)
                if set( ['timesheet_id_new', 'effect_from','state','active']).intersection(set(vals.keys())) \
                  and state in [False,'finish'] and active:
                    if vals.get('state', False) == 'finish':
                        context['create_from_movement'] = True
                    self.create_update_ts_emp_timesheet(cr, uid, [record['id']], context)
#                     self.create_update_ts_ws_employee(cr, uid, [record['id']], context)
            
            if vals.get('timesheet_id_new', False) or vals.get('state', False) == 'finish':
                context['name_object'] = 'employee timesheet'
                self.raise_error_if_create_update_wr_on_date_created_ts_detail(cr, uid, ids, context)
        
        # update job_level_id_new call update working record
        if (vals.get('job_level_person_id_new', False) or vals.get('active')) and not context.get('do_not_check_to_create_update_annual_leave',False):
            self.check_to_create_update_annual_leave(cr, uid, ids, context)

        return res
    
    def raise_error_if_create_update_wr_on_date_created_ts_detail(self, cr, uid, ids, context=None):
        """
        Raise error if change timesheet on date created timeshet detail
        """
        if ids:
            for record in self.read(cr, uid, ids, ['employee_id','effect_from',
                                                   'timesheet_id_old','timesheet_id_new','state']):
                state = record.get('state', False)
                effect_from = record.get('effect_from', False)
                employee_id = record.get('employee_id', False) and record['employee_id'][0]
                timesheet_id_old = record.get('timesheet_id_old', False) and record['timesheet_id_old'][0]
                timesheet_id_new = record.get('timesheet_id_new', False) and record['timesheet_id_new'][0]
                
                if timesheet_id_new != timesheet_id_old and state in [False, 'finish']:
                    self.pool.get('vhr.holiday.line').check_if_date_after_summary_timesheet(cr, uid, employee_id, effect_from, context)
        
        return True
    
    def check_to_unlink_next_year_annual_leave(self, cr, uid, record_id, context=None):
        #If WR is termination, check to unlink annual leave of next year
        if record_id and self.is_terminate_wr(cr, uid, record_id, [], context):
            annual_obj = self.pool.get('hr.holidays')
            
            data = self.read(cr, uid, record_id, ['employee_id','effect_from'])
            employee_id = data.get('employee_id', False) and data['employee_id'][0]
            effect_from = data.get('effect_from', False)
            effect_from = datetime.strptime(effect_from,DEFAULT_SERVER_DATE_FORMAT)
            
            #Search annual leave of next year
            annual_ids = annual_obj.search(cr, uid, [('type','=','add'),
                                                     ('employee_id','=',employee_id),
                                                     ('year','=',effect_from.year +1),
                                                     ('state','=','validate')])
            if annual_ids:
                begin_date = date(effect_from.year +1, 1, 1).strftime(DEFAULT_SERVER_DATE_FORMAT)
                contract_type_ids = self.pool.get('hr.contract.type').search(cr, uid, [('is_official','=',True)])
                
                contract_ids = self.pool.get('hr.contract').search(cr, uid, [('employee_id','=',employee_id),
                                                                             ('state','!=','cancel'),
                                                                             ('date_start_real','>=',begin_date),
                                                                             ('type_id','in',contract_type_ids)])
                #Only unlink if dont have any contract in next year
                if not contract_ids:
                    annual_obj.write(cr, uid, annual_ids, {'state':'cancel'})
                    annual_obj.unlink(cr, uid, annual_ids, context={'is_not_delete_leave': False})
        
        return True

    def get_list_working_record_of_employee_in_date_range(self, cr, uid, employee_id, company_id, date_start, date_end,
                                                          context=None):
        working_ids = []
        if date_end > date_start:
            domain = [('company_id', '=', company_id), ('employee_id', '=', employee_id),
                      ('state', 'in', [False, 'finish']),
                      '|', '&', ('effect_from', '<=', date_start),
                      '|', ('effect_to', '>=', date_start), ('effect_to', '=', False),
                      '&', ('effect_from', '<=', date_end),
                      '|', ('effect_to', '>=', date_start), ('effect_to', '=', False)]
            working_ids = self.search(cr, uid, domain)
        return working_ids
    
    def check_to_create_update_annual_leave(self, cr, uid, ids, context=None):
        """
        Create new annual leave balance for official employee join company/ back to work/ change type contract to official
        
        """
        if not context:
            context = {}
        if ids:
            if not isinstance(ids, list):
                ids = [ids]
            config_parameter = self.pool.get('ir.config_parameter')
            instance_obj = self.pool.get('vhr.employee.instance')
            back_work = config_parameter.get_param(cr, uid, 'vhr_master_data_back_to_work_change_form_code') or ''
            back_work = back_work.split(',')
            input_ihrp = config_parameter.get_param(cr, uid, 'vhr_master_data_input_data_into_iHRP') or ''
            input_ihrp = input_ihrp.split(',')
            
            change_type_code = config_parameter.get_param(cr, uid, 'vhr_master_data_change_type_of_contract') or ''
            change_type_code = change_type_code.split(',')
            
            start_change_form_list = back_work + input_ihrp + change_type_code
            for rc in self.browse(cr, uid, ids, context=context):
                job_level_person_id_old = rc.job_level_person_id_old and rc.job_level_person_id_old.id or False
                job_level_person_id_new = rc.job_level_person_id_new and rc.job_level_person_id_new.id or False
                contract_type_group = rc.contract_id and rc.contract_id.type_id and rc.contract_id.type_id.contract_type_group_id or False
                
                is_official = contract_type_group and contract_type_group.is_offical or False
                
                #Only create/update annual leave if contract is official
                if rc.active and is_official:
                    today = datetime.today().date()
                    employee_id = rc.employee_id and rc.employee_id.id or False
                    company_id = rc.company_id and rc.company_id.id or False
                    #Search active instance of other company, because current company may have active instance during update working record
                    #If employee have active instance of other company, dont create annual leave
                    active_instance = instance_obj.search(cr, uid, [('employee_id','=',employee_id),
                                                                    ('company_id','!=',company_id),
                                                                    ('date_start','<=', today),
                                                                    '|',('date_end','=',False),
                                                                        ('date_end','>=',today)])
                    for change_form in rc.change_form_ids:
                        if change_form.code in start_change_form_list and not active_instance:
                            try:
                                self.create_employee_allocation(cr, uid, rc.employee_id.id, rc.company_id.id, context)
                            except Exception, e:
                                log.exception(e)
                                
                        elif job_level_person_id_old != job_level_person_id_new and employee_id and company_id and not context.get('do_not_update_annual_day',False):
                            self.check_to_update_annual_day(cr, uid, employee_id, company_id, context)
        
        return True
    
    def check_to_update_annual_day(self, cr, uid, employee_id, company_id, context=None):
        default_comp_id, comp_ids = self.get_company_ids(cr, uid, employee_id, context)
        try:
            if default_comp_id == company_id:
                self.update_annual_days(cr, uid, employee_id, company_id, context)
        except Exception, e:
            log.exception(e)

    def create_employee_allocation(self, cr, uid, employee_id, company_id, context):
        log.info('create employee_allocation start employee %s company %s ()' % (employee_id, company_id))
        if context is None:
            context = {}
#         _pool = ConnectionPool(int(tools.config['db_maxconn']))
#         mcr = Cursor(_pool, cr.dbname, True)
#         reload(sys)
        self.pool.get('hr.holidays').create_allocation_for_newbie(cr, uid, employee_id=employee_id,
                                                                  company_id=company_id,
                                                                  context=context)
#         mcr.commit()
#         mcr.close()
        log.info('create employee_allocation end()')

    def update_annual_days(self, cr, uid, employee_id, company_id, context):
        log.info('update annual_days start() employee %s company %s' % (employee_id, company_id))
        if context is None:
            context = {}
#         _pool = ConnectionPool(int(tools.config['db_maxconn']))
#         mcr = Cursor(_pool, cr.dbname, True)
#         reload(sys)
        self.pool.get('hr.holidays').create_allocation_for_employee_change_level(cr, uid, employee_id=employee_id,
                                                                                 company_id=company_id, context=context)
#         mcr.commit()
#         mcr.close()
        log.info('update annual_days end()')


vhr_working_record()