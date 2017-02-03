#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import os
import re
import six
import unittest

from arpifs_listings import norms

DATADIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))


def _find_testfile(fname):
        return os.path.join(DATADIR, fname)


class TestListingNorms(unittest.TestCase):

    NODIFFS_STR = """### SPECTRAL NORMS ###
######################
         Worst norm comparison --> =========================
### GRIDPOINT NORMS ###
######################
         Worst norm comparison --> =========================
"""

    GPDIFFS_STR = """### SPECTRAL NORMS ###
######################
         Worst norm comparison --> =========================
### GRIDPOINT NORMS ###
######################
         Worst norm comparison --> identical up to  0 digits
"""

    @staticmethod
    def _ingest(fname):
        with open(_find_testfile(fname), 'r') as fh:
            return [l.rstrip("\n") for l in fh]

    def test_single(self):
        l1_n = norms.Norms(self._ingest('listing_screen_li1'))
        self.assertEqual(len(l1_n), 1)
        self.assertListEqual(l1_n.steps(), [0, ])
        self.assertListEqual(l1_n.get_first_and_last_norms_indexes(),
                             [(0, [None]), (0, [None])])
        norm = l1_n[0]
        norm = norm[None]
        self.assertEqual(norm.nstep, 0)
        self.assertEqual(norm.substep, None)
        self.assertDictEqual(norm.spnorms,
                             {u'VORTICITY': u'0.113257252552245E-04',
                              u'DIVERGENCE': u'0.963028513994313E-05',
                              u'LOG(PREHYDS)': u'0.127233694092756E-03',
                              u'TEMPERATURE': u'0.183611192189494E+00',
                              u'KINETIC ENERGY': u'0.197980105386348E+00'})
        self.assertEqual(len(norm.gpnorms), 568)
        skeys = set([re.sub(r'^S\d+', '', k) for k in norm.gpnorms.keys()])
        self.assertSetEqual(skeys,
                            set([u'PROFRESERV.EAU', u'SURFC.OF.OZONE', u'SURFRESERV.GLACE',
                                 u'SURFAEROS.SEA', u'SURFET.GEOPOTENT', u'SURFALBEDO.SOLNU',
                                 u'SURFZ0.FOIS.G', u'SURFAEROS.SOOT', u'PROFRESERV.GLACE',
                                 u'SURFIND.VEG.DOMI', u'SURFAEROS.DESERT', u'SURFIND.FOLIAIRE',
                                 u'SURFGZ0.THERM', u'TKE', u'LIQUID_WATER', u'SURFIND.TERREMER',
                                 u'SURFB.OF.OZONE', u'CV_PREC_FLUX', u'SURFALBEDO NEIGE',
                                 u'SURFPROP.SABLE', u'SURFEPAIS.SOL', u'SOLID_WATER',
                                 u'SURFRESERV.INTER', u'SURFPROP.ARGILE', u'SURFVAR.GEOP.DIR',
                                 u'SNOW', u'SURFRES.EVAPOTRA', u'RAIN', u'SURFALBEDO HISTO',
                                 u'SURFEMISSIVITE', u'SURFA.OF.OZONE', u'SURFALBEDO',
                                 u'SURFALBEDO.VEG', u'SURFDENSIT.NEIGE', u'SURFVAR.GEOP.ANI',
                                 u'SURFTEMPERATURE', u'SURFRESI.STO.MIN', u'SURFRESERV.EAU',
                                 u'SURFPROP.VEGETAT', u'SURFRESERV.NEIGE', u'SURFAEROS.LAND',
                                 u'SUNSHI. DURATION', u'PROFTEMPERATURE']))

    def test_diff_easy(self):
        # Norm comparison
        l1_n = norms.Norms(_find_testfile('listing_screen_li1'))
        l2_n = norms.Norms(_find_testfile('listing_screen_li1'))
        self.assertEqual(l1_n[0][None], l2_n[0][None])
        # Rich comparison
        ncomp = norms.NormComparison(l1_n[0][None], l2_n[0][None])
        self.assertIs(ncomp.get_worst(), None)
        self.assertSetEqual(set(ncomp.sp_comp.values()), set([None, ]))
        self.assertSetEqual(set(ncomp.gp_comp.values()), set([None, ]))
        str_out = six.StringIO()
        ncomp.write(str_out, onlymaxdiff=True)
        str_out.seek(0)
        self.assertEqual(str_out.read(), self.NODIFFS_STR)

    def test_diff_blurp(self):
        # Norm comparison
        l1_n = norms.Norms(_find_testfile('listing_screen_li1'))
        l2_n = norms.Norms(_find_testfile('listing_screen_li2'))
        self.assertNotEqual(l1_n[0][None], l2_n[0][None])
        # Rich comparison
        ncomp = norms.NormComparison(l1_n[0][None], l2_n[0][None])
        self.assertEqual(ncomp.get_worst(), 0)
        self.assertSetEqual(set(ncomp.sp_comp.values()), set([None, ]))
        self.assertSetEqual(set(ncomp.gp_comp.values()), set([None, 1, 0]))
        self.assertEqual(ncomp.gp_comp['S080TKE'], 1)
        self.assertEqual(ncomp.gp_comp['S087LIQUID_WATER'], 0)
        self.assertEqual(ncomp.gp_comp['SURFIND.VEG.DOMI'], 0)
        str_out = six.StringIO()
        ncomp.write(str_out, onlymaxdiff=True)
        str_out.seek(0)
        self.assertEqual(str_out.read(), self.GPDIFFS_STR)

if __name__ == '__main__':
    unittest.main()
