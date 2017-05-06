# -*-coding:utf-8-*-
import datetime
import time
import logging
from lxml import etree
import simplejson as json

from openerp.osv import osv, fields
from openerp.addons.vhr_common.model.vhr_common import vhr_common
from openerp import SUPERUSER_ID

log = logging.getLogger(__name__)


class hr_employee(osv.osv, vhr_common):
    _name = 'hr.employee'
    _inherit = 'hr.employee'
    _description = 'HR Employee'

    def _check_employee(self, cr, uid, ids, prop, unknow_none, context=None):
        res = {}
        for item in self.browse(cr, uid, ids, context=context):
            join_date = item.join_date
            if join_date and join_date > time.strftime("%Y-%m-%d"):
                res[item.id] = True
            else:
                res[item.id] = False
        return res
    
    def _is_able_to_see_other_tabs(self, cr, uid, ids, prop, unknow_none, context=None):
        res = {}
        groups = self.pool.get('res.users').get_groups(cr, uid)
        mcontext={'search_all_employee': True}
        for record in self.read(cr, uid, ids, ['user_id'],context=mcontext):
            res[record['id']] = False
            
            if set(['vhr_cb','vhr_assistant_to_hrbp','vhr_hrbp','vhr_dept_head','vhr_hr_dept_head','vhr_hr_admin']).intersection(set(groups)):
                res[record['id']] = True
            elif record['user_id'] and record['user_id'][0] == uid:
                res[record['id']] = True
            else:
                res[record['id']] = False
        
        return res
    
    def _get_old_bank_ids(self, cr, uid, ids, prop, unknow_none, context=None):
        res = {}
        for record_id in ids:
            res[record_id] = {}
            res[record_id]['old_bank_ids'] = []
            res[record_id]['is_have_main_bank'] = False
            main_bank_ids = self.pool.get('res.partner.bank').search(cr, uid, [('employee_id','=',record_id),('is_main','=',True)])
            if main_bank_ids:
                res[record_id]['is_have_main_bank'] = True
                    
        return res
    

    def _contracts_count(self, cr, uid, ids, field_name, arg, context=None):
        Contract = self.pool['hr.contract']
        return {
            employee_id: Contract.search_count(cr, uid, [('employee_id', '=', employee_id)], context=context)
            for employee_id in ids
        }

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        res = super(hr_employee, self).default_get(cr, uid, fields, context=context)
        if res.get('company_id'):
            del res['company_id']
        if not res.get('bank_ids', False) and context.get('default_unknown_bank', False):
            values = self.get_unknown_bank(cr, uid, context)
            res['bank_ids'] = values
        return res

    def get_unknown_bank(self, cr, uid, context=None):
        values = []
        bank_object = self.pool.get('res.bank')
        pn_bank_object = self.pool.get('res.partner.bank')
        acc_number = 'Unknown %s' % (str(time.time()))#Get acc number theo thời gian thực. 
        
        default_bank_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_master_data_default_bank') or ''
        default_bank_code = default_bank_code.split(',')
            
        bank_ids = bank_object.search(cr, uid, [('code', 'in', default_bank_code)], context=context)
        if bank_ids:
            values.append(
                [0, False, {'acc_number': acc_number, 'owner_name': 'Unknown', 'bank': bank_ids[0], 'is_main': True}])
        return values
    
    def _update_login_in_employee(self, cr, uid, ids, context=None):
        res = self.pool.get('hr.employee').search(cr, uid, [('user_id', 'in', ids),
                                                            '|',('active','=',False),
                                                                ('active','=',True)])
        return res
    
    def _get_employee_change_user_id(self, cr, uid, ids, context=None):
        return ids
    
    _columns = {
        'create_date': fields.datetime('Creation Date', readonly=True),
        'contracts_count': fields.function(_contracts_count, type='integer', string='Contracts'),
        'address_home_id': fields.many2one('res.partner', 'Home Address', domain=[('is_company', '=', False)]),

        'street': fields.related('address_home_id', 'street', type='char', string="Street"),
        'ward': fields.related('address_home_id', 'ward', type='char', string="Ward"),#Phường/xã 
        'city_id': fields.related('address_home_id', 'city', type='many2one', relation="res.city",
                                  string="Permanent City"),
        'district_id': fields.related('address_home_id', 'district_id', type='many2one', relation="res.district",
                                      string="District"),
        'partner_country_id': fields.related('address_home_id', 'country_id', type='many2one', relation="res.country",
                                             string="Country"),
        'use_parent_address': fields.related('address_home_id', 'use_parent_address', type='boolean',
                                             string='Use Company Address'),

        'temp_address': fields.related('address_home_id', 'temp_address', type='char', string="Temporary address"),
        'temp_ward': fields.related('address_home_id', 'temp_ward', type='char', string="Ward"),#Phường/xã 
        'temp_city_id': fields.related('address_home_id', 'temp_city_id', type='many2one', relation="res.city",
                                       string="Temporary City"),
        'temp_district_id': fields.related('address_home_id', 'temp_district_id', type='many2one',
                                           relation="res.district", string="Temporary District"),
        'phone': fields.related('address_home_id', 'phone', type='char', string="Home Phone"),
        'mobile': fields.related('address_home_id', 'mobile', type='char', string="Mobile"),
        'email': fields.related('address_home_id', 'email', type='char', string="Email"),

        'company_group_id': fields.many2one('vhr.company.group', 'Company Group'),
        # 'barcode': fields.char('Barcode', size=9),
        'gender': fields.selection([('male', 'Nam'), ('female', 'Nữ')], 'Gender'),
        'marital': fields.selection([('single', 'Độc Thân'), ('married', 'Đã Lập Gia Đình'), ('divorced', 'Đã Ly Hôn'),
                                     ('widowed', 'Góa Vợ/Chồng')], 'Marital Status'),
        'first_name': fields.char('First Name', size=128),
        'last_name': fields.char('Last & Mid Name', size=128),
        'birth_city_id': fields.many2one('res.city', 'City of Birth', ondelete='restrict'),
        'native_place': fields.char('Address', size=256),
        'native_city_id': fields.many2one('res.city', 'City', ondelete='restrict'),
        'nation_id': fields.many2one('vhr.dimension', 'Ethnic', ondelete='restrict',
                                     domain=[('dimension_type_id.code', '=', 'NATION'), ('active', '=', True)]),
        'religion_id': fields.many2one('vhr.dimension', 'Religion', ondelete='restrict',
                                       domain=[('dimension_type_id.code', '=', 'RELIGION'), ('active', '=', True)]),
        'relation_partners': fields.one2many('vhr.employee.partner', 'employee_id', 'Relation Partners'),
        'bank_ids': fields.one2many('res.partner.bank', 'employee_id', string='Bank Accounts'),
        'place_of_birth': fields.char('Place of Birth', size=256),
        # Get info form contract
        'division_id': fields.many2one('hr.department', 'Business Unit', ondelete='restrict',
                                       domain=[('organization_class_id.level', '=', 1)]),
                
        'department_group_id': fields.many2one('hr.department', 'Department Group', domain=[('organization_class_id.level','=', 2)], 
                                               ondelete='restrict'),    

        'team_id': fields.many2one('hr.department', 'Team', ondelete='restrict',
                                   domain=[('organization_class_id.level', '>', 3)]),
        'organization_class_id': fields.related('department_id', 'organization_class_id', type='many2one',
                                                relation='vhr.organization.class', string='Organization Class'),
        'title_id': fields.many2one('vhr.job.title', string='Job Title', ondelete='restrict'),
        'job_level_id': fields.many2one('vhr.job.level', 'Level', ondelete='restrict'),
        
         #New job level
        'job_level_position_id': fields.many2one('vhr.job.level.new', 'Position Level', ondelete='restrict'),
        'job_level_person_id': fields.many2one('vhr.job.level.new', 'Person Level', ondelete='restrict'),
        
         #LuanNG: Remove this field in future version of vHRS
        'position_class_id': fields.many2one('vhr.position.class', 'Position Class', ondelete='restrict'),

        'office_id': fields.many2one('vhr.office', 'Office', ondelete='restrict'),
        'ext_no': fields.char('Ext', size=32),
        'seat_no': fields.char('Seat No', size=32),
        'report_to': fields.many2one('hr.employee', 'Reporting line'),
        # Another info of employee
        'health_care': fields.one2many('vhr.health.care.record', 'employee_id', string='Health Check Info'),
        'property_management': fields.one2many('vhr.property.management', 'employee_id', string="Employee's Asset"),
        'personal_document': fields.one2many('vhr.personal.document', 'employee_id', string='Personal Document'),
        'duty_free': fields.one2many('vhr.duty.free', 'employee_id', string='Free duty'),
        'working_background': fields.related('address_home_id', 'working_background', type='one2many',
                                             relation='vhr.working.background', string='Working Background'),
        'certificate_ids': fields.one2many('vhr.certificate.info', 'employee_id', string='Certificates/Degree'),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                         domain=[('object_id.model', '=', _name), \
                                                 ('field_id.name', 'not in',
                                                  ['write_date', 'audit_log_ids','main_working'])]),
        'contract_ids': fields.one2many('hr.contract', 'employee_id', string='Contracts'),

        'working_background': fields.one2many('vhr.working.background', 'employee_id', 'Working Background'),
        'instance_ids': fields.one2many('vhr.employee.instance', 'employee_id', 'Employee Instance'),

        'write_uid': fields.many2one('res.users', 'Update User'),
        'write_user': fields.related('write_uid', 'login', type="char", string="Update User"),
        'write_date': fields.date('Update Date'),
        'login': fields.related('user_id', 'login', type='char', string='Login', readonly=1, 
                                                    store={'res.users': (_update_login_in_employee, ['login'], 10),
                                                           'hr.employee': (_get_employee_change_user_id, ['user_id'], 10)
                                                           }),
        'work_phone': fields.related('office_id', 'phone', type="char", string="Office Phone"),
        'mobile_phone': fields.char('Cell phone', size=32, readonly=False),
        'work_email': fields.char('Working Email', size=240),
        'join_date': fields.date('Join Date'),
        'end_date': fields.date('End Date'),
        'is_candidate': fields.function(_check_employee, type='boolean', string='Candidate'),
        'is_able_to_see_other_tabs': fields.function(_is_able_to_see_other_tabs, type='boolean', string='Is Able To See Other Tabs'),
        
        'old_bank_ids': fields.function(_get_old_bank_ids, type='one2many', relation='res.partner.bank', string='Old Bank', multi='bank'),
        'is_have_main_bank': fields.function(_get_old_bank_ids, type='boolean', string='Have Main Bank', multi='bank'),
        'is_create_account': fields.boolean('Is Create Account'),
        'is_asset': fields.boolean('Is Asset'),
        'is_reject': fields.boolean('Is Reject'),#Case employee will join date at today +2days but they decide to not join any more
        'assessment_result_ids': fields.one2many('vhr.employee.assessment.result', 'employee_id', "Assessment Result"),
        'company_code': fields.related('company_id', 'code', type='char', string='Company'),

    }

    _order = "join_date desc"
    
    _defaults = {
        'active': True,
        'is_able_to_see_other_tabs': True,
        'is_create_account': True,
        'is_asset': True,
        'partner_country_id': lambda self, cr, uid, context:
        self.pool.get('res.country').search(cr, uid, [('code', '=', 'VN')])[0]
    }

    _unique_insensitive_constraints = [{'code': "Employee's Code is already exist!"},
                                       # {'barcode': "Employee's barcode is already exist!"},
    ]

    def name_get(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        if not ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        reads = self.read(cr, uid, ids, ['name', 'login'], context=context)
        res = []
        for record in reads:
            login = record.get('login', '') or ""
            name = record.get('name', "") or ""
            fullname = name
            if context.get('show_domain', False):
                if login != "":
                    fullname = login
                res.append((record.get('id', False), fullname))
            else:
                if login != "":
                    fullname = fullname + " (" + login + ")"
                res.append((record.get('id', False), fullname))
        
        return res

    def generate_code(self, cr, uid, company_group_id, context=None):
        ''' MaKhoi-xxxxx
            Trong do xxxxx la so tu tang
        '''
        if not company_group_id:
            return False
        if context is None:
            context = {}
        
        res = ''
        
        is_turn_on = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_human_resource_code_turn_off_update_nearest_code') or 0
        if is_turn_on in ['2','1']:
            res = self.pool.get('ir.sequence').get_temp_next_by_code_with_company_group(cr, uid, 'hr.employee.sequence', company_group_id)
        else:
            context.update({'active_test': False})
            company_group = self.pool.get('vhr.company.group')
            res = company_group.read(cr, uid, company_group_id, ['code'])
            ids = self.search(cr, uid, [('company_group_id', '=', company_group_id)], None, None, 'id desc, code desc', context,
                              False)
            stt = 0
            for read_res in self.read(cr, uid, ids, ['code']):
                if read_res and isinstance(read_res['code'], (str, unicode)):
                    split_stt = read_res['code'].split('-')
                    if int(split_stt[1]) > stt:
                        stt = int(split_stt[1])
            res = '%s-%05i' % (res['code'], stt + 1)
            
        return res

    def onchange_company_group(self, cr, uid, ids, company_group_id):
        res = {'value': {}}
        if company_group_id:
            res['value'] = {'code': self.generate_code(cr, uid, company_group_id)}
        return res
    
    def onchange_division_id(self, cr, uid, ids, division_id):
        return {'value': {'department_group_id': False, 'department_id': False, 'parent_id': False}}
    
    def onchange_department_group_id(self, cr, uid, ids, department_group_id):
        return {'value': {'department_id': False, 'parent_id': False} }
    
    def onchange_department_id(self, cr, uid, ids, department_id, context=None):
        res ={'parent_id': False}
        if department_id:
            department = self.pool.get('hr.department').read(cr, uid, department_id, ['manager_id'])
            manager_id = department.get('manager_id', False) and department['manager_id'][0] or False
            res['parent_id'] = manager_id
        
        return {'value': res}
    
    def onchange_office_id(self, cr, uid, ids, office_id, context=None):
        res = {'work_phone': ''}
        if office_id:
            office = self.pool.get('vhr.office').read(cr, uid, office_id, ['phone'])
            phone = office.get('phone','')
            res['work_phone'] = phone
        
        return {'value': res}

    def onchange_name(self, cr, uid, ids, first_name, last_name):
        res = ''
        if first_name and last_name:
            res = '%s %s' % (last_name, first_name)
        return {'value': {'name': res}}
    
    def onchange_bank_ids(self, cr, uid, ids, bank_ids, old_bank_ids, context=None):
        res = {}
        
        if not old_bank_ids:
            old_bank_ids = []
        
        #Edit/Create first record
        bank_data_main = []
        if bank_ids == old_bank_ids:
            return {'value': {}}
        if not old_bank_ids:
            for bank_data in bank_ids:
                if len(bank_data) == 3 and bank_data[0] in [0,1] and bank_data[2] and bank_data[2].get('is_main',False):
                    bank_data_main = bank_data
                    break
        else:
            for bank_data in bank_ids:
                if len(bank_data) == 3 and bank_data not in old_bank_ids and bank_data[0] in [0,1] and bank_data[2] and bank_data[2].get('is_main',False):
                    bank_data_main = bank_data
                    break
        
        res['is_have_main_bank'] = False
        if bank_data_main:
            res['is_have_main_bank'] = True
            res['old_bank_ids'] = bank_ids
            for bank_data in bank_ids:
                if len(bank_data) == 3 and bank_data != bank_data_main:
                    if bank_data[0] == 4:
                        bank_data[0] = 1
                        bank_data[2] ={'is_main': False }
                
                    elif bank_data[0] == 0:
                        bank_data[2]['is_main'] = False
                    
                    elif bank_data[0] == 1:
                        bank_data[2]['is_main'] = False
            
            res['bank_ids'] = bank_ids
        
        else:
            bank_pool = self.pool.get('res.partner.bank')
            #Loop to check if have main bank
            for bank_data in bank_ids:
                if len(bank_data) == 3:
                    if bank_data[0] == 4 and bank_data[1]:
                        bank = bank_pool.read(cr, uid, bank_data[1], ['is_main'])
                        if bank.get('is_main', False):
                            res['is_have_main_bank'] = True
                            break
                
                    elif bank_data[0] == 0:
                        if 'is_main' in bank_data[2]:
                            res['is_have_main_bank'] = bank_data[2].get('is_main', False)
                            
                            if res['is_have_main_bank']:
                                break
                    
                    elif bank_data[0] == 1:
                        if 'is_main' in bank_data[2]:
                            res['is_have_main_bank'] = bank_data[2].get('is_main', False)
                        else:
                            bank = bank_pool.read(cr, uid, bank_data[1], ['is_main'])
                            if bank.get('is_main', False):
                                res['is_have_main_bank'] = True
                        
                        if res['is_have_main_bank']:
                            break
                        
        
        return {'value': res}
    
    
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(hr_employee, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res

    def get_company_ids(self, cr, uid, employee_id, context=None):
        """
        Currently this function used to get company base on employee instance and is_member in res.company
        """
        company_ids = []
        company_id = False
        if employee_id:
            emp_instance_obj = self.pool.get('vhr.employee.instance')
            # Get list employee instance of employee have date_end=False
            emp_instance_ids = emp_instance_obj.search(cr, uid, [('employee_id', '=', employee_id),
                                                                 ('date_end', '=', False)])
            if emp_instance_ids:
                emp_instances = emp_instance_obj.read(cr, uid, emp_instance_ids, ['company_id'], context=context)
                for emp_instance in emp_instances:
                    company_id = emp_instance.get('company_id', False) and emp_instance['company_id'][0]
                    company_ids.append(company_id)

        # Get default company to be the first company have is_member=False
        # If dont have any company have is_member=False, get first company
        if company_ids:
            company_ids = list(set(company_ids))
            company_pool = self.pool.get('res.company')
            company_infos = company_pool.read(cr, uid, company_ids, ['is_member'])
            for company_info in company_infos:
                if not company_info['is_member']:
                    company_id = company_info['id']
                    break
            if not company_id:
                company_id = company_ids[0]

        return company_id, company_ids

    def get_company_list_of_employee(self, cr, uid, employee_id, context=None):
        """
        Get active company list of employee
        :param cr:
        :param uid:
        :param employee_id:
        :param context:
        :return: list company_id
        """
        res = []
        if employee_id:
            contract_obj = self.pool.get('hr.contract')
            today = fields.date.context_today(self, cr, uid, context=context)
            contract_ids = contract_obj.search(cr, uid,
                                               [('employee_id', '=', employee_id), ('date_start', '<', today), '|',
                                                ('date_end', '=', False), ('date_end', '>=', today)])

            if contract_ids:
                contracts = contract_obj.read(cr, uid, contract_ids, ['company_id'], context=context)
                res = filter(None, map(lambda a: a.get('company_id') and a['company_id'][0] or '', contracts))
        return res

    def get_list_users_of_group(self, cr, uid, group_xml_id, context=None):
        """
        Return list users belong to group
        """
        user_ids = []
        if group_xml_id:
            ir_model_ids = self.pool.get('ir.model.data').search(cr, uid, [('model', '=', 'res.groups'),
                                                                           ('name', '=', group_xml_id)])
            if ir_model_ids:
                ir_model_info = self.pool.get('ir.model.data').read(cr, uid, ir_model_ids[0], ['res_id'])
                group_id = ir_model_info.get('res_id', False)
#                 group_info = self.pool.get('res.groups').read(cr, uid, group_id, ['users'])
                user_ids = self.get_user_id_of_group(cr, uid, group_id, context)

        return user_ids
    
    
    def get_user_id_of_group(self, cr, uid, group_id, context=None):
        user_ids = []
        if group_id:
            sql = "SELECT uid from res_groups_users_rel WHERE gid= %s"
            cr.execute(sql % group_id)
            user_ids = map(lambda x: x[0], cr.fetchall())
        
        return user_ids

    def validate_birthday(self, cr, uid, vals, context=None):
        if vals.get('birthday'):
            config_parameter = self.pool.get('ir.config_parameter')
            year_old = config_parameter.get_param(cr, uid, 'vhr_master_data_min_birth_of_employee') or 0
            birthday = self.validate_date(vals['birthday'])
            today = datetime.date.today()
            if (today.year - birthday.year) < int(year_old):
                raise osv.except_osv('Validation Error !',
                                     'Employee must be older than or equal to %s years old !' % (year_old))
        return True
    
    def update_default_account_owner_name_bank(self, cr, uid, vals, context=None):
        """
        Update default owner account name (Unknown) in Bank Accounts = Employee Name in case create directly and user forget to set owner name
        """
        employee_name = vals.get('name', False)
        if employee_name and vals.get('bank_ids', False):
            for bank_data in vals.get('bank_ids', False):
                if len(bank_data) == 3 and bank_data[2].get('owner_name', '') == 'Unknown':
                    bank_data[2]['owner_name'] = employee_name
        
        return vals
            

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
#         vals.update({'code': self.generate_code(cr, uid, vals['company_group_id'], context)})
        self.validate_birthday(cr, uid, vals, context)
        # When create directly, create partner for it
        if not context.get('create_emp_from_candidate', False) and vals.get('name', False):
            # Create partner before create employee
            vals = self.create_partner(cr, uid, vals, context)
        
        if vals.get('name', False):
            vals = self.update_default_account_owner_name_bank(cr, uid, vals, context)
        
        if vals.get('mobile', False):
            vals['mobile_phone'] = vals['mobile']
        
        context['do_not_check_overlap_personal_document'] = True
        res_id = super(hr_employee, self).create(cr, uid, vals, context)
        
        if res_id:
            if vals.get('personal_document', False):
                employee = self.read(cr, uid, res_id, ['personal_document'])
                document_ids = employee.get('personal_document',[])
                document_pool = self.pool.get('vhr.personal.document')
                for document in document_pool.read(cr, uid, document_ids, ['employee_id','document_type_id','issue_date','expiry_date']):
                    employee_id = document.get('employee_id', False) and document['employee_id'][0] or False
                    document_type_id = document.get('document_type_id', False) and document['document_type_id'][0] or False
                    issue_date = document.get('issue_date', False)
                    expiry_date = document.get('expiry_date', False)
                    document_pool.check_overlap(cr, uid, employee_id, document_type_id, issue_date, expiry_date, [document['id']])
            
            #Update employee code after create to prevent auto increment number when have error during create employee
            is_turn_on = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_human_resource_code_turn_off_update_nearest_code') or 0
            valm = {}
            if is_turn_on in ['2','1']:
                valm ={'code': self.pool.get('ir.sequence').next_by_code_with_company_group(cr, uid, 'hr.employee.sequence', vals['company_group_id'])}
            else:
                valm = {'code': self.generate_code(cr, uid, vals['company_group_id'], context)}
             
            if valm:
                super(hr_employee, self).write(cr, uid, res_id, valm, context)
                
        
        # if res_id:
        #     if context.get('create_emp_from_candidate', False):
        #         interface = self.pool.get('vhr.ldap.interface')
        #         interface.ldap_create_employee(cr, uid, res_id, context=context)

        return res_id

    def write(self, cr, uid, ids, vals, context=None):
        if not context:
            context = {}
        
        if vals.get('mobile', False):
            vals['mobile_phone'] = vals['mobile']
            
#         if vals.has_key('company_group_id'):
#             vals.update({'code': self.generate_code(cr, uid, vals['company_group_id'], context)})
        self.validate_birthday(cr, uid, vals, context)
        res = False
        if ids:
            if not isinstance(ids, list):
                ids = [ids]
            employee = self.read(cr, SUPERUSER_ID, ids[0], ['address_home_id', 'name'])
            # Create partner_id if dont have partner_id
            if not employee.get('address_home_id', False):
                if not vals.get('name', False):
                    vals['name'] = employee.get('name', '')
                vals = self.create_partner(cr, uid, vals, context)
            elif vals.get('name', False):
                partner_id = employee['address_home_id'][0]
                self.pool.get('res.partner').write(cr, uid, [partner_id], {'name': vals['name']})
            
#             if not vals.get('code', False) and vals.get('company_group_id', False):
#                 company_group_id = vals.get('company_group_id', False)
#                 vals['code'] = self.generate_code(cr, uid, company_group_id, context)
                
            context['do_not_check_overlap_personal_document'] = True
            res = super(hr_employee, self).write(cr, uid, ids, vals, context=context)
            
            if res:
                if vals.get('personal_document', False):
                    employee = self.read(cr, uid, ids[0], ['personal_document'])
                    document_ids = employee.get('personal_document',[])
                    document_pool = self.pool.get('vhr.personal.document')
                    
                    for document in document_pool.read(cr, uid, document_ids, ['employee_id','document_type_id','issue_date','expiry_date']):
                        employee_id = document.get('employee_id', False) and document['employee_id'][0] or False
                        document_type_id = document.get('document_type_id', False) and document['document_type_id'][0] or False
                        issue_date = document.get('issue_date', False)
                        expiry_date = document.get('expiry_date', False)
                        document_pool.check_overlap(cr, uid, employee_id, document_type_id, issue_date, expiry_date, [document['id']])
            
            # if context.get('return_emp_from_candidate', False):
            # interface = self.pool.get('vhr.ldap.interface')
            #     interface.ldap_create_employee(cr, uid, ids[0], context=context)
        return res

    def create_partner(self, cr, uid, vals, context=None):
        vals_partner = {'name': vals['name']}
        vals_partner['street'] = vals.get('street', False)
        vals_partner['city'] = vals.get('city_id', False)
        vals_partner['district_id'] = vals.get('district_id', False)
        vals_partner['country_id'] = vals.get('partner_country_id', False)
        vals_partner['temp_address'] = vals.get('temp_address', False)
        vals_partner['temp_city_id'] = vals.get('temp_city_id', False)
        vals_partner['temp_district_id'] = vals.get('temp_district_id', False)
        vals_partner['phone'] = vals.get('phone', '')
        vals_partner['mobile'] = vals.get('mobile', '')
        vals_partner['email'] = vals.get('email', '')
        partner_id = self.pool.get('res.partner').create(cr, uid, vals_partner, context)
        if partner_id:
            vals['address_home_id'] = partner_id

        return vals

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(hr_employee, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar=toolbar,
                                                       submenu=submenu)
        if context is None:
            context = {}
        if view_type == 'form' and res['type'] == 'form':
            doc = etree.XML(res['arch'])
            for node in doc.xpath("//field[@name='place_of_birth']"):
                node.set('modifiers', json.dumps({'invisible': True}))
                node.set('invisible', '1')
            groups = self.pool.get('res.users').get_groups(cr, uid)
            if 'vhr_cb_profile' not in groups:
                for node in doc.xpath("//field[@name='join_date']"):
                    node.set('modifiers', json.dumps({'readonly': True}))
            res['arch'] = etree.tostring(doc)
        return res

    
hr_employee()