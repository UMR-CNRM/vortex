#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

from vortex.data.geometries import LonlatGeometry
from vortex.data.outflow import StaticGeoResource, ModelGeoResource
from vortex.syntax.stdattrs import month_deco
from vortex.syntax.stddeco import namebuilding_insert
from gco.syntax.stdattrs import gvar, GenvDomain

#: No automatic export
__all__ = []


@namebuilding_insert('radical', lambda s: 'clim')
class GenericClim(ModelGeoResource):
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

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return 'Const.Clim'


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
        month_deco,
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
        month_deco,
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
        month_deco,
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
                    values = ['misc_orography'],
                ),
                source = dict(
                    values = ['GTOPO30'],
                ),
                geometry = dict(
                    values = ['global2m5'],
                ),
                gvar = dict(
                    default = '[source]_[kind]'
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
            info = 'Database for urbanisation.',
            attr = dict(
                kind = dict(
                    values   = ['urbanisation'],
                ),
                source = dict(
                    type = str,
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
            info = 'Database for water percentage.',
            attr = dict(
                kind = dict(
                    values   = ['water_percentage'],
                ),
                source = dict(
                    type = str,
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
                    type = str,
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
        month_deco,
        dict(
            info = 'Database for monthly LAI.',
            attr = dict(
                kind = dict(
                    values   = ['LAI'],
                ),
                source = dict(
                    type = str,
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


class MonthlyVegDB(StaticGeoResource):
    """
    Class of a binary file containing monthly vegetation derived from
    various databases.
    A Genvkey can be given.
    """
    _footprint = [
        gvar,
        month_deco,
        dict(
            info = 'Database for monthly vegetation.',
            attr = dict(
                kind = dict(
                    values   = ['vegetation'],
                ),
                source = dict(
                    type = str,
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
                    type = str,
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
                    type = str,
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
        month_deco,
        dict(
            info = 'Database for monthly soil climatology parameters.',
        )
    ]


class MonthlyChemicalDB(StaticGeoResource):
    """
    Class of a binary file containing climatologic chemicals (ozone, aerosols)
    parameters derived from various databases.
    A Genvkey can be given.
    """
    _footprint = [
        gvar,
        month_deco,
        dict(
            info = 'Database for monthly chemicals.',
            attr = dict(
                kind = dict(
                    values   = ['ozone', 'aerosols'],
                ),
                source = dict(
                    type = str,
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
