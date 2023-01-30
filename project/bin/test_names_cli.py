#!/usr/bin/env python3

"""
project.bin.test_names_cli.py -- Manages Unit-Tests from the test_names package.

There are several possible actions:
* list: List all the available tests configuration files
* load: Read in the tests configuration file(s)
* loadref: Load the reference data
* compute: Run the test(s) but do not check the results
* check: Run the test(s), Load the reference data, Check the results
* dump: Dump a new set of reference data

"""

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
import contextlib
import datetime
import sys
import os
import re

# Automatically set the python path
vortexbase = re.sub('{0:}project{0:}bin$'.format(os.path.sep), '',
                    os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, os.path.join(vortexbase, 'site'))
sys.path.insert(0, os.path.join(vortexbase, 'src'))
sys.path.insert(0, os.path.join(vortexbase, 'project'))
sys.path.insert(0, os.path.join(vortexbase, 'tests'))

from bronx.fancies import loggers

logger = loggers.getLogger(__name__)

ACTION_FUNCTION_ID = '_do_action_'


def _do_action_list(args):  # @UnusedVariable
    from test_names import discover
    print()
    print('Test files located in "{:s}". Here are the available test files:'
          .format(discover.TESTSPATH))
    print()
    for f in discover.all_tests:
        print('  * ' + f)
    print()
    return dict()


def _do_sequence(args, todo):
    from test_names import discover
    print()
    if args.only:
        _, rc, ntests, outputs = discover.all_tests.test_runsequence(args.only, todo=todo)
        discover.all_tests.summarise_runsequence(args.only, rc, ntests, outputs,
                                                 verbose=args.verbose)
        return {args.only: (rc, ntests, outputs)}
    else:
        re_select = re.compile(args.regex, re.IGNORECASE) if args.regex else None
        return discover.all_tests.alltests_runsequence(todo=todo,
                                                       verbose=args.verbose,
                                                       ntasks=args.ntasks,
                                                       regex=re_select)


def _do_action_load(args):
    return _do_sequence(args, todo=())


def _do_action_compute(args):
    return _do_sequence(args, todo=('compute_results', ))


def _do_action_loadref(args):
    return _do_sequence(args, todo=('load_references', ))


def _do_action_check(args):
    return _do_sequence(args,
                        todo=('compute_results', 'load_references', 'check_results'))


def _do_action_dump(args):
    return _do_sequence(args,
                        todo=('compute_results', 'dump_results'))


@contextlib.contextmanager
def cprofile_activate(do_cprofile):
    """Profile the context manager's content."""
    if do_cprofile:
        from cProfile import Profile
        import pstats
        pr = Profile()
        pr.enable()
        try:
            yield
        finally:
            pr.disable()
            ps = pstats.Stats(pr).sort_stats('cumulative')
            radix = (os.environ['HOME'] + '/test_names_cli_' +
                     datetime.datetime.utcnow().isoformat())
            ps.dump_stats(radix + '.prof')
    else:
        yield


_ARGPARSE_EPILOG = """
Note: With Python3 (only), several actions can be launched in parallel which
      speeds up the process. The number of tasks that should be used can be
      specified:
      - using the "--ntasks" command line option;
      - by setting the "VORTEX_TEST_NAMES_NTASKS" environment variable
        (that will be ignored when running Python 2.7);
      - otherwise, the default is to use a number of tasks equal to the number
        of CPUs available on the system.
"""


def main():
    """Process command line options."""

    program_name = os.path.basename(sys.argv[0])
    program_shortdesc = program_name + ' -- ' + __import__('__main__').__doc__.lstrip("\n")
    program_desc = program_shortdesc

    # Find possible actions
    possibleactions = sorted([f[len(ACTION_FUNCTION_ID):]
                              for f in globals() if f.startswith(ACTION_FUNCTION_ID)])

    # Setup the argument parser
    parser = ArgumentParser(description=program_desc, epilog=_ARGPARSE_EPILOG,
                            formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument("-v", "--verbose", action="count", default=0,
                        help="Increase the verbosity.")
    parser.add_argument("-p", "--cprofile", action="store_true",
                        help="Profile the code using cProfile.")
    parser.add_argument("-t", "--ntasks", action="store", type=int, default=None,
                        help="The number of parallel tasks to be used (default: %(default)s)")
    parser.add_argument("-i", "--only", action='store',
                        help="Process only one test file.")
    parser.add_argument("-r", "--regex", action='store',
                        help=("Use a regex to select which test files will be considered" +
                              "(This regex will be used in a case insensitive search)."))
    parser.add_argument("actions", action='store', nargs='+', choices=possibleactions,
                        help="A list of actions to perform (see abose the list of possible actions).")
    args = parser.parse_args()

    if args.verbose >= 2:
        loggers.getLogger('test_names').setLevel('DEBUG')

    if args.cprofile:
        logger.info("The number of tasks if resetted to 1 since a cProfile " +
                    "is requested.")
        args.ntasks = 1

    global_rc = True
    with cprofile_activate(args.cprofile):
        for action in args.actions:
            mtd_todo = '{:s}{:s}'.format(ACTION_FUNCTION_ID, action)
            allresults = globals()[mtd_todo](args)
            global_rc = global_rc and all([rc is True
                                           for rc, _, _ in allresults.values()])
            global_ntests = sum([ntests for _, ntests, _ in allresults.values()])

    if not global_rc:
        print('\nWARNING: Some tests failed (a total of {:d} resource Handlers were tested).\n'
              .format(global_ntests))
        sys.exit(1)
    else:
        print('\nEverything went fine (a total of {:d} resource Handlers were tested).\n'
              .format(global_ntests))


if __name__ == "__main__":
    main()
