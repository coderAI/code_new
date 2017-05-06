# -*- coding: utf-8 -*-

import logging

from openerp.osv import osv, fields


log = logging.getLogger(__name__)


class vhr_subgroup_jobtitle(osv.osv):
    _name = 'vhr.subgroup.jobtitle'
    _description = 'VHR SubGroup - JobTitle'

    _columns = {
        'name': fields.char('Name', size=128),
        'job_title_id': fields.many2one('vhr.job.title', 'Job Title', ondelete='restrict'),
        'sub_group_id': fields.many2one('vhr.sub.group', 'Sub Group', ondelete='restrict'),
        'description': fields.text('Description'),
        'active': fields.boolean('Active'),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'History',
                                      domain=[('object_id.model', '=', _name),
                                              ('field_id.name', 'not in', ['write_date', 'audit_log_ids'])]),

    }

    _defaults = {
        'active': True
    }

    _unique_insensitive_constraints = [{'job_title_id': "Job Title-Sub Group are already exist!",
                                        'sub_group_id': "Job Title-Sub Group are already exist!"
                                        }]

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        args_new = ['|', ('name', operator, name)] + args
        ids = self.search(cr, uid, args_new)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(vhr_subgroup_jobtitle, self).name_search(cr, uid, name, args, operator, context, limit)

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_subgroup_jobtitle, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res

vhr_subgroup_jobtitle()