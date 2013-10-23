#!/bin/env python
# -*- coding: utf-8 -*-

import os

import logging
logging.basicConfig(level=logging.ERROR)

from ConfigParser import InterpolationMissingOptionError

from unittest import TestCase, TestLoader, TextTestRunner
from vortex.tools.config import GenericConfigParser
from iga.data.providers import IgaCfgParser

DATAPATHTEST = './data'
IGADATAPATH = '/ch/mxpt/mxpt001/steph_perso/python/Vortex/src/iga/data'

class UtGenericConfigParser(TestCase):

    def setUp(self):
        self.path = DATAPATHTEST

    def test_void_init(self):
        gcp = GenericConfigParser()
        self.assertTrue(type(gcp) == GenericConfigParser)
        self.assertTrue(gcp.file is None)

    def test_init_1(self):
        self.assertRaises(Exception, GenericConfigParser, 'absent.ini')

    def test_init_2(self):
        false_ini = os.path.join(self.path, 'false.ini')
        self.assertRaises(Exception, GenericConfigParser, false_ini)

    def test_init_3(self):
        real_ini = os.path.join(self.path, 'iga-map-resources.ini')
        igacfgp = GenericConfigParser(real_ini)
        self.assertTrue(igacfgp.file.startswith('/'))
        sections = ['analysis', 'matfilter', 'rtcoef', 'namelist', 'climmodel',
                    'climmodel', 'climdomain']
        self.assertTrue(sorted(igacfgp.sections()), sorted(sections))
        for section in igacfgp.sections():
            self.assertTrue(igacfgp.options(section) == [ 'resolvedpath' ])
        self.assertRaises(
            InterpolationMissingOptionError,
            igacfgp.get,
            'analysis',  'resolvedpath'
        )

    def test_setall(self):
        real_ini = os.path.join(self.path, 'iga-map-resources.ini')
        igacfgp = GenericConfigParser(real_ini)
        kwargs = {
            'model': 'arpege',
            'igakey': 'france',
            'suite': 'oper',
            'fmt': 'autres'
        }
        resolvedpath = 'arpege/france/oper/data/autres'
        igacfgp.setall(kwargs)
        self.assertTrue(
            igacfgp.get('analysis',  'resolvedpath') == resolvedpath
        )


class UtIgaCfgParser(TestCase):

    def test_void_init(self):
        icp = IgaCfgParser()
        self.assertTrue(type(icp) == IgaCfgParser)
        self.assertTrue(icp.file is None)

    def test_init_1(self):
        self.assertRaises(Exception, IgaCfgParser, 'absent.ini')

    def test_init_2(self):
        false_ini = 'false.ini'
        self.assertRaises(Exception, IgaCfgParser, false_ini)

    def test_init_3(self):
        real_ini = 'iga-map-resources.ini'
        igacfgp = IgaCfgParser(real_ini)
        for section in ['analysis', 'matfilter', 'rtcoef', 'namelist', 'clim_model', 'clim_bdap']:
            self.assertIn(section, igacfgp.sections())
        for section in igacfgp.sections():
            self.assertTrue('resolvedpath' in igacfgp.options(section))
        self.assertRaises(
            InterpolationMissingOptionError,
            igacfgp.get,
            'analysis',  'resolvedpath'
        )

    def test_setall(self):
        real_ini = 'iga-map-resources.ini'
        igacfgp = IgaCfgParser(real_ini)
        kwargs = {
            'model': 'arpege',
            'igakey': 'france',
            'suite': 'oper',
            'fmt': 'autres'
        }
        resolvedpath = 'arpege/france/oper/data/autres'
        igacfgp.setall(kwargs)
        self.assertTrue( igacfgp.get('analysis', 'resolvedpath') == resolvedpath )

    def test_resolvedpath(self):
        real_ini = 'iga-map-resources.ini'
        igacfgp = IgaCfgParser(real_ini)
        kwargs = {
            'model': 'arpege',
            'igakey': 'france',
            'suite': 'oper',
            'fmt': 'autres'
        }
        resolvedpath = 'arpege/france/oper/data/autres'
        igacfgp.setall(kwargs)
        self.assertTrue(igacfgp.resolvedpath('analysis'), resolvedpath)

if __name__ == '__main__':
    action = TestLoader().loadTestsFromTestCase
    tests = [ UtGenericConfigParser, UtIgaCfgParser ]
    suites = [action(elmt) for elmt in tests]
    for suite in suites:
        TextTestRunner(verbosity=1).run(suite)

def get_test_class():
    return [ UtGenericConfigParser, UtIgaCfgParser ]
