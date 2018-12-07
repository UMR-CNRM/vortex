#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

'''
project.bin.test_names_cli.py -- Manages Unit-Tests from the test_names package.

There are several possible actions:
* list: List all the available test files
* load: Read in test file(s)
* loadref: Load the reference data
* compute: Run the test(s) but do not check the results
* check: Run the test(s), Load the reference data, Check the results
* dump: Dump a new set of reference data

'''

from __future__ import print_function, division, absolute_import, unicode_literals

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
import sys
import os
import re

# Automatically set the python path
vortexbase = re.sub('{0:}project{0:}bin$'.format(os.path.sep), '',
                    os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(vortexbase, 'site'))
sys.path.insert(0, os.path.join(vortexbase, 'src'))
sys.path.insert(0, os.path.join(vortexbase, 'project'))
sys.path.insert(0, os.path.join(vortexbase, 'tests'))

from bronx.fancies import loggers

from test_names import discover

ACTION_FUNCTION_ID = '_do_action_'


def _do_action_list(only):  # @UnusedVariable
    for f in discover.all_tests:
        print(f)


def _do_action_load(only):
    if only:
        discover.all_tests[only]
    else:
        discover.all_tests.all_load()


def _do_action_compute(only):
    if only:
        discover.all_tests[only].compute_results()
    else:
        discover.all_tests.all_compute_results()


def _do_action_loadref(only):
    if only:
        discover.all_tests[only].load_references()
    else:
        discover.all_tests.all_load_references()


def _do_action_check(only):
    _do_action_compute(only)
    _do_action_loadref(only)
    if only:
        discover.all_tests[only].check_results()
    else:
        discover.all_tests.all_check_results()


def _do_action_dump(only):
    _do_action_compute(only)
    if only:
        discover.all_tests[only].dump_results()
    else:
        discover.all_tests.all_dump_results()


def main():
    '''Process command line options.'''

    program_name = os.path.basename(sys.argv[0])
    program_shortdesc = program_name + ' -- ' + __import__('__main__').__doc__.lstrip("\n")
    program_desc = program_shortdesc

    # Find possible actions
    possibleactions = sorted([f[len(ACTION_FUNCTION_ID):]
                              for f in globals() if f.startswith(ACTION_FUNCTION_ID)])

    # Setup the argument parser
    parser = ArgumentParser(description=program_desc,
                            formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument("-v", "--verbose", dest="verbose", action="store_true",
                        help="Set verbosity flag.")
    parser.add_argument("--only", action='store',
                        help="Process only one test fine.")
    parser.add_argument("actions", action='store', nargs='+', choices=possibleactions,
                        help="What to do ?")
    args = parser.parse_args()

    if args.verbose:
        loggers.getLogger('test_names').setLevel('DEBUG')

    for action in args.actions:
        globals()['{:s}{:s}'.format(ACTION_FUNCTION_ID, action)](args.only)


if __name__ == "__main__":
    main()
