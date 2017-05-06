# -*-coding:utf-8-*-
import logging
from openerp import SUPERUSER_ID
from openerp.osv import osv, fields
import xmlrpclib
import email
from string import ascii_letters, digits
import hashlib
import re

log = logging.getLogger(__name__)

class mail_mail(osv.osv):
    _inherit = 'mail.mail'
    _columns = {
        'is_used': fields.boolean('Is used')
        }
    _defaults = {
        'is_used': False
        }
mail_mail()


class mail_thread(osv.AbstractModel):
    ''' mail_thread model is meant to be inherited by any model that needs to
        act as a discussion topic on which messages can be attached. Public
        methods are prefixed with ``message_`` in order to avoid name
        collisions with methods of the models that will inherit from this class.

        ``mail.thread`` defines fields used to handle and display the
        communication history. ``mail.thread`` also manages followers of
        inheriting classes. All features and expected behavior are managed
        by mail.thread. Widgets has been designed for the 7.0 and following
        versions of OpenERP.

        Inheriting classes are not required to implement any method, as the
        default implementation will work for any model. However it is common
        to override at least the ``message_new`` and ``message_update``
        methods (calling ``super``) to add model-specific behavior at
        creation and update of a thread when processing incoming emails.

        Options:
            - _mail_flat_thread: if set to True, all messages without parent_id
                are automatically attached to the first message posted on the
                ressource. If set to False, the display of Chatter is done using
                threads, and no parent_id is automatically set.
    '''
    _inherit = 'mail.thread'
    
    #Ma Hoa MD5
    
    magic_md5 = '$1$'

    def gen_salt(self, length=8, symbols=ascii_letters + digits):
        return 'asdjshderysncgr'

    def encrypt_md5(self, raw_pw, salt, magic=magic_md5):
        raw_pw = raw_pw.encode('utf-8')
        salt = salt.encode('utf-8')
        hash_md5 = hashlib.md5()
        hash_md5.update(raw_pw + magic + salt)
        st = hashlib.md5()
        st.update(raw_pw + salt + raw_pw)
        stretch = st.digest()

        for i in range(0, len(raw_pw)):
            hash_md5.update(stretch[i % 16])

        i = len(raw_pw)

        while i:
            if i & 1:
                hash_md5.update('\x00')
            else:
                hash_md5.update(raw_pw[0])
            i >>= 1

        saltedmd5 = hash_md5.digest()

        for i in range(1000):
            hash_md5 = hashlib.md5()

            if i & 1:
                hash_md5.update(raw_pw)
            else:
                hash_md5.update(saltedmd5)

            if i % 3:
                hash_md5.update(salt)
            if i % 7:
                hash_md5.update(raw_pw)
            if i & 1:
                hash_md5.update(saltedmd5)
            else:
                hash_md5.update(raw_pw)

            saltedmd5 = hash_md5.digest()

        itoa64 = './laskudkajshdhgfuehqajjasdfuaisdsakdajsdjasfhsjdfghsdkfaskdiasreruasdhglaweruy'

        rearranged = ''
        for a, b, c in ((0, 6, 12), (1, 7, 13), (2, 8, 14), (3, 9, 15), (4, 10, 5)):
            v = ord(saltedmd5[a]) << 16 | ord(saltedmd5[b]) << 8 | ord(saltedmd5[c])

            for i in range(4):
                rearranged += itoa64[v & 0x3f]
                v >>= 6

        v = ord(saltedmd5[11])

        for i in range(2):
            rearranged += itoa64[v & 0x3f]
            v >>= 6

        return magic + salt + '$' + rearranged
    
    def hrs_get_link(self, email_to, record_id, type_name, model, action_id=''):
        if isinstance(email_to, list):
            email_to = email_to[0]
        
        try:
            email_to = email_to.lower()
        except Exception as e:
            log.info('Can not convert email_to to lower: %s' % e)
            
        if not isinstance(record_id, str):
            record_id = str(record_id)
            
        key = 'hrsmissdteamtuannh3'
        link = '%s %s %s %s %s %s' % (type_name, email_to, record_id, key, model, action_id)
        link = self.encrypt_md5(link, self.gen_salt())
        link = "[" + link + "]"
        return link

    def hrs_check_mail(self, cr, uid, msg, action_id):
