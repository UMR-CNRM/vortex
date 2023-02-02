import io
import os
import re
import unittest

from arpifs_listings import norms

DATADIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data'))


def _find_testfile(fname):
    return os.path.join(DATADIR, fname)


class TestListingNorms(unittest.TestCase):

    NODIFFS_STR = """### SPECTRAL NORMS ###
######################
         Worst norm comparison --> =====================
### GRIDPOINT NORMS ###
######################
         Worst norm comparison --> =====================
"""

    GPDIFFS_STR = """### GRIDPOINT NORMS ###
######################
         Worst norm comparison --> 15 last digits differ
"""

    @staticmethod
    def _ingest(fname):
        with open(_find_testfile(fname)) as fh:
            return [line.rstrip("\n") for line in fh]

    def test_single(self):
        l1_n = norms.NormsSet(self._ingest('listing_screen_li1'))
        self.assertEqual(len(l1_n), 7)
        self.assertDictEqual(l1_n.steps()[5], {'subroutine': 'CNT4',
                                               'nstep': '0',
                                               'pc_step': None,
                                               'line': ' NORMS AT NSTEP CNT4    0',
                                               'nsim4d': '0'})

        norm = l1_n[5]
        self.assertDictEqual(norm.spnorms,
                             {'VORTICITY': '0.113257252552245E-04',
                              'DIVERGENCE': '0.963028513994313E-05',
                              'LOG(PREHYDS)': '0.127233694092756E-03',
                              'TEMPERATURE': '0.183611192189494E+00',
                              'KINETIC ENERGY': '0.197980105386348E+00',
                              'HUMIDITY': '0.707998843816537E-04', })
        norm = l1_n[6]
        self.assertEqual(len(norm.gpnorms), 562)
        skeys = {re.sub(r'^S\d+', '', k) for k in norm.gpnorms.keys()}
        self.assertSetEqual(skeys,
                            {'PROFRESERV.EAU', 'SURFC.OF.OZONE', 'SURFRESERV.GLACE',
                             'SURFAEROS.SEA', 'SURFET.GEOPOTENT', 'SURFALBEDO.SOLNU',
                             'SURFZ0.FOIS.G', 'SURFAEROS.SOOT', 'PROFRESERV.GLACE',
                             'SURFIND.VEG.DOMI', 'SURFAEROS.DESERT', 'SURFIND.FOLIAIRE',
                             'SURFGZ0.THERM', 'TKE', 'LIQUID_WATER', 'SURFIND.TERREMER',
                             'SURFB.OF.OZONE', 'SURFALBEDO NEIGE',
                             'SURFPROP.SABLE', 'SURFEPAIS.SOL', 'SOLID_WATER',
                             'SURFRESERV.INTER', 'SURFPROP.ARGILE', 'SURFVAR.GEOP.DIR',
                             'SNOW', 'SURFRES.EVAPOTRA', 'RAIN', 'SURFALBEDO HISTO',
                             'SURFEMISSIVITE', 'SURFA.OF.OZONE', 'SURFALBEDO',
                             'SURFALBEDO.VEG', 'SURFDENSIT.NEIGE', 'SURFVAR.GEOP.ANI',
                             'SURFTEMPERATURE', 'SURFRESI.STO.MIN', 'SURFRESERV.EAU',
                             'SURFPROP.VEGETAT', 'SURFRESERV.NEIGE', 'SURFAEROS.LAND',
                             'SUNSHI. DURATION', 'PROFTEMPERATURE'})
        # Empty equals
        self.assertEqual(norms.NormsSet([]),
                         norms.NormsSet([]))
        self.assertTrue(norms.NormsSet([]).steps_equal(norms.NormsSet([])))

    def test_diff_easy(self):
        # Norm comparison
        l1_n = norms.NormsSet(_find_testfile('listing_screen_li1'))
        l2_n = norms.NormsSet(_find_testfile('listing_screen_li1'))
        self.assertEqual(l1_n, l2_n)
        self.assertTrue(l1_n.steps_equal(l2_n))
        self.assertEqual(l1_n[0], l2_n[0])
        # Rich comparison
        ncomp = norms.NormsComparison(l1_n[5], l2_n[5])
        self.assertIs(ncomp.get_worst(), 0)
        self.assertSetEqual(set(ncomp.sp_comp.values()), {0})
        self.assertSetEqual(set(ncomp.gp_comp.values()), {0})
        str_out = io.StringIO()
        ncomp.write(str_out, onlymaxdiff=True)
        str_out.seek(0)
        self.assertEqual(str_out.read(), self.NODIFFS_STR)

    def test_diff_blurp(self):
        # Norm comparison
        l1_n = norms.NormsSet(_find_testfile('listing_screen_li1'))
        l2_n = norms.NormsSet(_find_testfile('listing_screen_li2'))
        self.assertNotEqual(l1_n, l2_n)
        self.assertTrue(l1_n.steps_equal(l2_n))
        self.assertEqual(l1_n[2], l2_n[2])
        self.assertNotEqual(l1_n[3], l2_n[3])
        # Rich comparison
        ncomp = norms.NormsComparison(l1_n[5], l2_n[5])
        self.assertEqual(ncomp.get_worst(), 0)
        self.assertSetEqual(set(ncomp.sp_comp.values()), {0})
        self.assertSetEqual(set(ncomp.gp_comp.values()), {0})
        ncomp = norms.NormsComparison(l1_n[6], l2_n[6])
        self.assertEqual(ncomp.gp_comp['S080TKE'], 14)
        self.assertEqual(ncomp.gp_comp['S087LIQUID_WATER'], 15)
        self.assertEqual(ncomp.gp_comp['SURFIND.VEG.DOMI'], 15)
        str_out = io.StringIO()
        ncomp.write(str_out, onlymaxdiff=True)
        str_out.seek(0)
        self.assertEqual(str_out.read(), self.GPDIFFS_STR)


if __name__ == '__main__':
    unittest.main()
