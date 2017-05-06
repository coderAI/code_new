# -*-coding:utf-8-*-
import logging

from openerp.osv import fields
from openerp.osv import osv

log = logging.getLogger(__name__)


class ir_config_parameter(osv.osv):
    _inherit = 'ir.config_parameter'

    _columns = {
        'description': fields.text('Description'),
        'module_id': fields.many2one('ir.module.module', string='Module', select=1),
    }


ir_config_parameter()