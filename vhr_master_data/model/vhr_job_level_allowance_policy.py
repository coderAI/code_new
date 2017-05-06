# -*- coding: utf-8 -*-

import logging

from openerp.osv import osv, fields

from openerp.tools.translate import _

log = logging.getLogger(__name__)


class vhr_job_level_allowance_policy(osv.osv):
    _name = 'vhr.job.level.allowance.policy'
    _description = 'VHR Job Level Allowance Policy'
    
    _columns = {
        'name': fields.char('Name', size=128),
        'job_level_id': fields.many2one('vhr.job.level', 'Job Level', ondelete='restrict'),
        'taxi_allowance': fields.float('Taxi Amount'),
        'tel_allowance': fields.float('Tel Amount'),
        'effective_date': fields.date('Effective Date'),
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

    _sql_constraints = [
        ('unique_job_level_effective_date', 'unique(job_level_id, effective_date)',
         _('Job Level and Effective Date already exist!')),
    ]

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_job_level_allowance_policy, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res

    def copy_data(self, cr, uid, id, default, context=None):
        """
        Handle when user duplicate record constraints unique will raise message.
        We del effective_date in data it will be alright.
        :param cr:
        :param uid:
        :param id:
        :param default:
        :param context:
        :return: dictionary of data without 'effective_date' key
        """
        data = super(vhr_job_level_allowance_policy, self).copy_data(cr, uid, id, default, context=context)
        if 'effective_date' in data:
            del data['effective_date']
        return data


vhr_job_level_allowance_policy()