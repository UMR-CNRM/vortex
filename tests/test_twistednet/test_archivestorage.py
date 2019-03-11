# -*- coding: utf-8 -*-

"""
Test Vortex's FTP client
"""

from __future__ import print_function, absolute_import, unicode_literals, division
import six

import ftplib
import gzip
import io
import tempfile
import unittest

from bronx.fancies import loggers
from footprints import proxy as fpx
import vortex
from vortex.tools import compression

from . import has_ftpservers
from .utils import get_ftp_port_number

tloglevel = 9999


@unittest.skipUnless(has_ftpservers(), 'FTP Server')
@loggers.unittestGlobalLevel(tloglevel)
class TestArchiveStorage(unittest.TestCase):

    def setUp(self):
        self.sh = vortex.sh()
        self.tdir = tempfile.mkdtemp(prefix='archive_storage_testdir_')
        self.udir = self.sh.path.join(self.tdir, 'testlogin')
        self.user = 'testlogin'
        self.password = 'aqmp'
        self.sh.mkdir(self.udir)
        self._oldpwd = self.sh.getcwd()
        self.sh.chdir(self.tdir)
        # Fake NetRC
        self._fnrc = 'fakenetrc'
        with io.open(self._fnrc, 'w') as fhnrc:
            fhnrc.write('machine localhost login {:s} password {:s}'
                        .format(self.user, self.password))
        self.sh.chmod(self._fnrc, 0o600)
        # FTP Config
        self.port = get_ftp_port_number()
        self.configure_ftpserver()

    def configure_ftpserver(self):
        from .ftpservers import TestFTPServer, logger
        logger.setLevel(tloglevel)
        self.server = TestFTPServer(self.port, self.tdir,
                                    self.user, self.password)

    def tearDown(self):
        self.sh.chdir(self._oldpwd)
        self.sh.rmtree(self.tdir)

    def assertFile(self, path, content):
        self.assertTrue(self.sh.path.exists(path))
        with io.open(path, 'rb') as fhr:
            self.assertEqual(fhr.read(), content)

    def assertRemote(self, path, content):
        where = self.sh.path.join(self.udir, path)
        self.assertFile(where, content)

    def ftp_client_thook(self):
        pass

    def archive(self):
        self.sh.touch('void_config_file.ini')
        return fpx.archive(kind = 'std',
                           storage='localhost:{:d}'.format(self.port),
                           tube = 'ftp',
                           inifile = 'void_config_file.ini')

    def test_archive_storage(self):
        with self.server():
            with self.sh.ftppool(nrcfile=self._fnrc):
                st = self.archive()
                self.assertEqual(st.actual_storage, 'localhost:{:d}'.format(self.port))
                self.assertEqual(st.actual_tube, 'ftp')
                self.assertEqual(st._ftp_hostinfos, ('localhost', self.port))
                self.assertEqual(st.fullpath('some/test/file'),
                                 'testlogin@localhost:some/test/file')
                self.assertEqual(st.check('some/test/file'), None)
                self.assertEqual(st.list('some/test/file'), None)
                with self.assertRaises(ftplib.error_perm):
                    self.assertEqual(st.retrieve('some/test/file', 'localtoto'), None)
                self.assertEqual(st.delete('some/test/file'), None)
                self.assertEqual(st.earlyretrieve('some/test/file', 'testlocal'), None)
                # Insert Some...
                testdata = six.BytesIO()
                testdata.write(b'Coucou')
                testdata.seek(0)
                self.assertTrue(st.insert('some/test/file1', testdata))
                self.assertRemote('some/test/file1', b'Coucou')
                # With a real file...
                with tempfile.NamedTemporaryFile(mode='wb', prefix='tmp_indputd',
                                                 delete=True) as fht:
                    fht.write(b'Hello')
                    fht.seek(0)
                    fht.flush()
                    self.assertTrue(st.insert('some/test/file1', fht.name))
                    self.assertRemote('some/test/file1', b'Hello')
                    # Another one...
                    self.assertTrue(st.insert('some/test/file2', fht.name))
                    self.assertEqual(st.check('some/test/file2'), 5)  # The file size
                    self.assertTrue(st.insert('file3', fht.name))
                    self.assertRemote('some/test/file2', b'Hello')
                    self.assertRemote('file3', b'Hello')
                # Test retrieves
                self.assertTrue(st.retrieve('some/test/file2', 'test_ret2'))
                self.assertFile('test_ret2', b'Hello')
                # Test Delete
                self.assertEqual(sorted(st.list('some/test')), ['file1', 'file2'])
                self.assertTrue(st.delete('some/test/file2'))
                self.assertEqual(sorted(st.list('some/test')), ['file1', ])
                self.assertEqual(st.list('some/test/file1'), True)
                self.assertFalse(st.check('some/test/file2'))
                # With compression
                cpipe = compression.CompressionPipeline(self.sh, 'gzip')
                with io.open('wonderfull_testfile', mode='w+b') as fht:
                    fht.write(b'Coucou_Very_Very_Long')
                    fht.seek(0)
                    fht.flush()
                    self.assertTrue(st.insert('some/test/filecomp', fht,
                                              compressionpipeline = cpipe))
                self.assertTrue(st.retrieve('some/test/filecomp.gz', 'testgzip1'))
                with gzip.GzipFile(filename='testgzip1', mode='rb') as fhgz:
                    self.assertEqual(fhgz.read(), b'Coucou_Very_Very_Long')
                self.assertTrue(st.retrieve('some/test/filecomp', 'testgzip2',
                                            compressionpipeline = cpipe))
                self.assertFile('testgzip2', b'Coucou_Very_Very_Long')
