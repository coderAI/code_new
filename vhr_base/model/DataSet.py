# -*-coding:utf-8-*-
import logging

import openerp

from openerp import http
from openerp.addons.web.controllers.main import DataSet
from openerp.http import request
from openerp.addons.audittrail import audittrail
from openerp import SUPERUSER_ID
from openerp.addons.vhr_base.model.base.ir_cron import str2tuple
from openerp.osv.orm import except_orm

log = logging.getLogger(__name__)


model_validate_read = ['vhr.working.record','hr.employee','hr.contract','vhr.termination.request',
                       'vhr.appendix.contract','vhr.employee.assessment.result','hr.department',
                       'vhr.exit.checklist.request','hr.holidays','vhr.ts.overtime','vhr.pr.salary',
                       'vhr.multi.renew.contract']

class DataSet(DataSet):
    
    @http.route('/web/dataset/load', type='json', auth="user")
    def load(self, model, id, fields):
        m = request.session.model(model)
        value = {}
            
        if model in model_validate_read:
            context_name = 'validate_read_' + model.replace('.','_')
            if context_name not in request.context:
                 request.context[context_name] = True
                     
        r = m.read([id], False, request.context)
        if r:
            value = r[0]
        return {'value': value}
    
    def do_search_read(self, model, fields=False, offset=0, limit=False, domain=None , sort=None):
        if model in model_validate_read:
            context_name = 'validate_read_' + model.replace('.','_')
            if context_name not in request.context:
                 request.context[context_name] = True
                 request.context['force_search_' +model.replace('.','_')] = True
        
        return super(DataSet, self).do_search_read(model, fields, offset, limit, domain, sort)
        
        
    def _call_kw(self, model, method, args, kwargs):
        if method in ('copy_data',) and kwargs.get('context', {}).get('future_display_name'):
            self.add_context_to_call_model_method(model, method, kwargs)
            
        # Temporary implements future display_name special field for model#read()
        if method in ('read', 'search_read') and kwargs.get('context', {}).get('future_display_name'):
            self.add_context_to_call_model_method(model, method, kwargs)
            if 'display_name' in args[1]:
                if method == 'read':
                    names = dict(request.session.model(model).name_get(args[0], **kwargs))
                else:
                    names = dict(request.session.model(model).name_search('', args[0], **kwargs))
                args[1].remove('display_name')
                records = getattr(request.session.model(model), method)(*args, **kwargs)
                for record in records:
                    record['display_name'] = \
                        names.get(record['id']) or "{0}#{1}".format(model, (record['id']))
                return records

        if method.startswith('_'):
            raise Exception("Access Denied: Underscore prefixed methods cannot be remotely called")

        cr = request.cr
        uid = request.uid
        if audittrail.check_rules(cr, uid, model, method):
            try:
                pool = openerp.registry(cr.dbname)
                audit_rule_obj = pool.get('audittrail.rule')
                rule_ids = audit_rule_obj.search(cr, SUPERUSER_ID,
                                                 [('object_id', '=', model), ('state', '=', 'subscribed')])
                if rule_ids:
                    data = audit_rule_obj.read(cr, SUPERUSER_ID, rule_ids[0],
                                               ['execute_parameter', 'execute_function', 'execute_obj_id'])
                    if data['execute_obj_id'] and data['execute_function']:
                        logging.info("audit_rule_execute_action %s" % data)
                        ex_args = str2tuple(data['execute_parameter'])
                        execute_model = pool.get(data['execute_obj_id'][1])
                        if execute_model and hasattr(execute_model, data['execute_function']):
                            ex_method = getattr(execute_model, data['execute_function'])
                            ex_method(cr, uid, *ex_args)
            except Exception, e:
                logging.exception("audit_rule_execute_action Exception %s" % e.message)

            fct_src = openerp.service.model.execute_cr
            return audittrail.log_fct(cr, uid, model, method, fct_src, *args, **kwargs)

        return getattr(request.registry.get(model), method)(cr, uid, *args, **kwargs)
    
    
    def add_context_to_call_model_method(self, model, method, kwargs):
        if not kwargs.get('context', {}):
            kwargs['context'] = {}
        if method in ['read','copy_data']:
            if model in model_validate_read:
                context_name = 'validate_read_' + model.replace('.','_')
                if context_name not in kwargs['context']:
                     kwargs['context'][context_name] = True
            
        
        return kwargs


DataSet()


def execute_cr(cr, uid, obj, method, *args, **kw):
    object = openerp.registry(cr.dbname).get(obj)
    if not object:
        raise except_orm('Object Error', "Object %s doesn't exist" % obj)
    
    if method == 'read':
        if not kw.get('context', {}):
            kw['context'] = {}
        if obj in model_validate_read:
            context_name = 'validate_read_' + obj.replace('.','_')
            if context_name not in kw['context']:
                 kw['context'][context_name] = True
                     
    return getattr(object, method)(cr, uid, *args, **kw)

openerp.service.model.execute_cr  = execute_cr
