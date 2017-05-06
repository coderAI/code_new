# -*-coding:utf-8-*-

import logging

from openerp.osv import osv, fields


log = logging.getLogger(__name__)


class vhr_termination_request(osv.osv):
    _name = 'vhr.termination.request'
    _inherit = 'vhr.termination.request'
    
    def write(self, cr, uid, ids, vals, context=None):
        if not isinstance(ids, list):
            ids = [ids]
        
        #Raise error if change date_end_working_approve when generated detail
        if vals.get('date_end_working_approve', False):
            date_end_working_approve = vals.get('date_end_working_approve', False)
            tr = self.read(cr, uid, ids[0], ['state','employee_id'])
            employee_id = tr.get('employee_id', False) and tr['employee_id'][0]
            if tr.get('state', False) == 'finish':
                ts_detail_obj = self.pool.get('vhr.ts.timesheet.detail')
                
                ts_detail_ids = ts_detail_obj.search(cr, uid, [('from_date','<=',date_end_working_approve),
                                                               ('to_date','>=',date_end_working_approve)], order='from_date asc')
                if ts_detail_ids:
                    detail = ts_detail_obj.read(cr, uid, ts_detail_ids[0], ['month','year'])
                    month = detail.get('month', 0)
                    year = detail.get('year', 0)
                    
                    monthly_ids = self.pool.get('vhr.ts.monthly').search(cr, uid, [('month','=',month),
                                                                                   ('year','=', year),
                                                                                   ('employee_id','=',employee_id),
                                                                                   ('state','!=','reject')])
                    if monthly_ids:
                        raise osv.except_osv('Validation Error !', 
                                             "You can't edit Approved last working date when detail timesheet already generated.\nPlease reject generated detail timesheet or contact to C&B for support" )
                     
        res = super(vhr_termination_request, self).write(cr, uid, ids, vals, context)
        
        
        return res
    
    
    
vhr_termination_request()