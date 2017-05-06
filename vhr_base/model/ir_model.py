# -*-coding:utf-8-*-
import logging
import time

import openerp
import openerp.modules.registry
from openerp.tools.translate import _
from openerp.addons.base.ir.ir_model import ir_model_data
from openerp.osv import osv, fields


log = logging.getLogger(__name__)

class ir_model_data(ir_model_data):
    
    
    def _update(self,cr, uid, model, module, values, xml_id=False, store=True, noupdate=False, mode='init', res_id=False, context=None):
        model_obj = self.pool[model]
        if not context:
            context = {}
        # records created during module install should not display the messages of OpenChatter
        context = dict(context, install_mode=True)
        if xml_id and ('.' in xml_id):
            assert len(xml_id.split('.'))==2, _("'%s' contains too many dots. XML ids should not contain dots ! These are used to refer to other modules data, as in module.reference_id") % xml_id
            module, xml_id = xml_id.split('.')
        if (not xml_id) and (not self.doinit):
            return False
        action_id = False
        if xml_id:
            cr.execute('''SELECT imd.id, imd.res_id, md.id, imd.model, imd.noupdate
                          FROM ir_model_data imd LEFT JOIN %s md ON (imd.res_id = md.id)
                          WHERE imd.module=%%s AND imd.name=%%s''' % model_obj._table,
                          (module, xml_id))
            results = cr.fetchall()
            for imd_id2,res_id2,real_id2,real_model,noupdate_imd in results:
                # In update mode, do not update a record if it's ir.model.data is flagged as noupdate
                if mode == 'update' and noupdate_imd:
                    return res_id2
                if not real_id2:
                    self.clear_caches()
                    cr.execute('delete from ir_model_data where id=%s', (imd_id2,))
                    res_id = False
                else:
                    assert model == real_model, "External ID conflict, %s already refers to a `%s` record,"\
                        " you can't define a `%s` record with this ID." % (xml_id, real_model, model)
                    res_id,action_id = res_id2,imd_id2

        if action_id and res_id:
            model_obj.write(cr, uid, [res_id], values, context=context)
            self.write(cr, uid, [action_id], {
                'date_update': time.strftime('%Y-%m-%d %H:%M:%S'),
                },context=context)
        elif res_id:
            model_obj.write(cr, uid, [res_id], values, context=context)
            if xml_id:
                if model_obj._inherits:
                    for table in model_obj._inherits:
                        inherit_id = model_obj.browse(cr, uid,
                                res_id,context=context)[model_obj._inherits[table]]
                        self.create(cr, uid, {
                            'name': xml_id + '_' + table.replace('.', '_'),
                            'model': table,
                            'module': module,
                            'res_id': inherit_id.id,
                            'noupdate': noupdate,
                            },context=context)
                self.create(cr, uid, {
                    'name': xml_id,
                    'model': model,
                    'module':module,
                    'res_id':res_id,
                    'noupdate': noupdate,
                    },context=context)
        else:
            if mode=='init' or (mode=='update' and xml_id):
                #NG: Add import_id to context to create record with id= import_id
                if mode=='init' and xml_id:
                    try:
                        int(xml_id)
                        context['import_id'] = xml_id
                    except:
                        pass
                        
                res_id = model_obj.create(cr, uid, values, context=context)
                if xml_id:
                    if model_obj._inherits:
                        for table in model_obj._inherits:
                            inherit_id = model_obj.browse(cr, uid,
                                    res_id,context=context)[model_obj._inherits[table]]
                            self.create(cr, uid, {
                                'name': xml_id + '_' + table.replace('.', '_'),
                                'model': table,
                                'module': module,
                                'res_id': inherit_id.id,
                                'noupdate': noupdate,
                                },context=context)
                    self.create(cr, uid, {
                        'name': xml_id,
                        'model': model,
                        'module': module,
                        'res_id': res_id,
                        'noupdate': noupdate
                        },context=context)
        if xml_id and res_id:
            self.loads[(module, xml_id)] = (model, res_id)
            for table, inherit_field in model_obj._inherits.iteritems():
                inherit_id = model_obj.read(cr, uid, res_id,
                        [inherit_field])[inherit_field]
                self.loads[(module, xml_id + '_' + table.replace('.', '_'))] = (table, inherit_id)
        return res_id

ir_model_data()

class ir_model_fields(osv.osv):
    _inherit = 'ir.model.fields'
    
    def vhr_build_args(self, cr, uid, args, context=None):
        if context is None: context = {}
        new_args = []
        if context.get('get_char'):
            if context['get_char']:
                ir_model = self.pool.get('ir.model')
                model = ir_model.read(cr, uid, context['get_char'], ['model'])['model']
                model = self.pool.get(model)
                model_inherits = [model._name]
                if '_inherit' in dir(model):
                    model_inherits.append(model._inherit)
                for key in model._inherits.keys():
                    model_inherits.append(key)
                new_args.append(('model_id.model','in', model_inherits))
            new_args.append(('ttype', '=', 'char'))
        args = new_args + args
        return args
    
    def search(self, cr, user, args, offset=0, limit=None, order=None, context=None, count=False):
        args = self.vhr_build_args(cr, user, args, context)
        return super(ir_model_fields, self).search(cr, user, args, offset, limit, order, context, count)
    
    def name_search(self, cr, user, name='', args=None, operator='ilike', context=None, limit=100):
        args = self.vhr_build_args(cr, user, args, context)
        return super(ir_model_fields, self).name_search(cr, user, name, args, operator, context, limit)
    
ir_model_fields()