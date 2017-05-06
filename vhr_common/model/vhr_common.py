# -*-coding:utf-8-*-
import datetime
import logging
import re
import math
import openerp

from openerp.osv import osv
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.addons.audittrail import audittrail
from openerp import SUPERUSER_ID
from openerp.tools.translate import _

log = logging.getLogger(__name__)


###########################Function convert number to character (anhnh4)
##################
zero_to_nineteen = 'zero one two three four five six seven eight nine ten eleven twelve ' \
                   'thirteen fourteen fifteen sixteen seventeen eighteen nineteen'.split()

zero_to_nineteen_vi = [u'không', u'một', u'hai', u'ba', u'bốn', u'năm', u'sáu', u'bảy', u'tám', u'chín', u'mười',
                       u'mười một', u'mười hai', u'mười ba', u'mười bốn', u'mười lăm', u'mười sáu', u'mười bảy',
                       u'mười tám', u'mười chín']

decades = 'zero ten twenty thirty forty fifty sixty seventy eighty ninety'.split()

decades_vi = [u'không', u'mười', u'hai mươi', u'ba mươi', u'bốn mươi', u'năm mươi',
              u'sáu mươi', u'bảy mươi', u'tám mươi', u'chín mươi']

ten_to_the_3n = 'ones thousand million billion trillion'.split()

ten_to_the_3n_vi = ['ones', u'ngàn', u'triệu', u'tỷ', u'tỷ tỷ']



def convert_number_to_char(n, locale='VN'):
    if not n:
        if locale == 'US':
            return zero_to_nineteen[0]
        else:
            return zero_to_nineteen_vi[0]
    if 0 < n:
        sign = ''
    else:
        n = -n
        sign = '-'
    if n < 1000:
        rv = hundreds(n, locale=locale)
    else:
        rv = thousands(n, locale=locale)
    if sign:
        rv[:0] = [sign, ]
    if rv[-1] == ten_to_the_3n[0] or rv[-1] == ten_to_the_3n_vi[0]:
        del rv[-1]
    else:
        if not n:
            if locale == 'US':
                return zero_to_nineteen[0]
            else:
                return zero_to_nineteen_vi[0]
        if 0 < n:
            sign = ''
        else:
            n = -n
            sign = '-'
        if n < 1000:
            rv = hundreds(n, locale=locale)
        else:
            rv = thousands(n, locale=locale)
        if sign:
            rv[:0] = [sign, ]
        if rv[-1] == ten_to_the_3n[0] or rv[-1] == ten_to_the_3n_vi[0]:
            del rv[-1]
    return' '.join(rv)

def tens(n, locale='VN'):
    if n < 20:
        if n == 0:
            if locale == 'US':
                return [decades[0], ]
            else:
                return [decades_vi[0], ]
        if locale == 'US':
            return [zero_to_nineteen[n], ]
        else:
            return [zero_to_nineteen_vi[n], ]

    decade, remainder = divmod(n, 10)
    if locale == 'US':
        rv = [decades[decade], ]
    else:
        rv = [decades_vi[decade], ]
    if remainder:
        if locale == 'US':
            rv.append(zero_to_nineteen[remainder])
        else:
            rv.append(zero_to_nineteen_vi[remainder])
    return [' '.join(rv), ]


def hundreds(n, locale='VN'):
    n, remainder = divmod(n, 100)
    if remainder:
        rv = tens(remainder, locale=locale)
    else:
        rv = []
    if n:
        if locale == 'US':
            rv[:0] = [zero_to_nineteen[n], 'hundred']
        else:
            rv[:0] = [zero_to_nineteen_vi[n], u'trăm']
    return rv


def thousands(n, locale='VN'):
    rv = []
    p = 0
    while n:
        n, remainder = divmod(n, 1000)
        if p < len(ten_to_the_3n):
            if remainder:
                if locale == 'US':
                    rv[:0] = hundreds(remainder, locale=locale)+[ten_to_the_3n[p], ]
                else:
                    rv[:0] = hundreds(remainder, locale=locale)+[ten_to_the_3n_vi[p], ]
        else:
            rv[:0] = ['really-huge', ]
            return rv
        p += 1
    return rv
    
