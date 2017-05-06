# -*- coding: utf-8 -*-
import logging

from openerp import http
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp import SUPERUSER_ID
import json

log = logging.getLogger(__name__)


class website_hr_orgchart(http.Controller):
    @http.route('/chart', type='http', auth='public', website=True)
    def chart(self):
        cr, uid = request.cr, request.uid
        res = []
        sql = """select *  from fn_orgchart_hr(0)"""

        cr.execute(sql)
        org_chart_view = cr.fetchall()
        try:
            for record in org_chart_view:
                headcount = record[7] > 0 and str(record[7]) or ""
                r = {'key': str(record[0]), 'name': unicode(record[1]), 'code': str(record[2]), 'level': record[3],
                     'manager': unicode(record[6]), 'parent': str(record[4]), 'headcount':  headcount,
                     'total': headcount, 'band': record[3]}
                if record[4]:
                    r['parent'] = str(record[4])
                else:
                    r['parent'] = ""
                if len(record) >= 10:
                    r['official'] = str(record[8])
                    r['temp'] = str(record[9])
                    if record[7] and record[7] > 0:
                        r['headcount'] += " (P:"+r['official']+", T:"+r['temp']+")"
                if len(record) >= 11:
                    r['note'] = unicode(record[10])

                res.append(r)
        except Exception, e:
            error = e.message
            log.warning(error)
        data = str(res).replace("u'", "'").replace("'", "\"")
        return request.website.render('vhr_mysite.orgchart', {'data': data})

    @http.route('/mysite/detailchart', methods=['GET'], type='http', auth='user', website=True)
    def detail_chart(self):
        cr, uid = request.cr, request.uid
        department_obj = request.registry['hr.department']
        department_ids = department_obj.search(cr, SUPERUSER_ID, [('organization_class_id.level', 'in', (2, 3, 4))])
        department_data = department_obj.name_get(cr, SUPERUSER_ID, department_ids)
        return request.website.render('vhr_mysite.dept_chart', {'department': department_data})

    @http.route('/mysite/detailchart', methods=['POST'], type='http', auth='user', website=True)
    def get_detail_chart(self, **post):
        cr, uid = request.cr, request.uid
        if post.get('department_id'):
            department_obj = request.registry['hr.department']
            hr_obj = request.registry['hr.employee']
            dept_data = department_obj.browse(cr, SUPERUSER_ID, int(post['department_id']))

            res = []
            dept = {
                'key': 'd' + post['department_id'],
                'parent': '',
                'manager': dept_data.manager_id and dept_data.manager_id.login or '',
                'name': dept_data.code and dept_data.name and dept_data.code + ' - ' + dept_data.name or '',
            }
            res.append(dept)
            if dept_data.level == 2:
                department_ids = department_obj.search(cr, uid, [('parent_id', '=', dept_data.id)])
                for department in department_obj.browse(cr, uid, department_ids):
                    r = {
                        'key': 'dept' + str(department.id),
                        'parent': 'd' + post['department_id'],
                        'manager': department.manager_id and department.manager_id.login or '',
                        'name': department.code and department.name and department.code + ' - ' + department.name or ''
                    }
                    res.append(r)
                    team_ids = department_obj.search(cr, SUPERUSER_ID, [('organization_class_id.level', '=', '4'), ('parent_id', '=', department.id)])
                    team_data = department_obj.browse(cr, uid, team_ids)
                    for team in team_data:
                        r = {
                            'key': 't' + str(team.id),
                            'parent': 'dept' + str(department.id),
                            'manager': team.manager_id and team.manager_id.login or '',
                            'name': team.code + ' - ' + team.name or ''
                        }
                        res.append(r)
                        emp_ids = hr_obj.search(cr, SUPERUSER_ID, [('team_id', '=', team.id)])
                        emp_data = hr_obj.read(cr, uid, emp_ids, ['id', 'login', 'name'])
                        for emp in emp_data:
                            e = {
                                'key': str(emp['id']),
                                'parent': 't' + str(team.id),
                                'manager': '',
                                'name': emp['login'] or emp['name'] or ''
                            }
                            res.append(e)
            elif dept_data.level == 3:
                team_ids = department_obj.search(cr, SUPERUSER_ID, [('organization_class_id.level', '=', '4'), ('parent_id', '=', int(post['department_id']))])
                team_data = department_obj.browse(cr, uid, team_ids)
                for team in team_data:
                    r = {
                        'key': 't' + str(team.id),
                        'parent': 'd' + post['department_id'],
                        'manager': team.manager_id and team.manager_id.login or '',
                        'name': team.code + ' - ' + team.name or ''
                    }
                    res.append(r)
                    emp_ids = hr_obj.search(cr, SUPERUSER_ID, [('team_id', '=', team.id)])
                    emp_data = hr_obj.read(cr, uid, emp_ids, ['id', 'login', 'name'])
                    for emp in emp_data:
                        e = {
                            'key': str(emp['id']),
                            'parent': 't' + str(team.id),
                            'manager': '',
                            'name': emp['login'] or emp['name'] or ''
                        }
                        res.append(e)
            else:
                emp_ids = hr_obj.search(cr, SUPERUSER_ID, [('team_id', '=', dept_data.id)])
                emp_data = hr_obj.read(cr, uid, emp_ids, ['id', 'login', 'name'])
                for emp in emp_data:
                    e = {
                        'key': str(emp['id']),
                        'parent': 'd' + str(dept_data.id),
                        'manager': '',
                        'name': emp['login'] or emp['name'] or ''
                    }
                    res.append(e)
            data = str(res).replace("u'", "'").replace("'", "\"")
            return json.dumps(data)
website_hr_orgchart()