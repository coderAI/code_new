# -*- coding: utf-8 -*-

import logging
import time
import simplejson as json
from lxml import etree

from openerp.osv import osv, fields
from openerp.tools.translate import _


log = logging.getLogger(__name__)


class vhr_sequence(osv.osv):
    """ Sequence model.

    The sequence model allows to define and use so-called sequence objects.
    Such objects are used to generate unique identifiers in a transaction-safe
    way.

    """
    _name = 'vhr.sequence'
    _order = 'name'

    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'active': fields.boolean('Active'),
        'prefix': fields.char('Prefix', size=64, help="Prefix value of the record for the sequence"),
        'suffix': fields.char('Suffix', size=64, help="Suffix value of the record for the sequence"),
        'padding': fields.integer('Number Padding', required=True,
                                  help="OpenERP will automatically adds some '0' on the left of the 'Next Number' to get the required padding size."),
        'model_id': fields.many2one('ir.model', 'Model', domain=[('model', 'not in', [_name])]),
        'field_id': fields.many2one('ir.model.fields', 'Field'),
        'dimension_type_id': fields.many2one('vhr.dimension.type', 'Dimension Type'),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                         domain=[('object_id.model', '=', _name),
                                                 ('field_id.name', 'not in',
                                                  ['write_date', 'audit_log_ids'])]),
    }
    _defaults = {
        'active': True,
        'padding': 3,
    }

    _unique_insensitive_constraints = [{'model_id': "Sequence configuration is already exist!",
                                        'field_id': "Sequence configuration is already exist!",
                                        'dimension_type_id': "Sequence configuration is already exist!"
                                        }]
        
    def onchange_prefix_suffix(self, cr, uid, ids, value, field):
        res = {'value': {}}
        if '-' in value:
            warning = {
                    'title': ('Warning!'),
                    'message': ("%s can't be have '-' in value" % field)
                }
            res['value'].update({field.lower(): value.replace('-','')})
            return {'value': res['value'], 'warning': warning}
        return res
        
    def _interpolate(self, s, d):
        if s:
            return s % d
        return ''

    def _interpolation_dict(self):
        t = time.localtime()  # Actually, the server is always in UTC.
        return {
            'year': time.strftime('%Y', t),
            'month': time.strftime('%m', t),
            'day': time.strftime('%d', t),
            'y': time.strftime('%y', t),
            'doy': time.strftime('%j', t),
            'woy': time.strftime('%W', t),
            'weekday': time.strftime('%w', t),
            'h24': time.strftime('%H', t),
            'h12': time.strftime('%I', t),
            'min': time.strftime('%M', t),
            'sec': time.strftime('%S', t),
        }

    def get_code(self, cr, uid, seq_id, model, field, context=None):
        uid = 1
        if not seq_id:
            return False
        if context is None:
            context = {}
        sequence = self.read(cr, uid, seq_id, ['name', 'prefix', 'number_increment', \
                                               'suffix', 'padding', 'model_id', 'field_id', 'dimension_type_id'])
        
        field_id = sequence.get('field_id', False) and sequence['field_id'][0] or False
        field_name = ''
        if field_id:
            field_data = self.pool.get('ir.model.fields').read(cr, uid, field_id, ['name'])
            field_name = field_data.get('name', '')
            
        obj_model = self.pool.get(model)
        context.update({'active_test': False})
        args = []
        if sequence['dimension_type_id']:
            args = [('dimension_type_id', '=', sequence['dimension_type_id'][0])]
        
        if field_name:
            args.append((field_name,'ilike',sequence['prefix']+'-'))
        
        sql = """
                SELECT id FROM {0} WHERE {1} order by code desc
              """
        #Make simple where sql based on domain, if domain is more complicated, you should check function _where_calc() in orm.py for more detail
        ids = []
        if args:
            where_clause = ''
            for tuple in args:
                if where_clause:
                    where_clause += ' AND '
                
                if tuple[1] == 'ilike':
                    where_clause += '%s'%tuple[0] + ' ilike ' + " '{0}%' ".format(tuple[2])
                else:
                    where_clause += '%s'%tuple[0] + ' %s '%tuple[1] + " '%s'" %tuple[2]
            
            model = model.replace('.','_')
            cr.execute(sql.format(model, where_clause))
            res = cr.fetchall()
            ids = [item[0] for item in res]
            
#            ids = obj_model.search(cr, uid, args, None, None, 'code desc', context, False)
            
        if ids:
            ids = ids[0]
        res_read = obj_model.read(cr, uid, ids, [field])
        stt = 0
        if res_read:
            try:
                list_code = res_read[field]
                list_code = list_code.split('-')
                for item in list_code:
                    if item.isdigit():
                        stt = int(item)
                    # d = self._interpolation_dict()
            except Exception as e:
                stt = 0
                log.exception(e)
        try:
            # Khong cho su dung nua
            # interpolated_prefix = self._interpolate(sequence['prefix'], d)
            # interpolated_suffix = self._interpolate(sequence['suffix'], d)
            interpolated_prefix = sequence['prefix'] or False
            interpolated_suffix = sequence['suffix'] or False
        except ValueError:
            raise osv.except_osv(_('Warning'),
                                 _('Invalid prefix or suffix for sequence \'%s\'') % (sequence.get('name')))
        stt = '%%0%sd' % sequence['padding'] % (stt + 1)
        if interpolated_prefix:
            stt = '%s-%s' % (interpolated_prefix, stt)
        if interpolated_suffix:
            stt = '%s-%s' % (stt, interpolated_suffix)
        res = {field: '%s' % (stt or '')}
        return res

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(vhr_sequence, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar=toolbar,
                                                        submenu=submenu)
        if res['type'] == 'form':
            ir_model = self.pool.get('ir.model')
            dimension = ir_model.search(cr, uid, [('model', '=', 'vhr.dimension')])
            doc = etree.XML(res['arch'])
            for node in doc.xpath("//field[@name='dimension_type_id']"):
                modifiers = json.loads(node.get('modifiers'))
                modifiers.update({'invisible': [('model_id', '!=', dimension[0])]})
                modifiers.update({'required': [('model_id', '=', dimension[0])]})
                node.set('modifiers', json.dumps(modifiers))
            res['arch'] = etree.tostring(doc)
        return res


vhr_sequence()