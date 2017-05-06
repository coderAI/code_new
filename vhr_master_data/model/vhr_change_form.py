# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields


log = logging.getLogger(__name__)


class vhr_change_form(osv.osv):
    _name = 'vhr.change.form'
    _description = 'VHR Change Form'

    _columns = {
        'code': fields.char('Code', size=64),
        'name': fields.char('Vietnamese Name', size=128),
        'name_en': fields.char('English Name', size=128),
        'change_form_type_id': fields.many2one('vhr.change.form.type', 'Change Form Type', ondelete='restrict'),
        'sign_emp_id': fields.many2one('hr.employee', 'Signer', ondelete='restrict'),
        'job_title_id': fields.many2one('vhr.job.title', "Signer's Title", ondelete='restrict'),
        'email_type_id': fields.many2one('vhr.dimension', 'Email Type', ondelete='restrict',
                                         domain=[('dimension_type_id.code', '=', 'EMAIL_TYPE'), ('active', '=', True)]),
        # TODO: Check useage later
        'show_qltv_admin': fields.boolean('Show In Working Record (Dept Admin)'),
        'show_qltv_af_admin': fields.boolean('Show In Working Record (AF Admin)'),
        'show_qltv_hrbp': fields.boolean('Show In Working Record (HRBP)'),
        'show_hr_rotate': fields.boolean('Show In Staff Movement'),
        'show_in_contract': fields.boolean('Show In Contract'),

        'is_salary_adjustment': fields.boolean('Salary Adjustments'),
#         'show_in_termination_request': fields.boolean('Show in Termination Request'),

        'access_field_ids': fields.many2many('ir.model.fields', 'change_form_working_field','change_form_id','field_id','Fields',
                                                   domain=[('model_id.model', '=', 'vhr.working.record'),('name','like','new')]),
        'description': fields.text('Description'),
        'active': fields.boolean('Active'),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                         domain=[('object_id.model', '=', _name),
                                                 ('field_id.name', 'not in',
                                                  ['write_date', 'audit_log_ids'])]),
    }

    _defaults = {
        'show_qltv_admin': True,
        'show_hr_rotate': True,
        'show_in_contract': False,
        'active': True,
    }

    _unique_insensitive_constraints = [{'code': "Change Form's Code is already exist!"},
                                       {'name': "Change Form's Vietnamese Name is already exist!"}]



    # When onchange change_form_type_id get sign_emp_id,job_id
    def onchange_change_form_type_id(self, cr, uid, ids, change_form_type_id, context=None):
        val = {'sign_emp_id': False, 'job_title_id': False}
        if change_form_type_id:
            change_form_type = self.pool.get('vhr.change.form.type').read(cr, uid, change_form_type_id,
                                                                          ['sign_emp_id', 'job_title_id'], context)
            if change_form_type.get('sign_emp_id', False):
                val['sign_emp_id'] = change_form_type['sign_emp_id'][0]
                if change_form_type.get('job_title_id', False):
                    val['job_title_id'] = change_form_type['job_title_id'][0]

        return {'value': val}

    #When onchange sign_emp_id get job_id
    #TODO: wait for field job_title_id in hr.employee
    def onchange_sign_emp_id(self, cr, uid, ids, sign_emp_id, context=None):
        val = {'job_title_id': False}
        if sign_emp_id:
            sign_emp = self.pool.get('hr.employee').read(cr, uid, sign_emp_id, ['title_id'], context)
            if sign_emp.get('title_id', False):
                val['job_title_id'] = sign_emp['title_id'][0]

        return {'value': val}

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        
        args_new = ['|', '|', ('name', operator, name), ('code', operator, name), ('name_en', operator, name)] + args
        ids = self.search(cr, uid, args_new, 0, None, None, context)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(vhr_change_form, self).name_search(cr, uid, name, args, operator, context, limit)

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if not context:
            context = {}

        return super(vhr_change_form, self).search(cr, uid, args, offset, limit, order, context, count)


    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            config_parameter = self.pool.get('ir.config_parameter')
            dismiss_code = config_parameter.get_param(cr, uid, 'vhr_master_data_dismiss_change_form_code') or ''
            dismiss_code_list = dismiss_code.split(',')

            backwork_code = config_parameter.get_param(cr, uid, 'vhr_master_data_back_to_work_change_form_code') or ''
            backwork_code_list = backwork_code.split(',')
            
            change_type_code = config_parameter.get_param(cr, uid, 'vhr_master_data_change_type_of_contract') or ''
            change_type_code_list = change_type_code.split(',')
            
            change_local_comp_code = config_parameter.get_param(cr, uid, 'vhr_master_data_change_local_company') or ''
            change_local_comp_code_list = change_local_comp_code.split(',')
            
            dismiss_local_comp_code = config_parameter.get_param(cr, uid, 'vhr_master_data_dismiss_local_company') or ''
            dismiss_local_comp_code_list = dismiss_local_comp_code.split(',')
            
            illegal_delete_list = dismiss_code_list + backwork_code_list + change_type_code_list + \
                                  change_local_comp_code_list + dismiss_local_comp_code_list

            #Do not allow to delete change form with code from vhr_master_data_dismiss_change_form_code, vhr_master_data_back_to_work_change_form_code
            change_forms = self.read(cr, uid, ids, ['code'])
            for change_form in change_forms:
                if change_form.get('code', False) in illegal_delete_list:
                    raise osv.except_osv('Validation Error !',
                                         'You cannot delete the record(s) which reference to others !')
            res = super(vhr_change_form, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res


vhr_change_form()