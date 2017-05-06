# -*- coding: utf-8 -*-

from openerp.osv import osv


class res_users(osv.osv):
    _inherit = 'res.users'
    
    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = []
        for record in self.read(cr, uid, ids, ['login'], context=context):
            login = record.get('login', '') or ""
            res.append((record.get('id', False), login))
        
        return res
    
    def get_groups(self, cr, uid):
        """
        :param cr:
        :param uid:
        :return:
        """
        groups = []
        if uid:
            # Get all group user belong to
            user_info = self.pool.get('res.users').read(cr, uid, uid, ['groups_id'])
            group_ids = user_info.get('groups_id', [])
            data_ids = self.pool.get('ir.model.data').search(cr, uid, [('model', '=', 'res.groups'),
                                                                       ('res_id', 'in', group_ids)])
            data_infos = self.pool.get('ir.model.data').read(cr, uid, data_ids, ['name'])
            for data_info in data_infos:
                groups.append(data_info.get('name', ''))
        return groups