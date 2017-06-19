#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.data.executables import BlackBox, Script, OceanographicModel
from gco.syntax.stdattrs import gdomain, gvar
from vortex.tools.date import Date


class MasterSurges(OceanographicModel):
    """Base class for the MASTER of a surges model"""
    _footprint = [
        gvar,
        gdomain,
        dict(
            info = 'Master surges',
            attr = dict(
                kind = dict(
                    values = ['BinboxSurges']
                ),
                gvar = dict(
                    default  = 'master_[model]_main_[gdomain]',
                ),
                model = dict(
                    value = ['hycom', ],
                ),
                rundir = dict(
                    type     = str,
                    outcast  = '',
                ),
                coupling_exec = dict(
                    type     = str,
                    optional = True,
                    default  = '',
                ),
                coupling_nprocs = dict(
                    type     = int,
                    optional = True,
                    default  = 0,
                ),
                num_exp = dict(
                    type     = int,
                    optional = True,
                    default  = 0,
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'binary_surges'

    def command_line(self, **opts):
        if self.coupling_exec:
            name_simu_arg = [self.rundir, self.coupling_exec, str(self.coupling_nprocs)]
        else:
            name_simu_arg = [self.rundir] * 3
        name_simu_arg += str( self.num_exp )
        cmd = ' '.join(name_simu_arg)
        return cmd


class IniZeroSurges(BlackBox):
    """Preparation step to launch a surges model without Atmospheric forcing"""
    _footprint = [
        gvar,
        gdomain,
        dict(
            info = 'ini_zero Restart',
            attr = dict(
                kind = dict(
                    values = ['InizeroSurges']
                ),
                gvar = dict(
                    default  = 'master_[model]_inizero_[gdomain]',
                ),
                binopts = dict(
                    type     = Date,
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'ini_zero_surges'

    def command_line(self, **opts):
        return self.binopts.compact()


class FiltrageGrib(Script):
    """Base class for Filtering Grib (Pmer, U,V 10-meters wind) on Model Grid"""
    _footprint = [
        gvar,
        dict(
            info = 'Filtering executable',
            attr = dict(
                kind = dict(
                    values = ['FilteringGrib']
                ),
                gvar = dict(
                    default  = 'pesurcote_filtrage_grib',
                    values   = ['pesurcote_filtrage_grib', 'filtrage_grib'],
                    remap    = {'filtrage_grib': 'pesurcote_filtrage_grib' },
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'filteringGrib'


class ConversionGrib2Taux(BlackBox):
    """A tool to convert Wind fields to Stress"""
    _footprint = [
        gvar,
        gdomain,
        dict(
            info = 'A tool to convert Wind fields to Stress: grib2taux',
            attr = dict(
                kind = dict(
                    values = ['convertgrib2taux']
                ),
                gvar = dict(
                    default  = 'master_[model]_grib2taux_[gdomain]',
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'grib2taux'


class WW3writeSurges(BlackBox):
    """Binary executables for writing Hycom results on WW3 grid."""
    _footprint = [
        gvar,
        gdomain,
        dict(
            info = 'Binary executables for writing Hycom results on WW3 grid',
            attr = dict(
                kind = dict(
                    values = ['WW3writeSurges']
                ),
                gvar = dict(
                    default  = 'master_[model]_ww3write_[gdomain]',
                ),
                rundir = dict(
                    type  = str,
                    outcast = '',
                ),
                num_exp = dict(
                    type     = int,
                    optional = True,
                    default  = 0,
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'WW3writeSurges'

    def command_line(self, **opts):
        name_simu_arg = [self.rundir] * 1
        name_simu_arg += str( self.num_exp )
        cmd = ' '.join(name_simu_arg)
        return cmd


class SurScriptSurges(BlackBox):
    """Wrapper script for mpiauto (for Binary executables)."""
    _footprint = [
        gvar,
        dict(
            info = ('SurScript Surges used on double binaries execution'),
            attr = dict(
                kind = dict(
                    values = [ 'SurScriptBinary'],
                ),
                gvar = dict(
                    default  = '[model]_shell_select_binary',
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'SurScriptBinary'
