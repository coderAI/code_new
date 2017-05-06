# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields



log = logging.getLogger(__name__)


class vhr_exit_checklist_department_fa(osv.osv):
    _name = 'vhr.exit.checklist.department.fa'
    _description = 'Exit Checklist Department FA'

    _columns = {
                'name': fields.char('Name', size=128),
                'department_id': fields.many2one('hr.department', 'Department', ondelete='restrict' , domain=[('organization_class_id.level','=', '3')]),
                'active': fields.boolean('Active'),
                'note': fields.text('Note'),
    }
    
    _defaults={'active': True}
    
    _unique_insensitive_constraints = [{'department_id': "Department is already exist!"}]

    
    def name_get(self, cr, uid, ids, context=None):
        if not ids or False in ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        reads = self.read(cr, uid, ids, ['department_id'], context=context)
        res = []
        for record in reads:
                name = record.get('department_id',False) and record['department_id'][1]
                res.append((record['id'], name))
        return res

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_exit_checklist_department_fa, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res
    


vhr_exit_checklist_department_fa()