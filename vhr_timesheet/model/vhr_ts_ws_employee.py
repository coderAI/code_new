# -*- coding: utf-8 -*-

import logging
import simplejson as json
from datetime import datetime
from lxml import etree
from dateutil.relativedelta import relativedelta

from openerp.osv import osv, fields
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.addons.vhr_common.model.vhr_common import vhr_common


log = logging.getLogger(__name__)


class vhr_ts_ws_employee(osv.osv, vhr_common):
    _name = 'vhr.ts.ws.employee'
    _description = 'VHR TS Working Schedule'

    def _is_new_record(self, cr, uid, ids, field_name, arg, context=None):
        if not isinstance(ids, list):
            ids = [ids]
        res = {}
        for record_id in ids:
            res[record_id] = False

        return res
    
    def _get_null_number(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for id in ids:
            res[id] = ''
        
        return res
    
    def _get_current_data(self, cr, uid, ids, field_name, arg, context=None):
        if not isinstance(ids, list):
            ids = [ids]
        ts_emp_pool = self.pool.get('vhr.ts.emp.timesheet')
        res = {}
        import time
        time1=time.time()
        for record in self.read(cr, uid, ids, ['employee_id']):
            res[record['id']] = {'current_timesheet_id': False, 'ts_working_group_id': False}
            employee_id = record.get('employee_id', False) and record['employee_id'][0] or False
            if employee_id:
                active_ts_emp_ids = ts_emp_pool.search(cr, uid, [('employee_id','=',employee_id),('active','=',True)])
                if active_ts_emp_ids:
                    ts_emp = ts_emp_pool.read(cr, uid, active_ts_emp_ids[0], ['timesheet_id'])
                    timesheet_id = ts_emp.get('timesheet_id',False) and ts_emp['timesheet_id'][0] or False
                    res[record['id']]['current_timesheet_id'] = timesheet_id
                     
                 
                working_group_id, working_group_code, tuple = self.pool.get('hr.holidays').get_current_working_group_of_employee(cr, uid, employee_id, context)
                res[record['id']]['ts_working_group_id'] = working_group_id
        
        time2=time.time()
        log.info("time get current ts/ws: %s"%(time2-time1))
        
        return res
    
    
    def fcnt_search_timesheet(self, cr, uid, obj, name, args, context=None):
        if not args:
            return []
        
        ts_emp_pool = self.pool.get('vhr.ts.emp.timesheet')
        domain = []
        employee_ids = []
        for item in args:
            if item[0] == 'current_timesheet_id':
                domain.append(('timesheet_id',item[1],item[2]))
            else:
                domain.append(item)
        
        print 'domain=',domain
        domain.append(('active','=', True))
        
        ts_emp_ids = ts_emp_pool.search(cr, uid, domain)
        
        if ts_emp_ids:
            ts_emps = ts_emp_pool.read(cr, uid, ts_emp_ids, ['employee_id'])
            employee_ids = [ts.get('employee_id', False) and ts['employee_id'][0] for ts in ts_emps]
        
        operator = 'in'
        for field, oper, value in args:
            if oper == '!=' and value == True:
                operator = 'not in'
                break
            elif oper == '==' and value == False:
                operator = 'not in'
                break
            
        if not employee_ids:
            return [('employee_id', '=', 0)]
        
        return [('employee_id',operator, employee_ids)]
    

    _columns = {
        'name': fields.char('Name', size=128),
        'employee_id': fields.many2one('hr.employee', 'Employee', ondelete='restrict'),
        'employee_code': fields.related('employee_id', 'code', type="char", string="Employee Code"),
        'department_id': fields.related('employee_id', 'department_id', type='many2one', relation="hr.department", string="Department"),
        'company_id': fields.many2one('res.company', 'Company', ondelete='restrict'),
        'ws_id': fields.many2one('vhr.ts.working.schedule', 'Working Schedule', ondelete='restrict'),
#         'ts_working_group_id': fields.many2one('vhr.ts.working.group', 'Working Group', ondelete='restrict'),
        # 'working_record_id': fields.many2one('vhr.working.record', 'Working Record', ondelete='cascade'),
        'effect_from': fields.date('Effect From'),
        'effect_to': fields.date('Effect To'),
        'active': fields.boolean('Active'),
        'current_timesheet_id': fields.function(_get_current_data, type='many2one', 
                                                relation='vhr.ts.timesheet', string="Timesheet",multi="get_current",fnct_search=fcnt_search_timesheet),
        'ts_working_group_id': fields.function(_get_current_data, type='many2one', relation='vhr.ts.working.group', string="Working Group", multi="get current"),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                         domain=[('object_id.model', '=', _name), \
                                                 ('field_id.name', 'not in', ['write_date', 'audit_log_ids'])]),

        #                 'is_create_from_working_record': fields.function(is_create_from_working_record, type='boolean', string='Is Create From Working Record'),
        'is_new': fields.function(_is_new_record, type='boolean', string="Is New"),
        #You dont need to care this field, its' use to make link to wizard for view data.
        'ts_working_schedule_employee_wizard_id': fields.many2one('vhr.ts.working.schedule.employee.wizard','Working Schedule Employee Wizard Test'),
        'number_index': fields.function(_get_null_number, type='char', string='Number'),
    }

    _order = "effect_from desc"

    #     def _get_default_company_id(self, cr, uid, context=None):
    # company_ids = self.pool.get('res.company').search(cr, uid, [('is_member', '=', False)], order="id asc")
    #         if company_ids:
    #             return company_ids[0]
    #
    #         return False


    _defaults = {
        #         'company_id': _get_default_company_id,
        'active': False,
        'is_new': True,
    }

    _unique_insensitive_constraints = [{'employee_id': "Employee - Effective Date are already exist!",
                                        # 'company_id': "Employee - Company - Effective Date are already exist!",
                                        'effect_from': "Employee - Effective Date are already exist!"
                                       }]

    def onchange_employee_id(self, cr, uid, ids, employee_id, context=None):
        res = {'employee_code': False, 'department_id': False}
        if employee_id:
            employee = self.pool.get('hr.employee').read(cr, uid, employee_id, ['code','department_id'])
            employee_code = employee.get('code', '')
            res['employee_code'] = employee_code
            res['department_id'] = employee.get('department_id',False) and employee['department_id'][0] or False

        return {'value': res}


    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if not context:
            context = {}

        if 'active_test' not in context:
            context['active_test'] = False

        res = super(vhr_ts_ws_employee, self).search(cr, uid, args, offset, limit, order, context, count)
        return res

    def name_get(self, cr, uid, ids, context=None):
        if not ids or False in ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        reads = self.read(cr, uid, ids, ['employee_id'], context=context)
        res = []
        for record in reads:
            name = record.get('employee_id', False) and record['employee_id'][1]
            res.append((record['id'], name))
        return res

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        return super(vhr_ts_ws_employee, self).name_search(cr, uid, name, args, operator, context, limit)

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        args_new = [('name', operator, name)] + args
        ids = self.search(cr, uid, args_new)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(vhr_ts_ws_employee, self).name_search(cr, uid, name, args, operator, context, limit)

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(vhr_ts_ws_employee, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar=toolbar,
                                                              submenu=submenu)
        if context is None:
            context = {}
        if view_type == 'form':
            doc = etree.XML(res['arch'])
            if res['type'] == 'form':

                fields = ['employee_id', 'ws_id', 'effect_from']
                today = datetime.today().date()
                today = today.strftime(DEFAULT_SERVER_DATE_FORMAT)
                for field in fields:
                    for node in doc.xpath("//field[@name='%s']" % field):
                        modifiers = json.loads(node.get('modifiers'))
                        #Readonly record if create by working record or effect_to < today
                        args_readonly = [('is_new', '=', False)]
                        # args_readonly = ['|',
                        #                                          ('is_create_from_working_record','=',True),
                        #                                          '&',('effect_to','!=',False),('effect_to','<',today)]

                        modifiers.update({'readonly': args_readonly})
                        node.set('modifiers', json.dumps(modifiers))

            res['arch'] = etree.tostring(doc)
        return res

    def cron_update_ts_ws_employee_state(self, cr, uid, context=None):
        """
        Update state of record if satisfy condition of active
        """
        log.info("Start run cron: Update VHR TS Working Schedule ")
        if not context:
            context = {}
        active_record_ids, inactive_record_ids = self.update_active_of_record_in_object_cm(cr, uid, 'vhr.ts.ws.employee')
        
        if inactive_record_ids:
            check_ws_ids = []
            #Get working schedule from inactive WS employee
            for record in self.read(cr, uid, inactive_record_ids, ['ws_id']):
                ws_id = record.get('ws_id', False) and record['ws_id'][0] or False
                if ws_id and ws_id not in check_ws_ids:
                    check_ws_ids.append(ws_id)
            #Check if Working Schedule doesnt have any active WS employee, inactive that WS
            if check_ws_ids:
                inactive_ws_ids = []
                for ws_id in check_ws_ids:
                    active_ws_emp_ids = self.search(cr, uid, [('ws_id','=',ws_id),('active','=',True)])
                    if not active_ws_emp_ids:
                        inactive_ws_ids.append(ws_id)
                if inactive_ws_ids:
                    self.pool.get('vhr.ts.working.schedule').write(cr, uid, inactive_ws_ids, {'active': False})
        
        log.info("End run cron: Update VHR TS Working Schedule ")
        return True

    def update_ts_ws_employee_state(self, cr, uid, ts_ws_ids, context=None):
        """
         Update state of all Working Schedule link to employee-company of input Working Schedule
         One employee at a company only have one Working Schedule is active
         Return list Working Schedule just active
        """
        if not context:
            context = {}
        context['do_not_update_ts_ws_employee_state'] = True
        dict_result = []
        list_unique = []
        if ts_ws_ids:
            ts_ws_records = self.read(cr, uid, ts_ws_ids, ['employee_id'])
            for ts_ws_record in ts_ws_records:
                #                 company_id = ts_ws_record.get('company_id', False) and ts_ws_record['company_id'][0] or False
                employee_id = ts_ws_record.get('employee_id', False) and ts_ws_record['employee_id'][0] or False

                if employee_id not in list_unique:
                    list_unique.append(employee_id)

        if list_unique:
            today = datetime.today().date()
            for unique_item in list_unique:

                #Get Salary have active=False need to update active=True
                active_record_ids = self.search(cr, uid, [('employee_id', '=', unique_item),
                                                          # ('company_id','=',unique_item[1]),
                                                          ('active', '=', False),
                                                          ('effect_from', '<=', today),
                                                          '|', ('effect_to', '=', False),
                                                          ('effect_to', '>=', today)])

                # Get Salary have active=True need to update active=False
                inactive_record_ids = self.search(cr, uid, [('employee_id', '=', unique_item),
                                                            #                                                             ('company_id','=',unique_item[1]),
                                                            ('active', '=', True),
                                                            '|', ('effect_to', '<', today),
                                                            ('effect_from', '>', today)])

                ts_ws_ids = inactive_record_ids + active_record_ids

                if ts_ws_ids:
                    self.update_active_of_record_cm(cr, uid, 'vhr.ts.ws.employee', ts_ws_ids, context)

        return dict_result

    def update_nearest_ts_ws_employee(self, cr, uid, ids, context=None):
        if not context:
            context = {}

        if not isinstance(ids, list):
            ids = [ids]

        if ids:
            context['do_not_update_ts_ws_employee_state'] = True
            context['do_not_update_nearest_ts_ws_employee'] = True
            records = self.read(cr, uid, ids, ['employee_id', 'effect_from'])
            for record in records:
                employee_id = record.get('employee_id', False) and record['employee_id'][0] or False
                #                 company_id = record.get('company_id',False) and record['company_id'][0] or False
                current_effect_from = record.get('effect_from', False)
                if current_effect_from:

                    # Update
                    nearest_ts_ws_ids = self.search(cr, uid, [('employee_id', '=', employee_id),
                                                              # ('company_id','=',company_id),
                                                              ('effect_from', '<', current_effect_from),
                                                              '|', ('active', '=', True),
                                                              ('active', '=', False)],
                                                    order="effect_from desc")

                    if nearest_ts_ws_ids:
                        current_effect_from = datetime.strptime(current_effect_from, DEFAULT_SERVER_DATE_FORMAT).date()
                        update_effect_to = current_effect_from - relativedelta(days=1)
                        update_effect_to = update_effect_to.strftime(DEFAULT_SERVER_DATE_FORMAT)
                        self.write(cr, uid, nearest_ts_ws_ids[0], {'effect_to': update_effect_to}, context)

            context['do_not_update_ts_ws_employee_state'] = False
        return True

    def update_from_future_ts_ws_employee(self, cr, uid, ids, context=None):
        if not context:
            context = {}

        if not isinstance(ids, list):
            ids = [ids]

        if ids:
            context['do_not_update_ts_ws_employee_state'] = True
            context['do_not_update_nearest_ts_ws_employee'] = True
            records = self.read(cr, uid, ids, ['employee_id', 'effect_from'])
            for record in records:
                employee_id = record.get('employee_id', False) and record['employee_id'][0] or False
                #                 company_id = record.get('company_id',False) and record['company_id'][0] or False
                current_effect_from = record.get('effect_from', False)
                if current_effect_from:
                    # update effect_to of edit record if edit record in the past
                    larger_pr_ids = self.search(cr, uid, [('employee_id', '=', employee_id),
                                                          #                                                           ('company_id','=',company_id),
                                                          ('effect_from', '>', current_effect_from),
                                                          '|', ('active', '=', True),
                                                          ('active', '=', False)],
                                                order="effect_from asc")
                    if larger_pr_ids:
                        larger_pr = self.read(cr, uid, larger_pr_ids[0], ['effect_from'])
                        larger_effect_from = larger_pr.get('effect_from', False)
                        if larger_effect_from:
                            larger_effect_from = datetime.strptime(larger_effect_from,
                                                                   DEFAULT_SERVER_DATE_FORMAT).date()
                            update_effect_to = larger_effect_from - relativedelta(days=1)
                            update_effect_to = update_effect_to.strftime(DEFAULT_SERVER_DATE_FORMAT)
                            self.write(cr, uid, record.get('id', False), {'effect_to': update_effect_to}, context)

        context['do_not_update_ts_ws_employee_state'] = False
        return True

    #Cannot create record which effect_from overlap with date range effect_from -effect_to of record with same employee_id, company_id:
    def check_overlap_date(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        if ids:
            ts_ws = self.browse(cr, uid, ids[0], context)
            employee_id = ts_ws.employee_id and ts_ws.employee_id.id or False
            #             company_id = ts_ws.company_id and ts_ws.company_id.id or False
            effect_from = ts_ws.effect_from
            effect_to = ts_ws.effect_to or False

            if employee_id:
                args = [('employee_id', '=', employee_id),
                        #                         ('company_id', '=', company_id),
                        '|', ('active', '=', False),
                        ('active', '=', True)]

                ts_ws_ids = self.search(cr, uid, args)

                if not ts_ws_ids:
                    return True

                not_overlap_args = [('effect_to', '<', effect_from)] + args
                if effect_to:
                    not_overlap_args.insert(0, '|')
                    not_overlap_args.insert(1, ('effect_from', '>', effect_to))

                not_overlap_ts_ws_ids = self.search(cr, uid, not_overlap_args)
                # Record not overlap is the record link to employee
                if len(ts_ws_ids) == len(not_overlap_ts_ws_ids):
                    return True
                else:
                    #Get records from working_ids not in not_overlap_working_ids
                    overlap_ids = [x for x in ts_ws_ids if x not in not_overlap_ts_ws_ids]
                    #Get records from working_ids are not working_id
                    overlap_ids = [x for x in overlap_ids if x not in ids]
                    if overlap_ids:
                        raise osv.except_osv('Validation Error !',
                                             'The effective duration is overlapped. Please check again !')

        return True

    def check_dates(self, cr, uid, ids, context=None):
        for record in self.read(cr, uid, ids, ['effect_from', 'effect_to'], context=context):
            if record.get('effect_from', False) and record.get('effect_to', False) and record['effect_from'] > record[
                'effect_to']:
                raise osv.except_osv('Validation Error !', 'Effect From must be greater than Effect To !')

        return True
    
    def check_if_have_leave_request_in_future(self, cr, uid, employee_id, date, context=None):
        '''
            Dont allow to create if created leave request in future
        '''
        if employee_id and date:
            holiday_line_obj = self.pool.get('vhr.holiday.line')
            future_line_ids = holiday_line_obj.search(cr, uid, [('employee_id','=', employee_id),
                                                                                 ('date', '>=',date)])
            if future_line_ids:
                future_lines = holiday_line_obj.read(cr, uid, future_line_ids, ['holiday_id'])
                holiday_ids = [line.get('holiday_id',False) and line['holiday_id'][0] for line in future_lines]
                holidays = self.pool.get('hr.holidays').read(cr, uid, holiday_ids, ['state'])
                holiday_states = [hr['state'] for hr in holidays if hr['state'] not in ['cancel','refuse']]
                if holiday_states:
                    raise osv.except_osv('Validation Error !', 'You can not create records which have effect from lower than registered leave request date ')
        
        return True
            
    
    def create(self, cr, uid, vals, context=None):
        try:
            if not context:
                context = {}
            res = super(vhr_ts_ws_employee, self).create(cr, uid, vals, context)

            if res:
                context['name_object'] = 'working schedule employee'
                self.pool.get('vhr.holiday.line').check_if_date_after_summary_timesheet(cr, uid, vals['employee_id'], vals['effect_from'], context)
                self.check_if_have_leave_request_in_future(cr, uid, vals.get('employee_id'), vals.get('effect_from'), context)
                self.update_nearest_ts_ws_employee(cr, uid, [res], context)
                self.update_from_future_ts_ws_employee(cr, uid, [res], context)
                self.check_overlap_date(cr, uid, [res], context)
                self.update_ts_ws_employee_state(cr, uid, [res], context)

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
            raise osv.except_osv('Validation Error !',
                                 'Have error during create Working Schedule Employee:\n %s!' % error_message)

    def write(self, cr, uid, ids, vals, context=None):
        try:
            if not context:
                context = {}
            if not isinstance(ids, list):
                ids = [ids]
            
            if vals.get('effect_from', False):
                self.check_if_update_effect_from_out_of_box(cr, uid, ids, vals, context)
                
            res = super(vhr_ts_ws_employee, self).write(cr, uid, ids, vals, context)

            if res:
                
                if vals.get('effect_from',False) or vals.get('ws_id',False):
                    records = self.read(cr, uid, ids, ['employee_id','effect_from'])
                    context['name_object'] = 'working schedule employee'
                    for record in records:
                        employee_id = record.get('employee_id',False) and record['employee_id'][0]
                        effect_from = record.get('effect_from',False)
                        self.pool.get('vhr.holiday.line').check_if_date_after_summary_timesheet(cr, uid, employee_id, effect_from, context)
                
                if vals.get('effect_to', False) or vals.get('effect_from', False):
                    self.check_dates(cr, uid, ids, context)
                    if vals.get('effect_from', False) and not context.get('do_not_update_nearest_ts_ws_employee',
                                                                          False):
                        self.update_nearest_ts_ws_employee(cr, uid, ids, context)

                    self.check_overlap_date(cr, uid, ids, context)

                if not context.get('do_not_update_ts_ws_employee_state', False):
                    self.update_ts_ws_employee_state(cr, uid, ids, context)
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
            raise osv.except_osv('Validation Error !',
                                 'Have error during update Working Schedule Employee:\n %s!' % error_message)
    
    def check_if_update_effect_from_out_of_box(self, cr, uid, ids, vals, context=None):
        """
            when change effect_from < effect_from of nearest (lower) WSE or  > effect_from of nearest (greater) WSE
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

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        if not isinstance(ids, list):
            ids = [ids]

        res = False
        if ids:
            records = self.read(cr, uid, ids, ['employee_id', 'effect_from', 'effect_to','ws_id'])
            for record in records:
                employee_id = record.get('employee_id', False) and record['employee_id'][0] or False
                working_schedule_id = record.get('ws_id',False) and record['ws_id'][0] or False
                #                 company_id = record.get('company_id',False) and record['company_id'][0] or False
                effect_from = record.get('effect_from', False)
                effect_to = record.get('effect_to', False)
                
                if employee_id and effect_from:
                    #Dont allow to delete when have leave request/overtime created in date range of Working SChedule Employee
                    holiday_line_obj = self.pool.get('vhr.holiday.line')
                    domain = [('employee_id','=',employee_id),
                              ('date','>=',effect_from)]
                    
                    if effect_to:
                        domain.append(('date','<=',effect_to))
                    line_ids = holiday_line_obj.search(cr, uid, domain)
                    if line_ids:
                        lines = holiday_line_obj.read(cr, uid, line_ids, ['holiday_id'])
                        holiday_ids = [line['holiday_id'] and line['holiday_id'][0] for line in lines]
                        holiday_ids = list(set(holiday_ids))
                        if holiday_ids:
                            holidays = self.pool.get('hr.holidays').read(cr, uid, holiday_ids, ['state'])
                            states = [holiday['state'] for holiday in holidays if holiday['state'] != 'refuse']
                            if states:
                                raise osv.except_osv('Validation Error !',
                                             "You can't delete these records because there are leave requests related to them. \n Please try again or contact to administrator !")
                            
                    domain = [('employee_id','=',employee_id),
                              ('date_off','>=',effect_from),
                              ('state','!=','cancel')]
                    ot_line_ids = self.pool.get('vhr.ts.overtime.detail').search(cr, uid, domain)
                    if ot_line_ids:
                        raise osv.except_osv('Validation Error !',
                                             "You can't delete these records because there are overtime related to them. \n Please try again or contact to administrator !")
                    
                    #Dont allow to delete working schedule employee if generated from effect_from
                    monthly_ids = self.pool.get('vhr.ts.monthly').search(cr, uid, [('employee_id','=',employee_id),
                                                                                   ('working_schedule_id','=',working_schedule_id),
                                                                                   ('date','>=',effect_from),
                                                                                   ('state','in',['sent','approve'])], context={'get_all': True})
                    if monthly_ids:
                        raise osv.except_osv('Validation Error !',
                                         "You can't delete these records which related to Monthly records!")
                    
                    larger_pr_ids = self.search(cr, uid, [('employee_id', '=', employee_id),
                                                          #                                                           ('company_id','=',company_id),
                                                          ('effect_from', '>', effect_from),
                                                          '|', ('active', '=', True),
                                                          ('active', '=', False), ])

                    if larger_pr_ids:
                        raise osv.except_osv('Validation Error !',
                                             'You cannot delete records which are not last Working Schedule Employee !')

                    lower_pr_ids = self.search(cr, uid, [('employee_id', '=', employee_id),
                                                         # ('company_id','=',company_id),
                                                         ('effect_from', '<', effect_from),
                                                         '|', ('active', '=', True),
                                                         ('active', '=', False), ], order="effect_from desc")

                    if not context.get('unlink_from_wr', False):
                        working_record_ids = []
                        try:
                            working_pool = self.pool.get('vhr.working.record')
                            working_record_ids = working_pool.search(cr, uid, [('ts_ws_employee_id', '=', record.get('id', False)),
                                                                                ('state', 'in', [False, 'finish'])])
                            if working_record_ids:
                                working_pool.unlink(cr, uid, working_record_ids, {'unlink_from_ts_ws_employee': True})
                        except Exception as e:
                            log.exception(e)
                            raise osv.except_osv('Error !',
                                'You cannot delete the record(s) which reference to Other Working Records %s'% str(working_record_ids))

                    res = self.unlink_record(cr, uid, [record.get('id', False)], context)

                    if lower_pr_ids:
                        # update effect_to of lower pr_salary
                        self.write(cr, uid, lower_pr_ids[0], {'effect_to': False}, context)

        return res

    def unlink_record(self, cr, uid, ids, context=None):
        res = False
        try:
            res = super(vhr_ts_ws_employee, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')

        return res


vhr_ts_ws_employee()