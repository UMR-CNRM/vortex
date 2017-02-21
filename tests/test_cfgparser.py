#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

import logging
logging.basicConfig(level=logging.ERROR)

from ConfigParser import InterpolationMissingOptionError, NoSectionError, NoOptionError

from unittest import TestCase, TestLoader, TextTestRunner
from vortex.util.config import ExtendedReadOnlyConfigParser, GenericConfigParser, AppConfigStringDecoder
from vortex.data import geometries
from iga.data.providers import IgaCfgParser

DATAPATHTEST = '/'.join(__file__.split('/')[0:-1]) + '/data'


class _FooResource(object):

    def __init__(self, kind):
        self.realkind = kind


class UtGenericConfigParser(TestCase):

    def setUp(self):
        self.path = DATAPATHTEST

    def test_void_init(self):
        gcp = GenericConfigParser()
        self.assertTrue(type(gcp) == GenericConfigParser)
        self.assertTrue(gcp.file is None)

    def test_init_1(self):
        self.assertRaises(Exception, GenericConfigParser, '@absent.ini')

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
            self.assertEqual(igacfgp.options(section), ['resolvedpath'],
                             msg='Block: {}. {!s}'.format(section,
                                                          igacfgp.options(section)))
        self.assertRaises(
            InterpolationMissingOptionError,
            igacfgp.get,
            'analysis', 'resolvedpath'
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
            igacfgp.get('analysis', 'resolvedpath') == resolvedpath
        )


class UtExtendedConfigParser(TestCase):

    def setUp(self):
        self.ecp = ExtendedReadOnlyConfigParser(os.path.join(DATAPATHTEST,
                                                             'extended-inheritance.ini'))

    def test_usual(self):
        me = 'bigbase'
        self.assertSetEqual(set(self.ecp.options(me)),
                            set(['toto_default', 'toto_over', 'titi', ]))
        self.assertEqual(self.ecp.get(me, 'titi'), 'bigbase')
        self.assertEqual(self.ecp.get(me, 'toto_default'), 'DEFAULT')
        self.assertEqual(self.ecp.get(me, 'toto_over'), 'DEFAULT')

    def test_one_tier(self):
        me = 'fancy1'
        self.assertSetEqual(set(self.ecp.options(me)),
                            set(['toto_default', 'toto_over', 'titi', 'tata']))
        self.assertEqual(self.ecp.get(me, 'tata'), 'fancy1')
        self.assertEqual(self.ecp.get(me, 'titi'), 'bigbase')
        self.assertEqual(self.ecp.get(me, 'toto_default'), 'DEFAULT')
        self.assertEqual(self.ecp.get(me, 'toto_over'), 'fancy1')

    def test_two_tier(self):
        me = 'fancy2'
        self.assertSetEqual(set(self.ecp.options(me)),
                            set(['toto_default', 'toto_over', 'titi', 'tata', 'truc']))
        self.assertEqual(self.ecp.get(me, 'tata'), 'fancy1')
        self.assertEqual(self.ecp.get(me, 'titi'), 'bigbase')
        self.assertEqual(self.ecp.get(me, 'toto_default'), 'DEFAULT')
        self.assertEqual(self.ecp.get(me, 'toto_over'), 'fancy2')
        self.assertEqual(self.ecp.get(me, 'truc'), 'fancy1')

    def test_nightmare(self):
        me = 'verystrange'
        self.assertSetEqual(set(self.ecp.options(me)),
                            set(['toto_default', 'toto_over', 'titi', 'tata', 'truc',
                                 'bonus', 'ouf', 'cool']))
        self.assertEqual(self.ecp.get(me, 'tata'), 'fancy1')
        self.assertEqual(self.ecp.get(me, 'titi'), 'bigbase')
        self.assertEqual(self.ecp.get(me, 'toto_default'), 'DEFAULT')
        self.assertEqual(self.ecp.get(me, 'toto_over'), 'fancy2')
        self.assertEqual(self.ecp.get(me, 'truc'), 'fancy1')
        self.assertEqual(self.ecp.get(me, 'bonus'), 'otherbase')
        self.assertEqual(self.ecp.get(me, 'ouf'), 'verystrange')
        self.assertEqual(self.ecp.get(me, 'cool'), 'fancy2')
        thedict = self.ecp.as_dict()
        self.assertDictEqual(thedict['verystrange'],
                             {'bonus': 'otherbase', 'tata': 'fancy1', 'titi': 'bigbase',
                              'ouf': 'verystrange', 'toto_default': 'DEFAULT',
                              'truc': 'fancy1', 'toto_over': 'fancy2', 'cool': 'fancy2'})

    def test_tricky(self):
        me = 'trick1'
        self.assertSetEqual(set(self.ecp.options(me)),
                            set(['toto_default', 'toto_over', ]))
        self.assertEqual(self.ecp.get(me, 'toto_default'), 'DEFAULT')
        self.assertEqual(self.ecp.get(me, 'toto_over'), 'trick1')
        me = 'trick2'
        self.assertSetEqual(set(self.ecp.options(me)),
                            set(['toto_default', 'toto_over', 'titi', ]))
        self.assertEqual(self.ecp.get(me, 'toto_default'), 'DEFAULT')
        self.assertEqual(self.ecp.get(me, 'toto_over'), 'trick2')
        self.assertEqual(self.ecp.get(me, 'titi'), 'bigbase')

    def test_exceptions(self):
        me = 'fake'
        self.assertFalse(self.ecp.has_section(me))
        with self.assertRaises(NoSectionError):
            self.ecp.options(me)
        with self.assertRaises(NoSectionError):
            self.ecp.items(me)
        with self.assertRaises(NoSectionError):
            self.ecp.has_option(me, 'truc')
        me = 'fancy2'
        self.assertFalse(self.ecp.has_option(me, 'dsgqgfafaqf'))
        with self.assertRaises(NoOptionError):
            self.ecp.get(me, 'dsgqgfafaqf')
        with self.assertRaises(ValueError):
            self.ecp.as_dict(merged=False)


