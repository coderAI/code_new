# -*- coding: utf-8 -*-
import json
import logging
import requests
import datetime
import locale
from operator import itemgetter

from openerp import SUPERUSER_ID
from openerp.osv import osv, fields
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.addons.vhr_recruitment.model.vhr_temp_applicant import SPECIALITY_DIMENSION_DOMAIN, \
    GRADUATION_DIMENSION_DOMAIN,STUDENT_STAFF_DOMAIN, SPECIALITY_ISPUBLIC_DIMENSION_DOMAIN
from openerp.addons.vhr_recruitment.model.vhr_email_news import PROGRAM_DIMENSION_DOMAIN
from openerp.addons.audittrail  import audittrail
from openerp.addons.vhr_recruitment.model.vhr_recruitment_abstract import vhr_recruitment_abstract
from openerp.addons.vhr_recruitment.model.vhr_recruitment_constant import RE_Student_Subcriber, RE_Candidate_Subcriber
from random import randrange

_logger = logging.getLogger(__name__)

RECRUITMENT_PROGRAM_DOMAIN = [('dimension_type_id.code', '=', 'DND_PROGRAM'),('active', '=', True),
                              ('code','!=','CANDIDATE')]

TOUR_FIELD_MAP = {
    'required': ['last_name', 'first_name', 'birthday', 'email', 'mobile_phone', 'school_id', 'speciality',
                 'time_graduation_id', 'program_event_id'],
    'optional': []
}

INTERNSHIP_FIELD_MAP = {
    'required': ['last_name', 'first_name', 'birthday', 'email', 'mobile_phone', 'speciality', 'time_graduation_id',
                 'school_id', 'recruitment_source_id', 'program_event_id', 'cumulative_gpa', 'gender', 'resume'],
    'optional': ['identification_no', 'permanent_address', 'compress']
}

TRAINEE_FIELD_MAP = {
    'required': ['last_name', 'first_name', 'birthday', 'email', 'mobile_phone', 'speciality', 'time_graduation_id',
                 'school_id', 'recruitment_source_id', 'program_event_id', 'cumulative_gpa', 'gender', 'resume'],
    'optional': ['identification_no', 'permanent_address', 'compress']
}

CV_ONLINE_MAP = {'required': ['last_name', 'first_name', 'birthday', 'gender', 'email', 'mobile_phone', 'post_job_id'],
                 'optional': ['note', 'compress']
}

FIELD_OBJECT_MAP = {
    'school_id': 'vhr.school',
    'speciality_id': ''
}
EMAIL_FIELD_MAP = {'required': ['name', 'email', 'program_type_ids']}


