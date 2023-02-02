import unittest

from bronx.system.memory import convert_bytes_in_unit


class TestMemory(unittest.TestCase):

    def test_bytes_convert(self):
        self.assertEqual(convert_bytes_in_unit(1024, 'B'), 1024)
        self.assertEqual(convert_bytes_in_unit(1024., 'B'), 1024.)
        self.assertEqual(convert_bytes_in_unit(1024, 'KB'), 1.024)
        self.assertEqual(convert_bytes_in_unit(1073741824., 'GB'), 1.073741824)
        self.assertEqual(convert_bytes_in_unit(1073741824, 'GiB'), 1.)
        with self.assertRaises(ValueError):
            self.assertEqual(convert_bytes_in_unit(1073741824, 'TOTO'))


if __name__ == '__main__':
    unittest.main()
