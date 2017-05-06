# -*- coding: utf-8 -*-
import logging

from openerp.osv import osv, fields
from openerp.addons.vhr_common.model.vhr_common import vhr_common
from openerp.tools.translate import _

log = logging.getLogger(__name__)


class vhr_family_deduct(osv.osv, vhr_common):
    _name = 'vhr.family.deduct'
    _description = 'VHR Dependant deduction'

    _columns = {
        'name': fields.related('employee_id', 'name', type='char', string='Name'),
        'employee_id': fields.many2one('hr.employee', 'Employee'),
        'emp_code': fields.related('employee_id', 'code', type='char', string='Employee Code'),
        'company_id': fields.related('employee_id', 'company_id', type='many2one', relation='res.company', string='Company'),
        'company_code': fields.related('company_id', 'code', type='char', string='Company'),
        'line_ids': fields.one2many('vhr.family.deduct.line', 'family_deduct_id', 'Line'),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                         domain=[('object_id.model', '=', _name),
                                                 ('field_id.name', 'not in',
                                                  ['write_date', 'audit_log_ids'])]),
    }



    def onchange_employee(self, cr, uid, ids, employee_id, context=None):
        res = {'value': {'company_id': False,'emp_code': ''}, 'domain': {}}
        if employee_id:
            # TODO: check condition later
            employee = self.pool.get('hr.employee').read(cr, uid, employee_id, ['company_id','code'])
            company_id = employee.get('company_id', False) and employee['company_id'][0]
            res['value']['company_id'] = company_id
            res['value']['emp_code'] = employee.get('code','')
            
            employee_instance_obj = self.pool.get('vhr.employee.instance')
            instance_ids = employee_instance_obj.search(cr, uid, [('employee_id', '=', employee_id),
                                                                  ('company_id', '=', company_id)],
                                                                  order='date_start desc')
            res['value']['employee_instance_id'] = instance_ids and instance_ids[0] or False
            res['value']['line_ids'] = [(6, 0, [])]
        return res

    def create(self, cr, uid, vals, context=None):
        res = super(vhr_family_deduct, self).create(cr, uid, vals, context=context)
        line_ids = self.read(cr, uid, res, ['line_ids'])
        line_ids = line_ids.get('line_ids', [])
        self.pool.get('vhr.family.deduct.line').check_overlap_date(cr, uid, line_ids, context)

        return res

    def write(self, cr, uid, ids, vals, context=None):
        res = super(vhr_family_deduct, self).write(cr, uid, ids, vals, context=context)
        line_ids = self.read(cr, uid, ids, ['line_ids'])
        line_ids = filter(None, map(lambda x: x['line_ids'], line_ids))
        line_temp_ids = []
        for i in line_ids:
            line_temp_ids.extend(i)
        self.pool.get('vhr.family.deduct.line').check_overlap_date(cr, uid, line_temp_ids, context)

        return res

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        args_new = [('name', operator, name)] + args
        ids = self.search(cr, uid, args_new, 0, None, None, context)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(vhr_family_deduct, self).name_search(cr, uid, name, args, operator, context, limit)
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if not context:
            context = {}
        
        return super(vhr_family_deduct, self).search(cr, uid, args, offset, limit, order, context, count)
    
vhr_family_deduct()