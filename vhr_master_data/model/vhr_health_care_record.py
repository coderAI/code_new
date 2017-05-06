# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields



log = logging.getLogger(__name__)


class vhr_health_care_record(osv.osv):
    _name = 'vhr.health.care.record'
    _description = 'VHR Health Care Record'

    _columns = {
                'name': fields.char('Name', size=256),
                'employee_id': fields.many2one('hr.employee', 'Employee'),
#                 'employee_name': fields.related('employee_id', 'name', type="char", string="Employees"),
#                 'employee_login': fields.related('employee_id', 'login', type="char", string="Employee Login"),
#                 'employee_code': fields.related('employee_id', 'code', type="char", string="Employee Code"),
        
                'department_id': fields.related('employee_id', 'department_id', type='many2one', 
                                                relation='hr.department', string='Department'),
                    
                'date': fields.date('Date'),
                'height': fields.float('Height (cm)'),
                'weight': fields.float('Weight (kg)'),
                'blood_group_id': fields.many2one('vhr.dimension', 'Blood Group', ondelete='restrict', domain=[('dimension_type_id.code', '=', 'BLOOD_GROUP'), ('active','=',True)]),
                'hospital_id': fields.many2one('vhr.hospital', 'Hospital'),
                'doctor': fields.char('Doctor'),
                'is_special': fields.boolean('Is Special'),
                'doctor_comment': fields.text('Doctor Comment'),
                'health_result': fields.selection([('good','Good'),
                                                   ('normal','Normal'),
                                                   ('not_good','Not Good')], 'Health Result'),
                'note': fields.text('Note'),
                'active': fields.boolean('Active'),
                'attached_file': fields.binary('Attached File'),
                'name_data': fields.char('Name Data', size = 255),
                'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                          domain=[('object_id.model', '=', _name),
                                                  ('field_id.name', 'not in',
                                                   ['write_date', 'audit_log_ids'])]),
    }

    _defaults = {
        'is_special': False,
        'health_result': 'normal',
        'active': True,
    }


    def name_get(self, cr, uid, ids, context=None):
        if not ids or False in ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        helth_cares = self.read(cr, uid, ids, ['employee_id'], context=context)
        res = []
        for helth_care in helth_cares:
            if helth_care.get('employee_id', False):
                name = helth_care['employee_id'][1]
                res.append((helth_care['id'], name))
        return res
    
    def onchange_employee_id(self, cr, uid, ids, employee_id, context=None):
        res = {}
        if employee_id:
            employee = self.pool.get('hr.employee').read(cr, uid, employee_id, ['department_id'])
            department_id = employee.get('department_id', False)
            res['department_id'] = department_id and department_id[0] or False
        
        return {'value': res}
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if not context:
            context = {}
              
        return super(vhr_health_care_record, self).search(cr, uid, args, offset, limit, order, context, count)


    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_health_care_record, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res


vhr_health_care_record()