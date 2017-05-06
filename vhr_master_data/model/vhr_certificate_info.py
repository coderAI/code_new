# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields
from datetime import date, datetime
import time
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT

log = logging.getLogger(__name__)

class vhr_certificate_info(osv.osv):
    _name = 'vhr.certificate.info'
    _description = 'VHR Certificate Information'
    
    def _get_school_year(self, cr, uid, context=None):
        minyear = 1975
        maxyear = date.today().year + 5
        list_result = [('%s'%(x),x) for x in range(maxyear,minyear, -1)]
        return tuple(list_result)
    
    def onchange_school_year(self, cr, uid, ids, school_year_from, school_year_to):
        if school_year_from and school_year_to:
            from_year = int(school_year_from)
            to_year = int(school_year_to)
            if from_year >  to_year:
                warning = {'title': 'User Alert!', 'message': 'Please check your data'}
                return {'value': {'school_year_to': None}, 'warning': warning}
        return {'value': {}}
    
    def onchange_date(self, cr, uid, ids, effect_date_from, effect_date_to):
        if effect_date_to and effect_date_from:
            time_delta = datetime.strptime(effect_date_to, DEFAULT_SERVER_DATE_FORMAT) - datetime.strptime(effect_date_from,
                                                                                                     DEFAULT_SERVER_DATE_FORMAT)
            day_delta = time_delta.days
            if day_delta < 0:
                warning = {'title': 'User Alert!', 'message': 'Date End must be greater than Date Effect'}
                return {'value': {'effect_date_to': None}, 'warning': warning}
        return {'value': {}}
    
    _columns = {
                'partner_id': fields.many2one('res.partner', 'Partner'),
                'code': fields.char('Code', size=64),
                'name': fields.char('Name', size=64),
                'certificate_level_id': fields.many2one('vhr.certificate.level', 'Degree type'),
                'certificate_rating_id': fields.many2one('vhr.dimension', 'Classification', ondelete='restrict', 
                                                 domain=[('dimension_type_id.code', '=', 'CERTIFICATE_RATING'), ('active','=',True)]),
                
                'issue_date': fields.date('Issue date'),
                'school_id': fields.many2one('vhr.school', 'University'),
                'speciality_id': fields.many2one('vhr.dimension', 'Speciality', ondelete='restrict', 
                                                 domain=[('dimension_type_id.code', '=', 'SPECIALITY'), ('active','=',True)]),
                'faculty_id': fields.many2one('vhr.dimension', 'Faculty', ondelete='restrict', 
                                              domain=[('dimension_type_id.code', '=', 'FACULTY'), ('active','=',True)]),
                'training_type_id': fields.many2one('vhr.dimension', 'Training Type', ondelete='restrict', 
                                                 domain=[('dimension_type_id.code', '=', 'TRAINING_TYPE'), ('active','=',True)]),
                
                'recruitment_degree_id': fields.many2one('hr.recruitment.degree', 'Degree/ Certificate'),
                'is_company_support': fields.boolean('Support by company'),
                'oversea': fields.many2one('res.country', 'Oversea'),
                'is_main_degree': fields.boolean('Main degree'),
                'comment': fields.text('Comment'),
                'file': fields.binary('file'),
                'effect_date_from': fields.date('Effect date from'),
                'effect_date_to': fields.date('Effect date to'),
                'employee_id': fields.many2one('hr.employee', string="Employee", ondelete='restrict'),
                'applicant_id': fields.many2one('hr.applicant', string="Candidate", ondelete='cascade'),
                'school_year_from': fields.selection(_get_school_year, 'Year from'), 
                'school_year_to': fields.selection(_get_school_year, 'Year to'), 
                #'school_year_from': fields.function(_get_school_year, method=True, type='selection', string='Year from', store=True, multi="get_year"),
                #'school_year_to': fields.function(_get_school_year, method=True, type='selection', string='Year to', store=True, multi="get_year"),
                'school_year_end':fields.selection([
                     ('early','Early'),
                     ('late','Late'),
                      ], 'Year end', select=True),
                # note bên candidate khi xóa sẽ xóa hết tất cả certificate ( chặn lại chỗ có đang link với request nào hay không )
                'gpa': fields.integer('GPA', size=64),
                'is_received_hard_copy': fields.boolean('Is Received Hard Copy'),
                'certificate_type': fields.selection([('degree', 'Degree'), ('certificate', 'Certificate')], 'Type'),
            }
    
    _defaults = {
                 'certificate_type': 'degree',
                 }
    
    _unique_insensitive_constraints = [{'employee_id': "This Certificate/Degree1 are already exist!",
                                        'school_id': "This Certificate/Degree2 are already exist!",
                                        'recruitment_degree_id': "This Certificate/Degree3 are already exist!",
                                        'speciality_id': "This Certificate/Degree4 are already exist!",
                                        'faculty_id': "This Certificate/Degree are already exist!",
                                        'validate_mandatory_fields': ['employee_id','school_id','recruitment_degree_id']},
                                       {'applicant_id': "This Certificate/Degree5 are already exist!",
                                        'school_id': "This Certificate/Degree6 are already exist!",
                                        'recruitment_degree_id': "This Certificate/Degree7 are already exist!",
                                        'speciality_id': "This Certificate/Degree8 are already exist!",
                                        'faculty_id': "This Certificate/Degree9 are already exist!",
                                        'validate_mandatory_fields': ['applicant_id','school_id','recruitment_degree_id']}]
    
    def onchange_certificate_type(self, cr, uid, ids, context=None):
        return {'value':{'recruitment_degree_id': False}}
    
    def name_get(self, cr, uid, ids, context=None):
        if not ids or False in ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        
        reads = self.read(cr, uid, ids, ['employee_id'], context=context)
        res = []
        for record in reads:
                name = record.get('employee_id',False) and record['employee_id'][1]
                res.append((record['id'], name))
        return res
    
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_certificate_info, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if not context:
            context = {}
        
        return super(vhr_certificate_info, self).search(cr, uid, args, offset, limit, order, context, count)
    
vhr_certificate_info()
