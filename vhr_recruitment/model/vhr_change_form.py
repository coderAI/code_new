# -*-coding:utf-8-*-
import logging
from openerp.osv import osv, fields

log = logging.getLogger(__name__)


class vhr_change_form(osv.osv):
    _inherit = 'vhr.change.form'
    _description = 'Change Form'
    

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if not context:
            context = {}
        
        config_parameter = self.pool.get('ir.config_parameter')
        
        #If contract transfer from RR, dont show change form chuyen doi cong ty
        if context.get('job_applicant_id', False):
            config_parameter = self.pool.get('ir.config_parameter')
            change_local_comp_code = config_parameter.get_param(cr, uid, 'vhr_master_data_change_local_company') or ''
            change_local_comp_code_list = change_local_comp_code.split(',')
            remove_ids = self.search(cr, uid, [('code','in',change_local_comp_code_list)])
            args.append(('id','not in',remove_ids))
        
        #Only show type back to work or change type of contract in form transfer from rr to cb when check ex_employee
        if context.get('filter_change_form_id_show_in_transfer_rr', False):
            input_code = config_parameter.get_param(cr, uid, 'vhr_master_data_input_data_into_iHRP') or ''
            input_code_list = input_code.split(',')
            
            back_code = config_parameter.get_param(cr, uid, 'vhr_master_data_back_to_work_change_form_code') or ''
            back_code_list = back_code.split(',')
            
            change_type_code = config_parameter.get_param(cr, uid, 'vhr_master_data_change_type_of_contract')
            change_type_code_list = change_type_code.split(',')
            
            code_list = input_code_list + back_code_list + change_type_code_list
            
            remove_ids = self.search(cr, uid, [('code','in',code_list)])
            args.append(('id','in',remove_ids))
            
        return super(vhr_change_form, self).search(cr, uid, args, offset, limit, order, context, count)

vhr_change_form()
