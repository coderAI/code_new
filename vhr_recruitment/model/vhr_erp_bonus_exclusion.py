# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from dateutil import relativedelta

log = logging.getLogger(__name__)

DEPT_EXCEPT = 'EXCLUSION_1'
LEVEL_EXCEPT_OTHER = 'EXCLUSION_2'
LEVEL_EXCEPT = 'EXCLUSION_3'
REPORT_EXCEPT = 'EXCLUSION_4'
CANDIDATE_EXCEPT = 'EXCLUSION_5'
CTV_EXCEPT = 'EXCLUSION_6'
SPECIAL_EXCEPT = 'EXCLUSION_7'



class vhr_erp_bonus_exclusion(osv.osv):
    _name = 'vhr.erp.bonus.exclusion'
    _description = 'VHR ERP Bonus Exclusion'
    
    
    def _get_department_team_ids(self, cr, uid, ids, name, arg, context=None):
        res = {}
        department_ids = []
        department_team_ids = []
        depament_obj = self.pool.get('hr.department')
        for data in self.browse(cr, uid, ids):
            for item in data.department_ids:
                parent_id = item.department_id
                department_ids.append(parent_id)
                
        if department_ids:
            department_team_ids = depament_obj.search(cr, uid, [('parent_id','in',department_ids[0][2])])
            if department_team_ids:
                for item in depament_obj.browse(cr, uid, department_team_ids):
                    department_id = item.id
                    department_team_ids.append(department_id)
            res[data.id] = department_team_ids
        return res

    _columns = {
        'name': fields.char('Name', size=128),
        'code': fields.char('Code', size=128),
        'value': fields.char('Value', size=255),
        'department_ids': fields.many2many('hr.department', 'erp_bonus_exclusion_department_rel',
                                           'exclusion_id', 'department_id', 'Value Dept',
                                           domain="[('organization_class_id.level','in',[3,6])]"),
                
        'level_ids': fields.many2many('vhr.job.level', 'erp_bonus_exclusion_level_rel', 
                                      'exclusion_id', 'level_id', 'Value Level'),
                
        'level_position_ids': fields.many2many('vhr.job.level.new', 'erp_bonus_exclusion_level_position_rel', 
                                      'exclusion_id', 'level_position_id', 'Value Position Level'), 
                
        'employee_ids': fields.many2many('hr.employee', 'erp_bonus_exclusion_employee_rel', 
                                      'exclusion_id', 'employee_id', 'Employee Level',),
                
        'special_employee_ids': fields.many2many('hr.employee', 'erp_bonus_special_exclusion_employee_rel', 
                                      'special_exclusion_id', 'employee_id', 'Special Employee',),
        
        'bonus': fields.float('Bonus'),
        'description': fields.text('Description'),
        'active': fields.boolean('Active'),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                         domain=[('object_id.model', '=', _name),
                                                 ('field_id.name', 'not in', ['write_date', 'audit_log_ids'])]),
       
        'department_line_ids': fields.one2many('vhr.erp.exclusion.department.line','department_line_id','Value Dept'),
    }

    _defaults = {
        'active': True,
    }

    def check_ex(self, cr, uid, code, context=None):
        dept_except = self.search(cr, uid, [('code', '=', code), ('active', '=', True)], context=context)
        if dept_except:
            return dept_except[0]
        return False
    
    def check_employee_exlusion(self, cr, uid, employee_id,exclusion_id, context=None):
        cr.execute('select employee_id, exclusion_id from erp_bonus_exclusion_employee_rel where employee_id = %s and exclusion_id = %s',(employee_id,exclusion_id))
        result = cr.fetchall()        
        if result:
            return False
        return True
    
            
    def get_bonus_by_code(self, cr, uid, code, context=None):
        dept_except = self.search(cr, uid, [('code', '=', code)], context=context)
        result = []
        if dept_except:
            lst_value = self.browse(cr, uid, dept_except[0], context=context)
            if code == DEPT_EXCEPT:
                for item in lst_value.department_line_ids:
                    if len(item.department_team_ids) > 0:
                        for team in item.department_team_ids:
                            result.append(team.code)
                    elif item.department_id and len(item.department_team_ids) < 0:
                        result.append(item.department_id.code)
                            
            if code == LEVEL_EXCEPT_OTHER:
                for item in lst_value.level_position_ids:
                    result.append(item.code)
            if code == LEVEL_EXCEPT:
                for item in lst_value.employee_ids:
                    result.append(item.id)
            if code == SPECIAL_EXCEPT:
                for item in lst_value.special_employee_ids:
                    result.append(item.id)
        return result

    def get_exclusion_erp(self, cr, uid, recommender_id, recom_depart_code,recom_depart_team_code, recom_level_code,
                          offer_depart_code, offer_depthead_id, offer_report_to_id, job_applicant_id, context=None):        
        result = False
        dept_except = self.get_bonus_by_code(cr, uid, DEPT_EXCEPT)
        level_except = self.get_bonus_by_code(cr, uid, LEVEL_EXCEPT)
        special_except = self.get_bonus_by_code(cr, uid, SPECIAL_EXCEPT)
        level_except_other = self.get_bonus_by_code(cr, uid, LEVEL_EXCEPT_OTHER)
        
        report_to = False
        employee = self.pool.get('hr.employee').browse(cr, uid, offer_report_to_id, context=context)
        if employee:
            report_to = employee.report_to.id if employee.report_to else False
            
        if self.check_ex(cr, uid, DEPT_EXCEPT) and (recom_depart_code in dept_except or recom_depart_team_code in dept_except):
            return self.check_ex(cr, uid, DEPT_EXCEPT)
          
        if self.check_ex(cr, uid, LEVEL_EXCEPT_OTHER) and (recom_level_code in level_except_other and offer_depart_code == recom_depart_code):
            return self.check_ex(cr, uid, LEVEL_EXCEPT_OTHER)
        
        if self.check_ex(cr, uid, LEVEL_EXCEPT) and recommender_id in level_except:
            return self.check_ex(cr, uid, LEVEL_EXCEPT)
        
        if self.check_ex(cr, uid, SPECIAL_EXCEPT) and recommender_id in special_except:
            return self.check_ex(cr, uid, SPECIAL_EXCEPT)
        
        if self.check_ex(cr, uid, REPORT_EXCEPT) and\
            ((recommender_id == offer_report_to_id or recommender_id == report_to) and (offer_depart_code == recom_depart_code)):
            return self.check_ex(cr, uid, REPORT_EXCEPT)
        
        if self.check_ex(cr, uid, CTV_EXCEPT):
            job_applicant = self.pool.get('vhr.job.applicant').browse(cr, uid, job_applicant_id)
            contract_obj = self.pool.get('hr.contract')
            termination_job = self.pool.get('vhr.termination.request')
            working_obj = self.pool.get('vhr.working.record')
            if job_applicant:
                is_new_emp = job_applicant.is_new_emp
                contracts = contract_obj.search(cr, uid, [('job_applicant_id', '=', job_applicant_id)],order= 'id desc', context=context)
                if contracts:
                    contract_candidate_hd = contract_obj.browse(cr, uid, contracts[0],context=context)
                    if contract_candidate_hd.type_id and contract_candidate_hd.type_id.contract_type_group_id and\
                        contract_candidate_hd.type_id.contract_type_group_id.code not in ( '2','CTG-008') and not is_new_emp:
                        sign_date  = job_applicant.join_date
                        if job_applicant.applicant_id and job_applicant.applicant_id.emp_id:
                            applicant_id = job_applicant.applicant_id.emp_id.id
                            termination_request_ids = termination_job.search(cr, uid, [('employee_id', '=', applicant_id),('state','=','finish')],order= 'id desc', limit = 1, context=context)
                            if termination_request_ids:
                                termination_request = termination_job.browse(cr, uid, termination_request_ids[0], context=context)
                                if termination_request.is_change_contract_type and termination_request.contract_id.type_id.contract_type_group_id.code in ('2','CTG-008'):
                                    working_record_ids = working_obj.search(cr, uid, [('employee_id', '=', applicant_id)],order = 'id asc', limit = 1, context=context)
                                    if working_record_ids:
                                        working_record = working_obj.browse(cr, uid, working_record_ids[0], context = context)
                                        join_date = working_record.effect_from
                                        format_date ='%Y-%m-%d'
                                        d1 = datetime.strptime(sign_date, format_date)
                                        d2 = datetime.strptime(join_date, format_date)
                                        temp_date = relativedelta.relativedelta(d1, d2)
                                        month_temp = temp_date.months
                                        if month_temp > 3:
                                            return self.check_ex(cr, uid, CTV_EXCEPT)
                                        
        if self.check_ex(cr, uid, CANDIDATE_EXCEPT):
            #nhan vien cu quay lai lam viec
            termination_job = self.pool.get('vhr.termination.request')
            job_applicant = self.pool.get('vhr.job.applicant').browse(cr, uid, job_applicant_id)
            applicant_id = job_applicant.applicant_id.emp_id.id if job_applicant.applicant_id and job_applicant.applicant_id.emp_id else False
            is_new_emp = job_applicant.is_new_emp
            termination_request_ids = termination_job.search(cr, uid, [('employee_id', '=', applicant_id),('state','=','finish')],order= 'id desc', limit = 1, context=context)
            if termination_request_ids:
                termination_request = termination_job.browse(cr, uid, termination_request_ids[0], context=context)
                if not termination_request.is_change_contract_type and not is_new_emp:
                    return self.check_ex(cr, uid, CANDIDATE_EXCEPT)
    
        return result

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_erp_bonus_exclusion, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res

vhr_erp_bonus_exclusion()
