# -*-coding:utf-8-*-
import logging
import time

from openerp.osv import osv, fields



log = logging.getLogger(__name__)


class project_project(osv.osv):
    _name = 'project.project'
    _inherit = 'project.project'
    _description = 'Project'

    _columns = {
        'code': fields.char('Code', size = 64),
        'name_en': fields.char('English Name', size=128),
        'description': fields.text('Description'),
        
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                      domain=[('object_id.model', '=', _inherit), \
                                              ('field_id.name', 'not in', ['write_date', 'audit_log_ids'])]),

    }

    _defaults = {
        'date_start': lambda *a: time.strftime('%Y-%m-%d')
    }
    
    _unique_insensitive_constraints = [{'code': "Project's Code is already exist!"},
                                       {'name': "Project's Vietnamese Name is already exist!"}]



    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        args_new = ['|', '|', ('name', operator, name), ('code', operator, name), ('name_en', operator, name)] + args
        ids = self.search(cr, uid, args_new)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(project_project, self).name_search(cr, uid, name, args, operator, context, limit)
    
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(project_project, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res


project_project()