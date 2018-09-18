# -*- coding: utf-8 -*-

"""
Defines an UnitTest class that can be launched using Nose.

The tests will be skipped if PyYAML is missing.
"""

from __future__ import print_function, division, absolute_import, unicode_literals

from unittest import TestCase, SkipTest

import footprints as fp

from . import discover


logger = fp.loggers.getLogger(__name__)
clogger = fp.loggers.getLogger('.'.join(__name__.split('.')[:-1]))

try:
    import yaml
except ImportError:
    yaml = None
    logger.error("The PyYAML package seems to be missing. test_names is not usable (skipping tests)")


def generate_driverrun_method(methodname, f):
    """Dynamically generate a test method for a given test file."""

    def generic_test_names(self):
        self._names_driverrun(f)

    generic_test_names.__name__ = str(methodname)
    return generic_test_names


def generate_driverrun_methods(cls):
    """Decorator that adds test methods to the TestNames class."""
    for f in discover.all_tests:
        mtdname = 'test_names{:s}'.format(discover.all_tests.shorten_names(f))
        setattr(cls, mtdname, generate_driverrun_method(mtdname, f))
    return cls


@generate_driverrun_methods
class TestNames(TestCase):

    def setUp(self):
        super(TestNames, self).setUp()
        if yaml is None:
            raise SkipTest("PyYAML seems to be missing")

    def _names_driverrun(self, f):
        """Generic test method."""
        oldlevel = clogger.level
        clogger.setLevel('ERROR')
        try:
            td = discover.all_tests[f]
            td.load_references()
            td.compute_results()
            td.check_results()
        finally:
            clogger.setLevel(oldlevel)
