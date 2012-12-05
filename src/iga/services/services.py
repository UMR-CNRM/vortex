#!/bin/env python
# -*- coding: utf-8 -*-

"""
The module contains the specific services adapted to the actions
performed int the IGA operational context :

  * AlarmService
  * SendbdapService
  * RoutingService

These classes are adpated to handle the data dedicated to the action to be
performed.
"""

#: No automatic export
__all__ = []

import os, sys, re

import logging
from vortex import sessions
from logging.handlers import SysLogHandler
from vortex.tools.date import Date
from vortex.tools.services import Service


class AlarmService(Service):
    """Class responsible for handling alarm data. You never call this class directly."""

    _footprint = dict(
        info = 'Alarm services class',
        attr = dict(
            action_type = dict(
                values = ['alarm']
            ),
            message = dict(),
            file = dict(
                optional = True,
            ),
            level = dict(
                optional = True,
                default = 'info',
                values = ['info', 'warning', 'error', 'critical']
            ),
            log = dict(
                optional = True,
                default = '/dev/log'
            ),
            facility = dict(
                optional = True,
                default = 'LOG_LOCAL2'
            ),
            format = dict(
                optional = True,
                default = None
            )
        )
    )

    def get_loggerservice(self):
        """docstring for add_loggerservice"""
        log = self.log
        facility = self.facility
        format = self.format
        level = self.level
        #log, facility, format, level = self._mess_data
        facility = getattr(SysLogHandler, facility, None)
        # create the logger object
        logger = logging.getLogger()
        # create the handlers
        hand = SysLogHandler(
            log,
            facility
        )
        # create the format
        fmt = logging.Formatter(format)
        # set the format of the handler
        hand.setFormatter(fmt)
        # add the handler to the logger
        logger.addHandler(hand)
        hook_levels = AlarmService.authvalues('level')
        return_func = dict(
            zip(
                 hook_levels,
                (logger.info, logger.warning, logger.error, logger.critical)
            )
        )
        return return_func[level]

    def get_message(self):
        return self.message


class BdapService(Service):
    """Class responsible for handling bdap data. You never call this class directly."""

    _footprint = dict(
        info = 'Bdap services class',
        attr = dict(
            action_type = dict(
                values = ['sendbdap', ]
            ),
            domain = dict(),
            localname = dict(
                optional = True,
                default = None
            ),
            extra = dict(
                optional = True,
                default = '0'
            ),
            srcdirectory = dict(),
            term = dict(),
            hour = dict(),
            bdapid = dict(),
            source = dict(),
            scalar = dict(
                optional = True,
                type = bool,
                default = False
            )
        )
    )

    def get_cmd_line(self):
        """
        Build and return the command line which will be executed by the current
        system object available associated with the service.
        """
        #Patch to determine the type of the computer: vectorial or scalar
        scalar = self.scalar
        hour = self.hour
        localname = self.localname
        srcdirectory = self.srcdirectory
        domain = self.domain
        extra = self.extra
        term = self.term
        bdapid = self.bdapid
        source = self.source
        #localname, srcdirectory, domain, extra, term, hour, bdapid, source = self._mess_data
        #send_bdap ${machine_envoi} ${domaine} $type $echagt $RESEAU $numpe
        #${REP_ENV}/${FICENV}
        if scalar:
            popenargs = "%s %s %s %s %s %s/%s" % (
                domain, extra, term, hour, bdapid, srcdirectory, localname )
            exec_name = 'envoi_bdap_tx'
        else:
            popenargs = "%s %s %s %s %s %s %s/%s" % (
                source, domain, extra, term, hour, bdapid, srcdirectory, localname )
            exec_name = 'send_bdap'
        return [ exec_name + ' ' + popenargs ]

    def get_system(self):
        return sessions.system()


class RoutingService(Service):
    """Class responsible for handling routing data. You never call this class directly."""

    _footprint = dict(
        info = 'Routing services class',
        attr = dict(
            action_type = dict(
                values = ['route', ]
            ),
            localname = dict(),
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

    def get_cmd_line(self):
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
        exec_name = os.path.join(path_exec, self.binary)
        popenargs = "%s/%s %s -p %s -n %s -e %s -d %s -q %s" % (
            srcdirectory, localname, productid, producer, productid[0:4], term,
            date, quality )
        return [ exec_name + ' ' + popenargs ]

    def get_system(self):
        return sessions.system()

