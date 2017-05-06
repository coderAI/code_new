# -*-coding:utf-8-*-
from openerp.osv import osv, fields
from openerp.addons.vhr_human_resource.model.vhr_exit_checklist_request import STATES, APPROVE_FIELDS

class vhr_mass_change_state_exit_checklist(osv.osv_memory):
    _name = 'vhr.mass.change.state.exit.checklist'
    _description = 'Mass Change State Exit Checklist'
    
    def _is_able_to_mass_change(self, cr, uid, ids, field_name, arg, context=None):
        """
        Only Cb Termination can mass change
        """
        res = {}
        
        groups = self.pool.get('res.users').get_groups(cr, uid)
        result = 'vhr_cb_termination' in groups
        for record_id in ids:
            res[record_id] = {}
            res[record_id] = result
        return res
    
    _columns = {
                'comment': fields.text('Ghi chú'),
                'is_able_to_mass_change': fields.function(_is_able_to_mass_change, type='boolean', string="Is Able To Mass Change"),
                'is_approve_responsibilities_hand_over': fields.boolean('BÀN GIAO CÔNG VIỆC'),
                'is_approve_administrative_office': fields.boolean(' PHÒNG HÀNH CHÍNH '),
                'is_approve_administrative_office_other': fields.boolean(' PHÒNG HÀNH CHÍNH (OTHER)'),
                'is_approve_it_office': fields.boolean('PHÒNG CÔNG NGHỆ THÔNG TIN'),
                'is_approve_it_office_other': fields.boolean('PHÒNG CÔNG NGHỆ THÔNG TIN (OTHER)'),
                'is_approve_accounting_office': fields.boolean('PHÒNG TÀI CHÍNH & KẾ TOÁN'),
                'is_approve_hr_office_training': fields.boolean('PHÒNG NHÂN SỰ (TRAINING)'),
                'is_approve_hr_office_other': fields.boolean('PHÒNG NHÂN SỰ (OTHER)'),

    }
    
    
    def _get_is_able_to_mass_change(self, cr, uid, context=None):
        if not context:
            context = {}
        
        active_ids = context.get('active_ids', [])
        if len(active_ids) >1:
            raise osv.except_osv('Warning !', u"Bạn chỉ có thể thực hiện chức năng này cho 1 yêu cầu duy nhất !")
        
        record = self.pool.get('vhr.exit.checklist.request').read(cr, uid, active_ids[0], ['state'])
        state = record.get('state',False)
        if state != 'department':
            raise osv.except_osv('Warning !', u"Bạn chỉ có thể thực hiện chức năng này cho yêu cầu đang ở trạng thái Waiting Department!")
        
        groups = self.pool.get('res.users').get_groups(cr, uid)
        result = 'vhr_cb_termination' in groups
        if not result:
            raise osv.except_osv('Warning !', u"Chỉ có C&B Termination mới được quyền thực hiện chức năng này !")
        
        return True

        
    _defaults = {
                 'is_able_to_mass_change': _get_is_able_to_mass_change}
    
    def execute(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        
        if not isinstance(ids, list):
            ids = [ids]
            
        if context.get('active_ids', False) and ids:
            exit_checklist_pool = self.pool.get('vhr.exit.checklist.request')
            active_ids = context.get('active_ids', False)
            record = self.read(cr, uid, ids[0], ['comment']+APPROVE_FIELDS)
            comment = record.get('comment','')
            
            is_empty_change_department = True
            vals = {}
            for field in APPROVE_FIELDS:
                if record.get(field, False) != False:
                    is_empty_change_department = False
                    vals[field] = True
                    
            if is_empty_change_department:
                raise osv.except_osv('Warning !', u"Bạn phải chọn ít nhất một phòng ban để phê duyệt !")
            
            dict_states = {item[0]: item[1] for item in STATES}
            list_state = [item[0] for item in STATES]
            for record_id in active_ids:
                record = exit_checklist_pool.read(cr, uid, record_id, ['state']+APPROVE_FIELDS)
                old_state = record.get('state', False)
                
                continue_to_next_state = True
                for field in APPROVE_FIELDS:
                    if record.get(field, False) or vals.get(field, False):
                        continue
                    else:
                        continue_to_next_state = False
                
                nvals = vals.copy()
                new_state = old_state
                if continue_to_next_state:
                    index_new_state = list_state.index(old_state) + 1
                    nvals['state'] = list_state[index_new_state]
                    new_state = nvals['state']
                    
                exit_checklist_pool.write(cr, uid, record_id, nvals, context)
            
                exit_checklist_pool.write_log_state_change(cr, uid, record_id, dict_states[old_state], dict_states[new_state], {'ACTION_COMMENT':comment})
        
        return {'type': 'ir.actions.act_window_close'}
            
    


vhr_mass_change_state_exit_checklist()