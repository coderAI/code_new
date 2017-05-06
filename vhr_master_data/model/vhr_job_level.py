#-*-coding:utf-8-*-
from openerp.osv import osv, fields
import logging


log = logging.getLogger(__name__)

class vhr_job_level(osv.osv):
    _name = 'vhr.job.level'
    _description = 'VHR Job Level'
    _order = 'id, name desc'
    
    _columns = {
                'name' : fields.char('Vietnamese Name', size=128),
                'name_en' : fields.char('English Name', size=128),
                'code' : fields.char('Code', size=64),
                'staff_classification_id': fields.many2one('vhr.dimension', 'Staff Classification', ondelete='restrict', 
                                                 domain=[('dimension_type_id.code', '=', 'STAFF_CLASSIFICATION'), ('active','=',True)]),
                'job_level_type_id' : fields.many2one('vhr.job.level.type', 'Job Level Type', ondelete='restrict'),
                'is_manager' : fields.boolean('Dept Head ?'),
                'check_ot' : fields.boolean('Check OT'),
                'effect_date': fields.date('Effect Date'),
                'description' : fields.text('Description'),
#                 'job_title_ids': fields.one2many('vhr.job.title', 'job_level_id', string='Job Titles'),
                'audit_log_ids' : fields.one2many('audittrail.log.line', 'res_id', 'Logs', domain=[('object_id.model','=', _name), \
                                                                                                ('field_id.name', 'not in', ['write_date', 'audit_log_ids'])]),
                'level': fields.integer('Level'),
                'active' : fields.boolean('Active')
     }
    
    _defaults = {
                 'check_ot' : True,
                 'is_manager' : True,
                 'active' : True
                 }
    _unique_insensitive_constraints = [{'code': "Job Level's Code is already exist!"},
                                       {'name': "Job Level's Vietnamese Name is already exist!"}]

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        
        if 'job_title_id' in context:
            job_level_ids = []
            title_level_ids = self.pool.get('vhr.jobtitle.joblevel').search(cr, uid, [('job_title_id','=',context['job_title_id'])])
            if title_level_ids:
                title_level_infos = self.pool.get('vhr.jobtitle.joblevel').read(cr, uid, title_level_ids, ['job_level_id'])
                for title_level_info in title_level_infos:
                    if title_level_info.get('job_level_id', False):
                        job_level_ids.append(title_level_info['job_level_id'][0])
            
            args.append( ('id','in',job_level_ids))
                        
                        
        args_new = ['|', '|', ('name', operator, name), ('code', operator, name), ('name_en', operator, name)] + args
        ids = self.search(cr, uid, args_new)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(vhr_job_level, self).name_search(cr, uid, name, args, operator, context, limit)
    
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_job_level, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res
    
vhr_job_level()





