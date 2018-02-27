#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

from vortex.data.outflow import StaticGeoResource
from gco.syntax.stdattrs import gvar

#: No automatic export
__all__ = []


class PGDRaw(StaticGeoResource):
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

    @property
    def realkind(self):
        return 'pgd'

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return 'PGDFILE-' + self.geometry.area + '.' + self.nativefmt

    def cenvortex_basename(self):
        """CEN specific naming convention"""
        return 'PGD_' + self.geometry.area + '.' + self.nativefmt

    def basename_info(self):
        """Generic information, radical = ``pgd``."""
        return dict(
            fmt     = self.nativefmt,
            geo     = self._geo2basename_info(),
            radical = self.realkind,
        )


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


class CoverParams(StaticGeoResource):
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


class IsbaParams(StaticGeoResource):
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


class SandDB(StaticGeoResource):
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


class ClayDB(StaticGeoResource):
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


class OrographyDB(StaticGeoResource):
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


class SurfaceTypeDB(StaticGeoResource):
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


class BathymetryDB(StaticGeoResource):
    """
    Class of a tar-zip (.dir/.hdr) file containing bathymetry database.
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
