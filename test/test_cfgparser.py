#!/bin/env python
# -*- coding:Utf-8 -*-

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
        self.assertRaises(Exception, GenericConfigParser)
        print "test __init__ without argument Ok"

    def test_init_1(self):
        self.assertRaises(Exception, GenericConfigParser, 'absent.ini')
        print "test __init__ with an absent file Ok"

    def test_init_2(self):
        false_ini = os.path.join(self.path, 'false.ini')
        self.assertRaises(Exception, GenericConfigParser, false_ini)
        print "test __init__ with a bad formatted file Ok"

    def test_init_3(self):
        real_ini = os.path.join(self.path, 'iga_map_resources.ini')
        igacfgp = GenericConfigParser(real_ini)
        self.assertTrue(igacfgp.file == real_ini)
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
        print "test __init__ with a real ini file Ok"

    def test_setall(self):
        real_ini = os.path.join(self.path, 'iga_map_resources.ini')
        igacfgp = GenericConfigParser(real_ini)
        kwargs = {
            'model': 'arpege',
            'geometry': 'france'
        }
        resolvedpath = 'arpege/france/oper/data/autres'
        igacfgp.setall(kwargs)
        self.assertTrue(
            igacfgp.get('analysis',  'resolvedpath') == resolvedpath
        )
        print "test setall Ok"


class UtIgaCfgParser(TestCase):

    def test_void_init(self):
        self.assertRaises(Exception, IgaCfgParser)
        print "test __init__ without argument Ok"

    def test_init_1(self):
        self.assertRaises(Exception, IgaCfgParser, 'absent.ini')
        print "test __init__ with an absent file Ok"

    def test_init_2(self):
        false_ini = 'false.ini'
        self.assertRaises(Exception, IgaCfgParser, false_ini)
        print "test __init__ with a bad formatted file Ok"

    def test_init_3(self):
        real_ini = 'iga_map_resources.ini'
        igacfgp = IgaCfgParser(real_ini)
        self.assertTrue(igacfgp.PATH_INI == IGADATAPATH)
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
        print "test __init__ with a real ini file Ok"

    def test_setall(self):
        real_ini = 'iga_map_resources.ini'
        igacfgp = IgaCfgParser(real_ini)
        kwargs = {
            'model': 'arpege',
            'igakey': 'france',
            'suite': 'oper'
        }
        resolvedpath = 'arpege/france/oper/data/autres'
        igacfgp.setall(kwargs)
        self.assertTrue( igacfgp.get('analysis', 'resolvedpath') == resolvedpath )
        print "test setall Ok"

    def test_resolvedpath(self):
        real_ini = 'iga_map_resources.ini'
        igacfgp = IgaCfgParser(real_ini)
        kwargs = {
            'model': 'arpege',
            'igakey': 'france',
            'suite': 'oper'
        }
        resolvedpath = 'arpege/france/oper/data/autres'
        igacfgp.setall(kwargs)
        self.assertTrue(igacfgp.resolvedpath('analysis'), resolvedpath)
        print "test resolvedpath Ok"

if __name__ == '__main__':
    action = TestLoader().loadTestsFromTestCase
    tests = [ UtGenericConfigParser, UtIgaCfgParser ]
    suites = [action(elmt) for elmt in tests]
    for suite in suites:
        TextTestRunner(verbosity=2).run(suite)
