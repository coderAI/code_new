# -*-coding:utf-8-*-
import logging
from openerp.osv import osv, fields

log = logging.getLogger(__name__)


class vhr_rr_recommend_cv(osv.osv):
    _name = 'vhr.rr.recommend.cv'
    _description = 'VHR RR Recommend CV'

    def _employee_ref(self, cr, uid, ids, fields, args, context=None):
        res = {}
        emp_obj = self.pool.get('hr.employee')
        for item in self.read(cr, uid, ids, ['ref_email'], context=context):
            res[item['id']] = False
            ref_email = item.get('ref_email', '') and item['ref_email'].strip().replace(';', '') or False
            if ref_email:
                emp_ids = emp_obj.search(cr, uid, ['|', ('work_email', 'ilike', ref_email),
                                                        ('address_home_id.email', 'ilike', ref_email)], context=context)
                res[item['id']] = emp_ids and emp_ids[0] or False
        return res

    def _get_email_handle_by(self, cr, uid, ids, fields, args, context=None):
        res = {}
        for item in self.browse(cr, uid, ids, context=context):
            res[item.id] = ""
            if item.post_id.request_job_ids:
                for line in item.post_id.request_job_ids:
                    if line.handle_by.work_email:
                        res[item.id] += line.handle_by.work_email + "; "
                    if line.share_handle_by.work_email:
                        res[item.id] += line.share_handle_by.work_email + "; "
        return res

    _columns = {
        'create_date': fields.datetime('Create Date'),
        'referee': fields.char('Referee'),
        'ref_email': fields.char('Referee Email'),
        'name': fields.char('Candidate Name'),
        'email': fields.char('Candidate Email'),
        'employee_id': fields.many2one('hr.employee', 'Employee'),
        'ref_employee_id': fields.function(_employee_ref, type="many2one", relation='hr.employee',
                                           string='Employee Referral'),
        'attachment_ids': fields.one2many('ir.attachment', 'res_id', 'Attachment', domain=[('res_model', '=', _name)]),
        'post_id': fields.many2one('vhr.post.job', 'Post Job'),
        'job_id': fields.many2one('vhr.job', 'Job'),
        'program_event_id': fields.many2one('vhr.program.event', 'Program Event'),
        'type': fields.selection([('recommend', 'Recommend'), ('internal', 'Internal')], 'Type'),
        'handle_by_email': fields.function(_get_email_handle_by, type='char', string='Email Recruiters'),
        'identity_number': fields.char('Identity Number'),

    }

    _defaults = {
        'type': 'recommend',
    }
    
    _order = 'write_date desc'
    
    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        res_id = super(vhr_rr_recommend_cv, self).create(cr, uid, vals, context)
        return res_id
    
vhr_rr_recommend_cv()
