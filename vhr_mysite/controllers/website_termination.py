# -*- coding: utf-8 -*-
import logging

from openerp import http
from openerp.addons.web import http
from openerp.addons.web.http import request
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.addons.vhr_common.model import vhr_encode
from openerp.addons.vhr_human_resource.model.vhr_termination_request import STATES

log = logging.getLogger(__name__)

#Giang - Define label for state
data = {}        
for key, value in STATES:
    data[key] = value


class website_termination(http.Controller):

    @http.route(['/termination'], methods=['GET', 'POST'], type='http', auth='user', website=True)
    def termination(self, **post):
        res = {'header': u'Đơn xin thôi việc', 'btn_confirm': u'Gửi', 'btn_approve': u'Approve',
               'lm_approve': False, 'hr_approve': False, 'dh_approve': False, 'btn_reject': u'Reject'}
        context = dict(request.context, show_address=True, no_tag_br=True)
        if context is None:
            context = {}
        cr, uid = request.cr, request.uid
        ter_obj = request.registry['vhr.termination.request']
        emp_obj = request.registry['hr.employee']
        wkr_obj = request.registry['vhr.working.record']
        msg = ''
        err = False
        ter_id = False
        emp_ids = emp_obj.search(cr, uid, [('user_id', '=', uid)], context=context)
        res_emp = emp_obj.read(cr, uid, emp_ids[0], [], context=context)
        comp_id = res_emp.get('company_id', False) and res_emp['company_id'][0] or False
        domain = [('employee_id', 'in', emp_ids), ('company_id', '=', comp_id),
                  ('state', 'in', [False, 'finish']), ('active', '=', True)]
        record_ids = wkr_obj.search(cr, uid, domain, context=context)
        today = date.today()
        res_contract, gap_days, get_lwd = ter_obj.get_data_from_effective_contract(cr, uid, emp_ids[0], comp_id, context=context)
        date_end = today + relativedelta(days=gap_days)
        date_end = date_end.strftime(DEFAULT_SERVER_DATE_FORMAT)
        wkr = {}
        if record_ids:
            wkr = wkr_obj.browse(cr, uid, record_ids[0], context=context)
        else:
            err = u'Không tìm thấy working record. Vui lòng liên hệ C&B để xử lý!'

        if post.get('ter_id'):
            ter_id = int(post.get('ter_id'))
        if post and post.keys():
            e_id = post.keys()[0]
            try:
                ter_id = int(vhr_encode.decode(e_id))
            except:
                pass
        data = self.serialize_post(post, ter_obj._columns.keys())
        if data and not ter_id and record_ids:
            expect_date = self.format_date_sys(data.get('date_end_working_expect', False))
            create_data = {
                'employee_id': emp_ids[0], 'working_record_id': record_ids and record_ids[0] or False,
                'company_id': wkr.company_id.id, 'contract_id': wkr.contract_id.id,
                'request_date': today.strftime(DEFAULT_SERVER_DATE_FORMAT), 'date_end_working_follow_rule': date_end,
                'date_end_working_expect': expect_date, 'date_end_working_approve': expect_date
            }
            data.update(create_data)
            try:
                context.update({'state': 'draft', 'is_offline': False, 'action': 'submit',
                                'is_official': wkr.contract_id.type_id and wkr.contract_id.type_id.is_official or False})
                ter_id = ter_obj.create(cr, uid, data, context=context)
                if ter_id:
                    ter_obj.execute_workflow(cr, uid, [ter_id], context=context)
                msg = u'Đăng ký thành công'
            except Exception, e:
                err = e.message and e.message
                if not err:
                    err = e.value
                cr.rollback()
        if ter_id:
            data = ter_obj.read(cr, uid, ter_id, [], context=context)
            is_emp = data.get('employee_id', False) and data['employee_id'][0] in emp_ids
            if is_emp or data.get('is_lm', False) or data.get('is_dept_head', False) or data.get('is_hrbp', False):
                emp_data = {
                    'emp_name': data.get('employee_id', False) and data['employee_id'][1] or '',
                    'department': data.get('department_id', '') and data['department_id'][1] or '',
                    'company': data.get('company_id', '') and data['company_id'][1] or '',
                    'reporter': data.get('supervisor_id', '') and data['supervisor_id'][1] or '',
                    'contract': data.get('contract_id', '') and data['contract_id'][1] or '',
                    'office':  data.get('office_id', '') and data['office_id'][1] or '',
                    'job_title': data.get('job_title_id', '') and data['job_title_id'][1] or '',
                    'job_level': data.get('job_level_id', '') and data['job_level_id'][1] or '',
                    'contract_type': data.get('contract_type_id', '') and data['contract_type_id'][1] or '',
                }
                data.update(emp_data)

                if data.get('is_lm', False) and data.get('state') == 'supervisor':
                    res['lm_approve'] = True
                    context.update({'state': 'supervisor'})
                if data.get('is_dept_head', False) and data.get('state') == 'dept_head':
                    res['dh_approve'] = True
                    context.update({'state': 'dept_head'})
                if data.get('is_hrbp', False) and data.get('state') == 'hrbp':
                    res['hr_approve'] = True
                    context.update({'state': 'hrbp'})

                if post.get('action') in ['approve', 'reject'] and (res['dh_approve'] or res['lm_approve']):
                    context.update({
                        'action': post['action'], 'is_offline': False,
                        'is_official': wkr.contract_id.type_id and wkr.contract_id.type_id.is_official or False
                    })
                    val = {}
                    if res['lm_approve']:
                        val = {
                            'date_end_working_approve': self.format_date_sys(post.get('date_end_working_approve', False)),
                            'lm_note': post.get('lm_note', False)
                        }
                    if res['dh_approve'] and post.get('date_end_working_approve', False):
                        val = {
                            'date_end_working_approve': self.format_date_sys(post.get('date_end_working_approve', False)),
                        }
                    ter_obj.write(cr, uid, [ter_id], val, context=context)
                    if ter_obj.execute_workflow(cr, uid, [ter_id], context=context):
                        res['dh_approve'] = res['lm_approve'] = False
                        data.update(post)
                        data.update({'date_end_working_approve': self.format_date_sys(data.get('date_end_working_approve', False))})
            else:
                data = {}
                ter_id = False
                err = u'Bạn Không Thể Xem Nội Dung. Vui Lòng Liên Hệ Administrator!'
        else:
            if res_emp and wkr.contract_id.type_id and wkr.contract_id.type_id.is_official:
                data = {'emp_name': '', 'emp_code': '', 'request_date': today.strftime(DEFAULT_SERVER_DATE_FORMAT)}
                data.update({'date_end_working_follow_rule': date_end})
                if record_ids:
                    emp_data = {
                        'emp_name': res_emp['name'], 'employee_code': res_emp['code'],
                        'department': wkr.department_id_new.complete_code, 'company': wkr.company_id.name,
                        'reporter': res_emp.get('report_to', '') and res_emp['report_to'][1] or '',
                        'contract': wkr.contract_id.name, 'office': wkr.office_id_new.name,
                        'job_title': wkr.job_title_id_new.name, 'job_level': wkr.job_level_id_new.name,
                        'contract_type': wkr.contract_id.type_id and wkr.contract_id.type_id.name or '',
                    }
                    data.update(emp_data)
                    data.update(res_contract)
                if err and post:
                    if 'state' in data:
                        del data['state']
            else:
                err = u'Bạn Không Có Quyền Tạo Đơn Xin Nghỉ Việc. Vui Lòng Liên Hệ Administrator!'
                data = {}
                ter_id = False

        res.update({'ter_id': ter_id, 'data': data, 'message': msg, 'error': err,
                    'format_date': self.format_date})

        return request.website.render("vhr_mysite.termination", res)

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

    #giang - get state label for termination
    def ter_state_label(self, state):  
        if state in data:
            return data[state]
        return state

    #giang
    @http.route(['/terminations'], methods=['GET', 'POST'], type='http', auth='user', website=True)
    def termination_list(self, **post):        
        context = dict(request.context, show_address=True, no_tag_br=True)
        if context is None:
            context = {}
        cr, uid = request.cr, request.uid
        try:            
            res = {'header': u'Thông tin nghỉ việc'}            
            leave_data = self.get_termination_list(cr, uid, context=context)
            if leave_data.__len__() == 0:
                res = {"error": u'Bạn Không Thể Xem Nội Dung. Vui Lòng Liên Hệ Administrator!'}
            res.update({'ter_lines': leave_data, 'format_date': self.format_date, 'get_label': self.ter_state_label})
        except Exception, e:
            res = {"error": u'Bạn Không Thể Xem Nội Dung. Vui Lòng Liên Hệ Administrator!'}
            message = e.message
            log.info('Terminations Error %s' % message)
        return request.website.render("vhr_mysite.termination_list", res)
    
    #giang
    def get_termination_list(self, cr, uid, context=None):
        if context is None:
            context = {}
        res = []
        context.update({'force_search_vhr_termination_request': 1, 'filter_by_permission_for_termination': 1})
        fields_lst = ['employee_id', 'department_id', 'id', 'employee_code', 'state', 'request_date', 'supervisor_id',
                      'current_state', 'resign_date', 'date_end_working_expect', 'date_end_working_approve',
                      'date_end_working_follow_rule', 'job_title_id']
        ter_obj = request.registry['vhr.termination.request']
        if uid:                                
            ter_ids = ter_obj.search(cr, uid, [], order='request_date desc', context=context)
            for item in ter_obj.read(cr, uid, ter_ids, fields_lst, context=context):
                item['department'] = item.get('department_id', False) and item['department_id'][1] or ''
                item['employee_name'] = item.get('employee_id', False) and item['employee_id'][1] or ''
                item['job_title'] = item.get('job_title_id', False) and item['job_title_id'][1] or ''
                res.append(item)
        return res

website_termination()