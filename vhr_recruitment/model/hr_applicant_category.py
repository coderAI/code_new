# -*-coding:utf-8-*-
import logging
from openerp.osv import osv, fields
from datetime import date, datetime, timedelta
log = logging.getLogger(__name__)


class hr_applicant_category(osv.osv):
    _inherit = 'hr.applicant_category'

    _columns = {
        'create_date': fields.datetime('Create date'),
        'create_uid': fields.many2one('res.users', 'Created By', readonly=True),
        'write_date': fields.datetime('Write date'),
        'write_uid': fields.many2one('res.users', 'Write By', readonly=True),
        'count_index': fields.integer('Count index'),
        'applicant_ids': fields.many2many('hr.applicant', 'hr_applicant_hr_applicant_category_rel',\
                                          'hr_applicant_category_id', 'hr_applicant_id',string='Applicants'),
        'available': fields.boolean('Available')
    }
    _defaults = {  
        'available': False,
        'count_index': 1
        }
    
    def update_key_word(self, cr, uid, keyword):
        lst = self.search(cr, uid, [('name', '=ilike', keyword)])
        count_config = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr.rr.search.count.skill')
        count_config = int(count_config) if count_config else 50
        if lst:
            for cate in self.read(cr, uid, lst, ['count_index', 'name']):
                count_index = cate.get('count_index',0) + 1
                update_vals = {'count_index': count_index}
                if count_index == count_config:
                    lst_candidate = self.pool.get('hr.applicant').search(cr, uid, [('description', 'ilike', cate.get('name'))])
                    update_vals['applicant_ids'] = [[6, 0, lst_candidate]]
                    update_vals['available'] = True
                self.write(cr, uid, cate.get('id'), update_vals)
        else:
            self.create(cr, uid, {'name': keyword})
        return True
            
    def cron_update_skill_candidate(self, cr, uid, num_cand, context=None):
        log.info('VHR RR cron_update_skill_candidate')
        count_config = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr.rr.search.count.skill')
        count_config = int(count_config) if count_config else 50
        lst_cate = self.search(cr, uid, [('count_index', '>=', count_config)], limit=num_cand,  order="write_date desc")
        applicant_obj = self.pool.get('hr.applicant')
        if lst_cate:
            for cate in self.read(cr, uid, lst_cate, ['name', 'write_date']):
                vals_cand = {}
                start = datetime.today()
                cate_name = cate.get('name')
                lst_candidate = applicant_obj.search(cr, uid, [('description', 'ilike', cate_name)])
                vals_cand['applicant_ids'] = [[6, 0, lst_candidate]]
                vals_cand['available'] = True
                self.write(cr, uid, cate.get('id'), vals_cand)
                end = datetime.today()
                log.debug('Time update candidate skill : %s' % (end - start))
        log.info('VHR RR cron_update_skill_candidate End')
        return True
hr_applicant_category()
