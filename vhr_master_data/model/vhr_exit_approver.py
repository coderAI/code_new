# -*- coding: utf-8 -*-

import logging

from openerp.osv import osv, fields


log = logging.getLogger(__name__)


class vhr_exit_approver(osv.osv):
    _name = 'vhr.exit.approver'
    _description = 'VHR Exit Approver'
    
    _columns = {
        'name': fields.char('Name', size=128),
#         'office_id': fields.many2one('vhr.office', 'Office', ondelete='restrict'),
        'exit_type_id': fields.many2one('vhr.exit.type', 'Exit Type', ondelete='restrict'),
        'city_id': fields.many2one('res.city', 'City', ondelete='restrict'),
        'approver_id': fields.many2one('hr.employee', 'Approver', ondelete='restrict'),  
        'is_fix_asset': fields.boolean('Is Fix Asset'),
        'is_default': fields.boolean('Is Default'),
        'description': fields.text('Description'),
        'active': fields.boolean('Active'),
        
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                          domain=[('object_id.model', '=', _name),
                                                  ('field_id.name', 'not in',
                                                   ['write_date', 'audit_log_ids'])]),

    }

    _defaults = {
        'is_fix_asset': True,
        'is_default': True,
        'active': True,
    }
    _unique_insensitive_constraints = [{'exit_type_id': "Exit Type, City and Approver are already exist!",
                                        'city_id': "Exit Type, City and Approver are already exist!",
                                        'approver_id': "Exit Type, City and Approver are already exist!",
                                        }]

    def name_get(self, cr, uid, ids, context=None):
        if not ids or False in ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        reads = self.read(cr, uid, ids, ['exit_type_id'], context=context)
        res = []
        for record in reads:
                name = record.get('exit_type_id',False) and record['exit_type_id'][1]
                res.append((record['id'], name))
        return res

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_exit_approver, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res


vhr_exit_approver()