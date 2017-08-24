#!/usr/bin/env python
# -*- coding:Utf-8 -*-

import unittest
import doctest

from vortex.data import geometries
from vortex.tools import date


class utDocTests(unittest.TestCase):

    def assert_doctests(self, module, **kwargs):
        rc = doctest.testmod(module, **kwargs)
        self.assertEqual(rc[0], 0,  # The error count should be 0
                         'Doctests errors {:s} for {!r}'.format(rc, module))

    def test_doctests(self):
        self.assert_doctests(date)
        self.assert_doctests(geometries)


if __name__ == '__main__':
    unittest.main(verbosity=2)
