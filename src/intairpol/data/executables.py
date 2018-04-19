#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from __future__ import print_function, absolute_import, division

#: No automatic export
__all__ = []


from vortex.data.executables import BlackBox, ChemistryModel
from gco.syntax.stdattrs import gvar
from bronx.stdtypes import date


class Mocage(ChemistryModel):
    """Compute mocage."""

    _footprint = [
        gvar,
        dict(
            info = 'Executable used in macc/mocage for forecast',
            attr = dict(
                kind = dict(
                    values = ['mocage'],
                ),
                gvar = dict(
                    default = 'master_[kind]',
                ),
                model = dict(
                    values = ['mocage']
                )
            )
        )
    ]


class ExecCorromegasurf(BlackBox):
    """Compute corromegasurf."""

    _footprint = [
        gvar,
        dict(
            info = 'Executable used in macc/mocage to correct omegasurf field',
            attr = dict(
                kind = dict(
                    values = ['altitude'],
                ),
                gvar = dict(
                    default = 'master_[kind]',
                )
            )
        )
    ]


class PrepSurfMocage(BlackBox):
    """Prepare surface fields for mocage, particularly sources emissions."""

    _footprint = [
        gvar,
        dict(
            info = 'Executable used in macc/mocage for surface coupling',
            attr = dict(
                kind = dict(
                    values  = ['surface'],
                ),
                gvar = dict(
                    default = 'master_[kind]',
                )
            )
        )
    ]


class Maccraq(BlackBox):
    """Convert fields to BDAP grib inputs."""

    _footprint = [
        gvar,
        dict(
            info = 'Convert fields to BDAP grib inputs',
            attr = dict(
                kind = dict(
                    values  = ['post_bdap'],
                ),
                gvar = dict(
                    default = 'master_[kind]',
                )
            )
        )
    ]


class MkTopBD(BlackBox):
    """Compute topbd."""

    _footprint = [
        gvar,
        dict(
            info = 'Executable used in macc/mocage',
            attr = dict(
                kind = dict(
                    values  = ['mktopbd'],
                ),
                gvar = dict(
                    default = 'master_[kind]'
                )
            )
        )
    ]

    def stdin_text(self, fcterm=date.Time('24:00'), basedate=None):
        """Build the stdin text used by the executable."""
        first = basedate.ymdh
        last = (basedate + fcterm).ymdh
        return '{first}\n{last}\n'.format(first=first, last=last)