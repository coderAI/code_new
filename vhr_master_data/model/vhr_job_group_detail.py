# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields



log = logging.getLogger(__name__)


class vhr_job_group_detail(osv.osv):
    _name = 'vhr.job.group.detail'
    _description = 'VHR Job Group Detail'

    _columns = {
        'job_group_id': fields.many2one('vhr.job.group', 'job Group', ondelete='restrict'),
        'name': fields.char('Vietnamese Name', size=128),
        'name_en': fields.char('English Name', size=128),
        'effect_date': fields.date('Effect Date'),
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

    _unique_insensitive_constraints = [{'effect_date': "Job Group Detail's effect_date is already exist!"},
                                       {'name': "Job Group Detail's Vietnamese Name is already exist!"}]
    
    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        args_new = ['|', '|', ('name', operator, name), ('code', operator, name), ('name_en', operator, name)] + args
        ids = self.search(cr, uid, args_new)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(vhr_job_group_detail, self).name_search(cr, uid, name, args, operator, context, limit)
    
    
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_job_group_detail, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res


vhr_job_group_detail()