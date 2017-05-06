# -*- coding: utf-8 -*-

import logging

from openerp.osv import osv, fields


log = logging.getLogger(__name__)


class vhr_core_team(osv.osv):
    _name = 'vhr.core.team'
    _description = 'VHR Core Team'

    _columns = {
        'name': fields.char('Name', size=128),
        'employee_id': fields.many2one('hr.employee', 'Employee'),
        'effect_from': fields.date('Effective From'),
        'effect_to': fields.date('Effective To'),
        'stock_qty': fields.integer('Stock Quantity'),
        'description': fields.text('Description'),
        'active': fields.boolean('Active'),
        'employee_code': fields.related('employee_id', 'code', type="char", string="Employee Code"),
#         'employee_name': fields.related('employee_id', 'name', type="char", string="Employees"),
#         'employee_login': fields.related('employee_id', 'login', type="char", string="Employee Login"),
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
        reads = self.read(cr, uid, ids, ['employee_id'], context=context)
        res = []
        for record in reads:
                name = record.get('employee_id',False) and record['employee_id'][1]
                res.append((record['id'], name))
        return res
    
    #Raise error if have record of same employee have overlap effect_from-effect_to
    def check_overlap_date(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        context['active_test'] = False
        if ids:
            core_info = self.read(cr, uid, ids[0], ['employee_id', 'effect_from', 'effect_to'])
            employee_id = core_info.get('employee_id', False) and core_info['employee_id'][0]
            effect_from = core_info['effect_from']
            effect_to = core_info['effect_to']
            
            
            all_core_ids = self.search(cr, uid, [('employee_id', '=', employee_id)])
            if not all_core_ids:
                    return True
            if not effect_to:
                effect_to = effect_from
            not_overlap_core_ids = self.search(cr, uid, [('employee_id', '=', employee_id),
                                                         '|',('effect_from', '>', effect_to), 
                                                             ('effect_to', '<', effect_from)])
            #Record not overlap is the record link to employee
            if len(all_core_ids) == len(not_overlap_core_ids):
                return True
            else:
                #Get records from working_ids not in not_overlap_working_ids
                overlap_ids = [x for x in all_core_ids if x not in not_overlap_core_ids]
                #Get records from working_ids are not working_id
                overlap_ids = [x for x in overlap_ids if x not in ids]
            
                #If have record overlap with current record 
                if overlap_ids:
                    return False
        return True
    
    def _check_dates(self, cr, uid, ids, context=None):
        for period in self.read(cr, uid, ids, ['effect_from', 'effect_to'], context=context):
            if period['effect_from'] and period['effect_to'] and period['effect_from'] >= period['effect_to']:
                return False
        return True
    
    _constraints = [
        (_check_dates, '\n\nEffect To must be greater than or equal to Effect From !', ['effect_from', 'effect_to']),
        (check_overlap_date, '\n\nThe effective duration is overlapped. Please check again !', ['effect_from', 'effect_to', 'employee_id']),
    ]
    
    #Check if have record of same employee have effect_to=False, raise error
    def check_not_update_effect_to(self, cr, uid, employee_id, context=None):
        if employee_id:
            not_update_record = self.search(cr, uid, [('employee_id','=', employee_id),('effect_to','=',False)])
            if not_update_record:
                raise osv.except_osv('Validation Error !',
                                 'There is a core team of this employee does not input effective to date. Please check again !')
        return True        
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if not context:
            context = {}
              
        return super(vhr_core_team, self).search(cr, uid, args, offset, limit, order, context, count)

        
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_core_team, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !',
                                 'You cannot delete the record(s) which reference to others !')
        return res
    
    def create(self, cr, uid, vals, context=None):
        #Check not record of same employee not update effect_to
        if vals.get('employee_id', False):
            self.check_not_update_effect_to(cr, uid, vals['employee_id'], context)
        
        res = super(vhr_core_team, self).create(cr, uid, vals, context)
        return res
    


vhr_core_team()