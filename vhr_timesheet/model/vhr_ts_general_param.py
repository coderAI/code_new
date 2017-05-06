# -*- coding: utf-8 -*-

MULTIPLE = 0.5
import logging
from datetime import datetime
from dateutil.relativedelta import relativedelta

from openerp.osv import osv, fields
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.addons.vhr_common.model.vhr_common import vhr_common


log = logging.getLogger(__name__)


class vhr_ts_general_param(osv.osv, vhr_common):
    _name = 'vhr.ts.general.param'
    _description = 'VHR TS General Parameter'

    def _display_string(self, cr, uid, ids, field_name, arg, context=None):
        res = dict.fromkeys(ids, {'new_staff_param_display': '', 'compensation_off_display': '',
                                  'change_level_param_display': '', 'termination_param_display': ''})
        for record in self.browse(cr, uid, ids, context=context):
            if record.compensation_off_hour and record.compensation_off_day:
                res[record.id]['compensation_off_display'] = "%s hours = %s days" % (
                    record.compensation_off_hour, record.compensation_off_day)
            if record.new_staff_param_ids:
                display_string = []
                for i in record.new_staff_param_ids:
                    display_string.append('From %s to %s: Coef %s.' % (i.from_date, i.to_date, i.coef))
                res[record.id]['new_staff_param_display'] = '\n'.join(display_string)
            if record.termination_param_ids:
                display_string = []
                for i in record.termination_param_ids:
                    display_string.append('From %s to %s: Coef %s.' % (i.from_date, i.to_date, i.coef))
                res[record.id]['termination_param_display'] = '\n'.join(display_string)
            if record.change_level_params_ids:
                display_string = []
                for i in record.change_level_params_ids:
                    display_string.append('From %s to %s: Coef %s.' % (i.from_date, i.to_date, i.coef))
                res[record.id]['change_level_param_display'] = '\n'.join(display_string)
        return res

    def _get_is_latest(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if not ids:
            return True
        if not isinstance(ids, list):
            ids = [ids]

        # records = self.browse(cr, uid, ids, fields_process=['company_id', 'effect_from'])
        records = self.browse(cr, uid, ids, fields_process=['effect_from'])
        for record in records:
            # company_id = record.company_id and record.company_id.id or False
            effect_from = record.effect_from or False
            # larger_ids = self.search(cr, uid, [('company_id', '=', company_id),
            # ('effect_from', '>', effect_from),
            # '|', ('active', '=', True),
            #                                    ('active', '=', False)])
            larger_ids = self.search(cr, uid, [('effect_from', '>', effect_from),
                                               '|', ('active', '=', True),
                                               ('active', '=', False)])

            if larger_ids:
                res[record.id] = False
            else:
                res[record.id] = True

        return res

    _columns = {
        'name': fields.char('Name', size=128),
        'company_id': fields.many2one('res.company', 'Company'),
        'effect_from': fields.date('Effective From'),
        'effect_to': fields.date('Effective To'),
        'standard_workday': fields.float('Date permit the termination of employment standards (A)', digits=(16, 1), ),
        'compensation_off_hour': fields.float('Hour', digits=(16, 1), ),
        'compensation_off_day': fields.float('Day', digits=(16, 1), ),
        'active': fields.boolean('Active'),
        'new_staff_param_ids': fields.one2many('vhr.ts.new.staff.param', 'ts_gen_param_id',
                                               'Range of join date to calculate leave days'),
        'termination_param_ids': fields.one2many('vhr.ts.termination.param', 'ts_gen_param_id',
                                                 'Range of termination date to calculate leave days'),
        'change_level_params_ids': fields.one2many('vhr.ts.change.level.param', 'ts_gen_param_id',
                                                   'Range of change level date to calculate leave days'),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                         domain=[('object_id.model', '=', _name),
                                                 ('field_id.name', 'not in',
                                                  ['write_date', 'audit_log_ids'])], limit=5),
        'compensation_off_display': fields.function(_display_string, type='char',
                                                    string='Specified number of days off in compensation from the hours (B)',
                                                    multi='display'),
        'new_staff_param_display': fields.function(_display_string, type='char',
                                                   string='Milestone for leave of new staff in month', multi='display'),
        'termination_param_display': fields.function(_display_string, type='char',
                                                     string='Milestone for leave of termination in month',
                                                     multi='display'),
        'change_level_param_display': fields.function(_display_string, type='char',
                                                      string='Milestone for leave of change level in month',
                                                      multi='display'),
        # 'is_latest': fields.boolean('Is Latest'),
        'is_latest': fields.function(_get_is_latest, type='boolean', string='Is Latest'),
    }

    def _get_default_company_id(self, cr, uid, context=None):
        company_ids = self.pool.get('res.company').search(cr, uid, [('is_member', '=', False)], order="id asc")
        if company_ids:
            return company_ids[0]

    _defaults = {
        'active': True,
        'is_latest': True,
        # 'company_id': _get_default_company_id,
    }

    @staticmethod
    def _validation_multiple(vals, multiple, field_name):
        if vals < 0 or vals % multiple > 0:
            raise osv.except_osv(_('Warning!'),
                                 _(" %s must be greater than or equal to 0 and is multiple of 0.5 !" % field_name))

    @staticmethod
    def _validate_config_param(config_param, name):
        from_date = map(lambda a: a[2]['from_date'], config_param)
        to_date = map(lambda a: a[2]['to_date'], config_param)
        if len(config_param) != len(set(from_date)) or len(config_param) != len(set(to_date)):
            raise osv.except_osv(_('Warning!'),
                                 _("Duration of %s is overlapped!" % name))
        for i in config_param:
            for j in config_param:
                if i != j and i[2]['from_date'] in range(j[2]['from_date'], j[2]['to_date'] + 1):
                    raise osv.except_osv(_('Warning!'),
                                         _("Duration of %s is overlapped!" % name))

        sorted_config_param = sorted(config_param, key=lambda key: key[2]['from_date'])
        date_list = []
        for param in sorted_config_param:
            date_list.append(param[2]['from_date'])
            date_list.append(param[2]['to_date'])

        if date_list[0] != 1 or date_list[-1] != 31:
            raise osv.except_osv(_('Warning!'),
                                 _("Duration of %s must be continuous and in range [1, 31] !" % name))

        index_list = range(1, len(date_list), 2)
        for pos in index_list:
            if pos < len(date_list) - 1 and date_list[pos + 1] - date_list[pos] != 1:
                raise osv.except_osv(_('Warning!'),
                                     _("Duration of %s must be continuous and in range [1, 31] !" % name))

    def check_overlap_date(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        if ids:
            param_info = self.browse(cr, uid, ids[0], context)
            # company_id = param_info.company_id and param_info.company_id.id or False
            effect_from = param_info.effect_from
            effect_to = param_info.effect_to or effect_from

            # if company_id:
            # args = [('company_id', '=', company_id),
            # '|', ('active', '=', True),
            # ('active', '=', False)]
            args = ['|', ('active', '=', True),
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

    def update_param_state(self, cr, uid, param_ids, context=None):
        """
         Update state of all param link to company-working_record-param_type
         One employee at a company-working_record-param_type only have param record is active
         Return list param just active
        """
        today = datetime.today().date()
        active_record_ids = self.search(cr, uid, [('active', '=', False),
                                                  ('effect_from', '<=', today),
                                                  '|', ('effect_to', '=', False),
                                                  ('effect_to', '>=', today)])

        # Get WR have active=True need to update active=False
        inactive_record_ids = self.search(cr, uid, [('active', '=', True),
                                                    '|', ('effect_to', '<', today),
                                                    ('effect_from', '>', today)])

        param_ids = inactive_record_ids + active_record_ids
        if param_ids:
            self.update_active_of_record_cm(cr, uid, 'vhr.ts.general.param', param_ids)

        return True

    def update_parameter_info(self, cr, uid, ids, context={}):
        """
         Update  effect_to of nearest record if satisfy condition
        """
        if not context:
            context = {}
        if ids:
            for record_id in ids:
                record = self.browse(cr, uid, record_id, fields_process=['effect_from'], context=context)
                effect_from = datetime.strptime(record.effect_from, DEFAULT_SERVER_DATE_FORMAT).date()

                context['editing_record'] = record_id
                # Put editing_record into context to get nearest record of record have record_id
                # latest_param_id = self.get_latest_param(cr, uid, record.company_id.id, context=context)
                latest_param_id = self.get_latest_param(cr, uid, company_id=False, context=context)
                latest_vals = {}

                if latest_param_id:
                    # If have latest working record, update effect_to of latest working record
                    latest_param_id_effect_to = effect_from - relativedelta(days=1)
                    latest_vals['effect_to'] = latest_param_id_effect_to
                    # latest_vals['is_latest'] = False
                    self.write(cr, uid, [latest_param_id], latest_vals, context)

        return True

    def check_dates(self, cr, uid, ids, context=None):
        for record in self.read(cr, uid, ids, ['effect_from', 'effect_to'], context=context):
            if record.get('effect_from', False) and record.get('effect_to', False) \
                    and record['effect_from'] > record['effect_to']:
                raise osv.except_osv('Validation Error !',
                                     'Effect From must be greater than Effect From of Latest General Parameter Of Company!')

        return True

    # Get latest param by job level or nearest the latest record
    def get_latest_param(self, cr, uid, company_id=False, context=None):
        """
        Return record_id,

        *** record_id is last param job level in same company_id, working_schedule_id and same param_type_id
        """
        # if company_id:
            # args = [('company_id', '=', company_id), '|', ('active', '=', True), ('active', '=', False)]
        args = ['|', ('active', '=', True), ('active', '=', False)]

        # Get last_record in same contract
        latest_record_ids = self.search(cr, uid, args, 0, None, 'effect_from desc', context)

        if latest_record_ids and context.get('editing_record', False) \
                and context['editing_record'] in latest_record_ids:
            latest_record_ids.remove(context['editing_record'])

        return latest_record_ids and latest_record_ids[0] or False

    def cron_update_param_state(self, cr, uid, context=None):
        """
        Update state of record if satisfy condition of active
        """
        self.update_active_of_record_in_object_cm(cr, uid, 'vhr.ts.general.param')

        return True

    def create(self, cr, uid, vals, context=None):
        self._validation_multiple(vals.get('standard_workday'), MULTIPLE, '(A)')
        self._validation_multiple(vals.get('compensation_off_hour'), MULTIPLE, '(B)')
        self._validation_multiple(vals.get('compensation_off_day'), MULTIPLE, '(B)')
        if vals.get('new_staff_param_ids'):
            self._validate_config_param(vals.get('new_staff_param_ids'), '(C)')
        if vals.get('termination_param_ids'):
            self._validate_config_param(vals.get('termination_param_ids'), '(D)')
        if vals.get('change_level_params_ids'):
            self._validate_config_param(vals.get('change_level_params_ids'), '(E)')
        res = super(vhr_ts_general_param, self).create(cr, uid, vals, context=context)
        if res and vals.get('effect_from', False):
            self.check_dates(cr, uid, [res], context=context)
            self.update_parameter_info(cr, uid, [res], context=context)
            self.check_overlap_date(cr, uid, [res], context)
            self.update_param_state(cr, uid, [res], context)
        return res

    def write(self, cr, uid, ids, vals, context=None):
        if not isinstance(ids, list):
            ids = [ids]
        if 'standard_workday' in vals:
            self._validation_multiple(vals.get('standard_workday'), MULTIPLE, '(A)')
        if 'compensation_off_hour' in vals:
            self._validation_multiple(vals.get('compensation_off_hour'), MULTIPLE, '(B)')
        if 'compensation_off_day' in vals:
            self._validation_multiple(vals.get('compensation_off_day'), MULTIPLE, '(B)')
        res = super(vhr_ts_general_param, self).write(cr, uid, ids, vals, context=context)
        # validate
        for i in self.browse(cr, uid, ids, context=context):
            param_vals = []
            for j in i.new_staff_param_ids:
                param_vals.append((0, 0, {'from_date': j.from_date, 'to_date': j.to_date}))
            if param_vals:
                self._validate_config_param(param_vals, '(C)')
            param_vals = []
            for j in i.termination_param_ids:
                param_vals.append((0, 0, {'from_date': j.from_date, 'to_date': j.to_date}))
            if param_vals:
                self._validate_config_param(param_vals, '(D)')
            param_vals = []
            for j in i.change_level_params_ids:
                param_vals.append((0, 0, {'from_date': j.from_date, 'to_date': j.to_date}))
            if param_vals:
                self._validate_config_param(param_vals, '(E)')

        if res and vals.get('effect_to', False):
            self.check_dates(cr, uid, ids, context)

        # if res and (vals.get('effect_from', False) or vals.get('company_id', False)):
        if res and (vals.get('effect_from', False)):
            self.update_parameter_info(cr, uid, ids, context=context)
            self.check_overlap_date(cr, uid, ids, context)
            self.update_param_state(cr, uid, ids, context)
        return res

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        res = False
        if ids:
            records = self.browse(cr, uid, ids)
            for record in records:
                # if not record.company_id:
                # res = self.unlink_record(cr, uid, [record.id], context)
                # Only allow delete latest record
                # Update nearest record to active and effect_to =False
                if record.is_latest:
                    context['editing_record'] = record.id
                    # latest_param_id = self.get_latest_param(cr, uid, record.company_id.id, context=context)
                    latest_param_id = self.get_latest_param(cr, uid, company_id=False, context=context)
                    # If only have one record have company_id
                    # working_record_id and param_type_id, don't allow to delete it
                    if latest_param_id:
                        res = self.unlink_record(cr, uid, [record.id], context)

                        self.write(cr, uid, [latest_param_id], {'effect_to': None}, context=context)
                        self.update_param_state(cr, uid, [latest_param_id], context=context)
                    else:
                        raise osv.except_osv('Validation Error !',
                                             'You cannot delete records which are first Parameter '
                                             'By General Parameter of Company!')

                else:
                    raise osv.except_osv('Validation Error !',
                                         'You cannot delete records which are first Parameter '
                                         'By General Parameter of Company!')

        return res

    def unlink_record(self, cr, uid, ids, context=None):
        try:
            res = super(vhr_ts_general_param, self).unlink(cr, uid, ids, context)
            return res
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')

    def copy_data(self, cr, uid, id, default, context=None):
        data = super(vhr_ts_general_param, self).copy_data(cr, uid, id, default, context=context)
        # just for sure company_id was removed
        if 'company_id' in data:
            del data['company_id']
        if 'effect_from' in data:
            del data['effect_from']
        if 'effect_to' in data:
            del data['effect_to']
        return data


vhr_ts_general_param()