#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import importlib
import unittest

testmodules = ['test_import',
               'tests_bronx.test_datagrip_datastore',
               'tests_bronx.test_datagrip_namelist',
               'tests_bronx.test_fancies_dump',
               'tests_bronx.test_fancies_loggers',
               'tests_bronx.test_patterns_getbytag',
               'tests_bronx.test_patterns_observer',
               'tests_bronx.test_stdtypes_date',
               'tests_bronx.test_stdtypes_dictionaries',
               'tests_bronx.test_syntax_parsing',
               'tests_bronx.test_system_hash',
               'tests_bronx.test_system_interrupt',
               'tests_footprints.test_fp_core',
               'tests_footprints.test_fp_doc',
               'tests_footprints.test_fp_priorities',
               'tests_footprints.test_fp_reporting',
               'tests_footprints.test_fp_setup',
               'tests_footprints.test_fp_stdtypes',
               'tests_footprints.test_fp_util',
               ]


def build_suite(testlist):
    """Load the test classes from a given list of modules."""
    outsuite = unittest.TestSuite()
    for t in testlist:
        try:
            # If the module defines a suite() function, call it to get the suite.
            mod = importlib.import_module(t)
            suitefn = getattr(mod, 'get_test_class')
            for x in suitefn():
                outsuite.addTest(unittest.makeSuite(x, 'test'))
        except (ImportError, AttributeError):
            # else, just load all the test cases from the module.
            outsuite.addTest(unittest.defaultTestLoader.loadTestsFromName(t))
    return outsuite


if __name__ == '__main__':
    results = unittest.TestResult()

    suite = build_suite(testmodules)
    suite.run(result=results)

    print("\n-- TEST RESULTS --\n")
    print('Number of tests executed: {:d}\n'.format(results.testsRun))

    for result, message in ((results.errors, "errors"),
                            (results.skipped, "tests skipped"),
                            (results.failures, "failures"),
                            ):
        if len(result):
            print('!!! Number of {}: {:d}\n'.format(message.upper(), len(result)))
            for entry in result:
                print(repr(entry[0]))
                print(entry[1])
        else:
            print('No {} :-)'.format(message))
        print()
