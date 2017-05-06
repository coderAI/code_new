# -*-coding:utf-8-*-
import logging
from openerp.osv import osv, fields

log = logging.getLogger(__name__)


class vhr_termination_request(osv.osv):
    _inherit = 'vhr.termination.request'
    _description = 'Termination Request'
    
    
    _columns = {
        'job_applicant_id': fields.many2one('vhr.job.applicant', 'Job Applicant'),
    }


    def action_next(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = super(vhr_termination_request, self).action_next(cr, uid, ids, context)           
        terminations = self.browse(cr, uid, ids,context=context)
        for termination in terminations:
            if termination.state in ['finish']:
                employee_id = termination.employee_id.id if termination.employee_id else False
                termination_id = termination.id
                if termination.contract_type_id and termination.contract_type_id.contract_type_group_id:
                    contract_type_group= termination.contract_type_id.contract_type_group_id.code
                    state_change = 'opening'
                    state_candidate = 'employee'
                    if employee_id and termination_id and contract_type_group in ('2','CTG-008'):
                        cr.execute('update hr_applicant set state = %s\
                            where id in (\
                                    select hra.id\
                                    from hr_applicant hra\
                                    left join vhr_termination_request tr on tr.employee_id = hra.emp_id\
                                    where tr.is_change_contract_type = true and hra.emp_id = %s and hra.state = %s and tr.id = %s\
                                   )',(state_change,employee_id,state_candidate,termination_id))
                            
            return res


vhr_termination_request()
