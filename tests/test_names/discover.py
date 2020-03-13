# -*- coding: utf-8 -*-

"""
Crawl into test directories and find available tests.
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
    """Class for collection of available tests (represented as TestDriver objects)."""

    _TXT_OK = 'SUCCESS'
    _FANCY_OK = '\x1b[32m{:s}\x1b[0m'
    _TXT_KO = 'FAILURE'
    _FANCY_KO = '\x1b[1;91m{:s}\x1b[0m'

    def __init__(self):
        self._tfiles = list()
        self._walk()

    def _walk(self):
        """Go through the test directories and finfg YAML files."""
        tfiles = set()
        for root, _, filenames in os.walk(TESTSPATH):
            for filename in filter(lambda f: f.endswith(STORAGEEXT), filenames):
                tfiles.add(os.path.join(root, filename)[len(TESTSPATH) + 1:])
        self._tfiles = sorted(tfiles)

    def keys(self):
        """An iterator over available test files."""
        for f in self._tfiles:
            yield f

    def __contains__(self, item):
        """Is a given test file availalble ?"""
        return item in self._tfiles

    def __len__(self):
        return len(self._tfiles)

    def __iter__(self):
        for f in self._tfiles:
            yield f

    def __getitem__(self, i):
        return self._tfiles[i]

    @core_checker.disabled_if_unavailable
    def test_load(self, tfile):
        # Delayed init... just incase yaml is missing
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
        return tfile, rc, alloutputs

    @classmethod
    def _rc_display(cls, rc):
        """Generate a string the summarise a return code."""
        txt = cls._TXT_OK if rc is True else cls._TXT_KO
        if sys.stdout.isatty():
            fmt = (cls._FANCY_OK if rc is True else cls._FANCY_KO)
        else:
            fmt = '{:s}'
        return fmt.format(txt)

    def summarise_runsequence(self, tfile, rc, outputs, verbose=False):
        print('[{:s}] {:s}'.format(self._rc_display(rc), tfile))
        if rc is not True or verbose:
            outputs.seek(0)
            print('\n--- Here is the captured output for "{:s}":\n{:s}\n---\n'
                  .format(tfile, outputs.read().strip('\n')))

    @core_checker.disabled_if_unavailable
    def alltests_runsequence(self, todo=(), verbose=False, ntasks=None, regex=None):
        if ntasks is None:
            ntasks = int(os.environ.get('VORTEX_TEST_NAMES_NTASKS', 2))
        allresults = dict()
        if regex:
            alltests = [tfile for tfile in self if regex.search(tfile)]
            if not alltests:
                return allresults
        else:
            alltests = self
        if has_futures and ntasks > 1:
            with concurrent.futures.ProcessPoolExecutor(max_workers=ntasks) as exc:
                fresults = [exc.submit(self.test_runsequence, tfile, todo)
                            for tfile in alltests]
                for fresult in concurrent.futures.as_completed(fresults):
                    tfile, rc, outputs = fresult.result()
                    self.summarise_runsequence(tfile, rc, outputs, verbose=verbose)
                    allresults[tfile] = (rc, outputs)
        else:
            for tfile in alltests:
                _, rc, outputs = self.test_runsequence(tfile, todo)
                self.summarise_runsequence(tfile, rc, outputs, verbose=verbose)
                allresults[tfile] = (rc, outputs)
        return allresults


#: Object that contains all of the available tests
all_tests = DiscoveredTests()
