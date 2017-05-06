# -*-coding:utf-8-*-
import logging
from openerp.osv import osv, fields

log = logging.getLogger(__name__)


class hr_department(osv.osv):
    _inherit = 'hr.department'
    _description = 'HR Department'
    
    _columns = {
        'main_hrbps': fields.many2many('hr.employee', 'main_hrbp_department_rel', 'department_id', 
                                       'employee_id',' Main HRBP', domain="[('id', 'in', hrbps[0][2])]"),
       'rr_hrbps': fields.many2many('hr.employee', 'rr_hrbp_department_rel', 'department_id', 'employee_id', 'RR HRBPs'),
   
    }
    
    def get_department_for_rr_hrbps(self, cr, uid, employee_id, context=None):
        """ Lấy danh sách department mà employee_id ( RR hrbp) được add vào
            không lấy theo cha con
        """
        department_ids = []
        if employee_id:
            sql = "SELECT department_id from rr_hrbp_department_rel where employee_id = %s" % employee_id
            cr.execute(sql)
            department_ids = map(lambda x: x[0], cr.fetchall())
        return department_ids
    
    def check_group_rr_hrbp_base_on_field_many2many(self, cr, uid, ids, dict, context=None):
        
        if not context:
            context = {}

        child_department_ids = context.get('child_department_ids', [])
        remove_department_ids = []
        user_pool = self.pool.get('res.users')
        field = context.get('field', 'rr_hrbps')
        group = context.get('group', 'vhr_rr_hrbp')
        
        #get group id of context['group']
        group_id = False
        model_data = self.pool.get('ir.model.data')
        model_ids = model_data.search(cr, uid, [('model', '=', 'res.groups'), ('name', '=', group)])
        if model_ids:
            model = model_data.read(cr, uid, model_ids[0], ['res_id'])
            group_id = model.get('res_id', False)
        if ids:
            if not isinstance(ids, list):
                ids = [ids]
            list_remove_user_id = []
            list_add_user_id = []
            for record_id in ids:
                
                #Get list add rr hrbps and list remove rr hrbps (or ass rr hrbps base on caller)
                specific_dict = dict.get(record_id, {})
                new_rr_hrbps = specific_dict.get('new_' + field, [])
                old_rr_hrbps = specific_dict.get('old_' + field, [])
                remove_rr_hrbps = []
                add_rr_hrbps = new_rr_hrbps
                if not new_rr_hrbps:
                    remove_rr_hrbps = old_rr_hrbps
                elif old_rr_hrbps:
                    remove_rr_hrbps = [item for item in old_rr_hrbps if item not in new_rr_hrbps]
                    add_rr_hrbps = [item for item in new_rr_hrbps if item not in old_rr_hrbps]

                # remove user from group if user is not appear in other rr hrbp
                if remove_rr_hrbps and group_id:
                    remove_department_ids = []
                    employee_rr_hrbps = self.pool.get('hr.employee').read(cr, uid, remove_rr_hrbps, ['user_id'])
                    for employee_rr_hrbp in employee_rr_hrbps:
                        user_id = employee_rr_hrbp.get('user_id',False) and employee_rr_hrbp['user_id'][0] or False
                        if user_id:
                                
                            #remove rr hrbp A from parent department and child department if department remove rr hrbp A
                            remove_department_ids = self.get_all_parent_department_have_same_rr_hrbp(cr, uid, field, record_id, employee_rr_hrbp['id'], context)
                            remove_department_ids += child_department_ids
                            if remove_department_ids:
                                super(hr_department, self).write(cr, uid, remove_department_ids, {field: [[3, employee_rr_hrbp['id']]]})
                                
                            #get all department which user is currenly rr hrbp
                            if context.get('field', False) == 'rr_hrbps':
                                department_ids = self.get_department_for_rr_hrbps(cr, uid, employee_rr_hrbp['id'], context)
                            else:
                                department_ids = self.get_department_of_ass_hrbp(cr, uid, employee_rr_hrbp['id'], context)
                                
                            #if user is not rr hrbp of any department, then remove user from group rr hrbp
                            if not department_ids:
                                list_remove_user_id.append(user_id)
                                
                #add user to group
                if add_rr_hrbps and group_id:
                    employee_rr_hrbps = self.pool.get('hr.employee').read(cr, uid, add_rr_hrbps, ['user_id'])
                    for employee_rr_hrbp in employee_rr_hrbps:
                        user_id = employee_rr_hrbp.get('user_id',False) and employee_rr_hrbp['user_id'][0] or False
                        if user_id:
                            #add rr hrbp
                            super(hr_department, self).write(cr, uid, child_department_ids, {field: [[4, employee_rr_hrbp['id']]]})
                            list_add_user_id.append(user_id)
            
            if list_remove_user_id:
                list_remove_user_id = list(set(list_remove_user_id))
                user_pool.write(cr, uid, list_remove_user_id, {'groups_id': [[3, group_id]]})
                
            if list_add_user_id:
                list_add_user_id = list(set(list_add_user_id))
                user_pool.write(cr, uid, list_add_user_id, {'groups_id': [[4, group_id]]})
        
        return True
    
    def get_all_parent_department_have_same_rr_hrbp(self, cr, uid, field, department_id, employee_id, context=None):
        remove_department_ids = []
        if field and department_id and employee_id:
            parent_department_ids = self.get_parent_department_by_sql(cr, uid, [department_id], context)
            if parent_department_ids:
                remove_department_ids = self.search(cr, uid, [('id','in',parent_department_ids),
                                                              (field,'=',employee_id)])
        
        return remove_department_ids
    
    def check_rr_hrbp_group(self, cr, uid, ids, dict, context=None):
        context.update({'field': 'rr_hrbps', 'group': 'vhr_rr_hrbp'})
        self.check_group_rr_hrbp_base_on_field_many2many(cr, uid, ids, dict, context)
    
    def create(self, cr, uid, vals, context=None):
        exlusion_obj = self.pool.get('vhr.erp.bonus.exclusion')
        organization_class =  self.pool.get('vhr.organization.class')
        employee_id = vals.get('manager_id',False)
        organization_class_id = vals.get('organization_class_id',False)
        hierarchical_id = vals.get('hierarchical_id',False)
        if hierarchical_id and hierarchical_id == 40:
            if employee_id:
                exlusion_ids = exlusion_obj.search(cr, uid, [('code','=','EXCLUSION_3')])
                organization_class_ids  = organization_class.search(cr, uid, [('id','=',organization_class_id)])
                if organization_class_ids:
                    organization  = organization_class.browse(cr, uid, organization_class_ids[0],context=context)
                    if organization.level in (1,2,3):
                        if exlusion_ids:
                            exlusion = self.browse(cr, uid, exlusion_ids[0], context = context)
                            if exlusion:
                                exlusion_id = exlusion.id
                                is_check = exlusion_obj.check_employee_exlusion(cr, uid, employee_id, exlusion_id, context = context)
                                if is_check:
                                    cr.execute('INSERT INTO erp_bonus_exclusion_employee_rel (exclusion_id,employee_id) VALUES (%s,%s)',(exlusion_id,employee_id))
          
        res =  super(hr_department, self).create(cr, uid, vals, context)
        if res:
            dict = {res:{}}
            if set(['rr_hrbps']).intersection(vals.keys()):
                record = self.read(cr, uid, res, ['rr_hrbps'])
                dict[res]['new_rr_hrbps'] = record.get('rr_hrbps',[])
            if vals.get('rr_hrbps', False):
                self.check_rr_hrbp_group(cr, uid, [res], dict, context)
        return res
    

    def write(self, cr, uid, ids, vals, context=None):
        if not context:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]
        child_department_ids = []
        if vals.get('rr_hrbps', False) and not context.get('create_directly', False):
            context['active_test'] = True
            child_department_ids = self.get_child_department(cr, uid, ids, context)
        context['child_department_ids'] = child_department_ids
        dict = {}
        if set(['rr_hrbps']).intersection(vals.keys()):
            for record in self.read(cr, uid, ids, ['rr_hrbps']):
                dict[record['id']] = {}
                dict[record['id']]['old_rr_hrbps'] = record.get('rr_hrbps',[])
        res = super(hr_department, self).write(cr, uid, ids, vals, context)
        
        if res:
            if set(['rr_hrbps']).intersection(vals.keys()):
                for record in self.read(cr, uid, ids, ['rr_hrbps']):
                    dict[record['id']]['new_rr_hrbps'] = record.get('rr_hrbps',[])
            if vals.get('rr_hrbps', False) and not context.get('create_directly', False):
                self.check_rr_hrbp_group(cr, uid, ids, dict, context)
                
        if vals.get('manager_id'):
            employee_id_new = vals.get('manager_id')
            for department in self.browse(cr, uid, ids, context=context):
                hierarchical_id = department.hierarchical_id.id if department.hierarchical_id else False
                if hierarchical_id and hierarchical_id == 40:
                    if department.manager_id and department.organization_class_id and\
                       department.organization_class_id.level in (1,2,3):
                        employee_id_old = department.manager_id.id
                        exlusion_ids = self.pool.get('vhr.erp.bonus.exclusion').search(cr, uid, [('code','=','EXCLUSION_3')])
                        if exlusion_ids:
                            exlusion = self.browse(cr, uid, exlusion_ids[0], context = context)
                            if exlusion:
                                exlusion_id = exlusion.id 
                                is_check = self.pool.get('vhr.erp.bonus.exclusion').check_employee_exlusion(cr, uid, employee_id_new, exlusion_id, context = context)
                                if is_check:
                                    cr.execute('UPDATE erp_bonus_exclusion_employee_rel set employee_id = %s where exclusion_id = %s and employee_id = %s',(employee_id_new,exlusion_id,employee_id_old))       
        
        # khi change hrbps check main hrbps
        if vals.get('hrbps'):
            #Remove person from main_hrbp if that person is not hrbp anymore
            for department in self.browse(cr, uid, ids, context=context):
                main_hrbp_val = []
                hrbps = department.hrbps
                for main_hrbp in department.main_hrbps:
                    if main_hrbp not in hrbps:
                        department_id = main_hrbp.department_id.id
                        employee_id = main_hrbp.id
                        main_hrbp_val.append((3,main_hrbp.id))  
                        cr.execute('delete from main_hrbp_department_rel where department_id= %s and employee_id = %s',(department_id,employee_id))          
                if main_hrbp_val:
                    super(hr_department, self).write(cr, uid, ids, {'main_hrbps':main_hrbp_val}, context)
        
        return res

hr_department()
