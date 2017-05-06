import openerp
import logging

from openerp.tests.common import TransactionCase
from datetime import date, datetime
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from dateutil.relativedelta import relativedelta

log = logging.getLogger(__name__)

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
        self.ws_employee_model = self.registry('vhr.ts.ws.employee')
        self.working_model = self.registry('vhr.working.record')
        self.salary_model = self.registry('vhr.pr.salary')
        self.start_time  = date(2015, 07, 01).strftime(DEFAULT_SERVER_DATE_FORMAT)
        self.now = datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT)
        self.current_year = datetime.now().year
    
    #============================
    #Annual Leave Balance
    #
    #Search active employee at offial contract dont have any annual leave in this year
    #Search official employee dont have enough annual leave balance at the moment
    #Search annual leave have wrong data 
    #Search annual leave have wrong taken day
    #Search annual leave have been duplicate in year
    #===========================
    
    def test_leave_request_01(self):
        """
        @summary: Search holiday detail have number_of_days_temp=0
        """
        cr, uid = self.cr, self.uid
        sql ="""
                SELECT id from vhr_holiday_line
                WHERE (number_of_days_temp = 0 or number_of_days_temp is null)and date >= '2016-01-01'
             """
        
        cr.execute(sql)
        line_ids = [item[0] for item in cr.fetchall()]
        line_ids = list(set(line_ids))
        self.assertEqual(len(line_ids), 0, "List holiday detail have number_of_days_temp = 0 at the moment: " + str(line_ids))
        
        
    
    def test_annual_leave_balance_01(self):
        """
        @see: Search active employee at offial contract dont have any annual leave in this year
        """
        cr, uid = self.cr, self.uid
        sql ="""
                SELECT distinct ct.employee_id, resource.code
                FROM   hr_employee emp
                                       INNER JOIN resource_resource  resource ON emp.resource_id = resource.id
                                       INNER JOIN hr_holidays leave ON leave.employee_id = emp.id
                                       INNER JOIN hr_contract ct ON ct.employee_id = emp.id
                                       INNER JOIN hr_contract_type c_type ON ct.type_id = c_type.id
                                       INNER JOIN hr_contract_type_group c_type_group ON c_type.contract_type_group_id = c_type_group.id
                where ct.date_start_real <= '{0}' and (ct.date_end is null or ct.date_end >= '{0}') and resource.active=True
                      and ct.state = 'finish' and leave.state='validate' and leave.year = {1} 
                      and leave.holiday_status_id=85 and c_type_group.is_offical=True
                GROUP BY ct.employee_id, resource.code
                HAVING count(*) =0
             """
        
        cr.execute(sql.format(self.now,self.current_year))
        emp_ids = [item[1] for item in cr.fetchall()]
        emp_ids = list(set(emp_ids))
        self.assertEqual(len(emp_ids), 0, "List official employee dont have any annual leave balance at the moment: " + str(emp_ids))
        
    
    def test_annual_leave_balance_02(self):
        """
        @see: Search active employee at offial contract join company from previous year have annual leave in current year <14
        """
        cr, uid = self.cr, self.uid
        sql ="""
                SELECT distinct ct.employee_id, resource.code
                FROM   hr_employee emp
                                       INNER JOIN resource_resource  resource ON emp.resource_id = resource.id
                                       INNER JOIN hr_holidays leave ON leave.employee_id = emp.id
                                       INNER JOIN hr_contract ct ON ct.employee_id = emp.id
                                       INNER JOIN hr_contract_type c_type ON ct.type_id = c_type.id
                                       INNER JOIN hr_contract_type_group c_type_group ON c_type.contract_type_group_id = c_type_group.id
                where ct.date_start_real <= '{0}' and (ct.date_end is null or ct.date_end >= '{0}') and resource.active=True
                      and ct.liquidation_date is null
                      and ct.state = 'signed' and leave.state='validate' and leave.year = {1} and leave.type='add'
                      and leave.holiday_status_id=85 and c_type_group.is_offical=True and emp.join_date <= '{2}' and leave.number_of_days_temp <14
             """
        
        today = datetime.today().date()
        first_day_of_year = (date(today.year, 1, 1)).strftime('%Y-%m-%d')
        cr.execute(sql.format(self.now,self.current_year, first_day_of_year))
        emp_ids = [item[1] for item in cr.fetchall()]
        emp_ids = list(set(emp_ids))
        self.assertEqual(len(emp_ids), 0, "List official employee dont have enough annual leave balance at the moment: " + str(emp_ids))
        
    
    def test_annual_leave_balance_03(self):
        """
        @see: Search annual leave have wrong data 
        """
        cr, uid = self.cr, self.uid
        sql ="""
                select rr.code
                    FROM hr_holidays leave inner join hr_employee emp on leave.employee_id=emp.id
                                           inner join resource_resource rr on emp.resource_id=rr.id
                    WHERE 
                    
                    type='add' and year={0}
                    and 
                    (
                    (actual_days_of_pre_year <> days_taken_of_pre_year + remain_days_of_pre_year)
                    or (days_of_year <> days_taken_of_year + remain_days_of_year)
                    or (total_days <> actual_days_of_pre_year + days_of_year)
                    or (total_days <> total_taken_days + total_destroy_days + total_remain_days)
                    
                    )
             """
        
        cr.execute(sql.format(self.current_year))
        emp_ids = [item[0] for item in cr.fetchall()]
        emp_ids = list(set(emp_ids))
        self.assertEqual(len(emp_ids), 0, "Employees have wrong calculate data in annual leave balance: " + str(emp_ids))
        
    
    def test_annual_leave_balance_04(self):
        """
        @see: Search annual leave have wrong taken day 
        """
        cr, uid = self.cr, self.uid
        sql ="""
                -- Table save from date of employee in year for calculate annual leave
                
                CREATE TEMP TABLE tbl_temp_emp_test_date ON COMMIT DROP AS
                select emp.id, (case when min(instance.date_start) < '{0}-01-01' then '{0}-01-01' else min(instance.date_start) end) as "from_date"
                FROM hr_employee emp inner join vhr_employee_instance instance on instance.employee_id=emp.id
                                     inner join vhr_working_record start_wr on instance.start_wr_id = start_wr.id
                                     inner join working_record_change_form_rel start_form on start_wr.id=start_form.working_id
                                     
                                     left join vhr_working_record end_wr on instance.end_wr_id=end_wr.id
                                     left join working_record_change_form_rel end_form on end_wr.id=end_form.working_id
                where  start_form.change_form_id != 38 and (instance.date_end is null or end_form.change_form_id =50)
                group by emp.id
                ;
                
                select rr.code,leave.id,leave.total_taken_days,total_leave.sum
                    FROM hr_holidays leave inner join hr_employee emp on leave.employee_id=emp.id
                                           inner join resource_resource rr on emp.resource_id=rr.id
                                           inner join vhr_working_record wr on wr.employee_id=emp.id
                                           inner join hr_contract ct on wr.contract_id=ct.id
                                           inner join hr_contract_type ctype on ct.type_id=ctype.id
                                           inner join hr_contract_type_group type_group on ctype.contract_type_group_id=type_group.id
                                           inner join 
                                           
                                           (select 

                    cast( sum(number_of_days_temp) as decimal(16,2)) as "sum",leave.employee_id,leave.holiday_status_id 
                                           from hr_holidays leave inner join tbl_temp_emp_test_date temp_tbl on leave.employee_id=temp_tbl.id
                                           where 
                                              leave.type='remove' 
                                              and leave.state='validate'
                                              and leave.date_from>=temp_tbl.from_date
                                              and leave.date_to<='{0}-12-31'
                                            group by leave.employee_id,leave.holiday_status_id) as total_leave on total_leave.employee_id=leave.employee_id
                                           
                    WHERE 
                    total_leave.holiday_status_id = leave.holiday_status_id
                    and leave.type='add' and leave.year={0}
                    and (leave.total_taken_days - total_leave.sum) not in (0,0.1,-0.1)
                    and wr.active=True
                    and type_group.is_offical = True ;
             """
        
        cr.execute(sql.format(self.current_year))
        emp_ids = [item[0] for item in cr.fetchall()]
        emp_ids = list(set(emp_ids))
        self.assertEqual(len(emp_ids), 0, "Employees have wrong taken day in annual leave balance: " + str(emp_ids))
    
    def test_annual_leave_balance_05(self):
        """
        @see: Search annual leave have been duplicate in year
        """
        cr, uid = self.cr, self.uid
        sql ="""
                select rr.code
                    FROM hr_holidays leave inner join hr_employee emp on leave.employee_id=emp.id
                                           inner join resource_resource rr on emp.resource_id=rr.id
                    WHERE 
                    
                    type='add' and year={0}
                    group by leave.holiday_status_id, rr.code
                    having count(*) >1 order by rr.code
             """
        
        cr.execute(sql.format(self.current_year))
        emp_ids = [item[0] for item in cr.fetchall()]
        emp_ids = list(set(emp_ids))
        self.assertEqual(len(emp_ids), 0, "Employees have duplicate annual leave balance: " + str(emp_ids))
    
    #============================
    #Working Schedule Employee
    #
    #Search active employee have more than 1 effect working schedule employee
    #Search ative employee dont have any working schedule employee
    #============================
    def test_ws_employee_01(self):
        """
        @see: Search active employee have more than 1 effect working schedule employee
        """
        cr, uid = self.cr, self.uid
        
        sql ="""
                SELECT distinct ws.employee_id, resource.code
                FROM vhr_ts_ws_employee ws INNER JOIN hr_employee emp ON ws.employee_id = emp.id
                                           INNER JOIN resource_resource  resource ON emp.resource_id = resource.id
                where effect_from <= '{0}' and (effect_to is null or effect_to >= '{0}') and resource.active=True
                GROUP BY ws.employee_id, resource.code
                HAVING count(*) >1
             """
        
        cr.execute(sql.format(self.now))
        emp_ids = [item[1] for item in cr.fetchall()]
        emp_ids = list(set(emp_ids))
        self.assertEqual(len(emp_ids), 0, "Employees have more than 1 effect Working SChedule Employee at the moment: " + str(emp_ids))
    
    def test_ws_employee_02(self):
        """
        @see: Search active employee have official effective signed contract dont have any effect working schedule employee
        """
        cr, uid = self.cr, self.uid
        
        sql = """

                 SELECT  distinct ws.employee_id, resource.code
                FROM vhr_ts_ws_employee ws INNER JOIN hr_employee emp ON ws.employee_id = emp.id
                                           INNER JOIN resource_resource  resource ON emp.resource_id = resource.id
                                           INNER JOIN hr_contract contract ON emp.id = contract.employee_id
                                           INNER JOIN hr_contract_type c_type ON contract.type_id = c_type.id
                                           INNER JOIN hr_contract_type_group t_group ON c_type.contract_type_group_id = t_group.id
                WHERE resource.active=True and emp.join_date <= now()
                       and contract.date_start<= now()
                       and ( (contract.date_end is null and contract.liquidation_date is null) 
                              or (contract.date_end >= now() and liquidation_date is null)
                              or (liquidation_date > now()) )
                       and t_group.is_offical= True
                       and contract.state = 'signed'
                and emp.id not in
                
                ( SELECT ws.employee_id
                FROM vhr_ts_ws_employee ws INNER JOIN hr_employee emp ON ws.employee_id = emp.id
                                           INNER JOIN resource_resource  resource ON emp.resource_id = resource.id
                where effect_from <= now() and (effect_to is null or effect_to >= now()) and resource.active=True
                GROUP BY ws.employee_id, resource.code
                HAVING count(*) >0)
              """
        cr.execute(sql)
        emp_ids = [item[1] for item in cr.fetchall()]
        self.assertEqual(len(emp_ids), 0, "Employees dont have any effect Working SChedule Employee at the moment: " + str(emp_ids))
        
        
     #============================
    #Timesheet Employee
    #
    #Search active employee have more than 1 effect Timesheet Employee
    #Search ative employee dont have any Timesheet Employee
    #============================
    def test_ts_emp_timesheet_01(self):
        """
        @see: Search active employee have more than 1 effect Timesheet Employee
        """
        cr, uid = self.cr, self.uid
        
        sql ="""
                SELECT distinct ws.employee_id, resource.code
                FROM vhr_ts_emp_timesheet ws INNER JOIN hr_employee emp ON ws.employee_id = emp.id
                                           INNER JOIN resource_resource  resource ON emp.resource_id = resource.id
                where effect_from <= '{0}' and (effect_to is null or effect_to >= '{0}') and resource.active=True
                GROUP BY ws.employee_id, resource.code
                HAVING count(*) >1
             """
        
        cr.execute(sql.format(self.now))
        emp_ids = [item[1] for item in cr.fetchall()]
        emp_ids = list(set(emp_ids))
        self.assertEqual(len(emp_ids), 0, "Employees have more than 1 effect Timesheet Employee at the moment: " + str(emp_ids))
        
    def test_ts_emp_timesheet_02(self):
        """
        @see: Search active employee dont have any effect Timesheet Employee
        """
        cr, uid = self.cr, self.uid
        
        sql = """
                
                SELECT  distinct  resource.code
                FROM      hr_employee emp 
                                           INNER JOIN resource_resource  resource ON emp.resource_id = resource.id
                                           INNER JOIN hr_contract contract ON emp.id = contract.employee_id
                                           INNER JOIN hr_contract_type c_type ON contract.type_id = c_type.id
                                           INNER JOIN hr_contract_type_group t_group ON c_type.contract_type_group_id = t_group.id
                WHERE resource.active=True and emp.join_date <= '{0}' 
                       and contract.date_start<= '{0}'
                       and (     (contract.date_end is null and contract.liquidation_date is null) 
                              or (contract.date_end >= '{0}' and liquidation_date is null)
                              or (liquidation_date > '{0}') )
                       and t_group.is_offical= True 
                       
                       and contract.state = 'signed'
                and emp.id not in
                
                ( SELECT ws.employee_id
                FROM vhr_ts_emp_timesheet ws INNER JOIN hr_employee emp ON ws.employee_id = emp.id
                                           INNER JOIN resource_resource  resource ON emp.resource_id = resource.id
                where effect_from <= '{0}' and (effect_to is null or effect_to >= '{0}') and resource.active=True 
                GROUP BY ws.employee_id, resource.code
                HAVING count(*) >0)
              """
        cr.execute(sql.format(self.now))
        emp_ids = [item[0] for item in cr.fetchall()]
        self.assertEqual(len(emp_ids), 0, "Employees dont have any effect Timesheet Employee at the moment: " + str(emp_ids))
    
        


    
