#!/bin/env python
# -*- coding:Utf-8 -*-

import os, logging
logging.basicConfig(level=logging.ERROR)

import vortex
from unittest import TestCase, TestLoader, TextTestRunner
from common.data.modelstates import Analysis
from vortex.data.geometries import SpectralGeometry
from vortex.tools.env import Environment


class UtEnv(TestCase):

    def setUp(self):
        self.res = Analysis(geometry=SpectralGeometry(), model='arpege', date='201304231500', cutoff='prod', kind='analysis')

    def test_basic(self):
        e = Environment()
        self.assertTrue('LOGNAME' in e)
        self.assertTrue('SHELL' in e)
        self.assertTrue('PATH' in e)
        self.assertTrue('PWD' in e)
 
        e['toto'] = 2
        self.assertEqual(e['toto'], 2)
        self.assertEqual(e['TOTO'], 2)
        self.assertEqual(e.native('TOTO'), '2')

    def test_activate(self):
        e = Environment()
        self.assertFalse(e.active())

        e.active(True)
        self.assertTrue(e.active())
        self.assertTrue(e.osbound())
        e['toto'] = 2
        self.assertEqual(os.environ['TOTO'], '2')
        e.active(False)
        e['toto'] = 42
        self.assertEqual(e.toto, 42)
        self.assertFalse('TOTO' in os.environ)

        e.active(True)
        e['bidon'] = 'bof'
        z = Environment(env=e)
        self.assertTrue(e.active())
        self.assertTrue(e.osbound())
        self.assertFalse(z.active())
        self.assertFalse(z.osbound())
        self.assertEqual(z['toto'], 42)
 
        z = Environment(env=e, active=True)
        self.assertTrue(z.active())
        self.assertTrue(z.osbound())
        self.assertTrue(e.active())
        self.assertFalse(e.osbound())
        self.assertEqual(os.environ['TOTO'], '42')
        z['bidon'] = 'coucou'
        self.assertEqual(e['bidon'], 'bof')

    def test_encoding(self):
        e = Environment(active=True)
        e['toto'] = range(1,4)
        self.assertEqual(os.environ['TOTO'], '[1, 2, 3]')
        e['toto'] = dict(toto = 2, fun = 'coucou')
        self.assertEqual(os.environ['TOTO'], '{"fun": "coucou", "toto": 2}')
        e['toto'] = self.res
        self.assertEqual(os.environ['TOTO'], '{"cutoff": "production", "kind": "analysis", "nativefmt": "fa", "geometry": {"area": "auto", "nlat": null, "stretching": 2.4, "nlon": null, "resolution": null, "id": "abstract", "truncation": 798}, "filling": "full", "filtering": null, "date": "201304231500", "clscontents": "DataRaw", "model": "arpege"}')


if __name__ == '__main__':
    action = TestLoader().loadTestsFromTestCase
    tests = [ UtEnv ]
    suites = [action(elmt) for elmt in tests]
    for suite in suites:
        TextTestRunner(verbosity=1).run(suite)
    vortex.exit()
    
def get_test_class():
    return [ UtEnv ]
