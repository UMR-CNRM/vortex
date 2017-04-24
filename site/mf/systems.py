#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This package handles some common targets used at Meteo France.
"""

#: No automatic export
__all__ = []

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.tools.targets import Target


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
                values = \
                    [ x + str(y) for x in ('beaufix',) for y in range(1836) ] + \
                    [ x + str(y) for x in ('beaufixlogin',) for y in range(6) ] + \
                    [ x + str(y) for x in ('beaufixtransfert',) for y in range(8) ]
            ),
            inetname = dict(
                default = 'beaufix',
                values  = ['beaufix']
            ),
        )
    )

    del x
    del y


class Prolix(MeteoBull):
    """Prolix Computer at Meteo-France."""

    _footprint = dict(
        info = 'Bull Prolix Supercomputer at Meteo France',
        attr = dict(
            hostname = dict(
                values = \
                    [ x + str(y) for x in ('prolix',) for y in range(1800) ] + \
                    [ x + str(y) for x in ('prolixlogin',) for y in range(6) ] + \
                    [ x + str(y) for x in ('prolixtransfert',) for y in range(8) ]
            ),
            inetname = dict(
                default = 'prolix',
                values  = ['prolix']
            ),
        )
    )

    del x
    del y


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

    del x
    del y


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
