# -*-coding:utf-8-*-
import logging
from openerp.osv import osv, fields
from datetime import date, datetime
from openerp import SUPERUSER_ID

log = logging.getLogger(__name__)


class ir_attachment(osv.osv):
    _name = 'ir.attachment'
    _inherit = "ir.attachment"

    _columns = {
        'attach_note': fields.char('Attach Note', size=128),
    }
    
    def read(self, cr, user, ids, fields=None, context=None, load='_classic_read'):
        if not context:
            context = {}
            
        result_check = self.check_read_access_hr_ts(cr, user, ids, fields, context)
        if not result_check:
            raise osv.except_osv('Validation Error !', 'You don’t have permission to access this data !')
        elif result_check:
            context['do_not_validate_read_attachment'] = True
        res = super(ir_attachment, self).read(cr, user, ids, fields, context, load)

        return res
    
    def check_read_access_hr_ts(self, cr, uid, ids, fields, context=None):
        # config đảm bảo các bản lên build tiếp theo chạy ổn định trong quá trình validate data cua 1 so model trong human resource
        # Nếu validate lỗi thì tắt validate đảm bảo bussiness ko bị gián đoạn
        if not context:
            context = {}
        run_validate_read = self.pool.get('ir.config_parameter').get_param(cr, SUPERUSER_ID, 'vhr_human_resource_run_validate_read')
        if run_validate_read and int(run_validate_read) and not context.get('do_not_validate_read_hr_ts',False):
            return self.validate_read_hr_ts(cr, uid, ids, fields, context)
        
        return True    
    
    def validate_read_hr_ts(self, cr, uid, ids, fields, context=None):  # implement
        log.info('validate_read : %s'%(uid))
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]
        
        #Get list model of attachment [model1,model2]
        models = []
        for item in super(ir_attachment, self).read(cr, uid, ids, ['res_model'], context={'do_not_validate_read_attachment': True}):
            model = item.get('res_model','')
            model = 'model_' + model.replace('.','_')
            if model not in models:
                models.append(model)
        
        if models:
            for model in models:
                model_id = self.pool.get('ir.model.data').search(cr, uid,  [('name','=',model),
                                                                            ('module','in',['vhr_human_resource','vhr_timesheet']),
                                                                            ('model','=','ir.model')])
                if model_id:
                    if item.get('res_model','') in ['vhr.working.record','vhr.mass.movement']:
                        return self.validate_read_attachment_staff_movement(cr, uid, ids, item['res_model'],fields, context)
                    
                    log.info('validate_read success')
                    return True
                
        return True
    
    def validate_read_attachment_staff_movement(self, cr, uid, ids, model, fields, context=None):
        """
        Nếu vừa thay đổi phòng ban vừa điều chỉnh lương thì old HRBP, old assistant, old dept head chỉ được thấy file đính kèm ở bước 1
        
        - Nếu vừa chuyển phòng ban + vừa thay đổi lương: 
    + Old Assistant/Old HRBP/Old DH xem được thông tin trên eform (ẩn trường "mức lương") + file đính kèm ở bước (1), không xem được file đính kèm ở bước (2).
    
        """
        if ids and 'datas' in fields:
            wr_obj = self.pool.get(model)
            
            for attachment in super(ir_attachment, self).read(cr, uid, ids, ['res_id','attach_note']):
                wr_id = attachment.get('res_id', False)
                wr_state = attachment.get('attach_note',False)
                if wr_id and wr_state:
                    record = wr_obj.read(cr, uid, wr_id, ['invisible_change_salary'])
                    #Dựa vào field invisible_change_salary để xác định
                    if record.get('invisible_change_salary') and wr_state != 'draft':
                        return False
        
        return True
    
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        #Search rule in staff movement
        if not context:
            context = {}
        
        if context.get('dont_show_created_attachment', False):
            args.append(('id','in',[]))
        res =  super(ir_attachment, self).search(cr, uid, args, offset, limit, order, context, count)
        return res
    
    def create(self, cr, uid, vals, context=None):
        if not context:
            context = {}
            
        if not vals.get('name', False) and vals.get('datas_fname', False):
            vals['name'] = vals['datas_fname']
        
        if vals.get('res_model',False) in ['vhr.working.record','vhr.mass.movement','vhr.termination.request'] and vals.get('res_id', False):
            record = self.pool.get(vals['res_model']).read(cr, uid, vals['res_id'], ['state'])
            vals['attach_note'] = record.get('state', False)
            
        id_new = super(ir_attachment, self).create(cr, uid, vals, context)
        return id_new
    
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            #Neu attachment gan toi working record, mass movement, termination chi cho xoa khi WR tai state gan attachment
            for attachment in self.read(cr, uid, ids, ['res_model','attach_note','res_id']):
                if attachment.get('res_model', False) in ['vhr.working.record','vhr.mass.movement','vhr.termination.request'] and attachment.get('res_id', False):
                    wr_record = self.pool.get(attachment['res_model']).read(cr, uid, attachment['res_id'], ['state'])
                    if attachment.get('attach_note', False) and attachment['attach_note'] != wr_record.get('state', False):
                        raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
                    
            res = super(ir_attachment, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            error_message = ''
            try:
                error_message = e.message
                if not error_message:
                    error_message = e.value
            except:
                error_message = ""
            raise osv.except_osv('Validation Error !', 'Have error during delete attachment(s):\n %s' % error_message)
        return res

ir_attachment()
