# -*-coding:utf-8-*-
import logging
from datetime import datetime

from openerp.osv import osv, fields
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT


log = logging.getLogger(__name__)


class vhr_employee_instance(osv.osv):
    _name = 'vhr.employee.instance'
    _description = 'VHR Employee Instance'

    _order = 'date_start desc'

    _columns = {
        'name': fields.char('Name', size=128),
        'employee_id': fields.many2one('hr.employee', 'Employee'),
        'company_id': fields.many2one('res.company', 'Company'),
        'company_code': fields.related('company_id', 'code', type='char', string='Company'),
        'date_start': fields.date('Join Date'),
        'date_end': fields.date('End Date'),
        'division_id': fields.many2one('hr.department', 'Business Unit',
                                       domain=[('organization_class_id.level', '=', 1)]),
        'department_group_id': fields.many2one('hr.department', 'Department Group',
                                         domain=[('organization_class_id.level', '=', 2)]),
        'department_id': fields.many2one('hr.department', 'Department',
                                         domain=[('organization_class_id.level', '=', 3)]),
        'team_id': fields.many2one('hr.department', 'Team', ondelete='restrict',
                                   domain=[('organization_class_id.level', '>', 3)]),
        'organization_class_id': fields.related('department_id', 'organization_class_id', type='many2one',
                                                relation='vhr.organization.class', string='Organization Class'),
        'title_id': fields.many2one('vhr.job.title', string='Job Title'),
        'job_level_id': fields.many2one('vhr.job.level', 'Job Level'),
        'manager_id': fields.many2one('hr.employee', 'Dept Head'),
        'report_to': fields.many2one('hr.employee', 'Report To'),
        
         #New job level
        'job_level_position_id': fields.many2one('vhr.job.level.new', 'Position Level', ondelete='restrict'),
        'job_level_person_id': fields.many2one('vhr.job.level.new', 'Person Level', ondelete='restrict'),
    }

    
    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        res = []
        for line in self.browse(cr, uid, ids, context=context):
            date_format = "%d/%m/%Y"
            date_start = line.date_start and datetime.strptime(line.date_start, DEFAULT_SERVER_DATE_FORMAT).strftime(
                date_format) or ''
            date_end = line.date_end and datetime.strptime(line.date_end, DEFAULT_SERVER_DATE_FORMAT).strftime(
                date_format) or ''

            res.append((line.id, ('%s - %s' % (date_start, date_end))))
        return res

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_employee_instance, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res


vhr_employee_instance()