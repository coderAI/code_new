# -*-coding:utf-8-*-
import logging
import thread
import time

import simplejson as json
from openerp.osv import osv, fields
from openerp.addons.vhr_common.model.vhr_common import vhr_common
from openerp import SUPERUSER_ID
from lxml import etree
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import datetime
from vhr_exit_checklist_request_email_process import mail_process
from vhr_human_resource_abstract import vhr_human_resource_abstract

log = logging.getLogger(__name__)

STATES = [
    ('draft', 'Requester'),
    ('department', 'Waiting Department'),
#     ('hrbp', 'Waiting HRBP'),
#     ('hr_executor', 'Waiting HR Executor'),
    ('finish', 'Finish'),
    ('cancel', 'Cancel')]


APPROVE_FIELDS = ['is_approve_responsibilities_hand_over','is_approve_administrative_office',
                  'is_approve_administrative_office_other','is_approve_it_office',
                  'is_approve_it_office_other','is_approve_accounting_office',
                  'is_approve_hr_office_training','is_approve_hr_office_other','is_approve_accounting_office_other']

DEPARTMENT_FIELDS = ['responsibilities_hand_over_ids','administrative_office_ids',
                     'administrative_office_other_ids','it_office_other_ids',
                     'accounting_office_ids','hr_office_training_ids','hr_office_other_ids','it_office_ids','accounting_office_other_ids']

APPROVER_FIELDS = ['approver_user_responsibilities_hand_over','approver_user_administrative_office',
                   'approver_user_administrative_office_other','approver_user_it_office',
                   'approver_user_it_office_other','approver_user_accounting_office',
                   'approver_user_hr_office_training','approver_user_hr_office_other','approver_user_accounting_office_other']

IS_APPROVER_FIELDS = ['is_person_responsibilities_hand_over', 'is_person_administrative_office',
                      'is_person_administrative_office_other', 'is_person_it_office',
                      'is_person_it_office_other', 'is_person_accounting_office',
                      'is_person_hr_office_training', 'is_person_hr_office_other','is_person_accounting_office_other'
                      ]

TEAM_FIELDS = {'responsibilities_hand_over_ids': ['is_approve_responsibilities_hand_over','approver_user_responsibilities_hand_over'  , '1', 'is_person_responsibilities_hand_over'],#Ban Giao Cong Viec
               'administrative_office_ids'      : ['is_approve_administrative_office'       ,'approver_user_administrative_office'        , 'AF', 'is_person_administrative_office'], #Phong Hanh Chinh
               'administrative_office_other_ids': ['is_approve_administrative_office_other','approver_user_administrative_office_other'  , '11' , 'is_person_administrative_office_other'], #Phong Hanh Chinh other
                'it_office_ids'                 : ['is_approve_it_office'                 ,'approver_user_it_office'                   , 'IT', 'is_person_it_office'],#Phong Cong Nghe Thong Tin 
               'it_office_other_ids'           : ['is_approve_it_office_other'           ,'approver_user_it_office_other'             , '12', 'is_person_it_office_other'],#Phong CNTT other
               'accounting_office_ids'         : ['is_approve_accounting_office'         ,'approver_user_accounting_office'           , '4' , 'is_person_accounting_office'],  #Phong TCKT
               'hr_office_training_ids'        : ['is_approve_hr_office_training'        ,'approver_user_hr_office_training'          , '10', 'is_person_hr_office_training'],#Phong Nhan Su Training
               'hr_office_other_ids'           : ['is_approve_hr_office_other'           ,'approver_user_hr_office_other'             , '8' , 'is_person_hr_office_other'],#Phong Nhan Su other
               'accounting_office_other_ids'         : ['is_approve_accounting_office_other'         ,'approver_user_accounting_office_other'           , '13' , 'is_person_accounting_office_other'],  #Phong TCKT other

               }

EXIT_TYPE_CODE = ['AF','11','IT','12','4','10','8','13']

