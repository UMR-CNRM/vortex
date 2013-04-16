#!/bin/env python
# -*- coding: utf-8 -*-

import logging
logging.basicConfig(level=logging.ERROR)

from unittest import TestCase, TestLoader, TextTestRunner

import vortex
from vortex import toolbox
from vortex.data.geometries import SpectralGeometry
import common.data
import olive.data

class UtObservations(TestCase):

    def setUp(self):
        self.attrset = dict(kind='observations', date = '2012021406', cutoff='production', namespace='[suite].archive.fr')
        self.std = SpectralGeometry(id='Current op', area='france', truncation=798)

    def test_v1(self):
        rl = toolbox.rload(
            self.attrset,
            namespace='vortex.cache.fr',
            experiment='OPER',
            block='observation',
            model='arpege',
            geometry=self.std,
            part='conv',
            nativefmt='obsoul',
            stage='std',
            local='[nativefmt].[part]',
        )
        for rh in rl:
            self.assertTrue(rh.complete)

        self.assertEqual(rl[0].location(), 'vortex://open.cache.fr/play/sandbox/OPER/20120214T0600P/observation/obsoul.std.conv')


    def test_v3(self):
        rl = toolbox.rload(
            self.attrset,
            namespace='vortex.cache.fr',
            experiment='oper',
            block='observation',
            model='arpege',
            geometry=self.std,
            part='full',
            nativefmt='ecma',
            stage='screen',
            local='[nativefmt].[part]',
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(rl[0].location(), 'vortex://open.cache.fr/play/sandbox/oper/20120214T0600P/observation/ecma.screen.full.tar')


    def test_o1(self):
        rl = toolbox.rload(
            self.attrset,
            local='obsoul.conv',
            igakey='arpege',
            suite='oper',
            model='arpege',
            geometry=self.std,
            part='conv',
            nativefmt='obsoul',
            stage='void'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(rl[0].location(), 'ftp://oper.archive.fr/arpege/oper/production/2012/02/14/r6/obsoul.conv')

    def test_o2(self):
        rl = toolbox.rload(
            self.attrset,
            local='bufr.iasi',
            igakey='arpege',
            suite='oper',
            model='arpege',
            geometry=self.std,
            part='iasi',
            nativefmt='bufr',
            stage='void'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(rl[0].location(), 'ftp://oper.archive.fr/arpege/oper/production/2012/02/14/r6/bufr.iasi')

    def test_o3(self):
        rl = toolbox.rload(
            self.attrset,
            local='odb_screen.tar',
            igakey='arpege',
            suite='oper',
            model='arpege',
            geometry=self.std,
            part='full',
            nativefmt='odb',
            stage='screen'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(rl[0].location(), 'ftp://oper.archive.fr/arpege/oper/production/2012/02/14/r6/odb_screen.tar?extract=all')

    def test_o4(self):
        rl = toolbox.rload(
            self.attrset,
            local='odb_cpl.tar',
            igakey='arpege',
            suite='oper',
            model='arpege',
            geometry=self.std,
            part='full',
            nativefmt='odb',
            stage='complete'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(rl[0].location(), 'ftp://oper.archive.fr/arpege/oper/production/2012/02/14/r6/odb_cpl.tar?extract=all')


class UtRefdata(TestCase):

    def setUp(self):
        self.attrset = dict(kind='refdata', date = '2012021406', cutoff='production', namespace='[suite].archive.fr')

    def test_r1(self):
        rl = toolbox.rload(
            self.attrset,
            local='refdata',
            igakey='arpege',
            suite='oper',
            model='arpege',
        )
        for rh in rl:
            self.assertTrue(rh.complete)

        self.assertEqual(rl[0].location(), 'ftp://oper.archive.fr/arpege/oper/production/2012/02/14/r6/refdata')

    def test_v1(self):
        rl = toolbox.rload(
            self.attrset,
            namespace='vortex.cache.fr',
            local='refdata',
            experiment='oper',
            block='observation',
            model='arpege',
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(rl[0].location(), 'vortex://open.cache.fr/play/sandbox/oper/20120214T0600P/observation/refdata.all')


class UtVarbc(TestCase):

    def setUp(self):
        self.attrset = dict(kind='varbc', date = '2012021400', cutoff='production', namespace='[suite].archive.fr')

    def test_v1(self):
        rl = toolbox.rload(
            self.attrset,
            local='varbc_reunion.cycle',
            suite='oper',
            model='aladin',
            igakey='reunion'
        )

        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(rl[0].location(), 'ftp://oper.archive.fr/reunion/oper/production/2012/02/14/r0/VARBC.cycle')


    def test_v2(self):
        rl = toolbox.rload(
            self.attrset,
            local='varbc_reunion.alad',
            suite='oper',
            model='aladin',
            igakey='reunion',
            inout='in',
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(rl[0].location(), 'ftp://oper.archive.fr/reunion/oper/production/2012/02/14/r0/VARBC.cycle_alad')

    def test_v3(self):
        rl = toolbox.rload(
            self.attrset,
            local='varbc_reunion.arp',
            suite='oper',
            model='arpege',
            igakey='reunion',
            inout='in',
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(rl[0].location(), 'ftp://oper.archive.fr/reunion/oper/production/2012/02/14/r0/VARBC.cycle_arp')

    def test_v4(self):
        rl = toolbox.rload(
            self.attrset,
            local='varbc_arome.merge',
            suite='oper',
            model='arome',
            igakey='arome',
            stage ='merge',
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(rl[0].location(), 'ftp://oper.archive.fr/arome/oper/production/2012/02/14/r0/VARBC.merge')

    def test_v5(self):
        rl = toolbox.rload(
            self.attrset,
            local='varbc_france.merge',
            suite='oper',
            model='aladin',
            igakey='france',
            stage ='merge',
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(rl[0].location(), 'ftp://oper.archive.fr/france/oper/production/2012/02/14/r0/VARBC.merge')

    def test_v6(self):
        rl = toolbox.rload(
            self.attrset,
            namespace='olive.archive.fr',
            local='varbc_olive.merge',
            model='aladin',
            date='2011092200',
            block='observations',
            experiment='99A2',
            stage ='merge',
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(rl[0].location(), 'olive://open.archive.fr/99A2/20110922H00P/observations/varbc')

    def test_v7(self):
        rl = toolbox.rload(
            self.attrset,
            namespace='olive.archive.fr',
            local='varbc_olive.cycle',
            model='aladin',
            date='2011092200',
            block='minim',
            experiment='99A2',
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(rl[0].location(), 'olive://open.archive.fr/99A2/20110922H00P/minim/varbc')

    def test_v8(self):
        rl = toolbox.rload(
            self.attrset,
            namespace='vortex.cache.fr',
            local='varbc_vortex',
            model='aladin',
            date='2011092200',
            block='minim',
            experiment='oper',
            stage='void,merge'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(rl[0].location(), 'vortex://open.cache.fr/play/sandbox/oper/20110922T0000P/minim/varbc.aladin')
        self.assertEqual(rl[1].location(), 'vortex://open.cache.fr/play/sandbox/oper/20110922T0000P/minim/varbc.aladin.merge')


class UtBlackListDiap(TestCase):

    def setUp(self):
        self.attrset = dict(kind='blacklist', date = '2012021406', cutoff='production', namespace='[suite].archive.fr')

    def test_v1(self):
        rl = toolbox.rload(
            self.attrset,
            namespace='vortex.cache.fr',
            experiment='OPER',
            block='observation',
            model='arpege',
            scope='site',
            local='blacklist_diap',
        )
        for rh in rl:
            self.assertTrue(rh.complete)

        self.assertEqual(rl[0].location(), 'vortex://open.cache.fr/play/sandbox/OPER/20120214T0600P/observation/blacklist.site.txt')

    def test_o1(self):
        rl = toolbox.rload(
            self.attrset,
            local='blacklist_diap',
            scope='site',
            igakey='arpege',
            suite='oper',
            model='arpege',
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(rl[0].location(), 'ftp://oper.archive.fr/arpege/oper/production/2012/02/14/r6/LISTE_NOIRE_DIAP')


class UtBlackListLoc(TestCase):

    def setUp(self):
        self.attrset = dict(kind='blacklist', date = '2012021406', cutoff='production', namespace='[suite].archive.fr')

    def test_o1(self):
        rl = toolbox.rload(
            self.attrset,
            local='blacklist_loc',
            scope='local',
            igakey='arpege',
            suite='oper',
            model='arpege',
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(rl[0].location(), 'ftp://oper.archive.fr/arpege/oper/production/2012/02/14/r6/LISTE_LOC')

class UtObsmap(TestCase):

    def setUp(self):
        self.attrset = dict(kind='obsmap', date = '2012021406', cutoff='production', namespace='[suite].archive.fr')

    def test_v1(self):
        rl = toolbox.rload(
            self.attrset,
            namespace='vortex.cache.fr',
            experiment='oper',
            block='observation',
            local='obsmap',
            model='arpege',
            stage='std'
        )
        for rh in rl:
            self.assertTrue(rh.complete)

        self.assertEqual(rl[0].location(), 'vortex://open.cache.fr/play/sandbox/oper/20120214T0600P/observation/obsmap.std')

    def test_o1(self):
        rl = toolbox.rload(
            self.attrset,
            local='obsmap',
            igakey='arpege',
            suite='oper',
            model='arpege',
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(rl[0].location(), 'ftp://oper.archive.fr/arpege/oper/production/2012/02/14/r6/BATOR_MAP')

    def test_o2(self):
        rl = toolbox.rload(
            self.attrset,
            namespace='olive.archive.fr',
            date='2011092200',
            local='obsmap_olive_split',
            model='arpege',
            experiment='99A0',
            stage='split',
            block='observations',
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(rl[0].location(), 'olive://open.archive.fr/99A0/20110922H00P/observations/OBSMAP_split')



if __name__ == '__main__':
    for test in [ UtObservations, UtVarbc, UtRefdata, UtBlackListDiap, UtBlackListLoc, UtObsmap ]:
        x = TextTestRunner(verbosity=2).run(TestLoader().loadTestsFromTestCase(test))
        if x.errors or x.failures:
            print "Something went wrong !"
            break

