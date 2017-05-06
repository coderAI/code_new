# -*-coding:utf-8-*-
import logging
from openerp.osv import osv, fields
from openerp import SUPERUSER_ID
from ir_view_security import view_security

_logger = logging.getLogger(__name__)

class ir_ui_view(osv.osv):
    _inherit = 'ir.ui.view'
    
    def init(self, cr):
        _logger.info('Start add security for view')
        try:
            ROLES = {}
            for view_xml, list_group_xml in view_security.iteritems():
                view_id = self.xmlid_lookup(cr, SUPERUSER_ID, view_xml)
                lst_roles = []
                if view_id:
                    for group_xml in list_group_xml:
                        if group_xml in ROLES:
                            role_id = ROLES.get(group_xml, False)
                        else:
                            role_id = self.xmlid_lookup(cr, SUPERUSER_ID, group_xml)
                            ROLES[group_xml] = role_id
                            
                        if role_id:
                            lst_roles.append(role_id)
                    groups = self.read(cr, SUPERUSER_ID, view_id, ['groups_id'])
                    groups_id = groups.get('groups_id', [])
                    if lst_roles:
                        lst_roles = list( set(lst_roles).difference(set(groups_id)))
                        if lst_roles:
                            lst_roles.extend(groups_id)
                            self.write(cr, SUPERUSER_ID, view_id, {'groups_id' : [(6, 0, list(set(lst_roles)))]})
                    
        except Exception as e:
            _logger.info(e)
        _logger.info('End add security for view')
        return True
    
    def xmlid_lookup(self, cr, uid, XML_ID):
        try:
            model_data = self.pool.get('ir.model.data')
            result = model_data.xmlid_lookup(cr, uid, XML_ID)
            return result[2]
        except Exception as e:
            _logger.info(e)
        return False
ir_ui_view()
