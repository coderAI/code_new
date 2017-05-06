# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields


log = logging.getLogger(__name__)


class vhr_permission_location(osv.osv):
    _name = 'vhr.permission.location'
    _description = 'VHR Permission Location'
    
    
    _columns = {
        'name': fields.char('Name', size=128),
        'employee_id': fields.many2one('hr.employee', string='Employee', ondelete='restrict'),
        'company_ids': fields.many2many('res.company','company_permission_location','permission_id','company_id','Company'),
        'office_ids': fields.many2many('vhr.office','office_permission_location','permission_id','office_id','Office'),
        'department_fa_ids': fields.many2many('hr.department','department_fa_permission_location','permission_id','department_id','Department FA'),
        'description': fields.text("Description"),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                         domain=[('object_id.model', '=', _name),
                                                 ('field_id.name', 'not in',
                                                  ['write_date', 'audit_log_ids'])]),
    }

    _unique_insensitive_constraints = [{'employee_id': "Employee is already exist!",
                                        }]
    
    
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

    def get_list_employee_can_use_based_on_permission_location(self, cr, uid, employee_id, context=None):
        """
            Return list employee base on vhr.permission.location
            Return None if dont set company_ids and office_ids or can not find employee_id in vhr_permission_location
        """
        if not context:
            context = {}
            
        if employee_id:
            employee_obj = self.pool.get('hr.employee')
            record_ids = self.search(cr, uid, [('employee_id','=',employee_id)])
            if record_ids:
                record = self.read(cr, uid, record_ids[0], ['company_ids','office_ids'])
                company_ids = record.get('company_ids',[])
                office_ids = record.get('office_ids',[])
                
                domain = []
                if company_ids:
                    domain.append(('company_id','in',company_ids))
                
                if office_ids:
                    domain.append(('office_id','in',office_ids))
                
                if domain:
                    employee_ids = employee_obj.search(cr, uid, domain)
                    return employee_ids
        
        return None
    
    def get_employees_can_used_for_user_based_on_permission_location(self, cr, uid, user_id, context=None):
        res = None
        if user_id:
            employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=',user_id)])
            if employee_ids:
                res = self.get_list_employee_can_use_based_on_permission_location(cr, uid, employee_ids[0], context)
        
        return res
    
    def is_able_to_manage_on_location(self, cr, uid, check_emp_id, company_id, office_id, context=None):
        if check_emp_id and company_id and office_id:
            record = self.read(cr, uid, check_emp_id, ['company_ids','office_ids'])
            company_ids = record.get('company_ids',[])
            office_ids = record.get('office_ids',[])
            if company_ids and company_id not in company_ids:
                    return False
                
            elif office_ids and office_id not in office_ids:
                return False
        
        return True
    
    def is_able_to_control_employee_based_on_permission_location(self, cr, uid, employee_id, check_emp_id, context=None):
        if not context:
            context = {}
        if employee_id and check_emp_id:
            record_ids = self.search(cr, uid, [('employee_id','=',check_emp_id)])
            if record_ids:
                record = self.read(cr, uid, record_ids[0], ['company_ids', 'office_ids'])
                company_ids = record.get('company_ids',[])
                office_ids = record.get('office_ids',[])
                
                if context.get('company_id', False):
                    emp_company_id = context.get('company_id', False)
                    emp_office_id = context.get('office_id', False)
                    
                else:
                    employee = self.pool.get('hr.employee').read(cr, uid, employee_id, ['company_id','office_id'])
                    emp_company_id = employee.get('company_id', False) and employee['company_id'][0] or False
                    emp_office_id = employee.get('office_id', False) and employee['office_id'][0] or False
                
                if company_ids and emp_company_id not in company_ids:
                    return False
                
                elif office_ids and emp_office_id not in office_ids:
                    return False
        
        return True
                
            
    
    def create(self, cr, uid, vals, context=None):
        res = super(vhr_permission_location, self).create(cr, uid, vals, context)
        
        if res:
            self.check_empty_data(cr, uid, res, context)
        
        return res
    
    def write(self, cr, uid, ids, vals, context=None):
        res = super(vhr_permission_location, self).write(cr, uid, ids, vals, context)
        
        self.check_empty_data(cr, uid, ids, context)
        
        return res
    
    def check_empty_data(self, cr ,uid, ids, context=None):
        """
        Can not empty both field company_ids and office_ids
        """
        if ids:
            if not isinstance(ids, list):
                ids = [ids]
            
            for record in self.read(cr, uid, ids, ['company_ids','office_ids','department_fa_ids']):
                company_ids = record.get('company_ids', [])
                office_ids = record.get('office_ids', [])
                department_fa_ids = record.get('department_fa_ids', [])
                if not company_ids and not office_ids and not department_fa_ids:
                    raise osv.except_osv('Validate Error !', 
                                         "You have to input company, office or department FA ! ")
        
        return True
    
    
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_permission_location, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res
            
                    


vhr_permission_location()