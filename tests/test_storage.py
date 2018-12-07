'''
Created on 13 nov. 2018

@author: meunierlf
'''
from __future__ import print_function, absolute_import, unicode_literals, division

import io
import os
import tempfile
import unittest

import footprints as fp

import vortex  # @UnusedImport
from vortex.tools.storage import MarketPlaceCache

DATAPATHTEST = os.path.join(os.path.dirname(__file__), 'data')


CACHE_CONFIG = """
[marketplace-vortex]
siteconf=cache-marketplace-unittest.ini
externalconf_fail1_path=do_not_exists
externalconf_fail2_path=do_not_exists
externalconf_fail2_restrict=a_very_strange_path
externalconf_fail3_path=do_not_exists
externalconf_fail3_restrict=****this_very_wrong
externalconf_ok1_path=xbcd-market.ini
externalconf_ok2_path=utest-market.ini
externalconf_ok2_restrict=\w+/\w+/[^@]+@utest/
"""

MARKET_SITECONFIG = """
[ABCD-arpege]
rootdir=markets/ABCDmarket
regex=arome/\w+/ABCD/

[no_regex_test]
rootdir=markets/ABCDmarket
"""

MARKET_EXT1 = """
[ABCD-arpege]
rootdir=markets/XBCDmarket
regex=\w+/\w+/XBCD/
owners=unittest,someoneelse

[idiotic_regex_test]
rootdir=markets/ABCDmarket
regex=******grr
"""

MARKET_EXT2 = """
[numbered_tests]
rootdir=markets/utest_market
regex=\w+/\w+/test\d+@utest/
owners=someoneelse

[hack_attempt]
rootdir=markets/YBCDmarket
regex=\w+/\w+/YBCD/
owners=malicious
"""


class EmptyMarketPlaceCache(MarketPlaceCache):

    _footprint = dict(
        info = 'Fully configurable cache places.',
        attr = dict(
            kind = dict(
                values   = ['emptymarketplace', ],
            ),
        )
    )


