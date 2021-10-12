# -*- coding: utf-8 -*-

"""
Test Vortex's FTP client
"""

from __future__ import print_function, absolute_import, unicode_literals, division
import six

import gzip
import io
import tarfile
import tempfile

from bronx.fancies import loggers
from footprints import proxy as fpx
from vortex.tools import compression
from vortex.tools import folder

from .ftpunittests import NetrcFtpBasedTestCase

assert folder

tloglevel = 9999


@loggers.unittestGlobalLevel(tloglevel)
class TestArchiveStorage(NetrcFtpBasedTestCase):

    _FTPLOGLEVEL = tloglevel

    def setUp(self):
        super(TestArchiveStorage, self).setUp()
        fpx.addon(kind='allfolders', shell=self.sh)

    def ftp_client_thook(self):
        pass

    def archive(self):
        self.sh.touch('void_config_file.ini')
        return fpx.archive(kind='std',
                           storage='localhost:{:d}'.format(self.port),
                           tube='ftp',
                           inifile='void_config_file.ini')

    def localarchive(self, expand=False):
        self.sh.touch('void_config_file.ini')
        return fpx.archive(kind='std',
                           storage='localhost',
                           tube='inplace',
                           inifile='void_config_file.ini',
                           auto_self_expand=expand,
                           )

    def _actual_archive_storage_test(self, st, remote_cb):
        self.assertEqual(st.check('some/test/file'), None)
        self.assertEqual(st.list('some/test/file'), None)
        self.assertFalse(st.retrieve('some/test/file', 'localtoto'))
        self.assertEqual(st.delete('some/test/file'), None)
        self.assertEqual(st.earlyretrieve('some/test/file', 'testlocal'), None)
        # Insert Some...
        testdata = six.BytesIO()
        testdata.write(b'Coucou')
        testdata.seek(0)
        self.assertTrue(st.insert('some/test/file1', testdata, usejeeves=False))
        remote_cb('some/test/file1', 'Coucou')
        # With a real file...
        with tempfile.NamedTemporaryFile(mode='wb', prefix='tmp_indputd',
                                         delete=True) as fht:
            fht.write(b'Hello')
            fht.seek(0)
            fht.flush()
            self.assertTrue(st.insert('some/test/file1', fht.name, usejeeves=False))
            remote_cb('some/test/file1', 'Hello')
            # Another one...
            self.assertTrue(st.insert('some/test/file2', fht.name, usejeeves=False))
            self.assertEqual(st.check('some/test/file2'), 5)  # The file size
            self.assertTrue(st.insert('file3', fht.name, usejeeves=False))
            remote_cb('some/test/file2', 'Hello')
            remote_cb('file3', 'Hello')
        # Test retrieves
        self.assertTrue(st.retrieve('some/test/file2', 'test_ret2'))
        self.assertFile('test_ret2', 'Hello')
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
                                      compressionpipeline=cpipe,
                                      usejeeves=False))
        self.assertTrue(st.retrieve('some/test/filecomp.gz', 'testgzip1'))
        with gzip.GzipFile(filename='testgzip1', mode='rb') as fhgz:
            self.assertEqual(fhgz.read(), b'Coucou_Very_Very_Long')
        self.assertTrue(st.retrieve('some/test/filecomp', 'testgzip2',
                                    compressionpipeline=cpipe))
        self.assertFile('testgzip2', 'Coucou_Very_Very_Long')
        # Work wth folders
        foldername = 'fancyfolder'
        self.sh.mkdir(foldername)
        self.sh.cp('wonderfull_testfile', self.sh.path.join(foldername, 'testfile1'))
        self.sh.cp('wonderfull_testfile', self.sh.path.join(foldername, 'testfile2'))
        self.assertTrue(st.insert('some/test/folder', foldername, fmt='filespack',
                                  usejeeves=False))
        self.assertTrue(st.retrieve('some/test/folder.tgz', foldername + '_raw.tgz'))
        tarobject = tarfile.open(foldername + '_raw.tgz', mode='r')
        try:
            tarobject.extractall(path='manual_ext1')
        finally:
            tarobject.close()
        for i in (1, 2):
            self.assertFile(self.sh.path.join('manual_ext1', foldername, 'testfile{:d}'.format(i)),
                            'Coucou_Very_Very_Long')
        self.assertTrue(st.retrieve('some/test/folder', foldername + '_auto', fmt='filespack'))
        for i in (1, 2):
            self.assertFile(self.sh.path.join(foldername + '_auto', 'testfile{:d}'.format(i)),
                            'Coucou_Very_Very_Long')

    def test_archive_storage(self):
        with self.server():
            with self.sh.ftppool(nrcfile=self._fnrc):
                st = self.archive()
                self.assertEqual(st._ftp_hostinfos, ('localhost', self.port))
                self.assertEqual(st.fullpath('some/test/file'),
                                 'testlogin@localhost:some/test/file')
                self._actual_archive_storage_test(st, remote_cb=self.assertRemote)

    def test_archive_localstorage(self):
        st = self.localarchive()
        self.assertEqual(st.fullpath('some/test/file'),
                         'some/test/file')
        self._actual_archive_storage_test(st, remote_cb=self.assertFile)
        # User expansion
        self.assertEqual(st.fullpath('~/mystuff'),
                         self.sh.path.expanduser('~/mystuff'))
        # Test the real-world storage
        st = self.localarchive(expand=True)
        self.assertEqual(st.fullpath('~/mystuff'),
                         self.sh.path.expanduser('~/mystuff'))
        self.assertEqual(st.fullpath('mystuff'),
                         self.sh.path.expanduser('~/mystuff'))
        self.assertEqual(st.fullpath('/mystuff'), '/mystuff')
        # Test failures
        with self.assertRaises(OSError):
            st.fullpath('~notexistingusername/mystuff')
