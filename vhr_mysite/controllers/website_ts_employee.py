# -*- coding: utf-8 -*-
import logging

from openerp import http
from openerp.addons.web import http
from openerp.addons.web.http import request
from datetime import datetime
import time
import ast
import json

log = logging.getLogger(__name__)

LEAVE_STATES = {'refuse': 'Cancelled', 'draft': 'Draft', 'confirm': 'Waiting LM',
                'validate1': 'Waiting DH', 'validate2': 'Waiting CB', 'validate': 'Finish'}
OT_STATES = {'draft': 'Draft', 'approve': 'Waiting LM', 'finish': 'Finish', 'cancel': 'Cancel'}

class website_leave_registration(http.Controller):

    @http.route(['/leave'], methods=['GET', 'POST'], type='http', auth='user', website=True)
    def leave(self, **post):
        res = {"error": u"Bạn Không Thể Xem Nội Dung. Vui Lòng Liên Hệ Administrator"}
        context = dict(request.context, show_address=True, no_tag_br=True)
        cr, uid = request.cr, request.uid
        try:
            res = {'header': u'Quá Trình Nghỉ Của Nhân Viên'}
            holiday_obj = request.registry['hr.holidays']
            leave_data = holiday_obj.get_leave_history(cr, uid, context=context)
            res.update({'leave_lines': leave_data, 'format_date': self.format_date, 'state_label': self.leave_state_label})

        except Exception, e:
            message = e.message
            log.info('Leave Registration Error %s' % message)

        return request.website.render("vhr_mysite.leave", res)

    @http.route(['/leave/registration'], methods=['GET', 'POST'], type='http', auth='user', website=True)
    def leave_registration(self, **post):
        res = {'header': u'Đăng Ký Nghỉ Online', 'btn_confirm': u'Gửi', 'btn_approve': u'Approve',
               'lm_approve': False, 'dh_approve': False, 'btn_reject': u'Reject', "can_renew": False}
        context = dict(request.context, show_address=True, no_tag_br=True)
        cr, uid = request.cr, request.uid
        holiday_obj = request.registry['hr.holidays']
        line_obj = request.registry['vhr.holiday.line']
        holiday_status_obj = request.registry['hr.holidays.status']
        param_obj = request.registry['ir.config_parameter']
        emp_obj = request.registry['hr.employee']
        msg = ''
        err = False
        leave_id = False
        emp_ids = emp_obj.search(cr, uid, [('user_id', '=', uid)], context=context)
        res_emp = emp_obj.read(cr, uid, emp_ids[0], ['gender','company_id','department_id',
                                                     'parent_id','report_to','name','code'], context=context)
        gender = res_emp.get('gender', False)
        comp_id = res_emp.get('company_id', False) and res_emp['company_id'][0] or False
        dept_id = res_emp.get('department_id', False) and res_emp['department_id'][0] or False
        dept_name = res_emp.get('department_id', False) and res_emp['department_id'][1] or ""
        dh_id = res_emp.get('parent_id', False) and res_emp['parent_id'][0] or False
        dh_name = res_emp.get('parent_id', False) and res_emp['parent_id'][1] or ""
        report_to_id = res_emp.get('report_to', False) and res_emp['report_to'][0] or False
        report_to = res_emp.get('report_to', False) and res_emp['report_to'][1] or ""

        args = [('holiday_status_group_id.gender', 'in', ['both', gender])]
        is_collaborator, is_probation = holiday_obj.is_collaborator_or_probation(cr, uid, emp_ids[0], comp_id, context)
        if is_collaborator:
            args += [('is_collaborator', '=', True)]
                
        elif is_probation:
            team_building_code = param_obj.get_param(cr, uid, 'ts_leave_type_outing_teambuilding') or ''
            team_building_code = team_building_code.split(',')
            args.append(('code', 'not in', team_building_code))
        domain = holiday_obj.get_domain_of_holiday_status_id(cr, uid, emp_ids[0], context=context)
        args += domain
        type_ids = holiday_status_obj.search(cr, uid, args, context=context)
        default_type_ids = holiday_status_obj.search(cr, uid, [('code', '=', 'P')], context=context)
        
        #Bo sung loai nghi phep nam cho CTV lam viec tren 12 thang
        if is_collaborator:
            find_emp_ids = holiday_obj.get_colla_emp_satisfy_condition_to_gen_annual_leave(cr, uid, [emp_ids[0]], context)
            if find_emp_ids:
                leave_type_code = param_obj.get_param(cr, uid, 'ts.leave.type.default.code') or ''
                leave_type_code = leave_type_code.split(',')
    
                status_ids = holiday_status_obj.search(cr, uid, [('code', 'in', leave_type_code)])
                type_ids.extend(status_ids)
        
        type_id = default_type_ids and default_type_ids[0] or False
        holiday_status = holiday_status_obj.browse(cr, uid, type_ids, context=context)
        if context is None:
            context = {}

        if post.get('leave_id'):
            leave_id = int(post.get('leave_id'))
        data = self.serialize_post(post, holiday_obj._columns.keys())
        if post.get('leave_detail_lines'):
            if not leave_id:
                lines, total_days, total_hours = self.gen_leave_lines(post['leave_detail_lines'], data.get('date_from'),
                                                                      data.get('date_to'))
                if not data.get('number_of_days_temp'):
                    data['number_of_days_temp'] = total_days
                data.update({'holiday_line_ids': lines, 'number_of_hours': total_hours})

        if data and not leave_id:
            data.update({'department_id': dept_id, 'dept_head_id': dh_id, 'report_to_id': report_to_id,
                         'employee_id': emp_ids[0], 'type': 'remove'})
            try:
                if data.get('number_of_days_temp', 0) > 0 and isinstance(data.get('holiday_line_ids', []), (list, dict)) \
                        and len(data.get('holiday_line_ids', [])) > 0:
                    if data.get('date_from') < time.strftime("%Y-%m-%d"):
                        err = u'Bạn không thể đăng ký ngày quá khứ! Vui lòng liên hệ admin để được hỗ trợ!'
                    else:
                        context.update({'action_directly': True})
                        if 'to_date_insurance' in data and not data.get('to_date_insurance', False):
                            del data['to_date_insurance']
                        leave_id = holiday_obj.create(cr, uid, data, context=context)
                        if leave_id:
                            holiday_obj.action_next(cr, uid, [leave_id], context=context)
                            res['can_renew'] = True
                        msg = u'Đăng ký thành công'
                else:
                    err = u'Số lượng đăng ký phải lớn hơn 0!'
            except Exception, e:
                err = e.message and e.message
                if not err:
                    err = e.value
                cr.rollback()

        if leave_id:
            leave_data = holiday_obj.read(cr, uid, leave_id, [], context=context)
            department_id = leave_data.get('department_id', False) and leave_data['department_id'][0]
            
            is_emp = leave_data.get('employee_id', False) and leave_data['employee_id'][0] in emp_ids
            is_lm = leave_data.get('report_to_id', False) and \
                           (leave_data['report_to_id'][0] in emp_ids or holiday_obj.is_delegate_from(cr, uid, uid, leave_data['report_to_id'][0],department_id))
            is_dh = leave_data.get('dept_head_id', False) and \
                           (leave_data['dept_head_id'][0] in emp_ids or holiday_obj.is_delegate_from(cr, uid, uid, leave_data['dept_head_id'][0],department_id))
            
            if is_emp or is_lm or is_dh:
                type_id = leave_data.get('holiday_status_id', False) and leave_data['holiday_status_id'][0] or False
                leave_data['department'] = leave_data.get('department_id', '') and leave_data['department_id'][1] or dept_name
                leave_data['employee_name'] = leave_data.get('employee_id', '') and leave_data['employee_id'][1] or ''
                leave_data['dept_head'] = leave_data.get('dept_head_id', '') and leave_data['dept_head_id'][1] or dh_name
                leave_data['reporter'] = leave_data.get('report_to_id', '') and leave_data['report_to_id'][1] or report_to
                if is_lm and leave_data.get('state') == 'confirm':
                    res['lm_approve'] = True
                if is_dh and leave_data.get('state') == 'validate1':
                    res['dh_approve'] = True
                if post.get('action') in ['validate', 'reject'] and (res['dh_approve'] or res['lm_approve']):
                    context.update({'action': post['action']})
                    if holiday_obj.execute_workflow(cr, uid, [leave_id], context=context):
                        res['dh_approve'] = res['lm_approve'] = False
                line_ids = leave_data.get('holiday_line_ids', [])
                leave_lines = {}
                i = 1
                for line in line_obj.read(cr, uid, list(set(line_ids)), context=context):
                    all_day = shift_d = shift_n = 1
                    if line['status'] == 'morning':
                        all_day = shift_n = 0
                    elif line['status'] == 'afternoon':
                        all_day = shift_d = 0
                    leave_lines["%s" % i] = {
                        "date": "%s/%s/%s" % (line['date'][8:10], line['date'][5:7], line['date'][:4]),
                        "all_day": all_day,
                        "shift_d": shift_d,
                        "shift_n": shift_n,
                        "remove": 0,
                    }
                    if leave_data['state'] and leave_data['state'] != 'draft':
                        leave_lines["%s" % i].update({'readonly': 1})
                    i += 1
                leave_data['leave_detail_lines'] = leave_lines and json.dumps(leave_lines) or ''
                no_salary_type_ids = holiday_status_obj.search(cr, uid, [('holiday_status_group_id.code', '=', '0007')], context=context)
                repeat_type_ids = holiday_status_obj.search(cr, uid, [
                    ('is_check_remain_day_on_current_registration.code', '=', True)], context=context)
                if type_id in no_salary_type_ids:
                    leave_data.update({'max_leaves': '', 'remaining_leaves': '', 'total_leaves': ''})
                if type_id in repeat_type_ids:
                    leave_data.update({'remaining_leaves': '', 'leaves_submitted': ''})
            else:
                leave_data = {}
                leave_id = False
                err = u'Bạn Không Thể Xem Nội Dung. Vui Lòng Liên Hệ Administrator!'
        else:
            now = time.strftime("%Y-%m-%d")
            leave_data = {'employee_name': '', 'employee_code': '', 'dept_code': '', 'create_date': now}
            if res_emp:
                leave_data.update({'employee_name': res_emp['name'], 'employee_code': res_emp['code'],
                                   'date_from': False, 'date_to': False,
                                   'department': dept_name, 'dept_head': dh_name, 'reporter': report_to})
                status = holiday_status_obj.get_days(cr, uid, type_ids, emp_ids[0], comp_id, date_from=now, context=context)
                if type_ids and (not type_id or type_id not in type_ids):
                    type_id = type_ids[0]
                leave_data.update(status[type_id])
                if 'max_leaves' in leave_data and leave_data['max_leaves'] < 0:
                    leave_data['max_leaves'] = 0
                if err and post:
                    if post.get("date_from", False):
                        post['date_from'] = self.format_date_sys(post['date_from'])
                    if post.get("date_to", False):
                        post['date_to'] = self.format_date_sys(post['date_to'])
                    if post.get("holiday_status_id", False):
                        type_id = int(post['holiday_status_id'])
                        leave_data.update(status[type_id])
                    leave_data.update(post)
                    if 'state' in leave_data:
                        del leave_data['state']

        res.update({'leave_id': leave_id, 'leave_data': leave_data, 'holiday_status': holiday_status,
                    'type_id': type_id, 'message': msg, 'error': err, 'format_date': self.format_date})

        return request.website.render("vhr_mysite.leave_registration", res)

    @http.route(['/leave/approval'], methods=['GET', 'POST'], type='http', auth='user', website=True)
    def leave_approval(self, **post):
        res = {"error": u"Bạn Không Thể Xem Nội Dung. Vui Lòng Liên Hệ Administrator"}
        context = dict(request.context, show_address=True, no_tag_br=True)
        cr, uid = request.cr, request.uid
        try:
            res = {'header': u'Đăng Ký Nghỉ Phép Chờ Duyệt'}
            holiday_obj = request.registry['hr.holidays']
            leave_data = holiday_obj.get_leave_approval(cr, uid, context=context)
            res.update({'leave_lines': leave_data, 'format_date': self.format_date, 'state_label': self.leave_state_label})

        except Exception, e:
            message = e.message
            log.info('Leave Registration Error %s' % message)

        return request.website.render("vhr_mysite.leave", res)

    @http.route(['/overtime'], methods=['GET', 'POST'], type='http', auth='user', website=True)
    def overtime(self, **post):
        res = {"error": u"Bạn Không Thể Xem Nội Dung. Vui Lòng Liên Hệ Administrator"}
        context = dict(request.context, show_address=True, no_tag_br=True)
        cr, uid = request.cr, request.uid
        try:
            res = {'header': u'Đăng Ký Ngoài Giờ'}
            overtime_obj = request.registry['vhr.ts.overtime']
            overtime_data = overtime_obj.get_overtime_history(cr, uid, context=context)
            res.update({'overtime_lines': overtime_data, 'format_date': self.format_date})
        except Exception, e:
            message = e.message
            log.info('Overtime Error %s' % message)

        return request.website.render("vhr_mysite.overtime", res)

    @http.route(['/overtime/approval'], methods=['GET', 'POST'], type='http', auth='user', website=True)
    def overtime_approval(self, **post):
        res = {"error": u"Bạn Không Thể Xem Nội Dung. Vui Lòng Liên Hệ Administrator"}
        context = dict(request.context, show_address=True, no_tag_br=True)
        cr, uid = request.cr, request.uid
        if context is None:
            context = {}
        try:
            res = {'header': u'Đăng Ký Ngoài Giờ Chờ Duyệt'}
            overtime_obj = request.registry['vhr.ts.overtime']
            overtime_data = overtime_obj.get_overtime_approval(cr, uid, context=context)
            res.update({'overtime_lines': overtime_data, 'format_date': self.format_date, 'state_label': self.ot_state_label})
        except Exception, e:
            message = e.message
            log.info('Overtime Error %s' % message)

        return request.website.render("vhr_mysite.overtime", res)

    @http.route(['/overtime/registration'], methods=['GET', 'POST'], type='http', auth='user', website=True)
    def overtime_registration(self, **post):
        res = {'header': u'Đăng Ký Ngoài Giờ', 'btn_confirm': u'Gửi',
               'lm_approve': False,  'btn_approve': u'Approve', 'btn_reject': u'Reject', 'can_renew': False}
        context = dict(request.context, show_address=True, no_tag_br=True)
        cr, uid = request.cr, request.uid
        overtime_obj = request.registry['vhr.ts.overtime']
        ot_detail_obj = request.registry['vhr.ts.overtime.detail']
        leave_obj = request.registry['hr.holidays']
        emp_obj = request.registry['hr.employee']
        msg = ''
        err = False
        ot_id = False
        emp_ids = emp_obj.search(cr, uid, [('user_id', '=', uid)], context=context)
        res_emp = emp_obj.read(cr, uid, emp_ids[0], ['company_id','department_id','code',
                                                     'report_to','gender','name'], context=context)
        if post.get('ot_id'):
            ot_id = int(post.get('ot_id'))
        data = self.serialize_post(post, overtime_obj._columns.keys())
        if post.get('overtime_detail_lines'):
            if not ot_id:
                comp_id = res_emp.get('company_id', False) and res_emp['company_id'][0] or False
                lines = self.gen_overtime_lines(post['overtime_detail_lines'], res_emp['id'], comp_id)
                data.update({'overtime_detail_ids': lines, 'company_id': comp_id, 'employee_code': res_emp['code']})

        if data:
                dept_id = res_emp.get('department_id', False) and res_emp['department_id'][0] or False
                report_to_id = res_emp.get('report_to', False) and res_emp['report_to'][0] or False
                data.update({'department_id': dept_id, 'report_to_id': report_to_id, 'state': 'draft'})
                try:
                    ot_id = overtime_obj.create(cr, uid, data, context=context)
                    if ot_id:
                        context = {'state': 'draft', 'action': 'submit'}
                        overtime_obj.execute_workflow(cr, uid, [ot_id], context=context)
                        res['can_renew'] = True
                    msg = u'Đăng ký thành công'

                except Exception, e:
                    err = e.message and e.message
                    if not err:
                        err = e.value
                    cr.rollback()

        if ot_id:
            ot_data = overtime_obj.read(cr, uid, ot_id, [], context=context)
            department_id = ot_data.get('department_id', False) and ot_data['department_id'][0]
            is_lm = ot_data.get('report_to', False) and \
                    (ot_data['report_to'][0] in emp_ids or leave_obj.is_delegate_from(cr, uid, uid, ot_data['report_to'][0], department_id, 'vhr.ts.overtime'))
            is_emp = ot_data.get('employee_id', False) and ot_data['employee_id'][0] in emp_ids
            if is_emp or is_lm:
                ot_data['department'] = ot_data.get('department_id', False) and ot_data['department_id'][1] or ''
                ot_data['employee_name'] = ot_data.get('employee_id', False) and ot_data['employee_id'][1] or ''
                ot_data['reporter'] = ot_data.get('report_to', False) and ot_data['report_to'][1] or ''
                line_ids = ot_data.get('overtime_detail_ids', [])
                if is_lm and ot_data.get('state') == 'approve':
                    res['lm_approve'] = True
                    if post.get('overtime_detail_lines'):
                        lines = ast.literal_eval(post.get('overtime_detail_lines'))
                        for key, line in lines.iteritems():
                            if line.get('line_id') and 'is_compensation_leave' in line:
                                ot_detail_obj.write(cr, uid, [line['line_id']], {
                                    'is_compensation_leave': line.get('is_compensation_leave', False)}, context=context)

                    if post.get('action') in ['submit', 'reject']:
                        context.update({'action': post['action'], 'state': ot_data.get('state', False)})
                        if overtime_obj.execute_workflow(cr, uid, [ot_id], context=context):
                            res['lm_approve'] = False
                ot_lines = {}
                i = 1
                for line in ot_detail_obj.read(cr, uid, list(set(line_ids)), context=context):
                    ot_lines["%s" % i] = {
                        "line_id": line['id'],
                        "date_off": line['correct_date_off'].replace('-', '/'),
                        "notes": line['notes'],
                        "start_time": line['correct_start_time'],
                        "end_time": line['correct_end_time'],
                        "break_time": line['break_time'],
                        "total_hours_register": line['correct_total_hours_register'],
                        "is_compensation_leave": line['is_compensation_leave'] and 1 or 0,
                    }
                    if ot_data['state'] and ot_data['state'] != 'draft':
                        ot_lines["%s" % i].update({'readonly': 1})
                    if is_lm and ot_data.get('state') == 'approve':
                        ot_lines["%s" % i].update({'lm_edit': 1})
                    i += 1
                ot_data['overtime_detail_lines'] = ot_lines and json.dumps(ot_lines) or ''
            else:
                ot_data = {}
                ot_id = False
                err = u'Bạn Không Thể Xem Nội Dung. Vui Lòng Liên Hệ Administrator!'
        else:
            now = time.strftime("%Y-%m-%d")
            ot_data = {'employee_name': '', 'employee_code': '', 'dept_code': '', 'request_date': now}
            if res_emp:
                dept = res_emp.get('department_id', False) and res_emp['department_id'][1] or ''
                reporter = res_emp.get('report_to', False) and res_emp['report_to'][1] or ''
                ot_data.update({'employee_name': res_emp['name'], 'employee_code': res_emp['code'],
                                'department': dept, 'reporter': reporter})
                if err and post:
                    ot_data.update(post)
                    if 'state' in ot_data:
                        del ot_data['state']

        res.update({'ot_id': ot_id, 'overtime_data': ot_data, 'message': msg, 'error': err,
                    'format_date': self.format_date})
        return request.website.render("vhr_mysite.overtime_registration", res)

    @http.route('/mysite/get_holiday_status', type='json', auth="user", website=True)
    def get_holiday_status(self, **kw):
        res = {}
        context = dict(request.context, show_address=True, no_tag_br=True)
        cr, uid = request.cr, request.uid
        holiday_obj = request.registry['hr.holidays']
        holiday_status_obj = request.registry['hr.holidays.status']
        emp_obj = request.registry['hr.employee']
        param_obj = request.registry['ir.config_parameter']
        emp_ids = emp_obj.search(cr, uid, [('user_id', '=', uid)], context=context)
        res_emp = emp_obj.read(cr, uid, emp_ids[0], ['company_id', 'gender'], context=context)
        gender = res_emp.get('gender', False)
        comp_id = res_emp.get('company_id', False) and res_emp['company_id'][0] or False
        args = [('holiday_status_group_id.gender', 'in', ['both', gender])]
        is_collaborator, is_probation = holiday_obj.is_collaborator_or_probation(cr, uid, emp_ids[0], comp_id, context)
        if is_collaborator:
            args += [('is_collaborator', '=', True)]
        elif is_probation:
            team_building_code = param_obj.get_param(cr, uid, 'ts_leave_type_outing_teambuilding') or ''
            team_building_code = team_building_code.split(',')
            args.append(('code', 'not in', team_building_code))

        type_ids = holiday_status_obj.search(cr, uid, args, context=context)
        no_salary_type_ids = holiday_status_obj.search(cr, uid, [('holiday_status_group_id.code', '=', '0007')], context=context)
        repeat_type_ids = holiday_status_obj.search(cr, uid, [('is_check_remain_day_on_current_registration', '=', True)], context=context)
        if emp_ids and type_ids:
            now = time.strftime("%Y-%m-%d")
            res = holiday_status_obj.get_days(cr, uid, type_ids, emp_ids[0], comp_id, date_from=now, context=context)
            for item in holiday_status_obj.browse(cr, uid, type_ids, context):
                if 'max_leaves' in res[item.id] and res[item.id]['max_leaves'] < 0:
                    res[item.id]['max_leaves'] = 0
                if item.id in no_salary_type_ids:
                    res[item.id].update({'max_leaves': '', 'remaining_leaves': '', 'total_leaves': ''})
                if item.id in repeat_type_ids:
                    res[item.id].update({'remaining_leaves': '', 'leaves_submitted': ''})
                res[item.id]['description'] = item.description

        return res

    @http.route('/mysite/get_holiday_line', type='json', auth="user", website=True)
    def get_holiday_line(self, **kw):
        result = {'alert': '', 'lines': {}, 'total_days': 0}
        context = dict(request.context, show_address=True, no_tag_br=True)
        cr, uid = request.cr, request.uid
        date_from = kw.get('date_from', False) and self.format_date_sys(kw['date_from']) or False
        date_to = kw.get('date_to', False) and self.format_date_sys(kw['date_to']) or False
        type_id = kw.get('type_id', False) and int(kw['type_id']) or False
        change_type = kw.get('type', False) and kw['type'] or False
        holiday_obj = request.registry['hr.holidays']
        holiday_status_obj = request.registry['hr.holidays.status']
        emp_obj = request.registry['hr.employee']

        status = holiday_status_obj.browse(cr, uid, type_id, context=context)
        if change_type == 'date_from' and status.check_to_date_insurance:
            date_to = False
        emp_ids = emp_obj.search(cr, uid, [('user_id', '=', uid)], context=context)
        res_emp = emp_obj.read(cr, uid, emp_ids[0], ['company_id'], context=context)
        no_salary_type_ids = holiday_status_obj.search(cr, uid, [('holiday_status_group_id.code', '=', '0007')], context=context)
        repeat_type_ids = holiday_status_obj.search(cr, uid, [('is_check_remain_day_on_current_registration', '=', True)], context=context)
        if emp_ids and date_from:
            comp_id = res_emp.get('company_id', False) and res_emp['company_id'][0] or False
            check_ins, to_date_ins = holiday_obj.update_insurance_date(cr, uid, emp_ids[0], comp_id, date_from, type_id, context=context)
            if (not date_to or date_to < date_from) and to_date_ins:
                date_to = to_date_ins.strftime('%Y-%m-%d') or False
            res = holiday_obj.onchange_date_range(cr, uid, [], emp_ids[0], comp_id, type_id, date_to, date_from, [])
            lines = res.get('value', False) and res['value'].get('holiday_line_ids', []) or []
            max_leaves = res.get('value', False) and res['value'].get('max_leaves', 0) or 0
            context.update({'date_from': date_from, 'date_to': date_to,'employee_id': emp_ids[0]})
            warning = res.get('warning', '') and res['warning'].get('message', '') or ''
            alert_note = res.get('value', '') and res['value'].get('alert_note', '') or ''
            alert = alert_note or warning
            res_update = holiday_obj.onchange_holiday_line(cr, uid, [], lines, type_id, max_leaves, context=context)
            if res.get('value', False) and res_update.get('value', False):
                res['value'].update(res_update['value'])
            result['alert'] = alert.strip().replace("  ", "")
            remove = 1
            if status.is_date_range_include_rest_date:
                remove = 0
            result['total_days'], result['lines'] = self.holiday_lines_to_string(lines, remove=remove)
            result['to_date_ins'] = to_date_ins and to_date_ins.strftime('%d/%m/%Y') or ''
            result['check_ins'] = check_ins and 1 or 0
            result.update(res.get('value', {}))
            if 'max_leaves' in result and result['max_leaves'] < 0:
                result['max_leaves'] = 0
            if type_id in no_salary_type_ids:
                result.update({'max_leaves': '', 'remaining_leaves': '', 'total_leaves': ''})
            if type_id in repeat_type_ids:
                    result.update({'remaining_leaves': '', 'leaves_submitted': ''})

        return result

    def holiday_lines_to_string(self, holiday_lines, remove=1):
        lines = {}
        index = 1
        total_days_temp = 0
        for line in holiday_lines:
            if not line or len(line) < 3 or line[0] != 0:
                continue
            lines[index] = {
                'date': self.format_date(line[2].get('date', False)),
                'readonly': line[2].get('is_edit_status', False) is False and 1 or 0,
                'number_of_days_temp': line[2].get('number_of_days_temp', False),
                'shift_d': line[2].get('status', False) in ['morning', 'full'] and 1 or 0,
                'shift_n': line[2].get('status', False) in ['afternoon', 'full'] and 1 or 0,
                'all_day': line[2].get('status', False) in ['full'] and 1 or 0,
                "remove": remove
            }
            total_days_temp += line[2].get('number_of_days_temp', 0)
            index += 1

        return total_days_temp, json.dumps(lines)

    def gen_leave_lines(self, data, date_from, date_to):
        lines = []
        context = dict(request.context, show_address=True, no_tag_br=True)
        cr, uid = request.cr, request.uid
        holiday_obj = request.registry['hr.holidays']
        emp_obj = request.registry['hr.employee']
        emp_ids = emp_obj.search(cr, uid, [('user_id', '=', uid)], context=context)
        total_days = 0
        total_hours = 0
        if emp_ids and data:
            res_emp = emp_obj.read(cr, uid, emp_ids[0], [], context=context)
            comp_id = res_emp.get('company_id', False) and res_emp['company_id'][0] or False
            list_date, dict_hours = holiday_obj.generate_date(cr, uid, emp_ids[0], comp_id, date_from[:10], date_to[:10])
            data = ast.literal_eval(data)
            for key, val in data.iteritems():
                status = 'full'
                number_of_days_temp = 1
                date = self.format_date_sys(val.get('date', False))
                if not val.get('all_day', False):
                    number_of_days_temp = 0.5
                    if val.get('shift_d', False):
                        status = 'morning'
                    elif val.get('shift_n', False):
                        status = 'afternoon'
                if not val.get('all_day', False) and not val.get('shift_d', False) and not val.get('shift_n', False):
                    number_of_days_temp = 0
                    status = ''
                    continue
                line = {
                    'date': date,
                    'status': status,
                    'number_of_days_temp': number_of_days_temp,
                }
                total_days += number_of_days_temp
                if dict_hours and date in dict_hours:
                    line.update({
                        'number_of_hours_in_shift': dict_hours[date],
                        'number_of_hours': dict_hours[date] * number_of_days_temp,
                    })
                    total_hours += dict_hours[date] * number_of_days_temp
                lines.append([0, 0, line])
        return lines, total_days, total_hours

    def gen_overtime_lines(self, data, emp_id, comp_id):
        now = time.strftime('%Y-%m-%d')
        lines = []
        if data:
            data = ast.literal_eval(data)
            for key, line in data.iteritems():
                start = line.get('start_time', 0)
                start = self.hours2float(start)
                end = line.get('end_time', 0)
                end = self.hours2float(end)
                break_time = int(line.get('break_time', 0))
                total_hours_register = line.get('total_hours_register', 0)
                total_hours_register = self.hours2float(total_hours_register)
                is_com_leave = int(line.get("is_compensation_leave", 0))
                line.update({'start_time': start, 'end_time': end, 'break_time': break_time,
                             'total_hours_register': total_hours_register, 'is_compensation_leave': is_com_leave,
                             'employee_id': emp_id, 'company_id': comp_id, 'request_date': now})
                lines.append([0, 0, line])
        return lines

    def hours2float(self, hours):
        res = 0
        if time:
            hm = hours.split(':')
            hh = int(hm[0])
            mm = float(hm[1])/60
            res = hh + mm
        return res

    def float2hours(self, num):
        res = 0
        if num:
            hm = str(num).split('.')
            hh = int(hm[0])
            mm = int(float(hm[1])*60)
            res = "%.2d:%.2d" % (hh, mm)
        return res

    def serialize_post(self, post, keys):
        res = {}
        if post:
            for key, val in post.iteritems():
                if key in keys:
                    try:
                        if key in ['date_from', 'date_to', 'to_date_insurance'] and len(val) == 10:
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

    def leave_state_label(self, state):
        if state in LEAVE_STATES:
            return LEAVE_STATES[state]
        return state

    def ot_state_label(self, state):
        if state in OT_STATES:
            return OT_STATES[state]
        return state


website_leave_registration()

