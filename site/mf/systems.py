#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This package handles some common targets used at Meteo France.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import ftplib
import six
import socket
import uuid

import footprints

from vortex.tools.targets import Target
from vortex.tools.prestaging import PrestagingTool

#: No automatic export
__all__ = []

logger = footprints.loggers.getLogger(__name__)


class MeteoBull(Target):
    """Bull Computer."""

    _abstract = True
    _footprint = dict(
        info = 'Bull Supercomputer at Meteo France',
        attr = dict(
            sysname = dict(
                values = [ 'Linux' ]
            ),
            inifile = dict(
                default = '@target-[inetname].ini',
            )
        ),
        priority = dict(
            level = footprints.priorities.top.TOOLBOX
        )
    )

    def generic(self):
        """Generic name is inetname suffixed with ``fe`` or ``cn``."""
        if 'login' in self.hostname or 'transfer' in self.hostname:
            return self.inetname + 'fe'
        else:
            return self.inetname + 'cn'


class Beaufix(MeteoBull):
    """Beaufix Computer at Meteo-France."""

    _footprint = dict(
        info = 'Bull Beaufix Supercomputer at Meteo France',
        attr = dict(
            hostname = dict(
                values = (
                    [ x + str(y) for x in ('beaufix',) for y in range(1836) ] +
                    [ x + str(y) for x in ('beaufixlogin',) for y in range(6) ] +
                    [ x + str(y) for x in ('beaufixtransfert',) for y in range(8) ] )
            ),
            inetname = dict(
                default = 'beaufix',
                values  = ['beaufix']
            ),
        )
    )


class Prolix(MeteoBull):
    """Prolix Computer at Meteo-France."""

    _footprint = dict(
        info = 'Bull Prolix Supercomputer at Meteo France',
        attr = dict(
            hostname = dict(
                values = (
                    [ x + str(y) for x in ('prolix',) for y in range(1800) ] +
                    [ x + str(y) for x in ('prolixlogin',) for y in range(6) ] +
                    [ x + str(y) for x in ('prolixtransfert',) for y in range(8) ] )
            ),
            inetname = dict(
                default = 'prolix',
                values  = ['prolix']
            ),
        )
    )


class Aneto(Target):
    """Aneto cluster at Meteo-France CNRM."""

    _footprint = dict(
        info='Aneto Cluster at CNRM',
        attr=dict(
            hostname=dict(
                values=[x + str(y) for x in ('ncx',) for y in range(30)] +
                [x + str(y) for x in ('ntx',) for y in range(6)]
            ),
            inetname=dict(
                default='aneto',
                values=['aneto']
            ),
            inifile=dict(
                optional=True,
                default='@target-aneto.ini',
            ),
        ),
        priority = dict(
            level = footprints.priorities.top.TOOLBOX
        )
    )


class MeteoSoprano(Target):
    """A Soprano Server."""

    _abstract = True
    _footprint = dict(
        info = 'A Soprano Server at Meteo France',
        attr = dict(
            sysname = dict(
                values = [ 'Linux' ]
            ),
        ),
        priority = dict(
            level = footprints.priorities.top.TOOLBOX
        )
    )


class MeteoSopranoDevRH6(MeteoSoprano):
    """ A Soprano Development Server running CentOS 6."""

    _footprint = dict(
        info = 'A Soprano Development Server running CentOS 6',
        attr = dict(
            hostname = dict(
                values = ['alose', 'pagre', 'rason', 'orphie'],
            ),
            inifile=dict(
                optional=True,
                default='@target-soprano_dev_rh6.ini',
            ),
        ),
    )

    def generic(self):
        """Generic name to be used in acess paths"""
        return 'soprano_dev_rh6'


class HendrixPrestagingTool(PrestagingTool):

    _footprint = dict(
        info = "Process Hendrix's pre-staging requests.",
        attr = dict(
            issuerkind = dict(
                values = ['archivestore', ]
            ),
            storage = dict(
                values = ['hendrix', 'hendrix.meteo.fr'],
                remap = dict(hendrix='hendrix.meteo.fr')
            ),
            scheme = dict(),
            stagedir = dict(
                optional = True,
                default = '/DemandeMig/ChargeEnEspaceRapide',
            ),
            logname = dict(
                optional = True
            )
        )
    )

    def flush(self, email=None):
        """Acutally send the pre-staging request to Hendrix."""
        # Build the target
        request = []
        if email is not None:
            request.append("#MAIL=" + email)
        request.extend(self.items())
        # Send this stuff to hendrix
        request_filename = '.'.join([self.logname or 'unknownuser',
                                     'stagereq',
                                     uuid.uuid4().hex[:16],
                                     'MIG'])
        request_data = six.StringIO()
        request_data.write('\n'.join(request))
        request_data.seek(0)
        try:
            ftp = self.system.ftp(self.storage, logname=self.logname)
        except (ftplib.all_errors, socket.error) as e:
            logger.error('Prestaging to %s: unable to connect: %s', self.storage, str(e))
            ftp = None
        if ftp:
            try:
                rc = ftp.cd(self.stagedir)
            except (IOError, ftplib.all_errors) as e:
                logger.error('Prestaging to %s: error with "cd": %s', self.storage, str(e))
                rc = False
            if rc:
                try:
                    ftp.put(request_data, request_filename)
                except (IOError, ftplib.all_errors) as e:
                    logger.error('Prestaging to %s: error with "put": %s', self.storage, str(e))
                    rc = False
            ftp.close()
            return rc
        else:
            return False
