# -*- coding: utf-8 -*-
import json
import simplejson
from itertools import islice
import base64
import logging
import time
import urllib2

import werkzeug.utils

from openerp import http
from openerp.addons.web.http import request
from openerp import SUPERUSER_ID
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.addons.web.controllers import main
from openerp.addons.website.controllers.main import Website
from openerp.addons.web.controllers.main import Session
from openerp.addons.web.controllers.main import Home
from openerp.addons.web.controllers.main import ensure_db
from openerp.addons.web.controllers.main import login_redirect
from openerp.addons.audittrail  import audittrail
from openerp.addons.report.controllers.main import ReportController
from openerp.addons.web.controllers.main import Reports

from datetime import datetime
from datetime import date

from openerp.http import serialize_exception as _serialize_exception

import functools

import string
import random


log = _logger = logging.getLogger(__name__)

ACTIVE_STRING = ['1', 'TRUE', 'true', 'True']


def concat(ls):
    """ return the concatenation of a list of iterables """
    res = []
    for l in ls: res.extend(l)
    return res

'''
    Rewrite function redirect_with_hash for the security
    For backend:
        - Group user_back_end
        - not belong above group but allow_backend = True
    For Frontend:
        - detect link: 
            - backend link -> redirect to fronend
            - frontend link -> check pemission
'''

def get_implied(group_objs):
    implied_list = []
    for group_obj in group_objs:
        if group_obj and not group_obj.implied_ids:
            implied_list.append(group_obj.id)
        else:
            get_implied(group_obj.implied_ids)
    
    return implied_list

def check_permission():
    if request.session.uid == SUPERUSER_ID:
        return True
    res_user_pool = request.registry['res.users']
    cr, uid = request.cr, request.session.uid
    # Check allow_backend or not:
#     allow_backend = res_user_pool.search(cr, uid, [['allow_backend', '=', True],
#                                                    ['id', '=', uid]])
#     if allow_backend:
#         return True
    
    # If not allow_backend, check group backend_user
    user_obj = res_user_pool.browse(cr, uid, uid)
    group_objs = user_obj and user_obj.groups_id or []
    group_ids = get_implied(group_objs)
    backend_group_id = request.registry['ir.model.data'].xmlid_to_res_id(
        cr, uid, 'vhr_mysite.group_backend_user')
    
    if backend_group_id in group_ids:
        return True
    return False

def check_demo_users():
    if request.session.uid == SUPERUSER_ID:
        return True
    res_user_pool = request.registry['res.users']
    cr, uid = request.cr, request.session.uid
    
    # get group frontend demo user
    allow_frontend_users = []
    frontend_demo_id = request.registry['ir.model.data'].xmlid_to_res_id(
        cr, uid, 'vhr_mysite.group_frontend_demo')
    if frontend_demo_id:
        frontend_group_users = request.registry['res.groups'].read(
            cr, uid, frontend_demo_id, ['users'])
        if frontend_group_users.get('users', []):
            allow_frontend_users = frontend_group_users['users']
    if uid in allow_frontend_users:
        return True
    return False

# def redirect_with_hash(url, code=303):
#         # Most IE and Safari versions decided not to preserve location.hash upon
#         # redirect. And even if IE10 pretends to support it, it still fails
#         # inexplicably in case of multiple redirects (and we do have some).
#         # See extensive test page at http://greenbytes.de/tech/tc/httpredirects/
#         
#         # If check_pemission == True keep the function work like origin
#         if check_permission():
#             if request.httprequest.user_agent.browser in ('firefox',):
#                 return werkzeug.utils.redirect(url, code)
#             return "<html><head><script>window.location = '%s' + location.hash;</script></head></html>" % url
#         # If user not pass check permission, we detect the link for furture function
#         # If link for frontend update the context
#         return "<html><head><script>window.location = '%s' + location.hash;</script></head></html>" % '/'
# 
# http.redirect_with_hash = redirect_with_hash

def login_redirect():
    url = '/web/login?'
    if request.debug:
        url += 'debug&'
    return """<html><head><script>
        window.location = '%sredirect=' + encodeURIComponent(window.location);
    </script></head></html>
    """ % (url,)
    
main.login_redirect = login_redirect

def content_disposition(filename):
    filename = filename.encode('utf8')
    escaped = urllib2.quote(filename)
    browser = request.httprequest.user_agent.browser
    version = int((request.httprequest.user_agent.version or '0').split('.')[0])
    if browser == 'msie' and version < 9:
        return "attachment; filename=%s" % escaped
    elif browser == 'safari':
        return "attachment; filename=%s" % filename
    else:
        return "attachment; filename*=UTF-8''%s" % escaped

