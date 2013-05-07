#!/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

from vortex.data.outflow import ModelResource, StaticResource
from vortex.data.geometries import GridGeometry
from gco.syntax.stdattrs import GenvKey


class RtCoef(ModelResource):
    """
    Class of a tar-zip file of satellite coefficients. A Genvkey can be given.
    """
    _footprint = [
        dict(
            info = 'Set of satellite  coefficients',
            attr = dict(
                kind = dict(
                    values = [ 'rtcoef' ]
                ),
                gvar = dict(
                    type = GenvKey,
                    optional = True,
                    default = 'rtcoef_tgz'
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'rtcoef'


class MatFilter(StaticResource):
    """
    Class of a filtering matrix. A SpectralGeometry object is needed,
	as well as the GridGeometry of the scope domain (countaining the filtering used).
	A GenvKey can be given.
    """
    _footprint = [
        dict(
            info = 'Filtering matrix',
            attr = dict(
                model = dict(
                    optional = True,
                ),
                kind = dict(
                    values = [ 'matfilter' ]
                ),
                scope = dict(
                    type = GridGeometry,
                ),
                gvar = dict(
                    type = GenvKey,
                    optional = True,
                    default = 'mat_filter_[scope::area]'
                )
            )
        )
    ]

    @property
    def realkind(self):
        return 'matfilter'

    def basename_info(self):
        """Generic information, radical = ``matfil``."""
        return dict(
            geo     = [{'truncation':self.geometry.truncation}, {'stretching':self.geometry.stretching}, self.scope.area, {'filtering':self.scope.filtering}],
            radical = 'matfil',
            src     = self.model,
        )

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return 'matrix.fil.' + self.scope.area + '.t' + str(self.geometry.truncation) + '.c' + str(self.geometry.stretching)

