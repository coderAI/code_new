# -*- coding: utf-8 -*-

from openerp.osv import osv, fields


class vhr_certificate_info_temp(osv.osv):
    _name = 'vhr.certificate.info.temp'
    _columns = {
        'employee_temp_id': fields.many2one('vhr.employee.temp', 'Employee', ondelete='cascade'),
        'vhr_certificate_info_id': fields.many2one('vhr.certificate.info', 'Certificates/Degree'),
        
        'ci_school_id': fields.related('vhr_certificate_info_id', 'school_id', type="many2one",relation="vhr.school", string="University"),
        'ci_recruitment_degree_id': fields.related('vhr_certificate_info_id', 'recruitment_degree_id', type="many2one",relation="hr.recruitment.degree", string="degree"),
        'ci_speciality_id': fields.related('vhr_certificate_info_id', 'speciality_id', type="many2one",relation="vhr.dimension", string="Speciality"),
        'ci_faculty_id': fields.related('vhr_certificate_info_id', 'faculty_id', type="many2one",relation="vhr.dimension", string="Faculty"),
        'ci_certificate_rating_id': fields.related('vhr_certificate_info_id', 'certificate_rating_id', type="many2one",relation="vhr.dimension", string="Classification"),
        
        
        'school_id': fields.many2one('vhr.school', 'University'),
        'recruitment_degree_id': fields.many2one('hr.recruitment.degree', 'Degree'),
        'speciality_id': fields.many2one('vhr.dimension', 'Speciality'),
        'faculty_id': fields.many2one('vhr.dimension', 'Faculty'),
        'origin_id': fields.integer('OID', readonly=True),
        'mode': fields.selection([('new', 'Tạo mới'), ('update', 'Cập nhật')], 'Request', readonly=True, required=True),
    }
    
    _order = "id desc"