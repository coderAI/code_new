# -*- coding: utf-8 -*-

from openerp.osv import osv


class ir_model_data(osv.osv):

    _inherit = 'ir.model.data'

    def remove_noupdate(self, cr, uid, module, xml_id):
        if not module or not xml_id:
            return True
        
        sql = '''
            UPDATE ir_model_data SET noupdate = 'f' WHERE module='%s' AND name='%s'
        ''' % (module, xml_id)
        cr.execute(sql)
        
        return True

    def split_xml(self, item):
        list = item.split('.')
        
        if list and len(list) == 2:
            return list[0], list[1]
        return '', ''

    def remove_noupdate_list(self, cr, uid, xml_ids):
        if not xml_ids:
            return True

        for item in xml_ids.split(','):
            module, xml_id = self.split_xml(item)
            self.remove_noupdate(cr, uid, module.strip(), xml_id.strip())

        return True
