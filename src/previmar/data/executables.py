# -*- coding: utf-8 -*-

"""
TODO: Module documentation
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import six

from bronx.fancies import loggers
from bronx.stdtypes.date import Date

from vortex.data.executables import BlackBox, Script, OceanographicModel
from vortex.syntax.stdattrs import model
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
    """Master MFWAM executable."""
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
    """Altimeter data filtering."""
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
    """MFWAM output post-processing."""
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


class ConversionWindWW3(BlackBox):
    """A tool to convert wind fields to ww3 format."""
    _footprint = [
        gvar,
        model,
        dict(
            info = 'A tool to convert wind to ww3 format',
            attr = dict(
                kind = dict(
                    values  = ['convertWindWw3']
                ),
                model = dict(
                    values  = ['ww3']
                ),
                gvar = dict(
                    default = 'master_[model]_prnc',
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'ConvertWindWW3'


class ConversionSpecWW3Ascii(BlackBox):
    """A tool to convert spectra from mfwam to ww3 ascii."""
    _footprint = [
        gvar,
        model,
        dict(
            info = 'A tool to convert mfwam spectra to ww3 ascii',
            attr = dict(
                kind = dict(
                    values  = ['specmfwam2ww3']
                ),
                model = dict(
                    values  = ['ww3']
                ),
                gvar = dict(
                    default  = 'master_[model]_bound_ascii',
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'ConvertMfwam2WW3Ascii'


class BoundariesConditionWw3(BlackBox):
    """A tool to compute ww3 boundaries conditions."""
    _footprint = [
        gvar,
        model,
        dict(
            info = 'A tool to compute ww3 boundaries conditions',
            attr = dict(
                kind = dict(
                    values  = ['boundww3']
                ),
                model=dict(
                    values  = ['ww3']
                ),
                gvar = dict(
                    default = 'master_[model]_bound',
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'BoundWW3'


class ConversionWW3Netcdf(BlackBox):
    """A tool to convert  ww3 result (to nc file)."""
    _footprint = [
        gvar,
        model,
        dict(
            info = 'A tool to convert  ww3 result',
            attr = dict(
                kind = dict(
                    values = ['convNetcdfPts', 'convNetcdfSurf']
                ),
                fields = dict(
                    values = ['ww3_ounp', 'ww3_ounf']
                ),
                model = dict(
                    values = ['ww3']
                ),
                gvar = dict(
                    default = 'master_[fields]',
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'ConvWW3Netcdf'


class InterpolationUGnc(BlackBox):
    """A tool to interpolate ww3 parameter nc file to regular grid."""
    _footprint = [
        gvar,
        dict(
            info = 'A tool to interpolate to regular grid',
            attr = dict(
                kind = dict(
                    values = ['interpnc']
                ),
                gvar = dict(
                    default  = 'master_interpolateugnc',
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'interpnc'


class ConversionNcGrib(BlackBox):
    """A tool to convert netcdf fields fo grib fields."""
    _footprint = [
        gvar,
        dict(
            info = 'Conversion nc to grib',
            attr = dict(
                kind = dict(
                    values = ['convncgrb']
                ),
                gvar = dict(
                    default  = 'master_nc_grb',
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'convertncgrb'
