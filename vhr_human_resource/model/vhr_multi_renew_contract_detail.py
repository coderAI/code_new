# -*-coding:utf-8-*-
from openerp.osv import osv, fields
from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.addons.vhr_common.model.vhr_common import vhr_common
from vhr_multi_renew_contract import STATES_ALL
from openerp import SUPERUSER_ID

class vhr_multi_renew_contract_detail(osv.osv, vhr_common):
    _name = 'vhr.multi.renew.contract.detail'
    _description = 'Duplicate Last Contract To Renew Contract'

    def default_get(self, cr, uid, flds, context=None):
        if not context:
            context = {}
        contract_obj = self.pool.get('hr.contract')
        emp_inst_obj = self.pool.get('vhr.employee.instance')
        wkr_obj = self.pool.get('vhr.working.record')
        config_obj = self.pool.get('ir.config_parameter')
#         change_form_obj = self.pool.get('vhr.change.form')
        if context is None:
            context = {}
        res = super(vhr_multi_renew_contract_detail, self).default_get(cr, uid, flds, context=context)
        if res.get('contract_id', False):
            contract_id = res['contract_id']
            res_contract = contract_obj.browse(cr, uid, contract_id, fields_process=['employee_id','company_id','name','type_id',
                                                                                     'date_start','date_end','liquidation_date',
                                                                                     'liquidation_reason'],context=context)
            if res_contract:
                emp_id = res_contract.employee_id and res_contract.employee_id.id or None
                company_id = res_contract.company_id and res_contract.company_id.id or None
                res['contract_name'] = res_contract.name
                res['employee_id'] = emp_id
                res['company_id'] = company_id
#                 res['type_id'] = res_contract.type_id and res_contract.type_id.id or None
                res['type_name'] = res_contract.type_id and res_contract.type_id.name or ''
                
                res['employee_code'] = res_contract.employee_id and res_contract.employee_id.code or None
                res['date_start'] = res_contract.date_start or None
#                 res['date_end'] = res_contract.date_end or None
#                 res['liquidation_date'] = res_contract.liquidation_date or None
#                 res['liquidation_reason'] = res_contract.liquidation_reason or None
#                 res['is_terminated'] = False
#                 code = config_obj.get_param(cr, uid, 'vhr_master_data_dismiss_change_form_code')
                #Assign is_terminated base on change_form of old contract
#                 change_form_ids = change_form_obj.search(cr, uid, [('code', '=', code)], context=context)
#                 if res['liquidation_date']:
#                     wkr_ids = wkr_obj.search(cr, uid, [
#                         ('effect_from', '=', res['liquidation_date']),
#                         ('contract_id', '=', contract_id)], context=context)
#                     for item in wkr_obj.read(cr, uid, wkr_ids, ['change_form_ids'], context=context):
#                         if change_form_ids and set(change_form_ids).issubset(item['change_form_ids']):
#                             res['is_terminated'] = True

                active_instance_ids = emp_inst_obj.search(cr, uid, [
                    ('employee_id', '=', emp_id), ('company_id', '=', company_id), ('date_end', '=', False)])
#                 date_end = False
#                 date_start = False
                is_on_probation = False
                inst_start_date = False
                if active_instance_ids:
                    emp_inst = emp_inst_obj.read(cr, uid, active_instance_ids[0], ['date_start'],context=context)
                    inst_start_date = emp_inst.get('date_start',False)
#                     contract_ids = contract_obj.search(cr, uid, [
#                         ('date_start', '>=', inst_start_date), ('state', '=', 'signed'),
#                         ('employee_id', '=', emp_id), ('company_id', '=', company_id),
#                     ], order='date_start desc,id desc', context=context)
#                     if contract_ids:
#                         last_contract = contract_obj.read(cr, uid, contract_ids[0], ['date_end', 'liquidation_date'])
                if res_contract.liquidation_date:
                    date_end = res_contract.liquidation_date
                    
                else:
                    date_end = res_contract.date_end
