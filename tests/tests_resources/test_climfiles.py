#!/bin/env python
# -*- coding:Utf-8 -*-

import logging
logging.basicConfig(level=logging.ERROR)

from unittest import TestCase, TestLoader, TextTestRunner

from vortex import toolbox, sessions
from vortex.data.geometries import SpectralGeometry, GridGeometry
import common.data
import gco.data
import gco.syntax


class UtClimGlobal(TestCase):

    def setUp(self):
        self.std = SpectralGeometry(id='Current op',  truncation=798, stretching=2.4)
        # sessions.current().debug()

    def test_v1(self):
        rl = toolbox.rload(
            kind='clim_model',
            namespace='vortex.cache.fr',
            experiment='oper',
            block='clim',
            geometry=self.std,
            local='clim.(month)',
            month='10',
            model='arpege'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
            
        self.assertEqual(rl[0].location(), 'vortex://open.cache.fr/play/sandbox/oper/clim/clim.arpege.tl798-c24.fa.m10')


    def test_c1(self):
        rl = toolbox.rload(
            kind='clim_model',
            geometry=self.std,
            local='clim.(month)',
            genv='cy36t1_op1.01',
            month='10',
            model='arpege'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' resource gvar > ', rh.resource.gvar
            
        self.assertEqual(rl[0].resource.gvar, 'CLIM_ARPEGE_T798')
 
 
class UtClimLAM(TestCase):

    def setUp(self):
        self.caledonie = SpectralGeometry(id='Current op', area='caledonie', resolution='08km00')
        #sessions.current().debug()
    
    def test_v1(self):
        rl = toolbox.rload(
            kind='clim_model',
            namespace='vortex.cache.fr',
            experiment='oper',
            block='clim',
            geometry=self.caledonie,
            local='clim.(month)',
            month='10',
            model='aladin'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
            
        self.assertEqual(rl[0].location(), 'vortex://open.cache.fr/play/sandbox/oper/clim/clim.aladin.caledonie-08km00.fa.m10')   
    
    def test_c1(self):
        rl = toolbox.rload(
            kind='clim_model',
            geometry=self.caledonie,
            local='clim.(month)',
            genv='cy36t1_op1.01',
            month='10',
            model='aladin'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' resource gvar > ', rh.resource.gvar
            
        self.assertEqual(rl[0].resource.gvar, 'CLIM_NCAL_08KM00')
        
    
class UtClimBDAP(TestCase):

    def setUp(self):
        self.frangp0025 = GridGeometry(id='Current op', area='FRANGP0025', resolution='0025', nlat=601, nlon=801)
        self.glob15 = GridGeometry(id='Current op', area='GLOB15', resolution='15')
        #sessions.current().debug()
        
    def test_v1(self):
        rl = toolbox.rload(
            kind='climbdap',
            namespace='vortex.cache.fr',
            experiment='oper',
            block='clim',
            geometry=self.glob15,
            local='clim.(month)',
            month='10',
            model='arpege'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
            
        self.assertEqual(rl[0].location(), 'vortex://open.cache.fr/play/sandbox/oper/clim/clim.arpege.glob15.fa.m10')   
        
    def test_v2(self):
        rl = toolbox.rload(
            kind='climbdap',
            namespace='vortex.cache.fr',
            experiment='oper',
            block='clim',
            geometry=self.frangp0025,
            local='clim.(month)',
            month='10',
            model='arome'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
            
        self.assertEqual(rl[0].location(), 'vortex://open.cache.fr/play/sandbox/oper/clim/clim.arome.frangp0025.fa.m10')   
    
    
    def test_c1(self):
        rl = toolbox.rload(
            kind='climbdap',
            geometry=self.glob15,
            local='clim.(month)',
            genv='cy36t1_op1.01',
            month='10',
            model='arpege'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' resource gvar > ', rh.resource.gvar
            
        self.assertEqual(rl[0].resource.gvar, 'CLIM_DAP_GLOB15')
    
    def test_c2(self):
        rl = toolbox.rload(
            kind='climbdap',
            geometry=self.frangp0025,
            local='clim.(month)',
            genv='cy36t1_op1.01',
            month='10',
            model='arome'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' resource gvar > ', rh.resource.gvar
            
        self.assertEqual(rl[0].resource.gvar, 'CLIM_DAP_FRANGP0025')


if __name__ == '__main__':
    for test in [ UtClimGlobal, UtClimLAM, UtClimBDAP]:
        x = TextTestRunner(verbosity=2).run(TestLoader().loadTestsFromTestCase(test))
        if x.errors or x.failures:
            print "Something went wrong !"
            break 
        
