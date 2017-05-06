# -*-coding:utf-8-*-
import logging
import openerp
import unittest2
import functools
import itertools

from openerp.osv import osv, fields
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT


_logger = logging.getLogger(__name__)


class vhr_hr_test_result(osv.osv):
    _name = 'vhr.hr.test.result'
    _description = 'VHR HR Test Result'
    
    _columns = {
        'name': fields.char('Name', size=128),
        'date_run': fields.date('Date Run'),
        'description': fields.text('Description'),
    }
    
    _defaults = {
                 'date_run': fields.datetime.now,
                 }
    
    _order = 'date_run desc'
    
    def run_test(self, cr, uid, ids, context=None):
        
        cr.execute("SELECT name FROM ir_module_module WHERE state='installed' and name like 'vhr_%'")
        failures_list = []
        for module_name in cr.fetchall():
            failures = run_unit_tests(module_name[0], cr.dbname)
            failures_list.extend(failures)
            
        error_message = ''
        for failure in failures_list:
            error_message += "\n\n" + str(failure[0]) + ' :   \n\n' + str(failure[1])
        
        self.write(cr, uid, ids, {'description': error_message})


from openerp.modules.module import get_test_modules, unwrap_suite, runs_at, TestStream
runs_at_install = functools.partial(runs_at, hook='at_install', default=True)

def run_unit_tests(module_name, dbname, position=runs_at_install):
    """
    :returns: ``True`` if all of ``module_name``'s tests succeeded, ``False``
              if any of them failed.
    :rtype: bool
    """
    global current_test
    
    current_test = module_name
    mods = get_test_modules(module_name)
#     r = True
    failures = []
    for m in mods:
        tests = unwrap_suite(unittest2.TestLoader().loadTestsFromModule(m))
        suite = unittest2.TestSuite(itertools.ifilter(position, tests))
        _logger.info('running %s tests.', m.__name__)

        result = unittest2.TextTestRunner(verbosity=2, stream=TestStream(m.__name__)).run(suite)
        failures.extend(result.failures)
        if not result.wasSuccessful():
#             r = False
            _logger.error("Module %s: %d failures, %d errors",
                          module_name, len(result.failures), len(result.errors))
    current_test = None
    return failures