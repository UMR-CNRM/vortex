"""
Test Vortex's FTP client
"""

import ftplib
import io
import tempfile

from bronx.fancies import loggers
from vortex.tools.net import StdFtp, AutoRetriesFtp, FtpConnectionPool

from .ftpunittests import FtpBasedTestCase

tloglevel = 9999


class FakeFp:

    def __init__(self):
        self.done = False

    def read(self, blocksize):
        if self.done:
            return ''
        else:
            self.done = True
            return b'Coucou'[:blocksize]


@loggers.unittestGlobalLevel(tloglevel)
class TestStdFtp(FtpBasedTestCase):

    _FTPLOGLEVEL = tloglevel

    def new_ftp_client(self):
        return StdFtp(self.sh, 'localhost', self.port, ignoreproxy=True)

    def ftp_client_thook(self):
        pass

    def test_ftp_client(self):
        with self.server():
            self.ftp_client_thook()
            ftpc = self.new_ftp_client()
            self.assertEqual(ftpc.host, 'localhost')
            ftpc.fastlogin(self.user, self.password)
            self.assertEqual(ftpc.pwd(), '/')
            self.assertEqual(ftpc.host, 'localhost')
            self.assertEqual(ftpc.netpath('toto'),
                             'testlogin@localhost:toto')
            self.assertEqual(ftpc.logname, 'testlogin')
            ftpc.close()
            ftpc = self.new_ftp_client()
            with self.assertRaises(RuntimeError):
                ftpc.pwd()
            ftpc.fastlogin(self.user, self.password, delayed=False)
            self.assertEqual(ftpc.logname, 'testlogin')
            with ftpc:
                self.assertEqual(ftpc.pwd(), '/')
                testdata = io.BytesIO()
                testdata.write(b'Coucou')
                self.assertTrue(ftpc.mkd('dirX'))
                self.assertTrue(ftpc.cd('dirX'))
                self.assertTrue(ftpc.put(testdata, 'coucou1'))
                self.assertRemote('dirX/coucou1', 'Coucou')
                self.assertTrue(ftpc.cd('..'))
                with tempfile.NamedTemporaryFile(mode='wb', prefix='tmp_indputd',
                                                 delete=True) as fht:
                    fht.write(b'Hello')
                    fht.seek(0)
                    fht.flush()
                    self.assertTrue(ftpc.put(fht.name, 'dir1/coucou1'))
                self.assertRemote('dir1/coucou1', 'Hello')
                self.assertTrue(ftpc.cd('dir1'))
                self.assertTrue(ftpc.put(FakeFp(), 'coucou2'))
                self.assertRemote('dir1/coucou2', 'Coucou')
                self.assertEqual(set(ftpc.nlst('.')),
                                 {'coucou1', 'coucou2'})
                self.assertTrue(all(['coucou' in l for l in ftpc.list()]))
                self.assertTrue(ftpc.put(testdata, 'dirbis/coucou3'))
                self.assertRemote('dir1/dirbis/coucou3', 'Coucou')
                self.assertTrue(ftpc.rm('coucou2'))
                self.assertFalse(self.sh.path.exists(self.sh.path.join(self.udir, 'dir1/coucou2')))
                self.assertEqual(ftpc.size('coucou1'), 5)
                self.assertIsInstance(ftpc.mtime('coucou1'), int)
                self.assertTrue(ftpc.get('dirbis/coucou3', 'rawget'))
                self.assertFile('rawget', 'Coucou')
                testget = io.BytesIO()
                self.assertTrue(ftpc.get('coucou1', testget))
                testget.seek(0)
                self.assertEqual(testget.read(), b'Hello')
                with self.assertRaises(ftplib.error_perm):
                    ftpc.get('unexistant', testget)


