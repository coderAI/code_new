# -*-coding:utf-8-*-
import logging
from openerp.osv import osv, fields
import simplejson as json
from lxml import etree
from vhr_recruitment_constant import RE_MASS_SEND_CV_TO_CONFIRM
from vhr_recruitment_abstract import vhr_recruitment_abstract, ADMIN
    
log = logging.getLogger(__name__)


class vhr_send_multi_cvs(osv.osv_memory, vhr_recruitment_abstract):
    _name = "vhr.send.multi.cvs"
    _description = "VHR RR Send CVs"
    
    def onchange_job_id(self, cr, uid, ids, job_id, context=None):
        domain = {'emp_receive_cvs': [('id', 'not in', [])], 'emp_cc_cvs': [('id', 'not in', [])]}
        if job_id:
            job_obj = self.pool.get('hr.job')
            domain['emp_receive_cvs'] = job_obj.get_list_emp_to_hr_job(cr, uid, job_id, context)
            domain['emp_cc_cvs'] = job_obj.get_list_emp_cc_hr_job(cr, uid, job_id, context)
        return {'value': domain}
    
    def default_get(self, cr, uid, fields_list, context=None):
        if context is None:
            context = {}
        res = super(vhr_send_multi_cvs, self).default_get(cr, uid, fields_list, context=context)
        if context.get('active_model') and context['active_model'] == 'hr.job':
            res['job_id'] = context.get('active_id')
        return res
    
    _columns = {
        'create_uid':fields.many2one('res.users', 'Create User'),
        'emp_receive_cvs': fields.many2many('hr.employee', 'send_cvs_employee_rel', 'candidate_id', 'employee_id', 'Send CV To'),
        'emp_cc_cvs': fields.many2many('hr.employee', 'send_cc_employee_rel', 'candidate_id', 'employee_id', 'CC To'),
        'note': fields.text('Note'),
        'job_id': fields.many2one('hr.job', 'Resource Request'),
        'number_cvs': fields.integer('Number CVs'),
        'count_number_applicant_cvs': fields.integer('Count Number Aplicant CVs')
    }

    def get_url(self, cr, uid, res_id, context=None):
        if isinstance(res_id, list):
            res_id = res_id[0]
        model_data = self.pool.get('ir.model.data')
        action_id = model_data.xmlid_lookup(cr, uid, 'vhr_recruitment.action_vhr_job_applicant')[2]
        parameter_obj = self.pool.get('ir.config_parameter')
        base_url = parameter_obj.get_param(cr, uid, 'web.base.url')
        url = '%s/web#page=0&limit=80&view_type=list&model=vhr.job.applicant&action=%s' % (base_url, action_id)
        return url
    
    def func_send_multi_cvs_hr_job(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]
        if context.get('active_id', False):
            job_applicant_obj = self.pool.get('vhr.job.applicant')
            job_obj= self.pool.get('hr.job').browse(cr, uid, context['active_id'])
            multi_cvs = self.read(cr, uid, ids[0], ['emp_cc_cvs','emp_receive_cvs'], context)
            lst_cv_send_emp = []
            lst_applicant_cvs_send = []
            for item in job_obj.job_applicant_ids:
                if item.state == 'draft':
                    lst_applicant_cvs_send.append(item.applicant_id.id)
                    for cv in item.applicant_id.cv_ids:
                        if cv.is_main and cv.type == 'binary':
                            lst_cv_send_emp.append(cv.id)
                    job_applicant_obj.write(cr, uid, item.id, {'emp_receive_cvs': [(6, 0, multi_cvs.get('emp_receive_cvs'))], 
                                                               'emp_cc_cvs': [(6, 0, multi_cvs.get('emp_cc_cvs'))]})
                    job_applicant_obj.execute_workflow(cr, uid, item.id, {'ACTION': 'trans_draft_confirm', 'IS_SEND_EMAIL': False})
            self.write(cr, uid, ids[0], {'number_cvs': len(lst_cv_send_emp),'count_number_applicant_cvs':len(lst_applicant_cvs_send)})
            if lst_cv_send_emp:
                self.recruitment_send_email(cr, uid, RE_MASS_SEND_CV_TO_CONFIRM, self._name, ids[0],lst_cv_send_emp, context=context)
                    
        return True

    def func_send_multi_cvs_hr_applicant(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]
        if context.get('active_ids', False):
            applicant_obj = self.pool.get('hr.applicant')
            job_applicant_obj = self.pool.get('vhr.job.applicant')
            multi_cvs = self.read(cr, uid, ids[0], ['job_id','emp_cc_cvs','emp_receive_cvs'], context)
            attachment_ids = []
            lst_applicant_cvs_send = []
            for applicant in applicant_obj.browse(cr, uid, context.get('active_ids'), context=context):
                if applicant.state == 'opening':# lay danh sach candidate state opening
                    lst_applicant_cvs_send.append(applicant.id)
                    for item in applicant.cv_ids:
                        if item.is_main and item.type == 'binary':
                            attachment_ids.append(item.id)
                    self.write(cr, uid, ids[0], {'number_cvs': len(attachment_ids),'count_number_applicant_cvs':len(lst_applicant_cvs_send)})
                    # gui mail cho depthead
                    is_new_emp = not applicant.ex_employee
                    vals = {'job_id': multi_cvs.get('job_id')[0],
                            'applicant_id': applicant.id,
                            'state': 'draft',
                            'is_new_emp': is_new_emp,
                            'emp_receive_cvs': [(6, 0, multi_cvs.get('emp_receive_cvs'))],
                            'emp_cc_cvs': [(6, 0, multi_cvs.get('emp_cc_cvs'))]
                            }
                    job_app_id = job_applicant_obj.execute_create(cr, uid, vals)
                    job_applicant_obj.execute_workflow(cr, uid, job_app_id, {'ACTION': 'trans_draft_confirm', 'IS_SEND_EMAIL': False})
                    applicant_obj.write_change_state(cr, uid, applicant.id, 'processing', u'Request Matching')

            if attachment_ids:
                self.recruitment_send_email(cr, uid, RE_MASS_SEND_CV_TO_CONFIRM, self._name, ids[0], attachment_ids, context=context)
        return True

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if context is None:
            context = {}
        if context.get('active_model') and context['active_model'] == 'hr.job':
            if not context.get('active_id'):
                raise osv.except_osv('Validation Error !', 'Please contact admin tool for support')

        res = super(vhr_send_multi_cvs, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar=toolbar, submenu=submenu)
        if view_type == 'form':
            doc = etree.XML(res['arch'])
            # Lọc task handle or share handle gửi CV
            hr_employee = self.pool.get('hr.employee')
            employee = hr_employee.search(cr, uid, [('user_id', '=', uid)], context={'active_test': False})
            emp = employee and employee[0] or 0
            domain = ['&', ('state', 'in', ['in_progress']), '|', ('handle_by', '=', emp), ('share_handle_by', '=', emp)]
            for node in doc.xpath("//field[@name='job_id']"):
                node.set('domain', json.dumps(domain))
            res['arch'] = etree.tostring(doc)
        return res

vhr_send_multi_cvs()
