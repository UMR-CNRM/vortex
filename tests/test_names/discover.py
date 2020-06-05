# -*- coding: utf-8 -*-

"""
Crawl into the tests configuration directory, find available tests and perform
operation on multiple tests configuration files.
"""

from __future__ import print_function, division, absolute_import, unicode_literals

import six
from six.moves import filter  # @UnresolvedImport

import io
import os
import sys
import traceback

from bronx.compat.moves import collections_abc
from bronx.fancies import loggers
from bronx.syntax.externalcode import ExternalCodeImportChecker

from .utils import mkdir_p, output_capture

logger = loggers.getLogger(__name__)

if six.PY3:
    import concurrent.futures
    has_futures = True
else:
    has_futures = False

core_checker = ExternalCodeImportChecker('test_names core module')
with core_checker:
    import yaml
    from .core import TestDriver

DATAPATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))
TESTSPATH = os.path.join(DATAPATH, 'namestest')
RESULTSPATH = os.path.join(DATAPATH, 'namestest_results')
REGISTERPATH = os.path.join(DATAPATH, 'namestest_register')
STORAGEEXT = '.yaml'


class DiscoveredTests(collections_abc.Sequence):
    """Class for a collection of available tests configuration files."""

    _TXT_OK = 'SUCCESS'
    _FANCY_OK = '\x1b[32m{:s}\x1b[0m'
    _TXT_KO = 'FAILURE'
    _FANCY_KO = '\x1b[1;91m{:s}\x1b[0m'

    def __init__(self):
        self._tfiles = list()
        self._walk()

    def _walk(self):
        """Go through the test directories and find YAML files."""
        tfiles = set()
        for root, _, filenames in os.walk(TESTSPATH):
            for filename in filter(lambda f: f.endswith(STORAGEEXT), filenames):
                tfiles.add(os.path.join(root, filename)[len(TESTSPATH) + 1:])
        self._tfiles = sorted(tfiles)

    def keys(self):
        """An iterator over available tests files"""
        for f in self._tfiles:
            yield f

    def __contains__(self, item):
        """Is a given test file available ?"""
        return item in self._tfiles

    def __len__(self):
        """The number of available test files."""
        return len(self._tfiles)

    def __iter__(self):
        """An iterator over available tests files"""
        return self.keys()

    def __getitem__(self, i):
        """Return the **i**-est test file."""
        return self._tfiles[i]

    @core_checker.disabled_if_unavailable
    def test_load(self, tfile):
        """Read an parse the **tfile** configuration file.

        :param tfile: the path  to the yaml file (relative to the
                      configuration files root).
        :rtype: core.TestDriver
        :return: The object representing this configuration file.
        """
        with io.open(os.path.join(TESTSPATH, tfile), 'r') as fhyaml:
            try:
                tdata = yaml.load(fhyaml, Loader=yaml.SafeLoader)
                logger.info('%s YAML read in.', tfile)
            except yaml.YAMLError as e:
                logger.error('Could not parse the YAML file: %s\n%s.', tfile, str(e))
                raise
        if tdata:
            resultfile = os.path.join(RESULTSPATH, tfile)
            mkdir_p(os.path.dirname(resultfile))
            tdriver = TestDriver(tfile, resultfile, REGISTERPATH)
            try:
                tdriver.load_test(tdata)
            except Exception:
                logger.error('Exception raised while created a TestDriver for %s.', tfile)
                raise
        return tdriver

    @core_checker.disabled_if_unavailable
    def test_runsequence(self, tfile, todo=()):
        """Run a sequence of method calls on the **tfile** configuration file.

        :param tfile: The path to the yaml file (relative to the
                      configuration files root).
        :param todo: A tuple of strings that holds names of methods to
                     execute on the :class:`~core.TestDriver` object
                     generated with the :meth:`test_load` method
                     given **tfile**.
        :return: A 4 elements tuple containing the path to the yaml file,
                 the return code (True or any exception captured during the
                 run sequance), the number of tested resource's Handlers and
                 the output generated during the run sequence.

        :note: The standard output and logging message are captured and
               returned as the fourth element of the returned tuple.

        :note: Any exception raised by the :class:`~core.TestDriver` object
               are captured and returned as the second element of the
               returned tuple
        """
        rc = True
        with loggers.contextboundRedirectStdout() as alloutputs:
            with output_capture(alloutputs):
                tdriver = self.test_load(tfile)
                for mtd in todo:
                    try:
                        getattr(tdriver, mtd)()
                    except Exception as e:
                        logger.error('Exception raised while calling "%s" for %s:\n%s',
                                     mtd, tfile, traceback.format_exc())
                        rc = e
        return tfile, rc, tdriver.ntests(), alloutputs

    @classmethod
    def _rc_display(cls, rc):
        """Generate a string the summarise a return code."""
        txt = cls._TXT_OK if rc is True else cls._TXT_KO
        if sys.stdout.isatty():
            fmt = (cls._FANCY_OK if rc is True else cls._FANCY_KO)
        else:
            fmt = '{:s}'
        return fmt.format(txt)

    def summarise_runsequence(self, tfile, rc, ntests, outputs, verbose=False):
        """
        Print a single line summarising a sequence of calls conducted by the
        :meth:`test_runsequence` method.

        :param tfile: the path to the yaml file (relative to the
                      configuration files root).
        :param rc: the return code of the run sequence.
        :param ntests: the number of tested resource's Handlers
        :param outputs: the outputs/logging messages emitted during the run
                        sequence
        :param verbose: print the outputs/logging messages even if the
                        run sequence succeeded
        """
        print('[{:s}] ({:4d} RH tested) {:s}'.format(self._rc_display(rc),
                                                     ntests, tfile))
        if rc is not True or verbose:
            outputs.seek(0)
            print('\n--- Here is the captured output for "{:s}":\n{:s}\n---\n'
                  .format(tfile, outputs.read().strip('\n')))

    @core_checker.disabled_if_unavailable
    def alltests_runsequence(self, todo=(), verbose=False, ntasks=None, regex=None):
        """Run a sequence of method calls on all of the available configuration files.

        :param todo: A tuple of strings that holds names of methods to
                     execute on each of the configuration file.
        :param verbose: Print the outputs/logging messages even if the
                        run sequence succeeded.
        :param ntasks: The number of parallel tasks that can be used (Python3
                       only).
        :param regex: A regular expression that can be used to launch the
                      **todo** methods on only a subset of configuration files
                      (whose path matches the regular expression).
        :return: A dictionary that associated the various configuration files
                 and their associated results represented as tuple (return code,
                 number of tested resource's Handlers, captured outputs).

        :seealso: The :meth:`test_runsequence` method.
        """
        if ntasks is None and 'VORTEX_TEST_NAMES_NTASKS' in os.environ:
            ntasks = int(os.environ['VORTEX_TEST_NAMES_NTASKS'])
        allresults = dict()
        if regex:
            alltests = [tfile for tfile in self if regex.search(tfile)]
            if not alltests:
                return allresults
        else:
            alltests = self
        if has_futures and (ntasks is None or ntasks > 1):
            with concurrent.futures.ProcessPoolExecutor(max_workers=ntasks) as exc:
                fresults = [exc.submit(self.test_runsequence, tfile, todo)
                            for tfile in alltests]
                for fresult in concurrent.futures.as_completed(fresults):
                    tfile, rc, ntests, outputs = fresult.result()
                    self.summarise_runsequence(tfile, rc, ntests, outputs, verbose=verbose)
                    allresults[tfile] = (rc, ntests, outputs)
        else:
            for tfile in alltests:
                _, rc, ntests, outputs = self.test_runsequence(tfile, todo)
                self.summarise_runsequence(tfile, rc, ntests, outputs, verbose=verbose)
                allresults[tfile] = (rc, ntests, outputs)
        return allresults


#: The :class:`DiscoveredTests` object that gives access to all of the
#: available configuration files.
all_tests = DiscoveredTests()
