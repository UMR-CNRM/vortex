#!/usr/bin/env python
# -*- coding: utf-8 -*-

import hashlib
import os
import shutil
import tempfile
import unittest

from bronx.system.hash import HashAdapter
from bronx.system.interrupt import SignalInterruptHandler

DATADIR = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'data'))


class TestHashAdapter(unittest.TestCase):

    def setUp(self):
        # Work in a dedicated directory
        self.tmpdir = tempfile.mkdtemp(suffix='test_utils_hash')
        self.oldpwd = os.getcwd()
        os.chdir(self.tmpdir)

        self.sigh = SignalInterruptHandler()
        self.sigh.activate()

        self.bin_path = os.path.join(DATADIR, 'random_data.bin')
        self.md5_path = os.path.join(DATADIR, 'random_data.bin.md5')
        self.fake_path = os.path.join(DATADIR, 'false.ini')
        with open(self.md5_path, 'r') as m_fh:
            self.md5_sum = self._read_md5line(m_fh)

        self.md5_h = HashAdapter('md5')
        # Decrease the blocksize in order to test everything
        self.md5_h._PREFERED_BLOCKSIZE = 1024

    def tearDown(self):
        os.chdir(self.oldpwd)
        shutil.rmtree(self.tmpdir)
        self.sigh.deactivate()

    def _read_md5line(self, i_fh):
        return i_fh.readline().split(' ')[0]

    def test_hash_compute(self):
        # Filename or FileHandle to hash string
        self.assertEqual(self.md5_h.file2hash(self.bin_path), self.md5_sum)
        with open(self.bin_path, 'rb') as i_fh:
            self.assertEqual(self.md5_h.file2hash(i_fh), self.md5_sum)
        # Filename to hash FileHandle
        self.assertEqual(self._read_md5line(self.md5_h.file2hash_fh(self.bin_path)),
                         self.md5_sum)
        # Filename to hash file
        self.md5_h.file2hash_file(self.bin_path, 'test_file1.md5')
        with open('test_file1.md5', 'r') as t_fh:
            md5_test = self._read_md5line(t_fh)
        self.assertEqual(md5_test, self.md5_sum)
        # String 2 Hash
        strdata = u'dgerqgjnmrsgr864bgvsrdvsrce'
        self.assertEqual(self.md5_h.string2hash(strdata),
                         hashlib.md5(strdata.encode()).hexdigest())
        # Automatic check
        self.assertTrue(self.md5_h.filecheck(self.bin_path, self.md5_path))
        with open(self.md5_path, 'r') as m_fh:
            self.assertTrue(self.md5_h.filecheck(self.bin_path, m_fh))
        self.assertFalse(self.md5_h.filecheck(self.bin_path, self.fake_path))
        self.assertFalse(self.md5_h.filecheck(self.bin_path, 'toto'))


if __name__ == '__main__':
    unittest.main()