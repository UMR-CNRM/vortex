#!/bin/env python
# -*- coding:Utf-8 -*-

import logging
logging.basicConfig(level=logging.ERROR)

from unittest import TestCase, TestLoader, TextTestRunner

from vortex import toolbox
from vortex.data.geometries import SpectralGeometry, GridGeometry
import common.data
import olive.data
import gco.data

class UtListing(TestCase):
    
    def test_v1(self):
        rl = toolbox.rload(
            kind='listing',
            namespace='vortex.cache.fr',
            experiment='oper',
            block='forecast',
            task='forecast',
            local='listing',
            date='20120420',
            cutoff='production',
            model='arpege',
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
            
        self.assertEqual(rl[0].location(), 'vortex://open.cache.fr/play/sandbox/oper/20120420H0000P/forecast/listing.forecast.2012042000.production')      


class UtMatFilter(TestCase):

    def setUp(self):
        self.std = SpectralGeometry(id='Current op', area='france', truncation=798)
        self.glob15 = GridGeometry(id='Current op', area='GLOB15', resolution=15, filtering='106') 
        
    def test_v1(self):
        rl = toolbox.rload(
            kind='matfilter',
            namespace='vortex.cache.fr',
            experiment='oper',
            block='forecast',
            geometry=self.std,
            scopedomain=self.glob15,
            model='arpege',
            local='matfilter.[scopedomain]',
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
            
        self.assertEqual(rl[0].location(), 'vortex://open.cache.fr/play/sandbox/oper/forecast/matfil.arpege.tl798-c24-glob15-f106')      

    def test_m1(self):
        rl = toolbox.rload(
            kind='matfilter',
            local='matfilter_file',
            genv='cy36t1_op1.01',
            model='arpege',
            geometry = self.std,
            scopedomain = self.glob15
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' resource gvar > ', rh.resource.gvar
            
        self.assertEqual(rl[0].resource.gvar, 'MAT_FILTER_GLOB15')


if __name__ == '__main__':
    for test in [ UtListing, UtMatFilter ]:
        x = TextTestRunner(verbosity=2).run(TestLoader().loadTestsFromTestCase(test))
        if x.errors or x.failures:
            print "Something went wrong !"
            break 
        