##################End Function convert number to character (anhnh4)
##################

class vhr_common(object):
    @staticmethod
    def validate_date(data):
        try:
            return datetime.datetime.strptime(data, "%Y-%m-%d %H:%M:%S")
        except Exception as e:
            try:
                log.info(e)
                return datetime.datetime.strptime(data, "%Y-%m-%d")
            except Exception as e:
                log.info(e)
                return False
    
    
    def validate_number(self, data, field_name,context=None):
        """
        Return True if data only have 0,1,2,3,4,5,6,7,8,9 ,-; 
        """
        if data:
            result = re.search('^[0-9,;-]+$',data)
            if result:
                return True
        
        raise osv.except_osv('Validation Error !', 'Incorrect %s format !\n(e.g: 090-123-456)'%field_name)

    def find_day_overlap(self, cr, uid, range_one, range_two, context=None):
        """It will return number of days of overlap
            Param:
                range_one, range_two = {
                                        'start_date' : '2014-01-28'
                                        'end_date' : '2014-02-01'
                                        }
        """

        try:
            if not isinstance(range_one, dict) or not range_one.has_key('start_date') or not range_one.has_key(
                    'start_date'):
                log.info("Don't have enough information. We need both start date and end date!")
                return False
            if not isinstance(range_two, dict) or not range_two.has_key('start_date') or not range_two.has_key(
                    'start_date'):
                log.info("Don't have enough information. We need both start date and end date!")
                return False
            r1_start = self.validate_date(range_one['start_date'])
            r1_end = self.validate_date(range_one['end_date'])
            r2_start = self.validate_date(range_two['start_date'])
            r2_end = self.validate_date(range_two['end_date'])
            if not r1_start or not r1_end or not r2_start or not r2_end:
                log.info('Format is invalid')
                return False
            latest_start = max(r1_start, r2_start)
            earliest_end = min(r1_end, r2_end)
            overlap = (earliest_end - latest_start).days + 1
            return overlap
        except Exception as e:
            log.info(e)
            return False

    @staticmethod
    def compare_day(date_one, date_two):
        """It will return number range of 2 date
            Param:
                range_one, range_two = {
                                        'start_date' : '2014-01-28'
                                        'end_date' : '2014-02-01'
                                        }
        """
        date_one = datetime.datetime.strptime(date_one, '%Y-%m-%d')
        date_two = datetime.datetime.strptime(date_two, '%Y-%m-%d')
        res = date_two - date_one
        return res.days
    
    def convert_from_float_to_float_time(self, number, context=None):
        """
        Convert from float number to float time
        ex: 12.5 --> 12:30
        """
        result = ''
        if number:
            floor_number = int(math.floor(number))
            result += str(floor_number)
            gap =  number - floor_number
            if gap > 0:
                minute = int(round(gap * 60))
                if minute < 10:
                    minute = '0' + str(minute)
                else:
                    minute = str(minute)
                result += ':' + minute
            else:
                result += ':00'
        
        return result
    
    #get all low level department of department_ids
    def get_child_department(self, cr, uid, department_ids, context=None):
        res = []
        if department_ids:
            for department_id in department_ids:
                sql = """
                        WITH RECURSIVE department(id, name,parent_left,parent_right,parent_id,depth) AS (
                                SELECT g.id, g.name, g.parent_left,g.parent_right,g.parent_id, 1
                                FROM hr_department g where id =%s
                              UNION ALL
                                SELECT g.id, g.name, g.parent_left,g.parent_right,g.parent_id, sg.depth + 1
                                FROM hr_department g, department sg
                                WHERE g.parent_id = sg.id and g.active=True
                        )
                        SELECT id FROM department;
                      """
                
                cr.execute(sql % department_id)
                results = cr.fetchall()
                res.extend( [res_id[0] for res_id in results] )
        
        return res
    
    def get_parent_department_by_sql(self, cr, uid, department_ids, context=None):
        res = []
        if department_ids:
            for department_id in department_ids:
                sql = """
                        WITH RECURSIVE department(id, name,parent_left,parent_right,parent_id,depth) AS (
                                SELECT g.id, g.name, g.parent_left,g.parent_right,g.parent_id, 1
                                FROM hr_department g where id =%s
                              UNION ALL
                                SELECT g.id, g.name, g.parent_left,g.parent_right,g.parent_id, sg.depth + 1
                                FROM hr_department g, department sg
                                WHERE g.id = sg.parent_id and g.active=True
                        )
                        SELECT id FROM department;
                      """
                
                cr.execute(sql % department_id)
                results = cr.fetchall()
                res.extend( [res_id[0] for res_id in results] )
        
        return res
            
        
    def get_hierachical_department_from_manager(self, cr, uid, manager_id, context=None):
        """
        Trả về danh sách phòng ban và phòng ban con của manager_id
        vd: A là manager của pb deptA, deptA có pb con là deptB,deptC, deptB có pb con là deptB1,deptB2
        thì sẽ return [deptA, deptB, deptC, deptB1, deptB2]
        """
        res = []
        if manager_id:
            sql = """
                    WITH RECURSIVE department(id, name,parent_left,parent_right,parent_id,depth) AS (
                            SELECT g.id, g.name, g.parent_left,g.parent_right,g.parent_id, 1
                            FROM hr_department g where manager_id =%s
                          UNION ALL
                            SELECT g.id, g.name, g.parent_left,g.parent_right,g.parent_id, sg.depth + 1
                            FROM hr_department g, department sg
                            WHERE g.parent_id = sg.id and g.active=True
                    )
                    SELECT id FROM department;
                  """
            
            cr.execute(sql % manager_id)
            results = cr.fetchall()
            res = [res_id[0] for res_id in results]
        
        return res
    
    #Get all department which have hrbp is employee_id
    def get_department_of_hrbp(self, cr, uid, employee_id, context=None):
        department_ids = []
        if employee_id:
            department_ids = self.pool.get('hr.department').search(cr, uid, [('hrbps','=',employee_id)], context={'active_test': False})
        
        return department_ids
    
    #Get all department which have ass_hrbp is employee_id
    def get_department_of_ass_hrbp(self, cr, uid, employee_id, context=None):
        department_ids = []
        if employee_id:
            department_ids = self.pool.get('hr.department').search(cr, uid, [('ass_hrbps','=',employee_id)], context={'active_test': False})
        
        return department_ids

    #Get all department which have hrbp and ass_hrbp is employee_id
    def get_department_of_all_hrbps(self, cr, uid, employee_id, context=None):
        department_ids = []
        if employee_id:
            department_ids = self.pool.get('hr.department').search(cr, uid, ['|', ('hrbps', '=', employee_id),
                                                                             ('ass_hrbps', '=', employee_id)])

        return department_ids
    
    #Get list record hrbp/ assist hrbp can see base on field employee._id
    #Input is: 1. object have field employee_id or object hr.employee 
    #          2.  user_id
    def get_records_for_user_of_group_hrbp_and_assist(self, cr, uid, object, user_id, context=None):
        """
        Remember this function only apply for hr.employee and objects have field employee_id
        """
        object_ids = []
        if object and user_id:
            employee_pool = self.pool.get('hr.employee')
            mcontext = {'search_all_employee': True}
            login_employee_ids = employee_pool.search(cr, uid, [('user_id','=',user_id)], 0, None, None, context=mcontext)
            if login_employee_ids:
                #Get list department which user is hrbp or assist_hrbp
                department_hrbp = self.get_department_of_hrbp(cr, uid, login_employee_ids[0], context)
                department_ass_hrbp = self.get_department_of_ass_hrbp(cr, uid, login_employee_ids[0], context)
                department_ids = department_hrbp + department_ass_hrbp
                
                #Get list employee belong to department which employee is hrbp/ assist hrbp
                object_ids = self.get_records_for_user_base_on_department_of_emp(cr, uid, object, department_ids, context)
        
        return object_ids
    
    #Return list record of object have employee in department_ids
    #Only apply for object hr.employee and object have field employee_id
    def get_records_for_user_base_on_department_of_emp(self, cr, uid, object, department_ids, context=None):
        """
        Remember this function only apply for hr.employee and objects have field employee_id
        """
        object_ids = []
        if object and department_ids:
            #Get list employee belong to department which employee is hrbp/ assist hrbp
            mcontext = {'search_all_employee': True, 'active_test': False}
            employee_ids = self.pool.get('hr.employee').search(cr, uid, [('department_id','in',department_ids)], 0, None, None, context=mcontext)
             
            if object == 'hr.employee':
                object_ids = employee_ids
            else:
                object_ids = self.pool.get(object).search(cr, uid, [('employee_id','in',employee_ids)], 0, None, None, context)
         
        return object_ids
    
    
    ###Thangvq comment: Must be install module vhr_timesheet before using this function
    def get_list_employees_of_dept_admin(self, cr, uid, dept_admin_id, context=None):
        """
            dept_admin_id is employee_id of dept_admin
        """
        
        employee_ids = []
        try:
            if dept_admin_id:
                today = datetime.datetime.today().date()
                #Get all timesheet of admin dept at present
                timesheet_detail_pool = self.pool.get('vhr.ts.timesheet.detail')
                detail_ids = timesheet_detail_pool.search(cr, uid, [('admin_id','=',dept_admin_id),
                                                                    ('from_date','<=',today),
                                                                    ('to_date','>=',today)])
                
                if detail_ids:
                    details = timesheet_detail_pool.read(cr, uid, detail_ids, ['timesheet_id'])
                    timesheet_ids = []
                    for detail in details:
                        timesheet_id = detail.get('timesheet_id', False) and detail['timesheet_id'][0]
                        if timesheet_id:
                            timesheet_ids.append(timesheet_id)
                    
                    #Get all employee using timesheet of admin dept at present
                    if timesheet_ids:
                        ts_emp_ids = self.pool.get('vhr.ts.emp.timesheet').search(cr, uid, [('timesheet_id','in', timesheet_ids),
                                                                                            ('active','=',True)])
                        
                        if ts_emp_ids:
                            ts_emps = self.pool.get('vhr.ts.emp.timesheet').read(cr, uid, ts_emp_ids, ['employee_id'])
                            for ts_emp in ts_emps:
                                employee_id = ts_emp.get('employee_id', False) and ts_emp['employee_id'][0]
                                employee_ids.append(employee_id)
        except Exception as e:
            log.info("\n\n You need to install module vhr_timesheet to get list employee of dept admin\n\n")
            log.exception(e)
        
        return employee_ids
    
    def get_groups_of_user_from_sql(self, cr, uid):
        groups = []
        if uid:
            sql = """
                    SELECT name FROM ir_model_data WHERE model='res.groups' and res_id in
                        (SELECT gid FROM res_groups_users_rel WHERE uid=%s)
                  """
            cr.execute(sql % uid)
            results = cr.fetchall()
            groups = [res_id[0] for res_id in results]
            
        return groups
    
    #Filter record base on group/permission of user belong to(only for object have field employee_id or object hr.employee)
    def get_domain_for_object_base_on_groups(self, cr, uid, args, object, context=None):
        """
        Currently only apply for employee and contract
        
        Filter list record can see base on group/ permission by position(dept head)
        This function can only run correctly for hr.employee and objects have field employee_id
        
        * Group C&B/ C&B Manager/ HR Dept Head/ AF Admin:   Do not filter
        * Group HRBP/ Assistant to HRBP:  can only see records of employees in departments where login user is HRBP/ Assistant to HRBP
        * Dept Head of department: see records of employees in departments where login user is manager
        * Dept Admin: see record of employee using timesheet which login user is admin dept at present(can't see contract of employee in department where user is dept admin)
        """
        if not context:
            context = {}
        
