# -*- coding: utf-8 -*-

import logging
import math
from datetime import datetime
from dateutil.relativedelta import relativedelta

from openerp.osv import osv, fields
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.addons.vhr_common.model.vhr_common import vhr_common


log = logging.getLogger(__name__)


class vhr_ts_param_working_schedule(osv.osv, vhr_common):
    _name = 'vhr.ts.param.working.schedule'
    _description = 'VHR TS Parameter By Working Schedule'

    def _get_value(self, cr, uid, ids, field_name, arg, context=None):
        """Returns value base on coef or time_from-time_to."""
        res = {}
        params = self.browse(cr, uid, ids, context=context)
        for param in params:
            if param.value_type == 'coef':
                res[param.id] = str(param.coef)
            else:
                res[param.id] = str(self.convert_from_float_to_float_time(param.time_from)) + " - " + str(
                    self.convert_from_float_to_float_time(param.time_to))
        return res

    def convert_from_float_to_float_time(self, number, context=None):
        result = ''
        if number:
            floor_number = int(math.floor(number))
            result += str(floor_number)
            gap = number - floor_number
            if gap > 0:
                minute = int(round(gap * 60))
                if minute < 10:
                    minute = '0' + str(minute)
                else:
                    minute = str(minute)
                result += ':' + minute
            else:
                result += ':00'

        return result
    
    def _get_is_latest(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if not ids:
            return True
        if not isinstance(ids, list):
            ids = [ids]
        
        records = self.browse(cr, uid, ids, fields_process=['company_id','effect_from','working_schedule_id','param_type_id'])
        for record in records:
            company_id = record.company_id and record.company_id.id or False
            effect_from = record.effect_from
            working_schedule_id = record.working_schedule_id and record.working_schedule_id.id or False
            param_type_id = record.param_type_id and record.param_type_id.id or False
            
            larger_ids = self.search(cr, uid, [('company_id','=',company_id),
                                               ('working_schedule_id','=',working_schedule_id),
                                               ('param_type_id','=',param_type_id),
                                                ('effect_from','>',effect_from),
                                                '|',('active','=',True),
                                                    ('active','=',False)])
            
            if larger_ids:
                res[record.id] = False
            else:
                res[record.id] = True
            
        return res

    _columns = {
        'name': fields.char('Name', size=128),
        'company_id': fields.many2one('res.company', 'Company', ondelete='restrict'),
        'working_schedule_group_id': fields.many2one('vhr.ts.working.schedule.group', 'Working Schedule Group', ondelete='restrict'),
        'working_schedule_id': fields.many2one('vhr.ts.working.schedule', 'Working Schedule', ondelete='restrict'),
        'param_type_id': fields.many2one('vhr.ts.param.type', 'Parameter', ondelete='restrict',
                                         domain=[('group_id.code', '=', 'TS_SCHEDULE'), ('active', '=', True)]),
        'effect_from': fields.date('Effective From'),
        'effect_to': fields.date('Effective To'),
        'value_type': fields.selection([('coef', 'Coef'),
                                        ('time', 'Time')], 'Type of Value'),
        'coef': fields.float('Coef', size=3),
        'coef_compensation_leave': fields.float('Coef Of Compensation leave', digits=(4, 2)),
        'time_from': fields.float('Time'),
        'time_to': fields.float('Time'),
        'value': fields.function(_get_value, type='char', string='Value'),

        'note': fields.text('Note'),
        'active': fields.boolean('Active'),
#         'is_latest': fields.boolean('Is Latest'),
        'is_latest': fields.function(_get_is_latest, type='boolean', string='Is Latest'),

        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                         domain=[('object_id.model', '=', _name), \
                                                 ('field_id.name', 'not in', ['write_date', 'audit_log_ids'])]),

    }

    def _get_default_company_id(self, cr, uid, context=None):
        company_ids = self.pool.get('res.company').search(cr, uid, [('is_member', '=', False)], order="id asc")
        if company_ids:
            return company_ids[0]

        return False
    
    def _get_default_working_schedule_id(self, cr, uid, context=None):
        general_ws_code = self.pool.get('ir.config_parameter').get_param(cr, uid, 'general_working_schedule_code')
        if general_ws_code:
            general_ws_code_list = general_ws_code.split(',')
            if general_ws_code_list:
                main_working_schedule_ids = self.pool.get('vhr.ts.working.schedule').search(cr, uid, [('code','in',general_ws_code_list)])
                if main_working_schedule_ids:
                    return main_working_schedule_ids[0]
        
        return False

    _defaults = {
        'active': False,
        'value_type': 'coef',
        'is_latest': True,
        'company_id': _get_default_company_id,
        'working_schedule_id': _get_default_working_schedule_id
        
    }

    _order = "id desc"

    def name_get(self, cr, uid, ids, context=None):
        if not ids or False in ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        reads = self.read(cr, uid, ids, ['working_schedule_id', 'param_type_id'], context=context)
        res = []
        for record in reads:
            working_schedule = record.get('working_schedule_id', False) and record['working_schedule_id'][1]
            param_type = record.get('param_type_id', False) and record['param_type_id'][1]
            name = ''
            if working_schedule:
                name = working_schedule 
            if param_type:
                name += ' - ' + param_type
            res.append((record['id'], name))
        return res

    def onchange_coef(self, cr, uid, ids, coef, context=None):
        res = {}
        warning = {}
        if coef and coef < 0:
            res['coef'] = False
            warning = {
                'title': 'Validation Error!',
                'message': "Coef have to greater than or equal to 0 !"
            }

        return {'value': res, 'warning': warning}
    
    def onchange_working_schedule_group_id(self, cr, uid, ids, working_schedule_group_id, context=None):
        res = {'working_schedule_id': False}
        
        return {'value': res}
    
    def onchange_working_schedule_id(self, cr, uid, ids, working_schedule_id, context=None):
        res = {}
        if working_schedule_id:
            res = {'working_schedule_group_id': False}
        
        return {'value': res}
    
    def onchange_coef_compensation_leave(self, cr, uid, ids, coef, context=None):
        res = {}
        warning = {}
        if coef and coef < 0:
            res['coef_compensation_leave'] = False
            warning = {
                'title': 'Validation Error!',
                'message': "Coef Of Compensation leave have to greater than or equal to 0 !"
            }

        return {'value': res, 'warning': warning}

    def onchange_time_from_to(self, cr, uid, ids, time_from, time_to, context=None):
        res = {}
        warning = {}
        if time_from and time_to:
            try:
                time_from = float(time_from)
            except:
                res['time_from'] = False

            try:
                time_to = float(time_to)
            except:
                res['time_to'] = False

            try:
                if time_from < 0 or time_from > 24:
                    warning = {
                        'title': 'Validation Error!',
                        'message': "Incorrect Format Time From !"
                    }
                    res['time_from'] = False

                elif time_to < 0 or time_to > 24:
                    warning = {
                        'title': 'Validation Error!',
                        'message': "Incorrect Format Time To !"
                    }
                    res['time_to'] = False

