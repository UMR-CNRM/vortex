#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

from vortex.data.geometries import LonlatGeometry
from vortex.data.outflow import StaticGeoResource
from vortex.syntax.stdattrs import month
from gco.syntax.stdattrs import gvar, GenvDomain


class GenericClim(StaticGeoResource):
    """
    Abstract class for a model climatology.
    An HorizontalGeometry object is needed.
    A Genvkey can be given.
    """
    _abstract = True
    _footprint = [
        gvar,
        dict(
            info = 'Model climatology',
            attr = dict(
                kind = dict(
                    values = ['clim_model']
                ),
                nativefmt = dict(
                    values = ['fa'],
                    default = 'fa',
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'clim_model'

    @property
    def truncation(self):
        """Returns geometry's truncation."""
        return self.geometry.truncation

    def _monthly_suffix(self, prefix=''):
        return '.{0:s}{1.month:s}'.format(prefix, self) if hasattr(self, 'month') else ''

    def gget_basename(self):
        """GGET specific naming convention."""
        return self._monthly_suffix(prefix='m')

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return 'Const.Clim' + self._monthly_suffix()

    def basename_info(self):
        sd = dict(
            fmt     = self.nativefmt,
            geo     = self._geo2basename_info(),
            radical = 'clim',
            src     = self.model,
        )
        if hasattr(self, 'month'):
            sd['suffix'] = {'month': self.month}
        return sd


class GlobalClim(GenericClim):
    """
    Class for a model climatology of a global model.
    A SpectralGeometry object is needed. A Genvkey can be given.
    """
    _footprint = dict(
        info = 'Model climatology for Global Models',
        attr = dict(
            model = dict(
                values = ['arpege']
            ),
            gvar = dict(
                default = 'clim_[model]_t[geometry::truncation]'
            ),
        )
    )


class MonthlyGlobalClim(GlobalClim):
    """
    Class for a monthly model climatology of a global model.
    A SpectralGeometry object is needed. A Genvkey can be given.
    """

    _footprint = [
        month,
        dict(
            info = 'Monthly model climatology for Global Models',
        )
    ]


class ClimLAM(GenericClim):
    """
    Class for a model climatology of a Local Area Model.
    A SpectralGeometry object is needed. A Genvkey can be given
    with a default name retrieved thanks to a GenvDomain object.
    """
    _footprint = dict(
        info = 'Model climatology for Local Area Models',
        attr = dict(
            model = dict(
                values = ['aladin', 'arome']
            ),
            gdomain = dict(
                type = GenvDomain,
                optional = True,
                default = '[geometry::area]'
            ),
            gvar = dict(
                default = 'clim_[gdomain]_[geometry::rnice]'
            ),
        )
    )


class MonthlyClimLAM(ClimLAM):
    """
    Class for a monthly model climatology of a Local Area Model.
    A SpectralGeometry object is needed. A Genvkey can be given
    with a default name retrieved thanks to a GenvDomain object.
    """

    _footprint = [
        month,
        dict(
            info = 'Monthly model climatology for Local Area Models',
        )
    ]


class ClimBDAP(GenericClim):
    """
    Class for a climatology of a BDAP domain.
    A LonlatGeometry object is needed. A Genvkey can be given
    with a default name retrieved thanks to a GenvDomain object.
    """
    _footprint = [
        dict(
            info = 'Bdap climatology',
            attr = dict(
                kind = dict(
                    values = ['clim_bdap']
                ),
                geometry = dict(
                    type = LonlatGeometry,
                ),
                gdomain = dict(
                    type = GenvDomain,
                    optional = True,
                    default = '[geometry::area]'
                ),
                gvar = dict(
                    default = 'clim_dap_[gdomain]'
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'clim_bdap'


class MonthlyClimBDAP(ClimBDAP):
    """
    Class for a monthly climatology of a BDAP domain.
    A LonlatGeometry object is needed. A Genvkey can be given
    with a default name retrieved thanks to a GenvDomain object.
    """

    _footprint = [
        month,
        dict(
            info = 'Monthly Bdap climatology',
        )
    ]


# Databases to generate clim files
class GTOPO30DerivedDB(StaticGeoResource):
    """
    Class of a tar-zip file containing parameters derived from
    GTOPO30 database, generated with old stuff.
    A Genvkey can be given.
    """
    _footprint = [
        gvar,
        dict(
            info = 'Database for GTOPO30-derived parameters.',
            attr = dict(
                kind = dict(
                    values   = ['misc_orography'],
                ),
                source = dict(
                    values   = ['GTOPO30'],
                ),
                geometry = dict(
                    values = ['global2m5'],
                ),
                gvar = dict(
                    default  = '[source]_[kind]'
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'misc_orography'


class UrbanisationDB(StaticGeoResource):
    """
    Class of a binary file containing urbanisation database.
    A Genvkey can be given.
    """
    _footprint = [
        gvar,
        dict(
            info = 'Database for GTOPO30 urbanisation.',
            attr = dict(
                kind = dict(
                    values   = ['urbanisation'],
                ),
                source = dict(
                    values   = ['GTOPO30'],
                ),
                geometry = dict(
                    values = ['global2m5'],
                ),
                gvar = dict(
                    default  = '[source]_[kind]'
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'urbanisation'


class WaterPercentageDB(StaticGeoResource):
    """
    Class of a binary file containing water percentage database.
    A Genvkey can be given.
    """
    _footprint = [
        gvar,
        dict(
            info = 'Database for GTOPO30 water percentage.',
            attr = dict(
                kind = dict(
                    values   = ['water_percentage'],
                ),
                source = dict(
                    values   = ['GTOPO30'],
                ),
                geometry = dict(
                    values = ['global2m5'],
                ),
                gvar = dict(
                    default  = '[source]_[kind]'
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'water_percentage'


class SoilANdVegDB(StaticGeoResource):
    """
    Class of a tar-zip file containing parameters derived from
    various databases.
    A Genvkey can be given.
    """
    _footprint = [
        gvar,
        dict(
            info = 'Database for Soil and Vegetation.',
            attr = dict(
                kind = dict(
                    values   = ['soil_and_veg'],
                ),
                source = dict(
                    values   = ['GiardBazile2000', 'AVHRR-ESA'],
                ),
                geometry = dict(
                    values = ['global1dg', 'europeb01'],
                ),
                gvar = dict(
                    default  = '[source]_[kind]'
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'soil_and_veg'


class MonthlyLAIDB(StaticGeoResource):
    """
    Class of a binary file containing monthly LAI derived from
    various databases.
    A Genvkey can be given.
    """
    _footprint = [
        gvar,
        month,
        dict(
            info = 'Database for monthly LAI.',
            attr = dict(
                kind = dict(
                    values   = ['LAI'],
                ),
                source = dict(
                    values   = ['GiardBazile2000', 'AVHRR-ESA'],
                ),
                geometry = dict(
                    values = ['global1dg', 'europeb01'],
                ),
                gvar = dict(
                    default  = '[source]_[kind]'
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'LAI'

    def gget_basename(self):
        """GGET specific naming convention."""
        return '.m' + str(self.month)


class MonthlyVegDB(StaticGeoResource):
    """
    Class of a binary file containing monthly vegetation derived from
    various databases.
    A Genvkey can be given.
    """
    _footprint = [
        gvar,
        month,
        dict(
            info = 'Database for monthly vegetation.',
            attr = dict(
                kind = dict(
                    values   = ['vegetation'],
                ),
                source = dict(
                    values   = ['GiardBazile2000', 'AVHRR-ESA'],
                ),
                geometry = dict(
                    values = ['global1dg', 'europeb01'],
                ),
                gvar = dict(
                    default  = '[source]_[kind]'
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'vegetation'

    def gget_basename(self):
        """GGET specific naming convention."""
        return '.m' + str(self.month)


class SoilClimatologyDB(StaticGeoResource):
    """
    Class of a binary file containing climatologic soil parameters
    (temperature, moisture, snow, ice) derived from
    various databases.
    A Genvkey can be given.
    """
    _footprint = [
        gvar,
        dict(
            info = 'Database for soil climatology parameters.',
            attr = dict(
                kind = dict(
                    values   = ['soil_clim'],
                ),
                source = dict(
                    values   = ['Arp-reanalysis', 'US-Navy'],
                ),
                geometry = dict(
                    values = ['globaln108', 'global1dg'],
                ),
                gvar = dict(
                    default  = '[source]_[kind]'
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'soil_clim'


class SurfGeopotentialDB(StaticGeoResource):
    """
    Class of a binary file containing Surface Geopotential derived from
    various databases.
    A Genvkey can be given.
    """
    _footprint = [
        gvar,
        dict(
            info = 'Database for surface geopotential.',
            attr = dict(
                kind = dict(
                    values   = ['surfgeopotential'],
                ),
                source = dict(
                    values   = ['Arp-reanalysis'],
                ),
                geometry = dict(
                    values = ['global1dg'],
                ),
                gvar = dict(
                    default  = '[source]_[kind]'
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'surfgeopotential'


class MonthlySoilClimatologyDB(SoilClimatologyDB):
    """
    Class of a binary file containing monthly climatologic soil parameters
    (temperature, moisture, snow, ice) derived from
    various databases.
    A Genvkey can be given.
    """
    _footprint = [
        month,
        dict(
            info = 'Database for monthly soil climatology parameters.',
        )
    ]

    def gget_basename(self):
        """GGET specific naming convention."""
        return '.m' + str(self.month)


class MonthlyChemicalDB(StaticGeoResource):
    """
    Class of a binary file containing climatologic chemicals (ozone, aerosols)
    parameters derived from various databases.
    A Genvkey can be given.
    """
    _footprint = [
        gvar,
        month,
        dict(
            info = 'Database for monthly chemicals.',
            attr = dict(
                kind = dict(
                    values   = ['ozone', 'aerosols'],
                ),
                source = dict(
                    values   = ['UGAMP', 'Tegen'],
                ),
                geometry = dict(
                    values = ['global2dg5', 'global5x4'],
                ),
                gvar = dict(
                    default  = '[source]_[kind]'
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return self.kind

    def gget_basename(self):
        """GGET specific naming convention."""
        return '.m' + str(self.month)


class GeometryIllustration(StaticGeoResource):
    _footprint = dict(
        info = 'Illustration of a domain geographic coverage.',
        attr = dict(
            kind = dict(
                values   = ['geometry_plot'],
            ),
            nativefmt = dict(
                values = ['png', 'pdf'],
            ),
        )
    )

    @property
    def realkind(self):
        return 'geometry_plot'

    def basename_info(self):
        return dict(
            radical = self.realkind,
            geo = self._geo2basename_info(),
            fmt = self.nativefmt
        )
