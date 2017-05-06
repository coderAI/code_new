# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from openerp.addons.vhr_common.model.vhr_common import vhr_common

log = logging.getLogger(__name__)


class vhr_termination_agreement_contract(osv.osv, vhr_common):
    _name = 'vhr.termination.agreement.contract'
    _description = 'VHR Termination Agreement Contract'
    
    def _get_is_created(self, cr, uid, ids, prop, unknow_none, context=None):
        res = {}
        for item in ids:
            res[item] = True
        return res
    
    _columns = {
        'name': fields.char('Name', size=128),
        'join_date': fields.date('Join Date'),
        'effect_date': fields.date('Effect Date'),
        'seniority': fields.float('Seniority'),
        'remain_leave': fields.float('Remain Annual Leave'),
        
        'is_created': fields.function(_get_is_created, type='boolean', string='Is Created'),
        'employee_id': fields.many2one('hr.employee', 'Employee'),
        'employee_code': fields.related('employee_id', 'code', type="char", string="Employee Code"),
        
        'old_contract_id': fields.many2one('hr.contract', 'Contract'),
        'old_company_id': fields.related('old_contract_id', 'company_id', readonly=True, type='many2one',
                                                 relation='res.company', string='Company'),
        'old_info_signer': fields.related('old_contract_id', 'info_signer', type="char", string="Signer"),
        'old_title_signer': fields.related('old_contract_id', 'title_signer', type="char", string="Signer's Title"), 
        'old_type_id': fields.related('old_contract_id', 'type_id', readonly=True, type='many2one',
                                                 relation='hr.contract.type', string='Contract Type'),
        
        'old_date_start': fields.related('old_contract_id', 'date_start', type="date", string="Date Start"),
        'old_date_end': fields.related('old_contract_id', 'date_end', type="date", string="Date End"),
        'old_liquidation_date':fields.related('old_contract_id', 'liquidation_date', type="date", string="Liquidation Date"),
                
        
        'new_contract_id': fields.many2one('hr.contract', 'Contract'),
        'new_company_id': fields.related('new_contract_id', 'company_id', readonly=True, type='many2one',
                                                 relation='res.company', string='Company'),
        'new_info_signer': fields.related('new_contract_id', 'info_signer', type="char", string="Signer"),
        'new_title_signer': fields.related('new_contract_id', 'title_signer', type="char", string="Signer's Title"), 
        'new_type_id': fields.related('new_contract_id', 'type_id', readonly=True, type='many2one',
                                                 relation='hr.contract.type', string='Contract Type'),
        
        'new_date_start': fields.related('new_contract_id', 'date_start', type="date", string="Date Start"),
        'new_date_end': fields.related('new_contract_id', 'date_end', type="date", string="Date End"),
        'new_liquidation_date':fields.related('new_contract_id', 'liquidation_date', type="date", string="Liquidation Date"),
        
                
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                         domain=[('object_id.model', '=', _name),
                                                 ('field_id.name', 'not in',
                                                  ['write_date', 'audit_log_ids'])]),
    }
    
    _unique_insensitive_constraints = [{'employee_id': "Employee - Effect Date is already exist!",
                                        'effect_date':"Employee - Effect Date is already exist!",
                                        }]
    
    _defaults = {
                 'is_created': False
                 }
    
    def onchange_employee_id(self, cr, uid, ids, employee_id, old_contract_id, new_contract_id, effect_date, context=None):
        res = {'old_contract_id': False,'new_contract_id': False, 'employee_code': '','join_date': False,'seniority': 0, 'remain_leave':0}
        
        if employee_id:
            employee = self.pool.get('hr.employee').read(cr, uid, employee_id, ['code','join_date'])
            res['employee_code'] = employee.get('code', '')
            join_date = employee.get('join_date')
            res['join_date'] = join_date
            
            contract_ids = self.pool.get('hr.contract').search(cr, uid, [('employee_id','=',employee_id)])
            if old_contract_id in contract_ids:
                del res['old_contract_id']
            
            if new_contract_id in contract_ids:
                del res['new_contract_id']
            
            if join_date and effect_date:
                res['seniority'] = self.get_gap_year(cr, uid, join_date, effect_date, context)
                res['remain_leave'] = self.get_remain_leave(cr, uid, employee_id, effect_date, context)
        
        return {'value': res}
    
    def onchange_effect_date(self, cr, uid, ids, employee_id, join_date, effect_date, context=None):
        res = {'seniority': 0}
        if join_date and effect_date:
            res['seniority'] = self.get_gap_year(cr, uid, join_date, effect_date, context)
            if employee_id:
                res['remain_leave'] = self.get_remain_leave(cr, uid, employee_id, effect_date, context)
        
        return {'value': res}
    
    def get_remain_leave(self, cr, uid, employee_id, effect_date, context=None):
        res = 0
        
        if effect_date and employee_id:
            leave_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'ts.leave.type.default.code').split(',')
            leave_ids = self.pool.get('hr.holidays.status').search(cr, uid, [('code', 'in', leave_code)])
            
            employee = self.pool.get('hr.employee').read(cr, uid, employee_id, ['company_id'])
            
            company_id = employee.get('company_id', False) and employee['company_id'][0]
            effect_date = datetime.strptime(effect_date, DEFAULT_SERVER_DATE_FORMAT)
            date_before_effect_date = (effect_date-relativedelta(days=1)).strftime(DEFAULT_SERVER_DATE_FORMAT)
            dict=self.pool.get('hr.holidays.status').get_days(cr, uid, leave_ids, employee_id, company_id, date_before_effect_date, {"check_on_date":date_before_effect_date})
            res = dict.get(leave_ids[0], {}).get('current_remain_leave',0)
        
        return res
        
    def get_gap_year(self, cr, uid, date1, date2, context=None):
        result = 0
        if date1 and date2:
            
            date1 = datetime.strptime(date1, DEFAULT_SERVER_DATE_FORMAT)
            date2 = datetime.strptime(date2, DEFAULT_SERVER_DATE_FORMAT)
            if date1 >=date2:
                return False
            
            date_last_month_of_date1 = (date(date1.year, date1.month, 1) +relativedelta(months=1)-relativedelta(days=1)).strftime(DEFAULT_SERVER_DATE_FORMAT)
            date_last_month_of_date1 = datetime.strptime(date_last_month_of_date1, DEFAULT_SERVER_DATE_FORMAT)
            date_last_month_of_date2 = (date(date2.year, date2.month, 1) +relativedelta(months=1)-relativedelta(days=1)).strftime(DEFAULT_SERVER_DATE_FORMAT)
            date_last_month_of_date2 = datetime.strptime(date_last_month_of_date2, DEFAULT_SERVER_DATE_FORMAT)
            
            total_month = 0
            total_year = 0
            if date2.year > date1.year:
                total_year = date2.year - date1.year -1
                total_month = date2.month -1 + 12 - date1.month
                
                total_month += (date_last_month_of_date1 - date1).days / float(date_last_month_of_date1.day)
                total_month += date2.day / float(date_last_month_of_date2.day)
            elif date2.month != date1.month:
                total_month += date2.month - date1.month - 1
                total_month += (date_last_month_of_date1 - date1).days / float(date_last_month_of_date1.day)
                total_month += date2.day / float(date_last_month_of_date2.day)
            else:
                #same year, same month
                total_month += (date2 - date1).days / float(date_last_month_of_date1.day)
                
                
            total_year = total_year + total_month/12.0
            
            result = float("{0:.02f}".format(total_year)) 
        
        return result
        
                                           
    def onchange_old_contract_id(self, cr, uid, ids, old_contract_id, context=None):
        res = {'old_info_signer': '','old_title_signer': '','old_type_id': False,'old_company_id': False,
               'old_date_start': False,'old_date_end': False, 'old_liquidation_date': False}
        
        if old_contract_id:
            contract = self.pool.get('hr.contract').read(cr, uid, old_contract_id, ['info_signer','title_signer','type_id','company_id',
                                                                                    'date_start','date_end','liquidation_date'])
            res['old_info_signer'] = contract.get('info_signer','')
            res['old_title_signer'] = contract.get('title_signer','')
            res['old_date_start'] = contract.get('date_start','')
            res['old_date_end'] = contract.get('date_end','')
            res['old_liquidation_date'] = contract.get('liquidation_date','')
            res['old_type_id'] = contract.get('type_id', False) and contract['type_id'][0]
            res['old_company_id'] = contract.get('company_id', False) and contract['company_id'][0]
        
        return {'value': res}
    
    def onchange_new_contract_id(self, cr, uid, ids, new_contract_id, context=None):
        res = {'new_info_signer': '','new_title_signer': '','new_type_id': False, 'new_company_id': False,
               'new_date_start': False,'new_date_end': False, 'new_liquidation_date': False}
        
        if new_contract_id:
            contract = self.pool.get('hr.contract').read(cr, uid, new_contract_id, ['info_signer','title_signer','type_id','company_id',
                                                                                    'date_start','date_end','liquidation_date'])
            res['new_info_signer'] = contract.get('info_signer','')
            res['new_title_signer'] = contract.get('title_signer','')
            res['new_date_start'] = contract.get('date_start','')
            res['new_date_end'] = contract.get('date_end','')
            res['new_liquidation_date'] = contract.get('liquidation_date','')
            res['new_type_id'] = contract.get('type_id', False) and contract['type_id'][0]
            res['new_company_id'] = contract.get('company_id', False) and contract['company_id'][0]
        
        return {'value': res}
    
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

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        args_new = [('name', operator, name)] + args
        ids = self.search(cr, uid, args_new)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(vhr_termination_agreement_contract, self).name_search(cr, uid, name, args, operator, context, limit)

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_termination_agreement_contract, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res
    
    def action_print_termination_agreement(self, cr, uid, ids, context=None):
        if not context:
            context = {}
            
        if not isinstance(ids, list):
            ids = [ids]
        
        emp_obj = self.pool.get('hr.employee')
        document_obj = self.pool.get('vhr.personal.document')

        report_name = 'termination_agreement_contract'
        data = self.read(cr, uid, ids, [], context=context)[0]
        
        data['old_signer'] = data['old_info_signer']
        data['new_signer'] = data['new_info_signer']
        data['seniority'] = str(data.get('seniority',0))
        data['remain_leave'] = str(data.get('remain_leave',0))
        
        employee_id = data.get('employee_id', False) and data['employee_id'][0]
        if employee_id:
            emp_data = emp_obj.read(cr, uid, employee_id, [], context=context)
            for k, v in emp_data.iteritems():
                new_key = 'emp_' + k
                data[new_key] = emp_data[k]
                
        if data.get('emp_street', False):
            data['emp_street'] = '%s%s%s' % (
                data['emp_street'],
                data.get('emp_district_id', False) and (', ' + data['emp_district_id'][1]) or '',
                data.get('emp_city_id', False) and (', ' + data['emp_city_id'][1]) or u'',
            )
