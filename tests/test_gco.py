import os
import tempfile
import unittest

from bronx.fancies import loggers
import footprints as fp

import vortex
from vortex.tools.net import uriparse
import iga.data.stores
from gco.data.stores import UgetArchiveStore
from gco.tools import genv, uenv
from ..syntax.stdattrs import AbstractUgetId, GgetId, ArpIfsSimplifiedCycle

DATAPATHTEST = os.path.join(os.path.dirname(__file__), 'data')

assert iga.data.stores

tloglevel = 'error'


class FooResource:

    def __init__(self, gvar='tools_lfi'):
        self.gvar = gvar

    def basename(self, prkind):
        if prkind in ('genv', 'uenv'):
            return self.gvar
        elif prkind in ('gget', 'uget'):
            return dict(suffix='.m01')  # Simulate a monthly data
        else:
            raise ValueError

    @staticmethod
    def urlquery(prkind):
        if prkind in ('genv', 'gget', 'uenv', 'uget'):
            return 'extract=toto'  # Simulate an extract
        else:
            raise ValueError


class PrivateCocoonGcoTest(unittest.TestCase):

    _TEST_SESSION_NAME = None

    def setUp(self):
        self.cursession = vortex.sessions.current()
        self.t = vortex.sessions.get(tag=self._TEST_SESSION_NAME,
                                     topenv=vortex.rootenv,
                                     glove=self.cursession.glove)
        self.t.activate()
        self.sh = self.t.sh
        # Tweak the target object
        self.testconf = os.path.join(DATAPATHTEST, 'target-test.ini')
        self.sh.target(inifile=self.testconf, sysname='Linux')
        # Temp directory
        self.tmpdir = tempfile.mkdtemp(suffix='test_gget_uget_uenv')
        self.oldpwd = self.sh.pwd()
        self.sh.cd(self.tmpdir)
        # Tweak the HOME directory in order to trick Uenv/Uget hack store
        self.sh.env.HOME = self.tmpdir
        # Set-up the MTOOLDIR
        self.sh.env.MTOOLDIR = self.tmpdir

    def tearDown(self):
        # Do some cleaning
        self.sh.cd(self.oldpwd)
        self.sh.rmtree(self.tmpdir)
        # Go back to the original session
        self.cursession.activate()


