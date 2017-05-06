# -*-coding:utf-8-*-
import logging
import datetime

from openerp import SUPERUSER_ID
from openerp.osv import osv, fields
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT

log = logging.getLogger(__name__)


class vhr_wizard_print_low_salary_confirmation(osv.osv):
    _name = 'vhr.wizard.print.low.salary.confirmation'
    _description = 'Print Low Salary Confirmation'
    
    
    _columns = {
                'employee_id': fields.many2one('hr.employee',  'Employee'),
                'money_number': fields.char('Số tiền bằng số'),
                'money_char': fields.char('Số tiền bằng chữ'),
                'year': fields.char('Year'),
    }
    
    
    _defaults = {
            'money_number': '108,000,000',
            'money_char': u'một trăm lẻ tám triệu',
        }
    
    def is_able_to_edit_emp(self, cr, uid, context=None):
        groups = self.pool.get('res.users').get_groups(cr, uid)
        special_groups = ['vhr_cb', 'vhr_dept_admin','vhr_assistant_to_hrbp','vhr_hrbp']
        if set(special_groups).intersection(set(groups)):
            return True
        return False
        
        
    def action_print(self, cr, uid, ids, context=None):
        if not isinstance(ids, list):
            ids = [ids]
            
        res = {}
        list_data = []
        
        record = self.read(cr, uid, ids[0], ['employee_id'], context={'active_test': False})
        employee_id = record.get('employee_id',False) and record['employee_id'][0]
        
        report_name = 'template_human_resource_low_salary_commitment'
        employee = self.pool.get('hr.employee').read(cr, uid, employee_id, ['code'])
        emp_code = employee.get('code','')
        
        file_name = 'Cam_ket_thu_nhap_thap_ ' + ' ' + emp_code
        
            
        res = self.get_data_of_employee(cr, uid, ids, employee_id, report_name, file_name,context)
        
        return res
    
    def get_data_of_employee(self, cr, uid, ids, employee_id, report_name='', file_name='report_human_resource_low_salary_commitment', context=None):
        company_obj = self.pool.get('res.company')
        office_obj = self.pool.get('vhr.office')
        
        fields = ['name','code','name_related','department_id','division_id','team_id','company_id','street','district_id','city_id',
                  'personal_document','office_id','birthday']
        data = self.pool.get('hr.employee').read(cr, uid, employee_id, fields, context={'get_pure_department_name': True})
        if ids:
            confirm = self.read(cr, uid, ids[0], [])
            data.update(confirm)
        
        today = datetime.datetime.today()
        data['today_str'] = u'ngày ' + str(today.day) + u' tháng ' + str(today.month) + u' năm ' + str(today.year)
        if not data.get('year', False):
            data['year'] = str(today.year)
            
        today = today.strftime(DEFAULT_SERVER_DATE_FORMAT)
        
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
            
            
        if data.get('street', False):
            data['street'] = '%s%s%s' % (
                data['street'],
                data.get('district_id', False) and (', ' + data['district_id'][1]) or '',
                data.get('city_id', False) and (', ' + data['city_id'][1]) or u'',
            )
        data.update({'cmnd_number': '', 'cmnd_issue_date': '', 'cmnd_city': '', 'lb_number': '',
                         'passport_number':'','passport_issue_date':'','passport_country':''})
        
        data['is_pit'] = False
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
                
                elif item.document_type_id and item.document_type_id.code == 'TAXID':
                    data['is_pit'] = True
                    data['pit_number'] = item.number or ''
                    data['pit_issue_date'] = item.issue_date or ''
                    data['pit_country'] = item.country_id and item.country_id.name or ''
        
        data['com_office_city_id'] = ''
        com_id = data['company_id'] and data['company_id'][0] or []
        if com_id:
            com_data = company_obj.read(cr, uid, com_id, ['office_id'], context=context)
            
            office_id = com_data.get('office_id', False) and com_data['office_id'][0] or False
            if office_id:
                office = office_obj.read(cr, uid, office_id, ['city_id'])
                if office.get('city_id', False):
                    data['com_office_city_id'] = office.get('city_id', 1)
                    
        
        data['today'] = today      
        
        datas = {
            'ids': [employee_id],
            'model': 'vhr.wizard.print.low.salary.confirmation',
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


vhr_wizard_print_low_salary_confirmation()