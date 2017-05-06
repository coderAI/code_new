import xmlrpclib
import json
import base64
# Local
local_common = 'http://localhost:8069/xmlrpc/common'
local_proxy = 'http://localhost:8069/xmlrpc/object'
username = 'admin'  # the user
pwd = '1'  # the password of the user
dbname = 'hrm_03_04'  # the database
sock_common = xmlrpclib.ServerProxy(local_common)
uid = sock_common.login(dbname, username, pwd)


sock = xmlrpclib.ServerProxy(local_proxy)
partner_id = sock.execute(dbname, uid, pwd, 'vhr.hrbp.assignment', 'update_name_for_all_hrbp_assignment')

