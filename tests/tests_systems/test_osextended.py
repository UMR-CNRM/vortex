# -*- coding:Utf-8 -*-
from __future__ import print_function, absolute_import, unicode_literals, division

import io
import os
import shutil
import tempfile
import unittest

import footprints as fp

from vortex.tools.systems import OSExtended


DATAPATHTEST = os.path.join(os.path.dirname(__file__), '../data')


class TestableOSExtended(OSExtended):

    _footprint = dict(
        attr = dict(
            hostname = dict(
                default  = 'unittestlogin001',
            ),
            sysname = dict(
                values  = ['UnitTestable'],
            ),
        )
    )


class TestOSExtendedBasics(unittest.TestCase):

    _TESTFILE_MSG = "This the test file !"
    _TESTFILE_DEFAULT = "the_testfile"

    def setUp(self):
        # Temporary heaven
        self.tmpdir = os.path.realpath(tempfile.mkdtemp(suffix='_test_storage'))
        self.startupdir = os.getcwd()
        os.chdir(self.tmpdir)
        self.create_testfile()
        # Create the system
        gl = fp.proxy.glove()
        self.sh = TestableOSExtended(glove=gl, sysname='UnitTestable')
        self.sh.target(inetname='unittest',
                       inifile=os.path.join(DATAPATHTEST, 'target-test.ini'),
                       sysname='Linux')

    def create_testfile(self):
        with io.open(self._TESTFILE_DEFAULT, 'w') as fhtest:
            fhtest.write(self._TESTFILE_MSG)

    def assert_testfile(self, path=_TESTFILE_DEFAULT):
        self.assertTrue(os.path.isfile(path))
        with io.open(path, 'r') as fhtest:
            self.assertEqual(fhtest.read(), self._TESTFILE_MSG)

    def assert_sameinode(self, file1, file2):
        self.assertEqual(self.sh.stat(file1).st_ino,
                         self.sh.stat(file2).st_ino)  # Hardlink

    def assert_not_sameinode(self, file1, file2):
        self.assertNotEqual(self.sh.stat(file1).st_ino,
                            self.sh.stat(file2).st_ino)  # "Real" copy

    def tearDown(self):
        # Clean up the mess
        os.chdir(self.startupdir)
        shutil.rmtree(self.tmpdir)

    def test_file_operations(self):
        # Cat
        fcat = self.sh.cat(self._TESTFILE_DEFAULT)
        self.assertEqual('\n'.join(fcat), self._TESTFILE_MSG)
        # Simple copy
        self.assertTrue(self.sh.cp(self._TESTFILE_DEFAULT, 'tbis.txt'))
        self.assert_testfile('tbis.txt')
        self.assert_not_sameinode(self._TESTFILE_DEFAULT, 'tbis.txt')
        self.assertTrue(self.sh.cp(self._TESTFILE_DEFAULT, 'tter.txt', intent="in"))
        self.assert_testfile('tter.txt')
        self.assert_sameinode(self._TESTFILE_DEFAULT, 'tter.txt')
        # Mkdir
        self.assertTrue(self.sh.mkdir('testdir'))
        self.assertTrue(self.sh.path.isdir('testdir'))
        self.assertTrue(self.sh.mkdir('testdir'))
        # The "mkdir -p" case
        self.assertTrue(self.sh.mkdir(self.sh.path.join('testdir', 'sub1', 'sub2')))
        self.assertTrue(self.sh.cp(self._TESTFILE_DEFAULT,
                                   self.sh.path.join('testdir', 'tsfile1'),
                                   intent='in'))
        self.assertTrue(self.sh.path.isdir(self.sh.path.join('testdir', 'sub1', 'sub2')))
        # Symlinks
        self.sh.softlink('tbis.txt', 'tlink0.txt')
        self.assertTrue(self.sh.path.islink('tlink0.txt'))
        self.sh.softlink('./tbis.txt', 'tlink1.txt')
        self.assertTrue(self.sh.path.islink('tlink1.txt'))
        self.sh.softlink('../../../{:s}/tbis.txt'
                         .format(self.sh.path.basename(self.tmpdir)),
                         self.sh.path.join('testdir', 'sub1', 'tlink2.txt'))
        self.assert_testfile(self.sh.path.join('testdir', 'sub1', 'tlink2.txt'))
        self.sh.softlink(self.sh.path.abspath('tbis.txt'),
                         self.sh.path.join('testdir', 'sub1', 'tlink2abs.txt'))
        self.sh.softlink('../tsfile1',
                         self.sh.path.join('testdir', 'sub1', 'tlink3.txt'))
        self.assert_testfile(self.sh.path.join('testdir', 'sub1', 'tlink2abs.txt'))
        # Valid symlinks
        self.assertEqual(self.sh._validate_symlink_below('tlink0.txt', self.tmpdir),
                         'tbis.txt')
        self.assertEqual(self.sh._validate_symlink_below('tlink1.txt', self.tmpdir),
                         'tbis.txt')
        self.assertEqual(
            self.sh._validate_symlink_below(
                self.sh.path.join('testdir', 'sub1', 'tlink2.txt'),
                self.tmpdir
            ),
            '../../tbis.txt'
        )
        self.assertIsNone(
            self.sh._validate_symlink_below(
                self.sh.path.join('testdir', 'sub1', 'tlink2.txt'),
                self.sh.path.join(self.tmpdir, 'testdir')
            )
        )
        self.assertIsNone(
            self.sh._validate_symlink_below(
                self.sh.path.join('testdir', 'sub1', 'tlink2abs.txt'),
                self.tmpdir
            )
        )
        # Copy of complex directory structures
        self.assertTrue(self.sh.cp('testdir', 'testdir_in', intent='in'))
        self.assert_sameinode(self._TESTFILE_DEFAULT,
                              self.sh.path.join('testdir_in', 'tsfile1'))
        for lname in ('tlink2.txt', 'tlink2abs.txt'):
            self.assert_sameinode('tbis.txt',
                                  self.sh.path.join('testdir_in', 'sub1', lname))
            self.assertFalse(self.sh.path.islink(
                self.sh.path.join('testdir_in', 'sub1', lname)
            ))
        self.assertTrue(self.sh.path.islink(
            self.sh.path.join('testdir_in', 'sub1', 'tlink3.txt')
        ))
        self.assert_sameinode(self._TESTFILE_DEFAULT,
                              self.sh.path.join('testdir_in', 'sub1', 'tlink3.txt'))
        self.assertTrue(self.sh.cp('testdir', 'testdir_inout', intent='inout'))
        self.assert_not_sameinode(self._TESTFILE_DEFAULT,
                                  self.sh.path.join('testdir_inout', 'tsfile1'))
        for lname in ('tlink2.txt', 'tlink2abs.txt'):
            self.assert_not_sameinode('tbis.txt',
                                      self.sh.path.join('testdir_inout', 'sub1', lname))
            self.assertFalse(self.sh.path.islink(
                self.sh.path.join('testdir_inout', 'sub1', lname)
            ))
        self.assertTrue(self.sh.path.islink(
            self.sh.path.join('testdir_inout', 'sub1', 'tlink3.txt')
        ))
        self.assert_sameinode(self.sh.path.join('testdir_inout', 'tsfile1'),
                              self.sh.path.join('testdir_inout', 'sub1', 'tlink3.txt'))


if __name__ == "__main__":
    unittest.main(verbosity=2)
