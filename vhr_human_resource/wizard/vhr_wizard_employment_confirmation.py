# -*-coding:utf-8-*-
import logging
import datetime

from openerp import SUPERUSER_ID
from openerp.osv import osv, fields
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT

log = logging.getLogger(__name__)

REPORT_SELECTION = [('template_human_resource_employment_confirmation','Employment Certificate'),
                    ('template_human_resource_certificate_service','Service Certificate')]

class vhr_wizard_employeement_confirmation(osv.osv):
    _name = 'vhr.wizard.employment.confirmation'
    _description = 'Print Employment Confirmation'
    
    
    _columns = {
                
                'employee_ids': fields.many2many('hr.employee', 'emp_confirm_rel','wizard_id','employee_id', 'Employee'),
                'report_name': fields.selection(REPORT_SELECTION, 'Type'),
    }
    
    _defaults={
               'report_name': 'template_human_resource_employment_confirmation'
               }
    
    
    def action_print(self, cr, uid, ids, context=None):
        if not isinstance(ids, list):
            ids = [ids]
            
        res = {}
        list_data = []
        
        record = self.read(cr, uid, ids[0], ['employee_ids','report_name'], context={'active_test': False})
        employee_ids = record.get('employee_ids',[])
        report_name = record.get('report_name', False)
        
        dict_report = {name:type for name,type in REPORT_SELECTION}
        
        employees = self.pool.get('hr.employee').read(cr, uid, employee_ids, ['code'])
        emp_code = [emp.get('code','') for emp in employees]
        emp_code = ','.join(emp_code)
        
        file_name = dict_report[report_name] + ' ' + emp_code
        
        for employee_id in employee_ids:
            
            res = self.get_data_of_each_employee(cr, uid, employee_id, report_name, file_name,context)
            datas = res.get('datas', False)
            if datas:
                data = datas.get('form')
                if isinstance(data, dict):
                    list_data.append({'report.'+ report_name : data})
                else:
                    list_data.extend(data)
        
        res['datas'] = {
                     'ids': ids,
                     'model': 'vhr.wizard.employment.confirmation',
                     'form': list_data,
                     'merge_multi_report': True,
                     'parse_condition': True
                     
                     }
        
        return res
    
    def get_data_of_each_employee(self, cr, uid, employee_id, report_name='', file_name='template_human_resource_employment_confirmation', context=None):
        data = self.pool.get('hr.employee').read(cr, uid, employee_id, [], context={'get_pure_department_name': True})
        
        today = datetime.datetime.today().strftime(DEFAULT_SERVER_DATE_FORMAT)
        
        if 'gender' in data:
            data['gender_en'] = data['gender'] == 'male' and u'Mr' or \
                                 (data['gender'] == 'female' and u'Ms' or u'Mr./Ms')
                                 
            data['gender'] = data['gender'] == 'male' and u'Ông' or \
                                 (data['gender'] == 'female' and u'Bà' or u'Ông/Bà')
        
        data.update({'company_name_en': '',
                     'salary': '',
                     'contract_type':'',
                     'contract_type_en': '',
                     'contract_date_start': '',
                     'contract_date_end': '',
                     'company_name_en': '',
                     'department_name_en': ''
                    })
        
        if data.get('department_id', False):
            department_id = data['department_id'][0]
            department = self.pool.get('hr.department').read(cr, uid, department_id, ['name_en'])
            data['department_name_en'] = department.get('name_en','')
        
        if data.get('division_id', False):
            division_id = data['division_id'][0]
            division = self.pool.get('hr.department').read(cr, uid, division_id, ['name_en'])
            data['division_name_en'] = division.get('name_en','')
        
        if data.get('company_id', False):
            company_id = data['company_id'][0]
            company = self.pool.get('res.company').read(cr, uid, company_id, ['name','name_en'])
            data['company_name_en'] = company.get('name_en','')
            
            
            #Get salary
            salary_obj = self.pool.get('vhr.pr.salary')
            
            salary_ids = salary_obj.search(cr, uid, [('employee_id','=',employee_id),
                                                     ('company_id','=',company_id),
                                                     ('effect_from','<=',today),
                                                     '|',('effect_to','=',False),
                                                         ('effect_to','>=',today)])
            if salary_ids:
                salary = salary_obj.read(cr, uid, salary_ids[0], ['gross_salary','collaborator_salary'])
                gross = salary.get('gross_salary',0)
                if not gross:
                    gross = salary.get('collaborator_salary',0)
                
                data['salary'] = gross
            
            #Get contract type
            contract_obj = self.pool.get('hr.contract')
            contract_ids = contract_obj.search(cr, uid, [('employee_id','=',employee_id),
                                                         ('company_id','=',company_id),
                                                         ('state','=','signed'),
                                                         ('date_start','<=',today),
                                                         '|','|','&',('date_end','>=',today),
                                                                     ('liquidation_date','=',False),
                                                                     
                                                                  '&',('date_end','=',False),
                                                                     ('liquidation_date','=',False),
                                                                     
                                                                  ('liquidation_date','>=',today),
                                                                  ])
            if not contract_ids:
                contract_ids = contract_obj.search(cr, uid, [('employee_id','=',employee_id),
                                                             ('company_id','=',company_id),
                                                             ('state','=','signed'),
                                                             ('date_start_real','<=',today)], order='date_start_real desc')
            
            if not contract_ids:
                contract_ids = contract_obj.search(cr, uid, [('employee_id','=',employee_id),
                                                             ('state','=','signed'),
                                                             ('date_start_real','<=',today)], order='date_start_real desc')
            
            if contract_ids:
                contract = contract_obj.read(cr, uid, contract_ids[0], ['type_id','date_start_real','date_end','liquidation_date'])
                
                contract_date_end = contract.get('liquidation_date', '')
                if not contract_date_end:
                    contract_date_end = contract.get('date_end','')
                
                data.update({'contract_type':contract.get('type_id',''),
                             'contract_date_start': contract.get('date_start_real',''),
                             'contract_date_end': contract_date_end
                    })
                
                if contract.get('type_id', False):
                    type_id = contract['type_id'][0]
                    type = self.pool.get('hr.contract.type').read(cr, uid, type_id, ['name_en'])
                    data['contract_type_en'] = type.get('name_en','')
                
        
        data.update({'cmnd_number': '', 'cmnd_issue_date': '', 'cmnd_city': '', 'lb_number': '',
                         'passport_number':'','passport_issue_date':'','passport_country':''})
        if data.get('personal_document', False):
            document_ids = data['personal_document']
            for item in self.pool.get('vhr.personal.document').browse(cr, uid, document_ids):
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
        
        
        data['today'] = today      
        
        datas = {
            'ids': [employee_id],
            'model': 'vhr.wizard.employment.confirmation',
            'form': data,
            'parse_condition': True
#             'multi': True,
        }
        
        res = {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': datas,
            'name': file_name,
            'parse_condition': True
        }
        return res


vhr_wizard_employeement_confirmation()