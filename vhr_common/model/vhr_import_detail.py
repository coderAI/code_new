# -*-coding:utf-8-*-
import logging
from openerp.osv import osv, fields
#TODO : move to master data
#TODO : change menu rr, security rr
log = logging.getLogger(__name__)

class vhr_import_detail(osv.osv):
    _name = 'vhr.import.detail'
    _description = 'VHR Import Detail'

    _columns = {
        'import_id': fields.many2one('vhr.import.status','Import'),
        'row_number': fields.integer('Row'),
        'message' : fields.char('Message', size = 254),
        'status': fields.selection([('fail', 'Failed'), ('success', 'Success')], 'Status'),
    }
    _order = 'status asc, row_number desc'
vhr_import_detail()
