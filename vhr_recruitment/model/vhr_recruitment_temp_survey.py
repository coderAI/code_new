# -*-coding:utf-8-*-
import logging
from openerp.osv import osv, fields
import simplejson as json
from lxml import etree
from vhr_recruitment_constant import RE_Request_Survey_By_Email
from vhr_recruitment_abstract import vhr_recruitment_abstract, ADMIN
    
log = logging.getLogger(__name__)


class vhr_recruitment_temp_survey(osv.osv, vhr_recruitment_abstract):
    _name = "vhr.recruitment.temp.survey"
    _description = "RR Temp Survey"    
    _columns = {
        'request_code': fields.char('Request Code'),
        'rep1': fields.text('REP1'),
        'rep2': fields.text('REP2'),
        'rating': fields.char('Rating', size=255),
        'md5':fields.char('MD5', size=255),
    }
    
vhr_recruitment_temp_survey()
