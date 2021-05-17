# -*- coding: utf-8 -*-

"""
Test Vortex's FTP client
"""

from __future__ import print_function, absolute_import, unicode_literals, division
import six

import gzip
import io
import tempfile

from bronx.fancies import loggers
from footprints import proxy as fpx
from vortex.tools import compression

from .ftpunittests import NetrcFtpBasedTestCase

tloglevel = 9999


@loggers.unittestGlobalLevel(tloglevel)
class TestArchiveStorage(NetrcFtpBasedTestCase):

    _FTPLOGLEVEL = tloglevel

    def ftp_client_thook(self):
        pass

    def archive(self):
        self.sh.touch('void_config_file.ini')
        return fpx.archive(kind='std',
                           storage='localhost:{:d}'.format(self.port),
                           tube='ftp',

                           inifile='void_config_file.ini')

    def test_archive_storage(self):
        with self.server():
            with self.sh.ftppool(nrcfile=self._fnrc):
                st = self.archive()
                self.assertEqual(st._ftp_hostinfos, ('localhost', self.port))
                self.assertEqual(st.fullpath('some/test/file'),
                                 'testlogin@localhost:some/test/file')
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
                self.assertRemote('some/test/file1', 'Coucou')
                # With a real file...
                with tempfile.NamedTemporaryFile(mode='wb', prefix='tmp_indputd',
                                                 delete=True) as fht:
                    fht.write(b'Hello')
                    fht.seek(0)
                    fht.flush()
                    self.assertTrue(st.insert('some/test/file1', fht.name, usejeeves=False))
                    self.assertRemote('some/test/file1', 'Hello')
                    # Another one...
                    self.assertTrue(st.insert('some/test/file2', fht.name, usejeeves=False))
                    self.assertEqual(st.check('some/test/file2'), 5)  # The file size
                    self.assertTrue(st.insert('file3', fht.name, usejeeves=False))
                    self.assertRemote('some/test/file2', 'Hello')
                    self.assertRemote('file3', 'Hello')
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
