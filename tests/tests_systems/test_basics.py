import unittest

from vortex.tools.systems import PythonSimplifiedVersion as PVClass


class TestSystemsBasics(unittest.TestCase):

    def test_python_version(self):
        with self.assertRaises(ValueError):
            PVClass('3.4')
        with self.assertRaises(ValueError):
            PVClass('Grr')
        self.assertEqual(PVClass('3.4.5'), PVClass('3.4.5c'))
        self.assertEqual(hash(PVClass('3.4.5')), hash(PVClass('3.4.5c')))
        self.assertEqual(str(PVClass('3.4.5c')), '3.4.5')
        self.assertEqual(PVClass('3.4.5c').version, (3, 4, 5))
        self.assertGreater(PVClass('3.5.10'), PVClass('3.4.5'))
        self.assertNotEqual(hash(PVClass('3.5.10')), hash(PVClass('3.4.5')))


if __name__ == "__main__":
    unittest.main(verbosity=2)
