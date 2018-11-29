#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import io
import six
import socket
import sys

from bronx.fancies import loggers
import footprints

from vortex import sessions
from vortex.util import config

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class ServerSyncTool(footprints.FootprintBase):
    """
    :class:`ServerSyncTool` classes are in charge of interactions between the
    main process and the server.
    """

    _abstract  = True
    _collector = ('serversynctool',)
    _footprint = dict(
        info = 'Abstract Server Synchronisation Tool',
        attr = dict(
            method = dict(
            ),
            medium = dict(
                optional    = True,
            ),
            raiseonexit = dict(
                type        = bool,
                optional    = True,
                default     = True
            ),
            checkinterval = dict(
                type        = int,
                optional    = True,
                default     = 10,
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Server Synchronisation Tool init %s', self.__class__)
        self._check_callback = lambda: True
        super(ServerSyncTool, self).__init__(*args, **kw)

    def set_servercheck_callback(self, cb):
        """Set a callback method that will be called to check the server state."""
        self._check_callback = cb

    def trigger_wait(self):
        """Ask the SyncTool to wait for a request."""
        raise NotImplementedError

    def trigger_run(self):
        """Indicate that the main process is ready for the server to run the next step.

        It then wait for the server to complete this step.
        """
        raise NotImplementedError

    def trigger_stop(self):
        """Ask the server to stop (gently)."""
        raise NotImplementedError


class ServerSyncSimpleSocket(ServerSyncTool):
    """Practical implementation of a ServerSyncTool that relies on sockets.

    A script is created (its name is defined by the *medium* attribute): it
    will be called by the server process before starting any computations. This
    script and the main process communicate using standard UNIX sockets (through
    the socket package).
    """

    _footprint = dict(
        info = 'Server Synchronisation Tool that uses a Socket',
        attr = dict(
            method = dict(
                values      = ['simple_socket'],
            ),
            medium = dict(
                optional    = False,
            ),
            tplname = dict(
                optional    = True,
                default     = '@servsync-simplesocket.tpl',
            ),
        )
    )

    def __init__(self, *args, **kw):
        super(ServerSyncSimpleSocket, self).__init__(*args, **kw)
        # Create the sockect
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.bind((socket.getfqdn(), 0))
        self._socket.listen(1)
        self._socket.settimeout(self.checkinterval)
        # Current connection
        self._socket_conn = None
        # Create the script that will be called by the server
        t = sessions.current()
        tpl = config.load_template(t, self.tplname)
        with io.open(self.medium, 'wb') as fd:
            fd.write(tpl.substitute(
                python  = sys.executable,
                address = self._socket.getsockname(),
            ))
        t.sh.chmod(self.medium, 0o555)

    def __del__(self):
        if self._socket_conn is not None:
            logger.warning("The socket is still up... that's odd.")
        t = sessions.current()
        if t.sh.path.exists(self.medium):
            t.sh.remove(self.medium)
        super(ServerSyncSimpleSocket, self).__del__()

    def _command(self, mess):
        """ Send a command (a string) to the server; wait for a response """
        if self._socket_conn is not None:
            logger.info('Sending "%s" to the server.', mess)
            # NB: For send/recv, the settimeout also applies...
            self._socket_conn.send(six.binary_type(mess))
            repl = str(self._socket_conn.recv(255))
            logger.info('Server replied "%s".', repl)
            if repl != 'OK':
                raise ValueError(mess + ' failed')
            self._socket_conn.close()
            self._socket_conn = None
            return True
        else:
            # This should not happen ! If we are sitting here, it's most likely
            # that the main process received a signal like SIGTERM...
            return False

    def trigger_wait(self):
        logger.info('Waiting for the server to complete')
        while self._socket_conn is None and self._check_callback():
            try:
                self._socket_conn, addr = self._socket.accept()  # @UnusedVariable
            except socket.timeout:
                logger.debug('Socket accept timed-out: checking for the server...')
                self._socket_conn = None
        if self._socket_conn is None:
            if self.raiseonexit:
                raise IOError('Apparently the server died.')
            else:
                logger.info('The server stopped.')
        else:
            logger.info('The server is now waiting')

    def trigger_run(self):
        # Tell the server that everything is ready
        self._command('STEP')
        # Wait for the server to complete its work
        self.trigger_wait()

    def trigger_stop(self):
        return self._command('STOP')
