# -*- coding: utf-8 -*-

"""
A set of servers.
"""

from __future__ import print_function, division, absolute_import, unicode_literals

import contextlib
import itertools
import multiprocessing as mproc
import os
import signal
import sys
import time

from bronx.fancies import loggers

from twisted.protocols.ftp import FTP, FTPFactory, FTPRealm, AUTH_FAILURE
from twisted.cred.portal import Portal
from twisted.cred.checkers import InMemoryUsernamePasswordDatabaseDontUse
from twisted.internet import reactor

if __name__ == '__main__':
    sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))

from .utils import wait_for_port

logger = loggers.getLogger(__name__)


class TwistedBrokenFTP(FTP):

    def __init__(self, *kargs, **kwargs):
        super(TwistedBrokenFTP, self).__init__(*kargs, **kwargs)
        self.pass_ticker = itertools.repeat(True)
        self.retr_ticker = itertools.repeat(True)
        self.stor_ticker = itertools.repeat(True)

    def ftp_PASS(self, password):
        what = next(self.pass_ticker)
        logger.info('ftp_PASS: ticker returned %s.', what)
        if what is True:
            return super(TwistedBrokenFTP, self).ftp_PASS(password)
        else:
            return (what, )

    def ftp_RETR(self, path):
        what = next(self.retr_ticker)
        logger.info('ftp_RETR: ticker returned %s.', what)
        if what is True:
            return super(TwistedBrokenFTP, self).ftp_RETR(path)
        else:
            return (what, )

    def ftp_STOR(self, path):
        what = next(self.stor_ticker)
        logger.info('ftp_STOR: ticker returned %s.', what)
        if what is True:
            return super(TwistedBrokenFTP, self).ftp_STOR(path)
        else:
            return (what, )


class TwistedBrokenFTPFactory(FTPFactory):

    protocol = TwistedBrokenFTP

    _pass_ticker_i = None
    _retr_ticker_i = None
    _stor_ticker_i = None

    @property
    def _pass_ticker(self):
        if self._pass_ticker_i is None:
            self._pass_ticker_i = itertools.chain(self.pass_seq,
                                                  itertools.repeat(True))
        return self._pass_ticker_i

    @property
    def _retr_ticker(self):
        if self._retr_ticker_i is None:
            self._retr_ticker_i = itertools.chain(self.retr_seq,
                                                  itertools.repeat(True))
        return self._retr_ticker_i

    @property
    def _stor_ticker(self):
        if self._stor_ticker_i is None:
            self._stor_ticker_i = itertools.chain(self.stor_seq,
                                                  itertools.repeat(True))
        return self._stor_ticker_i

    def buildProtocol(self, addr):
        p = FTPFactory.buildProtocol(self, addr)
        p.wrappedProtocol.pass_ticker = self._pass_ticker
        p.wrappedProtocol.retr_ticker = self._retr_ticker
        p.wrappedProtocol.stor_ticker = self._stor_ticker
        return p


class TestFTPServer(object):

    def __init__(self, port, serverroot, user, password,
                 pass_seq = (), retr_seq = (), stor_seq = ()):
        self.port = port
        self.serverroot = serverroot
        self.pass_seq = pass_seq
        self.retr_seq = retr_seq
        self.stor_seq = stor_seq

        userdb = InMemoryUsernamePasswordDatabaseDontUse()
        userdb.addUser(user, password)
        self.portal = Portal(FTPRealm(os.path.realpath(serverroot),
                                      userHome=os.path.realpath(serverroot)),
                             [userdb, ])

    def _server_task(self):

        def nicestop(signum, frame):
            reactor.stop()

        f = TwistedBrokenFTPFactory(self.portal)
        f.pass_seq = self.pass_seq
        f.retr_seq = self.retr_seq
        f.stor_seq = self.stor_seq
        signal.signal(signal.SIGTERM, nicestop)
        reactor.listenTCP(self.port, f)
        reactor.run()
        return True

    def check_port(self):
        wait_for_port(self.port)

    @contextlib.contextmanager
    def __call__(self):
        p = mproc.Process(target=self._server_task)
        p.start()
        try:
            self.check_port()
            logger.info('The test FTP server is ready on port: %d', self.port)
            yield
        finally:
            p.terminate()
            p.join()


if __name__ == '__main__':
    import io
    import shutil
    try:
        os.mkdir('testlogin')
        with io.open('testlogin/testfile', 'w') as fhtf:
            fhtf.write("TestFile1")
        with TestFTPServer(2121, '.', 'testlogin', 'aqmp',
                           pass_seq=(AUTH_FAILURE, ))():
            time.sleep(30)
    finally:
        shutil.rmtree('testlogin')