class Interface(osv.TransientModel, vhr_recruitment_abstract):
    _name = 'vhr.recruitment.interface'
    
    def get_know_fresher_by(self, cr, uid, data='{}', context=None):
        _logger.info('get_know_fresher_by() start')
        code = 1
        res = []
        message = 'success'
        try:
            data = json.loads(data)
            obj = self.pool.get('vhr.recruitment.source.online')
            event_obj = self.pool.get('vhr.program.event')
            if data.get('program_event_id'):
                event_id = int(data['program_event_id'])
                event = event_obj.read(cr, uid, event_id, ['recruitment_source_online_ids'])
                obj_ids = event['recruitment_source_online_ids']
            else:
                obj_ids = obj.search(cr, uid, [], order='name')
            res = obj.read(cr, uid, obj_ids, ['name', 'name_en'])
            res = sorted(res, key=itemgetter('name'))
        except Exception, e:
            code = -99
            message = e.message
            _logger.error('get_know_fresher_by() %s' % message)
        _logger.info('get_know_fresher_by() end')
        return json.dumps({'code': code, 'message': message, 'data': res})

    def get_job_categories(self, cr, uid, context=None):
        _logger.info('get_job_categories() start')
        code = 1
        data = ''
        message = 'success'
        try:
            obj = self.pool.get('vhr.job.category')
            obj_ids = obj.search(cr, uid, [], order='name')
            data = obj.read(cr, uid, obj_ids, ['name', 'name_en'])
            data = sorted(data, key=itemgetter('name'))
        except Exception, e:
            code = -99
            message = e.message
            _logger.error('get_job_categories() %s' % message)
        _logger.info('get_job_categories() end')
        return json.dumps({'code': code, 'message': message, 'data': data})

    def get_specialities(self, cr, uid, context=None):
        _logger.info('get_specialities() start')
        code = 1
        data = ''
        message = 'success'
        try:
            obj = self.pool.get('vhr.dimension')
            obj_ids = obj.search(cr, uid, SPECIALITY_ISPUBLIC_DIMENSION_DOMAIN)
            data = obj.read(cr, uid, obj_ids, ['name', 'name_en'])
        except Exception, e:
            code = -99
            message = e.message
            _logger.error('get_specialities() %s' % message)
        _logger.info('get_specialities() end')
        return json.dumps({'code': code, 'message': message, 'data': data})    

    def get_program_type(self, cr, uid, context=None):
        _logger.info('get_program_type() start')
        code = 1
        message = 'success'
        data = []
        try:
            obj = self.pool.get('vhr.dimension')
            obj_ids = obj.search(cr, uid, PROGRAM_DIMENSION_DOMAIN, order='name', context=context)
            data = obj.read(cr, uid, obj_ids, ['name', 'name_en', 'code', 'description'])
        except Exception, e:
            code = -99
            message = e.message
            _logger.error('get_program_type() %s' % message)
        _logger.info('get_program_type() end')
        return json.dumps({'code': code, 'message': message, 'data': data})

    def get_typical_faces(self, cr, uid, data='{}', context=None):
        _logger.info('get_typical_faces() start')
        code = 1
        res = []
        message = 'success'
        try:
            search_domain = []
            if data:
                data = json.loads(data)
                if data.get('face_type'):
                    face_type = data['face_type']
                    search_domain.append(('face_type_id.code', '=', face_type))
                else:
                    search_domain.append(('face_type_id.code', '=', 'TYPICAL_FACE'))
            else:
                search_domain.append(('face_type_id.code', '=', 'TYPICAL_FACE'))
            
            obj = self.pool.get('vhr.typical.face')
            obj_ids = obj.search(cr, uid, search_domain, order='name')
            res = obj.read(cr, uid, obj_ids, [])
            res = sorted(res, key=itemgetter('name'))
        except Exception, e:
            code = -99
            message = e.message
            _logger.error('get_typical_faces() %s' % message)
        _logger.info('get_typical_faces() end')
        return json.dumps({'code': code, 'message': message, 'data': res})

    def get_time_graduation(self, cr, uid, context=None):
        _logger.info('get_time_graduation() start')
        code = 1
        data = ''
        message = 'success'
        try:
            obj = self.pool.get('vhr.dimension')
            obj_ids = obj.search(cr, uid, GRADUATION_DIMENSION_DOMAIN, order='name')
            data = obj.read(cr, uid, obj_ids, ['name', 'name_en'])
            data = sorted(data, key=itemgetter('name'))
        except Exception, e:
            code = -99
            message = e.message
            _logger.error('get_time_graduation() %s' % message)
        _logger.info('get_time_graduation() end')
        return json.dumps({'code': code, 'message': message, 'data': data})

    def get_school(self, cr, uid, data='{}', context=None):
        _logger.info('get_school() start')
        code = 1
        message = 'success'
        school_obj = self.pool.get('vhr.school')
        res = []
        try:
            data = json.loads(data)
            if data.get('program_event_id'):
                event_id = int(data['program_event_id'])
                event_obj = self.pool.get('vhr.program.event')
                event = event_obj.read(cr, uid, event_id, ['school_ids'])
                school_ids = event['school_ids']
            else:
                school_ids = school_obj.search(cr, uid, [('website_published', '=', True)], order='name')

            res = school_obj.read(cr, uid, school_ids, ['name', 'name_en', 'speciality_ids'])
            res = sorted(res, key=itemgetter('name'))
        except Exception, e:
            code = -99
            message = e.message
            _logger.error('get_school() %s' % message)
        _logger.info('get_school() end')
        return json.dumps({'code': code, 'message': message, 'data': res})

    def get_office(self, cr, uid, context=None):
        _logger.info('get_office() start')
        code = 1
        message = 'success'
        res = []
        try:
            obj = self.pool.get('vhr.office')
            obj_ids = obj.search(cr, uid, [('is_head_office', '=', True)])
            data = obj.read(cr, uid, obj_ids, ['city_id'])
            res = []
            for i in data:
                if i.get('city_id') and i['city_id'] not in res:
                    res.append(i['city_id'])
            locale.setlocale(locale.LC_ALL, "")
            res.sort(cmp=locale.strcoll, key=lambda x: x[1], reverse=True)
        except Exception, e:
            code = -99
            message = e.message
            _logger.error('get_office() %s' % message)
        _logger.info('get_office() end')
        return json.dumps({'code': code, 'message': message, 'data': res})

    def get_country(self, cr, uid, context=None):
        _logger.info('get_country() start')
        code = 1
        data = []
        message = 'success'
        try:
            obj = self.pool.get('res.country')
            obj_ids = obj.search(cr, uid, [], order='name')
            data = obj.read(cr, uid, obj_ids, ['name', 'code'])
            data = sorted(data, key=itemgetter('name'))
        except Exception, e:
            code = -99
            message = e.message
            _logger.error('get_country() %s' % message)
        _logger.info('get_country() end')
        return json.dumps({'code': code, 'message': message, 'data': data})

    def get_recruitment_degree(self, cr, uid, context=None):
        _logger.info('get_recruitment_degree() start')
        code = 1
        data = ''
        message = 'success'
        try:
            obj = self.pool.get('hr.recruitment.degree')
            obj_ids = obj.search(cr, uid, [], order='name')
            data = obj.read(cr, uid, obj_ids, ['name', 'code'])
            data = sorted(data, key=itemgetter('name'))
        except Exception, e:
            code = -99
            message = e.message
            _logger.error('get_recruitment_degree() %s' % message)
        _logger.info('get_recruitment_degree() end')
        return json.dumps({'code': code, 'message': message, 'data': data})

    def get_job(self, cr, uid, context=None):
        _logger.info('get_job() start')
        code = 1
        message = 'success'
        res = []
        try:
            obj = self.pool.get('vhr.job')
            obj_ids = obj.search(cr, uid, [], order='name')
            data = obj.read(cr, uid, obj_ids, [])
            pos_job_obj = self.pool.get('vhr.post.job')
            # get corporation site
            m = self.pool.get('ir.model.data')
            corporation_site_id = m.get_object(cr, uid, 'vhr_recruitment', "post_job_location_to_corporation_site").id
            search_domain = [('post_location_ids', '=', corporation_site_id), ('date_start', '<=', fields.date.today()),
                             '|', ('date_end', '=', False), ('date_end', '>=', fields.date.today()),
                             ('state', '=', 'in_progress')]

            for i in data:
                job_domain = search_domain[:]
                job_domain.append(('vhr_job_id', '=', i['id']))
                
                #search vn
                job_domain_vn = job_domain[:]
                job_domain_vn.append(('description', '!=', False))
                job_ids = pos_job_obj.search(cr, uid, job_domain_vn)
                i['no_of_post_jobs'] = len(job_ids)
                # search eng
                job_domain_en = job_domain[:]
                job_domain_en.append(('description_en', '!=', False))
                job_ids_en = pos_job_obj.search(cr, uid, job_domain_en)
                i['no_of_post_jobs_en'] = len(job_ids_en)
                res.append(i)

            res = sorted(res, key=itemgetter('name'))
        except Exception, e:
            code = -99
            message = e.message
            _logger.error('get_job() %s' % message)
        _logger.info('get_job() end')
        return json.dumps({'code': code, 'message': message, 'data': res})

    def get_speciality_id(self, cr, speciality, uid):
        search_domain = SPECIALITY_DIMENSION_DOMAIN[:]
        search_domain.extend(['|', ('name', '=', speciality), ('name_en', '=', speciality)])
        speciality_ids = self.pool.get('vhr.dimension').search(cr, uid, search_domain)
        if speciality_ids:
            speciality_id = speciality_ids[0]
        else:
            speciality_id = self.pool.get('vhr.dimension').create(cr, uid, {'name': speciality},
                                                                  context={'dimension_type': 'SPECIALITY'})
        return speciality_id
    
    def get_student_staff(self, cr, uid, context=None):
        _logger.info('get_student_staff() start')
        code = 1
        data = ''
        message = 'success'
        try:
            obj = self.pool.get('vhr.dimension')
            obj_ids = obj.search(cr, uid, STUDENT_STAFF_DOMAIN)
            data = obj.read(cr, uid, obj_ids, ['name', 'name_en'])
        except Exception, e:
            code = -99
            message = e.message
            _logger.error('get_student_staff() %s' % message)
        _logger.info('get_student_staff() end')
        return json.dumps({'code': code, 'message': message, 'data': data})   
    
    def get_list_question(self, cr, uid, data='{}', context=None):# 6/1/2015
        _logger.info('get_list_question() start')
        code = 1
        res = []
        message = 'success'
        try:
            data = json.loads(data)
            search_domain = []
            question_obj = self.pool.get('vhr.program.question')
            answer_obj = self.pool.get('vhr.program.answer')
            dimension_obj = self.pool.get('vhr.dimension')
            if data.get('program_event_id'):
                program_event_id = int(data['program_event_id'])
                search_domain.append(('program_event_id', '=', program_event_id))
            obj_ids = question_obj.search(cr, uid, search_domain, order='id')
            res = question_obj.read(cr, uid, obj_ids, [])
            for item in res:
                if item.get('answer_ids'):
                    item['answer_ids'] = answer_obj.read(cr, uid, item.get('answer_ids'), ['name','name_en','id'])
                item['question_type_code'] = ''
                if item.get('question_type_id'):
                    item_code = dimension_obj.read(cr, uid, item.get('question_type_id')[0], ['code'])
                    item['question_type_code'] = item_code['code'] if item_code.get('code') else ''
                if item.get('question_part_id'):
                    item_code = dimension_obj.read(cr, uid, item.get('question_part_id')[0], ['code'])
                    item['question_part_code'] = item_code['code'] if item_code.get('code') else ''
        except Exception, e:
            code = -99
            message = e.message
            _logger.error('get_list_question() %s' % message)
        _logger.info('get_list_question() end')
        return json.dumps({'code': code, 'message': message, 'data': res})
    
    def get_request_job(self, cr, uid, data={}, context=None):
        _logger.info('get_request_job() start')
        code = 1
        data = ''
        message = 'success'
        try:
            obj = self.pool.get('vhr.post.job')
            # get corporation site
            m = self.pool.get('ir.model.data')
            corporation_site_id = m.get_object(cr, uid, 'vhr_recruitment', "post_job_location_to_corporation_site").id
            search_domain = [('post_location_ids', '=', corporation_site_id), ('date_start', '<=', fields.date.today()),
                             '|', ('date_end', '=', False), ('date_end', '>=', fields.date.today()),
                             ('state', '=', 'in_progress')]
            job_name = data and data.get('job_name') or ''
            if job_name:
                search_domain.append(('vhr_job_id', '=ilike', job_name.trim()))
            obj_ids = obj.search(cr, uid, search_domain, order='date_start desc')
            data = obj.read(cr, uid, obj_ids,
                            ['code', 'name', 'name_en', 'no_of_recruitment', 'office_id', 'job_type_id', 'date_start',
                             'date_end', 'description', 'description_en', 'requirement', 'vhr_job_id', 'city_id',
                             'job_category_id', 'requirement_en', 'preference', 'preference_en'])
            res = []
            for job in data:
                vhr_job_obj = self.pool.get('vhr.job')
                if job.get('vhr_job_id'):
                    vhr_job_id = job['vhr_job_id'][0]
                    job['vhr_job_id'] = vhr_job_obj.read(cr, uid, vhr_job_id, ['name', 'name_en', 'code'])
                res.append(job)
            res = sorted(res, key=itemgetter('date_start'), reverse=True)
        except Exception, e:
            code = -99
            message = e.message
            _logger.error('get_request_job() %s' % message)
        _logger.info('get_request_job() end')
        return json.dumps({'code': code, 'message': message, 'data': res})
    
    def get_life_at_hrs(self, cr, uid, context=None):
        _logger.info('get_life_at_hrs() begin')
        result = []
        try:             
            code_life = self.pool.get('ir.config_parameter').get_param(cr, uid, 'hrs.recruitment.hrs.site.code.for.life')
            code_life = code_life.split(',') if code_life else []
            if code_life:
                program_content_obj = self.pool.get('vhr.program.content')
                lst_result = program_content_obj.search(cr, uid, [('code','in', code_life)])
                result = program_content_obj.read(cr, uid, lst_result, [])
        except Exception, e:
            _logger.error('get_life_at_hrs() %s' % e.message)
        _logger.info('get_life_at_hrs() end')
        return result
    
    def get_advive(self, cr, uid, context=None):
        _logger.info('get_advive() begin')
        result = []
        try:             
            code_advice = self.pool.get('ir.config_parameter').get_param(cr, uid, 'hrs.recruitment.hrs.site.code.for.advice')
            code_advice = code_advice.split(',') if code_advice else []
            if code_advice:
                program_content_obj = self.pool.get('vhr.program.content')
                lst_result = program_content_obj.search(cr, uid, [('code', 'in', code_advice)])
                result = program_content_obj.read(cr, uid, lst_result, [])           
            
        except Exception, e:
            _logger.error('get_advive() %s' % e.message)
        _logger.info('get_advive() end')
        return result
    
    def get_faqs(self, cr, uid, data='{}', context=None):
        _logger.info('get_faqs() begin')
        result = []
        try:             
            code_faqs = self.pool.get('ir.config_parameter').get_param(cr, uid, 'hrs.recruitment.hrs.site.code.for.faqs')
            code_faqs = code_faqs.split(',') if code_faqs else []
            if code_faqs:
                domain_search =  [('code','in', code_faqs)]
                if data and data.get('program_type_ids'):
                    domain_search.append(('program_id.code','in', data.get('program_type_ids')))
                program_content_obj = self.pool.get('vhr.program.content')
                lst_result = program_content_obj.search(cr, uid,domain_search)
                result = program_content_obj.read(cr, uid, lst_result, [])           
            
        except Exception, e:
            _logger.error('get_faqs() %s' % e.message)
        _logger.info('get_faqs() end')
        return result
    
    def get_list_career(self, cr, uid, data='{}', context=None):
        _logger.info('get_list_career() begin')
        result = []
        carrer_domain = [('program_id.code', '=', 'CANDIDATE'), ('active', '=', True),
                         ('date_from', '<=', datetime.date.today()),
                         '|', ('date_to', '=', False), ('date_to', '>=', datetime.date.today())]
        fields_read = []
        lang = 'vn'
        if data :
            if data.get('fields'):
                fields_read = data.get('fields')
            if data.get('lang'):
                lang = data.get('lang')
        program_event_obj = self.pool.get('vhr.program.event')
        program_event_ids = program_event_obj.search(cr, uid, carrer_domain)
        if program_event_ids:  # Xu ly neu dang ton tai event
            # doc event cua carrer dang hoat dong
            result = program_event_obj.read(cr, uid, program_event_ids[0], fields_read)
            # get job post website
            job_cat_ids = []
            job_obj = self.pool.get('vhr.job')
            job_ids = job_obj.search(cr, uid, [], order='name')
            job_data = job_obj.read(cr, uid, job_ids, [])                
            m = self.pool.get('ir.model.data')
            pos_job_obj = self.pool.get('vhr.post.job')
            corporation_site_id = m.get_object(cr, uid, 'vhr_recruitment', "post_job_location_to_corporation_site").id
            post_job_domain = [('post_location_ids', '=', corporation_site_id), ('date_start', '<=', fields.date.today()),
                             '|', ('date_end', '=', False), ('date_end', '>=', fields.date.today()),
                             ('state', '=', 'in_progress')]

            # list job program minimize
            job_program_ids = []
            job_domain = post_job_domain[:]
            if lang == 'vn':
                job_domain.append(('description', '!=', False))
                flds = ['name', 'code', 'city_id', 'description', 'vhr_job_id', 'requirement', 'preference',
                        'salary', 'date_start', 'job_flags', 'allow_internal', 'hash_tags_str', 'job_categories']
            else:
                job_domain.append(('description_en', '!=', False))
                flds = ['name', 'name_en', 'code', 'city_id', 'description_en', 'vhr_job_id', 'requirement_en',
                        'preference_en', 'salary_en', 'date_start', 'job_flags', 'allow_internal',
                        'hash_tags_str', 'job_categories']

            lst_job_domain = pos_job_obj.search(cr, uid, job_domain, order='date_start desc')
            job_program_ids = pos_job_obj.read(cr, uid, lst_job_domain, flds)
            vhr_job_obj = self.pool.get('vhr.job')
            list_jobs = {}
            for item in job_program_ids:
                item['vhr_job_id'] = vhr_job_obj.read(cr, uid, item.get('vhr_job_id')[0], ['name', 'name_en'])
                for vhr_job in item.get('job_categories', []):
                    if vhr_job not in list_jobs.keys():
                        list_jobs[vhr_job] = {'vn': [], 'en': []}
                    if item.get('description', False):
                        list_jobs[vhr_job]['vn'].append(item)
                    if item.get('description_en', False):
                        list_jobs[vhr_job]['en'].append(item)

            # list job detail by cat
            for i in job_data:
                i['no_of_post_jobs'] = 0
                i['job_program_ids'] = []
                if i['id'] in list_jobs.keys():
                    if lang == 'vn':
                        no_of_post_jobs = list_jobs[i['id']]['vn']
                    else:
                        no_of_post_jobs = list_jobs[i['id']]['en']
                    i['no_of_post_jobs'] = len(no_of_post_jobs)
                    i['job_program_ids'] = no_of_post_jobs
                job_cat_ids.append(i)
            job_cat_ids = sorted(job_cat_ids, key=itemgetter('sequence'))
            result['job_cat_ids'] = job_cat_ids

            result['job_program_ids'] = job_program_ids
            # get list fields
            if result.get('field_ids'):
                result['field_ids'] = self._get_fields_by_event(cr, uid, result.get('field_ids'), program_event_ids[0])
            if result.get('part_ids'):
                result['part_ids'] = self._get_parts_and_question(cr, uid, result.get('part_ids'))
        _logger.info('get_list_career() end')
        return result
    
    def get_list_recruitment_program(self, cr, uid, data='{}', context=None):
        '''
            data = {
                        "program_id": 12,
                        "fields": ["name","description", "program_content_ids", "event_title",
                                    "short_description", "program_event_ids"
                                ],
                        "lang": 'en'
                    }
        '''
        _logger.info('get_list_recruitment_program() start')
        result = []
        search_domain = RECRUITMENT_PROGRAM_DOMAIN[:]
        fields_read = []
        lang = 'vn'
        if data : 
            data = json.loads(data)
            if data.get('program_id'):
                search_domain.append(('id', '=', int(data.get('program_id'))))
            if data.get('fields'):
                fields_read = data.get('fields')
            if data.get('lang'):
                lang = data.get('lang')
        obj = self.pool.get('vhr.program.recruitment')
        obj_ids = obj.search(cr, uid, search_domain)
        for obj_id in obj_ids:
            res = obj.read(cr, uid, obj_id, fields_read)
            # lay danh sach chuong trinh khac
            if res.get('id'):
                search_domain = RECRUITMENT_PROGRAM_DOMAIN[:]
                search_domain.append(('id', '!=', res.get('id')))
                lst_other = obj.search(cr, uid, search_domain)
                res['other_program_ids'] = obj.read(cr, uid, lst_other, ['name', 'name_en'])
            # lay danh sach event trong chuong trinh
            if res.get('program_event_ids'):
                event_obj = self.pool.get('vhr.program.event')
                # kiem tra thoi gian hop le
                event_domain = [('date_from', '<=', fields.date.today()),
                                '|', ('date_to', '=', False), ('date_to', '>=', fields.date.today())]
                event_domain.append(('id', 'in', res['program_event_ids']))
                if lang == 'vn':
                    event_domain.append(('description', '!=', False))
                else:
                    event_domain.append(('description_en', '!=', False))
                event_ids = event_obj.search(cr, uid, event_domain, order='name', context=context)
                res['program_event_ids'] = event_obj.read(cr, uid, event_ids, ['name','name_en'])
            # lay danh sach mo ta trong chuong trinh
            if res.get('program_content_ids'):
                content_obj = self.pool.get('vhr.program.content')
                res['program_content_ids'] = content_obj.read(cr, uid, res['program_content_ids'],\
                                                              ['name', 'name_en', 'description', 'description_en'])
            # lay danh sach face typical
            if res.get('face_typical_ids'):
                face_obj = self.pool.get('vhr.typical.face')
                res['face_typical_ids'] = face_obj.read(cr, uid, res['face_typical_ids'],\
                                                              ['name', 'name_en', 'content', 'content_en', 'image'])
            
            result.append(res)
        return result
    
    def get_dynamic_info(self, cr, uid, data='{}', context=None):
        '''
            {'method': 'get_school','data': {'program_event_id':45}}
        '''
        _logger.info('get_dynamic_info() start')
        code = 1
        res = []
        message = 'success'
        try: 
            data = json.loads(data) if data else {}
            if data.get('method'): 
                if data.get('data'):               
                    res = audittrail.execute_cr(cr, uid, self._name, data.get('method'),data.get('data') , context)
                else:
                    res = audittrail.execute_cr(cr, uid, self._name, data.get('method'), context)
            else:
                code = -99
                message = 'data blank'
        except Exception, e:
            code = -99
            message = e.message
            _logger.error('get_dynamic_info() %s' % message)
        _logger.info('get_dynamic_info() end')
        return json.dumps({'code': code, 'message': message, 'data': res})
    
    def notify_change(self, cr, uid, context=None):
        api_url = self.pool.get('ir.config_parameter').get_param(cr, uid, 'update.cache.hrs.api.url')
        i = 3
        while i and api_url:
            i -= 1
            try:
                res = requests.get(api_url, timeout=10)
                logging.info('notify_change %s' % res)
                if res.status_code == 200:
                    break
            except Exception, e:
                logging.exception('notify_change %s' % e.message)
        return True

    def unsubscribe_news_letter(self, cr, uid, data='{}', context=None):
        _logger.info('unsubscribe_news_letter() start: %s' % data)
        if context is None:
            context = {}
        context.update({'model': 'vhr.recruitment.interface', 'function': 'subscribe_news_letter'})

        code = 1
        message = 'success'
        try:
            data = json.loads(data)
            if data.get('email') and data.get('program_type'):
                program_type = data.get('program_type')

                email_news_obj = self.pool.get('vhr.email.news')
                email_ids = email_news_obj.search(cr, uid, [('email', '=', data['email'])])
                if email_ids:
                    m = self.pool.get('ir.model.data')
                    program_id = m.get_object(cr, uid, 'vhr_recruitment', 'hrs_data_program_candidate').id
                    email_data = email_news_obj.read(cr, uid, email_ids[0], ['program_type_ids'])
                    program_type_ids = email_data['program_type_ids']
                    email_data = {}
                    if program_type == 'CANDIDATE':
                        if program_type_ids:
                            program_type_ids.remove(program_id)
                            email_data['program_type_ids'] = [(6, 0, program_type_ids)]
                        else:
                            code = -99
                            message = 'email not found!'
                    elif program_type == 'STUDENT':
                        if program_type_ids:
                            email_data['program_type_ids'] = [(6, 0, [program_id])]
                        else:
                            email_data['program_type_ids'] = [(6, 0, [])]
                    if email_data:
                        email_news_obj.write(cr, uid, email_ids, email_data, context)

                else:
                    code = -99
                    message = 'email not found'
            else:
                code = -99
                message = 'missing email'
        except Exception, e:
            code = -99
            message = e.message
            _logger.error('unsubscribe_news_letter() %s' % message)

        return json.dumps({'code': code, 'message': message})

    def active_email_subscription(self, cr, uid, data='{}', context=None):
        code = 1
        message = 'success'
        try:
            data = json.loads(data)
            if data.get('email') and data.get('id'):
                yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime(
                    DEFAULT_SERVER_DATETIME_FORMAT)
                email_news_obj = self.pool.get('vhr.email.news')
                email_ids = email_news_obj.search(cr, uid, [('id', '=', data['id']), ('email', '=', data['email']),
                                                            ('active', '=', False), '|',
                                                            ('create_date', '>=', yesterday),
                                                            ('write_date', '>=', yesterday)])
                if not email_ids:
                    email_ids = email_news_obj.search(cr, uid, [('id', '=', data['id']), ('email', '=', data['email']),
                                                                ('active', '=', True), '|',
                                                                ('create_date', '>=', yesterday),
                                                                ('write_date', '>=', yesterday)])
                    if not email_ids:
                        code = -99
                        message = 'email not found'
                else:
                    email_news_obj.write(cr, uid, email_ids, {'active': True})

        except Exception, e:
            code = -99
            message = e.message
            _logger.error('check_email_valid() %s' % message)

        return json.dumps({'code': code, 'message': message})

    def subscribe_news_letter(self, cr, uid, data='{}', context=None):
        _logger.info('subscribe_news_letter() start: %s' % data)

        if context is None:
            context = {}
        context.update({'model': 'vhr.recruitment.interface', 'function': 'subscribe_news_letter'})

        code = 1
        message = 'success'
        try:
            data = json.loads(data)
            res = self._check_required_fields(EMAIL_FIELD_MAP, data)
            if res != 'ok':
                return res
            email_news_obj = self.pool.get('vhr.email.news')
            email_ids = email_news_obj.search(cr, uid, [('email', '=', data['email']), '|', ('active', '=', True),
                                                        ('active', '=', False)])
            program_type_ids = data['program_type_ids']
            dimension_obj = self.pool.get('vhr.dimension')
            program_ids = []

            for i in program_type_ids:
                search_domain = PROGRAM_DIMENSION_DOMAIN[:]
                search_domain.append(('code', '=', i))
                program_ids.extend(dimension_obj.search(cr, uid, search_domain, context=context))

            if len(program_type_ids) != len(program_ids):
                code = -99
                message = 'PROGRAM CODE NOT FOUND!'

            data['program_type_ids'] = [[6, False, program_ids]]
            if email_ids:
                email_id = email_ids[0]
                program_ids.extend(
                    email_news_obj.read(cr, uid, email_ids[0], ['program_type_ids']).get('program_type_ids'))
                data['program_type_ids'] = [[6, False, set(program_ids)]]
                email_news_obj.write(cr, uid, email_ids, data, context=context)
                res = {"email": data['email'], 'id': email_ids[0]}
            else:
                data['active'] = False
                email_id = email_news_obj.create(cr, uid, data, context=context)
                res = {"email": data['email'], 'id': email_id}
            # send email dang ky thanh cong
            email_template = RE_Candidate_Subcriber if 'CANDIDATE' in program_type_ids else RE_Student_Subcriber
            self.recruitment_send_email(cr, uid, email_template, 'vhr.email.news', email_id)
        except Exception, e:
            code = -99
            message = e.message
            _logger.error('subscribe_news_letter() %s' % message)

        return json.dumps({'code': code, 'message': message, 'data': res})

    @staticmethod
    def _check_required_fields(map_field, data):
        for field in map_field['required']:
            if not data.get(field):
                code = -99
                message = 'Missing field or value null in field %s value %s' % (field, data.get(field))
                return {'code': code, 'message': message}
        return 'ok'

    def _create_attachment_url(self, cr, uid, res_model, res_name, url, file_name, res_id, context):
        attachment_value = {
            'name': file_name,
            'type': 'url',
            'res_name': res_name,
            'res_model': res_model,
            'res_id': res_id,
            'url': url,
            'datas_fname': file_name,
        }
        return self.pool.get('ir.attachment').create(cr, uid, attachment_value, context=context)
        
    def _create_attachment(self, cr, uid, res_model, res_name, file_data, file_name, res_id, context):
        attachment_value = {
            'name': file_name,
            'res_name': res_name,
            'res_model': res_model,
            'res_id': res_id,
            'datas': file_data,
            'datas_fname': file_name,
        }
        return self.pool.get('ir.attachment').create(cr, uid, attachment_value,
                                                     context=context)

    def _get_fields_by_event(self, cr, uid, field_ids, event_id):
        '''Get D/S fields dua theo event'''
        lst_field_ids = []
        for item in  self.pool.get('vhr.program.field').read(cr, uid, field_ids, []):
            # nhung field ko duoc public ko duoc generate
            try:
                if not item.get('is_public'):
                    continue    
                if item.get('field_type') and item.get('field_type') in ['many2one', 'many2many', 'one2many']:
                    func = "vget_%s" % (item.get('field_model'))
                    result_field = audittrail.execute_cr(cr, uid, self._name, func, {'event_id': int(event_id)}, None)
                    item['data'] = result_field 
                elif item.get('field_type') and item.get('field_type') in ['selection']:
                    list_data = []
                    if item.get('default'):
                        split = item.get('default').split('-')
                        for default_item in split:
                            list_data.append({'id': default_item.split(':')[0],
                                              'name': default_item.split(':')[1],
                                              'name_en': default_item.split(':')[2]})
                    item['data'] = list_data
            except Exception, e:
                _logger.error('get_program_event error() %s' % e.message)
            lst_field_ids.append(item)
            lst_field_ids = sorted(lst_field_ids, key=itemgetter('sequence'))
        return lst_field_ids
    
    def _get_parts_and_question(self, cr, uid, part_ids):
        result_part_ids = []
        try:
            part_obj = self.pool.get('vhr.program.part')
            question_obj = self.pool.get('vhr.program.question')
            answer_obj = self.pool.get('vhr.program.answer')
            dimension_obj = self.pool.get('vhr.dimension')
            result_part_ids = part_obj.read(cr, uid, part_ids, [])                        
            for item in result_part_ids:
                item['question_ids'] = question_obj.read(cr, uid, item['question_ids'],
                                                         ['name', 'name_en', 'answer_ids', 'is_required',
                                                          'description', 'question_type_id'])
                for ite in item['question_ids']:
                    if ite.get('answer_ids'):
                        ite['answer_ids'] = answer_obj.read(cr, uid, ite.get('answer_ids'),
                                                            ['name', 'name_en', 'id'])
                    ite['question_type_code'] = ''
                    if ite.get('question_type_id'):
                        item_code = dimension_obj.read(cr, uid, ite.get('question_type_id')[0], ['code'])
                        ite['question_type_code'] = item_code['code'] if item_code.get('code') else ''
        except Exception, e:
            _logger.error('get_program_event error() %s' % e.message)                
        return result_part_ids
    
    def get_career_program(self, cr, uid, data='{}', context=None):
        '''get program and event data for candidate
        '''
        _logger.info('get_career_program() start')
        code = 1
        result = []
        message = 'success'
        try:
            carrer_domain = [('program_id.code', '=', 'CANDIDATE'), ('active', '=', True),
                             ('date_from', '<=', datetime.date.today()),
                             '|', ('date_to', '=', False), ('date_to', '>=', datetime.date.today())]
            fields_read = []
            if data : 
                data = json.loads(data)
                if data.get('fields'):
                    fields_read = data.get('fields')
            program_event_obj = self.pool.get('vhr.program.event')
            program_event_ids = program_event_obj.search(cr, uid, carrer_domain)
            if program_event_ids:# Xu ly neu dang ton tai event
                # doc event cua carrer dang hoat dong
                result = program_event_obj.read(cr, uid, program_event_ids[0], fields_read)
                # get job post website
                job_cat_ids = []
                job_obj = self.pool.get('vhr.job')
                job_ids = job_obj.search(cr, uid, [], order='name')
                job_data = job_obj.read(cr, uid, job_ids, [])                
                m = self.pool.get('ir.model.data')
                pos_job_obj = self.pool.get('vhr.post.job')
                corporation_site_id = m.get_object(cr, uid, 'vhr_recruitment', "post_job_location_to_corporation_site").id
                post_job_domain = [('post_location_ids', '=', corporation_site_id), ('date_start', '<=', fields.date.today()),
                                   '|', ('date_end', '=', False), ('date_end', '>=', fields.date.today()),
                                   ('state', '=', 'in_progress')]
                # get list job program
                job_program_ids = []
                job_domain = pos_job_obj.search(cr, uid, post_job_domain, order='date_start desc')
                flds = ['name', 'name_en', 'code', 'city_id', 'description', 'description_en', 'vhr_job_id',
                        'requirement', 'requirement_en', 'preference', 'preference_en', 'salary', 'salary_en',
                        'date_start', 'job_flags', 'allow_internal', 'hash_tags_str', 'job_categories']
                job_program_ids = pos_job_obj.read(cr, uid, job_domain, flds)
                result['job_program_ids'] = job_program_ids
                list_jobs = {}
                for job in job_program_ids:
                    for vhr_job in job.get('job_categories', []):
                        if vhr_job not in list_jobs:
                            list_jobs[vhr_job] = {'vn': [], 'en': []}
                        if job.get('description', False):
                            list_jobs[vhr_job]['vn'].append(job)
                        if job.get('description_en', False):
                            list_jobs[vhr_job]['en'].append(job)

                for i in job_data:
                    if i['id'] in list_jobs.keys():
                        i['no_of_post_jobs_vn'] = len(list_jobs[i['id']]['vn'])
                        i['job_program_vn_ids'] = list_jobs[i['id']]['vn']

                        i['no_of_post_jobs_en'] = len(list_jobs[i['id']]['en'])
                        i['job_program_en_ids'] = list_jobs[i['id']]['en']
                        job_cat_ids.append(i)
                job_cat_ids = sorted(job_cat_ids, key=itemgetter('sequence'))
                result['job_cat_ids'] = job_cat_ids

                # get list fields
                if result.get('field_ids'):
                    result['field_ids'] = self._get_fields_by_event(cr, uid, result.get('field_ids'), program_event_ids[0])
                if result.get('part_ids'):
                    result['part_ids'] = self._get_parts_and_question(cr, uid, result.get('part_ids'))
            else:
                code = -99
                message = 'Event of candidate program not exist'                    
        except Exception, e:
            code = -99
            message = e.message
            _logger.error('get_career_program() %s' % message)
        _logger.info('get_career_program() end')
        return json.dumps({'code': code, 'message': message, 'data': result})
        
    def get_recruitment_program(self, cr, uid, data='{}', context=None):
        '''
            data = {
                        "program_id": 12,
                        "fields": ["name","description", "program_content_ids", "event_title",
                                    "short_description", "program_event_ids"
                                ]
                    }
        '''
        _logger.info('get_recruitment_program() start')
        code = 1
        result = []
        message = 'success'
        try:
            search_domain = RECRUITMENT_PROGRAM_DOMAIN[:]
            fields_read = []
            order_by = 'id asc'
            if data : 
                data = json.loads(data)
                if data.get('program_id'):
                    search_domain.append(('id', '=', int(data.get('program_id'))))
                if data.get('fields'):
                    fields_read = data.get('fields')
                if data.get('order_by'):
                    order_by = data['order_by'] + (data.get('order_type') and ' ' + data['order_type'] or ' asc')
            obj = self.pool.get('vhr.program.recruitment')
            obj_ids = obj.search(cr, uid, search_domain, order=order_by)
            for obj_id in obj_ids:
                res = obj.read(cr, uid, obj_id, fields_read)
                # lay danh sach chuong trinh khac
                if res.get('id'):
                    search_domain = RECRUITMENT_PROGRAM_DOMAIN[:]
                    search_domain.append(('id', '!=', res.get('id')))
                    lst_other = obj.search(cr, uid, search_domain)
                    res['other_program_ids'] = obj.read(cr, uid, lst_other, ['name', 'name_en'])
                # lay danh sach event trong chuong trinh
                if res.get('program_event_ids'):
                    event_obj = self.pool.get('vhr.program.event')
                    # kiem tra thoi gian hop le
                    event_domain = [('date_from', '<=', fields.date.today()),
                                    '|', ('date_to', '=', False), ('date_to', '>=', fields.date.today())]
                    event_domain.append(('id', 'in', res['program_event_ids']))
                    event_ids = event_obj.search(cr, uid, event_domain, order='name', context=context)
                    res['program_event_ids'] = event_obj.read(cr, uid, event_ids, ['name','name_en'])
                # lay danh sach mo ta trong chuong trinh
                if res.get('program_content_ids'):
                    content_obj = self.pool.get('vhr.program.content')
                    res['program_content_ids'] = content_obj.read(cr, uid, res['program_content_ids'],\
                                                                  ['name', 'name_en', 'description', 'description_en'])
                # lay danh sach face typical
                if res.get('face_typical_ids'):
                    face_obj = self.pool.get('vhr.typical.face')
                    res['face_typical_ids'] = face_obj.read(cr, uid, res['face_typical_ids'],\
                                                                  ['name', 'name_en', 'content', 'content_en', 'image'])
                
                result.append(res)
        except Exception, e:
            code = -99
            message = e.message
            _logger.error('get_recruitment_program() %s' % message)
        _logger.info('get_recruitment_program() end')
        return json.dumps({'code': code, 'message': message, 'data': result})
    
    def get_program_event(self, cr, uid, data='{}', context=None):
        """
            Lay thong tin event dua vao id
        """
        _logger.info('get_program_event() start')
        code = 1
        message = 'success'
        res = []# haizzza thoi ke vay
        try:
            data = json.loads(data) if data else {}
            if data.get('event_id'):
                program_event_id = int(data.get('event_id'))
                program_event_obj = self.pool.get('vhr.program.event')
                data_read = program_event_obj.read(cr, uid, program_event_id, [])
                # lay danh sach field
                if data_read.get('field_ids'):
                    data_read['field_ids'] = self._get_fields_by_event(cr, uid, data_read['field_ids'], program_event_id)
                # lay danh sach part_ids danh sach cau hoi va cau tra loi trong part
                if data_read.get('part_ids'):
                    data_read['part_ids'] = self._get_parts_and_question(cr, uid, data_read.get('part_ids'))
                res.append(data_read)
            else:
                code = -99
                message = 'event_id not exist'
        except Exception, e:
            code = -99
            message = e.message
            _logger.error('get_program_event() %s' % message)
        _logger.info('get_program_event() end')
        return json.dumps({'code': code, 'message': message, 'data': res})     
    
    def receive_application_from_fe_v1(self, cr, uid, data, context=None):
        _logger.info('receive_application_from_fe_v1() start: %s' % data)
        if context is None:
            context = {}
        context.update({'model': 'vhr.recruitment.interface', 'function': 'receive_application_from_fe_v1'})
        code = 1
        message = 'success'
        try:
            data = json.loads(data)
            if data.get('recommend_data', False):
                return self.receive_recommend_candidate(cr, SUPERUSER_ID, data, context=context)
            if data.get('recommend_fresher', False):
                return self.receive_recommend_fresher(cr, SUPERUSER_ID, data, context=context)
            if data.get('internal', False):
                return self.receive_internal_candidate(cr, SUPERUSER_ID, data, context=context)
            if data.get('program_event_id'):
                program_event_id = int(data['program_event_id'])
                try:
                    model_name = 'vhr.temp.applicant'
                    temp_applicant_obj = self.pool.get(model_name)
                    event_obj = self.pool.get('vhr.program.event')
                    data['email'] = data['email'].strip()
                    # check duplicate register
                    search_domain = [('email', '=', data['email'])]
                    if data.get('post_job_id'):
                        post_job_id = int(data['post_job_id'])
                        search_domain.append(('post_job_id', '=', post_job_id))
                    else:
                        search_domain.append(('program_event_id', '=', program_event_id))
                    flds = ["source_id", "temp_email_for_rr_id", "temp_email_for_register_id"]
                    res_event = event_obj.read(cr, uid, program_event_id, flds, context=context)
                    data['recruitment_source_id'] = res_event.get("source_id", False) and res_event['source_id'][0] or False
                    email_template_for_recruiter = res_event.get("temp_email_for_rr_id", False) and res_event['temp_email_for_rr_id'][1] or ""
                    email_template_for_register = res_event.get("temp_email_for_register_id", False) and res_event['temp_email_for_register_id'][1] or ""
                    # thong tin bai thi
                    if data.get('test_result_ids'):
                        test_result_ids = data.get('test_result_ids')
                        test_result_ids_fn = []
                        for item in test_result_ids:
                            if item.get('id') and item.get('value'):
                                dict_val = {'answer': '||'.join(item.get('value')),
                                            'program_event_id': program_event_id,
                                            'program_question_id': int(item.get('id'))
                                }
                                test_result_ids_fn.append([0, False, dict_val])  
                        data['test_result_ids'] = test_result_ids_fn
                    # thong tin doan hoi
                    if data.get('student_staff_ids'):
                        student_staff_ids = data.get('student_staff_ids')
                        student_staff_ids_fn = []
                        for item in student_staff_ids:
                            student_staff_ids_fn.append(int(item))
                        data['student_staff_ids'] = [[6, False, student_staff_ids_fn]]

                    res_id = temp_applicant_obj.search(cr, uid, search_domain, context=context)
                    if not res_id:
                        res_id = temp_applicant_obj.create(cr, uid, data, context=context)
                    else:
                        res_id = res_id[0]
                            
                    attachment_ids = []
                    if data.get('resume'):
                        field_value = data['resume']
                        file_name = field_value and field_value.get('filename') or False
                        file_data = field_value and field_value.get('datas') or False
                        file_url = field_value and field_value.get('url') or False
                        if file_name and (file_data or file_url):
                            if data.get('first_name') and data.get('last_name'):
                                res_name = "%s %s" % (data['first_name'], data['last_name'])
                            elif data.get('name'):
                                res_name = data['name']
                            else:
                                res_name = 'default_file_name'
                            # tao url hoac tao file
                            attachment_id = None
                            if file_url:
                                attachment_id = self._create_attachment_url(cr, uid, model_name, res_name, file_url,
                                                                            file_name, res_id, context=context)
                            else:
                                attachment_id = self._create_attachment(cr, uid, model_name, res_name, file_data,
                                                                        file_name, res_id, context=context)
                            if attachment_id:
                                attachment_ids.append(attachment_id)
                        else:
                            code = -99
                            message = 'Missing resume filename or file_data'
                            _logger.error('receive_application_from_fe_v1(): %s' % message)

                    if data.get('compress'):
                        field_value = data['compress']
                        file_name = field_value and field_value.get('filename') or False
                        file_data = field_value and field_value.get('datas') or False
                        file_url = field_value and field_value.get('url') or False
                        if file_name and (file_data or file_url):
                            if data.get('first_name') and data.get('last_name'):
                                res_name = "%s %s" % (data['first_name'], data['last_name'])
                            elif data.get('name'):
                                res_name = data['name']
                            else:
                                res_name = 'default_file_name'
                            attachment_id = None
                            if file_url:
                                attachment_id = self._create_attachment_url(cr, uid, model_name, res_name, file_url,
                                                                            file_name, res_id, context=context)
                            else:
                                attachment_id = self._create_attachment(cr, uid, model_name, res_name, file_data,
                                                                        file_name, res_id, context=context)
                            if attachment_id:
                                attachment_ids.append(attachment_id)
                        else:
                            code = -99
                            message = 'Missing compress filename or file_data'
                            _logger.error('receive_application_from_fe_v1(): %s' % message)
                    # send email for register
                    if email_template_for_register and code == 1:
                        self.recruitment_send_email(cr, uid, email_template_for_register, model_name, res_id)
                    # send email for recruiter
