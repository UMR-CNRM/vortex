#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This package handles some common targets used at ECMWF.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import footprints

from vortex.tools.targets import Target

#: No automatic export
__all__ = []


class ECMWFCrayXC(Target):
    """Cray XC30/40 Computer."""

    _abstract = True
    _footprint = dict(
        info = 'Cray Supercomputers at ECMWF',
        attr = dict(
            sysname = dict(
                values = ['Linux', ]
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


class CCA(ECMWFCrayXC):
    """CCA Computer at ECMWF."""
    # TODO: Check the name and the number of the different CCA nodes

    _footprint = dict(
        info = 'Cray CCA Supercomputer at ECMWF',
        attr = dict(
            inetname = dict(
                default = 'cca',
                values  = ['cca']
            ),
        ),
        only = dict(
            hostname = footprints.FPRegex(r'cca(?:(?:-login|ppn|mom)?\d+|-batch)(?:\.|$)')
        ),
    )


class CCB(ECMWFCrayXC):
    """CCB Computer at ECMWF."""
    # TODO: Check the name and the number of the different CCB nodes

    _footprint = dict(
        info = 'Cray CCB Supercomputer at ECMWF',
        attr = dict(
            inetname = dict(
                default = 'ccb',
                values  = ['ccb']
            ),
        ),
        only = dict(
            hostname = footprints.FPRegex(r'ccb(?:(?:-login|ppn|mom)?\d+|-batch)(?:\.|$)')
        ),
    )
