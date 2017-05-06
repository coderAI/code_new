# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields
from openerp.addons.vhr_common.model.vhr_common import vhr_common
from openerp import SUPERUSER_ID

from lxml import etree
import simplejson as json
log = logging.getLogger(__name__)


HOLDER_FIELD = [ 'payment_recever_id', 'advance_recever_id', 'travel_authorization_receiver_id',
                 'expense_report_recever_id', 'planning_approval_recever_id', 'mtk_receiver_id',
                 'non_mtk_receiver_id', 'good_request_receiver_id','budget_controller','manager_id'
    ]


class hr_department(osv.osv, vhr_common):
    _name = 'hr.department'
    _inherit = 'hr.department'
    _description = 'Department'

    log = logging.getLogger(__name__)

#     def code_get(self, cr, uid, ids, context=None):
#         if context is None:
#             context = {}
#         if not ids:
#             return []
# 
#         reads = self.read(cr, uid, ids, ['code', 'parent_id'], context=context)
#         res = []
#         for record in reads:
#             code = self.get_dept_code(cr, uid, record['id'], context)
#             res.append((record['id'], code))
# 
#         return res
# 
#     def get_dept_code(self, cr, uid, dept_id, context=None):
#         full_dept_code = ''
#         dept_obj = self.read(cr, uid, dept_id, ['code','parent_id','parent_left','parent_right'])
#         if dept_obj:
#             parent_left = dept_obj.get('parent_left','')
#             parent_right = dept_obj.get('parent_right','')
#             
#             dept_code = dept_obj.get('code','')
#             
#             full_dept_code = dept_code
#             parent_dept_code = ''
#             if dept_obj.get('parent_id',False):
#                 parent_dept_code = self.get_parent_dept_code(cr, uid, parent_left, parent_right, context)
#                 full_dept_code = parent_dept_code + ' / ' + full_dept_code
#             
#         return full_dept_code
#     
#     def get_parent_dept_code(self, cr, uid, parent_left, parent_right, context=None):
#         res = ''
#         if parent_left and parent_right:
#             sql = """
#                     SELECT code FROM hr_department WHERE parent_left < %s and parent_right > %s ORDER BY parent_left asc
#                   """
#             cr.execute(sql%(parent_left,parent_right))
#             results = cr.fetchall()
#             code_list = [res_id[0] for res_id in results]
#             res = ' / '.join(code_list)
#         
#         return res

