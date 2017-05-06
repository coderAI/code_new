# -*- coding: utf-8 -*-
import logging
from datetime import datetime

from openerp.osv import osv, fields
from openerp.tools.translate import _
import openerp

log = logging.getLogger(__name__)

MISS_DATA = 'Employee Code or From Date or To Date is missing'
MISS_EMP = 'The employee with code %s is missing'
OVERLAP = 'The record is overlap'
WRONG_PERIOD = 'To Date must be greater than From Date'

class vhr_duty_free(osv.osv):
    _name = 'vhr.duty.free'
    _inherit = 'vhr.duty.free'

    def cron_active_record(self, cr, uid, context=None):
        log.info('vhr_duty_free cron_active_record start')
        active_record_ids, inactive_record_ids = self.update_active_of_record_in_object_cm(cr, uid)
            
        log.info('vhr_duty_free cron_active_record end')
        return True
    
    
    def update_active_of_record_in_object_cm(self, cr, uid, context=None):
        """
        Update active of record base on from_date, to_date, active
        Object need to update effect_to when possible
        """
        active_record_ids = []
        inactive_record_ids = []
        if object:
            today = datetime.today().date()
            
            active_record_ids = self.search(cr, uid, [('active','=',False),
                                                             ('from_date','<=',today),
                                                              '|',('to_date','=',False),
                                                                  ('to_date','>=',today)])
        
            #Get records have active=True need to update active=False
            inactive_record_ids = self.search(cr, uid, [('active','=',True),
                                                              '|',('to_date','<',today),
                                                                  ('from_date','>',today)])
             
#             record_ids = active_record_ids + inactive_record_ids
            for record_id in active_record_ids:
                super(vhr_duty_free, self).write(cr, uid, record_id, {'active': True})
            
            if inactive_record_ids:
                super(vhr_duty_free, self).write(cr, uid, inactive_record_ids, {'active': False})
                
            
        return active_record_ids, inactive_record_ids

    def _get_employee_id_by_code(self, cr, uid, code, context=None):
        if context is None:
            context = {}
        if not code:
            return False
        employee_ids = self.pool['hr.employee'].search(cr, uid, [('code', '=', code)])
        if not employee_ids:
            return False
        return employee_ids[0]

    def _convert_date_format(self, string_date):
        if not string_date:
            return False
        return datetime.strptime(string_date, '%d/%m/%Y').strftime('%Y-%m-%d')

    def _is_overlap(self, cr, uid, employee_id, from_date, to_date, context=None):
        if context is None:
            context = {}
        if not employee_id or not from_date or not to_date:
            return False
        prev_pit_ids = self.search(cr, uid, [('employee_id', '=', employee_id), ('active', '=', True)], context=context)
        if not prev_pit_ids:
            return False
        prev_pits = self.browse(cr, uid, prev_pit_ids, context=context)
        date_from = datetime.strptime(from_date, '%d/%m/%Y')
        date_to = datetime.strptime(to_date, '%d/%m/%Y')
        for prev_pit in prev_pits:
            prev_date_from = datetime.strptime(prev_pit.from_date, '%Y-%m-%d')
            prev_date_to = datetime.strptime(prev_pit.to_date, '%Y-%m-%d')
            if (prev_date_from <= date_from and date_from <= prev_date_to) or \
                    (prev_date_from <= date_to and date_to <= prev_date_to) or \
                    (date_from <= prev_date_to and prev_date_to <= date_to):
                return True
        return False


    def thread_import_pit(self, cr, uid, import_status_id, rows, context=None):
        if context is None:
            context = {}
        log.info('Begin: thread_import_pit')
        import_obj = self.pool.get('vhr.import.status')
        try:
            db = openerp.sql_db.db_connect(cr.dbname)
            cr = db.cursor()
            model_ids = self.pool.get('ir.model').search(cr, uid, [('model', '=', self._name)])
            model_id = model_ids and model_ids[0] or False
            detail_obj = self.pool['vhr.import.detail']
            import_obj.write(cr, uid, [import_status_id],
                             {'state': 'processing', 'num_of_rows': rows.nrows, 'current_row': 0, 'model_id': model_id})
            cr.commit()
            row_counter = 0
            success_row = 0
            for row in rows._cell_values:
                row_counter += 1
                if row_counter > 2:
                    vals_detail = {}
                    emp_code, from_date, to_date, description = row[0:4]
                    if emp_code and from_date and to_date:
                        employee_id = self._get_employee_id_by_code(cr, uid, emp_code, context=context)
                        if employee_id:
                            if datetime.strptime(to_date, '%d/%m/%Y') > datetime.strptime(from_date, '%d/%m/%Y'):
                                is_over_lap = self._is_overlap(cr, uid, employee_id, from_date, to_date, context=context)
                                if not is_over_lap:
                                    from_date = from_date and self._convert_date_format(from_date) or False
                                    to_date = to_date and self._convert_date_format(to_date) or False
                                    vals = {
                                        'employee_id': employee_id,
                                        'from_date': from_date,
                                        'to_date': to_date,
                                        'description': description,
                                    }
                                    self.create(cr, uid, vals, context=context)
                                    success_row = success_row + 1
                                else:
                                    vals_detail = {'import_id': import_status_id, 'row_number': row_counter,
                                                   'message': OVERLAP}
                            else:
                                vals_detail = {'import_id': import_status_id, 'row_number': row_counter,
                                               'message': WRONG_PERIOD}
                        else:
                            vals_detail = {'import_id': import_status_id, 'row_number': row_counter,
                                           'message': MISS_EMP % (emp_code)}
                    else:
                        vals_detail = {'import_id': import_status_id, 'row_number': row_counter, 'message': MISS_DATA}
                    if vals_detail:
                        detail_obj.create(cr, uid, vals_detail)
                        cr.commit()
                import_obj.write(cr, uid, [import_status_id], {'current_row': row_counter, 'success_row': success_row})
                cr.commit()
            import_obj.write(cr, uid, [import_status_id], {'state': 'done'})
            cr.commit()
            self.update_active_of_record_in_object_cm(cr, uid, context=context)
            cr.commit()
        except Exception as e:
            import_obj.write(cr, uid, [import_status_id], {'state': 'error'})
            cr.commit()
            log.info(e)
            cr.rollback()
        finally:
            cr.close()
        log.info('End: thread_import_pit')
        return True

vhr_duty_free()