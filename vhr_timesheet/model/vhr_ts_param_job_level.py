# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
import thread
import logging
import sys

from openerp.osv import osv, fields
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.addons.vhr_common.model.vhr_common import vhr_common
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.osv import osv, fields
from openerp.osv import osv, fields
from openerp.sql_db import Cursor
from openerp.sql_db import ConnectionPool
from openerp import tools


log = logging.getLogger(__name__)


class vhr_ts_param_job_level(osv.osv, vhr_common):
    _name = 'vhr.ts.param.job.level'
    _description = 'VHR TS Parameter By Job Level'

    def _get_is_latest(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if not ids:
            return True
        if not isinstance(ids, list):
            ids = [ids]

        records = self.read(cr, uid, ids, ['effect_from', 'job_level_id', 'param_type_id','job_level_new_id'])
        for record in records:
#             company_id = record.company_id and record.company_id.id or False
            effect_from = record.get('effect_from',False)
            job_level_id = record.get('job_level_id',False) and record['job_level_id'][0] or False
            job_level_new_id = record.get('job_level_new_id',False) and record['job_level_new_id'][0] or False
            param_type_id = record.get('param_type_id',False) and record['param_type_id'][0] or False
            domain = [('param_type_id', '=', param_type_id),
                       ('effect_from', '>', effect_from),
                       '|', ('active', '=', True),
                       ('active', '=', False)]
            
            if job_level_id:
                domain.insert(0,('job_level_id', '=', job_level_id))
            elif job_level_new_id:
                 domain.insert(0,('job_level_new_id', '=', job_level_new_id))
            
            larger_ids = self.search(cr, uid, domain)

            if larger_ids:
                res[record['id']] = False
            else:
                res[record['id']] = True

        return res

    _columns = {
        'name': fields.char('Name', size=128),
        'company_id': fields.many2one('res.company', 'Company', ondelete='restrict'),
        'job_level_type_id': fields.many2one('vhr.job.level.type', 'Job Level Type', ondelete='restrict'),
        'job_level_id': fields.many2one('vhr.job.level', 'Job Level', ondelete='restrict'),
        'job_level_new_id': fields.many2one('vhr.job.level.new', 'Job Level New', ondelete='restrict'),
        'param_type_id': fields.many2one('vhr.ts.param.type', 'Parameter', ondelete='restrict'),
        'effect_from': fields.date('Effective From'),
        'effect_to': fields.date('Effective To'),
        'value': fields.char('Value', size=32),
        'note': fields.text('Note'),
        'active': fields.boolean('Active'),
        # 'is_latest': fields.boolean('Is Latest'),
        'is_latest': fields.function(_get_is_latest, type='boolean', string='Is Latest'),

        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                         domain=[('object_id.model', '=', _name), \
                                                 ('field_id.name', 'not in', ['write_date', 'audit_log_ids'])]),

    }

