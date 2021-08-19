# -*- coding: utf-8 -*-

"""
Base classes for unittests that require an FTP server.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import io
import tempfile
import unittest

import vortex

from . import has_ftpservers
from .utils import get_ftp_port_number


@unittest.skipUnless(has_ftpservers(), 'FTP Server')
class FtpBasedTestCase(unittest.TestCase):

    _FTPLOGLEVEL = 'ERROR'

    def setUp(self):
        self.sh = vortex.sh()
        # Temp directory
        self.tdir = tempfile.mkdtemp(prefix='ftp_testdir_')
        self._oldpwd = self.sh.getcwd()
        self.sh.chdir(self.tdir)
        # Cocoon the ftp server directory
        self.udir = self.sh.path.join(self.tdir, 'testlogin')
        self.sh.mkdir(self.udir)
        self.user = 'testlogin'
        self.password = 'aqmp'
        # FTP Config
        self.port = get_ftp_port_number()
        self.configure_ftpserver()
        # Make sure FTP proxies are ignored during tests
        del self.sh.env['FTP_PROXY']
        del self.sh.env['VORTEX_FTP_PROXY']

    def configure_ftpserver(self):
        from .ftpservers import TestFTPServer, logger
        logger.setLevel(self._FTPLOGLEVEL)
        self.server = TestFTPServer(self.port, self.tdir,
                                    self.user, self.password)

    def tearDown(self):
        # Do some cleaning
        self.sh.chdir(self._oldpwd)
        self.sh.rmtree(self.tdir)

    def assertFile(self, path, content, binary=False):
        self.assertTrue(self.sh.path.exists(path),
                        msg="Testing existence of: {:s}".format(path))
        with io.open(path, 'rb' if binary else 'r') as fhr:
            self.assertEqual(fhr.read(), content)

    def assertRemote(self, path, content, binary=False):
        where = self.sh.path.join(self.udir, path)
        self.assertFile(where, content, binary=binary)


class NetrcFtpBasedTestCase(FtpBasedTestCase):

    def setUp(self):
        super(NetrcFtpBasedTestCase, self).setUp()
        # Fake NetRC
        self._fnrc = self.sh.path.join(self.tdir, 'fakenetrc')
        with io.open(self._fnrc, 'w') as fhnrc:
            fhnrc.write('machine localhost login {:s} password {:s}'
                        .format(self.user, self.password))
        self.sh.chmod(self._fnrc, 0o600)


class MtoolNetrcFtpBasedTestCase(NetrcFtpBasedTestCase):

    def setUp(self):
        super(MtoolNetrcFtpBasedTestCase, self).setUp()
        # Deal with the MTOOLDIR variable
        self._old_mtooldir = self.sh.env.get('MTOOLDIR', None)
        self.sh.env['MTOOLDIR'] = self.sh.path.join(self.udir, 'mtool')
        self.sh.mkdir(self.sh.env['MTOOLDIR'])

    def tearDown(self):
        super(MtoolNetrcFtpBasedTestCase, self).tearDown()
        if self._old_mtooldir:
            self.sh.env['MTOOLDIR'] = self._old_mtooldir
        else:
            del self.sh.env['MTOOLDIR']
