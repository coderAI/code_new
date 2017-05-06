# -*-coding:utf-8-*-

from openerp.osv import osv, fields

class vhr_applicant_job_track_group(osv.osv):
    _name = 'vhr.applicant.job.track.group'
    
    _columns = {
        'name': fields.char('Name', size=256),
        'job_track_ids': fields.one2many('vhr.applicant.job.track', 'job_track_group_id', string='Job Track')
    }

class vhr_applicant_job_track(osv.osv):
    _name = 'vhr.applicant.job.track'
    
    _columns = {
        'name': fields.char('Name', size=256),
        'job_track_group_id': fields.many2one('vhr.applicant.job.track.group', 'Group'),
    }
