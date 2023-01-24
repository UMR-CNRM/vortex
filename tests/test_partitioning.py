import contextlib
import unittest

from bronx.fancies.loggers import unittestGlobalLevel

from common.data.namelists import NamelistContent
from common.tools.partitioning import setup_partitioning_in_namelist, PartitioningError

tloglevel = 'ERROR'


class DummyNamContainer:

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
                N_EW=__PART_TASKS2D_X_XCLOSETO_2__,
                N_NS=__PART_TASKS2D_Y_XCLOSETO_2__,
                N_OMPX=__PART_THREADS2D_X_XCLOSETO_2__,
                N_OMPY=__PART_THREADS2D_Y_XCLOSETO_2__,
            /""")
        self.assertTrue(setup_partitioning_in_namelist(cont, 16, 8, 'fake'))
        self.assertEqual(cont.macros()['PART_TASKS2D_X_XCLOSETO_2'], 2)
        self.assertEqual(cont.macros()['PART_TASKS2D_Y_XCLOSETO_2'], 8)
        self.assertEqual(cont.macros()['PART_THREADS2D_X_XCLOSETO_2'], 2)
        self.assertEqual(cont.macros()['PART_THREADS2D_Y_XCLOSETO_2'], 4)
        cont = self._get_namcontents("""
            &NAMTRUC
                N_EW=__PART_TASKS2D_X_SQUARE__,
                N_NS=__PART_TASKS2D_Y_SQUARE__,
            /""")
        self.assertTrue(setup_partitioning_in_namelist(cont, 16, 8))
        self.assertEqual(cont.macros()['PART_TASKS2D_X_SQUARE'], 4)
        self.assertEqual(cont.macros()['PART_TASKS2D_Y_SQUARE'], 4)
        cont = self._get_namcontents("""
            &NAMTRUC
                N_EW=__PART_TASKS2D_X_ASPECT_3_1__,
                N_NS=__PART_TASKS2D_Y_ASPECT_3_1__,
            /""")
        self.assertTrue(setup_partitioning_in_namelist(cont, 32, 8))
        self.assertEqual(cont.macros()['PART_TASKS2D_X_ASPECT_3_1'], 8)
        self.assertEqual(cont.macros()['PART_TASKS2D_Y_ASPECT_3_1'], 4)
        # Correct but nothing to do...
        cont = self._get_namcontents("""
                &NAMTRUC
                    N_EW=__NBPROC__,
                    N_NS=1,
                /""")
        self.assertFalse(setup_partitioning_in_namelist(cont, 16, 8))
        # Wrong partitioning method name
        cont = self._get_namcontents("""
            &NAMTRUC
                N_EW=__PART_TASKS2D_X_DUMMY__,
            /""")
        with self.assertRaises(PartitioningError):
            setup_partitioning_in_namelist(cont, 16, 8)
