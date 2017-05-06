# -*-coding:utf-8-*-
import logging
import re

from openerp.osv import osv, fields


log = logging.getLogger(__name__)


class vhr_mission_collaborator_contract(osv.osv):
    _name = 'vhr.mission.collaborator.contract'
    _description = 'VHR Mission Collaborator Contract'
    
    _columns = {
        'name': fields.char('Name', size=512),
        'contract_id': fields.many2one('hr.contract', 'Contract'),
        'appendix_id': fields.many2one('vhr.appendix.contract', 'Appendix Contract'),

        'value': fields.char('Responsibilities', size=512),
        'salary': fields.integer('Salary'),

        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                         domain=[('object_id.model', '=', _name),
                                                 ('field_id.name', 'not in',
                                                  ['write_date', 'audit_log_ids'])]),
    }
    
    _order = 'name asc, value asc'
    
    
    def name_get(self, cr, uid, ids, context=None):
        if not ids or False in ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        
        reads = self.read(cr, uid, ids, ['name','value'], context=context)
        res = []
        for record in reads:
                name = record.get('name','') or ''
                value = record.get('value','') or ''
                res_name = name + '. ' + value
                res.append((record['id'], res_name))
        return res
    
    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        args_new = [('name', operator, name)] + args
        ids = self.search(cr, uid, args_new)
        if ids:
            return self.name_get(cr, uid, ids, context=context)
        return super(vhr_mission_collaborator_contract, self).name_search(cr, uid, name, args, operator, context, limit)
    
    def create(self, cr, uid, vals, context=None):
        vals = self.create_name_for_record(cr, uid, vals, context)
        res = super(vhr_mission_collaborator_contract, self).create(cr, uid, vals, context)
        
        return res
    
    def create_name_for_record(self, cr, uid, vals, context=None):
        '''
        Because old system vHCS mark priority for result, so we have to set name=?? for priority migration 
        '''
        if not context:
            context = {}
            
        if vals.get('contract_id',False) or vals.get('appendix_id', False):
            contract_id = vals.get('contract_id',False)
            appendix_id = vals.get('appendix_id',False)
            result_ids = []
            if contract_id:
                result_ids = self.search(cr, uid, [('contract_id','=', contract_id)], order='name asc')
            elif appendix_id:
                result_ids = self.search(cr, uid, [('appendix_id','=', appendix_id)], order='name asc')
            
            remove_ids = []
            if context.get('mission_ids', False):
                remove_ids = [data[1] for data in context['mission_ids'] if data[0] == 2]
                
            if remove_ids:
                result_ids = list( set(result_ids).difference(set(remove_ids)))
            if result_ids:
                results = self.read(cr, uid, result_ids, ['name'])
                result_names = [result.get('name',0) or 0 for result in results]
                
                priority_list = [int(re.search(r'\d+', name).group()) for name in result_names]
                priority_list.sort()
                
                missing = set( range( 1, int(priority_list[-1])+1  )  ).difference( set(priority_list) )
                missing = list(missing)
                if missing:
                    vals['name'] = str( missing[0])
                else:
                    vals['name'] = str( int(priority_list[-1]) + 1)
            
            else:
                vals['name'] = '1'
            
            if vals.get('name', False) and context.get('prefix_name_of_mission',False):
                vals['name'] = context['prefix_name_of_mission'] + vals['name']
        
        return vals
    
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_mission_collaborator_contract, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res


vhr_mission_collaborator_contract()