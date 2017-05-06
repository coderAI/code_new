# -*-coding:utf-8-*-
import logging
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp.osv import osv, fields


log = logging.getLogger(__name__)

class vhr_erp_level(osv.osv):
    _name = 'vhr.erp.level'
    _description = 'VHR ERP Level'
    _columns = {
                'code': fields.char('Code', size=64),
                'name': fields.char('Name', size=128),
                'description': fields.text('Description'),
                'job_family_id': fields.many2one('vhr.job.family','Job Family', ondelete='restrict'),
                'job_level_position_id': fields.many2one('vhr.job.level.new', 'Position Level', ondelete='restrict'),
                'total_bonus': fields.float('Total Bonus', digits=(12,0)),
                'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                                  domain=[('object_id.model', '=', _name),
                                                          ('field_id.name', 'not in',
                                                           ['write_date', 'audit_log_ids'])]),
                'active': fields.boolean('Active'),
                'payment1rate': fields.integer('Payment 1 Rate'),
                'paymenttime1_id': fields.many2one('vhr.erp.payment.time','Payment Time 1', ondelete='restrict'),
                'payment2rate': fields.integer('Payment 2 Rate'),
                'paymenttime2_id': fields.many2one('vhr.erp.payment.time','Payment Time 2', ondelete='restrict'),
                'payment3rate': fields.integer('Payment 3 Rate'),
                'paymenttime3_id': fields.many2one('vhr.erp.payment.time','Payment Time 3', ondelete='restrict'),
                'check_import': fields.boolean('Import'),
               
                }
    _defaults = {
                 'active':True,
                 'check_import':False,
    }
    
    _order = 'name asc'

    _unique_insensitive_constraints = [{'code': "ERP Level Code is already exist!"},
                                       {'name': "ERP Level Vietnamese Name is already exist!"}]

    
    def write(self, cr, uid, ids, vals, context=None):
        if not isinstance(ids, list):
            ids = [ids]
        bonus_scheme_obj = self.pool.get('vhr.erp.bonus.scheme')
        erp_level = self.browse(cr, uid, ids[0], context=context)
        payment1rate = vals.get('payment1rate', erp_level.payment1rate or 0)
        payment2rate = vals.get('payment2rate', erp_level.payment2rate or 0) 
        payment3rate = vals.get('payment3rate', erp_level.payment3rate or 0)
        job_family_id = erp_level.job_family_id.id if erp_level.job_family_id else False
        erp_level_id = erp_level.id if erp_level else False
        paymenttime1_id  = vals.get('paymenttime1_id',erp_level.paymenttime1_id.id if erp_level.paymenttime1_id else False)
        paymenttime2_id  = vals.get('paymenttime2_id',erp_level.paymenttime2_id.id if erp_level.paymenttime2_id else False)
        paymenttime3_id  = vals.get('paymenttime3_id',erp_level.paymenttime3_id.id if erp_level.paymenttime3_id else False)
        job_level_position_id = erp_level.job_level_position_id.id if erp_level.job_level_position_id else False
        total_bonus =  vals.get('total_bonus',erp_level.total_bonus or 0)
        if (payment1rate + payment2rate + payment3rate) != 100:
            raise osv.except_osv('Validation Error !', 'Payment Rate 1 + Payment Rate 2 + Payment Rate 3 = 100')
        
        scheme_ids = bonus_scheme_obj.search(cr, uid, [('job_family_id','=', job_family_id),('active','=',True),('erp_level_id','=',erp_level_id),
                                        ('job_level_position_id','=',job_level_position_id)], context=context)
        
        vals1 = {
                            #'erp_level_id':erp_level_id,
                            #'job_family_id': job_family_id,
                            #'job_group_id': group.id,
                            #'job_level_position_id':job_level_position_id ,
                            'total_bonus': total_bonus,
                            'paymenttime1_id':paymenttime1_id,
                            'payment1rate':payment1rate,
                            'paymenttime2_id':paymenttime2_id or False,
                            'payment2rate':payment2rate or 0,
                            'paymenttime3_id':paymenttime3_id or False,
                            'payment3rate':payment3rate or 0,
        }
        if scheme_ids:
            bonus_scheme_obj.write(cr, uid, scheme_ids, vals1, context)
            
        res = super(vhr_erp_level, self).write(cr, uid, ids, vals, context)
        return res 
    
    def create(self, cr, uid, vals, context=None):
        payment1rate = vals.get('payment1rate', 0)
        payment2rate = vals.get('payment2rate', 0) 
        payment3rate = vals.get('payment3rate', 0)
        if (payment1rate + payment2rate + payment3rate) != 100:
            raise osv.except_osv('Validation Error !', 'Payment Rate 1 + Payment Rate 2 + Payment Rate 3 = 100') 
        return super(vhr_erp_level, self).create(cr, uid, vals, context)
    
    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        args_new = ['|', ('name', operator, name), ('code', operator, name)] + args
        ids = self.search(cr, uid, args_new)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(vhr_erp_level, self).name_search(cr, uid, name, args, operator, context, limit)

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_erp_level, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res
    
vhr_erp_level()