#     def _dept_code_get_fnc(self, cr, uid, ids, prop, unknow_none, context=None):
#         res = self.code_get(cr, uid, ids, context=context)
#         return dict(res)

        # TODO: note confirm user

    # def _compute(self, cr, uid, ids, field_name, arg, context = None):
    # res = {}
    # for line in ids:
    # department_info = self.get_department(cr, uid, line)
    # division_info = self.get_division(cr, uid, line)
    # team_info = self.get_team(cr, uid, line)
    # department_id = None
    # division_id = None
    # team_id = None
    # if department_info:
    # department_id = department_info[0]
    # if division_info:
    # division_id = division_info[0]
    # if team_info:
    # team_id = team_info[0]
    # department_pool = self.pool.get('hr.department')
    # updated_value = {'department_official_id': department_id,
    # 'division_id': division_id,
    # 'team_id': team_id,
    # }
    # department_pool.write(cr, uid, [line], updated_value, context=context)
    # res[line] = True
    # return res
    #
    # def _check_recompute_departments(self, cr, uid, ids, context=None):
    # result = {}
    # if not ids:
    # ids = []
    # if not isinstance(ids, list):
    # ids = [ids]
    # department_pool = self.pool.get('hr.department')
    # for line in department_pool.browse(cr, uid, ids, context=context):
    # result[line.id] = True
    # if line.child_ids:
    #                 for child in line.child_ids:
    #                     result[child.id] = True
    #         return result.keys()

    _columns = {
        'code': fields.char('Code', size=64),
        'name': fields.char('Vietnamese Name', size=128),
        'name_en': fields.char('English Name', size=128),
        'active': fields.boolean('Active'),
        'hrbps': fields.many2many('hr.employee', 'hrbp_department_rel', 'department_id', 'employee_id', 'HRBPs'),
        'ass_hrbps': fields.many2many('hr.employee', 'ass_hrbp_department_rel', 'department_id', 'employee_id',
                                      'Assistant to HRBP'),
        'rams': fields.many2many('hr.employee', 'ram_department_rel', 'department_id', 'employee_id', 'RAMs'),
        'organization_class_id': fields.many2one('vhr.organization.class', 'Organization Class', ondelete='restrict'),
        'organization_class_code': fields.related('organization_class_id', 'code', type='char', string='Organization Code'),
#         'complete_code': fields.function(_dept_code_get_fnc, type="char", string='Full Code'),
        'level': fields.related('organization_class_id', 'level', type='integer', string='Level'),
        'email_group_id': fields.many2one('vhr.email.group', 'Email Group', ondelete='restrict'),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                         domain=[('object_id.model', '=', _name),
                                                 ('field_id.name', 'not in', ['write_date', 'audit_log_ids','history_ids'])]),
        #                 'recomputed_field': fields.function(_compute, type = "boolean",
        #                         store = {'hr.department': (_check_recompute_departments, ['parent_id', 'level'], 10)}),
        'parent_left': fields.integer('Left Parent', select=1),
        'parent_right': fields.integer('Right Parent', select=1),
        
        'hierarchical_id': fields.many2one('vhr.dimension', 'Hierachical Chart', ondelete='restrict',
                                     domain=[('dimension_type_id.code', '=', 'HIERARCHICAL_CHART'), ('active', '=', True)]),
        'approval_limit': fields.float('Approval Limit', select=1, digits=(2,0)),
        'cost_center': fields.char('Cost Center', size=64),
        'payment_recever_id': fields.many2one('hr.employee', 'Payment Receiver', ondelete='restrict'),
        'advance_recever_id': fields.many2one('hr.employee', 'Advance Receiver', ondelete='restrict'),
        'travel_authorization_receiver_id': fields.many2one('hr.employee', 'Travel Authorization Receiver', ondelete='restrict'),
        'expense_report_recever_id': fields.many2one('hr.employee', 'Expense Report Receiver', ondelete='restrict'),
        'planning_approval_recever_id': fields.many2one('hr.employee', 'Planning Approval Receiver', ondelete='restrict'),
        'eform_viewer_ids': fields.many2many('hr.employee', 'eform_viewer_department_rel', 'department_id', 'employee_id', 'Eform Viewer'),
        'salary_setting_id': fields.many2one('vhr.salary.setting', 'Type of salary', ondelete='restrict'),
        'budget_controller': fields.many2one('hr.employee', 'Budget Controller', ondelete='restrict'),
        
        'mtk_receiver_id': fields.many2one('hr.employee', 'MTK Receiver', ondelete='restrict'),
        'non_mtk_receiver_id': fields.many2one('hr.employee', 'Non MTK Receiver', ondelete='restrict'),
        'good_request_receiver_id': fields.many2one('hr.employee', 'Goods Request Receiver', ondelete='restrict'),
        
        'hrbp_viewer_ids': fields.many2many('hr.employee', 'hrbp_viewer_department_rel', 'department_id', 'employee_id', 'HRBP Viewer'),
    }
        
    def _get_default_hierarchical_id(self, cr, uid, context=None):
        if not context:
            context = {}
        
        if context.get('default_hierachical_code',False):
            dimension_type_ids = self.pool.get('vhr.dimension.type').search(cr, uid, [('code','=','HIERARCHICAL_CHART')])
            if dimension_type_ids:
                hierachical_ids = self.pool.get('vhr.dimension').search(cr, uid, [('code','=',context['default_hierachical_code']),
                                                                                  ('dimension_type_id','=',dimension_type_ids[0])])
            
            return hierachical_ids and hierachical_ids[0]

        return False
    
    _defaults = {
        'active': True,
        'approval_limit': 0,
        'hierarchical_id': _get_default_hierarchical_id,
    }

    _parent_name = "parent_id"
    _parent_store = True
    _parent_order = 'code, name'
    _order = 'parent_id'

    _unique_insensitive_constraints = [
        {'code': "Department's Code is already exist!", 'parent_id': "Department's Code is already exist!"},
        {'name': "Department's Vietnamese Name is already exist!", 'parent_id': "Department's Vietnamese Name is already exist!"}
    ]
    
    
    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False,
                   lazy=True):
        """
        Get the list of records in list view grouped by the given ``groupby`` fields
        """
        if not context:
            context = {}
        
        domain = self.get_search_argument(cr, uid, domain, context)

        res = super(hr_department, self).read_group(cr, uid, domain, fields, groupby, offset, limit, context, orderby, lazy)
        return res
    
    
    

    def get_level(self, cr, uid, department_id, context=None):
        organization_class = department_id.organization_class_id
        level = organization_class.level
        is_real = organization_class.is_real
        return level, is_real

    def serializable_object(self, cr, uid, node_id, context=None):
        node = self.browse(cr, uid, node_id, context=context)
        res = {
            'id': node_id,
            'name': node.name,
            'child_ids': [self.serializable_object(cr, uid, ch, context=context) for ch in
                          self.search(cr, uid, [('parent_id', '=', node_id)])]
        }
        return res

    def get_organise_department(self, cr, uid, company_id, context=None):
        return self.serializable_object(cr, uid, company_id)

    def int_become_obj(self, cr, uid, department_id, context=None):
        '''Change ID Department become Object'''
        if department_id:
            if isinstance(department_id, list):
                if len(department_id) > 1:
                    return False
                elif not isinstance(department_id[0], (int, long)):
                    return False
                else:
                    department_id = department_id[0]
            elif not isinstance(department_id, (int, long)):
                return False
        return self.browse(cr, uid, department_id)

    def get_department_unit_level(self, cr, uid, department_id, level, is_real=None, organ_ids=None, context=None):
        '''
            Params:
                department_id: Department's Employee. Its must be int or long or list have len = 1
                level: Int
                is_real: True: Department real
                        False: Department illusion
                        None: Get All
                organ_ids: All record of vhr.organization.class
            Return:
                List of result
                [1, 2, 3, 4]
        '''
        res = []
        department_id = self.int_become_obj(cr, uid, department_id, context)
        if not organ_ids:
            organ = self.pool.get('vhr.organization.class')
            organ_ids = organ.search(cr, uid, [])
        depart_level, depart_is_real = self.get_level(cr, uid, department_id, context)
        if level < depart_level:
            for item in organ_ids:
                if level == depart_level and (is_real == depart_is_real or is_real is None):
                    res.append(department_id.id)
                    break
                else:
                    department_id = department_id.parent_id
        elif level > depart_level:
            for item in organ_ids:
                parent_ids = [department_id.id]
                args = [('parent_id', 'child_of', parent_ids), ('level', '=', level)]
                if is_real is not None:
                    args.append(('is_real', '=', is_real))
                search_res = self.search(cr, uid, args)
                if search_res:
                    parent_ids = []
                    for depart in search_res:
                        department_id = self.int_become_obj(cr, uid, depart, context)
                        depart_level, depart_is_real = self.get_level(cr, uid, department_id, context)
                        if level == depart_level:
                            res.append(depart)
                        else:
                            parent_ids.append(depart)

        else:
            return []
        return res

    def get_department(self, cr, uid, department_id, level=None, context=None):
        '''
            Params:
                department_id: Department's Employee. Its must be int or long or list have len = 1
                level: List of department want to get.
                    {1: True, 2: False, 3: True}
                    True: Department real
                    False: Department illusion
                    None: Get All
            Return:
                {level: ids of department}
                Example: {1: [123], 2: [1234, 1234], ...}
        '''
        res = {}
        organ = self.pool.get('vhr.organization.class')
        organ_ids = organ.search(cr, uid, [])
        if level and isinstance(level, dict):
            for key in level.keys():
                value_res = self.get_department_unit_level(cr, uid, department_id, key, level[key], organ_ids, context)
                res.update({key: value_res})
        else:
            read_res = organ.read(cr, uid, organ_ids, ['level'])
            level = [item['level'] for item in read_res]
            for item in level:
                value_res = self.get_department_unit_level(cr, uid, department_id, item, None, organ_ids, context)
                res.update({item: value_res})
        return res


    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}

        if 'filter_by_parent_id' in context:
            args.append(('parent_id', '=', context['filter_by_parent_id']))

        if 'dept_from_division' in context:
            if context.get('dept_from_division', False):
                ids = self.get_department_unit_level(cr, uid, context['dept_from_division'], 2, None, None, context)
            else:
                ids = []
            args.append(('id', 'in', ids))
        
        elif 'dept_from_department_group' in context:
            ids = []
            if context.get('dept_from_department_group', False):
                ids = self.get_department_unit_level(cr, uid, context['dept_from_department_group'], 3, None, None, context)
            elif context.get('dept_from_division_bypass_group', False):
                #Case department có parent trực tiếp là division_id
                ids = self.get_department_unit_level(cr, uid, context['dept_from_division_bypass_group'], 3, None, None, context)
                
                ids = self.filter_to_get_direct_child_department(cr, uid, ids, 1, context)
                
            args.append(('id', 'in', ids))
            
        elif 'dept_from_department' in context:
            if context.get('dept_from_department', False):
                ids = self.get_department_unit_level(cr, uid, context['dept_from_department'], 4, None, None, context)
            else:
                ids = []
            args.append(('id', 'in', ids))

        args_new = ['|', '|', ('name', operator, name), ('code', operator, name), ('name_en', operator, name)] + args
        ids = self.search(cr, uid, args_new, context=context)
        return self.name_get(cr, uid, ids, context=context)
