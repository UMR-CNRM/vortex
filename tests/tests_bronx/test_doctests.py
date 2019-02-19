#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import doctest
import unittest

from bronx.datagrip import namelist
from bronx.fancies import display, loggers
from bronx.patterns import getbytag, observer
from bronx.stdtypes import date, history, tracking, xtemplates
from bronx.syntax import iterators, minieval


class utDocTests(unittest.TestCase):

    def assert_doctests(self, module, **kwargs):
        rc = doctest.testmod(module, **kwargs)
        self.assertEqual(rc[0], 0,  # The error count should be 0
                         'Doctests errors {!s} for {!r}'.format(rc, module))

    def test_doctests(self):
        self.assert_doctests(namelist)
        self.assert_doctests(display)
        self.assert_doctests(loggers)
        self.assert_doctests(getbytag)
        self.assert_doctests(observer)
        self.assert_doctests(date)
        self.assert_doctests(history)
        self.assert_doctests(tracking)
        self.assert_doctests(xtemplates)
        self.assert_doctests(iterators)
        self.assert_doctests(minieval)


if __name__ == '__main__':
    unittest.main(verbosity=2)
