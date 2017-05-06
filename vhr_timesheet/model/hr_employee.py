# -*- coding: utf-8 -*-
import time

from openerp.osv import osv
from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT


class hr_employee(osv.osv):
    _inherit = 'hr.employee'

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if not context:
            context = {}
        
        parameter_obj = self.pool.get('ir.config_parameter')
        if context.get('timesheet_detail', False):
            context['search_all_employee'] = True
            groups = self.pool.get('res.users').get_groups(cr, uid)
            special_groups = ['vhr_cb_timesheet']
            
            official_emp_ids = []
            is_filter_official_emp = False
            if context.get('filter_with_outing_leave', False):
                outing_code = parameter_obj.get_param(cr, uid, 'ts_leave_type_outing_teambuilding').split(',')
                outing_leave_ids = self.pool.get('hr.holidays.status').search(cr, uid, [('code','in',outing_code)])
                if outing_leave_ids and context['filter_with_outing_leave'] in outing_leave_ids:
                    is_filter_official_emp = True
                    official_emp_ids = self.pool.get('hr.employee').search(cr, uid, [('job_level_person_id','!=',False),
                                                                                     ('active','=',True)])
            if not set(special_groups).intersection(set(groups)):
                sql = """
                        SELECT
                          DISTINCT
                          ET.employee_id
                        FROM hr_employee HE
                          INNER JOIN resource_resource RR ON RR.id = HE.resource_id
                          INNER JOIN res_users UU ON UU.id = RR.user_id
                          INNER JOIN vhr_ts_timesheet_detail TD  ON HE.id = TD.admin_id
                          INNER JOIN vhr_ts_emp_timesheet ET ON TD.timesheet_id = ET.timesheet_id
                          INNER JOIN hr_employee HH ON ET.employee_id = HH.id
                          INNER JOIN resource_resource RU ON RU.id = HH.resource_id AND RU.active
                        WHERE UU.id = {0}
                              AND current_date BETWEEN TD.from_date AND TD.to_date
                              AND ET.active=True
                              AND ET.effect_from <= TD.to_date
                              AND (ET.effect_to IS NULL OR ET.effect_to >= TD.from_date);
                """.format(uid)
                cr.execute(sql)
                employee_ids = [res_id[0] for res_id in cr.fetchall()]
                
                if is_filter_official_emp:
                    employee_ids = list(set(employee_ids).intersection(official_emp_ids))
                    
                args.append(('id', 'in', employee_ids))
            
            elif is_filter_official_emp:
                args.append(('id', 'in', official_emp_ids))
                
        elif context.get('employee_timesheet', False):
           
            context['search_all_employee'] = True
            timesheet_detail_pool = self.pool.get('vhr.ts.timesheet.detail')
            groups = self.pool.get('res.users').get_groups(cr, uid)
            special_groups = ['vhr_cb_timesheet']
          
            if not context.get('context_month',False) or not context.get('context_year',False):
                args.append(('id', 'in', []))
            else:
                
                employee_ids = []
                admin_id = False
                timesheet_ids = []
                if context.get('admin_id', False):
                    admin_id = context['admin_id']
                else:
                    employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=',uid)])
                    admin_id = employee_ids and employee_ids[0] or False
                
                #Nếu có timesheet trong context, thì filter theo timesheet
                if context.get('timesheet', False) and context['timesheet'][0] and context['timesheet'][0][2]:
                    timesheet_ids = context['timesheet'][0][2] or []
                    if timesheet_ids:
                        employee_ids = self.get_employee_from_timesheet(cr, uid, timesheet_ids, context['context_month'], context['context_year'], context)
                       
                #nếu admin được truyền vào context, hoặc user ko thuộc special group, filter employee dựa vào admin_id
                elif context.get('admin_id', False) or not set(special_groups).intersection(set(groups)):
                    domain = [('admin_id','=',admin_id), ('month','=',context['context_month']), ('year','=',context['context_year'])]
                    detail_ids = timesheet_detail_pool.search(cr, uid, domain)
                    details = timesheet_detail_pool.read(cr, uid, detail_ids, ['timesheet_id'])
                    timesheet_ids = [detail.get('timesheet_id',False) and detail['timesheet_id'][0] for detail in details]
                    employee_ids = self.get_employee_from_timesheet(cr, uid, timesheet_ids, context['context_month'], context['context_year'], context)

                #Nếu ko có admin và timesheet trong context thì
                elif set(special_groups).intersection(set(groups)):
                    domain = [('month','=',context['context_month']), ('year','=',context['context_year'])]
                    detail_ids = timesheet_detail_pool.search(cr, uid, domain)
                    details = timesheet_detail_pool.read(cr, uid, detail_ids, ['timesheet_id'])
                    timesheet_ids = [detail.get('timesheet_id',False) and detail['timesheet_id'][0] for detail in details]
                    employee_ids = self.get_employee_from_timesheet(cr, uid, timesheet_ids, context['context_month'], context['context_year'], context)
                
                args.append(('id', 'in', employee_ids))
                context.update({'active_test': False})  
        
        elif context.get('get_employee_for_ws_permission', False):
            #Get dept admin of current period, and cb_admin
            today = time.strftime(DEFAULT_SERVER_DATE_FORMAT)
            ts_detail_ids = self.pool.get('vhr.ts.timesheet.detail').search(cr, uid, [('from_date','<=',today),
                                                                                      ('to_date','>=',today)])
            if ts_detail_ids:
                ts_details = self.pool.get('vhr.ts.timesheet.detail').read(cr, uid, ts_detail_ids, ['admin_id'])
                admin_ids = [detail.get('admin_id',False) and detail['admin_id'][0] for detail in ts_details]
                cb_admin_ids = self.get_employee_ids_belong_to_group(cr, uid, 'vhr_cb_admin', context)
                employee_ids = admin_ids + cb_admin_ids
                args.append(('id', 'in', employee_ids))
        
        elif context.get('department_ids_for_compen_ot_payment', False):
            department_ids = context['department_ids_for_compen_ot_payment']
            
            try:
                department_ids = department_ids and department_ids[0] and department_ids[0][2]
            except Exception as e:
                pass
            
            department_ids.append(0)
            #chỉ tính có những nhân viên có cấp bậc dưới specialist
