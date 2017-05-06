# -*-coding:utf-8-*-
import logging
from openerp.osv import osv, fields
from xlrd import open_workbook
import base64
import thread
from threading import Thread
import datetime
#TODO : move to master data
#TODO : change menu rr, security rr
log = logging.getLogger(__name__)

class vhr_import_status(osv.osv):
    _name = 'vhr.import.status'
    _description = 'VHR Import Status'

    _columns = {
        'create_date': fields.datetime('Create date'),
        'create_uid': fields.many2one('res.users', 'Created By', readonly=True),
        'module_id': fields.many2one('ir.module.module', 'Module'),
        'model_id': fields.many2one('ir.model', 'Object'),
        'name': fields.char('Name', size=256),
        'db_datas': fields.binary('Data', filters='*.xls', required = True),
        'name_data': fields.char('Name Data', size = 255, required = True),
        'num_of_rows': fields.integer('Num Of Row'),
        'current_row': fields.integer('Current row'),
        'success_row': fields.integer('Success row'),
        'status_ids': fields.one2many('vhr.import.detail', 'import_id', 'Details'),
        'state' : fields.selection([
                                    ('new', 'New'),
                                    ('processing', 'Processing'),
                                    ('error', 'Error'),
                                    ('done', 'Done'),
                                    ], 'State'),
    }

    _defaults = {
        'state': 'new'
    }
    _order = 'create_date desc'
    
    def import_excel_thread(self, cr, uid, ids, context = None):
        log.info('Begin: import_excel_thread')
        if context is None: context = {}
        if not isinstance(ids, list): ids = [ids]
        
        data_file = self.browse(cr, uid, ids)
        if data_file[0].db_datas == False:
            raise osv.except_osv('Validation Error !', 'Dont have file excel to import')
        base_data = base64.decodestring(data_file[0].db_datas)
        row_book = open_workbook(file_contents = base_data)
        rows = row_book.sheet_by_index(0)
        if context.get('function',False) and context.get('model',False) and context.get('module',False):
            try:
                func = context.get('function')
                module = context.get('module',False)
                module_id = self.pool.get('ir.model.data').get_object(cr, uid, 'base', module).id
                vals = {
                       'name' : func,
                       'module_id' : module_id
                }
                self.write(cr, uid, ids, vals)
                cr.commit()
                model = self.pool.get(context.get('model'))
                if model and hasattr(model, func):
                    func = getattr(model, func)
                    t = Thread(target=func, args=(cr, uid, ids[0], rows, context))
                    t.start()
                    if context.get('wait_for_completion', False):
                        t.join()
            except Exception as e:
                    log.exception(e)
        else:
            raise osv.except_osv('Validation Config !', 'Check your import config')
        log.info('End: import_excel_thread')
        return True

vhr_import_status()