class TestCacheStorage(unittest.TestCase):

    _REMAPS = [
        # Vortex Standard
        dict(item='arome/3dvarfr/ABCD/20180101T0000A/forecast/unittest',
             marketpath='markets/ABCDmarket/vortex/arome/3dvarfr/ABCD/20180101T0000A/forecast/unittest',
             mtoolpath='{:s}/vortex/arome/3dvarfr/ABCD/20180101T0000A/forecast/unittest',
             buddiespath='{:s}/vortexbuddies/arome/3dvarfr/ABCD/20180101T0000A/forecast/unittest', ),
        dict(item='arpege/3dvarfr/ABCD/20180101T0000A/forecast/unittest',
             marketpath=None,
             mtoolpath='{:s}/vortex/arpege/3dvarfr/ABCD/20180101T0000A/forecast/unittest',
             buddiespath='{:s}/vortexbuddies/arpege/3dvarfr/ABCD/20180101T0000A/forecast/unittest', ),
        dict(item='arpege/4dvarfr/XBCD/20180101T0000A/forecast/unittest',
             marketpath='markets/XBCDmarket/vortex/arpege/4dvarfr/XBCD/20180101T0000A/forecast/unittest',
             marketrw=True,
             mtoolpath='{:s}/vortex/arpege/4dvarfr/XBCD/20180101T0000A/forecast/unittest',
             buddiespath='{:s}/vortexbuddies/arpege/4dvarfr/XBCD/20180101T0000A/forecast/unittest', ),
        dict(item='arpege/4dvarfr/test2@utest/20180101T0000A/forecast/unittest',
             marketpath='markets/utest_market/vortex/arpege/4dvarfr/test2@utest/20180101T0000A/forecast/unittest',
             mtoolpath='{:s}/vortex/arpege/4dvarfr/test2@utest/20180101T0000A/forecast/unittest',
             buddiespath='{:s}/vortexbuddies/arpege/4dvarfr/test2@utest/20180101T0000A/forecast/unittest', ),
        dict(item='arpege/4dvarfr/test2@utestblop/20180101T0000A/forecast/unittest',
             marketpath=None,
             mtoolpath='{:s}/vortex/arpege/4dvarfr/test2@utestblop/20180101T0000A/forecast/unittest',
             buddiespath='{:s}/vortexbuddies/arpege/4dvarfr/test2@utestblop/20180101T0000A/forecast/unittest', ),
        dict(item='arpege/4dvarfr/YBCD/20180101T0000A/forecast/unittest',
             marketpath=None,
             mtoolpath='{:s}/vortex/arpege/4dvarfr/YBCD/20180101T0000A/forecast/unittest',
             buddiespath='{:s}/vortexbuddies/arpege/4dvarfr/YBCD/20180101T0000A/forecast/unittest', ),
    ]

    def _write_configfiles(self):
        with io.open('cache-unittest.ini', 'w') as fhc:
            fhc.write(CACHE_CONFIG)
        with io.open('cache-marketplace-unittest.ini', 'w') as fhc:
            fhc.write(MARKET_SITECONFIG)
        with io.open('xbcd-market.ini', 'w') as fhc:
            fhc.write(MARKET_EXT1)
        with io.open('utest-market.ini', 'w') as fhc:
            fhc.write(MARKET_EXT2)

    def _write_testfiles(self):
        self.tfile = 'testfile'
        with io.open(self.tfile, 'w') as fht:
            fht.write('toto')

    def setUp(self):
        # Generate a temporary directory
        self._oldsession = vortex.sessions.current()
        gl = vortex.sessions.getglove(user='unittest')
        self.t = vortex.sessions.get(tag='storage_test_view',
                                     topenv=vortex.rootenv, glove=gl)
        self.t.activate()
        self.t.critical()  # Decrease verbosity a lot !
        self.sh = self.t.system()
        self.sh.target(hostname='unittest', inetname='unittest',
                       sysname='Local')  # Trick the vortex's system !
        self.tmpdir = tempfile.mkdtemp(suffix='_test_storage')
        self.oldpwd = self.sh.pwd()
        self.sh.cd(self.tmpdir)
        self.sh.mkdir('mtool')
        self.sh.env['MTOOLDIR'] = self.sh.path.join(self.tmpdir, 'mtool')
        self._write_configfiles()
        self._write_testfiles()
        # Storage commons...
        self.commons = dict(storage=self.sh.default_target.inetname,
                            inifile='./cache-[storage].ini')

    def assertIsTestFile(self, path):
        with io.open(path, 'r') as fht:
            res = fht.read()
        self.assertEqual(res, 'toto')

    def tearDown(self):
        self.sh.cd(self.oldpwd)
        self.sh.remove(self.tmpdir)
        self._oldsession.activate()

    def test_mtool_and_buddies(self):
        # Basic one
        storage = fp.proxy.cache(kind='mtool', **self.commons)
        mtoolroot = self.sh.path.join(self.tmpdir, 'mtool', 'cache')
        for remap in self._REMAPS:
            self.assertEqual(storage._formatted_path(remap['item']),
                             remap['mtoolpath'].format(mtoolroot))
            self.assertTrue(storage.allow_writes(remap['item']))
            self.assertTrue(storage.allow_reads(remap['item']))
        item = self._REMAPS[0]['item']
        loc = self._REMAPS[0]['mtoolpath'].format(mtoolroot)
        self.assertFalse(storage.check(item))
        self.assertIsNone(storage.list('arome/'))
        self.assertTrue(storage.insert(item, self.tfile))
        self.assertIsTestFile(loc)
        self.assertListEqual(storage.list('arome/'), ['3dvarfr', ])
        self.assertTrue(storage.retrieve(item, 'rtestfile1'))
        self.assertIsTestFile('rtestfile1')
        self.assertTrue(storage.check(item))
        # Buddies
        storage_b = fp.proxy.cache(kind='mtoolbuddies', **self.commons)
        self.assertTrue(storage_b.readonly)
        mtoolroot_b = self.sh.path.join(self.tmpdir, 'mtool', 'cache')
        for remap in self._REMAPS:
            self.assertEqual(storage_b._formatted_path(remap['item']),
                             remap['buddiespath'].format(mtoolroot_b))
            self.assertTrue(storage_b.allow_writes(remap['item']))
            self.assertFalse(storage_b.allow_reads(remap['item']))
        self.sh.mkdir('mtool/cache/vortexbuddies/arome/3dvarfr')
        item = self._REMAPS[0]['item']
        self.assertTrue(storage_b.allow_reads(item))
        self.assertFalse(storage_b.check(item))
        self.sh.symlink('{:s}/vortex/arome/3dvarfr/ABCD'.format(mtoolroot),
                        'mtool/cache/vortexbuddies/arome/3dvarfr/ABCD',)
        self.assertTrue(storage_b.check(item))
        self.assertTrue(storage_b.retrieve(item, 'rtestfile2'))
        self.assertIsTestFile('rtestfile2')
        # Delete...
        self.assertTrue(storage.delete(item))
        self.assertFalse(storage.check(item))

    def test_empty_marketplace(self):
        storage = fp.proxy.cache(kind='emptymarketplace', **self.commons)
        for remap in self._REMAPS:
            self.assertFalse(storage.allow_writes(remap['item']))
            self.assertFalse(storage.allow_reads(remap['item']))
            self.assertFalse(storage.check(remap['item']))
            self.assertIsNone(storage.list(remap['item']))
            self.assertFalse(storage.insert(remap['item'], self.tfile))
            self.assertFalse(storage.retrieve(remap['item'], 'blop'))

    def test_marketplace(self):
        storage = fp.proxy.cache(kind='marketplace', **self.commons)
        for i, remap in enumerate(self._REMAPS):
            if remap['marketpath']:
                marketrw = remap.get('marketrw', False)
                if marketrw:
                    self.assertTrue(storage.allow_writes(remap['item']))
                else:
                    self.assertFalse(storage.allow_writes(remap['item']))
                self.assertTrue(storage.allow_reads(remap['item']))
                self.assertEqual(storage._formatted_path(remap['item']),
                                 remap['marketpath'])
                self.assertFalse(storage.check(remap['item']))
                if marketrw:
                    self.assertTrue(storage.insert(remap['item'], self.tfile))
                    self.assertIsTestFile(remap['marketpath'])
                    self.assertTrue(storage.retrieve(remap['item'], 'rtestfile{:d}'.format(i)))
                    self.assertIsTestFile('rtestfile{:d}'.format(i))
                    self.assertTrue(storage.check(remap['item']))
                    self.assertTrue(storage.delete(remap['item']))
                    self.assertFalse(storage.check(remap['item']))
                else:
                    self.assertFalse(storage.insert(remap['item'], self.tfile))
            else:
                self.assertFalse(storage.allow_writes(remap['item']))
                self.assertFalse(storage.allow_reads(remap['item']))
                self.assertEqual(storage._formatted_path(remap['item']), None)
                self.assertFalse(storage.check(remap['item']))
                self.assertFalse(storage.insert(remap['item'], self.tfile))


if __name__ == "__main__":
    unittest.main(verbosity=2)
