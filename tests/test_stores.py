import os
import pickle
import tempfile
import unittest

from bronx.fancies.loggers import unittestGlobalLevel

import footprints as fp

import vortex  # @UnusedImport
import vortex.data.stores
from vortex.tools.net import uriparse, uriunparse
from bronx.datagrip.datastore import DataStore

DATAPATHTEST = os.path.join(os.path.dirname(__file__), 'data')

TLOGLEVEL = 9999


@unittestGlobalLevel(TLOGLEVEL)
class AbstractTestStores(unittest.TestCase):

    def setUp(self):
        # Generate a temporary directory
        self.t = vortex.sessions.current()
        self.sh = self.t.system()
        self.sh.target(hostname='unittest', inetname='unittest',
                       inifile=os.path.join(DATAPATHTEST, 'target-test.ini'),
                       sysname='Local')  # Trick the vortex's system !
        self.tmpdir = self.sh.path.realpath(tempfile.mkdtemp(suffix='_test_stores'))
        self.oldpwd = self.sh.pwd()
        self.sh.cd(self.tmpdir)

    def tearDown(self):
        self.sh.target()
        self.sh.cd(self.oldpwd)
        self.sh.remove(self.tmpdir)


class TestVortexArchiveStore(AbstractTestStores):

    _TEST_STORAGE = 'unittesttarget.fake.com'

    _TEST_BUCKET = 'xtest.bucket.localhost'

    _HEAD = 'vortex'

    _REMAPS = [
        # Vortex Standard
        dict(uri='vortex://vortex.archive-legacy.fr/arome/3dvarfr/ABCD/20180101T0000A/forecast/unittest',
             rread='vortex://vortex.archive-legacy.fr/arome/3dvarfr/A/B/C/D/20180101T0000A/forecast/unittest',
             rread_root='/home/m/marp/marp999',
             rwrite='vortex://vortex.archive-legacy.fr/arome/3dvarfr/ABCD/20180101T0000A/forecast/unittest',
             rwrite_root=''),
        dict(uri='vortex://vortex.archive-legacy.fr/arome/3dvarfr/ABCD/forecast/unittest',
             rread='vortex://vortex.archive-legacy.fr/arome/3dvarfr/A/B/C/D/forecast/unittest',
             rread_root='/home/m/marp/marp999',
             rwrite='vortex://vortex.archive-legacy.fr/arome/3dvarfr/ABCD/forecast/unittest',
             rwrite_root=''),
        dict(uri='vortex://vortex.archive-legacy.fr/arome/3dvarfr/ABCD/20180101T0000-20180101T1800/forecast/unittest',
             rread='vortex://vortex.archive-legacy.fr/arome/3dvarfr/A/B/C/D/20180101T0000-20180101T1800/forecast/unittest',
             rread_root='/home/m/marp/marp999',
             rwrite='vortex://vortex.archive-legacy.fr/arome/3dvarfr/ABCD/20180101T0000-20180101T1800/forecast/unittest',
             rwrite_root=''),
        # Vortex Op
        dict(uri='vortex://vsop.archive-legacy.fr/arome/3dvarfr/OPER/20180101T0000A/forecast/unittest',
             rread='vortex://vsop.archive-legacy.fr/arome/3dvarfr/OPER/2018/01/01/T0000A/forecast/unittest',
             rread_root='/home/m/mxpt/mxpt001',
             rwrite='vortex://vsop.archive-legacy.fr/arome/3dvarfr/OPER/2018/01/01/T0000A/forecast/unittest',
             rwrite_root='/home/m/mxpt/mxpt001'),
        dict(uri='vortex://vsop.archive-legacy.fr/arome/3dvarfr/OPER/forecast/unittest',
             rread='vortex://vsop.archive-legacy.fr/arome/3dvarfr/OPER/forecast/unittest',
             rread_root='/home/m/mxpt/mxpt001',
             rwrite='vortex://vsop.archive-legacy.fr/arome/3dvarfr/OPER/forecast/unittest',
             rwrite_root='/home/m/mxpt/mxpt001'),
        dict(uri='vortex://vsop.archive-legacy.fr/arome/3dvarfr/OPER/20180101T0000-20180101T1800/forecast/unittest',
             rread='vortex://vsop.archive-legacy.fr/arome/3dvarfr/OPER/2018/01/01/T0000-20180101T1800/forecast/unittest',
             rread_root='/home/m/mxpt/mxpt001',
             rwrite='vortex://vsop.archive-legacy.fr/arome/3dvarfr/OPER/2018/01/01/T0000-20180101T1800/forecast/unittest',
             rwrite_root='/home/m/mxpt/mxpt001'),
    ]

    _REMAPS_BUCKET = [
        # Vortex Standard
        dict(uri='vortex://vortex.archive-legacy.fr/arome/3dvarfr/ABCD/20180101T0000A/forecast/unittest',
             rread='vortex://vortex.archive-legacy.fr/arome/3dvarfr/ABCD/20180101T0000A/forecast/unittest',
             rread_root='',
             rwrite='vortex://vortex.archive-legacy.fr/arome/3dvarfr/ABCD/20180101T0000A/forecast/unittest',
             rwrite_root=''),
        dict(uri='vortex://vortex.archive-legacy.fr/arome/3dvarfr/ABCD/forecast/unittest',
             rread='vortex://vortex.archive-legacy.fr/arome/3dvarfr/ABCD/forecast/unittest',
             rread_root='',
             rwrite='vortex://vortex.archive-legacy.fr/arome/3dvarfr/ABCD/forecast/unittest',
             rwrite_root=''),
        dict(uri='vortex://vortex.archive-legacy.fr/arome/3dvarfr/ABCD/20180101T0000-20180101T1800/forecast/unittest',
             rread='vortex://vortex.archive-legacy.fr/arome/3dvarfr/ABCD/20180101T0000-20180101T1800/forecast/unittest',
             rread_root='',
             rwrite='vortex://vortex.archive-legacy.fr/arome/3dvarfr/ABCD/20180101T0000-20180101T1800/forecast/unittest',
             rwrite_root=''),
        # Vortex Op
        dict(uri='vortex://vsop.archive-legacy.fr/arome/3dvarfr/OPER/20180101T0000A/forecast/unittest',
             rread='vortex://vsop.archive-legacy.fr/arome/3dvarfr/OPER/20180101T0000A/forecast/unittest',
             rread_root='',
             rwrite='vortex://vsop.archive-legacy.fr/arome/3dvarfr/OPER/20180101T0000A/forecast/unittest',
             rwrite_root=''),
        dict(uri='vortex://vsop.archive-legacy.fr/arome/3dvarfr/OPER/forecast/unittest',
             rread='vortex://vsop.archive-legacy.fr/arome/3dvarfr/OPER/forecast/unittest',
             rread_root='',
             rwrite='vortex://vsop.archive-legacy.fr/arome/3dvarfr/OPER/forecast/unittest',
             rwrite_root=''),
        dict(uri='vortex://vsop.archive-legacy.fr/arome/3dvarfr/OPER/20180101T0000-20180101T1800/forecast/unittest',
             rread='vortex://vsop.archive-legacy.fr/arome/3dvarfr/OPER/20180101T0000-20180101T1800/forecast/unittest',
             rread_root='',
             rwrite='vortex://vsop.archive-legacy.fr/arome/3dvarfr/OPER/20180101T0000-20180101T1800/forecast/unittest',
             rwrite_root=''),
    ]

    _REMAPS_CONFIGURABLE = [
        # Vortex Free
        dict(uri='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/ABCD@unittest/20180101T0000A/forecast/unittest',
             rread='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/ABCD/20180101T0000A/forecast/unittest',
             rread_root='~unittest',
             rwrite='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/ABCD/20180101T0000A/forecast/unittest',
             rwrite_root='~unittest'),
        dict(uri='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/ABCD@unittest/forecast/unittest',
             rread='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/ABCD/forecast/unittest',
             rread_root='~unittest',
             rwrite='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/ABCD/forecast/unittest',
             rwrite_root='~unittest'),
        dict(uri='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/ABCD@tata/20180101T0000-20180101T1800/forecast/unittest',
             rread='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/ABCD/20180101T0000-20180101T1800/forecast/unittest',
             rread_root='/somwhere/lies/tata',
             rwrite='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/ABCD/20180101T0000-20180101T1800/forecast/unittest',
             rwrite_root='/somwhere/lies/tata'),
        dict(uri='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/ABCD@toto15/20180101T0000-20180101T1800/forecast/unittest',
             rread='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/ABCD/20180101T0000-20180101T1800/forecast/unittest',
             rread_root='/somwhere/lies/toto15',
             rwrite='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/ABCD/20180101T0000-20180101T1800/forecast/unittest',
             rwrite_root='/somwhere/lies/toto15'),
        dict(
            uri='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/special666@toto15/20180101T0000-20180101T1800/forecast/unittest',
            rread='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/special666/20180101T0000-20180101T1800/forecast/unittest',
            rread_root='/somwhere/lies/toto15_by_foo',
            rwrite='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/special666/20180101T0000-20180101T1800/forecast/unittest',
            rwrite_root='/somwhere/lies/toto15_by_foo'),
        dict(
            uri='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/other_stuff@toto15/20180101T0000-20180101T1800/forecast/unittest',
            rread='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/other_stuff/20180101T0000-20180101T1800/forecast/unittest',
            rread_root='/somwhere/lies/toto15_by_foo',
            rwrite='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/other_stuff/20180101T0000-20180101T1800/forecast/unittest',
            rwrite_root='/somwhere/lies/toto15_by_foo'),
        dict(
            uri='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/special1@toto16/20180101T0000-20180101T1800/forecast/unittest',
            rread='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/special1/20180101T0000-20180101T1800/forecast/unittest',
            rread_root='/somwhere/lies/masked_guy',
            rwrite='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/special1/20180101T0000-20180101T1800/forecast/unittest',
            rwrite_root='/somwhere/lies/masked_guy'),
        # Two times in a row (to test the cache)
        dict(
            uri='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/special1@toto16/20180101T0000-20180101T1800/forecast/unittest',
            rread='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/special1/20180101T0000-20180101T1800/forecast/unittest',
            rread_root='/somwhere/lies/masked_guy',
            rwrite='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/special1/20180101T0000-20180101T1800/forecast/unittest',
            rwrite_root='/somwhere/lies/masked_guy'),
        dict(
            uri='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/nope@toto16/20180101T0000-20180101T1800/forecast/unittest',
            rread='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/nope/20180101T0000-20180101T1800/forecast/unittest',
            rread_root='~toto16',
            rwrite='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/nope/20180101T0000-20180101T1800/forecast/unittest',
            rwrite_root='~toto16'),
        dict(uri='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/ABCD@titi/20180101T0000-20180101T1800/forecast/unittest',
             rread='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/ABCD/20180101T0000-20180101T1800/forecast/unittest',
             rread_root='~titi',
             rwrite='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/ABCD/20180101T0000-20180101T1800/forecast/unittest',
             rwrite_root='~titi'),
        dict(
            uri='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/ABCD@self/20180101T0000-20180101T1800/forecast/unittest',
            rread='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/ABCD/20180101T0000-20180101T1800/forecast/unittest',
            rread_root='~',
            rwrite='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/ABCD/20180101T0000-20180101T1800/forecast/unittest',
            rwrite_root='~'),
    ]

    _REMAPS_CONFIGURABLE_BUCKET = [
        # Vortex Free
        dict(uri='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/ABCD@unittest/20180101T0000A/forecast/unittest',
             rread='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/ABCD@unittest/20180101T0000A/forecast/unittest',
             rread_root='',
             rwrite='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/ABCD@unittest/20180101T0000A/forecast/unittest',
             rwrite_root=''),
        dict(uri='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/ABCD@unittest/forecast/unittest',
             rread='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/ABCD@unittest/forecast/unittest',
             rread_root='',
             rwrite='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/ABCD@unittest/forecast/unittest',
             rwrite_root=''),
        dict(uri='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/ABCD@tata/20180101T0000-20180101T1800/forecast/unittest',
             rread='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/ABCD@tata/20180101T0000-20180101T1800/forecast/unittest',
             rread_root='',
             rwrite='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/ABCD@tata/20180101T0000-20180101T1800/forecast/unittest',
             rwrite_root=''),
        dict(uri='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/ABCD@toto15/20180101T0000-20180101T1800/forecast/unittest',
             rread='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/ABCD@toto15/20180101T0000-20180101T1800/forecast/unittest',
             rread_root='',
             rwrite='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/ABCD@toto15/20180101T0000-20180101T1800/forecast/unittest',
             rwrite_root=''),
        dict(
            uri='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/special666@toto15/20180101T0000-20180101T1800/forecast/unittest',
            rread='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/special666@toto15/20180101T0000-20180101T1800/forecast/unittest',
            rread_root='',
            rwrite='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/special666@toto15/20180101T0000-20180101T1800/forecast/unittest',
            rwrite_root=''),
        dict(
            uri='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/other_stuff@toto15/20180101T0000-20180101T1800/forecast/unittest',
            rread='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/other_stuff@toto15/20180101T0000-20180101T1800/forecast/unittest',
            rread_root='',
            rwrite='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/other_stuff@toto15/20180101T0000-20180101T1800/forecast/unittest',
            rwrite_root=''),
        dict(
            uri='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/special1@toto16/20180101T0000-20180101T1800/forecast/unittest',
            rread='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/special1@toto16/20180101T0000-20180101T1800/forecast/unittest',
            rread_root='',
            rwrite='vortex://vortex-free.archive-legacy.fr/arome/3dvarfr/special1@toto16/20180101T0000-20180101T1800/forecast/unittest',
            rwrite_root=''),
    ]

    def setUp(self):
        super().setUp()
        # Link in test config files
        self.sh.symlink(self.sh.path.join(DATAPATHTEST, 'store-vortex-free-testL.ini'),
                        'test_localconf.ini')
        self.sh.symlink(self.sh.path.join(DATAPATHTEST, 'store-vortex-free-testR0.ini'),
                        'test_remoteconf0.ini')
        self.sh.symlink(self.sh.path.join(DATAPATHTEST, 'store-vortex-free-testR1.ini'),
                        'test_remoteconf1.ini')

    def _do_remap_asserts(self, remaps, storage=_TEST_STORAGE):
        for remap in remaps:
            puri = uriparse(remap['uri'])
            st = fp.proxy.store(scheme=puri['scheme'], netloc=puri['netloc'],
                                storage=storage)
            puri2 = st.remap_read(puri, dict())
            self.assertEqual(uriunparse(list(puri2.values())[:6]), remap['rread'])
            self.assertEqual(puri2.get('root', ''), remap['rread_root'])
            if storage == self._TEST_BUCKET:
                self.assertEqual(st._inarchiveformatpath(puri2),
                                 self.sh.path.join(st.scheme, st.netloc, self._HEAD,
                                                   puri2['path'])
                                 )
            else:
                self.assertEqual(st._inarchiveformatpath(puri2),
                                 self.sh.path.join(remap['rread_root'],
                                                   self._HEAD,
                                                   puri2['path'])
                                 )
            puri2 = st.remap_write(puri, dict())
            self.assertEqual(uriunparse(list(puri2.values())[:6]), remap['rwrite'])
            self.assertEqual(puri2.get('root', ''), remap['rwrite_root'])

    def test_remaps1(self):
        self._do_remap_asserts(self._REMAPS)
        self._do_remap_asserts(self._REMAPS_BUCKET, self._TEST_BUCKET)

    def test_remaps2(self):
        self._do_remap_asserts(self._REMAPS_CONFIGURABLE)
        # Also test that the datastore is picklable
        ds = self.t.datastore
        conf = ds.get(vortex.data.stores.VortexFreeStdBaseArchiveStore._datastore_id,
                      dict(storage=self._TEST_STORAGE))
        pickle.dumps(conf, DataStore._PICKLE_PROTOCOL)
        # Bucket
        self._do_remap_asserts(self._REMAPS_CONFIGURABLE_BUCKET, self._TEST_BUCKET)

    def test_use_cache_and_archive(self):
        st = fp.proxy.store(scheme='vortex', netloc='vortex.archive-legacy.fr',
                            storage=self._TEST_STORAGE)
        self.assertFalse(st.use_cache())
        self.assertTrue(st.use_archive())
        st = fp.proxy.store(scheme='vortex', netloc='vortex.archive.fr',
                            storage=self._TEST_STORAGE)
        self.assertFalse(st.use_cache())
        self.assertTrue(st.use_archive())


