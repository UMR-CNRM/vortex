import unittest

from bronx.syntax.pretty import smooth_string


class SmoothStringTest(unittest.TestCase):

    def test_smooth_string(self):
        expected = 'not_smooth'
        self.assertEqual(smooth_string('not smooth'), expected)
        self.assertEqual(smooth_string('not smo?oth'), expected)
        self.assertEqual(smooth_string('n{ot smooth}'), expected)
        self.assertEqual(smooth_string('not smooth*'), expected)
        self.assertEqual(smooth_string('not (smooth)'), expected)
        self.assertEqual(smooth_string('[not (smooth)]'), expected)
        self.assertEqual(smooth_string('net_smeeth', {'e': 'o'}), expected)


if __name__ == "__main__":
    unittest.main()
