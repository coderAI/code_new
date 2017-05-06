# -*-coding:utf-8-*-
from openerp.osv import osv, fields
from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT

class vhr_renew_contract(osv.osv_memory):

    def default_get(self, cr, uid, flds, context=None):
        contract_obj = self.pool.get('hr.contract')
        emp_inst_obj = self.pool.get('vhr.employee.instance')
        wkr_obj = self.pool.get('vhr.working.record')
        config_obj = self.pool.get('ir.config_parameter')
        change_form_obj = self.pool.get('vhr.change.form')
        if context is None:
            context = {}
        res = super(vhr_renew_contract, self).default_get(cr, uid, flds, context=context)
        if res.get('contract_id', False):
            contract_id = res['contract_id']
            res_contract = contract_obj.browse(cr, uid, contract_id, context=context)
            if res_contract:
                emp_id = res_contract.employee_id and res_contract.employee_id.id or None
                company_id = res_contract.company_id and res_contract.company_id.id or None
                res['employee_id'] = emp_id
                res['company_id'] = company_id
                res['new_company_id'] = company_id
                res['type_id'] = res_contract.type_id and res_contract.type_id.id or None
                res['employee_code'] = res_contract.employee_id and res_contract.employee_id.code or None
                res['date_start'] = res_contract.date_start or None
                res['date_end'] = res_contract.date_end or None
                res['liquidation_date'] = res_contract.liquidation_date or None
                res['liquidation_reason'] = res_contract.liquidation_reason or None
                res['is_terminated'] = False
                code = config_obj.get_param(cr, uid, 'vhr_master_data_dismiss_change_form_code') or ''
                change_form_ids = change_form_obj.search(cr, uid, [('code', '=', code)], context=context)
                if res['liquidation_date']:
                    wkr_ids = wkr_obj.search(cr, uid, [('effect_from', '=', res['liquidation_date']),
                                                       ('contract_id', '=', contract_id),
                                                       ('state','in',['finish',False])], context=context)
                    for item in wkr_obj.read(cr, uid, wkr_ids, ['change_form_ids'], context=context):
                        if change_form_ids and set(change_form_ids).issubset(item['change_form_ids']):
                            res['is_terminated'] = True

                active_instance_ids = emp_inst_obj.search(cr, uid, [
                    ('employee_id', '=', emp_id), ('company_id', '=', company_id), ('date_end', '=', False)])
                date_end = False
                date_start = False
                is_on_probation = False
                inst_start_date = False
                if active_instance_ids:
                    emp_inst = emp_inst_obj.browse(cr, uid, active_instance_ids[0], context=context)
                    inst_start_date = emp_inst.date_start
                    contract_ids = contract_obj.search(cr, uid, [
                        ('date_start', '>=', inst_start_date), ('state', '=', 'signed'),
                        ('employee_id', '=', emp_id), ('company_id', '=', company_id),
                    ], order='date_start desc,id desc', context=context)
                    if contract_ids:
                        last_contract = contract_obj.browse(cr, uid, contract_ids[0], fields_process=['date_end', 'liquidation_date'])
                        if last_contract.liquidation_date:
                            date_end = last_contract.liquidation_date
                            
                            #If have liquidation date, next contract can start from liquidation_date
                            date_end = datetime.strptime(date_end, DEFAULT_SERVER_DATE_FORMAT) - relativedelta(days=1)
                            date_end = date_end.strftime(DEFAULT_SERVER_DATE_FORMAT)
                        else:
                            date_end = last_contract.date_end
                else:
                    #If employee dont have any instance with date_end=False, use date_end from contract to renew
                    date_end = res_contract.liquidation_date or res_contract.date_end or False

                if date_end:
                    date_start = datetime.strptime(date_end, DEFAULT_SERVER_DATE_FORMAT) + relativedelta(days=1)
                    date_start = date_start.strftime(DEFAULT_SERVER_DATE_FORMAT)
                    res['new_date_start'] = date_start

                if emp_id and company_id:
                    value = contract_obj.check_contract_type(cr, uid, [], emp_id, company_id, context=context)
                    res['list_contract_type_id'] = contract_obj.get_list_contract_type_id(cr, uid, value, context=context)
                if emp_id and company_id and active_instance_ids:
                    is_on_probation = contract_obj.check_last_contract_type_is_offer(cr, uid, [], emp_id, company_id, inst_start_date, date_start, context=context)
                res['is_on_probation'] = is_on_probation
                if is_on_probation:
                    res['include_probation'] = True
                res['renew_status'] = 'renew'

        return res

    def _get_list_contract_type(self, cr, uid, ids, field_name, arg, context=None):
        contract_obj = self.pool.get('hr.contract')
        res = {}
        for item in self.browse(cr, uid, ids):
            res[item.id] = False
            if item.employee_id and item.company_id:
                value = contract_obj.check_contract_type(cr, uid, [], item.employee_id.id, item.company_id.id, context=context)
                res[item.id] = contract_obj.get_list_contract_type_id(cr, uid, value, context=context)

        return res

    _name = 'vhr.renew.contract'
    _description = 'Duplicate Last Contract To Renew Contract'

    _columns = {
        'contract_id': fields.many2one('hr.contract', 'Contract'),
        'employee_id': fields.related('contract_id', 'employee_id', type='many2one', relation='hr.employee', string="Employee"),
        'company_id': fields.related('contract_id', 'company_id', type='many2one', relation='res.company', string="Company"),
        'employee_code': fields.related('employee_id', 'code', type='char', string='Employee Code'),
        'type_id': fields.related('contract_id', 'type_id', type='many2one', relation='hr.contract.type', string="Contract Type"),
        'date_start': fields.related('contract_id', 'date_start', type='date', string="Effective Date"),
        'date_end': fields.related('contract_id', 'date_end', type='date', string="Exxpired Date"),
        'liquidation_date': fields.date('Liquidation Date'),
        'liquidation_reason': fields.text('Reason'),
        
        'new_company_id': fields.many2one('res.company', 'Company'),
        'new_type_id': fields.many2one('hr.contract.type', 'Contract Type'),
        'new_date_start': fields.date('Effective Date'),
        'new_date_end': fields.date('Expired Date'),
        'new_date_start_temp': fields.date('Effective Date Temp'),
        'list_contract_type_id': fields.function(_get_list_contract_type, type='char', string='List Contract Type'),
        'include_probation': fields.boolean('Include Probation'),
        'is_on_probation': fields.boolean('Is on probation'),
        'is_terminated': fields.boolean('Is Terminated'),
        'multi_renew_id': fields.many2one('vhr.multi.renew.contract', 'Multi Renew', ondelete='cascade'),
        'renew_status': fields.selection([('renew', 'Renew'), ('reject', 'Reject'), ('pending', 'Pending')], 'Renew Status'),
    }

    _defaults = {
        'renew_status': 'renew',
    }

    def on_change_new_info(self, cr, uid, ids, type_id, date_start, new_date_start_temp, context=None):
        res = {'value': {}}
        contract_obj = self.pool.get('hr.contract')
        if type_id and date_start:
            date_compare = date_start
