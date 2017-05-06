# -*-coding:utf-8-*-
import logging
import openerp
from openerp.osv import fields
from openerp.osv import osv
from openerp.tools.translate import _
from openerp.addons.audittrail import audittrail
from openerp import SUPERUSER_ID

log = logging.getLogger(__name__)


class audittrail_log_line(osv.osv):
    _inherit = "audittrail.log.line"

    _columns = {
        'user_id': fields.related('log_id', 'user_id', type='many2one', relation='res.users', string='User',
                                  readonly=True, \
                                  store=False),
        'timestamp': fields.related('log_id', 'timestamp', type='datetime', string='Date', readonly=True, \
                                    store=False),
        'method': fields.related('log_id', 'method', type='char', string='Method', readonly=True, \
                                 store=False),
        'res_id': fields.related('log_id', 'res_id', type='integer', string='Resource Id', readonly=True, \
                                 store=False),
        'object_id': fields.related('log_id', 'object_id', type='many2one', relation='ir.model', string='Method',
                                    readonly=True, \
                                    store=False),
    }

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if order is None:
            order = 'id desc'
        return super(audittrail_log_line, self).search(cr, uid, args, offset, limit, order, context, count)
    

audittrail_log_line()


class audittrail_rule(osv.osv):
    _inherit = "audittrail.rule"

    _columns = {
        'execute_obj_id': fields.many2one('ir.model', 'Execute Object'),
        'execute_function': fields.char('Execute Function', size=128),
        'execute_parameter': fields.char('Execute Parameter', size=128),
    }

    # Subscribe for many selected record audittrai.rule
    def subscribe_list(self, cr, uid, context=None):
        active_ids = context.get('active_ids', False)
        if active_ids:
            self.subscribe(cr, uid, active_ids, context)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def unsubscribe(self, cr, uid, ids, *args):
        for i in self.browse(cr, uid, ids, fields_process=['execute_obj_id', 'execute_parameter', 'execute_function']):
            if i.execute_function or i.execute_obj_id or i.execute_parameter:
                raise osv.except_osv(
                    _('WARNING: You can not unsubscribe this rule!'),
                    _('This one contain Execution information (Execute Object, Execute Function,'
                      ' Execute Parameter). Please notify this action to responsible person and remove all execution'
                      ' information if you really really wanna unsubscribe this rule!'))
        return super(audittrail_rule, self).unsubscribe(cr, uid, ids, *args)

    # Subscribe for many selected record audittrai.rule
    def unsubscribe_list(self, cr, uid, context=None):
        active_ids = context.get('active_ids', False)
        if active_ids:
            self.unsubscribe(cr, uid, active_ids, context)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }


audittrail_rule()

def create_log_line(cr, uid, log_id, model, lines=None):
    """
    Creates lines for changed fields with its old and new values

    @param cr: the current row, from the database cursor,
    @param uid: the current user’s ID for security checks,
    @param model: Object which values are being changed
    @param lines: List of values for line is to be created
    """
    if lines is None:
        lines = []
    pool = openerp.registry(cr.dbname)
    obj_pool = pool[model.model]
    model_pool = pool.get('ir.model')
    field_pool = pool.get('ir.model.fields')
    log_line_pool = pool.get('audittrail.log.line')
    for line in lines:
        field_obj = obj_pool._all_columns.get(line['name'])
        assert field_obj, _("'%s' field does not exist in '%s' model" %(line['name'], model.model))
        field_obj = field_obj.column
        old_value = line.get('old_value', '')
        new_value = line.get('new_value', '')
        search_models = [model.id]
        if obj_pool._inherits:
            search_models += model_pool.search(cr, uid, [('model', 'in', obj_pool._inherits.keys())])
        field_id = field_pool.search(cr, uid, [('name', '=', line['name']), ('model_id', 'in', search_models)])
        if field_obj._type == 'many2one':
            old_value = old_value and old_value[0] or old_value
            new_value = new_value and new_value[0] or new_value
        #Tuannh3 fix text boolean and list
        elif field_obj._type == 'boolean':
            value_bool = 'False'
            if str(line.get('new_value_text', '')) != '':
                value_bool = str(line.get('new_value_text', ''))
            line.update({'new_value_text' : value_bool})
            value_bool = 'False'
            if str(line.get('old_value_text', '')) != '':
                value_bool = str(line.get('old_value_text', ''))
            line.update({'old_value_text' : value_bool})
        elif field_obj._type == 'many2many' or field_obj._type == 'one2many':
            old_value_text = line.get('old_value_text', '')
            new_value_text = line.get('new_value_text', '')
            res = ''
            if isinstance(old_value_text, list):
                for item in old_value_text:
                    if not res:
                        res = '%s' % (item)
                    else:
                        res = '%s, %s' % (res, item)
            line.update({'old_value_text' : res})
            res = ''
            if isinstance(new_value_text, list):
                for item in new_value_text:
                    if not res:
                        res = '%s' % (item)
                    else:
                        res = '%s, %s' % (res, item)
            line.update({'new_value_text' : res})    
        vals = {
                "log_id": log_id,
                "field_id": field_id and field_id[0] or False,
                "old_value": old_value,
                "new_value": new_value,
                "old_value_text": line.get('old_value_text', ''),
                "new_value_text": line.get('new_value_text', ''),
                "field_description": field_obj.string
                }
        line_id = log_line_pool.create(cr, uid, vals)
    return True

