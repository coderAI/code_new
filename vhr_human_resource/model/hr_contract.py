# -*-coding:utf-8-*-
import logging
import datetime
import time

from datetime import datetime as datetimes
from datetime import date
from dateutil.relativedelta import relativedelta
from lxml import etree
import simplejson as json
from openerp import SUPERUSER_ID
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.osv import osv, fields
from openerp.addons.vhr_common.model.vhr_common import vhr_common
from openerp.tools.translate import _


log = logging.getLogger(__name__)

DRAFT = 'draft'
WAITING = 'waiting'
SIGNED = 'signed'
CANCEL = 'cancel'

translate_contract_to_wr_dict = {'employee_id': 'employee_id', 'company_id': 'company_id',
                                  'date_start': 'effect_from', 'office_id': 'office_id_new',
                                  'division_id': 'division_id_new', 'department_id': 'department_id_new','department_group_id': 'department_group_id_new',
                                  'title_id': 'job_title_id_new', 'report_to': 'report_to_new', 'team_id': 'team_id_new',
                                  'manager_id': 'manager_id_new', 'seat_no': 'seat_new', 'ext_no': 'ext_new',
                                  'work_email': 'work_email_new', #'mobile_phone': 'mobile_phone_new',
                                  'work_phone': 'work_phone_new', 'change_form_id': 'change_form_ids',
                                  'info_signer': 'signer_id', 'sign_date': 'sign_date','country_signer':'country_signer',
                                  'title_signer': 'signer_job_title_id', #'job_level_id': 'job_level_id_new',
#                                   'position_class_id': 'position_class_id_new',
                                  'timesheet_id':'timesheet_id_new','sub_group_id': 'pro_sub_group_id_new',
                                  'job_family_id': 'pro_job_family_id_new','job_group_id': 'pro_job_group_id_new',
                                  'ts_working_group_id': 'ts_working_group_id_new','salary_setting_id': 'salary_setting_id_new',
                                  'job_level_person_id': 'job_level_person_id_new','career_track_id': 'career_track_id_new'}

SIGNAL = {
    'draft_waiting':
        {'old_state': DRAFT, 'new_state': WAITING},
    'waiting_signed':
        {'old_state': WAITING, 'new_state': SIGNED},
    'draft_cancel':
        {'old_state': DRAFT, 'new_state': CANCEL},
    'waiting_cancel':
        {'old_state': WAITING, 'new_state': CANCEL},
    'signed_cancel':
        {'old_state': SIGNED, 'new_state': CANCEL},
    'waiting_draft':
        {'old_state': WAITING, 'new_state': DRAFT},
}


