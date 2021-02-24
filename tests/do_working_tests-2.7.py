#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import codecs
import importlib
import os
import sys
import unittest


testmodules = ['test_import',
               'tests_algo.test_parallel',
               'tests_bronx.test_compat_functools',
               'tests_bronx.test_compat_random',
               'tests_bronx.test_datagrip_datastore',
               'tests_bronx.test_datagrip_misc',
               'tests_bronx.test_datagrip_namelist',
               'tests_bronx.test_datagrip_varbc',
               'tests_bronx.test_fancies_display',
               'tests_bronx.test_fancies_dump',
               'tests_bronx.test_fancies_loggers',
               'tests_bronx.test_net_netrc',
               'tests_bronx.test_patterns_getbytag',
               'tests_bronx.test_patterns_observer',
               'tests_bronx.test_stdtypes_catalog',
               'tests_bronx.test_stdtypes_date',
               'tests_bronx.test_stdtypes_dictionaries',
               'tests_bronx.test_stdtypes_xtemplates',
               'tests_bronx.test_syntax_externalcode',
               'tests_bronx.test_syntax_minieval',
               'tests_bronx.test_syntax_parsing',
               'tests_bronx.test_syntax_pretty',
               'tests_bronx.test_system_cpus',
               'tests_bronx.test_system_hash',
               'tests_bronx.test_system_interrupt',
               'tests_bronx.test_system_memory',
               'tests_contents.test_eps',
               'tests_contents.test_generic',
               'tests_contents.test_logs',
               'tests_contents.test_namelists',
               'tests_contents.test_obs',
               'tests_footprints.test_fp_core',
               'tests_footprints.test_fp_doc',
               'tests_footprints.test_fp_doctests',
               'tests_footprints.test_fp_priorities',
               'tests_footprints.test_fp_reporting',
               'tests_footprints.test_fp_setup',
               'tests_footprints.test_fp_stdtypes',
               'tests_footprints.test_fp_util',
               'tests_systems.test_basics',
               'tests_systems.test_osextended',
               'test_cfgparser',
               'test_compression',
               'test_containers',
               'test_ecmwf_interface',
               'test_env',
               'test_gco',
               'test_iosponge',
               'test_layoutappconf',
               'test_layoutjobs',
               'test_layoutnodes',
               'test_net_netstat',
               'test_providers',
               'test_sessions_stuff',
               'test_simpleworkflow',
               'test_storage',
               'test_stores',
               'test_syntax',
               'test_targets',
               'test_toolsodb',
               'test_vortexnames',
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
    # Jump into the test directory
    os.chdir(os.path.dirname(os.path.realpath(__file__)))

    # Ensure that stdout is fine...
    sys.stdout = codecs.getwriter('utf8')(sys.stdout)

    # Setup the import test (to be a little faster...)
    os.environ['VORTEX_IMPORT_UNITTEST_DO_DUMPS'] = '0'

    suite = build_suite(testmodules)
    results = unittest.TextTestRunner(verbosity=2, buffer=True).run(suite)

    if results.failures or results.errors:
        exit(1)
