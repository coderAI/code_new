# -*- coding: utf-8 -*-
import logging

from openerp import http
from openerp.addons.web import http
from openerp.addons.web.http import request
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import time
import json

log = logging.getLogger(__name__)

class website_pr_allowance_employee_list(http.Controller):

    @http.route('/allowance/employee/list', type='http', auth='user', website=True)
    def allowance_employee_list(self, **kw):
        log.info('The controller is called.')
        context = request.context
        cr, uid = request.cr, request.uid                
        
        emp_obj = request.registry['hr.employee']   
        dep_obj = request.registry['hr.department']
        requester_ids = emp_obj.search(cr, uid, [('user_id', '=', uid)], context=context)        
        dep_ids = dep_obj.search(cr, uid, [('manager_id', '=', requester_ids[0]), ('active', '=', True)], context=context)        
        emp_ids = emp_obj.search(cr, uid, [('department_id', 'in', dep_ids), ('department_id.manager_id.id','!=',uid)], context=context) 
        
        res_emps = emp_obj.read(cr, uid, emp_ids, ['name_related', 'login'], context=context)     
        
        return json.dumps(res_emps)
        
website_pr_allowance_employee_list()