@loggers.unittestGlobalLevel(tloglevel)
class TestGcoGget(PrivateCocoonGcoTest):

    _TEST_SESSION_NAME = 'test_session_gco_gget_1'

    def setUp(self):
        super().setUp()
        self.fakegget = os.path.join(DATAPATHTEST, 'fake_gget')

    def test_paths(self):
        st = fp.proxy.store(scheme='gget', netloc='gco.meteo.fr')
        self.assertEqual(st._actualgget('toto'),
                         (['gget', '-host', None], 'toto'))
        with self.t.sh.env.clone() as lenv:
            lenv.VORTEX_ARCHIVE_HOST = 'hendrix'
            self.assertEqual(st._actualgget('/toto'),
                             (['gget', '-host', 'hendrix'], 'toto'))
            self.assertEqual(st._actualgget('truc/toto'),
                             (['gget', '-host', 'hendrix'], 'toto'))
            lenv.VORTEX_ARCHIVE_USER = 'machin'
            self.assertEqual(st._actualgget('truc/toto'),
                             (['gget', '-host', 'hendrix', '-user', 'machin'],
                              'toto'))

    def assert_mantra(self, somefile):
        self.assertTrue(os.path.isfile(somefile))
        with open(somefile) as fh_s:
            self.assertEqual(fh_s.read(), 'This is a fake gget file.')

    def test_central_store_alone(self):
        st = fp.proxy.store(scheme='gget', netloc='gco.meteo.fr',
                            ggetpath=self.fakegget, ggetarchive='somehost')
        # Simple file
        self.assertTrue(st.get(uriparse('gget://gco.meteo.fr/fakefile.01'),
                               'somefile01', dict()))
        self.assert_mantra('somefile01')
        # Directory
        self.assertTrue(st.get(uriparse('gget://gco.meteo.fr/fakedir.01?dir_extract=0'),
                               'somedir01', dict()))
        self.assertTrue(st.get(uriparse('gget://gco.meteo.fr/fakedir.01?dir_extract=1'),
                               'somedir02', dict()))
        self.assertTrue(st.get(uriparse('gget://gco.meteo.fr/fakearchive.01.tgz?dir_extract=1'),
                               'tar_as_dir', dict()))
        for where in ('somedir01', 'somedir02', 'tar_as_dir'):
            self.assert_mantra(os.path.join(where, 'file1'))
            self.assert_mantra(os.path.join(where, 'file4'))
            self.assertTrue(os.path.islink(os.path.join(where, 'file4')))
            self.assertTrue(os.path.isdir(os.path.join(where, 'subdir')))
        # Directory with extract
        self.assertTrue(st.get(uriparse('gget://gco.meteo.fr/fakedir.01?extract=file4'),
                               'extracted', dict()))
        self.assert_mantra('extracted')
        # Directory with extract
        self.assertTrue(st.get(uriparse('gget://gco.meteo.fr/fakedir.01?extract=file5'),
                               'extracted_bis', dict()))
        self.assert_mantra('extracted_bis')
        # Directory with extract
        self.assertTrue(st.get(uriparse('gget://gco.meteo.fr/fakedir.01?extract=file6'),
                               'extracted_ter', dict()))
        self.assertFalse(os.path.islink('extracted_ter'))
        self.assert_mantra('extracted_ter')
        # Tar file
        self.assertTrue(st.get(uriparse('gget://gco.meteo.fr/fakearchive.01.tgz'),
                               'fulltoto', dict()))
        self.assertTrue(os.path.exists('fulltoto'))
        self.assertFalse(os.path.exists('file1'))
        self.assertTrue(st.get(uriparse('gget://gco.meteo.fr/fakearchive.01.tgz'),
                               'toto.tgz', dict()))
        self.assertTrue(os.path.exists('toto.tgz'))
        self.assert_mantra('file1')
        self.assert_mantra('file4')
        self.assertTrue(os.path.islink('file4'))
        self.assertTrue(os.path.isdir('subdir'))

    def test_multi_store(self):
        gcocache = os.path.join(self.tmpdir, 'cache', 'gco')
        st = fp.proxy.store(scheme='gget', netloc='gco.multi.fr')
        with self.t.sh.env.clone() as lenv:
            lenv.VORTEX_ARCHIVE_HOST = 'somehost'
            lenv.GGET_PATH = self.fakegget
            self.assertTrue(st.get(uriparse('gget://gco.multi.fr/fakefile.01'),
                                   'somefile01', dict()))
            self.assertTrue(st.get(uriparse('gget://gco.multi.fr/fakedir.01?extract=file4'),
                                   'extracted', dict()))
            self.assert_mantra('extracted')
            self.assertTrue(st.get(uriparse('gget://gco.multi.fr/fakedir.02?dir_extract=1'),
                                   'somedir01', dict()))
            self.assertTrue(st.get(uriparse('gget://gco.multi.fr/fakedir.02'),
                                   'somedir02', dict()))
            self.assertTrue(st.check(uriparse('gget://gco.multi.fr/fakedir.02'), dict()))
            self.assertTrue(st.check(uriparse('gget://gco.multi.fr/fakedir.02?dir_extract=1'),
                                     dict()))
            for where in ('somedir01', 'somedir02'):
                self.assert_mantra(self.sh.path.join(where, 'file1'))
                self.assert_mantra(self.sh.path.join(where, 'file4'))
                self.assertTrue(self.sh.path.islink(self.sh.path.join(where, 'file4')))
                self.assertTrue(self.sh.path.isdir(self.sh.path.join(where, 'subdir')))
            self.assertTrue(st.get(uriparse('gget://gco.multi.fr/fakearchive.01.tgz'),
                            'totofull', dict()))
        # Refill should be ok...
        with self.sh.cdcontext('fromcache', create=True):
            st = fp.proxy.store(scheme='gget', netloc='gco.cache.fr')
            self.assertTrue(st.get(uriparse('gget://gco.cache.fr/fakefile.01'),
                                   'somefile01', dict()))
            self.assertTrue(st.get(uriparse('gget://gco.cache.fr/fakedir.01?extract=file4'),
                                   'extracted', dict()))
            self.assert_mantra('extracted')
            self.assertTrue(st.get(uriparse('gget://gco.cache.fr/fakedir.02'),
                                   'somedir01', dict()))
            self.assertTrue(st.get(uriparse('gget://gco.cache.fr/fakedir.02?dir_extract=1'),
                                   'somedir02', dict()))
            for where in ('somedir01', 'somedir02'):
                self.assert_mantra(self.sh.path.join(where, 'file1'))
                self.assert_mantra(self.sh.path.join(where, 'file4'))
                self.assertTrue(self.sh.path.islink(self.sh.path.join(where, 'file4')))
                self.assertTrue(self.sh.path.isdir(self.sh.path.join(where, 'subdir')))
            # Stress the check/locate/delete methods
            self.assertTrue(st.check(uriparse('gget://gco.cache.fr/fakedir.02'), dict()))
            self.assertTrue(st.check(uriparse('gget://gco.cache.fr/fakedir.02?dir_extract=1'), dict()))
            fdir_location = st.locate(uriparse('gget://gco.cache.fr/fakedir.02'), dict())
            self.assertEqual(self.sh.path.join(gcocache, 'fakedir.02'),
                             fdir_location)
            fdir_locationE = st.locate(uriparse('gget://gco.cache.fr/fakedir.02?dir_extract=1'), dict())
            self.assertEqual(self.sh.path.join(gcocache, 'fakedir.02.autoextract'),
                             fdir_locationE)
            # Remove one of the files the .autoextract
            self.sh.rm(self.sh.path.join(fdir_locationE, 'file4'))
            self.assertTrue(st.check(uriparse('gget://gco.cache.fr/fakedir.02'), dict()))
            self.assertFalse(st.check(uriparse('gget://gco.cache.fr/fakedir.02?dir_extract=1'), dict()))
            self.assertFalse(st.get(uriparse('gget://gco.cache.fr/fakedir.02?dir_extract=1'),
                                    'somedir02ko', dict()))
            # Remove the index and check again...
            self.sh.mv(fdir_location + '.index', fdir_location + '.indexold')
            self.assertFalse(st.check(uriparse('gget://gco.cache.fr/fakedir.02'), dict()))
            self.assertFalse(st.check(uriparse('gget://gco.cache.fr/fakedir.02?dir_extract=1'), dict()))
            self.assertFalse(st.get(uriparse('gget://gco.cache.fr/fakedir.02'),
                                    'somedir01ko', dict()))
            self.assertFalse(self.sh.path.exists('somedir01ko'))
            self.assertTrue(st.check(uriparse('gget://gco.cache.fr/fakedir.02?extract=file1'), dict()))
            self.sh.mv(fdir_location + '.indexold', fdir_location + '.index')
            self.assertEqual(self.sh.path.join(gcocache, 'fakedir.02.autoextract', 'file1'),
                             st.locate(uriparse('gget://gco.cache.fr/fakedir.02?extract=file1'), dict()))
            self.assertTrue(st.delete(uriparse('gget://gco.cache.fr/fakedir.02?extract=file1'), dict()))
            self.assertFalse(st.check(uriparse('gget://gco.cache.fr/fakedir.02?extract=file1'), dict()))
            self.assertTrue(st.check(uriparse('gget://gco.cache.fr/fakedir.02'), dict()))
            self.assertTrue(st.delete(uriparse('gget://gco.cache.fr/fakedir.02'), dict()))
            self.assertTrue(st.delete(uriparse('gget://gco.cache.fr/fakedir.02?dir_extract=1'), dict()))
            self.assertFalse(self.sh.path.exists(fdir_locationE))
            self.assertFalse(st.check(uriparse('gget://gco.cache.fr/fakedir.02'), dict()))
            self.assertFalse(st.check(uriparse('gget://gco.cache.fr/fakedir.02?dir_extract=1'), dict()))
            # The tar should be available in cache...
            self.assertTrue(st.get(uriparse('gget://gco.cache.fr/fakearchive.01.tgz'),
                                   'toto.tgz', dict(intent='inout')))
            # Trash file1...
            with open('file1', 'a') as fh1:
                fh1.write(' + ExtraStuff')
            # The changed file1 file should not affect things...
            self.assertTrue(st.get(uriparse('gget://gco.cache.fr/fakearchive.01.tgz?dir_extract=1'),
                                   'fakearchive_dir', dict()))
            # Is the extracted tar in the cache directory ?
            edir_location = os.path.join(gcocache, 'fakearchive.01.tgz.autoextract')
            for edir_location in (self.sh.path.join(gcocache, 'fakearchive.01.tgz.autoextract'),
                                  'fakearchive_dir'):
                self.assert_mantra(self.sh.path.join(edir_location, 'file1'))
                self.assert_mantra(self.sh.path.join(edir_location, 'file4'))
                self.assertTrue(self.sh.path.islink(self.sh.path.join(edir_location, 'file4')))
                self.assertTrue(self.sh.path.isdir(self.sh.path.join(edir_location, 'subdir')))
            # Try to trash the index file
            self.sh.rm(self.sh.path.join(gcocache, 'fakearchive.01.tgz.index'))
            self.assertTrue(st.check(uriparse('gget://gco.cache.fr/fakearchive.01.tgz'), dict()))
            self.assertFalse(st.check(uriparse('gget://gco.cache.fr/fakearchive.01.tgz?dir_extract=1'), dict()))
            self.assertTrue(st.get(uriparse('gget://gco.cache.fr/fakearchive.01.tgz'),
                                   self.sh.path.join('the_ko_test', 'toto.tgz'), dict()))
            self.assertTrue(self.sh.path.exists(self.sh.path.join('the_ko_test', 'file1')))
            self.assertTrue(self.sh.path.isfile(self.sh.path.join('the_ko_test',
                                                                  'toto.tgz.index')))
            self.assertTrue(self.sh.path.isdir(self.sh.path.join('the_ko_test',
                                                                 'toto.tgz.autoextract')))
            # The index file should have been re-created
            self.assertTrue(self.sh.path.isfile(self.sh.path.join(gcocache,
                                                                  'fakearchive.01.tgz.index')))
            # Try to put something back in cache
            self.assertTrue(st.put(self.sh.path.join('the_ko_test', 'toto.tgz'),
                                   uriparse('gget://gco.cache.fr/fakearchive.01bis.tgz'),
                                   dict()))
            self.assertTrue(self.sh.path.isfile(self.sh.path.join(gcocache,
                                                                  'fakearchive.01bis.tgz.index')))
        # Refill should be ok...
        with self.sh.cdcontext('fromcachebis', create=True):
            st = fp.proxy.store(scheme='gget', netloc='gco.cache.fr')
            self.assertTrue(st.get(uriparse('gget://gco.cache.fr/fakearchive.01.tgz'),
                                   'toto.tgz', dict()))
            self.assert_mantra('file1')
            self.assert_mantra('file4')
            self.assertTrue(self.sh.path.islink('file4'))
            self.assertTrue(self.sh.path.isdir('subdir'))
            file1incache = self.sh.path.join(gcocache, 'fakearchive.01.tgz.autoextract', 'file1')
        # Intent ?
        with self.sh.cdcontext('fromcacheter', create=True):
            self.assertTrue(st.get(uriparse('gget://gco.cache.fr/fakearchive.01.tgz'),
                                   'toto.tgz', dict(intent='inout')))
            # The file should not come from the cache...
            self.assert_mantra('file1')
            self.assertNotEqual(self.sh.stat(file1incache).st_ino,
                                self.sh.stat('file1').st_ino)

    def test_iga_gco_store(self):
        frozencache = os.path.join(self.tmpdir, 'cache')
        datapath = self.sh.path.join(DATAPATHTEST, 'freezed_op_cycle_testdata.tar.bz2')
        with self.sh.cdcontext(frozencache, create=True):
            self.sh.untar(datapath, verbose=False)
        try:
            st = fp.proxy.store(scheme='gget', netloc='opgco.cache.fr', rootdir='auto')
            self.assertEqual(st.locate(uriparse('gget://opgco.cache.fr/tampon/fake_resource.01'), dict()),
                             self.sh.path.join(frozencache, 'gco', 'tampon', 'fake_resource.01'))
            self.assertEqual(st.check(uriparse('gget://opgco.cache.fr/tampon/fake_resource.01'), dict()).st_size,
                             6)
            self.assertSetEqual(set(st.list(uriparse('gget://opgco.cache.fr/tampon/'), dict())),
                                {'extract.mars.ifs.01.tgz',
                                 'extract.mars.ifs.01',
                                 'fake_resource.01',
                                 'al43t2_arome@ifs-op5.01.nam'})
            self.assertTrue(st.get(uriparse('gget://opgco.cache.fr/tampon/fake_resource.01'),
                                   'fake1', dict()))
            with open('fake1') as fhf:
                self.assertEqual(fhf.read(), 'opgco\n')
            self.assertTrue(st.get(uriparse('gget://opgco.cache.fr/tampon/extract.mars.ifs.01.tgz'),
                                   self.sh.path.join('sub1', 'extract.mars.ifs.01.tgz'), dict()))
            self.assertTrue(st.get(uriparse('gget://opgco.cache.fr/tampon/extract.mars.ifs.01.tgz?dir_extract=1'),
                                   'sub2', dict()))
            for where in ('sub1', 'sub2'):
                for what in ('extr_fc_00_vv', 'extr_fc_06_vv', 'extr_fc_12_vv', 'extr_fc_18_vv'):
                    self.assertTrue(self.sh.path.isfile(self.sh.path.join(where, what)))
                    self.assertFalse(self.sh.wperm(self.sh.path.join(where, what)))
            self.assertTrue(self.sh.path.exists(self.sh.path.join('sub1', 'extract.mars.ifs.01.tgz')))
            self.assertTrue(st.get(
                uriparse('gget://opgco.cache.fr/tampon/al43t2_arome@ifs-op5.01.nam?extract=namel_diag'),
                'nam_diag', dict()))
            self.assertTrue(self.sh.path.isfile('nam_diag'))
            self.assertFalse(self.sh.wperm('nam_diag'))
            self.assertTrue(st.get(
                uriparse('gget://opgco.cache.fr/tampon/al43t2_arome@ifs-op5.01.nam?extract=namel_prep'),
                'nam_prep', dict(intent='inout')))
            self.assertTrue(self.sh.path.isfile('nam_prep'))
            self.assertTrue(self.sh.wperm('nam_prep'))
            self.assertTrue(st.get(
                uriparse('gget://opgco.cache.fr/tampon/al43t2_arome@ifs-op5.01.nam?dir_extract=1'),
                'many_nam', dict()))
            self.assertTrue(self.sh.path.isfile(self.sh.path.join('many_nam', 'namel_prep')))
            self.assertTrue(self.sh.path.isfile(self.sh.path.join('many_nam', 'namel_diag')))
        finally:
            # Because ggetall enforce very strict rights...
            self.sh.wperm(self.sh.path.join(frozencache, 'gco', 'tampon', 'al43t2_arome@ifs-op5.01.nam'),
                          force=True)
            self.sh.wperm(self.sh.path.join(frozencache, 'gco', 'tampon', 'extract.mars.ifs.01'),
                          force=True)


