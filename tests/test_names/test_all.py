"""
Defines an UnitTest class that can be launched using Nose.

The tests will be skipped if PyYAML is missing.
"""

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


@loggers.unittestGlobalLevel('info')
class TestNames(TestCase):
    """The TestDriver class to run names tests."""

    def setUp(self):
        """Check if PyYAML is available."""
        super().setUp()
        if yaml is None:
            raise SkipTest("PyYAML seems to be missing")

    def test_all_names(self):
        """Actualy tests all the configured resource's Handlers."""
        allresults = discover.all_tests.alltests_runsequence(('compute_results',
                                                              'load_references',
                                                              'check_results'))
        self.assertTrue(all([rc is True for rc, _, _ in allresults.values()]),
                        'Some of the name check failed (see the output)')
