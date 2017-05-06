# -*- coding: utf-8 -*-
import logging
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.osv import osv, fields
from openerp.tools.translate import _
import openerp
from openerp import SUPERUSER_ID

log = logging.getLogger(__name__)

MISS_DATA = 'Employee Code or Number is missing'
MISS_EMP = 'The employee with code %s is missing'
MISS_COUNTRY = 'The country with name %s is missing'
MISS_CITY = 'The city with name %s is missing'
MISS_DISTRICT = 'The district with name %s is missing'
MISS_STATUS = 'The status with name %s is missing'
DUPLICATE_DATA = 'The tax code of %s is existed'
WRONG_NUMBER = 'The Number must be more than 9 characters'

class vhr_personal_document(osv.osv):
    _name = 'vhr.personal.document'
    _inherit = 'vhr.personal.document'
    
    _columns = {
        'employee_code': fields.related('employee_id', 'code', type='char', string='Employee Code'),
    }
    
    def create(self, cr, uid, vals, context=None):
        if vals.get('employee_code', False) and not vals.get('employee_id', False):
            emp_ids = self.pool.get('hr.employee').search(cr, uid, [('code','=', vals['employee_code'])])
            if emp_ids:
                vals['employee_id'] = emp_ids[0]
#         
        res = super(vhr_personal_document, self).create(cr, uid, vals)
        
        return res

    def _get_employee_id_by_code(self, cr, uid, code, context=None):
        if context is None:
            context = {}
        if not code:
            return False
        c = context.copy()
        c.update({'active_test': False})
        employee_ids = self.pool['hr.employee'].search(cr, uid, [('code', '=', code)], context=c)
        if not employee_ids:
            return False
        return employee_ids[0]

    def _convert_date_format(self, string_date):
        if not string_date:
            return False
        return datetime.strptime(string_date, '%d/%m/%Y').strftime('%Y-%m-%d')

    def _is_doc_existed(self, cr, uid, employee_id, doc_type_id, context=None):
        if context is None:
            context = {}
        if not employee_id or not doc_type_id:
            return False
        tax_code_doc_ids = self.search(cr, uid, [('employee_id', '=', employee_id),
                                                 ('active', '=', True),
                                                 ('document_type_id', '=', doc_type_id)], context=context)
        if not tax_code_doc_ids:
            return False
        return True

    def _get_country_id_by_name(self, cr, uid, name, context=None):
        if context is None:
            context = {}
        if not name:
            return False
        country_ids = self.pool['res.country'].search(cr, uid, [('name', '=', name)])
        if not country_ids:
            return False
        return country_ids[0]

    def _get_district_id_by_name(self, cr, uid, name, context=None):
        if context is None:
            context = {}
        if not name:
            return False
        district_ids = self.pool['res.district'].search(cr, uid, [('name', '=', name)])
        if not district_ids:
            return False
        return district_ids[0]

    def _get_city_id_by_name(self, cr, uid, name, context=None):
        if context is None:
            context = {}
        if not name:
            return False
        city_ids = self.pool['res.city'].search(cr, uid, [('name', '=', name)])
        if not city_ids:
            return False
        return city_ids[0]

    def _get_status_id_by_code(self, cr, uid, code, context=None):
        if context is None:
            context = {}
        if not code:
            return False
        status_ids = self.pool['vhr.personal.document.status'].search(cr, uid, [('code', '=', code)])
        if not status_ids:
            return False
        return status_ids[0]

    def _get_doc_type_id_by_code(self, cr, uid, code, context=None):
        if context is None:
            context = {}
        if not code:
            return False
        doc_type_ids = self.pool['vhr.personal.document.type'].search(cr, uid, [('code', '=', code)])
        if not doc_type_ids:
            return False
        return doc_type_ids[0]
    
    
    #Import nửa vời thế nhỉ
    def thread_import_tax_code(self, cr, uid, import_status_id, rows, context=None):
        
        if context is None:
            context = {}
        log.info('Begin: thread_import_tax_code')
        import_obj = self.pool.get('vhr.import.status')
        try:
            db = openerp.sql_db.db_connect(cr.dbname)
            cr = db.cursor()
            tax_code_doc_type_id = self._get_doc_type_id_by_code(cr, uid, 'TAXID', context=context)
            model_ids = self.pool.get('ir.model').search(cr, uid, [('model', '=', self._name)])
            model_id = model_ids and model_ids[0] or False
            detail_obj = self.pool['vhr.import.detail']
            import_obj.write(cr, uid, [import_status_id],
                             {'state': 'processing', 'num_of_rows': rows.nrows, 'current_row': 0, 'model_id': model_id})
            cr.commit()
            if not tax_code_doc_type_id:
                log.info('Error ! Cannot found document type with code TAXID')
                log.info('End: thread_import_tax_code')
                import_obj.write(cr, uid, [import_status_id], {'state': 'error'})
                cr.commit()
                cr.close()
                return True
            row_counter = 0
            success_row = 0
            for row in rows._cell_values:
                row_counter += 1
                if row_counter > 2:
                    vals_detail = {}
                    emp_code, number, issue_date, country, place_of_issued, district, status = row[0:7]
                    if emp_code and number:
                        employee_id = self._get_employee_id_by_code(cr, uid, emp_code, context=context)
                        if employee_id:
                            tax_code_doc_ids = self._is_doc_existed(cr, uid, employee_id, tax_code_doc_type_id, context=context)
                            if not tax_code_doc_ids:
                                if len(str(number)) >= 9:
                                    issue_date = issue_date and self._convert_date_format(issue_date) or False
                                    number = number and str(number) or ''
                                    msgs = []
                                    country_id = country and self._get_country_id_by_name(cr, uid, country, context=context) or False
                                    if country and not country_id:
                                        msgs.append(MISS_COUNTRY % (country))
                                    city_id = place_of_issued and self._get_city_id_by_name(cr, uid, place_of_issued, context=context) or False
                                    if place_of_issued and not city_id:
                                        msgs.append(MISS_CITY % (place_of_issued))
                                    district_id = district and self._get_district_id_by_name(cr, uid, district, context=context)
                                    if district and not district_id:
                                        msgs.append(MISS_DISTRICT % (district))
                                    status_id = status and self._get_status_id_by_code(cr, uid, status, context=context)
                                    if status and not status_id:
                                        msgs.append(MISS_STATUS % (status))
                                    if msgs:
                                        vals_detail = {'import_id': import_status_id, 'row_number': row_counter,
                                                       'message': ", ".join(msgs)}
                                    vals = {
                                        'employee_id': employee_id,
                                        'number': number,
                                        'issue_date': issue_date,
                                        'country_id': country_id,
                                        'city_id': city_id,
                                        'district_id': district_id,
                                        'status_id': status_id,
                                        'document_type_id': tax_code_doc_type_id,
                                    }
                                    self.create(cr, uid, vals, context=context)
                                    success_row = success_row + 1
                                else:
                                    vals_detail = {'import_id': import_status_id, 'row_number': row_counter,
                                                   'message': WRONG_NUMBER}
                            else:
                                vals_detail = {'import_id': import_status_id, 'row_number': row_counter,
                                               'message': DUPLICATE_DATA % (emp_code)}
                        else:
                            vals_detail = {'import_id': import_status_id, 'row_number': row_counter,
                                           'message': MISS_EMP % (emp_code)}
                    else:
                        vals_detail = {'import_id': import_status_id, 'row_number': row_counter, 'message': MISS_DATA}
                    if vals_detail:
                        detail_obj.create(cr, uid, vals_detail)
                        cr.commit()
                import_obj.write(cr, uid, [import_status_id], {'current_row': row_counter, 'success_row': success_row})
                cr.commit()
            import_obj.write(cr, uid, [import_status_id], {'state': 'done'})
            cr.commit()
        except Exception as e:
            import_obj.write(cr, uid, [import_status_id], {'state': 'error'})
            cr.commit()
            log.info(e)
            cr.rollback()
        finally:
            cr.close()
        log.info('End: thread_import_tax_code')
        return True
    
    def thread_import_personal_document(self, cr, uid, import_status_id, rows, context=None):
        log.info('Begin: thread_import_personal_document')
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
                              'Document Type':'document_type_id',
                              'Number': 'number',
                              'Issue Date': 'issue_date', 
                              'Expiry Date': 'expiry_date', 
                              'Country': 'country_id',
                              'Place of Issued': 'city_id',
                              'District': 'district_id',
                              'Status': 'status_id',
                              'Is Received Hard Copy': 'is_received_hard_copy',
                              'Active': 'active',
                              }
            
            required_fields = ['employee_id','document_type_id','number']
            fields_order = []
            fields_search_by_name = ['document_type_id','country_id','city_id','district_id','status_id']
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
                                missing_fields = list(set(required_fields).difference(set(input_required_fields)))
                                missing_name_fields = []
                                for key, value in mapping_fields.iteritems():
                                    if value in missing_fields:
                                        missing_name_fields.append(key)
                                
                                error = "You have to input data in %s" % str(missing_name_fields)
                            
                            else:    
                                onchange_vals = self.onchange_document_type_id(cr, uid, [], vals.get('document_type_id', False))
                                if onchange_vals.get('onchange', {}) and onchange_vals['onchange'].get('has_expiry_date', False)\
                                 and not vals.get('expiry_date'):
                                    error = "You have to input expiry date with this document type"
                                
                                if not error and not vals.get('issue_date', False):
                                    #CHeck if exist null issue date personal document when import personal document with empty issue_date
                                    dup_ids = self.search(cr, uid, [('employee_id','=', vals.get('employee_id', False)),
                                                                       ('document_type_id','=',vals.get('document_type_id', False)),
                                                                       ('issue_date','=', False),
                                                                       ('expiry_date','=', False),
                                                                       '|',('active','=', True),
                                                                           ('active','=', False)])
                                    if dup_ids:
                                        error = "Exist personal document with same document type!"
                                    
                                    
                                
                                if not error:
                                    #Search personal document
                                    mode = 'init'
                                    current_module = ''
                                    noupdate = False
                                    xml_id = vals.get('xml_id', False)
                                    
                                    
                                    #Search personal document have same employee_id and document_type_id  and number to override
                                    old_ids = self.search(cr, uid, [('employee_id','=',vals.get('employee_id', False)),
                                                                    ('document_type_id','=',vals.get('document_type_id',False)),
                                                                    ('number','=',vals.get('number',False))])
                                    
                                        
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
        log.info('End: thread_import_personal_document')
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

vhr_personal_document()