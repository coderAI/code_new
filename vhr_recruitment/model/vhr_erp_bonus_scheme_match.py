# -*-coding:utf-8-*-
import logging
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp.osv import osv, fields


log = logging.getLogger(__name__)

class vhr_erp_bonus_scheme_match(osv.osv):
    _name = 'vhr.erp.bonus.scheme.match'
    _description = 'VHR ERP Bonus Scheme match'
    
    def _check_duplicate_data(self, cr, uid, ids, context=None):
        if not isinstance(ids, list):
            ids = [ids]
        for wiz in self.browse(cr, uid, ids, context=context):
            domain = [('job_family_id', '=', wiz.job_family_id.id),
                     ('id','!=', wiz.id)]
            lst_data = self.search(cr, uid, domain, count=True, context=context)
            if lst_data>0:
                return False 
        return True
    
    _columns = {
        'job_family_id': fields.many2one('vhr.job.family','Job Family', ondelete='restrict'),
        'line_ids': fields.one2many('vhr.erp.bonus.scheme.match.line','match_id','Lines'),
        'state': fields.selection([
            ('draft','Draft'),
            ('transfer','Transfer'),
            ('done','Done'),
            ('cancel','Cancel'),
             ],'Status'),
    }
    
#    _constraints = [
#        (_check_duplicate_data, 'Duplicate Data', ['job_family_id']),
#    ]
    _defaults = {
                 'state':'draft',
    }
    
    def on_change_group_family_id(self,cr, uid, ids,group_family_id,context=None):
        context=context or {}
        line_ids = []
#        value = {}
#        match_id = ids and ids[0] or False
##        if ids:
##            old_line_ids = self.pool.get('vhr.erp.bonus.scheme.match.line').search(cr, uid,[('match_id','in',ids)])
##            self.pool.get('vhr.erp.bonus.scheme.match.line').unlink(cr, uid, old_line_ids)
#        #search for etudiant_ids with the conditions group_family_id etc
#        level_ids = self.pool.get('vhr.erp.level').search(cr, uid,[('job_family_id','=',group_family_id)])
#        for item in self.browse(cr, uid, ids, context = context):
#            if level_ids:
#                for level in self.pool.get('vhr.erp.level').browse(cr, uid, level_ids):
#                    total_bonus = level.total_bonus
#                    level_id = level.id
#                    job_level_position_id = level.job_level_position_id.id
#                    line_ids.append((1,0,{'job_level_position_id':job_level_position_id,
#                                  'erp_level_id':level_id,'total_bonus':total_bonus,'match_id':item.id}))
#        value.update(line_ids=line_ids)
#        return {'value':value}
        return True
    
    def action_load(self, cr, uid, ids, context=None):
        list_lines=[]
        level_ids = []
        if ids:
            old_line_ids = self.pool.get('vhr.erp.bonus.scheme.match.line').search(cr, uid,[('match_id','in',ids)])
            self.pool.get('vhr.erp.bonus.scheme.match.line').unlink(cr, uid, old_line_ids)
        for data in self.browse(cr, uid, ids):
            job_family_id = data.job_family_id.id if data.job_family_id else False
            if job_family_id:
                level_ids = self.pool.get('vhr.erp.level').search(cr, uid,[('job_family_id','=',job_family_id),('active','=',True),('check_import','=',False)])
                if level_ids:
                    for level in self.pool.get('vhr.erp.level').browse(cr, uid, level_ids):
                        total_bonus = level.total_bonus
                        level_id = level.id
                        job_level_position_id = level.job_level_position_id.id if level.job_level_position_id else False
                        val={
                             'job_level_position_id':job_level_position_id,
                             'erp_level_id':level_id,
                             'total_bonus':total_bonus,
                             'match_id':data.id
                            }
                        line_id = self.pool.get('vhr.erp.bonus.scheme.match.line').create(cr,uid,val,context)
                        list_lines.append(line_id)
        if list_lines:
            self.pool.get('vhr.erp.level').write(cr, uid, level_ids,{'check_import':True}, context)
            self.write(cr, uid, ids, {'state': 'transfer'})
        return True
    
    def action_match(self, cr, uid, ids, context=None):
        bonus_scheme_obj = self.pool.get('vhr.erp.bonus.scheme')
        job_group_obj = self.pool.get('vhr.job.group')
        for data in self.browse(cr, uid, ids):
            job_family_id = data.job_family_id.id if data.job_family_id else False
            if job_family_id:
                if data.line_ids:
                    for line in data.line_ids:
                        erp_level_id = line.erp_level_id.id if line.erp_level_id else False
                        paymenttime1_id  = line.erp_level_id.paymenttime1_id.id if line.erp_level_id and line.erp_level_id.paymenttime1_id else False
                        payment1rate  = line.erp_level_id.payment1rate if line.erp_level_id else 0
                        paymenttime2_id  = line.erp_level_id.paymenttime2_id.id if line.erp_level_id and line.erp_level_id.paymenttime2_id else False
                        payment2rate  = line.erp_level_id.payment2rate if line.erp_level_id else 0
                        paymenttime3_id  = line.erp_level_id.paymenttime3_id.id if line.erp_level_id and line.erp_level_id.paymenttime3_id else False
                        payment3rate  = line.erp_level_id.payment3rate if line.erp_level_id else 0
                        job_level_position_id = line.job_level_position_id.id if line.job_level_position_id else False
                        total_bonus =  line.total_bonus or 0
                        job_group_ids = job_group_obj.search(cr, uid, [('job_family_id','=', job_family_id),('active','=',True)], context=context)
                        if job_group_ids:
                            for group in job_group_obj.browse(cr, uid, job_group_ids):
                                vals1 = {
                                        'erp_level_id':erp_level_id,
                                        'job_family_id': job_family_id,
                                        'job_group_id': group.id or False,
                                        'job_level_position_id':job_level_position_id ,
                                        'total_bonus': total_bonus,
                                        'paymenttime1_id':paymenttime1_id,
                                        'payment1rate':payment1rate,
                                        'paymenttime2_id':paymenttime2_id or False,
                                        'payment2rate':payment2rate or 0,
                                        'paymenttime3_id':paymenttime3_id or False,
                                        'payment3rate':payment3rate or 0,
                                        }
                                bonus_scheme_obj.create(cr, uid, vals1, context)
        self.write(cr, uid, ids, {'state': 'done'})
        return True
    
    def action_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'cancel'})
        return True
    
