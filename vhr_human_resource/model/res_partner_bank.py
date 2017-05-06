# -*-coding:utf-8-*-
import logging

from datetime import datetime,date, timedelta
from openerp.osv import osv, fields
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
# from openerp.addons.vhr_common.model.vhr_common import vhr_common
from openerp import SUPERUSER_ID
# from dateutil.relativedelta import relativedelta
from openerp.tools.translate import _
from openerp.addons.vhr_common.model.vhr_common import vhr_common

log = logging.getLogger(__name__)


class res_partner_bank(osv.osv, vhr_common):
    _inherit = 'res.partner.bank'
    
    def read(self, cr, user, ids, fields=None, context=None, load='_classic_read'):
        if not context:
            context = {}
        
        self.prevent_normal_emp_read_data_of_other_emp(cr, user, ids, [], [], [], context=context)
        
        res =  super(res_partner_bank, self).read(cr, user, ids, fields, context, load)
            
        return res
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if not context:
            context = {}
        
        if 'active_test' not in context:
            context['active_test'] = False

        return super(res_partner_bank, self).search(cr, uid, args, offset, limit, order, context, count)
    
    def thread_import_partner_bank(self, cr, uid, import_status_id, rows, context=None):
        log.info('Begin: thread_import_partner_bank')
        if not context:
            context = {}
        try:
            import openerp
            db = openerp.sql_db.db_connect(cr.dbname)
            cr = db.cursor()
            mcr = db.cursor()
            import_obj = self.pool.get('vhr.import.status')
            detail_obj = self.pool.get('vhr.import.detail')
            employee_obj = self.pool.get('hr.employee')
            parameter_obj = self.pool.get('ir.config_parameter')
            
            model_ids = self.pool.get('ir.model').search(cr, uid, [('model','=',self._name)])
            model_id = model_ids and model_ids[0] or False
            mapping_fields = {'XML ID': 'xml_id',
                              'Employee Code': 'employee_id',
                              'Account Number':'acc_number',
                              'Effective Date': 'effect_from', 
                              'Bank': 'bank', 
                              'Bank Branch': 'bank_branch',
                              'Is Main': 'is_main',
                              }
            
            required_fields = ['employee_id','acc_number','bank']
            fields_order = []
            fields_search_by_name = ['bank','bank_branch']
            ac_fields = self._columns.keys()
            
            import_obj.write(mcr, uid, [import_status_id], {'state': 'processing', 'num_of_rows':rows.nrows-2, 'current_row':0,'model_id': model_id})
            mcr.commit()
            #Dont count two round describe data
            row_counter = 0
            success_row = 0
            for row in rows._cell_values:
                auto_break_thread_monthly_gen = parameter_obj.get_param(cr, uid, 'vhr_human_resource_auto_break_thread') or ''
                try:
                    auto_break_thread_monthly_gen = int(auto_break_thread_monthly_gen)
                except:
                    auto_break_thread_monthly_gen = False
                if auto_break_thread_monthly_gen:
                    break
                
                if row_counter == 0:
                    fields_order = row
                    
                row_counter += 1
                if row_counter > 2:
                    vals_detail = {}
                    data = row[:]
                    
                    
                    vals, error = self.parse_data_from_excel_row(cr, uid, row, mapping_fields, fields_search_by_name, fields_order, context)
                    warning = ''
                    if not error:
                        try:
                            #Check if missing required fields
                            vals_field = vals.keys()
                            input_required_fields = list(set(required_fields).intersection(set(vals_field)))
                            if len(required_fields) != len(input_required_fields):
                                missing_fields = list(set(required_field).difference(set(input_required_fields)))
                                missing_name_fields = []
                                for key, value in mapping_fields.iteritems():
                                    if value in missing_fields:
                                        missing_name_fields.append(key)
                                
                                error = "You have to input data in %s" % str(missing_name_fields)
                            
                            else:    
                                #Search Bank Account
                                mode = 'init'
                                current_module = ''
                                noupdate = False
                                xml_id = vals.get('xml_id', False)
                                
                                
                                if vals.get('employee_id', False):
                                    employee = employee_obj.read(cr, uid, vals['employee_id'], ['name'])
                                    vals['owner_name'] = employee.get('name', '')
                                
                                #Search bank account have same employee_id and acc_number to override
                                old_ids = self.search(cr, uid, [('employee_id','=',vals.get('employee_id', False)),
                                                                ('acc_number','=',vals.get('acc_number',False))])
                                
                                #Ghi đè lên dữ liệu cũ, nếu employee chỉ có 1 bank account và bank account này là Unknown
                                if not old_ids:
                                    bank_ids = self.search(cr, uid, [('employee_id','=',vals.get('employee_id', False)),
                                                                     ('active','=',True)])
                                    if len(bank_ids) == 1:
                                        bank = self.read(cr, uid, bank_ids[0], ['acc_number'])
                                        acc_number = bank.get('acc_number','')
                                        if 'Unknown' in acc_number:
                                            old_ids = bank_ids
                                            print "Override unknown bank account"
                                    
                                if old_ids:
                                    self.write(cr, uid, old_ids, vals, context)
                                else:
                                    self.pool.get('ir.model.data')._update(cr, SUPERUSER_ID, self._name, current_module, vals, mode=mode, xml_id=xml_id,
                                                      noupdate=noupdate, res_id=False, context=context)
                                success_row += 1
                                
                        except Exception as e:
                            log.exception(e)
                            try:
                                error = e.message
                                if not error:
                                    error = e.value
                            except:
                                error = ""
                    if error:
                        vals_detail = {'import_id': import_status_id, 'row_number' : row_counter -2, 'message':error,'status':'fail'}
                        detail_obj.create(mcr, uid, vals_detail)
                        mcr.commit() 
                        cr.rollback()
                    else:
                        if warning:
                            vals_detail = {'import_id': import_status_id, 'row_number' : row_counter -2, 'message':warning,'status':'success'}
                            detail_obj.create(mcr, uid, vals_detail)
                            mcr.commit() 
                        cr.commit()
                    
                import_obj.write(mcr, uid, [import_status_id], {'current_row':row_counter - 2, 'success_row':success_row})
                mcr.commit()
            import_obj.write(mcr, uid, [import_status_id], {'state': 'done'})
            mcr.commit()
        except Exception as e:
            log.exception(e)
            import_obj.write(mcr, uid, [import_status_id], {'state': 'error'})
            mcr.commit()
            log.info(e)
            cr.rollback()
        finally:    
            cr.close()
            mcr.close()
        log.info('End: thread_import_partner_bank')
        return True
    
    def parse_data_from_excel_row(self, cr, uid, row, mapping_fields, fields_search_by_name, fields_order, context=None):
        res = {}
        error = ""
        if row and mapping_fields and fields_order:
            for index, item in enumerate(row):
                #If item in row does not appear in mapping fields, by pass  
                field_name = mapping_fields.get(fields_order[index])
                if field_name:
                    field_obj = self._all_columns.get(field_name)
                    field_obj = field_obj and field_obj.column
                    if field_obj and field_obj._type == 'many2one':
                        model = field_obj._obj
                        value = str(item).strip()
                        
                        try:
                            value = value.replace('\xc2\xa0','')
                        except Exception as e:
                            log.exception(e)
                            
                        if value:
                            
                            #Assign False to field_name if value == 'false'
                            if value in ['false','0']:
                                res[field_name] = False
                                continue
                            
                            domain = ['|',('code','=ilike', value),('name','=ilike', value)]
                            if field_name in fields_search_by_name:
                                domain = [('name','=ilike', value)]
                            record_ids = self.pool.get(model).search(cr, uid, domain)
                            
                            #Try one more time with inactive record
                            if not record_ids:
                                domain.insert(0,('active','=', False))
                                record_ids = self.pool.get(model).search(cr, uid, domain)
                                
                                
                            if len(record_ids) == 0:
                                error = "Can't find record of '%s' with input data '%s' for field '%s'" % (model, value, field_obj.string)
                                return res, error
                            elif len(record_ids) ==1:
                                res[field_name] = record_ids[0]
                                
                            else:#len >=2
                                error = "Have %s record of '%s' with input data '%s' for field '%s'" % (len(record_ids), model, value, field_obj.string)
                                return res, error
                            
                    elif field_obj and field_obj._type == 'date':
                        try:
                            item = str(item)
                            if item:
                                value = datetime.strptime(item,"%d/%m/%Y").strftime(DEFAULT_SERVER_DATE_FORMAT)
                            else:
                                value = False
                                
                            res[field_name] = value
                        except Exception as e:
                            error = "Field %s have to input correct date format dd/mm/YYYY" % field_obj.string 
                    
                    elif field_obj and field_obj._type == 'boolean':
                        value = str(item).lower()
                        if value == 'true' or value == '1':
                            res[field_name] = True
                        else:
                            res[field_name] = False
                    
                    elif field_obj and field_obj._type in ['text','char']:
                        #Khong ghi de du lieu len description neu khong co data import
                        if field_name == 'description' and len(item) == 0:
                            continue
                        res[field_name] = item
                        
                    #log to trace back
                    elif not field_obj and field_name=='xml_id':
                        res[field_name] = str(item).strip()
                    
                            
        
        return res, error

res_partner_bank()