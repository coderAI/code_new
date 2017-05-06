# -*-coding:utf-8-*-
import logging
import datetime

from openerp.osv import osv, fields
import simplejson as json
from openerp import SUPERUSER_ID
from lxml import etree
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.addons.vhr_common.model.vhr_common import vhr_common

log = logging.getLogger(__name__)


class hr_employee(osv.osv, vhr_common):
    _inherit = 'hr.employee'
    _description = 'HR Employee'
    
    def _is_able_to_edit_info(self, cr, uid, ids, prop, unknow_none, context=None):
        res = {}
        groups = self.pool.get('res.users').get_groups(cr, uid)
        for record in self.read(cr, uid, ids, ['user_id']):
            res[record['id']] = False
            
            if set(['vhr_cb_profile','vhr_hr_admin']).intersection(set(groups)):
                res[record['id']] = True
        
        return res
    
    
    def _is_have_working_record(self, cr, uid, ids, prop, unknow_none, context=None):
        '''
        Check if employee is having active working record with change form != dissmiss
        '''
        res = {}
        
        change_form_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_master_data_dismiss_change_form_code') or ''
        change_form_code = change_form_code.split(',')
        
        dismiss_local_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_master_data_dismiss_local_company') or ''
        dismiss_local_code = dismiss_local_code.split(',')
        
        change_form_code += dismiss_local_code
        
        dismiss_change_form_ids = self.pool.get('vhr.change.form').search(cr, uid, [('code', 'in', change_form_code)],context=context)
        for employee_id in ids:
            domain = [('employee_id','=',employee_id),
                      ('active','=',True),
                      ]
            if dismiss_change_form_ids:
                for change_form_id in dismiss_change_form_ids:
                    domain.append(('change_form_ids','!=',change_form_id))
                    
            wr_ids = self.pool.get('vhr.working.record').search(cr, uid, domain)
            res[employee_id] = wr_ids and True or False
                
        return res
    
    def _get_current_contract_type(self, cr, uid, ids, field_name, arg, context=None):
        if not isinstance(ids, list):
            ids = [ids]
        contract_pool = self.pool.get('hr.contract')
        res = {}
        
        today = datetime.datetime.today().date()
        for record_id in ids:
            res[record_id] = False
            contract_ids = contract_pool.search(cr, uid, [('employee_id','=',record_id),
                                                                  ('state', 'in', ['draft', 'waiting', 'signed']),
                                                                   ('date_start','<=',today),
                                                                   '|','|',
                                                                   '&',('date_end','>=',today),
                                                                       ('liquidation_date','=',False),
                                                                   '&',('date_end','=',False),
                                                                       ('liquidation_date','=',False),
                                                                       
                                                                       ('liquidation_date','>=',today)
                                                                    ])
            if not contract_ids:
                contract_ids = contract_pool.search(cr, uid, [('employee_id','=',record_id),
                                                                  ('state', 'in', ['draft', 'waiting', 'signed']),
                                                                   ('date_start','>',today),
                                                                    ], order='date_start asc')
                contract_ids = contract_ids and [contract_ids[0]] or []
            if contract_ids:
                type_id = False
                for contract_id in contract_ids:
                    contract = contract_pool.browse(cr, SUPERUSER_ID, contract_id)
                    type_id = contract.type_id and contract.type_id.id or False
                    
                    is_member = contract.company_id and contract.company_id.is_member
                    if not is_member:
                        break
                res[record_id] = type_id
            
        return res
    
    def _get_employee_data_(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        
        for record in self.read(cr, uid, ids, ['gender','birthday']):
            res[record['id']] = {'gender_fcnt': record.get('gender', False),
                                 'birthday_fcnt': record.get('birthday', False)}
        
        return res
    
    _columns = {
        'main_working': fields.many2one('vhr.working.record', string='Main Working Record'),
        'is_able_to_edit_info': fields.function(_is_able_to_edit_info, type='boolean', string='Is Able To Edit Info'),
        'is_have_working_record': fields.function(_is_have_working_record, type='boolean', string="Is Have Working Record"),
        'current_contract_type_id': fields.function(_get_current_contract_type, type='many2one', relation='hr.contract.type', string="Contract Type"),
        'keep_authority': fields.boolean('Keep current authority'),
        
        'gender_fcnt': fields.function(_get_employee_data_,type='selection', selection=[('male', 'Nam'), ('female', 'Nữ')], string='Gender', readonly=True,multi='get_emp_data'),
        'birthday_fcnt': fields.function(_get_employee_data_, type='date', string='Date of Birth',multi='get_emp_data'),
        'job_family_id': fields.many2one('vhr.job.family','Job Family',ondelete='restrict',domain=[('track_id.code','=', 'Professional')]),
        'job_group_id': fields.many2one('vhr.job.group','Job Group',ondelete='restrict'),
        'sub_group_id': fields.many2one('vhr.sub.group','Sub Group',ondelete='restrict'),
        'career_track_id': fields.many2one('vhr.dimension','Career Track',ondelete='restrict',domain=[('dimension_type_id.code','=', 'CAREER_TRACK')]),
        
    }
    
    _defaults = {
                'is_able_to_edit_info': True,
                'is_have_working_record': False,
                'keep_authority': True,
                }
    
    def _check_recursion(self, cr, uid, ids, context=None):
        """
        By pass function to check recursion
        """
        return True

    _constraints = [
        (_check_recursion, 'Error! You cannot create recursive hierarchy of Employee(s).', ['parent_id']),
    ]
    
    def find_main_working(self, cr, uid, employee_id, context=None):
        """
        @return: working record from ealiest main active contract 
        
        (if employee dont have any active main contract to get search company, get first company from list active contract to get return working record)
        """
        res = False
        working_record = self.pool.get('vhr.working.record')
        
        #Get company from earliest main active contract
        default_company_id, company_ids = working_record.get_company_ids(cr, uid, employee_id, context)
        if not default_company_id and company_ids:
            default_company_id = company_ids[0]
        
        today = datetime.date.today()
        args = [('employee_id', '=', employee_id), 
                ('company_id', '=', default_company_id),
                ('state','in',['finish',False]),
                ('effect_from', '<=', today), 
                '|', ('effect_to', '>=', today),
                     ('effect_to', '=', False)
                ]
        res_search = working_record.search(cr, uid, args)
        if len(res_search) == 1:
            res = res_search[0]
        return res

    def update_employee(self, cr, uid, ids, context=None):
        if not isinstance(ids, list):
            ids = [ids]
        mapping_column = {
            'division_id': 'division_id_new',
            'department_group_id': 'department_group_id_new',
            'department_id': 'department_id_new',
            'team_id': 'team_id_new',
            'title_id': 'job_title_id_new',
#             'job_level_id': 'job_level_id_new',
#             'position_class_id': 'position_class_id_new',
            'parent_id': 'manager_id_new',
            'report_to': 'report_to_new',
            'office_id': 'office_id_new',
            'ext_no': 'ext_new',
            'seat_no': 'seat_new',
            'keep_authority': 'keep_authority',
            'company_id': 'company_id',
            
#             'job_level_position_id': 'job_level_position_id_new',
            'job_level_person_id': 'job_level_person_id_new',
            
            'job_family_id': 'pro_job_family_id_new',
            'job_group_id': 'pro_job_group_id_new',
            'sub_group_id': 'pro_sub_group_id_new',
            'career_track_id': 'career_track_id_new',
#             'work_phone': 'work_phone_new',
#             'mobile_phone': 'mobile_phone_new',
#             'work_email': 'work_email_new'
        }
        
        working_record = self.pool.get('vhr.working.record')
        field_read = mapping_column.values()
        
        is_not_allow_to_use_changed_data_from_emp = self.pool.get('ir.config_parameter').get_param(cr, uid, 
                                                                                            'vhr_human_resource_is_not_allow_to_get_changed_employee_data') or ''
                                                                                            
        for record_id in ids:
            try:
                res = {}
                main_working = self.find_main_working(cr, uid, record_id, context)
                if main_working:
                    res.update({'main_working': main_working})
                    value = working_record.read(cr, uid, main_working, field_read)
                    for field in mapping_column.keys():
                        field_value  = value.get(mapping_column[field])
                        if isinstance(field_value, tuple):
                            field_value = field_value[0]
                            
                        res.update({field: field_value})
                    
                    
                    #Clear data job level, job level position when update from vhr_working_record
                    res['job_level_id'] = False
                    res['job_level_position_id'] = False
                    self.write_with_log(cr, uid, record_id, res, context)
                    
                    
                    if not is_not_allow_to_use_changed_data_from_emp:
                        del res['job_level_person_id']
                        self.get_changed_data_employee(cr, uid, record_id, res, context)
                    
                else:
                    log.info('Employee don\'t have any contract')
            except Exception as e:
                log.exception(e)
                raise osv.except_osv('Validation Error !', '%s' % (e))
        
        log.info("Update data for list employee: " + str(ids))
           
        return True
    
    
    def get_changed_data_employee(self, cr, uid, employee_id, res, context=None):
        """
            Changed data at employee_id from working record (Dont have job_level_person_id)
        """
        return True
            

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        args_new = ['|', '|', ('name', operator, name), ('code', operator, name), ('login', operator, name)] + args
        # Use for termination, only hrbp/assistant and cb_termination can select employee for termination offline
        groups = self.pool.get('res.users').get_groups(cr, uid)
        
        emp_login_ids = self.search(cr, uid, [('user_id','=',uid)])
        if context.get('termination_filter_employee', False):
            if 'vhr_cb_termination' in groups or 'vhr_hr_dept_head' in groups:
                pass
            else:
                if 'vhr_hrbp' in groups or 'vhr_assistant_to_hrbp' in groups:
                    employee_ids = self.pool.get('vhr.working.record').get_employee_of_hrbp_ass_hrbp(cr, uid, context=context)
                    colla_employee_ids = self.filter_colla_emp(cr, uid, employee_ids)
                    
                    probation_emp_ids = self.filter_probation_emp(cr, uid, employee_ids, context)
                    #If make termination offline, only allow to choose colla employee
                    employee_ids = colla_employee_ids + emp_login_ids + probation_emp_ids
                        
                    domain = [('id', 'in', employee_ids)]
                else:
                    domain = [('id', 'in', [])]
                if domain:
                    args_new += domain
                    
        ids = self.search(cr, uid, args_new, context=context)
        return self.name_get(cr, uid, ids, context=context)
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        # Dont show employee in group system
        if not context:
            context = {}
#         log.info('-----start search')
#         if not context.get("search_all_employee", False):
#             system_user_ids = self.get_list_users_of_group(cr, uid, 'hrs_group_system', context)
#             args.append(('user_id', 'not in', system_user_ids))

        # Do not show employee_id from context['do_not_show_from_many2many] = [[6, False, [list_ids] ]]
        if context.get('do_not_show_from_many2many', False):
            list_do_not_show = context['do_not_show_from_many2many']
            list_ids = list_do_not_show[0] and list_do_not_show[0][2] or []
            if list_ids:
                args.append(('id', 'not in', list_ids))

        # Filter employee in vhr.mass.movement
        if context.get('filter_by_working_record',
                       False) and 'company_id' in context and 'department_id' in context and 'effect_date' in context:
            employee_ids = self.get_list_employee_belong_to_department_company(cr, uid, context['department_id'],
                                                                               context['company_id'],
                                                                               context['effect_date'], context)
            
            
            
            #Get list employee can choose base on permission of employee
            use_employee_ids = self.pool.get('vhr.working.record').get_list_employee_can_use(cr, uid, context)
            if use_employee_ids:
                if use_employee_ids != 'all_employees':
                    employee_ids = list( set(employee_ids).intersection(set(use_employee_ids)) )
            else:
                employee_ids =  []
            
            
            args.append(('id', 'in', employee_ids))
        
#       Filter employee base on login user and group of that user (filter by context['filter_by_group'] in function
        if context.get('filter_by_group', False):
                
            log.info( "---- filter by group in hr.employee")
            args = self.get_domain_for_object_base_on_groups(cr, uid, args, self._name, context)
            log.info("--- end filter by group in hr.employee")
            context['filter_by_group'] = False
            context['turn_on_filter_after_call_super'] = True
            
            #Filter list contract based on permisison location
            domain = self.get_domain_based_on_permission_location(cr, uid, uid, context)
            if domain:
                args.extend(domain)
            

        res = super(hr_employee, self).search(cr, uid, args, offset, limit, order, context, count)
        
        if context.get('turn_on_filter_after_call_super', False):
            context['filter_by_group'] = True
            context['turn_on_filter_after_call_super'] = False
        
#         log.info('-----end search')
        return res
    
    def filter_colla_emp(self, cr, uid, employee_ids, context=None):
        """
        Return list colla employee from employee_ids
        """
        colla_emp_ids = []
        if employee_ids:
            sql = """
                    SELECT wr.employee_id from vhr_working_record wr 
                                    inner join hr_contract  ct                   on wr.contract_id = ct.id
                                    inner join hr_contract_type c_type           on ct.type_id = c_type.id
                                    inner join hr_contract_type_group type_group on c_type.contract_type_group_id = type_group.id
                    WHERE (type_group.is_offical is null or type_group.is_offical=false) and wr.employee_id in %s and wr.active=True
                  """% str(tuple(employee_ids))
            
            cr.execute(sql)
            res = cr.fetchall()
            colla_emp_ids = [res_id[0] for res_id in res]
                    
        return colla_emp_ids
    
    def filter_probation_emp(self, cr, uid, employee_ids, context=None):
        """
        Return list p employee from employee_ids
        """
        probation_emp_ids = []
        probation_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_human_resource_probation_contract_type_group_code') or ''
        today = datetime.datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT)
        if employee_ids:
            sql = """
                    SELECT wr.employee_id from vhr_working_record wr 
                                    inner join hr_contract  ct                   on wr.contract_id = ct.id
                                    inner join hr_contract_type c_type           on ct.type_id = c_type.id
                                    inner join hr_contract_type_group type_group on c_type.contract_type_group_id = type_group.id
                    WHERE type_group.is_offical=True and 
                          type_group.code ='{1}' and 
                          wr.employee_id in {2} and 
                          wr.active=True and
                          ct.date_start <= '{0}' and
                         ( ct.date_end >= '{0}' or ct.date_end is null)
                  """.format(today, probation_code, str(tuple(employee_ids)))
            
            cr.execute(sql)
            res = cr.fetchall()
            probation_emp_ids = [res_id[0] for res_id in res]
                    
        return probation_emp_ids
    
    def get_domain_based_on_permission_location(self, cr, uid, user_id, context=None):
        """
        return domain to search employee based on permission location
        """
        res = []
        if user_id:
            permission_obj = self.pool.get('vhr.permission.location')
            working_obj = self.pool.get('vhr.working.record')
            employee_ids = self.search(cr, uid, [('user_id','=',user_id)])
            if employee_ids:
                record_ids = permission_obj.search(cr, uid, [('employee_id','in',employee_ids)])
                if record_ids:
                    record = permission_obj.read(cr, uid, record_ids[0], ['company_ids','office_ids'])
                    company_ids = record.get('company_ids',[])
                    office_ids = record.get('office_ids',[])
                    
                    domain = []
                    if company_ids:
                        domain.append(('company_id','in', company_ids))
                    
                    if office_ids:
                        domain.append(('office_id_new','in', office_ids))
                    
                    #Search employee in company or office at active working record
                    if domain:
                        domain.extend([('active','=',True),('state','in',[False,'finish'])])
                        working_ids = working_obj.search(cr, uid, domain, context={'active_test': False})
                        if working_ids:
                            workings = working_obj.read(cr, uid, working_ids, ['employee_id'])
                            employee_ids = [wr.get('employee_id', False) and wr['employee_id'][0] for wr in workings]
                            res.append(('id','in',employee_ids))
                        
        return res
    
    # Get list employee have department-company in effect_from
    def get_list_employee_belong_to_department_company(self, cr, uid, department_id, company_id, effect_date,
                                                       context=None):
        '''
            Get list employee belong to department- company and have contract at effect_date
        '''
        if not context:
            context = {}
        employee_ids = []
        if company_id and effect_date and (department_id or context.get('department_id_can_false', False)):
            working_pool = self.pool.get('vhr.working.record')
            contract_pool = self.pool.get('hr.contract')
            # Search for all WR have company,department_id, and effect_date in effect_from-effect_to
            
            dismiss_form_ids = self.get_change_form_ids_of_dismiss(cr, uid, context)
            sql = """
                    SELECT wr.employee_id FROM vhr_working_record   wr  
                    INNER JOIN working_record_change_form_rel rel ON wr.id=rel.working_id 
                    WHERE       wr.company_id = %s
                           and  (wr.state = 'finish' or wr.state is null)
                           and  wr.effect_from <= '%s'
                           and  (wr.effect_to is null or wr.effect_to >= '%s')
                           and rel.change_form_id not in %s
                  """% (company_id, effect_date, effect_date, str(tuple(dismiss_form_ids)).replace(',)', ')'))
            
            if department_id:
                sql += """ and department_id_new = %s""" % department_id
            
            cr.execute(sql)
            res = cr.fetchall()
            employee_ids = [item[0] for item in res]

            
            #Filter list employee have active contract at effect_date
            if employee_ids:
                #The domain of this search from onchange_effect_from of vhr_working_record
                #Get contract have effect_from >= date_start and effect_from <= date_end(or liquidation_date if liquidation_date!=False) of company contract and largest date_start 
                contract_ids = contract_pool.search(cr, uid,[('company_id','=',company_id),
                                                             ('employee_id','in',employee_ids),
                                                             ('date_start','<=',effect_date),
                                                             ('state','=','signed'),
                                                             '|','|',
                                                                 ('liquidation_date','>=',effect_date),
                                                             '&',('date_end','>=',effect_date),('liquidation_date','=',False),
                                                             '&',('date_end','=',False),('liquidation_date','=',False),
                                                             ], order='date_start desc')
                employee_ids = []
                if contract_ids:
                    contracts = contract_pool.read(cr, uid, contract_ids, ['employee_id'])
                    employee_ids = [contract.get('employee_id',False) and contract['employee_id'][0] for contract in contracts]
                    

        return list(set(employee_ids))
    
    def get_change_form_ids_of_dismiss(self, cr, uid, context=None):
        config_parameter = self.pool.get('ir.config_parameter')
        
        dismiss_code = config_parameter.get_param(cr, uid, 'vhr_master_data_dismiss_change_form_code') or ''
        dismiss_code_list = dismiss_code.split(',')
        
        dismiss_local_comp_code = config_parameter.get_param(cr, uid, 'vhr_master_data_dismiss_local_company') or ''
        dismiss_local_comp_code_list = dismiss_local_comp_code.split(',')
        
        code_list = dismiss_code_list + dismiss_local_comp_code_list
        
        form_ids = self.pool.get('vhr.change.form').search(cr, uid, [('code','in', code_list)])
        
        return form_ids
    
    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False,
                   lazy=True):
        """
        Get the list of records in list view grouped by the given ``groupby`` fields
        """
        if not context:
            context = {}
        
        res = self.search(cr, uid, domain, 0, 0, 0, context, False)
        domain.append(('id','in',res))

        res =  super(hr_employee, self).read_group(cr, uid, domain, fields, groupby, offset, limit, context, orderby,
                                                   lazy)
        
        return res
    
    def read(self, cr, user, ids, fields=None, context=None, load='_classic_read'):
        if not context:
            context = {}
            
        if context.get('validate_read_hr_employee',False):
            log.info('\n\n validate_read_hr_employee')
            if not context.get('filter_by_group', False):
                context['filter_by_group'] = True
            result_check = self.validate_read(cr, user, ids, context)
            if not result_check:
                raise osv.except_osv('Validation Error !', 'You don’t have permission to access this data !')
            del context['validate_read_hr_employee']
        
        groups = self.pool.get('res.users').get_groups(cr, user)
        
        is_have_audit_log_field = False
        if not set(groups).intersection(['hrs_group_system','vhr_cb_profile']) and 'audit_log_ids' in fields:
            fields.remove('audit_log_ids')
            is_have_audit_log_field = True
            
        res = super(hr_employee, self).read(cr, user, ids, fields, context, load)
        
        if res and is_have_audit_log_field:
            if isinstance(res, list):
                for data in res:
                    if data:
                        data['audit_log_ids'] = []
            else:
                res['audit_log_ids'] = []
                    
        
        res = self.mask_data_employee(cr, user, ids, res, fields, context)
        
        return res
    
    def mask_data_employee(self, cr, user, ids, res, fields=None, context=None):
        """
        Mask data if user dont have permission to read fields
        """
        if res and ids:
            if not isinstance(ids, list):
                ids = [ids]
                
            emp_login_ids = self.search(cr, user, [('user_id','=',user)])
            other_ids = set(ids).difference(emp_login_ids)
            
            none_data = self.get_none_data_for_employee(cr, user, context)
            groups = self.pool.get('res.users').get_groups(cr, user)
            
            allow_groups = ['vhr_cb','vhr_assistant_to_hrbp','vhr_dept_head',
                            'hrs_group_system','vhr_hr_admin','vhr_recruiter','vhr_recruitment_manager']
            
            if len(ids) == 1 and 'vhr_recruiter' in groups and 'address_home_id' in none_data: 
                del none_data['address_home_id']
                
            #If read employee data of another employee
            if 'is_able_to_see_other_tabs' in fields:
                if isinstance(res, list):
                    for data in res:
                        if data.get('is_able_to_see_other_tabs',False) == False:
                            data.update(none_data)
                            data['job_level_person_id'] = False
                elif res.get('is_able_to_see_other_tabs',False) == False:
                    res.update(none_data)
                    res['job_level_person_id'] = False
                    
            elif other_ids:
                
                none_fields = none_data.keys()
                none_fields.append('job_level_person_id')
                if set(none_fields).intersection(fields) and  not set(allow_groups).intersection(groups):
                    
                    if isinstance(res, list):
                        for data in res:
                            if data.get('id', False) not in emp_login_ids:
                                data.update(none_data)
                                data['job_level_person_id'] = False
                    else:
                        res.update(none_data)
                        res['job_level_person_id'] = False
                        
                        
        return res
    
    def get_none_data_for_employee(self, cr, uid, context=None):
        """
        return none data when read if dont have permission to read these fields
        """
        res = {'street': '', 'email': '', 'temp_address': '',
               'city_id': False, 'district_id': False, 'temp_city_id': False, 'temp_district_id': False, 'address_home_id': False,
               'nation_id': False, 'native_city_id': False, 'birth_city_id': False, 'religion_id': False, 'personal_document': [],
               'certificate_ids': [], 'duty_free': [], 'health_care': [], 'property_management': [], 'relation_partners': [],
               'bank_ids': [], 'old_bank_ids': [], 'instance_ids': [], 'working_background': [], 'assessment_result_ids': [],
               'audit_log_ids': []
               }
        
        return res
 
    def validate_read(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        user_groups = self.pool.get('res.users').get_groups(cr, uid)
        if set(['hrs_group_system', 'vhr_cnb_manager']).intersection(set(user_groups)):
            return True
        if isinstance(ids, (int, long)) or (isinstance(ids, list) and len(ids)) == 1:
            log.info( ' ---go to search in validate_read employee')
            check_id = ids
            if isinstance(ids, list):
                check_id = ids[0]
            new_context = context and context.copy() or {}
            new_context.update({'filter_by_group': True, 'active_test': False})
            lst_check = self.search(cr, uid, [], context=new_context)
            if check_id not in lst_check:
                return False
        return True


    def get_working_record_of_employee(self, cr, uid, employee_id, company_id, context=None):
        """
        get working_record of employee depend on company_id in working record
        :param cr:
        :param uid:
        :param company_id:
        :param context:
        :return: list department_id
        """
        if context is None:
            context = {}
        res = []
        if employee_id and company_id:
            working_record_obj = self.pool.get('vhr.working.record')
            record_ids = working_record_obj.search(cr, uid, [('employee_id', '=', employee_id),
                                                             ('company_id', '=', company_id),
                                                             ('active', '=', True)])
            if record_ids:
                for wr in working_record_obj.read(cr, uid, record_ids, [], context=context):
                    res.append(wr)
        return res
    
    def fields_view_get(self, cr, uid, view_id = None, view_type = 'form', context = None, toolbar = False, submenu = False):
        res = super(hr_employee, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar = toolbar, submenu = submenu)
        if context is None:
            context = {}
        
        special_group = ['vhr_cb_profile','vhr_hr_admin']
        groups = self.pool.get('res.users').get_groups(cr, uid)
        doc = etree.XML(res['arch'])
        if view_type == 'form':
            if res['type'] == 'form':
                
                #Only cb profile and hr_admin can create employee
                if not set(special_group).intersection(groups):
                    for node in doc.xpath("//form"):
                        node.set('create',  '0')
                        node.set('edit',  '0')
                        
                fields = self._columns.keys()
                fields.append('user_id')
                fields_not_update = ['is_reject','parent_id','login','end_date','audit_log_ids','instance_ids','mobile_phone',
                              'is_asset','is_create_account','keep_authority','work_phone','gender_fcnt','birthday_fcnt',
                              'job_family_id','job_group_id','sub_group_id''street','city_id','district_id','partner_country_id',
                              'birthday','birth_city_id','personal_document','native_city_id','nation_id','country_id','mobile']
                fields = list(set(fields)-set(fields_not_update))
                
                #Dont allow to edit these field when employee have working record
                fields_not_update_when_have_wr = ['office_id','seat_no','ext_no','division_id','department_id','department_group_id',
                                                   'team_id','title_id','job_level_id','report_to','job_level_person_id']
                    
                for field in fields:
                    for node in doc.xpath("//field[@name='%s']" %field):
                        modifiers = json.loads(node.get('modifiers'))
                        args_readonly = [('is_able_to_edit_info','=',False)]
                        
                        #Dont allow to edit join_date if: person is not cb_profile, employee having active working record(not dismiss)
                        if field == 'join_date':
                            args_readonly.insert(0,'|')
                            args_readonly.append(('is_have_working_record','=',True))
                            
                        elif field =='user_id':
                            if not set(special_group).intersection(groups):
                                args_readonly = True
                            else:
                                args_readonly = False
                                
                        elif field in fields_not_update_when_have_wr:
                            args_readonly.insert(0,'|'),
                            args_readonly.append(('is_have_working_record','=',True))
                        
                        if field =='assessment_result_ids' and modifiers.get('invisible', False) == True:
                            try:
                                node.getparent().remove(node)
                            except:
                                pass
                            
                        modifiers.update({'readonly' : args_readonly})
                        node.set('modifiers', json.dumps(modifiers))
        elif view_type == 'tree':
            if res['type'] == 'tree':
                #Only cb profile and hr_admin can create employee
                if not set(special_group).intersection(groups):
                    for node in doc.xpath("//tree"):
                        node.set('create',  '0')
                        node.set('edit',  '0')
                        
        res['arch'] = etree.tostring(doc)
        return res

    def get_employee_by_login(self, cr, uid, login, context=None):
        if context is None:
            context = {}
        res = {}
        emp_ids = self.search(cr, uid, [('login', '=', login), ('active', '=', True)], context=context)
        if emp_ids:
            flds = ['name', 'code', 'login', 'department_id', 'team_id', 'street', 'mobile']
            res = self.read(cr, uid, emp_ids[0], flds, context=context)
        return res
    
    def generate_none_job_family_in_employee(self, cr, uid, *args):
        emp_ids = self.search(cr, uid, [('job_family_id','=',False),
                                        ('main_working','!=',False),
                                        ('active','=',True)])
        print '\n len initial=',len(emp_ids)
        if emp_ids:
            emp_ids = emp_ids[:300]
        print '\n len after filter=',len(emp_ids)
        wr_obj = self.pool.get('vhr.working.record')
        
        print "\n generate job family for %s employees" % (len(emp_ids))
        for employee in self.read(cr, uid, emp_ids, ['main_working']):
            working_id = employee.get('main_working', False) and employee['main_working'][0]
            if working_id:
                wr = wr_obj.read(cr, uid, working_id, ['pro_job_family_id_new','pro_job_group_id_new','pro_sub_group_id_new'])
                pro_job_family_id_new = wr.get('pro_job_family_id_new', False) and wr['pro_job_family_id_new'][0]
                pro_job_group_id_new = wr.get('pro_job_group_id_new', False) and wr['pro_job_group_id_new'][0]
                pro_sub_group_id_new = wr.get('pro_sub_group_id_new', False) and wr['pro_sub_group_id_new'][0]
                
                vals = {'job_family_id': pro_job_family_id_new,
                        'job_group_id': pro_job_group_id_new,
                        'sub_group_id': pro_sub_group_id_new}
                
                super(hr_employee, self).write(cr, uid, employee['id'], vals)
        
        print '\n finish generate job family'
        return True
    
    def cron_remove_inactive_employee_from_mapping_table(self, cr, uid, mapping_table='', context=None):
        """
        Remove inactive employee from HRBP, Assistant HRBP
        """
        log.info("\nStart remove inactive employee from mapping table")
        
        if mapping_table:
            mapping_table = mapping_table.split(',')
        else:
            mapping_table = ['hrbp_department_rel','ass_hrbp_department_rel','ram_department_rel','main_hrbp_department_rel','rr_hrbp_department_rel']
        
    
        sql = "  SELECT employee_id from %s "
        
        for table in mapping_table:
            cr.execute(sql%table)
            employee_ids = map(lambda x: x[0], cr.fetchall())
            inactive_emp_ids = self.search(cr, uid, [('id','in',employee_ids),
                                                     ('active','=',False)])
            if inactive_emp_ids:
                rm_sql = " DELETE FROM %s where employee_id in %s "
                
                cr.execute(rm_sql%(table,str(tuple(inactive_emp_ids)).replace(',)', ')')))
        
        log.info("\nFinish remove inactive employee from mapping table")


hr_employee()