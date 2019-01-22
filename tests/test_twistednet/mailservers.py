# -*- coding: utf-8 -*-

"""
A set of servers.
"""

from __future__ import print_function, division, absolute_import, unicode_literals

import contextlib
import six.moves.queue as basequeue
import multiprocessing as mproc
import os
import signal
import sys
import time

from bronx.fancies import loggers

from zope.interface import implementer

from twisted.internet import defer, reactor
from twisted.mail import smtp

from twisted.cred.checkers import AllowAnonymousAccess
from twisted.cred.portal import IRealm
from twisted.cred.portal import Portal

if __name__ == '__main__':
    sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))

from .utils import wait_for_port

logger = loggers.getLogger(__name__)


@implementer(smtp.IMessageDelivery)
class MpQueueMessageDelivery:

    def __init__(self, queue):
        self._mpqueue = queue

    def receivedHeader(self, helo, origin, recipients):
        return b"Received: MpQueueMessageDelivery"

    def validateFrom(self, helo, origin):
        # All addresses are accepted
        return origin

    def validateTo(self, user):
        # Only messages directed to the "console" user are accepted.
        if user.dest.local == b"queue":
            return lambda: MpQueueMessage(self._mpqueue)
        raise smtp.SMTPBadRcpt(user)


@implementer(smtp.IMessage)
class MpQueueMessage:

    def __init__(self, queue):
        self._mpqueue = queue
        self.lines = []

    def lineReceived(self, line):
        self.lines.append(line)

    def eomReceived(self):
        self._mpqueue.put(list(self.lines))
        self.lines = None
        return defer.succeed(None)

    def connectionLost(self):
        # There was an error, throw away the stored lines
        self.lines = None


class MpQueueSMTPFactory(smtp.SMTPFactory):
    protocol = smtp.ESMTP

    def __init__(self, *a, **kw):
        mpqueue = kw.pop('mpqueue')
        smtp.SMTPFactory.__init__(self, *a, **kw)
        self.delivery = MpQueueMessageDelivery(mpqueue)

    def buildProtocol(self, addr):
        p = smtp.SMTPFactory.buildProtocol(self, addr)
        p.delivery = self.delivery
        return p


@implementer(IRealm)
class SimpleRealm:

    def requestAvatar(self, avatarId, mind, *interfaces):
        if smtp.IMessageDelivery in interfaces:
            return smtp.IMessageDelivery, MpQueueMessageDelivery(), lambda: None
        raise NotImplementedError()


class TestMessagesInterface(object):

    def __init__(self, queue):
        self._queue = queue

    def get(self):
        return self._queue.get()


class TestMailServer(object):

    def __init__(self, port):
        self.port = port

        userdb = AllowAnonymousAccess()
        self.portal = Portal(SimpleRealm)
        self.portal.registerChecker(userdb)

    def _server_task(self, queue):

        def nicestop(signum, frame):
            reactor.stop()

        f = MpQueueSMTPFactory(self.portal, mpqueue=queue)
        signal.signal(signal.SIGTERM, nicestop)
        reactor.listenTCP(self.port, f)
        reactor.run()
        return True

    def check_port(self):
        wait_for_port(self.port)

    @contextlib.contextmanager
    def __call__(self):
        q = mproc.Queue()
        p = mproc.Process(target=self._server_task, args=(q, ))
        p.start()
        try:
            self.check_port()
            logger.info('The test mailserver is ready on port: %d', self.port)
            yield TestMessagesInterface(q)
        finally:
            p.terminate()
            try:
                q.get(timeout=0.1)
            except basequeue.Empty:
                pass
            p.join()


if __name__ == '__main__':
    with TestMailServer(2525)() as messages:
        m = messages.get()
        print("\n".join([b.decode('ascii') for b in m]))
        time.sleep(0.5)
