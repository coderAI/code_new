# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields
from openerp import tools
from datetime import datetime, timedelta
from openerp import SUPERUSER_ID

import sys  

reload(sys)  
sys.setdefaultencoding('utf8')

_logger = logging.getLogger(__name__)

CLICKER     = 1
HRBP        = 2
DEPTHEAD    = 3
RECRUITER   = 4
MANAGER     = 5
ADMIN       = 6
REPORTER    = 7
COLLABORATER = 8
CANDB_ROLE = 9
COLLABORATER2 = 10
RRHRBP = 11

EMP_XML = 'base.group_user'
COLLABORATOR_XML = 'vhr_recruitment.vhr_collaborator'
RECRUITER_XML = 'vhr_recruitment.vhr_recruiter'
ADMIN_XML = 'vhr_recruitment.vhr_recruitment_admin'
MANAGER_XML = 'vhr_recruitment.vhr_recruitment_manager'
ERP_XML = 'vhr_recruitment.vhr_rr_erp'
HRBP_XML = 'vhr_master_data.vhr_hrbp'
ASST_HRBP_XML = 'vhr_master_data.vhr_assistant_to_hrbp'
REPORT_XML = 'vhr_recruitment.vhr_rr_report'
CB_XML = 'vhr_human_resource.vhr_cb'
COLLABORATOR2_XML = 'vhr_recruitment.vhr_collaborator2'
RRHRBP_XML = 'vhr_recruitment.vhr_rr_hrbp'



