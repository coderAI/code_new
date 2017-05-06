# -*-coding:utf-8-*-
import logging

from openerp.osv import fields
from openerp.osv import osv

log = logging.getLogger(__name__)


class ir_attachment(osv.osv):
    """Attachments are used to link binary files or url to any openerp document.

    External attachment storage
    ---------------------------
    
    The 'data' function field (_data_get,data_set) is implemented using
    _file_read, _file_write and _file_delete which can be overridden to
    implement other storage engines, shuch methods should check for other
    location pseudo uri (example: hdfs://hadoppserver)
    
    The default implementation is the file:dirname location that stores files
    on the local filesystem using name based on their sha1 hash
    """
    _inherit = 'ir.attachment'

    def check(self, cr, uid, ids, mode, context=None, values=None):
        """Restricts the access to an ir.attachment, according to referred model
        In the 'document' module, it is overriden to relax this hard rule, since
        more complex ones apply there.
        """
        if context is None:
            context = {}
        super(ir_attachment, self).check(cr, uid, ids, mode, context, values)
        if mode == 'unlink' and context.get('not_owner_delete', True):
            for item in self.read(cr, uid, ids, ['create_uid']):
                if item['create_uid'] and item['create_uid'][0] != uid:
                    raise osv.except_osv('Validation Error !', 'You cannot delete attached file which you are not owner !')
    
    def validate_read(self, cr, uid, ids, context=None):  # implement
        log.info('validate_read : %s'%(uid))
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]
        for item in self.browse(cr, 1, ids):
            if item.create_uid != uid:
                return False
        return True
    
    def read(self, cr, user, ids, fields=None, context=None, load='_classic_read'):
        if not context:
            context = {}
        
        # if not context.get('do_not_validate_read_attachment', False):
        #     try:
        #         result_check = self.validate_read(cr, user, ids, context)
        #         if not result_check:
        #             raise osv.except_osv('Validation Error !', 'You don’t have permission to access this data !')
        #     except Exception as e:
        #         log.exception(e)
        #         raise osv.except_osv('Read File Error !', 'File not exist or Permission deny on server!')
        
        result = super(ir_attachment, self).read(cr, user, ids, fields, context, load='_classic_read')
            
        return result
    
ir_attachment()