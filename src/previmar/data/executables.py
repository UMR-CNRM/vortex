#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.data.executables import BlackBox, Script, OceanographicModel
from gco.syntax.stdattrs import gdomain, GenvKey
from vortex.tools.date import Date


class MasterSurges(OceanographicModel):
    """Base class for the MASTER of a surges model"""
    _footprint = [
        gdomain,
        dict(
            info = 'Master surges',
            attr = dict(
                kind = dict(
                    values = ['BinboxSurges']
                ),
                gvar = dict(
                    type = GenvKey,
                    optional = True,
                    default  = 'master_[model]_main_[gdomain]',
                ),
                model = dict(
                    value = ['hycom', ],
                ),
                rundir = dict(
                    outcast  = '',
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'binary_surges'

    def command_line(self, **opts):
        name_simu_arg = [self.rundir] * 3
        name_simu_arg += "0"
        cmd = ' '.join(name_simu_arg)
        return cmd


class IniZeroSurges(BlackBox):
    """Preparation step to launch a surges model without Atmospheric forcing"""
    _footprint = dict(
        info = 'ini_zero Restart',
        attr = dict(
            kind = dict(
                values = ['InizeroSurges']
            ),
            gvar = dict(
                type     = GenvKey,
                optional = True,
                default  = 'master_[model]_inizero',
            ),
            binopts = dict(
                optional = False,
                type     = Date,
            ),
        )
    )

    @property
    def realkind(self):
        return 'ini_zero_surges'

    def command_line(self, **opts):
        return self.binopts.compact()


class FiltrageGrib(Script):
    """Base class for Filtering Grib (Pmer, U,V 10-meters wind) on Model Grid"""
    _footprint = dict(
        info = 'Filtering executable',
        attr = dict(
            kind = dict(
                values = ['FilteringGrib']
            ),
            gvar = dict(
                type     = GenvKey,
                optional = True,
                default  = 'pesurcote_filtrage_grib',
                values   = ['pesurcote_filtrage_grib', 'filtrage_grib'],
                remap    = {'filtrage_grib': 'pesurcote_filtrage_grib' },
            ),
        )
    )

    @property
    def realkind(self):
        return 'filteringGrib'


class ConversionGrib2Taux(BlackBox):
    """A tool to convert Wind fields to Stress"""
    _footprint = [
        gdomain,
        dict(
            info = 'grib2taux',
            attr = dict(
                kind = dict(
                    values = ['convertgrib2taux']
                ),
                gvar = dict(
                    type     = GenvKey,
                    optional = True,
                    default  = 'master_[model]_grib2taux_[gdomain]',
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'grib2taux'
