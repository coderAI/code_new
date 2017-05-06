# -*- coding: utf-8 -*-

import logging

from openerp.osv import osv, fields

log = logging.getLogger(__name__)


class vhr_ts_working_group(osv.osv):
    _name = 'vhr.ts.working.group'
    _description = 'VHR TS Working Group'
    _columns = {
        'code': fields.char('Code', size=64),
        'name': fields.char('Vietnamese Name', size=128),
        'name_en': fields.char('English Name', size=128),
        'description': fields.text('Description'),
        'active': fields.boolean('Active'),

        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                         domain=[('object_id.model', '=', _name), \
                                                 ('field_id.name', 'not in', ['write_date', 'audit_log_ids'])]),

    }

    _defaults = {
        'active': True,
    }

    _unique_insensitive_constraints = [{'code': "Working Group's Code is already exist!"},
                                       {'name': "Working Group's Vietnamese Name is already exist!"}]

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        
            
        args_new = ['|', '|', ('name', operator, name), ('code', operator, name), ('name_en', operator, name)] + args
        ids = self.search(cr, uid, args_new)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(vhr_ts_working_group, self).name_search(cr, uid, name, args, operator, context, limit)

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_ts_working_group, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res
    
    def write(self, cr, uid, ids, vals, context=None):
        if not isinstance(ids, list):
            ids = [ids]
        res = super(vhr_ts_working_group, self).write(cr, uid, ids, vals, context)
        
#         if res and 'active' in vals:
#             working_schedule_group_obj = self.pool.get('vhr.ts.working.schedule.working.group')
#             wsg_ids = working_schedule_group_obj.search(cr, uid, [('ts_working_group_id','in',ids),('active','!=',vals['active'])])
#             if wsg_ids:
#                 wsgs = working_schedule_group_obj.browse(cr, uid, wsg_ids)
#                 inactive_wsg = []
#                 active_wsg = []
#                 for wsg in wsgs:
#                     active_ws = wsg.ts_working_schedule_id and wsg.ts_working_schedule_id.active or False
#                     active_wg = wsg.ts_working_group_id and wsg.ts_working_group_id.active or False
#                     active = wsg.active
#                     
#                     if active_ws and active_wg and not active:
#                         active_wsg.append(wsg.id)
#                     elif not (active_ws and active_wg) and active:
#                         inactive_wsg.append(wsg.id)
#                         
#                 if inactive_wsg:
#                     working_schedule_group_obj.write(cr, uid, inactive_wsg, {'active': False})
#                 if active_wsg:
#                     working_schedule_group_obj.write(cr, uid, active_wsg, {'active': True})
                
        return res


vhr_ts_working_group()