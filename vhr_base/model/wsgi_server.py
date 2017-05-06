# -*- coding: utf-8 -*-
import openerp
import logging
import xmlrpclib

from openerp.service.wsgi_server import xmlrpc_handle_exception_string,xmlrpc_handle_exception_int

_logger = logging.getLogger(__name__)

def xmlrpc_return(start_response, service, method, params, string_faultcode=False):
    """
    Helper to call a service's method with some params, using a wsgi-supplied
    ``start_response`` callback.

    This is the place to look at to see the mapping between core exceptions
    and XML-RPC fault codes.
    """
    # Map OpenERP core exceptions to XML-RPC fault codes. Specific exceptions
    # defined in ``openerp.exceptions`` are mapped to specific fault codes;
    # all the other exceptions are mapped to the generic
    # RPC_FAULT_CODE_APPLICATION_ERROR value.
    # This also mimics SimpleXMLRPCDispatcher._marshaled_dispatch() for
    # exception handling.
    try:
        log_params = list(params)
        if len(log_params) >=3:
            log_params[2] = 'masked_password'
            
        _logger.info('::  XMLRPC call to service='+ str(service) + '; method=' +str(method)+ '; params='+str(log_params))
        result = openerp.http.dispatch_rpc(service, method, params)
        response = xmlrpclib.dumps((result,), methodresponse=1, allow_none=False, encoding=None)
    except Exception, e:
        if string_faultcode:
            response = xmlrpc_handle_exception_string(e)
        else:
            response = xmlrpc_handle_exception_int(e)
    start_response("200 OK", [('Content-Type','text/xml'), ('Content-Length', str(len(response)))])
    return [response]


openerp.service.wsgi_server.xmlrpc_return  = xmlrpc_return