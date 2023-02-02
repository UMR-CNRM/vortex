import itertools
import unittest

from bronx.compat.itertools import pairwise


class TestPairwise(unittest.TestCase):

    def test_normalpairs(self):
        item = pairwise([1, 2, 3, ])
        self.assertEqual(list(item), [(1, 2), (2, 3), ])

    def test_nopair(self):
        item = pairwise([1, ])
        self.assertEqual(list(item), [])

    def test_empty(self):
        item = pairwise([])
        self.assertEqual(list(item), [])

    def test_islice(self):
        """Check that we don't interfere with Python's itertools."""
        item = ''.join(itertools.islice('ABCDEFG', 0, None, 2))
        self.assertEqual(item, 'ACEG')


if __name__ == "__main__":
    unittest.main()
