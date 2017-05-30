#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.data.flow import GeoFlowResource
from common.data.obs import Observations
from vortex.syntax.stdattrs import term
from vortex.data.geometries import MassifGeometry
from common.data.modelstates import Historic, InitialCondition
from vortex.syntax.stdattrs import a_date

class SafranGuess(GeoFlowResource):
    """Class for the guess file (P ou E file) that is used by SAFRAN."""

    _footprint = [
        term,
        dict(
            info = 'Safran guess',
            attr = dict(
                kind = dict(
                    values = ['guess'],
                ),
                nativefmt = dict(
                    values  = ['ascii'],
                    default = 'ascii',
                ),
                model = dict(
                    values = ['safran'],
                    optional = True,
                ),
                source_app = dict(
                    values = ['arpege', 'arome', 'ifs', 'pearp', 'pearome'],
                    optional = True,
                ),
                geometry = dict(
                    info = "The resource's massif geometry.",
                    type = MassifGeometry,
                ),
            )

        )
    ]

    @property
    def realkind(self):
        return 'guess'

    def basename_info(self):
        return dict(
            radical = self.realkind,
            geo     = self.geometry.area,
            src     = self.source_app,
            term    = self.term.fmthm,
        )


# TO be continued...
class SafranRadioSondages(Observations):
    """Alti files (A files)"""

    _footprint = dict(
        info = 'Safran Alti',
        attr = dict(
            kind = dict(
                values = ['alti', 'altitude', 'radiosondage', 'RS'],
            ),
            nativefmt = dict(
                values  = ['ascii'],
                default = 'ascii',
            ),
            part = dict(
                info     = 'The name of this subset of observations.',
                optional = True,
                values   = ['full', 'all'],
                default  = 'all',
            ),
            stage = dict(
                info     = 'The processing stage for this subset of observations.',
                optional = True,
                stage    = ['safrane', 'analysis'],
                default  = 'analysis',
            ),
        )
    )

    @property
    def realkind(self):
        return 'radiosondage'

    def basename_info(self):
        return dict(
            radical = self.realkind,
            src = '.'.join(self.stage, self.part),
            fmt = self.nativefmt,
        )


class SurfaceForcing(GeoFlowResource):
    """Class for the safrane output files."""

    _footprint = [
        term,
        dict(
            info = 'Safran-produced forcing file',
            attr = dict(
                kind = dict(
                    values = ['analysis', 'forcing', 'interpolation', 'interp'],
                ),
                nativefmt = dict(
                    values  = ['netcdf', 'nc'],
                    default = 'netcdf',
                    remap = dict(autoremap = 'first'),
                ),
                model = dict(
                    values = ['safran'],
                ),
                geometry = dict(
                    info = "The resource's massif geometry.",
                    type = MassifGeometry,
                ),
            )
        )
    ]

    _extension_remap = dict(netcdf='nc')

    @property
    def realkind(self):
        return 'forcing'

    def basename_info(self):
        return dict(
            radical = self.realkind,
            geo     = self.geometry.area,
            src     = self.model,
            term    = self.term.fmthm,
            fmt     = self._extension_remap.get(self.nativefmt, self.nativefmt),
        )


class Prep(InitialCondition):
    """Class for the SURFEX-Crocus initialisation of the snowpack state."""

    _footprint = [
        term,
        dict(
            info = 'Instant SURFEX-Crocus Snowpack state',
            attr = dict(
                kind = dict(
                values  = ['SnowpackState'],
                ),
                nativefmt = dict(
                    values = ['netcdf', 'nc'],
                    default = 'netcdf',
                    remap = dict(autoremap = 'first'),
                ),
                origin = dict(
                    default = None,
                    optional = True,
                ),
                geometry = dict(
                    info = "The resource's massif geometry.",
                    type = MassifGeometry,
                ),
            )
        )
    ]

    _extension_remap = dict(netcdf='nc')

    @property
    def realkind(self):
        return 'snowpackstate'

    def basename_info(self):
        return dict(
            radical = self.realkind,
            geo     = self.geometry.area,
            fmt     = self._extension_remap.get(self.nativefmt, self.nativefmt),
        )


class Pro(Historic):
    """Class for the SURFEX-Crocus simulated snowpack."""

    _footprint = [
        term,
        dict(
            info = 'SURFEX-Crocus Snowpack simulation',
            attr = dict(
                kind = dict(
                values  = ['SnowpackSimulation', 'pro'],
                ),
                nativefmt = dict(
                    values = ['netcdf', 'nc'],
                    default = 'netcdf',
                    remap = dict(autoremap = 'first'),
                ),
                origin = dict(
                    default = None,
                    optional = True,
                ),
                geometry = dict(
                    info = "The resource's massif geometry.",
                    type = MassifGeometry,
                ),
                startdate = a_date,
                enddate   = a_date,
            )
        )
    ]

    _extension_remap = dict(netcdf='nc')

    @property
    def realkind(self):
        return 'snowpack'

    def basename_info(self):
        return dict(
            radical = self.realkind,
            geo     = self.geometry.area,
            term    = self.term.fmthm,
            fmt     = self._extension_remap.get(self.nativefmt, self.nativefmt),
        )

