# -*-coding:utf-8-*-
import logging
from openerp.osv import osv,fields
from datetime import datetime
import openerp

log = logging.getLogger(__name__)

MISS_DATA = 'Please check lastname, firstname, email excel file'
EXIST_DATA = 'Email in database only update data'
FORMAT_DATA = 'DOB in excel file error'

class vhr_rr_talent(osv.osv):
    _name = 'vhr.rr.talent'
    _description = 'VHR RR Talent'
    _inherit = 'vhr.rr.temp.applicant'

    _columns = {
        'target_source': fields.text('Target source'),
        'target_skill': fields.text('Target skill'),
        'current_position': fields.char('Current position'),
        'current_company': fields.char('Current company'),
        'current_salary': fields.float('Current salary'),
        'current_benefit': fields.text('Benefit'),
        'expectation': fields.text('Expectation'),
        'status_hiring': fields.boolean('Hiring'),
        'link': fields.char('Link', size=250),
        'pic': fields.many2one('hr.employee', 'PIC'),
        'recruitment_source_type_id': fields.many2one('vhr.recruitment.source.type', 'Source Type'),
    }
    _order = 'id desc'
    
    def thread_import_talent(self, cr, uid, import_status_id, rows, context=None):
        log.info('Begin: thread_import_talent')
        try:
            db = openerp.sql_db.db_connect(cr.dbname)
            cr = db.cursor()
            import_obj = self.pool.get('vhr.import.status')
            detail_obj = self.pool.get('vhr.import.detail')
            dimension_obj = self.pool.get('vhr.dimension')
            hr_source_obj = self.pool.get('hr.recruitment.source')
            employee_obj = self.pool.get('hr.employee')
            applicant_obj = self.pool.get('hr.applicant')
            vhr_source_type_obj = self.pool.get('vhr.recruitment.source.type')
            import_obj.write(cr, uid, [import_status_id], {'state': 'processing', 'num_of_rows':rows.nrows, 'current_row':0})
            cr.commit()
            row_counter = 0
            success_row = 0
            for row in rows._cell_values:
                row_counter += 1
                if row_counter > 2:
                    last_name, first_name, dob, email, phone, speciality, target_source, target_skill, current_company, current_position, \
                    current_salary, current_benefit, expectation, status_hiring,link, source, source_type, pic, note = row[1:20]
                    vals_detail = {}
                    if last_name and first_name and email:
                        email = email.lower()
                        lst_id = self.search(cr, uid, [('email', '=ilike', email)])
                        if lst_id:
                            lst_id = lst_id[0]
                            vals_detail = {'import_id': import_status_id, 'row_number' : row_counter, 'message':EXIST_DATA}
                        
                        applicant_id = applicant_obj.check_applicant_exist(cr, uid, email)                                                
                        applicant_suggest_id = applicant_id[0] if applicant_id else False
                        
                        speciality_id = dimension_obj.search(cr, uid, [('dimension_type_id.code', '=', 'SPECIALITY'), ('active', '=', True),
                                                                    '|', ('name', '=ilike', speciality), ('code', '=ilike', speciality)])
                        speciality_id = speciality_id[0] if speciality_id else False
                        
                        source_type_id = vhr_source_type_obj.search(cr, uid, ['|', ('name', '=ilike', source_type), ('code', '=ilike', source_type)])
                        source_type_id = source_type_id[0] if source_type_id else False
                        
                        source_domain = ['|', ('name', '=ilike', source), ('code', '=ilike', source)]
                        if source_type_id:
                            source_domain = [('source_type_id', '=', source_type_id)] + source_domain
                        source_id = hr_source_obj.search(cr, uid, source_domain)
                        source_id = source_id[0] if source_id else False
                        
                        pic = employee_obj.search(cr, uid, [('login', '=ilike', pic)])
                        pic = pic[0] if pic else False
                        
                        status_hiring = True if status_hiring and status_hiring=='yes' else False
                        
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
                        
                        vals = {'last_name':last_name, 'first_name':first_name, 'birthday': dob, 'mobile_phone':phone,
                                'target_source':target_source, 'target_skill': target_skill, 'speciality_id':speciality_id,
                                'current_company':current_company, 'current_position':current_position, 'current_salary':current_salary,
                                'current_benefit':current_benefit,'expectation':expectation,'status_hiring':status_hiring,
                                'recruitment_source_id':source_id, 'recruitment_source_type_id':source_type_id,
                                'pic':pic, 'note':note, 'link':link, 'email': email, 'applicant_suggest_id': applicant_suggest_id
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
        log.info('End: thread_import_talent')
        return True

vhr_rr_talent()
