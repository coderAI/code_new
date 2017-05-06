# -*-coding:utf-8-*-
import logging
from openerp.osv import osv, fields
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from dateutil import relativedelta
import time

log = logging.getLogger(__name__)

class vhr_erp_bonus_payment_line_reruitment_mail(osv.osv):
    _name = 'vhr.erp.bonus.payment.line.reruitment.mail'
    _description = 'VHR ERP Bonus Payment Line Mail'
    
    def action_payment(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'payment'})
        return True
    
    def action_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'cancel'})
        return True
    
    def _format_date_payment(self, cr, uid, ids, fields, args, context=None):
        result = {}
        for data in self.browse(cr, uid, ids, context=context):
            result[data.id]={
             'payment_date_temp':'',
             }
            
            payment_date = data.payment_date
            if payment_date:
                result[data.id]['payment_date_temp'] =  datetime.strptime(payment_date,'%Y-%m-%d').strftime('%m/%Y')
        return result 
    
    def format_currency(self, cr, uid,number,context=None):
        s = '%d' % number
        groups = []
        while s and s[-1].isdigit():
            groups.append(s[-3:])
            s = s[:-3]
        return s + ','.join(reversed(groups))
    
    def _format_payment_value(self, cr, uid, ids, fields, args, context=None):
        result = {}
        for data in self.browse(cr, uid, ids, context=context):
            result[data.id]={
             'payment_value_temp':'0',
             }
            
            payment_value = data.payment_value
            if payment_value >0:
                temp = self.format_currency(cr, uid, payment_value, context)
                result[data.id]['payment_value_temp'] =  temp
        return result
    
    
    
    _columns = {
        'bonus_payment_id': fields.many2one('vhr.erp.bonus.payment.reruitment.mail', 'Bonus Payment', ondelete='cascade'),
        'applicant_id':  fields.related('bonus_payment_id','applicant_id', type='many2one', relation='hr.applicant', string='Candidate'),
        'exclusion_id':  fields.related('bonus_payment_id','exclusion_id', type='many2one', relation='vhr.erp.bonus.exclusion', string='Exclusion'), 
        'payment_time_id': fields.many2one('vhr.erp.payment.time', 'Payment Time', ondelete='restrict'),
        'payment_rate': fields.integer('Payment Rate'),
        'payment_value': fields.integer('Payment Value'),
        'payment_date': fields.date('Month of paid'),
        'note': fields.text('Note'),
        'state': fields.selection([
            ('draft','Draft'),
            ('payment','Paid'),
             ('cancel','Cancel'),
             ], 'State'),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                         domain=[('object_id.model', '=', _name),
                                                 ('field_id.name', 'not in', ['write_date', 'audit_log_ids'])]),
    'active': fields.boolean('Active'),
    'payment_date_temp': fields.function(_format_date_payment, type='char', string='Date temp',
                    multi="payment_date_temp"),
    
     'payment_value_temp': fields.function(_format_payment_value, type='char', string='Value Temp',
                    multi="payment_value_temp"),
#    
#      'month_of_paid': fields.function(_month_of_paid, type='char', string='Month of paid',
#                    multi="month_of_paid"),
                
    }

    _defaults = {
        'state': 'draft',
        'active':True,
    }
    _rec_name = 'payment_date'
    _order = 'payment_date asc'
            
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_erp_bonus_payment_line_reruitment_mail, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res

vhr_erp_bonus_payment_line_reruitment_mail()
