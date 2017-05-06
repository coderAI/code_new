# -*- coding: utf-8 -*-

from openerp.osv import osv, fields


class vhr_personal_document_temp(osv.osv):
    _name = 'vhr.personal.document.temp'
    _columns = {
        'employee_temp_id': fields.many2one('vhr.employee.temp', 'Employee', ondelete='cascade'),
        'personal_document_id': fields.many2one('vhr.personal.document', 'Personal Document'),
        
        'pd_document_type_id': fields.related('personal_document_id', 'document_type_id', type="many2one",relation="vhr.personal.document.type", string="PD Document Type"),
        'pd_number': fields.related('personal_document_id', 'number', type="char", string="PD number"),
        'pd_issue_date': fields.related('personal_document_id', 'issue_date', type="date", string="PD issue_date"),
        'pd_expiry_date': fields.related('personal_document_id', 'expiry_date', type="date", string="PD expiry_date"),
        'pd_country_id': fields.related('personal_document_id', 'country_id', type="many2one", relation="res.country", string="PD Country"),
        'pd_city_id': fields.related('personal_document_id', 'city_id', type="many2one", relation="res.city", string="PD City"),
        'pd_district_id': fields.related('personal_document_id', 'district_id', type="many2one", relation="res.district", string="PD district"),
        'pd_state': fields.related('personal_document_id', 'state', type="selection", string="PD State"),
        
        'document_type_id': fields.many2one('vhr.personal.document.type', 'Document Type', ondelete='restrict'),
        'number': fields.char('Number', size=64),
        'issue_date': fields.date('Issue Date'),
        'expiry_date': fields.date('Expiry Date'),
        'country_id': fields.many2one('res.country', 'Country'),
        'city_id': fields.many2one('res.city', 'City', domain="[('country_id','=',country_id)]"),
        'district_id': fields.many2one('res.district', 'District', domain="[('city_id','=',city_id)]"),
        'state': fields.selection([('new', 'Cấp Mới'), ('update', 'Cấp Nhật'), ('move', 'Chuyển từ công ty cũ sang')], 'Status'),
        'active': fields.boolean('Active'),
        'origin_id': fields.integer('OID', readonly=True),
        'mode': fields.selection([('new', 'Tạo mới'), ('update', 'Cập nhật')], 'Request', readonly=True, required=True),
    }
    _defaults = {
        'active': True
    }
    
    _order = "id desc"