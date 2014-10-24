#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

from vortex.data.outflow    import ModelResource, StaticResource
from vortex.data.geometries import GridGeometry
from vortex.data.contents   import TextContent

from gco.syntax.stdattrs    import GenvKey


class GPSList(ModelResource):
    """
    Class of a GPS satellite ground coefficients. A Genvkey can be given.
    """
    _footprint = dict(
        info = 'Set of GPS coefficients',
        attr = dict(
            kind = dict(
                values   = ['gpslist', 'listgpssol'],
                remap    = dict(listgpssol = 'gpslist'),
            ),
            clscontents = dict(
                default  = TextContent,
            ),
            gvar = dict(
                type     = GenvKey,
                optional = True,
                default  = 'list_gpssol'
            ),
        )
    )

    @property
    def realkind(self):
        return 'gpslist'


class BatodbConf(ModelResource):
    """
    Default parameters for BATOR execution. A Genvkey can be given.
    """
    _footprint = dict(
        info = 'Batodb parametrization',
        attr = dict(
            kind = dict(
                values   = ['batodbconf', 'batorconf', 'parambator'],
                remap    = dict(
                    parambator = 'batodbconf',
                    batorconf  = 'batodbconf',
                ),
            ),
            clscontents = dict(
                default  = TextContent,
            ),
            gvar = dict(
                type     = GenvKey,
                optional = True,
                default  = 'param_bator_cfg'
            ),
        )
    )

    @property
    def realkind(self):
        return 'batodbconf'


class RtCoef(ModelResource):
    """
    Class of a tar-zip file of satellite coefficients. A Genvkey can be given.
    """
    _footprint = dict(
        info = 'Set of satellite  coefficients',
        attr = dict(
            kind = dict(
                values   = [ 'rtcoef' ]
            ),
            gvar = dict(
                type     = GenvKey,
                optional = True,
                default  = 'rtcoef_tgz'
            ),
        )
    )

    @property
    def realkind(self):
        return 'rtcoef'


class RRTM(ModelResource):
    """
    Class of a tar-zip file of coefficients for radiative transferts computations.
    A Genvkey can be given.
    """
    _footprint = dict(
        info = 'Coefficients of RRTM scheme',
        attr = dict(
            kind = dict(
                values   = [ 'rrtm' ]
            ),
            gvar = dict(
                type     = GenvKey,
                optional = True,
                default  = 'rrtm_const'
            ),
        )
    )

    @property
    def realkind(self):
        return 'rrtm'


class MatFilter(StaticResource):
    """
    Class of a filtering matrix. A SpectralGeometry object is needed,
    as well as the GridGeometry of the scope domain (countaining the filtering used).
    A GenvKey can be given.
    """
    _footprint = dict(
        info = 'Filtering matrix',
        attr = dict(
            model = dict(
                optional = True,
            ),
            kind = dict(
                values   = ['matfilter']
            ),
            scope = dict(
                type     = GridGeometry,
            ),
            gvar = dict(
                type     = GenvKey,
                optional = True,
                default  = 'mat_filter_[scope::area]'
            )
        )
    )

    @property
    def realkind(self):
        return 'matfilter'

    def basename_info(self):
        """Generic information, radical = ``matfil``."""
        return dict(
            geo     = [{'truncation': self.geometry.truncation},
                       {'stretching': self.geometry.stretching},
                       self.scope.area, {'filtering': self.scope.filtering}],
            radical = 'matfil',
            src     = self.model,
        )

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return 'matrix.fil.' + self.scope.area + '.t' + str(self.geometry.truncation) + \
               '.c' + str(self.geometry.stretching)
