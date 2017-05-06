# -*-coding:utf-8-*-
import logging
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp.osv import osv, fields


log = logging.getLogger(__name__)

class vhr_bonus_for_recruiter(osv.osv):
    _name = 'vhr.bonus.for.recruiter'
    _description = 'VHR Bonus FOR RECRUITER'
    
    _columns = {
            'job_family_id': fields.many2one('vhr.job.family','Job Family', ondelete='restrict'),
            'job_group_id': fields.many2one('vhr.job.group','Job Group', domain="[('job_family_id','=',job_family_id)]", ondelete='restrict'),
            'job_level_position_id': fields.many2one('vhr.job.level.new', 'Position Level', ondelete='restrict'),
            'erp_level_id': fields.many2one('vhr.erp.level','ERP Level', ondelete='restrict'),
            'bonus_for_recruiter_job_id': fields.many2one('hr.job','Job'),
            'bonus_for_recruiter': fields.float('Bonus for Recruiter', digits=(12,0)),
            'note': fields.text('Note'),
    }
    _order = 'id asc'
    
    _defaults = {
                 
    }
    

vhr_bonus_for_recruiter()