def custom_get_data(cr, uid, pool, res_ids, model, method, loop=1):
    data = {}
    resource_pool = pool[model.model]
    # read all the fields of the given resources in super admin mode (except field link to audittrail.log.line)
    fields = []
    
    dict_column = resource_pool._all_columns
    for field in dict_column:
        if hasattr (dict_column[field].column, 'audittrail_log') and dict_column[field].column.audittrail_log == False:
            continue
        if not (dict_column[field].column and dict_column[field].column._type == 'one2many' and dict_column[field].column._obj == 'audittrail.log.line'):
            fields.append(field)
    
    for resource in resource_pool.read(cr, SUPERUSER_ID, res_ids, fields):
        values = {}
        values_text = {}
        resource_id = resource['id']
        # loop on each field on the res_ids we just have read
        for field in resource:
            if field in ('__last_update', 'id') or not resource_pool._all_columns.get(field):
                continue
            
            field_obj = resource_pool._all_columns.get(field).column
            
            #Dont check log with field have is_log=False
            if field_obj and hasattr(field_obj,'is_log') and field_obj.is_log == False:
                continue
                
            values[field] = resource[field]
            # get the textual value of that field for this record
            values_text[field] = audittrail.get_value_text(cr, SUPERUSER_ID, pool, resource_pool, method, field, resource[field])

            
            if field_obj._type in ('one2many','many2many') and field_obj._obj not in ('audittrail.log.line',):
                # check if an audittrail rule apply in super admin mode
                if audittrail.check_rules(cr, SUPERUSER_ID, field_obj._obj, method):
                    # check if the model associated to a *2m field exists, in super admin mode
                    x2m_model_ids = pool.get('ir.model').search(cr, SUPERUSER_ID, [('model', '=', field_obj._obj)])
                    x2m_model_id = x2m_model_ids and x2m_model_ids[0] or False
                    assert x2m_model_id, _("'%s' Model does not exist..." %(field_obj._obj))
                    x2m_model = pool.get('ir.model').browse(cr, SUPERUSER_ID, x2m_model_id)
                    field_resource_ids = list(set(resource[field]))
                    if model.model == x2m_model.model:
                        # we need to remove current resource_id from the many2many to prevent an infinit loop
                        if resource_id in field_resource_ids:
                            field_resource_ids.remove(resource_id)
                    if loop<=1:
                        loop = loop + 1
                        data.update(custom_get_data(cr, SUPERUSER_ID, pool, field_resource_ids, x2m_model, method, loop))

        data[(model.id, resource_id)] = {'text':values_text, 'value': values}
    
    return data


