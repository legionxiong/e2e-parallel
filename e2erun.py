#!/usr/bin/python
# -*- coding:utf-8 -*-

'''
An implement of E2E parallel testing

@author: Lijin Xiong
'''

import os
import re
import sys
import unittest
import signal
import optparse
import time
from multiprocessing import Pool
import xml.etree.cElementTree as etree
import logging

logging.basicConfig(level=logging.DEBUG,
                    format='[%(asctime)s %(levelname)s] [%(filename)s:%(lineno)d] %(message)s')
formatter = logging.Formatter('[%(asctime)s %(levelname)s] [%(filename)s:%(lineno)d] %(message)s')


TestResultSum = {"Total": 0, "Pass": 0, "Fail/Error": 0}

def get_tests_from_xml(set_xml, app_type=None, _case_list=None):
    '''
    xml test set sample:
    <testset>
        <module name='app'>
            <test name='App' type='Web'>
                <case index='1'>test_app_add</case>
                <case priority='1' skipIf='Web'>test_app_share</case>
                <case priority='1' skipIfNot='Mobile'>test_app_update_url</case>
            </test>
        </module>
    </testset>
    '''
    global TestResultSum
    _noparallel = {}
    _parallel = {}
    test_list_noparallel = []
    test_list_parallel = []
    tree = etree.ElementTree(file=set_xml)
    root = tree.getroot()
    __case_list = re.split(' |,', _case_list) if _case_list else []
    for mod in root:
        for cls in mod:
            if not app_type:
                app_type = cls.attrib['type']
            for case in cls:
                if ('skipIf' in case.attrib and app_type in case.attrib['skipIf']) or ('skipIfNot' in case.attrib and app_type not in case.attrib['skipIfNot']) or \
                (_case_list and case.text.strip() not in __case_list):
                    continue
                if 'index' in case.attrib:
                    _index = case.attrib['index']
                    if _index not in _noparallel:
                        _noparallel[_index] = []
                    _noparallel[_index].append(mod.attrib['name'] + '.' + cls.attrib['name'] + '.' + case.text)
                    TestResultSum['Total'] += 1
                else:
                    _priority = case.attrib['priority']
                    if _priority not in _parallel:
                        _parallel[_priority] = []
                    _parallel[_priority].append(mod.attrib['name'] + '.' + cls.attrib['name'] + '.' + case.text)
                    TestResultSum['Total'] += 1

    index_str_list_noparallel = _noparallel.keys()
    index_int_list_noparallel = [int(i) for i in index_str_list_noparallel]
    index_int_list_noparallel.sort()

    priority_str_list_parallel = _parallel.keys()
    priority_int_list_parallel = [int(p) for p in priority_str_list_parallel]
    priority_int_list_parallel.sort()

    for i in index_int_list_noparallel:
        test_list_noparallel.extend(_noparallel[str(i)])

    for p in priority_int_list_parallel:
        if _case_list:
            test_list_noparallel.extend(_parallel[str(p)])
        else:
            test_list_parallel.append(_parallel[str(p)])
    return (test_list_noparallel, test_list_parallel, app_type)

def run_test(test_list, rerun):
    suite = unittest.TestLoader().loadTestsFromNames(test_list)
    success = unittest.TextTestRunner(verbosity=2).run(suite)
    if not success:
        rerun -= 1
        if rerun >= 0:
            return run_test(test_list, rerun)
    return 1 if success else 0

def init_worker():
    signal.signal(signal.SIGINT, signal.SIG_IGN)


if __name__ == '__main__':
    parser = optparse.OptionParser('Usage: uitest.py [options] \n')
    parser.add_option("--test-set",
                        dest="test_set",
                        default=None,
                        action='store',
                        help="Test set")
    parser.add_option("--test-url",
                        dest="test_url",
                        default=None,
                        action='store',
                        help="test url")
    parser.add_option("--app-type",
                        dest="app_type",
                        default=None,
                        action='store',
                        help="app type")
    parser.add_option("--selenium-server",
                        dest="selenium_server",
                        default=None,
                        action='store',
                        help="Selenium server IP")
    parser.add_option("--setup",
                        dest="setup",
                        default=False,
                        action='store_true',
                        help="Setup test environment")
    parser.add_option("--browser",
                        dest="browser",
                        default='Chrome',
                        action='store',
                        help="Real browser to launch test")
    parser.add_option("--rerun",
                        dest="rerun",
                        default=0,
                        action='store',
                        help="Rerun times")
    parser.add_option("--ver",
                        dest="version",
                        default=None,
                        action='store',
                        help="Product version")
    parser.add_option("--tc",
                        dest="test_case",
                        default=None,
                        action='store',
                        help="Test case")
    parser.add_option("-l", "--parallel-level",
                        dest="parallel_level",
                        default=8,
                        action='store',
                        help="Parallel tests number")
    parser.add_option("-s", "--screenshot",
                        dest="screenshot",
                        default=False,
                        action='store_true',
                        help="Take screenshot while running test")

    (options, arg) = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    if not options.test_url:
        logging.error('test_url was not specified \n')
        parser.print_help()
        sys.exit(1)

    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(os.path.join(current_dir, 'testcase'))

    if not options.selenium_server:
        logging.error('Selenium server IP is needed! \n')
        parser.print_help()
        sys.exit(1)

    setfile = options.test_set
    setname = os.path.basename(setfile).split('.')[0]

    tests_parallel = []
    if options.test_case:
        case_list = options.test_case
        (tests_noparallel, _, app_type) = get_tests_from_xml(setfile, options.app_type, case_list)
        if not tests_noparallel:
            logging.info('Test [%s] is not in %s or a SKIPPED case \n' % (case_list, setfile))
            sys.exit(1)
    else:
        (tests_noparallel, tests_parallel, app_type) = get_tests_from_xml(setfile, options.app_type)

    logging.info('Number of tests to run: %s \n' % TestResultSum['Total'])

    if options.setup:
        print 'Setup test environment... \n'
        os.environ['SETUPENV'] = 'true'
        if not tests_noparallel:
            logging.info('There must be at least 1 case that is nonparallel, which will set up the test environment. \n')
            sys.exit(1)

    parallel_level = int(options.parallel_level)

    try:
        start_tid = 1
        run_test(tests_noparallel, int(options.rerun))
        start_tid = len(tests_noparallel)
        if os.getenv('SETUPENV'):
            del os.environ['SETUPENV']

        for plist in tests_parallel:
            results = []
            pool = Pool(parallel_level, init_worker)
            for test in plist:
                start_tid += 1
                ret = pool.apply_async(run_test, args=([test], int(options.rerun)))
                results.append(ret)
            pool.close()
            pool.join()

            for ret in results:
                TestResultSum['Pass'] += ret.get(1)

        TestResultSum['Fail/Error'] = TestResultSum['Total'] - TestResultSum['Pass']
        logging.info('Test result: %s \n' % TestResultSum)
        if TestResultSum['Pass'] != TestResultSum['Total']:
            sys.exit(1)
        else:
            sys.exit(0)

    except KeyboardInterrupt:
        logging.info('exit main process due to User Interruption')
        if 'pool' in locals():
            pool.terminate()
        sys.exit(1)