#         log.info('\n\n <<<<< Start filter records based on list employees can see--')
        nargs = []
        try:
            if context.get('filter_by_group', False):
                context['filter_by_group'] = False
                groups = self.get_groups_of_user_from_sql(cr, uid)
                #Read all record if belong to these group
                dont_filter_group = ['hrs_group_system','vhr_hr_dept_head','vhr_af_admin','vhr_cnb_manager',
                                     'vhr_cb','vhr_cb_profile','vhr_cb_contract','vhr_cb_working_record',
                                     'vhr_cb_termination']
                if object == 'hr.employee':
                    dont_filter_group.extend(['vhr_hr_admin','vhr_fa','vhr_update_fa_hrbp_viewer','vhr_recruiter'])
                elif object == 'hr.contract':
                    dont_filter_group.extend(['vhr_cb_contract_readonly'])
                    if 'vhr_af_admin' in dont_filter_group:
                        dont_filter_group.remove('vhr_af_admin')
                    
                    if 'vhr_cb' in dont_filter_group:
                        dont_filter_group.remove('vhr_cb')
                    
                    if 'vhr_cb_profile' in dont_filter_group:
                        dont_filter_group.remove('vhr_cb_profile')
                    
                if set(dont_filter_group).intersection(set(groups)):
#                     log.info('\n >>>> End filter records based on list employees can see--\n')
                    return args
                #Thay nhung record co employee_id thuoc ve department ma user la HRBP/ assistant HRBP
                elif set(['vhr_hrbp','vhr_assistant_to_hrbp']).intersection(set(groups)):
