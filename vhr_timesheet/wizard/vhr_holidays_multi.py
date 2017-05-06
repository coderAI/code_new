# -*-coding:utf-8-*-
import thread
import logging
import sys
from datetime import datetime, timedelta, date
import base64
import xlrd
from lxml import etree
import simplejson as json
from xlrd import open_workbook

from openerp.osv import osv, fields
from openerp.sql_db import Cursor
from openerp.sql_db import ConnectionPool
from openerp import tools
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.tools.translate import _

log = logging.getLogger(__name__)

class vhr_holidays_multi(osv.osv):
    _name = 'vhr.holidays.multi'
    _description = 'Mass Multi Holiday'

    _columns = {
        'company_id': fields.many2one('res.company', 'Company'),
        # 'holiday_type': fields.selection([('employee','By Employee'),('category','By Employee Tag')], 'Allocation Mode', help='By Employee: Allocation/Request for individual Employee, By Employee Tag: Allocation/Request for group of employees in category', required=True),
        'holiday_status_id': fields.many2one("hr.holidays.status", "Leave Type", required=True),
        'notes': fields.text('Reasons'),
        'date_from': fields.date('From Date', select=True),
        'date_to': fields.date('End Date'),
        'number_of_days_temp': fields.float('Allocation', readonly=True),
        'holiday_line_ids': fields.one2many('vhr.holiday.line', 'holiday_multi_id', 'Detail'),
        'type': fields.selection([('remove', 'Leave Request'), ('add', 'Allocation Request')], 'Request Type'),
        'is_offline': fields.boolean('Is OffLine'),
        'employee_ids': fields.many2many('hr.employee', 'multi_vhr_holidays_employee_rel', 'wr_holidays_multi_id',
                                         'employee_id', 'Employees'),
                
        'file_name': fields.char('File name'),
        'file_data': fields.binary('File'),

    }

    def _get_default_company_id(self, cr, uid, context=None):
        company_ids = self.pool.get('res.company').search(cr, uid, [('is_member', '=', False)], order="id asc")
        if company_ids:
            return company_ids[0]

        return False


    _defaults = {
        'company_id': _get_default_company_id,
        'is_offline': True
    }

#     def onchange_company(self, cr, uid, ids, company_id, context=None):
#         res = {'employee_ids': []}
#         domain = {}
#         if company_id:
#             emp_instance_pool = self.pool.get('vhr.employee.instance')
#             emp_instance_ids = emp_instance_pool.search(cr, uid,
#                                                         [('company_id', '=', company_id), ('date_end', '=', False)])
#             if emp_instance_ids:
#                 emp_instances = emp_instance_pool.read(cr, uid, emp_instance_ids, ['employee_id'])
#                 employee_ids = []
#                 for emp_instance in emp_instances:
#                     employee_id = emp_instance.get('employee_id', False) and emp_instance['employee_id'][0] or False
#                     if employee_id:
#                         employee_ids.append(employee_id)
#                 domain['employee_ids'] = [('id', 'in', employee_ids)]
# 
#         return {'value': res, 'domain': domain}

    def on_change_file(self, cr, uid, ids, file_data, employee_ids, holiday_status_id, context=None):
        """
        Use in Multi Update Adjust
        ================================= File Teamplate Data ========================================
        [[
        u'Employee Code,
        ]]
        ================================= File Teamplate Data ========================================
        """
        emp_obj = self.pool.get('hr.employee')
        if context is None:
            context = {}
        
        res = {'value': {'adjusts': []}}
        department_ids = []
        dept_codes = []
        context['filter_by_group'] = True
        if file_data:
            mapping_fields = {'Employee Code': 'employee_id',
                              }
            
            required_fields = ['employee_id']
            fields_order = []
            fields_search_by_name = []
            object = 'hr.holidays'
            
            try:
                base_data = base64.decodestring(file_data)
                row_book = open_workbook(file_contents = base_data)
                rows = row_book.sheet_by_index(0)
            except Exception as e:
                log.exception(e)
                res['warning'] = {'title': 'Warning',
                                  'message': 'Error to read file: %s' % e}
                return res
           
