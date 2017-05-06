# -*-coding:utf-8-*-
import logging
from datetime import date, datetime
import time
from openerp import SUPERUSER_ID
from openerp.osv import osv, fields
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from lxml import html,etree
from xml.etree.ElementTree import ElementTree, XML
import re
import unicodedata

log = logging.getLogger(__name__)

patterns = {
    '[àáảãạăắằẵặẳâầấậẫẩ]': 'a',
    '[đ]': 'd',
    '[èéẻẽẹêềếểễệ]': 'e',
    '[ìíỉĩị]': 'i',
    '[òóỏõọôồốổỗộơờớởỡợ]': 'o',
    '[ùúủũụưừứửữự]': 'u',
    '[ỳýỷỹỵ]': 'y'
}


class vhr_post_job(osv.osv):#should name vhr_rr_post_job
    _name = 'vhr.post.job'
    _description = 'VHR Post Job'
    _order = 'date_start desc'
    
    def onchange_job_category_id(self, cr, uid, ids, job_category_id):
        value = {}
        value['vhr_job_id'] = False
        return {'value': value}

    def _get_default_city(self, cr, uid, context=None):
        m = self.pool.get('res.city')
        lst = m.search(cr, uid, ['|', ('code', '=', ' 79.0'), ('code', '=', '79')], context=context)
        if lst:
            return lst[0]
        return False
    
    def _get_default_post_location(self, cr, uid, context=None):
        m = self.pool.get('ir.model.data')
        return [(6, 0, [m.get_object(cr, uid, 'vhr_recruitment', 'post_job_location_to_corporation_site').id])]
    
    def onchange_date(self, cr, uid, ids, date_start, date_end):
        if date_end and date_start:
            time_delta = datetime.strptime(date_end, DEFAULT_SERVER_DATE_FORMAT) - datetime.strptime(date_start,
                                                                                                     DEFAULT_SERVER_DATE_FORMAT)
            day_delta = time_delta.days
            if day_delta < 0:
                warning = {'title': 'User Alert!', 'message': 'Date End must be larger Date Start'}
                return {'value': {'date_end': None}, 'warning': warning}
        return {'value': {}}
    
    def escape(self, strr):
        strr = strr.replace("<", "&lt;")
        strr = strr.replace(">", "&gt;")
        strr = strr.replace("\"", "&quot;")
        strr = strr.replace("&", "&amp;")
        return strr
    
    def format_html(self, contents):
        template_master = '''<w:document xmlns:wpc="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas" xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:wp14="http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:w10="urn:schemas-microsoft-com:office:word" xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml" xmlns:w15="http://schemas.microsoft.com/office/word/2012/wordml" xmlns:wpg="http://schemas.microsoft.com/office/word/2010/wordprocessingGroup" xmlns:wpi="http://schemas.microsoft.com/office/word/2010/wordprocessingInk" xmlns:wne="http://schemas.microsoft.com/office/word/2006/wordml" xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape" mc:Ignorable="w14 w15 wp14">%s</w:document>'''
        template = u'''<w:p><w:pPr><w:pStyle w:val="NoSpacing" /><w:numPr><w:ilvl w:val="0" /><w:numId w:val="4" /></w:numPr><w:spacing w:lineRule="auto" w:line="360" /><w:jc w:val="both" /><w:rPr><w:rFonts w:cs="Arial" w:ascii="Arial" w:hAnsi="Arial" /></w:rPr></w:pPr><w:r><w:rPr><w:rFonts w:cs="Arial" w:ascii="Arial" w:hAnsi="Arial" /></w:rPr><w:t>%s</w:t></w:r></w:p>'''
        result = ""
        contents = contents.split(".");
        for content in contents:
            content = self.escape(content).strip()
            if content:
                content = template%(content)
                result = "%s %s"%(result, content)
        result = template_master%(result)
        return [result]
    
    def action_print_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        report_name = context.get('report_name','rr_jd_template_vn')
        data = self.read(cr, uid, ids, [], context=context)[0]
        if data.get('description',""):
            description = html.document_fromstring(data.get('description',"<li></li>"))
            data['description'] = self.format_html(description.text_content())
            
        if data.get('requirement',""):
            requirement = html.document_fromstring(data.get('requirement',"<li></li>"))
            data['requirement'] = self.format_html(requirement.text_content())
            
        if data.get('requirement_en',""):
            requirement_en = html.document_fromstring(data.get('requirement_en',"<li></li>"))
            data['requirement_en'] = self.format_html(requirement_en.text_content())
        if data.get('requirement_en',""):
            description_en = html.document_fromstring(data.get('description_en',"<li></li>"))
            data['description_en'] = self.format_html(description_en.text_content())
        
        name = 'HRS - %s - %s - VN'%(data.get('code',""),data.get('name',""))
        if report_name=='rr_jd_template_en':
            name = 'HRS - %s - %s - EN'%(data.get('code',""),data.get('name_en',""))
        datas = {
            'ids': ids,
            'model': 'vhr.post.job',
            'form': data
        }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': datas,
            'name': name
        }

    def no_accent_vietnamese(self, s):
        s = s.decode('utf-8')
        s = re.sub(u'Đ', 'D', s)
        s = re.sub(u'đ', 'd', s)
        return unicodedata.normalize('NFKD', unicode(s)).encode('ASCII', 'ignore')

    def _get_hashtag_str(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        job_obj = self.pool.get('vhr.job')
        for item in self.browse(cr, uid, ids, context=context):
            result[item.id] = {'hash_tags_str': '', 'job_categories': [item.vhr_job_id.id]}
            for tag in item.hash_tags:
                if tag.name:
                    result[item.id]['hash_tags_str'] += (self.no_accent_vietnamese(tag.name)).lower().replace(" ", "") + ";"
                    job_cates = job_obj.search(cr, uid, ['|', ('name', 'ilike', tag.name), ('name_en', 'ilike', tag.name)])
                    result[item.id]['job_categories'] += job_cates
                    result[item.id]['job_categories'] = list(set(result[item.id]['job_categories']))
        return result

    _columns = {
        'name': fields.char('Vietnamese Name', size=256),
        'code': fields.char('Code', size=64),
        'name_en': fields.char('English Name', size=256),
        'no_of_recruitment': fields.integer('Quantity'),
        'salary': fields.char('Salary'),
        'salary_en': fields.char('Salary EN'),
        'salary_rank_vn': fields.float('Salary rank(VN)'),
        'salary_rank_en': fields.float('Salary rank(EN)'),
        # post information
        'vhr_job_id': fields.many2one('vhr.job', 'Job type in RR', ondelete='restrict', domain="[('job_category_id','=',job_category_id)]"),
        'job_category_id': fields.many2one('vhr.job.category','Job category', ondelete='restrict'),
        'date_start': fields.date('Start date'),
        'date_end': fields.date('End date'),
        'note': fields.text('Note'),
        # Information for recruitment
        'description': fields.text(u'Mô tả'),
        'requirement': fields.text(u"Yêu Cầu"),
        'preference': fields.text(u"Ưu tiên"),
        'description_en': fields.text('Description'),
        'requirement_en': fields.text("Requirement"),
        'preference_en': fields.text("Preference"),
        # information for postjob
        'post_location_ids': fields.many2many('vhr.post.location', 'post_job_post_location_rel', \
                                              'post_job_id', 'post_location_id', 'Post Locations'),
        'request_job_ids': fields.many2many('hr.job', 'post_job_hr_job_rel', 'post_job_id', 'hr_job_id', 'Request Jobs', \
                                            domain=[('state', '=', 'in_progress')]),
        'active': fields.boolean('Active'),
        'office_id': fields.many2one('vhr.office', 'Office', domain="[('city_id','=',city_id)]"),
        'city_id': fields.many2one('res.city', 'City'),
        'state': fields.selection([('draft', 'Draft'), ('in_progress', 'In progress'), ('done', 'Done')],
                                  string="Status"),
        'audit_log_ids': fields.one2many('audittrail.log.line', 'res_id', 'History', \
                                         domain=[('object_id.model', '=', _name),
                                                 ('field_id.name', 'not in', ['write_date', 'audit_log_ids'])]),
        'job_flags': fields.char('Job Flags'),
        'allow_internal': fields.boolean('Allow Internal'),
        'hash_tags': fields.many2many('hr.applicant_category', string='Hashtag'),
        'hash_tags_str': fields.function(_get_hashtag_str, type='char', string='Hashtag', multi='hashtags'),
        'job_categories': fields.function(_get_hashtag_str, type='char', string='Hashtag', multi='hashtags'),
    }

    _defaults = {
        'active': True,
        'state': 'draft',
        'city_id': _get_default_city,
        'post_location_ids': _get_default_post_location,
        'allow_internal': True,
    }

    def create(self, cr, uid, vals, context=None):
        if 'code' not in vals:
            vals['code'] = self.pool.get('hr.job').generate_code(cr, uid, 'HRS', context=context)
        if context is None: context = {}
        active_id = context.get('hr_job_active_id', False)# change from active_id to hr_job_active_id, lost active_id ???
        if active_id:
            vals['request_job_ids'] = [(6,0,[active_id])]
            #update ngược lại post job
            new_vals = {}
            if 'description'  in vals: new_vals['description'] = vals['description']
            if 'requirement'  in vals: new_vals['requirements'] = vals['requirement']
            if 'preference'   in vals: new_vals['preference'] = vals['preference']
            if 'description_en' in vals: new_vals['description_en'] = vals['description_en']
            if 'requirement_en' in vals: new_vals['requirement_en'] = vals['requirement_en']
            if 'preference_en'  in vals: new_vals['preference_en'] = vals['preference_en']
            self.pool['hr.job'].write(cr, uid, [active_id], new_vals)
        res = super(vhr_post_job, self).create(cr, uid, vals, context=context)
        if vals.get('state') == 'in_progress':
            self.pool.get('vhr.recruitment.interface').notify_change(cr, uid, context=context)
        return res

    def write(self, cr, uid, ids, vals, context=None):
        if not isinstance(ids, list):
            ids = [ids]
        res = super(vhr_post_job, self).write(cr, uid, ids, vals, context=context)
        current_state = self.browse(cr, uid, ids[0], context=context, fields_process=['state']).state
        if vals.get('state') == 'in_progress' or current_state == 'in_progress' or current_state == 'done':
            self.pool.get('vhr.recruitment.interface').notify_change(cr, uid, context=context)
        #update
        lst_job_ids = []
        if 'description' in vals or 'requirement' in vals or 'preference' in vals or \
           'description_en' in vals or 'requirement_en' in vals or 'preference_en'in vals:
            new_vals = {}
            if 'description'  in vals: new_vals['description'] = vals['description']
            if 'requirement'  in vals: new_vals['requirements'] = vals['requirement']
            if 'preference'   in vals: new_vals['preference'] = vals['preference']
            if 'description_en' in vals: new_vals['description_en'] = vals['description_en']
            if 'requirement_en' in vals: new_vals['requirement_en'] = vals['requirement_en']
            if 'preference_en'  in vals: new_vals['preference_en'] = vals['preference_en']
            for post_job_item in self.browse(cr, uid, ids, context=context):
                for job_item in post_job_item.request_job_ids:
                    lst_job_ids.append(job_item.id)   
            if lst_job_ids:
                self.pool['hr.job'].write(cr, uid, lst_job_ids, new_vals)
        return res

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        res = super(vhr_post_job, self).default_get(cr, uid, fields, context=context)
        today = date.today()
        job_title_id = context.get('job_title_id','')
        job_title_name = ''
        if job_title_id:
            job_title_name = self.pool.get('vhr.job.title').browse(cr, uid, job_title_id, context=context).name
        res.update({
            'name': job_title_name,
            'name_en': job_title_name,
            'description': context.get('description', ''),
            'requirement': context.get('requirement', ''),
            'preference': context.get('preference', ''),
            'description_en': context.get('description_en', ''),
            'requirement_en': context.get('requirement_en', ''),
            'preference_en': context.get('preference_en', ''),
            'office_id': context.get('office_id', False),
            'code': context.get('code', False),
            'date_start': today.strftime("%Y-%m-%d"),
            'salary': 'Thỏa thuận',
            'salary_en': 'Agreement' 
        })
        return res
    
    def copy(self, cr, uid, id, default=None, context=None):
        default = {} if default is None else default.copy()
        default.update({
            'code': self.pool.get('hr.job').generate_code(cr, uid, 'HRS', context=context),
            'request_job_ids':[],
            'date_start': date.today().strftime("%Y-%m-%d"),
        })
        return super(vhr_post_job, self).copy(cr, uid, id, default=default, context=context) 
    
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = False
        try:
            for obj in self.browse(cr, uid, ids, context=context):
                if len(obj.request_job_ids) > 0:
                    raise osv.except_osv('Validation Error !',
                                         'You cannot delete the record(s) which reference to others !')
            res = super(vhr_post_job, self).unlink(cr, uid, ids, context)
        except Exception as e:
            log.exception(e)
            raise osv.except_osv('Validation Error !', 'You cannot delete the record(s) which reference to others !')
        # notify change
        self.pool.get('vhr.recruitment.interface').notify_change(cr, uid, context=context)
        return res
    
vhr_post_job()
