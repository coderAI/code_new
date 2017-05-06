# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields



log = logging.getLogger(__name__)


class vhr_resignation_link_exit_survey(osv.osv):
    _name = 'vhr.resignation.link.exit.survey'
    _description = 'VHR Resignation Link Exit Survey'

    _columns = {
        'name': fields.char('Name', size=128),
        'department_ids': fields.many2many('hr.department', 'exit_survey_link_dept_rel','survey_link_id','department_id','Department'),
        'link': fields.char('Link', size = 512),
        'description': fields.text('Description'),
        'active': fields.boolean('Active'),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                          domain=[('object_id.model', '=', _name),
                                                  ('field_id.name', 'not in',
                                                   ['write_date', 'audit_log_ids'])]),
    }

    _defaults = {
        'active': True,
    }

    def name_get(self, cr, uid, ids, context=None):
        if not ids or False in ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        reads = self.read(cr, uid, ids, ['department_ids'], context=context)
        res = []
        
        dept_pool = self.pool.get('hr.department')
        for record in reads:
            department_ids = record.get('department_ids', []) 
            if department_ids:
                depts = dept_pool.read(cr, uid, department_ids, ['code'])
                dept_names = [dept.get('code','') for dept in depts]
            
            name = ','.join(dept_names)
            res.append((record['id'], name))
        return res
    
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_resignation_link_exit_survey, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res


vhr_resignation_link_exit_survey()