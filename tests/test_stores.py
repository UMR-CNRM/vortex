from __future__ import print_function, absolute_import, unicode_literals, division

import os
import tempfile
import unittest

import footprints as fp

import vortex  # @UnusedImport
from vortex.tools.net import uriparse, uriunparse

DATAPATHTEST = os.path.join(os.path.dirname(__file__), 'data')


class TestVortexArchiveStore(unittest.TestCase):

    _REMAPS = [
        # Vortex Standard
        dict(uri='vortex://vortex.archive.fr/arome/3dvarfr/ABCD/20180101T0000A/forecast/unittest',
             rread='vortex://vortex.archive.fr/vortex/arome/3dvarfr/A/B/C/D/20180101T0000A/forecast/unittest',
             rread_root='',
             rwrite='vortex://vortex.archive.fr/arome/3dvarfr/ABCD/20180101T0000A/forecast/unittest',
             rwrite_root='vortex'),
        dict(uri='vortex://vortex.archive.fr/arome/3dvarfr/ABCD/forecast/unittest',
             rread='vortex://vortex.archive.fr/vortex/arome/3dvarfr/A/B/C/D/forecast/unittest',
             rread_root='',
             rwrite='vortex://vortex.archive.fr/arome/3dvarfr/ABCD/forecast/unittest',
             rwrite_root='vortex'),
        dict(uri='vortex://vortex.archive.fr/arome/3dvarfr/ABCD/20180101T0000-20180101T1800/forecast/unittest',
             rread='vortex://vortex.archive.fr/vortex/arome/3dvarfr/A/B/C/D/20180101T0000-20180101T1800/forecast/unittest',
             rread_root='',
             rwrite='vortex://vortex.archive.fr/arome/3dvarfr/ABCD/20180101T0000-20180101T1800/forecast/unittest',
             rwrite_root='vortex'),
        # Vortex Op
        dict(uri='vortex://vsop.archive.fr/arome/3dvarfr/OPER/20180101T0000A/forecast/unittest',
             rread='vortex://vsop.archive.fr/vortex/arome/3dvarfr/OPER/2018/01/01/T0000A/forecast/unittest',
             rread_root='',
             rwrite='vortex://vsop.archive.fr/vortex/arome/3dvarfr/OPER/2018/01/01/T0000A/forecast/unittest',
             rwrite_root=''),
        dict(uri='vortex://vsop.archive.fr/arome/3dvarfr/OPER/forecast/unittest',
             rread='vortex://vsop.archive.fr/vortex/arome/3dvarfr/OPER/forecast/unittest',
             rread_root='',
             rwrite='vortex://vsop.archive.fr/vortex/arome/3dvarfr/OPER/forecast/unittest',
             rwrite_root=''),
        dict(uri='vortex://vsop.archive.fr/arome/3dvarfr/OPER/20180101T0000-20180101T1800/forecast/unittest',
             rread='vortex://vsop.archive.fr/vortex/arome/3dvarfr/OPER/2018/01/01/T0000-20180101T1800/forecast/unittest',
             rread_root='',
             rwrite='vortex://vsop.archive.fr/vortex/arome/3dvarfr/OPER/2018/01/01/T0000-20180101T1800/forecast/unittest',
             rwrite_root=''),
    ]

    _REMAPS_CONFIGURABLE = [
        # Vortex Free
        dict(uri='vortex://vortex-free.archive.fr/arome/3dvarfr/ABCD@unittest/20180101T0000A/forecast/unittest',
             rread='vortex://vortex-free.archive.fr/vortex/arome/3dvarfr/ABCD/20180101T0000A/forecast/unittest',
             rread_root='~unittest',
             rwrite='vortex://vortex-free.archive.fr/vortex/arome/3dvarfr/ABCD/20180101T0000A/forecast/unittest',
             rwrite_root='~unittest'),
        dict(uri='vortex://vortex-free.archive.fr/arome/3dvarfr/ABCD@unittest/forecast/unittest',
             rread='vortex://vortex-free.archive.fr/vortex/arome/3dvarfr/ABCD/forecast/unittest',
             rread_root='~unittest',
             rwrite='vortex://vortex-free.archive.fr/vortex/arome/3dvarfr/ABCD/forecast/unittest',
             rwrite_root='~unittest'),
        dict(uri='vortex://vortex-free.archive.fr/arome/3dvarfr/ABCD@tata/20180101T0000-20180101T1800/forecast/unittest',
             rread='vortex://vortex-free.archive.fr/vortex/arome/3dvarfr/ABCD/20180101T0000-20180101T1800/forecast/unittest',
             rread_root='/somwhere/lies/tata',
             rwrite='vortex://vortex-free.archive.fr/vortex/arome/3dvarfr/ABCD/20180101T0000-20180101T1800/forecast/unittest',
             rwrite_root='/somwhere/lies/tata'),
        dict(uri='vortex://vortex-free.archive.fr/arome/3dvarfr/ABCD@toto15/20180101T0000-20180101T1800/forecast/unittest',
             rread='vortex://vortex-free.archive.fr/vortex/arome/3dvarfr/ABCD/20180101T0000-20180101T1800/forecast/unittest',
             rread_root='/somwhere/lies/toto15',
             rwrite='vortex://vortex-free.archive.fr/vortex/arome/3dvarfr/ABCD/20180101T0000-20180101T1800/forecast/unittest',
             rwrite_root='/somwhere/lies/toto15'),
        dict(uri='vortex://vortex-free.archive.fr/arome/3dvarfr/ABCD@titi/20180101T0000-20180101T1800/forecast/unittest',
             rread='vortex://vortex-free.archive.fr/vortex/arome/3dvarfr/ABCD/20180101T0000-20180101T1800/forecast/unittest',
             rread_root='~titi',
             rwrite='vortex://vortex-free.archive.fr/vortex/arome/3dvarfr/ABCD/20180101T0000-20180101T1800/forecast/unittest',
             rwrite_root='~titi'),
    ]

    def setUp(self):
        # Generate a temporary directory
        self.t = vortex.sessions.current()
        self.sh = self.t.system()
        self.sh.target(hostname='unittest', inetname='unittest',
                       sysname='Local')  # Trick the vortex's system !
        self.tmpdir = tempfile.mkdtemp(suffix='_test_stores')
        self.oldpwd = self.sh.pwd()
        self.sh.cd(self.tmpdir)
        # Link in test config files
        self.sh.symlink(self.sh.path.join(DATAPATHTEST, 'store-vortex-free-testL.ini'),
                        'test_localconf.ini')
        self.sh.symlink(self.sh.path.join(DATAPATHTEST, 'store-vortex-free-testR0.ini'),
                        'test_remoteconf0.ini')
        self.sh.symlink(self.sh.path.join(DATAPATHTEST, 'store-vortex-free-testR1.ini'),
                        'test_remoteconf1.ini')

    def tearDown(self):
        self.sh.target()
        self.sh.cd(self.oldpwd)
        self.sh.remove(self.tmpdir)

    def _do_remap_asserts(self, remaps):
        for remap in remaps:
            puri = uriparse(remap['uri'])
            st = fp.proxy.store(scheme=puri['scheme'], netloc=puri['netloc'],
                                storage='unittesttarget.fake.com')
            puri2 = st.remap_read(puri, dict())
            self.assertEqual(uriunparse(list(puri2.values())[:6]), remap['rread'])
            self.assertEqual(puri2.get('root', ''), remap['rread_root'])
            puri2 = st.remap_write(puri, dict())
            self.assertEqual(uriunparse(list(puri2.values())[:6]), remap['rwrite'])
            self.assertEqual(puri2.get('root', ''), remap['rwrite_root'])

    def test_remaps1(self):
        self._do_remap_asserts(self._REMAPS)

    def test_remaps2(self):
        self._do_remap_asserts(self._REMAPS_CONFIGURABLE)


if __name__ == "__main__":
    unittest.main(verbosity=2)
