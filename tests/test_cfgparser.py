from configparser import InterpolationMissingOptionError, NoSectionError, NoOptionError
import logging
import os
import unittest
from unittest import TestCase

from bronx.stdtypes import date
import footprints

from vortex.util.config import ExtendedReadOnlyConfigParser, GenericConfigParser
from vortex.util.config import AppConfigStringDecoder, TableItem, ConfigurationTable
from vortex.data import geometries
from iga.data.providers import IgaCfgParser

logging.basicConfig(level=logging.ERROR)

DATAPATHTEST = os.path.join(os.path.dirname(__file__), 'data')


class _FooResource:

    def __init__(self, kind):
        self.realkind = kind


class UtGenericConfigParser(TestCase):

    def setUp(self):
        self.path = DATAPATHTEST

    def test_void_init(self):
        gcp = GenericConfigParser()
        self.assertIsInstance(gcp, GenericConfigParser)
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
                            {'toto_default', 'toto_over', 'titi'})
        self.assertEqual(self.ecp.get(me, 'titi'), 'bigbase')
        self.assertEqual(self.ecp.get(me, 'toto_default'), 'DEFAULT')
        self.assertEqual(self.ecp.get(me, 'toto_over'), 'DEFAULT')

    def test_one_tier(self):
        me = 'fancy1'
        self.assertSetEqual(set(self.ecp.options(me)),
                            {'toto_default', 'toto_over', 'titi', 'tata'})
        self.assertEqual(self.ecp.get(me, 'tata'), 'fancy1')
        self.assertEqual(self.ecp.get(me, 'titi'), 'bigbase')
        self.assertEqual(self.ecp.get(me, 'toto_default'), 'DEFAULT')
        self.assertEqual(self.ecp.get(me, 'toto_over'), 'fancy1')

    def test_two_tier(self):
        me = 'fancy2'
        self.assertSetEqual(set(self.ecp.options(me)),
                            {'toto_default', 'toto_over', 'titi', 'tata', 'truc'})
        self.assertEqual(self.ecp.get(me, 'tata'), 'fancy1')
        self.assertEqual(self.ecp.get(me, 'titi'), 'bigbase')
        self.assertEqual(self.ecp.get(me, 'toto_default'), 'DEFAULT')
        self.assertEqual(self.ecp.get(me, 'toto_over'), 'fancy2')
        self.assertEqual(self.ecp.get(me, 'truc'), 'fancy1')

    def test_nightmare(self):
        me = 'verystrange'
        self.assertSetEqual(set(self.ecp.options(me)),
                            {'toto_default', 'toto_over', 'titi', 'tata', 'truc',
                             'bonus', 'ouf', 'cool'})
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
                            {'toto_default', 'toto_over'})
        self.assertEqual(self.ecp.get(me, 'toto_default'), 'DEFAULT')
        self.assertEqual(self.ecp.get(me, 'toto_over'), 'trick1')
        me = 'trick2'
        self.assertSetEqual(set(self.ecp.options(me)),
                            {'toto_default', 'toto_over', 'titi'})
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
        self.assertIsInstance(icp, IgaCfgParser)
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

    def test_decode(self):
        # Remap ?
        tgeometry = 'geometry(global798)'
        self.assertEqual(self.cd(tgeometry), geometries.get(tag='global798'))
        tgeometries = 'geometry(global798,globalsp2)'
        self.assertListEqual(self.cd(tgeometries), [geometries.get(tag='global798'),
                                                    geometries.get(tag='globalsp2')])
        ttimes = 'time(1,12:00)'
        self.assertListEqual(self.cd(ttimes), [date.Time('1:00'), date.Time('12:00')])
        tdates = 'date(grrrr,2018010100,2018-01-01T00:00)'
        self.assertListEqual(self.cd(tdates), ['grrrr', date.Date('2018010100'), date.Date('2018010100')])
        # Builders
        trangex = 'rangex(1-35-1)'
        self.assertListEqual(self.cd(trangex), list(range(1, 36)))
        trangex = 'rangex(1-35-1,37,38-42-2)'
        self.assertListEqual(self.cd(trangex), list(range(1, 36)) + [37, 38, 40, 42])
        trangex = 'rangex(0-1-0:30)'
        self.assertListEqual(self.cd(trangex), ['0000:00', '0000:30', '0001:00'])
        trangex = 'rangex(start:1 end:3 shift:-1)'
        self.assertListEqual(self.cd(trangex), [0, 1, 2])
        trangex = 'rangex(start:1 end:3 shift:-0:30)'
        self.assertListEqual(self.cd(trangex), ['0000:30', '0001:30', '0002:30'])
        tdrangex = 'daterangex(2017123112-2018010112-PT12H)'
        self.assertListEqual(self.cd(tdrangex),
                             [date.Date(2017, 12, 31, 12, 0), date.Date(2018, 1, 1, 0, 0),
                              date.Date(2018, 1, 1, 12, 0)])
        tdrangex = 'daterangex(start:2018010100 end:date(2018-01-02T00:00) step:PT12H shift:-PT12H)'
        self.assertListEqual(self.cd(tdrangex),
                             [date.Date(2017, 12, 31, 12, 0), date.Date(2018, 1, 1, 0, 0),
                              date.Date(2018, 1, 1, 12, 0)])
        # Other simple builders...
        tbuild = 'dict(a:geometry(global798) b:time(12:00) c:date(2018-01-01T00:00))'
        self.assertDictEqual(self.cd(tbuild),
                             dict(a=geometries.get(tag='global798'),
                                  b=date.Time('12:00'), c=date.Date('2018010100')))


