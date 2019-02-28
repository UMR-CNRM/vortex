#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

from bronx.fancies           import loggers
from bronx.stdtypes.date     import Date, Time

import footprints
from footprints.util import rangex

from vortex.data.flow        import GeoFlowResource
from vortex.data.geometries  import UnstructuredGeometry, HorizontalGeometry
from vortex.syntax.stddeco   import namebuilding_append, namebuilding_delete, namebuilding_insert

from common.data.modelstates import InitialCondition
from common.data.obs         import ObsRaw

from vortex.syntax.stdattrs import a_date
from cen.syntax.stdattrs     import cendateperiod_deco

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class SafranObsDateError(ValueError):
    """General content error."""

    def __init__(self, allowedhours):
        super(SafranObsDateError, self).__init__(
            'SAFRAN guess are synoptic, therefore the hour must be in {!s}'.
            format(rangex(allowedhours))
        )


@namebuilding_insert('src', lambda s: [s.source_app, s.source_conf])
@namebuilding_insert('term', lambda s: s.cumul.fmthour)
@namebuilding_delete('geo')
class SafranGuess(GeoFlowResource):
    """Class for the guess file (P ou E file) that is used by SAFRAN."""

    _footprint = [
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
                    values = ['arpege', 'arome', 'ifs'],
                ),
                source_conf = dict(
                    values = ['4dvarfr', 'pearp', '3dvarfr', 'pefrance', 'eps', 'pearo', 'era40'],
                ),
                geometry = dict(
                    info = "The resource's massif geometry.",
                    type = UnstructuredGeometry,
                ),
                cumul = dict(
                    info     = "The duration of cumulative fields (equivalent to the initial"
                               " model resource term).",
                    type     = Time,
                ),
            )
        )
    ]

    _extension_remap = dict(ascii='txt')

    @property
    def realkind(self):
        return 'guess'

    def reanalysis_basename(self):
        # guess files are named PYYMMDDHH in cen re-analysis database
        if self.source_app == 'arpege':
            if self.date.hour in [0, 6, 12, 18]:
                return 'P' + self.date.yymdh
            else:
                raise SafranObsDateError('SAFRAN guess are synoptic, therefore the hour must be 0, 6, 12 or 18')
        elif self.conf.source_app == 'cep':
            return 'cep_' + self.data.nivologyseason


@namebuilding_delete('src')
@namebuilding_delete('geo')
class SurfaceIO(GeoFlowResource):

    _abstract = True
    _footprint = [
        cendateperiod_deco,
        dict(
            info = 'SURFEX input or output file',
            attr = dict(
                nativefmt = dict(
                    values  = ['netcdf', 'nc'],
                    default = 'netcdf',
                    remap = dict(autoremap = 'first'),
                ),
                geometry = dict(
                    info = "The resource's massif geometry.",
                    type = HorizontalGeometry,
                ),
                datebegin = dict(
                    info = "First date of the forcing file",
                ),
                dateend = dict(
                    info = "Last date of the forcing file",
                ),
                # This notion does not mean anything in our case (and seems to be
                # rather ambiguous also in other cases)
                cutoff = dict(
                    optional = True,
                ),
            )
        )
    ]

    _extension_remap = dict(netcdf='nc')

    @property
    def realkind(self):
        return self.kind


