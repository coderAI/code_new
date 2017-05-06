import logging
from openerp.osv import fields, osv
from openerp.tools.translate import _


log = logging.getLogger(__name__)

class function_migrate_data(osv.osv_abstract):
    
    _name = 'function.migrate.data'
    
    
    def update_change_form_field_new_job_level(self, cr, uid):
        log.info('======= START MIGRATE update_change_form_field_new_job_level ========')
        
        field_to_update = ['job_level_person_id_new']
        
        cr.execute("""
                    SELECT form.change_form_id,form.field_id,field.name 
                    FROM change_form_working_field form INNER JOIN ir_model_fields field ON form.field_id =field.id
                    WHERE field.name in %s
                    """ % str(tuple(field_to_update)).replace(',)', ')'))
        data = cr.fetchall()
        if data:
            return True
        
        cr.execute("""
                            SELECT * from ir_model_fields 
                            WHERE name in %s
                                     and model='vhr.working.record'
                            """% str(tuple(field_to_update)).replace(',)', ')'))
        
        field_datas = cr.fetchall()
        
        if field_datas:
            cr.execute("""
                        SELECT form.change_form_id
                        FROM change_form_working_field form INNER JOIN ir_model_fields field ON form.field_id =field.id
                        WHERE field.name='job_level_id_new'
                        """)
            data_forms = cr.fetchall()
            
            for field_data in field_datas:
                for form in data_forms:
                    sql = '''
                        INSERT INTO change_form_working_field (change_form_id, field_id) VALUES (%s, %s)
                    ''' % (form[0],field_data[0])
                    cr.execute(sql)
        

        log.info('======= END MIGRATE update_change_form_field_new_job_level ========')
        return True
    
    def update_signer_appendix_contract(self, cr, uid):
        log.info('======= START MIGRATE update_signer_appendix_contract ========')
        appendix_pool = self.pool['vhr.appendix.contract']
        
        try:
            #Search appendix dont have sign date
            appendix_ids = appendix_pool.search(cr, uid, [('sign_date','=',False),
                                                          ('is_extension_appendix','=',True),
                                                          ('name','!=',False)], order = 'name asc')
            if appendix_ids:
                for appendix in appendix_pool.read(cr, uid, appendix_ids, ['contract_id','date_start']):
                    vals = {}
                    
                    #Get signer info
                    contract_id = appendix.get('contract_id', False) and appendix['contract_id'][0]
                    if contract_id:
                        contract = self.pool['hr.contract'].read(cr, uid, contract_id, ['company_id'])
                        company_id = contract.get('company_id', False) and contract['company_id'][0]
                        if company_id:
                            res_read = self.pool['res.company'].read(cr, uid, company_id, ['sign_emp_id','job_title_id','country_signer'])
                            if res_read['sign_emp_id']:
                                vals.update({'info_signer': res_read['sign_emp_id'],
                                             'title_signer': res_read.get('job_title_id',''),
                                             'country_signer': res_read.get('country_signer',False) and res_read['country_signer'][0] or False,
                                             })
                    
                    
                    date_start = appendix.get('date_start', False)
#                     onchange_res = appendix_pool.on_change_date_start(cr, uid, [], date_start)
#                     sign_date = onchange_res.get('value', {}).get('sign_date', False)
                    vals['sign_date'] = date_start
                    
                    appendix_pool.write(cr, uid, appendix['id'], vals)
            
            
        except Exception as e:
            log.exception(e)
        
        log.info('======= END MIGRATE update_signer_appendix_contract ========')
        return True
    
    
    def update_approve_date_exit_checklist(self, cr, uid):
        log.info('======= START MIGRATE update_approve_date_exit_checklist ========')
        
        try:
            checklist_pool = self.pool['vhr.exit.checklist.request']
            
            exit_ids = checklist_pool.search(cr, uid, [('approve_date','=',False)])
            if exit_ids:
                for exit_id in exit_ids:
                    exit = checklist_pool.perm_read(cr, uid, [exit_id], context = {})[0]
                    create_date = exit.get('create_date', False) and exit.get('create_date', False)[:10]
                    write_date = exit.get('write_date', False) and exit.get('write_date', False)[:10]
                    approve_date = write_date or create_date
                    
                    checklist_pool.write(cr, uid, exit_id, {'approve_date': approve_date})
        
        except Exception as e:
            log.exception(e)
        
        log.info('======= END MIGRATE update_approve_date_exit_checklist ========')
    
    def create_organization_class_department_group(self, cr, uid):
        log.info('======= START MIGRATE create_organization_class_department_group ========')
        try:
            organization_obj = self.pool['vhr.organization.class']
            
            #update level of company to 0
            comp_class_ids = organization_obj.search(cr, uid, [('code','=','COMP'),
                                                              ('level','=',1)])
            if comp_class_ids:
                organization_obj.write(cr, uid, comp_class_ids, {'level': 0})
                
                #update level of division to 1
                division_class_ids = organization_obj.search(cr, uid, [('code','in',['DIV','DIVs']),
                                                              ('level','=',2)])
                if division_class_ids:
                    organization_obj.write(cr, uid, division_class_ids, {'level': 1})
                
                    
                    #Create new class for department group
                    vals = {'code':'DEPT_GROUP',
                            'name':'Department Group', 
                            'level': 2, 
                            'active':True}
                    
                    group_ids = organization_obj.create(cr, uid, vals)
                    if group_ids:
                        organization_obj.write(cr, uid, group_ids, {'code':'DEPT_GROUP'})
            
        
        except Exception as e:
            log.exception(e)
        
        
        
        log.info('======= END MIGRATE create_organization_class_department_group ========')
    
    
    
    
            
        
        
        