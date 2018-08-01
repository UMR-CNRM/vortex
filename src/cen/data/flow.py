#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import footprints
from footprints.util import rangex

from vortex.data.flow        import GeoFlowResource
from common.data.obs         import ObsRaw
from vortex.data.geometries  import MassifGeometry
from common.data.modelstates import InitialCondition
from vortex.syntax.stdattrs  import Time

from bronx.stdtypes.date import Date

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
                    type = MassifGeometry,
                ),
                cumul = dict(
                    info     = "The duration of cumulative fields (equivalent to the initial model resource term).",
                    type     = Time,
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
            src     = [self.source_app, self.source_conf],
            term    = self.cumul.fmthour,
            fmt     = self._extension_remap.get(self.nativefmt, self.nativefmt),
        )

#    def cenvortex_basename(self):
#        return self.realkind + "." + self.source_app + "." + self.source_conf + "-" + str(self.cumul.hh) + "." + self._extension_remap.get(self.nativefmt, self.nativefmt)

    def cendev_basename(self):
        # guess files could be named PYYMMDDHH_hh where YYMMDDHH is the creation date and hh the echeance
        # origin_date = self.date.replace(hour=0)
        # return 'P' + origin_date.yymdh + '_{0:02d}'.format(self.term.hour + 6)
        # guess files are named PYYMMDDHH
        if self.source_app == 'arpege':
            if self.date.hour in [0, 6, 12, 18]:
                return 'P' + self.date.yymdh
            else:
                raise SafranObsDateError('SAFRAN guess are synoptic, therefore the hour must be 0, 6, 12 or 18')
        elif self.conf.source_app == 'cep':
            return 'cep_' + self.data.nivologyseason()


class SurfaceIO(GeoFlowResource):

    _abstract = True
    _footprint = [
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
                    type = MassifGeometry,
                ),
                datebegin = dict(
                    info = "First date of the forcing file",
                    type = Date,
                ),
                dateend = dict(
                    info = "Last date of the forcing file",
                    type = Date,
                ),
                # This notion does not mean anything in our case (and seems to be rather ambiguous also in other cases)
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

    def basename_info(self):
        return dict(
            radical    = self.realkind,
            cen_period = [self.datebegin.ymdh, self.dateend.ymdh],
            fmt        = self._extension_remap.get(self.nativefmt, self.nativefmt),
        )

# A supprimer car normalement maintenant la méthode basename_info fait exactement la même chose
# vérifier que le provider cenvortex va bien chercher vortex_basename en l'absence de cenvortex_basename
#     def cenvortex_basename(self):
#         for var in [self.realkind, self.datebegin.ymdh, self.dateend.ymdh, self._extension_remap.get(self.nativefmt, self.nativefmt)]:
#             print type(var), var
#         return self.realkind + "_" + self.datebegin.ymdh + "_" + self.dateend.ymdh + "." + self._extension_remap.get(self.nativefmt, self.nativefmt)


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
                    values = ['safran', 'obs', 's2m'],
                ),
                source_app = dict(
                    values = ['arpege', 'arome', 'ifs', ],
                    optional = True,
                    default = None
                ),
                source_conf = dict(
                    values = ['4dvarfr', 'pearp', '3dvarfr', 'pefrance', 'determ', 'eps', 'pearome'],
                    optional = True,
                    default = None
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'FORCING'

    def basename_info(self):
        src = None
        for var in [self.source_app, self.source_conf]:
            if var:
                if not src:
                    src = list()
                src.append(var)
        return dict(
            radical     = self.realkind,
            src         = src,
            cen_period  = [self.datebegin.ymdh, self.dateend.ymdh],
            fmt         = self._extension_remap.get(self.nativefmt, self.nativefmt),
        )

    def cenvortex_basename(self):
        return self.vortex_basename()


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
                    type = MassifGeometry,
                ),
                filling = dict(
                    value = ['surf', ],
                    default = 'surf',
                ),
                # In operational applications, date is used to refer to the run time but the validity date of the file can be different.
                # In research applications, there is only the validity date which makes sense.
                datevalidity = dict(
                    optional = True,
                    type = Date,
                    default = '[date]',
                ),
                # This notion does not mean anything in our case (and seems to be rather ambiguous also in other cases)
                cutoff = dict(
                    optional = True)
            )
        )
    ]

    _extension_remap = dict(netcdf='nc', ascii='txt')

    @property
    def realkind(self):
        return 'PREP'

    def basename_info(self):
        return dict(
            radical    = self.realkind,
            cen_period = [self.datevalidity.ymdh],
            fmt        = self._extension_remap.get(self.nativefmt, self.nativefmt),
        )


class SnowObs(GeoFlowResource):

    _footprint = [
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
                    type = MassifGeometry,
                ),
                datebegin = dict(
                    info = "First date of the forcing file",
                    type = Date,
                ),
                dateend = dict(
                    info = "Last date of the forcing file",
                    type = Date,
                ),
                # This notion does not mean anything in our case (and seems to be rather ambiguous also in other cases)
                cutoff = dict(
                    optional = True)
            )
        )
    ]

    _extension_remap = dict(netcdf='nc')

    @property
    def realkind(self):
        return "obs_insitu"

    def cenvortex_basename(self):
        print("CENVORTEX_BASENAME")
        print(self.realkind + "_" + self.geometry.area + "_" + self.datebegin.y + "_" + self.dateend.y + "." + self._extension_remap.get(self.nativefmt, self.nativefmt))

        return self.realkind + "_" + self.geometry.area + "_" + self.datebegin.y + "_" + self.dateend.y + "." + self._extension_remap.get(self.nativefmt, self.nativefmt)


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