#                     log.info('\n get_records_for_user_of_group_hrbp_and_assist--')
                    record_ids = self.get_records_for_user_of_group_hrbp_and_assist(cr, uid, object, uid, context)
                    nargs.extend([('id','in',record_ids)])
                    
                #Dept Head can see record of it's employee
                mcontext = {'search_all_employee': True,'active_test': False}
                
                login_employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=',uid)], 0, None, None, context=mcontext)
                if login_employee_ids:
                    department_ids = self.get_hierachical_department_from_manager(cr, uid, login_employee_ids[0], context)
                    
                    if department_ids:
                        record_ids = self.get_records_for_user_base_on_department_of_emp(cr, uid, object, department_ids, context)
                        if record_ids:
                            if nargs:
                                nargs.insert(0,'|')
                            nargs.extend([('id','in',record_ids)])
                    
                    
                    #Get all record by employee using timesheet of admin dept at present
                    employee_ids = []
                    if not context.get('do_not_filter_for_dept_admin', False):
                        employee_ids = self.get_list_employees_of_dept_admin(cr, uid, login_employee_ids[0], context)
                        
                    #Get employee have report_to = login_employee_ids
#                     employee_lm_ids = self.pool.get('hr.employee').search(cr, uid, [('report_to','in',login_employee_ids)])    
                        
                    #Login user can see record of he/she
