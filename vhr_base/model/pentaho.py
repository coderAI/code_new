# -*-coding:utf-8-*-
import logging
from openerp.osv import orm, fields
from openerp.addons.pentaho_reports.core import VALID_OUTPUT_TYPES

log = logging.getLogger(__name__)

VALID_OUTPUT_TYPES = [('pdf', 'Portable Document (pdf)'),
                      ('xls', 'Excel Spreadsheet (xls)'),
                      ('xlsx', 'Excel Spreadsheet 2007 (xlsx)'),
                      ('csv', 'Comma Separated Values (csv)'),
                      ('rtf', 'Rich Text (rtf)'),
                      ('html', 'HyperText (html)'),
                      ('txt', 'Plain Text (txt)'),
                      ]

class report_xml(orm.Model):
    _inherit = 'ir.actions.report.xml'
    
    _columns = {
                'pentaho_report_output_type': fields.selection([("pdf", "PDF"), ("html", "HTML"), ("csv", "CSV"), ("xls", "Excel"), ("xlsx", "Excel (2007)"), ("rtf", "RTF"), ("txt", "Plain text")],
                                                               'Output format'),
                }
report_xml()

class report_prompt_class(orm.TransientModel):
    _inherit = 'ir.actions.report.promptwizard'
    
    _columns = {
                'output_type': fields.selection(VALID_OUTPUT_TYPES, 'Report format', help='Choose the format for the output', required=True),
                }
    
report_prompt_class()