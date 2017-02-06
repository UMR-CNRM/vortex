#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import os
import unittest

import arpifs_listings
from arpifs_listings import listings, norms, jo_tables

DATADIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))


def _find_testfile(fname):
        return os.path.join(DATADIR, fname)


class TestListings(unittest.TestCase):

    L1SIZE = 3000

    def setUp(self):
        self.l1File = _find_testfile('listing_screen_li1')
        self.l1N = listings.OutputListing(self.l1File, 'norms')
        self.l1J = listings.OutputListing(self.l1File, 'Jo-tables')

    def test_single(self):
        self.assertEqual(len(self.l1N), self.L1SIZE)
        self.assertEqual(self.l1N.look_for_end(), True)
        self.l1N.parse_patterns(flush_after_reading=True)
        self.assertEqual(self.l1N.patterns_count, 1)
        self.assertIsInstance(self.l1N.norms, norms.Norms)
        self.assertEqual(len(self.l1N), self.L1SIZE)

        self.assertEqual(len(self.l1J), self.L1SIZE)
        self.assertEqual(self.l1J.look_for_end(), True)
        self.l1J.parse_patterns(flush_after_reading=True)
        self.assertEqual(self.l1J.patterns_count, 1)
        self.assertIsInstance(self.l1J.jo_tables, jo_tables.JoTables)
        self.assertEqual(len(self.l1J), self.L1SIZE)

    def test_diff_easy(self):
        self.l1N.look_for_end()
        self.l1N.parse_patterns()
        self.assertEqual(listings.compare_norms(self.l1N, self.l1N,
                                                printmode='jobs_manager', onlymaxdiff=True),
                         [None, None])
        self.assertEqual(listings.compare(self.l1N, self.l1N,
                                          printmode='jobs_manager', onlymaxdiff=True),
                         [None, None])
        self.assertEqual(arpifs_listings.compare_files(self.l1File, self.l1File,
                                                       printmode='jobs_manager', onlymaxdiff=True),
                         [None, None])


if __name__ == '__main__':
    unittest.main()