# -*-coding:utf-8-*-
import logging
import time

from openerp.tools.translate import _
from openerp.osv import osv, fields
from openerp import tools

log = logging.getLogger(__name__)

class fetchmail_server(osv.osv):
    """Incoming POP/IMAP mail server account"""
    _inherit = 'fetchmail.server'
    
    def check_seen(self, cr, uid, nums_array, context=None):
        try:
            for item in nums_array:
                server = self.browse(cr, uid, item['server'], context=context)
                imap_server = server.connect()
                imap_server.select()
                for num in item['num']:
                    imap_server.store(num, '+FLAGS', '\\Seen')
        except:
            pass
        return True
    
    def fetch_mail(self, cr, uid, ids, context=None):
        """WARNING: meant for cron usage only - will commit() after each email!"""
        if context is None:
            context = {}
        context['fetchmail_cron_running'] = True
        log.debug("start vhr_message_process")
        mail_thread = self.pool.get('mail.thread')
        action_pool = self.pool.get('ir.actions.server')
        nums_array = []
        for server in self.browse(cr, uid, ids, context=context):
            log.info('start checking for new emails on %s server %s', server.type, server.name)
            context.update({'fetchmail_server_id': server.id, 'server_type': server.type})
            count, failed = 0, 0
            imap_server = False
            pop_server = False
            nums_email = {'server': server.id, 'num': []}
            if server.type == 'imap':
                try:
                    imap_server = server.connect()
                    imap_server.select()
                    result, data = imap_server.search(None, '(UNSEEN)')
                    for num in data[0].split():
                        res_id = None
                        result, data = imap_server.fetch(num, '(RFC822)')
                        imap_server.store(num, '-FLAGS', '\\Seen')
                        try:
#                             res_id = mail_thread.message_process(cr, uid, server.object_id.model,
#                                                                  data[0][1],
#                                                                  save_original=server.original,
#                                                                  strip_attachments=(not server.attach),
#                                                                  context=context)
                            """Tuannh3: Get decide in mail"""
                            log.info('call vhr_message_process')
                            res_id, decide = mail_thread.vhr_message_process(cr, uid, server.object_id.model,
                                                                data[0][1],
                                                                save_original=server.original,
                                                                strip_attachments=(not server.attach),
                                                                action_id=server.action_id.id,
                                                                context=context)
                        except Exception:
                            log.exception('Failed to process mail from %s server %s.', server.type, server.name)
                            failed += 1
                        if res_id and server.action_id:
#                             action_pool.run(cr, uid, [server.action_id.id], {'active_id': res_id, 'active_ids': [res_id], 'active_model': context.get("thread_model", server.object_id.model)})
                            """Tuannh3: Set decide in to context"""
                            action_pool.run(cr, uid, [server.action_id.id], {'mail_decide': decide, 'active_id': res_id, 'active_ids': [res_id], 'active_model': context.get("thread_model", server.object_id.model)})
                            imap_server.store(num, '+FLAGS', '\\Seen')
                        else:
                            nums_email['num'].append(num)
                        cr.commit()
                        count += 1
                    log.info("Fetched %d email(s) on %s server %s; %d succeeded, %d failed.", count, server.type, server.name, (count - failed), failed)
                except Exception:
                    log.exception("General failure when trying to fetch mail from %s server %s.", server.type, server.name)
                finally:
                    if imap_server:
#                         print 'imap server'
#                         print imap_server
                        imap_server.close()
                        imap_server.logout()
            elif server.type == 'pop':
                try:
                    pop_server = server.connect()
                    (numMsgs, totalSize) = pop_server.stat()
                    pop_server.list()
                    for num in range(1, numMsgs + 1):
                        (header, msges, octets) = pop_server.retr(num)
                        msg = '\n'.join(msges)
                        res_id = None
                        try:
                            res_id = mail_thread.message_process(cr, uid, server.object_id.model,
                                                                 msg,
                                                                 save_original=server.original,
                                                                 strip_attachments=(not server.attach),
                                                                 context=context)
                        except Exception:
                            log.exception('Failed to process mail from %s server %s.', server.type, server.name)
                            failed += 1
                        if res_id and server.action_id:
                            action_pool.run(cr, uid, [server.action_id.id], {'active_id': res_id, 'active_ids': [res_id], 'active_model': context.get("thread_model", server.object_id.model)})
                        pop_server.dele(num)
                        cr.commit()
                    log.info("Fetched %d email(s) on %s server %s; %d succeeded, %d failed.", numMsgs, server.type, server.name, (numMsgs - failed), failed)
                except Exception:
                    log.exception("General failure when trying to fetch mail from %s server %s.", server.type, server.name)
                finally:
                    if pop_server:
                        pop_server.quit()
            nums_array.append(nums_email)            
            server.write({'date': time.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)})
        self.check_seen(cr, uid, nums_array, context)
        return True
fetchmail_server()