class vhr_recruitment_abstract(osv.AbstractModel):
    _name = 'vhr.recruitment.abstract'
    _description = 'VHR Recruitment Abstract'
    
    def recruitment_send_email(self, cr, uid, template, model_name, res_id, attachment_ids=None, context=None):
        if context is None:
            context = {} 
        _logger.info('vhr_recruitment : begin recruitment_send_email()')
        try:
            email_template = self.pool.get('email.template')
            email_ids = email_template.search(cr, uid, [
                            ('model', '=', model_name),
                            ('name', '=', template),
                        ], context=context)
            if email_ids:
                email_template.vhr_send_mail(cr, uid, email_ids[0], res_id, attach_ids=attachment_ids, context=context)
            else:
                _logger.error('vhr_recruitment : can\'t search email template')
            _logger.info('vhr_recruitment : end recruitment_send_email()')
        except Exception as e:
            _logger.exception(e)
        return True
    
    def recruitment_get_server_email(self, cr, uid, ids, context=None):
        if context is None:
            context = {} 
        _logger.info('vhr_recruitment : begin recruitment_get_server_email()')
        email_from = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr.rr.email.system.config')
        email_from = email_from if email_from else 'service@hrs'
        _logger.info('vhr_recruitment : end recruitment_get_server_email()')
        return email_from
    
    def hrs_get_server_email(self, cr, uid, context=None):
        _logger.info('vhr_recruitment : begin hrs_get_server_email()')
        email_from = self.pool.get('ir.config_parameter').get_param(cr, uid, 'hrs.recruitment.hrs.site.email')
        email_from = email_from if email_from else 'recruitment@hrs'
        _logger.info('vhr_recruitment : end hrs_get_server_email()')
        return email_from
    
    def recruitment_get_group_array(self, cr, uid, res_user_id , context = None):
        groups = []
        try:
            model_data = self.pool.get('ir.model.data')
            employee_id = model_data.xmlid_lookup(cr, uid, 'base.group_user')[2]
            vhr_hrbp = model_data.xmlid_lookup(cr, uid, 'vhr_master_data.vhr_hrbp')[2]
            vhr_hrbp_assis = model_data.xmlid_lookup(cr, uid, 'vhr_master_data.vhr_assistant_to_hrbp')[2]
            vhr_recruiter = model_data.xmlid_lookup(cr, uid, 'vhr_recruitment.vhr_recruiter')[2]
            vhr_recruitment_manager = model_data.xmlid_lookup(cr, uid, 'vhr_recruitment.vhr_recruitment_manager')[2]
            vhr_recruitment_admin = model_data.xmlid_lookup(cr, uid, 'vhr_recruitment.vhr_recruitment_admin')[2]
            vhr_recruitment_reporter = model_data.xmlid_lookup(cr, uid, 'vhr_recruitment.vhr_rr_report')[2]
            vhr_recruitment_collab = model_data.xmlid_lookup(cr, uid, 'vhr_recruitment.vhr_collaborator')[2]
            vhr_recruitment_collab2 = model_data.xmlid_lookup(cr, uid, 'vhr_recruitment.vhr_collaborator2')[2]
            vhr_recruitment_rrhrbp = model_data.xmlid_lookup(cr, uid, 'vhr_recruitment.vhr_rr_hrbp')[2]
            vhr_cb = model_data.xmlid_lookup(cr, uid, "vhr_human_resource.vhr_cb")[2]
            user_obj = self.pool.get('res.users').browse(cr, uid, res_user_id, context=context)
            
            for user_group in user_obj.groups_id:
                if user_group.id == employee_id:
                    groups.append(CLICKER)
                # RR coi hrbp và hrbp assis là 1
                elif user_group.id == vhr_hrbp or user_group.id == vhr_hrbp_assis:
                    groups.append(HRBP)
                elif user_group.id == vhr_recruiter:
                    groups.append(RECRUITER)
                elif user_group.id == vhr_recruitment_manager:
                    groups.append(MANAGER)
                elif user_group.id == vhr_recruitment_reporter:
                    groups.append(REPORTER)
                elif user_group.id == vhr_recruitment_collab:
                    groups.append(COLLABORATER)
                elif user_group.id == vhr_recruitment_admin:
                    groups.append(ADMIN)
                elif user_group.id == vhr_cb:
                    groups.append(CANDB_ROLE)
                elif user_group.id == vhr_recruitment_collab2:
                    groups.append(COLLABORATER2)
                elif user_group.id == vhr_recruitment_rrhrbp:
                    groups.append(RRHRBP)
        except Exception as e:
            _logger.info(e)
        _logger.debug('vhr_rr : roles of user : %s login %s'%(uid, " ".join(str(x) for x in groups)))
        return groups
    
    def validate_read(self, cr, uid, ids, context=None):
        raise NotImplementedError( "Should have implemented this" )
    
    def check_read_access(self, cr, uid, ids, context=None):
        # config đảm bảo các bản lên build tiếp theo chạy ổn định trong quá trình validate data
        # Nếu validate lỗi thì tắt validate đảm bảo bussiness ko bị gián đoạn
        run_validate_read = self.pool.get('ir.config_parameter').get_param(cr, SUPERUSER_ID, 'vhr.rr.run.validate.read')
        if run_validate_read and int(run_validate_read):
            return self.validate_read(cr, uid, ids, context)
        return True    
    
    def get_last_message(self, cr, uid, res_id, context=None):
        result = self.pool.get('vhr.state.change').get_last_message(cr, uid, res_id, self._name)
        result = result if result else ''
        return result
    
    def get_last_user(self, cr, uid, res_id, context=None):
        result = self.pool.get('vhr.state.change').get_last_user(cr, uid, res_id, self._name)
        result = result if result else ''
        return result 
    
    def get_list_recruiter(self, cr, uid, context=None):
        ''' Lấy danh sách employee có quyền là recruiter
        '''
        # change 25/12/2014 get employee has role recruiter load in handle_by and share handle_by
        model_data = self.pool.get('ir.model.data')
        hr_emp_obj = self.pool.get('hr.employee')
        vhr_recruiter = model_data.xmlid_lookup(cr, uid, 'vhr_recruitment.vhr_recruiter')[2]
        if not vhr_recruiter:
            raise osv.except_osv('Validation Error !', 'Please contact admin tool')
        group_lst = self.pool.get('res.groups').browse(cr, uid, vhr_recruiter, context=context)
        users = [x.id for x in group_lst.users]
        lst_emp = hr_emp_obj.search(cr, uid, [('user_id', 'in', users)], context=context)
        return lst_emp
    
    def get_department_rams(self, cr, uid, employee_id, context=None):
        department_ids = []
        if employee_id:
            sql = "SELECT b.id from ram_department_rel a \
                    INNER JOIN hr_department b ON a.department_id = b.id\
                    INNER JOIN vhr_organization_class c on b.organization_class_id = c.id\
                    WHERE c.level = 3 and a.employee_id =%s\
                    UNION\
                    SELECT d.id from ram_department_rel a \
                    INNER JOIN hr_department b ON a.department_id = b.id\
                    INNER JOIN hr_department d on d.parent_id = b.id\
                    INNER JOIN vhr_organization_class c on d.organization_class_id = c.id\
                    WHERE c.level = 3 and a.employee_id =%s\
                    UNION\
                    SELECT d.id from ram_department_rel a \
                    INNER JOIN hr_department b ON a.department_id = b.id\
                    INNER JOIN hr_department c on c.parent_id = b.id\
                    INNER JOIN hr_department d on d.parent_id = c.id\
                    INNER JOIN vhr_organization_class  e on d.organization_class_id = e.id\
                    WHERE e.level = 3 and a.employee_id = %s" % (employee_id, employee_id, employee_id)
            cr.execute(sql)
            department_ids = map(lambda x: x[0], cr.fetchall())
        return department_ids
    
    def get_department_hrbps(self, cr, uid, employee_id, context=None):
        '''
            - SELECT 1 : Lay danh sach department tai phong ban duoc add
            - SELECT 2 : Lay danh sach department tai devision parent phong ban
            - SELECT 3 : Lay danh sach department tai devision parent cua devision (GE)
        '''
        department_ids = []
        if employee_id:
            sql = "SELECT b.id  from hrbp_department_rel a \
                INNER JOIN hr_department b ON a.department_id = b.id\
                INNER JOIN vhr_organization_class c on b.organization_class_id = c.id\
                WHERE c.level = 3 and a.employee_id = %s\
                UNION\
                SELECT  d.id from hrbp_department_rel a \
                INNER JOIN hr_department b ON a.department_id = b.id\
                INNER JOIN hr_department d on d.parent_id = b.id\
                INNER JOIN vhr_organization_class c on d.organization_class_id = c.id\
                WHERE c.level = 3 and a.employee_id = %s \
                UNION\
                SELECT d.id from hrbp_department_rel a \
                INNER JOIN hr_department b ON a.department_id = b.id\
                INNER JOIN hr_department c on c.parent_id = b.id\
                INNER JOIN hr_department d on d.parent_id = c.id\
                INNER JOIN vhr_organization_class  e on d.organization_class_id = e.id\
                WHERE e.level = 3 and a.employee_id = %s " % (employee_id, employee_id, employee_id)
            cr.execute(sql)
            department_ids = map(lambda x: x[0], cr.fetchall())
        return department_ids
    
    def get_department_ass_hrbps(self, cr, uid, employee_id, context=None):
        """ Lấy danh sách department mà employee_id ( assitant hrbp) được add vào
            không lấy theo cha con
        """
        department_ids = []
        if employee_id:
            sql = "SELECT department_id from ass_hrbp_department_rel where employee_id = %s" % employee_id
            cr.execute(sql)
            department_ids = map(lambda x: x[0], cr.fetchall())
        return department_ids
    
    def get_department_rr_hrbps(self, cr, uid, employee_id, context=None):
        """ Lấy danh sách department mà employee_id ( RR hrbp) được add vào
            không lấy theo cha con
        """
        department_ids = []
        if employee_id:
            sql = "SELECT department_id from rr_hrbp_department_rel where employee_id = %s" % employee_id
            cr.execute(sql)
            department_ids = map(lambda x: x[0], cr.fetchall())
        return department_ids
    
    def get_delegate_department(self, cr, uid, employee_id, context=None):
        """Lấy danh sách Job delegate cho employee_id
        """
        job_ids = []
        if employee_id:
            sql = """select distinct job.id, job.department_id \
                    from hr_job job \
                    inner join delegate_rr_department dlg_dept on dlg_dept.department_id = job.department_id \
                    inner join vhr_delegate_by_depart dlg on dlg.id = dlg_dept.delegate_id \
                    where job.state !='draft' and dlg.emp_del_to_id =  %s""" % (employee_id)
            cr.execute(sql)
            job_ids = map(lambda x: x[0], cr.fetchall())
        return job_ids
    
    def format_date(self, cr, uid, res_id, str_date='', type='US', context=None):
        if str_date:
            res_date = datetime.strptime(str_date[:10], '%Y-%m-%d')
            if type == 'VN':
                result = res_date.strftime('%d-%m-%Y')
            else:
                result = res_date.strftime('%b-%d-%Y')
            return result

        return ''

    def format_datetime(self, cr, uid, res_id, str_date='', format='US', context=None):
        if str_date:
            timezone = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr.default.timezone.config')
            timezone = int(timezone) if timezone else 0
            res_date = datetime.strptime(str_date, '%Y-%m-%d %H:%M:%S') + timedelta(hours=timezone)
            if format == 'VN':
                result = res_date.strftime('%d-%m-%Y %H:%M:%S')
            else:
                result = res_date.strftime('%b-%d-%Y %H:%M:%S')
            return result

        return ''
    
    def format_datetime_full_data(self, cr, uid, res_id, str_date='', context=None):
        # binhnx: More details about locale and datetime format, find at: http://apidock.com/ruby/Time/strftime
        if str_date:
            timezone = self.pool.get('ir.config_parameter').get_param(cr, uid, 'vhr.default.timezone.config')
            timezone = int(timezone) if timezone else 0
            res_date = datetime.strptime(str_date, '%Y-%m-%d %H:%M:%S') + timedelta(hours=timezone)
            import locale
            locale.setlocale(locale.LC_TIME, "en_US.UTF-8")
            return res_date.strftime('%H:%M, %A, %B %d, %Y').encode('utf-8').strip()

        return ''
    
    def get_email_group(self, cr, uid, res_id, group_name, context=None):
        result = ''
        if group_name:
            mail_group = self.pool.get('vhr.email.group')
            lst_id = mail_group.search(cr, uid, [('code','=', group_name)], context=context)
            if lst_id:
                result = mail_group.browse(cr, uid, lst_id[0], context=context).to_email
        return result
    
    def get_email_group_erp(self, cr, uid, res_id, group_name, context=None):
        list_cc_mail = []
        if group_name:
            group_obj = self.pool.get('res.groups')
            employee_obj = self.pool.get('hr.employee')
            lst_ids = group_obj.search(cr, uid, [('name','=', group_name)], context=context)
            if lst_ids:
                group = group_obj.browse(cr, uid, lst_ids[0], context=context)
                if group:
                    for user in group.users:
                        user_id = user.id
                        lst_employee_ids = employee_obj.search(cr, uid, [('user_id','=', user_id),('user_id','!=',1)], context=context)
                        for employee in employee_obj.browse(cr, uid, lst_employee_ids, context=context):
                            if employee.work_email:
                                list_cc_mail.append(employee.work_email)
        return ";".join(list_cc_mail)

    def get_first_name(self, cr, uid, ids, full_name='',context=None):
        if full_name == '' or not isinstance(full_name, basestring):
            return ''
        else:
            return full_name.split(' ')[-1]

vhr_recruitment_abstract()
