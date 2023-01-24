"""
Created on 13 nov. 2018

@author: meunierlf
"""

import contextlib
import copy
import io
import os
import shutil
import sys
import tempfile
import unittest

from bronx.fancies import loggers
from vortex.data import containers as cts

tloglevel = 'critical'


@contextlib.contextmanager
def capture(command, *args, **kwargs):
    out, sys.stdout = sys.stdout, io.StringIO()
    try:
        command(*args, **kwargs)
        sys.stdout.seek(0)
        yield sys.stdout.read()
    finally:
        sys.stdout = out


@loggers.unittestGlobalLevel(tloglevel)
class TestContainers(unittest.TestCase):

    def setUp(self):
        # Generate a temporary directory
        self.tmpdir = tempfile.mkdtemp(suffix='_test_storage')
        self.oldpwd = os.getcwd()
        os.chdir(self.tmpdir)

    def tearDown(self):
        os.chdir(self.oldpwd)
        shutil.rmtree(self.tmpdir)

    def test_incore(self):
        teststr = 'Coucou héhéhé'
        testraw = teststr.encode('utf_8')
        # Default write, rewind, read
        inc1 = cts.InCore(incore=True)
        self.assertEqual(inc1.actualpath(), 'NotSpooled')
        self.assertIs(inc1.defaultmode, None)
        self.assertEqual(inc1.actualmode, cts.InCore._DEFAULTMODE)
        self.assertIs(inc1.defaultencoding, None)
        self.assertEqual(inc1.actualencoding, None)
        self.assertIsInstance(inc1.iotarget(), tempfile.SpooledTemporaryFile)
        self.assertEqual(inc1.actualpath(), 'MemoryResident')
        inc1.write(testraw)
        inc1.rewind()
        self.assertEqual(inc1.read(), testraw)
        # As soon as preferred setting change, start from scratch
        with inc1.preferred_decoding(byte=False, encoding='utf-8'):
            inc1.write(teststr)
            self.assertEqual(inc1.actualmode, 'w+')
            self.assertEqual(inc1.actualencoding, 'utf-8')
            self.assertEqual(inc1.readlines(), [teststr, ])
        # The container is still open so that mode/encoding remain...
        self.assertEqual(inc1.actualmode, 'w+')
        self.assertEqual(inc1.actualencoding, 'utf-8')
        self.assertEqual(inc1.readlines(), [teststr, ])
        inc1.endoc()
        inc1.write('\n' + teststr)
        self.assertEqual(inc1.readlines(), [teststr + '\n', teststr])
        self.assertEqual(inc1.head(1), [teststr + '\n'])
        inc1.rewind()
        self.assertEqual(inc1.dataread(), (teststr + '\n', False))
        self.assertEqual(inc1.dataread(), (teststr, True))
        self.assertEqual([l for l in inc1], [teststr + '\n', teststr])
        # Temporise
        self.assertFalse(inc1.temporized)
        inc1.temporize()
        self.assertNotIn(inc1.actualpath(), ['NotSpooled', 'MemoryResident'])
        self.assertEqual(inc1.readlines(), [teststr + '\n', teststr])
        self.assertTrue(inc1.temporized)
        inc1.unroll()
        self.assertIsInstance(inc1.iotarget(), tempfile.SpooledTemporaryFile)
        self.assertEqual(inc1.readlines(), [teststr + '\n', teststr])
        self.assertFalse(inc1.temporized)
        # As soon as preferred setting change, start from scratch
        with inc1.preferred_decoding(byte=True):
            inc1.write(testraw)
            self.assertIs(inc1.defaultmode, None)
            self.assertEqual(inc1.actualmode, 'wb+')
            self.assertIs(inc1.defaultencoding, None)
            self.assertEqual(inc1.actualencoding, None)
            inc1.rewind()
            self.assertEqual(inc1.read(), testraw)
        # Prescribe the mode
        inc1.write(teststr, mode='w+', encoding='utf-8')
        self.assertEqual(inc1.defaultmode, 'w+')
        self.assertEqual(inc1.actualmode, 'w+')
        self.assertEqual(inc1.defaultencoding, 'utf-8')
        self.assertEqual(inc1.actualencoding, 'utf-8')
        # This will have no effect since mode/encoding is hardwired
        with inc1.preferred_decoding(byte=True):
            with self.assertRaises(TypeError):
                inc1.write(testraw)
            inc1.write('\n' + teststr)
        self.assertEqual(inc1.readlines(), [teststr + '\n', teststr])
        inc1.rewind()
        inc1.append('\n' + teststr)
        self.assertEqual(inc1.readlines(), [teststr + '\n',
                                            teststr + '\n', teststr])
        inc1.updfill(getrc=True)
        self.assertTrue(inc1.filled)
        self.assertTrue(inc1.exists())
        with capture(inc1.cat) as textout:
            textcat = textout
        self.assertEqual(textcat,
                         teststr + '\n' + teststr + '\n' + teststr + '\n')
        self.assertEqual(inc1.localpath(),
                         inc1.iodesc().name)
        inc1.close()
        # When default are not specified in the footprint, they are lost
        self.assertIs(inc1.defaultmode, None)
        self.assertEqual(inc1.actualmode, cts.InCore._DEFAULTMODE)
        self.assertIs(inc1.defaultencoding, None)
        self.assertEqual(inc1.actualencoding, None)
        # Prescribe the mode at startup
        inc2 = cts.InCore(mode='w+', encoding='utf-8')
        self.assertEqual(inc2.defaultmode, 'w+')
        self.assertEqual(inc2.actualmode, 'w+')
        self.assertEqual(inc2.defaultencoding, 'utf-8')
        self.assertEqual(inc2.actualencoding, 'utf-8')
        inc2.write(teststr)
        # This will have no effect since mode/encoding is hardwired
        with inc2.preferred_decoding(byte=True):
            with self.assertRaises(TypeError):
                inc2.write(testraw)
            inc2.write('\n' + teststr)
        self.assertEqual(inc2.readlines(), [teststr + '\n', teststr])
        inc2.close()
        # Default are kept since they where given in the footprint
        self.assertEqual(inc2.defaultmode, 'w+')
        self.assertEqual(inc2.actualmode, 'w+')
        self.assertEqual(inc2.defaultencoding, 'utf-8')
        self.assertEqual(inc2.actualencoding, 'utf-8')

    def test_mayfly(self):
        teststr = 'Coucou héhéhé'
        testraw = teststr.encode('utf_8')
        # Default write, rewind, read
        inc1 = cts.MayFly()
        self.assertEqual(inc1.actualpath(), 'NotDefined')
        inc1.write(testraw)
        inc1.rewind()
        self.assertEqual(inc1.read(), testraw)
        self.assertEqual(inc1.actualpath(), inc1.iodesc().name)

    def test_filelike(self):
        teststr = 'Coucou héhéhé'
        testraw = teststr.encode('utf_8')
        # ShouldFly
        inc1 = cts.UnnamedSingleFile()
        self.assertEqual(inc1.actualpath(),
                         os.path.join(os.getcwd(), inc1.filename))
        self.assertEqual(inc1.basename, inc1.filename)
        self.assertFalse(inc1.exists())
        inc1.write(testraw)
        inc1.rewind()
        self.assertEqual(inc1.read(), testraw)
        self.assertTrue(inc1.exists())
        inc1.clear()
        self.assertFalse(inc1.exists())
        inc1 = cts.UnnamedSingleFile(cwdtied=False)
        self.assertEqual(inc1.iotarget(), inc1.filename)
        self.assertEqual(inc1.abspath,
                         os.path.join(os.getcwd(), inc1.filename))
        self.assertEqual(inc1.absdir, os.getcwd())
        inc2 = copy.deepcopy(inc1)
        self.assertNotEqual(inc1.filename, inc2.filename)
        # Uuid4Fly
        inc1 = cts.Uuid4UnamedSingleFile(uuid4flydir='toto')
        os.makedirs('toto')
        self.assertEqual(os.path.dirname(inc1.actualpath()),
                         'toto')
        self.assertFalse(inc1.exists())
        inc1.write(testraw)
        inc1.rewind()
        self.assertEqual(inc1.read(), testraw)
        self.assertTrue(inc1.exists())
        inc1.clear()
        self.assertFalse(inc1.exists())
        inc2 = copy.deepcopy(inc1)
        self.assertNotEqual(inc1.filename, inc2.filename)
        # Common
        inc1 = cts.SingleFile(filename='testfile1')
        self.assertEqual(inc1.actualpath(), inc1.filename)
        self.assertFalse(inc1.exists())
        inc1.write(testraw)
        inc1.rewind()
        self.assertEqual(inc1.read(), testraw)
        self.assertTrue(inc1.exists())
        inc1.clear()
        self.assertFalse(inc1.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