class TestVortexCacheStore(AbstractTestStores):

    _REMAPS = [
        # Vortex Standard
        dict(uri='vortex://vortex.cache.fr/arome/3dvarfr/ABCD/20180101T0000A/forecast/unittest',
             located='{mtroot:s}/vortex/arome/3dvarfr/ABCD/20180101T0000A/forecast/unittest'),
        # Vortex OP
        dict(uri='vortex://vsop.cache.fr/arome/3dvarfr/ABCD/20180101T0000A/forecast/unittest',
             located=('{mtroot:s}/vortex/arome/3dvarfr/ABCD/20180101T0000A/forecast/unittest;' +
                      '{oproot1:s}/vortex/arome/3dvarfr/ABCD/20180101T0000A/forecast/unittest')),
        # Vortex Standard with stack
        dict(uri=('vortex://vortex.cache.fr/arome/3dvarfr/ABCD/20180101T0000P/forecast/listing.arpege-gruik.all' +
                  '?stackfmt=filespack&stackpath=arome%2F3dvarfr%2FABCD%2F20180101T0000P%2Fstacks%2Fflow_logs.filespack'),
             located=('{mtroot:s}/vortex/arome/3dvarfr/ABCD/20180101T0000P/forecast/listing.arpege-gruik.all;' +
                      '{mtroot:s}/vortex/arome/3dvarfr/ABCD/20180101T0000P/stacks/flow_logs.filespack/' +
                      'forecast/listing.arpege-gruik.all')),
        # Vortex OP with stack
        dict(uri=('vortex://vsop.cache.fr/arome/3dvarfr/ABCD/20180101T0000P/forecast/listing.arpege-gruik.all' +
                  '?stackfmt=filespack&stackpath=arome%2F3dvarfr%2FABCD%2F20180101T0000P%2Fstacks%2Fflow_logs.filespack'),
             located=('{mtroot:s}/vortex/arome/3dvarfr/ABCD/20180101T0000P/forecast/listing.arpege-gruik.all;' +
                      '{mtroot:s}/vortex/arome/3dvarfr/ABCD/20180101T0000P/stacks/flow_logs.filespack/' +
                      'forecast/listing.arpege-gruik.all;' +
                      '{oproot1:s}/vortex/arome/3dvarfr/ABCD/20180101T0000P/forecast/listing.arpege-gruik.all;' +
                      '{oproot1:s}/vortex/arome/3dvarfr/ABCD/20180101T0000P/stacks/flow_logs.filespack/' +
                      'forecast/listing.arpege-gruik.all')),
        # Vortex Standard Stack cache
        dict(uri=('vortex://vortex.stack.fr/arome/3dvarfr/ABCD/20180101T0000P/forecast/listing.arpege-gruik.all' +
                  '?stackfmt=filespack&stackpath=arome%2F3dvarfr%2FABCD%2F20180101T0000P%2Fstacks%2Fflow_logs.filespack'),
             located=('{mtroot:s}/vortex/arome/3dvarfr/ABCD/20180101T0000P/stacks/flow_logs.filespack/' +
                      'forecast/listing.arpege-gruik.all')),
        # Vortex OP Stack cache
        dict(uri=('vortex://vsop.stack.fr/arome/3dvarfr/ABCD/20180101T0000P/forecast/listing.arpege-gruik.all' +
                  '?stackfmt=filespack&stackpath=arome%2F3dvarfr%2FABCD%2F20180101T0000P%2Fstacks%2Fflow_logs.filespack'),
             located=('{mtroot:s}/vortex/arome/3dvarfr/ABCD/20180101T0000P/stacks/flow_logs.filespack/' +
                      'forecast/listing.arpege-gruik.all;' +
                      '{oproot1:s}/vortex/arome/3dvarfr/ABCD/20180101T0000P/stacks/flow_logs.filespack/' +
                      'forecast/listing.arpege-gruik.all')),
    ]

    def setUp(self):
        super().setUp()
        self.oldmtdir = self.sh.env.get('MTOOLDIR')
        self.sh.mkdir('mtool')
        self.sh.env['MTOOLDIR'] = self.sh.path.join(self.tmpdir, 'mtool')

    def tearDown(self):
        if self.oldmtdir:
            self.sh.env['MTOOLDIR'] = self.oldmtdir
        else:
            del self.sh.env['MTOOLDIR']
        super().tearDown()

    def _do_loc_asserts(self, remaps):
        for remap in remaps:
            puri = uriparse(remap['uri'])
            st = fp.proxy.store(scheme=puri['scheme'], netloc=puri['netloc'],
                                storage='unittesttarget.fake.com')
            plocated = st.locate(puri, dict())
            mtroot = self.sh.path.join(self.sh.env['MTOOLDIR'], 'cache')
            oproot1 = '/toto1/mxpt001/vortex/mtool/cache'
            self.assertEqual(plocated,
                             remap['located'].format(mtroot=mtroot,
                                                     oproot1=oproot1))

    def test_remaps1(self):
        self._do_loc_asserts(self._REMAPS)

    def test_use_cache_and_archive(self):
        st = fp.proxy.store(scheme='vortex', netloc='vortex.cache.fr')
        self.assertTrue(st.use_cache())
        self.assertFalse(st.use_archive())
        st = fp.proxy.store(scheme='vortex', netloc='vortex.stack.fr')
        self.assertTrue(st.use_cache())
        self.assertFalse(st.use_archive())


