# -*-coding:utf-8-*-
import logging
from datetime import datetime
from openerp import SUPERUSER_ID

from openerp.osv import osv, fields
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.addons.vhr_common.model.vhr_common import vhr_common

log = logging.getLogger(__name__)


class vhr_personal_document(osv.osv, vhr_common):
    _name = 'vhr.personal.document'
    _description = 'VHR Personal Document'

    _columns = {
        'name': fields.char('Name', size=256),
        'employee_id': fields.many2one('hr.employee', 'Employee'),
        # 'employee_name': fields.related('employee_id', 'name', type="char", string="Employees"),
        # 'employee_login': fields.related('employee_id', 'login', type="char", string="Employee Login"),
        # 'employee_code': fields.related('employee_id', 'code', type="char", string="Employee Code"),

        'department_id': fields.related('employee_id', 'department_id', type='many2one',
                                        relation='hr.department', string='Department'),
        'document_type_id': fields.many2one('vhr.personal.document.type', 'Document Type', ondelete='restrict'),
        'has_expiry_date': fields.related('document_type_id', 'has_expiry_date', type='boolean', readonly=True, string='Has Expiry Date'),
        'number': fields.char('Number', size=64),
        'issue_date': fields.date('Issue Date'),
        'effect_date': fields.date('Effective Date'),#remove in future version, no use anymore
        'expiry_date': fields.date('Expiry Date'),
        'country_id': fields.many2one('res.country', 'Country', ondelete='restrict'),
        'city_id': fields.many2one('res.city', 'City', domain="[('country_id','=',country_id)]", ondelete='restrict'),
        'district_id': fields.many2one('res.district', 'District', domain="[('city_id','=',city_id)]", ondelete='restrict'),
        'note': fields.text('Note'),
        #khong con dung nua, chi còn dùng để lưu dữ liệu của hệ thống cũ

        'status_id': fields.many2one('vhr.personal.document.status', 'Status', ondelete='restrict'),
        'active': fields.boolean('Active'),
        'is_received_hard_copy': fields.boolean('Is Received Hard Copy'),

        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                         domain=[('object_id.model', '=', _name),
                                                 ('field_id.name', 'not in',
                                                  ['write_date', 'audit_log_ids'])]),
    }

    _defaults = {
        'active': True,
        'country_id': lambda self, cr, uid, context:
        self.pool.get('res.country').search(cr, uid, [('code', '=', 'VN')])[0]
    }
    
    _order = "id desc"

    _unique_insensitive_constraints = [{'document_type_id': "Document Type and Number are already exist",
                                        'number': "Document Type and Number are already exist"}]
    
    def _validate(self, cr, uid, ids, context=None, vals=None):
        """
        This function use to check exception in create, write function.

        :param cr:
        :param uid:
        :param ids:
        :param context:
        :return: void but when error appear raise exception.
        """
        if not context:
            context = {}
            
        from openerp.osv.orm import except_orm, Model
        from openerp.tools.translate import _
        
        super(Model, self)._validate(cr, uid, ids, context=context)
        if self._unique_insensitive_constraints:
            for field in self._unique_insensitive_constraints:
                key = field.keys()[0]
                
                context['fields_require_data'] = field.get('validate_mandatory_fields',[])
                if key in vals.keys():
                    dup_ids = self._check_unique_insensitive(cr, uid, ids, field.keys(), self._name, context=context)
                    if dup_ids:
                        employees = ''
                        if 'employee_id' in self._all_columns:
                            dups = self.browse(cr, uid, dup_ids, fields_process=['employee_id'])
                            employees = [dup.employee_id and dup.employee_id.code for dup in dups]
                            employees = list(set(employees))
                            employees = ' - '.join(employees)
                            
                        raise except_orm(_('Validation Error !'),
                                         _('%s: %s \nEmployee Code: %s') % (field[key],vals[key], employees))
    
    def _check_unique_insensitive(self, cr, uid, ids, fields, model, context=None):
        """
        Note: we use =ilike for search character in ignore case sensitive
        We only need search ids[0] because if we have a lot ids but it have same value to write or create.
        That why we only read ids[0]
        Note: If field value = False and field in 'validate_mandatory_fields' ==> return []
        :param cr:
        :param uid:
        :param ids:
        :param field:
        :param model:
        :param context:
        :return: [ids] if more than 1 record have same field value found or True if not.
        """
        if not context:
            context = {}
        model_obj = self.pool.get(model)
        sr_ids = []
        context.update({'active_test': False})
        if ids and len(fields) > 0:
            args = []
            fields_require_data = context.get('fields_require_data',[])

            for fld in fields:
                if fld == 'validate_mandatory_fields':
                    continue
                
                opr = '=ilike'
                value = model_obj.read(cr, SUPERUSER_ID, ids[0], [fld], context=context)[fld]
                if self._all_columns[fld].column._type not in ['char', 'text']:
                    opr = '='
                    if isinstance(value, tuple):
                        value = value[0]
                args += [(fld, opr, value)]
                
                #If value of field = False and this field in fields_require_data==> do not check anymore, return True
                if value == False and fld in fields_require_data:
                    return sr_ids
            if ids:
                args.append(('id', 'not in', ids))
            if args:
                sr_ids = model_obj._search(cr, SUPERUSER_ID, args, context=context)
        return sr_ids
    
    
                        
    def read(self, cr, user, ids, fields=None, context=None, load='_classic_read'):
        if not context:
            context = {}
        
        self.prevent_normal_emp_read_data_of_other_emp(cr, user, ids, [], [], [], context=context)
        
        res =  super(vhr_personal_document, self).read(cr, user, ids, fields, context, load)
            
        return res
    
    def name_get(self, cr, uid, ids, context=None):
        if not ids or False in ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        helth_cares = self.read(cr, uid, ids, ['employee_id'], context=context)
        res = []
        for helth_care in helth_cares:
            if helth_care.get('employee_id', False):
                name = helth_care['employee_id'][1]
                res.append((helth_care['id'], name))
        return res

    def onchange_document_type_id(self, cr, uid, ids, document_type_id, context=None):
        if context is None:
            context = {}
        value = {
            'expiry_date': False,
            'state': '',
            'has_expiry_date': False,
        }
        if document_type_id:
            document_type_data = self.pool['vhr.personal.document.type'].read(cr, uid, document_type_id, ['has_expiry_date'], context=context)
            value.update({'has_expiry_date': document_type_data.get('has_expiry_date', False)})
        return {'value': value}


    def onchange_employee_id(self, cr, uid, ids, employee_id, context=None):
        res = {}
        if employee_id:
            employee = self.pool.get('hr.employee').read(cr, uid, employee_id, ['department_id'])
            department_id = employee.get('department_id', False)
            res['department_id'] = department_id and department_id[0] or False

        return {'value': res}

    def compare_date(self, cr, uid, first_date, second_date, res, context={}):
        if first_date and second_date:
            time_delta = datetime.strptime(second_date, DEFAULT_SERVER_DATE_FORMAT) - datetime.strptime(first_date,
                                                                                                        DEFAULT_SERVER_DATE_FORMAT)
            day_delta = time_delta.days
            if day_delta < 0:
                res['expiry_date'] = False
                warning = {'title': 'User Alert!', 'message': '%s Date must be greater than or equal to %s Date' % (
                    context.get('second', ''), context.get('first', ''))}
                return {'value': res, 'warning': warning}
        return {}

    # Condition: issue_date <=  effect_date <= expire_date
    def onchange_date(self, cr, uid, ids, issue_date, effect_date, expire_date):
        result = {'value': {}}
