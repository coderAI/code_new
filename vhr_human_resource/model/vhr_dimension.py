# -*- coding: utf-8 -*-

import logging

from openerp.osv import osv, fields


log = logging.getLogger(__name__)


class vhr_dimension(osv.osv):
    _name = 'vhr.dimension'
    _inherit = 'vhr.dimension'
    _description = 'VHR Dimension'


    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        
        args_new = ['|', '|', ('name', operator, name), ('code', operator, name), ('name_en', operator, name)] + args
        ids = self.search(cr, uid, args_new, context=context)
        return self.name_get(cr, uid, ids, context=context)
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if not context:
            context = {}
            
        if context.get('exit_checklist_request', False):
            from vhr_exit_checklist_request import DEPARTMENT_FIELDS, TEAM_FIELDS
            fields = DEPARTMENT_FIELDS
            record = self.pool.get('vhr.exit.checklist.request').read(cr, uid, context['exit_checklist_request'], fields)
            available_code = []
            for field in DEPARTMENT_FIELDS:
                if record.get(field, False):
                    available_code.append(TEAM_FIELDS[field][0])
             
            args.append(('code','in',available_code))
            
        return super(vhr_dimension, self).search(cr, uid, args, offset, limit, order, context, count)


vhr_dimension()