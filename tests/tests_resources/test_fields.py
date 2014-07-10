#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
logging.basicConfig(level=logging.ERROR)

from unittest import TestCase, TestLoader, TextTestRunner

from vortex import toolbox, sessions
from vortex.data.geometries import SpectralGeometry
from olive.data import fields


class UtRawFields(TestCase):

    def setUp(self):
        self.attrset = dict(kind='rawfields', suite='oper', date = '2012022800', cutoff='assim', namespace='[suite].archive.fr')
        #sessions.current().debug()

    def test_v1(self):
        #sessions.current().debug()
        rl = toolbox.rload(
            self.attrset,
            namespace='vortex.cache.fr',
            block='observation',
            experiment='oper',
            fields='seaice',
            origin='bdm',
            local='ICE_file'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(rl[0].location(), 'vortex://vortex.cache.fr/play/sandbox/oper/20120228T0000A/observation/seaice.bdm')

    def test_r1(self):
        #sessions.current().debug()
        rl = toolbox.rload(
             self.attrset,
             igakey='arpege',
             fields='sst',
             origin='nesdis,ostia',
             local='SST_File'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(rl[0].location(), 'op://oper.archive.fr/arpege/oper/assim/2012/02/28/r0/sst.nesdis.bdap')
        self.assertEqual(rl[1].location(), 'op://oper.archive.fr/arpege/oper/assim/2012/02/28/r0/sst.ostia')

    def test_r2(self):
        rl = toolbox.rload(
            self.attrset,
            igakey='arpege',
            fields='seaice',
            origin='bdm',
            local='ICE_file'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(rl[0].location(), 'op://oper.archive.fr/arpege/oper/assim/2012/02/28/r0/ice_concent')


class UtGeoFields(TestCase):

    def setUp(self):
        self.std = SpectralGeometry(id='Current op', truncation=798, stretching=2.4, area='france', lam=False)
        self.attrset = dict(kind='geofields', suite='oper', date = '2012022806', cutoff='production', namespace='[suite].archive.fr')
        #sessions.current().debug()

    def test_g1(self):
        rl = toolbox.rload(
             self.attrset,
             igakey='arpege',
             geometry=self.std,
             fields='sst,seaice',
             local='ICMSH_SST'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(rl[0].location(), 'op://oper.archive.fr/arpege/oper/production/2012/02/28/r6/icmshanalsst')
        self.assertEqual(rl[1].location(), 'op://oper.archive.fr/arpege/oper/production/2012/02/28/r6/icmshanalseaice')

    def test_v1(self):
        rl = toolbox.rload(
             self.attrset,
             namespace='vortex.cache.fr',
             experiment='oper',
             block='observation',
             geometry=self.std,
             fields='sst',
             local='ICMSH_SST'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(rl[0].location(), 'vortex://vortex.cache.fr/play/sandbox/oper/20120228T0600P/observation/sst.tl798-c24.fa')


if __name__ == '__main__':
    for test in [ UtRawFields, UtGeoFields ]:
        x = TextTestRunner(verbosity=2).run(TestLoader().loadTestsFromTestCase(test))
        if x.errors or x.failures:
            print "Something went wrong !"
            break

