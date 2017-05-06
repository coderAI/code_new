import logging
from openerp.osv import fields, osv
from openerp.tools.translate import _


log = logging.getLogger(__name__)

class function_migrate_data(osv.osv_abstract):
    
    _name = 'function.migrate.data'
    
    
    def create_sequence_for_employee_code(self, cr, uid):
        log.info('======= START create sequence in  create_sequence_for_employee_code ========')
        
        sequence_type_obj = self.pool.get('ir.sequence.type')
        sequence_obj = self.pool.get('ir.sequence')
        employee_obj = self.pool.get('hr.employee')
        company_group_obj = self.pool.get('vhr.company.group')
        
        sequence_code = 'hr.employee.sequence'
        #Create sequence type hr.employee.code
        sequence_type_id = sequence_type_obj.search(cr, uid, [('code','=', sequence_code)])
        if sequence_type_id:
            return True
        
        type_vals = {'name': 'HR Employee ', 'code': sequence_code}
        sequence_type_id = sequence_type_obj.create(cr, uid, type_vals)
        
        if sequence_type_id:
            company_group_ids = company_group_obj.search(cr, uid, [])
            context = {'active_test': False}
            if company_group_ids:
                for company_group in company_group_obj.read(cr, uid, company_group_ids, ['name','code']):
                    company_group_id = company_group['id']
                    ids = employee_obj.search(cr, uid, [('company_group_id', '=', company_group_id)], None, None, 'id desc, code desc', context, False)
                    max_value = 0
                    for read_res in employee_obj.read(cr, uid, ids, ['code']):
                        if read_res and isinstance(read_res['code'], (str, unicode)):
                            split_stt = read_res['code'].split('-')
                            if int(split_stt[1]) > max_value:
                                max_value = int(split_stt[1])
                    
                    vals = {'name': 'Employee Code Sequence ' + company_group['code'],
                            'code': sequence_code,
                            'company_id': False,
                            'company_group_id': company_group_id,
                            'padding': 5,
                            'prefix': company_group['code'] + '-'
                            }
                    sequence_id = sequence_obj.create(cr, uid, vals, context)
                    
                    #Update current value
                    sql = "SELECT setval('%s', %s)"
                    cr.execute(sql%('ir_sequence_%03d'%sequence_id, max_value))

        log.info('======= END create sequence create_sequence_for_employee_code ========')
        return True
        
        