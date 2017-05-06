# -*-coding:utf-8-*-
import logging
from openerp.osv import osv, fields
from vhr_recruitment_abstract import vhr_recruitment_abstract, HRBP, RECRUITER, COLLABORATER, CANDB_ROLE, COLLABORATER2, RRHRBP
from datetime import date, datetime

log = logging.getLogger(__name__)

HR_APPLICANT = 'hr.applicant'
HR_TEMP_APPLICANT = 'vhr.temp.applicant'


class ir_attachment(osv.osv, vhr_recruitment_abstract): # not used hrs osv at here used original osv
    _name = 'ir.attachment'
    _inherit = "ir.attachment"
    
    def _data_get(self, cr, uid, ids, name, arg, context=None):
        if context is None:
            context = {}
        result = {}
        bin_size = context.get('bin_size')
        for attach in self.browse(cr, uid, ids, context=context):
            if attach.store_fname:
                result[attach.id] = self._file_read(cr, uid, attach.store_fname, bin_size)
            else:
                result[attach.id] = attach.db_datas
        return result
    
    def _data_set(self, cr, uid, id, name, value, arg, context=None):
        # We dont handle setting data to null
        if not value:
            return True
        if context is None:
            context = {}
        location = self._storage(cr, uid, context)
        file_size = len(value.decode('base64'))
        attach = self.browse(cr, uid, id, context=context)
        if attach.store_fname:
            self._file_delete(cr, uid, attach.store_fname)
        if location != 'db':
            fname = self._file_write(cr, uid, value)
            # SUPERUSER_ID as probably don't have write access, trigger during create
            super(ir_attachment, self).write(cr, uid, [id], {'store_fname': fname, 'file_size': file_size, 'db_datas': False}, context=context)
        else:
            super(ir_attachment, self).write(cr, uid, [id], {'db_datas': value, 'file_size': file_size, 'store_fname': False}, context=context)
        return True
    
    _columns = {
        'is_main': fields.boolean('Is main'),
        'datas': fields.function(_data_get, fnct_inv=_data_set, string='File Content', type="binary", nodrop=True),
    }

    _defaults = {
        'is_main': True
        }

    def write(self, cr, uid, ids, vals, context=None):
        # TODO: process before updating resource
        res = super(ir_attachment, self).write(cr, uid, ids, vals, context)
        return res

    def create(self, cr, uid, vals, context=None):
        if vals and vals.get('res_model', '') == HR_TEMP_APPLICANT:
            vals['is_main'] = False
        
        if vals.get('res_model', '') == HR_APPLICANT or vals.get('res_model', '') == HR_TEMP_APPLICANT:
            is_allow = self.is_allow_to_read_attachment_in_applicant(cr, uid)
            if not is_allow:
                raise osv.except_osv('Create/Upload File Error !', "You don't have permission to do this action !")
            
        id_new = super(ir_attachment, self).create(cr, uid, vals, context)
        current_res_id = vals.get('res_id', False)
        
        if vals and current_res_id and (vals.get('res_model', '') == HR_APPLICANT or vals.get('res_model', '') == HR_TEMP_APPLICANT):
            index_content = self.browse(cr, uid, id_new, context=context).index_content
            applicant_obj = self.pool.get('hr.applicant')
            if index_content and len(index_content)>50:
                categ_ids = applicant_obj.get_applicant_skill(cr, uid, index_content)
                vals_update={'description': index_content, 'categ_ids': [[6, 0, categ_ids]]}
                if vals.get('res_model', '') == HR_APPLICANT:
                    applicant_obj .write(cr, uid, [current_res_id], vals_update)
                else:
                    temp_app_obj = self.pool.get('vhr.temp.applicant')
                    temp_app_obj.write(cr, uid, [current_res_id], {'index_content': index_content})                    
                    applicant = temp_app_obj.browse(cr, uid, current_res_id, context=context).applicant_id
                    if applicant:
                        applicant_obj.write(cr, uid, [applicant.id], vals_update)
        return id_new

    def validate_read(self, cr, uid, ids, context=None):  # implement
        """
           - ADMIN, MANAGER, RECRUITER, HRBP, C&B, COLOBORATOR
           - APPLICANT: Field cv_ids trong Applicant
           - CAND_INTERVIEW : Màn hình Candidate request
           - FROM_VIEW : APPLICANT: view applicant - JOB : view job           
        """
        if context is None:
            context = {}
#         if context.get('do_not_validate_read_attachment', False):
#             return True
        if uid == 1:
            return True
        log.info('validate_read : %s'%(uid))
        if not isinstance(ids, list):
            ids = [ids]
        if context.get('FROM_VIEW') and context.get('FROM_VIEW')=="APPLICANT":
            return True
        roles = self.recruitment_get_group_array(cr, uid, uid, context)
        
        lst_applicant = []
        for item in super(ir_attachment, self).read(cr, uid, ids, ['res_model', 'res_id']):
            if item['res_model']=='hr.applicant':
                lst_applicant.append(item['res_id'])
                
        if not lst_applicant and (CANDB_ROLE in roles or RECRUITER in roles or HRBP in roles or COLLABORATER in roles or COLLABORATER2 in roles or RRHRBP in roles):
            return True
        
        if lst_applicant:
            allow_groups = self.pool.get('ir.config_parameter').get_param(cr, uid, 
                                                                         'rr_recruitment_group_read_cv_in_applicant') or ''
            if not allow_groups:
                return self.pool['hr.applicant'].check_read_access(cr, uid, lst_applicant, context)
            elif allow_groups:
                allow_groups = [int(item) for item in allow_groups.split(',')]
                if set(allow_groups).intersection(roles):
                    return True
                else:
                    return False
                
        return True

    def read(self, cr, user, ids, fields=None, context=None, load='_classic_read'):
        if context is None:
            context = {}
        
        try:
            if not context.get('do_not_validate_read_attachment', False):
                result_check = self.check_read_access(cr, user, ids, context)
                if not result_check:
                    raise osv.except_osv('Validation Error !', 'You don’t have permission to access this data !')
            result = super(ir_attachment, self).read(cr, user, ids, fields, context, load='_classic_read')
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Read File Error !', 'File not exist or Permission deny on server!')
        return result
    
    def is_allow_to_read_attachment_in_applicant(self, cr, uid, context = None):
        allow_groups = self.pool.get('ir.config_parameter').get_param(cr, uid,'rr_recruitment_group_read_cv_in_applicant') or ''
        # allow admin and user odoo_esb
        if allow_groups and uid not in [1, 5]:
            allow_groups = [int(item) for item in allow_groups.split(',')]
            
            roles = self.recruitment_get_group_array(cr, uid, uid, context)
            if not (set(allow_groups).intersection(roles)):
                return False
        
        return True

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context = {}
        
        data = ['res_model','=','hr.applicant']
        str_args = str(args).replace('(','[').replace(')',']')
        if str(data) in str_args and uid != 1:
            is_allow = self.is_allow_to_read_attachment_in_applicant(cr, uid)
            if not is_allow:
                return []
                
        return super(ir_attachment, self).search(cr, uid, args, offset, limit, order, context, count)
ir_attachment()
