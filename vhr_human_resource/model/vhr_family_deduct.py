# -*-coding:utf-8-*-
import logging
import datetime

import simplejson as json

from lxml import etree
from openerp.osv import osv, fields
from openerp.addons.vhr_common.model.vhr_common import vhr_common

log = logging.getLogger(__name__)


class vhr_family_deduct(osv.osv, vhr_common):
    _inherit = 'vhr.family.deduct'
    _description = 'VHR Dependant deduction'
    
    def _is_able_to_edit_info(self, cr, uid, ids, prop, unknow_none, context=None):
        res = {}
        groups = self.pool.get('res.users').get_groups(cr, uid)
        for record in self.read(cr, uid, ids, ['user_id']):
            res[record['id']] = False
            
            if set(['vhr_cb_profile']).intersection(set(groups)):
                res[record['id']] = True
        
        return res
    
    def _is_able_to_view_info(self, cr, uid, ids, prop, unknow_none, context=None):
        res = {}
        groups = self.pool.get('res.users').get_groups(cr, uid)
        mcontext={'search_all_employee': True}
        for record in self.read(cr, uid, ids, ['user_id'],context=mcontext):
            res[record['id']] = False
            
            if set(['vhr_cb','vhr_assistant_to_hrbp','vhr_hrbp']).intersection(set(groups)):
                res[record['id']] = True
            elif record['user_id'] and record['user_id'][0] == uid:
                res[record['id']] = True
            else:
                res[record['id']] = False
        
        return res

    _columns = {
        'is_able_to_edit_info': fields.function(_is_able_to_edit_info, type='boolean', string='Is Able To Edit Info'),
        'is_able_to_view_info': fields.function(_is_able_to_view_info, type='boolean', string='Is Able To View Info'),
        
    }
    
    _defaults = {
                'is_able_to_edit_info': True,
                'is_able_to_view_info': True,
                }
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        # Search rule for specific menu
        if not context:
            context = {}
        
        if context.get('filter_by_permission_family_deduct',False):
            new_args = []   
            groups = self.pool.get('res.users').get_groups(cr, uid)
                
            if not set(['hrs_group_system','vhr_cb_profile']).intersection(set(groups)):
                new_args = [('id','in',[])]
                args += new_args
         
        return super(vhr_family_deduct, self).search(cr, uid, args, offset, limit, order, context, count)


    
    def fields_view_get(self, cr, uid, view_id = None, view_type = 'form', context = None, toolbar = False, submenu = False):
        res = super(vhr_family_deduct, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar = toolbar, submenu = submenu)
        if context is None:
            context = {}
        if view_type == 'form':
            doc = etree.XML(res['arch'])
            if res['type'] == 'form':
                
                fields = self._columns.keys()
                for field in fields:
                    for node in doc.xpath("//field[@name='%s']" %field):
                        
                        modifiers = json.loads(node.get('modifiers'))
                        if not modifiers.get('readonly', False):
                            args_readonly = [('is_able_to_edit_info','=',False)]
                            modifiers.update({'readonly' : args_readonly})
                            
                        if not modifiers.get('invisible', False):
                            args_invisible = [('is_able_to_view_info','=',False)]
                            modifiers.update({'invisible' : args_invisible})
                        
                        
                        node.set('modifiers', json.dumps(modifiers))
                    
            res['arch'] = etree.tostring(doc)
        return res
    
    
    
    
    

vhr_family_deduct()