class UtIgaCfgParser(TestCase):

    def setUp(self):
        self.path = DATAPATHTEST

    def test_void_init(self):
        icp = IgaCfgParser()
        self.assertTrue(type(icp) == IgaCfgParser)
        self.assertTrue(icp.file is None)

    def test_init_1(self):
        self.assertRaises(Exception, IgaCfgParser, '@absent.ini')

    def test_init_2(self):
        real_ini = os.path.join(self.path, 'false.ini')
        self.assertRaises(Exception, IgaCfgParser, real_ini)

    def test_init_3(self):
        real_ini = os.path.join(self.path, 'iga-map-resources.ini')
        igacfgp = IgaCfgParser(real_ini)
        for section in ['analysis', 'matfilter', 'rtcoef', 'namelist', 'clim_model', 'clim_bdap']:
            self.assertIn(section, igacfgp.sections())
        for section in igacfgp.sections():
            self.assertTrue('resolvedpath' in igacfgp.options(section))
        self.assertRaises(
            InterpolationMissingOptionError,
            igacfgp.get,
            'analysis', 'resolvedpath'
        )

    def test_setall(self):
        real_ini = os.path.join(self.path, 'iga-map-resources.ini')
        igacfgp = IgaCfgParser(real_ini)
        kwargs = {
            'model': 'arpege',
            'igakey': 'france',
            'suite': 'oper',
            'fmt': 'autres'
        }
        resolvedpath = 'arpege/france/oper/data/autres'
        igacfgp.setall(kwargs)
        self.assertTrue(igacfgp.get('analysis', 'resolvedpath') == resolvedpath)

    def test_resolvedpath(self):
        real_ini = os.path.join(self.path, 'iga-map-resources.ini')
        igacfgp = IgaCfgParser(real_ini)
        kwargs = {
            'model': 'arpege',
            'igakey': 'france',
            'suite': 'oper',
            'fmt': 'autres'
        }
        resolvedpath = 'arpege/france/oper/data/autres'
        igacfgp.setall(kwargs)
        res = _FooResource('analysis')
        self.assertTrue(igacfgp.resolvedpath(res, 'play', 'sandbox'),
                        resolvedpath)


