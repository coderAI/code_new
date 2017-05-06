# -*-coding:utf-8-*-
import logging
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp.osv import osv, fields


log = logging.getLogger(__name__)

class vhr_erp_setting_special(osv.osv):
    _name = 'vhr.erp.setting.special'
    _description = 'VHR ERP SETTING SPECIAL'
    
    _columns = {
        'job_family_id': fields.many2one('vhr.job.family','Job Family', ondelete='restrict'),
        'job_group_id': fields.many2one('vhr.job.group','Job Group', domain="[('job_family_id','=',job_family_id)]", ondelete='restrict'),
        #New Job Level
        'job_level_position_id': fields.many2one('vhr.job.level.new', 'Position Level', ondelete='restrict'),
        'erp_level_id': fields.many2one('vhr.erp.level','ERP Level', ondelete='restrict'),
        'total_bonus_specialerp': fields.float('Total Bonus Special', digits=(12,0)),
        'total_bonus': fields.float('Total Bonus', digits=(12,0)),
        'special_job_id': fields.many2one('hr.job','Job'),
    }
    
    _order = 'id asc'
    _defaults = {
    }

vhr_erp_setting_special()

