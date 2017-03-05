
import os
import tempfile
import unittest

import footprints as fp

import vortex
from vortex.tools.net import uriparse
from gco.tools import genv, uenv
from gco.syntax.stdattrs import UgetId, GgetId

DATAPATHTEST = os.path.join(os.path.dirname(__file__), 'data')


class FooResource(object):

    def __init__(self, gvar='tools_lfi'):
        self.gvar = gvar

    def basename(self, prkind):
        if prkind in ('genv', 'uenv'):
            return self.gvar
        elif prkind in ('gget', 'uget'):
            return '.m01'  # Simulate a monthly data
        else:
            raise ValueError

    def urlquery(self, prkind):
        if prkind in ('genv', 'gget', 'uenv', 'uget'):
            return 'extract=toto'  # Simulate an extract
        else:
            raise ValueError


class TestGcoGenv(unittest.TestCase):

    def setUp(self):
        self._ini_genvcmd = genv.genvcmd
        genv.genvcmd = 'fake_genv.py'
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
        self.assertItemsEqual(genv.cycles(),
                              ('cy42_op2.06', 'cy42_peace-op2.01'))
        # Clear
        genv.clearall()
        self.assertItemsEqual(genv.cycles(), ())
        # Start again...
        genv.autofill('cy42_op2.06')
        genv.autofill('blop', gdata)
        self.assertItemsEqual(genv.cycles(),
                              ('cy42_op2.06', 'cy42_peace-op2.01'))
        # Access it ?
        realstuff = [line for line in gdata if not line.startswith('CYCLE_NAME=')]
        self.assertItemsEqual(genv.nicedump(cycle='cy42_peace-op2.01'),
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


class TestUgetUenv(unittest.TestCase):

    def setUp(self):
        # Get ride of loggers
        glog = fp.loggers.getLogger('gco')
        self._glog_level = glog.level
        glog.setLevel('CRITICAL')
        vlog = fp.loggers.getLogger('vortex')
        self._vlog_level = vlog.level
        vlog.setLevel('CRITICAL')
        # Temp directory
        self.sh = vortex.sessions.current().system()
        self.tmpdir = tempfile.mkdtemp(suffix='test_uget_uenv')
        self.oldpwd = self.sh.pwd()
        self.sh.cd(self.tmpdir)
        # Tweak the HOME directory in order to trick Uenv/Uget kack store
        self.sh.env.HOME = self.tmpdir
        # Set-up the MTOOLDIR
        self.sh.env.MTOOLDIR = self.tmpdir
        # Untar the Uget sample data
        datapath = self.sh.path.join(self.sh.glove.siteroot, 'tests', 'data', 'uget_uenv_fake.tar.bz2')
        self.sh.untar(datapath)

    def tearDown(self):
        self.sh.cd(self.oldpwd)
        self.sh.remove(self.tmpdir)
        uenv.clearall()
        # restore loggers
        glog = fp.loggers.getLogger('gco')
        glog.setLevel(self._glog_level)
        vlog = fp.loggers.getLogger('vortex')
        vlog.setLevel(self._vlog_level)

    def test_basics(self):
        uenv.contents('uget:cy42_op2.06@huguette', 'uget', 'uget.multi.fr')
        self.assertItemsEqual(uenv.cycles(),
                              ('uget:cy42_op2.06@huguette', ))
        uenv.clearall()
        self.assertItemsEqual(uenv.cycles(), ())
        # One should always provide scheme and netloc is the cycle is not yet registered
        with self.assertRaises(uenv.UenvError):
            uenv.contents('uget:cy42_op2.06@huguette')
        mycycle = uenv.contents('uget:cy42_op2.06@huguette', 'uget', 'uget.multi.fr')
        self.assertIsInstance(mycycle.rrtm_const, UgetId)
        self.assertEqual(mycycle.rrtm_const, "uget:rrtm.const.02b.tgz@huguette")
        self.assertIsInstance(mycycle.master_arpege, GgetId)
        self.assertEqual(mycycle.master_arpege, "cy42_masterodb-op1.13.IMPI512IFC1601.2v.exe")
        # Let's try to fetch an erroneous Uenv
        try:
            uenv.contents('uget:cy42_op2.06.ko@huguette', 'uget', 'uget.multi.fr')
        except uenv.UenvError as e:
            self.assertEqual(str(e), 'Malformed environement file (line 3, "ANALYSE_ISBAanalyse.isba.03")')
        # Other possible errors
        with self.assertRaises(uenv.UenvError):
            uenv.contents('uget:do_not_exists@huguette')

    def test_stores(self):
        self.sh.mkdir('work')
        self.sh.cd('work')
        st = fp.proxy.store(scheme='uget', netloc='uget.multi.fr')
        # Get a simple file from the hack store
        st.get(uriparse('uget://uget.multi.fr/data/mask.atms.01b@huguette'), 'mask1', dict())
        with open('mask1') as fhm:
            self.assertEqual(fhm.readline().rstrip("\n"), 'hack')
        # Get a tar file but do not expand it because of its name
        st.get(uriparse('uget://uget.multi.fr/data/rrtm.const.02b.tgz@huguette'),
               'rrtm_nope', dict())
        self.assertTrue(self.sh.path.isfile('rrtm_nope'))
        # Now we want it expanded
        st.get(uriparse('uget://uget.multi.fr/data/rrtm.const.02b.tgz@huguette'),
               'rrtm/rrtm_full.tgz', dict())
        self.assertTrue(self.sh.path.isfile('rrtm/rrtm_full.tgz'))
        for i in range(1, 4):
            self.assertTrue(self.sh.path.isfile('rrtm/file{:d}'.format(i)))
        # Extract ?
        st.get(uriparse('uget://uget.multi.fr/data/rrtm.const.02b.tgz@huguette?extract=file1'),
               'file1_extra', dict())
        with open('file1_extra') as fhm:
            self.assertEqual(fhm.readline().rstrip("\n"), 'cache')
        # The element is kept for next time...
        self.assertTrue(self.sh.path.isfile('rrtm.const.02b.tgz'))
        self.assertTrue(self.sh.path.isdir('rrtm.const.02b'))
        # next time...
        st.get(uriparse('uget://uget.multi.fr/data/rrtm.const.02b.tgz@huguette?extract=file3'),
               'file3_extra', dict())
        with open('file3_extra') as fhm:
            self.assertEqual(fhm.readline().rstrip("\n"), 'cache')
        # GCO special (see @gget-key-specific-conf.ini)
        st.get(uriparse('uget://uget.multi.fr/data/grib_api.def.02.tgz@huguette'),
               'grib_stuff.tgz', dict())
        self.assertTrue(self.sh.path.isfile('grib_stuff.tgz'))
        # The grib1 subdirectory should not be removed !
        self.assertTrue(self.sh.path.isdir('grib1'))

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
