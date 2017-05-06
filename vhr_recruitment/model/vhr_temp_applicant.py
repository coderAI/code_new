# -*-coding:utf-8-*-
import logging
import json
import urllib2
import base64
from lxml import etree
from datetime import datetime
from dateutil.relativedelta import relativedelta
from urlparse import urlparse
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp import SUPERUSER_ID
from openerp.osv import osv, fields
from vhr_recruitment_abstract import vhr_recruitment_abstract

SPECIALITY_DIMENSION_DOMAIN = [('dimension_type_id.code', '=', 'SPECIALITY'), ('active', '=', True)]
SPECIALITY_ISPUBLIC_DIMENSION_DOMAIN = [('dimension_type_id.code', '=', 'SPECIALITY'), ('active', '=', True), ('is_published','=', True)]
PROGRAM_DIMENSION_DOMAIN = [('dimension_type_id.code', '=', 'DND_PROGRAM'), ('active', '=', True)]
PROGRAM_EVENT_DIMENSION_DOMAIN = [('program_id.code', '=', 'TOUR'), ('active', '=', True)]
GRADUATION_DIMENSION_DOMAIN = [('dimension_type_id.code', '=', 'TIME_GRADUATION'), ('active', '=', True)]
STUDENT_STAFF_DOMAIN = [('dimension_type_id.code', '=', 'STUDENT_STAFF'), ('active', '=', True)]

log = logging.getLogger(__name__)


