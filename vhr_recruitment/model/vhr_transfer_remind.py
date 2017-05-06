from openerp.osv import fields, osv
from openerp.tools.translate import _

class vhr_transfer_remind(osv.osv):
    _name = 'vhr.transfer.remind'
    _description = 'Transfer remind'

    _columns = {
       'name': fields.char('name'),
       'content': fields.html('Content'),
    }
    
    def transfer_cb(self, cr, uid, ids, context):
        if not context:
            context = {}
            
        active_ids = context.get('active_ids', [])
        job_app_obj = self.pool['vhr.job.applicant']
        
        return job_app_obj.transfer_candidate_to_employee(cr, uid, active_ids, context=context)
