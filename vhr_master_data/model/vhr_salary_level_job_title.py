# -*- coding: utf-8 -*-

import logging

from openerp.osv import osv, fields


log = logging.getLogger(__name__)


class vhr_salary_level_job_title(osv.osv):
    _name = 'vhr.salary.level.job.title'
    _description = 'VHR Salary Level Job Title'
    
    _columns = {
        'name': fields.char('Name', size=128),
        'salary_level_id': fields.many2one('vhr.salary.level', 'Salary Level', ondelete='restrict'),
        'job_title_id': fields.many2one('vhr.job.title', 'Job Title', ondelete='restrict'),
        'active': fields.boolean('Active'),
        'description': fields.text('Description'),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                          domain=[('object_id.model', '=', _name),
                                                  ('field_id.name', 'not in',
                                                   ['write_date', 'audit_log_ids'])]),
    }

    _defaults = {
        'active': True,
    }

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_salary_level_job_title, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res


vhr_salary_level_job_title()