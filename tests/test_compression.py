import hashlib
import os
import tempfile
import unittest

import vortex
from vortex.tools.compression import CompressionPipeline


class TestCompression(unittest.TestCase):

    def setUp(self):
        super().setUp()
        # Session + System
        self.t = vortex.sessions.current()
        self.sh = self.t.system()
        # Work in a dedicated directory
        self.tmpdir = tempfile.mkdtemp(suffix='test_compression')
        self.oldpwd = self.sh.pwd()
        self.sh.cd(self.tmpdir)
        # Create a temporary test file
        self.testfile = 'rawtestfile'
        try:
            raw = os.urandom(128 * 1024)  # 1Mb
        except NotImplementedError:
            self.skipTest("os.urandom is not availlable.")
        m = hashlib.md5()
        m.update(raw)
        self.testfilesum = m.digest()
        with open("rawtestfile", "wb") as fhtest:
            fhtest.write(raw)

    def tearDown(self):
        self.sh.cd(self.oldpwd)
        self.sh.remove(self.tmpdir)

    def assertDataConsistency(self, source):
        if isinstance(source, str):
            with open(source, 'rb') as fhin:
                data = fhin.read()
        else:
            data = source.read()
        m = hashlib.md5()
        m.update(data)
        return self.assertEqual(m.digest(), self.testfilesum)

    def test_compression_basics(self):
        # --- Basic gzip ---
        cp = CompressionPipeline(self.sh, 'gzip')
        # With files
        cp.compress2file(self.testfile, 'test_g1.gz')
        cp.file2uncompress('test_g1.gz', 'test_g1')
        self.assertDataConsistency('test_g1')
        # With streams
        with open("test_g2", "wb") as fhout:
            with open(self.testfile) as fhin:
                with cp.compress2stream(fhin) as scompressed:
                    with cp.stream2uncompress(fhout) as sdest:
                        self.sh.copyfileobj(scompressed, sdest)
        self.assertDataConsistency("test_g2")
        # IoSponge
        with cp.compress2stream(self.testfile, iosponge=True) as scompressed:
            self.assertEqual(scompressed.size, self.sh.size("test_g1.gz"))
        # --- Basic bzip2 with compression level ---
        cp = CompressionPipeline(self.sh, 'bzip2&complevel=2')
        with open("test_b1", "wb") as fhout:
            with cp.compress2stream(self.testfile) as scompressed:
                with cp.stream2uncompress(fhout) as sdest:
                    self.sh.copyfileobj(scompressed, sdest)
        self.assertDataConsistency("test_b1")
        # --- gzip+bzip2 ---
        cp = CompressionPipeline(self.sh, 'gzip|bzip2&complevel=2')
        self.assertEqual(cp.suffix, ".gz.bz2")
        with open("test_gb1", "wb") as fhout:
            with cp.compress2stream(self.testfile) as scompressed:
                with cp.stream2uncompress(fhout) as sdest:
                    self.sh.copyfileobj(scompressed, sdest)
        self.assertDataConsistency("test_gb1")

    def test_compression_system(self):
        self.sh.generic_compress('gzip&complevel=1', self.testfile, 'test_sys1.gz')
        self.sh.generic_uncompress('gzip&complevel=1', 'test_sys1.gz')
        self.assertDataConsistency("test_sys1")


if __name__ == '__main__':
    unittest.main()
