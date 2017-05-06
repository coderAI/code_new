# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields
from openerp.addons.vhr_common.model.vhr_common import vhr_common

from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import datetime
from dateutil.relativedelta import relativedelta

log = logging.getLogger(__name__)


class vhr_department_history(osv.osv, vhr_common):
    _name = 'vhr.department.history'
    _description = 'Department History'
    
    
    def _get_effect_to(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if not isinstance(ids, list):
            ids = [ids]
        
        for record_id in ids:
            res[record_id] = self.get_effect_to_of_history_department(cr, uid, record_id)
        return res
    
    def _get_update_history(self, cr, uid, ids, context=None):
        records = self.read(cr, uid, ids, ['department_id'])
        department_ids = [record.get('department_id', False) and record['department_id'][0] for record in records]
        return self.search(cr, uid,[('department_id','in',department_ids)])
    
    _columns = {
                'name': fields.char('Vietnamese Name', size=128),
                'name_en': fields.char('English Name', size=128),
                'code': fields.char('Code', size=128),
                'department_id': fields.many2one('hr.department', 'Department', ondelete='restrict'),
                
                'organization_class_id': fields.many2one('vhr.organization.class', 'Organization Class', ondelete='restrict'),
                'company_id': fields.many2one('res.company', 'Company', ondelete='restrict'),
                'manager_id': fields.many2one('hr.employee','Dept Head', ondelete='cascade'),
                'effect_from': fields.date('Effective From'),
                'effect_to': fields.function(_get_effect_to, type='date',string='Effective To', 
                                             store={'vhr.department.history': (_get_update_history, 
                                                                                ['effect_from'],20)}),
                'note': fields.text('Notes'),
    }
    
    _order = 'effect_from desc'

    def get_effect_to_of_history_department(self, cr, uid, record_id, context=None):
        """
        effect_to = nearest_greater_record_effect_from - 1 days
        """
        res = False
        if record_id:
            record = self.read(cr, uid, record_id, ['department_id', 'effect_from'])
            department_id = record.get('department_id', False) and record['department_id'][0]
            effect_from = record.get('effect_from', False)
            
            greater_ids = self.search(cr, uid, [('department_id','=',department_id),
                                                ('effect_from','>', effect_from)], order='effect_from asc', limit =1)
            if greater_ids:
                greater_record = self.read(cr, uid, greater_ids[0], ['effect_from'])
                greater_effect_from = greater_record.get('effect_from', False)
                if greater_effect_from:
                    res = datetime.strptime(greater_effect_from,DEFAULT_SERVER_DATE_FORMAT) - relativedelta(days=1)
                    res = res.strftime(DEFAULT_SERVER_DATE_FORMAT)
        
        return res
            
            
        
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_department_history, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res
    
    def cron_generate_default_history_for_dept(self, cr, uid, department_code, effect_from, is_generate_for_child_dept, context=None):
        """
        Genetate default history record for department if department dont have any history record
        """
        
        if department_code and effect_from:
            dept_obj = self.pool.get('hr.department')
            dept_ids = dept_obj.search(cr, uid, [('code','=',department_code),
                                                 ('active','=',True)])
            if dept_ids and is_generate_for_child_dept:
                dept_ids = self.get_child_department(cr, uid, dept_ids)
            
            fields = ['name','name_en','code','organization_class_id','company_id','manager_id']
            read_fields = fields + ['history_ids']
            for department in dept_obj.read(cr, uid, dept_ids, read_fields):
                if department.get('history_ids', []):
                    continue
                val = {'department_id': department['id'],'effect_from': effect_from}
                for field in fields:
                    val[field] = department.get(field)
                    if isinstance(val[field], tuple):
                        val[field] = val[field][0]
                
                self.create(cr, uid, val)
                


vhr_department_history()