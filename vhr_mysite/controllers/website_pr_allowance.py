# -*- coding: utf-8 -*-
import logging

from openerp import http
from openerp.addons.web import http
from openerp.addons.web.http import request
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import time

log = logging.getLogger(__name__)

class website_pr_allowance(http.Controller):

    @http.route(['/allowance/request'], methods=['GET', 'POST'], type='http', auth='user', website=True)
    def allowance_request(self, **post):        
        res = {'header': u'Nhân Viên Yêu Cầu'}
        #ONLY GET LIST EMPLOYEE ABIDE BY DEPARTMENT
        #define param
        context = request.context
        cr, uid = request.cr, request.uid
        now = time.strftime("%Y-%m-%d")
        requester_id = False
        
        emp_obj = request.registry['hr.employee']
        allowance_type_obj = request.registry['vhr.pr.allowance.cate']
        
        allowance_type_ids = allowance_type_obj.search(cr, uid, [('active', '=', True)], context=context)
        allowance_type = allowance_type_obj.browse(cr, uid, allowance_type_ids, context=context)
                
        emp_ids = emp_obj.search(cr, uid, [('user_id', '=', uid)], context=context)
        res_emp = emp_obj.read(cr, uid, emp_ids[0], ['department_id', 'name','code'], context=context)
        dept_name = res_emp.get('department_id', False) and res_emp['department_id'][1] or ""
        requester_data = {'employee_name': '', 'employee_code': '', 'dept_code': '', 'create_date': now, 'employee_requested': ''}
        if post.get('employee_requested'):
            requester_id = post.get('employee_requested')
        if requester_id:
            log.info('Entered')        
        
        if res_emp:            
            requester_data.update({'employee_name': res_emp['name'], 'employee_code': res_emp['code'], 'department': dept_name})                
        res.update({'requester_data': requester_data, 'allowance_type': allowance_type})
        return request.website.render("vhr_mysite.allowance_request", res)

website_pr_allowance()