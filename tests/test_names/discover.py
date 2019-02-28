# -*- coding: utf-8 -*-

"""
Crawl into test directories and find available tests.
"""

from __future__ import print_function, division, absolute_import, unicode_literals

from six.moves import filter  # @UnresolvedImport

import io
import os

from bronx.compat.moves import collections_abc
from bronx.fancies import loggers

from .utils import mkdir_p

logger = loggers.getLogger(__name__)


DATAPATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))
TESTSPATH = os.path.join(DATAPATH, 'namestest')
RESULTSPATH = os.path.join(DATAPATH, 'namestest_results')
REGISTERPATH = os.path.join(DATAPATH, 'namestest_register')


class DiscoveredTests(collections_abc.Mapping):
    """Class for collection of available tests (represented as TestDriver objects)."""

    def __init__(self):
        self._tfiles = list()
        self._tdrivers = dict()
        self.walk()

    def walk(self):
        """Go through the test directories and finfg YAML files."""
        tfiles = set()
        for root, _, filenames in os.walk(TESTSPATH):
            for filename in filter(lambda f: f.endswith('.yaml'), filenames):
                tfiles.add(os.path.join(root, filename))
        self._tfiles = sorted(tfiles)

    def keys(self):
        """An iterator over available test files."""
        for f in self._tfiles:
            yield f

    def values(self):
        """An iterator over available TestDriver objects."""
        for f in self._tfiles:
            yield self[f]

    def items(self):
        """An iterator over available (File names,TestDriver) pairs."""
        for f in self._tfiles:
            yield f, self[f]

    def __contains__(self, item):
        """Is a given test file availalble ?"""
        return item in self._tfiles

    def __len__(self):
        return len(self._tfiles)

    def __iter__(self):
        for f in self._tfiles:
            yield f

    @staticmethod
    def shorten_names(tfile):
        """Give a nice and short representation of teh test filename."""
        # Remove TESTSPATH and the .yaml extension
        return tfile[len(TESTSPATH):-5].replace(os.path.sep, '_')

    def _load_test(self, tfile):
        # Delayed init... just incas yaml is missing
        import yaml
        from .core import TestDriver
        with io.open(tfile, 'r') as fhyaml:
            try:
                tdata = yaml.load(fhyaml)
                logger.info('%s YAML read in.', tfile)
            except yaml.YAMLError as e:
                logger.error('Could not parse the YAML file: %s\n%s.', tfile, str(e))
                raise
        if tdata:
            resultfile = RESULTSPATH + tfile[len(TESTSPATH):]
            mkdir_p(os.path.dirname(resultfile))
            tdriver = TestDriver(tfile, resultfile, REGISTERPATH)
            try:
                tdriver.load_test(tdata)
            except:  # @IgnorePep8
                logger.error('Exception raised while created a TestDriver for %s.', tfile)
                raise
            self._tdrivers[tfile] = tdriver

    def __getitem__(self, f):
        if f not in self._tdrivers:
            self._load_test(f)
        return self._tdrivers[f]

    def all_clear(self):
        """Delete all test drivers."""
        self._tdrivers = dict()

    def _all_iter(self, callback, actionmsg):
        for tfile, td in self.items():
            try:
                callback(td)
            except:  # @IgnorePep8
                logger.error('Exception raised while %s for %s.',
                             actionmsg, self.shorten_names(tfile))
                raise
            else:
                logger.info('%s for %s went fine.', actionmsg, self.shorten_names(tfile))

    def all_load(self):
        """Load all of the YAML files."""
        self.all_clear()
        self._all_iter(lambda td: td, 'loading tests')

    def all_compute_results(self):
        """Launch all the tests."""
        self._all_iter(lambda td: td.compute_results(), 'computing results')

    def all_dump_results(self):
        """Dump all the test results into reference files."""
        self._all_iter(lambda td: td.dump_results(), 'dumping results')

    def all_load_references(self):
        """Load all of the reference data."""
        self._all_iter(lambda td: td.load_references(), 'loading references')

    def all_check_results(self):
        """Check all the computed values against reference data."""
        self._all_iter(lambda td: td.check_results(), 'checking results')


#: Object that contains all of the available tests
all_tests = DiscoveredTests()