#             if new_date_start_temp:
#                 date_compare = new_date_start_temp
            data = contract_obj.get_date_end_and_life_of_contract(cr, uid, [], type_id, date_start, context)
            date_end = data.get('date_end', False)
            res['value'].update({'new_date_end': date_end})

        return res

    def onchange_liquidation(self, cr, uid, ids, date_start, date_end, liquidation, context=None):
        contract_obj = self.pool.get('hr.contract')
        res = contract_obj.onchange_liquidation(cr, uid, [], date_start, date_end, liquidation, context=context)
        
        if not res.get('warning', False):
            liquidation_date = res['value'].get('liquidation_date', liquidation)
            if liquidation_date:
                new_date_start = datetime.strptime(liquidation_date, DEFAULT_SERVER_DATE_FORMAT) #+ relativedelta(days=1)
                new_date_start = new_date_start.strftime(DEFAULT_SERVER_DATE_FORMAT)
                res['value']['new_date_start'] = new_date_start
        return res

    def onchange_include_probation(self, cr, uid, ids, include_probation, employee_id, company_id, new_type_id, context=None):
        res = {'value': {}}
        contract_obj = self.pool.get('hr.contract')
        data = contract_obj.onchange_include_probation(cr, uid, ids, include_probation, employee_id, company_id, new_type_id, context=context)
        if data.get('value', False):
            res['value'].update({'new_date_start': data['value'].get('date_start', ''),'new_date_start_temp':data['value'].get('date_start_temp',False)})

        return res
    
    def onchange_new_company_id(self, cr, uid, ids, employee_id, company_id, new_company_id, context=None):
        res = {}
        if employee_id and company_id and new_company_id:
            if company_id == new_company_id:
                contract_obj = self.pool.get('hr.contract')
                value = contract_obj.check_contract_type(cr, uid, [], employee_id, company_id, context=context)
                res['list_contract_type_id'] = contract_obj.get_list_contract_type_id(cr, uid, value, context=context)
            else:
                res['list_contract_type_id'] = self.pool.get('hr.contract.type').search(cr, uid, [])
        
        return {'value': res}
    
    def action_renew_hr_contract(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        
        #Dont allow to renew in same company if old type is HDLD Khong Xac Dinh Thoi Han and dont have liquidation date
        if context.get('old_company_id', False) == context.get('new_company_id', False):
            type_id = context.get('old_type_id', False)
            if type_id:
                type = self.pool.get('hr.contract.type').read(cr, uid, type_id, ['code'])
                contract_type_code = type.get('code',False)
                if contract_type_code == '7' and not context.get('liquidation_date', False):
                    raise osv.except_osv('Validation Error !', "You can't renew contract when current contract is indefinite !")
        
        return  {
                'name': 'Contract',
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': self.pool.get('ir.model.data').get_object_reference(cr, uid, 'vhr_human_resource', 'view_hr_contract_form')[1],
                'res_model': 'hr.contract',
                'context': {'duplicate_active_id': context.get('contract_id', False),
                             'default_company_id': context.get('new_company_id', False),
                             'default_type_id': context.get('type_id', False),
                             'renew_status': 'renew',
                             'default_include_probation': context.get('include_probation', False),
                             'default_date_start': context.get('date_start', False),
                             'liquidation_date':context.get('liquidation_date',False),
                             'liquidation_reason':context.get('liquidation_reason',False),
                             'default_new_date_start_temp': context.get('new_date_start_temp', False),
                             'create_directly_from_contract': True
                            },
                'type': 'ir.actions.act_window',
            }
                    

#     def on_change_status(self, cr, uid, ids, status, context=None):
#         res = {'value': {}}
#         if status and status in ['refused', 'waiting']:
#             res['value'].update({'new_date_start': '', 'new_date_end': '', 'new_type_id': None})
# 
#         return res


vhr_renew_contract()