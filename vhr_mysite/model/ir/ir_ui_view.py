# -*- coding: utf-8 -*-
import copy
import re
import simplejson
import werkzeug

from lxml import etree, html

from openerp import SUPERUSER_ID
from openerp.addons.website.models import website
# from openerp.addons.vhr_payroll.model.vhr_pr_loan import CLICKER_REQUEST, DEPTH_APPROVE, CB_REVIEW, CB_APPROVE, DONE, CANCEL, G_CB_EXECUTOR, G_CB_LOAN, G_CB_MANAGER
from openerp.http import request
from openerp.osv import osv, fields


class view(osv.osv):
    _inherit = "ir.ui.view"

    def render(self, cr, uid, id_or_xml_id, values=None, engine='ir.qweb', context=None):

        if not context:
            context = {}
        if not values:
                values = {}

        if request and getattr(request, 'website_enabled', False):
            engine='website.qweb'
            hr_obj = self.pool['hr.employee']
            partner_obj = self.pool.get('res.partner')
            user_obj = self.pool.get('res.users')
            holiday_obj = self.pool.get('hr.holidays')
            ot_obj = self.pool.get('vhr.ts.overtime')
            # loan_obj = self.pool.get('vhr.pr.loan')
            # ca_obj = self.pool.get('vhr.pr.collaborator.assessment')
            try:
                employee_ids = hr_obj.search(cr, uid, [('user_id', '=', uid)], context=context)
            except:
                employee_ids = []
            user_groups = user_obj.get_groups(cr, uid)
            values.update({'user_groups': list(set(user_groups))})
            if employee_ids:
                employee = hr_obj.browse(cr, uid, employee_ids[0], context)
                values.update({
                    'my_current_employee': employee
                })
                if not values.has_key('my_employee'):
                    values['my_employee'] = employee
                if not values.get('my_employee_id', False):
                    values.update({
                        'my_employee_id': employee.id or 1
                    })
                if not values.get('my_employee_name', False):
                    values.update({
                        'my_employee_name': employee.name or ''
                    })
                context.update({'leave_approval': True})
                leave_ids = holiday_obj.search(cr, uid, [], order='date_from desc', context=context)
                if leave_ids:
                    values.update({
                        'leave_approval_count': len(leave_ids)
                    })

                context.update({'type': 'task'})
                ot_ids = ot_obj.search(cr, uid, [], context=context)
                if ot_ids:
                    values.update({
                        'ot_approval_count': len(ot_ids)
                    })

                # context.update({'loan_approval': True})
                # state_lists = []
                # all_dept_head_user_ids = loan_obj._get_all_dept_head_user_ids(cr, context=context)
                # if uid in all_dept_head_user_ids:
                #     state_lists.append(DEPTH_APPROVE)
                # if loan_obj.check_user_in_group(cr, uid, G_CB_EXECUTOR[0], G_CB_EXECUTOR[1], context=context):
                #     state_lists.append(CB_REVIEW)
                # if loan_obj.check_user_in_group(cr, uid, G_CB_MANAGER[0], G_CB_MANAGER[1], context=context):
                #     state_lists.append(CB_APPROVE)
                # loan_ids = loan_obj.search(cr, uid, [('employee_id', '!=', False),
                #                                      ('employee_id.user_id', '!=', uid),
                #                                      ('state', 'in', state_lists)], context=context)
                # if loan_ids:
                #     values.update({
                #         'loan_approval_count': len(loan_ids)
                #     })

                # ca_ids = ca_obj.search(cr, uid, [('state', '=', 'waiting_dept'),
                #                                  ('report_to', 'in', employee_ids)], context=context)
                # if ca_ids:
                #     values.update({
                #         'ca_approval_count': len(ca_ids)
                #     })
                #giangth3
                # total = len(leave_ids) + len(ot_ids) + len(ca_ids)
                # if total:
                #     values.update({
                #         'request_approval_count': total
                #     })

        return super(view, self).render(cr, uid, id_or_xml_id, values=values, engine=engine, context=context)
