# -*-coding:utf-8-*-
import logging
from openerp.osv import osv, fields
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT

log = logging.getLogger(__name__)
class vhr_contract_send_mail_remind(osv.osv):
    _name = 'vhr.contract.send.mail.remind'
    _description = 'Send mail remind signed'

    _columns = {
                'time_meet_user_sign_contract': fields.char('Working Time'),
                'day_meet_user_sign_contract': fields.char('Working Day'),
                'contract_ids': fields.one2many('hr.contract', 'remind_id', 'Detail', ondelete='restrict')
    }
    
    _defaults = {'time_meet_user_sign_contract': '16h – 17h'
                 }
    
    
    def get_default_day_meet_user_sign_contract(self, cr, uid, contract_id, context=None):
        deadline = False
        if contract_id:
            contract = self.pool.get('hr.contract').read(cr, uid, contract_id, ['day_meet_user_sign_contract','last_date_invited'])
            day_meet = contract.get('day_meet_user_sign_contract', False)
            if day_meet:
                return day_meet
            
            last_day_invited = contract.get('last_date_invited', False)
            if last_day_invited:
                last_day_invited = datetime.strptime(last_day_invited, DEFAULT_SERVER_DATE_FORMAT)
                deadline = last_day_invited + relativedelta(days=7)
                deadline = deadline.strftime('%d/%m/%Y')
        
        if not deadline:
            today = date.today()
            deadline = today + relativedelta(days=7)
            deadline = deadline.strftime('%d/%m/%Y')
        
        return 'các ngày làm việc trong tuần trước ngày ' + deadline
        
    def default_get(self, cr, uid, flds, context=None):
        if context is None:
            context = {}
        
        res = super(vhr_contract_send_mail_remind, self).default_get(cr, uid, flds, context=context)
        
        if context.get('active_ids', False):
            contract_obj = self.pool.get('hr.contract')
            res['contract_ids'] = []
            
            default_day = self.get_default_day_meet_user_sign_contract(cr, uid, False, context)
            res['day_meet_user_sign_contract'] = default_day
            
            dv_ctv_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_human_resource_colla_service_contract_type_group_code') or ''
            for contract_id in context['active_ids']:   
                contract = contract_obj.browse(cr, uid, contract_id)
                type_group_code = contract.type_id and contract.type_id.contract_type_group_id \
                                and contract.type_id.contract_type_group_id.code
                emp_mail = contract.employee_id and contract.employee_id.work_email or ''
                if type_group_code == dv_ctv_code:
                    emp_mail2 = contract.employee_id and contract.employee_id.email or ''
                    if emp_mail2:
                        emp_mail += ';' + emp_mail2
                res['contract_ids'].append([1,contract_id, {'mail_to_remind': emp_mail}])
        
        return res
    
    def create(self, cr, uid, vals, context=None):
        contract_ids = []
        if vals.get('contract_ids', False):
            for item in vals.get('contract_ids', []):
                if len(item) == 3 and item[0] == 2:
                    vals['contract_ids'].remove(item)
                elif len(item) ==3:
                    contract_ids.append(item[1])
                    
        res = super(vhr_contract_send_mail_remind, self).create(cr, uid, vals, context)
        
        if res and contract_ids:
            self.pool.get('hr.contract').write(cr, uid, contract_ids, {'remind_id': res})
            
        return res
        
    def execute_send_mail(self, cr, uid, ids, context=None):
        if not context:
            context = {}
            
        if not isinstance(ids, list):
            ids = [ids]
        
        record = self.read(cr, uid, ids[0], ['contract_ids','time_meet_user_sign_contract','day_meet_user_sign_contract'])
        contract_ids = record.get('contract_ids', [])
        time = record.get('time_meet_user_sign_contract','16h - 17h')
        day = record.get('day_meet_user_sign_contract', '')
        if contract_ids:
            self.pool.get('hr.contract').write(cr, uid, contract_ids, {'time_meet_user_sign_contract': time,
                                                                       'day_meet_user_sign_contract': day})
            self.send_mail(cr, uid, contract_ids, context)
        
        return {'type': 'ir.actions.act_window_close'}
    
    
    def send_mail(self, cr, uid, contract_ids, context=None):
        if not context:
            context = {}
            
        if contract_ids:
            employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=', uid)], context={'active_test':False})
            today = datetime.today().date()
            contract_obj = self.pool.get('hr.contract')
            
            mail_template = False
            if context.get('remind_sign_contract', False):
                mail_template = self.pool.get('ir.config_parameter').get_param(cr, uid, 'template_for_remind_sign_contract') or ''
            for contract in contract_obj.read(cr, uid, contract_ids, ['employee_id','type_id','mail_to_remind','inviter_id',
                                                                      'number_of_invited','state','time_meet_user_sign_contract',
                                                                      'day_meet_user_sign_contract']):
                if context.get('not_updated_inviter_id', False):
                    employee_ids = contract.get('inviter_id', False) and contract['inviter_id'][0] or False
                    employee_ids = [employee_ids]
                    
                if contract.get('state', False) != 'signed':
                    employee_id = contract.get('employee_id', False) and contract['employee_id'][1] or ''
                    raise osv.except_osv('Error !', "Contracts of these employee are not signed: "+ str(employee_id)) 
                number_of_invited = contract.get('number_of_invited',0) + 1
                
                
                if not mail_template:
                    mail_template = 'vhr_sm_contract_invite_to_sign_contract'
                
                email_cc = []
                mail_group_pool = self.pool.get('vhr.email.group')
                mail_group_ids = mail_group_pool.search(cr, uid, [('code','=','CC_Renew_Contract')])
                if mail_group_ids:
                    mail_group = mail_group_pool.read(cr, uid, mail_group_ids[0], ['to_email','cc_email'])
                    to_email = mail_group.get('to_email','') or ''
                    cc_email = mail_group.get('cc_email','') or ''
                    mail_to  = to_email.split(';')
                    mail_cc  = cc_email.split(';')
                    email_cc.extend(mail_to)
                    email_cc.extend(mail_cc)
                        
                vals = {'email_to': contract.get('mail_to_remind',''),
                        'email_cc': ';'.join(email_cc),
                        'contract_id': contract['id']
                        }
                
                time_meet_user_sign_contract = contract.get('time_meet_user_sign_contract', False) or '16h - 17h'
                day_meet_user_sign_contract = contract.get('day_meet_user_sign_contract', False)
                if not day_meet_user_sign_contract:
                    day_meet_user_sign_contract = self.get_default_day_meet_user_sign_contract(cr, uid, contract['id'])
                
                vals_contract = {'is_invited': True,
                                 'last_date_invited': today,
                                 'number_of_invited': number_of_invited,
                                 'inviter_id': employee_ids and employee_ids[0] or False,
                                 }
                
                if not contract.get('time_meet_user_sign_contract', False):
                    vals_contract.update({'time_meet_user_sign_contract': time_meet_user_sign_contract})
                
                if not contract.get('day_meet_user_sign_contract', False):
                    vals_contract.update({'day_meet_user_sign_contract': day_meet_user_sign_contract})
                    
                contract_obj.write(cr, uid, contract['id'], vals_contract)
                context['not_split_email'] = True
                self.pool.get('vhr.sm.email').send_email(cr, uid, mail_template, vals, context)
                    
        return True
    
    
    def cron_delete(self, cr, uid):
        contract_obj = self.pool.get('hr.contract')
        contract_ids = contract_obj.search(cr, uid, [('remind_id','!=', False)])
        if contract_ids:
            contract_obj.write(cr, uid, contract_ids, {'remind_id': False})
            ids = self.search(cr, uid, [])
            self.unlink(cr, uid, ids)
        
        return True
    
    def cron_send_mail_remind(self, cr, uid, context):
        '''
        Tìm các contract có is_invited=True 
                            lần cuối gửi mail cach day 6-7 ngày 
                             số lần invited <3
        '''
        if not context:
            context = {}
        
        context['not_updated_inviter_id'] = True
            
        log.info("start cron_send_mail_remind")
        today = datetime.today().date()
        six_days_ago = today -relativedelta(days=6)
        seven_days_ago = today -relativedelta(days=7)
        contract_obj = self.pool.get('hr.contract')
        contract_ids = contract_obj.search(cr, uid, [('is_invited','=',True),
                                                     ('is_delivered','=', False),
                                                     ('is_received','=', False),
                                                     ('number_of_invited','<',3),
                                                     ('last_date_invited','<=',six_days_ago),
                                                     ('last_date_invited','>=',seven_days_ago)])
        if contract_ids:
            context['remind_sign_contract'] = True
            self.send_mail(cr, uid, contract_ids, context)
        
        log.info("end cron_send_mail_remind")
        return True
            

vhr_contract_send_mail_remind()


class hr_contract(osv.osv):
    _name = 'hr.contract'
    _inherit = 'hr.contract'

    _columns = {
                
                'remind_id': fields.many2one('vhr.contract.send.mail.remind', 'Remind', ondelete='restrict')
                }
    

hr_contract()