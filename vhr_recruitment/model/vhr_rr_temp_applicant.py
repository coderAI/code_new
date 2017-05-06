# -*-coding:utf-8-*-
import logging
from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.osv import osv, fields

SPECIALITY_DIMENSION_DOMAIN = [('dimension_type_id.code', '=', 'SPECIALITY'), ('active', '=', True)]

log = logging.getLogger(__name__)


class vhr_rr_temp_applicant(osv.osv):
    _name = 'vhr.rr.temp.applicant'
    _description = 'VHR RR Temp Applicant'
    
    def search_candidate(self, cr, uid, email=None, name=None, birthday=None, gender=None, context=None):
        result = []
        applicant_obj = self.pool.get('hr.applicant')
        if email:
            args = [('email', '=ilike', email.strip())]
            result = applicant_obj.search(cr, uid, args, context=context)
            if not result and name and birthday and gender:
                args = [('name', '=ilike', name.strip()), ('birthday', '=', birthday), ('gender', '=', gender)]
                result = applicant_obj.search(cr, uid, args, context=context)
        return result
    
    def onchange_date(self, cr, uid, ids, birthday):
        if birthday:
            birthday = datetime.strptime(birthday, DEFAULT_SERVER_DATE_FORMAT)
            today = datetime.today()
            age = relativedelta(today, birthday).years
            age_config = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr.rr.age.limit.config')
            age_config = int(age_config) if age_config else 18
            if age < age_config:
                warning = {'title': 'User Alert!', 'message': 'Temp Candidate must be older than 17 years old'}
                return {'value': {'birthday': None}, 'warning': warning}
        return {'value': {}}
    
    _columns = {
        'create_date': fields.datetime('Create date', readonly=True),
        'create_uid': fields.many2one('res.users', 'Created By', readonly=True),
        'last_name': fields.char('Last Name', size=128),
        'first_name': fields.char('First Name', size=128),
        'name': fields.char('Name', size=128),
        'birthday': fields.date('Date of birth'),
        'gender': fields.selection([('male', 'Male'), ('female', 'Female')], 'Gender'),
        'email': fields.char('Email', size=256),
        'mobile_phone': fields.char('Mobile Phone', size=32),
        'permanent_address': fields.text('Permanent Address'),
        'recruitment_source_id': fields.many2one('hr.recruitment.source', 'Source Event'),
        'recruitment_source_online_id': fields.many2one('vhr.recruitment.source.online', 'Source Online'),
        'speciality_id': fields.many2one('vhr.dimension', 'Speciality', ondelete='restrict',
                                         domain=SPECIALITY_DIMENSION_DOMAIN),  # Graduation
        'note': fields.text('Note'),
        'applicant_id': fields.many2one('hr.applicant', 'Candidate'),
        'state': fields.selection([('draft', 'Draft'), ('approved', 'Approved'), ('reject', 'Reject')], 'State'),
        'facebook_link': fields.char('Facebook', size=250),
        'applicant_suggest_id': fields.many2one('hr.applicant', 'Candidate Suggest'),
        'recruitment_suggest_source_id': fields.related('applicant_suggest_id', 'source_id', type='many2one',
                                                        relation='hr.recruitment.source', string='Source Suggest'),
    }

    _defaults = {
        'state': 'draft',
    }
    _order = 'id desc'
    
    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        if vals.get('first_name') and vals.get('last_name'):
            vals['name'] = "%s %s" % (vals['last_name'].strip(), vals['first_name'].strip())
        res_id = super(vhr_rr_temp_applicant, self).create(cr, uid, vals, context=context)
        return res_id

    def write(self, cr, uid, ids, values, context=None):
        if not isinstance(ids, list):
            ids = [ids]
        if values.get('first_name') and values.get('last_name'):
            values['name'] = "%s %s" % (values['last_name'], values['first_name'])
        elif values.get('first_name'):
            values['name'] = "%s %s" % (self.browse(cr, uid, ids[0], context=context).last_name, values['first_name'])
        elif values.get('last_name'):
            values['name'] = "%s %s" % (values['last_name'], self.browse(cr, uid, ids[0], context=context).first_name)
        return super(vhr_rr_temp_applicant, self).write(cr, uid, ids, values, context=context)
vhr_rr_temp_applicant()
