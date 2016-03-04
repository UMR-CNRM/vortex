#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This package handles some common targets sused at Meteo France.
"""

#: No automatic export
__all__ = []

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.tools.targets import Target
from vortex.tools.systems import OSExtended, Linux27


class SuperUX(OSExtended):
    """NEC Operating System."""

    _footprint = dict(
        info = 'NEC operating system',
        attr = dict(
            sysname = dict(
                values = [ 'SUPER-UX' ]
            )
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('SuperUX system init %s', self.__class__)
        self._psopts = kw.pop('psopts', ['-f'])
        super(SuperUX, self).__init__(*args, **kw)
        if self.hostname == 'unix':
            hl = self.spawn(['hostname'])
            if len(hl) > 0:
                self._attributes['hostname'] = hl[0]

    def rawcp(self, source, destination):
        """NEC SX raw copy is a spawn of the shell cp."""
        self.spawn(['cp', source, destination], output=False)
        return bool(self.path.isfile(destination) and self.size(source) == self.size(destination))


class NECSX9(Target):
    """NEC Vector Computer."""

    _footprint = dict(
        info = 'NEC vector computer SX9',
        attr = dict(
            hostname = dict(
                values = [ 'unix' ] + [ x + '0' + str(y) for x in ('yuki', 'kumo') for y in range(10) ]
            ),
            sysname = dict(
                values = [ 'SUPER-UX' ]
            ),
            inifile = dict(
                default = 'target-necsx9.ini',
            )
        )
    )


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
                default = 'target-[inetname].ini',
            )
        ),
        priority = dict(
            level = footprints.priorities.top.TOOLBOX
        )
    )

    def spawn_hook(self, sh):
        """Specific target hook before any serious execution."""
        if not sh.env.VORTEX_NOFLUSH_LUSTRE:
            sh.header('Flush Lustre Locks')
            sh.spawn(['/opt/softs/bin/flush-lustre-locks'], output=False)

    def generic(self):
        """Generic name is inetname suffixed with ``fe`` or ``cn``."""
        if 'login' in self.hostname or 'transfert' in self.hostname:
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
                    [ x + str(y) for x in ('beaufix',) for y in range(1080) ] + \
                    [ x + str(y) for x in ('beaufixlogin',) for y in range(6) ] + \
                    [ x + str(y) for x in ('beaufixtransfert',) for y in range(4) ]
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
                default='target-aneto.ini',
            ),
        ),
        priority = dict(
            level = footprints.priorities.top.TOOLBOX
        )
    )

    del x
    del y
