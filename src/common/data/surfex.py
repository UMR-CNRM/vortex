#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Various resources to handle climatology files used in the Surfex model.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

from vortex.data.outflow import ModelGeoResource
from vortex.syntax.stddeco import namebuilding_delete
from gco.syntax.stdattrs import gvar

#: No automatic export
__all__ = []


@namebuilding_delete('src')
class PGDRaw(ModelGeoResource):
    """
    SURFEX climatological resource.
    A Genvkey can be provided.
    """
    _abstract = True
    _footprint = [
        gvar,
        dict(
            info = 'Surfex climatological file',
            attr = dict(
                gvar = dict(
                    default  = 'pgd_[nativefmt]',
                ),
            )
        )
    ]
    _extension_remap = dict(netcdf='nc')

    @property
    def realkind(self):
        return 'pgd'

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return 'PGDFILE-' + self.geometry.area + '.' + self.nativefmt

    def namebuilding_info(self):
        nbi = super(PGDRaw, self).namebuilding_info()
        nbi.update(
            # will work only with the @cen namebuilder:
            cen_rawbasename=('PGD_' + self.geometry.area + '.' +
                             self._extension_remap.get(self.nativefmt, self.nativefmt))
            # With the standard provider, the usual keys will be used...
        )
        return nbi


class PGDLFI(PGDRaw):
    """
    SURFEX climatological resource in lfi format.
    A Genvkey can be provided.
    """
    _footprint = dict(
        info = 'Grid-point data consts',
        attr = dict(
            kind = dict(
                values  = ['pgdlfi'],
            ),
            nativefmt = dict(
                default = 'lfi',
            )
        )
    )


class PGDFA(PGDRaw):
    """
    SURFEX climatological resource in fa format.
    A Genvkey can be provided.
    """
    _footprint = dict(
        info = 'Grid-point data consts',
        attr = dict(
            kind = dict(
                values  = ['pgdfa'],
            ),
            nativefmt = dict(
                default = 'fa',
            )
        )
    )


class PGDNC(PGDRaw):
    """
    SURFEX climatological resource in netcdf format.
    A Genvkey can be provided.
    """
    _footprint = dict(
        info = 'Grid-point data consts',
        attr = dict(
            kind = dict(
                values  = ['pgdnc'],
            ),
            nativefmt = dict(
                default = 'netcdf',
            )
        )
    )


@namebuilding_delete('src')
class PGDWithGeo(ModelGeoResource):
    """
    SURFEX climatological resource.
    A Genvkey can be provided.
    """
    _footprint = [
        gvar,
        dict(
            info = 'Surfex climatological file',
            attr = dict(
                kind = dict(
                    values  = ['pgd', ],
                ),
                nativefmt = dict(
                    values = ['fa', 'lfi', 'netcdf'],
                    default = 'fa',
                ),
            )
        )
    ]
    _extension_remap = dict(netcdf='nc')

    @property
    def realkind(self):
        return 'pgd'

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return 'PGDFILE-' + self.geometry.area + '.' + self.nativefmt

    def genv_basename(self):
        """Customise the Genv key..."""
        if self.gvar:
            return gvar
        else:
            if self.geometry.lam:
                geotag = '{0.area}_{0.rnice}'.format(self.geometry)
            else:
                geotag = 't{0.truncation:d}'.format(self.geometry)
            return 'pgd_{:s}_{:s}'.format(geotag, self.nativefmt)


class CoverParams(ModelGeoResource):
    """
    Class of a tar-zip set of coefficients for radiative transfers computations.
    A Genvkey can be given.
    """
    _footprint = [
        gvar,
        dict(
            info = 'Coefficients of RRTM scheme',
            attr = dict(
                kind = dict(
                    values   = ['coverparams', 'surfexcover'],
                    remap    = dict(surfexcover = 'coverparams'),
                ),
                source = dict(
                    optional = True,
                    default  = 'ecoclimap',
                    values   = ['ecoclimap', 'ecoclimap1', 'ecoclimap2'],
                ),
                gvar = dict(
                    default  = '[source]_covers_param'
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'coverparams'


class IsbaParams(ModelGeoResource):
    """
    Class of surface (vegetations, etc.) coefficients.
    A Genvkey can be given.
    """
    _footprint = [
        gvar,
        dict(
            info = 'ISBA parameters',
            attr = dict(
                kind = dict(
                    values   = ['isba', 'isbaan'],
                    remap    = dict(isbaan = 'isba'),
                ),
                gvar = dict(
                    default  = 'analyse_isba'
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'isba'


class SandDB(ModelGeoResource):
    """
    Class of a tar-zip (.dir/.hdr) file containing surface sand database.
    A Genvkey can be given.
    """
    _footprint = [
        gvar,
        dict(
            info = 'Database for quantity of sand in soil',
            attr = dict(
                kind = dict(
                    values   = ['sand'],
                ),
                source = dict(
                ),
                gvar = dict(
                    default  = '[source]_[kind]'
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'sand'


class ClayDB(ModelGeoResource):
    """
    Class of a tar-zip (.dir/.hdr) file containing surface clay database.
    A Genvkey can be given.
    """
    _footprint = [
        gvar,
        dict(
            info = 'Database for quantity of clay in soil',
            attr = dict(
                kind = dict(
                    values   = ['clay'],
                ),
                source = dict(
                ),
                gvar = dict(
                    default  = '[source]_[kind]'
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'clay'


class OrographyDB(ModelGeoResource):
    """
    Class of a tar-zip (.dir/.hdr) file containing orography database.
    A Genvkey can be given.
    """
    _footprint = [
        gvar,
        dict(
            info = 'Database for orography',
            attr = dict(
                kind = dict(
                    values   = ['orography'],
                ),
                source = dict(
                ),
                gvar = dict(
                    default  = '[source]_[kind]_[geometry::rnice_u]'
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'orography'


class SurfaceTypeDB(ModelGeoResource):
    """
    Class of a tar-zip (.dir/.hdr) file containing surface type database.
    A Genvkey can be given.
    """
    _footprint = [
        gvar,
        dict(
            info = 'Database for surface type',
            attr = dict(
                kind = dict(
                    values   = ['surface_type'],
                ),
                source = dict(
                ),
                gvar = dict(
                    default  = '[source]_[kind]'
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'surface_type'


class BathymetryDB(ModelGeoResource):
    """
    Class of file containing bathymetry database.
    A Genvkey can be given.
    """
    _footprint = [
        gvar,
        dict(
            info = 'Database for bathymetry',
            attr = dict(
                kind = dict(
                    values   = ['bathymetry'],
                ),
                source = dict(
                ),
                gvar = dict(
                    default  = '[source]_[kind]_[geometry::rnice_u]'
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'bathymetry'