def serialize_exception(f):
    @functools.wraps(f)
    def wrap(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception, e:
            _logger.exception("An exception occured during an http request")
            se = _serialize_exception(e)
            error = {
                'code': 200,
                'message': "OpenERP Server Error",
                'data': se
            }
            return werkzeug.exceptions.InternalServerError(simplejson.dumps(error))
    return wrap

class MysiteHome(Home):

    @http.route('/web', type='http', auth="none")
    def web_client(self, s_action=None, **kw):
        ensure_db()

        if request.session.uid:
            # Check permission when user trying to go to the backend
            if not check_permission():
                # if user was allowed to frontend (demo user)
                return werkzeug.utils.redirect('/mysite/', 303)
            if kw.get('redirect'):
                return werkzeug.utils.redirect(kw.get('redirect'), 303)
            return request.render('web.webclient_bootstrap')
        else:
            return login_redirect()


class MysiteSession(Session):
    
    @http.route('/web/session/logout', type='http', auth="none")
    def logout(self, redirect='/'):
        request.session.logout(keep_db=True)
        return werkzeug.utils.redirect(redirect, 303)

class Mysite(Website):

    @http.route(['/', '/mysite/'], type='http', auheth="user", website=True)
    def index(self, **kw):
        context = dict(request.context)
        cr, uid = request.cr, request.uid
        hr_obj = request.registry['hr.employee']
        
#         if not check_demo_users():
#             return request.render(
#                 'vhr_mysite.my_profile_demo',
#                 {'demo_page': True, 'check_permission': check_permission()})

        employee_ids = hr_obj.search(cr, uid, [('user_id', '=', uid)], context=context)
        if employee_ids:
            hr_temp_obj = request.registry['vhr.employee.temp']
            values = {'is_cb': False}

            employe_obj = hr_obj.browse(cr, uid, employee_ids[0], context)
            
            groups = request.registry['res.users'].get_groups(cr, uid)
            cb_groups = ['hrs_group_system','vhr_cb']
            if set(cb_groups).intersection(groups):
                values['is_cb'] = True
            
            check = hr_temp_obj.check_editable(request.cr, request.uid, employee_ids[0])
            if employe_obj:
                values.update({
                    'personal_documents': employe_obj.personal_document or [],
                    'bank_accounts': employe_obj.bank_ids or [],
                    'certificates': employe_obj.certificate_ids or [],
                    'relation_partners': employe_obj.relation_partners or [],
                    'my_title': 'Mysite - ' + employe_obj.name,
                    'format_date': self.format_date,
                    'get_gender_name': self.get_gender_name,
                    'get_marital_name': self.get_marital_name,
                    'get_document_status': self.get_document_status,
                    'my_editable': check and True or False,
                    'allow_backend': check_permission(),
                    'my_employee_id': employe_obj.id,
                    'gen_string_random': self.gen_string_random,
                })
                
                # Check holidays
                hr_holidays = request.registry['hr.holidays']
                hr_holidays_status = request.registry['hr.holidays.status']
                current_year = datetime.now().year
                holiday_status_code = request.registry['ir.config_parameter'].get_param(
                    cr, uid, 'ts.leave.type.default.code') or False
                
                holiday_ids = hr_holidays.search(
                    cr, uid,
                    [('employee_id', '=', employee_ids[0]),
                     ('year', '=', current_year),
                     ('holiday_status_id.code', '=', holiday_status_code),
                     ('type', '=', 'add')])
                
                if holiday_ids:
                    holidays = hr_holidays.browse(cr, uid, holiday_ids[0])
                    values.update({'holiday': holidays})
            # Check state of request
            # if state is draft mean return request
            # if state is verified mean success 
            # Example how to use notice:
#                     'my_notices': ['lalala', 'hahaha'],
#                     'my_suggestion_notices': ['suggest 1', 'suggest 1'],
#                     'my_system_notices': ['System 1', 'system 2'],
            # get message from system
            draft_result, message1 = self.get_mynotice(cr, uid, 'draft', employee_ids[0])
            verified_result, message2 = self.get_mynotice(cr, uid, 'verified', employee_ids[0])
            
            if draft_result:
                values.update({
                    'show_notice': True,
                    'my_system_notices': [message1]})
            if verified_result:
                values.update({
                    'show_notice': True,
                    'my_notices': [message2]})

            return request.render('vhr_mysite.my_profile', values)
        return http.local_redirect('/web', query=request.params, keep_hash=True)

    def get_mynotice(self, cr, uid, state, emp_id):
        if not state or not emp_id:
            return False, ''
        hr_temp_obj = request.registry['vhr.employee.temp']
        emp_temp_ids = hr_temp_obj.search(
            cr, uid, [['employee_id', '=', emp_id],
                      ['state', '=', state],
                      ['show_message', '=', True]])
        if emp_temp_ids:
            message = ''
            if state == 'draft':
                emp_temp = hr_temp_obj.browse(cr, uid, emp_temp_ids[0])
                message = u'Yêu cầu thay đổi thông tin của bạn bị trả lại vì lý do:'
                message = u' '.join((message, emp_temp.return_reason_note)).encode('utf-8').strip()
            if state == 'verified':
                message = u'Yêu cầu thay đổi thông tin của bạn đã được chấp nhận.'+ \
                    u' Hãy kiểm tra lại các thông tin bên dưới.'
                # update show message, make sure message only show one time
                hr_temp_obj.write(cr, uid, emp_temp_ids, {'show_message': False})
            return True, message
        return False, ''

    def format_date(self, date):
        if date:
            return datetime.strptime(date, '%Y-%m-%d').strftime('%d/%m/%Y')
        return date

    def get_gender_name(self, status, get_key=False):
        gender = {
            'male': u'Nam',
            'female': u'Nữ',
        }
        
        return self.get_select_value(gender, status, get_key)

    def get_marital_name(self, status, get_key=False):
        relation = {
            'single': u'Độc Thân',
            'married': u'Đã Lập Gia Đình',
            'divorced': u'Đã Ly Hôn',
            'widowed': u'Góa Vợ/Chồng',
        }
        
        return self.get_select_value(relation, status, get_key)

    def get_document_status(self, status, get_key=False):
        state = {
            'new': u'Cấp Mới',
            'update': u'Cập Nhật',
            'move': u'Chuyển từ công ty cũ sang',
        }
        
        return self.get_select_value(state, status, get_key)
    
    def get_mode(self, status, get_key=False):
        mode = {
            'new': u'Tạo mới',
            'update': u'Cập Nhật',
        }
        
        return self.get_select_value(mode, status, get_key)

    def get_select_value(self, select_dict, status, get_key=False):
        if not select_dict:
            return ''

        for key, val in select_dict.iteritems():
            if not get_key:
                if key == status:
                    return val
            else:
                if val == status:
                    return key
        return ''

    @http.route('/mysite/get_personal_info', type='json', auth="user", website=True)
    def get_personal_info(self, **kw):
        
        res = {}
        cr, uid = request.cr, request.uid
        employee_id = kw.get('employee_id', False)
        check = request.registry['vhr.employee.temp'].check_editable(
            request.cr, request.uid, employee_id)
        if check:
            county_pool = request.registry['res.country']
            city_pool = request.registry['res.city']
            district_pool = request.registry['res.district']
            office_pool = request.registry['vhr.office']
            document_type_pool = request.registry['vhr.personal.document.type']
            school_pool = request.registry['vhr.school']
            degree_pool = request.registry['hr.recruitment.degree']
            relation_pool = request.registry['vhr.relationship.type']
            bank_pool = request.registry['res.bank']
            bank_branch_pool = request.registry['res.branch.bank']
    
            ''' All data for frontend'''
            res.update({
                'cities': self._get_info_frontend(cr, uid, city_pool),
                'countries': self._get_info_frontend(cr, uid, county_pool),
                'districts': self._get_info_frontend(cr, uid, district_pool),
                'ethnices': self._get_info_frontend(cr, uid, None, 'NATION'),
                'religions': self._get_info_frontend(cr, uid, None, 'RELIGION'),
                'offices': self._get_info_frontend(cr, uid, office_pool),
                'doc_types': self._get_info_frontend(cr, uid, document_type_pool),
                'schools': self._get_info_frontend(cr, uid, school_pool),
                'degrees': self._get_info_frontend(cr, uid, degree_pool),
                'faculties': self._get_info_frontend(cr, uid, None, 'FACULTY'),
                'specialities': self._get_info_frontend(cr, uid, None, 'SPECIALITY'),
                'relationship': self._get_info_frontend(cr, uid, relation_pool),
                'banks': self._get_info_frontend(cr, uid, bank_pool),
                'bank_branchs': self._get_info_frontend(cr, uid, bank_branch_pool),
            })
        else:
            return False
        return res
    
    @http.route('/mysite/get_info_frontend', type='json', auth="user", website=True)
    def my_get_info_frontend(self, **kw):
        pool = kw.get('pool', False) and request.registry[kw['pool']] or False
        code = kw.get('code', False)
        domain = kw.get('domain', False)
        
        if not pool:
            return False
        cr, uid = request.cr, request.uid
        
        return self._get_info_frontend(cr, uid, pool, code, domain)

    def _get_info_frontend(self, cr, uid, pool, code=None, domain=None, fields=None, order='name asc'):
        if not order:
            order = 'name asc'
        if not fields:
            fields = ['id', 'name']
        if not code:
            if not domain:
                domain = []
            return pool.search_read(cr, uid, domain=domain, fields=fields, order=order)
#             return pool.read(cr, uid, pool_ids, ['id', 'name'], order=order)
        else:
            dimension_pool = request.registry['vhr.dimension']
            dimension_type_pool = request.registry['vhr.dimension.type']

            dimension_domain = []
            dimension_type_id = dimension_type_pool.search(cr, uid, [('code', '=', code)])[0]
            if dimension_type_id:
                dimension_domain.append(['dimension_type_id', '=', dimension_type_id])
            return dimension_pool.search_read(cr, uid, domain=dimension_domain, fields=fields, order=order)
#             return dimension_pool.read(cr, uid, dimension_ids, )

    ''' RETURN FRESHER '''
    def _check_contract_not_fresher(self, cr, uid, user_id, context=None):
        if not user_id:
            return False
        if context is None:
            context = {}

        hr_obj = request.registry['hr.employee']
        contract_obj = request.registry['hr.contract']
        contract_type_obj = request.registry['hr.contract.type']
        
        # Get contract type Fresher
        freser_type_ids = contract_type_obj.search(cr, uid, [('code', '=', 'FS')])
        
        employee_ids = hr_obj.search(
            cr, uid, [('user_id', '=', user_id)], context=context)
        if employee_ids:
            # Get current contract
            today = datetime.today().strftime('%Y-%m-%d')
            curent_contract_ids = contract_obj.search(
                cr, uid,[('employee_id', '=', employee_ids[0]),
                         ('is_main', '=', True),
                         ('date_start', '<=', today),
                         ('state', '=', 'signed'),
                         # Get hop dong ko phai la fresher
                        ('type_id', 'not in', freser_type_ids),
                         '|', '|', ('liquidation_date', '>=', today),
                         '&', ('date_end', '>=', today), ('liquidation_date', '=', False),
                         '&', ('date_end', '=', False), ('liquidation_date', '=', False)
                         ], order='date_start desc')
            if not curent_contract_ids:
                return False # FRESHER = True
            return True # FRESHER = False
#             for contract in contract_obj.browse(cr, uid, curent_contract_ids):
#                 if contract.type_id and contract.type_id.contract_type_group_id:
#                     if contract.type_id.contract_type_group_id.is_offical:
#                         code_probation = request.registry['ir.config_parameter'].get_param(
#                             cr, uid, 'vhr_human_resource_probation_contract_type_group_code') or 0
#                         if contract.type_id.contract_type_group_id.code == code_probation:
#                             return True # not_offical = True
#                     else:
#                         return True # not_offical = True
        return False # FRESHER = True

    ''' RETURN OFFICIAL '''
    def _check_contract_official(self, cr, uid, user_id, context=None):
        if not user_id:
            return False
        if context is None:
            context = {}

        hr_obj = request.registry['hr.employee']
        contract_obj = request.registry['hr.contract']
        contract_type_obj = request.registry['hr.contract.type']
        contract_type_group_obj = request.registry['hr.contract.type.group']
        
        # Get contract type Fresher
        official_type_ids = contract_type_obj.search(cr, uid, [('contract_type_group_id.is_offical', '=', True)])
        
        employee_ids = hr_obj.search(
            cr, uid, [('user_id', '=', user_id)], context=context)
        if employee_ids:
            # Get current contract
            today = datetime.today().strftime('%Y-%m-%d')
            curent_contract_ids = contract_obj.search(
                cr, uid,[('employee_id', '=', employee_ids[0]),
                         ('is_main', '=', True),
                         ('date_start', '<=', today),
                         ('state', '=', 'signed'),
                         # Get hop dong ko phai la fresher
                        ('type_id', 'in', official_type_ids),
                         '|', '|', ('liquidation_date', '>=', today),
                         '&', ('date_end', '>=', today), ('liquidation_date', '=', False),
                         '&', ('date_end', '=', False), ('liquidation_date', '=', False)
                         ], order='date_start desc')
            if curent_contract_ids:
                return True # official = True
        return False # official = False

    ''' RETURN Collaborator 1'''
    def _check_contract_collaborator_by_title(self, cr, uid, user_id, context=None):
        if not user_id:
            return False
        if context is None:
            context = {}

        hr_obj = request.registry['hr.employee']
        
        employee_ids = hr_obj.search(
            cr, uid, [('user_id', '=', user_id)], context=context)
        if employee_ids:
            employee = hr_obj.browse(cr, uid, employee_ids[0], context=context)
            if employee and employee.title_id and employee.title_id.name == 'Collaborator 1':
                return True
        return False

    '''
    Check group C&B 
    '''
    def _check_group_esop(self, cr, uid, context=None):
        if context is None:
            context = {}
        res_group_obj = request.registry['res.groups']
        model_data_obj = request.registry['ir.model.data']
        payroll_group_id = model_data_obj.xmlid_to_res_id(
            cr, uid, 'vhr_cnb_manager')
        
        if payroll_group_id:
            payroll_group = res_group_obj.read(cr, uid, payroll_group_id, ['users'], context=context)
            if payroll_group and uid in payroll_group.get('users', []):
                return True
        return False
    
    '''
    Check group C&B Payroll
    '''
    def _check_group_payroll(self, cr, uid, context=None):
        if context is None:
            context = {}
        res_group_obj = request.registry['res.groups']
        model_data_obj = request.registry['ir.model.data']
        payroll_group_id = model_data_obj.xmlid_to_res_id(
            cr, uid, 'vhr_payroll.vhr_cnb_payroll')
        
        if payroll_group_id:
            payroll_group = res_group_obj.read(cr, uid, payroll_group_id, ['users'], context=context)
            if payroll_group and uid in payroll_group.get('users', []):
                return True
        return False
    
    '''
    Check group C&B
    '''
    def _check_group_cb(self, cr, uid, context=None):
        if context is None:
            context = {}
        res_group_obj = request.registry['res.groups']
        model_data_obj = request.registry['ir.model.data']
        cb_group_id = model_data_obj.xmlid_to_res_id(
            cr, uid, 'vhr_human_resource.vhr_cb')
        
        if cb_group_id:
            cb_group = res_group_obj.read(cr, uid, cb_group_id, ['users'], context=context)
            if cb_group and uid in cb_group.get('users', []):
                return True
        return False
    
    '''
    Check group C&B Profile
    '''
    def _check_group_cb_profile(self, cr, uid, context=None):
        if context is None:
            context = {}
        res_group_obj = request.registry['res.groups']
        model_data_obj = request.registry['ir.model.data']
        cb_group_id = model_data_obj.xmlid_to_res_id(
            cr, uid, 'vhr_human_resource.vhr_cb_profile')
        
        if cb_group_id:
            cb_group = res_group_obj.read(cr, uid, cb_group_id, ['users'], context=context)
            if cb_group and uid in cb_group.get('users', []):
                return True
        return False

    '''
    GET get_prev_salary
    '''
    def get_prev_salary(self, payslip, field=None):
        if not payslip or field is None:
            return 0
        
        context = dict(request.context)
        cr, uid = request.cr, request.uid
        current_year = payslip.year or ''
        current_month = payslip.month or ''

        prev_year = current_year
        prev_month = str(int(current_month) - 1)
        if current_month == '1':
            prev_month = '12'
            prev_year = str(int(current_year) - 1)

        employee_id = payslip.employee_id and payslip.employee_id.id or False
        
        domain = [['employee_id', '=', employee_id],
                  ['year', '=', prev_year],
                  ['month', '=', prev_month]]
        
        
        payslips = request.registry['vhr.payslip'].search_read(
            cr, uid, domain=domain, fields=[field], context=context)
        if payslips:
            return payslips[0][field]
        return 0

    '''
    GET Employee from employee code
    '''
    def _get_emloyee_from_code(self, cr, uid, employee_code, context=None):
        if context is None:
            context = {}
        if employee_code:
            employee_code = employee_code.replace(" ", "")
            hr_employee = request.registry['hr.employee']
            resource_resource = request.registry['resource.resource']

            resource_ids = resource_resource.search(cr, uid, [('code', '=', employee_code),])
            if resource_ids:
                employee_ids = hr_employee.search(cr, uid, [('resource_id', '=', resource_ids[0])])
                if employee_ids:
                    employee = hr_employee.browse(cr, uid, employee_ids[0], context)
                    return employee
        return False

    @http.route('/mysite/search', type='http', auth="user", website=True, keep_hash=True)
    def mysite_search(self, **kw):
        
        context = dict(request.context)
        cr, uid = request.cr, request.uid
        hr_obj = request.registry['hr.employee']
        values = {'show_button_toggle_sidebar': True,
                  'results': [],
                  'format_date': self.format_date,
                  # Set select tag = false
                  'selected_div': False,
                  'selected_dept': False,
                  'selected_team': False,
                  'is_cb': False}
        
        # Get parameters
        query = request.params.get('q')
        div = request.params.get('div')
        dept = request.params.get('dept')
        team = request.params.get('team')
        
        # Check permission to search
        check_not_fresher = self._check_contract_not_fresher(cr, uid, request.session.uid)
        if not check_not_fresher:
            values.update({
                'show_notice': True,
                'my_system_notices': [u'Hiện tại bạn chưa được sử  dụng chức năng tìm kiếm'],
                'results': []})
            return request.render('vhr_mysite.my_search', values)
        
        # Set employee_ids which have searched = empty list
        employee_ids = []
        keyword = []
        domain = []
        
        if query:
            domain += ['|', '|',
                          ['name_related', 'ilike', query],
                          ['code', 'ilike', query],
                          ['login', 'ilike', query]]
            keyword.append(query)

        if div:
            # add the domain
            domain.append(['division_id', 'child_of', int(div)])
            # Add selected div
            values['selected_div'] = int(div)
            div_name = self._mysite_search_dept(cr, uid, 'div', None, values['selected_div'])
            div_name = div_name and div_name[0] or {}
            if div_name:
                keyword.append(u'Bộ phận: ' + div_name['code'] + ' - ' + div_name['name'])
        # The same with search div
        if dept:
            domain.append(['department_id', '=', int(dept)])
            values['selected_dept'] = int(dept)
            dept_name = self._mysite_search_dept(cr, uid, 'dept', None, values['selected_dept'])
            dept_name = dept_name and dept_name[0] or {}
            if dept_name:
                keyword.append(u'Phòng: ' + dept_name['code'] + ' - ' + dept_name['name'])
        # The same with search div
        if team:
            domain.append(['team_id', '=', int(team)])
            values['selected_team'] = int(team)
            team_name = self._mysite_search_dept(cr, uid, 'team', None, values['selected_team'])
            team_name = team_name and team_name[0] or {}
            if team_name:
                keyword.append(u'Nhóm: ' + team_name['code'] + ' - ' + team_name['name'])
        
        # Add keyword
        if keyword:
            values.update({
                'keyword': ', '.join(keyword)
            })
        
        # if search mode = department
        if domain:
            employee_ids = hr_obj.search(cr, SUPERUSER_ID, domain, context=context)
        
        # Get the employees
        if employee_ids:
            emloyees = hr_obj.browse(cr, uid, employee_ids, context=context)
            values.update({
                'results': emloyees,
            })

        # Get list div, dept, team by condition
        divisions = self._mysite_search_dept(cr, uid, 'div')
        if div:
            depts = self._mysite_search_dept(cr, uid, 'dept', int(div))
        else:
            depts = self._mysite_search_dept(cr, uid, 'dept')
        
        if dept:
            teams = self._mysite_search_dept(cr, uid, 'team', int(dept))
        else:
            teams = self._mysite_search_dept(cr, uid, 'team')

        values.update({'divisions': divisions or [],
                       'depts': depts,
                       'teams': teams})
        
        return request.render('vhr_mysite.my_search', values)

    def _mysite_search_dept(self, cr, uid, type, parent_id=None, _id=None):
        context = dict(request.context)
        hr_dept_obj = request.registry['hr.department']
        dimen_type = request.registry['vhr.dimension.type']
        # Remove GE and G6
        domain = [['active', '=', 't'], ['code', '!=', 'GE'], ['code', '!=', 'G6']]
        if parent_id:
            domain.append(['parent_id', '=', parent_id])
        if _id:
            domain.append(['id', '=', _id])
        fields = ['name', 'code']
        
        dimension_type_ids = dimen_type.search(cr, uid, [('code', '=', 'HIERARCHICAL_CHART')])
        if dimension_type_ids:
            hierachical_ids = request.registry['vhr.dimension'].search(
                    cr, uid, [('code', '=', 'ORGCHART'), ('dimension_type_id', '=', dimension_type_ids[0])])
            
            domain.append(('hierarchical_id', 'in', hierachical_ids))
        
        if type:
            # Type = division
            if type == 'div':
                domain.append(['organization_class_id', 'in', [2, 5]])
            # Type = department
            elif type == 'dept':
                domain.append(['organization_class_id', 'in', [3, 6]])
            # Type = team
            else:
                domain.append(['organization_class_id', '=', 4])
        # Default search division
        else:
            domain.append(['organization_class_id', 'in', [2, 5]])
        res = hr_dept_obj.search_read(cr, uid, domain, fields, order='code asc', context=context)
        
        return res

    @http.route('/mysite/search/dept', type='json', auth="user", website=True)
    def mysite_search_dept(self, **kw):
        context = dict(request.context)
        cr, uid = request.cr, request.uid
        hr_dept_obj = request.registry['hr.department']
        dimen_type = request.registry['vhr.dimension.type']
        domain = [['active', '=', 't']]
        type = kw.get('type', False)
        parent_id = kw.get('parent_id', False)
        fields = ['name', 'code']
        
        dimension_type_ids = dimen_type.search(cr, uid, [('code', '=', 'HIERARCHICAL_CHART')])
        if dimension_type_ids:
            hierachical_ids = request.registry['vhr.dimension'].search(
                    cr, uid, [('code', '=', 'ORGCHART'), ('dimension_type_id', '=', dimension_type_ids[0])])
            
            domain.append(('hierarchical_id', 'in', hierachical_ids))
        
        if type:
            # Type = division
            if type == 'div':
                domain.append(['organization_class_id', 'in', [2, 5]])
            # Type = department
            elif type == 'dept':
                domain.append(['organization_class_id', 'in', [3, 6]])
            # Type = team
            else:
                domain.append(['organization_class_id', '=', 4])
        # Default search division
        else:
            domain.append(['organization_class_id', 'in', [2, 5]])
        if parent_id:
            domain.append(['parent_id', '=', parent_id])
        
        res = hr_dept_obj.search_read(cr, uid, domain, fields, order='code asc', context=context)
        return res
    
    @http.route('/mysite/check_editable', type='json', auth="user", website=True)
    def check_editable(self, **kw):
        if not kw.get('employee_id', False):
            return False
        return request.registry['vhr.employee.temp'].check_editable(
            request.cr, request.uid, kw['employee_id'])

    @http.route('/mysite/set_personal_info', type='json', auth="user", website=True)
    def set_personal_info(self, **kw):

        employee_id = kw.get('employee_id', False)
        
        '''
            Check the key value (employee_id)
        '''

        if employee_id:
            context = dict(request.context)
            cr, uid = request.cr, request.uid
            emp_temp_pool = request.registry['vhr.employee.temp']
            cer_temp_pool = request.registry['vhr.certificate.info.temp']
            partner_temp_pool = request.registry['vhr.employee.partner.temp']
            doc_temp_pool = request.registry['vhr.personal.document.temp']
            bank_temp_pool = request.registry['vhr.res.partner.bank.temp']
            
            '''
                Check the temp employee (request) exist or not
            '''
            emp_temp_ids = emp_temp_pool.check_verified(
                cr, uid, employee_id, context
            )

            '''
                Collect data from request
            '''
            employee_data = kw.get('employee_data', {})
            contact_data = kw.get('contact_data', {})
            certificate_data = kw.get('certificate_data', [])
            partner_data = kw.get('partner_data', [])
            document_data = kw.get('document_data', [])
            bank_data = kw.get('bank_data', [])
            
            # Remove validate list null
            certificate_data.remove([])
            partner_data.remove([])
            document_data.remove([])
            bank_data.remove([])
            
            if not emp_temp_ids: # If not create a new temp employee
                if employee_data or contact_data or \
                    certificate_data or partner_data or \
                    document_data or bank_data: #If data is null return False and do not create employee temp
                    emp_temp_ids = [emp_temp_pool.create(
                                        cr, uid, {'employee_id': employee_id}, context)
                                    ]
                else:
                    return False
            
            # Update personal info
            vals = dict(list(employee_data.items()) + list(contact_data.items()))
            vals.update({
                'state': 'waiting'
            })
            emp_temp_pool.write(cr, uid, emp_temp_ids, vals, context=context)
            
            # Update extra info
            for emp_temp_id in emp_temp_ids:
                if certificate_data:
                    self._create_extra_temp_info(
                        cr, uid, emp_temp_id, cer_temp_pool,
                        certificate_data, 'vhr_certificate_info_id', context=context)
                if partner_data:
                    self._create_extra_temp_info(
                        cr, uid, emp_temp_id, partner_temp_pool,
                        partner_data, 'relation_partner_id', context=context)
                if document_data:
                    self._create_extra_temp_info(
                        cr, uid, emp_temp_id, doc_temp_pool,
                        document_data, 'personal_document_id', context=context)
                if bank_data:
                    self._create_extra_temp_info(
                        cr, uid, emp_temp_id, bank_temp_pool,
                        bank_data, 'res_bank_id', context=context)
        return True

    @http.route('/mysite/set_my_avatar', type='json', auth="user", website=True)
    def set_my_avatar(self, **kw):
        cr, uid, context = request.cr, request.uid, request.context
        context = context or {}
        hr_emp_obj = request.registry['hr.employee']

        emp_ids = hr_emp_obj.search(
            cr, uid, [['user_id', '=', uid]], context=context)
        image = kw.get('image', False)

        if emp_ids and image:
            context = dict(request.context)
            cr, uid = request.cr, request.session.uid
            hr_obj = request.registry['hr.employee']
   
#             audittrail.execute_cr(cr, uid, hr_obj._name, 'write', [employee_id], {'image': ''}, context)
            return hr_obj.write(cr, uid, emp_ids[0], {'image': image})
        return False

    def _create_extra_temp_info(self, cr, uid, emp_temp_id, pool,
                                extra_data, relation_field, context=None):
        if not emp_temp_id or not pool or not extra_data:
            return
        if not context:
            context = {}

        for data in extra_data:
            # There is origin_id mean mode = update
            if data.get('origin_id', False):
                
                # Remove update_id if exists
                if data.get('update_id', False):
                    del data['update_id']
                
                origin_id = int(data['origin_id'])
                # Check update request
                check_ids = pool.search(cr, uid, [['origin_id', '=', origin_id],
                                                  ['employee_temp_id', '=', emp_temp_id]])
                # if check_ids -> update request
                if check_ids:
                    pool.write(cr, uid, check_ids, data, context=context)
                # if not check_ids -> create request mode = update
                else:
                    data.update({
                        relation_field: origin_id,
                        'employee_temp_id': emp_temp_id,
                        'mode': 'update'
                    })
                    pool.create(cr, uid, data, context=context)
            # If not origin_id -> mode = new
            else:
                # A special case for quick update
                # When user create new lines and there is no origin_id
                # But we tracking by update_id
                if data.get('update_id', False):
                    update_id = int(data['update_id'])
                    del data['update_id']
                    pool.write(cr, uid, [update_id], data, context=context)
                    return True
                
                # Check duplicate value
                check_domain = [(key, '=', val) for key, val in data.iteritems()]
                check_ids = pool.search(cr, uid, check_domain)
                if not check_ids:
                    data.update({
                        'employee_temp_id': emp_temp_id,
                        'mode': 'new'
                    })
                    pool.create(cr, uid, data, context=context)
        return True

    '''
    Search employee
    '''
    def _search_employee(self, cr, uid, query, context=None):
        if context is None:
            context = {}
        if not query:
            return False
        hr_obj = request.registry['hr.employee']
        employee = False
        # Tim kiem bang ma nhan vien
        if '-' in query:
            query = query.upper()
            employee = self._get_emloyee_from_code(cr, uid, query, context=context)
        # Neu ko co thi tim kiem theo domain account
        else:
            query = query.lower()
            employee_ids = hr_obj.search(cr, uid, [('login', '=', query)])
            # Get employee sau do tim employee trong total income
            if employee_ids:
                employee = hr_obj.browse(cr, uid, employee_ids[0], context=context)
        return employee

    @http.route(['/mysite/request'], type='http', auth="user", website=True)
    def my_request_info(self, **kw):
        context = dict(request.context)
        cr, uid = request.cr, request.uid
        hr_obj = request.registry['hr.employee']

        employee_ids = hr_obj.search(cr, uid, [('user_id', '=', uid)], context=context)
        if employee_ids:
            hr_temp_obj = request.registry['vhr.employee.temp']
            res = []

            employee_temp_ids = hr_temp_obj.search(
                cr, uid, [('employee_id', '=', employee_ids[0])], context=context)
            temp_employee_objs = hr_temp_obj.browse(cr, uid, employee_temp_ids, context)

            for employe_obj in temp_employee_objs:
                res.append({
                    'personal_documents': employe_obj.personal_document_temp_ids or [],
                    'bank_accounts': employe_obj.bank_ids or [],
                    'certificates': employe_obj.certificate_ids or [],
                    'relation_partners': employe_obj.relation_partner_temp_ids or [],
                    'my_title': 'Mysite - ' + employe_obj.name,
                    'state': employe_obj.state,
                    'id': str(employe_obj.id),
                    'request_date': self.format_date(employe_obj.request_date),
                    'my_employee': employe_obj,
                })

            return request.render('vhr_mysite.my_profile_temp',
                {'res': res,
                 'format_date': self.format_date,
                 'get_gender_name': self.get_gender_name,
                 'get_marital_name': self.get_marital_name,
                 'get_document_status': self.get_document_status,
                 'get_mode': self.get_mode,})
        return http.local_redirect('/web', query=request.params, keep_hash=True)

    @http.route(['/mysite/working'], type='http', auth="user", website=True)
    def my_working_history_info(self, **kw):
        context = dict(request.context)
        cr, uid = request.cr, request.uid
        hr_obj = request.registry['hr.employee']
        res = {}
        
        employee_ids = hr_obj.search(
            cr, uid, [('user_id', '=', uid)], context=context)
        if employee_ids:
            wk_rec_obj = request.registry['vhr.working.record']
            wk_rec_ids = wk_rec_obj.search(
                cr, uid, [['employee_id', '=', employee_ids[0]]], context=context)
            wk_recs = wk_rec_obj.browse(cr, uid, wk_rec_ids, context=context)

            res.update({
                'wk_recs': wk_recs or [],
                'format_date': self.format_date,
            })

        return request.render('vhr_mysite.working_history', res)
    
    @http.route(['/mysite/contract'], type='http', auth="user", website=True)
    def my_contract_history_info(self, **kw):
        context = dict(request.context)
        cr, uid = request.cr, request.uid
        hr_obj = request.registry['hr.employee']
        contract_obj = request.registry['hr.contract']
        res = {}
        
        employee_ids = hr_obj.search(
            cr, uid, [('user_id', '=', uid)], context=context)
        if employee_ids:
            # Get current contract
            today = datetime.today().strftime('%Y-%m-%d')
            curent_contract_ids = contract_obj.search(
                cr, uid,[('employee_id', '=', employee_ids[0]),
                         ('is_main', '=', True),
                         ('date_start', '<=', today),
                         ('state', '=', 'signed'),
                         '|', '|', ('liquidation_date', '>=', today),
                         '&', ('date_end', '>=', today), ('liquidation_date', '=', False),
                         '&', ('date_end', '=', False), ('liquidation_date', '=', False)
                         ], order='date_start desc')
            if curent_contract_ids:
                res.update({
                    'current_contracts':
                    contract_obj.browse(cr, uid, curent_contract_ids) or [],
                })
            # Get all contract
            contract_ids = contract_obj.search(
                cr, uid, [['employee_id', '=', employee_ids[0]]], context=context)
            if contract_ids:
                res.update({
                    'contracts': contract_obj.browse(cr, uid, contract_ids) or [],
                    'format_date': self.format_date,
                    'curent_contract_ids': curent_contract_ids,
                })
            
        return request.render('vhr_mysite.contract_history', res)

    @http.route(['/mysite/salary'], type='http', auth="user", website=True)
    def my_salary_history_info(self, **kw):
        context = dict(request.context)
        cr, uid = request.cr, request.uid
        hr_obj = request.registry['hr.employee']
        salary_obj = request.registry['vhr.pr.salary']
        res = {}
        
        employee_ids = hr_obj.search(
            cr, uid, [('user_id', '=', uid)], context=context)
        if employee_ids:
            salary_ids = salary_obj.search(
                cr, uid, [['employee_id', '=', employee_ids[0]]], context=context)
            
            if salary_ids:
                res.update({
                    'salaries': salary_obj.browse(cr, uid, salary_ids) or [],
                    'format_date': self.format_date,
                })
        return request.render('vhr_mysite.salary_history', res)

    @http.route(['/mysite/kpi'], type='http', auth='user', website=True)
    def my_kpi_history(self, **kw):
        context = dict(request.context)
        cr, uid = request.cr, request.uid
        hr_emp_obj = request.registry['hr.employee']
        res = {}
        
        emp_ids = hr_emp_obj.search(
            cr, uid, [['user_id', '=', uid]], context=context)
        if emp_ids:
            emp_rec = hr_emp_obj.browse(cr , uid, emp_ids[0], context=context)
            res.update({
                'assess_recs': emp_rec.assessment_result_ids or [],
                'format_date': self.format_date,
            })
        return request.render('vhr_mysite.kpi_history', res)
    
    
    def compare_day(self, date_one, date_two):
        date_one = datetime.strptime(date_one, '%Y-%m-%d')
        date_two = datetime.strptime(date_two, '%Y-%m-%d')
        res = date_two - date_one
        return res.days
    
    def filter_current_benefit(self, cr, uid, ids, context=None):
        res = []
        today = datetime.now()
        allowance_obj = request.registry['vhr.pr.allowance']
        
        allowance_ids = allowance_obj.read(cr, uid, ids, ['allowance_cate_id','from_date_func'])
        dict = {}
        for record in allowance_ids:
            allowance_cate_id = record.get('allowance_cate_id', False) and record['allowance_cate_id'][0]
            from_date = record.get('from_date_func', False)
            if allowance_cate_id not in dict.keys():
                dict[allowance_cate_id] = [record['id'], from_date]
                res.append(record['id'])
            else:
                gap = self.compare_day(dict[allowance_cate_id][1], from_date)
                if gap > 0:
                    gap_today = self.compare_day(from_date, today.strftime('%Y-%m-%d'))
                    if gap_today >=0:
                        res.append(record['id'])
                        res.remove(dict[allowance_cate_id][0])
                        dict[allowance_cate_id] = [record['id'], from_date]
        
        return res
        
    
    @http.route(['/mysite/benefit'], type='http', auth="user", website=True)
    def my_benefit_info(self, **kw):
        context = dict(request.context)
        if not context:
            context = {}
            
        cr, uid = request.cr, request.uid
        hr_obj = request.registry['hr.employee']
        values = {'is_cb': False,
               'format_money': self.format_money,
               'benefits': False,
               'active_form': True,
               'insurance_data': '',
               'annual_leave': False,
               }
        
        check = self._check_group_payroll(cr, uid, context=context)
        if check:
            values['is_cb'] = True
        
        employee_ids = hr_obj.search( cr, uid, [('user_id', '=', uid)], context=context)
        
        if employee_ids:
            context['user_id'] = uid
            values = self.get_employee_benefit(cr, SUPERUSER_ID, employee_ids[0], values, context)
        
         # Kiem tra da public benefit hay chua
        active = request.registry['ir.config_parameter'].get_param(cr, uid, 'mysite.active.benefit')
        if active not in ACTIVE_STRING:
            values['active_form'] = False
                
        return request.render('vhr_mysite.vhr_benefit', values)
    
    @http.route(['/mysite/search_benefit'], type='http', auth='user', website=True)
    def mysite_search_benefit(self, **kw):
        context = dict(request.context)
        if not context:
            context = {}
            
        cr, uid = request.cr, request.uid
        hr_obj = request.registry['hr.employee']
        values = {'is_cb': False,
                  'format_money': self.format_money,
                  'benefits': False,
                  'active_form': True,
                  'insurance_data': '',
                  'annual_leave': False
                  }
        
        domain = []
        query = request.params.get('q')
        values['query'] = query
        if query:
            check = self._check_group_payroll(cr, uid, context=context)
            if check:
                values['is_cb'] = True
                if '-' in query:
                    query = query.upper()
                    domain = [['code', '=', query]]
                else:
                    query = query.lower()
                    domain = [('login', '=', query)]
                
            else:
                return http.local_redirect('/web', query={}, keep_hash=True)
        
        if not domain:
            employee_ids = []
        else:
            employee_ids = hr_obj.search(cr, uid, domain, context=context)
        
        if employee_ids:
            emp = hr_obj.browse(cr, uid, employee_ids[0])
            user_id = emp.user_id and emp.user_id.id or False
            context['user_id'] = user_id
            values = self.get_employee_benefit(cr, SUPERUSER_ID, employee_ids[0], values, context)
            
            
         # Kiem tra da public benefit hay chua
        active = request.registry['ir.config_parameter'].get_param(cr, uid, 'mysite.active.benefit')
        if active not in ACTIVE_STRING:
            values['active_form'] = False
        
        return request.render('vhr_mysite.vhr_benefit_search', values)
    
    def get_employee_benefit(self, cr, uid, employee_id, values, context=None):
        if not context:
            context = {}
        if not values:
            values = {}
        hr_obj = request.registry['hr.employee']
        contract_obj = request.registry['hr.contract']
        leave_obj = request.registry['hr.holidays']
        working_obj = request.registry['vhr.working.record']
        parameter_obj = request.registry['ir.config_parameter']
        allowance_cate_obj = request.registry['vhr.pr.allowance.cate']
        ts_param_type_obj = request.registry['vhr.ts.param.type']
        leave_type_obj = request.registry['hr.holidays.status']
        partner_obj = request.registry['res.partner']
        special_salary_obj = request.registry['vhr.mysite.benefit.salary']
        if employee_id:
            today = datetime.now()
            current_year = datetime.now().year
            # check employee is created before.
            year_val = current_year
                    
            #Level
            emp_obj = request.registry['hr.employee']
            employee = emp_obj.browse(cr, uid, employee_id)
            level = employee.job_level_person_id and employee.job_level_person_id.name or ''
            level_id = employee.job_level_person_id and employee.job_level_person_id.id or False
            partner_id = employee.address_home_id.id
            values['level'] = level
            values['employee'] = employee
            
            user_id = uid
            if context.get('user_id', False):
                user_id = context['user_id']
                
            in_esop_user_group = partner_obj.check_permission(cr, user_id, 'esop_user_group', context=context)
            is_active_esop_user = False
            if partner_id:
                partner_data = partner_obj.read(cr, uid, partner_id, ['stock_qty', 'unvested_qty'], context=context)
                if partner_data.get('stock_qty', 0) or partner_data.get('unvested_qty', 0):
                    is_active_esop_user = True

            values['is_ESOP_user'] = in_esop_user_group and is_active_esop_user

            # Check holidays
            hr_holidays = request.registry['hr.holidays']
            current_year = datetime.now().year
            holiday_status_code = parameter_obj.get_param(cr, uid, 'ts.leave.type.default.code') or False
            
            holiday_ids = hr_holidays.search(
                cr, uid,
                [('employee_id', '=', employee_id),
                 ('year', '=', current_year),
                 ('holiday_status_id.code', '=', holiday_status_code),
                 ('type', '=', 'add')])
            
            if holiday_ids:
                holidays = hr_holidays.browse(cr, uid, holiday_ids[0])
                values.update({'holiday': holidays})
            
            #Check allowance
            cate_code = parameter_obj.get_param( cr, uid, 'vhr_payroll_benefit_show_in_mysite_tab2') or ''
            cate_code = cate_code.split(',')
            cate_ids = allowance_cate_obj.search(cr, SUPERUSER_ID, [('code','in',cate_code)])
            
            allowance_obj = request.registry['vhr.pr.allowance']
            today = datetime.now()
            allowance_ids = allowance_obj.search(cr, uid, [('employee_id','=',employee_id),
                                                           ('state','=','done'),
                                                           ('allowance_cate_id','not in',cate_ids),
                                                           ('from_date_func','<=',today),
                                                           '|',('to_date_func','>=',today),
                                                               ('to_date_func','=',False) ], context={'active_test': False})
            
            if allowance_ids:
                allowance_ids = self.filter_current_benefit(cr, uid, allowance_ids, context)
                allowances = allowance_obj.browse(cr, SUPERUSER_ID, allowance_ids)
                values.update({'allowances': allowances})
            
            #Benefit show in table 2
            benefit_ids = allowance_obj.search(cr, uid, [('employee_id','=',employee_id),
                                                           ('state','=','done'),
                                                           ('allowance_cate_id','in',cate_ids),
                                                           ('from_date_func','<=',today),
                                                           '|',('to_date_func','>=',today),
                                                               ('to_date_func','=',False)], context={'active_test': False})
            
            if benefit_ids:
                benefit_ids = self.filter_current_benefit(cr, uid, benefit_ids, context)
                benefits = allowance_obj.browse(cr, SUPERUSER_ID, benefit_ids)
                values.update({'benefits': benefits})
            
            
            #Get insurance data
            param_obj = request.registry['vhr.pr.param.job.level']
            
            code = parameter_obj.get_param(cr, uid, 'vhr_payroll_code_allowance_cate_not_generate_allowance_from_parameter') or ''
            code = code.split(',')
            allowance_cate_ids = allowance_cate_obj.search(cr, uid, [('code','in',code)])
            
            param_ids = param_obj.search(cr, uid, [('job_level_new_id','=',level_id),
                                                   ('active','=',True),
                                                   ('allowance_cate_id','in',allowance_cate_ids)])
            
            if param_ids:
                param = param_obj.read(cr, uid, param_ids[0], ['description'])
                values['insurance_data'] = param.get('description','')
                
            #Get annual leave data
            ts_param_obj = request.registry['vhr.ts.param.job.level']
            
            code = parameter_obj.get_param(cr, uid, 'ts.param.type.stipulated.permit') or ''
            code = code.split(',')
            param_type_id = ts_param_type_obj.search(cr, uid, [('code','in',code)])
            
            ts_param_ids = ts_param_obj.search(cr, uid, [('job_level_new_id','=',level_id),
                                                         ('job_level_id','=',False),
                                                       ('active','=',True),
                                                       ('param_type_id','in',param_type_id)])
            
            leave_type_code = parameter_obj.get_param(cr, uid, 'ts.leave.type.default.code').split(',')
                    
            #Leave type nghi phep nam
            holiday_status_id = leave_type_obj.search(cr, uid, [('code', 'in', leave_type_code)])
            if holiday_status_id:
                holiday_status_id = holiday_status_id[0]
                
            if ts_param_ids:
                param = ts_param_obj.read(cr, uid, ts_param_ids[0], ['value'])
                values['annual_leave'] = int(param.get('value',''))
                
            elif not level_id:
                #If employee is CTV and fulltime and joindate <today-1year at office (!= Z0) and level =Temporary, can have annual leave
                default_number_of_days = parameter_obj.get_param(cr, uid, 'vhr_timesheet_annual_leave_day_for_CTV') or 0
                try:
                    default_number_of_days = int(default_number_of_days)
                except:
                    default_number_of_days = 0
                
                res_emp_ids = leave_obj.get_colla_emp_satisfy_condition_to_gen_annual_leave(cr, uid, [employee_id], context)
                if res_emp_ids:
                    if holiday_status_id:
                        #Check if already have annual leave in this year
                        leave_ids = leave_obj.search(cr, uid, [('employee_id','=',employee_id),
                                                               ('type','=','add'),
                                                               ('year','=',year_val),
                                                               ('state', '=', 'validate'),
                                                               ('holiday_status_id', '=', holiday_status_id),
                                                               ('number_of_days_temp','!=',0)
                                                               ])
                        if leave_ids:
                            values['annual_leave'] = default_number_of_days
            
            #Cong tham nien
            if values.get('annual_leave', False) and holiday_status_id:
                seniority = 0
                leave_ids = leave_obj.search(cr, uid, [('employee_id','=',employee_id),
                                                       ('type','=','add'),
                                                       ('year','=',year_val),
                                                       ('state', '=', 'validate'),
                                                       ('holiday_status_id', '=', holiday_status_id),
                                                       ('number_of_days_temp','!=',0)
                                                       ])
                if leave_ids:
                    leave = leave_obj.read(cr, uid, leave_ids[0], ['seniority_leave'])
                    seniority = leave.get('seniority_leave', 0)
                
                values['annual_leave'] += float(seniority)
            
            #Get salary
            salary_obj = request.registry['vhr.pr.salary']
            
            salary_ids = salary_obj.search(cr, uid, [('employee_id','=',employee_id),
                                                     ('effect_from','<=',today),
                                                     '|',('effect_to','>=', today),
                                                         ('effect_to','=', False)])
            gross_salary = 0
            if salary_ids:
                salaries = salary_obj.read(cr, uid, salary_ids, ['gross_salary','collaborator_salary'])
                for data in salaries:
                    gross = data.get('gross_salary',0)
                    colla = data.get('collaborator_salary', 0)
                    if gross:
                        gross_salary += gross
                    
                    elif colla:
                        gross_salary += colla
            
            special_salary = 0
            special_salary_ids = special_salary_obj.search(cr, uid, [('employee_id','=',employee_id),
                                                                     ('active','=',True)])
            if special_salary_ids:
                special_salarys = special_salary_obj.read(cr, uid, special_salary_ids, ['salary'])
                for sal in special_salarys:
                    salary = sal.get('salary', 0)
                    special_salary += int(salary)
                
            gross_salary += special_salary
            values.update({'gross_salary': gross_salary})
            
            #Get meal support, parking support
            
            meal_support = 0
            parking_support = 0
            
            if employee_id:
                employee = hr_obj.read(cr, uid, employee_id, ['company_id','office_id'])
                company_id = employee.get('company_id', False) and employee['company_id'][0]
                
                is_meal = False
                if company_id:
                    active_wr_ids = working_obj.search(cr, uid, [('employee_id','=',employee_id),
                                                                 ('company_id','=',company_id),
                                                                 ('state','in',[False,'finish']),
                                                                 ('active','=',True)])
                    if active_wr_ids:
                        working = working_obj.browse(cr, uid, active_wr_ids[0], fields_process=['salary_setting_id_new'])
                        is_meal = working.salary_setting_id_new and working.salary_setting_id_new.is_meal or False
                    else:
                        contract_ids = contract_obj.search(cr, uid, [('employee_id','=', employee_id),
                                                                     ('company_id','=', company_id),
                                                                     ('date_start','<=',today),
                                                                     '|',
                                                                         '&',('date_end','=', False),('liquidation_date','=', False),
                                                                         '&',('date_end','>=', today),('liquidation_date','=', False),
                                                                         ('liquidation_date','>=', today)
                                                                         ])
                        if contract_ids:
                            contract = contract_obj.read(cr, uid, contract_ids[0], ['salary_setting_id'])
                            salary_setting_id = contract.get('salary_setting_id', False) and contract['salary_setting_id'][0]
                            if salary_setting_id:
                                salary_setting = request.registry['vhr.salary.setting'].read(cr, uid, salary_setting_id, ['is_meal'])
                                is_meal = salary_setting.get('is_meal', False)
                
                if is_meal:
                    full_meal = parameter_obj.get_param(cr, uid, 'vhr_human_resource_full_meal_allowance') or 0
                    if full_meal:
                        meal_support = full_meal
                
                office_id = employee.get('office_id', False) and employee['office_id'][0]
                if office_id:
                    office = request.registry['vhr.office'].read(cr, uid, office_id, ['is_parking'])
                    is_parking = office.get('is_parking', False)
                    if is_parking:
                        full_meal = parameter_obj.get_param(cr, uid, 'vhr_human_resource_parking_allowance') or 0
                        if full_meal:
                            parking_support = full_meal
        
        values.update({'meal_support'   : meal_support,
                       'parking_support': parking_support})
        
        return values

    def format_money(self, money):
        if money:
            return '{:,.0f}'.format(money)
        return money
    
    def format_number(self, number):
        if number:
            return '{:,.2f}'.format(number)
        return number

    @http.route(['/mysite/total_income'], type='http', auth='user', website=True)
    def my_total_income(self, **kw):
        context = dict(request.context)
        cr, uid = request.cr, request.uid
        hr_emp_obj = request.registry['hr.employee']
        total_income_obj = request.registry['vhr.total.income']
        res = {'is_cb': False,
               'active_form': True}
        
        emp_ids = hr_emp_obj.search(
            cr, uid, [['user_id', '=', uid]], context=context)
        if emp_ids:
            total_incomes = []
            employee = hr_emp_obj.browse(cr, uid, emp_ids[0])
            total_income_ids = total_income_obj.search(cr, uid, [('employee_id', '=', emp_ids[0])])
            if total_income_ids:
                total_incomes = total_income_obj.browse(cr, uid, total_income_ids)
            res.update({
                'total_incomes': total_incomes,
                'employee': employee,
                'format_date': self.format_date,
                'format_money': self.format_money,
            })
        # Kiem tra user co thuoc group payroll hay khong
        check = self._check_group_esop(cr, uid, context=context)
        if check:
            res['is_cb'] = True
        
        # Kiem tra da public Total income hay chua
        active = request.registry['ir.config_parameter'].get_param(cr, uid, 'mysite.active.total.income')
        if active not in ACTIVE_STRING:
            res['active_form'] = False
        return request.render('vhr_mysite.total_income', res)

    @http.route('/mysite/search_total_income', type='http', auth="user", website=True, keep_hash=True)
    def mysite_search_total_income(self, **kw):
        
        context = dict(request.context)
        cr, uid = request.cr, request.uid
        hr_emp_obj = request.registry['hr.employee']
        total_income_obj = request.registry['vhr.total.income']
        resource_obj = request.registry['resource.resource']
        values = {
            'format_date': self.format_date,
            'format_money': self.format_money,
            'query': '',
            'selected_period': '',
#             'keyword': query,
            'active_form': True,
            'is_cb': False
        }
        income_objs = []
        employee = {}

        # Get query
        query = request.params.get('q')
        period = request.params.get('period')
        
        if query:
            # update query for message
            values.update({'query': query})
            # Kiem tra user co thuoc group payroll hay khong
            check = self._check_group_esop(cr, uid, context=context)
            if check:
                income_ids = []
                # Tim kiem bang ma nhan vien
                if '-' in query:
                    query = query.upper()
                    domain = [['employee_code', '=', query]]
                    if period:
                        values['selected_period'] = period
                        domain.append(['period', '=', period])
                    income_ids = total_income_obj.search(cr, uid, domain)
                # Neu ko co thi tim kiem theo domain account
                else:
                    query = query.lower()
                    employee_ids = hr_emp_obj.search(cr, uid, [('login', '=', query)])
                    # Get employee sau do tim employee trong total income
                    if employee_ids:
                        domain = [('employee_id', '=', employee_ids[0])]
                        if period:
                            domain.append(['period', '=', period])
                            values['selected_period'] = period
                        income_ids = total_income_obj.search(cr, uid, domain)
                # Neu co total income
                if income_ids:
                    income_objs = total_income_obj.browse(cr, uid, income_ids, context=context)
                    employee = income_objs[0].employee_id
                    
        values.update({'total_incomes': income_objs,
                       'employee': employee})
        # Kiem tra user co thuoc group payroll hay khong
        check = self._check_group_esop(cr, uid, context=context)
        if check:
            values['is_cb'] = True
        
        # Kiem tra da public total income hay chua
        active = request.registry['ir.config_parameter'].get_param(cr, uid, 'mysite.active.total.income')
        if active not in ACTIVE_STRING:
            values['active_form'] = False
        
        return request.render('vhr_mysite.total_income_search', values)

    def encode_payslip_id(self, payslip_id, context=None):
        if context is None:
            context = {}
        first = self.gen_string_random(size=525)
        last = self.gen_string_random(size=389)
        return first + str(payslip_id) + last

    def decode_payslip_id(self, payslip, context=None):
        if payslip:
            return str(payslip[525:-389])
        return False

    @http.route(['/mysite/payslip'], type='http', auth='user', website=True)
    def my_payslip(self, **kw):
        context = dict(request.context)
        cr, uid = request.cr, request.uid
        hr_emp_obj = request.registry['hr.employee']
        payslip_obj = request.registry['vhr.payslip']
        res = {
           'is_cb': False,
           'get_prev_salary': self.get_prev_salary,
           'active_form': True,
           'encode_payslip_id': self.encode_payslip_id,
        }
        
        cr.execute("select distinct year from vhr_payslip ")
        years = cr.fetchall()
        years = [year[0] for year in years]
        
        months = [month for month in range(1, 13)]
        
        res.update({
            'years': years,
            'months': months
        })
        
        emp_ids = hr_emp_obj.search(
            cr, uid, [['user_id', '=', uid]], context=context)
        if emp_ids:
            payslips = []
            employee = hr_emp_obj.browse(cr, uid, emp_ids[0])
            payslip_ids = payslip_obj.search(cr, uid, [('employee_id', '=', emp_ids[0])])
            if payslip_ids:
                payslips = payslip_obj.browse(cr, uid, payslip_ids)
            res.update({
                'payslips': payslips,
                'employee': employee,
                'format_date': self.format_date,
                'format_money': self.format_money,
            })
            
            # Kiem tra bank account
            if employee.bank_ids:
                for account in employee.bank_ids:
                    if account.is_main:
                        res['bank_account_number'] = account.acc_number or ''
                        break
            
            # Kiem tra ma so thue ca nhan
            if employee.personal_document:
                for document in employee.personal_document:
                    if document.document_type_id and document.document_type_id.code == 'TAXID':
                        res['pit_number'] = document.number
                        break
                        
        # Kiem tra user co thuoc group payroll hay khong
        check = self._check_group_payroll(cr, uid, context=context)
        if check:
            res['is_cb'] = True
        
        # Kiem tra da public payslip hay chua
        active = request.registry['ir.config_parameter'].get_param(cr, uid, 'mysite.active.payslip')
        if active not in ACTIVE_STRING:
            res['active_form'] = False
        return request.render('vhr_mysite.vhr_payslip', res)
    
    @http.route(['/mysite/search_payslip'], type='http', auth='user', website=True)
    def mysite_search_payslip(self, **kw):
        context = dict(request.context)
        cr, uid = request.cr, request.uid
        hr_emp_obj = request.registry['hr.employee']
        payslip_obj = request.registry['vhr.payslip']
        resource_obj = request.registry['resource.resource']
        res = {'is_cb': False,
               'get_prev_salary': self.get_prev_salary,
               'active_form': True,
               'encode_payslip_id': self.encode_payslip_id,}
        
        cr.execute("select distinct year from vhr_payslip ")
        years = cr.fetchall()
        years = [x[0] for x in years]
        
        months = [x for x in range(1, 13)]
        
        res.update({
            'years': years,
            'months': months,
            'format_date': self.format_date,
            'format_money': self.format_money,
            'query': '',
            'selected_year': '',
            'selected_month': '',
        })
        
        payslip_objs = []
        employee = {}
        
        # Get query
        query = request.params.get('q')
        year = request.params.get('year')
        month = request.params.get('month')
        
        if query:
            # update query for message
            res.update({'query': query})
            # Kiem tra user co thuoc group payroll hay khong
            check = self._check_group_payroll(cr, uid, context=context)
            if check:
                res['is_cb'] = True
                payslip_ids = []
                # Tim kiem bang ma nhan vien
                if '-' in query:
                    query = query.upper()
                    domain = [['employee_code', '=', query]]
                    if year:
                        domain.append(['year', '=', year])
                    if month:
                        domain.append(['month', '=', month])
                    payslip_ids = payslip_obj.search(cr, uid, domain)
                # Neu ko co thi tim kiem theo domain account
                else:
                    query = query.lower()
                    employee_ids = hr_emp_obj.search(cr, uid, [('login', '=', query)])
                    # Get employee sau do tim employee trong total income
                    if employee_ids:
                        domain = [('employee_id', '=', employee_ids[0])]
                        if year:
                            domain.append(['year', '=', year])
                            res['selected_year'] = year
                        if month:
                            domain.append(['month', '=', month])
                            res['selected_month'] = month
                        if year and month:
                            res.update({'selected_period': month + '/' + year})
                        payslip_ids = payslip_obj.search(cr, uid, domain)
                # Neu co total income
                if payslip_ids:
                    payslip_objs = payslip_obj.browse(cr, uid, payslip_ids, context=context)
                    employee = payslip_objs[0].employee_id
                    
                    # Kiem tra bank account
                    if employee.bank_ids:
                        for account in employee.bank_ids:
                            if account.is_main:
                                res['bank_account_number'] = account.acc_number or ''
                                break
                    
                    # Kiem tra ma so thue ca nhan
                    if employee.personal_document:
                        for document in employee.personal_document:
                            if document.document_type_id and document.document_type_id.code == 'TAXID':
                                res['pit_number'] = document.number
                                break
                    
        res.update({'payslips': payslip_objs,
                    'employee': employee,})
        # Kiem tra da public payslip hay chua
        active = request.registry['ir.config_parameter'].get_param(cr, uid, 'mysite.active.payslip')
        if active not in ACTIVE_STRING:
            res['active_form'] = False
        return request.render('vhr_mysite.vhr_payslip_search', res)

    @http.route(['/mysite/action_print_payslip'], methods=['GET', 'POST'], type='http', auth='user', website=True)
    def action_print_payslip(self, **kw):
        cr, uid, context = request.cr, request.uid, request.context
        if context is None:
            context = {}
        if kw and kw.get('payslip', False):
            hr_emp_obj = request.registry['hr.employee']
            emp_ids = hr_emp_obj.search(
                cr, uid, [['user_id', '=', uid]], context=context)
            if emp_ids:
                report_template = 'vhr_mysite.report_payslip_template'
                docids = self.decode_payslip_id(kw['payslip'])
                if docids:
                    payslip = request.registry['vhr.payslip'].browse(cr, uid, int(docids))
                    report_name = 'payslip_' + (payslip.employee_id and payslip.employee_id.code or '')
                    report_controller = ReportController()
                    ctx = ""
                    if kw.get('lg', '') and kw['lg'] == 'en':
                        ctx = '{"en": true}'
                    response = report_controller.report_routes(report_template, docids=docids, converter='pdf', context=ctx)
                    response.headers.add('Content-Disposition', 'attachment; filename=%s.pdf;' % report_name)
                    
                    return response
        return self.my_payslip(**kw)

    @http.route(['/mysite/year_end_bonus'], type='http', auth='user', website=True)
    def my_year_end_bonus(self, **kw):
        context = dict(request.context)
        cr, uid = request.cr, request.uid
        hr_emp_obj = request.registry['hr.employee']
        bonus_obj = request.registry['vhr.year.end.bonus']
        res = {'is_cb': False,
               'active_form': True,
               'format_number': self.format_number}
        
        cr.execute("select distinct year from vhr_year_end_bonus ")
        years = cr.fetchall()
        years = [year[0] for year in years]
        
        res.update({
            'years': years,
        })
        
        emp_ids = hr_emp_obj.search(
            cr, uid, [['user_id', '=', uid]], context=context)
        if emp_ids:
            total_bonus = []
            employee = hr_emp_obj.browse(cr, uid, emp_ids[0])
            bonus_ids = bonus_obj.search(cr, uid, [('employee_id', '=', emp_ids[0])])
            if bonus_ids:
                total_bonus = bonus_obj.browse(cr, uid, bonus_ids)
            res.update({
                'total_bonus': total_bonus,
                'employee': employee,
                'format_date': self.format_date,
                'format_money': self.format_money,
            })
            
            # Kiem tra bank account
            if employee.bank_ids:
                for account in employee.bank_ids:
                    if account.is_main:
                        res['bank_account_number'] = account.acc_number or ''
                        break
            
            # Kiem tra ma so thue ca nhan
            if employee.personal_document:
                for document in employee.personal_document:
                    if document.document_type_id and document.document_type_id.code == 'TAXID':
                        res['pit_number'] = document.number
                        break
                        
        # Kiem tra user co thuoc group payroll hay khong
        check = self._check_group_esop(cr, uid, context=context)
        if check:
            res['is_cb'] = True
        
        # Kiem tra da public year end bonus hay chua
        active = request.registry['ir.config_parameter'].get_param(cr, uid, 'mysite.active.year.end.bonus')
        if active not in ACTIVE_STRING:
            res['active_form'] = False
        return request.render('vhr_mysite.year_end_bonus', res)

    @http.route(['/mysite/search_year_end_bonus'], type='http', auth='user', website=True)
    def mysite_search_year_end_bonus(self, **kw):
        context = dict(request.context)
        cr, uid = request.cr, request.uid
        hr_emp_obj = request.registry['hr.employee']
        bonus_obj = request.registry['vhr.year.end.bonus']
        resource_obj = request.registry['resource.resource']
        res = {'is_cb': False,
               'active_form': True,
               'format_number': self.format_number}
        
        cr.execute("select distinct year from vhr_year_end_bonus ")
        years = cr.fetchall()
        years = [x[0] for x in years]
        
        res.update({
            'years': years,
            'format_date': self.format_date,
            'format_money': self.format_money,
            'query': '',
            'selected_year': '',
        })
        
        total_bonus = []
        employee = {}
        
        # Get query
        query = request.params.get('q', '')
        year = request.params.get('year', '')
        
        if query:
            # update query for message
            res.update({'query': query})
            # Kiem tra user co thuoc group payroll hay khong
            check = self._check_group_esop(cr, uid, context=context)
            if check:
                res['is_cb'] = True
                bonus_ids = []
                # Tim kiem bang ma nhan vien
                if '-' in query:
                    query = query.upper()
                    domain = [['employee_code', '=', query]]
                    if year:
                        domain.append(['year', '=', year])
                    bonus_ids = bonus_obj.search(cr, uid, domain)
                # Neu ko co thi tim kiem theo domain account
                else:
                    query = query.lower()
                    employee_ids = hr_emp_obj.search(cr, uid, [('login', '=', query)])
                    # Get employee sau do tim employee trong total income
                    if employee_ids:
                        domain = [('employee_id', '=', employee_ids[0])]
                        if year:
                            domain.append(['year', '=', year])
                            res['selected_year'] = year
                        bonus_ids = bonus_obj.search(cr, uid, domain)
                # Neu co year end bonus
                if bonus_ids:
                    total_bonus = bonus_obj.browse(cr, uid, bonus_ids, context=context)
                    employee = total_bonus[0].employee_id
                    
                    # Kiem tra bank account
                    if employee.bank_ids:
                        for account in employee.bank_ids:
                            if account.is_main:
                                res['bank_account_number'] = account.acc_number or ''
                                break
                    
                    # Kiem tra ma so thue ca nhan
                    if employee.personal_document:
                        for document in employee.personal_document:
                            if document.document_type_id and document.document_type_id.code == 'TAXID':
                                res['pit_number'] = document.number
                                break
        # Kiem tra da public year end bonus hay chua
        active = request.registry['ir.config_parameter'].get_param(cr, uid, 'mysite.active.year.end.bonus')
        if active not in ACTIVE_STRING:
            res['active_form'] = False
        res.update({'total_bonus': total_bonus,
                    'employee': employee,})
        return request.render('vhr_mysite.year_end_bonus_search', res)

    @http.route(['/mysite/quick_edit/<model("vhr.employee.temp.quick.edit"):edit>/<string:token>'],
                type='http', auth='user', website=True)
    def my_quick_edit(self, edit, token, **kw):
        '''Display and validates a survey'''
        cr, uid, context = request.cr, request.uid, request.context
        hr_obj = request.registry['hr.employee']

        employee_ids = hr_obj.search(cr, uid, [('user_id', '=', uid)], context=context)
        if employee_ids:
            hr_temp_obj = request.registry['vhr.employee.temp']
            values = {}

            employe_obj = hr_obj.browse(cr, uid, employee_ids[0], context)
            
            if edit and edit.employee_temp_id and employe_obj:
                if edit.employee_temp_id.employee_id and \
                        edit.employee_temp_id.employee_id.id != employe_obj.id:
                    return request.render('website.404', {})
            
            check = hr_temp_obj.check_editable(request.cr, request.uid, employee_ids[0])
            if employe_obj:
                values.update({
                    'personal_documents': edit.employee_temp_id.personal_document_temp_ids or [],
                    'bank_accounts': edit.employee_temp_id.bank_ids or [],
                    'certificates': edit.employee_temp_id.certificate_ids or [],
                    'relation_partners': edit.employee_temp_id.relation_partner_temp_ids or [],
                    'my_title': 'Mysite - ' + employe_obj.name,
                    'format_date': self.format_date,
                    'get_gender_name': self.get_gender_name,
                    'get_marital_name': self.get_marital_name,
                    'get_document_status': self.get_document_status,
                    'emp_field_ids': edit.emp_field_ids,
                    'my_employee': edit.employee_temp_id,
                    'my_employee_id': employe_obj.id,
                })
                
                for field in edit.emp_field_ids:
                    if field.name in ['personal_document_temp_ids',
                                      'relation_partner_temp_ids',
                                      'certificate_ids',
                                      'bank_ids']:
                        values.update({
                            'show_extra': True
                        })
                    if field.name not in ['personal_document_temp_ids',
                                          'relation_partner_temp_ids',
                                          'certificate_ids',
                                          'bank_ids']:
                        values.update({
                            'show_basic': True
                        })

            return request.render('vhr_mysite.my_profile_quick_edit', values)
        return http.local_redirect('/web', query=request.params, keep_hash=True)

    @http.route('/update_employee_info', type='http', auth="user", website=True, keep_hash=True)
    def update_employee_info(self, **kw):
        cr, uid, context = request.cr, request.uid, request.context
        hr_obj = request.registry['hr.employee']
        values = {'demo_page': True,
                  'format_date': self.format_date,
                  'id_number': {},
                  'update_info': {},
                  'is_cb': False}
        if kw and kw.get('message', False) == 'completed':
            values.update({'message': u'Thông tin thay đổi của bạn đã được gửi đến phòng Nhân sự'})

        employee_ids = hr_obj.search(cr, uid, [('user_id', '=', uid)], context=context)
        if employee_ids:
            
            #Check is c&b
            check = self._check_group_cb(cr, uid, context=context)
            if check:
                values['is_cb'] = True
                
            # Get current employee info
            employee = hr_obj.browse(cr, uid, employee_ids[0])
            values.update({'employee': employee})

            # Get ID Number info
            documents = employee.personal_document or []
            for document in documents:
                if document.document_type_id.code == 'ID' and \
                        document.document_type_id.name == "CMND" and \
                        document.document_type_id.active == True:
                    values.update({'id_number': document})
                    break
            # check update info exists or not
            update_obj = request.registry['vhr.update.employee.info']
            update_ids = update_obj._check_update_info_exists(cr, uid, employee.code)
            if update_ids:
                update_info = update_obj.browse(cr, uid, update_ids[0])
                values.update({'update_info': update_info})
            # Check user co thong tin cap nhat hay chua
            # neu chua tu dong tao 1 record
            else:
                update_obj.create_update_info(cr, uid, {'employee_code': employee.code, 'is_view': True}, context=context)
            return request.render('vhr_mysite.update_employee_info', values)
        return http.local_redirect('/', query=request.params, keep_hash=True)

    @http.route(['/seach/update_employee_info'], methods=['GET', 'POST'], type='http', auth='user', website=True)
    def search_update_employee_info(self, **kw):
        cr, uid, context = request.cr, request.uid, request.context
        hr_obj = request.registry['hr.employee']
        values = {'demo_page': True,
                  'format_date': self.format_date,
                  'id_number': {},
                  'update_info': {},
                  'is_cb': False,
                  'employee_code': False}
        # Get query
        query = kw.get('employee_code', '')
        if query:
            # Kiem tra user co thuoc group payroll hay khong
            check = self._check_group_cb(cr, uid, context=context)
            if check:
                values['is_cb'] = True
                employee = self._search_employee(cr, uid, query, context=context)
                if employee:
                    values.update({'employee': employee,
                                   'employee_code': query})
                    documents = employee.personal_document or []
                    for document in documents:
                        if document.document_type_id.code == 'ID' and \
                                document.document_type_id.name == "CMND" and \
                                document.document_type_id.active == True:
                            values.update({'id_number': document})
                            break
                    # check update info exists or not
                    update_obj = request.registry['vhr.update.employee.info']
                    update_ids = update_obj._check_update_info_exists(cr, uid, employee.code)
                    if update_ids:
                        update_info = update_obj.browse(cr, uid, update_ids[0])
                        values.update({'update_info': update_info})
                    return request.render('vhr_mysite.update_employee_info', values)
        return http.local_redirect('/update_employee_info', keep_hash=True)
    
    @http.route(['/action_update_employee_info'], methods=['GET', 'POST'], type='http', auth='user', website=True)
    def action_update_employee_info(self, **kw):
        cr, uid, context = request.cr, request.uid, request.context
        values = {}
        if kw:
            values.update({
                'employee_code': kw.get('user_code', ''),
                'is_submit': True,
                
                'current_id_number': kw.get('user_current_id_number', ''),
                'current_place_of_issued': kw.get('user_current_place_of_issued', ''),
                'current_phone': kw.get('user_current_phone', ''),
                'current_email': kw.get('user_current_email', ''),
                
                'new_id_number': kw.get('user_new_id_number', ''),
                'new_place_of_issued': kw.get('user_new_place_of_issued', ''),
                'new_phone': kw.get('user_new_phone', ''),
                'new_email': kw.get('user_new_email', ''),
            })
            
            if kw.get('user_current_date_of_issued', False):
                values['current_date_of_issued'] = kw['user_current_date_of_issued']
            if kw.get('user_new_date_of_issued', False):
                values['new_date_of_issued'] = kw['user_new_date_of_issued']
            update_pool = request.registry['vhr.update.employee.info']
            update_pool.create_update_info(cr, uid, values, context=context)
            
            employee_code = kw.get('render_from_form_search', '')
            if employee_code:
                return http.local_redirect('/seach/update_employee_info', query={'employee_code': employee_code}, keep_hash=True)
            
        return http.local_redirect('/update_employee_info', query={'message': 'completed'}, keep_hash=True)

    @http.route('/mysite/tax_settlement_auth', type='http', auth="user", website=True, keep_hash=True, methods=['GET', 'POST'])
    def tax_settlement_auth(self, **kw):
        cr, uid, context = request.cr, request.uid, request.context
        context = context or {}
        hr_obj = request.registry['hr.employee']
        tax_obj = request.registry['vhr.tax.settlement.auth']
        employee_ids = hr_obj.search(cr, uid, [('user_id', '=', uid)], context=context)
        res = {'pit_number': False,
               'id_number': False,
               'is_cb': False}
        employee = False
        # Kiem tra user co thuoc group c&b profile hay khong
        check = self._check_group_cb_profile(cr, uid, context=context)
        if check:
            res['is_cb'] = True
        
        # kiem tra user dang dang nhap co phai la employee hay ko
        if employee_ids:
            # neu ko phai la submit form
            if not kw or kw.get('q', ''):
                # Get config years
                years = request.registry['ir.config_parameter'].get_param(cr, uid, 'mysite.tax.settlement.years') or ''
                years = years.split(',')
                res.update({'years': [year.strip() for year in years]})
                
                # neu la c&b group
                if check:
                    # search employee
                    query = kw.get('q')
                    employee = self._search_employee(cr, uid, query, context=context)
                    # neu param truyen vao la employee
                    if employee:
                        # Kiem tra bank account
                        if employee.personal_document:
                            for document in employee.personal_document:
                                if document.document_type_id and document.document_type_id.code == 'TAXID':
                                    res['pit_number'] = document.number
                                    break
                        res.update({'employee': employee,
                                    'show_employee_info': True})
                
                return request.render('vhr_mysite.vhr_tax_settlement', res)
            else:
                if kw.get('employee_code', ''):
                    employee_code = kw.get('employee_code', '')
                    employee = self._search_employee(cr, uid, employee_code, context=context)
                    if not employee:
                        employee = hr_obj.browse(cr, uid, employee_ids[0])
                else:
                    employee = hr_obj.browse(cr, uid, employee_ids[0])
                
                user_select = kw.get('settlement', '')
                if user_select not in ['0', '1', '2']:
                    return http.local_redirect('/mysite/tax_settlement_auth', query={'message': 'error'}, keep_hash=True)
                
                selection = {'0': 'only_hrs', '1': 'not_over_10', '2': 'not_over_20'}
                
                documents = employee.personal_document or []
                for document in documents:
                    # Kiem tra CMND
                    if document.document_type_id and \
                            document.document_type_id.code == 'ID' and \
                            document.document_type_id.name == "CMND" and \
                            document.document_type_id.active == True:
                        res['id_number'] = document.number
                    # Kiem tra Ma so thue TNCN
                    if document.document_type_id and \
                            document.document_type_id.code == 'TAXID' and \
                            document.document_type_id.active == True:
                        res['pit_number'] = document.number
                
                # Kiem tra quoc tich
                res['nation'] = employee.country_id and employee.country_id.name or ''
                
                res.update({
                    'year': kw.get('select-year', ''),
                    'employee_id': employee.id,
                    'employee_code': employee.code,
                    'selection': selection[user_select]
                })
                
                report_template, docids, report_name = tax_obj.create_update_tax_settlement(cr, uid, res)
                # Print file
#                 report_controller = ReportController()
#                 response = report_controller.report_routes(report_template, docids=docids, converter='pdf')
#                 response.headers.add('Content-Disposition', 'attachment; filename=%s.pdf;' % report_name)
                now = datetime.now()
                report_controller = Reports()
                response = self.mysite_report({
                    'name': 'Uy_quyen_quyet_toan',
                    'report_name': 'tax_settlement_docx_report',
                    'context': {
                        'active_model': 'vhr.tax.settlement.auth',
                        'active_ids': [docids]},
                    'type' : 'ir.actions.report.xml',
                    'datas': {
                        'ids': [docids],
                        'model': 'vhr.tax.settlement.auth',
                        'parse_condition' : True,
                        'form': {
                            'year': res['year'],
                            'employee_name': employee.name or '',
                            'nation': res['nation'],
                            'pit_number': res['pit_number'] and str(res['pit_number']) or '',
                            'id_number': res['id_number'] and str(res['id_number']) or '',
                            'employee_code': employee.code or '',
                            'current_year': str(now.year),
                            'selection': selection[user_select],
                            'company_name': employee.company_id and employee.company_id.name or '',
                            'company_pit_number': str(employee.company_id and employee.company_id.vat or '')
                        }
                    }
                })
#                 response.set_cookie('fileToken', 1453705180967)
                return response
        return http.local_redirect('/', keep_hash=True)

    @http.route('/mysite/search_tax_settlement', type='http', auth="user", website=True, keep_hash=True, methods=['GET', 'POST'])
    def search_tax_settlement_auth(self, **kw):
        cr, uid, context = request.cr, request.uid, request.context
        context = context or {}
        hr_obj = request.registry['hr.employee']
        tax_obj = request.registry['vhr.tax.settlement.auth']
        employee_ids = hr_obj.search(cr, uid, [('user_id', '=', uid)], context=context)
        res = {'pit_number': False,
               'id_number': False}

    POLLING_DELAY = 0.25
    TYPES_MAPPING = {
        'doc': 'application/vnd.ms-word',
        'html': 'text/html',
        'odt': 'application/vnd.oasis.opendocument.text',
        'pdf': 'application/pdf',
        'sxw': 'application/vnd.sun.xml.writer',
        'xls': 'application/vnd.ms-excel',
    }
    
    @http.route('/mysite/report', type='http', auth="user")
    @serialize_exception
    def mysite_report(self, action):
        print action, type(action)

        report_srv = request.session.proxy("report")
        context = dict(request.context)
        context.update(action["context"])

        report_data = {}
        report_ids = context.get("active_ids", None)
        if 'report_type' in action:
            report_data['report_type'] = action['report_type']
        if 'datas' in action:
            if 'ids' in action['datas']:
                report_ids = action['datas'].pop('ids')
            report_data.update(action['datas'])

        report_id = report_srv.report(
            request.session.db, request.session.uid, request.session.password,
            action["report_name"], report_ids,
            report_data, context)

        report_struct = None
        while True:
            report_struct = report_srv.report_get(
                request.session.db, request.session.uid, request.session.password, report_id)
            if report_struct["state"]:
                break

            time.sleep(self.POLLING_DELAY)

        report = base64.b64decode(report_struct['result'])
        if report_struct.get('code') == 'zlib':
            report = zlib.decompress(report)
        report_mimetype = self.TYPES_MAPPING.get(
            report_struct['format'], 'octet-stream')
        file_name = action.get('name', 'report')
        if 'name' not in action:
            reports = request.session.model('ir.actions.report.xml')
            res_id = reports.search([('report_name', '=', action['report_name']),],
                                    0, False, False, context)
            if len(res_id) > 0:
                file_name = reports.read(res_id[0], ['name'], context)['name']
            else:
                file_name = action['report_name']
        file_name = '%s.%s' % (file_name, report_struct['format'])

        return request.make_response(report,
             headers=[
                 ('Content-Disposition', content_disposition(file_name)),
                 ('Content-Type', report_mimetype),
                 ('Content-Length', len(report))],
             )

    def _get_tax_settlement_data(self, cr, uid, emp_ids, context=None):
        hr_emp_obj = request.registry['hr.employee']
        tax_obj = request.registry['vhr.tax.settlement']
        res = {'is_cb': False,
               'format_number': self.format_number,
               'format_money': self.format_money,
               'format_date': self.format_date,
               'active_form': True,
               'document': False,
               'pit_number': False}
        
        cr.execute("select distinct year from vhr_tax_settlement ")
        years = cr.fetchall()
        years = [year[0] for year in years]
        
        res.update({
            'years': years,
        })
        
        if emp_ids:
            taxs = []
            employee = hr_emp_obj.browse(cr, uid, emp_ids[0])
            taxs_ids = tax_obj.search(cr, uid, [('employee_id', '=', emp_ids[0])])
            if taxs_ids:
                taxs = tax_obj.browse(cr, uid, taxs_ids)
            res.update({
                'taxs': taxs,
                'employee': employee,
            })
            
            documents = employee.personal_document or []
            for document in documents:
                # Kiem tra CMND
                if document.document_type_id and \
                        document.document_type_id.name == "CMND" and \
                        document.document_type_id.active == True:
                    res['document'] = document
                # Kiem tra Ma so thue TNCN
                if document.document_type_id and \
                        document.document_type_id.code == 'TAXID' and \
                        document.document_type_id.active == True:
                    res['pit_number'] = document.number
                        
        # Kiem tra user co thuoc group payroll hay khong
        check = self._check_group_payroll(cr, uid, context=context)
        if check:
            res['is_cb'] = True
        
        # Kiem tra da public year end bonus hay chua
        active = request.registry['ir.config_parameter'].get_param(cr, uid, 'mysite.active.tax.settlement')
        if active not in ACTIVE_STRING:
            res['active_form'] = False
        
        return res

    @http.route('/mysite/tax_settlement', type='http', auth="user", website=True, keep_hash=True)
    def tax_settlement(self, **kw):
        cr, uid, context = request.cr, request.uid, request.context
        context = context or {}
        hr_emp_obj = request.registry['hr.employee']
        emp_ids = hr_emp_obj.search(
            cr, uid, [['user_id', '=', uid]], context=context)
        res = self._get_tax_settlement_data(cr, uid, emp_ids, context)
        res.update({'selected_year': -1})
        
        return request.render('vhr_mysite.vhr_tax_settlement_result', res)

    @http.route('/mysite/search_tax_settlement', type='http', auth="user", website=True, keep_hash=True)
    def search_tax_settlement(self, **kw):
        cr, uid, context = request.cr, request.uid, request.context
        context = context or {}
        res = {'selected_year': -1}
        # Kiem tra user co thuoc group c&b profile hay khong
        check = self._check_group_payroll(cr, uid, context=context)
        if check:
            cr.execute("select distinct year from vhr_tax_settlement ")
            years = cr.fetchall()
            years = [year[0] for year in years]
            res.update({
                'active_form': True,
                'years': years,
                'is_cb': True,
            })
            # search employee
            query = kw.get('q', '')
            employee = self._search_employee(cr, uid, query, context=context)
            if employee:
                res = self._get_tax_settlement_data(cr, uid, [employee.id], context=context)
                res.update({
                    'query': query
                })
                year = kw.get('year', False)
                if year:
                    res.update({
                        'selected_year': year
                    })
            else:
                res.update({
                    'message': u'Không tìm thấy nhân viên ' + str(query)
                })
        return request.render('vhr_mysite.vhr_tax_settlement_result', res)

    @http.route('/mysite/recruitment_request', type='http', auth="user", website=True, keep_hash=True)
    def recruitment_request(self, **kw):
        cr, uid, context = request.cr, request.uid, request.context
        context = context or {}
        hr_emp_obj = request.registry['hr.employee']
        hr_job_obj = request.registry['hr.job']
        dimen_type = request.registry['vhr.dimension.type']
        emp_ids = hr_emp_obj.search(
            cr, uid, [['user_id', '=', uid]], context=context)
        res = {'format_number': self.format_number,
               'format_money': self.format_money,
               'format_date': self.format_date,
               'message': '',
               }
        if kw and kw.get('message', False):
            dept_id = kw['message']
            if dept_id != 'error':
                # Remove 44 first character and 15 last character
                dept_id = dept_id[593:-378]
                message = self._get_hrbp_info(cr, uid, dept_id, context=context)
            else:
                message = u'Lỗi trong quá trình tạo yêu cầu tuyển dụng'
            if message:
                res['message'] = message
        if emp_ids:
            department_domain = [['organization_class_id', 'in', [3, 6]]]
            dimension_type_ids = dimen_type.search(cr, uid, [('code', '=', 'HIERARCHICAL_CHART')])
            if dimension_type_ids:
                hierachical_ids = request.registry['vhr.dimension'].search(
                        cr, uid, [('code', '=', 'ORGCHART'), ('dimension_type_id', '=', dimension_type_ids[0])])
                
                department_domain.append(('hierarchical_id', 'in', hierachical_ids))
            
            
            # Get allowed departments for user login
            dept_ids = self.get_allowed_request_department(cr, uid, emp_ids[0], context=context)
            if dept_ids:
                department_domain.append(('id', 'in', dept_ids))
            
            # Get allowed employees for user login
            requester_domain = []
            requester_ids = self.get_allowed_request_employee(cr, uid, dept_ids, context=context)
            if requester_ids:
                requester_domain.append(('id', 'in', requester_ids))
            else:
                requester_domain.append(('id', '=', emp_ids[0]))
            
            employee = hr_emp_obj.browse(cr, uid, emp_ids[0])
            res.update({
                'companies': self._get_info_frontend(cr, uid, request.registry['res.company']),
                'departments': self._get_info_frontend(cr, uid, request.registry['hr.department'], None, department_domain, fields=['id', 'name', 'code']),
                'roles': self._get_info_frontend(cr, uid, request.registry['vhr.job.title']),
                'genders': [('any', 'Any'), ('male', 'Male'), ('female', 'Female')],
#                 'levels': self._get_info_frontend(cr, uid, request.registry['vhr.job.level']),
                'educations': self._get_info_frontend(cr, uid, request.registry['vhr.certificate.level'], domain=[('is_degree','=',True)]),
                'reasons': self._get_info_frontend(cr, uid, None, 'RECRUITMENT_REASON'),
                'places': self._get_info_frontend(cr, uid, request.registry['vhr.office']),
                'job_types': self._get_info_frontend(cr, uid, None, 'JOB_TYPE', order='id asc'),
                'request_types': self._get_info_frontend(cr, uid, None, 'RR_REQUEST_TYPE', order='id asc'),
                'report_tos': self._get_info_frontend(cr, uid, hr_emp_obj, order='login asc', fields=['id', 'name', 'login']),
                'requesters': self._get_info_frontend(cr, uid, hr_emp_obj, domain=requester_domain, order='login asc', fields=['id', 'name', 'login']),
                'employee': employee,
            })
        
        return request.render('vhr_mysite.vhr_recruitment_request', res)

    def get_allowed_request_department(self, cr, uid, employee_id, context=None):
        if context is None:
            context = {}
        hr_emp_obj = request.registry['hr.employee']
        hr_dept_obj = request.registry['hr.department']
        employee = hr_emp_obj.browse(cr, uid, employee_id, context=context)
        # Check employee is_depthead or not
        dept_dh_ids = hr_dept_obj.search(cr, uid, [('manager_id', '=', employee_id)])
        dept_hrbp_ids = hr_dept_obj.search(cr, uid, [('hrbps.id', '=', employee_id)])
        
        dept_ids = []
        if dept_dh_ids or dept_hrbp_ids:
            dept_ids = list(set(dept_dh_ids + dept_hrbp_ids))
        if employee.department_id:
            dept_ids = list(set(dept_ids + [employee.department_id.id]))
        return dept_ids

    def get_allowed_request_employee(self, cr, uid, dept_ids, context=None):
        if context is None:
            context = {}
        requester_ids = []
        if dept_ids:
            hr_emp_obj = request.registry['hr.employee']
            # Get dept_head from hr_department
            in_condition = ', '.join(map(lambda x: '%s', dept_ids))
            sql = """
                select distinct manager_id 
                from hr_department
                where id in (%s) """ % in_condition
            cr.execute(sql, dept_ids)
            res_ids = cr.fetchall()
            dept_head_ids = [dh_id[0] for dh_id in res_ids]
            # Get employee from department
            emp_dept_ids = hr_emp_obj.search(cr, uid, [('department_id', 'in', dept_ids)])
            requester_ids += list(set(emp_dept_ids + dept_head_ids))
        return requester_ids
        

    @http.route(['/mysite/action_recruitment_request'], methods=['GET', 'POST'], type='http', auth='user', website=True)
    def action_recruitment_request(self, **kw):
        cr, uid, context = request.cr, request.uid, request.context
        if context is None:
            context = {}
        values = {}
        message = ''
        hr_job_obj = request.registry['hr.job']
        hr_emp_obj = request.registry['hr.employee']
        emp_ids = hr_emp_obj.search(
            cr, uid, [['user_id', '=', uid]], context=context)
        if kw and emp_ids:
            
            # Check allowed department request
            request_for_dept = kw.get('request_for_dept', '') and int(kw['request_for_dept']) or False
            dept_ids = self.get_allowed_request_department(cr, uid, emp_ids[0], context=context)
            if not dept_ids or request_for_dept not in dept_ids:
                return http.local_redirect('/mysite/recruitment_request',
                                           query={'message': 'error'},
                                           keep_hash=True)
            
            # Check allowed employee for request
            allow_employee_ids = self.get_allowed_request_employee(cr, uid, dept_ids, context=context)
            report_to = kw.get('report_to', '') and int(kw['report_to']) or False
            requester = kw.get('requester', '') and int(kw['requester']) or False
            
            if not allow_employee_ids or \
                    report_to not in allow_employee_ids or \
                    requester not in allow_employee_ids:
                return http.local_redirect('/mysite/recruitment_request',
                                           query={'message': 'error'},
                                           keep_hash=True)
            
            values.update({
                'request_date': str(date.today()),
                'expected_date': kw.get('expected_date', '') and self.convert_request_date(kw['expected_date']) or False,
                'requestor_id': requester,
                'request_job_type': kw.get('request_type', '') and int(kw['request_type']) or False,
                'company': kw.get('request_for_comp', '') and int(kw['request_for_comp']) or False,
                'department_id': request_for_dept,
                'job_title_id': kw.get('request_role', '') and int(kw['request_role']) or False,
                'gender': kw.get('gender', ''),
                'degree_id': kw.get('education_level', '') and int(kw['education_level']) or False,
                'reason_id': kw.get('request_reason', '') and int(kw['request_reason']) or False,
                'office_id': kw.get('working_place', '') and int(kw['working_place']) or False,
                'job_type_id': kw.get('job_type', '') and int(kw['job_type']) or False,
                'no_of_recruitment': kw.get('request_qty', '') and int(kw['request_qty']) or False,
                'report_to': report_to,
                'description_en': kw.get('desc_english', ''),
                'description': kw.get('desc_vietnamese', ''),
                'preference': kw.get('preference_vietnamese', ''),
                'preference_en': kw.get('preference_english', ''),
                'requirements': kw.get('requirement_vietnamese', ''),
                'requirements_en': kw.get('requirement_english', ''),
                'job_applicant_ids' : [],
            })
            
            if values['requestor_id']:
                
                if values['requestor_id'] not in allow_employee_ids:
                    return http.local_redirect('/mysite/recruitment_request',
                                               query={'message': 'error'},
                                               keep_hash=True)
                requestor = hr_emp_obj.browse(cr, uid, values['requestor_id'], context=context)
                if requestor:
                    values.update({
                        'requestor_company_id': requestor.company_id and requestor.company_id.id or False,
                        'requestor_dept': requestor.department_id and requestor.department_id.id  or False,
                        'requestor_dev': requestor.division_id and requestor.division_id.id or False,
                        'requestor_role': requestor.title_id and requestor.title_id.id or False,
                    })
            
            if values['reason_id'] != 19 and kw.get('for_employees', ''):
                for_employees = map(int, kw['for_employees'].split(','))
                if not set(for_employees).issubset(set(allow_employee_ids)):
                    return http.local_redirect('/mysite/recruitment_request',
                                               query={'message': 'error'},
                                               keep_hash=True)
                values['reason_emp'] = [[6, False, for_employees]]
            if values:
                res = hr_job_obj.create(cr, uid, values, context=context)
                if res:
                    # submit form and get hrbp information
                    result = hr_job_obj.signal_workflow_ex(cr, uid, res, 'draft_waiting_hrbp')
                    if result:
                        hr_job_obj.write_change_state(cr, uid, res, 'draft_waiting_hrbp', 'ok')
                        first = self.gen_string_random(size=593)
                        last = self.gen_string_random(size=378)
                        message = first + str(kw.get('request_for_dept', '')) + last
        return http.local_redirect('/mysite/recruitment_request', query={'message': message}, keep_hash=True)

    def convert_request_date(self, date):
        if date:
            date = date.split('/')
            return date[2] + '-' + date[1] + '-' + date[0]
        return date

    def _get_hrbp_info(self, cr, uid, dept_id, context=None):
        if context is None:
            context = {}
        res = ''
        if dept_id:
            dept_id = int(dept_id)
            dept = request.registry['hr.department'].browse(cr, uid, dept_id, context=context)
            if dept:
                res = u'Yêu cầu tuyển dụng của bạn đã được gửi đến HRBPs: <ul>'
                for hrbp in dept.hrbps:
                    res += u'<li>'+ hrbp.name + (hrbp.login and ' (' + hrbp.login + ') ' or '') + (hrbp.title_id and ' - ' + hrbp.title_id.name or '') + u'</li>'
                res += u'</ul>'
        return res

    def gen_string_random(self, size=35, chars=string.ascii_uppercase + string.digits):
        return ''.join(random.choice(chars) for _ in range(size))

    @http.route('/mysite/insurance_registration', type='http', auth="user", website=True, keep_hash=True)
    def insurance_registration(self, **kw):
        cr, uid, context = request.cr, request.uid, request.context
        context = context or {}
        hr_emp_obj = request.registry['hr.employee']
        ins_per_obj = request.registry['vhr.insurance.period']
        emp_ids = hr_emp_obj.search(
            cr, uid, [['user_id', '=', uid]], context=context)
        today = datetime.today().strftime('%Y-%m-%d')
        ins_per_ids = ins_per_obj.search(cr, uid, [('from_date', '<=', today), ('to_date', '>=', today)])
        res = {
           'format_number': self.format_number,
           'format_money': self.format_money,
           'format_date': self.format_date,
           'message': '',
           'is_collaborator': False,
           'families': [],
           'packages': [],
           'my_editable': True,
           'is_buy': False,
           'allow_regis': False
        }
        
        if emp_ids and ins_per_ids:

            check_contract_collabor = self._check_contract_collaborator_by_title(cr, uid, uid, context)
            check_contract_official = self._check_contract_official(cr, uid, uid, context)
            
            if check_contract_collabor or check_contract_official:
                res['allow_regis'] = True
            
            if check_contract_collabor:
                res['is_collaborator'] = True
            ins_reg_obj = request.registry['vhr.insurance.registration']
            
            ins_reg_ids = ins_reg_obj.search(cr, uid, [('period_id', 'in', ins_per_ids), ('employee_id', 'in', emp_ids)])
            
            if ins_reg_ids:
                res['my_editable'] = False
            
            for ins_reg in ins_reg_obj.browse(cr, uid, ins_reg_ids):
                if ins_reg.is_buy:
                    res['is_buy'] = True
                res['families'] += ins_reg.family_ids
            
        return request.render('vhr_mysite.vhr_insurance_registration', res)

    @http.route('/mysite/_check_contract', type='json', auth="user", website=True)
    def check_contract(self, **kw):
        cr, uid, context = request.cr, request.uid, request.context
        context = context or {}
        hr_emp_obj = request.registry['hr.employee']
        emp_ids = hr_emp_obj.search(
            cr, uid, [['user_id', '=', uid]], context=context)
        if emp_ids:
            check_contract = self._check_contract_collaborator_by_title(cr, uid, uid, context)
            if check_contract:
                return True # is Collaborator
        return False

    @http.route('/mysite/check_insurance_edit', type='json', auth="user", website=True)
    def check_insurance_edit(self, **kw):
        cr, uid, context = request.cr, request.uid, request.context
        context = context or {}
        hr_emp_obj = request.registry['hr.employee']
        emp_ids = hr_emp_obj.search(
            cr, uid, [['user_id', '=', uid]], context=context)
        if emp_ids:
            ins_per_obj = request.registry['vhr.insurance.period']
            ins_reg_obj = request.registry['vhr.insurance.registration']
            
            today = datetime.today().strftime('%Y-%m-%d')
            ins_per_ids = ins_per_obj.search(cr, uid, [('from_date', '<=', today), ('to_date', '>=', today)])
            ins_reg_ids = ins_reg_obj.search(cr, uid, [('period_id', 'in', ins_per_ids), ('employee_id', 'in', emp_ids)])
            
            if ins_reg_ids:
                return False
        return True

    @http.route('/mysite/set_insurance_registration_info', type='json', auth="user", website=True)
    def set_insurance_registration_info(self, **kw):
        
        cr, uid, context = request.cr, request.uid, request.context
        context = context or {}
        hr_emp_obj = request.registry['hr.employee']
        ins_per_obj = request.registry['vhr.insurance.period']
        ins_reg_obj = request.registry['vhr.insurance.registration']
        
        emp_ids = hr_emp_obj.search(
            cr, uid, [['user_id', '=', uid]], context=context)
        family_data = kw.get('family_data', False)
        is_buy = kw.get('registration', False)
        
        # Get current period
        today = datetime.today().strftime('%Y-%m-%d')
        ins_per_ids = ins_per_obj.search(cr, uid, [('from_date', '<=', today), ('to_date', '>=', today)])
        
        if ins_per_ids and emp_ids:
            ins_reg_vals = {
                'employee_id': emp_ids[0],
                'period_id': ins_per_ids[0],
                'is_buy': is_buy
            }
        
            if family_data and len(family_data) >= 2:
                family_data = family_data[1:]
                
                family_ids = []
                for family in family_data:
                    family_ids.append([0, False, family])
                ins_reg_vals['family_ids'] = family_ids
                
            check_contract = self._check_contract_official(cr, uid, uid, context)
            # If Official
            if check_contract:
                ins_reg_vals['is_buy'] = True
            # If Collaborator
            else:
                check_contract = self._check_contract_collaborator_by_title(cr, uid, uid, context)
                if check_contract and not is_buy:
                    ins_reg_vals['is_buy'] = False
                    ins_reg_vals['family_ids'] = [(5)]
            return ins_reg_obj.create_update_reg(cr, uid, ins_reg_vals, emp_ids[0])
        return False

