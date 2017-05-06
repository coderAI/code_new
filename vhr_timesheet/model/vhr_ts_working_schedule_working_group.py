# -*- coding: utf-8 -*-

import logging

from openerp.osv import osv, fields

log = logging.getLogger(__name__)

#This object is not use anymore, due to break mapping between working schedule - working group

class vhr_ts_working_schedule_working_group(osv.osv):
    _name = 'vhr.ts.working.schedule.working.group'
    _description = 'VHR TS Working Schedule - Working Group'

    _columns = {
        'name': fields.char('Name', size=128),
        'ts_working_schedule_id': fields.many2one('vhr.ts.working.schedule', 'Working Schedule', ondelete='restrict'),
        'ts_working_group_id': fields.many2one('vhr.ts.working.group', 'Working Group', ondelete='restrict'),
        'description': fields.text('Description'),
        'active': fields.boolean('Active'),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'History',
                                      domain=[('object_id.model', '=', _name),
                                              ('field_id.name', 'not in', ['write_date', 'audit_log_ids'])]),

    }

    _defaults = {
        'active': True
    }

    _unique_insensitive_constraints = [{'ts_working_schedule_id': "Working Schedule - Working Group are already exist!",
                                        'ts_working_group_id'   : "Working Schedule - Working Group are already exist!"
                                        }]
    
    def name_get(self, cr, uid, ids, context=None):
        if not ids or False in ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        reads = self.read(cr, uid, ids, ['ts_working_schedule_id','ts_working_group_id'], context=context)
        res = []
        for record in reads:
            name = ''
            ws_name = record.get('ts_working_schedule_id', False) and record['ts_working_schedule_id'][1] or ''
            wg_name = record.get('ts_working_group_id', False) and record['ts_working_group_id'][1] or ''
            if ws_name:
                name += ws_name
            if wg_name:
                if name:
                    name += " : "
                name += wg_name
                
            res.append((record['id'], name))
        return res
    
    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        args_new = ['|', ('name', operator, name)] + args
        ids = self.search(cr, uid, args_new)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(vhr_ts_working_schedule_working_group, self).name_search(cr, uid, name, args, operator, context, limit)

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_ts_working_schedule_working_group, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res

vhr_ts_working_schedule_working_group()