# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import io
import os
import re
import six
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
        with io.open(_find_testfile(fname), 'r') as fh:
            return [line.rstrip("\n") for line in fh]

    def test_single(self):
        l1_n = norms.NormsSet(self._ingest('listing_screen_li1'))
        self.assertEqual(len(l1_n), 7)
        self.assertDictEqual(l1_n.steps()[5], {u'subroutine': u'CNT4',
                                               u'nstep': u'0',
                                               u'pc_step': None,
                                               u'line': u' NORMS AT NSTEP CNT4    0',
                                               u'nsim4d': u'0'})

        norm = l1_n[5]
        self.assertDictEqual(norm.spnorms,
                             {u'VORTICITY': u'0.113257252552245E-04',
                              u'DIVERGENCE': u'0.963028513994313E-05',
                              u'LOG(PREHYDS)': u'0.127233694092756E-03',
                              u'TEMPERATURE': u'0.183611192189494E+00',
                              u'KINETIC ENERGY': u'0.197980105386348E+00',
                              u'HUMIDITY': '0.707998843816537E-04', })
        norm = l1_n[6]
        self.assertEqual(len(norm.gpnorms), 562)
        skeys = set([re.sub(r'^S\d+', '', k) for k in norm.gpnorms.keys()])
        self.assertSetEqual(skeys,
                            set([u'PROFRESERV.EAU', u'SURFC.OF.OZONE', u'SURFRESERV.GLACE',
                                 u'SURFAEROS.SEA', u'SURFET.GEOPOTENT', u'SURFALBEDO.SOLNU',
                                 u'SURFZ0.FOIS.G', u'SURFAEROS.SOOT', u'PROFRESERV.GLACE',
                                 u'SURFIND.VEG.DOMI', u'SURFAEROS.DESERT', u'SURFIND.FOLIAIRE',
                                 u'SURFGZ0.THERM', u'TKE', u'LIQUID_WATER', u'SURFIND.TERREMER',
                                 u'SURFB.OF.OZONE', u'SURFALBEDO NEIGE',
                                 u'SURFPROP.SABLE', u'SURFEPAIS.SOL', u'SOLID_WATER',
                                 u'SURFRESERV.INTER', u'SURFPROP.ARGILE', u'SURFVAR.GEOP.DIR',
                                 u'SNOW', u'SURFRES.EVAPOTRA', u'RAIN', u'SURFALBEDO HISTO',
                                 u'SURFEMISSIVITE', u'SURFA.OF.OZONE', u'SURFALBEDO',
                                 u'SURFALBEDO.VEG', u'SURFDENSIT.NEIGE', u'SURFVAR.GEOP.ANI',
                                 u'SURFTEMPERATURE', u'SURFRESI.STO.MIN', u'SURFRESERV.EAU',
                                 u'SURFPROP.VEGETAT', u'SURFRESERV.NEIGE', u'SURFAEROS.LAND',
                                 u'SUNSHI. DURATION', u'PROFTEMPERATURE']))
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
        self.assertSetEqual(set(ncomp.sp_comp.values()), set([0, ]))
        self.assertSetEqual(set(ncomp.gp_comp.values()), set([0, ]))
        str_out = six.StringIO()
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
        self.assertSetEqual(set(ncomp.sp_comp.values()), set([0, ]))
        self.assertSetEqual(set(ncomp.gp_comp.values()), set([0, ]))
        ncomp = norms.NormsComparison(l1_n[6], l2_n[6])
        self.assertEqual(ncomp.gp_comp['S080TKE'], 14)
        self.assertEqual(ncomp.gp_comp['S087LIQUID_WATER'], 15)
        self.assertEqual(ncomp.gp_comp['SURFIND.VEG.DOMI'], 15)
        str_out = six.StringIO()
        ncomp.write(str_out, onlymaxdiff=True)
        str_out.seek(0)
        self.assertEqual(str_out.read(), self.GPDIFFS_STR)


if __name__ == '__main__':
    unittest.main()