#         return super(hr_department, self).name_search(cr, uid, name, args, operator, context, limit)
    
    
    def filter_to_get_direct_child_department(self, cr, uid, ids, parent_level =1, context=None):
        if ids:
            parent_dicts = {}
            records = self.read(cr, uid, ids, ['parent_id'])
            for record in records:
                parent_id = record.get('parent_id', False) and record['parent_id'][0] or False
                if parent_id:
                    if parent_id not in parent_dicts:
                        parent_dicts[parent_id] = [record['id']]
                    else:
                        parent_dicts[parent_id].append(record['id'])
                
            if parent_dicts:
                parent_ids = parent_dicts.keys()
                parents = self.browse(cr, uid, parent_ids, fields_process=['organization_class_id'])
                for parent in parents:
                    level = parent.organization_class_id and parent.organization_class_id.level or 0
                    if level != parent_level:
                        #Nếu parent của department là department group thì loại department ra khỏi danh sách con trực tiếp của division
                        ids = list(set(ids).difference(parent_dicts[parent.id]))
        
        return ids
        
        
    #Get all department which have hrbp is employee_id
    def get_department_of_hrbp(self, cr, uid, employee_id, context=None):
        department_ids = []
        if employee_id:
            sql = "SELECT department_id from hrbp_department_rel where employee_id = %s" % employee_id
            cr.execute(sql)
            department_ids = map(lambda x: x[0], cr.fetchall())

        return department_ids

    #Get all department which have ass_hrbp is employee_id
    def get_department_of_ass_hrbp(self, cr, uid, employee_id, context=None):
        department_ids = []
        if employee_id:
            sql = "SELECT department_id from ass_hrbp_department_rel where employee_id = %s" % employee_id
            cr.execute(sql)
            department_ids = map(lambda x: x[0], cr.fetchall())

        return department_ids


    def check_hrbp_group(self, cr, uid, ids, dict, context=None):
        context.update({'field': 'hrbps', 'group': 'vhr_hrbp'})

        self.check_group_base_on_field_many2many(cr, uid, ids, dict, context)

    def check_ass_hrbp_group(self, cr, uid, ids, dict, context=None):
        context.update({'field': 'ass_hrbps', 'group': 'vhr_assistant_to_hrbp'})
        self.check_group_base_on_field_many2many(cr, uid, ids, dict, context)

    #Remove or add user to group base on field many2many
    def write_to_hrbp_assignment(self, cr, uid, ids, add_hrbps, field, context=None):
        if context is None:
            context = {}
        assignment_obj = self.pool.get('vhr.hrbp.assignment')
        if add_hrbps and add_hrbps[0] == 'remove':
            write_sig = 3
        else:
            write_sig = 4
        add_hrbps = add_hrbps[1]
        add_hrbp_ids = assignment_obj.search(cr, uid, [('employee_id', 'in', add_hrbps)])
        context['from_hr_department_call_update'] = 1
        context['do_not_update_name'] = True
        if add_hrbp_ids:
            for res_id in ids:
                assignment_obj.write(cr, uid, add_hrbp_ids,
                                     {field == 'hrbps' and 'hrbp_department_ids'
                                      or 'ass_hrbp_department_ids': [[write_sig, res_id]]}, context=context)
        
