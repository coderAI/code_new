# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields
from openerp.tools.translate import _
from openerp.addons.vhr_common.model.vhr_common import vhr_common

log = logging.getLogger(__name__)


class vhr_hrbp_assignment(osv.osv, vhr_common):
    _name = 'vhr.hrbp.assignment'
    _description = 'HRBP Assignment'
    
    
    _columns = {
        'name': fields.char('Name', size=128),
        'company_id': fields.many2one('res.company', 'Company'),
        'employee_id': fields.many2one('hr.employee', 'HRBP'),
        'hrbp_department_ids': fields.many2many('hr.department', 'hrbp_assignment_department_rel',
                                                'hrbp_assignment_id',
                                                'department_id', 'HRBP Of Department'),
        'ass_hrbp_department_ids': fields.many2many('hr.department', 'hrbp_assignment_department_assistant_rel',
                                                    'hrbp_assignment_id',
                                                    'department_id', 'Assistant to HRBP Of Department'),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                         domain=[('object_id.model', '=', _name),
                                                 ('field_id.name', 'not in', ['write_date', 'audit_log_ids'])]),
                
        'hrbp_department_name' : fields.char('HRBP Of Department', size=128),
        'ass_hrbp_department_name' : fields.char('Assistant to HRBP Of Department', size=128),

    }

    def _get_default_company_id(self, cr, uid, context=None):
        company_ids = self.pool.get('res.company').search(cr, uid, [('is_member', '=', False)], order="id asc")
        if company_ids:
            return company_ids[0]

    _defaults = {
        'name': 'HRBP Assignment',
        'company_id': _get_default_company_id
    }
    _sql_constraints = [
        ('unique_company_id_employee_id', 'unique(company_id, employee_id)',
         _('Company and Employee already exist!')),
    ]

    def onchange_department_ass(self, cr, uid, ids, department_ids, context=None):
        return self.onchange_department(cr, uid, ids, department_ids, context={'ass_hrbp_department_ids': 1})

    def onchange_department(self, cr, uid, ids, department_ids, context=None):
        """
        When add department into list, auto add child department of its into list
        """
        res = {'value': {}}
        if context is None:
            context = {}
        context['active_test'] = True
        field_name = 'hrbp_department_ids'
        if context.get('ass_hrbp_department_ids'):
            field_name = 'ass_hrbp_department_ids'
        if ids:
            data = self.read(cr, uid, ids[0], [field_name], context=context)
            data = data.get('%s' % field_name)
            diff_department_ids = list(set(department_ids[0][2]) - set(data))
            diff_department_ids = self.get_child_department(cr, uid,diff_department_ids, context=context)
            department_ids = [[6, False, list(set(department_ids[0][2] + diff_department_ids))]]
            res['value'][field_name] = department_ids
        else:
            child_department_ids = self.get_child_department(cr, uid, department_ids[0][2], context=context)
            res['value'][field_name] = [[6, False, list(set(department_ids[0][2] + child_department_ids))]]
        return res

    def onchange_company_id(self, cr, uid, ids, company_id, context=None):
        res = {'employee_id': ''}
        domain = {'employee_id': [('id', 'in', [])]}
        if company_id:
            working_record_obj = self.pool.get('vhr.working.record')
            wr_company_ids = working_record_obj.search(cr, uid, [('company_id', '=', company_id),
                                                                 ('state','in',['finish',False])])

            employee_ids = working_record_obj.read(cr, uid, wr_company_ids, ['employee_id'])
            employee_ids = filter(None, map(lambda a: a['employee_id'] and a['employee_id'][0] or '', employee_ids))
            domain = {'employee_id': [('id', 'in', employee_ids)]}

        return {'value': res, 'domain': domain}

    # Get list employee have contract belong to company on effect_from

    def onchange_employee_id(self, cr, uid, ids, company_id, employee_id, context=None):
        res = {'value': {'hrbp_department_id': [(6, 0, [])], 'ass_hrbp_department_id': [(6, 0, [])]}}
        if employee_id and company_id:
            department_obj = self.pool.get('hr.department')
            department_ids = department_obj.search(cr, uid, [('hrbps', '=', employee_id)])
            ass_department_ids = department_obj.search(cr, uid, [('ass_hrbps', '=', employee_id)])
            res['value']['hrbp_department_ids'] = [(6, 0, department_ids)]
            res['value']['ass_hrbp_department_ids'] = [(6, 0, ass_department_ids)]
        return res
    
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
    
    def insert_hrbp_to_department(self, cr, uid, department_ids, ass_department_ids, employee_id, context=None):
        """
            Update HRBP, Assistant HRBP in department 
        """
        
        if context is None:
            context = {}
        context.update({'from_hrbp_assignment': 1})
        department_obj = self.pool.get('hr.department')
        if department_ids is not None:
            current_hrbp_ids = department_obj.search(cr, uid, [('hrbps', '=', employee_id)])
            #Get list department will be add employee as hrbp
            add_hrbp_department_ids = list(set(department_ids) - set(current_hrbp_ids))
            #Get list department will be remove employee as hrbp
            remove_hrbp_department_ids = list(set(current_hrbp_ids) - set(department_ids))
            if remove_hrbp_department_ids:
                department_obj.write(cr, uid, remove_hrbp_department_ids, {'hrbps': [(3, employee_id)]}, context=context)
                
            if add_hrbp_department_ids:
                department_obj.write(cr, uid, add_hrbp_department_ids, {'hrbps': [(4, employee_id)]}, context=context)
        if ass_department_ids is not None:
            current_ass_hrbp_ids = department_obj.search(cr, uid, [('ass_hrbps', '=', employee_id)])
            #Get list department will be remove employee as assistant hrbp
            remove_ass_hrbp_department_ids = list(set(current_ass_hrbp_ids) - set(ass_department_ids))
            #Get list department will be add employee as  assistant hrbp
            add_ass_hrbp_department_ids = list(set(ass_department_ids) - set(current_ass_hrbp_ids))
            if remove_ass_hrbp_department_ids:
                department_obj.write(cr, uid, remove_ass_hrbp_department_ids, {'ass_hrbps': [(3, employee_id)]}, context=context)
                
            if add_ass_hrbp_department_ids:
                department_obj.write(cr, uid, add_ass_hrbp_department_ids, {'ass_hrbps': [(4, employee_id)]}, context=context)

    def create(self, cr, uid, vals, context=None):
        department_ids = vals.get('hrbp_department_ids')[0][2]
        ass_department_ids = vals.get('ass_hrbp_department_ids')[0][2]
        employee_id = vals['employee_id']
        self.insert_hrbp_to_department(cr, uid, department_ids, ass_department_ids, employee_id, context=context)

        res =  super(vhr_hrbp_assignment, self).create(cr, uid, vals, context=context)
        
        if res:
            self.update_name_for_hrbp(cr, uid, [res], context)
        
        return res

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        
        if not isinstance(ids, list):
            ids = [ids]
        
        res =  super(vhr_hrbp_assignment, self).write(cr, uid, ids, vals, context=context)
        if not context.get('from_hr_department_call_update'):
            ass_department_ids = None
            department_ids = None
            employee_id = False
            
            if set(['hrbp_department_ids','ass_hrbp_department_ids']).intersection(vals.keys()):
                record = self.read(cr, uid, ids[0], ['hrbp_department_ids','ass_hrbp_department_ids','employee_id'])
                
                department_ids     = vals.get('hrbp_department_ids', None)     and record.get('hrbp_department_ids',[])
                ass_department_ids = vals.get('ass_hrbp_department_ids', None) and record.get('ass_hrbp_department_ids',[])
                
                employee_id = record.get('employee_id', False) and record['employee_id'][0] or False
            
            if department_ids is not None or ass_department_ids is not None:
                self.insert_hrbp_to_department(cr, uid, department_ids, ass_department_ids, employee_id, context=context)
        if res:
            if (vals.get('hrbp_department_ids',False) or vals.get('ass_hrbp_department_ids',False)) and not context.get('do_not_update_name',False):
                self.update_name_for_hrbp(cr, uid, ids, context)
            elif context.get('update_name',False):
                self.update_name_for_hrbp(cr, uid, ids, context)
                
        return res
    
    def unlink(self, cr, uid, ids, context=None):
        """
            Xóa employee ra khỏi toàn bộ các phòng ban làm HRBP/ assistant HRBP
        """
        if context is None:
            context = {}
        res = False
        try:
            for record in self.read(cr, uid, ids, ['employee_id']):
                employee_id = record.get('employee_id', False) and record['employee_id'][0] or False
                self.insert_hrbp_to_department(cr, uid, [], [], employee_id, context)
                
            res = super(vhr_hrbp_assignment, self).unlink(cr, uid, ids, context)
            
        except Exception as e:
            logging.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res
    
    def update_name_for_hrbp(self, cr, uid, ids, context=None):
        if not context:
            context= {}
        department_pool = self.pool.get('hr.department')
        for record in self.read(cr, uid, ids, ['hrbp_department_ids','ass_hrbp_department_ids']):
            res= {}
            hrbp_department_ids = record.get('hrbp_department_ids',[])
            hrbp_department_name = self.get_largest_department_name(cr, uid, hrbp_department_ids, context)
            
            ass_hrbp_department_ids = record.get('ass_hrbp_department_ids',[])
            ass_hrbp_department_name = self.get_largest_department_name(cr, uid, ass_hrbp_department_ids, context)
            res['hrbp_department_name'] = hrbp_department_name
            res['ass_hrbp_department_name'] = ass_hrbp_department_name
#             self.write(cr, uid, [record['id']], res, {'from_hr_department_call_update': True})
            super(vhr_hrbp_assignment, self).write(cr, uid, [record['id']], res, context=context)
        
        return True
    
    def update_name_for_all_hrbp_assignment(self, cr, uid, context=None):
        ids = self.search(cr, uid, [])
        log.info("Start update_name_for_all_hrbp_assignment")
        self.update_name_for_hrbp(cr, uid, ids, context)
        log.info("End update_name_for_all_hrbp_assignment")
        return True
    
    
   
    
    def get_largest_department_name(self, cr, uid, department_ids, context=None):
        """
        Trả về tên của các department cấp lớn nhất trong department_ids, vd, Nếu có B và A và con của A là A1, A2 thì trả về tên của A và B
        """
        name = []
        if department_ids:
            department_pool = self.pool.get('hr.department')
            for department in department_pool.read(cr, uid, department_ids, ['parent_id','complete_code']):
                parent_id = department.get('parent_id',False) and department['parent_id'][0] or False
                if parent_id not in department_ids:
                    name.append(department.get('complete_code',''))
        
        return ', '.join(name)


vhr_hrbp_assignment()