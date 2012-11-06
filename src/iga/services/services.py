#!/bin/env python
# -*- coding: utf-8 -*-

r"""
The module contains the service adapted to the actions present in the actions
module. We have an abstract class Services (inheritating from BFootprint)
and 4 more classes inheritating from it :
    - MailServices, AlarmServices, SendbdapServices and RoutingServices.
These classes are adpated to handle the data dedicated to the action to be
performed.
"""



import os, sys, re

import logging
from vortex import sessions
from logging.handlers import SysLogHandler
from vortex.syntax import BFootprint
from vortex.tools.date import Date
from vortex.utilities.catalogs import ClassesCollector, cataloginterface

class Services(BFootprint):
    """Abstract base class for services"""

    _footprint = dict(
        info = 'Abstract services class',
        )

    def get_action_type(self):
        return self.action_type

    @classmethod
    def realkind(self):
        return 'services'


class MailServices(Services):
    r"""
    Class responsible for handling email data. You never call this class
    directly.
    """
    _footprint = dict(
        info = 'Mail services class',
        attr = dict(
            action_type = dict(
                optional = True,
                type = str,
                default = 'mail',
                values = ['mail', ]
            ),
            sender = dict(
                optional = False,
                type = str,
            ),
            receiver = dict(
                optional = False,
                type = str
            ),
            message = dict(
                optional = True,
                type = str
            ),
            file = dict(
                optional = True,
                type = str,
            ),
            subject = dict(
                optional = False,
                type = str
            ),
            level = dict(
                optional = True,
                type = str,
                default = 'info',
                values = ['info', 'error', 'warning', 'critical']
            )
        )
    )

    def get_data(self):
        return (self.receiver, self.sender, self.subject, self.level)

    def get_message(self):
        return self.message

    def get_file(self):
        file_to_message = self.file
        tmp = open(file_to_message, 'r')
        message = tmp.read()
        tmp.close()
        return message


class AlarmServices(Services):
    r"""
    Class responsible for handling alarm data. You never call this class
    directly.
    """

    _footprint = dict(
        info = 'Alarm services class',
        attr = dict(
            action_type = dict(
                optional = False,
                type = str,
                default = 'alarm',
                values = ['alarm', ]
            ),
            message = dict(
                optional = False,
                type = str
            ),
            file = dict(
                optional = True,
                type = str,
            ),
            level = dict(
                optional = True,
                type = str,
                default = 'info',
                values = ['info', 'warning', 'error', 'critical']
            ),
            log = dict(
                optional = True,
                type = str,
                default = '/dev/log'
            ),
            facility = dict(
                optional = True,
                type = str,
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
        hook_levels = AlarmServices.authvalues('level')
        return_func = dict(
            zip(
                 hook_levels,
                (logger.info, logger.warning, logger.error, logger.critical)
            )
        )
        return return_func[level]

    def get_message(self):
        return self.message

class BdapServices(Services):
    r"""
    Class responsible for handling bdap data. You never call this class
    directly.
    """
    _footprint = dict(
        info = 'Bdap services class',
        attr = dict(
            action_type = dict(
                optional = False,
                type = str,
                default = 'sendbdap',
                values = ['sendbdap', ]
            ),
            domain = dict(
                optional = False,
                type = str
            ),
            localname = dict(
                optional = True,
                type = str,
                default = None
            ),
            extra = dict(
                optional = True,
                type = str,
                default = '0'
            ),
            srcdirectory = dict(
                optional = False,
                type = str
            ),
            term = dict(
                optional = False,
                type = str
            ),
            hour = dict(
                optional = False,
                default = None
            ),
            bdapid = dict(
                optional = False,
                type = str,
            ),
            source = dict(
                optional = False,
                type = str
            ),
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

class RoutingServices(Services):
    r"""
    Class responsible for handling routing data. You never call this class
    directly.
    """
    _footprint = dict(
        info = 'Routing services class',
        attr = dict(
            action_type = dict(
                optional = False,
                type = str,
                values = ['route', ]
            ),
            localname = dict(
                optional = False,
                type = str,
                default = None
            ),
            quality = dict(
                optional = True,
                type = str,
                default = '0',
                values = [ '0', ]
            ),
            srcdirectory = dict(
                optional = False,
                type = str
            ),
            term = dict(
                optional = False,
                type = str
            ),
            productid = dict(
                optional = False,
                type = str,
            ),
            source = dict(
                optional = False,
                type = str
            ),
            scalar = dict(
                optional = True,
                type = bool,
                default = False
            ),
            producer = dict(
                optional = True,
                type = str,
                default = 'fpe'
            ),
            date = dict(
                optional = False,
                type = Date
            ),
            path_exec = dict(
                optional = True,
                type = str,
                default = '/ch/mxpt/mxpt001/util/agt/'
            ),
            binary = dict(
                optional = True,
                type = str,
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


class ServicesCatalog(ClassesCollector):
    """Class in charge of collecting :class:`MpiTool` items."""

    def __init__(self, **kw):
        logging.debug('Services catalog init %s', self)
        cat = dict(
            remod = re.compile(r'.*\.services'),
            classes = [ Services ],
            itementry = Services.realkind()
        )
        cat.update(kw)
        super(ServicesCatalog, self).__init__(**cat)

    @classmethod
    def tablekey(cls):
        return 'services'


cataloginterface(sys.modules.get(__name__), ServicesCatalog)

