# -*-coding:utf-8-*-
import logging
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp.osv import osv, fields


log = logging.getLogger(__name__)

class vhr_erp_bonus_scheme(osv.osv):
    _name = 'vhr.erp.bonus.scheme'
    _description = 'VHR ERP Bonus Scheme'
    
    def onchange_job_family_id(self, cr, uid, ids, job_family_id, context=None):
        domain = {'job_group_id': [('id', 'not in', [])]}
        value = {'job_group_id': False}
        group_ids = []
        if job_family_id:
            sql = '''select e.id from vhr_jobtitle_joblevel a 
                        INNER JOIN vhr_job_title b on a.job_title_id = b.id
                        INNER JOIN vhr_subgroup_jobtitle c on b.id = c.job_title_id 
                        INNER JOIN vhr_sub_group d on c.sub_group_id = d."id" 
                        INNER JOIN vhr_job_group e on d.job_group_id = e."id"
                        WHERE e.job_family_id = %s 
                        '''%(job_family_id)
            cr.execute(sql)
            group_ids = map(lambda x: x[0], cr.fetchall())
            if group_ids:
                domain['job_group_id'] = [('id', 'in', group_ids)]
        return {'value':value, 'domain': domain}
    
    def _check_duplicate_data(self, cr, uid, ids, context=None):
        if not isinstance(ids, list):
            ids = [ids]
        for wiz in self.browse(cr, uid, ids, context=context):
            domain = [('job_family_id', '=', wiz.job_family_id.id), ('job_group_id', '=', wiz.job_group_id.id),('job_level_position_id', '=', wiz.job_level_position_id.id)
                     ,('erp_level_id','=',wiz.erp_level_id.id),('id','!=', wiz.id)]
            lst_data = self.search(cr, uid, domain, count=True, context=context)
            if lst_data>0:
                return False 
        return True
    
    _columns = {
        'job_family_id': fields.many2one('vhr.job.family','Job Family', ondelete='restrict'),
        'job_group_id': fields.many2one('vhr.job.group','Job Group', domain="[('job_family_id','=',job_family_id)]", ondelete='restrict'),
        'job_level_id': fields.many2one('vhr.job.level','Job Level', ondelete='restrict'),
        #New Job Level
        'job_level_position_id': fields.many2one('vhr.job.level.new', 'Position Level', ondelete='restrict'),
        'erp_level_id': fields.many2one('vhr.erp.level','ERP Level', ondelete='restrict'),
        
        'total_bonus': fields.float('Total Bonus', digits=(12,0)),
        'payment1rate': fields.integer('Payment 1 Rate'),
        'paymenttime1_id': fields.many2one('vhr.erp.payment.time','Payment Time 1', ondelete='restrict'),
        'payment2rate': fields.integer('Payment 2 Rate'),
        'paymenttime2_id': fields.many2one('vhr.erp.payment.time','Payment Time 2', ondelete='restrict'),
        'payment3rate': fields.integer('Payment 3 Rate'),
        'paymenttime3_id': fields.many2one('vhr.erp.payment.time','Payment Time 3', ondelete='restrict'),
        'bonus_rate_by_dept_ids': fields.one2many('vhr.erp.bonus.rate.by.dept', 'erp_bonus_id', 'Rate By Dept'),
        'description': fields.text('Description'),
        'active': fields.boolean('Active'),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                         domain=[('object_id.model', '=', _name),
                                                 ('field_id.name', 'not in', ['write_date', 'audit_log_ids'])]),
     'total_bonus_specialerp': fields.float('Total Bonus Special', digits=(12,0)),
     'special_job_id': fields.many2one('hr.job','Job'),
     'bonus_for_recruiter': fields.float('Bonus for Recruiter', digits=(12,0)),
    }
    
    _constraints = [
        (_check_duplicate_data, 'Duplicate Data', ['erp_level_id','job_level_position_id', 'job_family_id', 'job_group_id']),
    ]
    _defaults = {
        'active': True,
    }
    
    def write(self, cr, uid, ids, vals, context=None):
        if not isinstance(ids, list):
            ids = [ids]
        bonus_sheme = self.browse(cr, uid, ids[0], context=context)
        payment1rate = vals.get('payment1rate', bonus_sheme.payment1rate)
        payment2rate = vals.get('payment2rate', bonus_sheme.payment2rate) 
        payment3rate = vals.get('payment3rate', bonus_sheme.payment3rate)
        if (payment1rate + payment2rate + payment3rate) != 100:
            raise osv.except_osv('Validation Error !', 'Payment Rate 1 + Payment Rate 2 + Payment Rate 3 = 100')
        res = super(vhr_erp_bonus_scheme, self).write(cr, uid, ids, vals, context)
        return res 
    
    def create(self, cr, uid, vals, context=None):
        payment1rate = vals.get('payment1rate', 0)
        payment2rate = vals.get('payment2rate', 0) 
        payment3rate = vals.get('payment3rate', 0)
        if (payment1rate + payment2rate + payment3rate) != 100:
            raise osv.except_osv('Validation Error !', 'Payment Rate 1 + Payment Rate 2 + Payment Rate 3 = 100') 
        return super(vhr_erp_bonus_scheme, self).create(cr, uid, vals, context)
    
    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        reads = self.read(cr, uid, ids, ['job_family_id'], context=context)
        res = []
        for record in reads:
            #job_level_id = ''
            job_family_id = ''