#             job_level_obj = self.pool.get('vhr.job.level')
#             job_level_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_timesheet_job_level_start_is_compensation_leave') or ''
#             job_level_code = job_level_code.split(',')
#             job_level_ids = job_level_obj.search(cr, uid, [('code', 'in', job_level_code)],context=context)
#             if job_level_ids:
#                 job_level = job_level_obj.read(cr, uid, job_level_ids[0], ['level'])
#                 ground_level = job_level.get('level',0)
                 
            sql = """
                    SELECT employee.id FROM hr_employee employee WHERE employee.department_id in %s 
                  """
            cr.execute(sql % str(tuple(department_ids)).replace(',)', ')')) 
             
            res = cr.fetchall()
            employee_ids = [item[0] for item in res]
            
            ot_leave_type_code = parameter_obj.get_param(cr, uid, 'ts.leave.type.overtime.code') or ''
            ot_leave_type_code = ot_leave_type_code.split(',')
            ot_leave_type_ids = self.pool.get('hr.holidays.status').search(cr, uid, [('code','in',ot_leave_type_code)])
            
            sql = """
                    select employee_id from hr_holidays 
                    WHERE type='add' and state='validate' 
                                     and holiday_status_id in %s
                                     and year = %s
                                     and employee_id in %s
                  """
            
            today = datetime.now()
            cr.execute(sql% (str(tuple(ot_leave_type_ids)).replace(',)', ')'), today.year,
                             str(tuple(employee_ids)).replace(',)', ')'),))
            res = cr.fetchall()
            employee_ids = [item[0] for item in res]
            args.append(('id', 'in', employee_ids))
                
        elif context.get('department_ids_for_lock_ts_detail', False):
            department_ids = context['department_ids_for_lock_ts_detail']
            department_ids = department_ids and department_ids[0] and department_ids[0][2]
            if department_ids:
                args.append(('department_id','in',department_ids))
            
                
        if context.get('admin_timesheet', False):
            context['search_all_employee'] = True
            if ('context_month' in context and not context.get('context_month',False)) \
            or ('context_year' in context and not context.get('context_year',False)):
                args.append(('id', 'in', []))
            else:
                month = context.get('context_month', False)
                year = context.get('context_year', False)
                domain = [('admin_id', '!=', False)]
                if month:
                    domain.append(('month', '=', month))
                if year:
                    domain.append(('year', '=', year))
                timesheet_detail_obj = self.pool.get('vhr.ts.timesheet.detail')
                timesheet_detail_ids = timesheet_detail_obj.search(cr, uid, domain)
                admin_ids = []
                if timesheet_detail_ids:
                    admin_data = timesheet_detail_obj.read(cr, uid, timesheet_detail_ids, ['admin_id'])
                    admin_ids = filter(None, map(lambda x: x.get('admin_id') and x['admin_id'][0], admin_data))
                args.append(('id', 'in', list(set(admin_ids))))
                
        res = super(hr_employee, self).search(cr, uid, args, offset, limit, order, context, count)
        return res
    
     #Return list employee_ids belong groups
    def get_employee_ids_belong_to_group(self, cr, uid, group_xml_id, context={}):
        if not context:
            context= {}
        
        employee_ids = []
        if group_xml_id:
            model_data = self.pool.get('ir.model.data')
            model_ids = model_data.search(cr, uid, [('model','=','res.groups'),('name','=',group_xml_id)])
            if model_ids:
                model = model_data.read(cr, uid, model_ids[0], ['res_id'])
                group_id = model.get('res_id', False)
                if group_id:
                    #Get user_id belong to group
                    sql = """
                            SELECT uid FROM res_groups_users_rel WHERE gid = %s
                          """
                    
                    cr.execute(sql%group_id)
                    user_ids = [group[0] for group in cr.fetchall()]
                    
                    #Get list employee_id belong to users
                    context = {"search_all_employee": True}
                    employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','in',user_ids)],0,None,None, context)
        return employee_ids
    
    def get_employee_from_timesheet(self, cr, uid, timesheet_ids, month, year, context=None):
        #Trả về danh sách nhân viên còn làm việc trong tháng, năm month/year của timesheet period
        #Khong tra ve employee dang thuoc working group CTV - theo phiếu đánh giá
        sql = """
               SELECT distinct emp_timesheet.employee_id 

                FROM vhr_ts_emp_timesheet emp_timesheet 
                            INNER JOIN vhr_ts_timesheet_detail ts_detail  ON emp_timesheet.timesheet_id = ts_detail.timesheet_id
                            INNER JOIN vhr_employee_instance   instance   ON instance.employee_id = emp_timesheet.employee_id
                WHERE      
                    emp_timesheet.effect_from <= ts_detail.to_date 
                      AND (emp_timesheet.effect_to IS NULL OR emp_timesheet.effect_to >= ts_detail.from_date)
                      AND ts_detail.month = %s
                      AND ts_detail.year = %s
                      AND (instance.date_end IS NULL OR instance.date_end >= ts_detail.from_date)
        """ % (month, year)
        timesheet_ids.append(0)
        if timesheet_ids:
            sql += ' AND emp_timesheet.timesheet_id in %s' % str(tuple(timesheet_ids)).replace(',)', ')')
        timesheet_ids.remove(0)
        
        cr.execute(sql)
        res = cr.fetchall()
        res = [item[0] for item in res]
        
        if res:
            #Khong tra ve employee dang thuoc working group CTV - theo phiếu đánh giá trong ca ky timesheet do
            detail_obj = self.pool.get('vhr.ts.timesheet.detail')
            working_obj = self.pool.get('vhr.working.record')
            ts_detail_ids = detail_obj.search(cr, uid, [('month','=',month),
                                                        ('year','=',year)], limit=1)
            
            if ts_detail_ids:
                working_group_ctv_pdg_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'working_group_ctv_pdg_code') or ''
                working_group_ctv_pdg_code = working_group_ctv_pdg_code.split(',')
                working_group_ids = self.pool.get('vhr.ts.working.group').search(cr, uid, [('code','in',working_group_ctv_pdg_code)])
                if working_group_ids:
                    #Get list employee from working record active during timesheet period have working group CTV - phieu danh gia
                    #TODO: only check working record of main contract.
                    ts_detail = detail_obj.read(cr, uid, ts_detail_ids[0], ['from_date','to_date'])
                    wr_ids = working_obj.search(cr, uid, [('employee_id','in', res),
                                                             ('ts_working_group_id_new','in',working_group_ids),
                                                             ('state','in',[False,'finish']),
                                                             ('effect_from','<=',ts_detail.get('from_date', False)),
                                                             '|',('effect_to','>=',ts_detail.get('to_date', False)),
                                                                 ('effect_to','=',False) ])
                    if wr_ids:
                        wrs = working_obj.read(cr, uid, wr_ids, ['employee_id'])
                        employee_ids = [wr.get('employee_id',False) and wr['employee_id'][0] for wr in wrs]
                        res = list(set(res).difference(set(employee_ids)))
            
        return res
    
    def update_employee(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        
        mcontext=context.copy()
        res = super(hr_employee, self).update_employee(cr, uid, ids, context)
        
        if res and mcontext.get('wr_join_company_ids', False):
            try:
                self.pool.get('vhr.working.record').check_to_create_update_annual_leave(cr, uid, mcontext.get('wr_join_company_ids',[]))
            except Exception as e:
                print " error when check_to create_update_annual_leave after update employee from wr join company"
        
        return res
            


hr_employee()