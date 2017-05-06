# -*-coding:utf-8-*-
import logging
import thread

from openerp.osv import osv, fields
from datetime import datetime
from openerp.sql_db import Cursor
from openerp.sql_db import ConnectionPool
from openerp import tools

log = logging.getLogger(__name__)


class vhr_property_management(osv.osv):
    _name = 'vhr.property.management'
    _description = 'VHR Asset Management'

    _columns = {
        'name': fields.char('Name', size=128),
        'employee_id': fields.many2one('hr.employee', 'Employee'),
        'department_id': fields.related('employee_id', 'department_id', type='many2one',
                                        relation='hr.department', string='Department'),
        'property_type_id': fields.many2one('vhr.property.type', 'Asset Type'),
        'property_id': fields.many2one('vhr.property', 'Asset'),
        'property_code': fields.char('Asset Code'),
        'issue_date': fields.date('Issue Date', help=u'Ngày cấp'),
        'recovery_date': fields.date('Recovery Date', help=u'Ngày thu hồi'),
        'depreciation_expiry_date': fields.date('Depreciation Expiry Date', help=u'Ngày hết hạn khấu hao'),
        'depreciation_time': fields.integer('Depreciation Time', help=u'Thời gian khấu hao'),
        'time_type': fields.selection([
            ('month', 'Month'),
            ('year', 'Year'),
        ], 'Type'),
        'company_allowance': fields.float('Company Allowance', help=u'Mức hỗ trợ của công ty'),
        'description': fields.text('Description'),
        'active': fields.boolean('Active'),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                          domain=[('object_id.model', '=', _name),
                                                  ('field_id.name', 'not in',
                                                   ['write_date', 'audit_log_ids'])]),
    }

    _defaults = {
        'active': True,
        'time_type': 'month',
    }

    _unique_insensitive_constraints = [{'employee_id': "Asset Code which issue for this employee is already exist!",
                                        'property_type_id': "Asset Code which issue for this employee is already exist!",
                                        'property_id': "Asset Code which issue for this employee is already exist!",
                                        'property_code': "Asset Code which issue for this employee is already exist!"
                                        }]

    def _check_dates(self, cr, uid, ids, context=None):
        for period in self.read(cr, uid, ids, ['issue_date', 'recovery_date'], context=context):
            if period['issue_date'] and period['recovery_date'] and period['issue_date'] >= period['recovery_date']:
                return False
        return True

    _constraints = [
        (_check_dates, '\n\nRecovery date must be greater than or equal to Issue date !', ['issue_date', 'recovery_date']),
    ]
    
    def default_get(self, cr, uid, fields, context=None):
        if not context:
            context = {}
        res = super(vhr_property_management, self).default_get(cr, uid, fields, context=context)
        
        if context.get('property_type',False):
            property_type_ids = self.pool.get('vhr.property.type').search(cr, uid, [('code','=',context['property_type'])])
            if property_type_ids:
                res['property_type_id'] = property_type_ids[0]
        
        return res
            
    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        args_new = args
        ids = self.search(cr, uid, args_new,0, None, None, context)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(vhr_property_management, self).name_search(cr, uid, name, args, operator, context, limit)
    
    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False,
                   lazy=True):
        """
        Get the list of records in list view grouped by the given ``groupby`` fields
        """
        if not context:
            context = {}
        
        if context.get('property_type',False):
            property_type_ids = self.pool.get('vhr.property.type').search(cr, uid, [('code','=',context['property_type'])])
            if property_type_ids:
                domain.append(('property_type_id','=',property_type_ids[0]))
                
        res = super(vhr_property_management, self).read_group(cr, uid, domain, fields, groupby, offset, limit, context, orderby,
                                                   lazy)
        return res
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if not context:
            context = {}
        
        if 'active_test' not in context:
            context['active_test'] = False
        
        if context.get('property_type',False):
            property_type_ids = self.pool.get('vhr.property.type').search(cr, uid, [('code','=',context['property_type'])])
            if property_type_ids:
                args.append(('property_type_id','=',property_type_ids[0]))
        return super(vhr_property_management, self).search(cr, uid, args, offset, limit, order, context, count)


    def name_get(self, cr, uid, ids, context=None):
        if not ids or False in ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        reads = self.read(cr, uid, ids, ['employee_id'], context=context)
        res = []
        for record in reads:
            if 'employee_id' in record and isinstance(record['employee_id'], tuple):
                name = record['employee_id'][1]
                res.append((record['id'], name))
        return res

    def onchange_employee_id(self, cr, uid, ids, employee_id, context=None):
        res = {}
        if employee_id:
            employee = self.pool.get('hr.employee').read(cr, uid, employee_id, ['department_id'])
            department_id = employee.get('department_id', False)
            res['department_id'] = department_id and department_id[0] or False

        return {'value': res}

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_property_management, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res
    
    def update_property_management_from_ITAM(self, cr, uid, employee_id, login, mass_status_id, context=None):
        if employee_id and login and mass_status_id:
            mass_status_pool = self.pool.get('vhr.mass.status')
            mass_status_detail_pool = self.pool.get('vhr.mass.status.detail')
            
            log.info("\n\n Start get asset for employee %s" % login)
            _pool = ConnectionPool(int(tools.config['db_maxconn']))
            t_cr = Cursor(_pool, cr.dbname, True)
            mcr = Cursor(_pool, cr.dbname, True)
            try:
                
                property_pool = self.pool.get('vhr.property')
                property_management_pool = self.pool.get('vhr.property.management') 
                checklist_request_pool = self.pool.get('vhr.exit.checklist.request')
                checklist_detail_pool = self.pool.get('vhr.exit.checklist.detail')
                property_type_ids = self.pool.get('vhr.property.type').search(t_cr, uid, [('code','=','IT')])
                if not property_type_ids:
                    log.info("\n\n Don't have property type with code = 'IT' ")
                    return True
                
                from suds.client import Client
                url = 'http://.svc?wsdl'
                client = Client(url)
                result=client.service.GetAssetOfUser(login)
                update_create_ids = []
                create_ids = []
                if result:
                    log.info('Parse data from ITAM with employee: %s'% login)
