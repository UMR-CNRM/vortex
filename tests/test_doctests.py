#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals

import doctest
import unittest

from vortex import sessions
from vortex.data import geometries
from vortex.tools import delayedactions

from intairpol.tools import conftools


class utDocTests(unittest.TestCase):

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
        self.assert_doctests(conftools)


if __name__ == '__main__':
    unittest.main(verbosity=2)