class hr_contract(osv.osv, vhr_common):
    _name = 'hr.contract'
    _inherit = 'hr.contract'

    def _count_attachment(self, cr, uid, ids, prop, unknow_none, context=None):
        ir_attachment = self.pool.get('ir.attachment')
        res = {}
        for item in ids:
            number = ir_attachment.search(cr, uid, [('res_id', '=', item), ('res_model', '=', self._name)], count=True)
            res[item] = number
        return res

    def _count_working_record(self, cr, uid, ids, prop, unknow_none, context=None):
        wkr_obj = self.pool.get('vhr.working.record')
        res = {}
        for item in ids:
            number = wkr_obj.search(cr, uid, [('contract_id', '=', item),
                                              ('state','in',['finish',False])], count=True)
            res[item] = int(number)
        return res

    def _get_contract_list(self, cr, uid, ids, field_name, arg, context=None):
        """
        
        Return True nếu đang có instance với date_end = False, hoặc contract đang thuộc 1 instance nào đó
        Cheat đối với trường hợp transfer từ RR thì đã tạo ra WR mặc dù contract ở state draft, 
           khi đó return True nếu contract hiện tại có date_Start = date_start của instance, để cho edit change_form_id đối với các contract transfer từ RR mà chưa signed
        """
        res = {}
        instance_obj = self.pool.get('vhr.employee.instance')
        for item in self.browse(cr, uid, ids,context=context):
            date_start = item.date_start
            res[item.id] = False
            if item.employee_id and item.company_id:
                active_instance_ids = instance_obj.search(cr, uid, [
                                        ('employee_id', '=', item.employee_id.id),
                                        ('company_id', '=', item.company_id.id),
                                        ('date_end', '=', False)])
                
                if date_start and not active_instance_ids:
                    active_instance_ids = instance_obj.search(cr, uid, [
                                                    ('employee_id', '=', item.employee_id.id),
                                                    ('company_id', '=', item.company_id.id),
                                                    ('date_start', '<=', date_start),
                                                    ('date_end','>=',date_start)])
                
                if active_instance_ids:
                    for instance in instance_obj.read(cr, uid, active_instance_ids, ['date_start','date_end']):
                        date_start_instance = instance.get('date_start', False)
                        date_end_instance = instance.get('date_end', False)
                        if date_start_instance == date_start and not date_end_instance and item.state in ['draft','waiting']:
                            active_instance_ids.remove(instance['id'])
                        
                res[item.id] = active_instance_ids and True or False
        return res

    def _is_edit_emp_comp(self, cr, uid, ids, field_name, arg, context=None):
        """
        # Only allow to edit employee-company in contract when list WR link to contract(dont count first WR) is empty
        #and dont have any contract same company in the future
        """
        if not context:
            context = {}
        res = {}
        contracts = self.read(cr, uid, ids, ['first_working_record_id', 'employee_id','company_id','date_start'],context=context)
        for contract in contracts:
            employee_id = contract.get('employee_id', False) and contract['employee_id'][0]
            company_id = contract.get('company_id', False) and contract['company_id'][0]
            date_start = contract.get('date_start', False)
            first_working_record_id = contract.get('first_working_record_id', False) and contract['first_working_record_id'][0]
            working_record_ids = self.pool.get('vhr.working.record').search(cr, uid,[('contract_id', '=', contract['id']),
                                                                                     ('state','in',['finish',False])])
            if first_working_record_id in working_record_ids:
                working_record_ids.remove(first_working_record_id)

            if working_record_ids:
                res[contract['id']] = False
            else:
                #search company in the future
                contract_ids = self.search(cr, uid, [('employee_id','=',employee_id),
                                                     ('company_id','=',company_id),
                                                     ('state','not in',['cancel']),
                                                     ('date_start','>=',date_start),
                                                     ('id','!=',contract['id'])])
                if contract_ids:
                    res[contract['id']] = False
                else:
                    res[contract['id']] = True

        return res

    def _check_is_on_probation(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        emp_inst_obj = self.pool.get('vhr.employee.instance')
        for item in self.browse(cr, uid, ids,context=context):
            res[item.id] = False
            if item.employee_id and item.company_id:
                active_instance_ids = self.pool.get('vhr.employee.instance').search(cr, uid, [
                    ('employee_id', '=', item.employee_id.id),
                    ('company_id', '=', item.company_id.id),
                    ('date_end', '=', False)])
                if active_instance_ids:
                    emp_inst = emp_inst_obj.browse(cr, uid, active_instance_ids[0], context=context)
                    inst_start_date = emp_inst.date_start
                    res[item.id] = self.check_last_contract_type_is_offer(cr, uid, [item.id], item.employee_id.id,
                                                                          item.company_id.id, inst_start_date,
                                                                          item.date_start,context=context)
        return res

    def _get_list_contract_type(self, cr, uid, ids, field_name, arg, context=None):
        if not context:
            context = {}
            
        res = {}
        for item in self.browse(cr, uid, ids,context=context):
            res[item.id] = False
            if item.employee_id and item.company_id:
                date_start = item.date_start
                context['date_start'] = date_start
                value = self.check_contract_type(cr, uid, [item.id], item.employee_id.id, item.company_id.id, context=context)
                res[item.id] = self.get_list_contract_type_id(cr, uid, value, context=context)

        return res

    def _check_permission(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if not ids:
            return True
        if not isinstance(ids, list):
            ids = [ids]
        for record_id in ids:
            res[record_id] = self.check_permission(cr, uid, [record_id], context=context)

        return res

    def check_last_contract_type_is_offer(self, cr, uid, ids, employee_id, company_id, inst_start_date, date_start, context=None):
        if not context:
            context = {}
        res = False
        context['filter_by_group'] = False
        contract_ids = self.search(cr, uid, [('date_start', '>=', inst_start_date), 
                                             ('date_start', '<=', date_start), 
                                             ('state', '=', 'signed'),
                                             ('employee_id', '=', employee_id), 
                                             ('company_id', '=', company_id), 
                                             ('id', 'not in', ids)], order='date_start desc,id desc', context=context)
        if contract_ids:
            old_contract = self.browse(cr, uid, contract_ids[0], context=context)
            if old_contract.type_id and old_contract.type_id.contract_type_group_id and old_contract.type_id.contract_type_group_id.code == '1':
                res = True
        return res

    def default_get(self, cr, uid, flds, context=None):
        if context is None:
            context = {}
        res = super(hr_contract, self).default_get(cr, uid, flds, context=context)
        wkr_obj = self.pool.get('vhr.working.record')
        emp_inst_obj = self.pool.get('vhr.employee.instance')
        #Call from renew contract
        if context.get('duplicate_active_id', False):
            #Khi renew HĐ thì "is_main" của HĐ mới sẽ lấy theo giá trị của HĐ cũ được chọn để renew
            new_res = self.copy_data(cr, uid, context['duplicate_active_id'])
            
            for key in res:
                if key not in new_res:
                    new_res[key] = res[key]
            
            emp_id = new_res.get('employee_id', False)
            company_id = new_res.get('company_id', False)
            if context.get('default_company_id', False):
                company_id = context['default_company_id']
                new_res['company_id'] = company_id
            
            if 'date_start_temp' in new_res:
                del new_res['date_start_temp']
            
            if 'renew_status' in new_res:
                del new_res['renew_status']
            
            wkr_ids = wkr_obj.search(cr, uid, [('employee_id', '=', emp_id), 
                                               ('company_id', '=', company_id), 
                                               ('state','in',[False,'finish']),
                                               ('active', '=', True)], order='effect_from desc', limit=1)
            val = {}
            if wkr_ids:
                wkr_res = wkr_obj.browse(cr, uid, wkr_ids[0], context=context)
                val['office_id'] = wkr_res.office_id_new and wkr_res.office_id_new.id or False
                val['division_id'] = wkr_res.division_id_new and wkr_res.division_id_new.id or False
                val['department_group_id'] = wkr_res.department_group_id_new and wkr_res.department_group_id_new.id or False
                val['department_id'] = wkr_res.department_id_new and wkr_res.department_id_new.id or False
                val['report_to'] = wkr_res.report_to_new and wkr_res.report_to_new.id or False
                val['job_level_person_id'] = wkr_res.job_level_person_id_new and wkr_res.job_level_person_id_new.id or False
                

            active_instance_ids = emp_inst_obj.search(cr, uid, [
                ('employee_id', '=', emp_id),
                ('company_id', '=', company_id),
                ('date_end', '=', False)])

            type_id = context.get('default_type_id', False)
            date_start = context.get('default_date_start', False)
            include_probation = context.get('default_include_probation', False)

            date_end = False
            if not context.get('default_date_start', False):
                if active_instance_ids:
                    emp_inst = emp_inst_obj.browse(cr, uid, active_instance_ids[0], context=context)
                    inst_start_date = emp_inst.date_start
                    contract_ids = self.search(cr, uid, [
                        ('date_start', '>=', inst_start_date), ('state', '=', 'signed'),
                        ('employee_id', '=', emp_id), ('company_id', '=', company_id),
                    ], order='date_start desc,id desc', context=context)
                    if contract_ids:
                        last_contract = self.browse(cr, uid, contract_ids[0], fields_process=['date_end', 'liquidation_date'])
                        if last_contract.liquidation_date:
                            date_end = last_contract.liquidation_date
                            
                            #If have liquidation date, next contract can start from liquidation_date
                            date_end = datetimes.strptime(date_end, DEFAULT_SERVER_DATE_FORMAT) - relativedelta(days=1)
                            date_end = date_end.strftime(DEFAULT_SERVER_DATE_FORMAT)
                        else:
                            date_end = last_contract.date_end
                if date_end:
                    date_start = datetimes.strptime(date_end, DEFAULT_SERVER_DATE_FORMAT) + relativedelta(days=1)
                    date_start = date_start.strftime(DEFAULT_SERVER_DATE_FORMAT)
            new_res.update(val)
            new_res['name'] = False
            new_res['type_id'] = type_id
            new_res['date_start'] = date_start
            new_res['date_end'] = context.get('default_date_end', False)
            new_res['date_end_temp'] = False
            new_res['sign_date'] = fields.date.context_today(self, cr, uid)
            new_res['audit_log_ids'] = False
            new_res['first_working_record_id'] = False
            new_res['change_form_id'] = False
            new_res['is_change_data_from_duplicate'] = True
            new_res['liquidation_date'] = False
            new_res['liquidation_reason'] = False
            new_res['job_applicant_id'] = False
            new_res['is_edit_emp_comp'] = True
            new_res['job_level_id'] = False
            new_res['include_probation'] = include_probation
            new_res['state_log_ids'] = []
            new_res['appendix_ids'] = []
            new_res['inviter_id'] = False
            new_res.update({'mail_to_remind': '', 'is_invited': False, 'number_of_invited': 0,
                            'last_date_invited':False, 'is_delivered': False, 'delivery_id': False,
                            'delivery_note': '', 'holder_id': False, 'delivery_date': False,
                            'is_received': False, 'receiver_id': False, 'received_date': False,
                            'is_signed_by_emp': False, 'time_meet_user_sign_contract': '',
                            'day_meet_user_sign_contract': ''
                            })
            return new_res

        return res
    
    def _is_able_to_create_contract(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if not isinstance(ids, list):
            ids = [ids]
        
        for record_id in ids:
            res[record_id] = True
        return res
    
    def _is_created(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if not isinstance(ids, list):
            ids = [ids]
        
        for record_id in ids:
            res[record_id] = True
        return res
    
    def _is_show_sub_type(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if not isinstance(ids, list):
            ids = [ids]
        
        subtype_pool = self.pool.get('hr.contract.sub.type')
        
        for record in self.browse(cr, uid, ids, fields_process=['type_id']):
            contract_type_group_id = record.type_id and record.type_id.contract_type_group_id and record.type_id.contract_type_group_id.id or False
            type_id = record.type_id and record.type_id.id or False
            
            subtype_ids = subtype_pool.search(cr, uid, ['|',('contract_type_group_id','=',contract_type_group_id),
                                                            ('contract_type_id','=',type_id)])
            
            if subtype_ids:
                res[record.id] = True
            else:
                res[record.id] = False
        return res    
    
    def _check_contract_extension_appendix(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if not isinstance(ids, list):
            ids = [ids]
        
        for record in self.read(cr, uid, ids, ['date_end_temp','date_end']):
            res[record['id']] = {'date_end_func': False}
            if record.get('date_end_temp', False):
                res[record['id']]['date_end_func'] = record.get('date_end', False)
                res[record['id']]['is_have_extension_appendix'] = True
            else:
                res[record['id']]['is_have_extension_appendix'] = False
        
        return res
    
    def _number_of_appendix(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if not isinstance(ids, list):
            ids = [ids]
        
        for record in self.read(cr, uid, ids, ['appendix_ids']):
            appendix_ids = record.get('appendix_ids', [])
            res[record['id']] = len(appendix_ids)
        
        return res
        
    def _is_show_working_salary(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if not isinstance(ids, list):
            ids = [ids]
        
        code_show_salary = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_human_resource_contract_type_group_code_show_working_salary_in_contract') or ''
        code_show_salary = code_show_salary.split(',')
        
        for record in self.browse(cr, uid, ids, fields_process=['type_id']):
            res[record.id] = False
            contract_type_group_code = record.type_id and record.type_id.contract_type_group_id and record.type_id.contract_type_group_id.code or False
            if contract_type_group_code in code_show_salary:
                res[record.id] = True
        
        return res
    
    def _check_is_latest(self, cr, uid, ids, field_name, arg, context=None):
        """
        Get contract is latest of an employee at state signed
        """
        res = {}
        if not isinstance(ids, list):
            ids = [ids]
        
        for record in self.read(cr, uid, ids, ['employee_id','date_start_real','state']):
            res[record['id']] = False
            if record.get('state', False) == 'signed':
                employee_id = record.get('employee_id', False) and record['employee_id'][0]
                date_start_real = record.get('date_start_real', False)
                greater_ids = self.search(cr, uid, [('state','=','signed'),
                                                    ('employee_id','=',employee_id),
                                                    ('date_start_real','>',date_start_real)])
                if not greater_ids:
                    res[record['id']] = True
        
        return res
    
    def _check_is_require_job(self, cr, uid, ids, field_name, arg, context=None):
        """
        Only require for official employee from 1-1-2016
        Use to check whether contract is official or not official (remember this function apply start time from 1-1-2016)
        """
        res = {}
        for record_id in ids:
            is_require = False
            contract = self.perm_read(cr, SUPERUSER_ID, [record_id], context)[0]
            create_date = contract.get('create_date', False) and contract.get('create_date', False)[:10]
            if create_date:
                point_date = date(2016, 1, 1).strftime('%Y-%m-%d')
                if self.compare_day(point_date, create_date) >= 0:
                    contract = self.browse(cr, uid, record_id, fields_process=['type_id'])
                    if contract and contract.type_id and contract.type_id.contract_type_group_id and contract.type_id.contract_type_group_id.is_offical:
                        is_require=True
                    
            res[record_id] = is_require
        
        return res
    
    def _get_deadline_sign_contract(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for record in self.read(cr, uid, ids, ['last_date_invited']):
            res[record['id']] = False
            last_day_invited = record.get('last_date_invited',False)
            if last_day_invited:
                last_day_invited = datetimes.strptime(last_day_invited, DEFAULT_SERVER_DATE_FORMAT)
                deadline = last_day_invited + relativedelta(days=7)
                res[record['id']] = deadline.strftime('%d/%m/%Y')
            
        return res
    
    def _get_remind_sign_contract(self, cr, uid, ids, field_name, args, context=None):
        res = {}
        for record in self.read(cr, uid, ids, ['number_of_invited']):
            res[record['id']] = record.get('number_of_invited',0) - 1
        
        return res
    
    
    def _is_created_from_renew_contract(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        renew_detail_obj = self.pool.get('vhr.multi.renew.contract.detail')
        for record_id in ids:
            res[record_id] = False
            renew_detail_ids = renew_detail_obj.search(cr, uid, [('new_contract_id','=',record_id)])
            if renew_detail_ids:
                res[record_id] = True
        
        return res
    
    def fnct_search_is_latest_contract(self, cr, uid, obj, name, args, context=None):
        if not args:
            return []
        
        res = []
        domain = []
            
        #Search contract_id have max date_start of each employee and state=signed
        sql = """
                SELECT a.id FROM hr_contract a inner join 
                        (select employee_id, max(date_start_real) date_start_real from hr_contract where state='signed' group by employee_id) b
                    ON a.employee_id = b.employee_id and a.date_start_real=b.date_start_real
                WHERE a.state='signed'
              """
        
        cr.execute(sql)
        res = cr.fetchall()
        contract_ids = [item[0] for item in res]
        domain.extend(('id','in',contract_ids))
        
        operator = 'in'
        for field, oper, value in args:
            if oper == '!=' and value == True:
                operator = 'not in'
                break
            elif oper == '==' and value == False:
                operator = 'not in'
                break
            
        if not res:
            return [('id', '=', 0)]
        return [('id',operator, res)]
        
        
        
    _columns = {
        'company_id': fields.many2one('res.company', 'Entity'),
        'company_code': fields.related('company_id', 'code', type='char', string='Entity'),
        'info_signer': fields.char("Signer"),
        'sign_date': fields.date('Sign Date'),
        'title_signer': fields.char("Signer's Title"),
        'country_signer': fields.many2one('res.country', "Signer's Nationality"),
        
        'report_to': fields.many2one('hr.employee', 'Reporting line', domain="[('id','!=', employee_id)]",
                                     ondelete='restrict'),
        'date_start': fields.date('Effective Date', required=True),
        'date_end': fields.date('Expired Date'),
        'liquidation_date': fields.date('Liquidation Date'),
        'date_start_temp': fields.date('Temp Effective Date'),#This field use to calculate date_end in case check include probation
        'date_start_real': fields.date('Real Effective Date'),#This field use for migrate to vHCS, save real date_start of contract
        'date_end_temp': fields.date('Temp Expired Date'),#This field save date_end before have appendix contract (date_end_temp alway <= date_end)
#         'old_liquidation_date': fields.date('Old Liquidation Date'),
        
        'liquidation_reason': fields.text('Reason'),
        'partner_id': fields.related('employee_id', 'address_home_id', type='many2one', relation='res.partner',
                                     string='Partner'),
        'emp_code': fields.related('employee_id', 'code', type='char', string='Employee Code'),
        # Working
        'title_id': fields.many2one('vhr.job.title', 'Job Title', ondelete='restrict'),
        'job_level_id': fields.many2one('vhr.job.level', 'Level', ondelete="restrict"),
        
         #New job level
        'job_level_position_id': fields.many2one('vhr.job.level.new', 'Position Level', ondelete='restrict'),
        'job_level_person_id': fields.many2one('vhr.job.level.new', 'Person Level', ondelete='restrict'),
        
         #LuanNG: Remove this field in future version of vHRS
        'position_class_id': fields.many2one('vhr.position.class', 'Position class'),
        'job_type_id': fields.many2one('vhr.dimension', 'Job Type', ondelete='restrict',
                                       domain=[('dimension_type_id.code', '=', 'JOB_TYPE'), ('active', '=', True)]),
        'division_id': fields.many2one('hr.department', 'Business Unit', ondelete='restrict',
                                       domain=[('organization_class_id.level', '=', 1)]),
        'department_group_id': fields.many2one('hr.department', 'Department Group', domain=[('organization_class_id.level','=', 2)], 
                                               ondelete='restrict'),    
        'department_id': fields.many2one('hr.department', 'Department', ondelete='restrict'),
        'team_id': fields.many2one('hr.department', 'Team', ondelete='restrict'),
        'manager_id': fields.many2one('hr.employee', string='Dept Head'),
        'complete_code': fields.related('department_id', 'complete_code', type='char', string='Department'),
        'office_id': fields.many2one('vhr.office', 'Office', ondelete='restrict'),
        'office_code': fields.related('office_id', 'code', type='char', string='Office'),
        'ext_no': fields.char('Ext', size=32),
        'seat_no': fields.char('Seat No', size=32),
        'organization_class_id': fields.related('department_id', 'organization_class_id', type='many2one',
                                                relation='vhr.organization.class', string='Organization Class',
                                                store=True),
        'work_phone': fields.char('Office phone', size=32, readonly=False),#remove in future code
        'mobile_phone': fields.char('Cell phone', size=32, readonly=False),#remove in future code
        'work_email': fields.char('Working email', size=240),#remove in future code
        'bank_account_ids': fields.one2many('vhr.bank.contract', 'contract_id', 'Bank Account Number',
                                            help="Employee bank salary account", ondelete='restrict'),
        'mission_ids': fields.one2many('vhr.mission.collaborator.contract', 'contract_id', string='Responsibilities'),
        'result_ids': fields.one2many('vhr.result.collaborator.contract', 'contract_id', string='Results'),
        'attachment_count': fields.function(_count_attachment, type='integer', string='Attachments'),
        'contract_terms': fields.text('Note'),
        # TODO: confirm use or not
        'salaries': fields.one2many('vhr.salary.contract', 'contract_id', string='Salary Informations'),
                # Logs State Change
        'state_log_ids': fields.one2many('vhr.state.change', 'res_id', 'History', domain=[('model', '=', _name)]),

        'wage': fields.float('Wage', digits=(16, 2), help="Basic Salary of the employee"),
        'contract_duration': fields.integer('Contract Duration'),
        'first_working_record_id': fields.many2one('vhr.working.record', 'First Working Record'),
        'change_form_id': fields.many2one('vhr.change.form', 'Add To Working Record', ondelete='restrict'),

        'create_uid': fields.many2one('res.users', 'Create User'),
        'create_user': fields.related('create_uid', 'login', type="char", string="Create User"),
        'create_date': fields.date('Create Date'),

        'write_uid': fields.many2one('res.users', 'Update User'),
        'write_user': fields.related('write_uid', 'login', type="char", string="Update User"),
        'write_date': fields.date('Update Date'),
        'is_existing_contract': fields.function(_get_contract_list, type='boolean', string='Is Existing Contract'),
        'is_edit_emp_comp': fields.function(_is_edit_emp_comp, type='boolean', string='Can Edit Employee and Company'),
        # This field only use when duplicate to be sure all data will be duplicate
        'is_change_data_from_duplicate': fields.boolean('Is Change Data From Duplicate'),
        'state': fields.selection([
            ('draft', 'Draft'), ('waiting', 'Waiting Sign'),
            ('signed', 'Signed'), ('cancel', 'Cancelled'),
        ], 'Status', readonly=True),
        'type_id': fields.many2one('hr.contract.type', "Contract Type", required=True),
        
        'contract_type_code': fields.related('type_id', 'code', type='char', string='Contract Type Code', store=True),
        'name': fields.char('Contract number', size=64, required=True),

        'contract_type_group_id': fields.related('type_id', 'contract_type_group_id', readonly=True, type='many2one',
                                                 relation='hr.contract.type.group', string='Contract Type Group'),
        'is_official': fields.related('contract_type_group_id', 'is_offical', type='boolean', string='Is Official'),
        'include_probation': fields.boolean('Include Probation'),
        'total_wkr': fields.function(_count_working_record, type='integer', string='Total Working Record'),
        'is_on_probation': fields.function(_check_is_on_probation, type='boolean', string='Is on probation'),
        'list_contract_type_id': fields.function(_get_list_contract_type, type='char', string='List Contract Type'),
        'is_readonly': fields.function(_check_permission, type='boolean', string='Is Readonly', multi='permission'),
        'is_hrbp_editable': fields.function(_check_permission, type='boolean', string="Is HRBP Editable", multi='permission'),
        'can_renew': fields.function(_check_permission, type='boolean', string='Can Renew', multi='permission'),#currently only use for salary view
        'renew_status': fields.selection([('renew', 'Renew'), ('reject', 'Reject'), ('pending', 'Pending')], 'Renew Status'),
        'is_able_to_create_contract': fields.function(_is_able_to_create_contract, type='boolean', string='Is Able To Create Contract'),
        'is_created': fields.function(_is_created, type='boolean', string='Is Created'),
        'is_main': fields.boolean('Is Main'),
        'working_time': fields.text('Working time'),
        'working_address': fields.char('Working Address', size=250),
        'working_salary': fields.text("Working Salary"),
        'is_show_working_salary': fields.function(_is_show_working_salary, type='boolean', string="Is Show Working Salary"),
        
        'salary_setting_id': fields.many2one('vhr.salary.setting', 'Payroll', ondelete='restrict'),
        
        'is_show_sub_type': fields.function(_is_show_sub_type, type='boolean', string="Is Show Sub Type"),
        'sub_type_id': fields.many2one('hr.contract.sub.type', "Sub Type", ondelete='restrict'),
        'appendix_ids': fields.one2many('vhr.appendix.contract', 'contract_id', 'Appendix Contract', ondelete='restrict'),
        'job_description': fields.text('Job Description'),
        
        'is_have_extension_appendix': fields.function(_check_contract_extension_appendix, type='boolean', string="Extension appendix contract", multi='appendix'),
        'date_end_func': fields.function(_check_contract_extension_appendix, type='date', string="Appendix Contract To Date", multi='appendix'),
        'number_of_appendix': fields.function(_number_of_appendix, type='integer', string="Number of Appendix"),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                 domain=[('object_id.model', '=', _inherit),
                                         ('field_id.name', 'not in', ['write_date', 'audit_log_ids','write_uid','write_user','state_log_ids',
                                                                      'date_start_real','date_start_temp','date_end_temp','temp_salary_percentage',
                                                                      'list_contract_type_id'])]),
        
        'job_family_id': fields.many2one('vhr.job.family','Job Family',ondelete='restrict',domain=[('track_id.code','=', 'Professional')]),
        'job_group_id': fields.many2one('vhr.job.group','Job Group',ondelete='restrict'),
        'sub_group_id': fields.many2one('vhr.sub.group','Sub Group',ondelete='restrict'),
        
        'is_latest' : fields.function(_check_is_latest, type='boolean', string='Is Latest', readonly = 1, fnct_search=fnct_search_is_latest_contract),
        
        #Sử dụng field này để xác định hd có phải là official hay ko  (tu 1-1-2016)
        'is_require_job_family': fields.function(_check_is_require_job, type='boolean', string='Is Require Job Family'),
        'career_track_id': fields.many2one('vhr.dimension', 'Career Track', domain=[('dimension_type_id.code','=','CAREER_TRACK')], ondelete='restrict'),
        
        #Field for sign-send email
        'inviter_id': fields.many2one('hr.employee', 'Inviter', ondelete='restrict'),
        'mail_to_remind': fields.char('Mail To'),
        'is_invited': fields.boolean('Is Invited'),#Is Send Mail
        'number_of_invited': fields.integer('Number of invited'),#Number of time send mail
        'last_date_invited': fields.date('Last day of Invited'),
        'deadline_sign_contract': fields.function(_get_deadline_sign_contract, type='char', string='Deadline'),
        'is_delivered': fields.boolean('Is Delivered'),
        'delivery_id': fields.many2one('hr.employee', 'Delivery Person', ondelete='restrict'),
        'delivery_note': fields.text('Delivery Note'),
        'holder_id': fields.many2one('hr.employee','Holder', ondelete='restrict'),
        'delivery_date': fields.date('Delivery Date'),
        'is_received': fields.boolean('Is Received'),
        'receiver_id': fields.many2one('hr.employee', 'Receiver', ondelete='restrict'),
        'received_date': fields.date('Received Date'),
        'is_signed_by_emp': fields.boolean('Is Signed By Employee'),
        'time_meet_user_sign_contract': fields.char('Time Meet User To Sign Contract'),
        'day_meet_user_sign_contract': fields.char('Day Meet User To Sign Contract'),
        'remind_sign_time': fields.function(_get_remind_sign_contract, type='char', string='Remind Sign Time'),
        
        'is_created_from_renewal_contract': fields.function(_is_created_from_renew_contract, type='boolean', 
                                                            string='Is Created From Renewal Contract'),
        
        'date_change_state_to_signed': fields.date('Date Change State To Signed')
    }

    _order = "date_start desc,date_end desc"

    def _get_default_company_id(self, cr, uid, context=None):
        company_ids = self.pool.get('res.company').search(cr, uid, [('is_member', '=', False)], order="id asc")
        if company_ids:
            return company_ids[0]

        return False
    
    def _get_is_able_to_create_contract(self, cr, uid, context=None):
        if not context:
            context = {}
            
        if context.get('create_directly_from_contract', False):
            groups = self.pool.get('res.users').get_groups(cr, uid)
            if 'vhr_cb_contract' not in groups:
                raise osv.except_osv('Warning !', "You have to belong to group C&B Contract to create contract !")

        return True
    

    _defaults = {
        'company_id': _get_default_company_id,
        'is_change_data_from_duplicate': False,
        'is_existing_contract': True,
        'is_edit_emp_comp': True,
        'state': 'draft',
        'sign_date': fields.date.context_today,
        'is_able_to_create_contract': _get_is_able_to_create_contract,
        'is_created': False,
        'can_renew': True,
        'date_start': False,
        'is_hrbp_editable': True,
#         'is_main': False,
    }
    
    def check_generate_code(self, cr, uid, type_id, employee_id, date_start, company_id=None, ids=[], context=None):
        if not ids:
            return True
        if not isinstance(ids, list):
            ids = [ids]
        contract_type = self.pool.get('hr.contract.type')
        type_group = contract_type.browse(cr, uid, type_id).contract_type_group_id.id
        date_start = datetime.datetime.strptime(date_start, DEFAULT_SERVER_DATE_FORMAT)
        for item in self.browse(cr, uid, ids):
            if item.type_id.contract_type_group_id.id != type_group:
                return True
            if item.employee_id.id != employee_id:
                return True
            item_start = datetime.datetime.strptime(item.date_start, DEFAULT_SERVER_DATE_FORMAT)
            if item_start.year != date_start.year:
                return True
            elif item_start.month != date_start.month:
                return True
        return False
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(hr_contract, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar=toolbar,submenu=submenu)
        if context is None:
            context = {}
        
        special_group = ['vhr_cb_contract','vhr_assistant_to_hrbp']
        doc = etree.XML(res['arch'])
        groups = self.pool.get('res.users').get_groups(cr, uid)
        if view_type == 'form':
            
            if res['type'] == 'form':
                if context.get('ACTION_NAME', False) and context.get('active_id', False):
                    node = doc.xpath("//form/separator")
                    if node:
                        node = node[0].getparent()
                        if context.get('required_comment', False):
                            node_notes = etree.Element('field', name="action_comment", colspan="4", modifiers=json.dumps({'required' : True}))
                        else:
                            node_notes = etree.Element('field', name="action_comment", colspan="4")
                        node.append(node_notes)

                        for node in doc.xpath("//button[@is_save_button='True']"):
                            node.set('name', context['ACTION_NAME'])

                        res['arch'] = etree.tostring(doc)
                        res['fields'].update({'action_comment': {'selectable': True, 'string': 'Action Comment', 'type':'text', 'views': {}}})
                        
                #Only Cb_contract can edit Contract
                #allow hrbp edit job description in Contract
                
                if not set(special_group).intersection(set(groups)):
                    for node in doc.xpath("//form"):
                        node.set('create',  '0')
                        node.set('edit',  '0')
                        
        elif view_type == 'tree':
            if res['type'] == 'tree':
                #Only Cb_contract can edit Contract
                #allow hrbp edit job description in Contract
                if not set(special_group).intersection(groups):
                    for node in doc.xpath("//tree"):
                        node.set('create',  '0')
                        node.set('edit',  '0')
                
        
        res['arch'] = etree.tostring(doc)
                
        return res

    def action_open_window_ex(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        view_id = 'vhr_contract_submit_comment_form'
        context['validate_read_hr_contract'] = False
        return {
            'name': 'Comments',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.pool.get('ir.model.data').get_object_reference(cr, uid, 'vhr_human_resource', view_id)[1],
            'res_model': self._name,
            'context': context,
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'res_id': ids[0],
        }

    def button_set_to_draft(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'draft'}, context=context)

    def button_set_to_waiting(self, cr, uid, ids, context=None):
        res = self.write(cr, uid, ids, {'state': 'waiting'}, context=context)
        self.check_to_create_working_record(cr, uid, ids, context)
        
        return res

    def button_set_to_signed(self, cr, uid, ids, context=None):
        # Create working record, payroll when create contract, set effect_from = date_start
        if not context:
            context = {}
        
        today = fields.date.context_today(self, cr, uid)
        res = self.write(cr, uid, ids, {'state': 'signed',
                                        'date_change_state_to_signed': today}, context=context)
        
        self.check_to_create_working_record(cr, uid, ids, context)
        self.check_to_active_user(cr, uid, ids, context)
        self.check_to_send_mail_input_emp_data(cr, uid, ids, context)
        return res
    
    def button_set_to_return(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'draft'}, context=context)

    def check_to_create_working_record(self, cr, uid, ids, context=None):
        if not context:
            context = {}
            
        config_parameter = self.pool.get('ir.config_parameter')
        working_pool = self.pool.get('vhr.working.record')
        
        change_local_comp_code = config_parameter.get_param(cr, uid, 'vhr_master_data_change_local_company') or ''
        change_local_comp_code = change_local_comp_code.split(',')
        for item in self.browse(cr, uid, ids):
            employee_id = item.employee_id and item.employee_id.id or False
            company_id = item.employee_id and item.company_id.id or False
            change_form_id = item.change_form_id and item.change_form_id.id or False
            effect_from = item.date_start or False
            if not item.first_working_record_id:
                if item.change_form_id and item.change_form_id.code in change_local_comp_code:
                    context['do_not_update_annual_day'] = True
                
                context['signed_contract'] = item.id
                context['include_not_signed_contract'] = True
                if change_form_id:
                    
                    working_ids = working_pool.search(cr, uid, [('employee_id','=',employee_id),
                                                                ('company_id','=',company_id),
                                                                ('effect_from','=',effect_from),
                                                                ('change_form_ids','=',change_form_id),
                                                                ('state','in',[False,'finish'])])
                    if len(working_ids):
                        #Case working record created before contract from vHCS, we need to update first_working_record_id in contract
                        super(hr_contract, self).write(cr, uid, item.id, {'first_working_record_id': working_ids[0]})
                        
                        contract = self.read(cr, uid, item.id, ['employee_id', 'company_id', 'first_working_record_id','date_start','effect_salary_id'])
                        effect_salary_id = contract.get('effect_salary_id', False) and contract['effect_salary_id'][0]
                        
                        create_vals = context.get('create_vals', {})
                        if 'change_form_id' in create_vals:
                            del create_vals['change_form_id']
                        
                        #Update payroll_salary_id in WR if created when create contract
                        val_wr = {'contract_id': item.id}
                        if effect_salary_id:
                            val_wr['payroll_salary_id'] = effect_salary_id
                        
                        working_pool.write(cr, uid, working_ids[0], val_wr)
                        self.update_working_record(cr, uid, item.id, create_vals, contract, context)
                    else:
                        self.create_working_record(cr, uid, [item.id], {}, context)
                
                elif context.get('force_create_working_record', False):
                    #Even when dont have change_form_id , have to create WR when transfer from RR, -_-
                    self.create_working_record(cr, uid, [item.id], {}, context)
                
            
            if change_form_id and item.change_form_id.code in change_local_comp_code:
                self.create_termination_agreement_contract(cr, uid, item, context)
            
            if item.state == 'signed' and change_form_id and item.change_form_id.code in change_local_comp_code:
                #If contract create with change form "chuyển đổi công ty", 
                #create working record with type "chuyển đổi cty(xử lý thôi việc)" for other active contract
                self.create_local_terminate_working_record(cr, uid, item, context)
                
                self.pool.get('vhr.working.record').check_to_update_annual_day(cr, uid, employee_id, company_id)
                    
        return True

    # Active user when signed contract
    def check_to_active_user(self, cr, uid, ids, context):
        if context is None:
            context = {}
        contracts = self.browse(cr, uid, ids, context=context)
        res_users = self.pool['res.users']
        change_form = self.pool['vhr.change.form']
        config_obj = self.pool['ir.config_parameter']
        change_form_code = []
        change_form_ids = []
        user_ids = []
        # return and change contract type from 
        for code in ('vhr_master_data_back_to_work_change_form_code', 'vhr_change_form_collaborator_code'):
            code_val = config_obj.get_param(cr, uid, code) or ''
            if code_val != '':
                change_form_code.append(code_val)
        
        if change_form_code:
            change_form_ids = change_form.search(cr, uid, [('code', 'in', change_form_code)], context=context)
        for contract in contracts:
            if change_form_ids and contract.change_form_id and contract.change_form_id.id in change_form_ids:
                user = contract.employee_id and \
                    contract.employee_id.resource_id and \
                    contract.employee_id.resource_id.user_id or False
                if user and user.active == False:
                    user_ids.append(user.id)
        if user_ids:
            self.pool['res.users'].write(cr, uid, user_ids, {'active': True}, context=context)
    
    
    def get_change_form_need_to_send_email_input_emp_data(self, cr, uid, context=None):
        config_parameter = self.pool.get('ir.config_parameter')
        input_code = config_parameter.get_param(cr, uid, 'vhr_master_data_input_data_into_iHRP') or ''
        input_code_list = input_code.split(',')
        
        back_code = config_parameter.get_param(cr, uid, 'vhr_master_data_back_to_work_change_form_code') or ''
        back_code_list = back_code.split(',')
        
        codes = input_code_list + back_code_list
        
        change_form_ids = self.pool.get('vhr.change.form').search(cr, uid, [('code','in',codes)])
        return change_form_ids
    
    def check_to_send_mail_input_emp_data(self, cr, uid, ids, context=None):
        """
        Gửi email cho nhân viên yêu cầu nhập thông tin thay đổi trên mysite, nếu nhân viên mới vào cty/ quay lại làm việc 
        """
        if ids:
            mail_template = 'vhr_human_resource_hr_contract_send_mail_annouce_input_emp_data'
            email_cc = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_human_resource_cc_email_input_emp_data_when_join_company') or ''
            allow_form_ids = self.get_change_form_need_to_send_email_input_emp_data(cr, uid, context)
            for contract in self.browse(cr, uid, ids):
                change_form_id = contract.change_form_id and contract.change_form_id.id or False
                if change_form_id in allow_form_ids:
                    emp_email = contract.employee_id and contract.employee_id.work_email or ''
                    title_gender = 'Anh/chị'
                    gender = contract.employee_id and contract.employee_id.gender or ''
                    if gender == 'male':
                        title_gender = 'Anh'
                    elif gender:
                        title_gender = 'Chị'
                    
                    date_change_state_to_signed = contract.date_change_state_to_signed
                    date_change_state_to_signed = datetimes.strptime(date_change_state_to_signed, DEFAULT_SERVER_DATE_FORMAT)
                    next_5days = date_change_state_to_signed + relativedelta(days=5)
                    next_5days = next_5days.strftime('%d-%m-%Y')
                    vals = {'contract_id': contract['id'],
                            'email_to': emp_email,
                            'email_cc': email_cc,
                            'subject_element_name': title_gender,
                            'date': next_5days}
                    
                    self.pool.get('vhr.sm.email').send_email(cr, uid, mail_template, vals, context)
                    
        return True
    
    def send_mail_remind_input_emp_data(self, cr, uid, context=None):
        """
        Nếu nhân viên vào công ty hoặc quay lại làm việc nhưng sau 5 ngày kể từ khi gửi mail yêu cầu nhập thông tin trên mysite, 
        vẫn chưa submit thông tin thay đổi trên mysite thì gửi email remind 
        """
        temp_obj = self.pool.get('vhr.employee.temp')
        mail_template = 'vhr_human_resource_hr_contract_send_mail_remind_annouce_input_emp_data'
        email_cc = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_human_resource_cc_email_input_emp_data_when_join_company') or ''
        allow_form_ids = self.get_change_form_need_to_send_email_input_emp_data(cr, uid, context)
        
        today = fields.date.context_today(self, cr, uid)
        today = datetimes.strptime(today, DEFAULT_SERVER_DATE_FORMAT)
        previous_5days = today - relativedelta(days=5)
        today = today.strftime('%d-%m-%Y')
        contract_ids = self.search(cr, uid, [('state','=','signed'),
                                             ('date_change_state_to_signed','=',previous_5days),
                                             ('change_form_id','in',allow_form_ids)])
        if contract_ids:
            for contract in self.read(cr, uid, contract_ids, ['employee_id']):
                employee_id = contract.get('employee_id', False) and contract['employee_id'][0]
                if employee_id:
                    #Check if submit changed data in mysite
                    temp_ids = temp_obj.search(cr, uid, [('employee_id','=', employee_id),
                                                         ('state','in',['waiting','verified'])])
                    if not temp_ids:
                        emp = self.pool.get('hr.employee').read(cr, uid, employee_id, ['work_email','gender'])
                        emp_email = emp.get('work_email','')
                        
                        title_gender = 'Anh/chị'
                        gender = emp.get('gender','')
                        if gender == 'male':
                            title_gender = 'Anh'
                        elif gender:
                            title_gender = 'Chị'
                        vals = {'contract_id': contract['id'],
                            'email_to': emp_email,
                            'email_cc': email_cc,
                            'subject_element_name': title_gender,
                            'date':today}
                    
                        self.pool.get('vhr.sm.email').send_email(cr, uid, mail_template, vals, context)
        
        return True

    def button_set_to_cancel_waiting(self, cr, uid, ids, context=None):
        return self.button_set_to_cancel_signed(cr, uid, ids, context)
        
    def button_set_to_cancel_signed(self, cr, uid, ids, context=None):
        """
        Delete WR link to contract.
        Delete working schedule employee - timesheet employee - payroll salary in duration of contract(when employee have only one contract at that time)
        Update is_reject = True in hr.employee when employee dont have any contract at other company and this contract have change form: gia nhap cty, back to work

        """
        if context is None:
            context = {}
        context.update({'update_from_contract': True})
        wkr_obj = self.pool.get('vhr.working.record')
        
        # Unlink Working Record, PR
        for contract_id in ids:
            res_contract = self.browse(cr, uid, contract_id, context=context)
            emp_id = res_contract.employee_id and res_contract.employee_id.id or None
            company_id = res_contract.company_id and res_contract.company_id.id or None
            change_form_id  = res_contract.change_form_id and res_contract.change_form_id.id or False
            date_start = res_contract.date_start
            date_end = res_contract.date_end
            
            date_start_real = res_contract.date_start_real
            if not date_start_real:
                if not res_contract.include_probation:
                    date_start_real = date_start
                elif res_contract.date_start_temp:
                    date_start_temp = res_contract.date_start_temp
                    date_start_real = datetimes.strptime(date_start_temp, DEFAULT_SERVER_DATE_FORMAT) + relativedelta(days=1)
                    date_start_real = date_start_real.strftime(DEFAULT_SERVER_DATE_FORMAT)
                else:
                    date_start_real = date_start
            
            # if len(contract_ids) == 1:
                # ldap delete account domain

            #Delete WR
            #TODO: When cancel contract in the past only have 1 WR, what will you do ? -_-
            wkr_ids = wkr_obj.search(cr, uid, [('contract_id', '=', contract_id),
                                               ('state','in',[False, 'finish'])], context=context)
            
            if len(wkr_ids) <= 1:
                try:
                    #Find WR termination local create from contract with change form change local company
                    local_termination_wr_ids = wkr_obj.search(cr, uid, [('contract_id_change_local_company','=',contract_id)])
                    wkr_ids.extend(local_termination_wr_ids)
                    
                    wkr_obj.unlink(cr, uid, wkr_ids, context=context)
                except Exception as e:
                    log.exception(e)
                    try:
                        error_message = e.message
                        if not error_message:
                            error_message = e.value
                    except:
                        error_message = ""
                    raise osv.except_osv('Error !',
                        'Error when delete working record link to contract: \n %s'% error_message)
            else:
                raise osv.except_osv('Validation Error !', 'Cannot cancel contract with more than 1 working record!')
            
            #Cancel all staff movement not finish
            sm_ids = wkr_obj.search(cr, uid, [('contract_id','=',contract_id),
                                              ('state','not in',[False,'finish','cancel'])], context=context)
            if sm_ids:
                mcontext ={'ACTION_COMMENT': 'Reject when cancel contract'}
                
                from vhr_working_record import STATES_ALL
                list_dict_states = {item[0]: item[1] for item in STATES_ALL}
                for record in wkr_obj.read(cr, uid, sm_ids, ['state']):
                    old_state = record.get('state', False)
                    wkr_obj.write_log_state_change(cr, uid, record['id'], list_dict_states[old_state], list_dict_states['cancel'], mcontext)
                
                wkr_obj.write(cr, uid, sm_ids, {'state': 'cancel'})
            
            ter_ids = self.pool.get('vhr.termination.request').search(cr, uid, [('contract_id','=', contract_id),
                                                                                ('state','not in',[False,'cancel'])])
            if ter_ids:
                raise osv.except_osv('Validation Error !', 'Cannot cancel contract linked to exist Termination [{}] !'.format(ter_ids))
            
            #Delete termination agreement
            agreement_pool = self.pool.get('vhr.termination.agreement.contract')
            agreement_ids = agreement_pool.search(cr, uid, [('new_contract_id','=',contract_id)])
            if agreement_ids:
                #Update liquidation_date of old_contract_id in Termination Agreement to False
                if res_contract.state =='signed':
                    agreements = agreement_pool.read(cr, uid, agreement_ids, ['old_contract_id'])
                    old_contract_ids = [agree.get('old_contract_id', False) and agree['old_contract_id'][0] for agree in agreements]
                    super(hr_contract, self).write(cr, uid, old_contract_ids, {'liquidation_date': False})
                    
                agreement_pool.unlink(cr, uid, agreement_ids)
                
            
            domain_contract = [('employee_id','=',emp_id),
                              ('id','!=',contract_id),
#                                                       ('company_id','!=',company_id),
                              ('state', 'in', ['draft', 'waiting', 'signed']),
                              '|','|','|','|',
                              '&',('date_start','>=',date_start_real),
                                  ('date_start','<=',date_end),
                              
                              '&','&',('date_end','>=',date_start_real),
                                      ('date_end','<=',date_end),
                                      ('liquidation_date','=',False),
                              
                              '&',    ('liquidation_date','>=',date_start_real),
                                      ('liquidation_date','<=',date_end),
                            
                              '&','&',('date_start','<=',date_start_real),
                                      ('liquidation_date','=',False),
                                  '|',('date_end','>=',date_end),
                                      ('date_end','=',False),
                              
                              '&',('date_start','<=',date_start_real),
                                      ('liquidation_date','>=',date_end),
                            ]
            
            #Delete Timesheet employee/ working schedule employee in duration of contract if in that duration dont have any contract with other company
            exist_contract_ids = self.search(cr, uid, domain_contract)
            if not exist_contract_ids:
                self.delete_object_when_cancel_signed_contract(cr, uid, emp_id, date_start_real, date_end, context)
                
                #Update is_reject = True in hr.employee when employee dont have any contract at other company and this contract have change form: gia nhap cty, back to work
                if change_form_id and not context.get('do_not_inactive_employee', False):
                    check_change_form_ids = self.get_change_form_ids_join_company(cr, uid, context)
                    if change_form_id in check_change_form_ids:
                        vals_emp = {'is_reject': True}
                        
                        #check to inactive employee if dont have any active contract
                        today = fields.date.context_today(self, cr, uid)
                
                        active_ids = self.search(cr, uid,[('employee_id','=',emp_id),
                                                          ('state','in',['signed','draft','waiting']),
                                                          ('date_start','<=',today),
                                                          '|','|',
                                                             '&',('date_end','=',False),('liquidation_date','=',False),
                                                             '&',('date_end','>=',today),('liquidation_date','=',False),
                                                                 ('liquidation_date','>=',today),
                                                          ])
                
                        if not active_ids:
                            vals_emp.update({'active': False})
                        
                        self.pool.get('hr.employee').write(cr, uid, emp_id, vals_emp)
            else:
                #Try to delete all salary in contract duration
                domain_contract.insert(0,('company_id','=',company_id))
                exist_contract_ids = self.search(cr, uid, domain_contract)
                if not exist_contract_ids:
                    self.unlink_pr_salary_in_contract_duration(cr, uid, emp_id, company_id, date_start_real, date_end, context)
                
                
        return self.write(cr, uid, ids, {'state': 'cancel'}, context)
    
    def unlink_pr_salary_in_contract_duration(self, cr, uid, employee_id, company_id, date_start, date_end, context = None):
        
        salary_pool = self.pool.get('vhr.pr.salary')
        if employee_id and company_id and date_start and salary_pool:
            domain = [('employee_id','=',employee_id),
                      ('company_id','=',company_id),
                      ('effect_from','>=',date_start)]
            
            if date_end:
                domain.append(('effect_from','<=',date_end))
            
            salary_ids = salary_pool.search(cr, uid, domain)
            if salary_ids:
                try:
                    salary_pool.unlink(cr, uid, salary_ids, context)
                except Exception as e:
                    log.exception(e)
                    try:
                        error_message = e.message
                        if not error_message:
                            error_message = e.value
                    except:
                        error_message = ""
                    raise osv.except_osv('Error !',
                        'Error when delete payroll salary(s) effect in contract duration: \n %s'% error_message)
        
        return True
            
        
    def get_change_form_ids_join_company(self, cr, uid, context= None):
        config_parameter = self.pool.get('ir.config_parameter')
        back_code = config_parameter.get_param(cr, uid, 'vhr_master_data_back_to_work_change_form_code') or ''
        back_code_list = back_code.split(',')
        
        input_code = config_parameter.get_param(cr, uid, 'vhr_master_data_input_data_into_iHRP')
        input_code_list = input_code.split(',')
        
        change_type_code = config_parameter.get_param(cr, uid, 'vhr_master_data_change_type_of_contract')
        change_type_code_list = change_type_code.split(',')
        
        change_local_comp_code = config_parameter.get_param(cr, uid, 'vhr_master_data_change_local_company')
        change_local_comp_code_list = change_local_comp_code.split(',')
        
        check_change_form_list = back_code_list + input_code_list + change_type_code_list + change_local_comp_code_list
        check_change_form_ids = self.pool.get('vhr.change.form').search(cr, uid, [('code','in',check_change_form_list)])
        
        return check_change_form_ids
    
    def delete_object_when_cancel_signed_contract(self, cr, uid, emp_id, date_start, date_end, context=None):
        '''
        This funtion will be inherit in module Timesheet/ Payroll to delete employee timesheet, working schedule employee, payroll salary
        '''
        
        return True
    
        
    def write_change_state(self, cr, uid, ids, signal, comment="", context=None):
        if not isinstance(ids, list):
            ids = [ids]
        result = []
        state_change_obj = self.pool.get('vhr.state.change')
        if signal:
            for contract_id in ids:
                state_vals = SIGNAL[signal]
                state_vals['model'] = self._name
                state_vals['res_id'] = contract_id
                state_vals['comment'] = comment
                state_id = state_change_obj.create(cr, uid, state_vals)
                result.append(state_id)
        return result

    def update_liquidation_date(self, cr, uid, contract_id, liquidation_date, context=None):
        if not isinstance(contract_id, (int, long)):
            return False
        contract = self.read(cr, uid, contract_id, ['liquidation_date','date_end'])
        vals = {'liquidation_date'    : liquidation_date}
        
        flag = True
        if contract.get('date_end',False):
            days = self.compare_day(contract.get('date_end',False), liquidation_date)
            if days > 1:
                flag = False
        if flag:
            self.write(cr, uid, [contract_id], vals, context)
            
        return flag

    def update_users_company_rel(self, cr, uid, employee_id, company_id, user_id=None):
        # use by superuser to do this functionO
        SUPERUSER = 1
        if not isinstance(employee_id, (int, long)) \
                or not isinstance(company_id, (int, long)) \
                or (user_id is not None and not isinstance(user_id, (int, long))):
            return False
        if employee_id and company_id and user_id is None:
            hr_employee = self.pool.get('hr.employee')
            res_read = hr_employee.read(cr, SUPERUSER, employee_id, ['user_id'])
            user_id = res_read['user_id'][0]
        if user_id and company_id:
            res_user = self.pool.get('res.users')
            res_user.write(cr, SUPERUSER, user_id, {'company_ids': [(4, False, company_id)]})
        else:
            return False
        return True

    def increment_number_contract(self, cr, uid, type_increment, employee_id, date_start, company_id=None, ids=[], offer_contract=[], context=None):
        stt = 0
        if context is None:
            context = {}
        context.update({'active_test': False})
        if type_increment == 'month':
            date_start = datetime.datetime.strptime(date_start, DEFAULT_SERVER_DATE_FORMAT)
            start_month = datetime.date(date_start.year, date_start.month, 1).strftime("%Y-%m-%d")
            end_month = ((datetime.date(date_start.year, date_start.month, 1) + relativedelta(months=1)) -
                         datetime.timedelta(1)).strftime("%Y-%m-%d")
            ids = self.search(cr, uid, [('date_start', '>=', start_month), ('date_start', '<=', end_month), ('id', 'not in', ids)], None, None,
                              'id desc', context, False)
            for read_res in self.browse(cr, uid, ids):
                try:
                    if read_res and isinstance(read_res.name, (str, unicode)):
                        name_res = read_res.name
                        name_res = name_res.split('-')
                        name_res = name_res[0].split('/')
                        name_res = name_res[len(name_res) - 1]
                        if int(name_res) > stt:
                            stt = int(name_res)
                except Exception as e:
                    log.info(e)
                    log.info('Contract %s is invalid' % (read_res.name))
                    continue
        else:  # employee
            args = [('employee_id', '=', employee_id)]
            if company_id:
                args += [('company_id', '=', company_id)]
            contract_type_group = self.pool.get('hr.contract.type.group')
            emp_inst_obj = self.pool.get('vhr.employee.instance')
            type_group_ids = contract_type_group.search(cr, uid, [('is_offical', '=', True), ('code', 'not in', offer_contract)], None, None, None, context)

            inst_args = args + [('date_end', '=', False)]
            active_instance_ids = emp_inst_obj.search(cr, uid, inst_args, context=context)
            inst_start_date = None
            if active_instance_ids:
                emp_inst = emp_inst_obj.browse(cr, uid, active_instance_ids[0], context=context)
                inst_start_date = emp_inst.date_start

            contract_args = args + [('date_start', '>=', inst_start_date), ('state', '!=', 'cancel'),
                                    ('type_id.contract_type_group_id', 'in', type_group_ids), ('id', 'not in', ids)]
            contract_ids = self.search(cr, uid, contract_args, None, None, 'id desc, date_start desc', context, False)
            stt = len(contract_ids)
        return stt + 1

    def _interpolate(self, s, d):
        if s:
            return s % d
        return ''

    def _interpolation_dict(self):
        t = time.localtime()  # Actually, the server is always in UTC.
        return {
            'year': time.strftime('%Y', t),
            'month': time.strftime('%m', t),
            'day': time.strftime('%d', t),
            'y': time.strftime('%y', t),
            'doy': time.strftime('%j', t),
            'woy': time.strftime('%W', t),
            'weekday': time.strftime('%w', t),
            'h24': time.strftime('%H', t),
            'h12': time.strftime('%I', t),
            'min': time.strftime('%M', t),
            'sec': time.strftime('%S', t),
        }

    def _interpolation_date(self, date):
        date = datetime.datetime.strptime(date, DEFAULT_SERVER_DATE_FORMAT)
        return {
            'year': time.strftime('%Y', date),
            'month': time.strftime('%m', date),
            'day': time.strftime('%d', date),
            'y': time.strftime('%y', date),
            'doy': time.strftime('%j', date),
            'woy': time.strftime('%W', date),
            'weekday': time.strftime('%w', date),
            'h24': time.strftime('%H', date),
            'h12': time.strftime('%I', date),
            'min': time.strftime('%M', date),
            'sec': time.strftime('%S', date),
        }

    def generate_code(self, cr, uid, type_id, employee_id, date_start, company_id=None, ids=[], context=None):
        ''' Tinh theo ngay bat dau hieu luc hop dong
            1.    Loáº¡i há»£p Ä‘á»“ng thá»­ viá»‡c, mÃ£ há»£p Ä‘á»“ng = 0/yyyy/MM/Seq-Offer (Seq = sá»‘ há»£p Ä‘á»“ng trong thÃ¡ng)
            2.    Loáº¡i há»£p Ä‘á»“ng CTV, MÃ£ há»£p Ä‘á»“ng = 4/yyyy/MM/Seq-CTV
            3.    Loáº¡i há»£p Ä‘á»“ng tÆ° váº¥n, MÃ£ há»£p Ä‘á»“ng = 5/yyyy/MM/Seq-HÄ�TV
            4.    Loáº¡i há»£p Ä‘á»“ng chÃ­nh thá»©c, MÃ£ há»£p Ä‘á»“ng = (Sá»‘ há»£p Ä‘á»“ng chÃ­nh thá»©c ) /yyyy/MM/Seq-HÄ�LÄ�
        '''
        if not type_id:
            return False
        contract_type = self.pool.get('hr.contract.type')
        type_group = contract_type.browse(cr, uid, type_id).contract_type_group_id
        interpolated_prefix = type_group.prefix
        
        #Offer contract still follow rule 0/yyyy/MM/Seq-Offer (Seq = số hợp đồng trong tháng) even it is official
        parameter_obj = self.pool.get('ir.config_parameter')
        offer_contract_type_group_code = parameter_obj.get_param(cr, uid, 'vhr_human_resource_probation_contract_type_group_code') or ''
        offer_contract_type_group_code = offer_contract_type_group_code.split(',')
        
        if type_group.is_offical and type_group.code not in offer_contract_type_group_code:
            if not employee_id:
                return False
            interpolated_prefix = self.increment_number_contract(cr, uid, 'employee', employee_id, date_start, company_id, ids, offer_contract_type_group_code, context)
        sequence = self.increment_number_contract(cr, uid, 'month', employee_id, date_start, None, ids, offer_contract_type_group_code, context)
        # d = self._interpolation_dict()
        try:
            # interpolated_prefix = self._interpolate(type_group.prefix, d)
            date_start = datetime.datetime.strptime(date_start, DEFAULT_SERVER_DATE_FORMAT)
            year = date_start.year
            month = date_start.month
        except ValueError:
            raise osv.except_osv(_('Warning'),
                                 _('Invalid prefix or suffix for contract type group \'%s\'') % (type_group.name))
        res = '%s/%s/%02i/%03i-%s' % (interpolated_prefix, year, month, sequence, type_group.suffix)
        return res

    def get_data_salary(self, cr, uid, ids, employee_id, company_id, date_start, context=None):
        res = {'gross_salary': 0, 'basic_salary': 0, 'kpi_amount': 0,'general_allowance': 0,'v_bonus_salary':0}
        if employee_id and company_id and date_start:
            salary_pool = self.pool.get('vhr.pr.salary')
            salary_ids = salary_pool.search(cr, uid, [('employee_id','=',employee_id),
                                                                        ('company_id','=',company_id),
                                                                        ('effect_from','<=',date_start)], order='effect_from desc')
            if salary_ids:
                salary = salary_pool.read(cr, uid, salary_ids[0], ['gross_salary','basic_salary','kpi_amount','general_allowance','v_bonus_salary'])
                res['gross_salary'] = salary.get('gross_salary',0)
                res['basic_salary'] = salary.get('basic_salary',0)
                res['kpi_amount'] = salary.get('kpi_amount',0)
                res['general_allowance'] = salary.get('general_allowance',0)
                res['v_bonus_salary'] = salary.get('v_bonus_salary',0)

        return res

    def onchange_company_id(self, cr, uid, ids, company_id, employee_id, type_id, date_start, division_id=None,
                            include_probation=False, context=None):
        if not context:
            context = {}
        res = {'value': {'change_form_id':False,'info_signer': '','title_signer': '','country_signer': False}}
        if not company_id:
            return res
        res_company = self.pool.get('res.company')
        emp_inst_obj = self.pool.get('vhr.employee.instance')
        res_read = res_company.read(cr, uid, company_id, ['sign_emp_id','job_title_id','country_signer'])
        if res_read['sign_emp_id']:
            res['value'].update({'info_signer': res_read['sign_emp_id'],
                                 'title_signer': res_read.get('job_title_id',''),
                                 'country_signer': res_read.get('country_signer',False) and res_read['country_signer'][0] or False,
                                 })

#         data_salary = self.get_data_salary(cr, uid, ids, employee_id, company_id, date_start, context)
#         res['value'].update(data_salary)
        if employee_id:
            res['value'].update(self.suggest_work_email(cr, uid, ids, employee_id, company_id))
            active_instance_ids = emp_inst_obj.search(cr, uid, [('employee_id', '=', employee_id),
                                                                ('company_id', '=', company_id),
                                                                ('date_end', '=', False)])
            if active_instance_ids:
                instances = emp_inst_obj.read(cr, uid, active_instance_ids, ['date_start'])
                for instance in instances:
                    date_start_instance = instance.get('date_start', False)
                    if date_start_instance == date_start and not include_probation and ids:
                        active_instance_ids.remove(instance['id'])
                    
            res['value']['is_existing_contract'] = active_instance_ids and True or False
            
            if not active_instance_ids and 'change_form_id' in res['value']:
                del res['value']['change_form_id']

            if active_instance_ids:
                emp_inst = emp_inst_obj.browse(cr, uid, active_instance_ids[0], context=context)
                inst_start_date = emp_inst.date_start
                is_on_probation = self.check_last_contract_type_is_offer(cr, uid, ids, employee_id, company_id,
                                                                         inst_start_date, date_start, context=context)
                res['value'].update({'is_on_probation': is_on_probation})
            
            if type_id:
                type = self.pool.get('hr.contract.type').browse(cr, uid, type_id)
                is_official = type.contract_type_group_id and type.contract_type_group_id.is_offical or False
                context['dont_get_field_of_not_official_contract'] = not is_official
            val = self.get_employee_data_from_wkr(cr, uid, employee_id, company_id, division_id, context=context)
            res['value'].update(val)
            if include_probation:
                res['value'].update(self.validate_contract_include_probation(cr, uid, employee_id, company_id, type_id, context=context))
            
            #this code to be sure that person manage contract will go to config change form to show in contract
            contract_change_form_ids = self.pool.get('vhr.change.form').search(cr, uid, [('show_in_contract','=',True)])
            if not contract_change_form_ids and not res['value']['is_existing_contract']:
                res['warning'] = {
                            'title': 'Validation Error!',
                            'message' : "Can't find any available change form show in contract !"
                             }
                
            #Get domain of change form 
            res['domain'] = self.check_is_new_employee(cr, uid, employee_id, company_id, context=context)
            
            if not ids and not res['value']['is_existing_contract']:
                #When create and dont dont have any instance with date_end = False, set default for change_form
                if res['domain'].get('change_form_id', False):
                    change_form_ids = self.pool.get('vhr.change.form').search(cr, uid, res['domain']['change_form_id'])
                    if len(change_form_ids) == 1:
                        res['value']['change_form_id'] = change_form_ids[0]
            
            if ids and date_start:
                context['date_start'] = date_start
            value = self.check_contract_type(cr, uid, ids, employee_id, company_id, context=context)
            list_contract_type = self.get_list_contract_type_id(cr, uid, value, context=context)
            res['value'].update({'list_contract_type_id': list_contract_type})
            if type_id not in list_contract_type:
                res['value']['type_id'] = False
        

        return res

    def get_employee_data_from_wkr(self, cr, uid, employee_id, company_id, division_id=None, context=None):
        if not context:
            context = {}
            
        wkr_obj = self.pool.get('vhr.working.record')
        department_obj = self.pool.get('hr.department')
        division_com_id = None
        if division_id:
            res_division = department_obj.browse(cr, uid, division_id, context=context)
            division_com_id = res_division and res_division.company_id and res_division.company_id.id or None
        if not division_id or division_com_id != company_id:
            wkr_ids = wkr_obj.search(cr, uid, [('employee_id', '=', employee_id), 
                                               ('company_id', '=', company_id), 
                                               ('state','in',[False,'finish']),
                                               ('active', '=', True)
                                               ], order='effect_from desc', limit=1)
            val = {'office_id': None, 'division_id': None, 'department_id': None, 'work_email': '','department_group_id': False,
                   'mobile_phone': '', 'work_phone': '', 'title_id': None, 'ext_no': '', 'seat_no': ''}
            if wkr_ids:
                wkr_res = wkr_obj.browse(cr, uid, wkr_ids[0], context=context)
                if wkr_res:
                    val['office_id'] = wkr_res.office_id_new and wkr_res.office_id_new.id or None
                    val['division_id'] = wkr_res.division_id_new and wkr_res.division_id_new.id or None
                    val['department_group_id'] = wkr_res.department_group_id_new and wkr_res.department_group_id_new.id or None
                    val['department_id'] = wkr_res.department_id_new and wkr_res.department_id_new.id or None
                    val['report_to'] = wkr_res.report_to_new and wkr_res.report_to_new.id or None
                    val['is_change_data_from_duplicate'] = True
                    val['work_email'] = wkr_res.work_email_new or ''
                    #val['mobile_phone'] = wkr_res.mobile_phone_new or ''
#                     val['work_phone'] = wkr_res.work_phone_new or ''
                    val['title_id'] = wkr_res.job_title_id_new and wkr_res.job_title_id_new.id or None
                    val['ext_no'] = wkr_res.ext_new or ''
                    val['seat_no'] = wkr_res.seat_new or ''
                    
                    val['ts_working_group_id'] = wkr_res.ts_working_group_id_new and wkr_res.ts_working_group_id_new.id or None
                    val['timesheet_id'] = wkr_res.timesheet_id_new and wkr_res.timesheet_id_new.id or None
                    val['salary_setting_id'] = wkr_res.salary_setting_id_new and wkr_res.salary_setting_id_new.id or None
                    val['job_level_person_id'] = wkr_res.job_level_person_id_new and wkr_res.job_level_person_id_new.id or None
            else:
                val = self.get_initial_data_from_employee(cr, uid, employee_id, context)
            
            if context.get('dont_get_field_of_not_official_contract', False): 
                val['job_level_person_id'] = False
                
            return val
        return {}
    
    def get_initial_data_from_employee(self, cr, uid, employee_id, context=None):
        res = {}
        if employee_id:
            fields = ['division_id','department_group_id','department_id','report_to','title_id','office_id','seat_no','job_level_person_id']
            employee = self.pool.get('hr.employee').read(cr, uid, employee_id, fields)
            res['division_id'] = employee.get('division_id', False) and employee['division_id'][0] or False
            res['department_group_id'] = employee.get('department_group_id', False) and employee['department_group_id'][0] or False
            res['department_id'] = employee.get('department_id', False) and employee['department_id'][0] or False
            res['report_to'] = employee.get('report_to', False) and employee['report_to'][0] or False
            res['title_id'] = employee.get('title_id', False) and employee['title_id'][0] or False
#             res['job_level_id'] = employee.get('job_level_id', False) and employee['job_level_id'][0] or False
            res['office_id'] = employee.get('office_id', False) and employee['office_id'][0] or False
            res['seat_no'] = employee.get('seat_no','')
            res['is_change_data_from_duplicate'] = True
#             res['job_level_position_id'] = employee.get('job_level_position_id', False) and employee['job_level_position_id'][0] or False
            res['job_level_person_id'] = employee.get('job_level_person_id', False) and employee['job_level_person_id'][0] or False
            
            res['job_family_id'] = employee.get('job_family_id', False) and employee['job_family_id'][0] or False
            res['job_group_id'] = employee.get('job_group_id', False) and employee['job_group_id'][0] or False
            res['sub_group_id'] = employee.get('sub_group_id', False) and employee['sub_group_id'][0] or False
        
        return res
            
            

    def suggest_work_email(self, cr, uid, ids, employee_id, company_id):
        res = {}
        if not company_id or not employee_id:
            return res
        res_company = self.pool.get('res.company')
        hr_employee = self.pool.get('hr.employee')
        res_read = res_company.read(cr, uid, company_id, ['suffix_email'])
        value = hr_employee.browse(cr, uid, employee_id)
        if res_read['suffix_email'] and value.user_id:
            res.update({'work_email': '%s%s' % (value.user_id.login, res_read['suffix_email'])})
        return res

    def get_date_end_and_life_of_contract(self, cr, uid, ids, type_id, date_start, context=None):
        res = {}
        if type_id:
            code_probation = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_human_resource_probation_contract_type_group_code') or ''
            code_probation = code_probation.split(',')
        
            contract_type = self.pool.get('hr.contract.type').browse(cr, uid, type_id)
            life_of_contract = contract_type.life_of_contract
            is_official = contract_type.is_official
            type_group_code = contract_type.contract_type_group_id and contract_type.contract_type_group_id.code or False
            res['contract_duration'] = life_of_contract
            
            if date_start and life_of_contract:
                date_start = datetimes.strptime(date_start, DEFAULT_SERVER_DATE_FORMAT).date()
                date_end = date_start + relativedelta(months=life_of_contract) - relativedelta(days=1)
                # If contract is official then last day will be last day of month
                if is_official and type_group_code not in code_probation:
                    date_end = (date(date_end.year, date_end.month, 1) + relativedelta(months=1)) - relativedelta(days=1)

                res['date_end'] = date_end.strftime(DEFAULT_SERVER_DATE_FORMAT)

        return res

    def onchange_employee_id(self, cr, uid, ids, employee_id, type_id=None, company_id=None, date_start=False,
                             division_id=None, emp_change=False, include_probation=False, context=None):
        res = super(hr_contract, self).onchange_employee_id(cr, uid, ids, employee_id)
        if context is None:
            context = {}
        if not employee_id:
            return res
        hr_employee = self.pool.get('hr.employee')
        contract_type_obj = self.pool.get('hr.contract.type')
        contract_type_group_obj = self.pool.get('hr.contract.type.group')
        contract_sub_type_obj = self.pool.get('hr.contract.sub.type')
        bank_obj = self.pool.get('res.partner.bank')
        bank_contract_obj = self.pool.get('vhr.bank.contract')
        currency_obj = self.pool.get('res.currency')
        emp_inst_obj = self.pool.get('vhr.employee.instance')
        value = hr_employee.read(cr, uid, employee_id, ['address_home_id', 'code'])
        res['value'] = {
            'partner_id': value.get('address_home_id', False) and value['address_home_id'][0] or None,
            'emp_code': value['code'],
            'is_official': False,
        }
        
        if not isinstance(ids, list):
            ids = [ids]
            
        if ids and date_start:
            context['date_start'] = date_start
            
        #If contract is not first contract of employee, get default company from employee
        if employee_id and not context.get('onchange_type_id', False) and not context.get('default_company_id', False):
            contract_ids = self.search(cr, uid, [('employee_id','=',employee_id),
                                                 ('state','!=','cancel'),
                                                 ('id','not in', ids)])
            if contract_ids:
                employee = hr_employee.read(cr, uid, employee_id, ['company_id'])
                company_id = employee.get('company_id', False) and employee['company_id'][0]
                res['value']['company_id'] = company_id
        
        value = self.check_contract_type(cr, uid, ids, employee_id, company_id, context=context)
        list_contract_type = self.get_list_contract_type_id(cr, uid, value, context=context)
        res['value'].update({'list_contract_type_id': list_contract_type})
        if type_id not in list_contract_type:
            type_id = False
            res['value']['type_id'] = False
        
        is_official = False
        if type_id:
            if isinstance(type_id, tuple):
                type_id = type_id[0]
            
            type = contract_type_obj.browse(cr, uid, type_id)
            type_group_id = type.contract_type_group_id and type.contract_type_group_id.id or False
            contract_type_group_code = type.contract_type_group_id and type.contract_type_group_id.code or False
            is_official = type.contract_type_group_id and type.contract_type_group_id.is_offical or False
            
            if type_group_id and type.contract_type_group_id.is_offical:
                res['value']['is_official'] = True
                res['value']['is_require_job_family'] = True
                
                res['value']['collaborator_salary'] = 0
                res['value']['salary_percentage'] = 70
            else:
                res['value']['is_require_job_family'] = False
                res['value']['career_track_id'] = False
                res['value']['job_level_person_id'] = False
                
                res['value']['gross_salary'] = 0
                res['value']['salary_percentage'] = 0
                res['value']['kpi_amount'] = 0
                res['value']['basic_salary'] = 0
                res['value']['v_bonus_salary'] = 0
                res['value']['probation_salary'] = 0
        
        if not context.get('onchange_type_id', False):
            res['value']['change_form_id'] = False
            #onchange employee
            division_id = False
            res['value'].update({'office_id': False,
                                'division_id': False,
                                'department_group_id': False,
                                'department_id': False,
                                'report_to': False,
                                'is_change_data_from_duplicate': True,
                                'work_email': '',
                                'mobile_phone': '',
                                'work_phone': '',
                                'title_id': '',
                                'ext_no': '',
                                'seat_no': ''
                                })
        else:
            res['value']['is_show_sub_type'] = False
            res['value']['is_show_working_salary'] = False
            res['value']['contract_type_group_id'] = False
            res['value']['sub_type_id'] = False
            if type_id:
                code_show_salary = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_human_resource_contract_type_group_code_show_working_salary_in_contract') or ''
                code_show_salary = code_show_salary.split(',')
                
                if contract_type_group_code in code_show_salary:
                    res['value']['is_show_working_salary'] = True
                
                sub_type_ids = contract_sub_type_obj.search(cr, uid, ['|',('contract_type_id','=',type_id),
                                                                          ('contract_type_group_id','=',type_group_id)])
                
                res['value']['contract_type_group_id'] = type_group_id
                if sub_type_ids:
                    res['value']['is_show_sub_type'] = True
                    if 'sub_type_id' in res['value']:
                        del res['value']['sub_type_id']
                
            
        res['domain'] = {}
        res['warning'] = {}
        # load main bank account
        if emp_change:
            bank_values = []
            bank_ids = bank_obj.search(cr, uid, [('employee_id', '=', employee_id), ('is_main', '=', True), ('active', '=', True)], context=context)
            currency_ids = currency_obj.search(cr, uid, [('name', '=', 'VND')], context=context)
            currency_id = currency_ids and currency_ids[0] or False
            cur_banks = []
            if ids:
                bank_contract_ids = bank_contract_obj.search(cr, uid, [('contract_id', 'in', ids)], context=context)
                for bank_contract in bank_contract_obj.browse(cr, uid, bank_contract_ids):
                    if bank_contract.bank_id:
                        cur_banks.append(bank_contract.bank_id.id)
                bank_ids = list(set(bank_ids) - set(cur_banks))
            if bank_ids:
                bank_values.append([0, False, {'bank_id': bank_ids[0], 'weight': 100, 'value_type': 'percent',
                                               'currency': currency_id, 'employee_id': employee_id}])
                res['value'].update({'bank_account_ids': bank_values})
        
        #Check is_main
        # Nếu hiện tại NV chưa có HĐ nào đang hiệu lực thì "is_main"=True; 
        # Ngược lại, thì "is_main"=False
        if not context.get('is_main', False):
            res['value']['is_main'] = False
            today = fields.date.context_today(self, cr, uid)
            #Search ra HD dang hieu luc co is_main=True
            exist_contract_ids = self.search(cr, uid, [('employee_id','=',employee_id),
                                                          ('date_start', '<=', today),
                                                          ('state', '=', 'signed'),
                                                          ('is_main', '=', True),
                                                          '|', '|',
                                                          ('liquidation_date', '>=', today),
                                                          '&', ('date_end', '>=', today),
                                                          ('liquidation_date', '=', False),
                                                          '&', ('date_end', '=', False),
                                                          ('liquidation_date', '=', False),
                                                        ], order='date_start asc')
            if not exist_contract_ids:
                res['value']['is_main'] = True

        if type_id:
            if date_start:
                res['value'].update({'name': self.generate_code(cr, uid, type_id, employee_id, date_start, company_id, ids, None)})
                
                date_compare = date_start
                if context.get('date_start_temp', False):
                    date_compare = context['date_start_temp']
                data = self.get_date_end_and_life_of_contract(cr, uid, ids, type_id, date_compare, context)
                res['value'].update(data)
            else:
                res['value']['contract_duration'] = False
            
            
            contract_type = contract_type_obj.browse(cr, uid, type_id, context=context)
            if not emp_change:
                if contract_type and contract_type.code == '7':
                    res['value'].update({'contract_type_code': '7', 'date_end': False})
                else:
                    res['value'].update({'contract_type_code': ''})
            
            if not contract_type.is_official and not context.get('onchange_type_id',False) and not context.get('duplicate_active_id', False):
                res_collaborator = self.get_default_collaborator_data(cr, uid, context)
                res['value'].update(res_collaborator)

        if company_id:
            context['dont_get_field_of_not_official_contract'] = not is_official
            val = self.get_employee_data_from_wkr(cr, uid, employee_id, company_id, division_id, context=context)
            res['value'].update(val)

            res['value'].update(self.suggest_work_email(cr, uid, ids, employee_id, company_id))
            active_instance_ids = emp_inst_obj.search(cr, uid, [
                ('employee_id', '=', employee_id),
                ('company_id', '=', company_id),
                ('date_end', '=', False)])
            res['value']['is_existing_contract'] = active_instance_ids and True or False

            if active_instance_ids:
                emp_inst = emp_inst_obj.browse(cr, uid, active_instance_ids[0], context=context)
                inst_start_date = emp_inst.date_start
                is_on_probation = self.check_last_contract_type_is_offer(cr, uid, ids, employee_id, company_id,
                                                                         inst_start_date, date_start, context=context)
                res['value'].update({'is_on_probation': is_on_probation})

            if include_probation:
                res['value'].update(self.validate_contract_include_probation(cr, uid, employee_id, company_id, type_id, context=context))
            
            contract_change_form_ids = self.pool.get('vhr.change.form').search(cr, uid, [('show_in_contract','=',True)])
            if not contract_change_form_ids and not res['value']['is_existing_contract']:
                res['warning'] = {
                            'title': 'Validation Error!',
                            'message' : "Can't find any available change form show in contract !"
                             }
            
            #Get domain of change form
            res['domain'].update(self.check_is_new_employee(cr, uid, employee_id, company_id, context=context))
        
        return res

    def onchange_liquidation(self, cr, uid, ids, date_start, date_end, liquidation, context=None):
        res = {'value': {}}
        if date_end:
            if liquidation:
                compare = self.compare_day(date_end, liquidation)
                if compare > 1:
                    res['warning'] = {'title': _('Warning'),
                                      'message': _('Liquidation date must be less than or equal to end date plus 1 day!')}
                    res['value'] = {'liquidation_date': False}
#         else:
#             res['value'] = {'liquidation_date': False}

        if date_start and liquidation:
            compare = self.compare_day(liquidation, date_start)
            if compare > 0:
                res['warning'] = {'title': _('Warning'),
                                  'message': _('Start date must be less than or equal to liquidation date !')}
                res['value'] = {'liquidation_date': False}
        return res

    def onchange_date(self, cr, uid, ids, date_start, date_end, liquidation, contract_duration,
                      employee_id=None, type_id=None, company_id=None, date_start_temp=False, context=None):
        
        res = {'value': {}}
        if not date_start:
            return res
        
        res['value']['sign_date'] = date_start
        
        if employee_id and type_id:
            res['value'].update({'name': self.generate_code(cr, uid, type_id, employee_id, date_start, company_id, ids, None)})
        if type_id:
            date_compare = date_start
#             if date_start_temp:
#                 date_compare = date_start_temp
            data = self.get_date_end_and_life_of_contract(cr, uid, ids, type_id, date_compare, context)
            date_end = data.get('date_end', False)
            res['value'].update(data)

        if date_end:
            compare = self.compare_day(date_end, date_start)
            if compare > 0:
                res['warning'] = {'title': _('Warning'),
                                  'message': _('Start date must be less than or equal to end date !')}
                res['value'] = {'date_start': False}

        if liquidation:
            if date_end:
                compare = self.compare_day(date_end, liquidation)
                if compare > 1:
                    res['warning'] = {'title': _('Warning'),
                                      'message': _('Liquidation date must be less than or equal to end date plus 1 day!')}
                    res['value'] = {'liquidation_date': False}

            if date_start:
                compare = self.compare_day(liquidation, date_start)
                if compare > 0:
                    res['warning'] = {'title': _('Warning'),
                                      'message': _('Start date must be less than or equal to liquidation date !')}
                    res['value'] = {'date_start': False}

        return res
    
    def onchange_job_family_id(self, cr, uid, ids, job_family_id, job_group_id, context=None):
        if not context:
            context = {}
        res = {'job_group_id': False}  #,'pro_sub_group_id_new': False
        
        if job_family_id and job_group_id:
            job_group = self.pool.get('vhr.job.group').read(cr, uid, job_group_id, ['job_family_id'])
            c_job_family_id = job_group.get('job_family_id', False) and job_group['job_family_id'][0] or False
            if c_job_family_id == job_family_id:
                res = {}
            
        return {'value': res}
    
    def onchange_job_group_id(self, cr, uid, ids, job_group_id, sub_group_id, context=None):
        if not context:
            context = {}
        res = {'sub_group_id': False}
        
        if job_group_id and sub_group_id:
            sub_group = self.pool.get('vhr.sub.group').read(cr, uid, sub_group_id, ['job_group_id'])
            s_job_group_id = sub_group.get('job_group_id', False) and sub_group['job_group_id'][0] or False
            if s_job_group_id == job_group_id:
                res = {}
            
        return {'value': res}

    def onchange_include_probation(self, cr, uid, ids, include_probation, employee_id, company_id, type_id, context=None):
        if not context:
            context = {}
            
        res = {'value': {'date_start_temp': False}}
        emp_inst_obj = self.pool.get('vhr.employee.instance')
        if include_probation and employee_id and company_id:
            value = self.validate_contract_include_probation(cr, uid, employee_id, company_id, type_id, context=context)
            res['value'] = value
            if not value.get('date_start'):
                res['warning'] = {'title': _('Warning'),
                                  'message': _('The probationary contract does not exist!')}
        else:
            
            active_instance_ids = emp_inst_obj.search(cr, uid, [('employee_id', '=', employee_id), 
                                                                ('company_id', '=', company_id), 
                                                                ('date_end', '=', False)])
            date_end = False
            if active_instance_ids:
                emp_inst = emp_inst_obj.browse(cr, uid, active_instance_ids[0], context=context)
                inst_start_date = emp_inst.date_start
                #Get all contract of instance
                contract_ids = self.search(cr, uid, [ ('date_start', '>=', inst_start_date), 
                                                     ('state', '=', 'signed'),
                                                     ('employee_id', '=', employee_id), 
                                                     ('company_id', '=', company_id),
                                                     ('id','not in', ids),
                                                     ], order='date_start desc,id desc', context=context)
                if contract_ids:
                    if contract_ids[0] == context.get('duplicate_active_id', False) and context.get('liquidation_date', False):
                        date_end = datetimes.strptime(context['liquidation_date'], DEFAULT_SERVER_DATE_FORMAT) - relativedelta(days=1)
                        date_end = date_end.strftime(DEFAULT_SERVER_DATE_FORMAT)
                    else:
                        last_contract = self.browse(cr, uid, contract_ids[0], fields_process=['date_end', 'liquidation_date'])
                        if last_contract.liquidation_date:
                            date_end = last_contract.liquidation_date
                            
                            #If have liquidation date, next contract can start from liquidation_date
                            date_end = datetimes.strptime(date_end, DEFAULT_SERVER_DATE_FORMAT) - relativedelta(days=1)
                            date_end = date_end.strftime(DEFAULT_SERVER_DATE_FORMAT)
                        else:
                            date_end = last_contract.date_end
            if date_end:
                date_start = datetimes.strptime(date_end, DEFAULT_SERVER_DATE_FORMAT) + relativedelta(days=1)
                date_start = date_start.strftime(DEFAULT_SERVER_DATE_FORMAT)
                
                data = self.get_date_end_and_life_of_contract(cr, uid, ids, type_id, date_start, context)
                res['value'].update({'date_start': date_start,'date_end': data.get('date_end',False)})

        return res
    
    def get_default_collaborator_data(self, cr, uid, context=None):
        if not context:
            context = {}
        res = {}
        loop_unique = [('mission_ids','CONTRACT_COLLABORATOR_MISSION','mission_id'),
                       ('result_ids','CONTRACT_COLLABORATOR_RESULT','result_id')]
        
        dimension_type_obj = self.pool.get('vhr.dimension.type')
        dimension_obj = self.pool.get('vhr.dimension')
        for item in loop_unique:
            data_item = []
            dimension_type_ids = dimension_type_obj.search(cr, uid, [('code','=',item[1])])
            mission_value_ids = dimension_obj.search(cr, uid, [('dimension_type_id','in',dimension_type_ids)])
            if mission_value_ids:
                for mission_value_id in mission_value_ids:
                    data_item.append([0, False, {item[2]: mission_value_id}])
            
            if context.get(item[0], False):
                for existed_data in context[item[0]]:
                    if existed_data[0] in [1,4]:
                        data_item.append([2, existed_data[1], False])
                        
            res[item[0]] = data_item
        
        return res

    def validate_contract_include_probation(self, cr, uid, employee_id, company_id, type_id, context=None):
        res = {}
        contract_type_group_object = self.pool.get('hr.contract.type.group')
        contract_type_object = self.pool.get('hr.contract.type')
        type_group_ids = contract_type_group_object.search(cr, uid, [('code', '=', '1')])
        type_ids = contract_type_object.search(cr, uid, [('contract_type_group_id', 'in', type_group_ids)])
        contract_ids = self.search(cr, uid, [('employee_id', '=', employee_id), 
                                             ('company_id', '=', company_id), 
                                             ('type_id', 'in', type_ids), 
                                             ('state', '=', 'signed'),
                                             ], order='id desc', context=context)
        if contract_ids:
            contract = self.browse(cr, uid, contract_ids[0], context=context)
            res['date_start'] = contract.date_start
            res['date_start_temp'] = contract.date_end
            
            data = self.get_date_end_and_life_of_contract(cr, uid, [], type_id, contract.date_start, context)
            res['date_end'] = data.get('date_end')
        else:
            res['include_probation'] = False
        return res

    def check_is_new_employee(self, cr, uid, employee_id, company_id, context=None):
        '''
        Check if dont have any contract with change form gia nhap cong ty at company_id
        '''
        res = {'change_form_id': [('show_in_contract', '=', True)]}
        code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_master_data_input_data_into_iHRP') or ''
        change_form_ids = self.pool.get('vhr.change.form').search(cr, uid, [('code', '=', code)], context=context)
        contract_ids = self.search(cr, uid, [('employee_id', '=', employee_id), 
                                             ('company_id','=',company_id),
                                             ('state', 'in', ['draft', 'waiting', 'signed']),
                                             ('change_form_id', 'in', change_form_ids)], context=context)
        if len(contract_ids) > 0:
            res = {'change_form_id': [('code', '!=', code),('show_in_contract', '=', True)]}
            
        return res

    def onchange_division(self, cr, uid, ids, division_id, department_group_id, department_id, context=None):
        if not context:
            context = {}
        
        res = {'department_group_id': False, 'department_id':False, 'manager_id': False, 'report_to': False, 'team_id': False}
        dept_obj = self.pool.get('hr.department')
        
        if division_id:
            child_department_group_ids = dept_obj.get_department_unit_level(cr, uid, division_id, 2, None, None, context)
            if department_group_id:
                child_department_ids = dept_obj.get_department_unit_level(cr, uid, department_group_id, 3, None, None, context)
            else:
                child_department_ids = dept_obj.get_department_unit_level(cr, uid, division_id, 3, None, None, context)
                child_department_ids = dept_obj.filter_to_get_direct_child_department(cr, uid, child_department_ids, 1, context)
            
            if (department_group_id and department_group_id in child_department_group_ids and department_id in child_department_ids) or \
               (not department_group_id and department_id in child_department_ids):
                res = {}

        return {'value': res}
    
    def onchange_department_group(self, cr, uid, ids, division_id, department_group_id, department_id, context=None):
        if not context:
            context = {}
        
        res = {'department_id': False, 'manager_id': False, 'report_to': False, 'team_id': False}
        dept_obj = self.pool.get('hr.department')
        if division_id and department_id:
            if department_group_id:
                child_department_group_ids = dept_obj.get_department_unit_level(cr, uid, department_group_id, 3, None, None, context)
                if department_id in child_department_group_ids:
                    res = {}
            else:
                child_division_ids = dept_obj.get_department_unit_level(cr, uid, division_id, 3, None, None, context)
                child_division_ids = dept_obj.filter_to_get_direct_child_department(cr, uid, child_division_ids, 1, context)
            
                if department_id in child_division_ids:
                    res = {}

        return {'value': res}

    def onchange_department(self, cr, uid, ids, department, is_change_data_from_duplicate, context=None):
        if not department:
            return {'value': {}}
        depart_obj = self.pool.get('hr.department')
        depart_obj = depart_obj.browse(cr, uid, department)
        res = {
            'manager_id': depart_obj.manager_id.id,
            'team_id': False,
        }
        if not is_change_data_from_duplicate:
            res['report_to'] = depart_obj.manager_id.id
        else:
            res['is_change_data_from_duplicate'] = False

        return {'value': res}
    
    def onchange_title_id(self, cr, uid, ids, job_title_id, job_level_id, context=None):
        res = {}
        if job_title_id:
            job_level_ids = []
            title_level_ids = self.pool.get('vhr.jobtitle.joblevel').search(cr, uid, [('job_title_id','=',job_title_id)])
            if title_level_ids:
                title_level_infos = self.pool.get('vhr.jobtitle.joblevel').read(cr, uid, title_level_ids, ['job_level_id'])
                for title_level_info in title_level_infos:
                    if title_level_info.get('job_level_id', False):
                        job_level_ids.append(title_level_info['job_level_id'][0])
            if (job_level_id and job_level_id not in job_level_ids) or not job_level_id:
                res['job_level_id'] = False
                if job_level_ids:
                    res['job_level_id'] = job_level_ids[0]
                     
        return {'value': res}

    def validate_duration(self, cr, uid, vals, id_write=None, context=None):
        """
        Khong validate duration với hd ở trạng thái draft
        """
        contract_type_group_object = self.pool.get('hr.contract.type.group')
        field_need = []
        
        fields = ['company_id','employee_id','include_probation','date_start','date_end','state',' date_start_real']
        val = vals.copy()
        
        for field in fields:
            if field not in val and id_write:
                field_need.append(field)
        
        if field_need:
            res = self.read(cr, uid, id_write, field_need)
            for field in field_need:
                if field in field_need:
                    field_data = res.get(field)
                    if isinstance(field_data, tuple):
                        field_data = field_data[0]
                    val.update({field: field_data})
            
        if val.get('state', False) == 'draft':
            return True
        
        range_one = {'start_date': val.get('date_start_real',False) or val.get('date_start',False), 'end_date': val.get('date_end',False)}
            

        args = [('company_id', '=', val['company_id']), ('state', 'not in', ['cancel','draft']),
                ('employee_id', '=', val['employee_id'])]
        if id_write:
            args.append(('id', 'not in', [id_write]))
        ids_search = self.search(cr, uid, args)
        for item in self.read(cr, uid, ids_search, ['date_start', 'date_end', 'liquidation_date', 'contract_type_group_id','date_start_real']):
            if item['liquidation_date']:
                item['date_end'] = item['liquidation_date']
                
                #If have liquidation date, next contract can start from liquidation_date
                item['date_end'] = datetimes.strptime(item['date_end'], DEFAULT_SERVER_DATE_FORMAT) - relativedelta(days=1)
                item['date_end'] = item['date_end'].strftime(DEFAULT_SERVER_DATE_FORMAT)
            range_two = {
                'start_date': item['date_start_real'] or item['date_start'],
                'end_date': item.get('date_end',False)
            }
            
            #Dont check overlap in case:
            # old contract are probation, 
            #and new contract is include probation 
            #and new_start_date == old_state_date,
            #and (  (new_end_date = False and old_end_date is not null) or (new_end_date > old_end_date) )
            if item.get('contract_type_group_id', False):
                contract_type_group = contract_type_group_object.browse(cr, uid, item['contract_type_group_id'][0])
                if contract_type_group and contract_type_group.code == '1' \
                        and range_one['start_date'] == range_two['start_date'] \
                        and ( (range_one['end_date'] and range_two['end_date'] and self.compare_day(range_two['end_date'], range_one['end_date']) > 0) \
                              or ( not range_one['end_date'] and range_two['end_date'] ) )\
                        and val['include_probation']:
                    continue
            
            #In case contract are infinite contract, set date_end = today + 50 year to test :))
            test_end_date = (datetime.datetime.today() + relativedelta(years=50)).strftime(DEFAULT_SERVER_DATE_FORMAT)
            if not range_one['end_date']:
                range_one['end_date'] = test_end_date
                
            if not range_two['end_date']:
                range_two['end_date'] = test_end_date
            
            res = self.find_day_overlap(cr, uid, range_one, range_two, context)
            if res > 0:
                raise osv.except_osv('Validation Error !', 'The contract duration is overlapped. Please check again!')
        return True
    
    def get_date_start_real_for_create_write(self, cr, uid, vals, context=None):
        if vals.get('date_start_temp', False):
            date_start_temp = datetimes.strptime(vals['date_start_temp'], DEFAULT_SERVER_DATE_FORMAT).date()
            vals['date_start_real'] =  date_start_temp + relativedelta(days=1)
        elif vals.get('date_start', False):
            vals['date_start_real'] = vals['date_start']
        
        return vals
    
    def remove_working_record_part_if_no_change_form(self, cr, uid, vals, context=None):
        """
        Dont save timesheet/working group/salary in contract when not input change_form_id
        """
        if not vals.get('change_form_id', False) and vals.get('timesheet_id', False):
            del vals['timesheet_id']
            if 'salary_setting_id' in vals:
                del vals['salary_setting_id']
            
            if 'ts_working_group_id' in vals:
                del vals['ts_working_group_id']
        
        return vals
            
    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        if context.get('duplicate_active_id', False):
            update_val = {}
            if context.get('liquidation_date', False):
                update_val['liquidation_date'] = context['liquidation_date']
            if context.get('liquidation_reason', False):
                update_val['liquidation_reason'] = context['liquidation_reason']
            if context.get('renew_status', False):
                update_val['renew_status'] = context['renew_status']
            if update_val:
                self.write(cr, uid, [context['duplicate_active_id']], update_val, context=context)
        
        vals = self.get_date_start_real_for_create_write(cr, uid, vals, context)
        
        vals = self.remove_working_record_part_if_no_change_form(cr, uid, vals, context)
        
        if vals.get('date_start') and vals.get('type_id') and vals.get('employee_id'):
            if self.check_generate_code(cr, uid, vals['type_id'], vals['employee_id'], vals['date_start'], vals['company_id'], [], context):
                vals.update({'name': self.generate_code(cr, uid, vals['type_id'], vals['employee_id'], vals['date_start'], 
                                                                 vals['company_id'], [], context)})
        if 'date_start' in vals or 'date_end' in vals:
            self.validate_duration(cr, uid, vals, None, context)
        if vals.get('bank_account_ids', False):
            weight = 0
            count = 0
            for item in vals['bank_account_ids']:
                if item[2]['value_type'] == 'percent':
                    weight = weight + item[2]['weight']
                    count += 1
            if count > 0 and weight != 100:
                raise osv.except_osv('Validation Error !', 'Weight of banks must be equal 100%. Please check again!')
        #In case force to create working record, specific is from transfer RR, do not check condition next contract is Indefinite
        if vals.get('type_id', False) and not context.get('force_create_working_record', False):
            contract_type_obj = self.pool.get('hr.contract.type')
            type_id = vals.get('type_id')
            res_type = contract_type_obj.browse(cr, uid, type_id, context=context)
            if res_type and not (res_type.is_official and not res_type.life_of_contract):
                value = self.check_contract_type(cr, uid, [], vals.get('employee_id', False), vals.get('company_id', False), context=context)
                if value.get('is_indefinite', False):
                    raise osv.except_osv('Validation Error !', 'The Next Contract Is Indefinite Labour Contract!')

        res = super(hr_contract, self).create(cr, uid, vals, context)
        
        if res and context.get('create_directly_from_contract', False):
            self.button_set_to_waiting(cr, uid, [res], context)
            
            if context.get('renew_status', False) == 'renew' and  not vals.get('change_form_id', False):
                self.button_set_to_signed(cr, uid, [res], context)
            
            if vals.get('is_main', False):
                self.update_is_main_in_other_active_contract(cr, uid, vals.get('employee_id',False), res, context)
                self.update_is_main_in_other_future_contract(cr, uid, vals.get('employee_id',False), res, context)
            
        # Create working record when create contract, set effect_from = date_start
        if res and ( vals.get('change_form_id') or context.get('force_create_working_record', False)):
            context['create_vals'] = vals
            self.check_to_create_working_record(cr, uid, [res], context)
            
        return res
    
    def write(self, cr, uid, ids, vals, context=None):
        if not context:
            context = {}
        
        if not isinstance(ids, list):
            ids = [ids]
            
        if vals.get('result_ids', False):
            context['result_ids'] = vals['result_ids']
        
        if vals.get('mission_ids', False):
            context['mission_ids'] = vals['mission_ids']
            
        if context.get('ACTION', False) and vals.get('state', False):
            self.write_change_state(cr, uid, ids, context['ACTION'], context.get('ACTION_COMMENT', ''), context=context)
        
        if set(['date_start','date_end','employee_id','company_id','state']).intersection(vals.keys()) and not vals.get('state') == 'cancel':
            for item in ids:
                self.validate_duration(cr, uid, vals, item, context)
         
        vals = self.get_date_start_real_for_create_write(cr, uid, vals, context)
        
#         vals = self.remove_working_record_part_if_no_change_form(cr, uid, vals, context)
        
        #Check if contract type of contract is different with nearest signed contract at current company
        if vals.get('state', False) in ['signed','waiting']:
            self.check_if_not_belong_to_current_contract_type_group(cr, uid, ids, vals, context)
            
        bank_contract_obj = self.pool.get('vhr.bank.contract')
        if vals.get('bank_account_ids'):
            weight = 0
            count = 0
            list_ids = []
            list_unlink_ids = []
            for item in vals['bank_account_ids']:
                if item[0] == 0 and item[2] and item[2].get('value_type', False) == 'percent':
                    weight += item[2]['weight']
                    count += 1
                if item[0] == 1:
                    if item[2] and item[2].get('weight', -1) >= 0:
                        value_type = item[2].get('value_type', False)
                        if not value_type:
                            bank_acc = bank_contract_obj.browse(cr, uid, item[1], context=context)
                            value_type = bank_acc and bank_acc.value_type or False
                        if value_type == 'percent':
                            weight += item[2]['weight']
                            count += 1
                    else:
                        if item[1]:
                            list_ids.append(item[1])
                if item[0] == 4 and item[1]:
                    list_ids.append(item[1])
                if item[0] == 2:
                    list_unlink_ids.append(item[1])
                    vals['bank_account_ids'].remove(item)
            bank_contract_obj.unlink(cr, uid, list_unlink_ids, context=context)
            for bank_contract in bank_contract_obj.browse(cr, uid, list_ids):
                if bank_contract.value_type == 'percent':
                    weight += bank_contract.weight
                    count += 1

            if count > 0 and weight != 100:
                raise osv.except_osv('Validation Error !', 'Weight of banks must be equal 100%. Please check again!')

        contracts = []
        if vals and not context.get('update_from_working_record', False):
            contracts = self.read(cr, uid, ids, ['employee_id', 'company_id', 'first_working_record_id',
                                                 'date_start','effect_salary_id','job_applicant_id'])
            list_contracts = {}
            for contract in contracts:
                list_contracts[contract.get('id', False)] = contract
        if vals.get('date_start') or vals.get('type_id') or vals.get('employee_id'):
            date_start = vals.get('date_start', False)
            type_id = vals.get('type_id', False)
            employee_id = vals.get('employee_id', False)
            company_id = vals.get('company_id', False)
            for item in ids:
                cur_contract = self.read(cr, uid, item, ['date_start', 'type_id', 'employee_id', 'company_id'], context=context)
                if not date_start:
                    date_start = cur_contract['date_start']
                if not type_id:
                    type_id = cur_contract.get('type_id', False) and cur_contract['type_id'][0] or []
                if not employee_id:
                    employee_id = cur_contract.get('employee_id', False) and cur_contract['employee_id'][0] or []
                if not company_id:
                    company_id = cur_contract.get('company_id', False) and cur_contract['company_id'][0] or []
                if self.check_generate_code(cr, uid, type_id, employee_id, date_start, company_id, ids, context):
                    vals.update({'name': self.generate_code(cr, uid, type_id, employee_id, date_start, company_id, ids, context)})
                elif vals.has_key('name'):
                    del vals['name']
                res = super(hr_contract, self).write(cr, uid, item, vals, context)
        else:
            res = super(hr_contract, self).write(cr, uid, ids, vals, context)
        if res and vals and contracts and not context.get('update_from_working_record', False):
            context['include_not_signed_contract'] = True
            for item in ids:
                self.update_working_record(cr, uid, item, vals, list_contracts[item], context)
                
                #If change date start of contract chuyen doi cong ty, update effect_date of WR xu ly thoi viec noi bo
                if vals.get('date_start', False):
                    self.update_local_termination_working_record(cr, uid, item, vals, context=None)
                    self.update_termination_agreement_contract(cr, uid, item, vals, context=None)
                
                if vals.get('is_main', False):
                    contract = self.read(cr, uid, item, ['employee_id'])
                    employee_id = contract.get('employee_id',False) and contract['employee_id'][0] or False
                    self.update_is_main_in_other_active_contract(cr, uid, employee_id, item, context)
                    self.update_is_main_in_other_future_contract(cr, uid, employee_id, item, context)

        return res
    
    def check_if_not_belong_to_current_contract_type_group(self, cr, uid, ids, vals, context=None):
        """
        Check if employee is have a instance with date_end=False at company A, 
        new contract at A must be same value of is_official in contract type group
        """
        if ids:
            instance_obj = self.pool.get('vhr.employee.instance')
            contract_type_obj = self.pool.get('hr.contract.type')
            for record in self.browse(cr, uid, ids, context):
                employee_id = (vals.get('employee_id', False) and vals['employee_id'][0]) or (record.employee_id and record.employee_id.id or False)
                company_id = (vals.get('company_id', False) and vals['company_id'][0]) or (record.company_id and record.company_id.id or False)
                type_id = (vals.get('type_id', False) and vals['type_id'][0]) or (record.type_id and record.type_id.id or False)
                date_start = vals.get('date_start', record.date_start) or False
                
                if type_id:
                    contract_type = contract_type_obj.browse(cr, uid, type_id)
                    is_official_contract = contract_type.contract_type_group_id and contract_type.contract_type_group_id.is_offical
                                                
                    #Search if have instance
                    instance_ids = instance_obj.search(cr, uid, [('employee_id','=',employee_id),
                                                                 ('company_id','=',company_id),
                                                                 ('date_end','=',False)])
                    if instance_ids:
                        instance = instance_obj.read(cr, uid, instance_ids[0], ['date_start'])
                        date_start_instance = instance.get('date_start')
                        
                        #Search contract in same instance
                        contract_ids = self.search(cr, uid, [('employee_id','=',employee_id),
                                                             ('company_id','=',company_id),
                                                             ('date_start','>=',date_start_instance),
                                                             ('date_start','<=',date_start),
                                                             ('state','=','signed'),
                                                             ('id','!=',record.id)], order='date_start desc')
                        if contract_ids:
                            nearest_contract = self.browse(cr, uid, contract_ids[0], fields_process = ['type_id'])
                            is_official = nearest_contract.type_id and nearest_contract.type_id.contract_type_group_id\
                                            and nearest_contract.type_id.contract_type_group_id.is_offical
                                            
                            #If new contract have is_official different with is_official of nearest signed contract of same emp-comp, raise error
                            if is_official_contract != is_official:
                                raise osv.except_osv('Validation Error !', 'Please process terminaton of this employee before signing next contract !')
        
        return True
                    
            
    def update_is_main_in_other_active_contract(self, cr, uid, employee_id, contract_id, context=None):
        """
        Khi cập nhật "is_main"=True trên 1 HĐ Dang hieu luc thì set "is_main"=False cho những HĐ ĐANG HIỆU LỰC khác của NV
        """
        if employee_id and contract_id:
            today = fields.date.context_today(self, cr, uid)
            
            active_ids = self.search(cr, uid, [('employee_id','=',employee_id),
                                                      ('state','=','signed'),
                                                      ('date_start','<=',today),
                                                      '|','|',
                                                         '&',('date_end','=',False),('liquidation_date','=',False),
                                                         '&',('date_end','>=',today),('liquidation_date','=',False),
                                                             ('liquidation_date','>=',today),
                                                      ])
            
            if len(active_ids) > 1 and contract_id in active_ids:
                active_ids.remove(contract_id)
                super(hr_contract, self).write(cr, uid, active_ids, {'is_main': False})
        
        return True
    
    def update_is_main_in_other_future_contract(self, cr, uid, employee_id, contract_id, context=None):
        """
        Neu cập nhật "is_main"=True trên 1 HĐ tuong lai thì set "is_main"=False cho những HĐ Trong Tuong Lai khác của NV
        """
        if employee_id and contract_id:
            today = fields.date.context_today(self, cr, uid)
            
            future_ids = self.search(cr, uid, [('employee_id','=',employee_id),
                                                      ('state','=','signed'),
                                                      ('date_start','>',today),
                                                      ])
            if len(future_ids) > 1 and contract_id in future_ids:
                super(hr_contract, self).write(cr, uid, future_ids, {'is_main': False})
        
        return True
            

    def create_working_record(self, cr, uid, ids, vals, context=None):
        """
        Create first working record for contract
        """
        res = False
        if not context:
            context = {}
        if ids:
            working_pool = self.pool.get('vhr.working.record')
            working_record_columns = working_pool._columns
            working_record_fields = working_record_columns.keys()
            for record_id in ids:
                error_message = ''
                error_employees = ''
                context.update({'contract_id': record_id, 'record_type': 'record'})
                # get data from contract

                context['duplicate_active_id'] = False
                #Get basic information, do not get employee_id,effect_from,company_id from default_get of working record
                record_vals = working_pool.default_get(cr, uid, working_record_fields, context)

                data, context = self.get_data_from_contract(cr, uid, record_id, context)

                employee_id = data.get('employee_id', False)
                effect_from = data.get('effect_from', False)
                company_id = data.get('company_id', False)

                employee_name_related = ''
                employee_code = ''
                if employee_id:
                    employee = self.pool.get('hr.employee').read(cr, uid, employee_id, ['name_related', 'code'])
                    employee_name_related = employee.get('name_related', False)
                    employee_code = employee.get('code', False)

                context['create_from_outside'] = True
                # get data when onchange effect_from
                onchange_effect_from_data = working_pool.onchange_effect_from(cr, uid, [], effect_from, employee_id,
                                                                              company_id, False, False, False, False, True,
                                                                              False, False, False, context)
                # Raise error when can not find contract for employee on effect_from
                if onchange_effect_from_data.get('warning', False):
                    error_employees += "\n" + employee_name_related + " - " + employee_code
                    error_message = onchange_effect_from_data['warning'].get('message','')
                else:

                    onchange_effect_from_value = onchange_effect_from_data['value']
                    for field in onchange_effect_from_value.keys():
                        if isinstance(onchange_effect_from_value[field], tuple):
                            onchange_effect_from_value[field] = onchange_effect_from_value[field][0]

                    record_vals.update(onchange_effect_from_value)


                    record_vals.update(data)
                    
                    #In case transfer from RR, get job family,group, sub group for WR from RR context
#                     fields = ['job_family_id','job_group_id', 'sub_group_id']
#                     if set(fields).intersection(context.keys()):
#                         for field in fields:
#                             record_vals['pro_' + field + '_new'] = context.get(field, False)
                    
                    try:
                        context['create_from_contract'] = True
#                       res = working_pool.create        (cr, uid, record_vals, context)
                        res = working_pool.create_with_log(cr, uid, record_vals, context)
                        if res:
                            super(hr_contract, self).write(cr, uid, record_id, {'first_working_record_id': res})
                    except Exception as e:
                        log.exception(e)
                        try:
                            error_message = e.message
                            if not error_message:
                                error_message = e.value
                        except:
                            error_message = ""
                        
                        if 'Have error during create working record' in error_message:
                            error_message = error_message.replace("('Validation Error !", '').replace("Have error during create working record:", '')\
                                                         .replace("Have error during update working record:", '')
                            # Can not replace '\n' by normal way
                            error_message = error_message[2:]
                        #Remove  !!') in error_message
                        if "!!')" in error_message:
                            error_message = error_message.replace("!!')", '')
                
                        error_employees += "\n" + employee_name_related + " - " + employee_code

                if error_employees:
                    effect_from = datetimes.strptime(effect_from,DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y")
                    raise osv.except_osv('Validation Error !',
                                         "Can't create working record effect on %s for following employees: %s\
                                         \n\n\n\n Trace Log: %s" % (
                                             effect_from, error_employees, error_message))

        return res
    
    
    def update_local_termination_working_record(self, cr, uid, contract_id, vals, context=None):
        """
        Cập nhật effect_from của WR xử lý thôi việc nội bộ khi cập nhật date_start của Contract chuyển đổi công ty
        """
        if contract_id and vals.get('date_start', False):
            #Search WR xu ly thoi viec noi bo bang field  contract_id_change_local_company
            working_pool = self.pool.get('vhr.working.record')
            wr_ids = working_pool.search(cr, uid, [('contract_id_change_local_company','=',contract_id)])
            if wr_ids:
                date_liquidation = (datetimes.strptime(vals.get('date_start', False), DEFAULT_SERVER_DATE_FORMAT) - relativedelta(days=1)).strftime(DEFAULT_SERVER_DATE_FORMAT)
                working_pool.write_with_log(cr, uid, wr_ids, {'effect_from': date_liquidation})
        
        return True
    
    def update_termination_agreement_contract(self, cr, uid, contract_id, vals, context=None):
        """
        Cập nhật lại effect_date của Thỏa thuận 3 bên khi cập nhật date_start của contract chuyển đổi công ty
        """
        if contract_id and vals.get('date_start', False):
            agreement_pool = self.pool.get('vhr.termination.agreement.contract')
            agree_ids = agreement_pool.search(cr, uid, [('new_contract_id','=',contract_id)])
            if agree_ids:
                agreement_pool.write(cr, uid, agree_ids, {'effect_date': vals['date_start']})
        
        return True
        
    def update_working_record(self, cr, uid, contract_id, vals, contract, context=None):
        """
            Không cho sửa date_start mới >= effect_from của working record gần nhất trong tương lai.
            Trong trường hợp sửa lại employee_id - company_id:
             - Nếu contract có nhiều hơn 1 Working Record gắn tới nó(không tính wr được tạo khi contract được signed) thì không cho sửa.
             - Nếu kể từ thời điểm bắt đầu hợp đồng có working record (có effect_from > date_start_contract) thì không cho sửa.
             - Nếu là contract cũ (có contract có date_start lớn hơn) thì không cho sửa
             
             - Nếu ban đầu contract có gắn với first working record:
               + Nếu cặp employee - company mới không có gắn change form(ko show ra change form để chọn) 
                 tức là hd mới là dạng hd bình thường không có first working record ===> Xóa first working record gắn với contract.
               + Nếu cặp employee - company mới có gắn với change form(show ra field change form để chọn)
                 tức là hd mới của cặp emp-com là hd gia nhap cty/back to work ==> Sẽ có first working record gắn với nó, 
                 nên sẽ xóa first wr trước và tạo first wr mới gắn với cặp emp-com mới
                 
            - Nếu ban đầu contract không gắn với first working record (không có working record nào, dựa trên các rule phía trên):
               + Nếu cặp emp-com mới có gắn với change form (show ra field change form để chọn)
                 ===> sẽ có first working record gắn với contract đó, nên sẽ tạo ra first wr gắn với contract.
            
            Trong trường hợp sửa các field khác của contract có first working record thì sẽ cập nhật cho phần New của first working record 
            và phần Old của working record gần first wr nhất(greater)
        """
        try:
            if not context:
                context = {}
            
            context['include_not_signed_contract'] = True
            
            #i dont remember why do i use another context for unlink WR, -_-
            s_context = {'update_from_contract': True,
                         'include_not_signed_contract': context.get('include_not_signed_contract', False),
                         'update_from_candidate': context.get('update_from_candidate', False),
                         }
            
            working_pool = self.pool.get('vhr.working.record')
            salary_pool = self.pool.get('vhr.pr.salary')

            if contract_id and vals and contract and not (len(vals) == 1 and vals.get('first_working_record_id', False)):
                new_contract_data = self.browse(cr, uid, contract_id)
                new_change_form_id = new_contract_data.change_form_id and new_contract_data.change_form_id.id or False
                new_state = new_contract_data.state
                new_contract_date_start = new_contract_data.date_start
                
                #Field job_applicant_id create in module vhr_recruitment, carefull to use this field in vhr_human_resource
                job_applicant_id = contract.get('job_applicant_id', False) and contract['job_applicant_id'][0] or False
                
                contract_employee_id = contract.get('employee_id', False) and contract['employee_id'][0]
                contract_company_id = contract.get('company_id', False) and contract['company_id'][0]
                contract_first_wr_id = contract.get('first_working_record_id', False) and \
                                       contract['first_working_record_id'][0]
                contract_date_start = contract.get('date_start', False)
                
                #If contract is old(have contract with greater date_start) ==> raise error
                if (vals.get('company_id', False) and vals.get('company_id', False) != contract_company_id) or (vals.get('employee_id', False) and vals.get('employee_id', False) != contract_employee_id):
                    new_contract_ids = self.search(cr, uid,  [('employee_id','=',contract_employee_id),
                                                              ('company_id','=',contract_company_id),
                                                              ('state','in',['draft','waiting','signed']),
                                                              ('date_start','>',contract_date_start)])
                    if new_contract_ids:
                        raise osv.except_osv('Validation Error !',
                                                 'You cannot change company(employee) of old contract. Please check again !')
                    
                record_same_contract_ids = working_pool.search(cr, uid, [('contract_id', '=', contract_id),
                                                                         ('state','in',['finish',False]),
                                                                         '|', ('active', '=', True),
                                                                         ('active', '=', False)],
                                                               order='effect_from asc')
                #Have Working Record assign with contract
                if record_same_contract_ids:
    
                    begin_working_record = working_pool.read(cr, uid, record_same_contract_ids[0],['effect_from', 'employee_id', 'company_id'])
                    effect_from = begin_working_record.get('effect_from', False)
                    employee_id = begin_working_record.get('employee_id', False) and begin_working_record['employee_id'][0]
                    company_id = begin_working_record.get('company_id', False) and begin_working_record['company_id'][0]
    
                    wr_vals = {}
                    #Change to new employee -company
                    if (vals.get('company_id', False) and vals.get('company_id', False) != contract_company_id) or (vals.get('employee_id', False) and vals.get('employee_id', False) != contract_employee_id):
                        #Code in above if controller is for case change to new employee-company of contract have first working record
                        if not contract_first_wr_id:
                            raise osv.except_osv('Validation Error !',
                                                 'You cannot change company(employee) of contract. Please check again !')
                        
                        fail_update_wr = False
                        # If contract have WR link to it(not count first wr), raise error
                        if len(record_same_contract_ids) == 1:
                            record_effect_from_larger = working_pool.search(cr, uid, [('effect_from', '>', effect_from),
                                                                                      ('employee_id', '=', employee_id),
                                                                                      ('company_id', '=', company_id),
                                                                                      ('state','in',[False,'finish'])])
                            if record_effect_from_larger:
                                fail_update_wr = True
                        else:
                            fail_update_wr = True
    
                        if fail_update_wr:
                            raise osv.except_osv('Validation Error !',
                                                 "You cannot change company(employee) of contract because already existed more than one working records !")
                        else:
                            
                            #Case new change form = null --> delete first working record assign with it
                            #Case change emp - company of contract transfer from RR ===> delete old WR, create new WR like case have data in change_form_id
                            if 'change_form_id' in vals and not vals.get('change_form_id', False) and not job_applicant_id:
                                try:
                                    working_pool.unlink(cr, uid, contract_first_wr_id, s_context)
                                    return True
                                except Exception as e:
                                    log.exception(e)
                                    try:
                                        error_message = e.message
                                        if not error_message:
                                            error_message = e.value
                                    except:
                                        error_message = ""
                                    raise osv.except_osv('Error !',' \n %s'% error_message)
                                
                            #Casenew change form != null --> delete first working record assign with it, create new first wr assign with new emp-comp
                            elif ('change_form_id' in vals and vals.get('change_form_id', False)) or new_change_form_id or job_applicant_id:
                                try:
                                    #If dont change employee, map new WR to old Employee timesheet
                                    #if change employee, delete old employee timesheet, and new WR will auto create new one
                                    wr_data = working_pool.read(cr, uid, contract_first_wr_id, ['ts_emp_timesheet_id'])
                                    ts_emp_timesheet_id = wr_data.get('ts_emp_timesheet_id', False) and wr_data['ts_emp_timesheet_id'][0] or False
                                    if not (vals.get('employee_id', False) and vals.get('employee_id', False) != contract_employee_id) and ts_emp_timesheet_id:
                                        context['ts_emp_timesheet_id'] = ts_emp_timesheet_id
                                    
                                    #If old contract have salary and change emp-comp need to update data in salary(company)
                                    old_salary_data = False
                                    effect_salary_id = contract.get('effect_salary_id', False) and contract['effect_salary_id'][0] or False
                                    
                                    if effect_salary_id and salary_pool:
                                        new_salary_id = new_contract_data.effect_salary_id and new_contract_data.effect_salary_id.id or False
                                        if new_salary_id:
                                            salary = salary_pool.read(cr, uid, new_salary_id, ['effect_from'])
                                            salary_effect_from = salary.get('effect_from', False)
                                            if salary_effect_from and new_contract_date_start and self.compare_day(salary_effect_from, new_contract_date_start) != 0:
                                                old_salary_data = salary_pool.copy_data(cr, SUPERUSER_ID, effect_salary_id)
                                        else:
                                            old_salary_data = salary_pool.copy_data(cr, SUPERUSER_ID, effect_salary_id)
                                    
                                    #Only unlink WR, dont unlink salary, employeetimesheet link to it
                                    working_pool.unlink(cr, uid, contract_first_wr_id, s_context)
                                    
                                    if not context.get('ts_emp_timesheet_id', False) and ts_emp_timesheet_id:
                                        self.pool.get('vhr.ts.emp.timesheet').unlink(cr, uid, ts_emp_timesheet_id)
                                    
                                    if old_salary_data:
                                        salary_pool.unlink(cr, SUPERUSER_ID, effect_salary_id)
                                        
                                        self.create_payroll_salary_from_data(cr, uid, contract_id, old_salary_data, context)
                                        
                                    #To push data to employee again in Working Record
                                    context['effect_date'] = contract_date_start
                                    self.create_working_record(cr, uid, [contract_id], {}, context)
                                    return True
                                except Exception as e:
                                    log.exception(e)
                                    try:
                                        error_message = e.message
                                        if not error_message:
                                            error_message = e.value
                                    except:
                                        error_message = ""
                                    raise osv.except_osv('Error !',' \n %s'% error_message)
    
                    # If dont have first_wr_id in contract, when update info different emp-comp, dont do any thing
                    if not contract_first_wr_id:
                        return True
    
                    if vals.get('date_end', False):
                        # Do not allow to update date_end if have working record have effect_from > vals['date_end']
                        record_ids = working_pool.search(cr, uid, [('contract_id', '=', contract_id),
                                                                   ('effect_from', '>', vals['date_end']),
                                                                   '|', ('active', '=', True),
                                                                   ('active', '=', False)])
                        if record_ids:
                            raise osv.except_osv('Validation Error !',
                                                 "You cannot update expired date of contract which already existed working records not in new duration !")
                    
                    #Change contract date_start
                    if vals.get('date_start', False):
                        if len(record_same_contract_ids) > 1:
                            nearest_future_working = working_pool.read(cr, uid, record_same_contract_ids[1],
                                                                       ['effect_from'])
                            nearest_future_effect_from = nearest_future_working.get('effect_from', False)
                            nearest_future_effect_from = datetimes.strptime(nearest_future_effect_from,
                                                                            DEFAULT_SERVER_DATE_FORMAT).date()
    
                            date_start = datetimes.strptime(vals['date_start'], DEFAULT_SERVER_DATE_FORMAT).date()
    
                            if date_start >= nearest_future_effect_from:
                                raise osv.except_osv('Validation Error !',
                                                     "You cannot update effective date of contract which already existed working records in future. Please delete those working records firstly !")
                        
                    if contract_first_wr_id:
                        for field in vals.keys():
                            if field in translate_contract_to_wr_dict.keys():
                                if field == 'change_form_id':
                                    change_form_ids = vals.get(field,False) and [vals[field]] or []
                                    wr_vals[translate_contract_to_wr_dict[field]] = [[6,False,change_form_ids]]
                                else:
                                    wr_vals[translate_contract_to_wr_dict[field]] = vals[field]
#                             if field in ['division_id', 'department_id','department_group_id']:
#                                 wr_vals['team_id_new'] = False
                            elif field == 'job_title_id_new':
                                wr_vals['job_level_id_new'] = False
        
                        if wr_vals:
                            fields = ['job_family_id','job_group_id', 'sub_group_id']
                            
                            if set(fields).intersection(vals.keys()):
                                job_family_id = new_contract_data.job_family_id and new_contract_data.job_family_id.id or False
                                wr_vals['pro_job_family_id_new'] = job_family_id
                                
                                job_group_id = new_contract_data.job_group_id and new_contract_data.job_group_id.id or False
                                wr_vals['pro_job_group_id_new'] = job_group_id
                                
                                sub_group_id = new_contract_data.sub_group_id and new_contract_data.sub_group_id.id or False
                                wr_vals['pro_sub_group_id_new'] = sub_group_id
                                
                            #In case transfer from RR, get job family,group, sub group for WR from RR context
#                             if set(fields).intersection(context.keys()):
#                                 for field in fields:
#                                     wr_vals['pro_' + field + '_new'] = context.get(field, False)
                                    
#                                   working_pool.write(cr, uid, record_same_contract_ids[0], wr_vals,{'update_from_contract': True})
                            working_pool.write_with_log(cr, uid, record_same_contract_ids[0], wr_vals, s_context)
                
                #Case dont have any working record link to it and change to new employee - company
                elif (vals.get('company_id', False) and vals.get('company_id', False) != contract_company_id) or (vals.get('employee_id', False) and vals.get('employee_id', False) != contract_employee_id):
                    if 'change_form_id' in vals and vals.get('change_form_id', False) and new_state == 'signed':
                        try:
                            self.create_working_record(cr, uid, [contract_id], {}, context)
                            return True
                        except Exception as e:
                            log.exception(e)
                            try:
                                error_message = e.message
                                if not error_message:
                                    error_message = e.value
                            except:
                                error_message = ""
                            raise osv.except_osv('Error !',' \n %s'% error_message)
                    
            return True
        except Exception as e:
            log.exception(e)
            error_message = ''
            try:
                error_message = e.message
                if not error_message:
                    error_message = e.value
            except:
                error_message = ""
            
            error_message = error_message.replace("('Validation Error !", '') .replace("Have error during update working record:", '')
                                         
            raise osv.except_osv('Validation Error !', 'Have error during update first working record from contract:\n %s!' % error_message)
        
    def create_payroll_salary_from_data(self, cr, uid, contract_id, data, context=None):
        """
        Override function in vhr.payroll
        """
        return True
    
    
    def create_termination_agreement_contract(self, cr, uid, contract, context=None):
        if contract:
            termination_agreement_pool = self.pool.get('vhr.termination.agreement.contract')
            employee_id = contract.employee_id and contract.employee_id.id or False
            date_start_contract = contract.date_start
#             date_liquidation = (datetimes.strptime(date_start_contract, DEFAULT_SERVER_DATE_FORMAT) - relativedelta(days=1)).strftime(DEFAULT_SERVER_DATE_FORMAT)

            #get company from contract
            company_id = contract.company_id and contract.company_id.id or False
            join_date = contract.employee_id and contract.employee_id.join_date
            seniority = self.pool.get('vhr.termination.agreement.contract').get_gap_year(cr, uid, join_date, date_start_contract)
            
            agreement_ids = termination_agreement_pool.search(cr, uid, [('employee_id','=',employee_id),
                                                                            ('effect_date','=',date_start_contract)])
            if not agreement_ids:
                #Get data of old contract in termination agreement contract
                contract_ids = self.search(cr, uid,  [('employee_id','=',employee_id),
                                                    ('company_id','!=',company_id),
                                                      ('state','=','signed'),
                                                      ('date_start','<=',date_start_contract),
                                                      '|','|',
                                                              ('date_end','=',False),
                                                          '&',('date_end','>=',date_start_contract),('liquidation_date','=',False),
                                                              ('liquidation_date','>=',date_start_contract)], order='date_start_real desc, date_start desc')
                
                if contract_ids:
                    vals = {'employee_id': employee_id, 'join_date': join_date, 'effect_date': date_start_contract,
                            'old_contract_id': contract_ids[0], 'new_contract_id': contract.id, 'seniority':seniority}
                    
                    termination_agreement_pool.create(cr, uid, vals, context)
        
        return True
            
        
    def create_local_terminate_working_record(self, cr, uid, contract, context=None):
        """
        Tạo ra những working record bắt đầu từ contract.date_start -1 với loại change form Chuyển đổi công ty(Xử lý thôi việc)
        cho những công ty đang có hợp đồng hiệu lực vào ngày contract.date_start -1
        """
        if contract:
            employee_id = contract.employee_id and contract.employee_id.id or False
            company_id = contract.company_id and contract.company_id.id or False
            date_start_contract = contract.date_start
            if employee_id and company_id and date_start_contract:
                parameter_obj = self.pool.get('ir.config_parameter')
                working_pool = self.pool.get('vhr.working.record')
                
                change_form_terminated_code = parameter_obj.get_param(cr, uid, 'vhr_master_data_dismiss_local_company') or ''
                change_form_terminated_code = change_form_terminated_code.split(',')
                dismiss_change_form_ids = self.pool.get('vhr.change.form').search(cr, uid, [('code', 'in', change_form_terminated_code)],context=context)
                
                if not dismiss_change_form_ids:
                    raise osv.except_osv('Validation Error !',"Can't find change form 'Chuyển đổi công ty(Xử lý thôi việc)'")
                date_liquidation = (datetimes.strptime(date_start_contract, DEFAULT_SERVER_DATE_FORMAT) - relativedelta(days=1)).strftime(DEFAULT_SERVER_DATE_FORMAT)
                #Get company from active contract at effect_from
                default_company_id, company_ids = working_pool.get_company_ids(cr, uid, employee_id, context={'effect_date':date_liquidation})
                
                if company_ids:
                    for company_id in company_ids:
                        error_employees = ''
                        
                        effect_from = date_liquidation
                        record_vals = {'employee_id': employee_id, 'company_id': company_id, 'effect_from':effect_from}
                        employee_name_related = ''
                        employee_code = ''
                        if employee_id:
                            employee = self.pool.get('hr.employee').read(cr, uid, employee_id, ['name_related', 'code'])
                            employee_name_related = employee.get('name_related', False)
                            employee_code = employee.get('code', False)
        
                            # get data when onchange effect_from
                        context['create_from_outside'] = True
                        onchange_effect_from_data = working_pool.onchange_effect_from(cr, uid, [], effect_from, employee_id,
                                                                                      company_id, False, False, False, False, True,
                                                                                      False, False, False, context)
                        # Raise error when can not find contract for employee on effect_from
                        if onchange_effect_from_data.get('warning', False):
                            error_employees += "\n" + employee_name_related + " - " + employee_code
                            error_message = onchange_effect_from_data['warning'].get('message', '')
                        else:
                            onchange_effect_from_value = onchange_effect_from_data['value']
                            for field in onchange_effect_from_value.keys():
                                if isinstance(onchange_effect_from_value[field], tuple):
                                    onchange_effect_from_value[field] = onchange_effect_from_value[field][0]
        
                            record_vals.update(onchange_effect_from_value)
        
                            # TODO: delete change_form_id in future
                            change_form_ids = [dismiss_change_form_ids[0]]
                            record_vals['change_form_ids'] = [[6, False, change_form_ids]]
                            
                            record_vals['contract_id_change_local_company'] = contract.id
                            try:
#                               res =         working_pool.create(cr, uid, record_vals, context)
                                res = working_pool.create_with_log(cr, uid, record_vals, context)
                            except Exception as e:
                                log.exception(e)
                                try:
                                    error_message = e.message
                                    if not error_message:
                                        error_message = e.value
                                except:
                                    error_message = ""
                                error_employees += "\n" + employee_name_related + " - " + employee_code
        
                        if error_employees:
                            effect_from = datetimes.strptime(effect_from, DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y")
                            raise osv.except_osv('Validation Error !',
                                                 "Can't create working record effect on %s for following employees: %s\
                                                 \n\n\n\n Trace Log: %s" % (effect_from, error_employees, error_message))
        
        return True
    
    def get_data_from_contract(self, cr, uid, record_id, context=None):
        """
         When add field for update to WR, remember to insert into translate_dict of function update_working_record
        """
        if not context:
            context = {}
        res = {}
        if record_id:
            contract_columns = self._columns
            contract_fields = contract_columns.keys()
            contract = self.read(cr, SUPERUSER_ID, record_id, contract_fields)
            res['employee_id'] = contract.get('employee_id', False) and contract['employee_id'][0]
            res['company_id'] = contract.get('company_id', False) and contract['company_id'][0]
            res['work_for_company_id_new'] = res['company_id']
            date_start = contract.get('date_start', False)
            if contract.get('include_probation', False):
                contract_ids = self.search(cr, uid, [
                    ('employee_id', '=', res['employee_id']), ('date_start', '=', date_start),
                    ('id', '!=', record_id), ('company_id', '=', res['company_id'])], context=context)
                if contract_ids:
                    probation_contract = self.browse(cr, uid, contract_ids[0], fields_process=['date_end'])
                    if probation_contract and probation_contract.date_end:
                        date_end_probation = probation_contract.date_end
                        date_start = datetimes.strptime(date_end_probation, '%Y-%m-%d') + relativedelta(days=1)
                        date_start = date_start.strftime('%Y-%m-%d')
            res['effect_from'] = date_start
            res['office_id_new'] = contract.get('office_id', False) and contract['office_id'][0]
            res['division_id_new'] = contract.get('division_id', False) and contract['division_id'][0]
            res['department_group_id_new'] = contract.get('department_group_id', False) and contract['department_group_id'][0]
            res['department_id_new'] = contract.get('department_id', False) and contract['department_id'][0]
            res['team_id_new'] = contract.get('team_id', False) and contract['team_id'][0]
            
            res['job_title_id_new'] = contract.get('title_id', False) and contract['title_id'][0]
#             res['job_level_id_new'] = contract.get('job_level_id', False) and contract['job_level_id'][0]
            
#             res['job_level_position_id_new'] = contract.get('job_level_position_id', False) and contract['job_level_position_id'][0]
            res['job_level_person_id_new'] = contract.get('job_level_person_id', False) and contract['job_level_person_id'][0]
            
#             if not res.get('job_level_person_id_new', False):
#                 res['job_level_person_id_new'] = res['job_level_position_id_new']
            
            res['report_to_new'] = contract.get('report_to', False) and contract['report_to'][0]
            res['manager_id_new'] = contract.get('manager_id', False) and contract['manager_id'][0]
            res['seat_new'] = contract.get('seat_no', False)
            res['ext_new'] = contract.get('ext_no', False)
            res['work_email_new'] = contract.get('work_email', False)
            res['mobile_phone_new'] = contract.get('mobile_phone', False)
            res['work_phone_new'] = contract.get('work_phone', False)
            res['signer_id'] = contract.get('info_signer', '')
            res['sign_date'] = contract.get('sign_date', False)
            res['signer_job_title_id'] = contract.get('title_signer', '')
            res['country_signer'] = contract.get('country_signer', False) and contract['country_signer'][0] or False
            
            res['career_track_id_new'] = contract.get('career_track_id', False) and contract['career_track_id'][0] or False
            res['pro_job_family_id_new'] = contract.get('job_family_id', False) and contract['job_family_id'][0] or False
            res['pro_job_group_id_new'] = contract.get('job_group_id', False) and contract['job_group_id'][0] or False
            res['pro_sub_group_id_new'] = contract.get('sub_group_id', False) and contract['sub_group_id'][0] or False
            
#             res['position_class_id_new'] = contract.get('position_class_id', False) and contract['position_class_id'][0]
            
            res['ts_working_group_id_new'] = contract.get('ts_working_group_id', False) and contract['ts_working_group_id'][0] or False
            res['timesheet_id_new'] = contract.get('timesheet_id', False) and contract['timesheet_id'][0] or False
            res['salary_setting_id_new'] = contract.get('salary_setting_id', False) and contract['salary_setting_id'][0] or False
            #TODO: delete change_form_id in future
            res['change_form_id'] = contract.get('change_form_id', False) and contract['change_form_id'][0] or False
            change_form_ids = res['change_form_id'] and [res['change_form_id']] or []
            res['change_form_ids'] = [[6,False,change_form_ids]]
            
            
            
            #Update old salary in Working Record from record have lower effect_from
            if contract.get('effect_salary_id', False) and (contract.get('change_form_id', False) or contract.get('job_applicant_id',False)):
                context['update_old_salary_from_old_pr_salary'] = True
                
                #Save payroll_salary_id into Working Record if have created payroll salary 
                payroll_salary_id = contract.get('effect_salary_id', False) and contract['effect_salary_id'][0] or False
                if payroll_salary_id:
                    salary = self.pool.get('vhr.pr.salary').read(cr, uid, payroll_salary_id, ['effect_from'])
                    salary_effect_from = salary.get('effect_from', False)
                    if salary_effect_from and date_start and self.compare_day(salary_effect_from, date_start) == 0:
                        res['payroll_salary_id'] = payroll_salary_id
            
            #Case: change company-employee, need to unlink old WR to create new WR ===> map new WR to old employee timesheet
            if context.get('ts_emp_timesheet_id', False):
                res['ts_emp_timesheet_id'] = context['ts_emp_timesheet_id']
                context['update_old_timesheet_from_old_emp_timesheet'] = True
                
        return res, context


    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
            
        args_new = [('name', operator, name)] + args
        ids = self.search(cr, uid, args_new, 0, None, None, context)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(hr_contract, self).name_search(cr, uid, name, args, operator, context, limit)
    
    def name_get(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        res = []
        res = super(hr_contract, self).name_get(cr, uid, ids, context)
        return res
    
    def read(self, cr, user, ids, fields=None, context=None, load='_classic_read'):
        if not context:
            context = {}
        
        groups = self.pool.get('res.users').get_groups(cr, user)
        
        allow_fields = ['employee_id','company_id','is_main','date_start','date_end','life_of_contract',
                        'department_id','type_id','liquidation_date','contract_type_group_id']
        self.prevent_normal_emp_read_data_of_other_emp(cr, user, ids, groups, allow_fields, fields, context)
        
        if context.get('validate_read_hr_contract',False):
            log.info('\n\n validate_read_hr_contract')
            if not context.get('filter_by_group', False):
                context['filter_by_group'] = True
            result_check = self.validate_read(cr, user, ids, context)
            if not result_check:
                raise osv.except_osv('Validation Error !', 'You don’t have permission to access this data !')
            del context['validate_read_hr_contract']
        
        #Do not filter anymore in search function of other models
        context['filter_by_group'] = False
        
        is_have_audit_log_field = False
        if not set(groups).intersection(['hrs_group_system','vhr_cb_contract']) and 'audit_log_ids' in fields:
            fields.remove('audit_log_ids')
            is_have_audit_log_field = True
        
        if context.get('get_department_name_by_code', False) and len(fields) > 1:
            if not (set(['division_id','department_id','department_group_id']).intersection(fields)):
                context['get_department_name_by_code'] = False
            
        res =  super(hr_contract, self).read(cr, user, ids, fields, context, load)
    
        if res and is_have_audit_log_field:
            if isinstance(res, list):
                for data in res:
                    if data:
                        data['audit_log_ids'] = []
            else:
                res['audit_log_ids'] = []
        
        return res
    
    
    def validate_read(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        user_groups = self.pool.get('res.users').get_groups(cr, uid)
        if set(['hrs_group_system', 'vhr_cnb_manager']).intersection(set(user_groups)):
            return True
        if isinstance(ids, (int, long)) or (isinstance(ids, list) and len(ids)) == 1:
            check_id = ids
            if isinstance(ids, list):
                check_id = ids[0]
            new_context = context and context.copy() or {}
            lst_check = self.search(cr, uid, [], context=new_context)
            if check_id not in lst_check:
                return False
        return True

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if not context:
            context = {}
        
        if 'active_test' not in context:
            context['active_test'] = False
#       Filter employee base on login user and group of that user (filter by context['filter_by_group'] in function
        if context.get('filter_by_group', False) or context.get('force_search_hr_contract', False):
            if context.get('force_search_hr_contract', False):
                del context['force_search_hr_contract']
                if not context.get('filter_by_group', False):
                    context['filter_by_group'] = True
                
#             print "\n filter by group in contract"
            #do not filter with dep admin for contract
            context['do_not_filter_for_dept_admin'] = True
            args = self.get_domain_for_object_base_on_groups(cr, uid, args, self._name, context)
            context['filter_by_group'] = False
            context['turn_on_filter_contract_after_call_super'] = True
            
            #Filter list contract based on permisison location
            domain = self.get_domain_contract_can_used_based_on_permission_location(cr, uid, uid, context)
            if domain:
                args.extend(domain)
            
        contract_ids = super(hr_contract, self).search(cr, uid, args, offset, limit, order, context, count)
        
        if context.get('turn_on_filter_contract_after_call_super', False):
            context['filter_by_group'] = True
            context['turn_on_filter_contract_after_call_super'] = False
        
#         print contract_ids
        return contract_ids
    
    def get_domain_contract_can_used_based_on_permission_location(self, cr, uid, user_id, context=None):
        """
        return domain to search contract based on permission location
        """
        res = []
        if user_id:
            permission_obj = self.pool.get('vhr.permission.location')
            working_obj = self.pool.get('vhr.working.record')
            employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=',user_id)])
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
                            res.append(('employee_id','in',employee_ids))
                        
        return res
                    

    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False,
                   lazy=True):
        
        if 'active_test' not in context:
            context['active_test'] = False
        
        if not orderby:
            orderby = 'state desc'
#       Filter employee base on login user and group of that user (filter by context['filter_by_group'] in function
        if context.get('filter_by_group', False):
            #do not filter with dep admin for contract
            context['do_not_filter_for_dept_admin'] = True
            domain = self.get_domain_for_object_base_on_groups(cr, uid, domain, self._name, context)
            context['filter_by_group'] = False
            context['turn_on_filter_after_call_super'] = True
            
            #Filter list contract based on permisison location
            ex_domain = self.get_domain_contract_can_used_based_on_permission_location(cr, uid, uid, context)
            if ex_domain:
                domain.extend(ex_domain)

        res = super(hr_contract, self).read_group(cr, uid, domain, fields, groupby, offset, limit, context, orderby,
                                                   lazy)
        
        if context.get('turn_on_filter_after_call_super', False):
            context['filter_by_group'] = True
            context['turn_on_filter_after_call_super'] = False
        return res

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        for contract in self.browse(cr, uid, ids, context=context):
            if contract.state != 'draft':
                raise osv.except_osv('Validation Error !', 'You can only delete Contract(s) with draft state!')
        try:
            res = super(hr_contract, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res

    def check_on_change_one2many(self, cr, uid, ids, model, field_name, datas, field_domain, context=None):
        list_ids = []

        if ids:
            this = self.read(cr, uid, ids[0], [field_domain])
            if this and this[field_domain]:
                list_ids = list(set(this[field_domain] + list_ids))

        if field_name and datas and len(datas) > 0:
            for data in datas:
                if len(data) == 3 and data[2]:
                    if (data[0] in [0, 1]) and isinstance(data[2], dict) and data[2].get(field_name, False):
                        if data[0] == 1:
                            ac_obj = self.pool.get(model).read(cr, uid, data[1], [field_name])
                            if ac_obj and ac_obj[field_name][0] in list_ids:
                                list_ids.remove(ac_obj[field_name][0])
                        list_ids.append(data[2].get(field_name))
                if len(data) >= 2 and data[0] == 2 and data[1]:
                    ac_obj = self.pool.get(model).read(cr, uid, data[1], [field_name])
                    if ac_obj and ac_obj[field_name][0] in list_ids:
                        list_ids.remove(ac_obj[field_name][0])
        return {'value': {field_domain: list_ids}}

    def check_contract_type(self, cr, uid, ids, emp_id, com_id, context=None):
        if not context:
            context = {}
            
        user_obj = self.pool.get('res.users')
        emp_instance_obj = self.pool.get('vhr.employee.instance')
        #Khong xac dinh thoi han
        is_indefinite = None
        ignore_group_code = ''
        #Official
        is_official = None
        remove_indefinite = None
#         if ids:
#             res_contract = self.browse(cr, uid, ids[0], context=context)
#             #Contract type group HĐLĐ Không xác định thời hạn
#             if res_contract.type_id.contract_type_group_id.code == '4':
#                 is_indefinite = True
#             else:
#                 is_indefinite = False

        if emp_id and com_id:
            date_start_contract = False
            if ids and context.get('date_start', False):
                date_start_contract = context['date_start']
            
            #Get employee instance have date_end = False of emp - comp
            emp_inst_ids = emp_instance_obj.search(cr, uid, [('employee_id', '=', emp_id), 
                                                             ('company_id', '=', com_id), 
                                                             ('date_end', '=', False)
                                                            ], order='date_start desc', limit=1, context=context)
            if emp_inst_ids:
                res_inst = emp_instance_obj.browse(cr, uid, emp_inst_ids[0], context=context)
                date_start = res_inst and res_inst.date_start or None
                if not date_start:
                    is_indefinite = False
                else:
                    contract_domain = [('employee_id', '=', emp_id), 
                                       ('company_id', '=', com_id), 
                                       ('date_start', '>=', date_start),
                                       ('state', '=', 'signed')
                                       ]
                    #Search all contract of employee instance, order by date_start descending
                    if date_start_contract:
                        contract_domain.extend([('date_start','<=',date_start_contract),('id','not in',ids)])
                    contract_ids = self.search(cr, uid, contract_domain,order='date_start desc,id desc', context=context)
                    count = 0
                    is_have_probation_contract = False
                    #We only check 2 latest contract to decide list type of contract will be choose
                    #If 2 latest contract are official and not probation, next contract must be indefinite
                    #if 2 latest contract are official and 1 contract is probation, next contract must be official
                    #If data is wrong like 2 latest contract in instance duration is official and not official, next contract will have type from contract have lower date_start 
                    for contract in self.browse(cr, uid, contract_ids, context=context):
                        contract_type_group_code = contract.type_id and contract.type_id.contract_type_group_id and \
                                                    contract.type_id.contract_type_group_id.code or False
                        count += 1
                        
                        if count <= 2:
                            if count == 1:
                                is_official = contract.type_id and contract.type_id.is_official or False
                                #When contract is official, next contract shouldn't be probation
                                if is_official:
                                    ignore_group_code = '1'
                                    
                                #Case contract is probation
                                if contract_type_group_code == '1':
                                    is_have_probation_contract = True
                                    # Không cho DH/HRBP chọn loại HĐKXĐTH ngay sau thử việc
                                    groups = user_obj.get_groups(cr, uid)
                                    groups = list(set(groups))
                                    group_access = ['vhr_cb_contract', 'vhr_cnb_manager', 'vhr_hr_dept_head']
                                    group_not_access = list(set(groups) - set(group_access))
                                    is_access = len(groups) - len(group_not_access)
                                    if not is_access:
                                        remove_indefinite = True
                            
                            elif count == 2:
                                #Case contract is probation
                                if contract_type_group_code == '1':
                                    is_have_probation_contract = True
                                    
                            #If 2 consecutive contract are official (not probation), next contract will be indefinite
                            if contract.type_id and not contract.type_id.is_official or is_have_probation_contract:
                                is_indefinite = False
                            if count == 2 and is_indefinite is None:
                                is_indefinite = True
                                
                        else:
                            break

        res = {'is_indefinite': is_indefinite, 'ignore_group_code': ignore_group_code,
               'is_official': is_official, 'remove_indefinite': remove_indefinite}
        return res

    def get_list_contract_type_id(self, cr, uid, value, context=None):
        '''
        If employee is currently collaborator, can only create contract not official
        If employee is currently probation, can only create contract official and not probation
        If employee is currently official, can only create contract official and not probation
        If employee is have equal or greater 2 contract official, next contract is indefinite
        '''
        contract_type_obj = self.pool.get('hr.contract.type')
        contract_type_ids = []
        if value:
            is_indefinite = value.get('is_indefinite', False)
            ignore_group_code = value.get('ignore_group_code', False)
            is_official = value.get('is_official', None)
            remove_indefinite = value.get('remove_indefinite', None)
            if is_indefinite:
                #Search contract HĐLĐ không xác định thời hạn
                contract_type_ids = contract_type_obj.search(cr, uid, [('code', '=', '7'), ('active', '=', True)], context=context)
            elif ignore_group_code or is_official is not None:
                args = [('active', '=', True)]
                if ignore_group_code:
                    #Dont get contract probation
                    args.append(('contract_type_group_id.code', '!=', ignore_group_code))
                if is_official is not None:
                    args.append(('is_official', '=', is_official))
                if remove_indefinite is not None and remove_indefinite is True:
                    #Dont get contract HĐLĐ không xác định thời hạn
                    args.append(('code', '!=', '7'))
                contract_type_ids = contract_type_obj.search(cr, uid, args, context=context)
            else:
                domain = [('active', '=', True)]
                #If old contract is collaborator, new contract must be collaborator incase dont have any termination 
                if is_official is not None:
                    domain.append(('is_official','=',is_official))
                contract_type_ids = contract_type_obj.search(cr, uid, domain, context=context)

        return contract_type_ids

    def check_permission(self, cr, uid, ids, context=None):
        #Only cb contract can edit/ do action in contract
        user_obj = self.pool.get('res.users')
        emp_obj = self.pool.get('hr.employee')
        department_obj = self.pool.get('hr.department')
        is_readonly = False
        is_renew = False
        is_manager = False
        is_hrbp_editable = False
        if ids:
            login_emp_ids = emp_obj.search(cr, uid, [('user_id', '=', uid)])
            if login_emp_ids:
                context['filter_by_group'] = False
                department_ids = department_obj.search(cr, uid, [('manager_id', '=', login_emp_ids[0])], context=context)
                if department_ids:
#                     department_ids += self.get_child_department(cr, uid, department_ids, context=context)
                    department_ids += self.get_child_department(cr, uid, department_ids, context=context)
                    res_contract = self.browse(cr, uid, ids[0], fields_process=['department_id'], context=context)
                    if res_contract.department_id and res_contract.department_id.id in department_ids:
                        is_manager = True

            record = self.read(cr, uid, ids[0], ['state'],context=context)
            state = record.get('state', False)
            groups = user_obj.get_groups(cr, uid)
            groups = list(set(groups))
            group_access = ['vhr_cb_contract']
            is_access = set(group_access).intersection(set(groups))
            
            if set(['vhr_cb_contract','vhr_assistant_to_hrbp']).intersection(set(groups)):
                is_hrbp_editable = True
                
            if state == 'cancel':
                is_readonly = True
                is_hrbp_editable = False
            elif state == 'draft' and not is_access and not is_manager:
                is_readonly = True
            elif state in ['waiting', 'signed'] and  not 'vhr_cb_contract' in groups:
                is_readonly = True
            if is_access or is_manager:
                is_renew = True
            
                
        return {'is_readonly': is_readonly, 'can_renew': is_renew, 'is_hrbp_editable': is_hrbp_editable}

    def action_print_contract(self, cr, uid, ids, context=None):
        if not context:
            context = {}
            
        if not isinstance(ids, list):
            ids = [ids]
        
        multi = False
        emp_obj = self.pool.get('hr.employee')
        company_obj = self.pool.get('res.company')
        department_obj = self.pool.get('hr.department')
        office_obj = self.pool.get('vhr.office')
        salary_obj = self.pool.get('vhr.pr.salary')
        document_obj = self.pool.get('vhr.personal.document')
        emp_inst_obj = self.pool.get('vhr.employee.instance')
        pt_obj = self.pool.get('vhr.ts.param.type')
        pt_by_lv_obj = self.pool.get('vhr.ts.param.job.level')
        working_obj = self.pool.get('vhr.working.record')
        parameter_obj = self.pool.get('ir.config_parameter')
        job_level_obj = self.pool.get('vhr.job.level')
        job_level_new_obj = self.pool.get('vhr.job.level.new')
        leave_type_obj = self.pool.get('hr.holidays.status')
        
        report_name = 'official_contract_report'
        
        
        data = self.read(cr, uid, ids, [], context=context)[0]
        
        is_use_new_template_ktv = False
        is_use_new_template_ktv2 = False
        sign_date = data.get('sign_date', False)
        if sign_date:
            date_change_template_ktv = parameter_obj.get_param(cr, uid, 'vhr_human_resource_date_change_template_contract_ktv_time1') or '2015-11-25'
            is_use_new_template_ktv = self.compare_day(date_change_template_ktv,sign_date) > 0
            
            date_change_template_ktv = parameter_obj.get_param(cr, uid, 'vhr_human_resource_date_change_template_contract_ktv_time2') or '2016-04-28'
            is_use_new_template_ktv2 = self.compare_day(date_change_template_ktv,sign_date) > 0
        
        #Get correct date_end to print contract in case have appendix contract so date_end = extension_appendix.date_end
        if data['date_end_temp']:
            data['date_end'] = data['date_end_temp']
            
        emp_id = data.get('employee_id', False) and data['employee_id'][0] or []
        data['emp_temp_street'] = ''
        if emp_id:
            emp_data = emp_obj.read(cr, uid, emp_id, [], context=context)
            for k, v in emp_data.iteritems():
                new_key = 'emp_' + k
                data[new_key] = emp_data[k]
        if data.get('emp_street', False):
            data['emp_street'] = '%s%s%s' % (
                data['emp_street'],
                data.get('emp_district_id', False) and (', ' + data['emp_district_id'][1]) or '',
                data.get('emp_city_id', False) and (', ' + data['emp_city_id'][1]) or u'',
            )
        if data.get('emp_temp_address', False):
            data['emp_temp_street'] = '%s%s%s' % (
                data['emp_temp_address'],
                data.get('emp_temp_district_id', False) and (', ' + data['emp_temp_district_id'][1]) or '',
                data.get('emp_temp_city_id', False) and (', ' + data['emp_temp_city_id'][1]) or u'',
            )
        
        data['address_office_id'] = ''
        if data.get('office_id', False):
            office_id = data['office_id'][0]
            if office_id:
                office = office_obj.read(cr, uid, office_id, ['address'])
                data['address_office_id'] = office.get('address', '')
                
        
        data['emp_tax_id'] = ''
        if emp_id:
            type_ids = self.pool.get('vhr.personal.document.type').search(cr, uid, [('code','=','TAXID')])
            document_ids = document_obj.search(cr, uid, [('employee_id','=',emp_id),
                                                         ('document_type_id','in', type_ids),
                                                         ('active','=',True)])
            if document_ids:
                document = document_obj.read(cr, uid, document_ids[0], ['number'])
                data['emp_tax_id'] = document.get('number', '')
                
        
        data['emp_office_full_code'] = ''
        if data.get('emp_office_id', False):
            office_id = data['emp_office_id'] and data['emp_office_id'][0]
            if office_id:
                office = self.pool.get('vhr.office').read(cr, uid, office_id, ['code','city_id'])
                data['emp_office_full_code'] =( office.get('city_id',False) and office['city_id'][1] or '') + ' (' + office.get('code','') + ')'
                
            
        if 'emp_gender' in data:
            data['emp_gender_en'] = data['emp_gender'] == 'male' and u'Mr' or \
                                 (data['emp_gender'] == 'female' and u'Ms' or u'Mr./Ms')
                                 
            data['emp_gender'] = data['emp_gender'] == 'male' and u'Ông' or \
                                 (data['emp_gender'] == 'female' and u'Bà' or u'Ông/Bà')
            
            
        if data.get('info_signer', False):
            data['signer'] = data['info_signer'] or ''
            data['signer_country_id'] = data.get('country_signer',False) and data['country_signer'][1] or False
        
        data.update({'cmnd_number': '', 'cmnd_issue_date': '', 'cmnd_city': '', 'lb_number': '',
                         'passport_number':'','passport_issue_date':'','passport_country':''})
        if data.get('emp_personal_document', False):
            document_ids = data['emp_personal_document']
            for item in document_obj.browse(cr, uid, document_ids):
                if item.document_type_id and item.document_type_id.code == 'ID':
                    data['cmnd_number'] = item.number or ''
                    data['cmnd_issue_date'] = item.issue_date or ''
                    data['cmnd_city'] = item.city_id and item.city_id.name or ''
                elif item.document_type_id and item.document_type_id.code == 'LB':
                    data['lb_number'] = item.number or ''
                elif item.document_type_id and item.document_type_id.code == 'PASSPORT':
                    data['passport_number'] = item.number or ''
                    data['passport_issue_date'] = item.issue_date or ''
                    data['passport_country'] = item.country_id and item.country_id.name or ''
                    
        com_id = data.get('company_id', False) and data['company_id'][0] or []
        if com_id:
            move_fields = ['name', 'street', 'phone', 'fax', 'authorization_date','name_en','vat','code']
            com_data = company_obj.read(cr, uid, com_id, ['name', 'street', 'phone', 'fax', 'authorization_date',
                                                          'street2','city_id','district_id','name_en','vat','code'], context=context)
            for field in move_fields:
                new_key = 'com_' + field
                if field == 'street':
                    address = [com_data['street'] or '',com_data['street2'] or '',com_data['district_id'] and com_data['district_id'][1] or '',
                               com_data['city_id'] and com_data['city_id'][1] or '']
                    
                    address = filter(None, address)
                    address = ', '.join(address)
                    data[new_key] = address
                else:
                    data[new_key] = com_data[field]
            
            data['com_tax_id'] = data['com_vat']
        
        division_id = data.get('division_id', False) and data['division_id'][0] or []
        if division_id:
            division = department_obj.read(cr, uid, division_id, ['name'], context=context)
            data['division_id'] = division.get('name','')
        
        department_group_id = data.get('department_group_id', False) and data['department_group_id'][0] or []
        if department_group_id:
            department_group = department_obj.read(cr, uid, department_group_id, ['name'], context=context)
            data['department_group_id'] = department_group.get('name','')
            
        department_id = data.get('department_id', False) and data['department_id'][0] or []
        data['department_full_code'] = ''
        data['specialize_allowance'] = ''
        if department_id:
            department = department_obj.read(cr, uid, department_id, ['name', 'code','complete_code'], context=context)
            data.update({'department_id': department.get('name', ''), 'department_code': department.get('code', '')})
            data['department_full_code'] = department.get('complete_code','').replace(' / ','-')
            if department.get('code','') in ['WNW','WSL','CS','CHN']:
                data['specialize_allowance'] = u'+ Trợ cấp đặc thù:    Dựa vào kết quả công việc hoàn thành trong tháng và theo chính sách của từng bộ phận.'

        active_instance_ids = emp_inst_obj.search(cr, uid, [
            ('employee_id', '=', emp_id), ('company_id', '=', com_id), ('date_end', '=', False)], context=context)

        data.update({'gross_salary': '', 'probation_salary': '', 'date_end_probation': '',
                     'basic_salary': '', 'general_allowance': '', 'kpi_amount': '0', 'days_off': '',
                     'gross_salary_char': '','gross_salary_char_only':'',
                     'date_start_probation': '','v_bonus_salary': '',
                     'collaborator_salary': '', 'colla_salary_char': '', 'colla_salary_char_only': ''})
        
        #This array used for check to get position level for renew contract
        list_contract_in_same_instance = []
        if active_instance_ids:
            emp_inst = emp_inst_obj.browse(cr, uid, active_instance_ids[0], fields_process=['date_start'])
            #Search contract in same instance with date_start < data.date_start
            contract_ids = self.search(cr, uid, [('employee_id', '=', emp_id), 
                                                 ('company_id', '=', com_id), 
                                                 ('id', 'not in', ids), 
                                                 ('state', '=', 'signed'),
                                                 ('date_start', '>=', emp_inst.date_start), 
                                                 ('date_start', '<=', data['date_start'])
                                                 ], order= 'date_start desc',context=context)
            
            list_contract_in_same_instance = contract_ids
            #Only print with template 'renew_contract_report' if have contract same instance nearest it and have is_official = True
            if len(contract_ids) == 1:
                contract = self.browse(cr, uid, contract_ids[0], context=context)
                contract_type_group = contract.type_id and contract.type_id.contract_type_group_id
                
                if  contract_type_group and contract_type_group.code == '1':
                    data['date_start_probation'] = contract.date_start
                    data['date_end_probation'] = contract.date_end and datetime.datetime.strptime(contract.date_end, DEFAULT_SERVER_DATE_FORMAT).strftime("%d/%m/%Y")
                    if data['date_end_probation']:
                        data['date_end_probation'] = '- ' + data['date_end_probation']
                        
                elif contract_type_group and contract_type_group.is_offical:
                    report_name = 'renew_contract_report'
            else:
                if len(contract_ids) >= 1:
                    #Search if nearest contract is official ==> change report to renew_contract
                    nearest_contract = self.browse(cr, uid, contract_ids[0], fields_process=['type_id'])
                    if nearest_contract.type_id and nearest_contract.type_id.contract_type_group_id \
                     and nearest_contract.type_id.contract_type_group_id.is_offical:
                        report_name = 'renew_contract_report'
        
        contract = self.browse(cr, uid, ids[0], fields_process=['type_id'], context=context)
        contract_type_group_code = contract.type_id and contract.type_id.contract_type_group_id and contract.type_id.contract_type_group_id.code or ''
        is_official_contract = contract.type_id and contract.type_id.contract_type_group_id and contract.type_id.contract_type_group_id.is_offical or False
        contract_type_code = contract.type_id and contract.type_id.code or False
        
        data['-'] = data.get('date_end', False) and '-' or ''
        if data.get('date_start', False):
            date_start = data['date_start']
            data.update({'sign_date': date_start})
            data['day'] = str(date_start[8:10])
            data['month'] = str(date_start[5:7])
            data['year'] = str(date_start[:4])

        emp_salary_ids = salary_obj.search(cr, uid, [('effect_from', '<=', data['date_start']), 
                                                     ('company_id', '=', com_id), 
                                                     ('employee_id', '=', emp_id)], order='effect_from desc', context=context)
        if emp_salary_ids:
            emp_salary = salary_obj.browse(cr, uid, emp_salary_ids[0], context=context)
            data['gross_salary'] = emp_salary.gross_salary
            data['probation_salary'] = emp_salary.probation_salary
            data['basic_salary'] = emp_salary.basic_salary
            data['general_allowance'] = emp_salary.general_allowance
            data['v_bonus_salary'] = emp_salary.v_bonus_salary
            data['kpi_amount'] = emp_salary.kpi_amount or '0'
            data['collaborator_salary'] = emp_salary.collaborator_salary or '0'
            
            data['gross_salary_char'] = self.convert_number_to_char(int(data['gross_salary']), 'VN') + u' đồng'
            data['gross_salary_char_only'] = self.convert_number_to_char(int(data['gross_salary']), 'VN')
            
            data['colla_salary_char'] = self.convert_number_to_char(int(data['collaborator_salary']), 'VN') + u' đồng'
            data['colla_salary_char_only'] = self.convert_number_to_char(int(data['collaborator_salary']), 'VN')
        
        data['meal_support'] = ''
        data['meal_support_ctv_report'] = ''
        data['meal_support_ctv_report_number'] = ''
        data['meal_support_internship_report'] = ''
        data['meal_support_fresher'] = u'Không hỗ trợ'
        
        is_meal = False
        if emp_id and com_id:
            active_wr_ids = working_obj.search(cr, uid, [('employee_id','=',emp_id),
                                                         ('company_id','=',com_id),
                                                         ('state','in',[False,'finish']),
                                                         ('active','=',True)])
            if active_wr_ids:
                working = working_obj.browse(cr, uid, active_wr_ids[0], fields_process=['salary_setting_id_new'])
                is_meal = working.salary_setting_id_new and working.salary_setting_id_new.is_meal or False
            else:
                salary_setting_id = data.get('salary_setting_id', False) and data['salary_setting_id'][0]
                if salary_setting_id:
                    salary_setting = self.pool.get('vhr.salary.setting').read(cr, uid, salary_setting_id, ['is_meal'])
                    is_meal = salary_setting.get('is_meal', False)
            
        if is_meal:
            full_meal = parameter_obj.get_param(cr, uid, 'vhr_human_resource_full_meal_allowance') or 0
            if full_meal:
                data['meal_support'] = u'Chi phí hỗ trợ khác để thực hiện dịch vụ là: ' + full_meal + u' đồng/tháng'
                data['meal_support_ctv_report'] = u'-  Trợ cấp ăn trưa:                          660,000 đồng/ tháng, theo chính sách công ty'
                data['meal_support_ctv_report_number'] = parameter_obj.get_param(cr, uid, 'vhr_human_resource_meal_support_ctv') or '0'
                if not data['meal_support_ctv_report_number']:
                    data['meal_support_ctv_report_number'] = '0'
                data['meal_support_internship_report'] = u'-   Cơm trưa: 660,000 đồng/tháng.'
                data['meal_support_fresher'] = u'Có hỗ trợ'
        
        data['days_off'] = 0
        # Số ngày nghỉ theo cấp bậc
        if data.get('job_level_id', False) or data.get('job_level_person_id', False):
            today = fields.date.context_today(self, cr, uid)
            
            job_level_person_id = data.get('job_level_person_id', False) and data['job_level_person_id'][0]
                
            job_level_id = data.get('job_level_id', False) and data['job_level_id'][0]
            pt_ids = pt_obj.search(cr, uid, [('code', '=', '1')], context=context)
            domain=[('param_type_id', 'in', pt_ids),
                      ('active','=',True),
                      ('effect_from','<=',today),
                      '|',('effect_to','=',False),
                          ('effect_to','>=',today)]
            
            if job_level_person_id:
                domain.insert(0,('job_level_new_id', '=', job_level_person_id))
            elif job_level_id:
                domain.insert(0,('job_level_id', '=', job_level_id))
                
            pt_lv_ids = pt_by_lv_obj.search(cr, uid, domain, order='effect_from desc',context=context)
            if pt_lv_ids:
                pt = pt_by_lv_obj.browse(cr, uid, pt_lv_ids[0], context=context)
                data['days_off'] = pt and pt.value or ''
        
        if not data.get('is_official', False) and data['year'] and emp_id:
            leave_type_code = parameter_obj.get_param(cr, uid, 'ts.leave.type.default.code').split(',')
    
            holiday_status_ids = leave_type_obj.search(cr, uid, [('code', 'in', leave_type_code)])
            if holiday_status_ids:
                holiday_status_id = holiday_status_ids[0]
            
                annual_leave_ids = self.pool.get('hr.holidays').search(cr, uid, [('holiday_status_id', '=', holiday_status_id),
                                                                                ('type', '=', 'add'),
                                                                                ('employee_id', '=', emp_id),
                                                                                ('year', '=', int(data['year'])),
                                                                                ('state', '=', 'validate')])
                if annual_leave_ids:
                    annual_leave = self.pool.get('hr.holidays').read(cr, uid, annual_leave_ids[0], ['number_of_days_temp'])
                    data['days_off'] = annual_leave.get('number_of_days_temp',0)
        
        data['city_short_name'] = ''
        #Get office(working place)
        if data.get('working_address', False):
            data['office_id'] = data['working_address']     
        elif data.get('office_id', False):
            office = office_obj.browse(cr, uid, data['office_id'][0], context=context)
            data['office_id'] = office and office.city_id and office.city_id.name or data['office_id']
            
            data['city_short_name'] = data['office_id']
            if data['office_id'] == u'Hồ Chí Minh':
                data['city_short_name'] = 'TP.HCM'
                data['office_id'] = 'TP ' + data['office_id']
        
        data['emp_job_group_id'] = ''
        data['emp_job_family_id'] = ''
        #Title and job level get name_en
        if data.get('title_id', False):
            title_id = data['title_id'][0] or False
            if title_id:
                title = self.pool.get('vhr.job.title').read(cr, uid, title_id, ['name_en'])
                data['title_id'] = title.get('name_en','')
            
            if not data.get('job_family_id', False) and not data.get('job_group_id', False):
                subgroup_title_ids = self.pool.get('vhr.subgroup.jobtitle').search(cr, uid, [('job_title_id','=',title_id)])
                if subgroup_title_ids:
                    subgroup_title = self.pool.get('vhr.subgroup.jobtitle').browse(cr, uid, subgroup_title_ids[0])
                    subgroup = subgroup_title.sub_group_id
                    job_group = subgroup and subgroup.job_group_id or False
                    if job_group:
                        data['emp_job_group_id'] = job_group and job_group.name
                        
                        job_family = job_group and job_group.job_family_id or False
                        if job_family:
                            data['emp_job_family_id'] = job_family and job_family.name
            else:
                data['emp_job_group_id'] = data['job_group_id']
                data['emp_job_family_id'] = data['job_family_id']
        else:
            data['title_id'] = ''
        
        data['emp_job_level_id'] = ''
        
        job_level_id = data.get('job_level_id',False) and data['job_level_id'][0] or False
        if job_level_id:
            job_level = job_level_obj.read(cr, uid, job_level_id, ['name_en'])
            data['emp_job_level_id'] = job_level.get('name_en','')
        
        #Get old job level để phân loại hợp đồng
        data['job_level_id'] = data['emp_job_level_id']
        
        
        data['sign_date_str']  = self.convert_from_date_to_date_string(data['sign_date'])
        data['date_start_str'] = self.convert_from_date_to_date_string(data['date_start'])
        data['date_end_include_cn'] = ''
        data['date_end_str'] = ''
        if data['date_end']:
            data['date_end_str']   = self.convert_from_date_to_date_string(data['date_end'])
            data['date_end_include_cn'] = '- ' + datetime.datetime.strptime(data['date_end'], DEFAULT_SERVER_DATE_FORMAT).strftime("%d/%m/%Y")
            
        data['bank_account'] = ''
        data['bank_name'] = ''
        if data.get('bank_account_ids', False):
            bank_account_ids = data.get('bank_account_ids',[])
            bank_account = self.pool.get('vhr.bank.contract').browse(cr, uid, bank_account_ids[0])
            bank_account_number = bank_account.bank_id and bank_account.bank_id.acc_number or ''
            if 'Unknown' not in bank_account_number:
                data['bank_account'] = bank_account_number
                data['bank_name'] = bank_account.bank_id and bank_account.bank_id.bank and bank_account.bank_id.bank.name or ''
        
        if data.get('report_to', False):
            report_to = data['report_to'] and data['report_to'][1].split('(')
            data['report_to'] = report_to and report_to[0] and report_to[0].strip()
        
            
        data['mission_collaborator'] = ''
        if data.get('mission_ids', False):
            mission_ids = data['mission_ids']
            missions = self.pool.get('vhr.mission.collaborator.contract').read(cr, uid, mission_ids, ['value'])
            for mission in missions:
                value = mission.get('value','')
                if value:
                    if data['mission_collaborator']:
                        data['mission_collaborator'] += '\\n'
                    data['mission_collaborator'] += '- ' + value
        
        data['result_collaborator'] = ''
        if data.get('result_ids', False):
            result_ids = data['result_ids']
            results = self.pool.get('vhr.result.collaborator.contract').read(cr, uid, result_ids, ['value'])
            for result in results:
                value = result.get('value','')
                if value:
                    if data['result_collaborator']:
                        data['result_collaborator'] += '\\n ' 
                    data['result_collaborator'] +=  '- ' + value
        
        data['working_time_detail'] = '08:30 – 17:30 từ Thứ Hai đến Thứ Sáu (Nghỉ trưa: 12:00-13:00)'
        if data.get('working_time', False):
            data['working_time_detail'] = ''
            working_time_detail = data['working_time'].splitlines()
            for detail in working_time_detail:
                if data['working_time_detail']:
                    data['working_time_detail'] += '\\n ' 
                data['working_time_detail'] +=  detail
            
            #If working time have data, get job_type_id = working_time_detail, other wise get from job_type_id
            data['job_type_id'] = data['working_time_detail']
        
        if data['contract_type_group_id']:
            data['contract_type_group_id'] = data['contract_type_group_id'][1]
            data['contract_type_group_id'] = data['contract_type_group_id'].replace(u'HĐLĐ ','')
        
        if context.get('report_name', False):
            report_name = context['report_name']
        #HD DV-CTV
        elif contract_type_group_code == 'CTG-008':
            report_name = 'collaborator_service_contract_report'
            contract_sub_type_id = data.get('sub_type_id', False) and data['sub_type_id'][0] or False
            if contract_sub_type_id:
                contract_sub_type = self.pool.get('hr.contract.sub.type').read(cr, uid, contract_sub_type_id, ['code'])
                contract_sub_type_code = contract_sub_type.get('code', False)
                
                #Hợp đồng Ql KTV
                if contract_sub_type_code == 'CST-001':
                    report_name = 'contract_ql_ktv_report'
                elif contract_sub_type_code == 'CST-002':
                    report_name = 'contract_ktv_report'
                    
                #Check with new template ktv
                if is_use_new_template_ktv:
                    if contract_sub_type_code == 'CST-001':
                        report_name = 'contract_ql_ktv_report_from_10_12'
                    elif contract_sub_type_code in ['CST-003','CST-004','CST-005','CST-006']:
                        report_name = 'contract_ktv_report_from_10_12'
                        
                        #Kĩ thuật viên Thành phố
                        if contract_sub_type_code == 'CST-003':
                            data['muc_thu_lao'] = 'Nhóm B'
                            data['footer_note'] = 'HD-KTV-TP' 
                        
                        # Kỹ Thuật Viên Tỉnh
                        elif contract_sub_type_code == 'CST-004':
                            data['muc_thu_lao'] = 'Nhóm C'
                            data['footer_note'] = 'HD-KTV-Tinh' 
                        
                        # Kỹ Thuật Viên HV TP
                        elif contract_sub_type_code == 'CST-005':
                            data['muc_thu_lao'] = 'Nhóm D'
                            data['footer_note'] = 'HD-KTV-HVTP' 
                        
                        # Kỹ Thuật Viên HV Tinh
                        elif contract_sub_type_code == 'CST-006':
                            data['muc_thu_lao'] = 'Nhóm E'
                            data['footer_note'] = 'HD-KTV-HVTinh' 
                
                #Since 01-05-2016
                if is_use_new_template_ktv2:
                    if contract_sub_type_code == 'CST-001':
                        report_name = 'contract_ql_ktv_report_from_01_05_2016'
                    elif contract_sub_type_code == 'CST-002':
                        report_name = 'contract_ktv_report_from_01_05_2016'
                    elif contract_sub_type_code == 'CST-007':
                        report_name = 'contract_ktv_hv_report_from_01_05_2016'
                    
            
#             multi = True
        #HD Fresher
        elif contract_type_code == 'FS':
            report_name = 'non_official_fresher_contract'
        #HD Internship
        elif contract_type_code == '4':
            report_name = 'non_official_internship_contract'
        #HD CTV
        elif contract_type_group_code == '2':
            report_name = 'non_official_collaborator_contract'
        #HD Tu van
        elif contract_type_group_code == '5':
            report_name = 'official_consultant_contract'
        #Offer Contract
        elif contract_type_group_code == '1':
            report_name = 'offer_contract_report'
        
#         if context.get('report_name', False) == 'privacy_statement_contract':
#             raise osv.except_osv('Error !', "Can not print non-disclosure agreement with this contract !")
            
            
        file_name = 'Contract_' + data.get('name') + '_' + data.get('emp_name')
        
        if context.get('report_name', False) == 'privacy_statement_contract':
            file_name = 'Non-disclosure Agreement ' + data.get('name') + '_' + data.get('emp_name')
        
        
        print 'report_name=',report_name
        #Cheat title and job level in HD DV-CTV
        if contract_type_group_code == 'CTG-008':
            #Cheat tax
            if 'Collaborator' in data['title_id']:
                data['title_id'] = data['title_id'].replace('Collaborator ', 'Colla.')
            
            if 'Freelancer - Office' in data['job_level_id']:
                data['job_level_id'] = 'Free.Office'
                
            elif 'Freelancer' in data['job_level_id']:
                data['job_level_id'] = data['job_level_id'].replace('Freelancer', 'Free.')
            
            elif 'Temporary' in data['job_level_id']:
                data['job_level_id'] = data['job_level_id'].replace('Temporary', 'Temp.')
                
            
            if data.get('working_salary', False):
                data['gross_salary'] = data['working_salary']
                data['collaborator_salary'] = data['working_salary']
                data['salary_declare'] = ''
            else:
                data['salary_declare'] = 'đồng/tháng'
                
        if multi:
            data = [data]
        
        is_turn_on = parameter_obj.get_param(cr, uid, 'vhr_human_resource_code_turn_off_update_nearest_code') or 0
        
        if is_official_contract and emp_id and is_turn_on in ['1','2']:
            #Tạm thời chỉ những employee dược transfer từ ngày 20/8 mới sử dụng job level mới để in hợp đồng và hợp đồng gia hạn
            mine_date = date(2015, 8, 20).strftime(DEFAULT_SERVER_DATE_FORMAT)
            emp_data = emp_obj.read(cr, uid, emp_id, ['is_transfer_from_rr'])
            if emp_data.get('is_transfer_from_rr', False):
                is_get_new_level = False
                emp_meta_data = emp_obj.perm_read(cr, SUPERUSER_ID, [emp_id], context)
                emp_create_date = emp_meta_data and emp_meta_data[0].get('create_date', False)
                #Employee transfer from RR
                if emp_create_date:
                    emp_create_date = emp_create_date[:10]
                    emp_create_date = datetimes.strptime(emp_create_date, DEFAULT_SERVER_DATE_FORMAT).strftime(DEFAULT_SERVER_DATE_FORMAT)
                    if self.compare_day(mine_date, emp_create_date) >= 0:
                        is_get_new_level = True
                
                #Contract transfer from RR
                if not is_get_new_level and data.get('job_applicant_id', False):
                    contract_meta_data = self.perm_read(cr, SUPERUSER_ID, ids, context)
                    ct_create_date = contract_meta_data and contract_meta_data[0].get('create_date', False)
                    if ct_create_date:
                        ct_create_date = ct_create_date[:10]
                        ct_create_date = datetimes.strptime(ct_create_date, DEFAULT_SERVER_DATE_FORMAT).strftime(DEFAULT_SERVER_DATE_FORMAT)
                        if self.compare_day(mine_date, ct_create_date) >= 0:
                            is_get_new_level = True
                
                #Old employee have old contract in same instance transfer from RR
                if not is_get_new_level and list_contract_in_same_instance:
                    old_data = self.read(cr, uid, list_contract_in_same_instance[0], ['job_applicant_id'])
                    if old_data.get('job_applicant_id', False):
                        contract_meta_data = self.perm_read(cr, SUPERUSER_ID, [list_contract_in_same_instance[0]], context)
                        ct_create_date = contract_meta_data and contract_meta_data[0].get('create_date', False)
                        if ct_create_date:
                            ct_create_date = ct_create_date[:10]
                            ct_create_date = datetimes.strptime(ct_create_date, DEFAULT_SERVER_DATE_FORMAT).strftime(DEFAULT_SERVER_DATE_FORMAT)
                            if self.compare_day(mine_date, ct_create_date) >= 0:
                                is_get_new_level = True
                            
                if is_get_new_level:
                    #In Job Level Position nếu có đối với hợp đồng chính thức transfer từ bên RR sang
                    job_level_person_id = data.get('job_level_person_id',False) and data['job_level_person_id'][0] or False
                    if job_level_person_id:
                        job_level_new = job_level_new_obj.read(cr, uid, job_level_person_id, ['name_en'])
                        data['emp_job_level_id'] = job_level_new.get('name_en','')
        
        #Neu company co code thuoc parameter nay, khong show authorization date trong report Contract
        comp_code_not_show_authorization = parameter_obj.get_param(cr, uid, 'vhr_human_resource_company_do_show_authorization_in_contract') or ''
        comp_code_not_show_authorization = comp_code_not_show_authorization.split(',')
        data['is_head_of_company'] = False
        if com_id and comp_code_not_show_authorization:
            allow_comp_ids = company_obj.search(cr, uid, [('code','in',comp_code_not_show_authorization)])
            if com_id in allow_comp_ids:
                data['is_head_of_company'] = True
            
        
        datas = {
            'ids': ids,
            'model': 'hr.contract',
            'form': data,
            'parse_condition': True
#             'multi': True,
        }
        
        appendix_ids = self.pool.get('vhr.appendix.contract').search(cr, uid, [('contract_id','=',ids[0]),
                                                                               ('active','=',True)])
        if appendix_ids:
            res_appendix = self.action_print_appendix_contract(cr, uid, ids, context)
            appendix_report_name = res_appendix['report_name']
            appendix_data = res_appendix['datas'].get('form',{})
            appendix_data['report_name'] = appendix_report_name
            
            datas = {
                     'ids': ids,
                     'model': 'hr.contract',
                     'form': [{'report.'+report_name:data}, {'report.'+appendix_report_name:appendix_data}],
                     'merge_multi_report': True,
                     'parse_condition': True
                     }
        
#         if not context.get('report_name', False) and contract_type_code in ['FS','4']:
#             res_data = self.action_print_contract(cr, uid, ids, context={'report_name': 'privacy_statement_contract'})
#             privacy_report_name = res_data['report_name']
#             privacy_data = res_data['datas'].get('form',{})
#             privacy_data['report_name'] = privacy_report_name
#             
#             datas = {
#                      'ids': ids,
#                      'model': 'hr.contract',
#                      'form': [{'report.'+report_name:data}, {'report.'+privacy_report_name:privacy_data}],
#                      'merge_multi_report': True,
#                      'parse_condition': True
#                      }
            
        res = {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': datas,
            'name': file_name
        }
        
        return res
        
    
    def action_print_appendix_contract(self, cr, uid, ids, context=None):
        if not isinstance(ids, list):
            ids = [ids]
        
        appendix_contract_pool = self.pool.get('vhr.appendix.contract')
        if ids:
            report_name = ''
            res = {}
            
            appendix_ids = appendix_contract_pool.search(cr, uid, [('contract_id','=',ids[0]),
                                                                   ('is_extension_appendix','=',False),
                                                                   ('active','=',True)])
            
            if not appendix_ids:
                appendix_ids = appendix_contract_pool.search(cr, uid, [('contract_id','=',ids[0]),
                                                                       ('active','=',True)])
            
            if not appendix_ids:
                appendix_ids= appendix_contract_pool.search(cr, uid, [('contract_id','=',ids[0])])
            
            if len(appendix_ids) ==1:
                res = appendix_contract_pool.print_appendix_contract(cr, uid, appendix_ids, context)
                if res:
                    res['datas']['model'] = 'hr.contract'
            elif len(appendix_ids) >1:
                raise osv.except_osv('Error !', "Contract have more than 1 active appendix contract. Please check again !")
                    
            else:
                raise osv.except_osv('Error !', "Contract don't have any appendix contract !")
            
            return res
        
    
    def action_print_multi_merge_contract(self, cr, uid, ids, context=None):
        res = {}
        list_data = []
        for record_id in ids:
            res = self.action_print_contract(cr, uid, [record_id], context)
            datas = res.get('datas', False)
            if datas:
                data = datas.get('form')
                if isinstance(data, dict):
                    list_data.append({'report.'+ res['report_name'] : data})
                else:
                    list_data.extend(data)
        
        res['datas'] = {
                     'ids': ids,
                     'model': 'hr.contract',
                     'form': list_data,
                     'merge_multi_report': True
                     
                     }
        
        return res
    
    def cron_update_main_contract(self, cr, uid, context=None):
        """
        Check if employee only have one active contract and that contract is not main ==> update is_main=True for that contract
        """
        today = fields.date.context_today(self, cr, uid)
        
        #Search employee have main active contract
        sql = """
                SELECT employee_id FROM hr_contract WHERE      state = 'signed'
                                                          AND date_start <= '%s' 
                                                          AND is_main = true
                                                          AND (
                                                                  (date_end is null AND liquidation_date is null)
                                                               OR (date_end >= '%s'   AND liquidation_date is null)
                                                               OR (liquidation_date >= '%s')
                                                              )
              """
        cr.execute(sql%(today,today,today))
        res = cr.fetchall()
        employee_ids = [item[0] for item in res]
        employee_ids.append(0)
        
        #Search employee dont have main active contract and only have one contract active
        sql = """
                SELECT employee_id FROM hr_contract WHERE      state = 'signed'
                                                          AND date_start<= '%s'
                                                          AND employee_id not in %s
                                                          AND (
                                                                  (date_end is null AND liquidation_date is null)
                                                               OR (date_end >= '%s' AND liquidation_date is null)
                                                               OR (liquidation_date >= '%s')
                                                              )
                                                    GROUP BY employee_id
                                                    HAVING count(id) = 1
              """
        
        cr.execute(sql%(today, str(tuple(employee_ids)).replace(',)', ')'), today, today))
        res = cr.fetchall()
        update_employee_ids = [item[0] for item in res]
        
        if update_employee_ids:
            #Update for active contract of employee only have 1 active contract and there contracts have is_main = False
            sql = """
                    UPDATE hr_contract
                                    SET is_main = true
                                    
                                                WHERE      state = 'signed'
                                                              AND date_start<= '%s' 
                                                              AND employee_id in %s
                                                              AND (
                                                                      (date_end is null AND liquidation_date is null)
                                                                   OR (date_end >= '%s' AND liquidation_date is null)
                                                                   OR (liquidation_date >= '%s')
                                                                  )
                  """
            cr.execute(sql%(today, str(tuple(update_employee_ids)).replace(',)', ')'), today, today))
        
        return True

    # Author: Tannd2
    # Purpose: Get current contract of employee based on date
    # Note: I don't know why there was the method "get_emp_current_contracts" below
    def get_emp_contracts(self, cr, uid, emp_id, date, company_id=False, state=SIGNED, context=None):
        if context is None:
            context = {}
        current_contract_ids = []
        if not emp_id or not date:
            return current_contract_ids
        domain = [
            ('employee_id', '=', emp_id),
            ('date_start', '<=', date),
            ('state', '=', state),
            '|', ('date_end', '=', False), ('date_end', '>=', date),
            '|', ('liquidation_date', '=', False),
            ('liquidation_date', '>=', date),
        ]
        if company_id:
            domain.append(('company_id', '=', company_id))
        current_contract_ids = self.search(cr, uid, domain, context=context)
        return current_contract_ids

    def get_emp_current_contracts(self, cr, uid, emp_id, company_id=False, context=None):
        if context is None:
            context = {}
        today = datetimes.now().strftime("%Y-%m-%d")
        current_contract_ids = self.get_emp_contracts(cr, uid, emp_id, today, company_id=company_id, context=context)
        return current_contract_ids
    
    def thread_import_deliver_hr_contract(self, cr, uid, import_status_id, rows, context=None):
        log.info('Begin: thread_import_deliver_hr_contract')
        if not context:
            context = {}
        try:
            import openerp
            db = openerp.sql_db.db_connect(cr.dbname)
            cr = db.cursor()
            mcr = db.cursor()
            import_obj = self.pool.get('vhr.import.status')
            detail_obj = self.pool.get('vhr.import.detail')
            employee_obj = self.pool.get('hr.employee')
            change_form_pool = self.pool.get('vhr.change.form')
            contract_obj = self.pool.get('hr.contract')
            parameter_obj = self.pool.get('ir.config_parameter')
            
            model_ids = self.pool.get('ir.model').search(cr, uid, [('model','=',self._name)])
            model_id = model_ids and model_ids[0] or False
            mapping_fields = {
                              'Contract Name': 'name', 
                              'Is Delivered':'is_delivered',
                              'Delivery Person': 'delivery_id', 
                              'Holder': 'holder_id', 
                              'Delivery Date': 'delivery_date',
                              'Delivery Note': 'delivery_note',
                              'Receiver': 'receiver_id',
                              "Is Received": 'is_received',
                              "Received Date": 'received_date',
                              "Is Signed By Employee": 'is_signed_by_emp',
                              }
            
            required_fields = ['name']
            fields_order = []
            fields_search_by_name = ['name']
            ac_fields = self._columns.keys()
            
            import_obj.write(mcr, uid, [import_status_id], {'state': 'processing', 'num_of_rows':rows.nrows-2, 'current_row':0,'model_id': model_id})
            mcr.commit()
            #Dont count two round describe data
            row_counter = 0
            success_row = 0
            for row in rows._cell_values:
                auto_break_thread_monthly_gen = parameter_obj.get_param(cr, uid, 'vhr_human_resource_auto_break_thread') or ''
                try:
                    auto_break_thread_monthly_gen = int(auto_break_thread_monthly_gen)
                except:
                    auto_break_thread_monthly_gen = False
                if auto_break_thread_monthly_gen:
                    break
                
                if row_counter == 0:
                    fields_order = row
                    
                row_counter += 1
                if row_counter > 2:
                    vals_detail = {}
                    data = row[:]
                    
                    
                    vals, error = self.parse_data_from_excel_row(cr, uid, row, mapping_fields, fields_search_by_name, fields_order, context)
                    warning = ''
                    if not error:
                        try:
                            #Check if missing required fields
                            vals_field = vals.keys()
                            input_required_fields = list(set(required_fields).intersection(set(vals_field)))
                            if len(required_fields) != len(input_required_fields):
                                missing_fields = list(set(required_fields).difference(set(input_required_fields)))
                                missing_name_fields = []
                                for key, value in mapping_fields.iteritems():
                                    if value in missing_fields:
                                        missing_name_fields.append(key)
                                
                                error = "You have to input data in %s" % str(missing_name_fields)
                            
                            else:    
                                #Search contract
                                if vals.get('name', False):
                                    old_ids = self.search(cr, uid, [('name','=',vals.get('name', False))])
                                        
                                    if old_ids:
                                        del vals['name']
                                        self.write(cr, uid, old_ids, vals, context)
                                        success_row += 1
                                    else:
                                        error = "Employee have %s contract satisfy date_start and date_end of template: %s"%(len(old_ids), str(old_ids))
                                
                        except Exception as e:
                            log.exception(e)
                            try:
                                error = e.message
                                if not error:
                                    error = e.value
                            except:
                                error = ""
                    if error:
                        vals_detail = {'import_id': import_status_id, 'row_number' : row_counter -2, 'message':error,'status':'fail'}
                        detail_obj.create(mcr, uid, vals_detail)
                        mcr.commit() 
                        cr.rollback()
                    else:
                        if warning:
                            vals_detail = {'import_id': import_status_id, 'row_number' : row_counter -2, 'message':warning,'status':'success'}
                            detail_obj.create(mcr, uid, vals_detail)
                            mcr.commit() 
                        cr.commit()
                    
                import_obj.write(mcr, uid, [import_status_id], {'current_row':row_counter - 2, 'success_row':success_row})
                mcr.commit()
            import_obj.write(mcr, uid, [import_status_id], {'state': 'done'})
            mcr.commit()
        except Exception as e:
            log.exception(e)
            import_obj.write(mcr, uid, [import_status_id], {'state': 'error'})
            mcr.commit()
            log.info(e)
            cr.rollback()
        finally:    
            cr.close()
            mcr.close()
        log.info('End: thread_import_deliver_hr_contract')
        return True
    
    def parse_data_from_excel_row(self, cr, uid, row, mapping_fields, fields_search_by_name, fields_order, context=None):
        res = {}
        error = ""
        if row and mapping_fields and fields_order:
            for index, item in enumerate(row):
                #If item in row does not appear in mapping fields, by pass  
                field_name = mapping_fields.get(fields_order[index])
                #Only override if have value in cell
                if field_name and item:
                    field_obj = self._all_columns.get(field_name)
                    field_obj = field_obj and field_obj.column
                    if field_obj and field_obj._type == 'many2one':
                        model = field_obj._obj
                        value = str(item).strip()
                        
                        try:
                            value = value.replace('\xc2\xa0','')
                        except Exception as e:
                            log.exception(e)
                            
                        if value:
                            
                            #Assign False to field_name if value == 'false'
                            if value in ['false','0']:
                                res[field_name] = False
                                continue
                            
                            domain = ['|',('code','=ilike', value),('name','=ilike', value)]
                            if field_name in fields_search_by_name:
                                domain = [('name','=ilike', value)]
                            record_ids = self.pool.get(model).search(cr, uid, domain)
                            
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
                            value = False
                            if item:
                                value = datetimes.strptime(item,"%d/%m/%Y").strftime(DEFAULT_SERVER_DATE_FORMAT)
                            res[field_name] = value
                        except Exception as e:
                            error = "Field %s have to input correct date format dd/mm/YYYY" % field_obj.string 
                    
                    elif (field_obj and field_obj._type == 'boolean'):
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
                    
                    elif field_obj and field_obj._type == 'float':
                        try:
                            res[field_name] = item and float(item) or 0
                        except Exception as e:
                            error = "Field '%s' have to input number" % field_obj.string 
                    
                    elif field_obj and field_obj._type == 'integer':
                        try:
                            res[field_name] = item and int(item) or 0
                        except Exception as e:
                            error = "Field '%s' have to input number" % field_obj.string 
                        
                    #log to trace back
                    elif not field_obj and field_name=='xml_id':
                        res[field_name] = str(item).strip()
                    
                            
        
        return res, error
    
hr_contract()