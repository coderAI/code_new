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


class website_employee_coordinate(http.Controller):

    @http.route(['/map','/map/submited'], methods=['GET', 'POST'], type='http', auth='user', website=True)
    def get_coordinate(self, **post):
        res = {"header": u"Cập nhật địa điểm",'btn_confirm': u'Cập nhật','is_cb': False}
        context = dict(request.context, show_address=True, no_tag_br=True)
        cr, uid = request.cr, request.uid
        coor_obj = request.registry['vhr.employee.coordinate']
        
        groups = request.registry['res.users'].get_groups(cr, uid)
        cb_groups = ['hrs_group_system','vhr_cb']
        if set(cb_groups).intersection(groups):
            res['is_cb'] = True
                
        try:
            if not post.get('lat_value', False):
                coor_data = coor_obj.get_coordinate(cr, uid, context=context)
                res.update({'coor_data': coor_data})
            else:
                coor_obj.create_update_coordinate(cr, uid, post, context=None)
                res.update({'coor_data':post})
                if post.get('action', False) == 'approve':
                    res.update({'message': 'Cập nhật thành công'})
            
            campus_lng = coor_obj.get_campus_coordinate(cr, uid, context=None)
            res.update({'campus': campus_lng})

        except Exception, e:
            message = e.message
            log.info('Employee Coordinate Error %s' % message)

        return request.render("vhr_mysite.employee_coordinate", res)
    
    @http.route(['/map/summary'], methods=['GET', 'POST'], type='http', auth='user', website=True)
    def get_coordinate_summary(self, **post):
        res = {"header": u"Tổng hợp địa điểm của nhân viên",'is_cb': False}
        context = dict(request.context, show_address=True, no_tag_br=True)
        cr, uid = request.cr, request.uid
        coor_obj = request.registry['vhr.employee.coordinate']
        
        groups = request.registry['res.users'].get_groups(cr, uid)
        cb_groups = ['hrs_group_system','vhr_cb']
        if set(cb_groups).intersection(groups):
            res['is_cb'] = True
            
        try:
            if not post.get('lat_value', False):
                coor_data = coor_obj.get_coordinate(cr, uid, context=context)
                res.update({'coor_data': coor_data})
            else:
                coor_obj.create_update_coordinate(cr, uid, post, context=None)
                res.update({'coor_data':post})
 
        except Exception, e:
            message = e.message
            log.info('Employee Coordinate Error %s' % message)
 
        return request.render("vhr_mysite.coordinate_summary", res)
     
    @http.route(['/map/details'], type='json', auth='user', website=True)
    def get_detail_coordinate(self, **kw):
        res = {'coor_data':[]}
        context = dict(request.context, show_address=True, no_tag_br=True)
        cr, uid = request.cr, request.uid
        coor_obj = request.registry['vhr.employee.coordinate']
        try:
            if kw.get('employee_id', False):
                context['employee_id'] = kw['employee_id']
                coor_data = coor_obj.get_coordinate(cr, uid, context=context)
                res['coor_data'].extend(coor_data)
            else:
                coor_data = coor_obj.get_all_coordinate(cr, uid, context=None)
                res['coor_data'].extend(coor_data)
            
            campus_lng = coor_obj.get_campus_coordinate(cr, uid, context=None)
            res.update({'campus': campus_lng})
 
        except Exception, e:
            message = e.message
            log.info('Employee Coordinate Error %s' % message)
 
        return res
    
website_employee_coordinate()