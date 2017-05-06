# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields
from lxml import etree
import simplejson as json

log = logging.getLogger(__name__)

class vhr_erp_bonus_rate_by_dept(osv.osv):
    _name = 'vhr.erp.bonus.rate.by.dept'
    _description = 'VHR ERP Bonus Rate By Dept'

    _columns = {
        'erp_bonus_id': fields.many2one('vhr.erp.bonus.scheme','Bonus Scheme', ondelete='restrict'),
        'department_id': fields.many2one('hr.department', 'Department',
                                         domain="[('organization_class_id.level','in',[3,6])]", ondelete='restrict',),
        'job_title_ids': fields.many2many('vhr.job.title', 'erp_bonus_job_title_rel', 'bonus_id',
                                                       'title_id', 'Job titles'), 
        'rate': fields.integer('Rate'),
        'from_date': fields.date('From Date'),
        'to_date': fields.date('To Date'),
        'description': fields.text('Description'),
        'active': fields.boolean('Active'),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'Logs',
                                         domain=[('object_id.model', '=', _name),
                                                 ('field_id.name', 'not in', ['write_date', 'audit_log_ids'])]),
    }

    _defaults = {
        'active': True,
    }

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if context is None:
            context = {}
        res = super(vhr_erp_bonus_rate_by_dept, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar=toolbar, submenu=submenu)
        if view_type == 'form':
            if context.get('job_level_id'):
                doc = etree.XML(res['arch'])
                job_title_ids = []
                title_level_ids = self.pool.get('vhr.jobtitle.joblevel').search(cr, uid, [('job_level_id', '=', context.get('job_level_id'))], context=context)
                if title_level_ids:
                    title_level_infos = self.pool.get('vhr.jobtitle.joblevel').read(cr, uid, title_level_ids, ['job_title_id'], context=context)
                    for title_level_info in title_level_infos:
                        if title_level_info.get('job_title_id', False):
                            job_title_ids.append(title_level_info['job_title_id'][0])
                for node in doc.xpath("//field[@name='job_title_ids']"):
                    node.set('domain', "[('id', 'in', "+ str(job_title_ids)+")]")
                    #node.set('domain', json.dumps(domain))
                res['arch'] = etree.tostring(doc)
        return res

    def get_bonus_rate(self, cr, uid, erp_bonus_id, department_code, job_title_id=None, context=None):
        result = 1
        domain = [('erp_bonus_id', '=', erp_bonus_id), ('department_id.code', '=', department_code), ('active', '=', True)]
        lst_rate = self.search(cr, uid, domain, context=context)
        if lst_rate:
            for brbd in self.browse(cr, uid, lst_rate, context=context):
                if brbd.job_title_ids:
                    for title in brbd.job_title_ids:
                        if title.id == job_title_id:
                            result = brbd.rate
                            break
                else:
                    result = self.browse(cr, uid, brbd.id, context=context).rate
        return result

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            res = super(vhr_erp_bonus_rate_by_dept, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        return res

vhr_erp_bonus_rate_by_dept()
