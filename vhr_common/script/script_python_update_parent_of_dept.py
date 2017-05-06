#-*- coding: utf-8 -*-
import xmlrpclib
import simplejson as json
import unicodedata
import sys
import datetime


# Local
local_common = 'http://localhost:8069/xmlrpc/common'
local_proxy = 'http://localhost:8069/xmlrpc/object'
username = 'admin'  # the user
pwd = '1'  # the password of the user
dbname = 'hrm_uat1'  # the database

sock_common = xmlrpclib.ServerProxy(local_common)
uid = sock_common.login(dbname, username, pwd)

sock = xmlrpclib.ServerProxy(local_proxy)
res = sock.execute(dbname, uid, pwd, 'hr.department', 'call_parent_store_compute')
print res
