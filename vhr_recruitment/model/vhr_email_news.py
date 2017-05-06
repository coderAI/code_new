# -*-coding:utf-8-*-
import logging

from openerp.osv import osv, fields
from dateutil.relativedelta import relativedelta
from datetime import datetime
from vhr_recruitment_abstract import vhr_recruitment_abstract
from vhr_applicant import OPENING, PROCESSING, OFFERED, EMPLOYEE, BLACKLIST
import openerp

log = logging.getLogger(__name__)

PROGRAM_DIMENSION_DOMAIN = [('dimension_type_id.code', '=', 'DND_PROGRAM'), ('active', '=', True)]

MISS_DATA = 'Name or email is missing'
DUPLICATE_DATA = 'The email was duplicated'

class vhr_email_news(osv.osv, vhr_recruitment_abstract):
    _name = 'vhr.email.news'
    _description = 'VHR Email News'

    def _is_active(self, cr, uid, ids, field_name, arg, context=None):
        if context is None:
            context = {}
        res = {}
        email_subcribes = self.browse(cr, uid, ids, context=context)
        for e in email_subcribes:
            res[e.id] = True
            if e.candidate_id:
                res[e.id] = e.candidate_id.state == OPENING
        return res

    def _set_active(self, cr, uid, email_new_id, field_name, value, args=None, context=None):
        if context is None:
            context = {}
        email_new = self.browse(cr, uid, email_new_id, context=context)
        if not email_new.candidate_id:
            sql = """
            UPDATE vhr_email_news
            SET active = %s
            WHERE id = %s;
            """ % (value, email_new_id)
            cr.execute(sql)
        return True

    def _get_email_subcribes_from_candidates(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        email_subcribes_ids = self.pool['vhr.email.news'].search(cr, uid, [('candidate_id', 'in', ids)], context=context)
        return email_subcribes_ids

    _columns = {
        'create_uid': fields.many2one('res.users', 'Created By', readonly=True),
        'create_date': fields.datetime('Creation Date', readonly=True),
        'write_date': fields.datetime('Write Date', readonly=True),
        'name': fields.char('Name', size=128),
        'email': fields.char('Email', size=128),
        'description': fields.text('Description'),
        'candidate_id': fields.many2one('hr.applicant', 'Candidate', readonly=True),
        'active': fields.function(_is_active, type="boolean", string="Active", fnct_inv=_set_active,
                                  store={
                                    'vhr.email.news': (lambda self, cr, uid, ids, context=None: ids, ['candidate_id'], 1),
                                    'hr.applicant': (_get_email_subcribes_from_candidates, ['state'], 2),
                                  }),

        'is_unsubcribes': fields.boolean('Unsubcribes'),
        'program_type_ids': fields.many2many('vhr.dimension', 'email_news_programs_rel', 'email_id', 'program_id',
                                             'Email Program Types', domain=PROGRAM_DIMENSION_DOMAIN),
        'job_track_ids': fields.many2many('vhr.applicant.job.track', 'job_track_vhr_email_news_rel', 'vhr_email_news_id',
                                          'job_track_id', 'Job Track'),
        # ex : RR news or Student news

    }

    _defaults = {
        'active': True,
        'is_unsubcribes': False
    }

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        res = super(vhr_email_news, self).write(cr, uid, ids, vals, context=context)
        # Update job tracks of related candidates
        if not context.get('candidate_update', False) and vals.get('candidate_id', False) or vals.get('job_track_ids',
                                                                                                      False):
            ctx = context.copy()
            ctx.update({'subcribes_update': True})
            email_news = self.browse(cr, uid, ids, context=ctx)
            hr_applicant_pool = self.pool['hr.applicant']
            for vhr_email_new in email_news:
                if vhr_email_new.candidate_id:
                    job_track_ids = [job_track.id for job_track in vhr_email_new.job_track_ids]
                    hr_applicant_pool.write(cr, uid, [vhr_email_new.candidate_id.id],
                                            {'job_track_ids': [(6, False, job_track_ids)]}, context=ctx)
        return res

    def get_confirm_url(self, cr, uid, res_id, context=None):
        if isinstance(res_id, list):
            res_id = res_id[0]
        confirm_url = self.pool.get('ir.config_parameter').get_param(cr, uid, 'hrs.recruitment.site.confirm.url')
        email = self.browse(cr, uid, res_id).email
        str_encode = 'email=%s&id=%s'%(email,res_id)
        str_encode = str_encode.encode('base64', 'strict')
        confirm_url = '%s%s' % (confirm_url, str_encode)
        return confirm_url

    def get_end_date_confirm(self, cr, uid, res_id, context=None):
        if isinstance(res_id, list):
            res_id = res_id[0]
        write_date = self.browse(cr, uid, res_id).write_date
        write_date = datetime.strptime(write_date, '%Y-%m-%d %H:%M:%S')
        end_date = write_date + relativedelta(days = 2)
        end_date = end_date.strftime('%H:%M:%S %d-%m-%Y')
        return end_date

    def get_program_name(self, cr, uid, res_id, context=None):
        if isinstance(res_id, list):
            res_id = res_id[0]
        program_type_ids = self.browse(cr, uid, res_id).program_type_ids
        result = [program.name for program in program_type_ids if program.code !='CANDIDATE']
        result = ", ".join(result)
        return result

    def thread_import_email_subcribes(self, cr, uid, import_status_id, rows, context=None):
        if context is None:
            context = {}
        log.info('Begin: thread_import_email_subcribes')
        import_obj = self.pool.get('vhr.import.status')
        try:
            job_track_pool = self.pool['vhr.applicant.job.track']
            detail_obj = self.pool['vhr.import.detail']
            db = openerp.sql_db.db_connect(cr.dbname)
            cr = db.cursor()
            import_obj.write(cr, uid, [import_status_id],
                             {'state': 'processing', 'num_of_rows': rows.nrows, 'current_row': 0})
            cr.commit()
            row_counter = 0
            success_row = 0
            for row in rows._cell_values:
                row_counter += 1
                if row_counter > 2:
                    vals_detail = {}
                    name, email, job_track_names = row[0:3]
                    if name and email:
                        email_subcribes_ids = self.search(cr, uid, [('email', '=', email)], context=context)
                        if not email_subcribes_ids:
                            job_track_ids = []
                            if job_track_names:
                                job_track_names = job_track_names.split(',')
                                job_track_ids = job_track_pool.search(cr, uid, [('name', 'in', job_track_names)], context=context)
                            vals = {
                                'name': name,
                                'email': email,
                                'job_track_ids': [(6, False, job_track_ids)]
                            }
                            self.create(cr, uid, vals, context=context)
                            success_row = success_row + 1
                        else:
                            vals_detail = {'import_id': import_status_id, 'row_number': row_counter, 'message': DUPLICATE_DATA}
                    else:
                        vals_detail = {'import_id': import_status_id, 'row_number': row_counter, 'message': MISS_DATA}
                    if vals_detail:
                        detail_obj.create(cr, uid, vals_detail)
                        cr.commit()
                import_obj.write(cr, uid, [import_status_id], {'current_row': row_counter, 'success_row': success_row})
                cr.commit()
            import_obj.write(cr, uid, [import_status_id], {'state': 'done'})
            cr.commit()
        except Exception as e:
            import_obj.write(cr, uid, [import_status_id], {'state': 'error'})
            cr.commit()
            log.info(e)
            cr.rollback()
        finally:
            cr.close()
        log.info('End: thread_import_email_subcribes')
        return True

vhr_email_news()