class vhr_temp_applicant(osv.osv, vhr_recruitment_abstract):
    _name = 'vhr.temp.applicant'
    _description = 'VHR Temp Applicant'
    _inherit = 'vhr.rr.temp.applicant'
    
    def _get_attachment_number(self, cr, uid, ids, fields, args, context=None):
        res = dict.fromkeys(ids, 0)
        for app_id in ids:
            res[app_id] = self.pool['ir.attachment'].search_count(cr, uid, [('res_model', '=', 'vhr.temp.applicant'),
                                                                            ('res_id', '=', app_id)], context=context)
        return res

    def _get_program_event(self, cr, uid, ids, fields, args, context=None):
        if context is None:
            context = {}
        res = dict.fromkeys(ids, 0)
        for item in self.browse(cr, uid, ids, context=context):
            res[item.id] = item.program_event_id and item.program_event_id.code + ' - '+item.program_event_id.name or ''
        return res
    
    def _get_program_recruitment(self, cr, uid, ids, fields, args, context=None):
        if context is None:
            context = {}
        res = dict.fromkeys(ids, 0)
        for item in self.browse(cr, uid, ids, context=context):
            res[item.id] = item.program_event_id and item.program_event_id.program_id and item.program_event_id.program_id.name or ''
        return res
    
    def _get_sequence_program_recruitment(self, cr, uid, ids, fields, args, context=None):
        if context is None:
            context = {}
        res = dict.fromkeys(ids, 0)
        for item in self.browse(cr, uid, ids, context=context):
            res[item.id] = item.program_event_id and item.program_event_id.program_id and item.program_event_id.program_id.sequence or 1
        return res
    
    def _get_sequence_program(self, cr, uid, ids, fields, args, context=None):
        if context is None:
            context = {}
        res = dict.fromkeys(ids, 0)
        for item in self.browse(cr, uid, ids, context=context):
            res[item.id] = item.program_event_id and item.program_event_id.program_id and str(item.program_event_id.program_id.sequence)+'-'+item.program_event_id.program_id.name or ''
        return res


    def get_file_attachment(self, cr, url):
        res = None
        log.info('Start get_file_attachment')
        try:
            hrs_local_ip = self.pool.get('ir.config_parameter').get_param(cr, SUPERUSER_ID, 'hrs.recruitment.hrs.local.ip')
            url = urllib2.quote(url.encode('utf-8'), safe=':/').split('/')
            if url and len(url)>2:
                url[2] = hrs_local_ip
                response = urllib2.urlopen("/".join(url), timeout=120)
                if response.code == 200:
                    res = base64.encodestring(response.read())            
        except Exception, e:
            log.exception('%s' % e.message)
        log.info('End get_file_attachment')
        return res

    _columns = {
        'image': fields.binary("Photo",
                               help="This field holds the image used as photo for the employee, limited to 1024x1024px."),
        'school_id': fields.many2one('vhr.school', 'University'),
        'identification_no': fields.char('Identification No', size=32),
        'time_graduation_id': fields.many2one('vhr.dimension', 'Time Graduation', ondelete='restrict',
                                              domain=GRADUATION_DIMENSION_DOMAIN),  # Graduation
        'cumulative_gpa': fields.float('Cumulative GPA'),
        #change 22/12/2014 : source get from Event
        #change 22/12/2014 : get data
        'location_registry': fields.selection([('hcm', 'HCM')], 'Location Registration'),
        'speciality': fields.char('Speciality', size=150),  # Chuyên ngành không sử dụng nữa
        # 9/1/2015 : update for speaker
        'job_id': fields.many2one('vhr.event.job', 'Jobs', ), # Tai sao lai dat ten field ntn :'(
        
        'attachment_number': fields.function(_get_attachment_number, string='Number of Attachments', type="integer"),
        'program_event_id': fields.many2one('vhr.program.event', 'Program Event', ondelete='restrict',
                                            domain=PROGRAM_EVENT_DIMENSION_DOMAIN),
        'post_job_id': fields.many2one('vhr.post.job', 'Job Apply'),  # only for cv online program
        'country_id': fields.many2one('res.country', 'Country'),
        'index_content': fields.text('CV Index'),
        'recruitment_degree_id': fields.many2one('hr.recruitment.degree'),
        'cv_ids': fields.one2many('ir.attachment', 'res_id', 'Attachment', domain=[('res_model', '=', _name)]),
        #1/7/2015 add test result for program
        'test_result_ids': fields.one2many('vhr.candidate.test.result', 'temp_candidate_id', 'Test results'),
        'student_staff_ids': fields.many2many('vhr.dimension', 'tempapplicant_studentstaff_rel',
                                              'temp_app_id', 'student_staff_id', 'Student staff', domain=STUDENT_STAFF_DOMAIN),
        'student_code': fields.char('Student code', size=150),
        'porfolio_link': fields.char('Porfolio Link', size=250),
        'linkedin_link': fields.char('Linkedin Link', size=250),
        'messenger_name': fields.char('Messenger Name', size=250),
        #24/5/2016 event gift
        'gift_id': fields.many2one('vhr.program.event.gift', 'Gift'),
        'is_spin': fields.boolean('Is Spin'),
        
        'program_event': fields.function(_get_program_event, string='Program Event', type="char", store=True),
        'program_recruitment': fields.function(_get_program_recruitment, string='Program', type="char", store=True),
        'sequence_program_recruitment': fields.function(_get_sequence_program_recruitment, string='Program', type='integer', store=True),
        'sequence_program': fields.function(_get_sequence_program, string='Program', type='char', store=True),
    }

    _defaults = {
        'country_id': lambda self, cr, uid, context: self.pool.get('res.country').search(cr, uid, [('code', '=', 'VN')])[0]
    }

    _order = 'sequence_program asc,program_event desc, id desc'

        
    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        res = super(vhr_temp_applicant, self).default_get(cr, uid, fields, context=context)

        if context.get('PROGRAM', False):
            type_ids = self.pool.get('vhr.program.event').search(cr, uid,
                                                                 [('program_id.code', '=', context['PROGRAM'])],
                                                                 order='create_date desc', context=context)
            if type_ids:
                res['program_event_id'] = type_ids[0]
        return res
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(vhr_temp_applicant, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar=toolbar,
                                                              submenu=submenu)
        if view_type == 'form':
            doc = etree.XML(res['arch'])
            if res['type'] == 'form' and doc.xpath("//field[@name='applicant_id']"):
                for node in doc.xpath("//field"):
                    modifiers = json.loads(node.get('modifiers'))
                    args_readonly = [('applicant_id', '!=', False)]
                    modifiers.update({'readonly': args_readonly})
                    node.set('modifiers', json.dumps(modifiers))
            res['arch'] = etree.tostring(doc)
        return res

    def action_approve_temp_applicant(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        # update status for temp applicant become candidate
        self.write(cr, uid, ids, {'state': 'approved'}, context=context)
        applicant = self.browse(cr, uid, ids[0], context=context)
        applicant_obj = self.pool.get('hr.applicant')
        vhr_dimension_obj = self.pool.get('vhr.dimension')
        # search candidate
        applicant_ids = applicant_obj.check_applicant_exist(cr, uid, applicant.email, applicant.name,
                                                            applicant.gender, applicant.birthday)
        data = {'apply_date': applicant.create_date}
        data['description'] = applicant.index_content
        data['note'] = applicant.note
        data['source_type_id'] = applicant.program_event_id and applicant.program_event_id.source_type_id and\
                        applicant.program_event_id.source_type_id.id or False  
        data['source_id'] = applicant.program_event_id and applicant.program_event_id.source_id and\
                         applicant.program_event_id.source_id.id or False  
        data['auto_send_email'] = applicant.program_event_id and applicant.program_event_id.source_id and \
                         applicant.program_event_id.source_id.auto_send_email or False
        domain_job_type =  [('code', '=', 'PARTTIME'), ('dimension_type_id', '=', 'JOB_TYPE')]
        if context.get('PROGRAM') == 'CANDIDATE':
            domain_job_type =  [('code', '=', 'FULLTIME'), ('dimension_type_id', '=', 'JOB_TYPE')]
        job_type_ids = vhr_dimension_obj.search(cr, uid, domain_job_type, context=context)    
        data['job_type_id'] = job_type_ids and job_type_ids[0] or ''
        
        if context.get('PROGRAM') == 'FRESHER':  # Fresher
            data['is_fresher'] = True
            
        if applicant_ids:
            applicant_id = applicant_ids[0]
            applicant_obj.write(cr, uid, applicant_id, data, context=context)
            self.write(cr, uid, ids, {'applicant_id': applicant_id}, context=context)
        else:
            if applicant.school_id and applicant.recruitment_degree_id:
                data['certificate_ids'] = [[0, False, {'school_id': applicant.school_id.id,
                                                       'recruitment_degree_id': applicant.recruitment_degree_id.id}]]
            data['office_id'] = applicant.post_job_id and applicant.post_job_id.office_id \
                                and applicant.post_job_id.office_id.id or ''
            data['country_id'] = applicant.country_id and applicant.country_id.id or ''
            data['first_name'] = applicant.first_name
            data['last_name'] = applicant.last_name
            data['name'] = "%s %s" % (applicant.last_name, applicant.first_name)
            data['gender'] = applicant.gender
            data['birthday'] = applicant.birthday
            data['note'] = applicant.note
            data['identification_no'] = applicant.identification_no
            data['mobile'] = applicant.mobile_phone
            data['phone'] = applicant.mobile_phone
            data['street'] = applicant.permanent_address
            data['email'] = applicant.email
            applicant_id = applicant_obj.create(cr, uid, data, context=context)
            self.write(cr, uid, ids, {'applicant_id': applicant_id}, context=context)
        attachment_obj = self.pool.get('ir.attachment')
        lst_cv = attachment_obj.search(cr, uid, [('res_model', '=', 'vhr.temp.applicant'), ('res_id', '=', applicant.id)], context=context)
        for item in attachment_obj.browse(cr, uid, lst_cv, context=context):
            if item.type == 'url':
                data_b64 = self.get_file_attachment(cr, item.url)
                if data_b64:                
                    data_att = {'datas': data_b64, 'datas_fname': item.datas_fname, 'name': item.name,
                                'res_model': 'hr.applicant', 'res_id': applicant_id, 'is_main': True}
                    attachment_obj.create(cr, uid, data_att)
            else:
                new_cv = attachment_obj.copy(cr, uid, item.id, {'name': item.name})
                attachment_obj.write(cr, uid, new_cv, {'res_model': 'hr.applicant', 'res_id': applicant_id, 'is_main': True})
        return True

    def action_reject_temp_applicant(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'reject'}, context=context)
        return True

    def action_get_attachment_tree_view(self, cr, uid, ids, context=None):
        # open attachments of job and related applicantions.
        model, action_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'base', 'action_attachment')
        action = self.pool.get(model).read(cr, uid, action_id, context=context)
        action['context'] = {'default_res_model': self._name, 'default_res_id': ids[0]}
        action['domain'] = str(['&', ('res_model', '=', self._name), ('res_id', 'in', ids)])
        return action

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            for obj in self.browse(cr, uid, ids, context=context):
                if obj.applicant_id:
                    raise osv.except_osv('Validation Error !',
                                         'You cannot delete the record(s) which reference to others !')
            res = super(vhr_temp_applicant, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res

    def copy(self, cr, uid, id, default=None, context=None):
        default = {} if default is None else default.copy()
        default.update({
            'applicant_id': False,
        })
        return super(vhr_temp_applicant, self).copy(cr, uid, id, default=default, context=context)
    
    def cron_suggest_candidate(self, cr, uid, context=None):
        log.info('RR Start : cron_suggest_candidate()')
        lst_domain = [('state','=','draft'),('program_event_id.code','=', 'RECRUITMENT')]
        lst_temp = self.search(cr, uid, lst_domain, context=context)
        for item in self.browse(cr, uid , lst_temp, context=context):            
            suggest_ids = self.search_candidate(cr, uid, item.email, item.name, item.birthday, item.gender)
            if suggest_ids and not item.applicant_suggest_id:
                self.write(cr, uid, item.id, {'applicant_suggest_id': suggest_ids[0]})
        log.info('RR End : cron_suggest_candidate() end')
        return True
    
    def cron_get_cv_and_send_email(self, cr, uid, context=None):
        log.info('RR Start : cron_get_cv_and_send_email()')
        m = self.pool.get('ir.model.data')
        attachment_obj = self.pool.get('ir.attachment')
        cron_id = m.get_object(cr, uid, 'vhr_recruitment', 'vhr_rr_get_cv_from_career').id
        if cron_id:
            cron_obj = self.pool.get('ir.cron').browse(cr, SUPERUSER_ID, cron_id)
            interval_number = cron_obj.interval_number
            interval_unit = cron_obj.interval_type
            if interval_unit and interval_unit=='hours' and interval_number:
                current_time = datetime.today()
                last_time = current_time - relativedelta(hours = interval_number)
                # lấy danh sách candidate trong khoảng thời gian
                lst_temp_cands = self.search(cr, uid, [('create_date', '>=', str(last_time)), ('create_date', '<=', str(current_time))])
                # lấy danh sách CV của candidate với type là url
                lst_attachments = attachment_obj.search(cr, uid, [('res_model','=',self._name),('type','=','url'),\
                                                                  ('res_id', 'in', lst_temp_cands)])
                # lấy danh sách file về
                for item in attachment_obj.browse(cr, uid, lst_attachments, context=context):
                    try:
                        data_b64 = self.get_file_attachment(cr, item.url)
                        if data_b64:                
                            data_att = {'datas':data_b64, 'datas_fname': item.datas_fname, 'name': item.name,
                                        'res_model': self._name, 'res_id': item.res_id, 'is_main': True}
                            attachment_obj.create(cr, uid, data_att)                
                            cr.execute("delete from ir_attachment where id = %s"%(item.id))
                            cr.commit()
                    except Exception as e:
                        log.exception(e)
                for item in self.browse(cr, uid, lst_temp_cands):
                    email_template_name = item.program_event_id and item.program_event_id.temp_email_for_rr_id\
                                        and item.program_event_id.temp_email_for_rr_id.name or False
                    lst_cv_ids = []
                    for cv in item.cv_ids:
                        if cv.type == 'binary':
                            lst_cv_ids.append(cv.id)
                    if email_template_name and lst_cv_ids:
                        self.recruitment_send_email(cr, uid,email_template_name, self._name, item.id, lst_cv_ids)
        log.info('RR End : cron_get_cv_and_send_email()')
        return True

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if not context:
            context = {}
        if not isinstance(args, list):
            args = []
        if context.get('domain_gift_id', False):
            args += [('gift_id', '=', context['domain_gift_id']), ('is_spin', '=', True)]
            args = [i for i in args if i[0] not in ('state', 'program_event_id.program_id')]
            if 'search_default_filter_draft' in context:
                del context['search_default_filter_draft']
            if 'search_default_group_by_program_event_id' in context:
                del context['search_default_group_by_program_event_id']

        app_ids = super(vhr_temp_applicant, self).search(cr, uid, args, offset, limit, order, context, count)
        return app_ids

    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False,
                   lazy=True):
        if not context:
            context = {}
        if not isinstance(domain, list):
            domain = []
        if not orderby:
            orderby = self._order
        if context.get('domain_gift_id', False):
            domain += [('gift_id', '=', context['domain_gift_id']), ('is_spin', '=', True)]
            domain = [i for i in domain if i[0] not in ('state', 'program_event_id.program_id')]
            if 'search_default_filter_draft' in context:
                del context['search_default_filter_draft']
            if 'search_default_group_by_program_event_id' in context:
                del context['search_default_group_by_program_event_id']

        res = super(vhr_temp_applicant, self).read_group(cr, uid, domain, fields, groupby, offset, limit,
                                                         context, orderby, lazy)
        return res

vhr_temp_applicant()