class TestVortexMultiStore(AbstractTestStores):

    def test_use_cache_and_archive(self):
        st = fp.proxy.store(scheme='vortex', netloc='vortex.multi-legacy.fr')
        self.assertTrue(st.use_cache())
        self.assertTrue(st.use_archive())
        st = fp.proxy.store(scheme='vortex', netloc='vortex.multi.fr')
        self.assertTrue(st.use_cache())
        self.assertTrue(st.use_archive())


class TestFunctionStore(AbstractTestStores):

    def test_basics(self):
        furi = uriparse('function:///sandbox.util.storefunctions.echofunction?msg=toto&msg=titi')
        st = fp.proxy.store(scheme=furi['scheme'], netloc=furi['netloc'])
        self.assertEqual(st.locate(furi, dict(fmt='ascii')),
                         'sandbox.util.storefunctions.echofunction')
        self.assertTrue(st.get(furi, 'echotest', dict(fmt='ascii')))
        with open('echotest') as fhe:
            lines = fhe.readlines()
        self.assertIn('Message #0 is: toto\n', lines)
        self.assertIn('Message #1 is: titi\n', lines)
        self.assertTrue(st.get(furi, 'echotest', dict(fmt='ascii', intent='in')))
        self.assertFalse(st.put('echotest', furi, dict(fmt='ascii')))
        self.assertFalse(st.put('echotest', furi, dict(fmt='ascii')))
        self.assertFalse(st.delete(furi, dict(fmt='ascii')))
        self.assertFalse(st.check(furi, dict(fmt='ascii')))


