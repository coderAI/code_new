# -*-coding:utf-8-*-
import logging
import time
import openerp

from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.osv import osv, fields
from openerp import SUPERUSER_ID
from openerp.addons.vhr_common.model.vhr_common import vhr_common

log = logging.getLogger(__name__)



class vhr_employee_assessment_result(osv.osv, vhr_common):
    _name = 'vhr.employee.assessment.result'
    _inherit = 'vhr.employee.assessment.result'
    
    def read(self, cr, user, ids, fields=None, context=None, load='_classic_read'):
        if not context:
            context = {}
        
        self.prevent_normal_emp_read_data_of_other_emp(cr, user, ids, [], [], [], context=context)
        
        if context.get('validate_read_vhr_employee_assessment_result',False):
            log.info('\n\n validate_read_vhr_employee_assessment_result')
            result_check = self.validate_read(cr, user, ids, context)
            if not result_check:
                raise osv.except_osv('Validation Error !', 'You don’t have permission to access this data !')
            
            del context['validate_read_vhr_employee_assessment_result']
        
        res =  super(vhr_employee_assessment_result, self).read(cr, user, ids, fields, context, load)
        
            
        return res
    
    def validate_read(self, cr, uid, ids, context=None):
        user_groups = self.pool.get('res.users').get_groups(cr, uid)
        if set(['vhr_cnb_manager']).intersection(set(user_groups)):
            return True
        return False
    
    def thread_import_assessment_result(self, cr, uid, import_status_id, rows, context=None):
        log.info('Begin: thread_import_assessment_result')
        try:
            db = openerp.sql_db.db_connect(cr.dbname)
            cr = db.cursor()
            import_obj = self.pool.get('vhr.import.status')
            detail_obj = self.pool.get('vhr.import.detail')
            period_obj = self.pool.get('vhr.assessment.period')
            calibration_obj = self.pool.get('vhr.assessment.calibration')
            employee_obj = self.pool.get('hr.employee')
            
            model_ids = self.pool.get('ir.model').search(cr, uid, [('model','=',self._name)])
            model_id = model_ids and model_ids[0] or False
            
            import_obj.write(cr, uid, [import_status_id], {'state': 'processing', 'num_of_rows':rows.nrows-2, 'current_row':0,'model_id': model_id})
            cr.commit()
            row_counter = 0
            success_row = 0
            for row in rows._cell_values:
                error_message = ''
                warning_message = ''
                        
                row_counter += 1
                if row_counter > 2:
                    employee_code, period_name, kpi_score, calibration_name = row[1:5]
                    vals_detail = {}
                    if employee_code and period_name:
                        employee_code = str(employee_code).strip()
                        
                        if isinstance(period_name, float):
                            period_name = int(period_name)
                        period_name = str(period_name).strip()
                        
                        calibration_name = str(calibration_name)
                        employee_ids = employee_obj.search(cr, uid, [('code','=ilike',employee_code),
                                                                     '|',('active','=',True),('active','=',False)])
                        
                        period_ids = period_obj.search(cr, uid, [('name','=ilike',period_name),
                                                                 '|',('active','=',True),('active','=',False)])
                        
                        calibration_ids = []
                        if calibration_name:
                            calibration_ids = calibration_obj.search(cr, uid, [('name','=ilike',calibration_name),
                                                                               '|',('active','=',True),('active','=',False)])
                            
                            if not calibration_ids:
                                error_message = "Calibration Name can not found"
                        
                        employee_id = employee_ids and employee_ids[0] or False
                        period_id = period_ids and period_ids[0] or False
                        calibration_id = calibration_ids and calibration_ids[0] or False
                        
                        if not employee_id:
                            error_message ='Employee Code can not found'
                        elif not period_id:
                            error_message ='Period Name can not found'
                        elif not error_message:
                            result_ids = self.search(cr, uid, [('employee_id','=',employee_id),
                                                               ('period_id','=',period_id)])
                            if result_ids:
                                warning_message = 'Update Data for Exist Employee - Period'
                            
                            try:
                                kpi_score = float(kpi_score)
                            except Exception as e:
                                error_message = 'KPI Score have to be number'
                                kpi_score = 0
                                log.error(e)
                                
                            vals = {'employee_id': employee_id,
                                    'period_id': period_id,
                                    'calibration_id': calibration_id,
                                    'kpi_score': kpi_score}
                            
                            if not error_message:
                                if result_ids:
                                    self.write(cr, uid, result_ids, vals)
                                else:
                                    self.create(cr, uid, vals)
                        
                                success_row = success_row + 1
                    else:
                        error_message = 'You have to input employee code and period name'
                    
                    if error_message or warning_message:
                        message = error_message or warning_message
                        
                        vals_detail = {'import_id': import_status_id, 
                                       'row_number' : row_counter-2, 
                                       'message': message}
                        
                        if error_message:
                            vals_detail['status'] = 'fail'
                        
                        detail_obj.create(cr, uid, vals_detail)
                        cr.commit()                
                import_obj.write(cr, uid, [import_status_id], {'current_row':row_counter-2, 'success_row':success_row})
                cr.commit()
            import_obj.write(cr, uid, [import_status_id], {'state': 'done'})
            cr.commit()
        except Exception as e:
            log.exception(e)
            import_obj.write(cr, uid, [import_status_id], {'state': 'error'})
            cr.commit()
            log.info(e)
            cr.rollback()
        finally:    
            cr.close()
        log.info('End: thread_import_assessment_result')
        return True


vhr_employee_assessment_result()