#!/bin/env python
# -*- coding:Utf-8 -*-

import logging
logging.basicConfig(level=logging.ERROR)

from unittest import TestCase, TestLoader, TextTestRunner

from vortex import toolbox
import gco.data
import common.data
from olive.data import collected

class UtRtCoef(TestCase):

    def test_r1(self):
        rl = toolbox.rload(
            kind='rtcoef',
            local='rtcoef.tgz',
            genv='cy36t1_op1.01',
            model='arpege'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' resource gvar > ', rh.resource.gvar
            
        self.assertEqual(rl[0].resource.gvar, 'RTCOEF_TGZ')
        

class UtBcor(TestCase):

    def setUp(self):
        self.attrset = dict(kind='bcor', date = '2012021406', cutoff='production', namespace='[suite].archive.fr')
        
    def test_v1(self):
        rl = toolbox.rload(
            self.attrset,
            namespace='vortex.cache.fr',
            experiment='oper',
            block='observation',
            local='bcor_[collected].dat',
            model='arpege',
            collected='noaa'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
            
        self.assertEqual(rl[0].location(), 'vortex://open.cache.fr/play/sandbox/oper/20120214H0600P/observation/bcor_noaa.dat')   
        
        
    def test_b1(self):
        rl = toolbox.rload(
            self.attrset,
            local='bcor_[collected].dat',
            collected='noaa,ssmi,mtop',
            igakey='arpege',
            suite='oper',
            model='arpege',   
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
        self.assertEqual(rl[0].location(), 'ftp://oper.archive.fr/arpege/oper/production/2012/02/14/r6/entree.tar?extract=bcor_noaa.dat')
        self.assertEqual(rl[1].location(), 'ftp://oper.archive.fr/arpege/oper/production/2012/02/14/r6/entree.tar?extract=bcor_ssmi.dat')
        self.assertEqual(rl[2].location(), 'ftp://oper.archive.fr/arpege/oper/production/2012/02/14/r6/entree.tar?extract=bcor_mtop.dat')
              

if __name__ == '__main__':
    for test in [ UtRtCoef, UtBcor ]:
        x = TextTestRunner(verbosity=2).run(TestLoader().loadTestsFromTestCase(test))
        if x.errors or x.failures:
            print "Something went wrong !"
            break 
        
