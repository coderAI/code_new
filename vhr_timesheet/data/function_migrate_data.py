# -*-coding:utf-8-*-
import logging
from openerp.osv import fields, osv
from openerp.tools.translate import _


log = logging.getLogger(__name__)

class function_migrate_data(osv.osv_abstract):
    
    _name = 'function.migrate.data'
    
    
    def migrate_vhr_holidays_status(self, cr, uid):
        log.info('======= START MIGRATE migrate_vhr_holidays_status ========')
        
        holiday_group_pool = self.pool.get('vhr.holidays.status.group')
        
        updated_ids = holiday_group_pool.search(cr, uid, [('is_allow_to_register_from_now_to_next_year','=',True)])
        if updated_ids:
            return True
        
        #Leave Type Group Sinh con
        holiday_group_pool.write(cr, uid, 5, {'is_allow_to_register_from_now_to_next_year': True,
                                              'is_check_remain_day_on_current_registration': True})
        
        #Leave Type Group Nghi Khong Luong
        holiday_group_pool.write(cr, uid, 11, {'is_allow_to_register_from_now_to_next_year': True})
        
        #Leave Type sinh con có description nghỉ cả ngày rest date
        self.pool.get('hr.holidays.status').write(cr, uid, [81,79,80], {'is_date_range_include_rest_date': True})
        
        return True
        
        