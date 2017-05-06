# -*-coding:utf-8-*-
import logging
from openerp import SUPERUSER_ID
from openerp.osv import osv, fields
import xmlrpclib
import email
from string import ascii_letters, digits
import hashlib
import re
from datetime import date, datetime


log = logging.getLogger(__name__)



class mail_thread(osv.AbstractModel):
    _inherit = 'mail.thread'
    
mail_thread()