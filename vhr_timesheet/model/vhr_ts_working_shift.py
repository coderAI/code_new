# -*- coding: utf-8 -*-

import logging

from openerp.osv import osv, fields
from openerp.addons.vhr_common.model.vhr_common import vhr_common


log = logging.getLogger(__name__)


class vhr_ts_working_shift(osv.osv, vhr_common):
    _name = 'vhr.ts.working.shift'
    _description = 'VHR TS Working Shift'

    def _get_value(self, cr, uid, ids, field_names, arg, context=None):
        res = {}
        shifts = self.browse(cr, uid, ids, context=context)
        for shift in shifts:
            value_work_time = str(self.convert_from_float_to_float_time(shift.begin_work_time)) + " - " + str(
                self.convert_from_float_to_float_time(shift.end_work_time))
            value_break_time = str(self.convert_from_float_to_float_time(shift.begin_break_time)) + " - " + str(
                self.convert_from_float_to_float_time(shift.end_break_time))

            res[shift.id] = {
                'value_work_time': value_work_time,
                'value_break_time': value_break_time
            }
        return res

    _columns = {
        'code': fields.char('Code', size=64),
        'name': fields.char('Vietnamse Name', size=128),
        'name_en': fields.char('English Name', size=128),
        'company_id': fields.many2one('res.company', 'Company', ondelete='restrict'),
        'type_workday_id': fields.many2one('vhr.ts.type.workday', 'Type of workday', ondelete='restrict'),
        'type_cs_shift': fields.many2one('vhr.ts.type.cs.shift', 'Type of cs shift', ondelete='restrict'),
        'is_night_shift': fields.boolean('Night Shift ?'),
        'begin_work_time': fields.float('Working Time(hh:mm)'),
        'end_work_time': fields.float('Working Time(hh:mm)'),
        'value_work_time': fields.function(_get_value, type='char', string='Working Time(hh:mm)', multi='time'),

        'begin_break_time': fields.float('Break Time(hh:mm)'),
        'end_break_time': fields.float('Break Time(hh:mm)'),
        'value_break_time': fields.function(_get_value, type='char', string='Break Time(hh:mm)', multi='time'),
        'work_hour': fields.float('Working Hours'),
        'first_shift_hours': fields.float('First Shift Hours'),
        'last_shift_hours': fields.float('Last Shift Hours'),
        'description': fields.text('Description'),
        'active': fields.boolean('Active'),
        'color_name': fields.selection(
            [('red', 'Red'), ('blue', 'Blue'), ('lightgreen', 'Light Green'), ('lightblue', 'Light Blue'),
             ('lightyellow', 'Light Yellow'), ('magenta', 'Magenta'), ('lightcyan', 'Light Cyan'), ('black', 'Black'),
             ('lightpink', 'Light Pink'), ('brown', 'Brown'), ('violet', 'Violet'), ('lightcoral', 'Light Coral'),
             ('lightsalmon', 'Light Salmon'), ('lavender', 'Lavender'), ('wheat', 'Wheat'), ('ivory', 'Ivory')],
            'Color in Report', required=True, ),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                         domain=[('object_id.model', '=', _name), \
                                                 ('field_id.name', 'not in', ['write_date', 'audit_log_ids'])]),

    }

    def _get_default_company_id(self, cr, uid, context=None):
        company_ids = self.pool.get('res.company').search(cr, uid, [('is_member', '=', False)], order="id asc")
        if company_ids:
            return company_ids[0]

        return False

    #
    _defaults = {
        'active': True,
        'is_night_shift': False,
        'company_id': _get_default_company_id
    }
    _order = "id desc"

    _unique_insensitive_constraints = [{'code': "Working Shift's Code is already exist!"},
                                       {'name': "Working Shift's Vietnamese Name is already exist!"}]

    def onchange_work_time(self, cr, uid, ids, time_from, time_to, context=None):
        data = [['begin_work_time', 'Begin Working Time'], ['end_work_time', 'End Working Time']]
        res = self.onchange_time(cr, uid, ids, time_from, time_to, data, context)

        return res

    def onchange_break_time(self, cr, uid, ids, time_from, time_to, context=None):
        data = [['begin_break_time', 'Begin Break Time'], ['end_break_time', 'End Break Time']]
        res = self.onchange_time(cr, uid, ids, time_from, time_to, data, context)

        return res


    def onchange_time(self, cr, uid, ids, time_from, time_to, data, context={}):
        res = {}
        warning = {}
        if time_from and time_to and data:
            try:
                time_from = float(time_from)
            except:
                res[data[0][0]] = False

            try:
                time_to = float(time_to)
            except:
                res[data[1][0]] = False

            try:
                if time_from < 0 or time_from > 24:
                    warning = {
                        'title': 'Validation Error!',
                        'message': "Incorrect Format %s !" % data[0][1]
                    }
                    res[data[0][0]] = False

                elif time_to < 0 or time_to > 24:
                    warning = {
                        'title': 'Validation Error!',
                        'message': "Incorrect Format %s !" % data[1][1]
                    }
                    res[data[1][0]] = False

                    # elif time_from > time_to:
                    # warning = {
                    #         'title': 'Validation Error!',
                    #         'message': "%s have to greater %s !" % (data[1][1], data[0][1])
                    #     }
                    #     res[data[1][0]] = False
            except:
                return {'value': res}

        return {'value': res, 'warning': warning}

    def onchange_workhour(self, cr, uid, ids, hour, context=None):
        res = {'value': {'work_hour': False},
               'warning': {
                   'title': 'Validation Error!',
                   'message': "Work Hour must be greater than or equal to 0 and is mutiple of 0.5 !"
               }}

        if hour < 0 or hour % 0.5 != 0:
            return res

        return {'value': {}}

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        args_new = ['|', '|', ('name', operator, name), ('code', operator, name), ('name_en', operator, name)] + args
        ids = self.search(cr, uid, args_new)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(vhr_ts_working_shift, self).name_search(cr, uid, name, args, operator, context, limit)


    def unlink_record(self, cr, uid, ids, context=None):
        res = False
        try:
            res = super(vhr_ts_working_shift, self).unlink(cr, uid, ids, context)
            return res
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')

        return res


vhr_ts_working_shift()