#         if 'X-Originating-IP' in msg:
#             hrs_ip_mail = self.pool.get('hrs.ip.mail.server')
#             if isinstance(msg['X-Originating-IP'], list):
#                 for item in msg['X-Originating-IP']:
#                     ip_mail = hrs_ip_mail.search(cr, uid, ['|', ('lower_bound', '=', item), ('upper_bound', '=', item)])
#                     if ip_mail:
#                         return False
#             else:
#                 ip_mail = str(msg['X-Originating-IP']).replace('[', '')
#                 ip_mail = ip_mail.replace(']', '')
#                 ip_mail = hrs_ip_mail.search(cr, uid, ['|', ('lower_bound', '=', ip_mail), ('upper_bound', '=', ip_mail)])
#                 if ip_mail:
#                     return False
        
        log.info("body message=" + msg['body'])
        body = msg['body']
        
        #NG: Replace <a></a> with ''
        #TODO: Consider to get msg[body] from text/plain part if this code does not correct in all case.
        try:
            subrep = ["""<a href=[ a-zA-Z$!@#%^&*-+.:/'"|]+>""",
                      '</a>']
            for item in subrep:
                s = re.search(item, body)
                if not s:
                    break
                
                count = 0
                while s and count < 5:
                    body = body.replace(s.group(), '')
                    s = re.search(item, body)
                    count += 1
        except Exception as e:
            log.error(e)
        
        md5 = re.search("SD \[[a-zA-Z_0-9$!@#%^&*()-+,:;./~`={}|\<>?]+]", body)
        
        mail_obj = False
        if md5:
            md5 = md5.group(0).replace('SD ','')
            log.info("String Md5 in email : %s" % (md5))
            hrs_mail = self.pool.get('mail.mail')
            email_from = str(msg['from']).split('<')[1].replace('>', '').lower()+';'
            log.debug('start hrs_check_mail email from : %s'%(email_from))
            ids_mail = hrs_mail.search(cr, uid, [('email_to', '=ilike', email_from), ('res_id', '!=', 0), \
                                                 ('state', '=', 'sent'), ('is_used','=',False)])
            log.debug('ids email : %s'%(ids_mail))
            for mail in hrs_mail.browse(cr, uid, ids_mail):
                for item in ['approve', 'reject', 'reset', 'return']:
                    log.debug('email from  : %s  --mail_id: %s  -- res_id : %s -- item : %s -- model : %s, --action_id: %s'%(email_from, mail.id, mail.res_id, item, mail.model, action_id))
                    md5_db = self.hrs_get_link(email_from, mail.res_id, item, mail.model, action_id)
                    log.info("String md5 in database to check : %s" % (md5_db))
                    if md5 == md5_db:
                        mail_obj = mail
                        hrs_mail.write(cr, uid, mail.id, {'is_used': True})
                        log.info("Found checked mail")
                        return mail_obj.res_id, item
        return False, ''
    
    def vhr_message_process(self, cr, uid, model, message, custom_values=None,
                        save_original=False, strip_attachments=False,
                        thread_id=None, action_id=None, context=None):
        """Tuannh3: Build another function message process because i can't understand function router process"""
        """ Process an incoming RFC2822 email message, relying on
            ``mail.message.parse()`` for the parsing operation,
            and ``message_route()`` to figure out the target model.

            Once the target model is known, its ``message_new`` method
            is called with the new message (if the thread record did not exist)
            or its ``message_update`` method (if it did).

            There is a special case where the target model is False: a reply
            to a private message. In this case, we skip the message_new /
            message_update step, to just post a new message using mail_thread
            message_post.

           :param string model: the fallback model to use if the message
               does not match any of the currently configured mail aliases
               (may be None if a matching alias is supposed to be present)
           :param message: source of the RFC2822 message
           :type message: string or xmlrpclib.Binary
           :type dict custom_values: optional dictionary of field values
                to pass to ``message_new`` if a new record needs to be created.
                Ignored if the thread record already exists, and also if a
                matching mail.alias was found (aliases define their own defaults)
           :param bool save_original: whether to keep a copy of the original
                email source attached to the message after it is imported.
           :param bool strip_attachments: whether to strip all attachments
                before processing the message, in order to save some space.
           :param int thread_id: optional ID of the record/thread from ``model``
               to which this mail should be attached. When provided, this
               overrides the automatic detection based on the message
               headers.
        """
        if context is None:
            context = {}
        
        # extract message bytes - we are forced to pass the message as binary because
        # we don't know its encoding until we parse its headers and hence can't
        # convert it to utf-8 for transport between the mailgate script and here.
        if isinstance(message, xmlrpclib.Binary):
            message = str(message.data)
        # Warning: message_from_string doesn't always work correctly on unicode,
        # we must use utf-8 strings here :-(
        if isinstance(message, unicode):
            message = message.encode('utf-8')
        msg_txt = email.message_from_string(message)

        # parse the message, verify we are not in a loop by checking message_id is not duplicated
        msg = self.message_parse(cr, uid, msg_txt, save_original=save_original, context=context)
        if strip_attachments:
            msg.pop('attachments', None)

        if msg.get('message_id'):   # should always be True as message_parse generate one if missing
            existing_msg_ids = self.pool.get('mail.message').search(cr, SUPERUSER_ID, [
                                                                ('message_id', '=', msg.get('message_id')),
                                                                ], context=context)
            if existing_msg_ids:
                log.info('Ignored mail from %s to %s with Message-Id %s: found duplicated Message-Id during processing',
                                msg.get('from'), msg.get('to'), msg.get('message_id'))
                return False
            
        return self.hrs_check_mail(cr, uid, msg, action_id)

mail_thread()