class TestAppConfigDecoder(TestCase):

    def setUp(self):
        self.cd = AppConfigStringDecoder()

    def test_litteral_cleaner(self):
        sref = 'blop(uit:1 tri:2) rtui,trop'
        for svar in ('  blop(uit:1 tri:2) rtui,trop ',
                     'blop( uit:1 tri:2 ) rtui,trop',
                     'blop( uit:1 tri:2)   rtui,trop',
                     'blop(uit:1 tri:2) rtui,  trop',
                     'blop(uit:1 tri:2) rtui ,trop',
                     "blop(uit:1\ntri:2) rtui ,trop",
                     "blop(uit:1 \ntri:2) rtui ,trop",
                     'blop(uit:  1  tri:2) rtui ,trop',
                     ):
            self.assertEqual(self.cd._litteral_cleaner(svar), sref)

    def test_sparser(self):
        p = self.cd._sparser
        # Does nothing
        self.assertListEqual(p('blop(123)'), ['blop(123)', ])
        self.assertListEqual(p('bdict(123)'), ['bdict(123)', ])
        # Raise ?
        with self.assertRaises(ValueError):
            p('toto', keysep=':')
        with self.assertRaises(ValueError):
            p('toto', keysep=':', itemsep=' ')
        with self.assertRaises(ValueError):
            p('toto:titi tata', keysep=':', itemsep=' ')
        # Item separator only
        self.assertListEqual(p('1', itemsep=','), ['1', ])
        self.assertListEqual(p('1,2,3', itemsep=','), ['1', '2', '3'])
        self.assertListEqual(p('1,(2,5,6),3', itemsep=','),
                             ['1', '(2,5,6)', '3'])
        self.assertListEqual(p('1,machin(2,5,6),3', itemsep=','),
                             ['1', 'machin(2,5,6)', '3'])
        self.assertListEqual(p('1(fgt,jt)a,machin', itemsep=','),
                             ['1(fgt,jt)a', 'machin'])
        # Key/value separators
        self.assertListEqual(p('toto:titi', itemsep=' ', keysep=':'),
                             ['toto', 'titi'])
        self.assertListEqual(p('toto:titi blop:blurp', itemsep=' ', keysep=':'),
                             ['toto', 'titi', 'blop', 'blurp'])
        self.assertListEqual(p('toto:titi blop:dict(blurp:12 blip:13)', itemsep=' ', keysep=':'),
                             ['toto', 'titi', 'blop', 'dict(blurp:12 blip:13)'])
        self.assertListEqual(p('toto:titi blop:dict(blurp:dict(rrr=12 zzz=15) blip:13)', itemsep=' ', keysep=':'),
                             ['toto', 'titi', 'blop', 'dict(blurp:dict(rrr=12 zzz=15) blip:13)'])
        # Raise Unbalanced parenthesis
        with self.assertRaises(ValueError):
            p('toto:titi(arg', keysep=':', itemsep=' ')
        with self.assertRaises(ValueError):
            p('titi(arg', itemsep=',')
        with self.assertRaises(ValueError):
            p('titi)arg', itemsep=',')

    def test_value_expand(self):
        # Basics...
        self.assertEqual(self.cd._value_expand('toto', lambda x: x),
                         'toto')
        self.assertIs(self.cd._value_expand('None', lambda x: x),
                      None)
        self.assertEqual(self.cd._value_expand('toto(scrontch)', lambda x: x),
                         'toto(scrontch)')
        # Lists...
        self.assertListEqual(self.cd._value_expand('toto,titi,tata', lambda x: x),
                             ['toto', 'titi', 'tata'])
        self.assertListEqual(self.cd._value_expand('toto,None,tata', lambda x: x),
                             ['toto', None, 'tata'])
        self.assertListEqual(self.cd._value_expand('tot(o,tit)i,tata', lambda x: x),
                             ['tot(o,tit)i', 'tata'])
        # Dictionnaries...
        self.assertDictEqual(self.cd._value_expand('dict(01:1 02:2)', lambda x: x),
                             {'01': '1', '02': '2'})
        self.assertDictEqual(self.cd._value_expand('dict(01:(1:26,25) 02:2)', lambda x: x),
                             {'01': '(1:26,25)', '02': '2'})
        self.assertDictEqual(self.cd._value_expand('dict(assim:dict(01:1 02:2) production:dict(01:4 02:5))', lambda x: x),
                             {'assim': {'01': '1', '02': '2'},
                              'production': {'01': '4', '02': '5'}})
        self.assertDictEqual(self.cd._value_expand('dict(assim:dict(01:1 02:dict(1:2 2:1)) production:dict(01:4 02:5))', lambda x: x),
                             {'assim': {'01': '1', '02': {'1': '2', '2': '1'}},
                              'production': {'01': '4', '02': '5'}})
        # Dictionnary of lists
        self.assertEqual(self.cd._value_expand('dict(01:1,26,25 02:2)', lambda x: x),
                         {'01': ['1', '26', '25'], '02': '2'})
        # List of dictionnaries
        self.assertEqual(self.cd._value_expand('dict(01:1,26,25 02:2),1', lambda x: x),
                         [{'01': ['1', '26', '25'], '02': '2'}, '1'])
        # Remapping
        self.assertDictEqual(self.cd._value_expand('dict(assim:dict(01:1 02:dict(1:2 2:1)) production:dict(01:4 02:5))', int),
                             {'assim': {'01': 1, '02': {'1': 2, '2': 1}},
                              'production': {'01': 4, '02': 5}})
        self.assertEqual(self.cd._value_expand('dict(01:1,26,25 02:2),1', int),
                         [{'01': [1, 26, 25], '02': 2}, 1])
        self.assertEqual(self.cd._value_expand('dict(01:1,None,25 02:2),1', int),
                         [{'01': [1, None, 25], '02': 2}, 1])

    def test_decode(self):
        # Easy
        tlist = 'toto,titi,tata'
        self.assertListEqual(self.cd(tlist), ['toto', 'titi', 'tata'])
        tdict = 'dict(toto:titi tata:titi)'
        self.assertDictEqual(self.cd(tdict), {'toto': 'titi', 'tata': 'titi'})
        # Remap ?
        tgeometry = 'geometry(globalsp)'
        self.assertEqual(self.cd(tgeometry), geometries.get(tag='globalsp'))
        tgeometries = 'geometry(globalsp,globalsp2)'
        self.assertListEqual(self.cd(tgeometries), [geometries.get(tag='globalsp'),
                                                    geometries.get(tag='globalsp2')])
        tdict2 = 'int(dict(toto:1 tata:2))'
        self.assertDictEqual(self.cd(tdict2), {'toto': 1, 'tata': 2})
        tlist2 = 'float(2.6,2.8)'
        self.assertListEqual(self.cd(tlist2), [2.6, 2.8])
        # Strange case
        for sval in ('dict(toto:titi,tata tata:titi)',
                     "dict(toto:titi,tata \n\ntata:titi)",
                     "dict(toto:titi,\ntata tata:titi)",
                     'dict(toto:  titi,tata   tata:titi)',
                     '   dict(toto:titi,tata tata:titi)  ',
                     'dict(toto:titi ,  tata tata:titi)',
                     'dict(  toto:titi,tata tata:titi)',
                     'dict(toto:titi,tata tata:titi  )',
                     ):
            self.assertDictEqual(self.cd(sval),
                                 {'toto': ['titi', 'tata'], 'tata': 'titi'})

if __name__ == '__main__':
    action = TestLoader().loadTestsFromTestCase
    tests = [UtGenericConfigParser, UtExtendedConfigParser, UtIgaCfgParser,
             TestAppConfigDecoder]
    suites = [action(elmt) for elmt in tests]
    for suite in suites:
        TextTestRunner(verbosity=1).run(suite)


def get_test_class():
    return [UtGenericConfigParser, UtExtendedConfigParser, UtIgaCfgParser,
            TestAppConfigDecoder]