#         context['update_name'] = True
#         assignment_obj.write(cr, uid, add_hrbp_ids, {}, context)
        return True

    def check_group_base_on_field_many2many(self, cr, uid, ids, dict, context=None):
        
        if not context:
            context = {}

        child_department_ids = context.get('child_department_ids', [])
        remove_department_ids = []
        user_pool = self.pool.get('res.users')
        assignment_obj = self.pool.get('vhr.hrbp.assignment')
        field = context.get('field', 'hrbps')
        group = context.get('group', 'vhr_hrbp')
        
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
            total_employee_ids = []
            list_add_user_id = []
            for record_id in ids:
                
                #Get list add hrbps and list remove hrbps (or ass hrbps base on caller)
                specific_dict = dict.get(record_id, {})
                new_hrbps = specific_dict.get('new_' + field, [])
                old_hrbps = specific_dict.get('old_' + field, [])
                remove_hrbps = []
                add_hrbps = new_hrbps
                if not new_hrbps:
                    remove_hrbps = old_hrbps
                elif old_hrbps:
                    remove_hrbps = [item for item in old_hrbps if item not in new_hrbps]
                    add_hrbps = [item for item in new_hrbps if item not in old_hrbps]

                # remove user from group if user is not appear in other hrbp/ass_hrbp
                if remove_hrbps and group_id:
                    remove_department_ids = []
                    employee_hrbps = self.pool.get('hr.employee').read(cr, uid, remove_hrbps, ['user_id'])
                    for employee_hrbp in employee_hrbps:
                        user_id = employee_hrbp.get('user_id',False) and employee_hrbp['user_id'][0] or False
                        if user_id:
                                
                            #remove hrbp A from parent department and child department if department remove hrbp A
                            remove_department_ids = self.get_all_parent_department_have_same_hrbp_or_ass_hrbp(cr, uid, field, record_id, employee_hrbp['id'], context)
                            remove_department_ids += child_department_ids
                            if remove_department_ids:
                                super(hr_department, self).write(cr, uid, remove_department_ids, {field: [[3, employee_hrbp['id']]]})
                                
                            #get all department which user is currenly hrbp/assistant hrbp
                            if context.get('field', False) == 'hrbps':
                                department_ids = self.get_department_of_hrbp(cr, uid, employee_hrbp['id'], context)
                            else:
                                department_ids = self.get_department_of_ass_hrbp(cr, uid, employee_hrbp['id'], context)
                                
                            #if user is not hrbp/ass hrbp of any department, then remove user from group hrbp/ass hrbp
                            if not department_ids:
                                list_remove_user_id.append(user_id)
                                
                    #   hrbp assignment
                    department_ids = list(set(remove_department_ids))
                    total_employee_ids += remove_hrbps
                    remove_hrbps = ['remove', remove_hrbps]
                    self.write_to_hrbp_assignment(cr, uid, department_ids, remove_hrbps, field, context=context)

                #add user to group
                if add_hrbps and group_id:
                    employee_hrbps = self.pool.get('hr.employee').read(cr, uid, add_hrbps, ['user_id'])
                    for employee_hrbp in employee_hrbps:
                        user_id = employee_hrbp.get('user_id',False) and employee_hrbp['user_id'][0] or False
                        if user_id:
                            if not context.get('from_hrbp_assignment'):
                                #add hrbp/ assist_hrbp for child department
                                super(hr_department, self).write(cr, uid, child_department_ids, {field: [[4, employee_hrbp['id']]]})
                            list_add_user_id.append(user_id)

                    # hrbp assignment
                    if not context.get('from_hrbp_assignment'):
                        department_ids = list(set(child_department_ids))#child_department_ids included edit departments
                        total_employee_ids += add_hrbps
                        add_hrbps = ['add', add_hrbps]
                        self.write_to_hrbp_assignment(cr, uid, department_ids, add_hrbps, field, context=context)
            
            if list_remove_user_id:
                list_remove_user_id = list(set(list_remove_user_id))
                user_pool.write(cr, uid, list_remove_user_id, {'groups_id': [[3, group_id]]})
                
            if list_add_user_id:
                list_add_user_id = list(set(list_add_user_id))
                user_pool.write(cr, uid, list_add_user_id, {'groups_id': [[4, group_id]]})
                        
            #Update name of hrbp assignment
            total_employee_ids = list(set(total_employee_ids))
            if total_employee_ids:
                add_hrbp_ids = assignment_obj.search(cr, uid, [('employee_id', 'in', total_employee_ids)])
                if add_hrbp_ids:
                    assignment_obj.write(cr, uid, add_hrbp_ids, {}, {'update_name': True,'from_hr_department_call_update':True})
            
        return True
    
    def get_all_parent_department_have_same_hrbp_or_ass_hrbp(self, cr, uid, field, department_id, employee_id, context=None):
        remove_department_ids = []
        if field and department_id and employee_id:
            parent_department_ids = self.get_parent_department_by_sql(cr, uid, [department_id], context)
            if parent_department_ids:
                remove_department_ids = self.search(cr, uid, [('id','in',parent_department_ids),
                                                              (field,'=',employee_id)])
        
        return remove_department_ids
                

    def onchange_organization_class(self, cr, uid, ids, organization_class_id, context=None):
        res = {'value': {}, 'domain': {}}
        if organization_class_id:
            organization_class = self.pool.get('vhr.organization.class').browse(cr, uid, organization_class_id)
            res['value']['organization_class_code'] = organization_class.code or ''
            if organization_class and organization_class.level:
                res['value']['level'] = organization_class.level
                if organization_class.level == 3:
                    res['domain']['parent_id'] = [('level', '=', 2)]
                else:
                    res['domain']['parent_id'] = []
        return res

    def create(self, cr, uid, vals, context=None):
        
        res = super(hr_department, self).create(cr, uid, vals, context)
        
        if res:
            dict = {res:{}}
            if set(['hrbps','ass_hrbps']).intersection(vals.keys()):
                record = self.read(cr, uid, res, ['hrbps','ass_hrbps'])
                dict[res]['new_hrbps']     = record.get('hrbps',[])
                dict[res]['new_ass_hrbps'] = record.get('ass_hrbps',[])
            
            if vals.get('hrbps', False):
                self.check_hrbp_group(cr, uid, [], dict, context)
            
            if vals.get('ass_hrbps', False):
                self.check_ass_hrbp_group(cr, uid, [], dict, context)
                
            #Chi cap nhat cho nhung phong ban co organization class tu department tro len
            hierarchical_id = vals.get('hierarchical_id', False)
            if hierarchical_id:
                hierarchical = self.pool.get('vhr.dimension').read(cr, uid, hierarchical_id, ['code'])
                if hierarchical and hierarchical.get('code', False) == 'ORGCHART':
                    organization_class_id = vals.get('organization_class_id', False)
                    org_class_ids = self.pool.get('vhr.organization.class').search(cr, uid, [('level','<=',3)])
                    if organization_class_id in org_class_ids:
                        self.update_group_dept_head(cr, uid, [res], vals, context)
            
        return res

    def write(self, cr, uid, ids, vals, context=None):
        """
        Xóa  1 HRBP: Xóa HRBP đó ra khỏi các phòng ban con và phòng ban cha/ông/cụ.... của edit department.
        Thêm 1 HRBP: Thêm HRBP vào tất cả các phòng ban con/cháu/chắt chút chít.... của edit department -_-
        """
        if context is None:
            context = {}
        
        if not isinstance(ids, list):
            ids = [ids]
        #Get list include edit department and list child of edit department
        child_department_ids = []
        if (vals.get('hrbps', False) or vals.get('ass_hrbps', False)) and not context.get('create_directly', False):
            context['active_test'] = True
            child_department_ids = self.get_child_department(cr, uid, ids, context)
        context['child_department_ids'] = child_department_ids
        
        #Update group for hr_dept_head if change manager_id of department HR
        if vals.get('manager_id', False) and ids:
            record = self.read(cr, uid, ids[0], ['organization_class_id','hierarchical_id'])
            hierarchical_id = record.get('hierarchical_id', False) and record['hierarchical_id'][0] or False
            if hierarchical_id:
                hierarchical = self.pool.get('vhr.dimension').read(cr, uid, hierarchical_id, ['code'])
                if hierarchical and hierarchical.get('code', False) == 'ORGCHART':
                    old_organization_class_id = record.get('organization_class_id', False) and record['organization_class_id'][0] or False
                    organization_class_id = vals.get('organization_class_id', old_organization_class_id)
                    org_class_ids = self.pool.get('vhr.organization.class').search(cr, uid, [('level','<=',3)])
                    if organization_class_id in org_class_ids:
                        self.update_group_dept_head(cr, uid, ids, vals, context)
                        
                    self.update_group_hr_dept_head(cr, uid, ids, vals, context)
        
        #Only allow to inactive department if dont have any employee in active WR(change form != dismiss), 
        #and dont have any employee in not finish movement and not finish mass movement
        if 'active' in vals and not vals.get('active', False):
            self.check_if_exist_employee_in_active_working_record(cr, uid, ids, context)
        
        dict = {}
        if set(['hrbps','ass_hrbps']).intersection(vals.keys()):
            for record in self.read(cr, uid, ids, ['hrbps','ass_hrbps']):
                dict[record['id']] = {}
                dict[record['id']]['old_hrbps'] = record.get('hrbps',[])
                dict[record['id']]['old_ass_hrbps'] = record.get('ass_hrbps',[])
            
        res = super(hr_department, self).write(cr, uid, ids, vals, context)
        
        if res:
            
            if set(['hrbps','ass_hrbps']).intersection(vals.keys()):
                for record in self.read(cr, uid, ids, ['hrbps','ass_hrbps']):
                    dict[record['id']]['new_hrbps'] = record.get('hrbps',[])
                    dict[record['id']]['new_ass_hrbps'] = record.get('ass_hrbps',[])
                
            if vals.get('hrbps', False) and not context.get('create_directly', False):
                self.check_hrbp_group(cr, uid, ids, dict, context)
                
            if vals.get('ass_hrbps', False) and not context.get('create_directly', False):
                self.check_ass_hrbp_group(cr, uid, ids, dict, context)

        return res
    
    def check_if_exist_employee_in_active_working_record(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        if ids:
            if not isinstance(ids, list):
                ids = [ids]
            
            working_obj = self.pool.get('vhr.working.record')
            movement_obj = self.pool.get('vhr.mass.movement')
            
            dismiss_change_form_ids = []
            config_parameter = self.pool.get('ir.config_parameter')
            dismiss_code = config_parameter.get_param(cr, uid, 'vhr_master_data_dismiss_change_form_code') or ''
            dismiss_code_list = dismiss_code.split(',')
            
            dismiss_local_code = config_parameter.get_param(cr, uid, 'vhr_master_data_dismiss_local_company') or ''
            dismiss_local_code_list = dismiss_local_code.split(',')
            
            dismiss_code_list += dismiss_local_code_list
            if dismiss_code_list:
                dismiss_change_form_ids = self.pool.get('vhr.change.form').search(cr, uid, [('code','in',dismiss_code_list)])
            
            if not context.get('do_not_update_for_child_department', False):
                child_department_ids = self.get_child_department(cr, uid, ids)
                if child_department_ids:
                    self.write(cr, uid, child_department_ids, {'active': False}, context={'do_not_update_for_child_department': True})
            
#             #Search in active WR dont have change form dismiss
            active_wr_ids = working_obj.search(cr, uid, ['|','|','|',
                                                            ('division_id_new','in',ids),
                                                            ('department_group_id_new','in',ids),
                                                            ('department_id_new','in',ids),
                                                            ('team_id_new','in', ids),
                                                         ('change_form_ids','!=',dismiss_change_form_ids[0]),
                                                         ('state','in',[False,'finish']),
                                                         ('active','=',True)
                                                         ])
              
            if active_wr_ids:
                workings = working_obj.browse(cr, uid, active_wr_ids, fields_process = ['employee_id'])
                list_employee = [wr.employee_id and wr.employee_id.active and wr.employee_id.login or '' for wr in workings]
                list_employee = filter(None, list_employee)
                if list_employee:
                    list_employee = ', '.join(list_employee)
                    raise osv.except_osv('Error !', 'These are active employees still belong to department(s) in active working records: \n\n %s !' % list_employee)
             
            #Search in not finish staff movement
            not_fin_sm_ids = working_obj.search(cr, uid, ['|','|','|',
                                                            ('division_id_new','in',ids),
                                                            ('department_group_id_new','in',ids),
                                                            ('department_id_new','in',ids),
                                                            ('team_id_new','in', ids),
                                                          ('state','not in',[False,'finish','cancel'])])
             
            if not_fin_sm_ids:
                workings = working_obj.browse(cr, uid, not_fin_sm_ids, fields_process = ['employee_id'])
                list_employee = [wr.employee_id and wr.employee_id.active and wr.employee_id.login or '' for wr in workings]
                list_employee = filter(None, list_employee)
                if list_employee:
                    list_employee = ', '.join(list_employee)
                    raise osv.except_osv('Error !', 'These are active employees still belong to department(s) in not finish staff movements: \n\n %s !' % list_employee)
            
            #Search in not finish mass movement
            not_fin_mm_ids = movement_obj.search(cr, uid, ['|','|','|',
                                                            ('division_id_new','in',ids),
                                                            ('department_group_id_new','in',ids),
                                                            ('department_id_new','in',ids),
                                                            ('team_id_new','in', ids),
                                                           ('state','not in',['finish','cancel'])])
            
            if not_fin_mm_ids:
                workings = movement_obj.browse(cr, uid, not_fin_mm_ids, fields_process = ['employee_ids'])
                list_employee = []
                for working in workings:
                    list_employee.extend([ emp.active and emp.login or '' for emp in working.employee_ids])
                
                list_employee = filter(None, list_employee)
                if list_employee:
                    list_employee = ', '.join(list_employee)
                    raise osv.except_osv('Error !', 'These are active employees still belong to department(s) in not finish mass movements: \n\n %s' % list_employee)
                

                
    
    def update_group_hr_dept_head(self, cr, uid, ids, vals, context=None):
        #If change manager_id of HR Department, add new manager_id to group hr_dept_head, remove old_manager from group hr_dept_head
        if ids:
            try:
                hr_code_list = []
                hr_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr_master_data_code_of_HR_department')
                if hr_code:
                    hr_code_list = hr_code.split(',')
                
                    self.update_group_by_department(cr, SUPERUSER_ID, ids, vals, hr_code_list, 'vhr_hr_dept_head', context)
            except Exception as e:
                log.exception(e)
                try:
                    error_message = e.message
                    if not error_message:
                        error_message = e.value
                except:
                    error_message = ""
                raise osv.except_osv('Error !', 'Error when update group for hr_dept_head: %s' % error_message)
        return True
    
    def update_group_dept_head(self, cr, uid, ids, vals, context=None):
        #If change manager_id of Department, add new manager_id to group vhr_dept_head, remove old_manager from group vhr_dept_head
        if ids:
            try:
                
                self.update_group_by_department(cr, SUPERUSER_ID, ids, vals, [], 'vhr_dept_head', context)
            except Exception as e:
                log.exception(e)
                try:
                    error_message = e.message
                    if not error_message:
                        error_message = e.value
                except:
                    error_message = ""
                raise osv.except_osv('Error !', 'Error when update group for vhr_dept_head: %s' % error_message)
        return True
    
    def insert_member_into_group_dept_head(self, cr, uid, context=None):
        log.info("\nStart insert_member_into_group_dept_head")
        org_class_ids = self.pool.get('vhr.organization.class').search(cr, uid, [('level','<=',3)])
        ids = self.search(cr, uid, [('active','=',True),
                                    ('organization_class_id','in',org_class_ids)])
        if ids:
            self.update_group_dept_head(cr, uid, ids, {}, context)
        
        log.info("\n End insert_member_into_group_dept_head")
        return True
            
    
    def update_group_by_department(self, cr, uid, ids, vals, department_code_list, group_name, context=None):
        """
        Cập nhật member của group_name dựa vào manager_id của department,
        Nếu department_code_list <> null, chỉ cập nhật cho những department có code thuộc department_code_list
        Nếu department_code_list == null, cập nhật cho toàn bộ department
        """
        if not vals:
            vals = {}
        
        if not isinstance(ids, list):
            ids = [ids]
            
        if ids and group_name:
            group_id = False
            model_data = self.pool.get('ir.model.data')
            model_ids = model_data.search(cr, uid, [('model', '=', 'res.groups'), ('name', '=', group_name)])
            if model_ids:
                model = model_data.read(cr, uid, model_ids[0], ['res_id'])
                group_id = model.get('res_id', False)
            
            if group_id:
                records = self.read(cr, uid, ids, ['code','manager_id'])
                employee_pool = self.pool.get('hr.employee')
                user_pool = self.pool.get('res.users')
                for record in records:
                    dept_code = vals.get('code',record.get('code',''))
                    if dept_code in department_code_list or not department_code_list:
                        old_manager_id = record.get('manager_id',False) and record['manager_id'][0] or False
                        if vals.get('manager_id', False):
                            new_manager_id = vals['manager_id']
                        else:
                            new_manager_id = old_manager_id
                            #cheat
                            old_manager_id = False
                        
                        if old_manager_id:
                            #Check id old_manager_id is manager of any other department, dont remove old_manager_id from group_dept_head
                            domain = [('manager_id','=',old_manager_id)]
                            if department_code_list:
                                domain.append(('code','in',department_code_list))
                            department_dh_ids = self.search(cr, uid, domain)
                            department_dh_ids = [record_id for record_id in department_dh_ids if record_id not in ids]
                            if not department_dh_ids:
                                old_manager = employee_pool.read(cr, uid, old_manager_id, ['user_id'])
                                old_manager_user_id = old_manager.get('user_id',False) and old_manager['user_id'][0]
                                if old_manager_user_id:
                                    user_pool.write(cr, uid, [old_manager_user_id], {'groups_id': [[3, group_id]]})
                        
                        if new_manager_id:
                            new_manager = employee_pool.read(cr, uid, new_manager_id, ['user_id'])
                            new_manager_user_id = new_manager.get('user_id',False) and new_manager['user_id'][0]
                            if new_manager_user_id:
                                user_pool.write(cr, uid, [new_manager_user_id], {'groups_id': [[4, group_id]]})
        return True

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(hr_department, self).unlink(cr, uid, ids, context)
        except Exception as e:
            logging.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(hr_department, self).fields_view_get(cr, uid, view_id, view_type, context,
                                                                   toolbar=toolbar, submenu=submenu)
        if context is None:
            context = {}
        if view_type == 'form' and context.get('default_hierachical_code',False) == 'FAORGCHART':
            res = self.add_attrs_for_field(cr, uid, res, context)
        return res
    
    def add_attrs_for_field(self, cr, uid, res, context=None):
        """
        Hiện chỉ check cho FA Department Form
        
        Các user không thuộc group FA không được quyền edit các field trong Department FA (except hrbp_viewer_ids)
        Các user không thuộc group FA_HRBP_update không được quyền edit special_fields
        """
        employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', uid)])
        doc = etree.XML(res['arch'])
        if res['type'] == 'form':
            groups = self.pool.get('res.users').get_groups(cr, uid)
            special_fields = ['hrbp_viewer_ids']
            
            readonly_special_fields = False
            readonly_other = False
            if 'vhr_fa' not in groups:
                readonly_other = True
            
            if 'vhr_update_fa_hrbp_viewer' not in groups:
                readonly_special_fields = True
            fields = self._columns.keys()
            for field in fields:
                for node in doc.xpath("//field[@name='%s']" % field):
                    modifiers = json.loads(node.get('modifiers'))
                    readonly_attr = False
                    if field not in special_fields and readonly_other:
                        readonly_attr = True
                    elif field in special_fields and readonly_special_fields:
                        readonly_attr = True
                    
                    if readonly_attr:
                        modifiers['readonly'] = readonly_attr
                        node.set('modifiers', json.dumps(modifiers))
        
        res['arch'] = etree.tostring(doc)
        return res



hr_department()