#            if record.get('job_level_id', ''):
#                job_level_id = record['job_level_id'][1]
            if record.get('job_family_id', ''):
                job_family_id = record['job_family_id'][1]
            name = job_family_id
            res.append((record['id'], name))
        return res

    def get_time_for_payment(self, cr, uid, payment_time, offer_contract_type, offer_join_date, context=None):
        paytime = self.pool.get('vhr.erp.payment.time').browse(cr, uid, payment_time, context=context)
        life_of_contract = self.pool.get('hr.contract.type').browse(cr, uid, offer_contract_type, context=context).life_of_contract
        #result = datetime.today()
        result =  datetime.strptime(offer_join_date, '%Y-%m-%d')
        if paytime.payment_time == 'FINISH_PROBATION':
            month = life_of_contract if life_of_contract else 0
            result = result + relativedelta(months=month)
        else:
            day_add = paytime.period_days if paytime.period_days else 0
            result = result + relativedelta(days=day_add)
        return result

    def get_bonus_scheme_id(self, cr, uid, job_family_id, job_group_id, job_level_position_id, context=None):
        # search 3 cap
        bonus = []
        domain = [('job_family_id', '=', job_family_id), ('job_level_position_id', '=', job_level_position_id), ('job_group_id', '=', job_group_id),('active','=',True)]
        bonus = self.search(cr, uid, domain, context=context)
#        if not bonus:
#            domain = [('job_family_id', '=', job_family_id), ('job_level_position_id', '=', job_level_position_id)]
#            bonus = self.search(cr, uid, domain, context=context)
#        if not bonus:
#            domain = [('job_level_position_id', '=', job_level_position_id)]
#            bonus = self.search(cr, uid, domain, context=context)
        return bonus

    def get_bonus_scheme(self, cr, uid, department_code, job_family_id,\
                        job_group_id,  job_level_position_id, job_title_id,\
                        contract_type_id, offer_join_date, context=None):
        result = {}
        bonus = self.get_bonus_scheme_id(cr, uid, job_family_id, job_group_id, job_level_position_id)
        if bonus:
            result['bonus_scheme_id'] = bonus[0]
            bonus_obj = self.browse(cr, uid, bonus[0], context=context)
            rate_by_dept = self.pool.get('vhr.erp.bonus.rate.by.dept').get_bonus_rate(cr, uid, bonus[0], department_code, job_title_id)
            result['total_bonus'] = rate_by_dept * bonus_obj.total_bonus
            result['total_bonus_specialerp'] = rate_by_dept * bonus_obj.total_bonus_specialerp
            result['erp_level_id']= bonus_obj.erp_level_id.id
            if bonus_obj.paymenttime1_id:
                result['payment1rate'] = bonus_obj.payment1rate
                result['payment1'] = rate_by_dept * bonus_obj.total_bonus * bonus_obj.payment1rate/100
                result['payment1_date'] = self.get_time_for_payment(cr, uid, bonus_obj.paymenttime1_id.id, contract_type_id, offer_join_date)
                result['payment_time_id_1'] = bonus_obj.paymenttime1_id.id
            if bonus_obj.paymenttime2_id:
                result['payment2rate'] = bonus_obj.payment2rate
                result['payment2'] = rate_by_dept * bonus_obj.total_bonus * bonus_obj.payment2rate/100
                result['payment2_date'] = self.get_time_for_payment(cr, uid, bonus_obj.paymenttime2_id.id, contract_type_id, offer_join_date)
                result['payment_time_id_2'] = bonus_obj.paymenttime2_id.id
            if bonus_obj.paymenttime3_id:
                result['payment3rate'] = bonus_obj.payment3rate
                result['payment3'] = rate_by_dept * bonus_obj.total_bonus * bonus_obj.payment3rate/100
                result['payment3_date'] = self.get_time_for_payment(cr, uid, bonus_obj.paymenttime3_id.id, contract_type_id, offer_join_date)
                result['payment_time_id_3'] = bonus_obj.paymenttime3_id.id
        return result

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_erp_bonus_scheme, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res
    
    def deactivate(self, cr, uid, ids, context=None):
        cr.execute('update vhr_erp_bonus_scheme set active=False')
        return True

vhr_erp_bonus_scheme()

