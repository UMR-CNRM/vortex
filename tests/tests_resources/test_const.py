#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
logging.basicConfig(level=logging.ERROR)

from unittest import TestCase, TestLoader, TextTestRunner

from vortex import toolbox, sessions
import gco.data
import olive.data
import common.data

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

        self.assertEqual(rl[0].resource.gvar, 'RTCOEF_TGZ')


class UtBcor(TestCase):

    def setUp(self):
        self.attrset = dict(kind='bcor', date='2012021406', cutoff='production')

    def test_v1(self):
        rl = toolbox.rload(
            self.attrset,
            namespace='vortex.cache.fr',
            experiment='OPER',
            block='observation',
            local='bcor_[satbias].dat',
            model='arpege',
            satbias='noaa'
        )
        for rh in rl:
            self.assertTrue(rh.complete)

        self.assertEqual(rl[0].location(), 'vortex://vortex.cache.fr/play/sandbox/OPER/20120214T0600P/observation/bcor.noaa.txt')


    def test_b1(self):
        rl = toolbox.rload(
            self.attrset,
            namespace='[suite].archive.fr',
            local='bcor_[satbias].dat',
            satbias='noaa,ssmi,mtop',
            igakey='arpege',
            suite='oper',
            model='arpege',
        )

        for rh in rl:
            self.assertTrue(rh.complete)

        self.assertEqual(rl[0].location(), 'op://oper.archive.fr/arpege/oper/production/2012/02/14/r6/bcor_noaa.dat')
        self.assertEqual(rl[1].location(), 'op://oper.archive.fr/arpege/oper/production/2012/02/14/r6/bcor_ssmi.dat')
        self.assertEqual(rl[2].location(), 'op://oper.archive.fr/arpege/oper/production/2012/02/14/r6/bcor_mtop.dat')


if __name__ == '__main__':
    for test in [ UtRtCoef, UtBcor ]:
        x = TextTestRunner(verbosity=2).run(TestLoader().loadTestsFromTestCase(test))
        if x.errors or x.failures:
            print "Something went wrong !"
            break