class TestFinderStore(AbstractTestStores):

    def test_basics(self):
        with open('findertest', 'w') as fhf:
            fhf.write('findme')

        st = fp.proxy.store(scheme='file', netloc='')
        fileuri = uriparse('file:///findertest?relative=1')
        fileuri2 = uriparse('file:///findertest_bis?relative=1')
        fakeuri = uriparse('file:///tmp/nofindertest')
        self.assertEqual(st.locate(fakeuri, dict(fmt='foo')), '/tmp/nofindertest')
        self.assertEqual(st.check(fileuri, dict(fmt='foo')).st_size, 6)
        self.assertFalse(st.check(fakeuri, dict(fmt='foo')))
        self.assertFalse(st.get(fakeuri, 'toto', dict(fmt='foo')))
        self.assertTrue(st.get(fileuri, 'toto', dict(fmt='foo')))
        with open('toto') as fhf:
            self.assertEqual(fhf.read(), 'findme')
        self.assertTrue(st.get(fileuri, 'toto', dict(fmt='foo', intent='in')))
        self.assertTrue(st.put('toto', fileuri2, dict(fmt='foo')))
        self.assertFalse(st.delete(fakeuri, dict(fmt='foo')))
        self.assertTrue(st.delete(fileuri, dict(fmt='foo')))
        st = fp.proxy.store(scheme='symlink', netloc='')
        self.assertTrue(st.get(fileuri2, 'toto_link', dict(fmt='foo', intent='in')))
        self.assertFalse(st.get(fileuri2, 'toto_link_bis', dict(fmt='foo', intent='inout')))
        self.assertEqual(self.sh.path.realpath('toto_link'),
                         self.sh.path.join(self.tmpdir, 'findertest_bis'))
        self.assertFalse(st.check(fileuri, dict(fmt='foo')))
        self.assertFalse(st.delete(fileuri2, dict(fmt='foo')))
        self.assertFalse(st.put('toto', fileuri, dict(fmt='foo')))


if __name__ == "__main__":
    unittest.main(verbosity=2)
