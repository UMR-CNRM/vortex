# -*- coding: utf-8 -*-

"""
Test Vortex's Archive Stores + The folder special addon.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

from six.moves.urllib import parse as urlparse
import hashlib

from bronx.fancies import loggers
import footprints as fp
from footprints import proxy as fpx
import vortex
import vortex.tools.folder
from vortex.tools.prestaging import PrestagingTool
from vortex.tools.net import uriparse

from .ftpunittests import MtoolNetrcFtpBasedTestCase

fpx.addon(kind='allfolders', sh=vortex.sh())

tloglevel = 'ERROR'

_PATHl1 = 'arome/3dvarfr/ABCD/20180101T0000P/forecast/listing1'
_URIl1 = uriparse('vortex://vortex.archive.fr/{:s}'.format(_PATHl1))

_SA_PATHl1 = 'arome/3dvarfr/smile@someone/20180101T0000P/forecast/listing1'
_SA_URIl1 = uriparse('vortex://vortex.cache.fr/{:s}'.format(_PATHl1) +
                     '?setaside_n=vortex-free.cache.fr' +
                     '&setaside_p={:s}'.format(urlparse.quote_plus(_SA_PATHl1)))
_SA_URIl1_CHECK = uriparse('vortex://vortex.archive.fr/{:s}'.format(_SA_PATHl1))

_STACK_PATH = 'arome/3dvarfr/ABCD/20180101T0000P/stacks/flow_logs.filespack'
_STACK_URI = uriparse('vortex://vortex.archive.fr/' + _STACK_PATH)
_STACK_URIl1 = uriparse('vortex://vortex.archive.fr/{:s}'.format(_PATHl1) +
                        '?stackfmt=filespack' +
                        '&stackpath={:s}'.format(urlparse.quote_plus(_STACK_PATH)))
_STACK_URIl2 = uriparse('vortex://vortex.archive.fr/arome/3dvarfr/ABCD/20180101T0000P/minim/listing1' +
                        '?stackfmt=filespack' +
                        '&stackpath={:s}'.format(urlparse.quote_plus(_STACK_PATH)))


# Prestaging tools for this unittests

class UnitTestPrestagingTool(PrestagingTool):

    _footprint = dict(
        info = "Store away pre-staging requests.",
        attr = dict(
            issuerkind = dict(
                values = ['archivestore'],
            ),
            storage = dict(
            ),
        ),
        only = dict(
            storage = fp.FPRegex(r'localhost:\d+')
        ),
    )

    def flush(self, email=None):
        return True


@loggers.unittestGlobalLevel(tloglevel)
class TestVortexStores(MtoolNetrcFtpBasedTestCase):

    _FTPLOGLEVEL = tloglevel

    def vortex_store(self, netloc, **kwargs):
        return fpx.store(scheme='vortex', netloc=netloc,
                         storage='localhost:{:d}'.format(self.port),
                         storetube='ftp',
                         storeroot='theroot',
                         **kwargs)

    def vortex_in_ftp_path(self, path):
        return self.sh.path.join(self.udir, 'theroot', 'vortex', path)

    def assertVortexRemote(self, path, content, binary=False):
        path = self.sh.path.join('theroot', 'vortex', path)
        self.assertRemote(path, content, binary=binary)

    def test_vortex_store_features(self):
        with self.server():
            with self.sh.ftppool(nrcfile=self._fnrc):
                # Create a fake listing files
                sh = self.sh
                with open('flisting1', 'w') as fhl:
                    fhl.write('forecast_list')
                with open('flisting1.gz', 'wb') as fhl:
                    with open('flisting1', 'rb') as fhl_in:
                        sh.spawn(['gzip', '--stdout', '-6'], stdin=fhl_in, output=fhl)

                # Archive them using a compression pipeline (not advisable in real life).
                st = self.vortex_store('vortex.archive.fr', store_compressed='gz')
                self.assertTrue(st.put('flisting1', _URIl1, dict(fmt='ascii', delayed=False)))
                with open('flisting1.gz', 'rb') as fhl:
                    self.assertVortexRemote(_PATHl1 + '.gz', fhl.read(), binary=True)
                self.assertTrue(st.get(_URIl1, 'toto', dict(fmt='ascii')))
                self.assertFile('toto', 'forecast_list')
                sh.rm('toto')
                self.assertTrue(st.check(_URIl1, dict(fmt='ascii')))
                self.assertTrue(st.delete(_URIl1, dict(fmt='ascii')))
                # Done with compression pipelines

                # Archive them along with a hash file
                st = self.vortex_store('vortex.archive.fr', storehash='md5')
                stM = self.vortex_store('vortex.multi.fr', storehash='md5')
                self.assertTrue(st.put('flisting1', _URIl1, dict(fmt='ascii', delayed=False)))
                m_listing = hashlib.md5()
                m_listing.update('forecast_list'.encode())
                self.assertVortexRemote(_PATHl1 + '.md5', m_listing.hexdigest())
                self.assertTrue(st.check(_URIl1, dict(fmt='ascii')))
                self.assertTrue(st.get(_URIl1, 'toto', dict(fmt='ascii')))
                self.assertFile('toto', 'forecast_list')
                with open(self.vortex_in_ftp_path(_PATHl1 + '.md5'), 'w') as fhmd:
                    # Put erroneous things in the md5 file...
                    fhmd.write('1e25698a')
                self.assertFalse(st.get(_URIl1, 'toto', dict(fmt='ascii')))
                # The multi store also checks for md5 sum...
                self.assertFalse(stM.get(_URIl1, 'toto', dict(fmt='ascii')))
                self.assertTrue(st.delete(_URIl1, dict(fmt='ascii')))
                # Check that the md5 file was deleted to
                self.assertFalse(sh.path.exists(self.vortex_in_ftp_path(_PATHl1 + '.md5')))
                self.assertFalse(st.check(_URIl1, dict(fmt='ascii')))
                sh.rm('toto')

                # Archive/Multistore workflow
                stA = self.vortex_store('vortex.archive.fr')
                stM = self.vortex_store('vortex.multi.fr')
                stC = self.vortex_store('vortex.cache.fr')
                self.assertTrue(stA.put('flisting1', _URIl1, dict(fmt='ascii', delayed=False)))
                self.assertEqual(stA.check(_URIl1, dict(fmt='ascii')), 13)
                self.assertEqual(stM.check(_URIl1, dict(fmt='ascii')), 13)
                self.assertFalse(stM.check(_URIl1, dict(fmt='ascii', incache=True)))
                self.assertFalse(stC.check(_URIl1, dict(fmt='ascii')))
                # This should do nothing (because of incache=True)
                self.assertTrue(stM.delete(_URIl1, dict(fmt='ascii', incache=True)))
                self.assertFalse(stM.get(_URIl1, 'toto', dict(fmt='ascii', incache=True)))
                # This should trigger a refill
                self.assertTrue(stM.get(_URIl1, 'toto', dict(fmt='ascii')))
                self.assertFile('toto', 'forecast_list')
                # Refill Ok ?
                self.assertEqual(stC.check(_URIl1, dict(fmt='ascii')).st_size, 13)
                self.assertTrue(stM.delete(_URIl1, dict(fmt='ascii', incache=True)))
                self.assertFalse(stC.check(_URIl1, dict(fmt='ascii')))
                self.assertEqual(stA.check(_URIl1, dict(fmt='ascii')), 13)
                self.assertTrue(stM.delete(_URIl1, dict(fmt='ascii')))
                self.assertFalse(stA.check(_URIl1, dict(fmt='ascii')))
                # incache put & co
                self.assertTrue(stM.put('flisting1', _URIl1, dict(fmt='ascii', incache=True, delayed=False)))
                self.assertFalse(stA.check(_URIl1, dict(fmt='ascii')))
                self.assertEqual(stM.locate(_URIl1, dict(fmt='ascii')),
                                 '{0.udir}/mtool/cache/vortex/{1:s};{0.user}@localhost:theroot/vortex/{1:s}'
                                 .format(self, _PATHl1))
                self.assertEqual(stM.locate(_URIl1, dict(fmt='ascii', incache=True)),
                                 '{0.udir}/mtool/cache/vortex/{1:s}'
                                 .format(self, _PATHl1))
                sh.rm('toto')

                # Test the "set_aside stuff"
                self.assertTrue(stC.get(_SA_URIl1, 'toto', dict(fmt='ascii')))
                xloc = stC.locate(_SA_URIl1_CHECK, dict(fmt='ascii')).split(';')
                self.assertTrue(xloc)
                self.assertTrue(sh.readonly(xloc[0]))
                self.assertTrue(stC.get(_SA_URIl1_CHECK, 'toto_bis', dict(fmt='ascii')))
                with open('toto', 'r') as fhl:
                    self.assertFile('toto_bis', fhl.read())
                sh.rm('toto')
                sh.rm('toto_bis')
                self.assertTrue(stC.delete(_SA_URIl1_CHECK, dict(fmt='ascii')))
                self.assertTrue(stC.get(_SA_URIl1, 'toto', dict(fmt='ascii', intent="inout")))
                self.assertTrue(sh.wperm('toto'))
                self.assertTrue(sh.readonly(xloc[0]))
                with open('toto', 'r') as fhl:
                    self.assertFile(xloc[0], fhl.read())
                sh.rm('toto')

    def test_vortex_store_stacks(self):
        with self.server():
            with self.sh.ftppool(nrcfile=self._fnrc):
                # Working with stacks...
                # Create a fake stack of files
                sh = self.sh
                with open('flisting1', 'w') as fhl:
                    fhl.write('forecast_list')
                with open('mlisting1', 'w') as fhl:
                    fhl.write('minim_list')
                st = self.vortex_store('vortex.cache.fr')
                self.assertTrue(st.put('flisting1', _STACK_URIl1, dict(fmt='ascii')))
                self.assertTrue(st.check(_STACK_URIl1, dict(fmt='ascii')))
                stS = self.vortex_store('vortex.stack.fr')
                self.assertFalse(stS.check(_STACK_URIl1, dict(fmt='ascii')))
                self.assertTrue(st.delete(_STACK_URIl1, dict(fmt='ascii')))
                self.assertTrue(stS.put('flisting1', _STACK_URIl1, dict(fmt='ascii')))
                self.assertTrue(stS.check(_STACK_URIl1, dict(fmt='ascii')))
                self.assertTrue(st.check(_STACK_URIl1, dict(fmt='ascii')))
                self.assertTrue(st.delete(_STACK_URIl1, dict(fmt='ascii')))
                # No delete in the stack stores
                self.assertTrue(st.check(_STACK_URIl1, dict(fmt='ascii')))
                # For later
                self.assertTrue(stS.put('mlisting1', _STACK_URIl2, dict(fmt='ascii')))
                sh.rm('flisting1')
                sh.rm('mlisting1')
                self.assertTrue(st.get(_STACK_URI, 'thestack', dict(fmt='filespack')))
                self.assertTrue(st.delete(_STACK_URI, dict(fmt='filespack')))
                self.assertFalse(st.check(_STACK_URIl1, dict(fmt='ascii')))
                self.assertFalse(st.check(_STACK_URIl2, dict(fmt='ascii')))
                # Drop the stack
                st = self.vortex_store('vortex.archive-legacy.fr')
                self.assertTrue(st.put('thestack', _STACK_URI, dict(fmt='filespack', delayed=False)))
                self.assertTrue(sh.path.exists(sh.path.join(self.udir, 'theroot', 'vortex',
                                                            _STACK_PATH + '.tgz')))
                self.assertTrue(st.delete(_STACK_URI, dict(fmt='filespack')))
                self.assertFalse(sh.path.exists(sh.path.join(self.udir, 'theroot', 'vortex',
                                                             _STACK_PATH + '.tgz')))
                stM = self.vortex_store('vortex.multi.fr')
                self.assertTrue(stM.put('thestack', _STACK_URI, dict(fmt='filespack', inarchive=True, delayed=False)))
                self.assertTrue(sh.path.exists(sh.path.join(self.udir, 'theroot', 'vortex',
                                                            _STACK_PATH + '.tgz')))
                self.assertTrue(stM.check(_STACK_URI, dict(fmt='filespack', inarchive=True)))
                self.assertFalse(stM.check(_STACK_URI, dict(fmt='filespack', incache=True)))
                # Retrieve the whole stack
                self.assertEqual(st.locate(_STACK_URI, dict(fmt='filespack')),
                                 'testlogin@localhost:theroot/vortex/arome/3dvarfr/ABCD/20180101T0000P/stacks/flow_logs.filespack.tgz')
                self.assertTrue(st.check(_STACK_URI, dict(fmt='filespack')))
                self.assertTrue(st.get(_STACK_URI, 'thestack.bis', dict(fmt='filespack')))
                self.assertFile(sh.path.join('thestack.bis/forecast/listing1'), 'forecast_list')
                sh.rm('thestack.bis', fmt='filespack')
                # Retrieve the two listings independently: use the archive multi-store
                st = self.vortex_store('vortex.archive.fr')
                self.assertEqual(st.locate(_STACK_URIl1, dict(fmt='ascii')),
                                 'testlogin@localhost:theroot/vortex/arome/3dvarfr/ABCD/20180101T0000P/forecast/listing1;' +
                                 'testlogin@localhost:theroot/vortex/arome/3dvarfr/ABCD/20180101T0000P/stacks/flow_logs.filespack.tgz')
                # Prestaging ?
                self.assertTrue(st.prestage(_STACK_URIl1, dict(fmt='ascii')))
                phub = vortex.ticket().context.prestaging_hub
                self.assertIn('theroot/vortex/arome/3dvarfr/ABCD/20180101T0000P/stacks/flow_logs.filespack.tgz',
                              str(phub))
                self.assertTrue(st.prestage(_STACK_URIl2, dict(fmt='ascii')))
                self.assertIn('theroot/vortex/arome/3dvarfr/ABCD/20180101T0000P/stacks/flow_logs.filespack.tgz',
                              str(phub))
                phub.flush()
                self.assertIn('n_prestagingtools=0', str(phub))
                # Will change nothing since the stack based sotres are read-only
                self.assertFalse(st.delete(_STACK_URIl1, dict(fmt='ascii')))
                self.assertTrue(st.check(_STACK_URIl1, dict(fmt='ascii')))
                self.assertTrue(st.get(_STACK_URIl1, 'flisting', dict(fmt='ascii')))
                self.assertFile(sh.path.join('flisting'), 'forecast_list')
                self.assertTrue(st.get(_STACK_URIl2, 'mlisting', dict(fmt='ascii')))
                self.assertFile(sh.path.join('mlisting'), 'minim_list')
                sh.rm('flisting')
                sh.rm('mlisting')
                # Retrieve things using the smart multistore
                st = self.vortex_store('vortex.multi.fr')
                self.assertEqual(st.locate(_STACK_URIl1, dict(fmt='ascii')),
                                 ('{0.udir:s}/mtool/cache/vortex/arome/3dvarfr/ABCD/20180101T0000P/forecast/listing1;' +
                                  '{0.udir:s}/mtool/cache/vortex/arome/3dvarfr/ABCD/20180101T0000P/stacks/flow_logs.filespack/forecast/listing1;' +
                                  'testlogin@localhost:theroot/vortex/arome/3dvarfr/ABCD/20180101T0000P/forecast/listing1;' +
                                  'testlogin@localhost:theroot/vortex/arome/3dvarfr/ABCD/20180101T0000P/stacks/flow_logs.filespack.tgz')
                                 .format(self))
                self.assertEqual(
                    st.list(uriparse('vortex://vortex.multi.fr/arome/3dvarfr/ABCD/20180101T0000P/toto/'), dict()),
                    list())
                self.assertEqual(
                    st.list(uriparse('vortex://vortex.multi.fr/arome/3dvarfr/ABCD/20180101T0000P/'), dict()),
                    ['forecast', 'stacks'])
                self.assertFalse(st.delete(_STACK_URIl1, dict(fmt='ascii')))
                self.assertTrue(st.check(_STACK_URIl1, dict(fmt='ascii')))
                self.assertTrue(st.get(_STACK_URIl1, 'flisting', dict(fmt='ascii')))
                self.assertFile(sh.path.join('flisting'), 'forecast_list')
                self.assertTrue(st.get(_STACK_URIl2, 'mlisting', dict(fmt='ascii')))
                self.assertFile(sh.path.join('mlisting'), 'minim_list')
                sh.rm('flisting')
                sh.rm('mlisting')
                # Now, everything should be available in the cache store
                st = self.vortex_store('vortex.cache.fr')
                self.assertEqual(st.locate(_STACK_URIl1, dict(fmt='ascii')),
                                 ('{0.udir:s}/mtool/cache/vortex/arome/3dvarfr/ABCD/20180101T0000P/forecast/listing1;' +
                                  '{0.udir:s}/mtool/cache/vortex/arome/3dvarfr/ABCD/20180101T0000P/stacks/flow_logs.filespack/forecast/listing1')
                                 .format(self))
                self.assertTrue(st.check(_STACK_URIl1, dict(fmt='ascii')))
                self.assertTrue(st.get(_STACK_URIl1, 'flisting', dict(fmt='ascii')))
                self.assertFile(sh.path.join('flisting'), 'forecast_list')
                sh.rm('flisting')

    def test_finder_ftp(self):
        goto_path = 'testfinder_ftp/testfile1'
        goto_url_str = 'ftp://{0.user:s}@localhost:{0.port:d}/{1:s}'.format(self, goto_path)
        goto_url = uriparse(goto_url_str)
        with self.server():
            with self.sh.ftppool(nrcfile=self._fnrc):
                sh = self.sh
                with open('flisting1', 'w') as fhl:
                    fhl.write('forecast_list')
                stF = fpx.store(scheme='ftp',
                                netloc='{0.user:s}@localhost:{0.port:d}'.format(self))
                self.assertTrue(stF.put('flisting1', goto_url, dict(fmt='ascii')))
                self.assertRemote(goto_path, 'forecast_list')
                self.assertEqual(stF.check(goto_url, dict(fmt='ascii')), 13)
                self.assertEqual(stF.locate(goto_url, dict(fmt='ascii')),
                                 'testlogin@localhost:/testfinder_ftp/testfile1')
                self.assertTrue(stF.get(goto_url, 'toto', dict(fmt='ascii')))
                self.assertFile('toto', 'forecast_list')
                self.assertTrue(stF.delete(goto_url, dict(fmt='ascii')))
                self.assertFalse(stF.check(goto_url, dict(fmt='ascii')))
