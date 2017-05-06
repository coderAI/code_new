# -*- coding: utf-8 -*-

from openerp.osv import osv, fields


class vhr_ts_employee_expat(osv.osv):
    _name = 'vhr.ts.employee.expat'
    _columns = {
        'name': fields.char('Name'),
        'employee_id': fields.many2one('hr.employee', 'Employee'),
        'employee_code': fields.related('employee_id', 'code', type='char', string='Employee Code'),
        'active': fields.boolean('Active'),
        'description': fields.text('Description'),
        
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                          domain=[('object_id.model', '=', _name)]),
    
    }
    _defaults = {
        'active': True
    }
    
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
    
    def onchange_employee_id(self, cr, uid, ids, employee_id, context=None):
        res = {'employee_code' : '','company_id': False}
        
        if employee_id:
            employee = self.pool.get('hr.employee').read(cr, uid, employee_id, ['code','company_id'])
            res['employee_code'] = employee.get('code', '')
        
        return {'value': res}
    
    def create(self, cr, uid, vals, context=None):
        if vals.get('employee_code', False) and not vals.get('employee_id', False):
            emp_ids = self.pool.get('hr.employee').search(cr, uid, [('code','=', vals['employee_code'])])
            if emp_ids:
                vals['employee_id'] = emp_ids[0]
        
        res = super(vhr_ts_employee_expat, self).create(cr, uid, vals, context)
        
        return res
    
    

vhr_ts_employee_expat()