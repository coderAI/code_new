# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields
#from vhr_recruitment_constant import RE_ERP_Pass, RE_ERP_Pass_Not_Bonus
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from dateutil import relativedelta

log = logging.getLogger(__name__)
#from vhr_recruitment_abstract import vhr_recruitment_abstract


class vhr_erp_bonus_payment(osv.osv):
    _name = 'vhr.erp.bonus.payment'
    _description = 'VHR ERP Bonus Payment'
    
    def _check_payment_edit(self, cr, uid, ids, fields, args, context=None):
        result={}
        if not isinstance(ids, list):
            ids = [ids]
        bonus_payment_line_obj = self.pool.get('vhr.erp.bonus.payment.line')
        for item in ids:
            result[item] = False
            count = bonus_payment_line_obj.search(cr, uid, [('bonus_payment_id','=', item),
                                                          ('state','!=', 'draft')], count=True)
            if count == 0:
                result[item] = True
        return result

    def _get_total_bonus(self, cr, uid, ids, fields, args, context=None):
        result = {}
        for bonus in self.browse(cr, uid, ids, context=context):
            temp = 0
            for payment_line in bonus.payment_line_ids:
                temp = temp + payment_line.payment_value
            result[bonus.id] = temp
        return result

    def action_payment(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'payment'})
        return True

    def action_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'cancel'})
        return True

    def onchange_bonus_scheme_id(self, cr, uid, ids, bonus_scheme_id, context=None):
        res = {}
        domain = {}
        if bonus_scheme_id:
            total_bonus = self.pool.get('vhr.erp.bonus.scheme').browse(cr, uid, bonus_scheme_id, context=context).total_bonus
            res['total_bonus'] = total_bonus
        return {'value': res, 'domain': domain}

    def onchange_bonus_payment(self, cr, uid, ids, job_id, applicant_id, context=None):
        res = {'recommender_id': False, 'job_group_id': False, 'job_family_id': False,
               'department_id': False, 'total_bonus': False, 'bonus_scheme_id': False,
               'offer_job_level_position_id' : False, 'job_title_id': False,'erp_level_id': False  }
        domain = {'applicant_id': [('id', 'in', [])], 'recommender_id': [('id', 'in', [])], 'job_group_id': [('id', 'in', [])],
                  'job_family_id': [('id', 'in', [])], 'department_id': [('id', 'in', [])]}
        job_app_obj = self.pool.get('vhr.job.applicant')

        if job_id:
            arg = [('job_id', '=', job_id), ('state', 'in', ['offer', 'done']), ('hr_process', '=', True),
                   ('applicant_id.recommender_id', '!=', False), ('applicant_id.source_id.code', 'in', ('ERP','SR-100'))]
            lst_job_app = job_app_obj.search(cr, uid, arg, context=context)
            lst_applicant = [job_item.applicant_id.id for job_item in job_app_obj.browse(cr, uid, lst_job_app, context=context)]
            domain['applicant_id'] = [('id', 'in', lst_applicant)]

        if job_id and applicant_id:
            lst_job_app = job_app_obj.search(cr, uid, [('job_id', '=', job_id), ('applicant_id', '=', applicant_id)], context=context)
            if lst_job_app:
                job_app = job_app_obj.browse(cr, uid, lst_job_app[0], context=context)
                res['department_id'] = job_app.offer_department.id if job_app.offer_department else False
                res['recommender_id'] = job_app.applicant_id.recommender_id and job_app.applicant_id.recommender_id.id
                res['job_group_id'] = job_app.offer_job_group_id.id if job_app.offer_job_group_id else False
                res['job_family_id'] = job_app.offer_job_family_id.id if job_app.offer_job_family_id else False
                res['job_level_position_id'] = job_app.offer_job_level_position_id.id if job_app.offer_job_level_position_id else False
                res['job_title_id'] = job_app.offer_job_title_id.id if job_app.offer_job_title_id else False
                #offer_level_id = job_app.offer_job_level_id.id
                # load scheme
                scheme_id = self.pool.get('vhr.erp.bonus.scheme').get_bonus_scheme_id(cr, uid, res['job_family_id'],
                                                                                      res['job_group_id'], res['job_level_position_id'])
                res['bonus_scheme_id'] = scheme_id
                bonus_scheme = self.pool.get('vhr.erp.bonus.scheme').browse(cr, uid, scheme_id[0], context=context)
                res['erp_level_id'] = bonus_scheme.erp_level_id.id
            else:
                res['applicant_id'] = False
        return {'value': res, 'domain': domain}
    
    
    def get_time_for_payment2(self, cr, uid, payment_time, offer_contract_type, offer_join_date, context=None):
        result =  datetime.strptime(offer_join_date, '%Y-%m-%d')
        paytime = self.pool.get('vhr.erp.payment.time').browse(cr, uid, payment_time, context=context)
        contract = self.pool.get('hr.contract.type').browse(cr, uid, offer_contract_type, context=context)
        if contract:    
            life_of_contract = contract.life_of_contract if contract.life_of_contract else 0
            #result = datetime.today()
            if paytime:
                if paytime.payment_time == 'FINISH_PROBATION':
                    month = life_of_contract
                    result = result + relativedelta.relativedelta(months=month)
                else:
                    day_add = paytime.period_days if paytime.period_days else 0
                    result = result + relativedelta.relativedelta(days=day_add)
        return result
    
    def create_erp_bonus_payment(self, cr, uid, job_app_id, context=None):
        try:
            ja_obj = self.pool.get('vhr.job.applicant').browse(cr, uid, job_app_id, context=context)
            applicant = ja_obj.applicant_id
            request = ja_obj.job_id
            #and item.type_id and item.type_id.contract_type_group_id and\
            #item.type_id.contract_type_group_id.code not in ('2','CTG-008')
            if applicant and applicant.source_id.code == 'ERP' and applicant.recommender_id and\
             ja_obj.contract_type_id and ja_obj.contract_type_id.contract_type_group_id and\
             ja_obj.contract_type_id.contract_type_group_id.code not in ('2','CTG-008'):
                    exclusion_obj = self.pool.get('vhr.erp.bonus.exclusion')
                    scheme_obj = self.pool.get('vhr.erp.bonus.scheme')
                    setting_special_obj = self.pool.get('vhr.erp.setting.special')
                    recommender = applicant.recommender_id
                    recom_depart_code = recommender.department_id and recommender.department_id.code or ''
                    recom_depart_team_code = recommender.team_id and recommender.team_id.code or ''
                    recom_level_code = recommender.job_level_person_id and recommender.job_level_person_id.code or ''
                    # Offer information
                    offer_depart_code = ja_obj.offer_department.code if ja_obj.offer_department else ''
                    offer_dept_head = ja_obj.offer_department.manager_id.id if ja_obj.offer_department else False
                    offer_report = ja_obj.offer_report_to.id if ja_obj.offer_report_to else False
                    offer_job_family_id = ja_obj.offer_job_family_id.id if ja_obj.offer_job_family_id else False
                    offer_job_group_id = ja_obj.offer_job_group_id.id if ja_obj.offer_job_group_id else False
                    offer_job_level_position_id = ja_obj.offer_job_level_position_id.id if ja_obj.offer_job_level_position_id else False
                    offer_job_title_id = ja_obj.offer_job_title_id.id if ja_obj.offer_job_title_id else False
                    offer_contract_type_id = ja_obj.contract_type_id.id if ja_obj.contract_type_id else False
                    offer_join_date = ja_obj.join_date if ja_obj.join_date else False
                    offer_department  = ja_obj.offer_department.id if ja_obj.offer_department else False
                    # check for payment
                    exclusion_id = exclusion_obj.get_exclusion_erp(cr, uid, recommender.id, recom_depart_code,recom_depart_team_code, recom_level_code,
                                                                    offer_depart_code, offer_dept_head, offer_report, job_app_id)
                    
                    bonus_scheme = scheme_obj.get_bonus_scheme(cr, uid, offer_depart_code, offer_job_family_id, offer_job_group_id,
                                                               offer_job_level_position_id, offer_job_title_id, offer_contract_type_id, offer_join_date)
                    if bonus_scheme:
                        total_bonus = 0
                        is_specialerp =  False
                        total_bonus_specialerp = 0
                        if request.is_specialerp == True:
                            special_ids = setting_special_obj.search(cr, uid,[('job_family_id','=',offer_job_family_id),
                                                                              ('job_group_id','=',offer_job_group_id),
                                                                              ('job_level_position_id','=',offer_job_level_position_id),
                                                                              ('special_job_id','=',request.id)])
                            if special_ids:
                                special = setting_special_obj.browse(cr, uid, special_ids[0], context = context)
                                if special.total_bonus_specialerp > 0:
                                    total_bonus = special.total_bonus_specialerp
                                    total_bonus_specialerp = special.total_bonus_specialerp
                                    is_specialerp = True
                                else:
                                    total_bonus = bonus_scheme.get('total_bonus', 0)
                                    total_bonus_specialerp = 0
                                    is_specialerp =  False
                                    
                        elif request.is_specialerp == False:
                            total_bonus = bonus_scheme.get('total_bonus', 0)
                            total_bonus_specialerp = 0
                            is_specialerp =  False
                            
                        vals = {
                                'recommender_id': recommender.id or False,
                                'applicant_id': applicant.id or False,
                                'job_id': request.id or False,
                                'department_id': offer_department,
                                'job_family_id': offer_job_family_id,
                                'job_group_id': offer_job_group_id,
                                'job_level_position_id': offer_job_level_position_id,
                                'job_title_id': offer_job_title_id,
                                'erp_level_id':bonus_scheme.get('erp_level_id', 0),
                                'total_bonus': total_bonus,
                                'bonus_scheme_id': bonus_scheme.get('bonus_scheme_id', 0),
                                'exclusion_id':exclusion_id,
                                'is_specialerp': is_specialerp,
                                }
                        payment_id = self.create(cr, uid, vals)
                        payment_line = {'bonus_payment_id': payment_id}
                        payline_obj = self.pool.get('vhr.erp.bonus.payment.line')
                        #email_template = RE_ERP_Pass
                        if exclusion_id != False:
                            #email_template = RE_ERP_Pass_Not_Bonus
                            payment_line['state'] = 'cancel'
                            
                        if request.is_specialerp and total_bonus_specialerp > 0:
                            if ja_obj.contract_type_id.contract_type_group_id.code == '1':
                                date_temp1 = False
                                DATE_FORMAT_DAY1 = "%d"
                                payment_date1 = self.get_time_for_payment2(cr, uid, 1, offer_contract_type_id, offer_join_date)
                                if payment_date1:
                                    #temp1=datetime.strptime(payment_date1,'%Y-%m-%d')
                                    day_payment_date1= datetime.strftime(payment_date1,DATE_FORMAT_DAY1)
                                    if day_payment_date1 > '25':
                                        date_temp_date1 = payment_date1 + relativedelta.relativedelta(months=+1, day=1)
                                        date_temp1  = date_temp_date1.strftime('%Y-%m-%d')
                                    else:
                                        date_temp1 = payment_date1
                                                                
                                payment_line['payment_rate'] = 20
                                payment_line['payment_value'] = total_bonus_specialerp*0.2
                                payment_line['payment_date'] =  date_temp1
                                payment_line['payment_time_id'] = 1
                                payline_obj.create(cr, uid, payment_line)
                                if bonus_scheme.get('payment2', True):
                                    date_temp2 = False
                                    DATE_FORMAT_DAY2 = "%d"
                                    payment_date2 = self.get_time_for_payment2(cr, uid, 2, offer_contract_type_id, offer_join_date)
                                    if payment_date2:
                                        #temp2=datetime.strptime(payment_date2,'%Y-%m-%d')
                                        day_payment_date2= datetime.strftime(payment_date2,DATE_FORMAT_DAY2)
                                        if day_payment_date2 > '25':
                                            date_temp_date2 = payment_date2 + relativedelta.relativedelta(months=+1, day=1)
                                            date_temp2  = date_temp_date2.strftime('%Y-%m-%d')
                                        else:
                                            date_temp2 = payment_date2
                                            
                                    payment_line['payment_rate'] = 40
                                    payment_line['payment_value'] = total_bonus_specialerp*0.4
                                    payment_line['payment_date'] =  date_temp2
                                    payment_line['payment_time_id'] = 2
                                    payline_obj.create(cr, uid, payment_line)
                                    
                                if bonus_scheme.get('payment3', True):
                                    date_temp3 = False
                                    DATE_FORMAT_DAY3 = "%d"
                                    payment_date3 = self.get_time_for_payment2(cr, uid, 3, offer_contract_type_id, offer_join_date)
                                    if payment_date3:
                                        #temp3=datetime.strptime(payment_date3,'%Y-%m-%d')
                                        day_payment_date3= datetime.strftime(payment_date3,DATE_FORMAT_DAY3)
                                        if day_payment_date3 > '25':
                                            date_temp_date3 = payment_date3 + relativedelta.relativedelta(months=+1, day=1)
                                            date_temp3  = date_temp_date3.strftime('%Y-%m-%d')
                                        else:
                                            date_temp3 = payment_date3
                                            
                                    payment_line['payment_rate'] = 40
                                    payment_line['payment_value'] = total_bonus_specialerp*0.4
                                    payment_line['payment_date'] =  date_temp3
                                    payment_line['payment_time_id'] = 3
                                    payline_obj.create(cr, uid, payment_line)
                            elif ja_obj.contract_type_id.contract_type_group_id.code != '1':
                                date_temp1 = False
                                DATE_FORMAT_DAY1 = "%d"
                                payment_date1 = self.get_time_for_payment2(cr, uid, 1, offer_contract_type_id, offer_join_date)
                                if payment_date1:
                                    #temp1=datetime.strptime(payment_date1,'%Y-%m-%d')
                                    day_payment_date1= datetime.strftime(payment_date1,DATE_FORMAT_DAY1)
                                    if day_payment_date1 > '25':
                                        date_temp_date1 = payment_date1 + relativedelta.relativedelta(months=+1, day=1)
                                        date_temp1  = date_temp_date1.strftime('%Y-%m-%d')
                                    else:
                                        date_temp1 = payment_date1
                                                                
                                payment_line['payment_rate'] = 60
                                payment_line['payment_value'] = total_bonus_specialerp*0.6
                                payment_line['payment_date'] =  date_temp1
                                payment_line['payment_time_id'] = 1
                                payline_obj.create(cr, uid, payment_line)
                                
                                if bonus_scheme.get('payment3', True):
                                    date_temp3 = False
                                    DATE_FORMAT_DAY3 = "%d"
                                    payment_date3 = self.get_time_for_payment2(cr, uid, 3, offer_contract_type_id, offer_join_date)
                                    if payment_date3:
                                        #temp3=datetime.strptime(payment_date3,'%Y-%m-%d')
                                        day_payment_date3= datetime.strftime(payment_date3,DATE_FORMAT_DAY3)
                                        if day_payment_date3 > '25':
                                            date_temp_date3 = payment_date3 + relativedelta.relativedelta(months=+1, day=1)
                                            date_temp3  = date_temp_date3.strftime('%Y-%m-%d')
                                        else:
                                            date_temp3 = payment_date3
                                            
                                    payment_line['payment_rate'] = 40
                                    payment_line['payment_value'] = total_bonus_specialerp*0.4
                                    payment_line['payment_date'] =  date_temp3
                                    payment_line['payment_time_id'] = 3
                                    payline_obj.create(cr, uid, payment_line)
                                    
                        if request.is_specialerp == False:
                            if ja_obj.contract_type_id.contract_type_group_id.code == '1':
                                if bonus_scheme.get('payment1', False):
                                    date_temp_temp1 = False
                                    DATE_FORMAT_DAY_TEMP1 = "%d"
                                    payment_date_temp1 = bonus_scheme.get('payment1_date', 0)
                                    if payment_date_temp1:
                                        #temp_temp1=payment_date_temp1.strptime('%Y-%m-%d')
                                        day_payment_date_temp1= datetime.strftime(payment_date_temp1,DATE_FORMAT_DAY_TEMP1)
                                        if day_payment_date_temp1 > '25':
                                            date_temp_date_temp1 = payment_date_temp1 + relativedelta.relativedelta(months=+1, day=1)
                                            date_temp_temp1  = date_temp_date_temp1.strftime('%Y-%m-%d')
                                        else:
                                            date_temp_temp1 = payment_date_temp1
                                            
                                    payment_line['payment_rate'] = bonus_scheme.get('payment1rate', 0)
                                    payment_line['payment_value'] = bonus_scheme.get('payment1', 0)
                                    payment_line['payment_date'] = date_temp_temp1
                                    payment_line['payment_time_id'] = bonus_scheme.get('payment_time_id_1', 0)
                                    payline_obj.create(cr, uid, payment_line)
                                    
                                if bonus_scheme.get('payment2', False):
                                    date_temp_temp2 = False
                                    DATE_FORMAT_DAY_TEMP2 = "%d"
                                    payment_date_temp2 = bonus_scheme.get('payment2_date', 0)
                                    if payment_date_temp2:
                                        #temp_temp2=payment_date_temp2.strptime('%Y-%m-%d')
                                        day_payment_date_temp2 = datetime.strftime(payment_date_temp2,DATE_FORMAT_DAY_TEMP2)
                                        if day_payment_date_temp2 > '25':
                                            date_temp_date_temp2 = payment_date_temp2 + relativedelta.relativedelta(months=+1, day=1)
                                            date_temp_temp2  = date_temp_date_temp2.strftime('%Y-%m-%d')
                                        else:
                                            date_temp_temp2 = payment_date_temp2
                                            
                                    payment_line['payment_rate'] = bonus_scheme.get('payment2rate', 0)
                                    payment_line['payment_value'] = bonus_scheme.get('payment2', 0)
                                    payment_line['payment_date'] = date_temp_temp2
                                    payment_line['payment_time_id'] = bonus_scheme.get('payment_time_id_2', 0)
                                    payline_obj.create(cr, uid, payment_line)
                                    
                                if bonus_scheme.get('payment3', False):
                                    date_temp_temp3 = False
                                    DATE_FORMAT_DAY_TEMP3 = "%d"
                                    payment_date_temp3 = bonus_scheme.get('payment3_date', 0)
                                    if payment_date_temp3:
                                        #temp_temp3=payment_date_temp3.strptime('%Y-%m-%d')
                                        day_payment_date_temp3 = datetime.strftime(payment_date_temp3,DATE_FORMAT_DAY_TEMP3)
                                        if day_payment_date_temp3 > '25':
                                            date_temp_date_temp3 = payment_date_temp3 + relativedelta.relativedelta(months=+1, day=1)
                                            date_temp_temp3  = date_temp_date_temp3.strftime('%Y-%m-%d')
                                        else:
                                            date_temp_temp3 = payment_date_temp3
                                            
                                    payment_line['payment_rate'] = bonus_scheme.get('payment3rate', 0)
                                    payment_line['payment_value'] = bonus_scheme.get('payment3', 0)
                                    payment_line['payment_date'] = date_temp_temp3
                                    payment_line['payment_time_id'] = bonus_scheme.get('payment_time_id_3', 0)
                                    payline_obj.create(cr, uid, payment_line)
                                    
                            elif ja_obj.contract_type_id.contract_type_group_id.code != '1':
                                if bonus_scheme.get('payment1', False):
                                    date_temp_temp1 = False
                                    DATE_FORMAT_DAY_TEMP1 = "%d"
                                    payment_date_temp1 = bonus_scheme.get('payment1_date', 0)
                                    payment_rate1 = bonus_scheme.get('payment1rate', 0)
                                    payment_rate2 = 0
                                    payment_rate = 0
                                    payment_value = 0
                                    payment_value2 = 0
                                    if bonus_scheme.get('payment2'):
                                        payment_rate2 = bonus_scheme.get('payment2rate',0)
                                        payment_value2 = bonus_scheme.get('payment2', 0)
                                    payment_value = bonus_scheme.get('payment1', 0) + payment_value2    
                                    payment_rate = payment_rate1  + payment_rate2
                                    if payment_date_temp1:
                                        #temp_temp1=payment_date_temp1.strptime('%Y-%m-%d')
                                        day_payment_date_temp1= datetime.strftime(payment_date_temp1,DATE_FORMAT_DAY_TEMP1)
                                        if day_payment_date_temp1 > '25':
                                            date_temp_date_temp1 = payment_date_temp1 + relativedelta.relativedelta(months=+1, day=1)
                                            date_temp_temp1  = date_temp_date_temp1.strftime('%Y-%m-%d')
                                        else:
                                            date_temp_temp1 = payment_date_temp1
                                            
                                    payment_line['payment_rate'] = payment_rate
                                    payment_line['payment_value'] = payment_value
                                    payment_line['payment_date'] = date_temp_temp1
                                    payment_line['payment_time_id'] = bonus_scheme.get('payment_time_id_1', 0)
                                    payline_obj.create(cr, uid, payment_line)
                                    
                                if bonus_scheme.get('payment3', False):
                                    date_temp_temp3 = False
                                    DATE_FORMAT_DAY_TEMP3 = "%d"
                                    payment_date_temp3 = bonus_scheme.get('payment3_date', 0)
                                    if payment_date_temp3:
                                        #temp_temp3=payment_date_temp3.strptime('%Y-%m-%d')
                                        day_payment_date_temp3 = datetime.strftime(payment_date_temp3,DATE_FORMAT_DAY_TEMP3)
                                        if day_payment_date_temp3 > '25':
                                            date_temp_date_temp3 = payment_date_temp3 + relativedelta.relativedelta(months=+1, day=1)
                                            date_temp_temp3  = date_temp_date_temp3.strftime('%Y-%m-%d')
                                        else:
                                            date_temp_temp3 = payment_date_temp3
                                            
                                    payment_line['payment_rate'] = bonus_scheme.get('payment3rate', 0)
                                    payment_line['payment_value'] = bonus_scheme.get('payment3', 0)
                                    payment_line['payment_date'] = date_temp_temp3
                                    payment_line['payment_time_id'] = bonus_scheme.get('payment_time_id_3', 0)
                                    payline_obj.create(cr, uid, payment_line)
                        # chi gui mail khi duoc bat
                        #if applicant.is_erp_mail:
                        #    email_ids = self.pool.get('email.template').search(cr, uid, [('model', '=', 'vhr.job.applicant'),
                        #                                                                 ('name', '=', email_template)], context=context)
                        #    if email_ids:
                        #        self.vhr_send_mail(cr, uid, email_ids[0], job_app_id)                    
                                
            if applicant and applicant.source_id.code == 'SR-100' and applicant.recommender_id and\
             ja_obj.contract_type_id and ja_obj.contract_type_id.contract_type_group_id and\
             ja_obj.contract_type_id.contract_type_group_id.code not in ('2','CTG-008'):
                    exclusion_obj = self.pool.get('vhr.erp.bonus.exclusion')
                    scheme_obj = self.pool.get('vhr.erp.bonus.scheme')
                    setting_special_obj = self.pool.get('vhr.erp.setting.special')
                    recommender = applicant.recommender_id
                    recom_depart_code = recommender.department_id and recommender.department_id.code or ''
                    recom_depart_team_code = recommender.team_id and recommender.team_id.code or ''
                    recom_level_code = recommender.job_level_person_id and recommender.job_level_person_id.code or ''
                    # Offer information
                    offer_depart_code = ja_obj.offer_department.code if ja_obj.offer_department else False
                    offer_dept_head = ja_obj.offer_department.manager_id.id if ja_obj.offer_department else False
                    offer_report = ja_obj.offer_report_to.id if ja_obj.offer_report_to else False
                    offer_job_family_id = ja_obj.offer_job_family_id.id if ja_obj.offer_job_family_id else False
                    offer_job_group_id = ja_obj.offer_job_group_id.id if ja_obj.offer_job_group_id else False
                    offer_job_level_position_id = ja_obj.offer_job_level_position_id.id if ja_obj.offer_job_level_position_id else False
                    offer_job_title_id = ja_obj.offer_job_title_id.id if ja_obj.offer_job_title_id else False
                    offer_contract_type_id = ja_obj.contract_type_id.id if ja_obj.contract_type_id else False
                    offer_join_date = ja_obj.join_date if ja_obj.join_date else False
                    offer_department = ja_obj.offer_department.id if ja_obj.offer_department else False
                    # check for payment
                    exclusion_id = exclusion_obj.get_exclusion_erp(cr, uid, recommender.id, recom_depart_code,recom_depart_team_code, recom_level_code,
                                                                    offer_depart_code, offer_dept_head, offer_report, job_app_id)
                    
                    bonus_scheme = scheme_obj.get_bonus_scheme(cr, uid, offer_depart_code, offer_job_family_id, offer_job_group_id,
                                                               offer_job_level_position_id, offer_job_title_id, offer_contract_type_id, offer_join_date)
                    if bonus_scheme:
                        total_bonus_sr = 0
                        is_specialerp = False
                        total_bonus_specialerp_sr = 0
                        if request.is_specialerp == True:
                            special_ids = setting_special_obj.search(cr, uid,[('job_family_id','=',offer_job_family_id),
                                                                              ('job_group_id','=',offer_job_group_id),
                                                                              ('job_level_position_id','=',offer_job_level_position_id),
                                                                              ('special_job_id','=',request.id)])
                            if special_ids:
                                special = setting_special_obj.browse(cr, uid, special_ids[0], context = context)
                                if special.total_bonus_specialerp > 0:
                                    total_bonus_sr = special.total_bonus_specialerp*0.3
                                    total_bonus_specialerp_sr = special.total_bonus_specialerp*0.3
                                    is_specialerp = True
                                else:
                                    total_bonus_sr = bonus_scheme.get('total_bonus', 0)*0.3
                                    total_bonus_specialerp_sr = 0
                                    is_specialerp =  False
                                    
                        elif request.is_specialerp == False:
                            total_bonus_sr = bonus_scheme.get('total_bonus', 0)*0.3
                            total_bonus_specialerp_sr = 0
                            is_specialerp =  False
                            
                        vals = {
                                'recommender_id': recommender.id or False,
                                'applicant_id': applicant.id or False,
                                'job_id': request.id or False,
                                'department_id': offer_department,
                                'job_family_id': offer_job_family_id,
                                'job_group_id': offer_job_group_id,
                                'job_level_position_id': offer_job_level_position_id,
                                'job_title_id': offer_job_title_id,
                                'erp_level_id':bonus_scheme.get('erp_level_id', 0),
                                'total_bonus': total_bonus_sr,
                                'bonus_scheme_id': bonus_scheme.get('bonus_scheme_id', 0),
                                'exclusion_id':exclusion_id,
                                'is_specialerp':is_specialerp
                                }
                        payment_id = self.create(cr, uid, vals)
                        payment_line = {'bonus_payment_id': payment_id}
                        payline_obj = self.pool.get('vhr.erp.bonus.payment.line')
                        #email_template = RE_ERP_Pass
                        if exclusion_id != False:
                            #email_template = RE_ERP_Pass_Not_Bonus
                            payment_line['state'] = 'cancel'
                        if ja_obj.contract_type_id.contract_type_group_id.code == '1':
                            date_temp_sr = False
                            DATE_FORMAT_DAY_SR = "%d"
                            payment_date_sr = self.get_time_for_payment2(cr, uid, 2, offer_contract_type_id, offer_join_date)
                            if payment_date_sr:
                                #temp_sr=payment_date_sr.strptime('%Y-%m-%d')
                                day_payment_date_sr= datetime.strftime(payment_date_sr,DATE_FORMAT_DAY_SR)
                                if day_payment_date_sr > '25':
                                    date_temp_date_sr = payment_date_sr + relativedelta.relativedelta(months=+1, day=1)
                                    date_temp_sr  = date_temp_date_sr.strftime('%Y-%m-%d')
                                else:
                                    date_temp_sr = payment_date_sr
                                        
                            payment_line['payment_rate'] = 100
                            if request.is_specialerp ==True and total_bonus_specialerp_sr > 0:
                                payment_line['payment_value'] = total_bonus_specialerp_sr  
                            elif request.is_specialerp == False:
                                payment_line['payment_value'] = bonus_scheme.get('total_bonus', 0)*0.3
                            
                            payment_line['payment_date'] = date_temp_sr
                            payment_line['payment_time_id'] = 2
                            
                            payline_obj.create(cr, uid, payment_line)
                            
                        elif ja_obj.contract_type_id.contract_type_group_id.code != '1':
                            date_temp_sr = False
                            DATE_FORMAT_DAY_SR = "%d"
                            payment_date_sr = self.get_time_for_payment2(cr, uid, 1, offer_contract_type_id, offer_join_date)
                            if payment_date_sr:
                                #temp_sr=payment_date_sr.strptime('%Y-%m-%d')
                                day_payment_date_sr= datetime.strftime(payment_date_sr,DATE_FORMAT_DAY_SR)
                                if day_payment_date_sr > '25':
                                    date_temp_date_sr = payment_date_sr + relativedelta.relativedelta(months=+1, day=1)
                                    date_temp_sr  = date_temp_date_sr.strftime('%Y-%m-%d')
                                else:
                                    date_temp_sr = payment_date_sr
                                        
                            payment_line['payment_rate'] = 100
                            if request.is_specialerp ==True and total_bonus_specialerp_sr > 0:
                                payment_line['payment_value'] = total_bonus_specialerp_sr 
                            elif request.is_specialerp == False:
                                payment_line['payment_value'] = bonus_scheme.get('total_bonus', 0)*0.3
                            
                            payment_line['payment_date'] = date_temp_sr
                            payment_line['payment_time_id'] = 1
                            payline_obj.create(cr, uid, payment_line)
                        
                        # chi gui mail khi duoc bat
                        #if applicant.is_erp_mail:
                        #    email_ids = self.pool.get('email.template').search(cr, uid, [('model', '=', 'vhr.job.applicant'),
                        #                                                                 ('name', '=', email_template)], context=context)
                        #    if email_ids:
                        #        self.vhr_send_mail(cr, uid, email_ids[0], job_app_id)
                                
        except Exception as e:
            log.exception(e)
        return True
    
    def update_erp_bonus_payment(self, cr, uid, bonus_payment_id, context=None):
        return True
    
    def format_currency(self, cr, uid,number,context=None):
        s = '%d' % number
        groups = []
        while s and s[-1].isdigit():
            groups.append(s[-3:])
            s = s[:-3]
        return s + ','.join(reversed(groups))
    
    def _format_total_bonus(self, cr, uid, ids, fields, args, context=None):
        result = {}
        total_bonus = 0
        for data in self.browse(cr, uid, ids, context=context):
            result[data.id]={
             'total_bonus_temp':'0',
             }
            
            total_bonus = data.total_bonus
            if total_bonus >0:
                temp = self.format_currency(cr, uid, total_bonus, context)
                result[data.id]['total_bonus_temp'] =  temp
        return result

    _columns = {
        'create_date': fields.datetime('Create date'),
        'recommender_id': fields.many2one('hr.employee', 'Recommender', ondelete='restrict'),
        'applicant_id': fields.many2one('hr.applicant', 'Candidate', ondelete='restrict'),
        'job_id': fields.many2one('hr.job', 'Resource Request', ondelete='restrict', domain="[('state','in',['in_progress', 'done', 'close'])]"),
        'bonus_scheme_id': fields.many2one('vhr.erp.bonus.scheme', 'Bonus scheme', ondelete='restrict'),
        'department_id': fields.many2one('hr.department', 'Department', ondelete='restrict',
                                         domain="[('organization_class_id.level','in',[3,6])]"),
        'job_family_id': fields.many2one('vhr.job.family', 'Job family', ondelete='restrict'),
        'job_group_id': fields.many2one('vhr.job.group', 'Job group', ondelete='restrict'),
        'job_level_id': fields.many2one('vhr.job.level', 'Job level', ondelete='restrict'),
        'erp_level_id': fields.many2one('vhr.erp.level', 'ERP level', ondelete='restrict'),
        #New Job Level
        'job_level_position_id': fields.many2one('vhr.job.level.new', 'Position Level', ondelete='restrict'),
        
        'job_title_id': fields.many2one('vhr.job.title', 'Job title', ondelete='restrict'),
        'total_bonus': fields.integer('Bonus'),
        # 'total_bonus': fields.function(_get_total_bonus, method=True, type='integer', string='Total Bonus'),
        'payment_rate': fields.integer('Payment Rate'),
        'note': fields.text('Note'),
        'exclusion_id': fields.many2one('vhr.erp.bonus.exclusion', 'Exclusion', ondelete='restrict'),
        'payment_line_ids': fields.one2many('vhr.erp.bonus.payment.line', 'bonus_payment_id', 'Payment Lines'),
        'is_edit': fields.function(_check_payment_edit, method=True, type='boolean', string='Is edit'),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                         domain=[('object_id.model', '=', _name),
                                                 ('field_id.name', 'not in', ['write_date', 'audit_log_ids'])]),
        'active': fields.boolean('Active'),
        'is_specialerp':fields.boolean('Is Special ERP',),
        
        'total_bonus_temp': fields.function(_format_total_bonus, type='char', string='Date temp',
                    multi="total_bonus_temp"),
    }
    #_sql_constraints = [('unique_applicant_job', 'unique(job_id, applicant_id)', 'Request and Application are already exist')]

    _order = 'id desc'
    
    _defaults = {  
        'is_edit': True,
        'active':True,  
        }

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        reads = self.read(cr, uid, ids, ['recommender_id', 'job_id'], context=context)
        res = []
        for record in reads:
            employee = ''
            job_id = ''
            if record.get('recommender_id', ''):
                employee = record['recommender_id'][1]
            if record.get('job_id', ''):
                job_id = record['job_id'][1]
            name = employee + ' / ' + job_id
            res.append((record['id'], name))
        return res

    def create(self, cr, uid, vals, context={}):
        if 'payment_line_ids' in vals:
            total_payment_rate = 0
            total_bonus = 0
            for item in vals['payment_line_ids']:
                temp_payment = 0
                temp_bonus = 0
                # get payment rate
                if not item[0] and isinstance(item[2], dict) and 'payment_rate' in item[2]:
                    temp_payment = item[2].get('payment_rate', 0)
                total_payment_rate = total_payment_rate + temp_payment
                # get payment bonus
                if not item[0] and isinstance(item[2], dict) and 'payment_value' in item[2]:
                    temp_bonus = item[2].get('payment_value', 0)
                total_bonus = total_bonus + temp_bonus
            if total_payment_rate != 100:
                raise osv.except_osv('Validation Error !', 'Please check payment rate')
            if vals.get('bonus_scheme_id'):
                bonus = self.pool.get('vhr.erp.bonus.scheme').browse(cr, uid, vals.get('bonus_scheme_id'), context).total_bonus
                if total_bonus != bonus:
                    raise osv.except_osv('Validation Error !', 'Please check total bonus')
        res_id = super(vhr_erp_bonus_payment, self).create(cr, uid, vals, context)
        return res_id

    def write(self, cr, uid, ids, vals, context=None):
        # TODO: process before updating resource
        if not isinstance(ids, list): ids =[ids]
        payline = self.pool.get('vhr.erp.bonus.payment.line')
        total_bonus_value = 0
        if 'payment_line_ids' in vals:
            total_payment_rate = 0
            for item in vals['payment_line_ids']:
                temp_payment = 0
                temp_bonus = 0
                # check payment rate
                if (not item[0] or item[0] == 1) and isinstance(item[2], dict) and 'payment_rate' in item[2]:
                    temp_payment = item[2].get('payment_rate', 0)
                elif item[0] and item[0] != 2:
                    temp_payment = payline.browse(cr, uid, item[1], context=context).payment_rate
                # check payment value
                if (not item[0] or item[0] == 1) and isinstance(item[2], dict) and 'payment_value' in item[2]:
                    temp_bonus = item[2].get('payment_value', 0)
                elif item[0] and item[0] != 2:
                    temp_bonus = payline.browse(cr, uid, item[1], context=context).payment_value

                total_payment_rate = total_payment_rate + temp_payment
                total_bonus_value = total_bonus_value + temp_bonus
            if total_payment_rate != 100:
                raise osv.except_osv('Validation Error !', 'Please check payment rate')
        else:
            temp_bonus = 0
            for item in self.browse(cr, uid, ids[0], context).payment_line_ids:
                total_bonus_value = total_bonus_value + item.payment_value
        total_bonus = vals.get('total_bonus', self.browse(cr, uid, ids[0], context=context).total_bonus)
        if total_bonus != total_bonus_value:
            raise osv.except_osv('Validation Error !', 'Please check total bonus')
        res = super(vhr_erp_bonus_payment, self).write(cr, uid, ids, vals, context=context)
        return res

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_erp_bonus_payment, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res
    
    def deactivate(self, cr, uid, ids, context=None):
        cr.execute('update vhr_erp_bonus_payment set active=False')
        return True
    

vhr_erp_bonus_payment()
