#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import six

from bronx.fancies import loggers
from bronx.stdtypes.date import Date

from vortex.data.executables import BlackBox, Script, OceanographicModel
from gco.syntax.stdattrs import gdomain, gvar

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


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
                forcage = dict(
                    values   = ['aro', 'cep', 'arp', 'aoc', ],
                    optional = True,
                    default  = '',
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
            name_simu_arg = [self.rundir, self.coupling_exec, six.text_type(self.coupling_nprocs)]
        else:
            name_simu_arg = [self.rundir] * 3
        name_simu_arg += [six.text_type(self.num_exp), ]
        cmd = ' '.join(name_simu_arg)
        return cmd


class InterpolationSurges(MasterSurges):
    """Base class for the master of interpolation of a surges model"""
    _footprint = [
        gvar,
        gdomain,
        dict(
            info = 'Interpolation surges',
            attr = dict(
                kind = dict(
                    values = ['BinboxInterpSurges']
                ),
                gvar = dict(
                    default  = 'master_[model]_main_[gdomain]_interpol',
                ),
                version = dict(
                    optional = True,
                    type     = str,
                    default  = 'V4',
                ),
                version_cible = dict(
                    optional = True,
                    type     = str,
                    default  = 'V3',
                ),
                bloc_increment = dict(
                    optional = True,
                    type     = str,
                    default  = '',
                ),
            )
        )
    ]

    def command_line(self, **opts):
        name_simu_arg = [self.rundir, self.coupling_exec, six.text_type(self.coupling_nprocs)]
        name_simu_arg += [six.text_type(self.num_exp), ]
        name_simu_arg += [self.version, self.version_cible]
        name_simu_arg += [six.text_type(self.bloc_increment), ]

        cmd = ' '.join(name_simu_arg)
        return cmd


class SimulationSurges(MasterSurges):
    """Base class for the master of simulation of a surges model, either Full or tideonly simulation"""
    _footprint = [
        gvar,
        gdomain,
        dict(
            info = 'Simulation surges difference because full simulation need coupling execution',
            attr = dict(
                kind = dict(
                    values = ['SimuSurges']
                ),
                gvar = dict(
                    default  = 'master_[model]_main_[gdomain]_[param]',
                ),
                param = dict(
                    optional = True,
                    type     = str,
                    default  = 'full',
                    values   = ['ms', 'full'],
                ),
            )
        )
    ]


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
    """Base class for Filtering Grib (Pmer, U,V 10-meters wind) on Model Grid."""
    _footprint = [
        gvar,
        dict(
            info = 'Filtering Grib input',
            attr = dict(
                kind = dict(
                    values = ['FilteringGrib']
                ),
                model = dict(
                    values = ['hycom'],
                ),
                gvar = dict(
                    default  = 'pesurcote_filtrage_grib',
                    values   = ['pesurcote_filtrage_grib', 'filtrage_grib'],
                    remap    = {'filtrage_grib': 'pesurcote_filtrage_grib'},
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'filteringGrib'


class FiltrageGribWave(FiltrageGrib):
    """Base class."""
    _footprint = [
        gvar,
        dict(
            info = 'Filtering Grib input',
            attr = dict(
                model = dict(
                    values = ['mfwam'],
                ),
                gvar = dict(
                    default  = 'filtrage_grib',
                    values   = ['wave_filtrage_grib', 'filtrage_grib'],
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'filteringGribWave'


class FusionGrib(Script):
    """Base class for Grib Fusion (Pmer, U,V 10-meters wind) on 2 different Model Grid."""
    _footprint = [
        gvar,
        dict(
            info = 'Fusion Grib input',
            attr = dict(
                kind = dict(
                    values = ['FusionGrib']
                ),
                gvar = dict(
                    default  = 'pesurcote_fusion_grib',
                    values   = ['pesurcote_fusion_grib', 'fusion_grib'],
                    remap    = {'fusion_grib': 'pesurcote_fusion_grib'},
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'fusionGrib'


class ConversionGrib2Taux(BlackBox):
    """A tool to convert Wind fields to Stress."""
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
        name_simu_arg += [six.text_type(self.num_exp), ]
        cmd = ' '.join(name_simu_arg)
        return cmd


class SurScriptSurges(BlackBox):
    """Wrapper script for mpiauto (for Binary executables)."""
    _footprint = [
        gvar,
        dict(
            info = 'SurScript Surges used on double binaries execution',
            attr = dict(
                kind = dict(
                    values = ['SurScriptBinary', ],
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


class MasterWaves(OceanographicModel):
    """ Master MFWAM exe """
    _footprint = [
        gvar,
        dict(
            info = 'Master wave',
            attr = dict(
                kind = dict(
                    values = ['MasterWaves'],
                ),
                model = dict(
                    value = ['mfwam', ],
                ),
                gvar = dict(
                    default  = 'master_[model]',
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'WaveChief'


class Filteralti(BlackBox):
    """ Altimeter data filtering."""
    _footprint = [
        gvar,
        dict(
            info = 'Altimeter data filtering',
            attr = dict(
                kind = dict(
                    values = ['Filteralti'],
                ),
                gvar = dict(
                    default  = 'master_[model]_filter_alti_[satellite]',
                ),
                satellite = dict(
                    values = ['jason2', 'saral', 'cryosat2'],
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'Filteralti'

    def command_line(self, begindate, enddate):
        """Build command line for execution as a single string."""
        return ' '.join([begindate.ymdhms, enddate.ymdhms])


class InterpWave(BlackBox):
    """ MFWAM output post-processing."""
    _footprint = [
        gvar,
        dict(
            info = 'MFWAM output post-processing',
            attr = dict(
                kind = dict(
                    values = ['InterpWave'],
                ),
                gvar = dict(
                    default  = 'master_[model]_interp',
                ),
                model = dict(
                    value = ['mfwam', ],
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'InterpWave'
