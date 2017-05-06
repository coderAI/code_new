import xmlrpclib
import json
import base64
# Local
local_common = 'http://localhost:8069/xmlrpc/common'
local_proxy = 'http://localhost:8069/xmlrpc/object'
username = 'admin'  # the user
pwd = '1'  # the password of the user
dbname = 'staging_vhrs'  # the database

# Get the uid
sock_common = xmlrpclib.ServerProxy(local_common)
uid = sock_common.login(dbname, username, pwd)

sock = xmlrpclib.ServerProxy(local_proxy)


#partner_id = sock.execute(dbname, uid, pwd, 'vhr.job.applicant', 'execute_workflow', 10016, {'ACTION': 'trans_offer_done'})
txt =         sock.execute(dbname, uid, pwd, 'mail.thread', 'encrypt_md5', 'approve luanpd@hrs.com.vn; 1432 hrsmissdteamtuannh3 vhr.ts.leave.email 1078','asdjshderysncgr')
print txt
