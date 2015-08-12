#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import os


testmodules = ['test_env',
               'test_date',
               'test_import',
               'test_cfgparser',
               ]


def build_suite(testlist):
    '''Function that load the test classes from a given list of modules'''
    outsuite = unittest.TestSuite()
    for t in testlist:
        try:
            # If the module defines a suite() function, call it to get the suite.
            mod = __import__(t, globals(), locals(), ['get_test_class'])
            suitefn = getattr(mod, 'get_test_class')
            for x in suitefn():
                outsuite.addTest(unittest.makeSuite(x, 'test'))
        except (ImportError, AttributeError):
            # else, just load all the test cases from the module.
            outsuite.addTest(unittest.defaultTestLoader.loadTestsFromName(t))
    return outsuite


if __name__ == '__main__':
    results = unittest.TestResult()
    dirsave = os.getcwd()

    '''
    Now we run the tests
    '''

    # First we test footprints (it need to be done first before any of the
    # vortex module is import. Otherwise it fails !
    footprint_special = build_suite(['test_footprints', ])
    footprint_special.run(result=results)
    # We run all the other tests (in the original working directory)
    os.chdir(dirsave)
    suite = build_suite(testmodules)
    suite.run(result=results)

    '''
    Now we will print the test results...
    '''

    def test_results_print(test_list):
        for entry in test_list:
            print repr(entry[0])
            print entry[1]

    print
    print "-- TEST RESULTS --"
    print

    print 'Number of executed tests: {:d}'.format(results.testsRun)
    print

    if len(results.errors):
        print '!!!Number of ERRORS: {:d}'.format(len(results.errors))
        print
        test_results_print(results.errors)
    else:
        print 'No errors :-)'
    print

    if len(results.failures):
        print '!!!Number of FAILURES: {:d}'.format(len(results.failures))
        print
        test_results_print(results.failures)
    else:
        print 'No failures :-)'
    print
