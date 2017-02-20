
import os
import unittest

from gco.tools import genv

DATAPATHTEST = os.path.join(os.path.dirname(__file__), 'data')


class TestGcoGenv(unittest.TestCase):

    def setUp(self):
        self._ini_genvcmd = genv.genvcmd
        genv.genvcmd = 'fake_genv.py'
        self._ini_genvpath = genv.genvpath
        genv.genvpath = DATAPATHTEST

    def tearDown(self):
        genv.genvcmd = self._ini_genvcmd
        genv.genvpath = self._ini_genvpath

    def test_basics(self):
        # Test genv autofill
        genv.autofill('cy42_op2.06')
        # Test DSI like autofill
        with open(os.path.join(DATAPATHTEST, 'cy42_peace-op2.01.genv')) as fh:
            gdata = fh.read().rstrip('\n').split('\n')
        genv.autofill('cy42_peace-op2.01', gdata)
        # Check keys
        self.assertItemsEqual(genv.cycles(),
                              ('cy42_op2.06', 'cy42_peace-op2.01'))
        # Clear
        genv.clearall()
        self.assertItemsEqual(genv.cycles(), ())
        # Start again...
        genv.autofill('cy42_op2.06')
        genv.autofill('blop', gdata)
        self.assertItemsEqual(genv.cycles(),
                              ('cy42_op2.06', 'cy42_peace-op2.01'))
        # Access it ?
        realstuff = [line for line in gdata if not line.startswith('CYCLE_NAME=')]
        self.assertItemsEqual(genv.nicedump(cycle='cy42_peace-op2.01'),
                              realstuff)
        cy = genv.contents(cycle='cy42_op2.06')
        self.assertEqual(cy.TOOLS_LFI, "tools.lfi.05.tgz")
        # cy should be a cipy of the real thing...
        cy.TOOLS_LFI = 'trash'
        clean_cy = genv.contents(cycle='cy42_op2.06')
        self.assertEqual(clean_cy.TOOLS_LFI, "tools.lfi.05.tgz")
        # Still, it is possible to update things
        # Originally index 15 is: PGD_FA="pgd_pearp.t798.01.fa"
        gdata[15] = 'PGD_FA="trash"'
        genv.autofill('blop', gdata)
        cy = genv.contents(cycle='cy42_peace-op2.01')
        self.assertEqual(cy.PGD_FA, "trash")

if __name__ == "__main__":
    unittest.main(verbosity=2)