#                     log.info(result)
                    for list in result:
                        for team in list:
                            for item in team:
                                property_code = ''
                                property_name = ''
                                issue_date = False
                                property_state = ''
                                property_model = ''
                                property_note = ''
                                if 'AssetCode' in item:
                                    property_code = item['AssetCode']
                                if 'AssetType' in item:
                                    property_name = item['AssetType']
                                if 'AssignDate' in item:
                                    issue_date = item['AssignDate']
                                if 'ResourceState' in item:
                                    property_state = item['ResourceState']
                                if 'Model' in item:
                                    property_model = item['Model']
                                if 'Note' in item:
                                    property_note = item['Note']
                                    if not property_note:
                                        property_note = ''
                                    if '<a' in property_note:
                                        first_index = property_note.index('>')
                                        property_note = property_note[first_index:]
                                        second_index = property_note.index('<')
                                        property_note = property_note[:second_index]
                                
                                if issue_date:
                                    try:
                                        issue_date = datetime.strptime(issue_date, '%d/%m/%Y')
                                    except Exception as e:
                                        issue_date = False
                                    
                                property_ids = property_pool.search(t_cr, uid, [('name','=',property_name)])
                                if property_ids:
                                    property_management_ids = property_management_pool.search(t_cr, uid, [('employee_id','=',employee_id),
                                                                                                        ('property_code','=',property_code),
                                                                                                        ('property_id','=',property_ids[0])
                                                                                                       ])
                                    #Nếu đã có dữ liệu tài sản, thì ghi lại 1 số thông tin
                                    #Nếu chưa có dữ liệu tài sản, thì thêm mới
                                    if property_management_ids:
                                        data = {
                                                'issue_date': issue_date,
                                                'description': property_note + ';;;;' + property_model,
                                                'active': True}
                                        
                                        property_management_pool.write(t_cr, uid, property_management_ids[0], data)
                                        update_create_ids.append(property_management_ids[0])
                                    else:
                                        data = {'employee_id': employee_id,
                                                'property_code': property_code,
                                                'property_id': property_ids[0],
                                                'property_type_id':property_type_ids and property_type_ids[0],
                                                'issue_date': issue_date,
                                                'description': property_note + ';;;;' + property_model,
                                                'active': True}
                                        
                                        new_property_management_id = property_management_pool.create(t_cr, uid, data)
                                        if new_property_management_id:
                                            update_create_ids.append(new_property_management_id)
                                            create_ids.append(new_property_management_id)
                
                #Inactive những property_management không nhận được từ ITAM
                if update_create_ids:
                    str_update_create_ids = [str(item) for item in update_create_ids]
                    all_ids = property_management_pool.search(t_cr, uid, [('employee_id','=',employee_id),
                                                                        ('property_type_id','=',property_type_ids[0])])
                    
                    inactive_ids = [item for item in all_ids if item not in update_create_ids]
                    if inactive_ids:
                        checklist_ids = checklist_detail_pool.search(t_cr, uid, [('property_management_id','in',inactive_ids)])
                        if checklist_ids:
                            checklist_detail_pool.unlink(t_cr, uid, checklist_ids)
                        property_management_pool.unlink(t_cr, uid, inactive_ids)
                
                
                if create_ids:
                    #Update for Exit Checklist Request of Employee
                    employee = self.pool.get('hr.employee').read(t_cr, uid, employee_id, ['join_date'])
                    employee_join_date = employee.get('join_date',False)
                    checklist_request_ids = checklist_request_pool.search(t_cr, uid, [('employee_id','=',employee_id),
                                                                                    ('join_date','=',employee_join_date)])
                    if checklist_request_ids:
                        property_managements = property_management_pool.read(t_cr, uid, create_ids, ['property_id','issue_date','recovery_date'])
                        for record in property_managements:
                            property_name = record.get('property_id','')
                            if isinstance(property_name, tuple):
                                property_name = property_name[1]
                            data = {'name': property_name, 
                                   'type_exit': 'it_office', 
                                   'allocation_date': record.get('issue_date'),
                                   'withdraw_date': record.get('recovery_date'),
                                   'property_management_id': record['id'],
                                   'exit_checklist_id': checklist_request_ids[0]}
                            
                            checklist_detail_pool.create(t_cr, uid, data)
                
                
                t_cr.commit()
                t_cr.close()
                mcr.commit()
                mcr.close()
                log.info("\n End Get asset for employee %s"% login)
            except Exception as e:
                try:
                    error_item = e.message
                    if not error_item:
                        error_item = e.value
                except:
                    try:
                        error_item = str(e)
                    except:
                        error_item = ""
                
                mass_status_detail_pool.create(mcr, uid, {'mass_status_id': mass_status_id,
                                                           'employee_id': employee_id,
                                                           'message': error_item,
                                                           'status': 'fail'})
                log.exception(e)
                log.info("Can not get asset from employee %s"% login)
                t_cr.commit()
                t_cr.close()
                mcr.commit()
                mcr.close()
            
        return True
    
    
    def cron_get_asset_of_all_employee_from_ITAM(self, cr, uid, context=None):
        if not context:
            context = {}
        
        try:
            log.info("Start cron_get_asset_of_all_employee_from_ITAM")
            employee_pool = self.pool.get('hr.employee')
            employee_ids = []
            employee_ids = employee_pool.search(cr, uid, [('active','=',True)])