@namebuilding_append('src', lambda self: self.source_conf, none_discard=True)
@namebuilding_append('src', lambda self: self.source_app, none_discard=True)
class SurfaceForcing(SurfaceIO):
    """Class for all kind of meteorological forcing files."""
    _footprint = [
        dict(
            info = 'Safran-produced forcing file',
            attr = dict(
                kind = dict(
                    values = ['MeteorologicalForcing'],
                ),
                model = dict(
                    values = ['safran', 'obs', 's2m', 'adamont'],
                ),
                source_app = dict(
                    values = ['arpege', 'arome', 'ifs', ],
                    optional = True
                ),
                source_conf = dict(
                    values = ['4dvarfr', 'pearp', '3dvarfr', 'pefrance', 'determ', 'eps', 'pearome', 'era40'],
                    optional = True
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'FORCING'


class Pro(SurfaceIO):
    """Class for the safrane output files."""
    _footprint = [
        dict(
            info = 'Safran-produced forcing file',
            attr = dict(
                kind = dict(
                    values = ['SnowpackSimulation'],
                ),
                model = dict(
                    values = ['surfex'],
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return "PRO"


@namebuilding_delete('src')
@namebuilding_delete('geo')
@namebuilding_insert('cen_period', lambda self: [self.datevalidity.ymdh, ])
class Prep(InitialCondition):
    """Class for the SURFEX-Crocus initialisation of the snowpack state."""

    _footprint = [
        dict(
            info = 'Instant SURFEX-Crocus Snowpack state',
            attr = dict(
                kind = dict(
                    values  = ['PREP'],
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
                    type = HorizontalGeometry,
                ),
                filling = dict(
                    value = ['surf', ],
                    default = 'surf',
                ),
                # In operational applications, date is used to refer to the run time
                # but the validity date of the file can be different.
                # In research applications, there is only the validity date which makes sense.
                datevalidity = dict(
                    optional = True,
                    type = Date,
                    default = '[date]',
                ),
                # This notion does not mean anything in our case (and seems to be rather
                # ambiguous also in other cases)
                cutoff = dict(
                    optional = True
                )
            )
        )
    ]

    _extension_remap = dict(netcdf='nc', ascii='txt')

    @property
    def realkind(self):
        return 'PREP'


@namebuilding_insert('cen_period', lambda self: [self.datebegin.y, self.dateend.y])
class SnowObs(GeoFlowResource):

    _footprint = [
        cendateperiod_deco,
        dict(
            info = 'Observations of snow for model evaluation',
            attr = dict(
                kind = dict(
                    values = ['SnowObservations'],
                ),

                model = dict(
                    values = ['obs']
                ),

                nativefmt = dict(
                    values  = ['netcdf', 'nc'],
                    default = 'netcdf',
                    remap = dict(autoremap = 'first'),
                ),
                geometry = dict(
                    info = "The resource's massif geometry.",
                    type = HorizontalGeometry,
                ),
                datebegin = dict(
                    info = "First date of the forcing file",
                ),
                dateend = dict(
                    info = "Last date of the forcing file",
                ),
                # This notion does not mean anything in our case (and seems to be rather
                # ambiguous also in other cases)
                cutoff = dict(
                    optional = True
                )
            )
        )
    ]

    _extension_remap = dict(netcdf='nc')

    @property
    def realkind(self):
        return "obs_insitu"


class ScoresSnow(SurfaceIO):
    """Class for the safrane output files."""

    _footprint = [
        dict(
            info = 'Safran-produced forcing file',
            attr = dict(
                kind = dict(
                    values = ['ScoresSnow'],
                ),
                model = dict(
                    values = ['surfex'],
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return "scores"


class SafranObsRaw(ObsRaw):

    _footprint = dict(
        info = 'SAFRAN observation files (SYNOP observations)',
        attr = dict(
            part = dict(
                values  = ['synop', 'precipitation', 'hourlyobs', 'radiosondage', 'nebulosity', 'all'],
            ),
            model = dict(
                values  = ['safran'],
            ),
            stage = dict(
                values = ['safrane', 'sypluie', 'safran']
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
        if self.part == 'nebulosity':
            return '{0:s}{1:s}.tgz'.format(prefix, self.date.yymd)
        elif self.date.hour in allowed:
            return prefix + self.date.yymdh
        else:
            raise SafranObsDateError(allowed)

    def reanalysis_basename(self):
        return self.cendev_basename()


@namebuilding_append('cen_period', lambda self: [{'begindate': self.begindate},
                                                 {'enddate': self.enddate}])
class SafranPackedObs(GeoFlowResource):

    _footprint = dict(
        info = 'SAFRAN packed observations covering the given period',
        attr = dict(
            kind = dict(
                values = ['packedobs'],
            ),
            model = dict(
                values  = ['safran'],
            ),
            nativefmt = dict(
                values = ['tar'],
                default = 'tar'
            ),
            begindate = a_date,
            enddate   = a_date,
        ),
    )

    @property
    def realkind(self):
        return 'observations'
