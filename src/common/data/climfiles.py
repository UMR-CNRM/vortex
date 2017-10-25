#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

from vortex.data.geometries import LonlatGeometry
from vortex.data.outflow import StaticGeoResource
from vortex.syntax.stdattrs import a_model, month
from gco.syntax.stdattrs import gvar, GenvDomain


class ClimModel(StaticGeoResource):
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
                model = a_model,
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


class MonthlyClimModel(ClimModel):
    """
    Abstract class for a monthly model climatology.
    An HorizontalGeometry object is needed.
    A Genvkey can be given.
    """
    _abstract = True
    _footprint = [
        month,
        dict(
            info = 'Model climatology',
            attr = dict(
                kind = dict(
                    values = ['monthly_clim_model']
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'monthly_clim_model'

    def gget_basename(self):
        """GGET specific naming convention."""
        return '.m' + str(self.month)

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return 'Const.Clim.' + str(self.month)


class ClimGlobal(ClimModel):
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

    def basename_info(self):
        """Generic information, radical = ``clim``."""
        return dict(
            fmt     = self.nativefmt,
            geo     = [{'truncation': self.geometry.truncation},
                       {'stretching': self.geometry.stretching}],
            radical = 'clim',
            src     = self.model,
        )


class MonthlyClimGlobal(MonthlyClimModel, ClimGlobal):
    """
    Class for a monthly model climatology of a global model.
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

    def basename_info(self):
        """Generic information, radical = ``clim``."""
        return dict(
            fmt     = self.nativefmt,
            geo     = [{'truncation': self.geometry.truncation},
                       {'stretching': self.geometry.stretching}],
            radical = 'clim',
            src     = self.model,
            suffix  = {'month': self.month},
        )


class ClimLAM(ClimModel):
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

    def basename_info(self):
        """Generic information, radical = ``clim``."""
        return dict(
            fmt     = self.nativefmt,
            geo     = [self.geometry.area, self.geometry.rnice],
            radical = 'clim',
            src     = self.model,
        )


class MonthlyClimLAM(MonthlyClimModel, ClimLAM):
    """
    Class for a monthly model climatology of a Local Area Model.
    A SpectralGeometry object is needed. A Genvkey can be given
    with a default name retrieved thanks to a GenvDomain object.
    """
    _footprint = dict(
        info = 'Model climatology for Local Area Models',
        attr = dict(
#            model = dict(
#                values = ['aladin', 'arome']
#            ),
#            gdomain = dict(
#                type = GenvDomain,
#                optional = True,
#                default = '[geometry::area]'
#            ),
#            gvar = dict(
#                default = 'clim_[gdomain]_[geometry::rnice]'
#            ),
        )
    )

    def basename_info(self):
        """Generic information, radical = ``clim``."""
        return dict(
            fmt     = self.nativefmt,
            geo     = [self.geometry.area, self.geometry.rnice],
            radical = 'clim',
            src     = self.model,
            suffix  = {'month': self.month},
        )


class ClimBDAP(StaticGeoResource):
    """
    Class for a climatology of a BDAP domain.
    A LonlatGeometry object is needed. A Genvkey can be given
    with a default name retrieved thanks to a GenvDomain object.
    """
    _footprint = [
        gvar,
        dict(
            info = 'Bdap climatology',
            attr = dict(
                kind = dict(
                    values = ['clim_bdap']
                ),
                nativefmt = dict(
                    values = ['fa'],
                    default = 'fa',
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

    def basename_info(self):
        """Generic information, radical = ``clim``."""
        return dict(
            fmt     = self.nativefmt,
            geo     = self.geometry.area,
            radical = 'clim',
            src     = self.model,
        )

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return 'Const.Clim'


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
            attr = dict(
                kind = dict(
                    values = ['monthly_clim_bdap']
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'monthly_clim_bdap'

    def basename_info(self):
        """Generic information, radical = ``clim``."""
        return dict(
            fmt     = self.nativefmt,
            geo     = self.geometry.area,
            radical = 'clim',
            src     = self.model,
            suffix  = {'month': self.month},
        )

    def gget_basename(self):
        """GGET specific naming convention."""
        return '.m' + str(self.month)

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return 'Const.Clim.' + str(self.month)


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


class GTOPO30Urbanisation(StaticGeoResource):
    """
    Class of a binary file containing urbanisation from
    GTOPO30 database.
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


class GTOPO30WaterPercentage(StaticGeoResource):
    """
    Class of a binary file containing water percentage from
    GTOPO30 database.
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


class GB2000SoilVeg(StaticGeoResource):
    """
    Class of a tar-zip file containing parameters derived from
    Giard and Bazile 2000 Soil and vegetation database.
    A Genvkey can be given.
    """
    _footprint = [
        gvar,
        dict(
            info = 'Database for Giard and Bazile 2000 Soil and Vegetation.',
            attr = dict(
                kind = dict(
                    values   = ['soil_and_veg'],
                ),
                source = dict(
                    values   = ['GiardBazile2000'],
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
        return 'soil_and_veg'


class GB2000MonthlyLAI(StaticGeoResource):
    """
    Class of a binary file containing monthly LAI derived from
    Giard and Bazile 2000 Soil and vegetation database.
    A Genvkey can be given.
    """
    _footprint = [
        gvar,
        dict(
            info = 'Database for Giard and Bazile 2000 monthly LAI.',
            attr = dict(
                kind = dict(
                    values   = ['LAI'],
                ),
                source = dict(
                    values   = ['GiardBazile2000'],
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
        return 'LAI'


class GB2000MonthlyVeg(StaticGeoResource):
    """
    Class of a binary file containing monthly vegetation derived from
    Giard and Bazile 2000 Soil and vegetation database.
    A Genvkey can be given.
    """
    _footprint = [
        gvar,
        dict(
            info = 'Database for Giard and Bazile 2000 monthly vegetation.',
            attr = dict(
                kind = dict(
                    values   = ['vegetation'],
                ),
                source = dict(
                    values   = ['GiardBazile2000'],
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
        return 'vegetation'


class USNavySoil(StaticGeoResource):
    """
    Class of a binary file containing soil parameters derived from
    a US-Navy soil database.
    A Genvkey can be given.
    """
    _footprint = [
        gvar,
        dict(
            info = 'Database for US-Navy derived soil parameters.',
            attr = dict(
                kind = dict(
                    values   = ['soil'],
                ),
                source = dict(
                    values   = ['US-Navy'],
                ),
                geometry = dict(
                    values = ['globaln108'],
                ),
                gvar = dict(
                    default  = '[source]_[kind]'
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'soil'


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
        if self.geometry.kind == 'projected':
            lgeo = [self.geometry.area, self.geometry.rnice]
        elif self.geometry.kind == 'gauss':
            lgeo = [{'truncation': self.geometry.truncation}, {'stretching': self.geometry.stretching}]
        else:
            lgeo = self.geometry.area
        return dict(
            radical = self.realkind,
            geo = lgeo,
            fmt = self.nativefmt
        )
