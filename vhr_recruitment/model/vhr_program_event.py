# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from dateutil import relativedelta

log = logging.getLogger(__name__)

PROGRAM_DIMENSION_DOMAIN = [('dimension_type_id.code', '=', 'DND_PROGRAM'), ('active', '=', True)]


class vhr_program_event(osv.osv):
    _name = 'vhr.program.event'
    _description = 'VHR Program Event'
    
    def onchange_source_type_id(self, cr, uid, ids, source_type_id, context=None):
        value = {'source_id': False}
        return {'value': value}
    
    def onchange_program_id(self, cr, uid, ids, program_id, context=None):
        value = {'recruitment_source_online_ids': []}
        if program_id:
            code = self.pool.get('vhr.dimension').browse(cr, uid, program_id, context=context).code
            if code and code != 'CANDIDATE':
                lst_source_onlines = self.pool.get('vhr.recruitment.source.online').search(cr, uid, [], context=context)
                value['recruitment_source_online_ids']= lst_source_onlines
        return {'value': value}
    
    _columns = {
        'image': fields.binary("Photo",
                               help="This field holds the image used as photo for the employee, limited to 1024x1024px."),
        'date_from': fields.date('Date From'),
        'date_to': fields.date('Date To'),
        'name': fields.char('Vietnamese Name', size=128),
        'name_en': fields.char('English Name', size=128),
        'code': fields.char('Code', size=128),
        'description': fields.text('Description Vietnamese'),
        'description_en': fields.text('Description English'),
        'popup_success': fields.text('Popup Success'),
        'popup_fail': fields.text('Popup Fail'),
        'popup_success_en': fields.text('Popup Success En'),
        'popup_fail_en': fields.text('Popup Fail En'),
        'active': fields.boolean('Active'),
        'has_job': fields.boolean('Has Job'),
        'email_cc': fields.text('Cc Email'),
        'position_ids': fields.one2many('vhr.event.job', 'event_id', 'Position'),
        'program_id': fields.many2one('vhr.program.recruitment', 'Program', ondelete='restrict'),  # Fresher, temp candidate, tour,Internship
        # change from 22/12/2014 : transfer to candidate with source and source type
        'source_id': fields.many2one('hr.recruitment.source', 'Source', domain="[('source_type_id','=',source_type_id)]"),
        'source_type_id': fields.many2one('vhr.recruitment.source.type', 'Source type'),
        'recruitment_source_ids': fields.many2many('hr.recruitment.source', 'event_recruitment_source_rel', 'event_id',
                                                   'source_id', string='Recruitment Source'),
        
        # change from 22/12/2014 : change from recruiter source to source online
        'recruitment_source_online_ids': fields.many2many('vhr.recruitment.source.online', 'event_recruitment_source_online_rel', 'event_id',
                                                   'source_id', string='Source Online'),
        'school_ids': fields.many2many('vhr.school', 'event_vhr_school_rel', 'event_id', 'school_id', string='School'),
        # change 1/7/2015 for seminarprogram_event_id
        'question_ids': fields.one2many('vhr.program.question', 'program_event_id','Questions'),
        'part_ids': fields.one2many('vhr.program.part', 'program_event_id', 'Parts'),
        # change 26/1/2015 for generate form with 123phim
        'field_ids': fields.many2many('vhr.program.field', 'event_field_rel', 'event_id', 'field_id', 'Fields'),
        # change 29/1/2015 send email with template
        'temp_email_for_rr_id': fields.many2one('vhr.dimension', 'Email for RR', 
                                                domain=[('dimension_type_id.code', '=', 'EMAIL_TEMPLATE_FOR_RR'), ('active', '=', True)]),
        'temp_email_for_register_id': fields.many2one('vhr.dimension', 'Email for register', 
                                                      domain=[('dimension_type_id.code', '=', 'EMAIL_TEMPLATE_FOR_REGISTER'), ('active', '=', True)]),
        'has_gift': fields.boolean('Has Gift'),
        'gift_note': fields.text('Gift Note'),
        'event_gifts': fields.one2many('vhr.program.event.gift', 'event_id', 'Event Gift'),
        'show_min_gift': fields.integer('Show Min Gift'),
        'end_get_gifts': fields.boolean('End Get Gift'),
        'gift_alert': fields.text('Alert Duplicate'),
        'gift_alert_en': fields.text('Alert Duplicate En'),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'History',
                                         domain=[('object_id.model', '=', _name),
                                                 ('field_id.name', 'not in', ['write_date', 'audit_log_ids'])]),
        'write_date': fields.datetime('Write date'),
        'invite_bonus': fields.boolean("Invite Bonus"),
        'reload_page': fields.boolean("Reload Page"),
    }

    _defaults = {
        'active': True,
        'show_min_gift': 6,
        'reload_page': True
    }
    
    _order = 'write_date desc'

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        res = super(vhr_program_event, self).default_get(cr, uid, fields, context=context)

        if context.get('program_code', False):
            type_ids = self.pool.get('vhr.dimension').search(cr, uid, [('code', '=', context['program_code'])], context=context)
            if type_ids:
                res['program_id'] = type_ids[0]
        try:
            source_data = self.pool.get('ir.config_parameter').get_param(cr, uid, 'default.program.event.source')
            source_data_ids = filter(None, map(lambda a: a.strip() and int(a.strip()) or '', source_data.split(',')))
            recruitment_source_ids = self.pool.get('hr.recruitment.source').search(cr, uid,
                                                                                   [('id', 'in', source_data_ids)], context=context)
            res['recruitment_source_ids'] = [(6, 0, recruitment_source_ids)]
        except Exception, e:
            log.exception('vhr_program_event default_get %s' % e.message)
        school_ids = self.pool.get('vhr.school').search(cr, uid, [('website_published', '=', True)], order='name', context=context)
        res['school_ids'] = [(6, 0, school_ids)] 
        return res
    
    def create(self, cr, uid, vals, context={}):
        res_id = super(vhr_program_event, self).create(cr, uid, vals, context)
        self.pool.get('vhr.recruitment.interface').notify_change(cr, uid, context=context)
        return res_id 
    
    def write(self, cr, uid, ids, vals, context=None):
        #TODO: process before updating resource
        res = super(vhr_program_event, self).write(cr, uid, ids, vals, context)
        self.pool.get('vhr.recruitment.interface').notify_change(cr, uid, context=context)
        return res 

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_program_event, self).unlink(cr, uid, ids, context)
            self.pool.get('vhr.recruitment.interface').notify_change(cr, uid, context=context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res

#    def onchange_date(self, cr, uid, ids, date_from, date_to, context=None):
#        res = {'value': {}, 'warning': {}}
#        if date_from and date_to:
#            if date_from > date_to:
#                res['value']['date_from'] = False
#                res['value']['date_to'] = False
#                res['warning']['title'] = 'Validation Error!'
#                res['warning']['message'] = 'Date to must be greater than date from!'
#        return res
    
    def onchange_date(self, cr, uid, ids, date_from, context=None):
        res = {'value': {}}
        if date_from:
            date_temp1  = datetime.strptime(date_from,'%Y-%m-%d')
            date_to = date_temp1 + relativedelta.relativedelta(months=+1)
            date_temp2  = date_to.strftime('%Y-%m-%d')
            res['value']['date_to'] = date_temp2
        return res

vhr_program_event()
