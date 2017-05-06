# -*-coding:utf-8-*-
import logging
from openerp.osv import osv, fields
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from vhr_recruitment_constant import RE_TALENT_AA, RE_REMIND_RECRUITER_TAKE_ACTION_COMMUNICATION
from vhr_recruitment_abstract import vhr_recruitment_abstract

log = logging.getLogger(__name__)


class vhr_rr_talent_communi(osv.osv, vhr_recruitment_abstract):
    _name = 'vhr.rr.talent.communi'
    _description = 'VHR RR Talent Communication'
    
    def _get_default_channel_id(self, cr, uid, context=None):
        default_channel_id = False
        try:    
            default_channel_id = self.pool.get('ir.model.data').get_object(cr, uid, 'vhr_recruitment', 'vhr_rr_com_channel_default').id
        except Exception as e:
            log.exception(e)
        return default_channel_id
    
    _columns = {
        'who_met_ids': fields.many2many('hr.employee', 'talent_communi_employee_rel',
                                        'talent_communi_id', 'employee_id', 'Who met'), 
        'channel_id': fields.many2one('vhr.rr.com.channel','Channel'),
        'talent_group_id': fields.many2many('vhr.dimension', 'talent_communi_dimension_rel',
                                            'talent_communi_id', 'dimension_id',
                                            'Group', ondelete='restrict',
                                            domain=[('dimension_type_id.code', '=', 'RR_TALENT_GROUP'),
                                               ('active', '=', True)]),
        'time': fields.datetime('Time'),
        'place': fields.char('Place'),
        'content': fields.text('Content'),
        'applicant_id': fields.many2one('hr.applicant', 'Candidate', ondelete='cascade')
    }
    
    _defaults = {
        'channel_id': _get_default_channel_id
    }
    
    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        if vals.get('time', False):
            current_date = date.today()
            current_date = current_date.strftime('%Y-%m-%d')
            for com in self.browse(cr, uid, ids, context=context):
                time_com = com.time
                time_com = datetime.strptime(time_com, '%Y-%m-%d %H:%M:%S')
                time_com = time_com.strftime('%Y-%m-%d')
                if time_com == current_date:
                    self.recruitment_send_email(cr, uid, RE_REMIND_RECRUITER_TAKE_ACTION_COMMUNICATION, self._name, com.id, context=context)
    
    def get_appoitment_date(self, cr, uid, res_id, context=None):
        if isinstance(res_id, list):
            res_id = res_id[0]
        result = 0
        appointment_date = self.browse(cr, uid, res_id).time
        if appointment_date:
            appointment_date = datetime.strptime(appointment_date, '%Y-%m-%d %H:%M:%S')
            result = appointment_date.date() - date.today()
            result = result.days
        return result
    
            
    def cron_arrange_appointment_with_talent(self, cr, uid, delta_date, context=None):
        log.info('VHR RR cron_arrange_appointment_with_candidate: Start')
        appointment_date = date.today() + relativedelta(days = delta_date)
        appointment_date = appointment_date.strftime('%Y-%m-%d') + ' 00:00:00'
        next_appointment_date = date.today() + relativedelta(days = delta_date+1)
        next_appointment_date = next_appointment_date.strftime('%Y-%m-%d') + ' 00:00:00'
        lst_appoint = self.search(cr, uid, [('time','>=',appointment_date),
                                                          ('time','<',next_appointment_date),
                                                          ('applicant_id.in_charge_talent','!=', None)])
        for item in lst_appoint:
            self.recruitment_send_email(cr, uid, RE_TALENT_AA, self._name, item, context=context)
        log.info('VHR RR cron_arrange_appointment_with_candidate: End')      
        return True
    
    
    def cron_remind_recruiter_take_action_communication(self, cr, uid, context=None):
        if context is None:
            context = {}
        log.info('VHR RR cron_remind_recruiter_take_action_communication Start')
        current_date = date.today()
        current_date = current_date.strftime('%Y-%m-%d')
        cr.execute('select com.id as id from vhr_rr_talent_communi com where com.time::date = %s',(current_date,))
        for item in cr.dictfetchall():
            if item['id']:
                self.recruitment_send_email(cr, uid, RE_REMIND_RECRUITER_TAKE_ACTION_COMMUNICATION, self._name, item['id'], context=context)
        log.info('VHR RR cron_remind_recruiter_take_action_communication End')
        return True
    

vhr_rr_talent_communi()
