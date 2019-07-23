#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division, unicode_literals

from vortex.data.executables import BlackBox, ChemistryModel
from gco.syntax.stdattrs import gvar
from bronx.stdtypes import date
from vortex.syntax.stddeco import namebuilding_append
#: No automatic export
__all__ = []


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
@namebuilding_append('src',lambda s:s.subkind)
class MocageAssim(ChemistryModel):
    """Mocage Palm Component (assim version)"""
    _footprint = [
        gvar,
        dict(
            info = 'Palm coupler for assimilation in mocage',
            attr = dict(
                kind = dict(
                    values = ['mocage_assim'],
                ),
                gvar = dict(
                    default = 'master_[kind]_[subkind]',
                ),
                model = dict(
                    values = ['mocage']
                ),
                subkind = dict(
                    values = ['palm','main']
                ),
                tasks = dict(
                    type = int,
                    optional = True,
                    default = 12,
                ),
                openmp = dict(
                    type = int,
                    optional = True,
                    default = 20,
                )
             )
        )
    ]
    def make_mpi_opts(self):
        """ return mpi options to produce mpibinary 
        """
        return { 'kind' :'basic',
                 'tasks': 1,
                 'nodes' : self.tasks if self.subkind == 'main' else 1,
                 'openmp': self.openmp,
        }
    


    
class MocageAssimPalm(ChemistryModel):
    """Mocage Palm Component (assim version)"""
    _footprint = [
        gvar,
        dict(
            info = 'Palm coupler for assimilation in mocage',
            attr = dict(
                kind = dict(
                    values = ['mocage_assim_palm'],
                ),
                gvar = dict(
                    default = 'palm_[kind]',
                ),
                model = dict(
                    values = ['mocage']
                ),
             )
        )
    ]

class MocageAssimMainBlock(ChemistryModel):
    """Mocage Main block (assim version)"""
    _footprint = [
        gvar,
        dict(
            info = 'Main block for assimilation in mocage',
            attr = dict(
                kind = dict(
                    values = ['mocage_assim_main'],
                ),
                gvar = dict(
                    optional = True,
                    default = 'main_[kind]',
                ),
                model = dict(
                    values = ['mocage']
                ),
                tasks = dict(
                    type = int,
                    optional = True,
                    default = 12
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

    def stdin_text(self, fcterm=date.Time('24:00'), basedate=None, **opts):  # @UnusedVariable
        """Build the stdin text used by the executable."""
        first = basedate.ymdh
        last = (basedate + fcterm).ymdh
        return '{first}\n{last}\n'.format(first=first, last=last)


class Init(BlackBox):
    """Chemical Climatological Init"""

    _footprint = [
        gvar,
        dict(
            info = 'Update the date value of a chemical climatologic file',
            attr = dict(
                kind = dict(
                    values  = ['initmoc'],
                ),
                gvar = dict(
                    default = 'master_[kind]',
                )
            )
        )
    ]


class TestRestart(BlackBox):
    """Control Guess file """

    _footprint = [
        gvar,
        dict(
            info = 'Control the guess files species under fixed thresholds',
            attr = dict(
                kind = dict(
                    values  = ['tstrestart'],
                ),
                gvar = dict(
                    default = 'master_[kind]',
                )
            )
        )
    ]
