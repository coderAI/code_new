import openerp
import functools
import logging
import simplejson
import werkzeug.utils
# import werkzeug.wrappers

from openerp import http

from openerp.http import request, serialize_exception as _serialize_exception
from openerp.addons.web.controllers.main import CSVExport, ExcelExport


_logger = logging.getLogger(__name__)

def serialize_exception(f):
    @functools.wraps(f)
    def wrap(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception, e:
            _logger.exception("An exception occured during an http request")
            se = _serialize_exception(e)
            error = {
                'code': 200,
                'message': "OpenERP Server Error",
                'data': se
            }
            return werkzeug.exceptions.InternalServerError(simplejson.dumps(error))
    return wrap

class CSVExport(CSVExport):

    @http.route('/web/export/csv', type='http', auth="user")
    @serialize_exception
    def index(self, data, token):
        #NG: Only allow admin/C&B to export csv
        if http and http.request and http.request.uid != openerp.SUPERUSER_ID:
            groups_model = request.registry.get('res.groups')
            group_ids = groups_model.search(request.cr, openerp.SUPERUSER_ID, [('users','=',http.request.uid),
                                                                               ('name','=',"VHR C&B")])
            if not group_ids:
                raise Exception("AccessDenied")
        
        
        return self.base(data, token)


# class ExcelExport(ExcelExport):
# 
#     @http.route('/web/export/xls', type='http', auth="user")
#     @serialize_exception
#     def index(self, data, token):
#         #NG: Only allow admin to export
#         if http and http.request and http.request.uid != openerp.SUPERUSER_ID:
#             raise Exception("AccessDenied")
#         return self.base(data, token)
    
    
    