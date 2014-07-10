#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

from vortex.data.outflow import StaticResource
from vortex.syntax.stdattrs import a_model, month
from vortex.data.geometries import GridGeometry
from gco.syntax.stdattrs import GenvKey, GenvDomain


class Clim(StaticResource):
    """
    Abstract class for all kinds of climatology
    """
    _abstract = True
    _footprint = [
        month,
        dict(
            info = 'Climatology file',
            attr = dict(
                kind = dict(
                    values = [ 'clim' ],
                ),
                nativefmt = dict(
                    values = [ 'fa' ],
                    default = 'fa',
                ),
            )
          )
    ]

    @property
    def realkind(self):
        return 'clim'

    @property
    def truncation(self):
        """Returns geometry's truncation."""
        return self.geometry.truncation

    def gget_basename(self):
        """GGET specific naming convention."""
        return '.m' + str(self.month)


class ClimModel(Clim):
    """
    Abstract class for a model climatology. A SpectralGeometry object is needed. A Genvkey can be given.
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
                values = [ 'clim_model' ]
            )
        )
    )

    @property
    def realkind(self):
        return 'clim_model'


class ClimGlobal(ClimModel):
    """
    Class for a model climatology of a global model.
    A SpectralGeometry object is needed. A Genvkey can be given.
    """
    _footprint = dict(
        info = 'Model climatology for Global Models',
        attr = dict(
            model = dict(
                values = [ 'arpege' ]
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
                values = [ 'aladin', 'arome' ]
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


class ClimBDAP(Clim):
    """
    Class for a climatology of a BDAP domain.
    A GridGeometry object is needed. A Genvkey can be given
    with a default name retrieved thanks to a GenvDomain object.
    """
    _footprint = [
        dict(
            info = 'Bdap climatology',
            attr = dict(
                geometry= dict(
                    type = GridGeometry,
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
                kind = dict(
                    values = [ 'clim_bdap' ]
                )
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
            suffix  = {'month':self.month},
        )
