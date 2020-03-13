# -*- coding: utf-8 -*-

"""
Defines an UnitTest class that can be launched using Nose.

The tests will be skipped if PyYAML is missing.
"""

from __future__ import print_function, division, absolute_import, unicode_literals

from unittest import TestCase, SkipTest

from bronx.fancies import loggers

with loggers.contextboundGlobalLevel('error'):
    from . import discover

logger = loggers.getLogger(__name__)


try:
    import yaml
except ImportError:
    yaml = None
    logger.error("The PyYAML package seems to be missing. test_names is not usable (skipping tests)")


class TestNames(TestCase):

    def setUp(self):
        super(TestNames, self).setUp()
        if yaml is None:
            raise SkipTest("PyYAML seems to be missing")

    def test_all_names(self):
        allresults = discover.all_tests.alltests_runsequence(('compute_results',
                                                              'load_references',
                                                              'check_results'))
        self.assertTrue(all([rc is True for rc, _ in allresults.values()]),
                        'Some of the name check failed (see the output)')
