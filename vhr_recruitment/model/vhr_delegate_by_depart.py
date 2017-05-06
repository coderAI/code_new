# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields


log = logging.getLogger(__name__)


class vhr_delegate_by_depart(osv.osv):
    _name = 'vhr.delegate.by.depart'
    _description = 'VHR Delegate By Department'
    
    def _get_department_code(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if context is None: context = {}
        hr_dept_obj = self.pool.get('hr.department')
        for item in self.browse(cr, uid, ids, context=context):
            res[item.id]= ''            
            lst_dept = hr_dept_obj.search(cr, uid, [('manager_id', '=', item.emp_del_from_id.id),
                                                    ('organization_class_id.level', 'in', [3, 6])], context=context)
            temp_dept_code =  [x.code for x in hr_dept_obj.browse(cr, uid, lst_dept, context=context)]
            if temp_dept_code:
                res[item.id]= '-'.join(temp_dept_code)  
        return res
    
    def _check_duplicate_data(self, cr, uid, ids, context=None):
        if not isinstance(ids, list):
            ids = [ids]
        for wiz in self.browse(cr, uid, ids, context=context):
            domain = [('emp_del_from_id', '=', wiz.emp_del_from_id.id),('id','!=', wiz.id)]
            lst_data = self.search(cr, uid, domain, count=True, context=context)
            if lst_data>0:
                return False 
        return True

    _columns = {
#         'department_id': fields.many2one('hr.department', 'Department', ondelete='restrict',
#                                          domain="[('organization_class_id.level','in',[3,6])]"),
        'emp_del_from_id': fields.many2one('hr.employee', 'Emp delegate from'),
        'emp_del_to_id': fields.many2one('hr.employee', 'Emp delegate to'),
        'department_code': fields.function(_get_department_code, method=True, type='char', string='Department Code'), 
        'active': fields.boolean('Active'),
        'description': fields.text('Description'),
        'department_ids':fields.many2many('hr.department','delegate_rr_department','delegate_id','department_id', 'Department', domain=[('organization_class_id.level','in', [3, 6])]),
    }

    _defaults = {
        'active': True,
    }
    
    _constraints = [
        (_check_duplicate_data, 'Emp delegate from is already exist!', ['emp_del_from_id']),
    ]
    
    _sql_constraints = [
                        ('vhr_delegate_by_depart_uniq','unique(emp_del_from_id)', 'Data is already exist!')
                        ]
    
    
    def get_delegate(self, cr, uid, delegate_from_id, context=None):
        """ get list delegate
        :param delegate_from_id: delegate from id
        :type integer: Integer value
        :returns: [] or list id of delegate to
        """
        if context is None:
            context = {}
        result = []
        if context.get('delegate'):
            result.append(delegate_from_id)
        search_domain = [('active', '=', True), ('emp_del_from_id', '=', delegate_from_id)]
        lst_del_from = self.search(cr, uid, search_domain, context=context)
        for item in self.browse(cr, uid, lst_del_from, context=context):
            # Get List dept ID from deligate item
            dept_allowed = [dept.id for dept in item.department_ids if dept]
            # if context get department_id and department_id in dept_allowed
            if context.get('department_id') and context['department_id'] in dept_allowed:
                result.append(item.emp_del_to_id.id)
        return list(set(result))
    
    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        if context is None:
            context = {}
        context['show_domain'] =  True
        reads = self.read(cr, uid, ids, ['emp_del_from_id', 'emp_del_to_id'], context=context)
        context['show_domain'] =  False
        res = []
        for record in reads:
            job = ''
            applicant = ''
            if record.get('emp_del_from_id', ''):
                job = record['emp_del_from_id'][1]
            if record.get('emp_del_to_id', ''):
                applicant = record['emp_del_to_id'][1]
            name = job + ' -> ' + applicant
            res.append((record['id'], name))
        return res
    
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_delegate_by_depart, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res

    def onchange_emp_del_from_id(self, cr, uid, ids, emp_del_from_id, context=None):
        if context is None:
            context = {}
        result = {'value': {}, 'domain': {}}
        
        dept_obj = self.pool['hr.department']
        dept_ids = dept_obj.search(cr, uid, [('manager_id', '=', emp_del_from_id),
                                             ('organization_class_id.level', 'in', [3, 6])], context=context)
        
        result['value']['department_ids'] = dept_ids
        result['domain']['department_ids'] = [('id', 'in', dept_ids)]
        return result

vhr_delegate_by_depart()
