import openerp
import logging

from openerp.tests.common import TransactionCase
from datetime import date, datetime
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT


log = logging.getLogger(__name__)

#  --test-enable --log-level=test

@openerp.tests.common.post_install(True)
class TestSearch(TransactionCase):
    """Tests for correct data

    The name search on account.account is quite complexe, make sure
    we have all the correct results
    """

    def setUp(self):
        log.info("==================================================================================")
        super(TestSearch, self).setUp()
        cr, uid = self.cr, self.uid
        self.employee_model = self.registry('hr.employee')
        self.contract_model = self.registry('hr.contract')
        self.working_model = self.registry('vhr.working.record')
        self.salary_model = self.registry('vhr.pr.salary')
        self.start_time  = date(2015, 07, 01).strftime(DEFAULT_SERVER_DATE_FORMAT)
        self.now = datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT)
        self.message = ''
    
    
    #============================
    #Employee
    #
    #Search active employee and join_date >= end_date
    #Search active employee dont have join_date
    #Search active employee dont have company / employee_code / user_id
    #Search inactive employee have active contract 
    #Search active employee have active contract with liquidation_date = null but have end_date
    #Search active employee have 2 instance null in same company
    #============================
    def test_employee_01(self):
        """
        @see: Search active employee and join_date >= end_date
        """
        cr, uid = self.cr, self.uid
        
        sql = """
                SELECT resource.code FROM hr_employee emp INNER JOIN resource_resource resource ON emp.resource_id = resource.id
                WHERE resource.active=True and emp.join_date is not null and emp.end_date is not null and emp.join_date >= emp.end_date
              """
        cr.execute(sql)
        emp_ids = [item[0] for item in cr.fetchall()]
        self.assertEqual(len(emp_ids), 0, "List active employee with join_date >= end_date: " + str(emp_ids))
    
    def test_employee_02(self):
        """
        #Search active employee dont have join_date
        """
        cr, uid = self.cr, self.uid
        
        sql = """
                SELECT resource.code FROM hr_employee emp INNER JOIN resource_resource resource ON emp.resource_id = resource.id
                WHERE resource.active=True and emp.join_date is null
              """
        cr.execute(sql)
        emp_ids = [item[0] for item in cr.fetchall()]
        self.assertEqual(len(emp_ids), 0, "List active employee have null join_date : " + str(emp_ids))
    
    def test_employee_03(self):
        """
        #Search active employee dont have company
        """
        cr, uid = self.cr, self.uid
        
        sql = """
                SELECT resource.code,emp.resource_id,resource.company_id,emp.login,emp.join_date
                FROM hr_employee emp 
                        INNER JOIN resource_resource resource ON emp.resource_id = resource.id
                        INNER JOIN hr_contract contract ON emp.id=contract.employee_id
                WHERE      resource.active=True 
                      and contract.is_main=True
                      and contract.state='signed'
                      and emp.is_create_account=True
                      and resource.company_id is null
                      and emp.join_date <= '{0}'
              """
        cr.execute(sql.format(self.now))
        emp_ids = [item[0] for item in cr.fetchall()]
        self.assertEqual(len(emp_ids), 0, "List active employee with main signed contract have null company : " + str(emp_ids))
        
    def test_employee_04(self):
        """
        Search employee have active contract dont active
        """
        cr, uid = self.cr, self.uid
        sql = """
                SELECT rr.code from hr_employee emp 
                                  INNER JOIN hr_contract contr ON emp.id=contr.employee_id
                                  INNER JOIN resource_resource rr on emp.resource_id=rr.id
                WHERE rr.active=False and contr.state='signed' and contr.date_start <= now() and 
                      (                  ( contr.date_end >= now() and contr.liquidation_date is null)
                                      OR (contr.date_end is null and contr.liquidation_date is null)
                                      OR contr.liquidation_date > now()
                      )
                      
              """
        cr.execute(sql.format(self.now))
        emp_ids = [item[0] for item in cr.fetchall()]
        self.assertEqual(len(emp_ids), 0, "List inactive employee have active contract : " + str(emp_ids))
    
    def test_employee_05(self):
        """
        #Search active employee dont have resource
        """
        cr, uid = self.cr, self.uid
        
        sql = """
                SELECT resource.code,emp.resource_id,resource.company_id,emp.login,emp.join_date
                FROM hr_employee emp INNER JOIN resource_resource resource ON emp.resource_id = resource.id
                WHERE      resource.active=True 
                      and emp.is_create_account=True
                      and emp.resource_id is null
                      and emp.join_date <= '{0}'
              """
        cr.execute(sql.format(self.now))
        emp_ids = [item[0] for item in cr.fetchall()]
        self.assertEqual(len(emp_ids), 0, "List active employee with null resource_id : " + str(emp_ids))
    
    def test_employee_06(self):
        """
        #Search active employee dont have code
        """
        cr, uid = self.cr, self.uid
        
        sql = """
                SELECT resource.code,emp.resource_id,resource.company_id,emp.login,emp.join_date
                FROM hr_employee emp INNER JOIN resource_resource resource ON emp.resource_id = resource.id
                WHERE      resource.active=True 
                      and emp.is_create_account=True
                      and resource.code is null
                      and emp.join_date <= '{0}'
              """
        cr.execute(sql.format(self.now))
        emp_ids = [item[0] for item in cr.fetchall()]
        self.assertEqual(len(emp_ids), 0, "List active employee with null code : " + str(emp_ids))
        
    def test_employee_07(self):
        """
        #Search active employee have signed contract dont have user_id
        """
        cr, uid = self.cr, self.uid
        
        sql = """
                SELECT resource.code,emp.resource_id,resource.company_id,emp.login,emp.join_date
                FROM hr_employee emp 
                   INNER JOIN resource_resource resource ON emp.resource_id = resource.id
                   INNER JOIN hr_contract contract on emp.id=contract.employee_id
                WHERE      resource.active=True 
                      and emp.is_create_account=True
                      and resource.user_id is null
                      and emp.join_date <= '{0}'
                      and contract.date_start <= '{0}'
                      and (contract.date_end is null or contract.date_end >= '{0}')
                      and contract.state='signed'
              """
        cr.execute(sql.format(self.now))
        emp_ids = [item[0] for item in cr.fetchall()]
        self.assertEqual(len(emp_ids), 0, "List active employee with null user_id : " + str(emp_ids))
        
        
    def test_employee_08(self):
        """
        @see: Search active employee have active contract with liquidation_date = null but have end_date
        """
        cr, uid = self.cr, self.uid
        
        sql = """
                SELECT resource.code,emp.resource_id,resource.company_id,emp.login,emp.join_date
                FROM hr_employee emp 
                   INNER JOIN resource_resource resource ON emp.resource_id = resource.id
                   INNER JOIN hr_contract contract on emp.id=contract.employee_id
                WHERE      resource.active=True 
                      and contract.is_main=True
                      and contract.state='signed'
                      and contract.date_start<= now()
                      and (contract.date_end is null or contract.date_end >= now())
                      and contract.liquidation_date is null
                      and emp.end_date is not null
              """
        cr.execute(sql.format(self.now))
        emp_ids = [item[0] for item in cr.fetchall()]
        self.assertEqual(len(emp_ids), 0, "Employees have active contract with null liquidation but have end_date : " + str(emp_ids))
    
    def test_employee_09(self):
        """
        @see: Search active employee have wrong join_date
        """
        cr, uid = self.cr, self.uid
        
        sql = """
                select resource.code, emp.id,emp.join_date,instance.date_start

                FROM hr_employee emp inner join resource_resource resource on emp.resource_id=resource.id
                             inner join vhr_employee_instance instance on emp.id=instance.employee_id
                             inner join vhr_working_record wr on emp.id=wr.employee_id
                             inner join working_record_change_form_rel rel on wr.id=rel.working_id
                             inner join vhr_termination_request tr on emp.id=tr.employee_id
                WHERE
                
                emp.id in (
                
                        select emp.id
                
                        FROM hr_employee emp inner join resource_resource resource on emp.resource_id=resource.id
                                     inner join vhr_employee_instance instance on emp.id=instance.employee_id
                        WHERE
                             resource.active=True
                        and  instance.date_start != emp.join_date
                        and  instance.id in 
                             (select distinct first_value("id") OVER (PARTITION BY employee_id ORDER BY date_start DESC)  from vhr_employee_instance order by 1)
                        )
                and emp.join_date = instance.date_start
                and instance.date_end is not null
                and wr.effect_from = instance.date_end
                and rel.change_form_id=6
                and tr.is_change_contract_type=False

              """
        cr.execute(sql.format(self.now))
        emp_ids = [item[0] for item in cr.fetchall()]
        self.assertEqual(len(emp_ids), 0, "Active Employees have wrong join_date : " + str(emp_ids))
    
    def test_employee_10(self):
        """
        #Search active employee have 2 employee instance null at same company
        """
        cr, uid = self.cr, self.uid
        
        sql = """
                
            select rr.code from
            hr_employee emp inner join resource_resource rr on emp.resource_id=rr.id
            inner join 
                (
                    SELECT instance.employee_id as "id"
                                    FROM vhr_employee_instance instance
                                    WHERE date_end is null
                                    GROUP BY instance.employee_id,instance.company_id
                                    having count(*)>1) 
                    as wrap on emp.id=wrap.id
                            
                
              """
        cr.execute(sql)
        emp_ids = [item[0] for item in cr.fetchall()]
        self.assertEqual(len(emp_ids), 0, "List active employee have 2 null employee instance in same company : " + str(emp_ids))
        
    
    
    #============================
    #Contract
    #
    #Search any contract start from 14/9/2015 have change form_id but dont have first_working_record_id
    #============================
    def test_contract_01(self):
        """
        #Search any contract start from 14/9/2015 have change form_id but dont have first_working_record_id
        """
        cr, uid = self.cr, self.uid
        
        contract_ids = self.contract_model.search(cr, uid, [('create_date','>=','2015-09-14'),
                                                            ('state','=','signed'),
                                                            ('change_form_id','!=',False),
                                                            ('first_working_record_id','=',False)])
        
        self.assertEqual(len(contract_ids), 0, "List signed contract have change_form_id but dont have first_working_record_id: " + str(contract_ids))
    
    
    
    #============================
    #Working Record
    #
    #Search any working record of same emp-company have more than 1 WR with effect_to = False
    #Search any active employee join date before today dont have effective WR at the moment
    #Search any employee have latest working record is termination but employee.active=true or employee.end_date =null
    #============================
    def test_working_record_01(self):
        """
        #Search any working record of same emp-company have more than 2 WR with effect_to = False
        """
        cr, uid = self.cr, self.uid
        
        
        sql = """
                SELECT  rr.code,wr.employee_id, wr.company_id, count(*)
                FROM vhr_working_record wr
                      INNER JOIN hr_employee emp ON wr.employee_id=emp.id
                      INNER JOIN resource_resource rr ON emp.resource_id=rr.id
                where wr.effect_to is null and (wr.state is null or wr.state ='finish')
                GROUP BY rr.code,wr.employee_id,wr.company_id
                HAVING count(*) >1
              """
        cr.execute(sql)
        emp_ids = [item[0] for item in cr.fetchall()]
        self.assertEqual(len(emp_ids), 0, "Employees with more than 1 WR have effect_to is null: " + str(emp_ids))
    
    def test_working_record_02(self):
        """
        #Search any active employee join date before today dont have effective WR at the moment
        """
        cr, uid = self.cr, self.uid
        
        sql = """
                SELECT  distinct resource.code,wr.employee_id, wr.company_id, resource.code
                FROM vhr_working_record wr INNER JOIN hr_employee emp ON wr.employee_id = emp.id
                                           INNER JOIN resource_resource  resource ON emp.resource_id = resource.id
                where resource.active=True and emp.join_date <= '{0}' and emp.id not in
                
                ( SELECT  wr.employee_id
                FROM vhr_working_record wr INNER JOIN hr_employee emp ON wr.employee_id = emp.id
                                           INNER JOIN resource_resource  resource ON emp.resource_id = resource.id
                where effect_from <= '{0}' and (effect_to is null or effect_to >= '{0}') and resource.active=True
                GROUP BY wr.employee_id,wr.company_id, resource.code
                HAVING count(*) >0)
              """
        cr.execute(sql.format(self.now))
        emp_ids = [item[0] for item in cr.fetchall()]
        emp_ids = list(set(emp_ids))
        self.assertEqual(len(emp_ids), 0, "List active employee dont have any effect WR at the moment: " + str(emp_ids))
        
    
    def test_working_record_03(self):
        """
        #Search any employee have latest working record is termination but employee.active=true or employee.end_date =null
        """
        cr, uid = self.cr, self.uid
        
        sql = """
                SELECT rr.code,emp.login,rr.active, emp.end_date,wr.id
                FROM hr_employee emp inner join resource_resource rr on emp.resource_id = rr.id
                             inner join vhr_working_record wr on emp.id=wr.employee_id
                             inner join working_record_change_form_rel rel on wr.id=rel.working_id
                             inner join (select employee_id, max(effect_from) as effect_from from vhr_working_record group by employee_id) group_wr on emp.id = group_wr.employee_id
                
                WHERE 
                wr.effect_from = group_wr.effect_from
                and wr.effect_from <= now()
                and wr.effect_to is null and rel.change_form_id=6
                and (rr.active=true or emp.end_date is null)
                order by rr.active desc
              """
        cr.execute(sql)
        emp_ids = [item[0] for item in cr.fetchall()]
        emp_ids = list(set(emp_ids))
        self.assertEqual(len(emp_ids), 0, "Employees dont update active=false and set end_date when have termination: " + str(emp_ids))
    
    
    def test_working_record_04(self):
        """
        @see: Search WR with pr_salary_id is not null have wr.gross_salary_new != pr.gross_salary_id or basic_salary!=pr.basic_salary..
        """
        cr, uid = self.cr, self.uid
        
        sql = """
                SELECT wr.id,rr.code,emp.login,rr.active
                FROM vhr_working_record wr 
                    INNER JOIN hr_employee emp on wr.employee_id=emp.id
                    INNER JOIN resource_resource rr on emp.resource_id=rr.id
                    INNER JOIN vhr_pr_salary sal on wr.payroll_salary_id = sal.id
                WHERE
                        rr.active=True
                    and wr.payroll_salary_id is not null
                    and (
                          wr.gross_salary_new != sal.gross_salary
                          or wr.basic_salary_new != sal.basic_salary
                          or wr.v_bonus_salary_new != sal.v_bonus_salary
                          or wr.collaborator_salary_new != sal.collaborator_salary
                        )
              """
        
        cr.execute(sql)
        emp_ids = [item[0] for item in cr.fetchall()]
        emp_ids = list(set(emp_ids))
        self.assertEqual(len(emp_ids), 0, "List WR with not null payroll_salary_id have wrong map salary: " + str(emp_ids))
    
    def test_working_record_05(self):
        """
        @see: Search WR is first_working_record of  Contract have wrong map data with contract
        """
        
        sql ="""
                SELECT rr.code,wr.id,contract.id,emp.login,rr.active
                FROM vhr_working_record wr 
                    INNER JOIN hr_employee emp on wr.employee_id=emp.id
                    INNER JOIN resource_resource rr on emp.resource_id=rr.id
                    INNER JOIN hr_contract contract on wr.contract_id = contract.id
                WHERE
                        rr.active=True
                    and contract.first_working_record_id = wr.id
                    and wr.effect_from>='2016-01-01'
                    and (
                              wr.effect_from != contract.date_start
                          or  wr.office_id_new != contract.office_id
                          or  wr.division_id_new != contract.division_id
                          or  wr.department_id_new != contract.department_id
                          or  wr.department_group_id_new != contract.department_group_id
                          or  wr.job_title_id_new != contract.title_id
                          or  wr.report_to_new != contract.report_to
                          or  wr.team_id_new != contract.team_id
                          or  wr.manager_id_new != contract.manager_id
                          or  wr.seat_new != contract.seat_no
                          or  wr.timesheet_id_new != contract.timesheet_id
                          or  wr.pro_sub_group_id_new != contract.sub_group_id
                          or  wr.pro_job_family_id_new != contract.job_family_id
                          or  wr.ts_working_group_id_new != contract.ts_working_group_id
                          or  wr.salary_setting_id_new != contract.salary_setting_id
                          or  wr.job_level_person_id_new != contract.job_level_person_id
                          or  wr.career_track_id_new != contract.career_track_id
                        )
             """
        cr, uid = self.cr, self.uid
        cr.execute(sql)
        emp_ids = [item[0] for item in cr.fetchall()]
        emp_ids = list(set(emp_ids))
        self.assertEqual(len(emp_ids), 0, "List first working record map wrong data with contract have 'Add To Working Record': " + str(emp_ids))
        
    
    def test_working_record_06(self):
        """
        @see: Search employee have wrong map between data in employee and active WR
        """
        
        sql = """
                SELECT rr.code,emp.id
                
                FROM hr_employee emp 
                    inner join resource_resource rr on emp.resource_id=rr.id
                    inner join vhr_working_record wr on emp.id=wr.employee_id
                
                WHERE 
                        wr.active=True
                    and wr.company_id = rr.company_id
                    and rr.active = True
                    and
                      (
                          emp.division_id != wr.division_id_new
                       or emp.department_group_id != wr.department_group_id_new
                       or emp.department_id != wr.department_id_new
                       or emp.team_id != wr.team_id_new
                       or emp.title_id != wr.job_title_id_new
                       or emp.parent_id != wr.manager_id_new
                       or emp.report_to != wr.report_to_new
                       or emp.office_id != wr.office_id_new
                       or emp.ext_no != wr.ext_new
                       or emp.seat_no != wr.seat_new
                       or emp.keep_authority != wr.keep_authority
                       or emp.job_level_person_id != wr.job_level_person_id_new
                       or emp.job_family_id != wr.pro_job_family_id_new
                       or emp.job_group_id != wr.pro_job_group_id_new
                       or emp.sub_group_id != wr.pro_sub_group_id_new
                       or emp.career_track_id != wr.career_track_id_new
                      )
                
              """
        cr, uid = self.cr, self.uid
        cr.execute(sql)
        emp_ids = [item[0] for item in cr.fetchall()]
        emp_ids = list(set(emp_ids))
        self.assertEqual(len(emp_ids), 0, "List employee have wrong data compare with active WR': " + str(emp_ids))
              
              
    
