#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This package handles some common targets used at Meteo France.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import six
import ftplib
import uuid

from bronx.fancies import loggers
import footprints

from vortex.tools.targets import Target
from vortex.tools.prestaging import PrestagingTool

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


# Any kind of DSI's Supercomputer

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
            inetname = dict(
                default = 'beaufix',
                values  = ['beaufix']
            ),
        ),
        only = dict(
            hostname = footprints.FPRegex(r'beaufix(?:login|transfert)?\d+(?:\.|$)')
        )
    )


class Prolix(MeteoBull):
    """Prolix Computer at Meteo-France."""

    _footprint = dict(
        info = 'Bull Prolix Supercomputer at Meteo France',
        attr = dict(
            inetname = dict(
                default = 'prolix',
                values  = ['prolix']
            ),
        ),
        only = dict(
            hostname = footprints.FPRegex(r'prolix(?:login|transfert)?\d+(?:\.|$)')
        )
    )


# Any kind of DSI's Soprano servers

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
                values = ['alose', 'pagre', 'rason', 'orphie', 'guppy'],
            ),
            inifile = dict(
                optional=True,
                default='@target-soprano_dev_rh6.ini',
            ),
        ),
    )

    def generic(self):
        """Generic name to be used in acess paths"""
        return 'soprano_dev_rh6'


# Any kind of CNRM server or workstation

class UmrCnrmTarget(Target):
    """Restrict the FQDN to cnrm.meteo.fr."""

    _abstract = True
    _footprint = dict(
        info='Aneto Cluster at CNRM',
        only = dict(
            fqdn = [footprints.FPRegex(r'.+\.cnrm\.meteo\.fr$'),
                    footprints.FPRegex(r'.+\.umr-cnrm\.fr$')]
        ),
        priority = dict(
            level = footprints.priorities.top.TOOLBOX
        )
    )


class Aneto(UmrCnrmTarget):
    """Aneto cluster at Meteo-France CNRM."""

    _footprint = dict(
        info='Aneto Cluster at CNRM',
        attr=dict(
            inetname=dict(
                default = 'aneto',
                values = ['aneto']
            ),
            inifile=dict(
                default = '@target-[inetname].ini',
            ),
        ),
        only = dict(
            hostname = footprints.FPRegex(r'n[ctx]\d+(?:\.|$)')
        )
    )


class CnrmLinuxWorkstation(UmrCnrmTarget):
    """Aneto cluster at Meteo-France CNRM."""

    _footprint = dict(
        info='Aneto Cluster at CNRM',
        attr=dict(
            sysname = dict(
                values = [ 'Linux' ]
            ),
            inifile=dict(
                default = '@target-cnrmworkstation.ini',
            ),
        ),
        only = dict(
            hostname = footprints.FPRegex(r'[lp]x\w+(?:\.|$)')
        )
    )

    def cache_storage_alias(self):
        """The tag used when reading Cache Storage configuration files."""
        return 'cnrmworkstation'


class CnrmLinuxServer(UmrCnrmTarget):
    """Aneto cluster at Meteo-France CNRM."""

    _footprint = dict(
        info='Aneto Cluster at CNRM',
        attr=dict(
            sysname = dict(
                values = [ 'Linux' ]
            ),
            inifile=dict(
                default = '@target-cnrmserver.ini',
            ),
        ),
        only = dict(
            hostname = footprints.FPRegex(r'[scv]x\w+(?:\.|$)')
        )
    )


# Prestaging tools for MF mass storage archives

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
        """Actually send the pre-staging request to Hendrix."""
        # Build the target
        request = []
        if email is not None:
            request.append("#MAIL=" + email)
        request.extend(sorted(self.items()))
        # Send this stuff to hendrix
        request_filename = '.'.join([self.logname or 'unknownuser',
                                     'stagereq',
                                     uuid.uuid4().hex[:16],
                                     'MIG'])
        request_data = six.BytesIO()
        request_data.write(('\n'.join(request)).encode(encoding='utf_8'))
        request_data.seek(0)
        try:
            ftp = self.system.ftp(self.storage, logname=self.logname)
        except ftplib.all_errors as e:
            logger.error('Prestaging to %s: unable to connect: %s', self.storage, str(e))
            ftp = None
        if ftp:
            try:
                rc = ftp.cd(self.stagedir)
            except ftplib.all_errors as e:
                logger.error('Prestaging to %s: error with "cd": %s', self.storage, str(e))
                rc = False
            if rc:
                try:
                    ftp.put(request_data, request_filename)
                except ftplib.all_errors as e:
                    logger.error('Prestaging to %s: error with "put": %s', self.storage, str(e))
                    rc = False
            ftp.close()
            return rc
        else:
            return False
