#-*-coding:utf-8-*-
from openerp.osv import osv, fields
import logging


log = logging.getLogger(__name__)

class vhr_test_result(osv.osv):#should name vhr_rr_test_result
    _name = 'vhr.test.result'
    _description = 'VHR Test Result'
    
    _columns = {
                'name': fields.char('Test Name', size=256),
                'candidate_id' : fields.many2one('hr.applicant', 'Candidate ID'),
                'test_date': fields.date('Test Date'),
                'test_result': fields.char('Test Result'),
                'test_type_id': fields.many2one('vhr.dimension', 'Test Type', ondelete='restrict',
                                     domain=[('dimension_type_id.code', '=', 'RR_TEST_TYPE'), ('active', '=', True)]),
                'note': fields.text('Notes'),
     }
    
    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        args_new = ['|', '|', ('name', operator, name), ('code', operator, name), ('name_en', operator, name)] + args
        ids = self.search(cr, uid, args_new, context=context)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(vhr_test_result, self).name_search(cr, uid, name, args, operator, context, limit)
    
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_test_result, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res
    
vhr_test_result()