def custom_prepare_audittrail_log_line(cr, uid, pool, model, resource_id, method, old_values, new_values, field_list=None, loop=1):
    if field_list is None:
        field_list = []
    key = (model.id, resource_id)
    lines = {
        key: []
    }
    # loop on all the fields
    for field_name, field_definition in pool[model.model]._all_columns.items():
        if field_name in ('__last_update', 'id'):
            continue
        #if the field_list param is given, skip all the fields not in that list
        if field_list and field_name not in field_list:
            continue
        field_obj = field_definition.column
        if field_obj._type in ('one2many','many2many'):
            # checking if an audittrail rule apply in super admin mode
            if audittrail.check_rules(cr, SUPERUSER_ID, field_obj._obj, method):
                # checking if the model associated to a *2m field exists, in super admin mode
                x2m_model_ids = pool.get('ir.model').search(cr, SUPERUSER_ID, [('model', '=', field_obj._obj)])
                x2m_model_id = x2m_model_ids and x2m_model_ids[0] or False
                assert x2m_model_id, _("'%s' Model does not exist..." %(field_obj._obj))
                x2m_model = pool.get('ir.model').browse(cr, SUPERUSER_ID, x2m_model_id)
                # the resource_ids that need to be checked are the sum of both old and previous values (because we
                # need to log also creation or deletion in those lists).
                x2m_old_values_ids = old_values.get(key, {'value': {}})['value'].get(field_name, [])
                x2m_new_values_ids = new_values.get(key, {'value': {}})['value'].get(field_name, [])
                # We use list(set(...)) to remove duplicates.
                res_ids = list(set(x2m_old_values_ids + x2m_new_values_ids))
                if model.model == x2m_model.model:
                    # we need to remove current resource_id from the many2many to prevent an infinit loop
                    if resource_id in res_ids:
                        res_ids.remove(resource_id)
                for res_id in res_ids:
                    if loop<=1:
                        loop = loop + 1
                        lines.update(custom_prepare_audittrail_log_line(cr, SUPERUSER_ID, pool, x2m_model, res_id, method, old_values, new_values, field_list, loop))
        # if the value value is different than the old value: record the change
        if key not in old_values or key not in new_values or old_values[key]['value'].get(field_name,False) != new_values[key]['value'].get(field_name,False):
            data = {
                  'name': field_name,
                  'new_value': key in new_values and new_values[key]['value'].get(field_name),
                  'old_value': key in old_values and old_values[key]['value'].get(field_name),
                  'new_value_text': key in new_values and new_values[key]['text'].get(field_name),
                  'old_value_text': key in old_values and old_values[key]['text'].get(field_name)
            }
            #Prevent log data not change or not update anything
            if data['old_value'] == data['new_value'] or (not data['old_value'] and not data['new_value']):
                continue
            
            lines[key].append(data)
            
    return lines


def custom_process_data(cr, uid, pool, res_ids, model, method, old_values=None, new_values=None, field_list=None):
    if field_list is None:
        field_list = []
    # loop on all the given ids
    for res_id in res_ids:
        # compare old and new values and get audittrail log lines accordingly
        lines = custom_prepare_audittrail_log_line(cr, uid, pool, model, res_id, method, old_values, new_values, field_list)

        # if at least one modification has been found
        for model_id, resource_id in lines:
            line_model = pool.get('ir.model').browse(cr, SUPERUSER_ID, model_id).model

            vals = {
                'method': method,
                'object_id': model_id,
                'user_id': uid,
                'res_id': resource_id,
            }
            if (model_id, resource_id) not in old_values and method not in ('copy', 'read'):
                # the resource was not existing so we are forcing the method to 'create'
                # (because it could also come with the value 'write' if we are creating
                #  new record through a one2many field)
                vals.update({'method': 'create'})
            if (model_id, resource_id) not in new_values and (model_id, resource_id) in old_values and method not in ('copy', 'read'):
                # the resource is not existing anymore so we are forcing the method to 'unlink'
                # (because it could also come with the value 'write' if we are deleting the
                #  record through a one2many field)
                name = old_values[(model_id, resource_id)]['value'].get('name',False)
                vals.update({'method': 'unlink'})
            else :
                name = pool[line_model].name_get(cr, uid, [resource_id])
                if not name:
                    name = ''
                else:
                    name = name[0] and name[0][1] or ''
            vals.update({'name': name})
            # create the audittrail log in super admin mode, only if a change has been detected
            if lines[(model_id, resource_id)]:
                log_id = pool.get('audittrail.log').create(cr, SUPERUSER_ID, vals)
                model = pool.get('ir.model').browse(cr, uid, model_id)
                audittrail.create_log_line(cr, SUPERUSER_ID, log_id, model, lines[(model_id, resource_id)])
    return True

audittrail.get_data = custom_get_data
audittrail.prepare_audittrail_log_line = custom_prepare_audittrail_log_line
audittrail.process_data = custom_process_data
audittrail.create_log_line = create_log_line