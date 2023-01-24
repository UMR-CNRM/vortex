import unittest

from bronx.datagrip.namelist import namparse, FIRST_ORDER_SORTING
from bronx.fancies import loggers
import footprints

import common.tools.ifstools

assert common.tools.ifstools

tloglevel = 'critical'

_PRE_NAM46 = """
&NAMOPH
  LINC=.FALSE.,
/
&NAMCT0
  NFPOS=2,
  NFRPOS=1,
/
"""

_RES_NAM46_1 = """\
 &NAMCT0
   NFPOS=2,
   NHISTS(0)=-4,
   NHISTS(1)=-1,
   NHISTS(2)=-3,
   NHISTS(3)=-6,
   NHISTS(4)=-12,
   NPOSTS(0)=-2,
   NPOSTS(1)=-3,
   NPOSTS(2)=-6,
   NSFXHISTS(0)=-4,
   NSFXHISTS(1)=-1,
   NSFXHISTS(2)=-3,
   NSFXHISTS(3)=-6,
   NSFXHISTS(4)=-12,
 /
 &NAMCT1
   N1HIS=1,
   N1POS=1,
   N1SFXHIS=1,
 /
 &NAMOPH
   LINC=.TRUE.,
 /
"""

_RES_NAM46_2 = """\
 &NAMCT0
   NFPOS=0,
   NHISTS(0)=-4,
   NHISTS(1)=-1,
   NHISTS(2)=-3,
   NHISTS(3)=-6,
   NHISTS(4)=-12,
   NSFXHISTS(0)=-2,
   NSFXHISTS(1)=-1,
   NSFXHISTS(2)=-3,
   NSFXHISTSMIN(1)=0,
   NSFXHISTSMIN(2)=15,
 /
 &NAMCT1
   N1HIS=1,
   N1POS=0,
   N1SFXHIS=1,
 /
 &NAMOPH
   LINC=.TRUE.,
 /
"""

_RES_NAM46_3 = """\
 &NAMCT0
   NFPOS=1,
   NPOSTS(0)=-1,
   NPOSTS(1)=-1,
   NSFXHISTS(0)=-1,
   NSFXHISTS(1)=-1,
 /
 &NAMCT1
   N1HIS=0,
   N1POS=1,
   N1SFXHIS=1,
 /
 &NAMOPH
   LINC=.TRUE.,
 /
"""

_RES_NAM46_4 = """\
 &NAMCT0
   NFPOS=0,
   NHISTS(0)=4,
   NHISTS(1)=1,
   NHISTS(2)=3,
   NHISTS(3)=6,
   NHISTS(4)=12,
 /
 &NAMCT1
   N1HIS=1,
   N1POS=0,
 /
 &NAMOPH
   LINC=.FALSE.,
 /
"""


@loggers.unittestGlobalLevel(tloglevel)
class TestIfsOutputsConfigurator(unittest.TestCase):

    def _load_tool(self, model, cycle, unit):
        mytool = footprints.proxy.ifsoutputs_configurator(
            model=model, cycle=cycle, fcterm_unit=unit
        )
        self.assertIsNotNone(mytool)
        return mytool

    @staticmethod
    def _load_nam(txt):
        return namparse(txt)

    def test_outputs_conf_cy43_1(self):
        ct = self._load_tool('arpege', 'cy43', 'h')
        nstart = self._load_nam(_PRE_NAM46)
        self.assertFalse(ct(nstart, 'fake.4'))
        ct.modelstate = [1, 3, 6, 12]
        ct.surf_modelstate = [1, 3, 6, 12]
        ct.post_processing = [3, 6]
        with self.assertRaises(ValueError):
            ct.modelstate = 'Toto'
        self.assertTrue(ct(nstart, 'fake.4'))
        self.assertEqual(_RES_NAM46_1,
                         nstart.dumps(sorting=FIRST_ORDER_SORTING, block_sorting=True))
        del ct.modelstate  # Tricky: won't change anything since modelstate besomes None
        ct.spectral_diag = None
        ct.post_processing = []
        ct.surf_modelstate = [1, '3:15']
        self.assertTrue(ct(nstart, 'fake.4'))
        self.assertEqual(_RES_NAM46_2,
                         nstart.dumps(sorting=FIRST_ORDER_SORTING, block_sorting=True))
        ct.modelstate = []
        ct.post_processing = [1, ]
        ct.surf_modelstate = [1, ]
        self.assertTrue(ct(nstart, 'fake.4'))
        self.assertEqual(_RES_NAM46_3,
                         nstart.dumps(sorting=FIRST_ORDER_SORTING, block_sorting=True))
        ct = self._load_tool('arpege', 'cy43', 't')
        nstart = self._load_nam(_PRE_NAM46)
        ct.post_processing = []
        ct.modelstate = [1, 3, 6, 12]
        self.assertEqual([1, 3, 6, 12], ct.modelstate)
        self.assertTrue(ct(nstart, 'fake.4'))
        self.assertEqual(_RES_NAM46_4,
                         nstart.dumps(sorting=FIRST_ORDER_SORTING, block_sorting=True))

    def test_outputs_conf_cy46_t1(self):
        ct = self._load_tool('arpege', 'cy46t1', 'h')
        nstart = self._load_nam(_PRE_NAM46)
        ct.modelstate = [1, 3, 6, 12]
        ct.spectral_diag = None
        ct.post_processing = []
        ct.surf_modelstate = [1, '3:15']
        self.assertTrue(ct(nstart, 'fake.4'))
        # This part is cy46 specific
        self.assertEqual(nstart['NAMCT0']['NSFXHISTSMIN(0)'], 2)
        del nstart['NAMCT0']['NSFXHISTSMIN(0)']
        # End of cy46 part
        self.assertEqual(_RES_NAM46_2,
                         nstart.dumps(sorting=FIRST_ORDER_SORTING, block_sorting=True))


if __name__ == "__main__":
    unittest.main()
