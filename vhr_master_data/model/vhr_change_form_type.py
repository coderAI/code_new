# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields


log = logging.getLogger(__name__)


class vhr_change_form_type(osv.osv):
    _name = 'vhr.change.form.type'
    _description = 'VHR Change Form Type'

    _columns = {
        'code': fields.char('Code', size = 64),
        'name': fields.char('Vietnamese Name', size=128),
        'name_en': fields.char('English Name', size=128),
        'sign_emp_id': fields.many2one('hr.employee', 'Signer', ondelete='restrict'),
        'job_title_id': fields.many2one('vhr.job.title', "Signer's Title", ondelete='restrict'),
        'description': fields.text('Description'),
        'active': fields.boolean('Active'),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                          domain=[('object_id.model', '=', _name),
                                                  ('field_id.name', 'not in',
                                                   ['write_date', 'audit_log_ids'])]),
    }

    _defaults = {
        'active': True,
    }
    
    _unique_insensitive_constraints = [{'code': "Change Form Type's Code is already exist!"},
                                       {'name': "Change Form Type's Vietnamese Name is already exist!"}]
    
    
    #When onchange sign_emp_id get job_title_id
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
        return super(vhr_change_form_type, self).name_search(cr, uid, name, args, operator, context, limit)
    
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_change_form_type, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if not context:
            context = {}
        
        return super(vhr_change_form_type, self).search(cr, uid, args, offset, limit, order, context, count)



vhr_change_form_type()