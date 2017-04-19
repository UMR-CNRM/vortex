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


class SafranEbauche(GeoFlowResource):
    """Class for the ebauche file (P ou E file) that is used by SAFRAN."""

    _footprint = [
        term,
        dict(
            info = 'Safran ebauche',
            attr = dict(
                kind = dict(
                    values = ['ebauche'],
                ),
                nativefmt = dict(
                    values  = ['ascii'],
                    default = 'ascii',
                ),
                model = dict(
                    values = ['pearp', 'arpege', 'ifs'],
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
        return 'ebauche'

    def basename_info(self):
        return dict(
            radical = self.realkind,
            geo     = self.geometry.area,
            src     = self.model,
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


class MetFiles(GeoFlowResource):
    """Class for the met, metcli or MET files produced by SAFRAN."""

    _footprint = [
        term,
        dict(
            info = 'Safran analysis',
            attr = dict(
                kind = dict(
                    values = ['met', 'MET', 'metcli'],
                ),
                nativefmt = dict(
                    values  = ['grib', 'netcdf', 'unknown'],
                    default = 'grib',
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

    @property
    def realkind(self):
        return 'met'

    def basename_info(self):
        return dict(
            radical = self.realkind,
            geo     = self.geometry.area,
            src     = self.model,
            term    = self.term.fmthm,
            fmt     = self.nativefmt,
        )
