# -*-coding:utf-8-*-
import logging
from openerp.osv import osv, fields
from datetime import date, datetime
import openerp

from openerp.tools.translate import _

log = logging.getLogger(__name__)

MISS_DATA = 'Please check lastname, firstname, email excel file'
EXIST_DATA = 'Email in database only update data'
FORMAT_DATA = 'DOB in excel file error'
class vhr_rr_key_student(osv.osv):
    _name = 'vhr.rr.key.student'
    _description = 'VHR RR Key Student'
    _inherit = 'vhr.rr.temp.applicant'
    
    def _get_school_year(self, cr, uid, context=None):
        minyear = 1975
        maxyear = date.today().year + 5
        list_result = [('%s' % (x), x) for x in range(maxyear, minyear, -1)]
        return tuple(list_result)
    
    def onchange_school_year(self, cr, uid, ids, school_year_from, school_year_to):
        if school_year_from and school_year_to:
            from_year = int(school_year_from)
            to_year = int(school_year_to)
            if from_year > to_year:
                warning = {'title': 'User Alert!', 'message': 'Please check your data'}
                return {'value': {'school_year_to': None}, 'warning': warning}
        return {'value': {}}
    
    _columns = {
        'cumulative_gpa': fields.float('Cumulative GPA'),
        'school_id': fields.many2one('vhr.school', 'University'),
        'school_year_from': fields.selection(_get_school_year, 'Year from'),
        'school_year_to': fields.selection(_get_school_year, 'Year to'),
        'school_year_end':fields.selection([
                     ('early', 'Early'),
                     ('late', 'Late'),
                      ], 'Year end', select=True),
        'pic': fields.many2one('hr.employee', 'PIC'),
        'student_code': fields.char('Student code', size=150),
        'recruitment_source_type_id': fields.many2one('vhr.recruitment.source.type', 'Source Type'),
        'write_date': fields.datetime('Last Update', readonly=True),
        'student_event_id': fields.many2one('vhr.student.event', 'Event'),
        'student_organization_unit_id': fields.many2one('vhr.student.organization.unit', 'Organization Unit'),
    }
    _order = 'id desc'

    def _check_duplicate_student(self, cr, uid, vals):
        if vals.get('email', False):
            email = vals['email'].lower()
            duplicate = self.search(cr, uid, [('email', '=ilike', email)])
            if duplicate:
                raise osv.except_osv(_('Invalid Action!'),
                                     _("Duplicate Student Email"))
        if vals.get('mobile_phone', False):
            duplicate = self.search(cr, uid, [('mobile_phone', '=ilike', vals['mobile_phone'])])
            if duplicate:
                raise osv.except_osv(_('Invalid Action!'),
                                     _("Duplicate Student Mobile Phone"))
        return True

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        self._check_duplicate_student(cr, uid, vals)
        return super(vhr_rr_key_student, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        self._check_duplicate_student(cr, uid, vals)
        return super(vhr_rr_key_student, self).write(cr, uid, ids, vals, context=context)
    
    def thread_import_key_student(self, cr, uid, import_status_id, rows, context=None):
        log.info('Begin: thread_import_key_student')
        try:
            db = openerp.sql_db.db_connect(cr.dbname)
            cr = db.cursor()
            import_obj = self.pool.get('vhr.import.status')
            detail_obj = self.pool.get('vhr.import.detail')
            school_obj = self.pool.get('vhr.school')
            dimension_obj = self.pool.get('vhr.dimension')
            hr_source_obj = self.pool.get('hr.recruitment.source')
            employee_obj = self.pool.get('hr.employee')
            applicant_obj = self.pool.get('hr.applicant')
            vhr_source_type_obj = self.pool.get('vhr.recruitment.source.type')
            student_event_obj = self.pool.get('vhr.student.event')
            org_unit_obj = self.pool.get('vhr.student.organization.unit')
            import_obj.write(cr, uid, [import_status_id], {'state': 'processing', 'num_of_rows':rows.nrows, 'current_row':0})
            cr.commit()
            row_counter = 0
            success_row = 0
            for row in rows._cell_values:
                row_counter += 1
                if row_counter > 2:
#                     last_name, first_name, dob, email, phone, facebook_link, school, student_code, speciality, \
#                     gpa, from_year, to_year, end_time, source, source_type, pic, note = row[1:18]
                    last_name, first_name, dob, email, phone, facebook_link, school, student_code, speciality, \
                    gpa, from_year, to_year, end_time, org_unit, student_event, pic, note = row[1:18]
                    vals_detail = {}
                    if last_name and first_name and email:
                        email = email.lower()
                        lst_id = self.search(cr, uid, ['|', ('email', '=ilike', email),
                                                       ('mobile_phone', '=ilike', phone)])
                        if lst_id:
                            lst_id = lst_id[0]
                            vals_detail = {'import_id': import_status_id, 'row_number' : row_counter, 'message':EXIST_DATA}
                        
                        applicant_id = applicant_obj.check_applicant_exist(cr, uid, email)                                                
                        applicant_suggest_id = applicant_id[0] if applicant_id else False
                        
                        from_year = str(int(from_year)) if from_year else ''
                        to_year = str(int(to_year)) if to_year else ''
                        
                        school_id = school_obj.search(cr, uid, ['|', ('name', '=ilike', school), ('code', '=ilike', school)])
                        school_id = school_id[0] if school_id else False
                        
                        speciality_id = dimension_obj.search(cr, uid, [('dimension_type_id.code', '=', 'SPECIALITY'), ('active', '=', True),
                                                                    '|', ('name', '=ilike', speciality), ('code', '=ilike', speciality)])
                        speciality_id = speciality_id[0] if speciality_id else False

                        org_unit_id = org_unit_obj.search(cr, uid, ['|', '|', ('name', '=ilike', org_unit),
                                                                    ('name_en', '=ilike', org_unit),
                                                                    ('code', '=ilike', org_unit)])
                        org_unit_id = org_unit_id and org_unit_id[0] or False
                        
                        student_event_id = student_event_obj.search(cr, uid,
                                                                    ['|', '|', ('name', '=ilike', student_event),
                                                                     ('name_en', '=ilike', org_unit),
                                                                     ('code', '=ilike', student_event)])
                        student_event_id = student_event_id and student_event_id[0] or False
                        
                        pic = employee_obj.search(cr, uid, [('login', '=ilike', pic)])
                        pic = pic[0] if pic else False
                        
                        try:
                            if isinstance(dob, float):
                                seconds = (dob - 25569) * 86400.0
                                dob = datetime.utcfromtimestamp(seconds)
                            else:
                                dob = datetime.strptime(dob, '%d/%m/%Y')
                        except Exception as e:
                            dob = False
                            log.error(e)
                            vals_detail = {'import_id': import_status_id, 'row_number' : row_counter, 'message':FORMAT_DATA}
                        
#                         vals = {'last_name':last_name, 'first_name':first_name, 'birthday': dob, 'mobile_phone':phone,
#                                 'facebook_link':facebook_link, 'school_id': school_id, 'speciality_id':speciality_id,
#                                 'cumulative_gpa':gpa, 'school_year_from':from_year, 'school_year_to':to_year, 'school_year_end':end_time,
#                                 'recruitment_source_id':source_id, 'recruitment_source_type_id':source_type_id,
#                                 'pic':pic, 'note':note, 'student_code':student_code, 'email': email, 'applicant_suggest_id': applicant_suggest_id
#                                 }
                        vals = {'last_name': last_name,
                                'first_name': first_name,
                                'birthday': dob,
                                'mobile_phone': phone,
                                'facebook_link': facebook_link,
                                'school_id': school_id,
                                'speciality_id': speciality_id,
                                'cumulative_gpa': gpa,
                                'school_year_from': from_year,
                                'school_year_to': to_year,
                                'school_year_end': end_time,
                                'student_organization_unit_id': org_unit_id,
                                'student_event_id': student_event_id,
                                'pic': pic,
                                'note': note,
                                'student_code': str(student_code),
                                'email': email,
                                'applicant_suggest_id': applicant_suggest_id
                                }
                        if lst_id:
                            self.write(cr, uid, lst_id, vals, context)
                        else:
                            self.create(cr, uid, vals, context)

                        success_row = success_row + 1
                    else:
                        vals_detail = {'import_id': import_status_id, 'row_number' : row_counter, 'message':MISS_DATA}
                    
                    if vals_detail:
                        detail_obj.create(cr, uid, vals_detail)
                        cr.commit()                
                import_obj.write(cr, uid, [import_status_id], {'current_row':row_counter, 'success_row':success_row})
                cr.commit()
            import_obj.write(cr, uid, [import_status_id], {'state': 'done'})
            cr.commit()
        except Exception as e:
            import_obj.write(cr, uid, [import_status_id], {'state': 'error'})
            cr.commit()
            log.info(e)
            cr.rollback()
        finally:    
            cr.close()
        log.info('End: thread_import_key_student')
        return True

vhr_rr_key_student()