#         if issue_date and not effect_date:
#             result['value']['effect_date'] = issue_date
#         if issue_date and effect_date:
#             res = {'effect_date': None}
#             result = self.compare_date(cr, uid, issue_date, effect_date, res, {'first': 'Issue', 'second': 'Effective'})
#             if result:
#                 return result

        if issue_date and expire_date:
            res = {'expire_date': None}
            result = self.compare_date(cr, uid, issue_date, expire_date, res,
                                       {'first': 'Issue', 'second': 'Expiry'})
            if result:
                return result

        return result

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if not context:
            context = {}

        return super(vhr_personal_document, self).search(cr, uid, args, offset, limit, order, context, count)

    def check_overlap(self, cr, uid, employee_id, document_type_id, issue_date, expiry_date, ids=[]):
        
        if not isinstance(ids, list):
            ids = [ids]
            
        if employee_id and document_type_id and issue_date:
            
            args = [('employee_id', '=', employee_id),
                    ('document_type_id','=',document_type_id),
                   '|', ('active', '=', False),
                        ('active', '=', True)]

            document_ids = self.search(cr, uid, args)

            if not document_ids:
                return True

            not_overlap_args = [('expiry_date', '<', issue_date)] + args
            if expiry_date:
                not_overlap_args.insert(0, '|')
                not_overlap_args.insert(1, ('issue_date', '>', expiry_date))

            not_overlap_document_ids = self.search(cr, uid, not_overlap_args)
            #If leng document_ids == length not_verlap_document_ids ---> dont have any overlap document
            if len(document_ids) == len(not_overlap_document_ids):
                return True
            else:
                #Get records from document_ids not in not_overlap_document_ids
                overlap_ids = [x for x in document_ids if x not in not_overlap_document_ids]
                #Get records from document_ids are not working_id
                overlap_ids = [x for x in overlap_ids if x not in ids]
                if overlap_ids:
                    document_type_name = self.pool.get('vhr.personal.document.type').read(cr, uid, document_type_id, ['name'])
                    document_type_name = document_type_name and document_type_name['name'] or ''
                    raise osv.except_osv('Personal Document Validation Error !',
                                         'The effective duration (Issue date- Expiry date) of %s is overlapped!' % (document_type_name))
            
        return True

    def create(self, cr, uid, vals, context=None):
        if not context:
            context = {}
            
        res = super(vhr_personal_document, self).create(cr, uid, vals, context=context)
        if vals.get('document_type_id') and \
                vals.get('employee_id') and \
                vals.get('issue_date') and \
                vals.get('expiry_date'):
            employee_id = vals['employee_id']
            document_type_id = vals['document_type_id']
            issue_date = vals['issue_date']
            expiry_date = vals['expiry_date']
            
            if not context.get('do_not_check_overlap_personal_document', False):
                self.check_overlap(cr, uid, employee_id, document_type_id, issue_date, expiry_date, ids=[res])
        return res

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
            
        res = super(vhr_personal_document, self).write(cr, uid, ids, vals, context=context)
        
        if not context.get('do_not_check_overlap_personal_document'):
            issue_date = False
            data = self.read(cr, uid, ids[0], ['employee_id', 'document_type_id', 'effect_date','expiry_date','issue_date'])
            if vals.get('employee_id'):
                employee_id = vals['employee_id']
            else:
                employee_id = data.get('employee_id') and data['employee_id'][0]
            if vals.get('document_type_id'):
                document_type_id = vals['document_type_id']
            else:
                document_type_id = data.get('document_type_id') and data['document_type_id'][0]
            if vals.get('issue_date'):
                issue_date = vals['issue_date']
            else:
                issue_date = data['issue_date']
            
            expiry_date = vals.get('expiry_date',data.get('expiry_date',False))
            
            if employee_id and document_type_id and issue_date:
                self.check_overlap(cr, uid, employee_id, document_type_id, issue_date, expiry_date, ids=ids)
        return res


    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_personal_document, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res


vhr_personal_document()