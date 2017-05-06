# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields

from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import datetime

log = logging.getLogger(__name__)


class vhr_working_background(osv.osv):
    _name = 'vhr.working.background'
    _description = 'VHR Working Background'

    def _get_default_job_type(self, cr, uid, context=None):
        m = self.pool.get('vhr.dimension')
        lst = m.search(cr, uid, [('dimension_type_id.code', '=', 'JOB_TYPE'),
                                 ('active', '=', True), ('code', '=', 'FULLTIME')])
        if lst:
            return lst[0]
        return False

    _columns = {
        'name': fields.char('Name', size=256),
        'from_date': fields.date('From Date'),
        'to_date': fields.date('To Date'),
        'company': fields.char('Company', size=256),
        'job_title': fields.char('Job Title', size=256),
        'current_salary': fields.float('Current Salary'),
        'main_task': fields.text('Main Task', size=256),
        'move_reason': fields.text('Move Reason'),
        'ref_person': fields.char('Contact Person', size=256),
        'ref_job_title': fields.char('Job Title', size=256),
        'ref_phone': fields.char('Phone', size=32),
        'note': fields.text('Note'),
        'active': fields.boolean('Active'),
        'is_current': fields.boolean('Is Current'),
        'employee_id': fields.many2one('hr.employee', string="Employee", ondelete='restrict'),
        'applicant_id': fields.many2one('hr.applicant', string="Candidate", ondelete='cascade'),
        # khi xóa candidate sẽ xóa toàn bộ working background nên bên candidate sẽ phải check lại có link với request nào hay không
        'industry_id': fields.many2one('vhr.dimension', 'Industry', ondelete='restrict',
                                       domain=[('dimension_type_id.code', '=', 'INDUSTRY'), ('active', '=', True)]),

        'job_type_id': fields.many2one('vhr.dimension', 'Job Type', ondelete='restrict',
                                       domain=[('dimension_type_id.code', '=', 'JOB_TYPE'), ('active', '=', True)]),
        'oversea': fields.many2one('res.country', 'Oversea', ondelete='restrict'),
        'relevant': fields.selection([
            ('yes','Yes'),
            ('no','No'),
             ], 'Relevant Company', select=True),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                          domain=[('object_id.model', '=', _name),
                                                  ('field_id.name', 'not in',
                                                   ['write_date', 'audit_log_ids'])]),
    }

    _defaults = {
                 'active': True,
                 'job_type_id': _get_default_job_type
    }
    
    def _check_dates(self, cr, uid, ids, context=None):
        for period in self.read(cr, uid, ids, ['from_date', 'to_date'], context=context):
            if period['from_date'] and period['to_date'] and period['from_date'] >= period['to_date']:
                return False
        return True

    _constraints = [
        (_check_dates, '\n\nTo date must be greater than or equal to From date !', ['from_date', 'to_date']),
    ]

    def name_get(self, cr, uid, ids, context=None):
        if not ids or False in ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        helth_cares = self.read(cr, uid, ids, ['employee_id', 'applicant_id'], context=context)
        res = []
        if helth_cares:
            for helth_care in helth_cares:
                if helth_care.get('employee_id', False):
                    name = helth_care['employee_id'][1]
                    res.append((helth_care['id'], name))
                elif helth_care.get('applicant_id', False):
                    name = helth_care['applicant_id'][1]
                    res.append((helth_care['id'], name))
        else:  # fix for audittrail
            for item in ids:
                res.append((item, ''))
        return res

    def onchange_date(self, cr, uid, ids, start_date, end_date):
        if end_date and start_date:
            time_delta = datetime.strptime(end_date, DEFAULT_SERVER_DATE_FORMAT) - datetime.strptime(start_date, DEFAULT_SERVER_DATE_FORMAT)
            day_delta = time_delta.days
            if day_delta < 0:           
                warning = {'title': 'User Alert!', 'message': 'Date To must be larger Date From'}
                return {'value': {'date_to': None}, 'warning': warning}
        return {'value': {} }
    
    def onchange_is_current(self, cr, uid, ids, is_current, context=None):
        res = {}
        if is_current:
            res = {'to_date': False}
        
        return {'value': res}
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if not context:
            context = {}
              
        return super(vhr_working_background, self).search(cr, uid, args, offset, limit, order, context, count)


    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_working_background, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res
    
            
            
vhr_working_background()
