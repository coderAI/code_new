# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields



log = logging.getLogger(__name__)


class vhr_employee_assessment_result(osv.osv):
    _name = 'vhr.employee.assessment.result'
    _description = 'VHR Employee Assessment Result'

    _columns = {
        'name': fields.char('Name', size=128),
        'employee_id': fields.many2one('hr.employee', 'Employee', ondelete='restrict'),
        'employee_code': fields.related('employee_id', 'code', type="char", string="Employee Code"),
        'period_id': fields.many2one('vhr.assessment.period', 'Period', ondelete='restrict'),
        'calibration_id': fields.many2one('vhr.assessment.calibration', 'Calibration', ondelete='restrict'),
        'kpi_score': fields.float('KPI Score'),
        'from_date': fields.related('period_id', 'from_date', type="date", string="From Date"),
        'to_date': fields.related('period_id', 'to_date', type="date", string="To Date"),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                          domain=[('object_id.model', '=', _name),
                                                  ('field_id.name', 'not in',
                                                   ['write_date', 'audit_log_ids'])]),
    }
    _order = "period_id desc, employee_id"

    _unique_insensitive_constraints = [{'employee_id': "Assessment result of employee at period is already exist!",
                                        'period_id': "Assessment result of employee at period is already exist!"
                                        }]
    
    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        
        res = super(vhr_employee_assessment_result, self).default_get(cr, uid, fields, context=context)
        
        if context.get('duplicate_active_id', False):
            columns =  self._columns
            fields = columns.keys()
            
            newres = self.copy_data(cr, uid, context['duplicate_active_id'])
            
            for key in res:
                if key not in new_res:
                    new_res[key] = res[key]
            
            newres['audit_log_ids'] = []
            return newres
        
        return res
            
    def onchange_employee_id(self, cr, uid, ids, employee_id , context=None):
        res = {'employee_code': False}
        if employee_id:
            employee = self.pool.get('hr.employee').read(cr, uid, employee_id, ['code'])
            res['employee_code'] = employee.get('code', False)
        
        return {'value': res}
    
    def onchange_period_id(self, cr, uid, ids, period_id, context=None):
        res= {'from_date': False, 'to_date': False}
        
        if period_id:
            period = self.pool.get('vhr.assessment.period').read(cr, uid, period_id, ['from_date','to_date'])
            res['from_date'] = period.get('from_date', False)
            res['to_date'] = period.get('to_date', False)
        
        return {'value': res}
    
    def name_get(self, cr, uid, ids, context=None):
        if not ids or False in ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        
        reads = self.read(cr, uid, ids, ['employee_id'], context=context)
        res = []
        for record in reads:
                name = record.get('employee_id',False) and record['employee_id'][1]
                res.append((record['id'], name))
        return res
    
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_employee_assessment_result, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res


vhr_employee_assessment_result()