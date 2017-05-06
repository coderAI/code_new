# -*-coding:utf-8-*-
import logging
from openerp.osv import osv, fields
from openerp import SUPERUSER_ID

log = logging.getLogger(__name__)
class vhr_sm_email(osv.osv):
    _name = 'vhr.sm.email'
    _inherit = 'vhr.sm.email'

    _columns = {
        'ot_id': fields.many2one('vhr.ts.overtime', 'Overtime'),
    }

    def execute_action(self, cr, action_uid, record, context=None):
        if not context:
            context = {}
        if record:
            ot_object = self.pool.get('vhr.ts.overtime')
            log.info('Execute Workflow with uid %s' % action_uid)
            if context.get('mail_decide', False) in ['return','approve','reject']:
                context['action'] = context.get('mail_decide','')
                context['ACTION_COMMENT'] = 'action from email'
                if record.ot_id:
                    ot_object.execute_workflow(cr, action_uid, record.ot_id.id, context)
                else:
                    context = super(vhr_sm_email, self).execute_action(cr, action_uid, record, context)
            
        return context
        

vhr_sm_email()