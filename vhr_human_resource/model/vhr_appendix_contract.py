# -*-coding:utf-8-*-
import logging

from datetime import datetime,date, timedelta
from openerp.osv import osv, fields
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.addons.vhr_common.model.vhr_common import vhr_common
from openerp import SUPERUSER_ID
from dateutil.relativedelta import relativedelta
from openerp.tools.translate import _

log = logging.getLogger(__name__)


class vhr_appendix_contract(osv.osv, vhr_common):
    _name = 'vhr.appendix.contract'
    _description = 'Appendix Contract'
    
    
#     def _get_next_number_of_mission(self, cr, uid, ids, field_name, arg, context=None):
#         res = {}
#         if not isinstance(ids, list):
#             ids = [ids]
#         
#         for record in self.read(cr, uid, ids, ['mission_ids']):
#             number = len(record.get('mission_ids',[]))
#             res[record['id']] = "Công việc" + str(number + 1)
#         
#         return res
    
    def _is_created(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if not isinstance(ids, list):
            ids = [ids]
        
        for record_id in ids:
            res[record_id] = True
        return res
    
    def _is_readonly(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if not isinstance(ids, list):
            ids = [ids]
        
        for record in self.read(cr, uid, ids, ['wr_id']):
            res[record['id']] = False
            if record.get('wr_id', False):
                res[record['id']] = True
                
        return res
        
    
    
    _columns = {
                'name': fields.char('Name', size=128),
                'contract_id': fields.many2one('hr.contract', 'Contract', ondelete='restrict'),
                'employee_id': fields.related('contract_id', 'employee_id', readonly=True, type='many2one',relation='hr.employee', string='Employee'),
                'company_id': fields.related('contract_id', 'company_id', readonly=True, type='many2one',relation='res.company', string='Company'),
                'contract_sub_type_id': fields.related('contract_id', 'sub_type_id', readonly=True, type='many2one',
                                                       relation='hr.contract.sub.type', string='Contract Sub Type'),
                'appendix_type_id': fields.many2one('vhr.appendix.contract.type', 'Appendix Type', ondelete='restrict'),
                'is_change_mission': fields.related('appendix_type_id', 'is_change_mission', readonly=True, 
                                                    type='boolean', string='Is Change Mission'),
                'is_change_salary': fields.related('appendix_type_id', 'is_change_salary', readonly=True, 
                                                    type='boolean', string='Is Change Salary'),
                'is_change_allowance': fields.related('appendix_type_id', 'is_change_allowance', readonly=True, 
                                                    type='boolean', string='Is Change Allowance'),
                'is_extension_appendix': fields.related('appendix_type_id', 'is_extension_appendix', readonly=True, 
                                                    type='boolean', string='Is Extension Appendix'),
                'date_start': fields.date('Date Start', required=True),
                'date_end': fields.date('Date End'),
                'description': fields.text('Description'),
                'active': fields.boolean('Active'),
                
                'mission_ids': fields.one2many('vhr.mission.collaborator.contract', 'appendix_id', string='Responsibilities'),

#                 'next_number_of_mission': fields.function(_get_next_number_of_mission, type='char', string="Next Number of Mission"),
                'is_create_code': fields.boolean('Is Create Appendix Name'),
                'is_created': fields.function(_is_created, type='boolean', string='Is Created'),
                'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                      domain=[('object_id.model', '=', _name), \
                                              ('field_id.name', 'not in', ['write_date', 'audit_log_ids'])]),
                
                'info_signer': fields.char("Signer"),
                'sign_date': fields.date('Sign Date'),
                'title_signer': fields.char("Signer's Title"),
                'country_signer': fields.many2one('res.country', "Signer's Nationality"),
                
                'department_id': fields.related('employee_id', 'department_id', type='many2one',
                                        relation='hr.department', string='Department'),
                'division_id': fields.related('employee_id', 'division_id', type='many2one',
                                        relation='hr.department', string='Division'),
                
                #Working record created appendix contract
                'wr_id': fields.many2one('vhr.working.record', 'Working Record', ondelete='restrict'),
                'is_readonly': fields.function(_is_readonly, type='boolean', string='Is readonly'),
                'job_title': fields.many2one('vhr.job.title', 'Job Title', ondelete='restrict'),
    }

    _defaults = {
        'active': False,
        'is_extension_appendix': False,
#         'next_number_of_mission': 'Công việc 1',
        'is_created': False
    }

    
    def read(self, cr, user, ids, fields=None, context=None, load='_classic_read'):
        if not context:
            context = {}
            
        if context.get('validate_read_vhr_appendix_contract',False):
            log.info('\n\n validate_read_vhr_appendix_contract')
            if not context.get('filter_by_group', False):
                context['filter_by_group'] = True
            result_check = self.validate_read(cr, user, ids, context)
            if not result_check:
                raise osv.except_osv('Validation Error !', 'You don’t have permission to access this data !')
            del context['validate_read_vhr_appendix_contract']
        return super(vhr_appendix_contract, self).read(cr, user, ids, fields, context, load)
    
    def validate_read(self, cr, uid, ids, context=None):
        user_groups = self.pool.get('res.users').get_groups(cr, uid)
        if set(['hrs_group_system', 'vhr_cnb_manager']).intersection(set(user_groups)):
            return True
        if isinstance(ids, (int, long)) or (isinstance(ids, list) and len(ids)) == 1:
            log.info( ' ---go to search in validate_read_vhr_appendix_contract employee')
            check_id = ids
            if isinstance(ids, list):
                check_id = ids[0]
            new_context = context and context.copy() or {}
            new_context.update({'filter_by_group': True})
            lst_check = self.search(cr, uid, [], context=new_context)
            if check_id not in lst_check:
                return False
        return True
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if not context:
            context = {}
        
        if 'active_test' not in context:
            context['active_test'] = False
        
        if context.get('filter_by_group', False):
            contract_ids = self.pool.get('hr.contract').search(cr, uid, [], 0, None, None, context)
            args.append(('contract_id','in', contract_ids))
        
        res =  super(vhr_appendix_contract, self).search(cr, uid, args, offset, limit, order, context, count)
        return res
    
    
    def name_get(self, cr, uid, ids, context=None):
        if not ids or False in ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        
        reads = self.read(cr, uid, ids, [], context=context)
        res = []
        for record in reads:
            name = record.get('employee_id',False) and record['employee_id'][1]
            res.append((record['id'], name))
        return res
    
    def onchange_is_extension_appendix(self, cr, uid, ids, is_extension_appendix, context=None):
        res = {}
#         if not is_extension_appendix:
#             res['mission_ids'] = []
#             res['gross_salary'] = 0
#             res['basic_salary'] = 0
#             res['general_allowance'] = 0
#             res['kpi_amount'] = 0
#             res['allowance_ids'] = []
        
        return {'value': res}
    
    
    def onchange_contract_id(self, cr, uid, ids, contract_id, appendix_type_id, context=None):
        res = {'employee_id': False,'info_signer': '', 'title_signer': '','country_signer': ''}
        
        if contract_id:
            contract = self.pool.get('hr.contract').read(cr, uid, contract_id, ['employee_id','sub_type_id','company_id','date_end'])
            res['employee_id'] = contract.get('employee_id', False) and contract['employee_id'][0]
            res['contract_sub_type_id'] = contract.get('sub_type_id', False) and contract['sub_type_id'][0]
            
            company_id = contract.get('company_id', False) and contract['company_id'][0]
            if company_id:
                res_read = self.pool.get('res.company').read(cr, uid, company_id, ['sign_emp_id','job_title_id','country_signer'])
                if res_read['sign_emp_id']:
                    res.update({'info_signer': res_read['sign_emp_id'],
                                 'title_signer': res_read.get('job_title_id',''),
                                 'country_signer': res_read.get('country_signer',False) and res_read['country_signer'][0] or False,
                                 })
                    
            if appendix_type_id:
                appendix_type = self.pool.get('vhr.appendix.contract.type').read(cr, uid, appendix_type_id, ['is_extension_appendix'])
                is_extension_appendix = appendix_type.get('is_extension_appendix',False)
                if is_extension_appendix:
                    res['date_start'] = self.get_date_after_data_end_contract(cr, uid, contract_id, context)
        
        return {'value': res}
    
    def onchange_appendix_type_id(self, cr, uid, ids, appendix_type_id, contract_id, context=None):
        if not context:
            context = {}
        res={'is_extension_appendix': False, 'is_change_mission': False, 'is_change_salary': False, 'is_change_allowance': False}
        
        if not isinstance(ids, list):
            ids = [ids]
            
        if appendix_type_id:
            record = {}
            if ids:
                record = self.read(cr, uid, ids[0], ['mission_ids','allowance_ids'])
                
            appendix_type = self.pool.get('vhr.appendix.contract.type').read(cr, uid, appendix_type_id, [])
            res['is_change_mission'] = appendix_type.get('is_change_mission', False)
            if not res['is_change_mission']:
                res['mission_ids'] = []
                for mission_id in record.get('mission_ids',[]):
                    res['mission_ids'].append((2,mission_id))
                
            res['is_change_salary'] = appendix_type.get('is_change_salary', False)
            if not res['is_change_salary']:
                res['gross_salary'] = 0
                res['basic_salary'] = 0
                res['general_allowance'] = 0
                res['v_bonus_salary'] = 0
                res['kpi_amount'] = 0
                                      
            res['is_change_allowance'] = appendix_type.get('is_change_allowance', False)
            if not res['is_change_allowance']:
                res['allowance_date_to'] = False
                res['allowance_date_from'] = False
                res['allowance_ids'] = []
                for allowance_id in record.get('allowance_ids',[]):
                    res['allowance_ids'].append((2,allowance_id))
            
            is_extension_appendix = appendix_type.get('is_extension_appendix',False)
            if is_extension_appendix:
                res['is_extension_appendix'] = True
            
                if contract_id:
                    res['date_start'] = self.get_date_after_data_end_contract(cr, uid, contract_id, context)
                elif context.get('contract_date_end', False):
                    date_end = datetime.strptime(context['contract_date_end'], DEFAULT_SERVER_DATE_FORMAT) + relativedelta(days=1)
                    res['date_start'] = date_end.strftime(DEFAULT_SERVER_DATE_FORMAT)
        
        return {'value': res}
    
    def on_change_date_start(self, cr, uid, ids, date_start, context=None):
        """
        Sign_date = date_start-1 - 14 normal days: Only for Official
        Sign_date = date_start: For Non-Official
        """
        if not context:
            context = {}
            
        res = {'sign_date': False}
        
        if date_start:
            is_official = True
            contract_id = context.get('contract_id', False)
            if contract_id:
                contract = self.pool.get('hr.contract').browse(cr, uid, contract_id, fields_process=['type_id'])
                is_official = contract.type_id and contract.type_id.is_official or False
            
            if is_official:
                start_time = datetime.strptime(date_start, DEFAULT_SERVER_DATE_FORMAT) - relativedelta(days=1)
                date_check = start_time
                for index in range(0,14):
                    date_check = date_check - relativedelta(days=1)
                    while date_check.weekday() in [5,6]:
                        date_check = date_check - relativedelta(days=1)
                
                sign_date = date_check.strftime(DEFAULT_SERVER_DATE_FORMAT)
            else:
                sign_date = date_start
            
            res['sign_date'] = sign_date
        
        return {'value': res}
                 
    def onchange_is_create_code(self, cr, uid, ids, is_create_code, sign_date, context=None):
        res = {'name': ''}
        
        if sign_date and is_create_code:
            res['name'] = self.generate_code(cr, uid, [], {'sign_date': sign_date})
            
        return {'value': res}
    
    def onchange_sign_date(self, cr, uid, ids, sign_date, is_create_code, context=None):
        res = {'name': ''}
        if sign_date and is_create_code:
            res['name'] = self.generate_code(cr, uid, [], {'sign_date': sign_date})
            
        return {'value': res}
    
    
    def get_date_after_data_end_contract(self, cr, uid, contract_id, context=None):
        res = False
        if contract_id:
            contract = self.pool.get('hr.contract').read(cr, uid, contract_id, ['date_end','date_end_temp'])
            date_end = contract.get('date_end_temp', False) or contract.get('date_end', False)
            if date_end:
                date_end = datetime.strptime(date_end, DEFAULT_SERVER_DATE_FORMAT) + relativedelta(days=1)
                res = date_end.strftime(DEFAULT_SERVER_DATE_FORMAT)
        
        return res

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        ids = self.search(cr, uid, args)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(vhr_appendix_contract, self).name_search(cr, uid, name, args, operator, context, limit)
    
    def check_dates(self, cr, uid, ids, context=None):
        for record in self.read(cr, uid, ids, ['date_start', 'date_end'], context=context):
            if record.get('date_start',False) and record.get('date_end',False) and self.compare_day(record['date_end'],record['date_start']) > 0:
#                 return False
                raise osv.except_osv('Validation Error !', '[Appendix Contract] Date To must be greater Date Start !')

        return True
    
#     def check_overlap_date(self, cr, uid, ids, context=None):
#         if not context:
#             context = {}
#         if ids:
#             data = self.browse(cr, uid, ids[0], context)
#             contract_id = data.contract_id and data.contract_id.id or False
#             date_start = data.date_start
#             date_end = data.date_end or False
#             
#             if contract_id and date_start:
#                 args = [('contract_id', '=', contract_id),('is_extension_appendix','=',False)]
#                 
#                 appendix_ids = self.search(cr, uid, args)
#                 if not appendix_ids:
#                     return True
#                 
#                 not_overlap_args = [('date_end', '<', date_start)] + args
#                 if date_end:
#                     not_overlap_args.insert(0,'|')
#                     not_overlap_args.insert(1,('date_start', '>', date_end))
#                 
# #                     not_overlap_args = ['|',('date_start', '>', date_end),('date_end', '<', date_start)] + args
#                 not_overlap_appendix_ids = self.search(cr, uid, not_overlap_args)
#                 #Record not overlap is the record link to employee
#                 if len(appendix_ids) == len(not_overlap_appendix_ids):
#                     return True
#                 else:
#                     #Get records from working_ids not in not_overlap_working_ids
#                     overlap_ids = [x for x in appendix_ids if x not in not_overlap_appendix_ids]
#                     #Get records from working_ids are not working_id
#                     overlap_ids = [x for x in overlap_ids if x not in ids]
#                     if overlap_ids:
#                         employee_name = data.employee_id and data.employee_id.code or ''
#                         contract_name = data.contract_id and data.contract_id.name or ''
#                         raise osv.except_osv('Validation Error !', 'The effective duration in Appendix Contracts of employee "%s" at contract "%s" is overlapped. Please check again '%(employee_name, contract_name))
# 
#         return True
    
    def check_out_of_contract_effect_date(self, cr, uid, ids, context=None):
        """
        Effective duration of Appendix Contract (exception with extension appendix) have to inside effective duration of contract
        """
        if ids:
            
            for record in self.browse(cr, uid, ids):
                if not record.is_extension_appendix:
                    contract = record.contract_id
                    contract_date_start = contract and contract.date_start
                    contract_date_end = contract and ( contract.liquidation_date or contract.date_end)
                    
                    appendix_date_start = record.date_start
                    appendix_date_end = record.date_end
                    
                    is_appendix_start_greater_contract_start = self.compare_day(contract_date_start, appendix_date_start)
                    is_contract_end_greater_appendix_end = contract_date_end and appendix_date_end and self.compare_day(appendix_date_end, contract_date_end)
                    if is_appendix_start_greater_contract_start >= 0  and (not (contract_date_end and appendix_date_end) or is_contract_end_greater_appendix_end >=0):
                        return True
                    else:
                        raise osv.except_osv('Validation Error !',"The effective duration of Appendix Contract have to in effective duration of Contract")
        
        return True
    
    def check_unique_extension_appendix(self, cr, uid, ids, context=None):
        """
        Each contract only have one extension appendix
        """
        if ids:
            
            for record in self.read(cr, uid, ids, ['contract_id','date_end']):
                contract_id = record.get('contract_id', False) and record['contract_id'][0]
                date_end = record.get('date_end', False)
                
                extension_ids = self.search(cr, uid, [('contract_id','=',contract_id),
                                                      ('is_extension_appendix','=',True),
                                                      ('id','!=',record['id'])])
                if extension_ids:
                    contract_name = record.get('contract_id', False) and record['contract_id'][1]
                    raise osv.except_osv('Validation Error !',"Contract %s had an extension appendix contract !" % contract_name)
                
                #If contract dont have date end, we dont need extension appendix contract
                if not date_end:
                    raise osv.except_osv('Validation Error !',"Contract is indefinite !")
        
        return True
                
                
    def check_active_record(self, cr, uid, ids, context=None):
        """
        Update active=False, active=True based on date_start, date_end
        """
        if ids:
            today = datetime.today().date().strftime(DEFAULT_SERVER_DATE_FORMAT)
            for record in self.read(cr, uid, ids, ['date_start', 'date_end']):
                date_start = record['date_start']
                date_end = record['date_end']
                vals = {}
                if self.compare_day(date_start, today) >= 0 and  (not date_end or self.compare_day(today, date_end)) >= 0:
                    vals['active'] = True
                else:
                    vals['active'] = False
                
                super(vhr_appendix_contract, self).write(cr, uid, record['id'], vals)
        
        return True
                
    
    def update_contract_date_end_real(self, cr, uid, ids, context=None):
        """
        Update date_end_real in contract if record is extension appendix
        """
        if ids:
            contract_obj = self.pool.get('hr.contract')
            for record in self.browse(cr, uid, ids):
                contract_id = record.contract_id and record.contract_id.id or False
                contract_date_end = record.contract_id and record.contract_id.date_end or False
                contract_date_end_temp = record.contract_id and record.contract_id.date_end_temp or False
                
                if contract_id and contract_date_end and record.is_extension_appendix:
                    new_date_end = record.date_end
                    vals = {"date_end": new_date_end}
                    if not contract_date_end_temp:
                        vals['date_end_temp'] = contract_date_end
                        
                    contract_obj.write(cr, uid, contract_id, vals, context={'do_not_check_extension_appendix': True})
        
        return True
    
    def increment_number_contract(self, cr, uid, ids, sign_date, context=None):
        stt = 0
        if context is None:
            context = {}
        context.update({'active_test': False})
        
        sign_date = datetime.strptime(sign_date, DEFAULT_SERVER_DATE_FORMAT)
        start_month = date(sign_date.year, sign_date.month, 1).strftime(DEFAULT_SERVER_DATE_FORMAT)
        end_month = ((date(sign_date.year, sign_date.month, 1) + relativedelta(months=1)) - timedelta(1)).strftime("%Y-%m-%d")
        find_ids = self.search(cr, uid, [('sign_date', '>=', start_month), 
                                    ('sign_date', '<=', end_month), 
                                    ('is_create_code','=',True),
                                    ('id', 'not in', ids)], None, None, 'id desc', context, False)
        for read_res in self.browse(cr, uid, find_ids):
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
        return stt + 1
    
    def generate_code(self, cr, uid, ids, vals, context=None):
        """
        Currently only generate name for extension appendix contract
        """
        
        record = {}
        
        old_employee_id = False
        old_sign_date = False
        if ids:
            record = self.read(cr, uid, ids[0], ['sign_date'])
            old_sign_date = record.get('sign_date', False)
            
        sign_date = vals.get('sign_date', old_sign_date)
        
        sequence = self.increment_number_contract(cr, uid, ids, sign_date, context)
        try:
            sign_date = datetime.strptime(sign_date, DEFAULT_SERVER_DATE_FORMAT)
            year = sign_date.year
            month = sign_date.month
        except ValueError:
            raise osv.except_osv(_('Warning'),
                                 _('Invalid prefix or suffix for contract type group \'%s\'') % (type_group.name))
        res = '%s/%02i/%03i-%s' % (year, month, sequence, 'PL')
        return res
        
    
    def create(self, cr, uid, vals, context=None):
        if not context:
            context = {}
        context['prefix_name_of_mission'] = 'Công việc '
        
        if vals.get('is_create_code', False) and not context.get('do_not_generate_name', False):
            vals['name'] = self.generate_code(cr, uid, [], vals)
        res = super(vhr_appendix_contract, self).create(cr, uid, vals, context)
        
        if res:
            if vals.get('is_extension_appendix', False):
                self.check_unique_extension_appendix(cr, uid, [res], context)
                self.update_contract_date_end_real(cr, uid, [res], context)
                
            self.check_dates(cr, uid, [res], context)
#             self.check_overlap_date(cr, uid, [res], context)
            self.check_out_of_contract_effect_date(cr, uid, [res], context)
            self.check_active_record(cr, uid, [res], context)
            
        
        return res
    
    def write(self, cr, uid, ids, vals, context=None):
        if not isinstance(ids, list):
            ids = [ids]
        
        if not context:
            context = {}
        context['prefix_name_of_mission'] = 'Công việc '
        
        if vals.get('is_create_code', False) and not context.get('do_not_generate_name', False):
            vals['name'] = self.generate_code(cr, uid, ids, vals)
        
        old_appendix_datas = [{}]
        if 'is_extension_appendix' in vals.keys() and not vals.get('is_extension_appendix', False):
            old_appendix_datas = self.read(cr, uid, ids, ['is_extension_appendix'])
            
        
        res = super(vhr_appendix_contract, self).write(cr, uid, ids, vals, context)
        
        if res:
            if vals.get('is_extension_appendix', False):
                self.check_unique_extension_appendix(cr, uid, ids, context)
            
            if set(['date_start','date_end']).intersection(vals.keys()): 
                self.check_dates(cr, uid, ids, context)
#                 self.check_overlap_date(cr, uid, ids, context)
            
            if 'is_extension_appendix' in vals.keys() and not vals.get('is_extension_appendix', True):
                context['old_appendix_datas'] = old_appendix_datas
                self.check_to_rollback_update_contract_date_end_real(cr, uid, ids, context)
                
            
            if set(['date_start','date_end','is_extension_appendix']).intersection(vals.keys()):
                self.check_out_of_contract_effect_date(cr, uid, ids, context)
                
            if set(['date_start','date_end','description']).intersection(vals.keys()):
                self.check_active_record(cr, uid, ids, context)
            
            if set(['date_end','description','appendix_type_id','is_extension_appendix']).intersection(vals.keys()):
                self.update_contract_date_end_real(cr, uid, ids, context)
                
                if vals.get('date_end', False):
                    self.check_if_out_of_wr_of_contract(cr, uid, ids, old_appendix_datas, context)
            
        return res

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            for record in self.read(cr, uid, ids, ['wr_id']):
                if record.get('wr_id', False):
                    raise osv.except_osv('Validation Error !', 'You can not delete directly appendix contract created from Working Record !')
                
            self.check_to_rollback_update_contract_date_end_real(cr, uid, ids, context)
            res = super(vhr_appendix_contract, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            error_message = ''
            try:
                error_message = e.message
                if not error_message:
                    error_message = e.value
            except:
                error_message = ""
            raise osv.except_osv('Validation Error !', ' %s'%error_message)
        return res
    
    
    def check_if_out_of_wr_of_contract(self, cr, uid, ids, old_appendix_datas, context=None):
        """
        If change date_end of extension appendix and have WR with effect from between (old_date_end,date_start) but not in (new_date_end,date_start) ==>Raise error
        """
        working_pool = self.pool.get('vhr.working.record')
        for record in self.read(cr, uid, ids, ['contract_id', 'is_extension_appendix']):
            contract_id = record.get('contract_id', False) and record['contract_id'][0]
            is_extension_appendix = record.get('is_extension_appendix')
            
            #If change is_extension_appendix from True to False, need to check WR too
            if not is_extension_appendix and old_appendix_datas:
                for data in old_appendix_datas:
                    if data and data['id'] == record['id'] and data.get('is_extension_appendix', False):
                        is_extension_appendix = True
                        break
                    
            if contract_id and is_extension_appendix:
                contract_data = self.pool.get('hr.contract').read(cr, uid,contract_id, ['date_start', 'date_end'])
                contract_date_start = contract_data.get('date_start', False)
                contract_date_end = contract_data.get('date_end', False)
                #Search WR have contract_id and effect_from out of contract_date_start,contract_date_end
                if contract_date_end:
                    domain_wr = [('state','in', [False,'finish']),
                                 ('contract_id','=',contract_id),
                                 '|',
                                 ('effect_from','<',contract_date_start),
                                 ('effect_from','>',contract_date_end)]
                    
                    working_ids = working_pool.search(cr, uid, domain_wr, context=context)
                    if working_ids:
                        raise osv.except_osv('Validation Error !', 
                                             'Have working records with effective date out of date start contract and new date end contract ! \n %s'%str(working_ids))
        
        return True
                    
            
    def check_to_rollback_update_contract_date_end_real(self, cr, uid, ids, context):
        """
        Reupdate contract_date_end = contract_date_end_temp when contract no longer have extension appendix contract
        """
        if not context:
            context = {}
            
        if ids:
            working_pool = self.pool.get('vhr.working.record')
            contract_pool = self.pool.get('hr.contract')
            old_appendix_datas = context.get('old_appendix_datas', [])
            
            for record in self.read(cr, uid, ids, ['contract_id','is_extension_appendix']):
                contract_id = record.get('contract_id', False) and record['contract_id'][0]
                is_extension_appendix = record.get('is_extension_appendix')
                
                #If change is_extension_appendix from True to False, need to check WR too
                if not is_extension_appendix and old_appendix_datas:
                    for data in old_appendix_datas:
                        if data['id'] == record['id'] and data.get('is_extension_appendix', False):
                            is_extension_appendix = True
                            break
                    
                #Only check with extension appendix
                if contract_id and is_extension_appendix:
                    extend_appendix_ids = self.search(cr, uid, [('contract_id','=',contract_id),
                                                                ('is_extension_appendix','=',True),
                                                                ('id','not in', ids)])
                    if not extend_appendix_ids:
                        contract = contract_pool.read(cr, uid, contract_id, ['date_end','date_end_temp','liquidation_date','date_start'])
                        if contract.get('date_end_temp', False):
                            vals = {'date_end':contract['date_end_temp'],
                                    'date_end_temp': False}
                            
                            #if liquidation date over date_end_temp, set liquidation_date = date_end_temp+1
                            if contract.get('liquidation_date', False):
                                date_end_temp_plus = datetime.strptime(contract['date_end_temp'], DEFAULT_SERVER_DATE_FORMAT) + relativedelta(days=1)
                                date_end_temp_plus = date_end_temp_plus.strftime(DEFAULT_SERVER_DATE_FORMAT)
                                is_greater = self.compare_day(date_end_temp_plus, contract['liquidation_date'])
                                if is_greater:
                                    vals['liquidation_date'] = date_end_temp_plus
                                
                            contract_pool.write_with_log(cr, uid, contract_id, vals, context)
                            
                            #Check if have wr effect with contract_id effect out of contract duration
                            contract_date_end = contract.get('liquidation_date', False) or contract.get('date_end_temp', False)
                            if vals.get('liquidation_date', False):
                                contract_date_end = contract['date_end_temp']
                                
                            domain_wr = [('state','in', [False,'finish']),
                                         ('contract_id','=',contract_id),
                                         '|',
                                         ('effect_from','<',contract['date_start']),
                                         ('effect_from','>',contract_date_end)]
                            working_ids = working_pool.search(cr, uid, domain_wr, context=context)
                            if working_ids:
                                raise osv.except_osv('Validation Error !', 
                                                     'Have working records with effective date out of date start contract and new date end contract ! \n %s'%str(working_ids))
        
        return True
            
            
    
    
    def cron_appendix_contract_state(self, cr, uid, context=None):
        """
        Update state of record if satisfy condition of active
            set = True: date_start <= today <= date_end; contract.state=signed
        """
        if not context:
            context = {}
            
        log.info('start cron update appendix contract state')
        today = datetime.today().date()
        working_record_ids = []
        #Get WR have active=False need to update active=True
        active_record_ids = self.search(cr, uid, [('active','=',False),
                                                  ('date_start','<=',today),
                                                  '|',('date_end','=',False),
                                                       ('date_end','>=',today)])
        
        #Get WR have active=True need to update active=False
        inactive_record_ids = self.search(cr, uid, [('active','=',True),
                                                      '|',('date_end','<',today),
                                                           ('date_start','>',today)])
        
        ##Select not latest appendix of each contract when appendix dont have date_end
        sql = """
                SELECT temp.id FROM 
                    (SELECT id,date_start,date_end,
                           case when lead(date_start) over (partition by contract_id order by date_start) is not null then false 
                                else true end as is_latest 
                    FROM vhr_appendix_contract where date_end is null) temp where temp.is_latest = false
              """
        cr.execute(sql)
        res = cr.fetchall()
        appendix_ids = [item[0] for item in res]
        if appendix_ids:
            active_record_ids = list( set(active_record_ids).difference(set(appendix_ids)))
            inactive_record_ids.extend(appendix_ids)
         
        record_ids = active_record_ids + inactive_record_ids
        
        if record_ids:
            self.write(cr, uid, active_record_ids, {'active': True})
            
            super(vhr_appendix_contract, self).write(cr, uid, inactive_record_ids, {'active': False})
            log.info("Active WR: %s, Inactive WR:%s"%(len(active_record_ids),len(inactive_record_ids)))
            
        log.info('end cron update appendix contract state')
        return True
    
    def thread_import_appendix_contract(self, cr, uid, import_status_id, rows, context=None):
        log.info('Begin: thread_import_working_record')
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
            mapping_fields = {'XML ID': 'xml_id',
                              'Employee Code': 'employee_id',
                              'Contract Name': 'contract_id', 
                              'Contract Sub Type':'contract_sub_type_id',
                              'Appendix Contract Type': 'appendix_type_id', 
                              'Date Start': 'date_start', 
                              'Date End': 'date_end',
                              'Create Code': 'is_create_code',
                              'Appendix Name': 'name',
                              "Description": 'description',
                              "Sign Date": 'sign_date',
                              "Create Salary Progress": 'is_generate_salary',
                              "Gross Salary": 'gross_salary',
                              "Basic Salary": 'basic_salary',
                              "% Split Salary": 'salary_percentage',
                              "KPI": 'kpi_amount',
                              "General Allowance": 'general_allowance',
                              "V_Bonus":'v_bonus_salary',
                              "Type Of Salary": 'type_of_salary',
                              }
            
            required_fields = ['employee_id','appendix_type_id','date_start']
            fields_order = []
            fields_search_by_name = ['contract_id']
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
                                if vals.get('contract_id', False):
                                    contract_ids = [vals['contract_id']]
                                else:
                                    contract_ids = contract_obj.search(cr, uid, [ ('employee_id', '=',vals['employee_id']),
                                                                                  ('date_start','<=',vals['date_start']),
                                                                                  ('date_end','>=',vals['date_end'])])
                                
                                
                                if len(contract_ids) == 1:
                                    vals['contract_id'] = contract_ids[0]
                                    
                                    if vals.get('contract_id', False) and vals.get('contract_sub_type_id', False):
                                        contract_obj.write_with_log(cr, uid, vals['contract_id'], {'sub_type_id':vals['contract_sub_type_id']})
                                    
                                    if vals.get('contract_id', False):
                                        contract = contract_obj.read(cr, uid, vals['contract_id'], ['info_signer','title_signer','country_signer'])
                                        vals['info_signer'] = contract.get('info_signer', '')
                                        vals['title_signer'] = contract.get('title_signer', '')
                                        vals['country_signer'] = contract.get('country_signer', False) and contract['country_signer'][0]
                                        
                                    mode = 'init'
                                    current_module = ''
                                    noupdate = False
                                    xml_id = vals.get('xml_id', False)
                                    
                                    old_ids = self.search(cr, uid, [('contract_id','=',vals.get('contract_id', False)),
                                                                    ('appendix_type_id','=',vals.get('appendix_type_id',False)),
                                                                    ('date_start','=',vals.get('date_start', False))])
                                    
                                    if vals.get('name', False):
                                        context['do_not_generate_name'] = True
                                    else:
                                        context['do_not_generate_name'] = False
                                    
                                    context['prevent_gen_salary'] = False
                                    if vals.get('is_generate_salary', False) ==  False:
                                        context['prevent_gen_salary'] = True
                                        
                                    if old_ids:
                                        self.write(cr, uid, old_ids, vals, context)
                                    else:
                                        self.pool.get('ir.model.data')._update(cr, SUPERUSER_ID, self._name, current_module, vals, mode=mode, xml_id=xml_id,
                                                          noupdate=noupdate, res_id=False, context=context)
                                    success_row += 1
                                else:
                                    error = "Employee have %s contract satisfy date_start and date_end of template: %s"%(len(contract_ids), str(contract_ids))
                                
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
        log.info('End: thread_import_working_record')
        return True
    
    def parse_data_from_excel_row(self, cr, uid, row, mapping_fields, fields_search_by_name, fields_order, context=None):
        res = {}
        error = ""
        if row and mapping_fields and fields_order:
            for index, item in enumerate(row):
                #If item in row does not appear in mapping fields, by pass  
                field_name = mapping_fields.get(fields_order[index])
                if field_name:
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
                                value = datetime.strptime(item,"%d/%m/%Y").strftime(DEFAULT_SERVER_DATE_FORMAT)
                            res[field_name] = value
                        except Exception as e:
                            error = "Field %s have to input correct date format dd/mm/YYYY" % field_obj.string 
                    
                    elif (field_obj and field_obj._type == 'boolean') or field_name == 'is_generate_salary':
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
                        if field_name == 'name':
                            res['is_create_code'] = True
                    
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
    
    def print_appendix_contract(self, cr, uid, ids, context=None):
        if not isinstance(ids, list):
            ids = [ids]
        
        
        department_obj = self.pool.get('hr.department')
        document_obj = self.pool.get('vhr.personal.document')
        employee_obj = self.pool.get('hr.employee')
        company_obj = self.pool.get('res.company')
        allowance_obj = self.pool.get('vhr.pr.allowance')
        salary_obj = self.pool.get('vhr.pr.salary')
        if ids:
            report_name = ''
            data = {}
            appendix = self.browse(cr, uid, ids[0], fields_process=['appendix_type_id'])
            appendix_type_code = appendix.appendix_type_id and appendix.appendix_type_id.code or ''
            
            appendix_data = self.read(cr, uid, ids[0], [], context=context)
            for k, v in appendix_data.iteritems():
                new_key = 'app_' + k
                data[new_key] = appendix_data[k]
            
            data['app_sum_pr_allowance'] = 0
            if data.get('app_allowance_ids', []):
                allowances = allowance_obj.read(cr, uid, data['app_allowance_ids'], ['name','amount','allowance_cate_id','from_date','to_date'])
                for allowance in allowances:
                    for key in allowance:
                        if isinstance(allowance[key], tuple):
                            allowance[key] = allowance[key][1]
                        if key in ['from_date','to_date']:
                            allowance[key] = datetime.strptime(allowance[key], DEFAULT_SERVER_DATE_FORMAT).strftime("%d/%m/%Y")
                            
                    data['app_sum_pr_allowance'] += allowance['amount']
            
                data['app_allowance_ids'] = allowances
                
#             else:
#                 data['app_allowance_ids'] = [{'name': '','amount': '', 'allowance_cate_id': ''}]
            
            #Contract data
            contract_id = appendix_data.get('contract_id',False) and appendix_data['contract_id'][0] or False
            if contract_id:
                contract_data = self.pool.get('hr.contract').read(cr, uid, contract_id, [])
                data.update(contract_data)
            
            #Check if need to print clause 2 for second appendix not extension of contract
            data['is_second_appendix_of_contract'] = False
            if not data.get('app_is_extension_appendix', False) and contract_id:
                appendix_ids = self.search(cr, uid, [('contract_id','=',contract_id),
                                                     ('is_extension_appendix','=',False),
                                                     ],order='date_start asc')
                if appendix_ids and appendix_ids.index(ids[0]) == 1:
                    data['is_second_appendix_of_contract'] = True
                
            
            #Company data
            data['com_code'] = ''
            company_id = appendix_data.get('company_id',False) and appendix_data['company_id'][0] or False
            if company_id:
                comp_data = self.pool.get('res.company').read(cr, uid, company_id, ['code'])
                data['com_code'] = comp_data.get('code', '')
                    
            
            #Department Code
            department_id = data.get('department_id', False) and data['department_id'][0] or []
            data['department_code'] = ''
            if department_id:
                department = department_obj.read(cr, uid, department_id, ['name', 'code','complete_code'], context=context)
                data.update({'department_id': department.get('name', ''), 'department_code': department.get('code', '')})
            
            data['signer'] = ''
            if data.get('info_signer', False):
                data['signer'] = data['info_signer'] or ''
                data['signer_country_id'] = data.get('country_signer',False) and data['country_signer'][1] or False
            
            #employee data
            emp_id = data.get('employee_id', False) and data['employee_id'][0] or []
            data['emp_temp_street'] = ''
            if emp_id:
                emp_data = employee_obj.read(cr, uid, emp_id, [], context=context)
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
            
            if 'emp_gender' in data:
                data['emp_gender_en'] = data['emp_gender'] == 'male' and u'Mr' or \
                                     (data['emp_gender'] == 'female' and u'Ms' or u'Mr./Ms')
                                     
                data['emp_gender'] = data['emp_gender'] == 'male' and u'Ông' or \
                                     (data['emp_gender'] == 'female' and u'Bà' or u'Ông/Bà')
            
            #document data
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
            
            #company data
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
            
            #bank data
            data['bank_account'] = ''
            data['bank_name'] = ''
            if data.get('bank_account_ids', False):
                bank_account_ids = data.get('bank_account_ids',[])
                bank_account = self.pool.get('vhr.bank.contract').browse(cr, uid, bank_account_ids[0])
                bank_account_number = bank_account.bank_id and bank_account.bank_id.acc_number or ''
                if 'Unknown' not in bank_account_number:
                    data['bank_account'] = bank_account_number
                    data['bank_name'] = bank_account.bank_id and bank_account.bank_id.bank and bank_account.bank_id.bank.name or ''
                    
            data['sign_date_str']  = self.convert_from_date_to_date_string(data['sign_date'])
            data['date_start_str'] = self.convert_from_date_to_date_string(data['date_start'])
            data['app_sign_date_str'] = self.convert_from_date_to_date_string(data['app_sign_date'])
            data['app_date_start_str'] = data['app_sign_date_str']
            
            #Mission data
            data['app_mission'] = ''
            data['app_mission_salary'] = ''
            if data.get('app_mission_ids', False):
                mission_ids = data['app_mission_ids']
                missions = self.pool.get('vhr.mission.collaborator.contract').read(cr, uid, mission_ids, ['name','value','salary'])
                for mission in missions:
                    name = mission.get('name','')
                    value = mission.get('value','')
                    salary = mission.get('salary', 0)
                    if value and name:
                        if data['app_mission']:
                            data['app_mission'] += '\\n'
                            data['app_mission_salary'] += '\\n'
                        data['app_mission'] += '- ' + name + ':' + value
                        data['app_mission_salary'] += ' ' + name + ' với mức lương thỏa thuận: ' + str(salary) + ' đồng/tháng'
            
            
            data['app_change_salary'] = True
            if not data['app_mission_salary'] and not data['app_gross_salary']:
                data['app_change_salary'] = False
            
            file_name = 'Appendix Contract_' + data.get('name') + '_' + data.get('emp_name')
            
            data.update({'nearest_gross_salary': 0,
                         'nearest_basic_salary': 0,
                         'nearest_general_allowance':0,
                         'nearest_v_bonus_salary': 0})
            
            salary_ids = salary_obj.search(cr, uid, [('effect_from','<',data['app_date_start']),
                                                            ('employee_id','=',emp_id),
                                                            ('company_id','=',com_id)], order='effect_from desc', limit=1)
            if salary_ids:
                salary = salary_obj.read(cr, uid, salary_ids[0], ['gross_salary','basic_salary','general_allowance','v_bonus_salary'])
                data['nearest_gross_salary'] = salary.get('gross_salary',0)
                data['nearest_basic_salary'] = salary.get('basic_salary',0)
                data['nearest_general_allowance'] = salary.get('general_allowance',0)
                data['nearest_v_bonus_salary'] = salary.get('v_bonus_salary',0)
                
            
            parse_condition = True
            #Phu luc HD KTV TP
            if appendix_type_code == 'ACT-001':
                report_name = 'appendix_contract_ktv_tp_report'
            elif appendix_type_code == 'ACT-002':
                #Phu luc HD KTV Tinh
                report_name = 'appendix_contract_ktv_tinh_report'
            elif appendix_type_code == 'ACT-003':
                #Phu luc HD QL KTV TP
                report_name = 'appendix_contract_ql_ktv_report'
            
            elif appendix_type_code == 'ACT-004':
                #Phu luc HD KTV HV Tp
                report_name = 'appendix_contract_ktv_hv_tp_report'
            
            elif appendix_type_code == 'ACT-005':
                #Phu luc HD KTV HV Tinh
                report_name = 'appendix_contract_ktv_hv_tinh_report'
            elif appendix_type_code == 'ACT-006':
                #Phu luc HD gia han
                report_name = 'appendix_contract_extension'
#                 parse_condition = True
            
            elif appendix_type_code in ['ACT-007','ACT-008']:
                #Phu luc HD gia han va thay doi noi dung
                report_name = 'appendix_contract_extension_and_change_info'
            
            elif appendix_type_code in ['ACT-009']:
                #Phụ lục cho kỳ thay đổi hệ thống chức danh, cách tính lương
                report_name = 'appendix_contract_salary_review'
                
            if context.get('force_report_name', False):
                report_name = context.get('force_report_name', False)
            
            
            datas = {
            'ids': ids,
            'model': 'vhr.appendix.contract',
            'form': data,
            'parse_condition': parse_condition
            }
            
            res =  {
                'type': 'ir.actions.report.xml',
                'report_name': report_name,
                'datas': datas,
                'name': file_name
            }
            
            
            return res
    
    def action_print_multi_merge_appendix_contract(self, cr, uid, ids, context=None):
        res = {}
        list_data = []
        for record_id in ids:
            res = self.print_appendix_contract(cr, uid, [record_id], context)
            datas = res.get('datas', False)
            if datas:
                data = datas.get('form')
                if isinstance(data, dict):
                    list_data.append({'report.'+ res['report_name'] : data})
                else:
                    list_data.extend(data)
        
        res['datas'] = {
                     'ids': ids,
                     'model': 'vhr.appendix.contract',
                     'form': list_data,
                     'merge_multi_report': True
                     
                     }
        
        return res


vhr_appendix_contract()