class vhr_exit_checklist_request(osv.osv,vhr_common, vhr_human_resource_abstract):
    _name = 'vhr.exit.checklist.request'
    _description = 'Exit Checklist Request'
    
    
    def _is_person_do_action(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for record_id in ids:
            res[record_id] = self.is_person_do_action(cr, uid, [record_id], context)

        return res
    
    
    def _is_person_able_to_edit_employee(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        is_able = self.get_is_able_to_edit_employee(cr, uid)
        
        for record_id in ids:
            res[record_id] = is_able
        
        return res
    
    def _is_person_able_to_reject(self, cr, uid, ids, field_name, arg, context=None):
        '''
        When change this function need to change function is_person_do_action_reject to apply for field is_person_able_to_reject
        '''
        res = {}
        
        groups = self.pool.get('res.users').get_groups(cr, uid)
        result = 'vhr_cb_termination' in groups
        for record_id in ids:
            res[record_id] = {}
            res[record_id]['is_person_able_to_reject'] = result
            res[record_id]['is_cb_termination'] = result
        return res
    
    
    def _is_person_do_action_department(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        exit_detail_pool = self.pool.get('vhr.exit.checklist.detail')
        emp_pool = self.pool.get('hr.employee')
        exit_approver_pool = self.pool.get('vhr.exit.approver')
        exit_type_pool = self.pool.get('vhr.exit.type')
        city_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_human_resource_code_of_hochiminh_city') or ''
        hcm_city_id = False
        if city_code:
            hcm_city_id = self.pool.get('res.city').search(cr, uid, [('code','=',city_code)])
        
        employee_ids = emp_pool.search(cr, uid, [('user_id','=',uid)])
        for record in self.browse(cr, uid, ids, fields_process=['employee_id']):
            res[record.id] = {'is_person_do_action_for_department': False}
            city_id = record.employee_id and record.employee_id.office_id and record.employee_id.office_id.city_id and record.employee_id.office_id.city_id.id or False
            report_to = record.employee_id and record.employee_id.report_to or False
            manager = record.employee_id and record.employee_id.parent_id or False
            department_id = record.employee_id and record.employee_id.department_id and record.employee_id.department_id.id or False
            for field in TEAM_FIELDS:
                code_exit_type = TEAM_FIELDS[field][2]
                is_person = TEAM_FIELDS[field][3]
                res[record.id][is_person] = False
                
                #exception case for responsiblity hand over
                if field == 'responsibilities_hand_over_ids':
                    if report_to:
                        manager = report_to
                        
                    if manager and manager.user_id and manager.user_id.id == uid:
                        res[record.id][is_person] = True
                        res[record.id]['is_person_do_action_for_department'] = True
                    
                    delegator_ids = self.get_delegator(cr, uid, department_id, manager.id)
                    if delegator_ids and employee_ids and employee_ids[0] in delegator_ids:
                        res[record.id][is_person] = True
                        res[record.id]['is_person_do_action_for_department'] = True
                    
                    delegator_ids = self.get_delegator_by_process(cr, uid, record.id, manager.id)
                    if delegator_ids and employee_ids and employee_ids[0] in delegator_ids:
                        res[record.id][is_person] = True
                        res[record.id]['is_person_do_action_for_department'] = True
                            
                    continue
                
                exit_type_ids = exit_type_pool.search(cr, uid, [('code','=',code_exit_type)])
                if exit_type_ids:
                    exit_approver_ids = exit_approver_pool.search(cr, uid, [('exit_type_id','in',exit_type_ids),
                                                                            ('city_id','=',city_id)])
                    if not exit_approver_ids:
                        exit_approver_ids = exit_approver_pool.search(cr, uid, [('exit_type_id','in',exit_type_ids),
                                                                            ('city_id','=',hcm_city_id)])
                
                    exit_approver = exit_approver_pool.browse(cr, uid, exit_approver_ids[0], fields_process=['approver_id'])
                    approver_user_id = exit_approver.approver_id and exit_approver.approver_id.user_id and exit_approver.approver_id.user_id.id or False
                    if uid == approver_user_id:
                        res[record.id][is_person] = True
                        res[record.id]['is_person_do_action_for_department'] = True
        
        return res
    
    def get_approver_department(self, cr, uid, ids, field_names, unknow_none, context = None):
        return self.get_login_and_id_department_approver(cr, uid, ids, context)
    
    def _check_waiting_for(self, cr, uid, ids, prop, unknow_none, context = None):
        if not context:
            context= {}
        
        context["search_all_employee"] = True
        context['active_test'] = False
        
        if uid:
            user = self.pool.get('res.users').read(cr, uid, uid, ['login'])
            login = user.get('login','')
            context['login'] = login
            
        res = self.get_login_users_waiting_for_action(cr, uid, ids, context)
        return res
    
    def is_action_user_search(self, cr, uid, obj, name, args, context=None):
        if not args:
            return []
        
        domain = []
        res = []
        employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=',uid)])
        if employee_ids:
            domain.extend(['&',('employee_id','in',employee_ids),('state','=','draft')])
            
#             department_ids = self.pool.get('hr.department').search(cr, SUPERUSER_ID,
#                                                                            [('manager_id', 'in', employee_ids)])
#             if department_ids:
            domain.insert(0, '|')
            domain.extend(['&','&',('state','=','department'),
                                   ('approver_user_responsibilities_hand_over_id','in',employee_ids),
                                   ('is_approve_responsibilities_hand_over','=',False)])
                
            dict = self.pool.get('vhr.termination.request').get_emp_make_delegate(cr, uid, employee_ids[0], {'a_model_name': self._name})
            if dict:
                for employee_id in dict:
                    domain.insert(0,'|')
                    domain.extend(['&','&','&',('approver_user_responsibilities_hand_over_id','=',employee_id),
                                               ('state','=','department'),
                                               ('department_id','in',dict[employee_id]),
                                               ('is_approve_responsibilities_hand_over','=',False)])
            
            dict = self.pool.get('vhr.termination.request').get_emp_make_delegate_by_process(cr, uid, employee_ids[0], {'a_model_name': self._name})
            if dict:
                for employee_id in dict:
                    domain.insert(0,'|')
                    domain.extend(['&','&','&',('approver_user_responsibilities_hand_over_id','=',dict[employee_id]),
                                               ('state','=','department'),
                                               ('employee_id','=',employee_id),
                                               ('is_approve_responsibilities_hand_over','=',False)])
                        
            #department filter
            exit_approver_pool = self.pool.get('vhr.exit.approver')
            approver_ids = exit_approver_pool.search(cr, uid, [('approver_id','=',employee_ids[0])])
            if approver_ids:
                city_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_human_resource_code_of_hochiminh_city') or ''
                hcm_city_id = False
                if city_code:
                    hcm_city_ids = self.pool.get('res.city').search(cr, uid, [('code','=',city_code)])
                    if hcm_city_ids:
                        hcm_city_id = hcm_city_ids[0]
                    
                for field in TEAM_FIELDS:
                    if field == 'responsibilities_hand_over_ids':
                        continue
                    is_approve_exit_type = TEAM_FIELDS[field][0]
                    is_person_for_exit_type = TEAM_FIELDS[field][3]
                    exit_type_code = TEAM_FIELDS[field][2]
                    exit_type_ids = self.pool.get('vhr.exit.type').search(cr, uid, [('code','=',exit_type_code)])
                    
                    #Get all city have exit approver
                    all_city_ids = []
                    all_exit_approver_ids =  exit_approver_pool.search(cr, uid, [('exit_type_id','in',exit_type_ids)])
                    if all_exit_approver_ids:
                        exit_approvers = exit_approver_pool.read(cr, uid, all_exit_approver_ids, ['city_id'])
                        all_city_ids = [exit_approver.get('city_id',False) and exit_approver['city_id'][0] for exit_approver in exit_approvers]
                    
                    #Get approver_ids that user is approver
                    approver_ids = exit_approver_pool.search(cr, uid, [('approver_id','=',employee_ids[0]),('exit_type_id','in',exit_type_ids)])
                    if approver_ids:
                        get_all_city = False
                        exit_approvers = exit_approver_pool.read(cr, uid, approver_ids, ['city_id'])
                        city_ids = [exit_approver.get('city_id',False) and exit_approver['city_id'][0] for exit_approver in exit_approvers]
                        #Get city_ids, user is not approver
                        except_city_ids = [city_id for city_id in all_city_ids if city_id not in city_ids]
                        #If user is approver for HCM, user is approver for other city not define in exit approver
                        operator_city = 'not in'
                        filter_city_id = except_city_ids
                        #If user is not approver for HCM, filter by city user is approver
                        if hcm_city_id not in city_ids:
                            operator_city = 'in'
                            filter_city_id = city_ids
                        
                        domain.insert(0, '|')
                        if field == 'it_office_ids':
                            domain.extend(['&','&','&',
                                                ('state','not in',['draft','cancel']),
                                                ('city_id',operator_city,filter_city_id),
                                                (is_approve_exit_type,'=',False),
                                                (is_person_for_exit_type,'=',True)])
                        else:
                            domain.extend(['&','&','&','&',
                                                ('state','not in',['draft','cancel']),
                                                (field,'!=',[]),
                                                ('city_id',operator_city,filter_city_id),
                                                (is_approve_exit_type,'=',False),
                                                (is_person_for_exit_type,'=',True)])
            
            res = self.search(cr, uid, domain)
            
            
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
    
    def _get_last_working_date(self, cr, uid, ids, field_name, unknow_none, context = None):
        res = {}
        records = self.read(cr, uid, ids, ['employee_id','join_date'])
        for record in records:
            res[record['id']] = {'correct_last_working_date': '','last_working_date': False}
            employee_id = record.get('employee_id', False) and record['employee_id'][0]
            join_date = record.get('join_date', False)
            if employee_id and join_date:
                
                last_working_date = self.get_last_working_date(cr, uid, employee_id, join_date, context)
                res[record['id']]['last_working_date'] = last_working_date
                if last_working_date:
                    res[record['id']]['correct_last_working_date'] = datetime.strptime(last_working_date, DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y")
        
        return res
    
    def _get_update_dept_head(self, cr, uid, ids, context=None):
        checklist_ids = self.pool.get('vhr.exit.checklist.request').search(cr, uid, [('employee_id','in',ids),
                                                                                     ('state','not in', ['cancel','finish'])])
        return checklist_ids
    
    def _get_update_last_working_date(self, cr, uid, ids, context=None):
        '''
        Lấy ra danh sách exit checklist có state!='cancel' và có join date lớn nhất của mỗi employee
        '''
        terminations = self.pool.get('vhr.termination.request').read(cr, uid, ids, ['employee_id'])
        employee_ids = [tr.get('employee_id', False) and tr['employee_id'][0] for tr in terminations]
        
        sql = """
                SELECT DISTINCT
                  first_value("id") OVER (PARTITION BY employee_id ORDER BY join_date DESC) 
                FROM vhr_exit_checklist_request
                where employee_id in %s and state != 'cancel'
                ORDER BY 1;
              """
        cr.execute(sql% str(tuple(employee_ids)).replace(',)', ')'))
        res = cr.fetchall()
        checklist_ids = [item[0] for item in res]
                
#         checklist_ids = self.pool.get('vhr.exit.checklist.request').search(cr, uid, [('employee_id','in',employee_ids),
#                                                                                      ('state','not in', ['cancel'])])
        return checklist_ids
    
    def _get_update_approver(self, cr, uid, ids, context=None):
        checklist_ids = self.pool.get('vhr.exit.checklist.request').search(cr, uid, [('state','not in', ['cancel','finish'])])
        return checklist_ids
    
    def _get_update_checklist(self, cr, uid, ids, context=None):
        return ids
    
    _columns = {
                'name': fields.char('Code', size=128),
                'employee_id': fields.many2one('hr.employee', 'Tên Nhân Viên', ondelete='restrict'),
                'department_id': fields.related('employee_id', 'department_id', type='many2one',
                                        relation='hr.department', string='Phòng làm việc',store=True),
                'report_to': fields.related('employee_id', 'report_to', type='many2one',
                                        relation='hr.employee', string='Reporting Line'),
                'city_id': fields.many2one('res.city', string='City', ondelete='restrict'),
                'employee_code': fields.related('employee_id', 'code', type="char", string="Mã Nhân Viên"),
#                 'company_id': fields.many2one('res.company', 'Company', ondelete='restrict'),
                'join_date': fields.date("Ngày bắt đầu làm việc"),
                'last_working_date': fields.function(_get_last_working_date, type='date',string='Ngày làm việc cuối cùng', 
                                                     multi='get_last_working_date', store={'vhr.termination.request':
                                                                                                    (_get_update_last_working_date, 
                                                                                                     ['employee_id','state','date_end_working_approve'],20),
                                                                                           'vhr.exit.checklist.request':
                                                                                                                    (_get_update_checklist,
                                                                                                                     ['name'],10)}),
                
                'correct_last_working_date': fields.function(_get_last_working_date, type='date', string='Correct Last Working Date', multi='get_last_working_date'),

                'email': fields.char('Email cá nhân', size=128),
                'note': fields.text('Ghi chú'),
 #                 Ban Giao Cong Viec
                 'is_approve_responsibilities_hand_over': fields.boolean('Is Approve Responsibilities Hand-over'),
                'approver_user_responsibilities_hand_over': fields.function(get_approver_department, type='char', string='Approver User Responsibilities Hand-over',
                                                                            multi='get_approver_department', store={'hr.employee':
                                                                                                                    (_get_update_dept_head,
                                                                                                                     ['department_id','team_id'],
                                                                                                                     20),
                                                                                                              'vhr.exit.checklist.request':
                                                                                                                    (_get_update_checklist,
                                                                                                                     ['employee_id','is_new'],10)}),
                'approver_user_responsibilities_hand_over_id': fields.function(get_approver_department, type='many2one', relation='hr.employee', string='Approver User Responsibilities Hand-over ID',
                                                                            multi='get_approver_department', store={'hr.employee':
                                                                                                                    (_get_update_dept_head,
                                                                                                                     ['department_id','team_id'],
                                                                                                                     20),
                                                                                                              'vhr.exit.checklist.request':
                                                                                                                    (_get_update_checklist,
                                                                                                                     ['employee_id','is_new'],10)}),
                'responsibilities_hand_over_ids': fields.one2many('vhr.exit.checklist.detail','exit_checklist_id', 'Exit Checklist Detail', ondelete='cascade',
                                                                  domain=[('type_exit', '=', 'responsibilities_hand_over')]),
                'is_person_responsibilities_hand_over': fields.function(_is_person_do_action_department, type='boolean', string='Is Person Do Action', multi="check_is_person"),
                  #Phong Hanh Chinh
                 'is_approve_administrative_office': fields.boolean('Is Approve Administrative Office'),
                'approver_user_administrative_office': fields.function(get_approver_department, type='char', string='Approver User Administrative Office',
                                                                       multi='get_approver_department',store={'vhr.exit.approver':
                                                                                                                    (_get_update_approver,
                                                                                                                     ['city_id', 'approver_id', 'active'],
                                                                                                                     20),
                                                                                                              'vhr.exit.checklist.request':
                                                                                                                    (_get_update_checklist,
                                                                                                                     ['employee_id','is_new'],10)}),
                'administrative_office_ids': fields.one2many('vhr.exit.checklist.detail','exit_checklist_id', 'Exit Checklist Detail', ondelete='cascade',
                                                             domain=[('type_exit', '=', 'administrative_office')]),
                'is_person_administrative_office': fields.function(_is_person_do_action_department, type='boolean', string='Is Person Do Action', multi="check_is_person"),
                
                #Phong hanh chinh other
                 'is_approve_administrative_office_other': fields.boolean('Is Approve Administrative Office Other'),
                'approver_user_administrative_office_other': fields.function(get_approver_department, type='char', string='Approver User Administrative Office Other',
                                                                             multi='get_approver_department',store={'vhr.exit.approver':
                                                                                                                    (_get_update_approver,
                                                                                                                     ['city_id', 'approver_id', 'active'],
                                                                                                                     20),
                                                                                                              'vhr.exit.checklist.request':
                                                                                                                    (_get_update_checklist,
                                                                                                                     ['employee_id','is_new'],10)}),
                'administrative_office_other_ids': fields.one2many('vhr.exit.checklist.detail','exit_checklist_id', 'Exit Checklist Detail', ondelete='cascade',
                                                             domain=[('type_exit', '=', 'administrative_office_other')]),
                'is_person_administrative_office_other': fields.function(_is_person_do_action_department, type='boolean', string='Is Person Do Action', multi="check_is_person"),
                 #Phong Cong Nghe Thong Tin 
                 'is_approve_it_office': fields.boolean('Is Approve IT Office'),
                'approver_user_it_office': fields.function(get_approver_department, type='char', string='Approver User IT Office',
                                                           multi='get_approver_department',store={'vhr.exit.approver':
                                                                                                                    (_get_update_approver,
                                                                                                                     ['city_id', 'approver_id', 'active'],
                                                                                                                     20),
                                                                                                              'vhr.exit.checklist.request':
                                                                                                                    (_get_update_checklist,
                                                                                                                     ['employee_id','is_new'],10)}),
                #Field này được sử dụng để đảm bảo việc get approver của các phòng ban từ các list field được khai báo trên cùng, 
                #sẽ được thực hiện chung với người approver của it office, khỏi mất công viết lại thêm code cho riêng IT Office
                'it_office_ids': fields.one2many('vhr.exit.checklist.detail','exit_checklist_id', 'Exit Checklist Detail', ondelete='cascade',
                                                             domain=[('type_exit', '=', 'it_office')]),
                'is_person_it_office': fields.function(_is_person_do_action_department, type='boolean', string='Is Person Do Action', multi="check_is_person"),
                #Phong CNTT other
                 'is_approve_it_office_other': fields.boolean('Is Approve IT Office Other'),
                  'approver_user_it_office_other': fields.function(get_approver_department, type='char', string='Approver User IT Office Other',
                                                                   multi='get_approver_department',store={'vhr.exit.approver':
                                                                                                                    (_get_update_approver,
                                                                                                                     ['city_id', 'approver_id', 'active'],
                                                                                                                     20),
                                                                                                              'vhr.exit.checklist.request':
                                                                                                                    (_get_update_checklist,
                                                                                                                     ['employee_id','is_new'],10)}),
                'it_office_other_ids': fields.one2many('vhr.exit.checklist.detail','exit_checklist_id', 'Exit Checklist Detail', ondelete='cascade',
                                                             domain=[('type_exit', '=', 'it_office_other')]),
                'is_person_it_office_other': fields.function(_is_person_do_action_department, type='boolean', string='Is Person Do Action', multi="check_is_person"),
                 #Phong TCKT
                 'is_approve_accounting_office': fields.boolean('Is Approve Accounting Office'),
                  'approver_user_accounting_office': fields.function(get_approver_department, type='char', string='Approver User Accounting Office',
                                                                     multi='get_approver_department',store={'vhr.exit.approver':
                                                                                                                    (_get_update_approver,
                                                                                                                     ['city_id', 'approver_id', 'active'],
                                                                                                                     20),
                                                                                                              'vhr.exit.checklist.request':
                                                                                                                    (_get_update_checklist,
                                                                                                                     ['employee_id','is_new'],10)}),
                'accounting_office_ids': fields.one2many('vhr.exit.checklist.detail','exit_checklist_id', 'Exit Checklist Detail', ondelete='cascade',
                                                             domain=[('type_exit', '=', 'accounting_office')]),
                'is_person_accounting_office': fields.function(_is_person_do_action_department, type='boolean', string='Is Person Do Action', multi="check_is_person"),
                
                 #Phong TCKT other
                 'is_approve_accounting_office_other': fields.boolean('Is Approve Accounting Office Other'),
                  'approver_user_accounting_office_other': fields.function(get_approver_department, type='char', string='Approver User Accounting Office Other',
                                                                     multi='get_approver_department',store={'vhr.exit.approver':
                                                                                                                    (_get_update_approver,
                                                                                                                     ['city_id', 'approver_id', 'active'],
                                                                                                                     20),
                                                                                                              'vhr.exit.checklist.request':
                                                                                                                    (_get_update_checklist,
                                                                                                                     ['employee_id','is_new'],10)}),
                'accounting_office_other_ids': fields.one2many('vhr.exit.checklist.detail','exit_checklist_id', 'Exit Checklist Detail', ondelete='cascade',
                                                             domain=[('type_exit', '=', 'accounting_office_other')]),
                'is_person_accounting_office_other': fields.function(_is_person_do_action_department, type='boolean', string='Is Person Do Action', multi="check_is_person"),

                #Phong Nhan Su Training
                 'is_approve_hr_office_training':fields.boolean('Is Approve HR Training'),
                  'approver_user_hr_office_training': fields.function(get_approver_department, type='char', string='Approver User  HR Training',
                                                                      multi='get_approver_department',store={'vhr.exit.approver':
                                                                                                                    (_get_update_approver,
                                                                                                                     ['city_id', 'approver_id', 'active'],
                                                                                                                     20),
                                                                                                              'vhr.exit.checklist.request':
                                                                                                                    (_get_update_checklist,
                                                                                                                     ['employee_id','is_new'],10)}),
                'hr_office_training_ids': fields.one2many('vhr.exit.checklist.detail','exit_checklist_id', 'Exit Checklist Detail', ondelete='cascade',
                                                             domain=[('type_exit', '=', 'hr_office_training')]),
                'is_person_hr_office_training': fields.function(_is_person_do_action_department, type='boolean', string='Is Person Do Action', multi="check_is_person"),
                #Phong Nhan Su other
                 'is_approve_hr_office_other': fields.boolean('Is Approve HR Other'),
                  'approver_user_hr_office_other': fields.function(get_approver_department, type='char', string='Approver User  HR Other',
                                                                   multi='get_approver_department',store={'vhr.exit.approver':
                                                                                                                    (_get_update_approver,
                                                                                                                     ['city_id', 'approver_id', 'active'],
                                                                                                                     20),
                                                                                                              'vhr.exit.checklist.request':
                                                                                                                    (_get_update_checklist,
                                                                                                                     ['employee_id','is_new'],10)}),
                'hr_office_other_ids': fields.one2many('vhr.exit.checklist.detail','exit_checklist_id', 'Exit Checklist Detail', ondelete='cascade',
                                                             domain=[('type_exit', '=', 'hr_office_other')]),
                'is_person_hr_office_other': fields.function(_is_person_do_action_department, type='boolean', string='Is Person Do Action', multi="check_is_person"),
                
                #Is Person have power to approve at state waiting department
                'is_person_do_action_for_department': fields.function(_is_person_do_action_department, type='boolean', string='Is Person Do Action For Department', multi="check_is_person"),

 
                'state': fields.selection(STATES, 'Status',readonly='True'),
                'is_person_do_action': fields.function(_is_person_do_action, type='boolean', string='Is Person Do Action'),
                'waiting_for' : fields.function(_check_waiting_for, type='char', string='Waiting For', readonly = 1, multi='waiting_for'),
                'is_waiting_for_action' : fields.function(_check_waiting_for, type='boolean', string='Yêu cầu đang chờ duyệt', readonly = 1, 
                                                          multi='waiting_for', fnct_search=is_action_user_search),

                'state_log_ids': fields.one2many('vhr.state.change', 'res_id', 'History', domain=[('model', '=', _name)]),
                'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                      domain=[('object_id.model', '=', _name), \
                                              ('field_id.name', 'not in', ['write_date', 'audit_log_ids'])]),
                
                'back_department_ids': fields.many2many('vhr.dimension', 'exit_checklist_department_rel','exit_checklist_request_ids','department','Back Departments',
                                                   domain=[('dimension_type_id.code', '=', 'CHECKLIST_DEPT')]),
                
                'request_date': fields.date('Ngày tạo yêu cầu'),
                'is_new': fields.boolean('is New'),
                'is_person_able_to_edit_employee': fields.function(_is_person_able_to_edit_employee, type='boolean', string="Is Person Able To Edit Employee"),
#                 'money_payment_of_it_office': fields.float('Money Payment Of It Office'),
#                 'notes_of_it_office': fields.text('Notes Of IT Office'),
                
                'create_uid': fields.many2one('res.users', 'Create User', ondelete='restrict'),
                'is_person_able_to_reject': fields.function(_is_person_able_to_reject, type='boolean', string="Is Person Able To Reject", multi='get_person_reject'),
                'is_cb_termination': fields.function(_is_person_able_to_reject, type='boolean', string="Is C&B Termination", multi='get_person_reject'),
                'approve_date': fields.date('Approved Date'),
    }
    
    _order = "last_working_date desc , approve_date desc"
    
    def _get_requester_id(self, cr, uid, context=None):
        context["search_all_employee"] = True
        employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', uid)], context=context)
        if employee_ids:
            return employee_ids[0]

        return False
    
    def _get_is_able_to_edit_employee(self, cr, uid, context=None):
        return self.get_is_able_to_edit_employee(cr, uid)
    
    def _get_is_cb_termination(self, cr, uid, context=None):
        groups = self.pool.get('res.users').get_groups(cr, uid)
        return 'vhr_cb_termination' in groups
                    
    _defaults = {
                'state': 'draft',
                'is_person_do_action': True,
#                 'is_register_unemployment_benefits': True,
                'is_new': True,
                'request_date': fields.datetime.now,
                 'employee_id': _get_requester_id,
                 'is_person_able_to_edit_employee': _get_is_able_to_edit_employee,
                 'is_cb_termination': _get_is_cb_termination,
#                  'approve_date': fields.datetime.now,
                }
    
    def get_is_able_to_edit_employee(self, cr, uid):
        groups = self.pool.get('res.users').get_groups(cr, uid)
        is_able = False
        if set(['vhr_dept_admin','vhr_cb_termination','vhr_assistant_to_hrbp','vhr_hrbp']).intersection(set(groups)):
            is_able = True
        
        return is_able
    
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
    
    def read(self, cr, user, ids, fields=None, context=None, load='_classic_read'):
        if not context:
            context = {}
        
        if 'active_test' not in context:
            context['active_test'] = False
            
        if context.get('validate_read_vhr_exit_checklist_request',False):
            log.info('\n\n validate_read_vhr_exit_checklist_request')
            if not context.get('filter_by_permission_exit_checklist', False):
                context['filter_by_permission_exit_checklist'] = True
            result_check = self.validate_read(cr, user, ids, context)
            if not result_check:
                raise osv.except_osv('Validation Error !', 'You don’t have permission to access this data !')
            
            del context['validate_read_vhr_exit_checklist_request']
        
        res =  super(vhr_exit_checklist_request, self).read(cr, user, ids, fields, context, load)
            
        return res
    
    def validate_read(self, cr, uid, ids, context=None):
        user_groups = self.pool.get('res.users').get_groups(cr, uid)
        if set(['hrs_group_system', 'vhr_cnb_manager', 'vhr_hr_dept_head','vhr_cb_termination']).intersection(set(user_groups)):
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
    
    def get_login_users_waiting_for_action(self, cr, uid, ids, context=None):
        res = {}
        if ids:
            login = context.get('login',False)
            for record in self.read(cr, uid, ids, ['state']):
                vals = ''
                vals_id = []
                state = record.get('state', '')
                if state == 'draft':
                    meta_datas = self.perm_read(cr, SUPERUSER_ID, [record['id']], context)
                    user_id =  meta_datas and meta_datas[0].get('create_uid', False) and meta_datas [0]['create_uid'][0] or False
                    if user_id:
                        context['search_all_employee'] = True
                        employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', user_id)], 0, None, None,
                                                                           context)
                        if employee_ids:
                            employee = self.pool.get('hr.employee').read(cr, uid, employee_ids[0], ['login'])
                            requester_name =employee.get('login', '')
                            vals = '%s' % (requester_name)
                            vals_id.append(employee_ids[0])
                            
                elif state == 'department':
                    dep_data = self.get_login_and_id_department_approver(cr, uid, record['id'], context)
                    approver_login_list = dep_data[record['id']]['approver_login']
                    approver_login_list = list(set(approver_login_list))
                    vals = '; '.join(approver_login_list)
                    
                    approver_ids = dep_data[record['id']]['approver_id']
                    vals_id.extend(approver_ids)
                    
#                 elif state == 'hrbp':
#                     hrbp_names, hrbp_ids, hrbp_mails = self.get_hrbp_name_and_id(cr, uid, record['id'], context)
#                     vals = '; '.join(hrbp_names)
#                     vals_id.extend(hrbp_ids)
#                     
#                 elif state == 'hr_executor':
#                     names, emp_ids, mails = self.get_hr_executor_name_and_id(cr, uid, context)
#                     vals = '; '.join(names)
#                     vals_id.extend(emp_ids)
                
                res[record['id']] = vals
                
                res[record['id']] = {'is_waiting_for_action': False}
                res[record['id']]['waiting_for'] = vals
                if login in vals:
                    res[record['id']]['is_waiting_for_action'] = True
                
#                 result_ids[item.id] = vals_id
        
        return res
    
    def get_requester_mail(self, cr, uid, record_id, context=None):
        if not context:
            context = {}
        
        requester_mail = ''
        if record_id:
            meta_datas = self.perm_read(cr, SUPERUSER_ID, [record_id], context)
            user_id =  meta_datas and meta_datas[0] and meta_datas[0].get('create_uid', False) and meta_datas [0]['create_uid'] or False
            if isinstance(user_id, tuple):
                user_id = user_id[0]
            if user_id:
                context['search_all_employee'] = True
                employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', user_id)], 0, None, None,
                                                                   context)
                if employee_ids:
                    employee = self.pool.get('hr.employee').read(cr, uid, employee_ids[0], ['work_email'])
                    requester_mail = employee.get('work_email','')
        
        return requester_mail
    
    def get_personal_email(self, cr, uid, record_id, context=None):
        if not context:
            context = {}
        
        personal_email = ''
        if record_id:
            data = self.read(cr, uid, record_id, ['email'])
            personal_email = data.get('email','')
        
        return personal_email
    
    def get_hr_executor_name_and_id(self, cr, uid, context=None):
        names = []
        emp_ids = []
        mails = []
        employee_ids = self.pool.get('vhr.working.record').get_employee_ids_belong_to_group(cr, uid, 'group_hr_executor', context)
        if employee_ids:
            employees = self.pool.get('hr.employee').read(cr, uid, employee_ids, ['login','work_email'])
            for employee in employees:
                emp_ids.append(employee.get('id',False))
                names.append(employee.get('login',''))
                mails.append(employee.get('work_email',''))
        
        return names, emp_ids, mails
                        
    
    def get_hrbp_name_and_id(self, cr, uid, record_id, context=None):
        if not context:
            context = {}
        hrbp_names = []
        hrbp_ids = []
        hrbp_mails = []
        if record_id:
            record = self.browse(cr, uid, record_id, fields_process=['employee_id'])
            hrbps = record.employee_id and record.employee_id.department_id and record.employee_id.department_id.hrbps or []
            if hrbps:
                for emp in hrbps:
                    hrbp_ids.append(emp.id)
                    hrbp_names.append(emp.login)
                    hrbp_mails.append(emp.work_email)
                    
        return hrbp_names, hrbp_ids, hrbp_mails
    
    def get_assist_hrbp_name_and_id(self, cr, uid, record_id, context=None):
        if not context:
            context = {}
        hrbp_names = []
        hrbp_ids = []
        hrbp_mails = []
        if record_id:
            record = self.browse(cr, uid, record_id, fields_process=['employee_id'])
            hrbps = record.employee_id and record.employee_id.department_id and record.employee_id.department_id.ass_hrbps or []
            if hrbps:
                for emp in hrbps:
                    hrbp_ids.append(emp.id)
                    hrbp_names.append(emp.login)
                    hrbp_mails.append(emp.work_email)
                    
        return hrbp_names, hrbp_ids, hrbp_mails
    
    def get_available_approver_department_mail(self, cr, uid, record_id, context=None):
        """
        Get list email of all approver in state department (dont count approver of section dont have data)
        """
        res_mail = []
        if record_id:
            res = self.get_login_and_id_department_approver(cr, uid, [record_id], context)
            res_mail = res[record_id]['all_approver_mail']
        
        return res_mail
    
    def get_return_approver_mail(self, cr, uid, record_id, context=None):
        """
        Get list email of approver have been return by hr_executor
        """
        res_mail = []
        if record_id:
            res = self.get_login_and_id_department_approver(cr, uid, [record_id], context)
            res_mail = res[record_id]['approver_mail']
        
        return res_mail
            
    
    def get_login_and_id_department_approver(self, cr, uid, ids, context=None):
        if not isinstance(ids, list):
            ids = [ids]
        res = {}
        exit_detail_pool = self.pool.get('vhr.exit.checklist.detail')
        emp_pool = self.pool.get('hr.employee')
        
        if ids:
                                
            fields = DEPARTMENT_FIELDS + ['employee_id'] + APPROVE_FIELDS
            for record in self.read(cr, uid, ids, fields):
                record_id = record['id']
                res[record_id] = {}
                employee_id = record.get('employee_id', False) and record['employee_id'][0] or False
                res[record_id] = self.get_login_id_department_approver_from_employee_id(cr, uid, employee_id, res[record_id], record, context)
                                
        return res
    
    def get_login_id_department_approver_from_employee_id(self, cr, uid, employee_id, res, record, context=None):
        if not record:
            record = {}
        res['approver_login'] = []#List approver does not approve
        res['approver_id'] = []#List approver does not approve
        res['approver_mail'] = []#List mail of approver does not approve
        res['all_approver_mail'] = []#List approver available(have data in their section)
        if employee_id:
            exit_approver_pool = self.pool.get('vhr.exit.approver')
            exit_type_pool = self.pool.get('vhr.exit.type')
            emp_pool = self.pool.get('hr.employee')
            employee = emp_pool.browse(cr, uid, employee_id)
            emp_city_id = employee.office_id and employee.office_id.city_id and employee.office_id.city_id.id or False
            department_id = employee.department_id and employee.department_id.id or False
            report_to = employee.report_to or False
            manager = employee.parent_id or False
            
            city_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_human_resource_code_of_hochiminh_city') or ''
            hcm_city_ids = []
            if city_code:
                hcm_city_ids = self.pool.get('res.city').search(cr, uid, [('code','=',city_code)])
                
            for field in DEPARTMENT_FIELDS:
                        
                approver_field = TEAM_FIELDS[field][1]
                is_approved_field = TEAM_FIELDS[field][0]
                
                is_approved = record.get(is_approved_field, False)
                res[approver_field] = ''
                
                if field == 'responsibilities_hand_over_ids':
                    if report_to:
                        manager = report_to
                        
                    if manager:
                        manager_login = manager.login or ''
                        manager_ext = manager.ext_no or ''
                        res[approver_field] = manager_login + ' (Ext. ' +  manager_ext + ')'
                        res['approver_user_responsibilities_hand_over_id'] = manager.id
                        if not is_approved:
                            res['approver_login'].append(manager_login)
                            res['approver_id'].append(manager.id)
                        
                        if record.get(field, False):
                            res['all_approver_mail'].append(manager.work_email or '')
                            if not is_approved:
                                res['approver_mail'].append(manager.work_email or '')
                    
                        delegator_ids = self.get_delegator(cr, uid, department_id, manager.id)
                        if delegator_ids:
                            res['approver_user_responsibilities_hand_over_delegate_ids'] = []
                            for employee_id in delegator_ids:
                                employee = emp_pool.read(cr, uid, employee_id, ['login','work_email'])
                                res['approver_user_responsibilities_hand_over_delegate_ids'].append(employee.get('login',''))
                                if not is_approved:
                                    res['approver_login'].append(employee.get('login',''))
                                    res['approver_id'].append(employee['id'])
                                
                                if record.get(field, False):
                                    res['all_approver_mail'].append(employee.get('work_email', ''))
                                    if not is_approved:
                                        res['approver_mail'].append(employee.get('work_email', ''))
                        
                        
                        if record.get('id', False):
                            delegator_ids = self.get_delegator_by_process(cr, uid, record['id'], manager.id)
                            if delegator_ids:
                                if not res.get('approver_user_responsibilities_hand_over_delegate_ids', False):
                                    res['approver_user_responsibilities_hand_over_delegate_ids'] = []
                                for employee_id in delegator_ids:
                                    employee = emp_pool.read(cr, uid, employee_id, ['login','work_email'])
                                    res['approver_user_responsibilities_hand_over_delegate_ids'].append(employee.get('login',''))
                                    if not is_approved:
                                        res['approver_login'].append(employee.get('login',''))
                                        res['approver_id'].append(employee['id'])
                                    
                                    if record.get(field, False):
                                        res['all_approver_mail'].append(employee.get('work_email', ''))
                                        if not is_approved:
                                            res['approver_mail'].append(employee.get('work_email', ''))
                    
                    continue
                
                code_exit_type = TEAM_FIELDS[field][2]
                exit_type_ids = exit_type_pool.search(cr, uid, [('code','=',code_exit_type)])
                if exit_type_ids:
                    exit_approver_ids = exit_approver_pool.search(cr, uid, [('exit_type_id','=',exit_type_ids[0]),
                                                                            ('city_id','=',emp_city_id)])
                    #Get approver name of exit type
                    if exit_approver_ids:
                        approver_login, ext_approver, approver_id, approver_mail = self.get_data_from_exit_approver(cr, uid, exit_approver_ids[0], context)
  
                        res[approver_field] = approver_login + ' (Ext. ' +  ext_approver + ')'
                        if not is_approved and record.get(field, False):
                            res['approver_login'].append(approver_login)
                            res['approver_id'].append(approver_id)
                        if record.get(field, False):
                            res['all_approver_mail'].append(approver_mail)
                            if not is_approved:
                                res['approver_mail'].append(approver_mail)
                    else:
                        #Get approver name of exit type in HCM if employee work in office not in exit approver city
                        if hcm_city_ids:
                            exit_approver_ids = exit_approver_pool.search(cr, uid, [('exit_type_id','=',exit_type_ids[0]),
                                                                                    ('city_id','in',hcm_city_ids)])
                
                            if exit_approver_ids:
                                approver_login, ext_approver, approver_id, approver_mail = self.get_data_from_exit_approver(cr, uid, exit_approver_ids[0], context)
                                
                                res[approver_field] = approver_login + ' (Ext. ' +  ext_approver + ')'
                                if not is_approved and record.get(field, False):
                                    res['approver_login'].append(approver_login)
                                    res['approver_id'].append(approver_id)
                                
                                if record.get(field, False):
                                    res['all_approver_mail'].append(approver_mail)
                                    if not is_approved:
                                        res['approver_mail'].append(approver_mail)
        return res
    
    
    def get_data_from_exit_approver(self, cr, uid, exit_approver_id, context=None):
        approver_login = ''
        ext_approver = ''
        approver_id = False
        approver_mail = ''
                        
        if exit_approver_id:
            exit_approver_pool = self.pool.get('vhr.exit.approver')
            exit_approver = exit_approver_pool.browse(cr, uid, exit_approver_id, fields_process=['approver_id'])
            approver_id = exit_approver.approver_id and exit_approver.approver_id.id or False
            approver_login = exit_approver.approver_id and exit_approver.approver_id.login or ''
            ext_approver = exit_approver.approver_id and exit_approver.approver_id.ext_no or ''
            approver_mail = exit_approver.approver_id and exit_approver.approver_id.work_email or ''
                
        return approver_login, ext_approver, approver_id, approver_mail
            
#     def is_hrbp(self, cr, uid, ids, context=None):
#         hrbp_employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', uid)], context=context)
#         if ids and hrbp_employee_ids:
#             hrbp_names, hrbp_ids, hrbp_mails = self.get_hrbp_name_and_id(cr, uid, ids[0], context)
#             if hrbp_employee_ids[0] in hrbp_ids:
#                 return True
# 
#         return False
    
    def is_creator(self, cr, uid, ids, context=None):
        if ids:
            meta_datas = self.perm_read(cr, SUPERUSER_ID, ids, context)
            if meta_datas and meta_datas[0].get('create_uid', False) and meta_datas[0]['create_uid'][0] == uid:
                return True
        
        return False
    
    def is_person_do_action(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        context['search_all_employee'] = True
        context['active_test'] = False
        if ids:
            employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', uid)], context=context)
            
            state = context.get('state', False)
            record = self.read(cr, uid, ids[0], ['state'])
            if not state:
                state = record.get('state','')
            
            groups = self.pool.get('res.users').get_groups(cr, uid)

            if (state == 'draft' and self.is_creator(cr, uid, ids, context)):
#                     or (state == 'hrbp' and  self.is_hrbp(cr, uid, ids, context)) \
#                     or (state == 'hr_executor' and 'group_hr_executor' in groups):
                return True
            
            elif state == 'department' and employee_ids:
                res = self.get_login_and_id_department_approver(cr, uid, ids[0], context)
                approver_ids = res[ids[0]]['approver_id']
                if employee_ids[0] in approver_ids:
                    return True
                
            elif state=='finish' and ('group_hr_executor' in groups or 'vhr_cb_termination' in groups):
                return True

        return False
    
    def is_person_do_action_reject(self, cr, uid, ids, context=None):
        '''
        When change this function need to change function _is_person_able_to_reject to apply for field is_person_able_to_reject
        '''
        result = False
        if ids:
            groups = self.pool.get('res.users').get_groups(cr, uid)
            result = 'vhr_cb_termination' in groups
        
        return result
            
        
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        # Search rule for specific menu
        if not context:
            context = {}
        
        if 'active_test' not in context:
            context['active_test'] = False
            
        if context.get('filter_by_permission_exit_checklist',False):
            new_args = []   
            log.info( "\n search filter_by_permission_exit_checklist")
            groups = self.pool.get('res.users').get_groups(cr, uid)
            employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', uid)], context={'active_test': False})
            
            if not employee_ids:
                new_args = [('id','in',[])]
                
            elif set(['hrs_group_system','vhr_cb_termination','vhr_cnb_manager']).intersection(set(groups)):
                new_args = []
            elif employee_ids:
#                 department_ids = self.pool.get('hr.department').search(cr, SUPERUSER_ID,
#                                                                            [('manager_id', 'in', employee_ids)])
                
                department_hrbp_ids = self.get_department_of_hrbp(cr, uid, employee_ids[0], context)
                department_ass_hrbp_ids = self.get_department_of_ass_hrbp(cr, uid, employee_ids[0], context)
                department_hrbp_ids += department_ass_hrbp_ids
                
                new_args = ['|','|','|',
                                '&',('employee_id', 'in', employee_ids), ('state', '!=', False),#Draft
                                '&',('create_uid', '=', uid), ('state', '!=', False),#Draft
                                ('department_id', 'in', department_hrbp_ids),#HRBP
                                '&',('approver_user_responsibilities_hand_over_id','in',employee_ids),('state','!=','draft'),#Department--Responsible hand over
                            ]
                
                dict = self.pool.get('vhr.termination.request').get_emp_make_delegate(cr, uid, employee_ids[0], {'a_model_name': self._name})
                if dict:
                    for employee_id in dict:
                        new_args.insert(0,'|')
                        new_args.extend(['&','&',('approver_user_responsibilities_hand_over_id','=',employee_id),
                                                 ('state','!=','draft'),
                                                 ('department_id','in',dict[employee_id])])
                
                dict = self.pool.get('vhr.termination.request').get_emp_make_delegate_by_process(cr, uid, employee_ids[0], {'a_model_name': self._name})
                if dict:
                    print 'dict=',dict
                    for employee_id in dict:
                        new_args.insert(0,'|')
                        new_args.extend(['&','&',('approver_user_responsibilities_hand_over_id','=',dict[employee_id]),
                                                 ('state','!=','draft'),
                                                 ('employee_id','=',employee_id)])
                        
                #department filter
                exit_approver_pool = self.pool.get('vhr.exit.approver')
                approver_ids = exit_approver_pool.search(cr, uid, [('approver_id','=',employee_ids[0])])
                if approver_ids:
                    city_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_human_resource_code_of_hochiminh_city') or ''
                    hcm_city_id = False
                    if city_code:
                        hcm_city_ids = self.pool.get('res.city').search(cr, uid, [('code','=',city_code)])
                        if hcm_city_ids:
                            hcm_city_id = hcm_city_ids[0]
                        
                    for field in TEAM_FIELDS:
                        exit_type_code = TEAM_FIELDS[field][2]
                        exit_type_ids = self.pool.get('vhr.exit.type').search(cr, uid, [('code','=',exit_type_code)])
                        
                        #Get all city have exit approver
                        all_city_ids = []
                        all_exit_approver_ids =  exit_approver_pool.search(cr, uid, [('exit_type_id','in',exit_type_ids)])
                        if all_exit_approver_ids:
                            exit_approvers = exit_approver_pool.read(cr, uid, all_exit_approver_ids, ['city_id'])
                            all_city_ids = [exit_approver.get('city_id',False) and exit_approver['city_id'][0] for exit_approver in exit_approvers]
                        
                        #Get approver_ids that user is approver
                        approver_ids = exit_approver_pool.search(cr, uid, [('approver_id','=',employee_ids[0]),('exit_type_id','in',exit_type_ids)])
                        if approver_ids:
                            get_all_city = False
                            exit_approvers = exit_approver_pool.read(cr, uid, approver_ids, ['city_id'])
                            city_ids = [exit_approver.get('city_id',False) and exit_approver['city_id'][0] for exit_approver in exit_approvers]
                            #Get city_ids, user is not approver
                            except_city_ids = [city_id for city_id in all_city_ids if city_id not in city_ids]
                            
                            exit_ids = []
                            if field == 'accounting_office_other_ids':
                                sql = "select exit_checklist_id from vhr_exit_checklist_detail where type_exit='accounting_office_other'"
                                cr.execute(sql)
                                exit_ids = [group[0] for group in cr.fetchall()]
                                
                            #If user is approver for HCM, user is approver for other city not define in exit approver
                            if hcm_city_id in city_ids:
                                new_args.insert(1, '|')
                                sub_args = ['&','&',('state','not in',['draft']),(field,'!=',[]),('city_id','not in',except_city_ids)]
                                
                                if field == 'accounting_office_other_ids':
                                    sub_args.insert(0,'&')
                                    sub_args.append(('id','in',exit_ids))
                                new_args.extend(sub_args)
                            else:
                                #If user is not approver for HCM, filter by city user is approver
                                new_args.insert(1, '|')
                                sub_args = ['&','&',('state','not in',['draft']),(field,'!=',[]),('city_id','in',city_ids)]
                                if field == 'accounting_office_other_ids':
                                    sub_args.insert(0,'&')
                                    sub_args.append(('id','in',exit_ids))
                                new_args.extend(sub_args)
    
                    
                if 'group_hr_executor' in groups:
                    new_args.insert(1, '|')
                    new_args.append(('state','in',['hr_executor','finish']))
            args += new_args
         
        return super(vhr_exit_checklist_request, self).search(cr, uid, args, offset, limit, order, context, count)
    
    
    
    
    def create(self, cr, uid, vals, context=None):
        
        if vals.get('request_date',False) and len(vals['request_date']) > 10:
            vals['request_date'] = vals['request_date'][:10]
            
        for field in DEPARTMENT_FIELDS:
            if field in ['it_office_ids','accounting_office_other_ids']:
                continue
            if not vals.get(field, []):
                is_approved_field = TEAM_FIELDS[field][0]
                vals[is_approved_field] = True
        
        vals.update({'is_new': False})
        self.check_duplicate(cr, uid, vals.get('employee_id', False), vals.get('join_date', False), context)
        
        #Check when create termination from form for other employee, raise error if employee dont belong to any special group of HR
        employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=',uid)])
        if employee_ids and vals.get('employee_id', False) not in employee_ids:
            groups = self.pool.get('res.users').get_groups(cr, uid)
            special_groups = ['vhr_cb','vhr_hrbp','vhr_assistant_to_hrbp','hrs_group_system']
            if not set(groups).intersection(special_groups):
                raise osv.except_osv('Validation Error !', "You don't have permission to create Checklist Request for other employees")
            
        res = super(vhr_exit_checklist_request, self).create(cr, uid, vals, context)
        
        return res
    
    def write(self, cr, uid, ids, vals, context=None):
        
        if not isinstance(ids, list):
            ids = [ids]
            
        if vals.get('employee_id', False):
            self.check_duplicate(cr, uid, vals.get('employee_id', False), vals.get('join_date', False), context)
        
        
        #Check if write is restrict
        if not self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_human_resource_turn_off_check_update_exit_checklist'):
            employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=',uid)])
            if employee_ids and vals:
                groups = self.pool.get('res.users').get_groups(cr, uid)
                special_groups = ['vhr_cb','vhr_assistant_to_hrbp','hrs_group_system']
                
                record = self.read(cr, uid, ids[0], ['employee_id','report_to','department_id'])
                saved_emp_id = record.get('employee_id', False) and record['employee_id'][0] or False
                report_to = record.get('report_to', False) and record['report_to'][0] or False
                department_id = record.get('department_id', False) and record['department_id'][0] or False
                emp_id = vals.get('employee_id', saved_emp_id)
                
                delegator_ids = []
                if report_to:
                    delegator_ids = self.get_delegator(cr, uid, department_id, report_to)
                    
                    delegator_process_ids = self.get_delegator_by_process(cr, uid, ids[0], report_to)
                    delegator_ids  += delegator_process_ids
                    
                if not set(groups).intersection(special_groups) and emp_id not in employee_ids \
                   and report_to not in employee_ids and not set(delegator_ids).intersection(employee_ids):
                    approver_ids = self.pool.get('vhr.exit.approver').search(cr, uid, [('approver_id','in',employee_ids)])
                    if not approver_ids:
                        raise osv.except_osv('Validation Error !', "You don't have permission to update Checklist Request for other employees")
        
        res = super(vhr_exit_checklist_request, self).write(cr, uid, ids, vals, context)
        
        return res
    
    def check_duplicate(self, cr, uid, employee_id, join_date, context=None):
        if employee_id:
            duplicate_ids = self.search(cr, uid, [('employee_id','=',employee_id),
                                                    ('join_date','=',join_date),
                                                    ('state','!=','cancel')])
            if duplicate_ids:
                raise osv.except_osv('Lỗi xác thực !', 'Nhân viên - Ngày bắt đầu làm việc đã tồn tại trong một yêu cầu khác !')
        
        return True
    
    def get_list_approver(self, cr, uid, ids, context=None):
        if ids:
            record = self.read(cr, uid, ids[0],DEPARTMENT_FIELDS)
            user_ids = []
            logins = []
            for field in DEPARTMENT_FIELDS:
                if record.get(field, False):
                    approver = record[field][0]
                
            
    
    def onchange_employee_id(self, cr, uid, ids, employee_id, context=None):
        res = {'employee_code': '', 'join_date': '','last_working_date': False,'department_id':False}
        if employee_id:
            employee = self.pool.get('hr.employee').browse(cr, uid, employee_id, fields_process=['code','join_date','login','email','office_id','department_id'])
            account_domain = employee.login or ''
            res['employee_code'] = employee.code or ''
            res['join_date'] = employee.join_date or False
#             res['email'] = employee.email or ''
            res['city_id'] = employee.office_id and employee.office_id.city_id and employee.office_id.city_id.id or False
            res['department_id'] = employee.department_id and employee.department_id.id or False
            
            res_checklist = self.get_popular_checklist_detail(cr, uid, employee_id, account_domain, context)
            res_department_approver = self.get_login_id_department_approver_from_employee_id(cr, uid, employee_id, res, {},context)
            res.update(res_checklist)
            
            res['last_working_date'] = self.get_last_working_date(cr, uid, employee_id, res['join_date'], context)
            
        
        return {'value': res}
    
    def get_last_working_date(self, cr, uid, employee_id, join_date, context=None):
        date = False
        if employee_id and join_date:
            termination_pool = self.pool.get('vhr.termination.request')
            termination_ids = termination_pool.search(cr, uid, [('employee_id','=',employee_id),
                                                                ('state','!=','cancel'),
                                                                ('date_end_working_approve','>',join_date)
                                                                ], limit =1, order='date_end_working_approve asc')
            if termination_ids:
                for termination_id in termination_ids:
                    termination = termination_pool.read(cr, uid, termination_id, ['date_end_working_approve'])
                    date = termination.get('date_end_working_approve',False)
                    if self.compare_day(join_date, date) >0:
                        return date
        
        return False
                
    
    def get_popular_checklist_detail(self, cr, uid, employee_id, account_domain, context=None):
        if context is None:
            context = {}
        res = {}
        checklist_detail = []
        exit_type_pool = self.pool.get('vhr.exit.type')
        exit_pool = self.pool.get('vhr.exit')
        
                    #  exit type code -- exit type  --- ids
        loop_unique = [('1','responsibilities_hand_over', 'responsibilities_hand_over_ids'), #Ban Giao Cong Viec
                       ('11','administrative_office_other',  'administrative_office_other_ids'),#Phong hanh chinh other
                       ('12','it_office_other', 'it_office_other_ids'),           #Phong CNTT Other
                       ('4','accounting_office', 'accounting_office_ids'),          #Phong TCKT
                       ('10','hr_office_training', 'hr_office_training_ids'),        #Phong Nhan su dao tao
                       ('8','hr_office_other', 'hr_office_other_ids')]           #Phong Nhan su other
        for item in loop_unique:
            checklist_detail = self.get_popular_checklist_detail_by_exit_type_code(cr, uid, item[0], item[1], context)
            res[item[2]] = checklist_detail
        
        
        try:
            asset_unique = [('AF', 'administrative_office', 'administrative_office_ids'),
#                         ('IT', 'it_office', 'it_office_ids')
                        ]
            for item in asset_unique:
                property_type_code = item[0]
                exit_type = item[1]
                property_type_pool = self.pool.get('vhr.property.type')
                property_type_id = property_type_pool.search(cr, uid, [('code','=',property_type_code)])
                if property_type_id:
                    asset_detail = self.get_asset_of_user_from_property_type(cr, uid, employee_id, property_type_id, exit_type, context)
                    res[item[2]] = asset_detail
            
            res['it_office_ids'] = [[0,False,{'type_exit':'it_office','name':'IT Office Note'}]]
            
            if employee_id:
                emp = self.pool.get('hr.employee').read(cr, uid, employee_id, ['department_id'])
                department_id = emp.get('department_id', False) and emp['department_id'][0]
                if department_id:
                    check_ids = self.pool.get('vhr.exit.checklist.department.fa').search(cr, uid, [('department_id','=',department_id),
                                                                                                   ('active','=',True)])
                    if check_ids:
                        res['accounting_office_other_ids'] = [[0,False,{'type_exit':'accounting_office_other','name':'Accounting Office Note'}]]
        except Exception as e:
            print "\n Error connect to get Asset"
            log.exception(e)
        
        return res
    
    def get_popular_checklist_detail_by_exit_type_code(self, cr, uid, exit_type_code, type_exit, context=None):
        exit_type_pool = self.pool.get('vhr.exit.type')
        exit_pool = self.pool.get('vhr.exit')
        checklist_detail = []
        if exit_type_code and type_exit:
            type_ids = exit_type_pool.search(cr, uid, [('code','=',exit_type_code)])
            if type_ids:
                exit_ids = exit_pool.search(cr, uid, [('exit_type_id','in',type_ids), ('active','=',True)])
                if exit_ids:
                    for record in exit_pool.read(cr, uid, exit_ids, ['name']):
                        checklist_detail.append([0, False, {'name': record['name'], 'exit_id':record['id'], 'type_exit': type_exit}])
        
        return checklist_detail
    
    def get_asset_of_user_from_property_type(self, cr, uid, employee_id, property_type_id, exit_type, context=None):
        res = []
        if employee_id and property_type_id and exit_type:
            property_management_pool = self.pool.get('vhr.property.management')
            property_management_ids = property_management_pool.search(cr, uid, [('employee_id','=',employee_id),
                                                                                ('active','=',True),
                                                                                ('property_type_id','=',property_type_id),
                                                                                ('recovery_date','=',False)])
            if property_management_ids:
                property_managements = property_management_pool.read(cr, uid, property_management_ids, ['property_id','issue_date','recovery_date'])
                for record in property_managements:
                    property_name = record.get('property_id','')
                    if isinstance(property_name, tuple):
                        property_name = property_name[1]
                    res.append([0,False, {'name': property_name, 
                                          'type_exit': exit_type, 
                                          'allocation_date': record.get('issue_date'),
                                          'withdraw_date': record.get('recovery_date'),
                                          'property_management_id': record['id']}])
        return res
    

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        
        for record in self.read(cr, uid, ids, ['state']):
            if record.get('state','') != 'draft':
                raise osv.except_osv('Validation Error !', 'You can only delete records which are at state Requester !')
        try:     
            res = super(vhr_exit_checklist_request, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res
    
    
    def execute_workflow(self, cr, uid, ids, context=None):
        
        if isinstance(ids, (int, long)):
            ids = [ids]
        if context is None: context = {}
        context['call_from_execute'] = True
        for record_id in ids:
            try:
                action_result = False
                action_next_result = False
                record = self.read(cr, uid, record_id, ['state'])
                old_state = record.get('state', False)
                
                if old_state:
                    if context.get('action', False) in ['submit','approve']:
                        action_next_result = self.action_next(cr, uid, [record_id], context) 
                        
                    elif context.get('action', False) == 'return':
                        action_result = self.action_return(cr, uid, [record_id], context)
                        
                    elif context.get('action', False) == 'reject':
                        action_result = self.action_reject(cr, uid, [record_id], context)
                    
                    if action_next_result or action_result:
                        record = self.read(cr, uid, record_id, ['state'])
                        new_state = record.get('state', False)
                        if old_state != new_state:
                            self.send_mail(cr, uid, record_id, old_state, new_state, context)
                            
                    if context.get('action') and action_result:
                        list_states = {item[0]: item[1] for item in STATES}
                        
                        record = self.read(cr, uid, record_id, ['state'])
                        new_state = record.get('state', False)
                        
                        self.write_log_state_change(cr, uid, record_id, list_states[old_state], list_states[new_state], context)
                        
            except Exception as e:
                log.exception(e)
                try:
                    error_message = e.message
                    if not error_message:
                        error_message = e.value
                except:
                    error_message = ""
                raise osv.except_osv('Validation Error !', 'Have error during execute record:\n %s!' % error_message)
                
        return True
    
    def write_log_state_change(self, cr, uid, record_id, old_state, new_state, context=None):
        if not context:
            context = {}
        state_vals = {}
        state_vals['old_state'] = old_state
        state_vals['new_state'] = new_state
#         state_vals['create_uid'] = uid
        state_vals['res_id'] = record_id
        state_vals['model'] = self._name
        if 'ACTION_COMMENT' in context:
            state_vals['comment'] = context['ACTION_COMMENT']
        self.pool.get('vhr.state.change').create(cr, uid, state_vals)
        return True
    
    def send_mail(self, cr, uid, record_id, state, new_state, context=None):
        if not context:
            context = {}
        context["search_all_employee"] = True
        if record_id and state and new_state:
            action_user = ''
            if context.get('action_user', False):
                action_user = context['action_user']
            else:
                user = self.pool.get('res.users').read(cr, uid, uid, ['login'])
                if user:
                    action_user = user.get('login','')
            
            log.info("Send mail in Exit Checklist from old state %s to new state %s"% (state, new_state))
            if state in mail_process.keys():
                data = mail_process[state]
                is_have_process = False
                for mail_data in data:
                    if new_state == mail_data[0]:
                        is_have_process = True
                        mail_detail = mail_data[1]
                        vals = {'action_user':action_user, 'exit_id': record_id}
                        list_group_mail_to = mail_detail['to']
                                
                        list_mail_to, list_mail_cc_from_group_mail_to = self.get_email_to_send(cr, uid, record_id, list_group_mail_to, context)
                        mail_to = ';'.join(list_mail_to)
                        vals['email_to'] = mail_to
                        
                        if 'cc' in mail_detail:
                            list_group_mail_cc = mail_detail['cc']
                            
                            list_mail_cc, list_mail_cc_from_group_mail_cc = self.get_email_to_send(cr, uid, record_id, list_group_mail_cc, context)
                            list_mail_cc += list_mail_cc_from_group_mail_cc + list_mail_cc_from_group_mail_to
                            list_mail_cc = list(set(list_mail_cc))
                            mail_cc = ';'.join(list_mail_cc)
                            vals['email_cc'] = mail_cc
                        
                        link_email = self.get_url(cr, uid, record_id, context)
                        vals['link_email'] = link_email
                        context = {'action_from_email': mail_detail.get('action_from_email',''),'not_split_email':True }
                        self.pool.get('vhr.sm.email').send_email(cr, uid, mail_detail['mail_template'], vals, context)
                
                if not is_have_process:
                    log.info("Exit Checklist don't have mail process from old state %s to new state %s "%(state, new_state))
            
        return True
    
    def get_email_to_send(self, cr, uid, record_id, list_mail, context=None):
        """
        Returl list email from list
        """
        res = []
        res_cc = []
        if list_mail and record_id:
            for item in list_mail:
                if item == 'requester':
                    mail = self.get_requester_mail(cr, uid, record_id, context)
                    if mail:
                        res.append(mail)
                        
                elif item == 'personal_email':
                    mail = self.get_personal_email(cr, uid, record_id, context)
                    if mail:
                        res.append(mail)
                elif item == 'hrbp':
                    name, id, mail = self.get_hrbp_name_and_id(cr, uid, record_id, context)
                    if mail:
                        res.extend(mail)
                        
                elif item == 'assist_hrbp':
                    name, id, mail = self.get_assist_hrbp_name_and_id(cr, uid, record_id, context)
                    if mail:
                        res.extend(mail)
                
                elif item == 'hr_executor':
                    name ,id, mail = self.get_hr_executor_name_and_id(cr, uid, context)
                    if mail:
                        res.extend(mail)
                
                elif item == 'department':
                    mail = self.get_available_approver_department_mail(cr, uid, record_id, context)
                    if mail:
                        mail = list(set(mail))
                        res.extend(mail)
                
                elif item == 'return_department':
                    mail = self.get_return_approver_mail(cr, uid, record_id, context)
                    if mail:
                        mail = list(set(mail))
                        res.extend(mail)
                
                else:
                    mail_group_pool = self.pool.get('vhr.email.group')
                    mail_group_ids = mail_group_pool.search(cr, uid, [('code','=',item)])
                    if mail_group_ids:
                        mail_group = mail_group_pool.read(cr, uid, mail_group_ids[0], ['to_email','cc_email'])
                        to_email = mail_group.get('to_email','') or ''
                        cc_email = mail_group.get('cc_email','') or ''
                        mail_to  = to_email.split(';')
                        mail_cc  = cc_email.split(';')
                        res.extend(mail_to)
                        res_cc.extend(mail_cc)
                    
                    else:
                        log.info("Can't find mail for " + item)
        return res, res_cc
    
    def get_url(self, cr, uid, res_id, context=None):
        if isinstance(res_id, list):
            res_id = res_id[0]
        model_data = self.pool.get('ir.model.data')
        action_id = model_data.xmlid_lookup(cr, uid, 'vhr_human_resource.act_vhr_exit_checklist_request')[2]
        
        url = ''
        config_parameter = self.pool.get('ir.config_parameter')
        base_url = config_parameter.get_param(cr, uid, 'web.base.url') or ''
        if base_url:
            url = base_url
        url += '/web#id=%s&view_type=form&model=vhr.exit.checklist.request&action=%s' % (res_id, action_id)
        return url
    
    #Action for workflow
    def action_next(self, cr, uid, ids, context=None):
        log.info('Change status to next state')
        if not context:
            context = {}
        context['search_all_employee'] = True
        if ids:
            
            detail_pool = self.pool.get('vhr.exit.checklist.detail')
            record_id = ids[0]
            mcontext = context
            if self.is_person_do_action(cr, uid, [record_id], mcontext):
                vals = {}
                fields = ['state'] + APPROVE_FIELDS + DEPARTMENT_FIELDS
                record = self.read(cr, uid, record_id, fields)
                state = record.get('state', False)
                
                if state in ['finish','cancel']:
                    return True
                
                today = time.strftime(DEFAULT_SERVER_DATE_FORMAT)
#                 update_approve_date_fields = ['responsibilities_hand_over_ids','administrative_office_ids',
#                                               'administrative_office_other_ids','it_office_ids']
                
                not_check_money_included = ['responsibilities_hand_over_ids','it_office_other_ids']
                
                continue_to_next_state = True
                if state == 'department':
                    vals['state'] = 'department'
                    user = self.pool.get('res.users').read(cr, uid, uid, ['login'])
                    user_login = user.get('login','')
                    res = self.get_login_and_id_department_approver(cr, uid, ids, context)
                    res1 = res[ids[0]]
                    for field in DEPARTMENT_FIELDS:
                        approver_field = TEAM_FIELDS[field][1]
                        is_approved_field = TEAM_FIELDS[field][0]
                        if record.get(is_approved_field, False) or not record.get(field, False):
                            continue
                        if user_login in res1[approver_field] or \
                          (field == 'responsibilities_hand_over_ids' and user_login in res1.get('approver_user_responsibilities_hand_over_delegate_ids',[])):
                            vals[is_approved_field] = True
                            
                            #Update approve date
#                             if field in update_approve_date_fields:
                            detail_ids = detail_pool.search(cr, uid, [('exit_checklist_id','=',record_id),
                                                                      ('type_exit','=',field[:-4]),
                                                                      ('withdraw_date','=',False)])
                            if detail_ids:
                                detail_pool.write(cr, uid, detail_ids, {'withdraw_date': today})
                            
                            #Check if not update money included and not update comment
                            if field not in not_check_money_included:
                                detail_ids = detail_pool.search(cr, uid, [('exit_checklist_id','=',record_id),
                                                                          ('type_exit','=',field[:-4]),
                                                                          ('money_included_in_the_settlement','=',False)])
                                if detail_ids:
                                    raise osv.except_osv('Sự cố !', 'Bạn phải nhập thông tin số tiền đưa vào quyết toán (nếu không có thì nhập số 0)')
                            
                            detail_ids = detail_pool.search(cr, uid, [('exit_checklist_id','=',record_id),
                                                                      ('type_exit','=',field[:-4]),
                                                                      ('note','!=',False)])
                            if not detail_ids:
                                raise osv.except_osv('Sự cố !', 'Bạn phải nhập thông tin ghi chú tại ít nhất 1 dòng của mỗi mục ')
                            
                        else:
                            continue_to_next_state = False
                            
                if continue_to_next_state:
                    list_state = [item[0] for item in STATES]
                    index_new_state = list_state.index(state) + 1
                    vals['state'] = list_state[index_new_state]
                
                vals['approve_date'] = time.strftime(DEFAULT_SERVER_DATE_FORMAT)
                res = self.write(cr, uid, [record_id], vals, mcontext)
                
                if res:
                    #Send mail if IT and IT other is approved EC
                    if set(['is_approve_it_office','is_approve_it_office_other']).intersection(vals.keys()):
                        record = self.read(cr, uid, record_id, ['is_approve_it_office','is_approve_it_office_other'])
                        if record.get('is_approve_it_office', False) and record.get('is_approve_it_office_other', False):
                            self.send_mail(cr, uid, record_id, 'department', 'IT_approved', context)
                        
                    list_dict_states = {item[0]: item[1] for item in STATES}
                    self.write_log_state_change(cr, uid, record_id, list_dict_states[state], list_dict_states[vals['state']], mcontext)
                    
#                     if vals['state'] not in  ['finish']:
#                         mcontext['state'] = vals['state']
#                         
#                         self.action_next(cr, uid, ids, context=mcontext)
                        

        
        return True
    
    def action_reject(self, cr, uid, ids, context=None):
        log.info('Change status to cancel state')
        if ids:
            record_id = ids[0]
            if self.is_person_do_action_reject(cr, uid, [record_id], context):
                record = self.read(cr, uid, record_id, ['state'])
                state = record.get('state', False)
                
                super(vhr_exit_checklist_request, self).write(cr, uid, [record_id], {'state': 'cancel'}, context)
                
                return True
        
        return False
    
    def action_return(self, cr, uid, ids, context=None):
        log.info('Change status to previous state')
        if not context:
            context = {}
        if ids:
            record_id = ids[0]
            if self.is_person_do_action(cr, uid, [record_id], context):
                vals = {}
                vals['state'] = 'department'
                if context.get('back_department_ids', False):
                    back_department_ids = context['back_department_ids'][0][2]
                    if back_department_ids:
                        back_departments = self.pool.get('vhr.dimension').read(cr, uid, back_department_ids, ['code'])
                        for back_department in back_departments:
                            field_is_approve = back_department.get('code','')
                            vals[field_is_approve] = False
                    vals['back_department_ids'] = [[6,False,[]]]
                self.write(cr, uid, [record_id], vals, context)
                return True
               
        
        return False
    
    
    def open_window(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        
        if context.get('action', False) == 'return':
            context['show_back_department'] = True
        view_open = 'view_vhr_exit_checklist_request_submit_form'
        if context.get('view_open',False):
            view_open = context['view_open']
            
        action = {
            'name': 'Notes',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.pool.get('ir.model.data').get_object_reference(cr, uid, 'vhr_human_resource', view_open)[1],
            'res_model': 'vhr.exit.checklist.request',
            'context': context,
            'type': 'ir.actions.act_window',
            #'nodestroy': True,
            'target': 'new',
            #'auto_refresh': 1,
            'res_id': ids[0],
        }
        return action
    
    def action_print(self, cr, uid, ids, context=None):
#         wizard_pool = self.pool.get('ir.actions.report.promptwizard')
        
        
        record_id = ids and ids[0] or False
        record = self.browse(cr, uid, record_id, fields_process=['employee_id'])
        emp_login = record.employee_id and record.employee_id.login or ''
        
        data = {'variables': {'checklist_id': record_id}, 
                'output_type': 'pdf', 
                'model': 'ir.ui.menu', 
                'ids': []}
        
        return {
                'type': 'ir.actions.report.xml',
                'report_name': context.get('service_name', ''),
                'datas': data,
                'name': 'Exit Checklist_' + emp_login
                }
    
    def fields_view_get(self, cr, uid, view_id = None, view_type = 'form', context = None, toolbar = False, submenu = False):
        res = super(vhr_exit_checklist_request, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar = toolbar, submenu = submenu)
        if context is None:
            context = {}
        if view_type == 'form':
            res = self.add_attrs_for_field(cr, uid, res, context)
        return res
    
    def add_attrs_for_field(self, cr, uid, res, context=None):
        doc = etree.XML(res['arch'])
        if res['type'] == 'form':
            #When view view_vhr_working_record_submit_form
            #To add field text action_comment 
            if context.get('action',False) and context.get('active_id', False):
                node = doc.xpath("//form/separator")
                if node:
                    node = node[0].getparent()
                    if context.get('required_comment', False):
                        node_notes = etree.Element('field', name="action_comment", colspan="4", modifiers=json.dumps({'required' : True}))
                    else:
                        node_notes = etree.Element('field', name="action_comment", colspan="4")
                    node.append(node_notes)
                    res['arch'] = etree.tostring(doc)
                    res['fields'].update({'action_comment': {'selectable': True, 'string': 'Action Comment', 'type': 'text', 'views': {}}})
                
        res['arch'] = etree.tostring(doc)
        return res
    
    def cron_regenerate_exit_approver(self, cr, uid, employee_code, context=None):
        if not context:
            context = {}
        log.info('start  cron regenerate_exit_approver')
        domain = [('state','!=','cancel')]
        if employee_code:
            domain.append(('employee_id.code','in', employee_code))
        
        if context.get('division_id', False):
            domain.append(('division_id','in', context['division_id']))
        elif context.get('department_id', False):
            domain.append(('department_id','in', context['department_id']))
        
        if context.get('restrict_date', False):
            domain.append(('request_date','>=','2016-01-01'))
                
        request_ids = self.search(cr, uid, domain)
        if request_ids:
            log.info("Number of regen request: %s"% len(request_ids))
            super(vhr_exit_checklist_request, self).write(cr, uid, request_ids, {'is_new': False})
        
        log.info('end cron regenerate_exit_approver')
        return True
    
    def cron_generate_exit_approver(self, cr, uid, *args):
        log.info('start  cron generate_exit_approver')
        domain = [('state','!=','cancel')]
        if args:
            args = list(args)
            domain.append(('employee_id.code','in', args))
        else:
            domain.append(('approver_user_it_office','=',False))
        
        request_ids = self.search(cr, uid, domain, limit=300)
        if request_ids:
            log.info("Number of gen request: %s"% len(request_ids))
            super(vhr_exit_checklist_request, self).write(cr, uid, request_ids, {'is_new': False})
        
        log.info('end cron generate_exit_approver')
        return True
    
    def get_delegator(self, cr, uid, department_id, employee_id, context=None):
        '''
        Check if have record delegate detail with employee 
        Return list delegate_ids of record if have
        '''
        if not context:
            context = {}
        if employee_id and department_id:
                
            detail_obj = self.pool.get('vhr.delegate.detail')
            
            module_ids = self.pool.get("ir.module.module").search(cr, uid, [('name','=','vhr_human_resource')])
            
            
            model_ids = self.pool.get('ir.model').search(cr, uid, [('model','=',self._name)])
            delegate_model_id = self.pool.get('vhr.delegate.model').search(cr, uid, [('model_id','in',model_ids),
                                                                                     ('active','=',True)])
            
            if delegate_model_id and module_ids:
                domain = [('employee_id','=',employee_id),
                         ('module_id','in',module_ids),
                         ('model_ids','=',delegate_model_id),
                         ('department_ids','=',department_id),
                         ('active','=',True)]
                
                detail_ids = detail_obj.search(cr, uid, domain)
                
                if detail_ids:
                    details = detail_obj.read(cr, uid, detail_ids, ['delegate_id'])
                    delegate_ids = [detail.get('delegate_id', False) and detail['delegate_id'][0] for detail in details]
                    
                    return delegate_ids
        
        return []
    

vhr_exit_checklist_request()
