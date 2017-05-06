# -*-coding:utf-8-*-
import logging
import openerp

from openerp.tools.config import config
import os
import time
from openerp import http
import werkzeug.utils


log = logging.getLogger(__name__)


# def setup_session(self, httprequest):
#     
#     # recover or create session
#     if not openerp.tools.config.get('memcached'):
#         session_gc(self.session_store)
#     
#     sid = httprequest.args.get('session_id')
#     explicit_session = True
#     if not sid:
#         sid =  httprequest.headers.get("X-Openerp-Session-Id")
#     if not sid:
#         sid = httprequest.cookies.get('session_id')
#         explicit_session = False
#     
#     #NG: Delete session when logout
#     if httprequest.path == '/web/login' and sid is not None:
#         print 'delete session when logout'
# #         httprequest.session = self.session_store.get(sid)
# #         self.session_store.delete(httprequest.session)
#         sid = None
#         explicit_session = False
#         
#     if sid is None:
#         httprequest.session = self.session_store.new()
#     else:
#         httprequest.session = self.session_store.get(sid)
#     return explicit_session
    
    
def session_gc(session_store):
    #            
#     if random.random() < 0.001:
        # we keep session one week
#         last_week = time.time() - 60*60*24*7
        
        session_timeout = config.get('session_timeout') or 60 * 60 * 2
        last_week = time.time() - int(session_timeout)
        for fname in os.listdir(session_store.path):
            path = os.path.join(session_store.path, fname)
            try:
                if os.path.getmtime(path) < last_week:
                    os.unlink(path)
            except OSError:
                pass

def get_response(self, httprequest, result, explicit_session):
    if isinstance(result, http.Response) and result.is_qweb:
        try:
            result.flatten()
        except(Exception), e:
            if http.request.db:
                result = http.request.registry['ir.http']._handle_exception(e)
            else:
                raise
     
    if isinstance(result, basestring):
        response = http.Response(result, mimetype='text/html')
    else:
        response = result
     
    if httprequest.session.should_save:
        self.session_store.save(httprequest.session)
    # We must not set the cookie if the session id was specified using a http header or a GET parameter.
    # There are two reasons to this:
    # - When using one of those two means we consider that we are overriding the cookie, which means creating a new
    #   session on top of an already existing session and we don't want to create a mess with the 'normal' session
    #   (the one using the cookie). That is a special feature of the Session Javascript class.
    # - It could allow session fixation attacks.
    if not explicit_session and hasattr(response, 'set_cookie'):
        max_age = 2 * 60 * 60
        if config.get('session_timeout_idle'):
            max_age = int(config.get('session_timeout_idle'))
        response.set_cookie('session_id', httprequest.session.sid, max_age=max_age)
     
    return response
 

 
http.Root.get_response = get_response
http.session_gc = session_gc
# http.Root.setup_session = setup_session