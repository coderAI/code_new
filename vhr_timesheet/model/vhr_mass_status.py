# -*-coding:utf-8-*-

import logging

from openerp.osv import osv, fields
from openerp.addons.vhr_common.model.vhr_common import vhr_common

log = logging.getLogger(__name__)


class vhr_mass_status(osv.osv, vhr_common):
    _name = 'vhr.mass.status'
    _inherit = 'vhr.mass.status'

    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if not context:
            context = {}
        
        mcontext = {'search_all_employee': True, 'active_test': False}
        employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', uid)],context=mcontext)
        if context.get('filter_by_permission_dept_admin', False):
            groups = self.pool.get('res.users').get_groups(cr, uid)
            new_args = []
            if set(['hrs_group_system', 'vhr_cb']).intersection(set(groups)):
                new_args = []
            elif 'vhr_dept_admin' in groups:
                employee_ids = self.get_list_employees_of_dept_admin(cr, uid, employee_ids[0], context)
                detail_ids = self.pool.get('vhr.mass.status.detail').search(cr, uid, [('employee_id','in',employee_ids)])
                new_args = [('mass_status_detail_ids','in', detail_ids)]
            
            args.extend(new_args)
            
        res = super(vhr_mass_status, self).search(cr, uid, args, offset, limit, order, context, count)
        
        return res
    
vhr_mass_status()