#             rows = self.act_gen_data(file_data)
            datas = []
            list_code = []
            if rows:
                msg_err = ''
                row_counter = 0
                
                mcontext = {'timesheet_detail': True}
                if holiday_status_id:
                    mcontext['filter_with_outing_leave'] = holiday_status_id
                allow_emp_ids = self.pool.get('hr.employee').search(cr, uid, [], context=mcontext)
                print 'allow_emp_ids=',allow_emp_ids
                for row in rows._cell_values:
                    try:
                        if row_counter == 0:
                            fields_order = row
                            
                        row_counter += 1
                        if row_counter > 2:
                            print '2='
                            val, error = self.parse_data_from_excel_row(cr, uid, row, mapping_fields, fields_search_by_name, fields_order, object, context)
                            
                            if val.get('employee_code', False) and val['employee_code'] not in list_code:
                                print '3=',val
                                employee_id = val.get('employee_id', False)
                                emp_code = val.get('employee_code',False)
                                list_code.append(emp_code)
                                
                                if employee_id in allow_emp_ids:
                                    datas.append(employee_id)
                                    
                    except Exception, e:
                        log.exception(e)
                
                if msg_err:
                    res['warning'] = {'title': "Warning",
                                      'message': "Invalid data entry in excel or You dont have permission to import. "
                                                 "Please check Employee code: %s" % msg_err}
                    return res
                
                return {'value': {'employee_ids': [[6, False, datas]]}}
        else:
            return {}
    
        
    def onchange_holiday_status_id(self, cr, uid, ids, holiday_status_id, number_of_days_temp, context=None):
        res = {'notes':''}
        if holiday_status_id:
            if not number_of_days_temp:
                number_of_days_temp = 0
            outing_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'ts_leave_type_outing_teambuilding').split(',')
            outing_leave_ids = self.pool.get('hr.holidays.status').search(cr, uid, [('code','in',outing_code)])
            if outing_leave_ids and holiday_status_id in outing_leave_ids:
                res['employee_ids'] = [(6, 0, [])]
                outing_leave = self.pool.get('hr.holidays.status').read(cr, uid, outing_leave_ids[0], ['timelines','date_type'])
                timelines = outing_leave.get('timelines', 0)
                if timelines < number_of_days_temp:
                    res['holiday_line_ids'] = []
                    res['date_to'] = False
                    res['notes'] = _("You can only register %s day at Outing Leave Type !")% str(timelines)
        
        return {'value': res}
        
        
    def onchange_date_range(self, cr, uid, ids, date_to, date_from, context=None):
        result = {'value': {}}
        holiday_line_ids = []
        if date_from and date_to:
            if date_from > date_to:
                result['value']['date_to'] = date_from
                date_to = date_from
            list_date = self.get_list_date(cr, uid, date_from, date_to)
            for date in list_date:
                holiday_line_ids.append((0, 0, {'date': date, 'status': 'full', 'number_of_days_temp': 1,'number_of_hours': 8,'number_of_hours_in_shift':8}))

        result['value']['holiday_line_ids'] = holiday_line_ids
        return result

    # Return list date from date_from to date_to
    def get_list_date(self, cr, uid, date_from, date_to, context=None):
        list_date = []
        if date_from and date_to:
            from_dt = datetime.strptime(date_from, DEFAULT_SERVER_DATE_FORMAT)
            to_dt = datetime.strptime(date_to, DEFAULT_SERVER_DATE_FORMAT)
            if to_dt >= from_dt:
                gap_days = (to_dt - from_dt).days
                list_date = [(from_dt + timedelta(days=x)).strftime(DEFAULT_SERVER_DATE_FORMAT) for x in
                             range(0, gap_days + 1)]

        return list_date

    def onchange_holiday_line(self, cr, uid, ids, holiday_line_ids, holiday_status_id, date_from, date_to, context=None):
        if context is None:
            context = {}
        context['multi'] = 1
        context['date_from'] = date_from
        context['date_to'] = date_to
        res =  self.pool.get('hr.holidays').onchange_holiday_line(cr, uid, ids, holiday_line_ids, holiday_status_id, 0, context)
        
        res['value']['notes'] = ''
        if holiday_status_id and res.get('value', {}):
            number_of_days_temp = res.get('value',{}).get('number_of_days_temp', 0) or 0
            outing_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'ts_leave_type_outing_teambuilding').split(',')
            outing_leave_ids = self.pool.get('hr.holidays.status').search(cr, uid, [('code','in',outing_code)])
            if outing_leave_ids and holiday_status_id in outing_leave_ids:
                outing_leave = self.pool.get('hr.holidays.status').read(cr, uid, outing_leave_ids[0], ['timelines','date_type'])
                timelines = outing_leave.get('timelines', 0)
                if timelines < number_of_days_temp:
                    res['value']['holiday_line_ids'] = []
                    res['value']['date_to'] = False
                    res['value']['notes'] = _("You can only register %s day at Outing Leave Type !")% str(timelines)
                    
        return res

    def create_mass_status(self, cr, uid, context=None):
        disable = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_timesheet_disable_run_thread_in_selected_function') or ''
        
        if disable.lower() != 'true':
            _pool = ConnectionPool(int(tools.config['db_maxconn']))
            tcr = Cursor(_pool, cr.dbname, True)
        else:
            tcr = cr
            
        vals = {'state': 'new'}

        employee_ids = self.pool.get('hr.employee').search(tcr, uid, [('user_id', '=', uid)], context={'search_all_employee': True,'active_test':False})
        if employee_ids:
            vals['requester_id'] = employee_ids[0]

        module_ids = self.pool.get('ir.module.module').search(tcr, uid, [('name', '=', 'vhr_timesheet')])
        if module_ids:
            vals['module_id'] = module_ids[0]

        model_ids = self.pool.get('ir.model').search(tcr, uid, [('model', '=', 'hr.holidays')])
        if model_ids:
            vals['model_id'] = model_ids[0]

        mass_status_id = self.pool.get('vhr.mass.status').create(tcr, uid, vals)
        
        if disable.lower() != 'true':
            tcr.commit()
            tcr.close()
        return mass_status_id

    def open_window(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        
        disable = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_timesheet_disable_run_thread_in_selected_function') or ''
        mass_status_id = False
        try:
            log.info('Start running execute Multi Holidays')
            mass_status_id = self.create_mass_status(cr, uid, context)
            if disable.lower() != 'true':
                thread.start_new_thread(vhr_holidays_multi.thread_execute, (self, cr, uid, ids, mass_status_id, context))
            else:
                self.thread_execute(cr, uid, ids, mass_status_id, context)
                
        except Exception as e:
            log.exception(e)
            log.info('Error: Unable to start thread execute Multi Holidays')

        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        result_context = {}
        if context is None:
            context = {}
        result = mod_obj.get_object_reference(cr, uid, 'vhr_timesheet', 'act_tracking_vhr_holidays_multi')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        
        result['res_id'] = mass_status_id
        result['view_type'] = 'form'
        result['view_mode'] = 'form,tree'
        result['views'].sort()
        return result

    def thread_execute(self, cr, uid, ids, mass_status_id, context=None):
        if not context:
            context = {}
        log.info('Start execute multi leave request')
        disable = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_timesheet_disable_run_thread_in_selected_function') or ''
        
        
        holiday_pool = self.pool.get('hr.holidays')
        holiday_status_pool = self.pool.get('hr.holidays.status')
        mass_status_pool = self.pool.get('vhr.mass.status')
        mass_status_detail_pool = self.pool.get('vhr.mass.status.detail')
        
        if disable.lower() != 'true':
            _pool = ConnectionPool(int(tools.config['db_maxconn']))
            # cr used to create WR
            cr = Cursor(_pool, cr.dbname, True)
            # t_cr used to create/write Mass Status/ Mass Status Detail
            t_cr = Cursor(_pool, cr.dbname, True)  # Thread's cursor
        else:
            t_cr = cr

        # clear old thread in cache to free memory
        if disable.lower() != 'true':
            reload(sys)
        create_ids = []
        error_message = ""
        try:
            if ids:
                if not isinstance(ids, list):
                    ids = [ids]

                record_id = ids[0]
                data = self.browse(cr, uid, record_id, context)
                company_id = data.company_id and data.company_id.id or False
                holiday_status_id = data.holiday_status_id and data.holiday_status_id.id or False
                holiday_status_name = data.holiday_status_id and data.holiday_status_id.name or ''
                is_offline = data.is_offline

#                 mass_status_id = self.create_mass_status(t_cr, uid, context)
#                 t_cr.commit()
                # if mass_status_id and company_id and holiday_status_id:
                if mass_status_id and holiday_status_id:
                    mass_status_pool.write(t_cr, uid, [mass_status_id], {'state': 'running',
                                                                         'number_of_record': len(data.employee_ids),
                                                                         'number_of_execute_record': 0,
                                                                         'number_of_fail_record': 0})
                    
                    if disable.lower() != 'true':
                        t_cr.commit()
                    list_error = []
                    num_count = 0
                    for employee in data.employee_ids:
                        num_count += 1
                        mass_status_pool.write(t_cr, uid, [mass_status_id], {'number_of_execute_record': num_count})
                        error_item = ''
                        try:
                            if disable.lower() == 'true':
                                cr.execute('SAVEPOINT import')
                            employee_id = employee.id
                            vals = {}
                            reserve_vals = {'holiday_type': 'employee',
                                            'employee_id': employee_id,
                                            # 'company_id': company_id,
                                            'notes': data.notes,
                                            'date_from': data.date_from,
                                            'date_to': data.date_to,
                                            'is_offline': is_offline,
                                            'holiday_status_id': holiday_status_id,
                                            'user_id': uid,
                                            'state': 'draft',
                                            'type': 'remove',
                            }
                            # Get data from onchange employee: company_id, name, employee_code, remaining_leaves
                            vals_employee = holiday_pool.onchange_employee_id(cr, uid, [], employee_id,
                                                                              holiday_status_id, False, False, False, 0,is_offline,
                                                                              context)
                            vals.update(vals_employee['value'])

                            #Get data from onchange company: department_id, dept_head_id, report_to_id
                            #                             vals_comp = holiday_pool.onchange_company_id(cr, uid, [], employee_id, company_id, context)
                            #                             vals.update(vals_comp['value'])

                            #Get data from onchange holiday_status: holiday_status_description, max_leaves, 
                            #                                       leaves_taken, remaining_leaves, virtual_remaining_leaves, limit
                            context['forced_get_default_holiday_status'] = True
                            vals_holiday_status = holiday_pool.onchange_holiday_status_id(cr, uid, [], employee_id,
                                                                                          company_id, holiday_status_id,
                                                                                          data.date_from, data.date_to,
                                                                                          holiday_line_ids=False,
                                                                                          number_of_days_temp=0,
                                                                                          is_offline=is_offline,
                                                                                          context=context)
                            vals.update(vals_holiday_status['value'])
                            domain_holiday_status = vals_holiday_status.get('domain',{}).get('holiday_status_id',[])
                            approve__holiday_status_ids = holiday_status_pool.search(cr, uid, domain_holiday_status)
                            if holiday_status_id not in approve__holiday_status_ids:
                                error_item = "Employee can't register leave request with leave type '%s' " % holiday_status_name
                                list_error.append((employee_id, error_item))
                            else:

                                #Copy data holiday line in multi holiday
                                vals_holiday_line = self.copy_data_holiday_line_from_multi_holiday(cr, uid, record_id,
                                                                                                   holiday_status_id,
                                                                                                   employee_id,
                                                                                                   vals.get('max_leaves',
                                                                                                            0),
                                                                                                   context)
                                vals.update(vals_holiday_line)
    
                                if not vals['holiday_line_ids']:
                                    date_from_str = datetime.strptime(data.date_from, DEFAULT_SERVER_DATE_FORMAT).strftime(
                                        "%d-%m-%Y")
                                    date_to_str = datetime.strptime(data.date_to, DEFAULT_SERVER_DATE_FORMAT).strftime(
                                        "%d-%m-%Y")
                                    raise osv.except_osv('Validation Error !',
                                                         'Employee dont have working shift from %s to %s !' % (
                                                             date_from_str, date_to_str))
    
    #                             elif vals.get('holiday_status_id', False) and vals['holiday_status_id'] != holiday_status_id:
    #                                 holiday_status = self.pool.get('hr.holidays.status').read(cr, uid, holiday_status_id,
    #                                                                                           ['name'])
    #                                 holiday_status_name = holiday_status.get('name', '')
    #                                 raise osv.except_osv('Validation Error !',
    #                                                      'Employee dont have remaining leaves of leave type "%s" !' % holiday_status_name)
    
                                vals.update(reserve_vals)
                                res = holiday_pool.create(cr, uid, vals, context)
                                if res:
                                    create_ids.append(res)
                                    mass_status_detail_pool.create(t_cr, uid, {'mass_status_id': mass_status_id,
                                                                                   'employee_id': employee_id,
                                                                                   'message': '',
                                                                                   'status': 'success'})
                                
                            if disable.lower() == 'true':
                                cr.execute('RELEASE SAVEPOINT import')

                        except Exception as e:
                            log.exception(e)
                            try:
                                error_item = e.message
                                if not error_item:
                                    error_item = e.value
                            except:
                                error_item = ""

                            list_error.append((employee_id, error_item))
                            
                            if disable.lower() == 'true':
                                cr.execute('ROLLBACK TO SAVEPOINT import')

                        if error_item:
                            mass_status_pool.write(t_cr, uid, [mass_status_id],
                                                   {'number_of_fail_record': len(list_error)})
                            mass_status_detail_pool.create(t_cr, uid, {'mass_status_id': mass_status_id,
                                                                       'employee_id': list_error[-1][0],
                                                                       'message': list_error[-1][1]})
                            
                            if disable.lower() != 'true':
                                t_cr.commit()
                                cr.rollback()
                        else:
                            if disable.lower() != 'true':
                                # if dont have error, then commit
                                t_cr.commit()
                                cr.commit()

                    if list_error:
                        mass_status_pool.write(t_cr, uid, [mass_status_id],
                                               {'state': 'error', 'number_of_fail_record': len(list_error)})

                    else:
                        mass_status_pool.write(t_cr, uid, [mass_status_id], {'state': 'finish'})

#                 if create_ids and data.is_offline:
#                     holiday_pool.signal_confirm(cr, uid, create_ids)
        except Exception as e:
            log.exception(e)
            try:
                error_message = e.message
                if not error_message:
                    error_message = e.value
            except:
                error_message = ""
            
            if disable.lower() != 'true':
                # If have error with first try, then rollback to clear all created holiday
                cr.rollback()
                if create_ids:
                    holiday_pool.write(cr, uid, create_ids, {'state': 'draft'}, context)
                    holiday_pool.unlink(cr, uid, create_ids, context)
            log.info('Error occur while Multi Holiday!')

        if error_message:
            # Use cr in here because InternalError if use t_cr
            mass_status_pool.write(cr, uid, [mass_status_id], {'state': 'fail', 'error_message': error_message})

        # Delete all mullti holiday to fresh database, dont use osv_memory because it's take so many times to reupgrade
        multi_holiday_ids = self.search(cr, uid, [])
        self.unlink(cr, uid, multi_holiday_ids, context)
        
        if disable.lower() != 'true':
            cr.commit()
            cr.close()
    
            t_cr.commit()
            t_cr.close()
        log.info('End execute multi holiday')
        return True

    def copy_data_holiday_line_from_multi_holiday(self, cr, uid, holiday_multi_id, holiday_status_id, employee_id,
                                                  max_leaves, context=None):
        """
        Only copy holiday line, create function will check if it employee dont have remaining leave
        """
        res_holiday_line = []
        holiday_line_pool = self.pool.get('vhr.holiday.line')
        holiday_pool = self.pool.get('hr.holidays')
        parameter_obj = self.pool.get('ir.config_parameter')
        leave_type_obj = self.pool.get('hr.holidays.status')
        
        number_of_days_temp = 0
        number_of_hours = 0
        if holiday_multi_id and holiday_status_id and employee_id:
            
            #OT and annual leave
            special_holiday_status_code = parameter_obj.get_param(cr, uid, 'leave_type_code_for_accumulation') or ''
            special_holiday_status_code = special_holiday_status_code.split(',')
            special_holiday_status_ids = leave_type_obj.search(cr, uid, [('code','in',special_holiday_status_code)])
            
            holiday_line_ids = holiday_line_pool.search(cr, uid, [('holiday_multi_id', '=', holiday_multi_id)])
#             list_date_selected = []

            record = self.browse(cr, uid, holiday_multi_id, fields_process=['company_id', 'date_from', 'date_to'])
            company_id = record.company_id and record.company_id.id or False
            date_from = record.date_from or False
            date_to = record.date_to or False
            
            list_date_available, dict_hours, dict_type_workday = holiday_pool.generate_date(cr, uid, employee_id, company_id, date_from[:10],
                                                             date_to[:10])
            if holiday_line_ids:
                fields = ['date', 'status', 'number_of_days_temp', 'holiday_status_id']
                holiday_lines = holiday_line_pool.read(cr, uid, holiday_line_ids, fields)
                for holiday_line in holiday_lines:
                    vals = {}
                    for field in fields:
                        vals[field] = holiday_line.get(field, False)
                        if isinstance(vals[field], tuple):
                            vals[field] = vals[field][0]

#                     list_date_selected.append(vals['date'])
                    date = vals.get('date',False)
                    vals['number_of_hours_in_shift']  = date in dict_hours and dict_hours[date] or 0
                    vals['number_of_days_temp'] = dict_type_workday.get(date,1) * vals['number_of_days_temp']
                    vals['number_of_hours']= (date in dict_hours and dict_hours[date] or 0) * vals['number_of_days_temp'] / dict_type_workday.get(date,1)
                    res_holiday_line.append([0, False, vals])
                    
                    number_of_days_temp += vals['number_of_days_temp']
                    number_of_hours += vals['number_of_hours']

            holiday_status = self.pool.get('hr.holidays.status').read(cr, uid, holiday_status_id, ['name', 'limit'])
            limit = holiday_status.get('limit', False)
            holiday_status_name = holiday_status.get('name', '')
            if limit:
                return {'holiday_line_ids': res_holiday_line}

            # Get list date in working shift of employee from date_from to date_to
            
            

#             list_intersect = list(set(list_date_available).intersection(set(list_date_selected)))

#             remove_items = []
#             for item in res_holiday_line:
#                 if item[2]['date'] not in list_intersect:
#                     remove_items.append(item)
#                 else:
#                     number_of_days_temp += item[2]['number_of_days_temp']
# 
#             res_holiday_line = [item for item in res_holiday_line if item not in remove_items]
#             
#             if holiday_status_id in special_holiday_status_ids:
#                 for item in res_holiday_line:
#                     line_date = item[2]['date']
#                     if line_date in dict_hours:
#                         item[2]['number_of_hours_in_shift'] = dict_hours.get(line_date,0)
#                         item[2]['number_of_hours'] = item[2]['number_of_hours_in_shift'] * item[2]['number_of_days_temp'] \
#                                                                                          / dict_type_workday.get(line_date,1)
#                     
#                         number_of_hours += item[2]['number_of_hours']

            # if not max_leaves or max_leaves < number_of_days_temp:
        #                 date_from_str = datetime.strptime(date_from, DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y")
#                 date_to_str = datetime.strptime(date_to, DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y")
#                 raise osv.except_osv('Validation Error !',
#                                      'Employee dont have enough remaining leaves of "%s" to make a leave request from %s to %s !' % (
#                                          holiday_status_name, date_from_str, date_to_str))

        return {'holiday_line_ids': res_holiday_line, 'number_of_days_temp': number_of_days_temp, 'number_of_hours': number_of_hours}
    
    
    def parse_data_from_excel_row(self, cr, uid, row, mapping_fields, fields_search_by_name, fields_order, object, context=None):
        res = {}
        error = ""
        if row and mapping_fields and fields_order:
            pool = self.pool.get(object)
            for index, item in enumerate(row):
                #If item in row does not appear in mapping fields, by pass  
                field_name = mapping_fields.get(fields_order[index])
                if field_name:
                    if field_name == 'month':
                        print '1'
                    field_obj = pool._all_columns.get(field_name)
                    field_obj = field_obj and field_obj.column
                    if field_obj and field_obj._type == 'many2one':
                        model = field_obj._obj
                        value = str(item).strip()
                        
                        try:
                            value = value.replace('\xc2\xa0','')
                        except Exception as e:
                            log.exception(e)
                        
                        if field_name == 'employee_id':
                            res['employee_code'] = value
                            
                        if value:
                            
                            #Assign False to field_name if value == 'false'
                            if value in ['false','0']:
                                res[field_name] = False
                                continue
                            
                            domain = ['|',('code','=ilike', value),('name','=ilike', value)]
                            if field_name in fields_search_by_name:
                                domain = [('name','=ilike', value)]
                            elif 'name_en' in self.pool.get(model)._all_columns:
                                domain.append(('name_en','ilike', value))
                                domain.insert(0,'|')
                                
                            record_ids = self.pool.get(model).search(cr, uid, domain, context=context)
                            
                            #Try one more time with inactive record
                            if not record_ids and field_name != 'contract_id':
                                domain.insert(0,('active','=', False))
                                record_ids = self.pool.get(model).search(cr, uid, domain)
                                
                            if len(record_ids) == 0:
                                error = "Can't find record of '%s' with input data '%s' for field '%s'" % (model, value, field_obj.string)
                                return res, error
                            elif len(record_ids) ==1:
                                res[field_name] = record_ids[0]
                                
                            else:#len >=2
                                error = "Have %s record of '%s' with input data '%s' for field '%s'" % (len(record_ids), model, value, field_obj.string)
                                return res, error
                            
                    elif field_obj and field_obj._type == 'date':
                        try:
                            item = str(item)
                            print 'date=',item,'len=',len(item)
                            value = False
                            if item:
                                value = datetime.strptime(item,"%d/%m/%Y").strftime(DEFAULT_SERVER_DATE_FORMAT)
                            res[field_name] = value
                        except Exception as e:
                            error = "Field %s have to input correct date format dd/mm/YYYY" % field_obj.string 
                    
                    elif (field_obj and field_obj._type == 'boolean') or field_name == 'is_generate_salary':
                        value = str(item).lower()
                        if value == 'true' or value == '1':
                            res[field_name] = True
                        else:
                            res[field_name] = False
                    
                    elif field_obj and field_obj._type in ['text','char']:
                        #Khong ghi de du lieu len description neu khong co data import
                        if field_name == 'description' and len(item) == 0:
                            continue
                        res[field_name] = item
                        if field_name == 'name':
                            res['is_create_code'] = True
                    
                    elif field_obj and field_obj._type == 'float':
                        try:
                            res[field_name] = item and float(item) or 0
                        except Exception as e:
                            error = "Field '%s' have to input number" % field_obj.string 
                    
                    elif field_obj and field_obj._type in ['integer','selection']:
                        #Selection for field month
                        try:
                            res[field_name] = item and int(item) or 0
                        except Exception as e:
                            error = "Field '%s' have to input number" % field_obj.string 
                        
                    #log to trace back
                    elif not field_obj and field_name=='xml_id':
                        res[field_name] = str(item).strip()
                    
                            
        
        return res, error


vhr_holidays_multi()