import doctest
import unittest

from vortex import sessions
from vortex.data import geometries
from vortex.tools import delayedactions
from vortex.util import worker

from common.tools import partitioning
from common.tools import conftools as common_conftools

from intairpol.tools import conftools as interpol_conftools


class UtDocTests(unittest.TestCase):

    def assert_doctests(self, module, **kwargs):
        rc = doctest.testmod(module, **kwargs)
        self.assertEqual(rc[0], 0,  # The error count should be 0
                         'Doctests errors {!s} for {!r}'.format(rc, module))

    def test_doctests(self):
        self.assert_doctests(geometries)
        try:
            self.assert_doctests(delayedactions)
        finally:
            # Clean the mess
            t = sessions.current()
            a_hub = t.context.delayedactions_hub
            t.sh.rmtree(a_hub.stagedir)
            a_hub.clear()
        self.assert_doctests(worker)
        self.assert_doctests(partitioning)
        self.assert_doctests(common_conftools)
        self.assert_doctests(interpol_conftools)


if __name__ == '__main__':
    unittest.main(verbosity=2)
