# -*- coding: utf-8 -*-
import logging
from openerp.osv import osv, fields
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import datetime, timedelta

log = logging.getLogger(__name__)

class vhr_ts_timesheet_period(osv.osv):
    _name = 'vhr.ts.timesheet.period'

    _columns = {
        'name': fields.char('Name', size=64),
        'from_date': fields.date('From Date'),
        'to_date': fields.date('To Date'),
        'close_date': fields.date('Close Date'),
        'month': fields.integer('Month'),
        'year': fields.integer('Year'),
        'description': fields.text('Description'),
        'detail_ids': fields.one2many('vhr.ts.timesheet.detail', 'timesheet_period_id', "Timesheet Detail"),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                         domain=[('object_id.model', '=', _name),
                                                 ('field_id.name', 'not in', ['write_date', 'audit_log_ids'])]),
    }


    _order = "from_date desc"

    _defaults = {
    }

    def _check_overlap(self, cr, uid, res_id, context=None):
        check_date = self.read(cr, uid, res_id, ['from_date', 'to_date', 'close_date'], context=context)
        if check_date['from_date'] >= check_date['to_date']:
            raise osv.except_osv(_('Validation Error!'),
                                 _('To Date must be > From Date !'))
        overlap_ids = self.search(cr, uid,
                                  [
                                      ('id', '!=', res_id),
                                      ('from_date', '=', check_date['from_date']),
                                      ('to_date', '=', check_date['to_date'])
                                  ])
        if overlap_ids:
            from_date = datetime.strptime(check_date['from_date'],DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y")
            to_date = datetime.strptime(check_date['to_date'],DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y")
            raise osv.except_osv('Validation Error!',
                                 'Timesheet Period from %s to %s is overlapped!' % (
                                     from_date, to_date))
    
    def onchange_close_date(self, cr, uid, ids, date_to, close_date, context=None):
        res = {'value': {}, 'warning': {}}
        if date_to and close_date and close_date < date_to:
            res['warning'] = {'title': _('Validation Error!'),
                              'message': _('Close Date must be >= To Date !')}
            res['value']['close_date'] = self.get_close_date(cr, uid, date_to)
        return res

    def onchange_date(self, cr, uid, ids, date_from, date_to, context=None):
        res = {'value': {'name': '', 'month': 0, 'year': 0}, 'warning': {}}
        if date_from and date_to:
            if date_to <= date_from:
                date_to = False
                res['value']['to_date'] = False
                res['value']['close_date'] = False
                res['value']['month'] = 0
                res['value']['year'] = 0
                res['warning'] = {'title': _('Validation Error!'),
                                  'message': _('To Date must be > From Date !')}
            else:
                res['value']['name'] = self.get_period_name(cr, uid, date_from, date_to, context)
        if date_to:
            res['value']['close_date'] = self.get_close_date(cr, uid, date_to)
            
            date_to = datetime.strptime(date_to, DEFAULT_SERVER_DATE_FORMAT)
            res['value']['month'] = date_to.month
            res['value']['year'] = date_to.year
            
        return res
    
    def get_period_name(self, cr, uid, date_from, date_to, context=None):
        name = ''
        if date_from and date_to:
            date_from_str = datetime.strptime(date_from, DEFAULT_SERVER_DATE_FORMAT).strftime("%d/%m/%Y")
            date_to_str = datetime.strptime(date_to, DEFAULT_SERVER_DATE_FORMAT).strftime("%d/%m/%Y")
            name = date_from_str + ' --> ' + date_to_str
        
        return name
            

    def get_close_date(self, cr, uid, to_date):
        value = self.pool.get('ir.config_parameter').get_param(cr, uid, 'ts.timesheet.detail.close.date.interval')
        try:
            value = int(value)
        except:
            value = 0
        return (datetime.strptime(to_date, DEFAULT_SERVER_DATE_FORMAT) + timedelta(
            days=value)).strftime(DEFAULT_SERVER_DATE_FORMAT)

    
    def update_data_for_timesheet_detail(self, cr, uid, ids, context=None):
        if ids:
            if not isinstance(ids, list):
                ids = [ids]
            detail_pool = self.pool.get('vhr.ts.timesheet.detail')
            for record in self.read(cr, uid, ids, ['from_date','to_date','close_date','month','year','detail_ids']):
                detail_ids = record.get('detail_ids',[])
                if detail_ids:
                    vals={'from_date': record.get('from_date',False),
                          'to_date': record.get('to_date',False),
                          'close_date': record.get('close_date',False),
                          'month': record.get('month',False),
                          'year': record.get('year',False),
                          }
                    detail_pool.write(cr, uid, detail_ids, vals)
        
        return True
    
    def check_remove_expire_timesheet_detail(self, cr, uid, ids, context=None):
        '''  Remove timesheet detail have from_date > timesheet effect_to '''
        if ids:
            if not isinstance(ids, list):
                ids = [ids]
            detail_pool = self.pool.get('vhr.ts.timesheet.detail')
            for record in self.read(cr, uid, ids, ['detail_ids']):
                detail_ids = record.get('detail_ids',[])
                if detail_ids:
                    
                    rm_detail_ids = []
                    for detail in detail_pool.browse(cr, uid, detail_ids, fields_process=['timesheet_id', 'from_date']):
                        timesheet_effect_to = detail.timesheet_id and detail.timesheet_id.effect_to or False
                        if timesheet_effect_to:
                            from_date = detail.from_date
                            from_date = datetime.strptime(from_date, DEFAULT_SERVER_DATE_FORMAT)
                            
                            timesheet_effect_to = datetime.strptime(timesheet_effect_to, DEFAULT_SERVER_DATE_FORMAT)
                            if from_date > timesheet_effect_to:
                                rm_detail_ids.append(detail.id)
                                
                    if rm_detail_ids:
                        detail_pool.unlink(cr, uid, rm_detail_ids)
        
        return True
                
    def create(self, cr, uid, vals, context=None):
        if not context:
            context = {}
        
        context['do_not_check_overlap'] = True
        res = super(vhr_ts_timesheet_period, self).create(cr, uid, vals, context=context)
        self._check_overlap(cr, uid, res, context=context)
        if res:
            self.update_data_for_timesheet_detail(cr, uid, [res], context=None)
            self.check_remove_expire_timesheet_detail(cr, uid, [res], context)
        return res

    def write(self, cr, uid, ids, vals, context=None):
        if not context:
            context = {}
        
        if set(['from_date','to_date','close_date','month','year']).intersection(set(vals.keys())):
            context['do_not_check_overlap'] = True
        res = super(vhr_ts_timesheet_period, self).write(cr, uid, ids, vals, context=context)
        for res_id in ids:
            self._check_overlap(cr, uid, res_id, context=context)
        
        if res and set(['from_date','to_date','close_date','month','year']).intersection(set(vals.keys())):
            self.update_data_for_timesheet_detail(cr, uid, ids, context)
        
        if vals.get('detail_ids', False):
            self.check_remove_expire_timesheet_detail(cr, uid, ids, context)
            
        return True

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        try:
            res = super(vhr_ts_timesheet_period, self).unlink(cr, uid, ids, context=context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res
    

vhr_ts_timesheet_period()