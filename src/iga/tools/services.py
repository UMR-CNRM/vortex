#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
The module contains the service adapted to the actions present in the actions
module. We have an abstract class Services (inheritating from FootprintBase)
and 3 more classes inheritating from it: AlarmService, BdapService, RoutingService.
These classes are adpated to handle the data dedicated to the action to be
performed.
"""

#: No automatic export
__all__ = []

import logging
from logging.handlers import SysLogHandler

import socket
from StringIO import StringIO

import vortex
import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.tools.date import Date
from vortex.tools.services import Service

#TODO devrait dépendre d'un objet TARGET
LOGIN_NODES = [
    x + str(y)
    for x in ('prolixlogin', 'beaufixlogin', )
    for y in range(6)
]


class LogFacility(int):
    """
    Attribute for SysLogHandler facility value, could be either a valid ``int``
    or a logging name such as ``log_local7`` or ``local7``.
    """
    def __new__(cls, value):
        if type(value) is str:
            value = value.lower()
            if value.startswith('log_'):
                value = value[4:]
            try:
                value = SysLogHandler.facility_names[value]
            except KeyError:
                logger.error('Could not get a SysLog value for name ' + value)
                raise
        if value not in SysLogHandler.facility_names.values():
            raise ValueError('Not a SysLog facility value: ' + str(value))
        return int.__new__(cls, value)

    def name(self):
        for s, n in SysLogHandler.facility_names.iteritems():
            if self == n:
                return s
        raise ValueError('Not a SysLog facility value: ' + str(self))


class RemoteCommandProxy(footprints.FootprintBase):
    """
    Remote execution via ssh
    """
    _collector = ('miscellaneous',)
    _footprint = dict(
        info = 'Remote command proxy',
        attr = dict(
            kind = dict(
                values = ['ssh_proxy'],
                alias  = ('remotecommand',),
            ),
            remote = dict(
                values = ['login', 'transfert'],
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Remote command proxy init %s', self.__class__)
        super(RemoteCommandProxy, self).__init__(*args, **kw)
        self._sh = sessions.system()

    def node(self):
        """node name for this kind of remote execution"""
        t = self._sh.target()
        inikey = 'services:' + self.remote + 'node'
        return t.get(inikey, 'localhost')

    def execute(self, command):
        rc = self._sh.spawn(
            ('/usr/bin/ssh', '-x', self.node(), command),
            shell=False,
            output=False)
        return rc


class AlarmService(Service):
    """
    Class responsible for handling alarm data.
    This class should not be called directly.
    """

    _abstract = True
    _footprint = dict(
        info = 'Alarm services class',
        attr = dict(
            kind = dict(
                values   = ['sendalarm']
            ),
            message = dict(
                alias    = ('content',)
            ),
            facility = dict(
                type     = LogFacility,
                optional = True,
                default  = SysLogHandler.LOG_LOCAL3,
            ),
            alarmfmt = dict(
                optional = True,
                default  = None,
            ),
        )
    )

    def get_syslog(self):
        pass

    def get_logger_action(self):
        """
        Define a SysLogHandler to broadcast the alarm.
        Return the actual logging method.
        """

        # create the syslog handler
        hand = self.get_syslog()
        hand.setFormatter(logging.Formatter(self.alarmfmt))
        logger.addHandler(hand)

        return getattr(logger, self.level, logger.warning)

    def get_message(self):
        """Return the actual message to log."""
        return self.message

    def __call__(self):
        """Main action: pack the message to the actual logger action."""
        logmethod = self.get_logger_action()
        return logmethod(self.get_message())


class AlarmProxyService(AlarmService):
    """
    Class responsible for handling alarm data through the remote
    unix "logger" command invocation (mandatory on non-login nodes)
    This class should not be called directly.
    """
    _footprint = dict(
        info = 'Alarm Proxy Service',
        attr = dict(
            hostname = dict(
                outcast = LOGIN_NODES,
            ),
        )
    )

    def get_syslog(self):
        """Return an in-memory handler"""
        self.buffer = StringIO()
        self.handler = logging.StreamHandler(self.buffer)
        return self.handler

    def __call__(self):
        """Main action: pack the message to the actual logger action."""

        # send to the logger as usual
        super(AlarmProxyService, self).__call__()

        # get the formatted message from the logger
        self.handler.flush()
        self.buffer.flush()
        message = self.buffer.getvalue().rstrip('\n')
        self.buffer.truncate(0)

        # send it to the unix 'logger' command on a login node
        command = "logger -p {}.{} '{}'".format(
            self.facility.name(),
            self.level,
            message)
        rcp = RemoteCommandProxy(kind='ssh_proxy', remote='login')
        rc = rcp.execute(command)
        if not rc:
            logger.warning("Remote execution returns" + rc)
        return rc


class AlarmLogService(AlarmService):
    """
    Class responsible for handling alarm data through domain socket.
    This class should not be called directly.
    """

    _footprint = dict(
        info = 'Alarm Log Service',
        attr = dict(
            address = dict(
                optional = True,
                default  = None,
                access   = 'rwx',
            ),
            hostname = dict(
                values = LOGIN_NODES,
            ),
        )
    )

    def get_syslog(self):
        """Return a SysLog on domain socket given by ``address`` attribute."""
		# TODO les objets services ne pourraient -ils pas avoir un accès sh
        if self.address is None:
            self.address = vortex.ticket().system().default_syslog
        return SysLogHandler(self.address, self.facility, None)


class AlarmRemoteService(AlarmService):
    """
    Class responsible for handling alarm data through domain socket.
    This class should not be called directly.
    """

    _footprint = dict(
        info = 'Alarm services class',
        attr = dict(
            syshost = dict(
                optional = True,
                default = 'localhost',
            ),
            sysport = dict(
                type     = int,
                optional = True,
                default  = 514,
            ),
            socktype = dict(
                type     = int,
                optional = True,
                default  = socket.SOCK_DGRAM,
            ),
            hostname = dict(
                values = LOGIN_NODES,
            ),
        )
    )

    def get_syslog(self):
        """Return a SysLog on remote socket given by ``syshost`` and ``sysport`` attributes."""
        return SysLogHandler((self.syshost, self.sysport), self.facility, self.socktype)


class BdapService(Service):
    """
    Class responsible for handling bdap data.
    This class should not be called directly.
    """
    _footprint = dict(
        info = 'Bdap services class',
        attr = dict(
            kind = dict(
                values   = ['routing' ]
            ),
            domain = dict(),
            localname = dict(
                optional = True,
                default  = None
            ),
            extra = dict(
                optional = True,
                default  = '0'
            ),
            srcdirectory = dict(),
            term = dict(),
            hour = dict(),
            bdapid = dict(),
            source = dict(),
            sendbdap = dict(
                optional = True,
                default  = 'envoi_bdap',
            )
        )
    )

    def get_cmdline(self):
        """
        Build and return the command line which will be executed by the current
        system object available associated with the service.
        """
        return [ str(k) for k in (
            self.sendbdap,
            self.domain,
            self.extra,
            self.term,
            self.hour,
            self.bdapid,
            self.sh.path.join(self.srcdirectory, self.localname or '')
        )]

    def __call__(self):
        """Main action: spawn the external router tool."""
        return self.sh.spawn(self.get_cmdline(), output=False)


class RoutingService(Service):
    """
    Class responsible for handling routing data.
    This class should not be called directly.
    """
    _footprint = dict(
        info = 'Routing services class',
        attr = dict(
            action_type = dict(
                values = [ 'routing' ]
            ),
            localname = dict(
                default = None
            ),
            quality = dict(
                optional = True,
                default = '0',
                values = [ '0', ]
            ),
            srcdirectory = dict(),
            term = dict(),
            productid = dict(),
            source = dict(),
            scalar = dict(
                optional = True,
                type = bool,
                default = False
            ),
            producer = dict(
                optional = True,
                default = 'fpe'
            ),
            date = dict(
                type = Date
            ),
            path_exec = dict(
                optional = True,
                default = '/ch/mxpt/mxpt001/util/agt/'
            ),
            binary = dict(
                optional = True,
                default = '[scalar]',
                remap = dict(
                    False = 'router_pe',
                    True = 'router_pe_sx'
                )
            )
        )
    )

    def get_cmdline(self):
        """
        Build and return the command line which will be executed by the current
        system object available associated with the service.
        """
        localname = self.localname
        srcdirectory = self.srcdirectory
        productid = self.productid
        producer = self.producer
        term = self.term
        date = self.date
        quality = self.quality
        #localname, srcdirectory, producer, productid, term, date, quality = self._mess_data
        #/ch/mxpt/mxpt001/util/agt/router_pe_sx
        #/utmp/nqs.53009.kumo-batch/COUPL000.r0 2088000000 -p fpe -n 2088 -e
        #000000 -d 20120710000000 -q 0
        path_exec = self.path_exec
        exec_name = self.sh.path.join(path_exec, self.binary)
        popenargs = "%s/%s %s -p %s -n %s -e %s -d %s -q %s" % (
            srcdirectory, localname, productid, producer, productid[0:4], term,
            date, quality )
        return [ exec_name + ' ' + popenargs ]

    def __call__(self):
        """docstring for route"""
        cmdline = self.get_cmdline()
        return self.sh.spawn(cmdline, shell=True, output=False)

