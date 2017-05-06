# -*-coding:utf-8-*-
import logging
import time
import thread, threading
import sys

from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp.osv import osv, fields
from openerp.sql_db import Cursor
from openerp.sql_db import ConnectionPool
from openerp import tools
from openerp import SUPERUSER_ID
from openerp.addons.vhr_common.model.vhr_common import vhr_common

log = logging.getLogger(__name__)

# max_connections = 60
# semaphore = threading.BoundedSemaphore(max_connections)

class hr_department(osv.osv, vhr_common):
    _inherit = 'hr.department'
    
    def _get_false_value(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if not isinstance(ids, list):
            ids = [ids]
        
        for record_id in ids:
            res[record_id] = False
        return res
    
    def _dept_code_get_fnc(self, cr, uid, ids, prop, unknow_none, context=None):
        res = self.code_get(cr, uid, ids, context=context)
        return dict(res)
    
    _columns = {
                'is_change_parent_id': fields.function(_get_false_value, type='date', string='Is Change Parent Id'),
                'is_change_data_to_create_history': fields.function(_get_false_value, type='date', string='Is Change Data To Create History'),
                'new_wr_effect_from': fields.function(_get_false_value, type='date', string='New Effective Date'),
                'old_id_before_change_parent': fields.integer( string='Old Id Before Change Parent'),
                'is_create_new_wr': fields.function(_get_false_value, type='selection', selection=[('yes', 'Yes'), ('no', 'No')], string='Is Create WR'),

                'history_ids': fields.one2many('vhr.department.history', 'department_id', 'History', audittrail_log=False),
                'complete_code': fields.function(_dept_code_get_fnc, type="char", string='Full Code'),
                }
    
    _defaults = {
                 'is_change_parent_id': False,
                 'is_change_data_to_create_history': False
                 }
    
    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if not ids:
            return []
        
        if context.get('get_department_name_by_code', False):
            res = []
            if set(['dept_effect_from_in_history','dept_effect_from_in_history']).intersection(context.keys()):
                for record_id in ids:
                    res.append(record_id, self.get_history_code_of_department(cr, uid, record_id, context))
            else:
                for record in self.read(cr, uid, ids, ['code']):
                    res.append(  (record['id'], record.get('code', False)) )
            
            return res
        
        if not context.get('get_pure_department_name', False):
            res = self.code_get(cr, uid, ids, context=context)
        else:
            res = super(hr_department, self).name_get(cr, uid, ids, context)
        return res
    
    def code_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if not ids:
            return []

#         reads = self.read(cr, uid, ids, ['code', 'parent_id'], context=context)
        res = []
        for record_id in ids:
            code = self.get_dept_code(cr, uid, record_id, context)
            res.append((record_id, code))

        return res

    def get_dept_code(self, cr, uid, dept_id, context=None):
        if not context:
            context = {}
            
        full_dept_code = ''
        dept_obj = self.read(cr, uid, dept_id, ['code','parent_id','parent_left','parent_right','history_ids'])
        if dept_obj:
            parent_left = dept_obj.get('parent_left','')
            parent_right = dept_obj.get('parent_right','')
            history_ids = dept_obj.get('history_ids', [])
            
            dept_code = dept_obj.get('code','')
            
            full_dept_code = dept_code
            if history_ids and (context.get('dept_effect_from_in_history', False) or context.get('dept_effect_from_in_history_by_one_day', False)):
                code_history = self.get_code_by_history(cr, uid, history_ids, context)
                if code_history:
                    full_dept_code = code_history
            
            parent_dept_code = ''
            if dept_obj.get('parent_id',False):
                parent_dept_code = self.get_parent_dept_code(cr, uid, parent_left, parent_right, context)
                full_dept_code = parent_dept_code + ' / ' + full_dept_code
            
        return full_dept_code
    
    def get_parent_dept_code(self, cr, uid, parent_left, parent_right, context=None):
        if not context:
            context = {}
            
        res = ''
        if parent_left and parent_right:
            sql = """
                    SELECT code,id FROM hr_department WHERE parent_left < %s and parent_right > %s ORDER BY parent_left asc
                  """
            cr.execute(sql%(parent_left,parent_right))
            results = cr.fetchall()
            code_list = [res_id[0] for res_id in results]
            id_list = [res_id[1] for res_id in results]
            
            if set(['dept_effect_from_in_history','dept_effect_from_in_history_by_one_day']).intersection(context.keys()):
                index = 0
                for code, record_id in results:
                    code = self.get_history_code_of_department(cr, uid, record_id, context)
                    if code:
                        code_list[index] = code
                    index += 1
                
            res = ' / '.join(code_list)
            
        return res
    
    
    def get_history_code_of_department(self, cr, uid, department_id, context=None):
        code = ''
        if department_id:
            department = self.read(cr, uid, department_id, ['history_ids','code'])
            history_ids = department.get('history_ids', [])
            code = self.get_code_by_history(cr, uid, history_ids, context)
            if not code:
                return department.get('code','')
        
        return code
            
    
    def get_code_by_history(self, cr, uid, history_ids, context=None):
        if not context:
            context = {}
        
        res = ''
        effective_date = context.get('dept_effect_from_in_history', False)
        if context.get('dept_effect_from_in_history_by_one_day', False):
            effective_date = context['dept_effect_from_in_history_by_one_day']
            effective_date = datetime.strptime(effective_date, DEFAULT_SERVER_DATE_FORMAT) - relativedelta(days=1)
            effective_date = effective_date.strftime(DEFAULT_SERVER_DATE_FORMAT)
            
        if effective_date:
            history_obj = self.pool.get("vhr.department.history")
            history_ids = history_obj.search(cr, uid, [('id','in',history_ids),
                                                       ('effect_from','<=',effective_date),
                                                       '|',('effect_to','>=',effective_date),
                                                            ('effect_to','=',False)])
            if history_ids:
                history = history_obj.read(cr, uid, history_ids[0], ['code'])
                res = history.get('code','')
        
        return res
    
    
    def onchange_parent_id(self, cr, uid, ids, parent_id, context=None):
        res = {}
        if ids:
            if not isinstance(ids, list):
                ids = [ids]
            
            record = self.read(cr, uid, ids[0], ['parent_id'])
            old_parent_id = record.get('parent_id', False) and record['parent_id'][0]
            if old_parent_id != parent_id:
                res['is_change_parent_id'] = True
        
        return {'value': res}
    
    def onchange_data(self, cr, uid, ids, context=None):
        return {'value': {'is_change_data_to_create_history': True}}
    
    def onchange_name(self, cr, uid, ids, name, context=None):
        return self.onchange_data(cr, uid, ids, context=None)
    
    def onchange_name_en(self, cr, uid, ids, name, context=None):
        return self.onchange_data(cr, uid, ids, context=None)
    
    def onchange_code(self, cr, uid, ids, name, context=None):
        return self.onchange_data(cr, uid, ids, context=None)
    
    def onchange_organization_class_id(self, cr, uid, ids, organization_class_id, context=None):
        res = super(hr_department, self).onchange_organization_class(cr, uid, ids, organization_class_id, context)
        res_update= self.onchange_data(cr, uid, ids, context=None)
        res.update(res_update)
        return res
    
    def onchange_manager_id(self, cr, uid, ids, manager_id, context=None):
        return self.onchange_data(cr, uid, ids, context=None)
    
    def onchange_company_id(self, cr, uid, ids, company_id, context=None):
        return {'value': {}}
#         return self.onchange_data(cr, uid, ids, context=None)
    
    
    
    
    def read(self, cr, user, ids, fields=None, context=None, load='_classic_read'):
        if not context:
            context = {}
            
        if context.get('validate_read_hr_department',False):
            log.info('\n\n validate read_hr_department')
            
            is_stop_validate = self.pool.get('ir.config_parameter').get_param(cr, user, 'vhr_human_resource_stop_validate_read_hr_department') or ''
            if not is_stop_validate:
                if not context.get('default_hierachical_code', False):
                    context['default_hierachical_code'] = 'ORGCHART'
                result_check = self.validate_read(cr, user, ids, context)
                if not result_check:
                    raise osv.except_osv('Validation Error !', 'You don’t have permission to access this data !')
                
                del context['validate_read_hr_department']
        
        res =  super(hr_department, self).read(cr, user, ids, fields, context, load)
            
        return res
    
    def validate_read(self, cr, uid, ids, context=None):
        user_groups = self.pool.get('res.users').get_groups(cr, uid)
        if set(['hrs_group_system', 'vhr_cnb_manager', 'vhr_hr_dept_head']).intersection(set(user_groups)):
            return True
        if isinstance(ids, (int, long)) or (isinstance(ids, list) and len(ids)) == 1:
            check_id = ids
            if isinstance(ids, list):
                check_id = ids[0]
            new_context = context and context.copy() or {}
            lst_check = self.search(cr, uid, ["|",('active','=', True),('active','=', False)], context=new_context)
            if check_id not in lst_check:
                return False
        return True
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        
        args = self.get_search_argument(cr, uid, args, context)
        
        res = super(hr_department, self).search(cr, uid, args, offset, limit, order, context, count)
        return res
    
    def get_search_argument(self, cr, uid, args, context=None):
        if not context:
            context = {}
        
        employee_pool = self.pool.get('hr.employee')
        organization_class_pool = self.pool['vhr.organization.class']
        
        if context.get('organization_class_level', False):
            org_class_ids = organization_class_pool.search(cr, uid, [('level','=',context['organization_class_level'])])
            if org_class_ids:
                args.append(('organization_class_id','in',org_class_ids))

        if context.get('organization_class_code', False):
            org_class_ids = organization_class_pool.search(cr, uid, [('code', '=', context['organization_class_code'])])
            if org_class_ids:
                args.append(('organization_class_id', 'in', org_class_ids))
        
        #Mặc định nếu ko có context['defaul_hierachical_code'] thì luôn luôn lấy các department từ ORGCHART
        if not context.get('default_hierachical_code',False):
            context['default_hierachical_code'] = 'ORGCHART'
        
        if context.get('default_hierachical_code', False):
            dimension_type_ids = self.pool.get('vhr.dimension.type').search(cr, uid, [('code','=','HIERARCHICAL_CHART')])
            if dimension_type_ids:
                hierachical_ids = self.pool.get('vhr.dimension').search(cr, uid, [('code','=',context['default_hierachical_code']),
                                                                ('dimension_type_id','=',dimension_type_ids[0])])
                
                args.append(('hierarchical_id','in',hierachical_ids))
        
        if context.get('default_hierachical_code', False) == 'FAORGCHART':
            login_employee_ids = employee_pool.search(cr, uid, [('user_id','=',uid)], 0, None, None, context)
            res = self.get_domain_fa_based_on_permission_location(cr, uid, login_employee_ids, context)
            if res:
                args.extend(res)
        
        return args
    
    def get_domain_fa_based_on_permission_location(self, cr, uid, employee_ids, context=None):
        """
        return domain to search department FA based on permission location
        """
        domain = []
        if employee_ids:
            if not isinstance(employee_ids, list):
                employee_ids = [employee_ids]
            permission_obj = self.pool.get('vhr.permission.location')
            record_ids = permission_obj.search(cr, uid, [('employee_id','in',employee_ids)])
            if record_ids:
                record = permission_obj.read(cr, uid, record_ids[0], ['department_fa_ids'])
                department_fa_ids = record.get('department_fa_ids',[])
                
                if department_fa_ids:
                    domain.append(('id','in', department_fa_ids))
                        
        return domain
    

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        
        if not isinstance(ids, list):
            ids = [ids]
        
        disable_new_tree = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_human_resource_disable_create_new_department_tree') or ''
        
        new_parent_id = False
        if ids and vals.get('parent_id',False) and vals.get('new_wr_effect_from', False) and disable_new_tree in ['0','']:
            new_parent_id = vals['parent_id']
            del vals['parent_id']
#             vals['active'] = False
        
        #Save to history
        if vals.get('new_wr_effect_from', False) and not vals.get('parent_id', False):
            fields = ['name','name_en','code','organization_class_id','company_id','manager_id']
            record = self.read(cr, uid, ids[0], fields)
            val = {'department_id': ids[0],'effect_from': vals['new_wr_effect_from']}
            for field in fields:
                val[field] = vals.get(field, record.get(field))
                if isinstance(val[field], tuple):
                    val[field] = val[field][0]
            
            self.pool.get('vhr.department.history').create(cr, uid, val)
            
        res = super(hr_department, self).write(cr, uid, ids, vals, context)
        
        
        if res and ids and disable_new_tree in ['0','']:
            if new_parent_id:
                self.create_new_department_tree(cr, uid, ids, new_parent_id, context)
            context['new_wr_effect_from'] = vals.get('new_wr_effect_from', False)
            if vals.get('is_create_new_wr', False) == 'yes':
                if not new_parent_id:
                    context['create_wr_from_change_pure_data'] = True
                self.create_working_record_when_onchange_parent_id(cr, uid, ids, context)
        
        return res
    
    def create_new_department_tree(self, cr, uid, ids, new_parent_id, context=None):
        """
        When onchange parent department:
           - Create a group departments copy from edit department and all it's child departments
           - Inactive edit department and all it's child departments
        """
        if not isinstance(ids, list):
            ids = [ids]
        
        if ids:
            data = self.copy_data(cr, uid, ids[0], default = {'audit_log_ids':[],'old_id_before_change_parent':0,'child_ids': [],'jobs_ids': []})
            
            data['audit_log_ids'] = []
            data['old_id_before_change_parent'] = ids[0]
            if new_parent_id:
                data['parent_id'] = new_parent_id
            
            
            new_dept_id = self.create(cr, uid, data, context)
            if new_dept_id:
                child_ids = self.search(cr, uid, [('parent_id','=',ids[0]),
                                                  ('active','=',True)])
                if child_ids:
                    for child_id in child_ids:
                        self.create_new_department_tree(cr, uid, [child_id], new_dept_id, context)
                        
        return True

    def create_working_record_when_onchange_parent_id(self, cr, uid, ids, context=None):
        """
        Only create WR luan chuyen phong ban for department HR
        """
        if not isinstance(ids, list):
            ids = [ids]
        
        record = self.read(cr, uid, ids[0], ['hierarchical_id'])
        hierarchical_id = record.get('hierarchical_id', False) and record['hierarchical_id'][0] or False
        if hierarchical_id:
            hierarchical = self.pool.get('vhr.dimension').read(cr, uid, hierarchical_id, ['code'])
            if hierarchical and hierarchical.get('code', False) == 'ORGCHART':
                thread.start_new_thread(hr_department.thread_execute, (self,cr, uid, ids[0],context) )
        
        return True
    
    def get_list_employee_on_team_department_at_date(self, cr, uid, department_id, team_id, date, context=None):
        """
        Return list (employee_id-company) at department/team at date
        """
        unique_list = []
        if (department_id or team_id) and date:
            working_pool = self.pool.get('vhr.working.record')
            
            dismiss_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_master_data_dismiss_change_form_code') or ''
            dismiss_code_list = dismiss_code.split(',')
            dismiss_change_form_ids = self.pool.get('vhr.change.form').search(cr, uid, [('code','in',dismiss_code_list)])
            
            domain = [('state','in',['finish',False]),
                      ('effect_from','<=',date),
                      '|',('effect_to','=',False),('effect_to','>=',date),
                      '|',('active','=',True),('active','=',False)]
            
            #Dont get employee have Termination WR 
            for form_id in dismiss_change_form_ids:
                domain.append(('change_form_ids','!=',form_id))
            
            if department_id:
                domain.insert(0, ('department_id_new','=',department_id))
            
            if team_id:
                domain.insert(0, ('team_id_new','=',team_id))
            
            working_ids = working_pool.search(cr, uid, domain)
            if working_ids:
                records = working_pool.read(cr, uid, working_ids, ['employee_id','company_id'])
                unique_list = [(record.get('employee_id', False) and record['employee_id'][0], record.get('company_id',False) and record['company_id'][0]) for record in records]
        
        return list(set(unique_list))
    
    def create_mass_status(self, cr, uid, context=None):
        vals = { 'state' : 'new', 'type': 'record'}
        
        employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', uid)])
        if employee_ids:
            vals['requester_id'] = employee_ids[0]
            
        module_ids = self.pool.get('ir.module.module').search(cr, uid, [('name','=','vhr_human_resource')])
        if module_ids:
            vals['module_id'] = module_ids[0]
            
        model_ids = self.pool.get('ir.model').search(cr, uid, [('model','=','vhr.working.record')])
        if model_ids:
            vals['model_id'] = model_ids[0]
        
        mass_status_id = self.pool.get('vhr.mass.status').create(cr, uid, vals)
        return mass_status_id
    
    def get_parent_by_level(self, cr, uid, department_id, level, context=None):
        if department_id and level:
            department = self.browse(cr, uid, department_id, fields_process=['parent_id','organization_class_id'])
            dept_level = department.organization_class_id and department.organization_class_id.level or 0
            if level == dept_level:
                return department_id
            elif department.parent_id:
                return self.get_parent_by_level(cr, uid, department.parent_id.id, level, context)
            else:
                return False
            
        return False
    
    def thread_execute(self, cr, uid, record_id, context=None):
        if not context:
            context = {}
        log.info('Start execute create multi working record when onchange parent department in department')
        mass_status_pool = self.pool.get('vhr.mass.status')
        mass_status_detail_pool = self.pool.get('vhr.mass.status.detail')
        working_record_pool = self.pool.get('vhr.working.record')
        dept_pool = self.pool.get('hr.department')
#         semaphore.acquire()
        _pool = ConnectionPool(int(tools.config['db_maxconn']))
        #cr used to create WR
        m_cr = Cursor(_pool, cr.dbname, True)
        #t_cr used to create/write Mass Status/ Mass Status Detail
        t_cr = Cursor(_pool, cr.dbname, True) #Thread's cursor
        
        #clear old thread in cache to free memory
        reload(sys)
        cr.commit()
        mass_status_id = self.create_mass_status(t_cr, uid, context)
        t_cr.commit()
        error_employees = ""
        if record_id and mass_status_id:
            department_id = False
            team_id = False
            parent_id = False
            grand_parent_id = False
            
            department = self.browse(m_cr, uid, record_id, fields_process=['organization_class_id','code'])
            org_level = department.organization_class_id and department.organization_class_id.level or 0
            department_code = department.code or ''
            if org_level:
                if org_level == 3:
                    department_id = record_id
#                     parent_id = self.get_parent_by_level(m_cr, uid, record_id, 2, context)
                elif org_level >=4:
                    team_id = record_id
#                     parent_id = self.get_parent_by_level(m_cr, uid, record_id, 3, context)
#                     grand_parent_id = self.get_parent_by_level(m_cr, uid, record_id, 2, context)
                else:
                    m_cr.commit()
                    m_cr.close()
                    
                    t_cr.commit()
                    t_cr.close()
                    log.info('End execute create multi working record when onchange parent department in department')
#                     semaphore.release()
                    return True
            
            today = time.strftime(DEFAULT_SERVER_DATE_FORMAT)
            today = context.get('new_wr_effect_from', today)
#             from datetime import datetime
#             today_p = datetime.strptime(today, DEFAULT_SERVER_DATE_FORMAT).date()
#             from dateutil.relativedelta import relativedelta
#             today_p = today_p + relativedelta(days=19)
#             today = today_p.strftime(DEFAULT_SERVER_DATE_FORMAT)
            #Get list employee will create WR
            unique_list = self.get_list_employee_on_team_department_at_date(m_cr, uid, department_id, team_id, today, context)
            
            if unique_list:
                if context.get('create_wr_from_change_pure_data', False):
                    mass_status_info = 'Create multi working record when change data (name,code,etc) in department'
                else:
                    mass_status_info = 'Create multi working when change parent department in department %s (id = %s)'% (department_code, record_id)
                number_of_record = len(unique_list)
                mass_status_vals = {'state': 'running',
                                     'number_of_record': number_of_record, 
                                     'number_of_execute_record': 0,
                                     'number_of_fail_record': 0,
                                     'mass_status_info': mass_status_info
                                     }
                mass_status_pool.write(t_cr, uid, [mass_status_id], mass_status_vals)
#                 t_cr.commit()
                error_message = ""
                create_ids = []
                try:
                    working_record_columns = working_record_pool._columns
                    working_record_fields = working_record_columns.keys()
                    
                    
                    if context.get('create_wr_from_change_pure_data', False):
                        change_form_param = 'vhr_human_resource_change_form_change_department_name'
                    else:
                        change_form_param = 'vhr_human_resource_change_form_change_parent_department'
                    
                    promotion_code = self.pool.get('ir.config_parameter').get_param(m_cr, uid, change_form_param) or ''
                    promotion_code = promotion_code.split(',')
                    change_form_ids = self.pool.get('vhr.change.form').search(m_cr, uid, [('code','in',promotion_code)])
                        
                    list_error = []
                    num_count = 0
                    list_state_change = {}
                    for unique_item in unique_list:
                        employee_id = unique_item[0]
                        company_id = unique_item[1]
                        if employee_id and company_id:
                            error_item = False
                            try:
                                num_count += 1
                                mass_status_pool.write(t_cr, uid, [mass_status_id], {'number_of_execute_record': num_count})
                                t_cr.commit()
                                record_vals = working_record_pool.default_get(m_cr, SUPERUSER_ID, working_record_fields, context)
                                
                                #If employee had a Working Record on today, try to create new one on tomorrow
                                same_wr_ids = working_record_pool.search(m_cr, uid, [('employee_id','=',employee_id),
                                                                                     ('company_id','=',company_id),
                                                                                     ('effect_from','=',today),
                                                                                     ('state','!=','cancel')])
                                effect_from = today
                                if same_wr_ids:
                                    from datetime import datetime
                                    today_p = datetime.strptime(today, DEFAULT_SERVER_DATE_FORMAT).date()
                                    from dateutil.relativedelta import relativedelta
                                    today_p = today_p + relativedelta(days=1)
                                    effect_from = today_p.strftime(DEFAULT_SERVER_DATE_FORMAT)
                                    
                                record_vals.update({'employee_id': employee_id,
                                                    'company_id': company_id,
                                                    'effect_from': effect_from,
                                                    'change_form_ids': [[6,False,change_form_ids]]} )
                                #get data when onchange effect_from
                                context['create_from_outside'] = True
                                onchange_effect_from_data = working_record_pool.onchange_effect_from(m_cr, uid, [], today, employee_id, company_id, False, False, False, False, True, False, False, False, context)
                                #Raise error when can not find contract for employee on effect_from
                                if onchange_effect_from_data.get('warning', False):
                                    error_item = onchange_effect_from_data['warning']
                                    list_error.append( (employee_id, error_item) )
    
                                else:
                                    onchange_effect_from_value = onchange_effect_from_data['value']
                                    for field in onchange_effect_from_value.keys():
                                        if isinstance(onchange_effect_from_value[field], tuple):
                                            onchange_effect_from_value[field] = onchange_effect_from_value[field][0]
                                    
                                    record_vals.update( onchange_effect_from_value )
                                    
                                    if context.get('create_wr_from_change_pure_data', False):
                                        if record_vals.get('department_id_new', False):
                                            dept = dept_pool.read(m_cr, uid, record_vals['department_id_new'], ['manager_id'])
                                            record_vals['manager_id_new'] = dept.get('manager_id', False) and dept['manager_id'][0] or False
                                                
                                    else:
                                        if department_id:
                                            new_department_ids = self.search(m_cr, uid, [('old_id_before_change_parent','=',department_id)])
                                            if new_department_ids:
                                                record_vals['department_id_new'] = new_department_ids[0]
                                                
                                                dept = dept_pool.read(m_cr, uid, new_department_ids[0], ['manager_id'])
                                                record_vals['manager_id_new'] = dept.get('manager_id', False) and dept['manager_id'][0] or False
                                                
                                                #Find new division_id_new
                                                parent_id = self.get_parent_by_level(m_cr, uid, new_department_ids[0], 2, context)
                                                record_vals['division_id_new'] = parent_id
                                                
                                                #Find new team_id_new
                                                team_id_new = record_vals.get('team_id_new', False)
                                                if team_id_new:
                                                    new_team_ids = self.search(m_cr, uid, [('old_id_before_change_parent','=',team_id_new)])
                                                    if new_team_ids:
                                                        record_vals['team_id_new'] = new_team_ids[0]
                                                    else:
                                                        raise osv.except_osv('Warning !', "Can not find new id of team with id %s !"%team_id_new) 
                                            else:
                                                raise osv.except_osv('Warning !', "Can not find new id of department with id %s !"% department_id)
                                            
                                            
                                        elif team_id:
                                            onchange_department_data = working_record_pool.onchange_department_id_new(m_cr, uid, [], department_id, team_id, False, False, context)
                                            record_vals.update( onchange_department_data['value'] )
                                            
                                            new_team_ids = self.search(m_cr, uid, [('old_id_before_change_parent','=',team_id)])
                                            if new_team_ids:
                                                onchange_team_data = working_record_pool.onchange_team_id_new(m_cr, uid, [], new_team_ids[0], False, context)
                                                record_vals.update( onchange_team_data['value'] )
                                                record_vals['team_id_new'] = new_team_ids[0]
                                                
                                                parent_id = self.get_parent_by_level(m_cr, uid, new_team_ids[0], 3, context)
                                                grand_parent_id = self.get_parent_by_level(m_cr, uid, new_team_ids[0], 2, context)
                                                record_vals['department_id_new'] = parent_id
                                                record_vals['division_id_new'] = grand_parent_id
                                            
                                            else:
                                                raise osv.except_osv('Warning !', "Can not find new id of team with id %s !"% team_id)
                                            
                                        
#                                     record_vals.update(data )
#                                     del record_vals['name']
                                    m_cr.commit()
                                    mcontext= {'do_not_check_change_data': True}
                                    res = working_record_pool.create_with_log(m_cr, uid, record_vals, mcontext)
                                    if res:
                                        create_ids.append(res)
                                        mass_status_detail_pool.create(m_cr, uid, {'mass_status_id': mass_status_id,
                                                                                'employee_id': employee_id,
                                                                                'status': 'success'})

                                        m_cr.commit()
                                        
                            except Exception as e:
                                log.exception(e)
                                try:
                                    error_item = e.message
                                    if not error_item:
                                        error_item = e.value
                                except:
                                    error_item = ""
                                    
                                list_error.append( (employee_id, error_item) )
                            #If have error during the task with employee_id, then roll back to revert action create new working record
                            if error_item:
                                mass_status_pool.write(t_cr, uid, [mass_status_id], {'number_of_fail_record': len(list_error)})
                                mass_status_detail_pool.create(t_cr, uid, {'mass_status_id': mass_status_id,
                                                                           'employee_id' : list_error[-1][0],
                                                                           'message':list_error[-1][1]})
                                t_cr.commit()
                                m_cr.rollback()
                            else:
                                #if dont have error with employee_id, then commit to action with next employee_id wont affect to new WR of current employee_id
                                m_cr.commit()
                                t_cr.commit()
#                                
#                                 t_cr.commit()
                    if list_error:
                        mass_status_pool.write(t_cr, uid, [mass_status_id], {'state': 'error','number_of_fail_record': len(list_error)})
                            
                    else:
                        mass_status_pool.write(t_cr, uid, [mass_status_id], {'state': 'finish'})
                
                except Exception as e:
                    log.exception(e)
                    try:
                        error_message = e.message
                        if not error_message:
                            error_message = e.value
                    except:
                        error_message = ""
                        
                    #If have error with first try, then rollback to clear all created WR
                    m_cr.rollback()
                    self.pool.get('vhr.working.record').roll_back_working_record(m_cr, uid, create_ids, context)
                    log.info('Error occur while create multi working record when onchange parent department in department')
                
                if error_message:
                    #Use mcr in here because InternalError if use t_cr
                    mass_status_pool.write(m_cr, uid, [mass_status_id], {'state': 'fail','error_message': error_message})
                else:
                    #Inactive department and all it's child 
                    try:
                        t_cr.commit()
                        super(hr_department, self).write(t_cr, uid, record_id, {'active': False}, context)
                    except Exception as e:
                        log.exception(e)
                        try:
                            error_message = e.message
                            if not error_message:
                                error_message = e.value
                        except:
                            error_message = ""
                        
                        m_cr.commit()
                        mass_status_pool.write(m_cr, uid, [mass_status_id], {'state': 'fail','error_message': error_message})
                
                m_cr.commit()
                m_cr.close()
                
                t_cr.commit()
                t_cr.close()
                log.info('End execute create multi working record when onchange parent department in department')
#                 semaphore.release()
                return True
        
        m_cr.commit()
        m_cr.close()
        
        t_cr.commit()
        t_cr.close()
        log.info('End execute create multi working record when onchange parent department in department')
#         semaphore.release()
        return True

    def get_all_department(self, cr, uid, company_code, context=None):
        if context is None:
            context = {}
        res = []
        dept_ids = self.search(cr, uid, [('company_id.code', '=', company_code), ('active', '=', True)], context=context)
        if dept_ids:
            for item in self.browse(cr, uid, dept_ids, context=context):
                res.append((str(item.id), item.complete_code))
        return res
    
    def reset_parent_left_parent_right_hr_department(self, cr, uid, context=None):
        log.info('======= START MIGRATE reset_parent_left_parent_right_hr_department ========')
        if not context:
            context = {}
            
        length = 15
        if context.get('len',0):
            length = context['len']
        
        code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_human_resource_delete_all_parent_left_right') or ''
        if code == '1':
            cr.execute('update hr_department set parent_left=0,parent_right=0')
        
        
        cr.execute("select id from hr_department where parent_id is null and parent_left=0")
        results = cr.fetchall()
        root_dept_ids = [res_id[0] for res_id in results]
        
        
        if context.get('department_code', False):
            sql = "select id from hr_department where parent_id is null and code='%s'" % context['department_code']
            cr.execute(sql)
            results = cr.fetchall()
            root_dept_ids = [res_id[0] for res_id in results]
        
        log.info('root_dept_ids='+str(root_dept_ids))
        if root_dept_ids:
            cr.execute('select parent_right from hr_department order by parent_right desc limit 1')
            results = cr.fetchall()
            res = [res_id[0] for res_id in results]
            parent_left = res[0] + 1
            
            print 'parent_left=',parent_left
            
            root_dept_ids = root_dept_ids[:length]
            
            log.info('root_dept_ids='+str(root_dept_ids))
            for record_id in root_dept_ids:
                all_child_ids = self.get_all_child_department(cr, uid, [record_id])
#                 print 'all_child_ids=',all_child_ids
                count_all = len(all_child_ids)-1
                print 'count_all=',count_all,';;record_id=',record_id
                
                parent_right = parent_left + 1 + (count_all *2 ) 
                cr.execute('update '+self._table+' set parent_left=%s, parent_right=%s where id=%s'% (parent_left, parent_right, record_id))
                
                self.reupdate_parent_left_parent_right_hr_department(cr, uid, record_id, parent_left, parent_right, is_root=True)
                
                parent_left = parent_right + 1
        
        log.info('======= END MIGRATE reset_parent_left_parent_right_hr_department ========')
        
    def reupdate_parent_left_parent_right_hr_department(self, cr, uid, record_id, input_parent_left, input_parent_right, is_root=False):
        
        parent_left = input_parent_left
        parent_right = input_parent_right
        department_obj = self.pool.get('hr.department')
        
        cr.execute('select id from hr_department where parent_id=%s' %record_id)
        results = cr.fetchall()
        child_ids = [res_id[0] for res_id in results]
        
        if not is_root:
            cr.execute('update '+self._table+' set parent_left=%s, parent_right=%s where id=%s'%(parent_left, parent_right,record_id))
        
        position = parent_left +1
        for child_id in child_ids:
#             cr.execute('update '+self._table+' set parent_left=parent_left+%s where parent_left>=%s'% (2, position))
#             cr.execute('update '+self._table+' set parent_right=parent_right+%s where parent_right>=%s'% (2, position))
            
            grand_ids = self.get_all_child_department(cr, uid, [child_id])
        
            count_all = len(grand_ids) - 1
            distance = (count_all * 2)
            self.reupdate_parent_left_parent_right_hr_department(cr, uid, child_id, position, position +distance+1, False)
            
            position = position + distance + 2
        
        return True
    
    def get_all_child_department(self, cr, uid, department_ids, context=None):
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
                                WHERE g.parent_id = sg.id
                        )
                        SELECT id FROM department;
                      """
                
                cr.execute(sql % department_id)
                results = cr.fetchall()
                res.extend( [res_id[0] for res_id in results] )
        
        return res

hr_department()