    # -*-coding:utf-8-*-
import logging
import unicodedata
from openerp.osv import osv, fields
from openerp import tools
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from lxml import etree
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from vhr_recruitment_constant import RE_ERP_Confirm, RE_ERP_Thank_Applicant, \
    RE_TALENT_AA, RE_TALENT_UI, RE_TALENT_UP, RE_ERP_DUPPLICATE
from vhr_recruitment_abstract import vhr_recruitment_abstract,\
    HRBP, RECRUITER, MANAGER, ADMIN, CANDB_ROLE, COLLABORATER, COLLABORATER2, RRHRBP

log = logging.getLogger(__name__)

OPENING = 'opening'
PROCESSING = 'processing'
OFFERED = 'offered'
EMPLOYEE = 'employee'
BLACKLIST = 'blacklist'

STATE_APP = [
    (OPENING, 'Opening'),
    (PROCESSING, 'Processing'),
    (OFFERED, 'Offered'),
    (EMPLOYEE, 'Employee'),
    (BLACKLIST, 'Blacklist')
]

class vhr_applicant(osv.osv, vhr_recruitment_abstract):
    _name = 'hr.applicant'
    _inherit = 'hr.applicant'
    _description = 'VHR Applicant'

    def function_quickadd_tags_categ_ids(self, cr, uid, context=None):
        cat_obj = self.pool.get('hr.applicant_category')
        ids = cat_obj.search(cr, uid, [('available','=', True)], context=context)
        return cat_obj.name_get(cr, uid, ids, context=context)

    def function_quickadd_tags_school_id(self, cr, uid, context=None):
        school = self.pool.get('vhr.school')
        ids = school.search(cr, uid, [], context=context)
        return school.name_get(cr, uid, ids, context=context)

    def function_quickadd_tags_yob(self, cr, uid, context=None):
        year = 1950
        list_year = []
        for item in range(200):
            list_year.append((year + item, str(year + item)))
        return list_year

    def _get_image(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = tools.image_get_resized_images(obj.image)
        return result

    def _set_image(self, cr, uid, id, name, value, args, context=None):
        return self.write(cr, uid, [id], {'image': tools.image_resize_image_big(value)}, context=context)

    def onchange_name(self, cr, uid, ids, first_name, last_name):
        res = ''
        if first_name and last_name:
            res = '%s %s' % (last_name.strip(), first_name.strip())
        return {'value': {'name': res}}

    def onchange_date(self, cr, uid, ids, birthday, context=None):
        if birthday:
            current_birthday = None
            if ids:
                current_birthday = self.browse(cr, uid, ids[0], context=context).birthday
            birthday = datetime.strptime(birthday, DEFAULT_SERVER_DATE_FORMAT)
            today = datetime.today()
            age = relativedelta(today, birthday).years
            age_config = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr.rr.age.limit.config')
            age_config = int(age_config) if age_config else 18
            if age < age_config:
                warning = {'title': 'User Alert!', 'message': 'Candidate must be older than 17 years old'}
                return {'value': {'birthday': current_birthday}, 'warning': warning}
        return {'value': {}}

    def on_change_source_type_id(self, cr, uid, ids, source_type_id, context=None):
        value = {}
        value['source_id'] = False
        return {'value': value}

    def on_change_partner_country_id(self, cr, uid, ids, partner_country_id, context=None):
        value = {'partner_country_code':''}
        source_obj = self.pool.get('res.country')
        if partner_country_id:
            source = source_obj.browse(cr, uid, partner_country_id, context=context).code
            value['partner_country_code'] = source
        return {'value': value}

    def on_change_source_id(self, cr, uid, ids, source_id, context=None):
        value = {}
        source_obj = self.pool.get('hr.recruitment.source')
        if source_id:
            source = source_obj.browse(cr, uid, source_id, context=context)
            value['source_code'] = source.code
            if source.code not in ('ERP','SR-100'):
                value['recommender_id'] = False
                value['is_erp_mail'] = False
            else:
                value['is_erp_mail'] = True
            if source.auto_send_email:
                value['auto_send_email'] = True
            else:
                value['auto_send_email'] = False
        return {'value': value}

    def on_change_ex_employee(self, cr, uid, ids, ex_employee, email, mobile, name, birthday, gender):
        value = {}
        emp_obj = self.pool.get('hr.employee')
        if not ex_employee:
            value['emp_id'] = False
        if ex_employee and name and birthday and gender:
            name = " ".join(name.split())
            mobile = mobile or ''
            email = email or ''
            emp_search = emp_obj.search(cr, uid, [('name', '=', name),
                                                  ('gender', '=', gender),
                                                  ('birthday', '=', birthday),
                                                  '|',
                                                  ('mobile', '=', mobile),
                                                  ('email', '=', email)],
                                        context={'active_test': False})
            if emp_search:
                value['emp_id'] = emp_search[0]
        return {'value': value}

    def on_change_emp_id(self, cr, uid, ids, emp_id, context=None):
        value = {}
        emp_obj = self.pool.get('hr.employee')
        if emp_id:
            value['login'] = emp_obj.browse(cr, uid, emp_id, context=context).login
        return {'value': value}


    def on_change_erp_dupplicate(self, cr, uid, ids, erp_dupplicate):
        value = {}
        if not erp_dupplicate:
            value['emp_erp_dupplicate_id'] = False
        return {'value': value}
    
    def open_new_tab(self, cr, uid, ids, context=None):
        if not isinstance(ids, list):
            ids = ids[0]
        url = '/web#id=%s&view_type=form&model=hr.applicant' % (ids[0])
        return {
                    'type'     : 'ir.actions.act_url',
                    'target'   : '_blank',
                    'url'      : url
               }

    def onchange_is_talent(self, cr, uid, ids, is_talent):
        value = {}
        if ids:
            if is_talent:
                value['talent_state'] = 'talent'
            else:
                value['talent_state'] = 'untalent'
        else:
            if is_talent:
                value['talent_state'] = 'talent'
            else:
                value['talent_state'] = 'normal'
        return {'value': value}

    def change_state_talent(self, cr, uid, ids, context=None):
        return True

    def view_talent_profile(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        view_type = context.get('VIEW_TYPE', 'form')
        view_id = context.get('VIEW_ID', '')
        view_name = context.get('VIEW_NAME', '')
        target = context.get('TARGET', 'new')
        res_model = context.get('MODEL', self._name)
        res_id = False
        try:
            view_module = view_id.split(".")
            res_id = ids[0]
            return {
                'name': view_name,
                'view_type': view_type,
                'view_mode': 'form',
                'view_id': self.pool.get('ir.model.data').get_object_reference(cr, uid, view_module[0], view_module[1])[1],
                'res_model': res_model,
                'context': context,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': target,
                'res_id': res_id,
                }
        except ValueError:  # ignore if views are missing
            log.error('VHR.APPLICANT : can not search view')
            pass
        return True

    def _get_default_country(self, cr, uid, context=None):
        m = self.pool.get('res.country')
        lst = m.search(cr, uid, [('code','=','VN')], context=context)
        if lst:
            return lst[0]
        return False

    def _get_applicant_job(self, cr, uid, ids, fields, args, context=None):
        result={}
        for item in self.browse(cr, uid, ids, context=context):
            code = ''
            for app_inter in item.applicant_job_ids:
                if not code:
                    code = app_inter.job_code
                else:
                    if app_inter.job_code:
                        code = code + ',' + app_inter.job_code
            result[item.id] = code
        return result

    def _get_year_of_birth(self, cr, uid, ids, fields, args, context=None):
        result={}
        for item in self.browse(cr, uid, ids, context=context):
            birthday = item.birthday
            result[item.id] = False
            if birthday:
                birthday = datetime.strptime(birthday, DEFAULT_SERVER_DATE_FORMAT)
                result[item.id] = birthday.year
        return result

    def write_change_state(self, cr, uid, ids, new_state, comment="", context=None):
        if not isinstance(ids, list):
            ids = [ids]
        state_change_obj = self.pool['vhr.state.change']
        for app_obj in self.browse(cr, uid, ids, context=context):
            state_vals = {}
            state_vals['old_state'] = app_obj.state
            state_vals['new_state'] = new_state
            state_vals['model'] = self._name
            state_vals['res_id'] = app_obj.id
            state_vals['comment'] = comment
        state_change_obj.create(cr, uid, state_vals)
        self.write(cr, uid, ids, {'state': new_state})
        return True

    _columns = {
        'name': fields.char('Name', size=128, required=True),
        'name_eng': fields.char('Name Eng', size=128),
        'partner_id': fields.many2one('res.partner', domain=[('is_company', '=', False)], string="Contact"),
        'street': fields.related('partner_id', 'street', type='char', string="Street"),
        'city_id': fields.related('partner_id', 'city', type='many2one', relation="res.city", string="City"),
        'district_id': fields.related('partner_id', 'district_id', type='many2one', relation="res.district",
                                      string="District"),
        'partner_country_code': fields.related('partner_id', 'country_id', 'code', type='char', relation="res.country",
                                             string="Country Code"),
        'partner_country_id': fields.related('partner_id', 'country_id', type='many2one', relation="res.country",
                                             string="Country"),
        'use_parent_address': fields.related('partner_id', 'use_parent_address', type='boolean',
                                             string='Use Company Address'),

        'temp_address': fields.related('partner_id', 'temp_address', type='char', string="Temp address"),
        'temp_city_id': fields.related('partner_id', 'temp_city_id', type='many2one', relation="res.city",
                                       string="Temp City"),
        'temp_district_id': fields.related('partner_id', 'temp_district_id', type='many2one', relation="res.district",
                                           string="Temp District"),
        'phone': fields.related('partner_id', 'phone', type='char', string="Phone"),
        'mobile': fields.related('partner_id', 'mobile', type='char', string="Mobile"),
        'email': fields.related('partner_id', 'email', type='char', string="Email"),
        'skype': fields.char('Skype', size=128),

        'last_name': fields.char('Last name', size=32),
        'first_name': fields.char('First name', size=32),
        'birthday': fields.date('Date of birth'),
        'yob': fields.function(_get_year_of_birth, method=True, type='char', string='Yob', store=True),
        'gender': fields.selection([('male', 'Male'), ('female', 'Female')], 'Gender'),

        'image': fields.binary("Photo",
                               help="This field holds the image used as photo for the employee, limited to 1024x1024px."),
        'image_medium': fields.function(_get_image, fnct_inv=_set_image,
                                        string="Medium-sized photo", type="binary", multi="_get_image",
                                        store={
                                            'hr.applicant': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
                                        },
                                        help="Medium-sized photo of the employee. It is automatically " \
                                             "resized as a 128x128px image, with aspect ratio preserved. " \
                                             "Use this field in form views or some kanban views."),
        'image_small': fields.function(_get_image, fnct_inv=_set_image,
                                       string="Small-sized photo", type="binary", multi="_get_image",
                                       store={
                                           'hr.applicant': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
                                       },
                                       help="Small-sized photo of the employee. It is automatically " \
                                            "resized as a 64x64px image, with aspect ratio preserved. " \
                                            "Use this field anywhere a small image is required."),

        'country_id': fields.many2one('res.country', 'Nationality'),

        'marital': fields.selection([('single', 'Single'), ('married', 'Married')], 'Marital Status'),
        'recommender_id': fields.many2one('hr.employee', 'Recommender'),
        'job_type_id': fields.many2one('vhr.dimension', 'Job type', ondelete='restrict',
                                       domain=[('dimension_type_id.code', '=', 'JOB_TYPE'), ('active', '=', True)]),
        'willing_location': fields.boolean('Willing location'),
        'office_id': fields.many2one('vhr.office', 'Location'),
        'title_ids': fields.many2many('vhr.job.title', 'job_title_applicant_rel', 'applicant_id', 'title_id', 'Titles Apply'),
        'apply_date': fields.date('Apply date'),
        'note': fields.text('Note'),
        'note_erp': fields.text('Note for ERP'),
        'religion_id': fields.many2one('vhr.dimension', 'Religion', ondelete='restrict',
                                       domain=[('dimension_type_id.code', '=', 'RELIGION'), ('active', '=', True)]),

        'nation_id': fields.many2one('vhr.dimension', 'Ethnic', ondelete='restrict',
                                     domain=[('dimension_type_id.code', '=', 'NATION'), ('active', '=', True)]),
        'identification_no': fields.char('Identification No', size=32),
        'certificate_ids': fields.one2many('vhr.certificate.info', 'applicant_id', string='Certificates/Degree'),
        # change to function or related
        'home_phone': fields.related('partner_id', 'phone', type='char', relation='res.partner', string='Home phone'),
        'source_id': fields.many2one('hr.recruitment.source', 'Source', domain="[('source_type_id','=',source_type_id)]"),
        'source_type_id': fields.many2one('vhr.recruitment.source.type', 'Source type'),
        'source_code': fields.related('source_id', 'code', type='char', relation='hr.recruitment.source',
                                      string='Source Code'),
        'state': fields.selection(STATE_APP, string="State"),
        'never_recruit': fields.boolean('Never Recruit Again'),
        'never_recruit_comment': fields.text('Comment'),
        'working_background': fields.one2many('vhr.working.background', 'applicant_id', 'Working Background'),
        #audittrail
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'History', \
                              domain=[('object_id.model', '=', _name),
                                      ('field_id.name', 'not in', ['write_date', 'audit_log_ids'])]),
        #required used
        'ex_employee': fields.boolean('Ex-employee'),
        'login': fields.related('emp_id','login', type='char', string='Account'),
        'cv_ids': fields.one2many('ir.attachment', 'res_id', 'Attachment', \
                              domain=[('res_model', '=', _name)],
                              context={'FROM_VIEW':'APPLICANT'}),
        #state log
        'state_log_ids': fields.one2many('vhr.state.change', 'res_id', 'History', \
                              domain=[('model', '=', _name)]),
        'description': fields.text('CV Content'),
        'test_result_ids': fields.one2many('vhr.test.result', 'candidate_id', 'Test Result'),
        'applicant_job_ids': fields.one2many('vhr.job.applicant', 'applicant_id', 'Inteviews'),
        'applicant_job_name': fields.function(_get_applicant_job, type='char',string='Request Code'),
        'current_salary': fields.float('Current salary', digits=(12,3)),
        'expected_salary': fields.float('Expected salary', digits=(12,3)),
        'total_income': fields.float('Total income', digits=(12,0)),
        'com_group_id': fields.many2one('vhr.company.group', 'Company group'),
        #'is_key_student': fields.boolean('Key student'),
        'key_student': fields.selection([('yes', 'Yes'), ('no', 'No')], 'Key student'),
        #'collaborator': fields.boolean('Collaborator'),
        'collaborator': fields.selection([('yes', 'Yes'), ('no', 'No')], 'Collaborator'),
        'write_uid': fields.many2one('res.users', 'Modified User'),
        # send mail erp voi big boss gui CV ko muon nhan email
        'is_erp_mail': fields.boolean('Send mail ERP'),
        # talent pool
        'is_talent': fields.boolean('Talent'),
        'in_charge_student': fields.many2one('hr.employee','Talent_In charge person'),
        'in_charge_talent': fields.many2one('hr.employee','Talent_In charge person'),
        'note_for_talent': fields.text('Note Talent'),
        'talent_state': fields.selection([('normal', 'Normal'),
                                          ('talent', 'Talent'),
                                          ('untalent', 'UnTalent'),], 'Talent State', select=True, readonly=True),
        'talent_award_ids': fields.one2many('vhr.rr.talent.award', 'applicant_id', 'Talent_Awards'),
        'talent_communi_ids': fields.one2many('vhr.rr.talent.communi', 'applicant_id', 'Talent_Communications'),
        'talent_recom_ids': fields.one2many('vhr.rr.talent.recom', 'applicant_id', 'Talent_Recommendations'),
        'talent_expertise_ids': fields.many2many('vhr.rr.talent.expertise', 'applicant_expertise_rel', 'applicant_id',
                                                 'expertise_id', 'Talent_Expertise'),
        'note_ids': fields.one2many('vhr.note', 'res_id', 'Notes', domain=[('model', '=', _name)]),
        'benefits': fields.char('Benefit', size=128),
        'is_staff_movement': fields.boolean('Staff Movement'),
        'contact_ids': fields.one2many('vhr.candidate.contact', 'candidate_id', 'Contacts'),

        'auto_send_email': fields.boolean('Auto Send Email'),

        'job_track_ids': fields.many2many('vhr.applicant.job.track', 'job_track_hr_applicant_rel', 'applicant_id', 'job_track_id', 'Job Track'),
        'option_apply_date': fields.date('Option Apply date'),
        'erp_dupplicate': fields.boolean('ERP Duplicate'),
        'emp_erp_dupplicate_id': fields.many2one('hr.employee', 'ERP Duplicate'),
        'recommender_outsiderp': fields.char('Recommender ID', size=128),
        'recommender_email': fields.char('Recommender Email', size=128),
        'is_potential': fields.boolean('Is Potential'),

    }

    _defaults = {
        'state': 'opening',
        'marital': 'single',
        'ex_employee': False,
        'collaborator': False,
        'country_id': _get_default_country,
        'partner_country_id': _get_default_country,
        'apply_date': str(date.today()),
        'birthday': str(date.today()- relativedelta(years = 28)),
        'is_erp_mail': False,
        'talent_state': 'normal',
        'option_apply_date': str(date.today()),
    }
    _order = 'write_date desc'

    def _check_email_exist(self, cr, uid, email, name, gender, birthday, ids=None, context=None):
        if email:
            partner_obj = self.pool['res.partner']
            lst_email = partner_obj.search(cr, uid, [('email', '=ilike', email.strip())], context=context)
            if lst_email:
                raise osv.except_osv('Validation Error !', 'Email is already exist!')
        if name and gender and birthday:
            args = ['&', '&', ('name', '=ilike', name.strip()), ('gender', '=', gender.strip()), ('birthday', '=', birthday)]
            if ids:
                args = ['&', '&', '&', ('name', '=ilike', name.strip()), ('gender', '=', gender.strip()),
                        ('birthday', '=', birthday), ('id', 'not in', ids)]
            lst_applicant = self.search(cr, uid, args, context=context)
            if lst_applicant:
                raise osv.except_osv('Validation Error !', 'Name, Gender, DOB is already exist!')
        return True

    def check_applicant_exist(self, cr, uid, email=None, name=None, gender=None, birthday=None, ids=None, context=None):
        result = []
        if email:
            args = [('email', '=ilike', email.strip())]
            if ids:
                args = [('email', '=ilike', email.strip()), ('id', 'not in', ids)]
            result = self.search(cr, uid, args, context=context)
        if name and gender and birthday:
            new_name = u'%s' % (name)
            new_name = new_name.replace(u"Đ", "D") if new_name else ''
            name_eng = unicodedata.normalize('NFKD', new_name).encode('ascii', 'ignore').lower()
            args = ['&', '&', ('name_eng', '=ilike', name_eng), ('gender', '=', gender.strip()), ('birthday', '=', birthday)]
            if ids:
                args = ['&', '&', '&', ('name_eng', '=ilike', name_eng), ('gender', '=', gender.strip()),
                        ('birthday', '=', birthday), ('id', 'not in', ids)]
            result_temp2 = self.search(cr, uid, args, context=context)
            result.extend(result_temp2)
        return list(set(result))

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]
        # Begin validate
        if vals.get('email', False) or vals.get('name', False) or vals.get('gender', False) or vals.get('birthday', False):
            for app_obj in self.browse(cr, uid, ids, context=context):
                name = vals['name'] if vals.get('name', False) else app_obj.name
                gender = vals['gender'] if vals.get('gender', False) else app_obj.gender
                birthday = vals['birthday'] if vals.get('birthday', False) else app_obj.birthday
                email = vals['email'] if vals.get('email', False) else app_obj.email
                list_cand = self.check_applicant_exist(cr, uid, email, name, gender, birthday, [app_obj.id])
                if list_cand:
                    raise osv.except_osv('Validation Error !', 'Candidate is already exist!')
        # End validate
        applicant = self.read(cr, uid, ids[0], ['partner_id', 'name'], context=context)
        # Create partner_id if dont have partner_id
        if not applicant.get('partner_id', False):
            if not vals.get('name', False):
                vals['name'] = applicant.get('name', '')
            vals = self.create_partner(cr, uid, vals, context=context)
        elif vals.get('name', False):
            # update name_eng
            new_name = u'%s' % (vals['name'])
            new_name = new_name.replace(u"Đ", "D") if new_name else ''
            name_eng = unicodedata.normalize('NFKD', new_name).encode('ascii', 'ignore').lower()
            vals['name_eng'] = name_eng
            # write name in res_partner
            self.pool.get('res.partner').write(cr, uid, applicant['partner_id'][0], {'name': vals['name']})

        if 'expected_salary' in vals or 'current_salary' in vals:
            if vals.has_key('expected_salary')  and vals['expected_salary'] == 0 and type( vals['expected_salary'])==int:
                vals['expected_salary'] = 0.001
            if vals.has_key('current_salary') and vals['current_salary'] == 0 and type( vals['current_salary'])==int:
                vals['current_salary'] = 0.001

        if 'never_recruit' in vals:
            if vals['never_recruit']:
                vals['state'] = 'blacklist'
                state_vals = {'new_state': 'blacklist'}
            else:
                vals['state'] = 'opening'
                vals['never_recruit_comment'] = ''
                state_vals = {'new_state': 'opening'}
            for app_obj in self.browse(cr, uid, ids, context=context):
                state_change_obj = self.pool['vhr.state.change']
                state_vals['old_state'] = app_obj.state
                state_vals['model'] = self._name
                state_vals['res_id'] = app_obj.id
                state_vals['comment'] = vals['never_recruit_comment'] if 'never_recruit_comment' in vals else ''
                state_change_obj.create(cr, uid, state_vals)
        result = super(vhr_applicant, self).write(cr, uid, ids, vals, context=context)
        if vals.get('is_erp_mail') and vals.get('recommender_id'):
            self.recruitment_send_email(cr, uid, RE_ERP_Confirm, self._name, ids[0], context=context)
        # Update job tracks of related email subcribes
        if vals.get('emp_erp_dupplicate_id'):
            self.recruitment_send_email(cr, uid, RE_ERP_DUPPLICATE, self._name, ids[0], context=context)
        if not context.get('subcribes_update', False) and vals.get('job_track_ids'):
            ctx = context.copy()
            ctx.update({'candidate_update': True})
            candidates = self.browse(cr, uid, ids, context=ctx)
            vhr_email_news_pool = self.pool['vhr.email.news']
            for candidate in candidates:
                vhr_email_news_ids = vhr_email_news_pool.search(cr, uid, [('candidate_id', '=', candidate.id)], context=ctx)
                if vhr_email_news_ids:
                    job_track_ids = [job_track.id for job_track in candidate.job_track_ids]
                    vhr_email_news_pool.write(cr, uid, vhr_email_news_ids, {'job_track_ids': [(6, False, job_track_ids)]}, context=ctx)
        return result

    def create(self, cr, uid, vals, context=None):
        email = vals.get('email', '')
        name = vals.get('name', '')
        gender = vals.get('gender', '')
        dob = vals.get('birthday', '')
        if name:
            name = " ".join(name.split())
            vals['name'] = name
            new_name = u'%s' % (name)
            new_name = new_name.replace(u"Đ", "D") if new_name else ''
            name_eng = unicodedata.normalize('NFKD', new_name).encode('ascii', 'ignore').lower()
            vals['name_eng'] = name_eng
            list_cand = self.check_applicant_exist(cr, uid, email, name, gender, dob)
            if list_cand:
                raise osv.except_osv('Validation Error !', 'Candidate is already exist!')
            # Create partner before create candidate
            vals = self.create_partner(cr, uid, vals, context)            
        result =  super(vhr_applicant, self).create(cr, uid, vals, context=context)
        if vals.get('is_erp_mail') and vals.get('recommender_id'):
            self.recruitment_send_email(cr, uid, RE_ERP_Confirm, self._name, result, context=context)
        # Create email subcribes
        # self.create_email_subcribes(cr, uid, result, context=context)
        return result

    def validate_read(self, cr, uid, ids, context=None):
        '''
            - CAND_INTERVIEW : đọc từ màn hình view buổi phỏng vấn khi click candidate
            - APPLICANT: được truyền từ danh sách interview hoặc ds CV trong candidate
            - CAND_INTERVIEW : Thao tác từ vhr_job_applicant sẽ được thao tác
        '''
        if uid == 1:
            return True
        log.info('validate_read : %s'%(uid))
        if context is None: context = {}
        if context.get('FROM_VIEW') and (context.get('FROM_VIEW')=="CAND_INTERVIEW" or context.get('FROM_VIEW')=="APPLICANT")\
            or context.get('CAND_INTERVIEW'):
            return True

        roles = self.recruitment_get_group_array(cr, uid, uid, context)
        if ADMIN in roles or MANAGER in roles or CANDB_ROLE in roles or\
            RECRUITER in roles or HRBP in roles or COLLABORATER in roles or COLLABORATER2 in roles or RRHRBP in roles:
            return True

        if not isinstance(ids, list): ids = [ids]
        current_emp = self.pool.get('hr.employee').search(cr, uid, [('user_id.id', '=', uid)], context={'active_test': False})
        if current_emp:
            job_applicant_obj = self.pool['vhr.job.applicant']
            lst_data = job_applicant_obj.search(cr, uid,[('applicant_id','in',ids)])# có thể lọt key =))
            if lst_data:
                return job_applicant_obj.check_read_access(cr, uid, lst_data, context)
        return False

    def read(self, cr, user, ids, fields=None, context=None, load='_classic_read'):
        if context is None:
            context = {}
        # validate read
        result_check = self.check_read_access(cr, user, ids, context)
        if not result_check:
            raise osv.except_osv('Validation Error !', 'You don’t have permission to access this data !')
        # end validate read
        return super(vhr_applicant, self).read(cr, user, ids, fields, context, load)

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context = {}
        if context.get('show_appli') and context.get('active_id'):
            job_id = context.get('active_id') if context.get('active_id') else False
            if job_id:
                lst_applicant_ids = []
                job_applicant = self.pool.get('vhr.job.applicant')
                job_applicant_ids = job_applicant.search(cr, uid, [('job_id', '=', int(job_id))])
                for job_app_item in job_applicant.read(cr, uid, job_applicant_ids, ['applicant_id']):
                    lst_applicant_ids.append(job_app_item.get('applicant_id')[0])
                args.append(('id', 'not in', lst_applicant_ids))
        if count==False and context.get('template_quickadd') and context.get('template_quickadd')=='ApplicantSeach':
            category_obj = self.pool.get('hr.applicant_category')
            for item in args:
                if isinstance(item, list) and len(item) == 3 and item[0]=='description':
                    category_obj.update_key_word(cr, uid, item[2])
        return super(vhr_applicant, self).search(cr, uid, args, offset, limit, order, context, count)

    def create_partner(self, cr, uid, vals, context=None):
        vals_partner = {'name': vals['name']}
        vals_partner['street'] = vals.get('street', False)
        vals_partner['city'] = vals.get('city_id', False)
        vals_partner['district_id'] = vals.get('district_id', False)
        vals_partner['country_id'] = vals.get('partner_country_id', False)
        vals_partner['temp_address'] = vals.get('temp_address', False)
        vals_partner['temp_city_id'] = vals.get('temp_city_id', False)
        vals_partner['temp_district_id'] = vals.get('temp_district_id', False)
        vals_partner['phone'] = vals.get('phone', '')
        vals_partner['mobile'] = vals.get('mobile', '')
        vals_partner['email'] = vals.get('email', '')
        partner_id = self.pool.get('res.partner').create(cr, uid, vals_partner, context)
        if partner_id:
            vals['partner_id'] = partner_id

        return vals

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        if 'match_cv' in context:
            job_applicant_pool = self.pool.get('vhr.job.applicant')
            job_applicant_ids = job_applicant_pool.search(cr, uid, [('state', '=', 'interview')], context=context)
            applicant_ids = []
            for job_applicant in job_applicant_pool.browse(cr, uid, job_applicant_ids, context=context):
                if job_applicant.applicant_id:
                    applicant_ids.append(job_applicant.applicant_id.id)
            args_new = [('id', 'not in', applicant_ids)] + args
            ids = self.search(cr, uid, args_new, context=context)
            return self.name_get(cr, uid, ids, context=context)

        else:
            args_new = ['|', ('first_name', operator, name), ('last_name', operator, name)] + args
            ids = self.search(cr, uid, args_new, context=context)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(vhr_applicant, self).name_search(cr, uid, name, args, operator, context, limit)

    def get_formview_action(self, cr, uid, id, context=None):
        # Luannk inherit truyen target xuong ho tro (new, current,....)
        """ Return an action to open the document. This method is meant to be
            overridden in addons that want to give specific view ids for example.
            :param int id: id of the document to open
        """
        if context is None:
            context = {}
        view_id = self.get_formview_id(cr, uid, id, context=context)
        target = context.get('target', 'current')
        initial_mode = context.get('initial_mode', 'edit')
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_type': 'form',
            'view_mode': 'form',
            'views': [(view_id, 'form')],
            'target': target,
            'res_id': id,
            'initial_mode': initial_mode,
            'context': context
            }

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_applicant, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res

    def fields_view_get(self, cr, user, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if context is None:
            context = {}
        res = super(vhr_applicant, self).fields_view_get(cr, user, view_id, view_type, context, toolbar=toolbar,
                                                  submenu=submenu)
        if view_type == 'form':
            doc = etree.XML(res['arch'])
            #chặn quyền edit form
            roles = self.recruitment_get_group_array(cr, user, user)
            if not (RECRUITER in roles or COLLABORATER in roles or COLLABORATER2 in roles):
                for node in doc.xpath("//form"):
                    node.set('edit', 'false')
            res['arch'] = etree.tostring(doc)
        return res

    def copy(self, cr, uid, id, default=None, context=None):
        default = {} if default is None else default.copy()
        if id:
            name = self.browse(cr, uid, id, context=context).name + '(copy)' if self.browse(cr, uid, id, context=context).name else '(copy)'
            first_name = self.browse(cr, uid, id, context=context).first_name + '(copy)' if self.browse(cr, uid, id, context=context).first_name else '(copy)'
        default.update({
            'name': name,
            'first_name': first_name,
            'applicant_job_ids': [],
            'state_log_ids': []
        })
        return super(vhr_applicant, self).copy(cr, uid, id, default=default, context=context)

    def cron_send_mail_info_for_candidate(self, cr, uid, day_send, context=None):
        log.info('VHR RR cron_send_mail_info_for_candidate: Start Send email for candidate')
        
        # Check how many weekend days between from_date and to_date
        from_date = date.today() - relativedelta(days = day_send + 1)
        to_date = date.today()
        daygenerator = (from_date + relativedelta(days = x + 1) for x in xrange((to_date - from_date).days))
        weekend_day = sum(1 for day in daygenerator if (day.weekday() > 4))
        
        day_send = date.today() - relativedelta(days = day_send + weekend_day)
        search_erp = [('recommender_id', '!=', False), ('is_erp_mail', '=', True),
                      ('source_id.code', '=', 'ERP'), ('apply_date', '=', day_send),('state', '=', 'opening')]
        lst_app = self.search(cr, uid, search_erp, context=context)
        for item in self.browse(cr, uid, lst_app, context=context):
            if not item.applicant_job_ids:
                self.recruitment_send_email(cr, uid, RE_ERP_Thank_Applicant, self._name, item.id, context=context)
        log.info('VHR RR cron_send_mail_info_for_candidate: End Send email for candidate')      
        return True

    def cron_remind_update_talent_information(self, cr, uid, delta_date_60,delta_date_61,delta_date_62, context=None):
        log.info('VHR RR cron_remind_update_talent_information Start')
        lst_talent = []
        #last date is 60
        last_date_60 = date.today() - relativedelta(days = delta_date_60)
        last_date_60 = last_date_60.strftime('%Y-%m-%d')
        cr.execute('select hra.id as applicant_id from hr_applicant hra where hra.is_talent = %s \
                    and hra.write_date::date = %s and hra.in_charge_talent is not null',(True,last_date_60))
        for item_60 in cr.dictfetchall():
            lst_talent.append(item_60['applicant_id'])
        #last date is 61
        last_date_61 = date.today() - relativedelta(days = delta_date_61)
        last_date_61 = last_date_61.strftime('%Y-%m-%d')
        cr.execute('select hra.id as applicant_id from hr_applicant hra where hra.is_talent = %s \
                    and hra.write_date::date = %s and hra.in_charge_talent is not null',(True,last_date_61))
        for item_61 in cr.dictfetchall():
            lst_talent.append(item_61['applicant_id'])
        #last date is 62
        last_date_62 = date.today() - relativedelta(days = delta_date_62)
        last_date_62 = last_date_62.strftime('%Y-%m-%d')
        cr.execute('select hra.id as applicant_id from hr_applicant hra where hra.is_talent = %s \
                    and hra.write_date::date = %s and hra.in_charge_talent is not null',(True,last_date_62))
        for item_62 in cr.dictfetchall():
            lst_talent.append(item_62['applicant_id'])
        #Send email write date as 60,61,62
        for item in lst_talent:
            self.recruitment_send_email(cr, uid, RE_TALENT_UI, self._name, item, context=context)
        log.info('VHR RR cron_remind_update_talent_information End')
        return True

    def cron_remind_update_talent_pool(self, cr, uid, day_send, context=None):
        log.info('VHR RR cron_remind_update_talent_pool Start')
        current_date = date.today()
        if current_date.day == day_send:
            lst_recruiter = self.search(cr, uid, [('name','!=',None)], limit=1)
            self.recruitment_send_email(cr, uid, RE_TALENT_UP, self._name, lst_recruiter[0], context=context)
        log.info('VHR RR cron_remind_update_talent_pool End')
        return True

    def get_applicant_skill(self, cr, uid, cv_content):
        count_config = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr.rr.search.count.skill')
        count_config = int(count_config) if count_config else 50
        category_obj = self.pool.get('hr.applicant_category')
        lst_cate = category_obj.search(cr, uid, [('count_index', '>=', count_config)])
        categ_ids = []
        cv_content = cv_content.lower()
        if lst_cate:
            lst_cate = category_obj.read(cr, uid, lst_cate, ['name'])
            for cate in lst_cate:
                cate_name = cate.get('name').lower()
                if cate_name in cv_content:
                    categ_ids.append(cate.get('id'))
        return categ_ids

    def create_email_subcribes(self, cr, uid, applicant_id, context=None):
        if context is None:
            context = {}
        if not applicant_id:
            return False
        # create email subcribes only one time
        email_subcribes_pool = self.pool['vhr.email.news']
        related_email_subcribes_ids = email_subcribes_pool.search(cr, uid, [('candidate_id', '=', applicant_id)], context=context)
        if related_email_subcribes_ids:
            return False
        applicant = self.browse(cr, uid, applicant_id, context=context)
        if not applicant or applicant.state != OPENING:
            return False
        vals = {
            'name': applicant.name,
            'email': applicant.email,
            'candidate_id': applicant_id,
        }
        email_subcribes_id = email_subcribes_pool.create(cr, uid, vals, context=context)
        return email_subcribes_id

    def cron_send_email_applicant_apply_hrs(self, cr, uid, delta_date, context=None):
        if context is None:
            context = {}
        date_send = date.today() - relativedelta(days = delta_date)
        date_send = date_send.strftime('%Y-%m-%d')
        log.info('VHR RR: START send email to Applicant who apply to hrs base on Resource for Date: %s' % (date_send))
        applicant_ids = self.search(
            cr, uid, [('auto_send_email', '=', True),('state', '=', 'opening')],
            context=context)
        for item in self.browse(cr, uid, applicant_ids, context=context):
            apply_date = item.apply_date
            option_apply_date = item.option_apply_date
            if option_apply_date > apply_date:
                applicant_ids_option_date = self.search(cr, uid, [('id','=',item.id),('option_apply_date', '=', date_send)],context=context)
                for applicant_id_option in applicant_ids_option_date:
                    self.recruitment_send_email(cr, uid, 'RE_send_email_applicant_apply_hrs', self._name, applicant_id_option, context=context)
            else:
                applicant_ids_apply_date = self.search(cr, uid, [('id','=',item.id),('apply_date', '=', date_send)],context=context)
                for applicant_id in applicant_ids_apply_date:
                    self.recruitment_send_email(cr, uid, 'RE_send_email_applicant_apply_hrs', self._name, applicant_id, context=context)
       
        log.info('VHR RR: END send email to Applicant who apply to hrs base on Resource')

    def cron_update_offered_applicant(self, cr, uid, context=None):
        if context is None:
            context = {}
        log.info('VHR RR: START employee applicants after they left for date: %s' % (date.today()))
        cr.execute('''
            update hr_applicant
            set state = 'employee'
            where id in (
                select ha.id from hr_applicant ha
                left join hr_employee hr on hr.id = ha.emp_id
                left join hr_contract hrc on hrc.employee_id = hr.id
                where hrc.state='signed');
        ''')

        log.info('VHR RR: END employee applicants after they left for date: %s' % (date.today()))
    
    def cron_update_employee_applicant(self, cr, uid, context=None):
        if context is None:
            context = {}
        log.info('VHR RR: START opening applicants after they left for date: %s' % (date.today()))

        cr.execute('''
            update hr_applicant
            set state = 'opening'
            where id in (
                select ap.id
                from hr_applicant ap
                inner join hr_employee ee on ee.id = ap.emp_id
                inner join resource_resource rr on rr.id = ee.resource_id
                where rr.active = false and ap.state = 'employee');
        ''')

        log.info('VHR RR: END opening applicants after they left for date: %s' % (date.today()))
        
        
    def cron_update_applicant_ex_employee(self, cr, uid, context=None):
        if context is None:
            context = {}
        log.info('VHR RR: START ex employee applicants after they left for date: %s' % (date.today()))

        cr.execute('''
            Update hr_applicant set ex_employee = True
            where id in(
            select distinct ha.id from hr_applicant ha
            left join hr_employee hr on hr.id = ha.emp_id
            left join hr_contract hrc on hrc.employee_id = hr.id
            where hrc.state='signed' and ha.ex_employee = False);
            ''')

        log.info('VHR RR: END ex employee applicants after they left for date: %s' % (date.today()))
          
vhr_applicant()
