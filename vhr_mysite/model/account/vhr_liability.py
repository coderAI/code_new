# -*- coding: utf-8 -*-

from openerp.osv import osv, fields
from openerp import SUPERUSER_ID
from datetime import datetime


class vhr_liability(osv.osv):
    _name = 'vhr.liability'

    def _get_liability_ids_when_emp_change_dept(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        liability_ids = self.pool['vhr.liability'].search(cr, uid, [('employee_id', 'in', ids)], context=context)
        return liability_ids

    def _get_liability_ids_when_dept_change(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        child_dept_ids = self.search(cr, uid, [('id', 'child_of', ids)], context=context)
        ids.extend(child_dept_ids)
        employee_ids = self.pool['hr.employee'].search(cr, uid, [('department_id', 'in', ids)], context=context)
        liability_ids = self.pool['vhr.liability'].search(cr, uid, [('employee_id', 'in', employee_ids)], context=context)
        return liability_ids

    _columns = {
        "supplier_code": fields.integer("Supplier Code"),
        "document_no": fields.char("Document No", size=400),
        "name": fields.text("Description", size=8000),
        "reimbursement_day": fields.date("Reimbursement Day"),
        "employee_id": fields.many2one("hr.employee", "Employee", required=True),
        "employee_code": fields.related('employee_id', 'code', type='char', string='Employee Code', readonly=True),
        "div_name": fields.related('employee_id', 'department_id', 'parent_id', 'complete_code', type='char',
                                   relation='hr.department', string='Business Unit', readonly=True, store={
                                        'vhr.liability': (lambda self, cr, uid, ids, context=None: ids, ['employee_id'], 10),
                                        'hr.employee': (_get_liability_ids_when_emp_change_dept, ['department_id'], 11),
                                        'hr.department': (_get_liability_ids_when_dept_change, ['parent_id', 'code', 'complete_code'], 12),
                                   }),
        "close_day": fields.date("Close Day"),
        "advance_payment": fields.float("Advance Payment"),
        "document_day": fields.date("Document Day"),
        "department_name": fields.related('employee_id', 'department_id', 'code', type='char',
                                          relation='hr.department', string='Department', readonly=True,
                                          store={
                                                'vhr.liability': (lambda self, cr, uid, ids, context=None: ids, ['employee_id'], 10),
                                                'hr.employee': (_get_liability_ids_when_emp_change_dept, ['department_id'], 11),
                                                'hr.department': (_get_liability_ids_when_dept_change, ['parent_id', 'code', 'complete_code'], 12),
                                          }),
        'active': fields.boolean('Active'),
        'is_send_mail': fields.boolean('Mail Sent', readonly=True),
    }

    _defaults = {
        'active': True,
        'is_send_mail': False,
    }

    _rec_name = 'employee_id'

    def onchange_employee_id(self, cr, uid, ids, employee_id, context=None):
        if context is None:
            context = {}
        values = {
            'employee_code': '',
            'div_name': '',
            'department_name': '',
        }
        if employee_id:
            employee = self.pool['hr.employee'].browse(cr, uid, employee_id, context=context)
            if employee:
                values.update({
                    'employee_code': employee.code,
                    'div_name': employee.department_id and employee.department_id.parent_id and employee.department_id.parent_id.complete_code or '',
                    'department_name': employee.department_id and employee.department_id.code or '',
                })
        return {'value': values}

    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = []
        liability_datas = self.read(cr, uid, ids, ['employee_id', 'document_day', 'reimbursement_day', 'close_day'], context=context)
        for liability_data in liability_datas:
            list_temp_name = []
            emp_name = liability_data.get('employee_id', False) and liability_data['employee_id'][1] or False
            close_day = liability_data.get('close_day') and self._format_date(liability_data['close_day']) or False
            document_day = liability_data.get('document_day') and self._format_date(liability_data['document_day']) or False
            reimbursement_day = liability_data.get('reimbursement_day') and self._format_date(liability_data['reimbursement_day']) or False
            if emp_name:
                list_temp_name.append(emp_name)
            if document_day:
                list_temp_name.append(document_day)
            if reimbursement_day:
                list_temp_name.append(reimbursement_day)
            if close_day:
                list_temp_name.append(close_day)
            res.append((liability_data['id'], " - ".join(list_temp_name)))
        return res

    # Check user is Liability Manager or not
    def _check_user_is_liability_manager(self, cr, uid, context=None):
        if context is None:
            context = {}
        res = False
        if uid == SUPERUSER_ID:
            return True
        group_liability_manager = self.pool['ir.model.data'].get_object_reference(cr, uid, "vhr_mysite", "group_liability_manager")
        if not group_liability_manager:
            return res
        user_data = self.pool['res.users'].read(cr, uid, uid, ['groups_id'], context=context)
        if group_liability_manager[1] in user_data['groups_id']:
            res = True
        return res

    # Administrator or Liability Manager can see all of liabilites
    # Clickers just see only their liabilities
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context = {}
        if uid != SUPERUSER_ID and not self._check_user_is_liability_manager(cr, uid, context=context):
            related_emp_ids = self.pool['hr.employee'].search(cr, SUPERUSER_ID, [('user_id', '=', uid)], context=context)
            args.append(('employee_id', 'in', related_emp_ids))
        return super(vhr_liability, self).search(cr, uid , args, offset=offset, limit=limit, order=order, context=context, count=count)

    def read(self, cr, user, ids, fields=None, context=None, load='_classic_read'):
        if context is None:
            context = {}
        if user != SUPERUSER_ID and not self._check_user_is_liability_manager(cr, user, context=context):
            all_liability_ids = self.search(cr, user, [], context=context)
            for liability_id in ids:
                if liability_id not in all_liability_ids:
                    raise osv.except_osv('Validation Error !', 'You don’t have permission to access this data !')
        return super(vhr_liability, self).read(cr, user, ids, fields=fields, context=context, load=load)

    def _format_date(self, date, format="%d/%m/%Y"):
        res = ''
        if not date:
            return res
        res = datetime.strptime(date, '%Y-%m-%d').strftime(format)
        return res

    def convert_to_frontend_data(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        list_liability_datas = []
        liabilities = self.browse(cr, uid, ids, context=context)
        for liability in liabilities:
            liability_data = {
                'id': liability.id,
                'employee_code': liability.employee_id and liability.employee_id.code or '',
                'employee_id': liability.employee_id and liability.employee_id.id or False,
                'employee_name': liability.employee_id and liability.employee_id.name or '',
                'department_name': liability.department_name or '',
                'div_name': liability.div_name or '',
                'supplier_code': liability.supplier_code or '',
                'document_no': liability.document_no or '',
                'name': liability.name or '',
                'close_day': liability.close_day and self._format_date(liability.close_day) or '',
                'document_day': liability.document_day and self._format_date(liability.document_day) or '',
                'reimbursement_day': liability.reimbursement_day and self._format_date(liability.reimbursement_day) or '',
                'advance_payment': liability.advance_payment or 0.0,
            }
            list_liability_datas.append(liability_data)
        return list_liability_datas

    def get_liability_datas(self, cr, uid, args=None, offset=0, limit=None, order=None, context=None):
        if context is None:
            context = {}
        if args is None:
            args = []
        liability_datas = []
        if not uid:
            return liability_datas
        liability_ids = self.search(cr, uid, args, offset=offset, limit=limit, order=order, context=context)
        if not liability_ids:
            return liability_datas
        liability_datas = self.convert_to_frontend_data(cr, uid, liability_ids, context=context)
        return liability_datas

    # return {
    #         employee_id1: {
    #             "full_name": "Nguyen Van A",
    #             "first_name": "A",
    #             "email": "a@com.local",
    #             "liability_ids": [1,2,3]
    #         },
    #         employee_id2: {...}
    #     }
    def _get_employees_liabilities_data(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = {}
        liabilities = self.browse(cr, uid, ids, context=context)
        for liability in liabilities:
            employee = liability.employee_id or False
            if employee:
                if employee.id in res:
                    res[employee.id]['liability_ids'].append(liability.id)
                else:
                    res.update({
                        employee.id: {
                            "full_name": employee.name_related,
                            "first_name": employee.first_name,
                            "email": employee.work_email,
                            "liability_ids": [liability.id]
                        }
                    })
        return res

    def _get_email_from_emp_code(self, cr, uid, emp_codes, context=None):
        if context is None:
            context = {}
        if not emp_codes:
            return ''
        employee_pool = self.pool['hr.employee']
        emails = ''
        emp_ids = employee_pool.search(cr, SUPERUSER_ID, [('code', 'in', emp_codes)], context=context)
        if not emp_ids:
            return emails
        emp_datas = employee_pool.read(cr, SUPERUSER_ID, emp_ids, ['work_email'], context=context)
        emp_emails = [emp_data['work_email'] for emp_data in emp_datas if emp_data.get('work_email', False)]
        emails = ','.join(emp_emails)
        return emails

    def get_reply_to(self, cr, uid, context=None):
        if context is None:
            context = {}
        reply_to_emp_codes = eval(self.pool['ir.config_parameter'].get_param(cr, uid, 'employee.codes.to.reply.email', "[]"))
        emails = self._get_email_from_emp_code(cr, uid, reply_to_emp_codes, context=context)
        return emails

    def get_cc(self, cr, uid, context=None):
        if context is None:
            context = {}
        cc_emp_codes = eval(self.pool['ir.config_parameter'].get_param(cr, uid, 'employee.codes.to.cc.email', "[]"))
        emails = self._get_email_from_emp_code(cr, uid, cc_emp_codes, context=context)
        return emails

    def _get_liability_mysite_link(self, cr, uid, liability_ids=None, context=None):
        if context is None:
            context = {}
        if not liability_ids:
            liability_ids = []
        web_base_url = self.pool['ir.config_parameter'].get_param(cr, uid, 'web.base.url', '')
        if not web_base_url:
            return "#"
        link = web_base_url + '/liability'
        if liability_ids:
            link += '?ids=[' + ','.join(str(liability_id) for liability_id in liability_ids) + ']'
        return link

    def _get_table_details(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        liability_datas = self.convert_to_frontend_data(cr, uid, ids, context=context)
        res = ""
        if not liability_datas:
            return res
        res += "<table width='100%' style='border-collapse: collapse'>"
        res += "\r\t<thead>"
        res += "\r\t\t<tr>"
        res += "\r\t\t\t<th style='background-color: #ccffff; border: 1px solid black; text-align: center'>Mã Nhân Viên / Employee Code</th>"
        res += "\r\t\t\t<th style='background-color: #ccffff; border: 1px solid black; text-align: center'>Mã NCC / Supplier Code</th>"
        res += "\r\t\t\t<th style='background-color: #ccffff; border: 1px solid black; text-align: center'>Tên Nhân Viên / Employee Name</th>"
        res += "\r\t\t\t<th style='background-color: #ccffff; border: 1px solid black; text-align: center'>Bộ Phận / Division</th>"
        res += "\r\t\t\t<th style='background-color: #ccffff; border: 1px solid black; text-align: center'>Phòng Ban / Department</th>"
        res += "\r\t\t\t<th style='background-color: #ccffff; border: 1px solid black; text-align: center'>Ngày Chứng Từ / Invoice Date</th>"
        res += "\r\t\t\t<th style='background-color: #ccffff; border: 1px solid black; text-align: center'>Số Chứng Từ / Invoice Number</th>"
        res += "\r\t\t\t<th style='background-color: #ccffff; border: 1px solid black; text-align: center'>Diễn Giải / Description</th>"
        res += "\r\t\t\t<th style='background-color: #ccffff; border: 1px solid black; text-align: center'>Ngày Hoàn Ứng / Reimbursement Date</th>"
        res += "\r\t\t\t<th style='background-color: #ccffff; border: 1px solid black; text-align: center'>Số Tiền Còn Tạm Ứng / Remaining Amount</th>"
        res += "\r\t\t</tr>"
        res += "\r\t</thead>"
        res += "\r\t<tbody>"
        for data in liability_datas:
            res += "\r\t\t<tr>"
            res += "\r\t\t\t<td style='border: 1px solid black; padding-left: 5px'>%s</td>" % (data.get('employee_code', ''))
            res += "\r\t\t\t<td style='border: 1px solid black; padding-left: 5px'>%s</td>" % (data.get('supplier_code', ''))
            res += "\r\t\t\t<td style='border: 1px solid black; padding-left: 5px'>%s</td>" % (data.get('employee_name', ''))
            res += "\r\t\t\t<td style='border: 1px solid black; padding-left: 5px'>%s</td>" % (data.get('div_name', ''))
            res += "\r\t\t\t<td style='border: 1px solid black; padding-left: 5px'>%s</td>" % (data.get('department_name', ''))
            res += "\r\t\t\t<td style='border: 1px solid black; padding-left: 5px'>%s</td>" % (data.get('document_day', ''))
            res += "\r\t\t\t<td style='border: 1px solid black; padding-left: 5px'>%s</td>" % (data.get('document_no', ''))
            res += "\r\t\t\t<td style='border: 1px solid black; padding-left: 5px'>%s</td>" % (data.get('name', ''))
            res += "\r\t\t\t<td style='color: red; border: 1px solid black; padding-left: 5px'>%s</td>" % (data.get('reimbursement_day', ''))
            res += "\r\t\t\t<td style='border: 1px solid black; padding-left: 5px'>%s</td>" % (data.get('advance_payment', '') and '{0:,}'.format(int(data['advance_payment'])) or '')
            res += "\r\t\t</tr>"
        res += "\r\t\t<tr>"
        res += "\r\t\t\t<td style='border: 1px solid black; padding-left: 5px' colspan='9'><b>Số Dư Cuối Kỳ / Ending Balance</b></td>"
        res += "\r\t\t\t<td style='border: 1px solid black; padding-left: 5px'><b>%s</b></td>" % ('{0:,}'.format(int(sum(l['advance_payment'] for l in liability_datas if l.get('advance_payment', 0.0)))))
        res += "\r\t\t</tr>"
        res += "\r\t</tbody>"
        res += "\r</table>"
        return res

    def _get_body_html(self, cr, uid, first_name, liability_ids, context=None):
        if context is None:
            context = {}
        body_html = ""
        if not first_name or not liability_ids:
            return body_html
        table_details = self._get_table_details(cr, uid, liability_ids, context=context)
        body_html = """<body>
            <p>
                Dear Anh/Chị,
             </p>
             <p>Anh/Chị vui lòng xem chi tiết cột <b style="color:red">ngày hoàn ứng</b> dưới đây, hoặc truy cập <b>mysite</b> theo đường <a href="%s">link</a>.</p>
             %s
             <p>
             Nếu ngày hoàn ứng quá hạn Anh/Chị không có phản hồi gì đến Kế toán, thì khoản tạm ứng này sẽ được <b>tạm cấn trừ vào lương cuối tháng</b>.<br/><br/>
             Sau khi Anh/Chị submit eform và gửi chứng từ đầy đủ đến Kế toán, thì chi phí này sẽ được <b>thanh toán lại theo eform được duyệt</b>.<br/><br/>
             Nếu có bất kỳ thắc mắc nào, xin vui lòng gửi về email <a>%s</a>.
             </p>
             <p>
                Thanks and Best regards.<br/>
                FA Department
             </p>
        </body>""" % (self._get_liability_mysite_link(cr, uid, liability_ids=liability_ids, context=context), table_details, self.get_reply_to(cr, uid, context=context))
        return body_html

    def send_email(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        # Group employee and his liabilities
        employees_liabilities_data = self._get_employees_liabilities_data(cr, uid, ids, context=context)
        # Get the email template
        email_template = self.pool['ir.model.data'].get_object_reference(cr, SUPERUSER_ID, "vhr_mysite", "notify_employee_liabilities")
        if not email_template:
            return False
        # send email for each employee
        mail_mail_pool = self.pool['mail.mail']
        email_template_id = email_template[1]
        email_values = self.pool['email.template'].generate_email(cr, SUPERUSER_ID, email_template_id, ids[0], context=context)
        email_from = self.pool['ir.config_parameter'].get_param(cr, SUPERUSER_ID, "vhr_master_data_email_system_config") or "hr.service@com.vn"
        email_values.update({
            'email_from': email_from,
            'reply_to': self.get_reply_to(cr, uid, context=context),
            'email_cc': self.get_cc(cr, uid, context=context),
            'res_id': False,
        })
        for employee_id, data in employees_liabilities_data.iteritems():
            if data.get('email', ''):
                liability_ids = data.get('liability_ids', [])
                body_html = self._get_body_html(cr, uid, data.get('first_name', ''), liability_ids, context=context)
                email_values.update({
                    'email_to': data['email'],
                    'body': body_html,
                    'body_html': body_html,
                })
                msg_id = mail_mail_pool.create(cr, SUPERUSER_ID, email_values, context=context)
                if msg_id:
                    mail_mail_pool.send(cr, SUPERUSER_ID, [msg_id], context=context)
                    self.write(cr, uid, liability_ids, {'is_send_mail': True}, context=context)
        return True