@loggers.unittestGlobalLevel(tloglevel)
class TestGcoGenv(unittest.TestCase):

    def setUp(self):
        self._ini_genvcmd = genv.genvcmd
        genv.genvcmd = 'fake_genv.sh'
        self._ini_genvpath = genv.genvpath
        genv.genvpath = DATAPATHTEST

    def tearDown(self):
        genv.genvcmd = self._ini_genvcmd
        genv.genvpath = self._ini_genvpath
        genv.clearall()

    def test_basics(self):
        # Test genv autofill
        genv.autofill('cy42_op2.06')
        # Test DSI like autofill
        with open(os.path.join(DATAPATHTEST, 'cy42_peace-op2.01.genv')) as fh:
            gdata = fh.read().rstrip('\n').split('\n')
        genv.autofill('cy42_peace-op2.01', gdata)
        # Check keys
        self.assertEqual(sorted(genv.cycles()),
                         sorted(['cy42_op2.06', 'cy42_peace-op2.01']))
        # Clear
        genv.clearall()
        self.assertEqual(genv.cycles(), [])
        # Start again...
        genv.autofill('cy42_op2.06')
        genv.autofill('blop', gdata)
        self.assertEqual(sorted(genv.cycles()),
                         sorted(['cy42_op2.06', 'cy42_peace-op2.01']))
        # Access it ?
        realstuff = [line for line in gdata if not line.startswith('CYCLE_NAME=')]
        self.assertEqual(genv.nicedump(cycle='cy42_peace-op2.01'),
                         realstuff)
        cy = genv.contents(cycle='cy42_op2.06')
        self.assertEqual(cy.TOOLS_LFI, "tools.lfi.05.tgz")
        # cy should be a copy of the real thing...
        cy.TOOLS_LFI = 'trash'
        clean_cy = genv.contents(cycle='cy42_op2.06')
        self.assertEqual(clean_cy.TOOLS_LFI, "tools.lfi.05.tgz")
        # Still, it is possible to update things
        # Originally index 15 is: PGD_FA="pgd_pearp.t798.01.fa"
        gdata[15] = 'PGD_FA="trash"'
        genv.autofill('blop', gdata)
        cy = genv.contents(cycle='cy42_peace-op2.01')
        self.assertEqual(cy.PGD_FA, "trash")

    def test_provider(self):
        genv.autofill('cy42_op2.06')

        resource = FooResource()
        provider = fp.proxy.provider(gnamespace='gco.meteo.fr',
                                     genv='cy42_op2.06')
        self.assertEqual(provider.scheme(resource), 'gget')
        self.assertEqual(provider.netloc(resource), provider.gnamespace)
        self.assertEqual(provider.pathname(resource), 'tampon')
        self.assertEqual(provider.basename(resource), 'tools.lfi.05.tgz.m01')
        self.assertEqual(provider.urlquery(resource), 'extract=toto')


