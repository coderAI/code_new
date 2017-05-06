# -*-coding:utf-8-*-
import logging
import thread
import sys
import re
import simplejson as json

from openerp import SUPERUSER_ID
from openerp.osv import osv, fields
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from lxml import etree
from openerp import tools
from datetime import datetime
from openerp.addons.vhr_human_resource.model.vhr_working_record import dict_fields
from openerp.addons.vhr_human_resource.model.vhr_working_record import dict_salary_fields

log = logging.getLogger(__name__)


class vhr_wizard_privacy_statement(osv.osv):
    _name = 'vhr.wizard.privacy.statement'
    _description = 'Print Privacy Statement'
    
    
    _columns = {
                'name': fields.char('Name', size=64),
                'company_id': fields.many2one('res.company', 'Company', ondelete='restrict'),
                'change_form_ids':fields.many2many('vhr.change.form','privacy_statement_change_form_rel','privacy_id','change_form_id','Change Form'),
                'division_id': fields.many2one('hr.department', 'Business Unit', domain=[('organization_class_id.level','=', '1')], ondelete='restrict'),
                'department_group_id': fields.many2one('hr.department', 'Department Group', domain=[('organization_class_id.level','=', '2')], ondelete='restrict'), 
                'department_id': fields.many2one('hr.department', 'Department', domain=[('organization_class_id.level','=', '3')], ondelete='restrict'),
                'team_id': fields.many2one('hr.department', 'Team', domain=[('organization_class_id.level','>=', '4')], ondelete='restrict'),
                'employee_id': fields.many2one('hr.employee', 'Employee', ondelete='restrict'),
#                 'date_from': fields.date('Date From'),
#                 'date_to': fields.date('Date To'),
                'report_id': fields.many2one('vhr.dimension', 'Report' ,domain=[('dimension_type_id.code','=', 'PRIVACY_STATEMENT_REPORT')], ondelete='restrict'),
                
                'working_ids': fields.many2many('vhr.working.record', 'privacy_statement_wr_rel','privacy_id','working_id', 'Mapping WR'),
                'effect_from': fields.date('Effective Date'),
                'effective_at_date': fields.date('Effective At Date'),
    }
    
    
    def read(self, cr, user, ids, fields=None, context=None, load='_classic_read'):
        if not context:
            context = {}
        
        if 'active_test' not in context:
            context['active_test'] = False
        
        res =  super(vhr_wizard_privacy_statement, self).read(cr, user, ids, fields, context, load)
        
        return res
    
    
    def update_list_working_record(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        
        if not isinstance(ids, list):
            ids = [ids]
        
        wr_pool = self.pool.get('vhr.working.record')
        
        delete_ids = self.search(cr, uid, [('id','not in', ids)])
        if delete_ids:
            self.unlink(cr, uid, delete_ids)
        
        for record_id in ids:
            record = self.browse(cr, uid, record_id)
            company_id = record.company_id and record.company_id.id or False
            division_id = record.division_id and record.division_id.id or False
            department_group_id = record.department_group_id and record.department_group_id.id or False
            department_id = record.department_id and record.department_id.id or False
            team_id = record.team_id and record.team_id.id or False
            employee_id = record.employee_id and record.employee_id.id or False
            effect_from = record.effect_from or False
            effective_at_date = record.effective_at_date or False
            
            report_id = record.report_id and record.report_id.id or False
            change_form_ids = record.change_form_ids
            change_form_ids = [form.id for form in change_form_ids]
            
            dict = {'company_id': company_id,
                    'division_id_new': division_id,
                    'department_group_id_new': department_group_id,
                    'department_id_new': department_id,
                    'team_id_new': team_id,
                    'employee_id': employee_id,
                    'effect_from': effect_from}
            
            domain = []
            for item in dict:
                if dict[item]:
                    domain.append((item,'=',dict[item]))
                    
            
            for change_form_id in change_form_ids:
                domain.append(('change_form_ids','=',change_form_id))
            
            if effective_at_date and not effect_from:
                domain.extend([('effect_from','<=',effective_at_date),'|',('effect_to','>=',effective_at_date),('effect_to','=',False)])
            
            other_form_ids = self.pool.get('vhr.change.form').search(cr, uid, [('id','not in',change_form_ids)])
            domain.append(('change_form_ids','not in',other_form_ids))
            
            if domain:
                domain.append(('state','in',[False,'finish']))
                if not effect_from:
                    domain.append(('active','=',True))
                else:
                    domain.extend(['|',('active','=',True),('active','=',False)])
                
                print '\n domain search==',domain
                working_ids = wr_pool.search(cr, uid, domain, context={'active_test': False})
                print '\n working record found=',working_ids
                self.write(cr, uid, record_id, {'working_ids': [[6, False, working_ids]]})
    
    def print_multi_privacy_statement(self, cr, uid, ids, context=None):
        if not isinstance(ids, list):
            ids = [ids]
            
        res = {}
        list_data = []
        
        record = self.read(cr, uid, ids[0], ['working_ids','report_id'])
        working_ids = record.get('working_ids',[])
        report_id = record.get('report_id', False) and record['report_id'][0]
        report = self.pool.get('vhr.dimension').read(cr, uid, report_id, ['name','code'])
        report_name = report.get('code', '')
        file_name = "Privacy Statement " +    report.get('name', '')
        
        for record_id in working_ids:
            
            res = self.get_data_of_each_employee(cr, uid, record_id, report_name, file_name,context)
            datas = res.get('datas', False)
            if datas:
                data = datas.get('form')
                if isinstance(data, dict):
                    list_data.append({'report.'+ report_name : data})
                else:
                    list_data.extend(data)
        
        res['datas'] = {
                     'ids': ids,
                     'model': 'vhr.wizard.privacy.statement',
                     'form': list_data,
                     'merge_multi_report': True
                     
                     }
        
        return res
    
    def get_data_of_each_employee(self, cr, uid, working_id, report_name='', file_name='privacy_statement_report', context=None):
        data = self.pool.get('vhr.working.record').read(cr, uid, working_id, 
                                                           ['employee_id','company_id','change_form_ids','job_title_id_new','effect_from','contract_id',
                                                            'job_level_id_new','job_level_position_id_new','job_level_person_id_new',
                                                            'department_id_new','office_id_new','gross_salary_old','collaborator_salary_new',
                                                            'gross_salary_new','salary_percentage_new','basic_salary_new','v_bonus_salary_new',
                                                            'collaborator_salary_old'])
        data.update( {'employee_name': '',
                      'emp_first_name': '',
                     'employee_code': '',
                     'company_name': '',
                     'job_title': '',
                     'job_level': '',
                     'job_level_position_new': '',
                     'job_level_person_new':'',
                     'emp_gender': '',
                     'salary_percen_differ': 0})
        
        
        if data.get('collaborator_salary_new', False):
            data['gross_salary_new'] = data['collaborator_salary_new']
            data['gross_salary_old'] = data['collaborator_salary_old']
            
        data['salary_percen_differ']= (data.get('gross_salary_new',0) -data.get('gross_salary_old',0))/ float(data.get('gross_salary_old',0)) *100
        data['salary_percen_differ'] = abs(round(data['salary_percen_differ']))
        
        wr = data
        employee_id = wr.get('employee_id', False) and wr['employee_id'][0]
        if employee_id:
            employee = self.pool.get('hr.employee').read(cr, uid, employee_id, ['name','code','first_name','gender'])
            data['employee_name'] = employee.get('name','')
            data['employee_code'] = employee.get('code','')
            data['emp_first_name'] = employee.get('first_name','')
            
            if employee.get('gender',False):
                data['emp_gender_en'] = employee['gender'] == 'male' and u'Mr' or \
                                     (employee['gender'] == 'female' and u'Ms' or u'Mr./Ms')
                                     
                data['emp_gender'] = employee['gender'] == 'male' and u'Anh' or \
                                     (employee['gender'] == 'female' and u'Chị' or u'Anh/Chị')
        
        
        data.update({'contract_sign_date': '',
                     'contract_signer': '',
                     'contract_title_signer': ''})
        contract_id = data.get('contract_id', False) and data['contract_id'][0]
        if contract_id:
            contract = self.pool.get('hr.contract').read(cr, uid, contract_id, ['date_start','info_signer','title_signer'])
            data['contract_sign_date'] = contract.get('date_start',False)
            data['contract_signer'] = contract.get('info_signer',False)
            data['contract_title_signer'] = contract.get('title_signer',False)
        
        company_id = wr.get('company_id', False) and wr['company_id'][0]
        if company_id:
            company = self.pool.get('res.company').read(cr, uid, company_id, ['name'])
            data['company_name'] = employee.get('name','')
        
        
        if data.get('effect_from', False):
            data['effect_from_str'] = datetime.strptime(data['effect_from'], DEFAULT_SERVER_DATE_FORMAT).strftime('%d/%m/%Y')
        
        data.update({'show_all_salary': False,
                     'show_partial_salary': False})
        if data.get('v_bonus_salary_new', False):
            data['show_all_salary'] = True
        elif data.get('basic_salary_new', False):
            data['show_partial_salary'] = True
        
        
        data['percent_state'] = u'tăng'
        if data.get('gross_salary_new', 0) < data.get('gross_salary_old', 0):
            data['percent_state'] = u'giảm'
            
        datas = {
            'ids': [working_id],
            'model': 'vhr.wizard.privacy.statement',
            'form': data,
            'parse_condition': True
#             'multi': True,
        }
        
        res = {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': datas,
            'name': file_name
        }
        return res


vhr_wizard_privacy_statement()