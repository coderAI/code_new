# -*- coding: utf-8 -*-
from datetime import datetime, date
import thread
import logging
import sys

from lxml import etree
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.osv import osv, fields
from openerp.sql_db import Cursor
from openerp.sql_db import ConnectionPool
from openerp import tools
from openerp import SUPERUSER_ID


log = logging.getLogger(__name__)


class vhr_ts_update_ot_summary(osv.osv_memory):
    _name = 'vhr.ts.update.ot.summary'

    _columns = {
                'year': fields.integer('Year'),
                }
    
    _defaults={
               'year': datetime.today().date().year,
               }
    
    def update_ot_summary(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        if ids:
            if not isinstance(ids, list):
                ids = [ids]
                
            record = self.read(cr, uid, ids[0], ['year'])
            year = record.get('year',False)
            first_date_of_year = date(year, 1, 1).strftime(DEFAULT_SERVER_DATE_FORMAT)
            last_date_of_year = date(year, 12, 31).strftime(DEFAULT_SERVER_DATE_FORMAT)
            
            ot_detail_pool = self.pool.get('vhr.ts.overtime.detail')
            ot_detail_ids = ot_detail_pool.search(cr, uid, [('overtime_sum_id','=',False),
                                                            ('date_off','>=',first_date_of_year),
                                                            ('date_off','<=',last_date_of_year)])
            
            if not ot_detail_ids:
                raise osv.except_osv('Validation Error !','Can not find any OT Detail does not link to OT Summary !')
            
            if ot_detail_ids:
                try:
                    log.info('Start running Update OT Summary')
        
                    thread.start_new_thread(vhr_ts_update_ot_summary.thread_execute, (self, cr, uid, ot_detail_ids, context) )
                except Exception as e:
                    log.exception(e)
                    log.info('Error: Unable to start thread Update OT Summary')
            
            mod_obj = self.pool.get('ir.model.data')
            act_obj = self.pool.get('ir.actions.act_window')
            result_context = {}
            if context is None:
                context = {}
            result = mod_obj.get_object_reference(cr, uid, 'vhr_timesheet', 'act_tracking_vhr_ts_update_ot_summary')
            id = result and result[1] or False
            result = act_obj.read(cr, uid, [id], context=context)[0]
            return result
            
    def create_mass_status(self, cr, uid, context=None):
        if not context:
            context = {}
        vals = {'state': 'new'}
        if context.get('type',False):
            vals['type'] = context['type']
            
        employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', uid)])
        if employee_ids:
            vals['requester_id'] = employee_ids[0]
        module_ids = self.pool.get('ir.module.module').search(cr, uid, [('name', '=', 'vhr_timesheet')])
        if module_ids:
            vals['module_id'] = module_ids[0]

        model_ids = self.pool.get('ir.model').search(cr, uid, [('model', '=', 'vhr.ts.overtime.summarize')])
        if model_ids:
            vals['model_id'] = model_ids[0]
        
        if context.get('mass_status_info', False):
            vals['mass_status_info'] = context['mass_status_info']
        mass_status_id = self.pool.get('vhr.mass.status').create(cr, uid, vals)
        return mass_status_id
    
    
    def thread_execute(self, cr, uid, ot_detail_ids, context=None):
        if not context:
            context = {}
        log.info('Start update OT Summary')

        ot_detail_pool = self.pool.get('vhr.ts.overtime.detail')
        mass_status_pool = self.pool.get('vhr.mass.status')
        mass_status_detail_pool = self.pool.get('vhr.mass.status.detail')
        _pool = ConnectionPool(int(tools.config['db_maxconn']))
        # cr used to do my job
        cr = Cursor(_pool, cr.dbname, True)
        # t_cr used to create/write Mass Status/ Mass Status Detail
        t_cr = Cursor(_pool, cr.dbname, True)  # Thread's cursor

        # clear old thread in cache to free memory
        reload(sys)
        error_message = ""
        try:
            if ot_detail_ids:
                mass_status_id = self.create_mass_status(t_cr, uid, context)
                t_cr.commit()
                if mass_status_id:
                    mass_status_pool.write(t_cr, uid, [mass_status_id], {'state': 'running',
                                                                         'number_of_record': len(ot_detail_ids),
                                                                         'number_of_execute_record': 0,
                                                                         'number_of_fail_record': 0})
                    number_of_fail_record = 0
                    num_count = 0
                    t_cr.commit()
                    
                    records = ot_detail_pool.browse(cr, uid, ot_detail_ids, fields_process=['date_off','approve_date','is_compensation_leave','employee_id','overtime_sum_id'])
                    overtime_sum_pool = self.pool.get('vhr.ts.overtime.summarize')
                    update_overtime_sum_ids = []
                    recalcu_overtime_sum_ids = []
                    for record in records:
                        error_item = ''
                        try:
                            num_count += 1
                            mass_status_pool.write(t_cr, uid, [mass_status_id], {'number_of_execute_record': num_count})
                            update_ot_sum_ids, recalcu_ot_sum_ids = ot_detail_pool.check_update_ot_sum(cr, uid, record, [], [], context)
                            
                            update_overtime_sum_ids.extend(update_ot_sum_ids)
                            recalcu_overtime_sum_ids.extend(recalcu_ot_sum_ids)
                            
                        except Exception as e:
                            log.exception(e)
                            try:
                                error_item = e.message
                                if not error_item:
                                    error_item = e.value
                            except:
                                error_item = ""
                            number_of_fail_record += 1
                            employee_id = record.employee_id and record.employee_id.id or False
                        
                        if error_item:
                            mass_status_pool.write(t_cr, uid, [mass_status_id],
                                                   {'number_of_fail_record': number_of_fail_record})
                            
                            mass_status_detail_pool.create(t_cr, uid, {'mass_status_id': mass_status_id,
                                                                       'employee_id': employee_id,
                                                                       'status': 'fail',
                                                                       'message': 'ot_detail_id = ' + str(record.id) +' ;;;' + error_item})
                            t_cr.commit()
                            cr.rollback()
                        else:
                            #if dont have error, then commit 
                            t_cr.commit()
                            cr.commit()
                    
                    if update_overtime_sum_ids:
                        overtime_sum_pool.update_overtime_detail_ids(cr, SUPERUSER_ID, update_overtime_sum_ids)
                    
                    recalcu_overtime_sum_ids = [record_id for record_id in recalcu_overtime_sum_ids if record_id not in update_overtime_sum_ids]
                    if recalcu_overtime_sum_ids:
                        overtime_sum_pool.calculate_value_from_overtime_detail(cr, SUPERUSER_ID, recalcu_overtime_sum_ids)
                        
        except Exception as e:
            log.exception(e)
            try:
                error_message = e.message
                if not error_message:
                    error_message = e.value
            except:
                error_message = ""

            #If have error with first try, then rollback to clear all created holiday 
            cr.rollback()
            log.info('Error occur while Update OT Summary!')

        if error_message:
            #Use cr in here because InternalError if use t_cr
            mass_status_pool.write(t_cr, uid, [mass_status_id], {'state': 'fail', 'error_message': error_message})
        else:
            mass_status_pool.write(t_cr, uid, [mass_status_id], {'state': 'finish'})

        cr.commit()
        cr.close()

        t_cr.commit()
        t_cr.close()
        log.info('End execute update OT Summary')
        return True

                    
vhr_ts_update_ot_summary()