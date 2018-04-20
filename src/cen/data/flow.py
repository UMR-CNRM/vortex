#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import footprints
from footprints.util import rangex

from vortex.data.flow        import GeoFlowResource
from common.data.obs         import ObsRaw
from vortex.data.geometries  import MassifGeometry
from common.data.modelstates import Historic, InitialCondition
from vortex.syntax.stdattrs  import a_date, term

#: No automatic export
__all__ = []

logger = footprints.loggers.getLogger(__name__)


class SafranObsDateError(ValueError):
    """General content error."""

    def __init__(self, allowedhours):
        super(SafranObsDateError, self).__init__(
            'SAFRAN guess are synoptic, therefore the hour must be in {!s}'.
            format(rangex(allowedhours))
        )


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
                    values  = ['ascii', 'txt'],
                    default = 'ascii',
                ),
                model = dict(
                    values = ['safran'],
                    optional = True,
                ),
                source_app = dict(
                    values = ['arpege', 'arome', 'ifs', ],
                    optional = True,
                ),
                source_conf = dict(
                    values = ['4dvarfr', 'pearp', '3dvarfr', 'pefrance', 'determ', 'eps'],
                    optional = True,
                ),
                geometry = dict(
                    info = "The resource's massif geometry.",
                    type = MassifGeometry,
                ),
            )

        )
    ]

    _extension_remap = dict(ascii='txt')

    @property
    def realkind(self):
        return 'guess'

    def basename_info(self):
        return dict(
            radical = self.realkind,
            geo     = self.geometry.area,
            src     = [self.source_app, self.source_conf],
            term    = self.term.fmthour,
            fmt     = self._extension_remap.get(self.nativefmt, self.nativefmt),
        )

    def cendev_basename(self):
        # guess files could be named PYYMMDDHH_hh where YYMMDDHH is the creation date and hh the echeance
        # origin_date = self.date.replace(hour=0)
        # return 'P' + origin_date.yymdh + '_{0:02d}'.format(self.term.hour + 6)
        # guess files are named PYYMMDDHH
        if self.date.hour in [0, 6, 12, 18]:
            return 'P' + self.date.yymdh
        else:
            raise SafranObsDateError('SAFRAN guess are synoptic, therefore the hour must be 0, 6, 12 or 18')


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
            term    = self.term.fmthour,
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
                    values = ['ascii', 'netcdf', 'nc'],
                    default = 'netcdf',
                ),
                origin = dict(
                    default = None,
                    optional = True,
                ),
                geometry = dict(
                    info = "The resource's massif geometry.",
                    type = MassifGeometry,
                ),
                filling = dict(
                    value = ['surf', ],
                    default = 'surf',
                ),
            )
        )
    ]

    _extension_remap = dict(netcdf='nc', ascii='txt')

    @property
    def realkind(self):
        return 'snowpackstate'

    def basename_info(self):
        return dict(
            radical = self.realkind,
            geo     = self.geometry.area,
            fmt     = self._extension_remap.get(self.nativefmt, self.nativefmt),
        )

    def cendev_basename(self):
        return 'prep' + self.date.yymdh


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
            term    = self.term.fmthour,
            fmt     = self._extension_remap.get(self.nativefmt, self.nativefmt),
        )


class SafranObsRaw(ObsRaw):

    _footprint = dict(
        info = 'SAFRAN observation files (SYNOP observations)',
        attr = dict(
            part = dict(
                values  = ['synop', 'precipitation', 'hourlyobs', 'radiosondage', 'nebulosity'],
            ),
            model = dict(
                values  = ['safran'],
            ),
            stage = dict(
                values = ['safrane', 'sypluie']
            ),
            cendev_map = dict(
                type     = footprints.FPDict,
                optional = True,
                default  = footprints.FPDict({'precipitation': 'R',
                                              'hourlyobs': 'T',
                                              'radiosondage': 'A'}),
            ),
            cendev_hours = dict(
                type     = footprints.FPDict,
                optional = True,
                default  = footprints.FPDict({'default': '0-18-6',
                                              'precipitation': '6',
                                              'hourlyobs': '6',
                                              'nebulosity': '6'}),
            ),
        ),
    )

    def cendev_basename(self):
        prefix = self.cendev_map.get(self.part, self.part[0].upper())
        allowed = rangex(self.cendev_hours.get(self.part, self.cendev_hours['default']))
        if self.date.hour in allowed:
            return prefix + self.date.yymdh
        else:
            raise SafranObsDateError(allowed)
