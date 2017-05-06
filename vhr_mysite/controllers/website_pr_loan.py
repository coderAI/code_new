# -*- coding: utf-8 -*-
import logging

from openerp import http
from openerp.addons.web import http
from openerp.addons.web.http import request
from datetime import datetime
# from openerp.addons.vhr_payroll.model.vhr_pr_loan import CLICKER_REQUEST, DEPTH_APPROVE, CB_REVIEW, CB_APPROVE, DONE, CANCEL, G_CB_EXECUTOR, G_CB_LOAN, G_CB_MANAGER
import time
import ast
import json
import werkzeug.utils

import string
import random

log = logging.getLogger(__name__)

class website_pr_loan_controller(http.Controller):

    @http.route(['/loan'], methods=['GET', 'POST'], type='http', auth='user', website=True)
    def loan(self, **kwargs):
        cr = request.cr
        uid = request.uid
        context = dict(request.context, show_address=True, no_tag_br=True)
        loan_pool = request.registry['vhr.pr.loan']
        values = {
            'header': '',
            'loan_datas': [],
            'encrypt_query_value': self.encrypt_query_value
        }
        try:
            loan_datas = loan_pool.get_loan_datas(cr, uid, [('employee_id', '!=', False),
                                                            ('employee_id.user_id', '=', uid)], context=context)
            values.update({
                'header': 'Qúa Trình Vay Nợ Của Nhân Viên',
                'loan_datas': loan_datas
            })
        except Exception, e:
            message = e.message
            log.info('Leave Error %s' % message)
        return request.website.render("vhr_mysite.loan", values)

    @http.route(['/loan/approval'], methods=['GET', 'POST'], type='http', auth='user', website=True)
    def loan_approval(self, **kwargs):
        cr = request.cr
        uid = request.uid
        context = dict(request.context, show_address=True, no_tag_br=True)
        loan_pool = request.registry['vhr.pr.loan']
        values = {
            'header': '',
            'loan_datas': [],
            'encrypt_query_value': self.encrypt_query_value
        }
        try:
            state_lists = []
            all_dept_head_user_ids = loan_pool._get_all_dept_head_user_ids(cr, context=context)
            if uid in all_dept_head_user_ids:
                state_lists.append(DEPTH_APPROVE)
            if loan_pool.check_user_in_group(cr, uid, G_CB_EXECUTOR[0], G_CB_EXECUTOR[1], context=context):
                state_lists.append(CB_REVIEW)
            if loan_pool.check_user_in_group(cr, uid, G_CB_MANAGER[0], G_CB_MANAGER[1], context=context):
                state_lists.append(CB_APPROVE)
            loan_datas = loan_pool.get_loan_datas(cr, uid, [('employee_id', '!=', False),
                                                            ('employee_id.user_id', '!=', uid),
                                                            ('state', 'in', state_lists)], context=context)
            values.update({
                'header': 'Đăng Ký Vay Nợ Chờ Duyệt',
                'loan_datas': loan_datas
            })
        except Exception, e:
            message = e.message
            log.info('Loan Error %s' % message)
        return request.website.render("vhr_mysite.loan", values)

    @http.route(['/loan/form'], methods=['GET', 'POST'], type='http', auth='user', website=True)
    def loan_form(self, **kwargs):
        cr = request.cr
        uid = request.uid
        context = dict(request.context, show_address=True, no_tag_br=True)
        loan_pool = request.registry['vhr.pr.loan']
        loan_detail_pool = request.registry['vhr.pr.loan.detail']
        salary_pool = request.registry['vhr.pr.salary']
        all_dept_head_user_ids = loan_pool._get_all_dept_head_user_ids(cr, context=context)
        values = {
            'company_datas': [],
            'state': CLICKER_REQUEST,
            'status': 'Clicker Request',
            'header': '',
            'is_cb_user': False,
            'is_dept_head_login_user': uid in all_dept_head_user_ids,
            'is_document_submitted': False,
            'is_pay_payroll': True,
            'loan_categ_datas': [],
            'loan_amount': 0.0,
            'interest_rate': 0.0,
            'support_rate': 0.0,
            'amount': 0.0,
            'current_salary': 0.0,
            'paid': 0.0,
            'balance': 0.0,
            'pay_each_month': 0.0,
            'month_list': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
            'year_loan': datetime.now().year,
            'year_paid': datetime.now().year,
            'month_paid': 2,
            'loan_detail_datas': [],
            # MODE:
            # Create: form is used to create
            # Edit: form is used to edit
            # Read: form is used to read
            'mode': 'read',
            # action for form
            'action': '/loan/form',
            'encrypt_query_value': self.encrypt_query_value,
            'is_visible_note': False,
            'is_visible_warning': False,
        }
        try:
            mode = kwargs.get('mode', 'read')
            success_msg = self.get_message(self.decrypt_query_value(kwargs.get('success_msg', '')))
            values.update({
                'success_msg': success_msg,
            })
            loan_id = kwargs.get('id', False) and int(self.decrypt_query_value(kwargs['id'])) or False
            if request.httprequest.method == 'POST':
                dict_values = self._get_dict_value_to_create_update(kwargs)
                if mode == 'edit':
                    try:
                        loan_pool.write(cr, uid, [loan_id], dict_values, context=context)
                        success_msg = u"1"
                        return http.local_redirect('/loan/form?id=%s&success_msg=%s' % (self.encrypt_query_value(loan_id), self.encrypt_query_value(success_msg)))
                    except Exception, e1:
                        message = e1.message or e1.value
                        values.update({
                            'alert_msg': message
                        })
                        cr.rollback()
                elif mode == 'create':
                    try:
                        loan_id = loan_pool.create(cr, uid, dict_values, context=context)
                        success_msg = u"2"
                        return werkzeug.utils.redirect('/loan/form?id=%s&success_msg=%s' % (self.encrypt_query_value(loan_id), self.encrypt_query_value(success_msg)))
                    except Exception, e1:
                        message = e1.message or e1.value
                        values.update({
                            'alert_msg': message
                        })
                        cr.rollback()
            if loan_id:
                loan_datas = loan_pool.get_loan_datas(cr, uid, [('id', '=', loan_id)], context=context)
                if loan_datas:
                    loan_data = loan_datas[0]
                    loan_detail_datas = loan_detail_pool.get_loan_detail_datas(cr, uid, [('loan_id', '=', loan_id)], context=context)
                    values.update({
                        'header': 'Chi Tiết Đăng Ký Vay Nợ',
                        'id': loan_id,
                        'employee_id': loan_data.get('employee_id', ''),
                        'employee_name': loan_data.get('employee_name', ''),
                        'employee_code': loan_data.get('employee_code', ''),
                        'state': loan_data.get('state', ''),
                        'status': loan_data.get('status', ''),
                        'company_name': loan_data.get('company_name', ''),
                        'current_contract_type_name': loan_data.get('current_contract_type_name', ''),
                        'current_contract_type_id': loan_data.get('current_contract_type_id', ''),
                        'joined_date': loan_data.get('joined_date', ''),
                        'current_salary': loan_data.get('current_salary', 0.0),
                        'loan_categ_name': loan_data.get('loan_type_name', ''),
                        'required_document': loan_data.get('required_document', ''),
                        'loan_amount': loan_data.get('loan_amount', 0.0),
                        'interest_rate': loan_data.get('interest_rate', 0.0),
                        'support_rate': loan_data.get('support_rate', 0.0),
                        'amount': loan_data.get('amount', 0.0),
                        'is_document_submitted': loan_data.get('is_document_submitted', False),
                        'month_loan': loan_data.get('month_loan', 0),
                        'year_loan': loan_data.get('year_loan', 0),
                        'month_paid': loan_data.get('month_paid', 0),
                        'year_paid': loan_data.get('year_paid', 0),
                        'no_month_paid': loan_data.get('total_month_pay', 0),
                        'is_pay_payroll': loan_data.get('is_pay_payroll', False),
                        'date_of_expected_wire_transfer': loan_data.get('date_of_expected_wire_transfer', ''),
                        'paid': loan_data.get('paid', 0.0),
                        'balance': loan_data.get('balance', 0.0),
                        'pay_each_month': loan_data.get('pay_each_month', 0.0),
                        'loan_detail_datas': loan_detail_datas,
                        'loan_type_note': loan_data.get('loan_type_note', ''),
                        'loan_type_warning': loan_data.get('loan_type_warning', ''),
                        'is_visible_note': loan_data.get('is_visible_note', False),
                        'is_visible_warning': loan_data.get('is_visible_warning', False),
                    })
                    if mode == 'edit':
                        values.update({'mode': mode})
                        company_id, company_ids = loan_pool.get_company_ids(cr, uid, loan_data['employee_id'])
                        company_datas = self._get_company_datas(cr, uid, company_ids, context=context)
                        values.update({
                            'company_datas': company_datas
                        })
                        loan_categ_datas = self._get_loan_categ_datas(cr, uid, context=context)
                        values.update({
                            'loan_categ_datas': loan_categ_datas,
                            'action': '/loan/form?id=%s&mode=%s' % (self.encrypt_query_value(loan_id), kwargs['mode'])
                        })
                else:
                    values.update({'error': "Không tìm thấy Đăng Ký Vay Nợ"})
            else:
                employee_data = self._get_employee_data_from_user_id(cr, uid, context=context)
                # Check whether employee is offical
                offical_current_contracts = loan_pool.get_emp_offical_current_contracts(cr, uid, employee_data.get('id', False), context=context)
                if offical_current_contracts:
                    values.update({
                        'header': 'Đăng Ký Vay Nợ',
                        'employee_id': employee_data.get('id', ''),
                        'employee_name': employee_data.get('name', ''),
                        'employee_code': employee_data.get('code', ''),
                        'joined_date': employee_data.get('joined_date', ''),
                    })
                    employee_id = employee_data['id']
                    company_id, company_ids = loan_pool.get_company_ids(cr, uid, employee_id)
                    if company_id and company_ids:
                        company_datas = self._get_company_datas(cr, uid, company_ids, context=context)
                        values.update({
                            'company_datas': company_datas
                        })
                        offical_current_contracts = loan_pool.get_emp_offical_current_contracts(cr, uid, employee_data.get('id', False), company_id=company_id, context=context)
                        current_salary = sum(salary_pool.get_emp_current_salary(cr, uid, employee_id, com_id, context=context)['gross_salary']
                                             for com_id in company_ids)
                        values.update({
                            'current_salary': current_salary
                        })
                        contract_data = request.registry['hr.contract'].read(cr, uid, offical_current_contracts[0], ['type_id'], context=context)
                        values.update({
                            'current_contract_type_name': contract_data.get('type_id', False) and contract_data['type_id'][1] or '',
                            'current_contract_type_id': contract_data.get('type_id', False) and contract_data['type_id'][0] or '',
                        })
                    loan_categ_datas = self._get_loan_categ_datas(cr, uid, context=context)
                    values.update({
                        'loan_categ_datas': loan_categ_datas,
                        'required_document': loan_categ_datas and loan_categ_datas[0].get('required_document') or '',
                        'mode': 'create',
                        'action': '/loan/form?mode=create'
                    })
                else:
                    values.update({'error': "Bạn chưa đáp ứng điều kiện để được vay nợ theo Chính sách Công ty"})
        except Exception, e:
            message = e.message
            log.info('Loan Error %s' % message)
        return request.render("vhr_mysite.loan_form", values)

    @http.route(['/loan/approve'], methods=['GET', 'POST'], type='http', auth='user', website=True)
    def approve_loan(self, **kwargs):
        cr = request.cr
        uid = request.uid
        context = dict(request.context, show_address=True, no_tag_br=True)
        loan_pool = request.registry['vhr.pr.loan']
        success_msg = ''
        try:
            loan_id = kwargs.get('loan_id', False) and int(kwargs['loan_id']) or False
            action_call = kwargs.get('action_call', '')
            if loan_id and action_call:
                if action_call == 'submit':
                    loan_pool.action_submit_request_loan(cr, uid, [loan_id], context=context)
                    success_msg = u"3"
                elif action_call == 'approve':
                    loan_pool.action_depthead_approve_loan(cr, uid, [loan_id], context=context)
                    success_msg = u"4"
                elif action_call == 'cancel':
                    loan_pool.action_cancel_loan(cr, uid, [loan_id], context=context)
                    success_msg = u"5"
        except Exception, e:
            alert_msg = e.message
            return werkzeug.utils.redirect('/loan/form?id=%s&alert_msg=%s' % (self.encrypt_query_value(loan_id), self.encrypt_query_value(alert_msg)))
        return werkzeug.utils.redirect('/loan/form?id=%s&success_msg=%s' % (self.encrypt_query_value(loan_id), self.encrypt_query_value(success_msg)))

    def gen_string_random(self, size=35, chars=string.ascii_uppercase + string.digits):
        return ''.join(random.choice(chars) for _ in range(size))

    def encrypt_query_value(self, value):
        first = self.gen_string_random(size=593)
        last = self.gen_string_random(size=378)
        return "%s%s%s" % (first, value, last)

    def decrypt_query_value(self, query_value):
        return query_value[593:-378]

    def get_message(self, message_code):
        message_dict = {
            u'1': u"Cập nhật thành công !!!",
            u'2': u"Đăng ký thành công !!!",
            u'3': u"Đã nộp !!!",
            u'4': u"Đã duyệt !!!",
            u'5': u"Đã hủy !!!",
        }
        return message_dict.get(message_code, '')

    def _get_dict_value_to_create_update(self, post_param):
        if not post_param:
            return {}
        res = {
            'employee_id': post_param.get('employee_id', False) and int(post_param['employee_id']) or False,
            'current_contract_type': post_param.get('current_contract_type', False) and int(post_param['current_contract_type']) or False,
            'company_id': post_param.get('company_id', False) and int(post_param['company_id']) or False,
            'joined_date': post_param.get('joined_date', False) and datetime.strptime(post_param['joined_date'], '%d/%m/%Y').strftime('%Y-%m-%d') or '',
            'current_salary': post_param.get('current_salary', False) and float(post_param['current_salary']) or 0.0,
            'loan_cate_id': post_param.get('loan_cate_id', False) and int(post_param['loan_cate_id']) or False,
            'required_document': post_param.get('required_document', ''),
            'is_document_submitted': post_param.get('is_document_submitted', False) and post_param['is_document_submitted'] == 'true' or False,
            'is_pay_payroll': post_param.get('is_pay_payroll', False) and post_param['is_pay_payroll'] == 'true' or False,
            'loan_amount': post_param.get('loan_amount', False) and float(post_param['loan_amount']) or 0.0,
            'interest_rate': post_param.get('interest_rate', False) and float(post_param['interest_rate']) or 0.0,
            'support_rate': post_param.get('support_rate', False) and float(post_param['support_rate']) or 0.0,
            'amount': post_param.get('amount', False) and float(post_param['amount']) or 0.0,
            'month_loan': post_param.get('month_loan', False) and int(post_param['month_loan']) or 0,
            'year_loan': post_param.get('year_loan', False) and int(post_param['year_loan']) or 0,
            'month_paid': post_param.get('month_paid', False) and int(post_param['month_paid']) or 0,
            'year_paid': post_param.get('year_paid', False) and int(post_param['year_paid']) or 0,
            'no_month_paid': post_param.get('no_month_paid', False) and int(post_param['no_month_paid']) or 0,
            'loan_type_note': post_param.get('loan_type_note', ''),
            'loan_type_warning': post_param.get('loan_type_warning', ''),
            'is_visible_note': post_param.get('is_visible_note', False) and post_param['is_visible_note'] == 'true' or False,
            'is_visible_warning': post_param.get('is_visible_warning', False) and post_param['is_visible_warning'] == 'true' or False,
            'date_of_expected_wire_transfer': post_param.get('date_of_expected_wire_transfer', False) and datetime.strptime(post_param['date_of_expected_wire_transfer'], '%d/%m/%Y').strftime('%Y-%m-%d') or False,
        }
        return res

    def _format_date(self, date, format="%d/%m/%Y"):
        res = ''
        if not date:
            return res
        res = datetime.strptime(date, '%Y-%m-%d').strftime(format)
        return res

    def _get_employee_data_from_user_id(self, cr, uid, context=None):
        if context is None:
            context = {}
        employee_data = {
            'id': '',
            'name': '',
        }
        if not uid:
            return employee_data
        emp_pool = request.registry['hr.employee']
        related_emp_ids = emp_pool.search(cr, uid, [('user_id', '=', uid)], context=context)
        if not related_emp_ids:
            return employee_data
        emp_data = emp_pool.read(cr, uid, related_emp_ids[0], ['name', 'code', 'join_date'], context=context)
        employee_data.update({
            'id': emp_data.get('id', ''),
            'name': emp_data.get('name', ''),
            'code': emp_data.get('code', ''),
            'joined_date': emp_data.get('join_date') and self._format_date(emp_data['join_date']) or '',
        })
        return employee_data

    def _get_company_datas(self, cr, uid, company_ids, context=None):
        if context is None:
            context = {}
        company_datas = []
        if not company_ids:
            return company_datas
        com_datas = request.registry['res.company'].read(cr, uid, company_ids, ['name'], context=context)
        for com_data in com_datas:
            company_datas.append({
                'id': com_data['id'],
                'name': com_data['name'],
            })
        return company_datas

    def _get_loan_categ_datas(self, cr, uid, context=None):
        if context is None:
            context = {}
        loan_categ_datas = []
        ctx = context.copy()
        ctx.update({'search_by_type_xml_id': {'module_name': 'vhr_master_data', 'xml_id': 'data_dimension_type_LOAN_TYPE'}})
        dimension_pool = request.registry['vhr.dimension']
        loan_categ_ids = dimension_pool.search(cr, uid, [], context=ctx)
        if not loan_categ_ids:
            return loan_categ_datas
        categ_datas = dimension_pool.read(cr, uid, loan_categ_ids, ['name', 'required_document'], context=context)
        for categ_data in categ_datas:
            loan_categ_datas.append({
                'id': categ_data['id'],
                'name': categ_data['name'],
                'required_document': categ_data['required_document'],
            })
        return loan_categ_datas

    def _get_contract_type_data_from_contract_id(self, cr, uid, contract_id, context=None):
        if context is None:
            context = {}
        contract_type_data = {}
        if not contract_id:
            return contract_type_data
        ct_data = request.registry['hr.contract'].read(cr, uid, contract_id, ['type_id'], context=context)
        if not ct_data.get('type_id'):
            return contract_type_data
        contract_type_data.update({
            'id': ct_data['type_id'][0],
            'name': ct_data['type_id'][1]
        })
        return contract_type_data

    @http.route("/loan/form/contracts", type='json', auth='user')
    def get_current_contract_and_current_salary(self, **kwargs):
        result_data = {
            'contract_type_data': {
                'id': '',
                'name': '',
            },
        }
        emp_id = kwargs.get("employee_id", False)
        company_id = kwargs.get("company_id", False)
        if not emp_id or not company_id:
            return result_data
        loan_pool = request.registry['vhr.pr.loan']
        cr = request.cr
        uid = request.uid
        context = dict(request.context, show_address=True, no_tag_br=True)
        contract_ids = loan_pool.get_emp_offical_current_contracts(
            cr, uid, emp_id, company_id=company_id, context=context)
        if contract_ids:
            contract_data = request.registry['hr.contract'].read(
                cr, uid, contract_ids[0], ['type_id'], context=context)
            if contract_data.get('type_id', False):
                result_data.update({
                    'contract_type_data': {
                        'id': contract_data['type_id'][0],
                        'name': contract_data['type_id'][1],
                    }
                })
        return result_data

    @http.route("/loan/form/required_document", type='json', auth='user')
    def get_required_document(self, **kwargs):
        loan_cate_id = kwargs.get('loan_cate_id', False)
        employee_id = kwargs.get('employee_id', False)
        joined_date = kwargs.get('joined_date', False)
        loan_id = kwargs.get('loan_id', False)
        res = {
            'required_document': '',
            'error': '',
            'loan_type_warning': '',
            'is_visible_note': False,
        }
        if not loan_cate_id or not employee_id or not joined_date:
            return res
        loan_registry = request.registry['vhr.pr.loan']
        joined_date = datetime.strptime(joined_date, '%d/%m/%Y').strftime('%Y-%m-%d')
        cr = request.cr
        uid = request.uid
        context = dict(request.context, show_address=True, no_tag_br=True)
        if loan_registry._is_old_loan_existed(cr, uid, loan_cate_id, employee_id, joined_date, loan_id=loan_id, state='', context=context):
            if loan_registry._is_old_loan_existed(cr, uid, loan_cate_id, employee_id, joined_date, loan_id=loan_id, state=CLICKER_REQUEST, context=context):
                res.update({'error': u'Bạn đang có một yêu cầu vay nợ với mục đích này trong trạng thái %s' % (CLICKER_REQUEST)})
                return res
            res.update({'loan_type_warning': u'Bạn đã vay  1 lần với mục đích này, theo policy bạn không dược vay nữa'})
        if loan_registry._is_loan_type_difference(cr, uid, loan_cate_id, context=context):
            res.update({'is_visible_note': True})
        loan_cate_data = request.registry['vhr.dimension'].read(cr, uid, loan_cate_id, ['required_document'], context=context)
        res.update({
            'required_document': loan_cate_data.get('required_document', '')
        })
        return res
