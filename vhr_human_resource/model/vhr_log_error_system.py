# -*-coding:utf-8-*-
import logging

from datetime import datetime
from openerp.osv import osv, fields

from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT

log = logging.getLogger(__name__)


class vhr_log_error_system(osv.osv):
    _name = 'vhr.log.error.system'
    _description = 'VHR Log Error System'
    
    _columns = {
        'name': fields.char('Name', size=512),
        'module': fields.char('Module'),
        'model': fields.char('Object'),
        'log_time': fields.datetime('Log time'),
        'description': fields.text('Description'),
        'parameter': fields.char('Parameter'),
        
    }
    
    _order = 'log_time desc'
    
    def create_from_data(self, cr, uid, module, model, description, parameter, context=None):
        if module and model and description and parameter:
            import openerp
            db = openerp.sql_db.db_connect(cr.dbname)
            mcr = db.cursor()
            vals = {'module': module,
                    'model': model,
                    'description': description,
                    'parameter': parameter}
            
            vals['log_time'] = datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            
            self.create(mcr, uid, vals, context)
            mcr.commit()
            mcr.close()
        
        return True
    
    def name_get(self, cr, uid, ids, context=None):
        if not ids or False in ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        
        reads = self.read(cr, uid, ids, ['log_time'], context=context)
        res = []
        for record in reads:
                res.append((record['id'], record.get('log_time','')))
        return res
    


vhr_log_error_system()