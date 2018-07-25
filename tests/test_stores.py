from __future__ import print_function, absolute_import, unicode_literals, division

import unittest

import footprints as fp

import vortex  # @UnusedImport
from vortex.syntax.stdattrs import FreeXPid
from vortex.tools.net import uriparse, uriunparse


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
        dict(uri='vortex://vortex-free.archive.fr/arome/3dvarfr/ABCD@unittest/20180101T0000-20180101T1800/forecast/unittest',
             rread='vortex://vortex-free.archive.fr/vortex/arome/3dvarfr/ABCD/20180101T0000-20180101T1800/forecast/unittest',
             rread_root='~unittest',
             rwrite='vortex://vortex-free.archive.fr/vortex/arome/3dvarfr/ABCD/20180101T0000-20180101T1800/forecast/unittest',
             rwrite_root='~unittest'),
    ]

    def _do_remap_asserts(self, remaps):
        for remap in remaps:
            puri = uriparse(remap['uri'])
            st = fp.proxy.store(scheme=puri['scheme'], netloc=puri['netloc'])
            puri2 = st.remap_read(puri, dict())
            self.assertEqual(uriunparse(puri2.values()[:6]), remap['rread'])
            self.assertEqual(puri2.get('root', ''), remap['rread_root'])
            puri2 = st.remap_write(puri, dict())
            self.assertEqual(uriunparse(puri2.values()[:6]), remap['rwrite'])
            self.assertEqual(puri2.get('root', ''), remap['rwrite_root'])

    def test_remaps1(self):
        self._do_remap_asserts(self._REMAPS)

    def test_remaps2(self):
        to_skiptest = set()
        for remap in self._REMAPS_CONFIGURABLE:
            puri = uriparse(remap['uri'])
            to_skiptest.add((puri['scheme'], puri['netloc']))
        for scheme, netloc in to_skiptest:
            st = fp.proxy.store(scheme=scheme, netloc=netloc)
            try:
                st._actual_storeroot(FreeXPid('ABCD@unittest'))
            except IOError:
                self.skipTest('No network access to get the store config.')
        self._do_remap_asserts(self._REMAPS_CONFIGURABLE)


if __name__ == "__main__":
    unittest.main(verbosity=2)
