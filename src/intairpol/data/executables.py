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
                gvar = dict(
                    default = "master_mocage",
                ),
                kind = dict(
                    values = ['mocage'],
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
                gvar = dict(
                    default = "master_corromegasurf"
                ),
                kind = dict(
                    values = ['exec_corromegasurf'],
                )
            )
        )
    ]


class ExecSumo(BlackBox):
    """Compute sumo."""

    _footprint = [
        gvar,
        dict(
            info = 'Executable used in macc/mocage for surface coupling',
            attr = dict(
                gvar = dict(
                    default = "master_sumo"
                ),
                kind = dict(
                    values = ['exec_sumo'],
                )
            )
        )
    ]


class Maccraq(BlackBox):
    """Compute mktopbd."""

    _footprint = [
        gvar,
        dict(
            info = 'Executable used in macc fullpos',
            attr = dict(
                gvar = dict(
                    default = "master_maccraq"
                ),
                kind = dict(
                    values = ['maccraq'],
                )
            )
        )
    ]


class ExecMktopbd(BlackBox):
    """Compute mktopbd."""

    _footprint = [
        gvar,
        dict(
            info = 'Executable used in macc/mocage',
            attr = dict(
                gvar = dict(
                    default = "master_mktopbd"
                ),
                kind = dict(
                    values = ['exec_mktopbd'],
                )
            )
        )
    ]

    def stdin_text(self, fcterm=date.Time('24:00'), basedate=None):
        """Build the stdin text used by the executable."""

        first = basedate.ymdh
        last = (basedate + fcterm).ymdh

        return '{first}\n{last}\n'.format(first=first, last=last)
