# -*-coding:utf-8-*-
import logging
import openerp

from openerp.osv import osv, fields

log = logging.getLogger(__name__)


class vhr_state_change(osv.osv):
    _name = 'vhr.state.change'
    _inherit = 'vhr.state.change'
    
    def read(self, cr, user, ids, fields=None, context=None, load='_classic_read'):
        if not context:
            context = {}
        
        res =  super(vhr_state_change, self).read(cr, user, ids, fields, context, load)
        
        if res and context.get('is_show_comment',False):
            for item in res:
            
                """Termination:
                    - Nhân viên không thấy được comment của tất cả
                    - LM chỉ thấy được comment của Nhân viên
                    - DH chỉ thấy được comment của Nhân viên và LM, không thấy HRBP's comment/note
                    - HRBP và C&B thấy được tất cả comment
                """
                if context.get('is_cb', False) or context.get('is_hrbp', False) or context.get('is_assistant_hrbp', False):
                    print '.'
                elif context.get('is_dept_head', False) and item.get('old_state',False) == 'Waiting HRBP':
                    item['comment'] = ''
                elif context.get('is_lm', False) and item.get('old_state',False) not in ['Draft','Waiting LM']:
                    item['comment'] = ''
                elif context.get('is_requester', False) and item.get('old_state',False) != 'Draft':
                    item['comment'] = ''
        
        return res
    


vhr_state_change()