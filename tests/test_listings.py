import os
import unittest

import arpifs_listings
from arpifs_listings import listings, norms, jo_tables

DATADIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data'))


def _find_testfile(fname):
    return os.path.join(DATADIR, fname)


class TestListings(unittest.TestCase):

    L1SIZE = 3000
    L2SIZE = 8071

    def setUp(self):
        self.l1File = _find_testfile('listing_screen_li1')
        self.l1N = listings.OutputListing(self.l1File, 'norms')
        self.l1J = listings.OutputListing(self.l1File, 'Jo-tables')
        self.l2File = _find_testfile('listing_minim_li5')
        self.l2J = listings.OutputListing(self.l2File, 'costs')

    def test_single(self):
        self.assertEqual(len(self.l1N), self.L1SIZE)
        self.assertEqual(self.l1N.look_for_end(), True)
        self.l1N.parse_patterns(flush_after_reading=True)
        self.assertEqual(self.l1N.patterns_count, 7)
        self.assertIsInstance(self.l1N.normset, norms.NormsSet)
        self.assertEqual(len(self.l1N), self.L1SIZE)

        self.assertEqual(len(self.l1J), self.L1SIZE)
        self.assertEqual(self.l1J.look_for_end(), True)
        self.l1J.parse_patterns(flush_after_reading=True)
        self.assertEqual(self.l1J.patterns_count, 1)
        self.assertIsInstance(self.l1J.jo_tables, jo_tables.JoTables)
        self.assertEqual(len(self.l1J), self.L1SIZE)

        self.assertEqual(len(self.l2J), self.L2SIZE)
        self.l2J.parse_patterns(flush_after_reading=True)
        self.assertEqual(self.l2J.patterns_count, 7)
        self.assertEqual(len(self.l2J), self.L2SIZE)

    def test_diff_easy(self):
        self.l1N.look_for_end()
        self.l1N.parse_patterns()
        self.assertEqual(listings.compare_norms(self.l1N, self.l1N,
                                                mode='get_worst',
                                                onlymaxdiff=True),
                         0)
        self.assertEqual(listings.compare(self.l1N, self.l1N,
                                          mode='get_worst',
                                          onlymaxdiff=True),
                         0)
        self.assertEqual(arpifs_listings.compare_files(self.l1File, self.l1File,
                                                       mode='get_worst',
                                                       onlymaxdiff=True),
                         0)


if __name__ == '__main__':
    unittest.main()