#                     employee_ids += login_employee_ids + employee_lm_ids
                    object_ids = []
                    if object == 'hr.employee':
                        object_ids = employee_ids
                    else:
                        object_ids = self.pool.get(object).search(cr, uid, [('employee_id','in',employee_ids)], 0, None, None, context)
                    
                    if object_ids:
                        if nargs:
                            nargs.insert(0,'|')
                        nargs.extend([('id','in',object_ids)])
                    
                if not nargs:
                    nargs.extend([('id','in',[])])
                
                context['filter_by_group'] = True
                
        except Exception as e:
            log.exception(e)
            error_message = ''
            try:
                error_message = e.message
                if not error_message:
                    error_message = e.value
            except:
                error_message = ""
            raise osv.except_osv('Validation Error !', 'Have error during filter list record:\n %s!' % error_message)
        
        args += nargs
#         log.info('\n >>>> End filter records based on list employees can see--\n')
        return args
    
    def update_active_of_record_in_object_cm(self, cr, uid, object, context=None):
        """
        Update active of record base on effect_from, effect_to, active
        Object need to update effect_to when possible
        """
        active_record_ids = []
        inactive_record_ids = []
        if object:
            today = datetime.datetime.today().date()
            object_pool = self.pool.get(object)
            
            active_record_ids = object_pool.search(cr, uid, [('active','=',False),
                                                             ('effect_from','<=',today),
                                                              '|',('effect_to','=',False),
                                                                  ('effect_to','>=',today)])
        
            #Get records have active=True need to update active=False
            inactive_record_ids = object_pool.search(cr, uid, [('active','=',True),
                                                              '|',('effect_to','<',today),
                                                                  ('effect_from','>',today)])
             