#                 elif time_from > time_to:
#                     warning = {
#                         'title': 'Validation Error!',
#                         'message': "Time To have to greater Time From !"
#                     }
#                     res['time_to'] = False
            except:
                return {'value': res}

        return {'value': res, 'warning': warning}

    def onchange_value_type(self, cr, uid, ids, context=None):
        return {'value': {'time_from': False, 'time_to': False, 'coef': False}}

    def check_dates(self, cr, uid, ids, context=None):
        for record in self.read(cr, uid, ids, ['effect_from', 'effect_to'], context=context):
            if record.get('effect_from', False) and record.get('effect_to', False) and record['effect_from'] > record[
                'effect_to']:
                # return False
                raise osv.except_osv('Validation Error !',
                                     'Effect From must be greater Effect From of Latest Parameter By Working Schedule !')

        return True

    def check_overlap_date(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        if ids:
            param_info = self.browse(cr, uid, ids[0], context)
            company_id = param_info.company_id and param_info.company_id.id or False
            working_schedule_id = param_info.working_schedule_id and param_info.working_schedule_id.id or False
            working_schedule_group_id = param_info.working_schedule_group_id and param_info.working_schedule_group_id.id or False
            param_type_id = param_info.param_type_id and param_info.param_type_id.id or False
            effect_from = param_info.effect_from
            effect_to = param_info.effect_to or effect_from

            if company_id and working_schedule_id and param_type_id:
                args = [('company_id', '=', company_id),
                        ('working_schedule_id', '=', working_schedule_id),
                        ('working_schedule_group_id','=',working_schedule_group_id),
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
                    #Get records from working_ids not in not_overlap_working_ids
                    overlap_ids = [x for x in param_ids if x not in not_overlap_param_ids]
                    #Get records from working_ids are not working_id
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
                latest_param_id = self.get_latest_param(cr, uid, record.company_id.id, 
                                                        record.working_schedule_id and record.working_schedule_id.id or False,
                                                        record.working_schedule_group_id and record.working_schedule_group_id.id or False,
                                                        record.param_type_id.id, context)
                latest_vals = {}

                if latest_param_id:
                    #If have latest working record, update effect_to of latest working record
                    latest_param_id_effect_to = effect_from - relativedelta(days=1)
                    latest_vals['effect_to'] = latest_param_id_effect_to
#                     latest_vals['is_latest'] = False
                    self.write(cr, uid, latest_param_id, latest_vals, context)

        return True

    # Get latest param by job level or nearest the latest record
    def get_latest_param(self, cr, uid, company_id, working_schedule_id, working_schedule_group_id, param_type_id, context=None):
        """
        Return record_id,
        
        *** record_id is last param job level in same company_id, working_schedule_id and same param_type_id
        """
        if company_id and (working_schedule_id or working_schedule_group_id) and param_type_id:
            args = [('company_id', '=', company_id),
                    ('working_schedule_id', '=', working_schedule_id),
                    ('working_schedule_group_id', '=', working_schedule_group_id),
                    ('param_type_id', '=', param_type_id),
                    '|', ('active', '=', True),
                    ('active', '=', False)]

            #Get last_record in same contract
            latest_record_ids = self.search(cr, uid, args, 0, None, 'effect_from desc', context)

            if latest_record_ids and context.get('editing_record', False) and context[
                'editing_record'] in latest_record_ids:
                latest_record_ids.remove(context['editing_record'])

            return latest_record_ids and latest_record_ids[0] or False

        return False

    def update_param_working_schedule_state(self, cr, uid, param_ids, context=None):
        """
         Update state of all param link to company-working_record-param_type
         One employee at a company-working_record-param_type only have param record is active
         Return list param just active
        """
        dict_result = []
        unique_list = []
        if param_ids:
            param_records = self.read(cr, uid, param_ids, ['company_id', 'working_schedule_id', 'working_schedule_group_id','param_type_id'])
            for param_record in param_records:
                company_id = param_record.get('company_id', False) and param_record['company_id'][0] or False
                working_schedule_id = param_record.get('working_schedule_id', False) and \
                                      param_record['working_schedule_id'][0] or False
                working_schedule_group_id = param_record.get('working_schedule_group_id', False) and \
                                      param_record['working_schedule_group_id'][0] or False
                param_type_id = param_record.get('param_type_id', False) and param_record['param_type_id'][0] or False
                if company_id and (working_schedule_id or working_schedule_group_id) and param_type_id \
                        and [company_id, working_schedule_id, working_schedule_group_id, param_type_id] not in unique_list:
                    unique_list.append([company_id, working_schedule_id, working_schedule_group_id, param_type_id])

        if unique_list:
            today = datetime.today().date()
            for unique_item in unique_list:
#                 param_ids = self.search(cr, uid, [('company_id', '=', unique_item[0]),
#                                                   ('working_schedule_id', '=', unique_item[1]),
#                                                   ('param_type_id', '=', unique_item[2]),
#                                                   '|', ('active', '=', True),
#                                                   ('active', '=', False)], 0, None, None, context)
#                 
                active_record_ids = self.search(cr, uid, [('company_id',          '=', unique_item[0]),
                                                          ('working_schedule_id', '=', unique_item[1]),
                                                          ('working_schedule_group_id', '=', unique_item[2]),
                                                          ('param_type_id',       '=', unique_item[3]),
                                                          ('active','=',False),
                                                          ('effect_from','<=',today),
                                                          '|',('effect_to','=',False),
                                                              ('effect_to','>=',today)])
                
                 #Get WR have active=True need to update active=False
                inactive_record_ids = self.search(cr, uid, [('company_id',          '=', unique_item[0]),
                                                            ('working_schedule_id', '=', unique_item[1]),
                                                            ('working_schedule_group_id', '=', unique_item[2]),
                                                            ('param_type_id',       '=', unique_item[3]),
                                                            ('active','=',True),
                                                              '|',('effect_to','<',today),
                                                                  ('effect_from','>',today)])
        
                update_param_ids = inactive_record_ids + active_record_ids
                
                if update_param_ids:
                    self.update_active_of_record_cm(cr, uid, 'vhr.ts.param.working.schedule', update_param_ids)

        return True

    def cron_update_param_working_schedule_state(self, cr, uid, context=None):
        """
        Update state of record if satisfy condition of active
        """
        self.update_active_of_record_in_object_cm(cr, uid, 'vhr.ts.param.working.schedule')

        return True

    def create(self, cr, uid, vals, context=None):
        if not context:
            context = {}

        res = super(vhr_ts_param_working_schedule, self).create(cr, uid, vals, context)

        if res and vals.get('effect_from', False):
            self.update_parameter_info(cr, uid, [res], context)
            self.check_overlap_date(cr, uid, [res], context)

            self.update_param_working_schedule_state(cr, uid, [res], context)

        return res

    def write(self, cr, uid, ids, vals, context=None):
        if not context:
            context = {}

        res = super(vhr_ts_param_working_schedule, self).write(cr, uid, ids, vals, context)
        if not isinstance(ids, list):
            ids = [ids]

        if res and (vals.get('effect_from', False) or vals.get('company_id', False) \
                            or vals.get('working_schedule_id', False) \
                            or vals.get('working_schedule_group_id', False) \
                            or vals.get('param_type_id', False)):
            self.update_parameter_info(cr, uid, ids, context)
            self.check_overlap_date(cr, uid, ids, context)

            self.update_param_working_schedule_state(cr, uid, ids, context)

        if res and vals.get('effect_to', False):
            self.check_dates(cr, uid, ids, context)

        return res


    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        res = False
        if ids:
            records = self.browse(cr, uid, ids)
            for record in records:
                
                if not record.company_id or (not record.working_schedule_id and not record.working_schedule_group_id)or not record.param_type_id:
                    res = self.unlink_record(cr, uid, [record.id], context)

                #Only allow delete latest record
                #Update nearest record to active and effect_to =False
                if record.is_latest:
                    context['editing_record'] = record.id
                    latest_param_id = self.get_latest_param(cr, uid, record.company_id.id,
                                                            record.working_schedule_id and record.working_schedule_id.id or False, 
                                                            record.working_schedule_group_id and record.working_schedule_group_id.id or False,
                                                            record.param_type_id.id,
                                                             context)

                    #If only have one record have company_id  - working_record_id and param_type_id, don't allow to delete it
                    if latest_param_id:
                        res = self.unlink_record(cr, uid, [record.id], context)

                        self.write(cr, uid, latest_param_id, {'effect_to': None}, context)
                        self.update_param_working_schedule_state(cr, uid, [latest_param_id], context)
                    else:
                        raise osv.except_osv('Validation Error !',
                                             'You cannot delete records which are first Parameter By Working Schedule of Company - Working Schedule - Parameter !')

                else:
                    raise osv.except_osv('Validation Error !',
                                         'You cannot delete records which are not last Parameter By Working Schedule of Company - Working Schedule - Parameter !')

        return res

    def unlink_record(self, cr, uid, ids, context=None):
        res = False
        try:
            res = super(vhr_ts_param_working_schedule, self).unlink(cr, uid, ids, context)
            return res
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')

        return res

    def get_all_param_working_schedule(self, cr, uid, context=None):
        res = {}
        if context is None:
            context = {}

        param_ids = self.search(cr, uid, [], context=context)
        for param in self.browse(cr, uid, param_ids, context=context):
            key = param.param_type_id.code
            if key and key not in res and param.value_type == 'coef':
                res[key] = param.coef
        return res


vhr_ts_param_working_schedule()