#             employee_ids = employee_ids[:200]
            
            len_emp = len(employee_ids)
            
            mass_status_id = self.create_mass_status(cr, uid, len_emp, context)
            employees = employee_pool.read(cr, uid, employee_ids, ['login'])
#             number = 1
#             begin = 0
#             end = 0
#             while number <= 6:
#                 begin = end
#                 end = len_emp / 5 * number
            thread.start_new_thread(vhr_property_management.update_property_management_from_ITAM_for_employees, (self,cr, uid, employees, mass_status_id, context) )
#                 number += 1
                
        except Exception as e:
            log.exception(e)
            log.info("Can not cron_get_asset_of_all_employee_from_ITAM")
            
        return True
    
    def update_property_management_from_ITAM_for_employees(self, cr, uid, employees, mass_status_id, context=None):
        if not context:
            context = {}
        if employees and mass_status_id:
            for employee in employees:
                employee_id = employee['id']
                login = employee.get('login','')
                self.update_property_management_from_ITAM(cr, uid, employee_id, login, mass_status_id, context)
                
        return True
    
    def create_mass_status(self, cr, uid, number_of_record, context=None):
        
        _pool = ConnectionPool(int(tools.config['db_maxconn']))
        t_cr = Cursor(_pool, cr.dbname, True)
        vals = { 'state' : 'new','number_of_record':number_of_record}
        
        employee_ids = self.pool.get('hr.employee').search(t_cr, uid, [('user_id', '=', uid)])
        if employee_ids:
            vals['requester_id'] = employee_ids[0]
            
        module_ids = self.pool.get('ir.module.module').search(t_cr, uid, [('name','=','vhr_master_data')])
        if module_ids:
            vals['module_id'] = module_ids[0]
            
        model_ids = self.pool.get('ir.model').search(t_cr, uid, [('model','=','vhr.property.management')])
        if model_ids:
            vals['model_id'] = model_ids[0]
        
        mass_status_id = self.pool.get('vhr.mass.status').create(t_cr, uid, vals)
        
        t_cr.commit()
        t_cr.close()
        
        return mass_status_id
            
            
        
        


vhr_property_management()