#     def _get_default_company_id(self, cr, uid, context=None):
#         company_ids = self.pool.get('res.company').search(cr, uid, [('is_member', '=', False)], order="id asc")
#         if company_ids:
#             return company_ids[0]
# 
#         return False

    _defaults = {
        'active': False,
        'is_latest': True,
#         'company_id': _get_default_company_id
    }

    _order = "id desc"


    def name_get(self, cr, uid, ids, context=None):
        if not ids or False in ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        reads = self.read(cr, uid, ids, ['job_level_id', 'param_type_id','job_level_new_id'], context=context)
        res = []
        for record in reads:
            job_level_new = record.get('job_level_new_id', False) and record['job_level_new_id'][1] or ''
            job_level = record.get('job_level_id', False) and record['job_level_id'][1] or ''
            param_type = record.get('param_type_id', False) and record['param_type_id'][1] or ''
            name = job_level + ' - ' + param_type
            
            if record.get('job_level_new_id', False):
                name = job_level_new + ' - ' + param_type
                
            res.append((record['id'], name))
        return res

    def onchange_job_level_id(self, cr, uid, ids, job_level_id, context=None):
        res = {'job_level_type_id': False}
        if job_level_id:
            job_level = self.pool.get('vhr.job.level').browse(cr, uid, job_level_id, context)
            job_level_type_id = job_level.job_level_type_id and job_level.job_level_type_id.id or False
            res['job_level_type_id'] = job_level_type_id

        return {'value': res}


    def check_dates(self, cr, uid, ids, context=None):
        for record in self.read(cr, uid, ids, ['effect_from', 'effect_to'], context=context):
            if record.get('effect_from', False) and record.get('effect_to', False) and record['effect_from'] > record[
                'effect_to']:
                # return False
                raise osv.except_osv('Validation Error !',
                                     'Effect From must be greater Effect From of Latest Parameter By Job Level !')

        return True

    def check_overlap_date(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        if ids:
            param_info = self.browse(cr, uid, ids[0], context)
#             company_id = param_info.company_id and param_info.company_id.id or False
            job_level_id = param_info.job_level_id and param_info.job_level_id.id or False
            job_level_new_id = param_info.job_level_new_id and param_info.job_level_new_id.id or False
            param_type_id = param_info.param_type_id and param_info.param_type_id.id or False
            effect_from = param_info.effect_from
            effect_to = param_info.effect_to or effect_from

#             if job_level_id and param_type_id:
#                 args = [#('company_id', '=', company_id),
#                         ('job_level_id', '=', job_level_id),
#                         ('param_type_id', '=', param_type_id),
#                         '|', ('active', '=', True),
#                         ('active', '=', False)]
# 
#                 param_ids = self.search(cr, uid, args)
# 
#                 if not param_ids:
#                     return True
#                 not_overlap_args = ['|', ('effect_from', '>', effect_to), ('effect_to', '<', effect_from)] + args
#                 not_overlap_param_ids = self.search(cr, uid, not_overlap_args)
#                 # Record not overlap is the record link to employee
#                 if len(param_ids) == len(not_overlap_param_ids):
#                     return True
#                 else:
#                     # Get records from working_ids not in not_overlap_working_ids
#                     overlap_ids = [x for x in param_ids if x not in not_overlap_param_ids]
#                     # Get records from working_ids are not working_id
#                     overlap_ids = [x for x in overlap_ids if x not in ids]
#                     if overlap_ids:
#                         raise osv.except_osv('Validation Error !',
#                                              'The effective duration is overlapped. Please check again !')
            
            if job_level_new_id and param_type_id:
                args = [#('company_id', '=', company_id),
                        ('job_level_new_id', '=', job_level_new_id),
                        ('param_type_id', '=', param_type_id),
                        '|', ('active', '=', True),
                        ('active', '=', False)]

                param_ids = self.search(cr, uid, args)

                if not param_ids:
                    return True
                not_overlap_args = ['|', ('effect_from', '>', effect_to), ('effect_to', '<', effect_from)] + args
                not_overlap_param_ids = self.search(cr, uid, not_overlap_args)
                # Record not overlap is the record link to employee
                if len(param_ids) == len(not_overlap_param_ids):
                    return True
                else:
                    # Get records from working_ids not in not_overlap_working_ids
                    overlap_ids = [x for x in param_ids if x not in not_overlap_param_ids]
                    # Get records from working_ids are not working_id
                    overlap_ids = [x for x in overlap_ids if x not in ids]
                    if overlap_ids:
                        raise osv.except_osv('Validation Error !',
                                             'The effective duration is overlapped. Please check again !')

        return True

    def update_parameter_info(self, cr, uid, ids, context={}):
        """
         Update  effect_to of nearest record if satisfy condition
        """
        if not context:
            context = {}
        if ids:
            for record_id in ids:
                record = self.browse(cr, uid, record_id, context)
                effect_from = datetime.strptime(record.effect_from, DEFAULT_SERVER_DATE_FORMAT).date()

                context['editing_record'] = record_id
                # Put editing_record into context to get nearest record of record have record_id
                latest_param_id = self.get_latest_param(cr, uid, record.job_level_new_id.id,
                                                        record.param_type_id.id, context)
                latest_vals = {}

                if latest_param_id:
                    # If have latest working record, update effect_to of latest working record
                    latest_param_id_effect_to = effect_from - relativedelta(days=1)
                    latest_vals['effect_to'] = latest_param_id_effect_to
                    # latest_vals['is_latest'] = False
                    self.write(cr, uid, latest_param_id, latest_vals, context)

        return True

    # Get latest param by job level new or nearest the latest record
    def get_latest_param(self, cr, uid, job_level_new_id, param_type_id, context=None):
        """
        Return record_id,
        
        *** record_id is last param job level new in same job_level_id and same param_type_id
        """
        if job_level_new_id and param_type_id:
            args = [#('company_id', '=', company_id),
                    ('job_level_new_id', '=', job_level_new_id),
                    ('param_type_id', '=', param_type_id),
                    '|', ('active', '=', True),
                    ('active', '=', False)]

            # Get last_record in same contract
            latest_record_ids = self.search(cr, uid, args, 0, None, 'effect_from desc', context)

            if latest_record_ids and context.get('editing_record', False) and context[
                'editing_record'] in latest_record_ids:
                latest_record_ids.remove(context['editing_record'])

            return latest_record_ids and latest_record_ids[0] or False

        return False

    def update_param_job_level_state(self, cr, uid, param_ids, context=None):
        """
         Update state of all param link to company-job_level-param_type
         One employee at a company-job_level-param_type only have param record is active
         Return list param just active
        """
        dict_result = []
        unique_list = []
        if param_ids:
            param_records = self.read(cr, uid, param_ids, ['job_level_new_id', 'param_type_id'])
            for param_record in param_records:
#                 company_id = param_record.get('company_id', False) and param_record['company_id'][0] or False
                job_level_new_id = param_record.get('job_level_new_id', False) and param_record['job_level_new_id'][0] or False
                param_type_id = param_record.get('param_type_id', False) and param_record['param_type_id'][0] or False
                if job_level_new_id and param_type_id \
                        and [job_level_new_id, param_type_id] not in unique_list:
                    unique_list.append([job_level_new_id, param_type_id])

        if unique_list:
            today = datetime.today().date()
            for unique_item in unique_list:
                # param_ids = self.search(cr, uid, [('company_id', '=', unique_item[0]),
                # ('job_level_id', '=', unique_item[1]),
                # ('param_type_id', '=', unique_item[2]),
                # '|', ('active', '=', True),
                # ('active', '=', False)], 0, None, None, context)

                active_record_ids = self.search(cr, uid, [#('company_id', '=', unique_item[0]),
                                                          ('job_level_new_id', '=', unique_item[0]),
                                                          ('param_type_id', '=', unique_item[1]),
                                                          ('active', '=', False),
                                                          ('effect_from', '<=', today),
                                                          '|', ('effect_to', '=', False),
                                                          ('effect_to', '>=', today)])

                # Get WR have active=True need to update active=False
                inactive_record_ids = self.search(cr, uid, [#('company_id', '=', unique_item[0]),
                                                            ('job_level_new_id', '=', unique_item[0]),
                                                            ('param_type_id', '=', unique_item[1]),
                                                            ('active', '=', True),
                                                            '|', ('effect_to', '<', today),
                                                            ('effect_from', '>', today)])

                param_ids = inactive_record_ids + active_record_ids
                if param_ids:
                    self.update_active_of_record_cm(cr, uid, 'vhr.ts.param.job.level', param_ids)

        return True

    def cron_update_param_by_job_level_state(self, cr, uid, context=None):
        """
        Update state of record if satisfy condition of active
        """
        self.update_active_of_record_in_object_cm(cr, uid, 'vhr.ts.param.job.level')

        return True

    def create(self, cr, uid, vals, context=None):
        if not context:
            context = {}

        res = super(vhr_ts_param_job_level, self).create(cr, uid, vals, context)

        if res and vals.get('effect_from', False):
            self.update_parameter_info(cr, uid, [res], context)
            self.check_overlap_date(cr, uid, [res], context)

            self.update_param_job_level_state(cr, uid, [res], context)

        return res

    def write(self, cr, uid, ids, vals, context=None):
        if not context:
            context = {}

        res = super(vhr_ts_param_job_level, self).write(cr, uid, ids, vals, context)
        if not isinstance(ids, list):
            ids = [ids]
        if res and (vals.get('effect_from', False) #or vals.get('company_id', False)
                    or vals.get('job_level_new_id', False) or vals.get('param_type_id', False)):
            self.update_parameter_info(cr, uid, ids, context)
            self.check_overlap_date(cr, uid, ids, context)

            self.update_param_job_level_state(cr, uid, ids, context)

        if res and vals.get('effect_to', False):
            self.check_dates(cr, uid, ids, context)
        for param in self.browse(cr, uid, ids):
            if not param.active or param.effect_to and param.effect_to < fields.date.today():
                continue
            # search previous value
            parameter_obj = self.pool.get('ir.config_parameter')
            plus_one_code = parameter_obj.get_param(cr, uid, 'ts.param.type.seniority.plus.one.day.be.allowed.code').split(',')
            # stipulated_code = parameter_obj.get_param(cr, uid,
            # 'ts.param.type.stipulated.permit').split(',')
            if param.param_type_id and param.param_type_id.code in plus_one_code:
                try:
                    value = int(param.value)
                    if value < 0:
                        raise osv.except_osv('Validation Error !',
                                             'Value must be >= 0 !')
                    thread.start_new_thread(vhr_ts_param_job_level.update_seniority_days, ( self, cr, uid, param))
                except Exception as e:
                    log.exception(e)
                    log.info('Error: Unable to start thread execute update_seniority_days')
                    # elif param.param_type_id and param.param_type_id.code in stipulated_code:
                    # try:
                    # thread.start_new_thread(vhr_ts_param_job_level.update_annual_days, (self, cr, uid, param))
                    # except Exception as e:
                    # log.exception(e)
                    # log.info('Error: Unable to start thread execute update_seniority_days')
        return res

    def update_seniority_days(self, cr, uid, param):
        log.info('start thread execute update_seniority_days')
        try:
            value = int(param.value)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Value of Parameter By Job Level with id %s must be integer' % param.id)
        
        if value <= 0:
            log.info('update_seniority_days end()')
            return True
        _pool = ConnectionPool(int(tools.config['db_maxconn']))
        cr = Cursor(_pool, cr.dbname, True)
        reload(sys)

        job_level_new_id = param.job_level_new_id and param.job_level_new_id.id or False
        if not job_level_new_id:
            return True
        
        employee_obj = self.pool.get('hr.employee')
        valid_date = (datetime.now() - relativedelta( years=value)).strftime(DEFAULT_SERVER_DATE_FORMAT)
        employee_ids = employee_obj.search(cr, uid, [('job_level_person_id', '=', job_level_new_id),
                                                     ('join_date', '<=', valid_date)])
        for employee in employee_obj.browse(cr, uid, employee_ids, fields_process=['join_date', 'login']):
            join_date = employee.join_date
            sql = """
                    SELECT
                      coalesce(sum(number_of_days_temp), 0)
                    FROM hr_holidays
                    WHERE type = 'remove'
                          AND employee_id = %s
                          AND state = 'validate'
                          AND holiday_status_id IN (SELECT
                                                      id
                                                FROM hr_holidays_status
                                                WHERE is_seniority IS TRUE)

                    """ % employee.id
            cr.execute(sql)
            seniority_days = cr.fetchone() or 0
            if seniority_days:
                seniority_days = seniority_days[0]
            join_date = datetime.strptime(join_date, DEFAULT_SERVER_DATE_FORMAT) - timedelta(
                days=seniority_days)
            log.info('update_seniority_days detail %s - %s - %s ' % (
                employee.login, join_date.strftime(DEFAULT_SERVER_DATE_FORMAT), seniority_days))
            delta = relativedelta(datetime.now(), join_date)
            if delta.years and delta.years / value >= 1:
                holidays_obj = self.pool.get('hr.holidays')
                context = {'get_all': 1}
                res_ids = holidays_obj.search(cr, uid, [('type', '=', 'add'),
                                                        ('employee_id', '=', employee.id),
                                                        ('year', '=', datetime.now().year),
                                                        ('state', '=', 'validate')],context=context)
                log.info('update_seniority_days update employee_id %s - %s days' % (
                    employee.id, delta.years / value))
                holidays_obj.write(cr, uid, res_ids, {'seniority_leave': delta.years / value})
                log.info('update_seniority_days number_days: %s' % (delta.years / value))
        cr.autocommit(True)
        cr.close()
        log.info('update_seniority_days end()')
        return True

    # def update_annual_days(self, cr, uid, param):
    # _pool = ConnectionPool(int(tools.config['db_maxconn']))
    # cr = Cursor(_pool, cr.dbname, True)
    # reload(sys)
    # effect_from = param.effect_from
    # effect_to = param.effect_to
    # holidays_obj = self.pool.get('hr.holidays')
    # job_level_id = param.job_level_id and param.job_level_id.id or False
    # employee_obj = self.pool.get('hr.employee')
    # employee_ids = employee_obj.search(cr, uid,
    #                                        [('job_level_id', '=', job_level_id)])
    #     for employee_id in employee_ids:
    #         try:
    #             holidays_obj.create_allocation_for_employee_change_level(cr, uid, employee_id, company_id=False,
    #                                                                      effect_from=effect_from, effect_to=effect_to,
    #                                                                      context={})
    #         except Exception, e:
    #             log.exception(e)
    #     cr.commit()
    #     cr.close()

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        res = False
        if ids:
            records = self.browse(cr, uid, ids)
            for record in records:
                if not record.job_level_new_id or not record.param_type_id: #not record.company_id or 
                    res = self.unlink_record(cr, uid, [record.id], context)

                # Only allow delete latest record
                # Update nearest record to active and effect_to =False
                if record.is_latest:
                    context['editing_record'] = record.id
                    job_level_new_id = record.job_level_new_id and record.job_level_new_id.id or False
                    latest_param_id = self.get_latest_param(cr, uid, job_level_new_id,
                                                            record.param_type_id.id, context)

                    # If only have one record have job_level_id and param_type_id, don't allow to delete it
                    if latest_param_id:
                        res = self.unlink_record(cr, uid, [record.id], context)

                        self.write(cr, uid, latest_param_id, {'effect_to': None}, context)
                        self.update_param_job_level_state(cr, uid, [latest_param_id], context)
                    else:
                        raise osv.except_osv('Validation Error !',
                                             'You cannot delete records which are first Parameter Type by Job Level of Company - Job Level - Parameter !')

                else:
                    raise osv.except_osv('Validation Error !',
                                         'You cannot delete records which are not last Parameter Type by Job Level of Company - Job Level - Parameter !')

        return res

    def unlink_record(self, cr, uid, ids, context=None):
        res = False
        try:
            res = super(vhr_ts_param_job_level, self).unlink(cr, uid, ids, context)
            return res
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')

        return res


vhr_ts_param_job_level()