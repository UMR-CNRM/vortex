"""Tests both :mod:`bronx.datagrip.varbc` and :mod:`bronx.datagrip.varbcheaders`."""

import copy
import os
import unittest

from bronx.syntax.externalcode import ExternalCodeImportChecker

from bronx.datagrip import varbcheaders

# Numpy is not mandatory
npchecker = ExternalCodeImportChecker('numpy')
with npchecker as npregister:
    import numpy as np

if npchecker.is_available():
    from bronx.datagrip import varbc


DATADIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data'))


def _find_testfile(fname):
    return os.path.join(DATADIR, fname)


@unittest.skipUnless(npchecker.is_available(), 'NumPy is not available.')
class TestVarbcFile(unittest.TestCase):

    def _assert_ok_varbc(self, vbc):
        refkeys = ['4 3 4', '4 3 5', 'SARLROBH 16012128    NULL   227']
        self.assertEqual(len(vbc), 3)
        self.assertListEqual([e for e in vbc], refkeys)
        self.assertListEqual(list(vbc.keys()), refkeys)
        self.assertListEqual([e.key for e in vbc.values()], refkeys)
        self.assertListEqual([(k, e.key) for k, e in vbc.items()],
                             list(zip(refkeys, refkeys)))
        self.assertIn(refkeys[0], vbc)
        self.assertNotIn(0, vbc)
        self.assertIn(3, vbc)
        self.assertListEqual([e.type for e in vbc.values()],
                             ['rad', 'rad', 'sfcobs'])
        self.assertEqual(vbc[2].ndata, 5789)
        self.assertTrue(np.all(vbc['4 3 5'].params ==
                               np.array([0.3652, -0.06524, -0.0005376, 0.0712, -0.132, -0.07716,
                                         -0.07886, -0.02799, 0.09752, 0.02008], dtype=np.float32)))
        self.assertFalse(vbc['4 3 4'] == vbc['4 3 5'])
        self.assertTrue(vbc['4 3 4'] != 1)
        self.assertTrue(vbc['4 3 4'] == copy.copy(vbc['4 3 4']))
        with self.assertRaises(KeyError):
            vbc['4 3 95']
        with self.assertRaises(KeyError):
            vbc[1.5]
        self._assert_ok_headers(vbc.metadata)

    def _assert_ok_headers(self, vbc_h):
        self.assertEqual(vbc_h['version'], 6)
        self.assertEqual(vbc_h['date'].ymdh, '2020012306')
        self.assertEqual(vbc_h['nentries'], 3)
        self.assertEqual(vbc_h['expver'], 'TRAJ')
        self.assertSetEqual(set(vbc_h), {'version', 'date', 'nentries', 'expver'})
        self.assertEqual(len(vbc_h), 4)

    def test_varbc_read(self):
        with open(_find_testfile('varbc.arpege-traj.txt.li')) as fhvbc:
            vbc = varbc.VarbcFile(fhvbc)
        self._assert_ok_varbc(vbc)
        with open(_find_testfile('varbc.arpege-traj.txt.li.ko1')) as fhvbc:
            with self.assertRaises(ValueError):
                varbc.VarbcFile(fhvbc)
        with open(_find_testfile('varbc.arpege-traj.txt.li.ko2')) as fhvbc:
            with self.assertRaises(ValueError):
                varbc.VarbcFile(fhvbc)

    def test_varbc_headers(self):
        with open(_find_testfile('varbc.arpege-traj.txt.li')) as fhvbc:
            vbc = varbcheaders.VarbcHeadersFile(fhvbc)
        self._assert_ok_headers(vbc)
        with self.assertRaises(StopIteration):
            varbcheaders.VarbcHeadersFile(['VARBC_cycle.version006', ])
        with self.assertRaises(ValueError):
            varbcheaders.VarbcHeadersFile(['VARBC_cycle.version006', 'blop'])


if __name__ == '__main__':
    unittest.main()
