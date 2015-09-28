#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
logging.basicConfig(level=logging.ERROR)

from unittest import TestCase, TestLoader, TextTestRunner

from vortex import toolbox
from vortex.data.geometries import SpectralGeometry

import olive.data
u_fill_fp_catalogs = olive.data


class UtBackgroundErrStd(TestCase):

    def setUp(self):
        self.attrset = dict(
            kind='bgerrstd',
            date = '2012021400',
            cutoff='production',
            namespace='[suite].archive.fr'
        )
        self.std = SpectralGeometry(id='Current op', truncation=224)
        #sessions.current().debug()

    def test_v1(self):

        rl = toolbox.rload(
            self.attrset,
            geometry=self.std,
            local='errgribvor',
            namespace='vortex.cache.fr',
            experiment='oper',
            block='analysis',
            model='arpege',
            term=3,
            nativefmt='grib'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(
            rl[0].location(),
            'vortex://vortex.cache.fr/play/sandbox/oper/20120214T0000P/analysis/bgerrstd.arpege.tl224+0003:00.grib'
        )

    def test_e1(self):
        rl = toolbox.rload(
            self.attrset,
            geometry=self.std,
            local='errgribvor+arpege+[term::fmth]',
            suite='oper',
            term=3,
            model='arpege',
            igakey='arpege'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(rl[0].location(), 'op://oper.archive.fr/arpege/oper/production/2012/02/14/r0/errgribvor')

    def test_e2(self):

        rl = toolbox.rload(
            self.attrset,
            geometry=self.std,
            local='errgribvor+aearp+[term::fmth].in',
            suite='oper',
            term=3,
            inout='in',
            model='arpege',
            cutoff='assim',
            igakey='aearp'
        )

        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(rl[0].location(), 'op://oper.archive.fr/aearp/oper/assim/2012/02/14/r0/errgribvor.in')

    def test_e3(self):

        rl = toolbox.rload(
            self.attrset,
            geometry=self.std,
            local='errgribvor+aearp+[term::fmth].out',
            suite='oper',
            term=9,
            inout='out',
            model='arpege',
            cutoff='assim',
            igakey='aearp'
        )

        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(
            rl[0].location(),
            'op://oper.archive.fr/aearp/oper/assim/2012/02/14/r0/errgribvor_production.out'
        )

    def test_e4(self):
        rl = toolbox.rload(
            self.attrset,
            geometry=self.std,
            local='errgribvor+aearp+[term::fmth].dsbscr.out',
            suite='oper',
            term=12,
            inout='out',
            model='arpege',
            cutoff='assim',
            igakey='aearp'
        )

        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(
            rl[0].location(),
            'op://oper.archive.fr/aearp/oper/assim/2012/02/14/r0/errgribvor_production_dsbscr.out'
        )


class UtInflFactor(TestCase):

    def setUp(self):
        self.attrset = dict(kind='inflfactor', date = '2012021400',
                            cutoff='assim', namespace='[suite].archive.fr')

    def test_a1(self):
        rl = toolbox.rload(
            self.attrset,
            local='inflfactor',
            suite='oper',
            model='arpege',
            igakey='aearp'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(
            rl[0].location(),
            'op://oper.archive.fr/aearp/oper/assim/2012/02/14/r0/inflation_factor'
        )


if __name__ == '__main__':
    for test in [ UtBackgroundErrStd, UtInflFactor ]:
        x = TextTestRunner(verbosity=1).run(TestLoader().loadTestsFromTestCase(test))
        if x.errors or x.failures:
            print "Something went wrong !"
            break

