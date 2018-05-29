#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This package handles some common targets used at ECMWF.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

#: No automatic export
__all__ = []

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.tools.targets import Target


class ECMWFCray(Target):
    """Cray Computer."""

    _abstract = True
    _footprint = dict(
        info = 'Cray Supercomputers at ECMWF',
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
        if 'login' in self.hostname or 'batch' in self.hostname:
            return self.inetname + 'fe'
        else:
            return self.inetname + 'cn'


class CCA(ECMWFCray):
    """CCA Computer at ECMWF."""
    # TODO: Check the name and the number of the different CCA nodes

    _footprint = dict(
        info = 'Cray CCA Supercomputer at ECMWF',
        attr = dict(
            hostname = dict(
                values = \
                    [ x + str(y) for x in ('cca',) for y in range(1836) ] + \
                    [ x + str(y) for x in ('cca-login',) for y in range(1,5) ] + \
                    [ 'cca-batch' ]
            ),
            inetname = dict(
                default = 'cca',
                values  = ['cca']
            ),
        )
    )


class CCB(ECMWFCray):
    """CCB Computer at ECMWF."""
    # TODO: Check the name and the number of the different CCB nodes

    _footprint = dict(
        info = 'Cray CCB Supercomputer at ECMWF',
        attr = dict(
            hostname = dict(
                values = \
                    [ x + str(y) for x in ('ccb',) for y in range(1836) ] + \
                    [ x + str(y) for x in ('ccb-login',) for y in range(1,5) ] + \
                    [ 'ccb-batch' ]
            ),
            inetname = dict(
                default = 'ccb',
                values  = ['ccb']
            ),
        )
    )
