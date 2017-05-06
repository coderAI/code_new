# -*-coding:utf-8-*-
import logging
from openerp.osv import osv, fields
import simplejson as json
from lxml import etree
from vhr_recruitment_constant import RE_Request_Survey_By_Email
from vhr_recruitment_abstract import vhr_recruitment_abstract, ADMIN
    
log = logging.getLogger(__name__)


class vhr_recruitment_survey(osv.osv, vhr_recruitment_abstract):
    _name = "vhr.recruitment.survey"
    _description = "RR Survey"
    
    def onchange_job_id(self, cr, uid, ids, job_id, context=None):
        domain = {'emp_to_survey': [('id', 'not in', [])], 'emp_cc_survey': [('id', 'not in', [])]}
        if job_id:
            job_obj = self.pool.get('hr.job')
            domain['emp_to_survey'] = job_obj.get_list_emp_to_survey_job(cr, uid, job_id, context)
            domain['emp_cc_survey'] = job_obj.get_list_emp_cc_survey_job(cr, uid, job_id, context)
        return {'value': domain}
    
    def default_get(self, cr, uid, fields_list, context=None):
        if context is None:
            context = {}
        res = super(vhr_recruitment_survey, self).default_get(cr, uid, fields_list, context=context)
        if context.get('active_model') and context['active_model'] == 'hr.job':
            if context.get('active_id',False):
                res['job_id'] = context.get('active_id')
        return res
    
    _columns = {
        'user_id':fields.many2one('res.users', 'User'),
        'emp_to_survey': fields.many2many('hr.employee', 'send_to_employee_survey_rel', 'survey_id', 'employee_id', 'Send To'),
        'emp_cc_survey': fields.many2many('hr.employee', 'send_cc_employee_survey_rel', 'survey_id', 'employee_id', 'CC To'),
        'comment': fields.text('Comment'),
        'job_id': fields.many2one('hr.job', 'Resource Request'),
    }
    
    
    def get_url(self, cr, uid, res_id, context=None):
        if isinstance(res_id, list):
            res_id = res_id[0]
        model_data = self.pool.get('ir.model.data')
        parameter_obj = self.pool.get('ir.config_parameter')
        base_url = parameter_obj.get_param(cr, uid, 'web.base.url')
        action_id = model_data.xmlid_lookup(cr, uid, 'vhr_recruitment.action_vhr_rr_survey')[2]
        url = '%s/web#id=%s&view_type=form&model=vhr.recruitment.survey&action=%s' % (base_url, res_id, action_id)
        return url
    
    
    def func_send_rr_survey(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]
        list_emp_to = []
        list_emp_cc = []
        list_cc_mail = []
        hr_job_obj= self.pool.get('hr.job')
        if context.get('active_id', False):
            job_obj= self.pool.get('hr.job').browse(cr, uid, context['active_id'])
            rr_survey_email_obj = self.pool['vhr.recruitment.survey.email']
            survey_obj = self.browse(cr, uid, ids[0], context=context)
            for item_to in survey_obj.emp_to_survey:
                if item_to.id:
                    list_emp_to.append(item_to.id)
            for item_cc in survey_obj.emp_cc_survey:
                if item_cc.id:
                    list_emp_cc.append(item_cc.id)
            link_email = self.get_url(cr, uid, job_obj.id, context)
            for emp_cc in self.pool['hr.employee'].browse(cr, uid, list_emp_cc, context=context):
                if emp_cc.work_email:
                    list_cc_mail.append(emp_cc.work_email)
            email_cc = ";".join(list_cc_mail)
            for approve in self.pool['hr.employee'].browse(cr, uid, list_emp_to, context=context):
                email_to = approve.work_email.lower() if approve.work_email else ''
                if email_to:
                    is_success = rr_survey_email_obj.send_email(cr, uid, RE_Request_Survey_By_Email,{'email_to':email_to,'email_cc':email_cc,
                                                            'link_email':link_email,'approver':approve.id,'job_id': job_obj.id,'request_code': job_obj.code}, context={'APPROVE_EMAIL': True})
                    if is_success:
                        hr_job_obj.write(cr, uid, job_obj.id, {'is_send_survey': True})
        return True

vhr_recruitment_survey()