class _UnitTestTableItem(TableItem):
    """
    Test element only
    """
    _RST_NAME = 'name'
    _RST_HOTKEYS = ['latitude', 'longitude', 'description']

    _footprint = dict(
        info = 'Sites for sources of pollution (radiologic, chemical, volcanic, etc.)',
        attr = dict(
            name = dict(),
            family = dict(
                values = ['utest_chemical', 'utest_volcanic'],
            ),
            latitude = dict(
                type = float
            ),
            longitude = dict(
                type = float
            ),
            description = dict(
            ),
            location = dict(
                optional = True,
                default  = '[name]',
            ),
        )
    )

    @property
    def realkind(self):
        return 'utest_item'


class _UnitTestConfTable(ConfigurationTable):

    _footprint = dict(
        info = 'Pollutants elements table',
        attr = dict(
            family = dict(
                values = ['utestfamily', ]
            ),
            kind = dict(
                values   = ['utestsites'],
            ),
            searchkeys = dict(
                default  = ('name', 'location'),
            ),
            inifile = dict(
                default  = os.path.join(DATAPATHTEST,
                                        '[family]-[kind]-[version].ini'),
            ),
        )
    )


class UtConfigurationTable(TestCase):

    _last_rawdump = """description : Chimique
family      : utest_chemical
latitude    : 0.0
location    : HELLO
longitude   : 0.0
name        : HELLO"""
    _last_endump = """Latitude     : 0.0
Longitude    : 0.0
Site's type  : Chimique
Localisation : HELLO"""
    _last_frdump = """Latitude     : 0.0
Longitude    : 0.0
Type de site : Chimique
Localisation : HELLO"""
    _last_rstdump = """**HELLO** : `description=Chimique, latitude=0.0, longitude=0.0`

    * family: utest_chemical
    * location: HELLO

"""

    def test_bare(self):
        c_conf = footprints.proxy.iniconf(kind='utestsites', family='utestfamily',
                                          version='bare')
        self.assertEqual(set(c_conf.groups()), {'utest_chemical', 'utest_volcanic'})
        self.assertEqual(set(c_conf.keys()), {'AGUA-DE-PAU', 'ARDOUKOBA', 'HELLO'})
        self.assertEqual(len(c_conf.tablelist), 3)
        self.assertIsInstance(c_conf.tablelist[0], _UnitTestTableItem)
        self.assertListEqual(c_conf.find('somewhere'), [c_conf.get('ARDOUKOBA')])
        self.assertListEqual(c_conf.grep('PA.'), [c_conf.get('AGUA-DE-PAU')])
        itemtest = c_conf.get('HELLO')
        self.assertEqual(str(itemtest), self._last_rawdump)
        self.assertEqual(itemtest.nice_rst(), self._last_rstdump)

    def test_traslate(self):
        c_conf = footprints.proxy.iniconf(kind='utestsites', family='utestfamily',
                                          version='tr')
        itemtest = c_conf.get('HELLO')
        self.assertEqual(str(itemtest), self._last_endump)
        c_conf = footprints.proxy.iniconf(kind='utestsites', family='utestfamily',
                                          version='tr', language='fr')
        itemtest = c_conf.get('HELLO')
        self.assertEqual(str(itemtest), self._last_frdump)


if __name__ == '__main__':
    unittest.main(verbosity=2)


def get_test_class():
    return [UtGenericConfigParser, UtExtendedConfigParser, UtIgaCfgParser,
            TestAppConfigDecoder, UtConfigurationTable]