#    def set_active_data_old(self, cr, uid, ids, context=None):
#        cr.execute('update vhr_erp_bonus_payment_line set active=False')
#        return True
    # Form filling
    def unlink(self, cr, uid, ids, context=None):
        imports = self.read(cr, uid, ids, ['state'], context=context)
        unlink_ids = []
        for s in imports:
            if s['state'] in ['draft', 'cancel']:
                unlink_ids.append(s['id'])

            else:
                raise osv.except_osv('Invalid Action!', 'In import to delete a confirmed, you must cancel it before!')

        return osv.osv.unlink(self, cr, uid, unlink_ids, context=context)
    
        
vhr_erp_bonus_scheme_match()

class vhr_erp_bonus_scheme_match_line(osv.osv):
    _name = 'vhr.erp.bonus.scheme.match.line'
    _description = 'VHR ERP Bonus Scheme Match Lines'
    _columns = {
                'job_level_position_id': fields.many2one('vhr.job.level.new', 'Position Level'),
                'erp_level_id': fields.many2one('vhr.erp.level','ERP Level'),
                'match_id': fields.many2one('vhr.erp.bonus.scheme.match','Match'),
                'total_bonus': fields.float('Total Bonus', digits=(12,0)),
            }
    
    def write(self, cr, uid, ids, vals, context=None):
        if not isinstance(ids, list):
            ids = [ids]
        res = super(vhr_erp_bonus_scheme_match_line, self).write(cr, uid, ids, vals, context)
        return res 
    
    def create(self, cr, uid, vals, context=None):
        return super(vhr_erp_bonus_scheme_match_line, self).create(cr, uid, vals, context)
    
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_erp_bonus_scheme_match_line, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res
    
vhr_erp_bonus_scheme_match_line()