#                     if email_template_for_recruiter:
#                         self.recruitment_send_email(cr, uid, email_template_for_recruiter, model_name, res_id)
                except Exception, e:
                    code = -99
                    message = e.message
                    _logger.error('receive_application_from_fe_v1() error_create_record: %s' % message)
            else:
                code = -99
                message = 'Missing program_event_id'
                _logger.error('receive_application_from_fe_v1() error_create_record: %s' % message)

        except Exception, e:
            code = -99
            message = e.message
            _logger.error('receive_application_from_fe_v1() error_load_data: %s' % message)
        _logger.info('receive_application_from_fe_v1() end')
        res = {'code': code, 'message': message}
        return json.dumps(res)
    
#   Support generate form auto
    
    def vget_recruitment_source_id(self, cr, uid, data={}, context=None):
        result = []
        return result
    
    def vget_post_job_id(self, cr, uid, data={}, context=None):
        result = []
        return result
    
    def vget_program_event_id(self, cr, uid, data={}, context=None):
        result = []
        return result
    
    def vget_country_id(self, cr, uid, data={}, context=None):
        obj = self.pool.get('res.country')
        id_vn = 243
        obj_ids = obj.search(cr, uid, [('id','!=', id_vn)], order='name')
        data_not_vn = obj.read(cr, uid, obj_ids, ['name', 'code'])
        result = obj.read(cr, uid, [id_vn], ['name', 'code'])
        result.extend(data_not_vn)
        return result        
      
    def vget_school_id(self, cr, uid, data={}, context=None):
        result = []
        if data.get('event_id'):
            event_id = int(data['event_id'])
            event_obj = self.pool.get('vhr.program.event')
            school_obj = self.pool.get('vhr.school')
            event = event_obj.read(cr, uid, event_id, ['school_ids'])
            result = school_obj.read(cr, uid, event['school_ids'], ['name', 'name_en', 'speciality_ids'])
            for line in result:
                lst_speciality_ids = line.get('speciality_ids', False)
                line['domain'] = {
                    'list': lst_speciality_ids,
                    'field': 'speciality_id'
                }

        return result
    
    def vget_recruitment_degree_id(self, cr, uid, data={}, context= None):
        obj = self.pool.get('hr.recruitment.degree')
        obj_ids = obj.search(cr, uid, [], order='name')
        result = obj.read(cr, uid, obj_ids, ['name', 'code', 'name_en'])
        result = sorted(result, key=itemgetter('name'))
        return result
    
    def vget_recruitment_source_online_id(self, cr, uid, data={}, context=None):
        result = []
        if data.get('event_id'):
            event_id = int(data['event_id'])
            event_obj = self.pool.get('vhr.program.event')
            obj = self.pool.get('vhr.recruitment.source.online')
            event = event_obj.read(cr, uid, event_id, ['recruitment_source_online_ids'])
            obj_ids = event['recruitment_source_online_ids']
            result = obj.read(cr, uid, obj_ids, ['name', 'name_en'])
            result = sorted(result, key=itemgetter('name'))
        return result
    
    def vget_speciality_id(self, cr, uid, data={}, context=None):
        obj = self.pool.get('vhr.dimension')
        obj_ids = obj.search(cr, uid, SPECIALITY_ISPUBLIC_DIMENSION_DOMAIN)
        result = obj.read(cr, uid, obj_ids, ['name', 'name_en'])
        result = sorted(result, key=itemgetter('name'))
        return result
    
    def vget_time_graduation_id(self, cr, uid, data={}, context=None):
        obj = self.pool.get('vhr.dimension')
        obj_ids = obj.search(cr, uid, GRADUATION_DIMENSION_DOMAIN, order='name')
        result = obj.read(cr, uid, obj_ids, ['name', 'name_en'])
        result = sorted(result, key=itemgetter('name'))
        return result
        
    def vget_student_staff_ids(self, cr, uid, data={}, context=None):
        obj = self.pool.get('vhr.dimension')
        obj_ids = obj.search(cr, uid, STUDENT_STAFF_DOMAIN)
        data = obj.read(cr, uid, obj_ids, ['name', 'name_en'])
        return data
    
    def vget_job_id(self, cr, uid, data={}, context=None):
        result = []
        if data.get('event_id'):
            event_id = int(data['event_id'])
            event_obj = self.pool.get('vhr.program.event')
            event_job_obj = self.pool.get('vhr.event.job')
            event = event_obj.read(cr, uid, event_id, ['position_ids'])
            result = event_job_obj.read(cr, uid, event['position_ids'], ['name', 'name_en'])
        return result

    def get_program_event_gifts(self, cr, uid, data=None, context=None):
        """
            Update program event gifts
        """
        _logger.info('get_program_event_gifts() start')
        code = 1
        message = 'success'
        if data is None:
            data = {}
        try:
            data = json.loads(data)
            if data.get('res_id'):
                email_template = "RE_CANDIDATE_RECEIVE_GIFT_SPIN_WHEEL"
                res_id = int(data.get('res_id'))
                temp_app_obj = self.pool.get('vhr.temp.applicant')
                gift_obj = self.pool.get('vhr.program.event.gift')
                temp_ids = temp_app_obj.search(cr, uid, [
                    ('id', '=', res_id), ('gift_id', '!=', False), ('is_spin', '=', False)], context=context)
                if temp_ids:
                    temp_app_obj.write(cr, uid, temp_ids, {'is_spin': True}, context=context)
                    res_temp = temp_app_obj.read(cr, uid, temp_ids[0], ["gift_id"], context=context)
                    if res_temp.get("gift_id", False):
                        gift_id = res_temp["gift_id"][0]
                        res_gift = gift_obj.read(cr, uid, gift_id, ['is_lucky'], context=context)
                        if not res_gift.get("is_lucky", False):
                            self.recruitment_send_email(cr, uid, email_template, 'vhr.temp.applicant', temp_ids[0])
            else:
                code = -99
                message = 'res_id does not exist'
        except Exception, e:
            code = -99
            message = e.message
        _logger.error('get_program_event_gifts() %s' % message)
        _logger.info('get_program_event_gifts() end')
        return json.dumps({'code': code, 'message': message})

    def update_program_event_gifts(self, cr, uid, data_event, context=None):
        res = {}
        base = 0.0004
        start_speed = 507.875
        end_speed = 41
        event_gift_obj = self.pool.get('vhr.program.event.gift')
        min_item = data_event.get('show_min_gift', False)
        if data_event:
            res = {'gifts': [], 'item': 0, 'pos': 0, 'auto_get': 0, 'speed': 0, 'is_lucky': 0}
            if data_event.get('has_gift', False) and not data_event.get('end_get_gifts', False):
                if data_event.get('event_gifts', []):
                    event_gifts = event_gift_obj.read(cr, uid, data_event['event_gifts'], [], context=context)
                    event_gifts = sorted(event_gifts, key=lambda elem: elem['weight'])
                    loop_item = {}
                    if min_item and len(data_event['event_gifts']) < min_item:
                        loop = min_item
                    else:
                        loop = len(data_event['event_gifts'])
                    total_gifts = []
                    for gift in event_gifts:
                        item = {'name': gift['name'], 'name_en': gift['name_en'],
                                'item': gift['id'], 'is_lucky': gift['is_lucky']}
                        res['gifts'].append(item)
                        if gift.get('unlimited', False) or gift.get('quantity', 0) > gift.get('used', 0):
                            if gift.get('unlimited', False):
                                total_gifts += [gift['id']]*100
                            else:
                                total_gifts += [gift['id']]*(gift.get('quantity', 0) - gift.get('used', 0))
                            if gift.get('unlimited', False) or gift.get('quantity', 0) > loop_item.get('quantity', 0):
                                loop_item = item
                                res['item'] = gift['id']

                    if len(total_gifts) <= 0 or len(res['gifts']) <= 0:
                        return res
                    random_item = randrange(0, len(total_gifts))
                    res['item'] = total_gifts[random_item]
                    res['pos'] = len(res['gifts'])
                    res['speed'] = 0.210

                    if 2 < len(res['gifts']) < loop:
                        step = loop-len(res['gifts'])
                        for i in range(0, step):
                            pos = i*2+1
                            if pos > len(res['gifts']):
                                pos = len(res['gifts'])
                            res['gifts'].insert(pos, loop_item)

                    for i, gift in enumerate(res['gifts']):
                        if gift['item'] == res['item']:
                            res['pos'] = i
                            if gift.get('is_lucky', False):
                                res['is_lucky'] = 1
                            break
                    res['speed'] = start_speed*base+(end_speed+len(res['gifts']))*base*(res['pos']+1)

                    if 0 < len(res['gifts']) <= 2:
                        res['auto_get'] = 1
        return res

    def receive_recommend_candidate(self, cr, uid, data, context=None):
        code = 1
        message = 'success'
        email_template = 'RE_RECOMMEND_CV_TO_ERP'
        temp_app_obj = self.pool.get('vhr.temp.applicant')
        try:
            if data.get('email', False) and data.get('ref_email', False):
                try:
                    model_name = 'vhr.rr.recommend.cv'
                    rec_cv_obj = self.pool.get(model_name)
                    data['email'] = (data['email'].strip()).lower()
                    data['ref_email'] = (data['ref_email'].strip()).lower()
                    # check duplicate register
                    search_domain = [('email', '=', data['email']), ('ref_email', '=', data['ref_email'])]

                    if data.get('job_id'):
                        job_id = int(data['job_id'])
                        data['job_id'] = job_id
                        search_domain.append(('job_id', '=', job_id))
                        email_template = 'RE_RECOMMEND_CV_TO_ERP_2'

                    if data.get('post_id'):
                        post_id = int(data['post_id'])
                        data['post_id'] = post_id
                        search_domain.append(('post_id', '=', post_id))
                        email_template = 'RE_RECOMMEND_CV_TO_ERP'


                    rec_ids = rec_cv_obj.search(cr, uid, search_domain, context=context)
                    if not rec_ids:
                        res_id = rec_cv_obj.create(cr, uid, data, context=context)
                    else:
                        res_id = rec_ids[0]
                    attachment_ids = []
                    file_data = False
                    if data.get('resume'):
                        field_value = data['resume']
                        file_name = field_value and field_value.get('filename') or False
                        file_url = field_value and field_value.get('url') or False
                        if file_name and file_url:
                            res_name = data.get('name', 'default_file_name')
                            try:
                                file_data = temp_app_obj.get_file_attachment(cr, file_url)
                                attachment_id = self._create_attachment(cr, uid, model_name, res_name, file_data,
                                                                        file_name, res_id, context=context)
                            except Exception, e:
                                message = e.message
                                _logger.error('receive_recommend_candidate() create attachment error: %s' % message)

                                attachment_id = self._create_attachment_url(cr, uid, model_name, res_name, file_url,
                                                                            file_name, res_id, context=context)
                            if attachment_id:
                                attachment_ids.append(attachment_id)
                        else:
                            code = -99
                            message = 'Missing resume filename or file_data'
                            _logger.error('receive_recommend_candidate(): %s' % message)

                    # send email for register
                    if code == 1:
                        if file_data and attachment_ids:
                            self.recruitment_send_email(cr, uid, email_template, model_name, res_id, attachment_ids)
                        else:
                            self.recruitment_send_email(cr, uid, email_template, model_name, res_id)


                except Exception, e:
                    code = -99
                    message = e.message
                    _logger.error('receive_recommend_candidate() error_create_record: %s' % message)
            else:
                code = -99
                message = 'Missing Request Email'
                _logger.error('receive_recommend_candidate() error_create_record: %s' % message)
        except Exception, e:
            code = -99
            message = e.message
            _logger.error('receive_recommend_candidate() error_load_data: %s' % message)
        _logger.info('receive_recommend_candidate() end')
        res = {'code': code, 'message': message}
        return json.dumps(res)

    def receive_internal_candidate(self, cr, uid, data, context=None):
        code = 1
        message = 'success'
        email_template = 'RE_INTERNAL_CANDIDATE_APPLY_JOB'
        email_template2 = 'RE_INTERNAL_CANDIDATE_THANKS_LETTER'
        temp_app_obj = self.pool.get('vhr.temp.applicant')
        emp_obj = self.pool.get('hr.employee')
        try:
            if data.get('login', False):
                emp_ids = emp_obj.search(cr, uid, [('login', '=', data['login'])],  context=context)
                if not emp_ids:
                    code = -99
                    message = 'Employee Login does not exist!'
                    _logger.error('receive_internal_candidate() receive_internal_candidate: %s' % message)
                else:
                    try:
                        res_emp = emp_obj.browse(cr, uid, emp_ids[0], context=context)
                        model_name = 'vhr.rr.recommend.cv'
                        rec_cv_obj = self.pool.get(model_name)
                        emp_email = res_emp.work_email or res_emp.address_home_id.email
                        vals = {'name': res_emp.name, 'email': emp_email, 'employee_id': emp_ids[0], 'type': 'internal'}
                        search_domain = [('employee_id', '=', emp_ids[0]), ('type', '=', 'internal')]
                        if data.get('post_job_id'):
                            post_id = int(data['post_job_id'])
                            vals['post_id'] = post_id
                            search_domain.append(('post_id', '=', post_id))
                        rec_ids = rec_cv_obj.search(cr, uid, search_domain, context=context)
                        if not rec_ids:
                            res_id = rec_cv_obj.create(cr, uid, vals, context=context)
                        else:
                            res_id = rec_ids[0]
                        attachment_ids = []
                        file_data = False
                        if data.get('resume'):
                            field_value = data['resume']
                            file_name = field_value and field_value.get('filename') or False
                            file_url = field_value and field_value.get('url') or False
                            if file_name and file_url:
                                res_name = data.get('name', 'default_file_name')
                                try:
                                    file_data = temp_app_obj.get_file_attachment(cr, file_url)
                                    attachment_id = self._create_attachment(cr, uid, model_name, res_name, file_data,
                                                                            file_name, res_id, context=context)
                                except Exception, e:
                                    message = e.message
                                    _logger.error('receive_internal_candidate() create attachment error: %s' % message)

                                    attachment_id = self._create_attachment_url(cr, uid, model_name, res_name, file_url,
                                                                                file_name, res_id, context=context)
                                if attachment_id:
                                    attachment_ids.append(attachment_id)
                            else:
                                code = -99
                                message = 'Missing resume filename or file_data'
                                _logger.error('receive_internal_candidate(): %s' % message)

                        # send email for register
                        if code == 1 and (not rec_ids or (file_data and attachment_ids)):
                            if file_data and attachment_ids:
                                self.recruitment_send_email(cr, uid, email_template, model_name, res_id, attachment_ids)
                                self.recruitment_send_email(cr, uid, email_template2, model_name, res_id, attachment_ids)
                            else:
                                self.recruitment_send_email(cr, uid, email_template, model_name, res_id)
                                self.recruitment_send_email(cr, uid, email_template2, model_name, res_id)

                    except Exception, e:
                        code = -99
                        message = e.message
                        _logger.error('receive_internal_candidate() error_create_record: %s' % message)
            else:
                code = -99
                message = 'Missing Request Employee Login'
                _logger.error('receive_internal_candidate() error_create_record: %s' % message)
        except Exception, e:
            code = -99
            message = e.message
            _logger.error('receive_internal_candidate() error_load_data: %s' % message)
        _logger.info('receive_internal_candidate() end')
        res = {'code': code, 'message': message}
        return json.dumps(res)

    def receive_recommend_fresher(self, cr, uid, data, context=None):
        code = 1
        message = 'success'
        email_template = 'RE_SEND_TO_REGISTER_INVITE_FRIEND'
        temp_app_obj = self.pool.get('vhr.temp.applicant')
        try:
            if data.get('email', False) and data.get('ref_email', False):
                try:
                    model_name = 'vhr.rr.recommend.cv'
                    rec_cv_obj = self.pool.get(model_name)
                    data['email'] = (data['email'].strip()).lower()
                    data['ref_email'] = (data['ref_email'].strip()).lower()
                    # check duplicate register
                    search_domain = [('email', '=', data['email']), ('ref_email', '=', data['ref_email'])]
                    if data.get('program_event_id'):
                        program_event_id = int(data['program_event_id'])
                        data['program_event_id'] = program_event_id
                        search_domain.append(('program_event_id', '=', program_event_id))

                    rec_ids = rec_cv_obj.search(cr, uid, search_domain, context=context)
                    if not rec_ids:
                        res_id = rec_cv_obj.create(cr, uid, data, context=context)
                    else:
                        res_id = rec_ids[0]
                    attachment_ids = []
                    file_data = False
                    if data.get('resume'):
                        field_value = data['resume']
                        file_name = field_value and field_value.get('filename') or False
                        file_url = field_value and field_value.get('url') or False
                        if file_name and file_url:
                            res_name = data.get('name', 'default_file_name')
                            try:
                                file_data = temp_app_obj.get_file_attachment(cr, file_url)
                                attachment_id = self._create_attachment(cr, uid, model_name, res_name, file_data,
                                                                        file_name, res_id, context=context)
                            except Exception, e:
                                message = e.message
                                _logger.error('receive_recommend_fresher() create attachment error: %s' % message)

                                attachment_id = self._create_attachment_url(cr, uid, model_name, res_name, file_url,
                                                                            file_name, res_id, context=context)
                            if attachment_id:
                                attachment_ids.append(attachment_id)
                        else:
                            code = -99
                            message = 'Missing resume filename or file_data'
                            _logger.error('receive_recommend_fresher(): %s' % message)

                    if data.get('compress'):
                        field_value = data['compress']
                        file_name = field_value and field_value.get('filename') or False
                        file_url = field_value and field_value.get('url') or False
                        if file_name and file_url:
                            res_name = data.get('name', 'default_file_name')
                            try:
                                file_data = temp_app_obj.get_file_attachment(cr, file_url)
                                attachment_id = self._create_attachment(cr, uid, model_name, res_name, file_data,
                                                                        file_name, res_id, context=context)
                            except Exception, e:
                                message = e.message
                                _logger.error('receive_recommend_fresher() create compress error: %s' % message)

                                attachment_id = self._create_attachment_url(cr, uid, model_name, res_name, file_url,
                                                                            file_name, res_id, context=context)
                            if attachment_id:
                                attachment_ids.append(attachment_id)

                    # send email for register
                    if code == 1:
                        if file_data and attachment_ids:
                            self.recruitment_send_email(cr, uid, email_template, model_name, res_id, attachment_ids)
                        else:
                            self.recruitment_send_email(cr, uid, email_template, model_name, res_id)

                except Exception, e:
                    code = -99
                    message = e.message
                    _logger.error('receive_recommend_fresher() error_create_record: %s' % message)
            else:
                code = -99
                message = 'Missing Request Email'
                _logger.error('receive_recommend_fresher() error_create_record: %s' % message)
        except Exception, e:
            code = -99
            message = e.message
            _logger.error('receive_recommend_fresher() error_load_data: %s' % message)
        _logger.info('receive_recommend_fresher() end')
        res = {'code': code, 'message': message}
        return json.dumps(res)


Interface()
