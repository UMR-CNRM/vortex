# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import contextlib
import unittest

from bronx.fancies.loggers import unittestGlobalLevel

from common.data.namelists import NamelistContent
from common.tools.partitioning import setup_partitioning_in_namelist, PartitioningError

tloglevel = 'ERROR'


class DummyNamContainer(object):

    def __init__(self, thetxt):
        self.mytxt = thetxt

    def rewind(self):
        pass

    def read(self):
        return self.mytxt

    def close(self):
        pass

    def write(self, thetxt):
        self.mytxt = thetxt

    @contextlib.contextmanager
    def preferred_decoding(self, *kargs, **kwargs):
        yield


@unittestGlobalLevel(tloglevel)
class UtPartitioning(unittest.TestCase):

    @staticmethod
    def _get_namcontents(txt):
        cont = DummyNamContainer(txt)
        ncontents = NamelistContent()
        ncontents.slurp(cont)
        return ncontents

    def test_partitioning_in_namelists(self):
        # Working scenarios
        cont = self._get_namcontents("""
            &NAMTRUC
                N_EW=__PART2D_X_XCLOSETO_2__,
                N_NS=__PART2D_Y_XCLOSETO_2__,
            /""")
        self.assertTrue(setup_partitioning_in_namelist(cont, 16, 'fake'))
        self.assertEqual(cont.macros()['PART2D_X_XCLOSETO_2'], 2)
        self.assertEqual(cont.macros()['PART2D_Y_XCLOSETO_2'], 8)
        cont = self._get_namcontents("""
            &NAMTRUC
                N_EW=__PART2D_X_SQUARE__,
                N_NS=__PART2D_Y_SQUARE__,
            /""")
        self.assertTrue(setup_partitioning_in_namelist(cont, 16))
        self.assertEqual(cont.macros()['PART2D_X_SQUARE'], 4)
        self.assertEqual(cont.macros()['PART2D_Y_SQUARE'], 4)
        cont = self._get_namcontents("""
            &NAMTRUC
                N_EW=__PART2D_X_ASPECT_3_1__,
                N_NS=__PART2D_Y_ASPECT_3_1__,
            /""")
        self.assertTrue(setup_partitioning_in_namelist(cont, 32))
        self.assertEqual(cont.macros()['PART2D_X_ASPECT_3_1'], 8)
        self.assertEqual(cont.macros()['PART2D_Y_ASPECT_3_1'], 4)
        # Correct but nothing to do...
        cont = self._get_namcontents("""
                &NAMTRUC
                    N_EW=__NBPROC__,
                    N_NS=1,
                /""")
        self.assertFalse(setup_partitioning_in_namelist(cont, 16))
        # Wrong partitioning method name
        cont = self._get_namcontents("""
            &NAMTRUC
                N_EW=__PART2D_X_DUMMY__,
            /""")
        with self.assertRaises(PartitioningError):
            setup_partitioning_in_namelist(cont, 16)
