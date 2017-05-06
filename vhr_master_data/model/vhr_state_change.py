# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields

log = logging.getLogger(__name__)


class vhr_state_change(osv.osv):
    _name = 'vhr.state.change'
    _description = 'VHR State Change'
    _order = 'create_date desc, id desc'

    _columns = {
        'create_date': fields.datetime('Create date'),
        'create_uid': fields.many2one('res.users', 'User Create'),
        'old_state': fields.char('Old Status'),
        'new_state': fields.char('New Status'),
        'comment': fields.text('Comment'),
        'res_id': fields.integer('Resource id'),
        'model': fields.char('Model'),
        'login_create_uid': fields.related('create_uid', 'login', type='char', string='User Create', readonly=1),
    }

    _order = 'id desc,create_date desc'

    def get_last_user(self, cr, uid, res_id, model):
        result = u''
        if res_id and model:
            lst = self.search(cr, uid, [('model', '=', model), ('res_id', '=', res_id)], order='create_date desc',
                              limit=1)
            if lst:
                create_uid = self.read(cr, uid, lst[0], ['create_uid']).get('create_uid', '')
                if create_uid and len(create_uid) == 2:
                    result = create_uid[1]
        return result

    def get_last_user_id(self, cr, uid, res_id, model):
        result = u''
        if res_id and model:
            lst = self.search(cr, uid, [('model', '=', model), ('res_id', '=', res_id)], order='create_date desc',
                              limit=1)
            if lst:
                create_uid = self.read(cr, uid, lst[0], ['create_uid']).get('create_uid', '')
                if create_uid and len(create_uid) == 2:
                    result = create_uid[0]
        return result

    def get_last_message(self, cr, uid, res_id, model):
        result = u''
        if res_id and model:
            lst = self.search(cr, uid, [('model', '=', model), ('res_id', '=', res_id)], order='create_date desc',
                              limit=1)
            if lst:
                result = self.read(cr, uid, lst[0], ['comment'])['comment']
        return result

    def get_last_state(self, cr, uid, res_id, model):
        result = {'old_state': '',
                  'new_state': ''
        }
        if res_id and model:
            lst = self.search(cr, uid, [('model', '=', model), ('res_id', '=', res_id)], order='id desc')
            if lst:
                result = self.read(cr, uid, lst[0], ['old_state', 'new_state'])
        return result

    def read(self, cr, user, ids, fields=None, context=None, load='_classic_read'):
        res = super(vhr_state_change, self).read(cr, user, ids, fields, context, load)
        if context is None: context = {}
        for item in res:
            # change 16-10-2014
            if 'old_state' in item and 'new_state' in item:
                if item['old_state'] == 'waiting_hrbp' and item['new_state'] in ['waiting_dept', 'waiting_rrm']:
                    item['old_state'] = 'HRBP Approved'
                    if item['new_state'] == 'waiting_dept':
                        item['new_state'] = 'Waiting Dept'
                    else:
                        item['new_state'] = 'Waiting RRM'
                elif item['old_state'] == 'waiting_dept' and item['new_state'] == 'waiting_rrm':
                    item['old_state'] = 'DeptHead Approved'
                    item['new_state'] = 'Waiting RRM'
                elif item['old_state'] == 'waiting_rrm' and item['new_state'] == 'in_progress':
                    item['old_state'] = 'RRM Approved'
                    item['new_state'] = 'In Progress'
                elif item['old_state'] == 'draft' and item['new_state'] == 'waiting_hrbp':
                    item['old_state'] = 'Draft'
                    item['new_state'] = 'Waiting HRBP'
            
            if 'is_show_comment' in context and not context.get('is_show_comment',False):
                item['comment'] = ''
        return res


vhr_state_change()
