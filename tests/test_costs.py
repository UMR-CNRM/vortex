import os
import unittest

from arpifs_listings import cost_functions

DATADIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data'))


def _find_testfile(fname):
    return os.path.join(DATADIR, fname)


class TestListingCosts(unittest.TestCase):

    @staticmethod
    def _ingest(fname):
        filename = _find_testfile(fname)
        with open(filename) as fh:
            return (filename, [line.rstrip("\n") for line in fh])

    def test_single(self):
        l1_j = cost_functions.CostFunctions(* self._ingest('listing_minim_li5'))
        self.assertEqual(len(l1_j), 7)
        self.assertEqual(l1_j[(1, 1)].jb, 41397.7651306)
        self.assertEqual(l1_j[(999, 999)].j, 1530237.138612592)


if __name__ == '__main__':
    unittest.main()
