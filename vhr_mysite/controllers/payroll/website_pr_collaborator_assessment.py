# -*- coding: utf-8 -*-
import logging

from openerp import http
from openerp.addons.web import http
from openerp.addons.web.http import request
from datetime import date, datetime
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
import json

log = logging.getLogger(__name__)


class website_pr_collaborator_assessment(http.Controller):
    @http.route(['/collaborator/assessment'], methods=['GET', 'POST'], type='http', auth='user', website=True)
    def request_collaborator_assessment(self, **post):
        res = {'header': u'Bảng Chấm Công Cộng Tác Viên', 'btn_confirm': u'Gửi', 'btn_approve': u'Approve',
               'cb_approve': False, 'dh_approve': False, 'btn_reject': u'Reject'}
        context = dict(request.context, show_address=True, no_tag_br=True)
        if context is None:
            context = {}
        cr, uid = request.cr, request.uid
        ca_obj = request.registry['vhr.pr.collaborator.assessment']
        dimension_obj = request.registry['vhr.dimension']
        emp_obj = request.registry['hr.employee']
        comp_obj = request.registry['res.company']
        comp_list = comp_obj.search_read(cr, uid, [('active', '=', True)], ['name'], context=context)
        msg = ''
        err = False
        ca_id = False
        months = [(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5'), (6, '6'),
                  (7, '7'), (8, '8'), (9, '9'), (10, '10'), (11, '11'), (12, '12')]
        years = ca_obj._get_year(cr, uid, context=context)

        emp_ids = emp_obj.search(cr, uid, [('user_id', '=', uid)], context=context)
        res_emp = emp_obj.read(cr, uid, emp_ids[0], [], context=context)
        comp_id = res_emp.get('company_id', False) and res_emp['company_id'][0] or False
        comp_name = res_emp.get('company_id', False) and res_emp['company_id'][1] or False
        dept_name = res_emp.get('department_id', False) and res_emp['department_id'][1] or False
        dept_id = res_emp.get('department_id', False) and res_emp['department_id'][0] or False
        ca_type_ids = dimension_obj.search(cr, uid, [('dimension_type_id.code', '=', 'PR_COLLABORATOR_ASSESSMENT')])
        ca_type_id = ca_type_ids and ca_type_ids[0] or False
        ca_type_args = [('code', '=', 'PR_COLLA_1'), ('dimension_type_id.code', '=', 'PR_COLLABORATOR_ASSESSMENT')]
        ca_types = dimension_obj.read(cr, uid, ca_type_ids, ['name', 'code'], context=context)
        ca_product_ids = dimension_obj.search(cr, uid, ca_type_args, context=context)
        is_ca_products = ca_type_id in ca_product_ids and 1 or 0
        today = date.today()
        if post.get('ca_id'):
            ca_id = int(post.get('ca_id'))

        data = self.serialize_post(post, ca_obj._columns.keys())
        if data and not ca_id:
            try:
                context.update({'ACTION': 'draft_waiting_dept', 'VIEW_NAME': 'Notes',
                                'VIEW_ID': 'vhr_payroll.view_vhr_pr_collaborator_assessment_submit'})
                ca_id = ca_obj.create(cr, uid, data, context=context)
                if ca_id:
                    ca_obj.action_execute(cr, uid, [ca_id], context=context)
                msg = u'Đăng ký thành công'
            except Exception, e:
                err = e.message and e.message
                if not err:
                    err = e.value
                cr.rollback()
        if ca_id:
            data = ca_obj.read(cr, uid, ca_id, [], context=context)
            is_emp = data.get('requester_id', False) and data['requester_id'][0] in emp_ids
            if is_emp or data.get('is_cb', False) or data.get('is_dept_head', False):

                ca_type_id = data.get('collaborator_assessment_type_id', '') and data['collaborator_assessment_type_id'][0] or ''
                is_ca_products = ca_type_id in ca_product_ids and 1 or 0
                emp_data = {
                    'requester': data.get('requester_id', False) and data['requester_id'][1] or '',
                    'department_id': data.get('department_id', '') and data['department_id'][0] or '',
                    'department': data.get('department_id', '') and data['department_id'][1] or '',
                    'company_id': data.get('company_id', '') and data['company_id'][0] or '',
                    'company': data.get('company_id', '') and data['company_id'][1] or '',
                    'collaborator_assessment_type_id': ca_type_id,
                    'is_ca_products': is_ca_products
                }
                data.update(emp_data)

                if data.get('is_cb', False) and data.get('state') == 'cb_executive':
                    res['cb_approve'] = True
                    context.update({'VIEW_NAME': 'Notes',  'VIEW_ID': 'vhr_payroll.view_vhr_pr_collaborator_assessment_submit'})
                if data.get('is_dept_head', False) and data.get('state') == 'waiting_dept':
                    res['dh_approve'] = True
                    context.update({'VIEW_NAME': 'Notes', 'VIEW_ID': 'vhr_payroll.view_vhr_pr_collaborator_assessment_submit'})

                if post.get('action') in ['approve', 'reject'] and (res['dh_approve'] or res['cb_approve']):
                    context.update({'ACTION': post['action'], 'ACTION_COMMENT': post.get('action_comment')})
                    if ca_obj.action_execute(cr, uid, [ca_id], context=context):
                        res['dh_approve'] = res['lm_approve'] = False
                        data.update(post)
            else:
                data = {}
                ca_id = False
                err = u'Bạn Không Thể Xem Nội Dung. Vui Lòng Liên Hệ Administrator!'
        else:
            if res_emp:
                data = {
                    'requester': res_emp['name'],
                    'department_id': dept_id,
                    'department': dept_name,
                    'company_id': comp_id,
                    'company': comp_name,
                    'month': today.month,
                    'year': str(today.year),
                    'request_date': today.strftime(DEFAULT_SERVER_DATE_FORMAT),
                    'collaborator_assessment_type_id': ca_type_id,
                    'is_ca_products': is_ca_products
                }
                if err and post:
                    if 'state' in data:
                        del data['state']
            else:
                err = u'Bạn Không Có Quyền Tạo Đơn Xin Nghỉ Việc. Vui Lòng Liên Hệ Administrator!'
                data = {}
                ca_id = False

        res.update({'ca_id': ca_id, 'data': data, 'message': msg, 'error': err, 'ca_types': ca_types,
                    'months': months, 'years': years, 'format_date': self.format_date, 'comp_list': comp_list})

        return request.render("vhr_mysite.collaborator_assessment", res)

    def serialize_post(self, post, keys):
        res = {}
        if post:
            for key, val in post.iteritems():
                if key in keys:
                    try:
                        if key in ['date_from', 'date_to'] and len(val) == 10:
                            date = datetime.strptime(str(val), '%d/%m/%Y')
                            val = date.strftime('%Y-%m-%d')
                    except ValueError:
                        continue
                    res[key] = val
        return res

    def format_date(self, date):
        if isinstance(date, (str, unicode)) and len(date) >= 10:
            date = date[:10]
        else:
            return ""
        return datetime.strptime(date, '%Y-%m-%d').strftime('%d/%m/%Y')

    def format_date_sys(self, date):
        if isinstance(date, (str, unicode)) and len(date) >= 10:
            date = date[:10]
        else:
            return ""
        return datetime.strptime(date, '%d/%m/%Y').strftime('%Y-%m-%d')

    @http.route('/mysite/get_all_departments', methods=['GET', 'POST'], type='http', auth="user", website=True)
    def get_all_departments(self, **kw):
        context = dict(request.context, show_address=True, no_tag_br=True)
        cr, uid = request.cr, request.uid
        code = kw.get("code", "")
        department_obj = request.registry['hr.department']
        domain = [('active', '=', True), ('organization_class_id.level', '=', 3)]
        if code:
            codes = code.split("/")
            code = codes[len(codes)-1]
            code = code.replace(" ", "")
            domain += ['|', ('code', 'ilike', code), ('parent_id.code', 'ilike', code)]
        fields = ['name', 'complete_code']
        res = department_obj.search_read(cr, uid, domain, fields, context=context)
        return json.dumps(res)

website_pr_collaborator_assessment()