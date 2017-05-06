# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields
from lxml import etree

log = logging.getLogger(__name__)


class vhr_multi_renew_contract_setting(osv.osv):
    _name = 'vhr.multi.renew.contract.setting'
    _description = 'Multi Renew Contract Setting'
    
    
    def _get_person_to_cc(self, cr, uid, ids, field_names, unknow_none, context = None):
        res = {}
        if ids and field_names:
            records = self.browse(cr, uid, ids)
            for record in records:
                res[record.id] = {}
                name1 = record.official_to_type_person_id and record.official_to_type_person_id.name or ''
                name2 = record.official_to_person_id and record.official_to_person_id.login or ''
                
                res[record.id]['official_to_person_fnct'] = ', '.join([name1,name2])
                if not name1 or not name2:
                    res[record.id]['official_to_person_fnct'] = name1 or name2
                
                
                name1 = self.get_employee_name_from_group(cr, uid, record.official_cc_type_person_ids, context)
                name2 = self.get_employee_name_from_group(cr, uid, record.official_cc_person_ids, context)
                res[record.id]['official_cc_person_fnct'] = ', '.join(name1+name2)
                
                
                name1 = record.non_official_to_type_person_id and record.non_official_to_type_person_id.name or ''
                name2 = record.non_official_to_person_id and record.non_official_to_person_id.login or ''
                res[record.id]['non_official_to_person_fnct'] = ', '.join([name1,name2])
                if not name1 or not name2:
                    res[record.id]['non_official_to_person_fnct'] = name1 or name2
                
                
                name1 = self.get_employee_name_from_group(cr, uid, record.non_official_cc_type_person_ids, context)
                name2 = self.get_employee_name_from_group(cr, uid, record.non_official_cc_person_ids, context)
                res[record.id]['non_official_cc_person_fnct'] = ', '.join(name1+name2)
                
                
                #Sub Type Configure
                name1 = record.subtype_non_official_to_type_person_id and record.subtype_non_official_to_type_person_id.name or ''
                name2 = record.subtype_non_official_to_person_id and record.subtype_non_official_to_person_id.login or ''
                res[record.id]['subtype_non_official_to_person_fnct'] = ', '.join([name1,name2])
                if not name1 or not name2:
                    res[record.id]['subtype_non_official_to_person_fnct'] = name1 or name2
                
                name1 = self.get_employee_name_from_group(cr, uid, record.subtype_non_official_cc_type_person_ids, context)
                name2 = self.get_employee_name_from_group(cr, uid, record.subtype_non_official_cc_person_ids, context)
                res[record.id]['subtype_non_official_cc_person_fnct'] = ', '.join(name1+name2)
                
                
        return res
    
        
    _columns = {
        'name': fields.char('Name', size=128),
        'is_team': fields.boolean('Is Team ?'),
        'is_bu': fields.boolean('Is BU ?'),
        'is_department': fields.boolean('Is Department ?'),
        'is_department_group': fields.boolean('Is Department Group ?'),
        'division_id': fields.many2one('hr.department', 'BU', domain=[('organization_class_id.level','=', '1')], ondelete='restrict'),
        'department_group_id': fields.many2one('hr.department', 'Department Group', domain=[('organization_class_id.level','=', '2')], ondelete='restrict'),
        'department_id': fields.many2one('hr.department', 'Department', domain=[('organization_class_id.level','=', '3')], ondelete='restrict'),
        'team_id': fields.many2one('hr.department', 'Team', domain=[('organization_class_id.level','>=', '4')], ondelete='restrict'),
        'official_to_person_fnct': fields.function(_get_person_to_cc, type='char', string='Official To', size=256, multi='get_char'),
        
        'official_to_type_person_id':fields.many2one('vhr.dimension',#'multi_renew_setting_official_to_type','setting_id','person_id','To',
                                                  domain=[('dimension_type_id.code','=', 'PERSON_MULTI_RENEW_CONTRACT')]),
        'official_to_person_id':fields.many2one('hr.employee',#'multi_renew_setting_official_to_emp','setting_id','emp_id',
                                                 'To'),
        
        'official_cc_person_fnct': fields.function(_get_person_to_cc, type='char', string='Official CC', size=256, multi='get_char'),
        'official_cc_type_person_ids':fields.many2many('vhr.dimension','multi_renew_setting_official_cc_type','setting_id','person_id','CC',
                                                  domain=[('dimension_type_id.code','=', 'PERSON_MULTI_RENEW_CONTRACT')]),
        'official_cc_person_ids':fields.many2many('hr.employee','multi_renew_setting_official_cc_emp','setting_id','emp_id','CC'),
                
        'non_official_to_person_fnct': fields.function(_get_person_to_cc, type='char', string='Non Official To', size=256, multi='get_char'),
        'non_official_to_type_person_id':fields.many2one('vhr.dimension',#'multi_renew_setting_non_official_to_type','setting_id','person_id','To',
                                                  domain=[('dimension_type_id.code','=', 'PERSON_MULTI_RENEW_CONTRACT')]),
        'non_official_to_person_id':fields.many2one('hr.employee',#'multi_renew_setting_non_official_to_emp','setting_id','emp_id',
                                                     'To'),
        
        'non_official_cc_person_fnct': fields.function(_get_person_to_cc, type='char', string='Non Official CC', size=256, multi='get_char'),
        'non_official_cc_type_person_ids':fields.many2many('vhr.dimension','multi_renew_setting_non_official_cc_type','setting_id','person_id','CC',
                                                  domain=[('dimension_type_id.code','=', 'PERSON_MULTI_RENEW_CONTRACT')]),
        'non_official_cc_person_ids':fields.many2many('hr.employee','multi_renew_setting_non_official_cc_emp','setting_id','emp_id','To'),
        
        
        'is_sub_type_configure': fields.boolean('Sub Type Configure ?'),
        'subtype_non_official_to_person_fnct': fields.function(_get_person_to_cc, type='char', string='Sub Type Non Official To', size=256, multi='get_char'),
        'subtype_non_official_to_type_person_id':fields.many2one('vhr.dimension',#'multi_renew_setting_non_official_to_type','setting_id','person_id','To',
                                                  domain=[('dimension_type_id.code','=', 'PERSON_MULTI_RENEW_CONTRACT')]),
        'subtype_non_official_to_person_id':fields.many2one('hr.employee',#'multi_renew_setting_non_official_to_emp','setting_id','emp_id',
                                                     'To'),
        
        'subtype_non_official_cc_person_fnct': fields.function(_get_person_to_cc, type='char', string='Sub Type Non Official CC', size=256, multi='get_char'),
        'subtype_non_official_cc_type_person_ids':fields.many2many('vhr.dimension','multi_renew_setting_subtype_non_official_cc_type','setting_id','person_id','CC',
                                                  domain=[('dimension_type_id.code','=', 'PERSON_MULTI_RENEW_CONTRACT')]),
        'subtype_non_official_cc_person_ids':fields.many2many('hr.employee','multi_renew_setting_subtype_non_official_cc_emp','setting_id','emp_id','To'),
        
        
        'active': fields.boolean("Active"),
        'description': fields.text('Description'),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                         domain=[('object_id.model', '=', _name),
                                                 ('field_id.name', 'not in',
                                                  ['write_date', 'audit_log_ids'])]),
    }
    
    _defaults = {
                 'active': True,
                 'is_department': True
                 }
    
    def get_employee_name_from_group(self, cr, uid, datas, context=None):
        if not context:
            context = {}
            
        res = []
        if datas:
            for data in datas:
                if hasattr(data, 'code') and context.get('get_code'):
                    res.append(data.code)
                elif hasattr(data,'login'):
                    res.append(data.login)
                elif hasattr(data,'name'):
                    res.append(data.name)
        
        return res
    
    
    def onchange_is_bu(self, cr, uid, ids, is_bu, context=None):
        res = {}
        if is_bu:
            res = {'department_id': False,'team_id': False,'department_group_id': False,
                   'is_team': False,'is_department': False, 'is_department_group': False}
            
        return {'value': res}
    
    
    def onchange_is_department_group(self, cr, uid, ids, is_bu, context=None):
        res = {}
        if is_bu:
            res = {'department_id': False,'team_id': False,'is_bu': False,
                   'is_team': False,'is_department': False}
        return {'value': res}
    
    def onchange_is_department(self, cr, uid, ids, is_department, context=None):
        res = {}
        if is_department:
            res = {'team_id': False,'is_team': False,
                   'is_bu': False, 'is_department_group': False}
        
        return {'value': res}
    
    def onchange_is_team(self, cr, uid, ids, is_team, context=None):
        res = {}
        if is_team:
            res = {'is_department': False,'is_bu': False, 'is_department_group': False}
        
        return {'value': res}
    
        
    def onchange_official_to_type_person_id(self, cr, uid, ids, official_to_type_person_id, context=None):
        res = {}
        if official_to_type_person_id:
            res = {'official_to_person_id':  False}#[[6, False, []]] }
        
        return {'value': res}
    
    def onchange_official_to_person_id(self, cr, uid, ids, official_to_person_id, context=None):
        res = {}
        if official_to_person_id:
            res = {'official_to_type_person_id': False}#[[6, False, []]] }
        
        return {'value': res}
    
    
    def onchange_non_official_to_type_person_id(self, cr, uid, ids, non_official_to_type_person_id, context=None):
        res = {}
        if non_official_to_type_person_id:
            res = {'non_official_to_person_id':  False}#[[6, False, []]] }
        
        return {'value': res}
    
    def onchange_non_official_to_person_id(self, cr, uid, ids, non_official_to_person_id, context=None):
        res = {}
        if non_official_to_person_id:
            res = {'non_official_to_type_person_id':  False}#[[6, False, []]] }
        
        return {'value': res}
    
    def onchange_is_sub_type_configure(self, cr, uid, ids, is_sub_type_configure, context=None):
        res = {}
        if not is_sub_type_configure:
            res.update({'subtype_non_official_to_person_id': False,
                        'subtype_non_official_to_type_person_id': False,
                        'subtype_non_official_cc_type_person_ids': [(6, False, [])],
                        'subtype_non_official_cc_person_ids': [(6, False, [])]
                        
                        })
        
        return {'value': res}
    
    def onchange_subtype_non_official_to_type_person_id(self, cr, uid, ids, subtype_non_official_to_type_person_id, context=None):
        res = {}
        if subtype_non_official_to_type_person_id:
            res = {'subtype_non_official_to_person_id':  False}#[[6, False, []]] }
        
        return {'value': res}
    
    def onchange_subtype_non_official_to_person_id(self, cr, uid, ids, subtype_non_official_to_person_id, context=None):
        res = {}
        if subtype_non_official_to_person_id:
            res = {'subtype_non_official_to_type_person_id':  False}#[[6, False, []]] }
        
        return {'value': res}
    
    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        args_new = [('name', operator, name)] + args
        ids = self.search(cr, uid, args_new)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(vhr_multi_renew_contract_setting, self).name_search(cr, uid, name, args, operator, context, limit)

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_multi_renew_contract_setting, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res
    
    def fields_view_get(self, cr, uid, view_id = None, view_type = 'form', context = None, toolbar = False, submenu = False):
        res = super(vhr_multi_renew_contract_setting, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar = toolbar, submenu = submenu)
        if context is None:
            context = {}
        if view_type == 'form':
            doc = etree.XML(res['arch'])
            for node in doc.xpath("//field[@name='department_id']"):
                domain = [('organization_class_id.level','=', '3')]
                node.set('domain', str(domain))
                
            res['arch'] = etree.tostring(doc)
            
        return res

vhr_multi_renew_contract_setting()