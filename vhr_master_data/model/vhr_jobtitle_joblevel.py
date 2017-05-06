# -*- coding: utf-8 -*-

import logging

from openerp.osv import osv, fields

log = logging.getLogger(__name__)


class vhr_jobtitle_joblevel(osv.osv):
    _name = 'vhr.jobtitle.joblevel'
    _description = 'VHR JobTitle - JobLevel'

    _columns = {
        'name': fields.char('Name', size=128),
        'job_title_id': fields.many2one('vhr.job.title', 'Job Title', ondelete='restrict'),
        'job_level_id': fields.many2one('vhr.job.level', 'Job Level', ondelete='restrict'),
        'description': fields.text('Description'),
        'active': fields.boolean('Active'),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'History',
                                      domain=[('object_id.model', '=', _name),
                                              ('field_id.name', 'not in', ['write_date', 'audit_log_ids'])]),

    }

    _defaults = {
        'active': True
    }

    _unique_insensitive_constraints = [{'job_title_id': "Job Title-Job Level are already exist!",
                                        'job_level_id': "Job Title-Job Level are already exist!"
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
        return super(vhr_jobtitle_joblevel, self).name_search(cr, uid, name, args, operator, context, limit)

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_jobtitle_joblevel, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res

vhr_jobtitle_joblevel()