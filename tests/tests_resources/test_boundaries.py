#!/bin/env python
# -*- coding:Utf-8 -*-

import logging
logging.basicConfig(level=logging.ERROR)

from unittest import TestCase, TestLoader, TextTestRunner

from vortex import toolbox, sessions
from vortex.data.geometries import SpectralGeometry
import common.data
import olive.data

class UtElscf(TestCase):

    def setUp(self):
        self.attrset = dict(kind='elscf', date = '2012021400', cutoff='production', namespace='[suite].archive.fr')
        self.std = SpectralGeometry(id='Current op', area='france', truncation=798)
        self.caledonie = SpectralGeometry(id='Current op', area='caledonie', resolution='08km00')
        self.arome = SpectralGeometry(id='Current op', area='frangp', resolution='02km50')
        self.aladin = SpectralGeometry(id='Current op', area='france')
        self.califs = SpectralGeometry(id='Current op', area='ifs', resolution='16km00')
        self.mp1 = SpectralGeometry(id='Current op', area='testmp1')
        self.mp2 = SpectralGeometry(id='Current op', area='testmp2')

    def test_v1(self):
        rl = toolbox.rload(
            self.attrset,
            geometry=self.arome, 
            local='ELSCFAROME+[term]',
            namespace='vortex.cache.fr',
            experiment='oper',
            block='coupling',
            source='arpege',
            term='12',
            model='arome'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(rl[0].location(), 'vortex://open.cache.fr/play/sandbox/oper/20120214T0000P/coupling/cpl.arpege.frangp-02km50+0012.fa')

    def test_e1(self):
        rl = toolbox.rload(
            self.attrset,
            geometry=self.arome, 
            local='ELSCFAROME+[term]',
            source='arpege',
            suite='oper',
            term='12',
            model='arome',
            igakey='arome'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(rl[0].location(), 'ftp://oper.archive.fr/arome/oper/production/2012/02/14/r0/COUPL0012.rCM')
 
    def test_e2(self):
        rl = toolbox.rload(
            self.attrset,
            geometry=self.caledonie, 
            local='ELSCFCALEDONIE+[term].[cutoff]',
            source='ifs',
            suite='oper',
            term='6',
            model='aladin',
            igakey='caledonie',
            cutoff='assim,production'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(rl[0].location(), 'ftp://oper.archive.fr/caledonie/oper/assim/2012/02/14/r0/COUPL0006.r00') 
        self.assertEqual(rl[1].location(), 'ftp://oper.archive.fr/caledonie/oper/production/2012/02/14/r0/COUPL0006.rAM') 
        
    def test_e3(self):
        rl = toolbox.rload(
            self.attrset,
            geometry=self.califs, 
            local='ELSCFIFSCALEDONIE+[term].[cutoff]',
            igakey='caledonie',
            suite='oper',
            source='ifs',
            term='06',
            cutoff='assim,production',
            model='aladin'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(rl[0].location(), 'ftp://oper.archive.fr/caledonie/oper/assim/2012/02/14/r0/COUPLIFS0006.r00') 
        self.assertEqual(rl[1].location(), 'ftp://oper.archive.fr/caledonie/oper/production/2012/02/14/r0/COUPLIFS0006.rAM') 
        
    def test_e4(self):
        rl = toolbox.rload(
            self.attrset,
            geometry=self.mp1, 
            local='ELSCFTESTMP1+[term].[cutoff]',
            igakey='testmp1',
            suite='oper',
            source='arpege',
            term='06',
            model='aladin'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(rl[0].location(), 'ftp://oper.archive.fr/testmp1/14/r0/COUPL0006.rAM') 
 
    def test_e5(self):
        rl = toolbox.rload(
            self.attrset,
            geometry=self.mp2, 
            local='ELSCFTESTMP2+[term].[cutoff]',
            igakey='testmp2',
            suite='oper',
            source='arpege',
            term='06',
            model='aladin'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(rl[0].location(), 'ftp://oper.archive.fr/testmp2/oper/production/2012/02/14/r0/COUPL0006.rAM') 
 
    def test_e6(self):
        rh = toolbox.rload(
            self.attrset,
            local='ELSCFOLIVE+[term]',
            namespace='olive.archive.fr',
            geometry=self.aladin,
            source='arpege',
            experiment = '99A2', 
            block='coupling',
            date='2011092200',
            model='aladin',
            term='06'
        ).pop()
        self.assertTrue(rh.complete)
        self.assertEqual(rh.location(), 'olive://open.archive.fr/99A2/20110922H00P/coupling/ELSCFALAD_france+0006')
   
    def test_e7(self):
        rh = toolbox.rload(
            self.attrset,
            local='ELSCFOLIVE2+[term]',
            namespace='olive.archive.fr',
            geometry=self.arome,
            source='arpege',
            experiment = '99Q7', 
            block='coupling',
            date='2012020800',
            model='arome',
            term='06'
        ).pop()
        self.assertTrue(rh.complete)
        self.assertEqual(rh.location(), 'olive://open.archive.fr/99Q7/20120208H00P/coupling/ELSCFAROM_frangp+0006')
              
              

if __name__ == '__main__':
    for test in [ UtElscf ]:
        x = TextTestRunner(verbosity=1).run(TestLoader().loadTestsFromTestCase(test))
        if x.errors or x.failures:
            print "Something went wrong !"
            break 
        
