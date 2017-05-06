#-*-coding:utf-8-*-
from openerp.osv import osv, fields
import logging


log = logging.getLogger(__name__)

class vhr_award_form(osv.osv):
    _name = 'vhr.award.form'
    _description = 'VHR Award Form'
    _order = 'id desc'
    
    _columns = {
                'name' : fields.char('Vietnamese Name', size=128),
                'name_en' : fields.char('English Name', size=128),
                'code' : fields.char('Code', size=64),
                'sign_emp_id' : fields.many2one('hr.employee', 'Signer', ondelete='restrict'),
                'job_title_id' : fields.related('sign_emp_id', 'title_id', type='many2one', relation='vhr.job.title', string="Signer's Title"),
                'is_award_form' : fields.boolean('Award Form ?'),
                'description' : fields.text('Description'),
                'active' : fields.boolean('Active'),
                'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                          domain=[('object_id.model', '=', _name),
                                                  ('field_id.name', 'not in',
                                                   ['write_date', 'audit_log_ids'])]),
                
     }
    
    _defaults = {
                 'is_award_form' : True,
                 'active' : True
                 }
    _unique_insensitive_constraints = [{'code': "Award Form's code is already exist!"},
                                       {'name': "Award Form's name is already exist!"}]
    
    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        args_new = ['|', '|', ('name', operator, name), ('code', operator, name), ('name_en', operator, name)] + args
        ids = self.search(cr, uid, args_new, 0, None, None, context)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(vhr_award_form, self).name_search(cr, uid, name, args, operator, context, limit)
    
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_award_form, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if not context:
            context = {}
        
        return super(vhr_award_form, self).search(cr, uid, args, offset, limit, order, context, count)


vhr_award_form()





