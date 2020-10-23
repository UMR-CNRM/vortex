# -*- coding: utf-8 -*-

"""
Test Vortex's FTP client
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import io
import os
import tempfile
import unittest

import footprints as fp
from bronx.fancies import loggers
import vortex
from vortex.tools.net import uriparse
from gco.data.stores import UgetArchiveStore

from . import has_ftpservers
from .utils import get_ftp_port_number

DATAPATHTEST = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')

tloglevel = 9999


class UgetArchiveTestStore(UgetArchiveStore):

    _store_global_config = './storetest_uget.ini'
    _footprint = dict(
        priority = dict(
            level = fp.priorities.top.DEBUG
        )
    )


@unittest.skipUnless(has_ftpservers(), 'FTP Server')
@loggers.unittestGlobalLevel(tloglevel)
class TestGcoArchiveStore(unittest.TestCase):

    _TEST_SESSION_NAME = None

    def setUp(self):
        self.cursession = vortex.sessions.current()
        self.t = vortex.sessions.get(tag=self._TEST_SESSION_NAME,
                                     topenv=vortex.rootenv,
                                     glove=self.cursession.glove)
        self.t.activate()
        self.sh = self.t.sh
        # Tweak the target object
        self.testconf = self.sh.path.join(DATAPATHTEST, 'target-test.ini')
        self.sh.target(inifile=self.testconf, sysname='Linux')
        # Temp directory
        self.tdir = tempfile.mkdtemp(suffix='test_uget_archive_store_')
        self.oldpwd = self.sh.pwd()
        self.sh.cd(self.tdir)
        # Tweak the HOME directory in order to trick Uenv/Uget hack store
        self.sh.env.HOME = self.tdir
        # Set-up the MTOOLDIR
        self.sh.mkdir('mtool')
        self.sh.env.MTOOLDIR = self.sh.path.join(self.tdir, 'mtool')
        # Cocoon the ftp server directory
        self.udir = self.sh.path.join(self.tdir, 'testlogin')
        self.user = 'testlogin'
        self.password = 'aqmp'
        self.sh.mkdir(self.udir)
        # FTP Config
        self.port = get_ftp_port_number()
        self.configure_ftpserver()
        # Fake NetRC
        self._fnrc = self.sh.path.join(self.tdir, 'fakenetrc')
        with io.open(self._fnrc, 'w') as fhnrc:
            fhnrc.write('machine localhost login {:s} password {:s}'
                        .format(self.user, self.password))
        self.sh.chmod(self._fnrc, 0o600)

    def configure_ftpserver(self):
        from .ftpservers import TestFTPServer, logger
        logger.setLevel(tloglevel)
        self.server = TestFTPServer(self.port, self.tdir,
                                    self.user, self.password)

    def tearDown(self):
        # Do some cleaning
        self.sh.cd(self.oldpwd)
        self.sh.rmtree(self.tdir)
        # Go back to the original session
        self.cursession.activate()

    def assertFile(self, path, content):
        self.assertTrue(self.sh.path.exists(path))
        with io.open(path, 'rb') as fhr:
            self.assertEqual(fhr.read(), content)

    def assertRemote(self, path, content):
        where = self.sh.path.join(self.udir, path)
        self.assertFile(where, content)

    def ftp_client_thook(self):
        pass

    def _uget_archive_dump_config(self):
        with io.open('storetest_uget.ini', 'w') as fhini:
            fhini.write('[localhost:{:d}]\n'.format(self.port))
            fhini.write('localconf=./storetest-uget-local.ini')
        with io.open('storetest-uget-local.ini', 'w') as fhini:
            fhini.write('[DEFAULT]\n')
            fhini.write('storeroot = ./')

    def test_archive_storage(self):
        with self.sh.cdcontext(self.udir):
            self.sh.untar(self.sh.path.join(DATAPATHTEST, 'uget_uenv_fakearchive.tar.bz2'),
                          verbose=False)
        with self.server():
            # Necessary setup for archive stores
            self.t.glove.default_fthost = 'localhost:{:d}'.format(self.port)
            self.t.glove.setftuser('testlogin')
            # Fake config for the uget store
            self._uget_archive_dump_config()
            with self.sh.ftppool(nrcfile=self._fnrc):

                # Test the archive store alone
                stA = fp.proxy.store(scheme='uget', netloc='uget.archive.fr', storetube='ftp')
                # In order to have the configuration file read in
                self.assertTrue(stA.check(uriparse('uget://uget.archive.fr/data/mask.atms.01b@huguette'),
                                dict()))
                with self.sh.cdcontext('archive1', create=True):
                    # "Normal" file
                    stA.get(uriparse('uget://uget.archive.fr/data/mask.atms.01b@huguette'),
                            'mask1', dict())
                    with io.open('mask1') as fhm:
                        self.assertEqual(fhm.readline().rstrip("\n"), 'archive')
                    # "Normal" file in a container
                    cont = fp.proxy.container(incore=True)
                    self.assertTrue(
                        stA.get(uriparse('uget://uget.archive.fr/data/mask.atms.01b@huguette'),
                                cont.iotarget(), dict()))
                    cont.rewind()
                    self.assertEqual(cont.readline().rstrip(b'\n'), b'archive')
                    # Get a tar file but do not expand it because of its name (from hack)
                    self.assertTrue(
                        stA.get(uriparse('uget://uget.archive.fr/data/rrtm.const.02b.tgz@huguette'),
                                'nam_nope', dict()))
                    # Get a tar file and expand it because of its name (from hack)
                    self.assertTrue(
                        stA.get(uriparse('uget://uget.archive.fr/data/rrtm.const.02b.tgz@huguette'),
                                self.sh.path.join('rrtm_arch', 'rrtm_full.tgz'), dict()))
                    with self.sh.cdcontext('rrtm_arch'):
                        for i in range(1, 4):
                            with io.open('file{:d}'.format(i)) as fhm:
                                self.assertEqual(fhm.readline().rstrip("\n"), 'archive')
                    self.assertTrue(
                        stA.get(uriparse('uget://uget.archive.fr/data/cy99t1.00.nam.tgz@huguette'),
                                self.sh.path.join('nam_arch', 'nam_full.tgz'), dict()))
                    with self.sh.cdcontext('nam_arch'):
                        for i in range(1, 4):
                            with io.open('file{:d}'.format(i)) as fhm:
                                self.assertEqual(fhm.readline().rstrip("\n"), 'archive')
                        self.assertTrue(self.sh.path.islink('link1'))
                    # Namelist with extract
                    self.assertTrue(
                        stA.get(uriparse('uget://uget.archive.fr/data/cy99t1.00.nam.tgz@huguette?extract=file1'),
                                self.sh.path.join('nam_ext1', 'nam_ext_arch1'), dict()))
                    with io.open(self.sh.path.join('nam_ext1', 'nam_ext_arch1')) as fhm:
                        self.assertEqual(fhm.readline().rstrip("\n"), 'archive')
                    # Namelist in a container
                    cont = fp.proxy.container(incore=True)
                    self.assertTrue(
                        stA.get(uriparse('uget://uget.archive.fr/data/cy99t1.00.nam.tgz@huguette?extract=file1'),
                                cont.iotarget(), dict()))
                    cont.rewind()
                    self.assertEqual(cont.readline().rstrip(b'\n'), b'archive')
                    # Put a file in the archive
                    stAbis = fp.proxy.store(scheme='uget', netloc='uget.archive.fr',
                                            storetube='ftp', readonly=False)
                    self.assertTrue(stAbis.put('mask1',
                                               uriparse('uget://uget.archive.fr/data/mask.atms.02@huguette'),
                                               dict()))
                    self.assertFalse(stAbis.put(
                        self.sh.path.join('nam_ext1', 'nam_ext_arch1'),
                        uriparse('uget://uget.archive.fr/data/cy99t1.00.nam.tgz@huguette?extract=fileX'),
                        dict()
                    ))
                    with io.open(self.sh.path.join(self.udir, 'uget', 'data', 'c', 'mask.atms.02')) as fhm:
                        self.assertEqual(fhm.readline().rstrip("\n"), 'archive')
                    # Check the remote file size
                    self.assertEqual(stA.check(uriparse('uget://uget.archive.fr/data/mask.atms.02@huguette'),
                                               dict()), 8)
                    # Locate a file
                    self.assertEqual(stA.locate(uriparse('uget://uget.archive.fr/data/mask.atms.02@huguette'),
                                                dict()),
                                     'testlogin@localhost:./uget/data/c/mask.atms.02')
                    # List remote data
                    self.assertSetEqual(set(stA.list(uriparse('uget://uget.archive.fr/data/@huguette'), dict())),
                                        {'cy99t1.00.nam.tgz', 'grib_api.def.02.tgz',
                                         'mask.atms.01b', 'mask.atms.02', 'rrtm.const.02b.tgz'})
                    self.assertFalse(stA.list(uriparse('uget://uget.archive.fr/data/mask@huguette'), dict()))
                    self.assertTrue(stA.list(uriparse('uget://uget.archive.fr/data/mask.atms.02@huguette'), dict()))
                    # Delete from archive
                    self.assertTrue(stAbis.delete(uriparse('uget://uget.archive.fr/data/mask.atms.02@huguette'),
                                                  dict()))
                    self.assertFalse(stA.check(uriparse('uget://uget.archive.fr/data/mask.atms.02@huguette'),
                                               dict()))

                # Test some refill
                stM = fp.proxy.store(scheme='uget', netloc='uget.multi.fr', storetube='ftp')
                with self.sh.cdcontext('refill1', create=True):
                    stM.get(uriparse('uget://uget.multi.fr/data/mask.atms.01b@huguette'),
                            'mask2', dict())
                    with io.open('mask2') as fhm:
                        self.assertEqual(fhm.readline().rstrip("\n"), 'archive')
                    # Get a tar file but do not expand it because of its name (from hack)
                    self.assertTrue(
                        stM.get(uriparse('uget://uget.multi.fr/data/rrtm.const.02b.tgz@huguette'),
                                'nam_nope2', dict()))
                    # Get a tar file and expand it because of its name (from hack)
                    self.assertTrue(
                        stM.get(uriparse('uget://uget.multi.fr/data/rrtm.const.02b.tgz@huguette'),
                                self.sh.path.join('rrtm_arch2', 'rrtm_full.tgz'), dict()))
                    with self.sh.cdcontext('rrtm_arch2'):
                        for i in range(1, 4):
                            with io.open('file{:d}'.format(i)) as fhm:
                                self.assertEqual(fhm.readline().rstrip("\n"), 'archive')
                    # Namelist with extract
                    self.assertTrue(
                        stM.get(
                            uriparse('uget://uget.multi.fr/data/cy99t1.00.nam.tgz@huguette?extract=file1'),
                            'nam_ext_arch2', dict()))
                    with io.open('nam_ext_arch2') as fhm:
                        self.assertEqual(fhm.readline().rstrip("\n"), 'archive')
                    self.assertTrue(
                        stM.get(uriparse('uget://uget.multi.fr/data/cy99t1.00.nam.tgz@huguette'),
                                self.sh.path.join('nam_arch2', 'nam_full.tgz'), dict()))
                    with self.sh.cdcontext('nam_arch2'):
                        for i in range(1, 4):
                            with io.open('file{:d}'.format(i)) as fhm:
                                self.assertEqual(fhm.readline().rstrip("\n"), 'archive')
                        self.assertTrue(self.sh.path.islink('link1'))

        # Did the refill succeed ?
        stC = fp.proxy.store(scheme='uget', netloc='uget.cache.fr', storetube='ftp')
        with self.sh.cdcontext('refill2', create=True):
            stC.get(uriparse('uget://uget.cache.fr/data/mask.atms.01b@huguette'),
                    'mask3', dict())
            with io.open('mask3') as fhm:
                self.assertEqual(fhm.readline().rstrip("\n"), 'archive')
            # Get a tar file but do not expand it because of its name (from hack)
            self.assertTrue(
                stC.get(uriparse('uget://uget.cache.fr/data/rrtm.const.02b.tgz@huguette'),
                        'nam_nope3', dict()))
            # Get a tar file and expand it because of its name (from hack)
            self.assertTrue(
                stC.get(uriparse('uget://uget.cache.fr/data/rrtm.const.02b.tgz@huguette'),
                        self.sh.path.join('rrtm_arch3', 'rrtm_full.tgz'), dict()))
            with self.sh.cdcontext('rrtm_arch3'):
                for i in range(1, 4):
                    with io.open('file{:d}'.format(i)) as fhm:
                        self.assertEqual(fhm.readline().rstrip("\n"), 'archive')
            # Namelist with extract
            self.assertTrue(
                stC.get(
                    uriparse('uget://uget.cache.fr/data/cy99t1.00.nam.tgz@huguette?extract=file2'),
                    'nam_ext_arch3', dict()))
            with io.open('nam_ext_arch3') as fhm:
                self.assertEqual(fhm.readline().rstrip("\n"), 'archive')
            self.assertTrue(
                stC.get(uriparse('uget://uget.cache.fr/data/cy99t1.00.nam.tgz@huguette'),
                        self.sh.path.join('nam_arch3', 'nam_full.tgz'), dict()))
            with self.sh.cdcontext('nam_arch3'):
                for i in range(1, 4):
                    with io.open('file{:d}'.format(i)) as fhm:
                        self.assertEqual(fhm.readline().rstrip("\n"), 'archive')
                self.assertTrue(self.sh.path.islink('link1'))