#               
                res['date_end'] = date_end
                
                #If have liquidation date, next contract can start from liquidation_date
                if res_contract.liquidation_date:
                    date_end = datetime.strptime(date_end, DEFAULT_SERVER_DATE_FORMAT) - relativedelta(days=1)
                    date_end = date_end.strftime(DEFAULT_SERVER_DATE_FORMAT)
                    
                if date_end:
                    date_start = datetime.strptime(date_end, DEFAULT_SERVER_DATE_FORMAT) + relativedelta(days=1)
                    date_start = date_start.strftime(DEFAULT_SERVER_DATE_FORMAT)
                    res['new_date_start'] = date_start

                if emp_id and company_id:
                    value = contract_obj.check_contract_type(cr, uid, [], emp_id, company_id, context=context)
                    res['list_contract_type_id'] = contract_obj.get_list_contract_type_id(cr, uid, value, context=context)
                    
                    
                    res['new_type_id'] = res_contract.type_id and res_contract.type_id.id or False
                    #Case can only choose infinite contract
                    if res['new_type_id'] not in res['list_contract_type_id']:
                        res['new_type_id'] = res['list_contract_type_id'] and res['list_contract_type_id'][0]
                    
                    if res['new_type_id']:
                        res['new_date_end'] = contract_obj.get_date_end_and_life_of_contract(cr, uid, [], res['new_type_id'], res['new_date_start']).get('date_end',False)
                if emp_id and company_id and active_instance_ids:
                    is_on_probation = contract_obj.check_last_contract_type_is_offer(cr, uid, [], emp_id, company_id, inst_start_date, date_start, context=context)
                res['is_on_probation'] = is_on_probation
                if is_on_probation:
                    res['include_probation'] = True
                    data = contract_obj.onchange_include_probation(cr, uid, [], True, emp_id, company_id, res['new_type_id'], context=context)
                    if data.get('value', False):
                        res.update({'new_date_start': data['value'].get('date_start', ''),
                                     'new_date_start_temp':data['value'].get('date_start_temp',False),
                                     'new_date_end': data['value'].get('date_end', False)
                                     })
                        
                res['renew_status'] = 'renew'

        return res

    def _get_list_contract_appendix_type(self, cr, uid, ids, field_name, arg, context=None):
        contract_obj = self.pool.get('hr.contract')
        res = {}
        for item in self.browse(cr, SUPERUSER_ID, ids):
            res[item.id] = {'list_contract_type_id': False, 'list_appendix_type_id': False}
            if item.employee_id and item.company_id:
                value = contract_obj.check_contract_type(cr, SUPERUSER_ID, [], item.employee_id.id, item.company_id.id, context=context)
                res[item.id]['list_contract_type_id'] = contract_obj.get_list_contract_type_id(cr, uid, value, context=context)
            
            if item.contract_id and item.contract_id.type_id.life_of_contract:
                life_of_contract = item.contract_id.type_id.life_of_contract
                code_list = []
                if life_of_contract == 12:
                    code_list = ['appendix_1_year','appendix_2_year']
                elif life_of_contract == 24:
                    code_list = ['appendix_1_year']
                
                dimension_type_ids = self.pool.get('vhr.dimension.type').search(cr, uid, [('code','=','TYPE_OF_EXTEND_APPENDIX_CONTRACT')])
                domain = [('code','in',code_list),
                          ('dimension_type_id','in',dimension_type_ids),
                          ('active','=', True)]
                res[item.id]['list_appendix_type_id'] = self.pool.get('vhr.dimension').search(cr, uid, domain)
                
        print 'res=',res
        return res
    
    
    def _get_correct_date_format(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if not isinstance(ids, list):
            ids = [ids]
        
        records = self.read(cr, uid, ids, ['date_start','date_end'])
        for record in records:
            res[record['id']] = {'correct_date_start': '','correct_date_end': ''}
            
            if record.get('date_start'):
                date_approve = datetime.strptime(record['date_start'], DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y")
                res[record['id']]['correct_date_start'] = date_approve
            if record.get('date_end'):
                date_expect = datetime.strptime(record['date_end'], DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y")
                res[record['id']]['correct_date_end'] = date_expect
        return res
    
    def _get_remain_day_for_renew(self, cr, uid, ids, field_name, arg, context=None):
        '''
        Công thức tính Remained day for contract renewal:
                NVCT: Expired date – Today – 15
                CTV: Expired date – Today – 7 
        '''
        res = {}
        if not isinstance(ids, list):
            ids = [ids]
        
        records = self.read(cr, uid, ids, ['date_end','is_collaborator'])
        today = datetime.today().date().strftime(DEFAULT_SERVER_DATE_FORMAT)
        for record in records:
            date_end_contract = record.get('date_end',False)
            is_collaborator = record.get('is_collaborator',False)
            gap = 0
            if date_end_contract:
                gap = self.compare_day(today, date_end_contract)
                if not is_collaborator:
                    gap = gap - 15
                else:
                    gap = gap - 7
                if gap < 0 :
                    gap = -1
            res[record['id']] = gap
        
        return res
    
    def _get_update_detail(self, cr, uid, ids, context=None):
        return ids

    def _get_number_of_signed_contract(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        instance_obj = self.pool.get('vhr.employee.instance')
        contract_obj = self.pool.get('hr.contract')
        type_obj = self.pool.get('hr.contract.type')
        
        except_type_ids = []
        probation_type_group_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_human_resource_probation_contract_type_group_code') or ''
        if probation_type_group_code:
            group_ids = self.pool.get('hr.contract.type.group').search(cr, uid, [('code','=',probation_type_group_code)])
            if group_ids:
                except_type_ids = type_obj.search(cr, uid, [('contract_type_group_id','in', group_ids)])
                
        for record in self.read(cr, uid, ids, ['employee_id','date_start','type_id','company_id']):
            res[record['id']] = 0
            date_start = record.get('date_start', False)
            employee_id = record.get('employee_id', False) and record['employee_id'][0]
            company_id = record.get('company_id', False) and record['company_id'][0]
            type_id = record.get('type_id', False) and record['type_id'][0]
            if type_id:
                type = self.pool.get('hr.contract.type').browse(cr, uid, type_id, fields_process=['contract_type_group_id'])
                is_official = type.contract_type_group_id and type.contract_type_group_id.is_offical
                if is_official:
                    instance_ids = instance_obj.search(cr, uid, [('employee_id','=',employee_id),
                                                                 ('company_id','=',company_id),
                                                                 ('date_end','=',False),
                                                                 ('date_start','<=',date_start)
                                                                 ], order='date_start desc')
                    if instance_ids:
                        instance  = instance_obj.read(cr, uid, instance_ids[0], ['date_start'])
                        date_start_ins = instance.get('date_start', False)
                        ct_ids = contract_obj.search(cr, uid, [('employee_id','=', employee_id),
                                                              ('company_id','=', company_id),
                                                              ('state','=','signed'),
                                                              ('date_start','>=',date_start_ins),
                                                              ('date_start','<=',date_start),
                                                              ('type_id','not in',except_type_ids)])
                        
                        res[record['id']] = len(ct_ids)
        
        return res
    
    def _get_link_to_detail(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        
        for record in self.read(cr, uid, ids, ['multi_renew_id']):
            res[record['id']] = ''
            multi_renew_id = record.get('multi_renew_id', False) and record['multi_renew_id'][0] or False
            res[record['id']] = self.get_url(cr, uid, multi_renew_id, context)
        
        return res
    
    def _get_new_type_contract_name(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for record in self.read(cr, uid, ids, ['new_type_id','appendix_type_id']):
            appendix_type_id = record.get('appendix_type_id', False) and record['appendix_type_id'][1] or ''
            new_type_id = record.get('new_type_id', False) and record['new_type_id'][1] or ''
            res[record['id']] = appendix_type_id or new_type_id
        
        return res
    
    def _get_correct_date_end_incase_has_appendix(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for record in self.browse(cr, uid, ids):
            res[record['id']] = record.contract_id and (record.contract_id.date_end_temp or record.contract_id.date_end) or False
        return res
        

    _columns = {
#         'date_request': fields.date('Date Request'),
        'name': fields.char('Name'),
        'contract_id': fields.many2one('hr.contract', 'Contract'),
        'contract_name': fields.char('Contract'),
        'employee_id': fields.related('contract_id', 'employee_id', type='many2one', relation='hr.employee', string="Employee"),
        'company_id': fields.related('contract_id', 'company_id', type='many2one', relation='res.company', string="Company"),
        'employee_code': fields.related('employee_id', 'code', type='char', string='Employee Code'),
        'report_to': fields.related('employee_id', 'report_to', type='many2one', relation='hr.employee', string="Report To"),
        'type_id': fields.related('contract_id', 'type_id', type='many2one', relation='hr.contract.type', string="Term of contract"),
        'title_id': fields.related('contract_id', 'title_id', type='many2one', relation='vhr.job.title', string="Job Title"),
        'type_name': fields.char('Contract Type'),
        'date_start': fields.related('contract_id', 'date_start', type='date', string="Effective Date"),
        'date_end': fields.related('contract_id', 'date_end', type='date', string="Expired Date"),
        'date_end_temp_func': fields.function(_get_correct_date_end_incase_has_appendix, type='date', string='Expired Date'),
#         'liquidation_date': fields.date('Liquidation Date'),
#         'liquidation_reason': fields.text('Reason'),
        'new_type_id': fields.many2one('hr.contract.type', 'Contract Type'),
        'new_date_start': fields.date('Effective Date'),
        'new_date_start_temp': fields.date('Effective Date'),
        'new_date_end': fields.date('Expired Date'),
        'list_contract_type_id': fields.function(_get_list_contract_appendix_type, type='char', string='List Contract Type',multi='get_list_ct_ap'),
        'list_appendix_type_id': fields.function(_get_list_contract_appendix_type, type='char', string='List Appendix Type', multi='get_list_ct_ap'),
        'include_probation': fields.boolean('Include Probation'),
#         'is_on_probation': fields.boolean('Is on probation'),
#         'is_terminated': fields.boolean('Is Terminated'),
        'multi_renew_id': fields.many2one('vhr.multi.renew.contract', 'Multi Renew Contract', ondelete='cascade'),
        'renew_status': fields.selection([('renew', 'Renew'), ('reject', 'Reject'), ('pending', 'Pending')], 'Renew Status'),
        
        'correct_date_start': fields.function(_get_correct_date_format, type='date', string='Correct Approved last working date', multi='get_correct_date'),
        'correct_date_end': fields.function(_get_correct_date_format, type='date', string='Correct Expected last working date', multi='get_correct_date'),
        'remain_day_for_renew': fields.function(_get_remain_day_for_renew, type='integer', string='Remained Day For Renewal'),
        'state': fields.selection(STATES_ALL, 'Status', readonly=True),
        'performance': fields.text('Performance'),
        'behavior_core_value': fields.text('Behavior/ 6 core values'),
        'is_collaborator': fields.boolean('Is Collaborator'),
        'new_contract_id': fields.many2one('hr.contract', 'Contract'),
        
        'new_appendix_contract_id': fields.many2one('vhr.appendix.contract', 'Appendix Contract'),
        
        'appendix_type_id':fields.many2one('vhr.dimension','Appendix Type',
                                                  domain=[('dimension_type_id.code','=', 'TYPE_OF_EXTEND_APPENDIX_CONTRACT')]),
        
        'number_of_signed': fields.function(_get_number_of_signed_contract, type='integer', string='Number of Signed Contract', 
                                                            store={'vhr.multi.renew.contract.detail':
                                                               (_get_update_detail,
                                                                ['type_name','performance'], 10)}),
        'link': fields.function(_get_link_to_detail, type='char',string="URL Link"),
        'new_type_contract_name': fields.function(_get_new_type_contract_name, type='char', string='New Type'),
        
        'request_state':fields.related('multi_renew_id', 'state', type='selection', selection=STATES_ALL, string="Request State"),
    }

    _defaults = {
        'renew_status': 'renew'
    }

    def on_change_new_info(self, cr, uid, ids, type_id, date_start, context=None):
        res = {'value': {}}
        contract_obj = self.pool.get('hr.contract')
        if type_id and date_start:
            res['value']['appendix_type_id'] = False
            data = contract_obj.get_date_end_and_life_of_contract(cr, uid, [], type_id, date_start, context)
            date_end = data.get('date_end', False)
            res['value'].update({'new_date_end': date_end})

        return res
    
    def on_change_appendix_new_info(self, cr, uid, ids, appendix_type_id, date_start, context=None):
        res = {'value': {}}
        if appendix_type_id:
            res['value']['new_type_id'] = False
            
            appendix_type = self.pool.get('vhr.dimension').read(cr, uid, appendix_type_id, ['code'])
            appendix_code = appendix_type.get('code', False)
            new_life = 0
            if appendix_code == 'appendix_1_year':
                new_life = 12
            elif appendix_code == 'appendix_2_year':
                new_life = 24
            
            date_start = datetime.strptime(date_start, DEFAULT_SERVER_DATE_FORMAT).date()
            date_end = date_start + relativedelta(months=new_life) - relativedelta(days=1)
            date_end = date_end.strftime(DEFAULT_SERVER_DATE_FORMAT)
            res['value'].update({'new_date_end': date_end})
        
        return res

    def onchange_liquidation(self, cr, uid, ids, date_start, date_end, liquidation, context=None):
        contract_obj = self.pool.get('hr.contract')
        res = contract_obj.onchange_liquidation(cr, uid, [], date_start, date_end, liquidation, context=context)
        return res

    def onchange_include_probation(self, cr, uid, ids, include_probation, employee_id, company_id, type_id, context=None):
        res = {'value': {}}
        contract_obj = self.pool.get('hr.contract')
        data = contract_obj.onchange_include_probation(cr, uid, ids, include_probation, employee_id, company_id, type_id, context=context)
        if data.get('value', False):
            res['value'].update({'new_date_start': data['value'].get('date_start', ''),
                                 'new_date_end': data['value'].get('date_end', ''),
                                 'new_date_start_temp': data['value'].get('date_start_temp','')
                                 })

        return res

    def on_change_status(self, cr, uid, ids, status, context=None):
        res = {'value': {}}
        if status and status in ['refused', 'waiting']:
            res['value'].update({'new_date_start': '', 'new_date_end': '', 'new_type_id': None})

        return res
    
    
    def btn_go_to_new_contract(self, cr, uid, ids, context=None):
        if ids:
            if not isinstance(ids, list):
                ids = [ids]
                
            record = self.read(cr, uid, ids[0], ['new_contract_id','new_appendix_contract_id'])
            new_contract_id = record.get('new_contract_id',False) and record['new_contract_id'][0] or False
            new_appendix_contract_id = record.get('new_appendix_contract_id',False) and record['new_appendix_contract_id'][0] or False
            
            mod_obj = self.pool.get('ir.model.data')
            act_obj = self.pool.get('ir.actions.act_window')
            
            if new_contract_id:
                result = mod_obj.get_object_reference(cr, uid, 'hr_contract', 'action_hr_contract')
                id = result and result[1] or False
                result = act_obj.read(cr, uid, [id], context=context)[0]
                
                result['res_id'] = new_contract_id
            elif new_appendix_contract_id:
                result = mod_obj.get_object_reference(cr, uid, 'vhr_human_resource', 'act_vhr_appendix_contract')
                id = result and result[1] or False
                result = act_obj.read(cr, uid, [id], context=context)[0]
                
                result['res_id'] = new_appendix_contract_id
                
            result['view_type'] = 'form'
            result['view_mode'] = 'form,tree'
            result['views'].sort()
            return result
        
        return True
    
    def get_url(self, cr, uid, res_id, context=None):
        """
        res_id: Id of Multi Renew Contract
        """
        if not context:
            context = {}
        if isinstance(res_id, list):
            res_id = res_id[0]
        model_data = self.pool.get('ir.model.data')
        parameter_obj = self.pool.get('ir.config_parameter')
        base_url = parameter_obj.get_param(cr, uid, 'web.base.url')
        xml_id = 'vhr_human_resource.action_multi_renew_official_contract'
        
        multi = self.pool.get('vhr.multi.renew.contract').read(cr, uid, res_id, ['is_probation','is_collaborator'])
        if multi.get('is_probation', False):
            xml_id = 'vhr_human_resource.action_multi_renew_probation_contract'
        elif multi.get('is_collaborator', False):
            xml_id = 'vhr_human_resource.action_multi_renew_collaborator_contract'
        
        action_id = model_data.xmlid_lookup(cr, uid, xml_id)[2]
        url = '/web#id=%s&view_type=form&model=vhr.multi.renew.contract&action=%s' % (res_id, action_id)
        return url
    


vhr_multi_renew_contract_detail()