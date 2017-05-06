# -*- coding: utf-8 -*-

import logging

from openerp.tools.safe_eval import safe_eval as eval

from openerp.osv import osv

log = logging.getLogger(__name__)


class ir_ui_menu(osv.osv):
    _inherit = 'ir.ui.menu'

    def get_needaction_data(self, cr, uid, ids, context=None):
        """ Return for each menu entry of ids :
            - if it uses the needaction mechanism (needaction_enabled)
            - the needaction counter of the related action, taking into account
              the action domain
        """
        if context is None:
            context = {}
        res = {}
        menu_ids = set()
        for menu in self.browse(cr, uid, ids, context=context):
            menu_ids.add(menu.id)
            ctx = None
            if menu.action and menu.action.type in ('ir.actions.act_window', 'ir.actions.client') and menu.action.context:
                try:
                    # use magical UnquoteEvalContext to ignore undefined client-side variables such as `active_id`
                    eval_ctx = tools.UnquoteEvalContext(**context)
                    ctx = eval(menu.action.context, locals_dict=eval_ctx, nocopy=True) or None
                except Exception:
                    # if the eval still fails for some reason, we'll simply skip this menu
                    pass
            menu_ref = ctx and ctx.get('needaction_menu_ref')
            if menu_ref:
                if not isinstance(menu_ref, list):
                    menu_ref = [menu_ref]
                model_data_obj = self.pool.get('ir.model.data')
                for menu_data in menu_ref:
                    model, id = model_data_obj.get_object_reference(cr, uid, menu_data.split('.')[0], menu_data.split('.')[1])
                    if (model == 'ir.ui.menu'):
                        menu_ids.add(id)
        menu_ids = list(menu_ids)

        for menu in self.browse(cr, uid, menu_ids, context=context):
            res[menu.id] = {
                'needaction_enabled': False,
                'needaction_counter': False,
            }
            if menu.action and menu.action.type in ('ir.actions.act_window', 'ir.actions.client') and menu.action.res_model:
                if menu.action.res_model in self.pool:
                    obj = self.pool[menu.action.res_model]
                    if obj._needaction:
                        if menu.action.type == 'ir.actions.act_window':
                            dom = menu.action.domain and eval(menu.action.domain, {'uid': uid}) or []
                            
                            #NG: Get context from action window
                            context = menu.action.context and eval(menu.action.context) or {}
                        else:
                            dom = eval(menu.action.params_store or '{}', {'uid': uid}).get('domain')
                        res[menu.id]['needaction_enabled'] = obj._needaction
                        res[menu.id]['needaction_counter'] = obj._needaction_count(cr, uid, dom, context=context)
        return res