class TestAutoRetriesFtp(TestStdFtp):

    def configure_ftpserver(self):
        from .ftpservers import TestFTPServer, logger
        from twisted.protocols.ftp import AUTH_FAILURE, TOO_MANY_CONNECTIONS
        logger.setLevel(self._FTPLOGLEVEL)
        self.server = TestFTPServer(self.port, self.tdir,
                                    self.user, self.password,
                                    pass_seq=(AUTH_FAILURE, AUTH_FAILURE, TOO_MANY_CONNECTIONS, AUTH_FAILURE, True,),
                                    retr_seq=(TOO_MANY_CONNECTIONS, True, TOO_MANY_CONNECTIONS),
                                    stor_seq=(AUTH_FAILURE, TOO_MANY_CONNECTIONS, TOO_MANY_CONNECTIONS,
                                              TOO_MANY_CONNECTIONS,),
                                    )

    def new_ftp_client(self):
        return AutoRetriesFtp(self.sh, 'localhost', port=self.port, ignoreproxy=True,
                              retrycount_default=2, retrycount_connect=2, retrycount_login=3,
                              retrydelay_default=0.1, retrydelay_connect=0.1, retrydelay_login=0.1)

    def ftp_client_thook(self):
        ftpc = self.new_ftp_client()
        self.assertEqual(ftpc.host, 'localhost')
        with self.assertRaises(ftplib.error_temp):
            ftpc.fastlogin(self.user, self.password, delayed=False)
        ftpc.fastlogin(self.user, self.password, delayed=False)
        self.assertEqual(ftpc.pwd(), '/')
        with self.assertRaises(ftplib.error_perm):
            self.assertTrue(ftpc.put(FakeFp(), 'dir2/coucouX'))
        with self.assertRaises(ftplib.error_temp):
            self.assertTrue(ftpc.put(FakeFp(), 'dir2/coucouX'))


class TestPooledFtp(TestStdFtp):

    def setUp(self):
        super().setUp()
        self._fnrc = 'fakenetrc'
        with open(self._fnrc, 'w') as fhnrc:
            fhnrc.write('machine localhost login {:s} password {:s}'
                        .format(self.user, self.password))
        self.sh.chmod(self._fnrc, 0o600)
        self._ftppool = FtpConnectionPool(self.sh, nrcfile=self._fnrc, ignoreproxy=True)

    def tearDown(self):
        self._ftppool.clear()
        del self._ftppool
        self.sh.rm(self._fnrc)
        super().tearDown()

    def new_ftp_client(self, delayed=True):
        return self._ftppool.deal('localhost', self.user, port=self.port, delayed=delayed)

    def test_ftp_client(self):
        with self.server():
            # Create #1
            ftpc1 = self.new_ftp_client()
            ftpc1_id = id(ftpc1)
            self.assertEqual(ftpc1.host, 'localhost')
            self.assertEqual(ftpc1.pwd(), '/')
            self.assertEqual(ftpc1.host, 'localhost')
            self.assertEqual(ftpc1.netpath('toto'),
                             'testlogin@localhost:toto')
            self.assertTrue(ftpc1.mkd('FTP1'))
            self.assertTrue(ftpc1.cd('FTP1'))
            self.assertEqual(ftpc1.pwd(), '/FTP1')
            self.assertTrue(ftpc1.put(FakeFp(), 'coucou1'))
            self.assertRemote('FTP1/coucou1', 'Coucou')
            # Create #2
            ftpc2 = self.new_ftp_client(delayed=False)
            self.assertIsNot(ftpc1, ftpc2)
            self.assertTrue(ftpc2.mkd('FTP2'))
            self.assertTrue(ftpc2.cd('FTP2'))
            # Release #1
            ftpc1.close()
            del ftpc1
            self.assertEqual(self._ftppool.poolsize, 1)
            # Create #3
            ftpc3 = self.new_ftp_client()
            ftpc3_id = id(ftpc3)
            self.assertIsNot(ftpc1_id, ftpc3_id)
            self.assertEqual(self._ftppool.poolsize, 0)
            # FTP #3rRestarted at the server root ?
            self.assertEqual(ftpc3.pwd(), '/')
            # And it works
            self.assertTrue(ftpc3.put(FakeFp(), 'coucou1'))
            self.assertRemote('coucou1', 'Coucou')
            # FTP #2 also works
            self.assertTrue(ftpc2.put(FakeFp(), 'coucou1'))
            self.assertRemote('FTP2/coucou1', 'Coucou')
            # Get with #3 stills works
            testget = io.BytesIO()
            self.assertTrue(ftpc3.get('FTP1/coucou1', testget))
            testget.seek(0)
            self.assertEqual(testget.read(), b'Coucou')
            # Release #2
            ftpc2.close()
            del ftpc2
            # Release #3
            ftpc3.close()
            del ftpc3
            self.assertEqual(self._ftppool.poolsize, 2)
            # Clear...
            self._ftppool.clear()
            self.assertEqual(self._ftppool.poolsize, 0)