#             record_ids = active_record_ids + inactive_record_ids
            for record_id in active_record_ids:
                object_pool.write(cr, uid, record_id, {'active': True})
            
            if inactive_record_ids:
                object_pool.write(cr, uid, inactive_record_ids, {'active': False})
                
#             if record_ids:
#                 self.update_active_of_record_cm(cr, uid, object, record_ids, context)
            
        return active_record_ids, inactive_record_ids
    
    #TODO: remove this function
    def update_active_of_record_cm(self, cr, uid, object, record_ids, context=None):
        """
        Update active of record_ids in object base on effect_from, effect_to
        """
        if not context:
            context = {}
        res = []
        if record_ids and object:
            object_pool = self.pool.get(object)
            records = object_pool.read(cr, uid, record_ids, ['effect_from','effect_to','active'])
            for record in records:
                effect_from = record.get('effect_from', False)
                effect_from = effect_from and datetime.datetime.strptime(effect_from,
                                                                DEFAULT_SERVER_DATE_FORMAT).date() or False

                effect_to = record.get('effect_to', False)
                effect_to = effect_to and datetime.datetime.strptime(effect_to,
                                                            DEFAULT_SERVER_DATE_FORMAT).date() or False

                active = record.get('active', False)
                today = datetime.datetime.today().date()

                if effect_from <= today and (not effect_to or effect_to >= today) and not active:
                    object_pool.write(cr, uid, record.get('id', False), {'active': True}, context)
                    res.append(record.get('id', False))

                elif effect_to and effect_to < today and active:
                    object_pool.write(cr, uid, record.get('id', False), {'active': False}, context)

                elif effect_from > today and active:
                    object_pool.write(cr, uid, record.get('id', False), {'active': False}, context)
        
        return res
                    
    def call_parent_store_compute(self, cr, uid):
        return self._parent_store_compute(cr)

    def format_date(self, cr, uid, res_id, str_date='', type='VN', sep='/', context=None):
        if str_date:
            res_date = datetime.datetime.strptime(str_date[:10], '%Y-%m-%d')
            if type == 'VN':
                result = res_date.strftime('%d'+sep+'%m'+sep+'%Y')
            else:
                result = res_date.strftime('%b'+sep+'%d'+sep+'%Y')
            return result

        return ''

    def get_group_id(self, cr, uid, module, xml_id, context=None):
        """
        Param:
            Module Name, Group XML ID
        Return Group ID
        """
        group_id = False
        model_data = self.pool.get('ir.model.data')
        ids = model_data.search(cr, uid, [('module', '=', module), ('name', '=', xml_id)], context=context)
        if ids:
            res_data = model_data.read(cr, uid, ids[0], ['res_id'], context=context)
            group_id = res_data['res_id']
        return group_id
    
    
    def convert_from_date_to_date_string(self, date):
        '''
        Convert '2015-01-31' to ngày 31 tháng 1 năm 2015
        '''
        res = ''
        if date:
            date = datetime.datetime.strptime(date, "%Y-%m-%d")
            
            day = date.day
            month = date.month
            year = date.year
            
            res = u'ngày ' + str(day) + u' tháng ' + str(month) + u' năm ' + str(year)
        else:
            res = u'ngày ...'
        
        return res

    def convert_number_to_char(self, number, locale='VN'):
        return convert_number_to_char(number, locale)
    
    def execute_create(self, cr, uid, data, context=None):
        if not context:
            context = {}
        
        model = self._name
        result = False
        try:
            log.debug("Execute create on model %s" % model)
            import time
            time1=time.time()
            result = audittrail.execute_cr(cr, uid, model, 'create', data, context)
            time2 = time.time()
            log.info("Time create %s: %s" % (model, time2-time1))
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', '%s' % (e))
        return result
    
    def execute_write(self, cr, uid, ids, data, context=None):
        if not context:
            context = {}
        
        model = self._name
        result = False
        try:
            log.debug("Execute write on model %s" % model)
            result = audittrail.execute_cr(cr, uid, model, 'write', ids, data, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', '%s' % (e))
        return result
    
    def create_with_log(self, cr, uid, vals, context=None):
        if not context:
            context = {}
            
        model = self._name
        
        res = openerp.service.model.execute_cr(cr, uid, model, 'create', vals, context)
        if res:
            mcontext = context.copy()
            mcontext['old_data'] = [{'id': res}]
            
            self.create_simple_audittrail_log(cr, uid, 'create', [res], vals.keys(), mcontext)
         
        return res
    
    def write_with_log(self, cr, uid, ids, vals, context=None):
        if not context:
            context = {}
            
        if not isinstance(ids, list):
            ids = [ids]
        
        model = self._name
#         if context.get('model_name', False):
#             model = context['model_name']
        
        fields = []
        dict_column = self._all_columns
        for field in dict_column:
            if not (dict_column[field].column and dict_column[field].column._type == 'one2many' and dict_column[field].column._obj == 'audittrail.log.line'):
                fields.append(field)
        
        old_data = self.pool.get(model).read(cr, SUPERUSER_ID, ids, fields)
        res = openerp.service.model.execute_cr(cr, uid, model, 'write', ids, vals, context)
        
        import time
        time1= time.time()
        
        mcontext = context.copy()
        mcontext['old_data'] = old_data
        
        self.create_simple_audittrail_log(cr, uid, 'write', ids, vals.keys(), mcontext)
        time2= time.time()
        
        log.info('Time to write log:%s'%(time2-time1))
        
        return res
    
    def create_simple_audittrail_log(self, cr, uid, method, ids, fields, context=None):
        """
        Create audittrail log when write to record
        Only for log field except one2many,many2many
        """
        if not context:
            context = {}
        
        old_datas = context.get('old_data', [])
        log_pool = self.pool.get('audittrail.log')
        log_line_pool = self.pool.get('audittrail.log.line')
        model_pool = self.pool.get('ir.model')
        
        user_id = context.get('user_id', uid)
        if ids and fields:
            model_ids = model_pool.search(cr, SUPERUSER_ID, [('model', '=', self._name)])
            model_id = model_ids and model_ids[0] or False
            if model_id:
                model = model_pool.browse(cr, uid, model_id)
                for old_data in old_datas:
                    record_id = old_data['id']
                    lines = self.prepare_log_line_data(cr, uid, record_id, model, fields, old_data, context)
                    val_log = {
                                'method': method,
                                'object_id': model_id,
                                'user_id': user_id,
                                'res_id': record_id,
                            }
                    log_id = log_pool.create(cr, uid, val_log)
                    for line in lines:
                        val_line = line.copy()
                        val_line['log_id'] = log_id
                        log_line_pool.create(cr, uid, val_line)
        
        return True
    
    def prepare_log_line_data(self, cr, uid, record_id, model, fields, old_data, context=None):
        res = []
        field_pool = self.pool.get('ir.model.fields')
        model_pool = self.pool.get('ir.model')
        if fields and record_id:
            record = self.read(cr, uid, record_id, fields)
            for field_name in fields:
                field_obj = self._all_columns.get(field_name)
                if not field_obj:
                    continue
                
                field_obj = field_obj.column
                search_models = [model.id]
                if self._inherits:
                    search_models += model_pool.search(cr, uid, [('model', 'in', self._inherits.keys())])
                field_id = field_pool.search(cr, uid, [('name', '=', field_name), ('model_id', 'in', search_models)])
                
                old_value = old_data.get(field_name,'')
                new_value = record.get(field_name, '')
                old_value_text = old_value
                new_value_text = new_value
                if field_obj._type == 'many2one':
                    old_value_text = old_value and old_value[1] or old_value
                    new_value_text = new_value and new_value[1] or new_value
                    
                    old_value = old_value and old_value[0] or old_value
                    new_value = new_value and new_value[0] or new_value
                elif field_obj._type == 'boolean':
                    old_value_text = str(old_value)
                    new_value_text = str(new_value)
                
                elif field_obj._type == 'many2many':
                    old_value_text = self.parse_many2many_value_to_char(cr, uid, field_obj._obj, old_value_text)
                    
                    new_value_text = self.parse_many2many_value_to_char(cr, uid, field_obj._obj, new_value_text)
                    
                if old_value == new_value or (not old_value and not new_value):
                    continue
                
                line = {  "field_id": field_id and field_id[0] or False,
                           "old_value": old_value,
                           "new_value": new_value,
                          "old_value_text": old_value_text,
                          "new_value_text": new_value_text,
                          "field_description": field_obj.string
                      }
                res.append(line)
        
        return res
    
    def parse_many2many_value_to_char(self, cr, uid, model, ids, context=None):
        res = ids
        if model and ids:
            if ids and isinstance(ids, list):
                pool = self.pool.get(model)
                datas = pool.name_get(cr, uid, ids)
                res = []
                for data in datas:
                    res.append(data[1])
                
                res = '-'.join(res)
        
        return res
    
    
    def prevent_normal_emp_read_data_of_other_emp(self, cr, user, ids, groups, allow_fields =[], read_fields=[], context=None):
        """
        @param user: User_id of employee
        @param ids: Records want to read in object 
        @param groups: Groups that user belong to
        @param allow_fields: Fields allow to read
        @param read_fields: Fields want to read
        @summary: : Prevent normal user read data of other employees in object
        """
        vhr_human_resource_group_hr = self.pool.get('ir.config_parameter').get_param(cr, user, 'vhr_human_resource_group_hr') or ''
        vhr_human_resource_group_hr = vhr_human_resource_group_hr.split(',')
        
        if not groups:
            groups = self.pool.get('res.users').get_groups(cr, user)
        
        if not isinstance(ids, list):
            ids = [ids]
        
        if not allow_fields:
            allow_fields = []
        
        if not read_fields:
            read_fields = []
        
        if vhr_human_resource_group_hr and not set(groups).intersection(vhr_human_resource_group_hr):
            emp_login_ids = self.pool.get('hr.employee').search(cr, user, [('user_id','=',user)])
            
            wr_ids = self.search(cr, user, [('employee_id','in',emp_login_ids)])
            if set(ids).difference(wr_ids):
                #If all field read_fields appear in allow_fields, allow to read
                if allow_fields and not set(read_fields).difference(allow_fields):
                    return True
                raise osv.except_osv('Validation Error !', 'You don’t have permission to access this data !')
        
        return True

    # get Action ID by XML ID
    def get_action_id(self, cr, uid, res_id, module='', xml_id='', context=None):
        if xml_id:
            data_obj = self.pool.get('ir.model.data')
            data_id = data_obj._get_id(cr, SUPERUSER_ID, module, xml_id)
            if data_id:
                act_id = data_obj.browse(cr, uid, data_id, context).res_id
                return act_id
        return False
            

vhr_common()