@loggers.unittestGlobalLevel(tloglevel)
class TestUgetUenv(PrivateCocoonGcoTest):

    _TEST_SESSION_NAME = 'test_session_gco_uget_uenv_1'

    def setUp(self):
        super().setUp()
        # Untar the Uget sample data
        datapath = self.sh.path.join(self.sh.glove.siteroot, 'tests', 'data', 'uget_uenv_fake.tar.bz2')
        self.sh.untar(datapath, verbose=False)

    def tearDown(self):
        uenv.clearall()
        super().tearDown()

    def test_basics(self):
        uenv.contents('uget:cy42_op2.06@huguette', 'uget', 'uget.multi.fr')
        self.assertEqual(uenv.cycles(),
                         ['uget:cy42_op2.06@huguette', ])
        uenv.clearall()
        self.assertEqual(uenv.cycles(), [])
        # One should always provide scheme and netloc is the cycle is not yet registered
        with self.assertRaises(uenv.UenvError):
            uenv.contents('uget:cy42_op2.06@huguette')
        mycycle = uenv.contents('uget:cy42_op2.06@huguette', 'uget', 'uget.multi.fr')
        self.assertIsInstance(mycycle.rrtm_const, AbstractUgetId)
        self.assertEqual(mycycle.rrtm_const, "uget:rrtm.const.02b.tgz@huguette")
        self.assertIsInstance(mycycle.master_arpege, GgetId)
        self.assertEqual(mycycle.master_arpege, "cy42_masterodb-op1.13.IMPI512IFC1601.2v.exe")
        # Let's try to fetch an erroneous Uenv
        try:
            uenv.contents('uget:cy42_op2.06.ko@huguette', 'uget', 'uget.multi.fr')
        except uenv.UenvError as e:
            self.assertEqual(str(e), 'Malformed environment file (line 3, "ANALYSE_ISBAanalyse.isba.03")')
        # Other possible errors
        with self.assertRaises(uenv.UenvError):
            uenv.contents('uget:do_not_exists@huguette')

    def test_stores(self):
        self.sh.mkdir('work')
        self.sh.cd('work')
        ugetdatacache = os.path.join(self.tmpdir, 'cache', 'uget', 'huguette', 'data')
        ugetdatahack = os.path.join(self.tmpdir, '.vortexrc', 'hack', 'uget', 'huguette', 'data')
        st = fp.proxy.store(scheme='uget', netloc='uget.multi.fr')
        sthack = fp.proxy.store(scheme='uget', netloc='uget.hack.fr')
        stcache = fp.proxy.store(scheme='uget', netloc='uget.cache.fr')

        # HACK STORE TEST
        # Get a simple file from the hack store
        st.get(uriparse('uget://uget.multi.fr/data/mask.atms.01b@huguette'), 'mask1', dict())
        with open('mask1') as fhm:
            self.assertEqual(fhm.readline().rstrip("\n"), 'hack')
        # Get a tar file but do not expand it because of its name (from hack)
        st.get(uriparse('uget://uget.multi.fr/data/rrtm.const.03hack.tgz@huguette'),
               'nam_nope', dict())
        # Get a tar file and expand it because of its name (from hack)
        st.get(uriparse('uget://uget.multi.fr/data/rrtm.const.03hack.tgz@huguette'),
               'rrtm_hack/rrtm_full.tgz', dict())
        self.assertTrue(self.sh.path.isfile('rrtm_hack/rrtm_full.tgz'))
        # Get a tar file and expand it because of dir_extract
        st.get(uriparse('uget://uget.multi.fr/data/rrtm.const.03hack.tgz@huguette?dir_extract=1'),
               'rrtm_hack_bis', dict())
        # Check the tar content
        for a_dir in ('rrtm_hack', 'rrtm_hack_bis'):
            for i in range(1, 4):
                self.assertTrue(self.sh.path.isfile(self.sh.path.join(a_dir, 'file{:d}'.format(i))))
            self.assertTrue(self.sh.path.islink(self.sh.path.join(a_dir, 'link1')))
        # Get a tar file and extract some stuff (from hack)
        st.get(uriparse('uget://uget.multi.fr/data/rrtm.const.03hack.tgz@huguette?extract=file1'),
               'rrtm_hack/rrtm_f1', dict())
        self.assertTrue(self.sh.path.isfile('rrtm_hack/rrtm.const.03hack.tgz'))
        self.assertTrue(self.sh.path.isdir('rrtm_hack/rrtm.const.03hack'))
        self.assertTrue(self.sh.path.isfile('rrtm_hack/rrtm_f1'))
        # Second round (the local directory should be used)
        st.get(uriparse('uget://uget.multi.fr/data/rrtm.const.03hack.tgz@huguette?extract=file2'),
               'rrtm_hack/rrtm_f2', dict())
        self.assertTrue(self.sh.path.isfile('rrtm_hack/rrtm_f2'))
        # Get a tar file but do not expand it because of its name (from hack)
        self.assertFalse(sthack.get(uriparse('uget://uget.multi.fr/data/cy99t1.01.nam.tgz@huguette'),
                         'nam_nope', dict()))
        # Get a tar file and expand it because of its name (from hack)
        st.get(uriparse('uget://uget.multi.fr/data/cy99t1.01.nam.tgz@huguette'),
               'nam_hack/nam_full.tgz', dict())
        self.assertTrue(self.sh.path.isdir('nam_hack/nam_full.tgz'))
        # Get a tar file and expand it because of dir_extract
        st.get(uriparse('uget://uget.multi.fr/data/cy99t1.01.nam.tgz@huguette?dir_extract=1'),
               'nam_hack_bis', dict(intent='inout'))
        for a_dir in ('nam_hack', 'nam_hack_bis'):
            for i in range(1, 4):
                self.assertTrue(self.sh.path.isfile(self.sh.path.join(a_dir, 'file{:d}'.format(i))))
            self.assertTrue(self.sh.path.islink(self.sh.path.join(a_dir, 'link1')))
        # Get a tar file but do not expand it because of its name but autorepack (from hack)
        self.assertTrue(sthack.get(uriparse('uget://uget.multi.fr/data/cy99t1.01.nam.tgz@huguette'),
                                   'nam_nope_repack', dict(auto_repack=True)))
        self.assertTrue(self.sh.path.isfile('nam_nope_repack'))
        self.sh.rm(self.sh.path.join(ugetdatahack, 'cy99t1.01.nam.tgz'))
        # Get a tar file and extract some stuff (from hack)
        st.get(uriparse('uget://uget.multi.fr/data/cy99t1.01.nam.tgz@huguette?extract=file1'),
               'nam_hack/nam_f1', dict())
        self.assertTrue(self.sh.path.isfile('nam_hack/nam_f1'))
        # Hack's check method
        for a_st in (st, sthack):
            self.assertTrue(
                a_st.check(uriparse('uget://uget.multi.fr/data/mask.atms.01b@huguette'),
                           dict()))
            self.assertTrue(
                a_st.check(uriparse('uget://uget.multi.fr/data/cy99t1.01.nam.tgz@huguette'),
                           dict()))
            self.assertTrue(
                a_st.check(uriparse('uget://uget.multi.fr/data/cy99t1.01.nam.tgz@huguette?dir_extract=1'),
                           dict()))
            self.assertTrue(
                a_st.check(uriparse('uget://uget.multi.fr/data/cy99t1.01.nam.tgz@huguette?extract=file1'),
                           dict()))
            self.assertTrue(
                a_st.check(uriparse('uget://uget.multi.fr/data/rrtm.const.03hack.tgz@huguette?dir_extract=0'),
                           dict()))
            self.assertTrue(
                a_st.check(uriparse('uget://uget.multi.fr/data/rrtm.const.03hack.tgz@huguette?extract=file1'),
                           dict()))
        # Hack's locate method
        self.assertEqual(
            sthack.locate(uriparse('uget://uget.multi.fr/data/mask.atms.01b@huguette'),
                          dict()),
            self.sh.path.join(ugetdatahack, 'mask.atms.01b'))
        self.assertEqual(
            sthack.locate(uriparse('uget://uget.multi.fr/data/cy99t1.01.nam.tgz@huguette'),
                          dict()),
            self.sh.path.join(ugetdatahack, 'cy99t1.01.nam'))
        self.assertEqual(
            sthack.locate(uriparse('uget://uget.multi.fr/data/cy99t1.01.nam.tgz@huguette?dir_extract=1'),
                          dict()),
            self.sh.path.join(ugetdatahack, 'cy99t1.01.nam'))
        self.assertEqual(
            sthack.locate(uriparse('uget://uget.multi.fr/data/cy99t1.01.nam.tgz@huguette?extract=file1'),
                          dict()),
            self.sh.path.join(ugetdatahack, 'cy99t1.01.nam', 'file1'))
        self.assertEqual(
            sthack.locate(uriparse('uget://uget.multi.fr/data/rrtm.const.03hack.tgz@huguette'),
                          dict()),
            self.sh.path.join(ugetdatahack, 'rrtm.const.03hack.tgz'))
        self.assertEqual(
            sthack.locate(uriparse('uget://uget.multi.fr/data/rrtm.const.03hack.tgz@huguette?dir_extract=1'),
                          dict()),
            self.sh.path.join(ugetdatahack, 'rrtm.const.03hack.tgz'))
        self.assertEqual(
            sthack.locate(uriparse('uget://uget.multi.fr/data/rrtm.const.03hack.tgz@huguette?extract=file1'),
                          dict()),
            self.sh.path.join(ugetdatahack, 'rrtm.const.03hack.tgz'))
        # Delete some files in the hack cache
        sthack = fp.proxy.store(scheme='uget', netloc='uget.hack.fr', readonly=False)
        self.assertTrue(sthack.delete(uriparse('uget://uget.multi.fr/data/cy99t1.01.nam.tgz@huguette?dir_extract=1'),
                                      dict()))
        self.assertFalse(self.sh.path.isfile(self.sh.path.join(ugetdatahack,
                                                               'cy99t1.01.nam.tgz')))
        self.assertFalse(self.sh.path.isdir(self.sh.path.join(ugetdatahack,
                                                              'cy99t1.01.nam')))
        self.assertTrue(sthack.delete(uriparse('uget://uget.multi.fr/data/rrtm.const.03hack.tgz@huguette'),
                                      dict()))
        self.assertFalse(self.sh.path.isfile(self.sh.path.join(ugetdatahack,
                                                               'rrtm.const.03hack.tgz')))

        # MT-CACHE STORE TEST
        # Get a tar file but do not expand it because of its name (from cache)
        st.get(uriparse('uget://uget.multi.fr/data/rrtm.const.02b.tgz@huguette'),
               'rrtm_nope', dict())
        self.assertTrue(self.sh.path.isfile('rrtm_nope'))
        # Now we want it expanded  (from cache, the autoextract and index pre-exists)
        st.get(uriparse('uget://uget.multi.fr/data/rrtm.const.02b.tgz@huguette'),
               'rrtm/rrtm_full.tgz', dict())
        self.assertTrue(self.sh.path.isfile('rrtm/rrtm_full.tgz'))
        # Get a tar file and expand it because of dir_extract
        st.get(uriparse('uget://uget.multi.fr/data/rrtm.const.02b.tgz@huguette?dir_extract=1'),
               'rrtm_bis', dict())
        for a_dir in ('rrtm', 'rrtm_bis'):
            for i in range(1, 4):
                self.assertTrue(self.sh.path.isfile(self.sh.path.join(a_dir, 'file{:d}'.format(i))))
        # Put back:
        self.assertTrue(st.put('rrtm_bis',
                               uriparse('uget://uget.multi.fr/data/rrtm.const.02c.tgz@huguette?dir_extract=1'),
                               dict()))
        # Idem with extract ?
        st.get(uriparse('uget://uget.multi.fr/data/rrtm.const.02b.tgz@huguette?extract=file1'),
               'file1_extra', dict())
        with open('file1_extra') as fhm:
            self.assertEqual(fhm.readline().rstrip("\n"), 'cache')
        # GCO special (see @gget-key-specific-conf.ini) + not yet extracted incache
        st.get(uriparse('uget://uget.multi.fr/data/grib_api.def.02.tgz@huguette'),
               self.sh.path.join('gribtest1', 'grib_stuff.tgz'), dict())
        self.assertTrue(self.sh.path.isfile(self.sh.path.join('gribtest1', 'grib_stuff.tgz')))
        # The grib1 subdirectory should not be removed !
        self.assertTrue(self.sh.path.isdir(self.sh.path.join('gribtest1', 'grib1')))
        # The auto extract stuff should be in cache
        self.assertTrue(st.check(uriparse('uget://uget.multi.fr/data/grib_api.def.02.tgz@huguette?extract=grib1'),
                        dict()))
        # The whole index structure should be here
        self.assertTrue(self.sh.path.isfile(self.sh.path.join(ugetdatacache,
                                                              'grib_api.def.02.tgz.index')))
        # Redo (the index + autoextract should be used)
        st.get(uriparse('uget://uget.multi.fr/data/grib_api.def.02.tgz@huguette'),
               self.sh.path.join('gribtest2', 'grib_stuff.tgz'), dict())
        self.assertTrue(self.sh.path.isfile(self.sh.path.join('gribtest2', 'grib_stuff.tgz')))
        # The grib1 subdirectory should not be removed !
        self.assertTrue(self.sh.path.isdir(self.sh.path.join('gribtest2', 'grib1')))
        # Test list
        self.assertSetEqual(set(stcache.list(uriparse('uget://uget.multi.fr/data/@huguette'),
                                             dict())),
                            {'grib_api.def.02.tgz', 'mask.atms.01b', 'rrtm.const.02b.tgz'})
        self.assertEqual(stcache.list(uriparse('uget://uget.multi.fr/data/grib_api@huguette'),
                                      dict()),
                         [])
        self.assertTrue(stcache.list(uriparse('uget://uget.multi.fr/data/grib_api.def.02.tgz@huguette'),
                                     dict()))
        # Delete from Mt cache
        self.assertTrue(st.delete(uriparse('uget://uget.multi.fr/data/grib_api.def.02.tgz@huguette'),
                                  dict()))
        self.assertFalse(self.sh.path.exists(self.sh.path.join(ugetdatacache,
                                                               'grib_api.def.02.tgz')))
        self.assertFalse(self.sh.path.exists(self.sh.path.join(ugetdatacache,
                                                               'grib_api.def.02.tgz.index')))
        self.assertTrue(self.sh.path.isdir(self.sh.path.join(ugetdatacache,
                                                             'grib_api.def.02.tgz.autoextract')))

    def test_provider(self):
        uenv.contents('uget:cy42_op2.06@huguette', 'uget', 'uget.multi.fr')

        # Uget provider
        provider = fp.proxy.provider(unamespace='uget.multi.fr',
                                     uget='uget:rrtm.const.02b.tgz@huguette')
        resource = FooResource()
        self.assertEqual(provider.scheme(resource), 'uget')
        self.assertEqual(provider.netloc(resource), provider.unamespace)
        self.assertEqual(provider.pathname(resource), 'data')
        self.assertEqual(provider.basename(resource), 'rrtm.const.02b.tgz.m01@huguette')
        self.assertEqual(provider.urlquery(resource), 'extract=toto')

        # Uenv provider
        provider = fp.proxy.provider(unamespace='uget.multi.fr',
                                     gnamespace='gco.meteo.fr',
                                     genv='uget:cy42_op2.06@huguette')  # Uenv is compatible with Genv
        resource = FooResource()
        self.assertEqual(provider.scheme(resource), 'gget')
        self.assertEqual(provider.netloc(resource), provider.gnamespace)
        self.assertEqual(provider.pathname(resource), 'tampon')
        self.assertEqual(provider.basename(resource), 'tools.lfi.05.tgz.m01')
        self.assertEqual(provider.urlquery(resource), 'extract=toto')
        resource = FooResource('rrtm_const')
        self.assertEqual(provider.scheme(resource), 'uget')
        self.assertEqual(provider.netloc(resource), provider.unamespace)
        self.assertEqual(provider.pathname(resource), 'data')
        self.assertEqual(provider.basename(resource), 'rrtm.const.02b.tgz.m01@huguette')
        self.assertEqual(provider.urlquery(resource), 'extract=toto')

    def test_uget_archive_hashes(self):
        expected = [('demo.constant.01', 'a'),
                    ('demo.constant.02', 'a'),
                    ('demo.constant.02toto', 'a'),
                    ('rrtm.const.02.tgz', '8'),
                    ('rrtm.const.02blip.tgz', '8'),
                    ('rrtm.const.02Blip.tgz', '8'),
                    ('rrtm.const.02bl-ip.tgz', '8'),
                    ('rrtm.const.02bl_ip.tgz', '8'),
                    ('rrtm.const.03.tgz', '8'),
                    ('rrtm.const.03.toto.tgz', 'f'),
                    ('mat.filter.glob05.06', 'd'),
                    ('mat.filter.glob05.06.m01', 'd'),
                    ('mat.filter.glob05.06lf.m01', 'd'),
                    ('mat.filter.glob05.06lf.mtoto', '7'),
                    ('mat.filter.glob05.06.gz', '3'),
                    ('mat.filter.glob05.06.gz.m01', '3'),
                    ('mat.filter.glob05.06lf.gz.m01', '3'),
                    ('grib_api.def.02.tgz', '4'),
                    ('mask.atms.01b', 'c'),
                    ('cy99t1.01.nam.tgz', 'f'),
                    ]
        for eltid, hashletter in expected:
            self.assertEqual(UgetArchiveStore._hashdir(eltid), hashletter)