#         if data.get('emp_temp_address', False):
#             data['emp_temp_street'] = '%s%s%s' % (
#                 data['emp_temp_address'],
#                 data.get('emp_temp_district_id', False) and (', ' + data['emp_temp_district_id'][1]) or '',
#                 data.get('emp_temp_city_id', False) and (', ' + data['emp_temp_city_id'][1]) or u'',
#             )
        
        if 'emp_gender' in data:
            data['emp_gender_en'] = data['emp_gender'] == 'male' and u'Mr' or \
                                 (data['emp_gender'] == 'female' and u'Ms' or u'Mr./Ms')
                                 
            data['emp_gender'] = data['emp_gender'] == 'male' and u'Ông' or \
                                 (data['emp_gender'] == 'female' and u'Bà' or u'Ông/Bà')
        
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
                                 
        data['date_create_agreement'], data['date_before_effect_date'] = self.get_date_create_agreement(cr, uid, data['effect_date'])
        if data['date_create_agreement']:
            data['date_create_agreement_str'] = self.convert_from_date_to_date_string(data['date_create_agreement'])
        else:
            data['date_create_agreement_str'] = ''

        com_id = data.get('old_company_id', False) and data['old_company_id'][0] or []
        if com_id:
            data_old_com = self.get_data_from_company(cr, uid, com_id, 'old_com', context)
            data.update(data_old_com)
            
            if data.get('old_com_name', False):
                data['old_com_name_upper'] = data['old_com_name'].upper()
        
        com_id = data.get('new_company_id', False) and data['new_company_id'][0] or []
        if com_id:
            data_new_com = self.get_data_from_company(cr, uid, com_id, 'new_com', context)
            data.update(data_new_com)
            
            if data.get('new_com_name', False):
                data['new_com_name_upper'] = data['new_com_name'].upper()
        
        
        file_name = 'Termination Agreement ' + data.get('emp_name','')
        
        
        datas = {
            'ids': ids,
            'model': 'hr.contract',
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
    
    def get_data_from_company(self, cr, uid, company_id, name, context=None):
        data = {}
        company_obj = self.pool.get('res.company')
        if company_id:
            move_fields = ['name', 'street', 'phone', 'fax', 'authorization_date','name_en','vat','code','establish_license']
            com_data = company_obj.read(cr, uid, company_id, ['name', 'street', 'phone', 'fax', 'authorization_date','establish_license',
                                                          'street2','city_id','district_id','name_en','vat','code'], context=context)
            for field in move_fields:
                new_key = name + '_' + field
                if field == 'street':
                    address = [com_data['street'] or '',com_data['street2'] or '',com_data['district_id'] and com_data['district_id'][1] or '',
                               com_data['city_id'] and com_data['city_id'][1] or '']
                    
                    address = filter(None, address)
                    address = ', '.join(address)
                    data[new_key] = address
                else:
                    data[new_key] = com_data.get(field,'')
            
            data[name + '_tax_id'] = data[name+'_vat']
        
        return data
    
    def get_date_create_agreement(self, cr, uid, effect_date, context=None):
        """
        Ngày hiệu lực chuyển đổi trừ 1. Nếu rơi vào ngày nghỉ, lễ tết thì phải lùi ngày hành chánh
        """
        agreement_date = False
        date_before_agreement_date = False
        if effect_date:
            
            agreement_date = datetime.strptime(effect_date, DEFAULT_SERVER_DATE_FORMAT) - relativedelta(days=1)
            date_before_agreement_date = agreement_date
            while agreement_date.weekday() in [5,6]:
                agreement_date = agreement_date - relativedelta(days=1)
            
            agreement_date = agreement_date.strftime(DEFAULT_SERVER_DATE_FORMAT)
        
        return agreement_date, date_before_agreement_date.strftime(DEFAULT_SERVER_DATE_FORMAT)
    
    


vhr_termination_agreement_contract()