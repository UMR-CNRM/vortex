#!/usr/bin/env python
# -*- coding: utf-8 -*-
from mlt import Geometry

#: No automatic export
__all__ = []

from vortex.data.geometries import LonlatGeometry
from vortex.data.outflow import StaticGeoResource
from vortex.syntax.stdattrs import a_model, month
from gco.syntax.stdattrs import GenvKey, GenvDomain


class ClimModel(StaticGeoResource):
    """
    Abstract class for a model climatology. An HorizontalGeometry object is needed. 
    A Genvkey can be given.
    """
    _abstract = True
    _footprint = dict(
        info = 'Model climatology',
        attr = dict(
            model = a_model,
            gvar = dict(
                type = GenvKey,
                optional = True,
            ),
            kind = dict(
                values = ['clim_model']
            ),
            nativefmt = dict(
                values = ['fa'],
                default = 'fa',
            ),
        )
    )

    @property
    def realkind(self):
        return 'clim_model'

    @property
    def truncation(self):
        """Returns geometry's truncation."""
        return self.geometry.truncation

    def gget_basename(self):
        """GGET specific naming convention."""
        return '.m' + str(self.month)


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
            geo     = [{'truncation': self.geometry.truncation}, {'stretching': self.geometry.stretching}],
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
            suffix  = {'month': self.month},
        )


class ClimBDAP(StaticGeoResource):
    """
    Class for a climatology of a BDAP domain.
    A LonlatGeometry object is needed. A Genvkey can be given
    with a default name retrieved thanks to a GenvDomain object.
    """
    _footprint = [
        month,
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
                    type = GenvKey,
                    optional = True,
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
            suffix  = {'month': self.month},
        )

    def gget_basename(self):
        """GGET specific naming convention."""
        return '.m' + str(self.month)