class TestArpIfsSimplifiedCycle(unittest.TestCase):

    def assertInvalid(self, cycle):
        with self.assertRaises(ValueError):
            ArpIfsSimplifiedCycle(cycle)

    def assertDetect(self, cycle, s_cycle):
        self.assertEqual(str(ArpIfsSimplifiedCycle(cycle)),
                         s_cycle)

    def test_arpifs_cycles_basics(self):
        s_cycle = ArpIfsSimplifiedCycle('cy42_op2.23')
        self.assertEqual(s_cycle, ArpIfsSimplifiedCycle('cy42_op2'))
        self.assertEqual(s_cycle, 'cy42_op2')
        self.assertNotEqual(s_cycle, 'toto')
        self.assertLess(s_cycle, ArpIfsSimplifiedCycle('cy42t1'))
        self.assertLess(s_cycle, 'cy42t1')
        self.assertLess(s_cycle, 'cy43_op3')
        self.assertGreater(s_cycle, ArpIfsSimplifiedCycle('cy42'))
        self.assertGreater(s_cycle, 'cy42')
        self.assertGreater(s_cycle, 'cy41t6')

    def test_arpifs_cycles_reallife(self):
        # Failures
        wrongnames = ['toto', 'cya42', 'notcy42_op2.23',
                      # No cycle number
                      'cy', 'cyABC-op1.12', 'uget:cy', 'uget:cyABC-op1.12',
                      # Strange cycle
                      'cy42blop', 'cy42blop_op1', 'cy42blop_op1.02',
                      ]
        for cycle in wrongnames:
            self.assertInvalid(cycle)

        # No OP
        self.assertDetect('cy42_main.23', 'cy42')
        self.assertDetect('uget:cy42_main.06@huguette', 'cy42')
        self.assertDetect('uget:cy42_notop2Ican_write_whatever_i_want', 'cy42')
        self.assertDetect('al42_aromeop2.11', 'cy42')  # op should always be preceded with _ or -
        # No OP + t
        self.assertDetect('cy42t6_main.23', 'cy42t6')
        self.assertDetect('uget:cy42t6_main.06@huguette', 'cy42t6')
        self.assertDetect('uget:cy42t6_notop2Ican_write_whatever_i_want', 'cy42t6')
        self.assertDetect('al42t6_aromeop2.11', 'cy42t6')  # op should always be preceded with _ or -
        # OP
        self.assertDetect('cy42_op2.23', 'cy42_op2')
        self.assertDetect('uget:cy42_op2.06@huguette', 'cy42_op2')
        self.assertDetect('uget:cy42_op2Ican_write_whatever_i_want', 'cy42_op2')
        self.assertDetect('uget:cy42_coucou_op2Ican_write_whatever_i_want', 'cy42_op2')
        self.assertDetect('uget:cy42_coucou-op2Ican_write_whatever_i_want', 'cy42_op2')
        self.assertDetect('al42_arome-op2.11', 'cy42_op2')
        self.assertDetect('al42_-op2.11', 'cy42_op2')  # That's ugly but ok
        # OP + t
        self.assertDetect('cy42t1_op2.23', 'cy42t1_op2')
        self.assertDetect('uget:cy42t1_op2.06@huguette', 'cy42t1_op2')
        self.assertDetect('cy42t1_op2_IbelieveIcanFly', 'cy42t1_op2')
        self.assertDetect('cy42t1_op2_IbelieveIcanFlyWith_op3', 'cy42t1_op2')
        self.assertDetect('cy42t1_myfirst-op2_IbelieveIcanFlyWith_op3', 'cy42t1_op2')
        self.assertDetect('uget:cy42t1_op2Ican_write_whatever_i_want', 'cy42t1_op2')
        self.assertDetect('uget:cy42t1_coucou_op2Ican_write_whatever_i_want', 'cy42t1_op2')
        self.assertDetect('al42t1_arome-op2.11', 'cy42t1_op2')
        self.assertDetect('al42t1_-op2.11', 'cy42t1_op2')  # That's ugly but ok
        # Realistic
        self.assertDetect('cy42t1_op2.23', 'cy42t1_op2')
        self.assertDetect('al42t1_arome-op2.11', 'cy42t1_op2')
        self.assertDetect('al42_arome-op2.11', 'cy42_op2')
        self.assertDetect('al42_arome@pe-op2.03', 'cy42_op2')
        self.assertDetect('al42_arome@polynesie-op2.01', 'cy42_op2')
        self.assertDetect('cy42_peace-op2.05', 'cy42_op2')
        self.assertDetect('cy42_pacourt-op2.04', 'cy42_op2')
        self.assertDetect('al42_cpl-op2.02', 'cy42_op2')
        self.assertDetect('al41t1_reunion-op2.17', 'cy41t1_op2')
        self.assertDetect('cy42_assimens-op2.05', 'cy42_op2')
        self.assertDetect('al41t1_arome@asscom1-op2.01', 'cy41t1_op2')


if __name__ == "__main__":
    unittest.main(verbosity=2)
