#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

from vortex.data.outflow import StaticGeoResource
from gco.syntax.stdattrs import GenvKey


class PGDRaw(StaticGeoResource):
    """
    SURFEX climatological resource.
    A Genvkey can be provided.
    """
    _abstract = True
    _footprint = dict(
        info = 'Surfex climatological file',
        attr = dict(
            gvar = dict(
                type = GenvKey,
                optional = True,
                default  = 'pgd_[nativefmt]',
            ),
        )
    )

    @property
    def realkind(self):
        return 'pgd'

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return 'PGDFILE-' + self.geometry.area + '.' + self.nativefmt

    def basename_info(self):
        """Generic information, radical = ``pgd``."""
        return dict(
            fmt     = self.nativefmt,
            geo     = [ self.geometry.area, self.geometry.rnice ],
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


class CoverParams(StaticGeoResource):
    """
    Class of a tar-zip set of coefficients for radiative transfers computations.
    A Genvkey can be given.
    """
    _footprint = dict(
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
                type     = GenvKey,
                optional = True,
                default  = '[source]_covers_param'
            ),
        )
    )

    @property
    def realkind(self):
        return 'coverparams'


class IsbaParams(StaticGeoResource):
    """
    Class of surface (vegetations, etc.) coefficients.
    A Genvkey can be given.
    """
    _footprint = dict(
        info = 'ISBA parameters',
        attr = dict(
            kind = dict(
                values   = ['isba', 'isbaan'],
                remap    = dict(isbaan = 'isba'),
            ),
            gvar = dict(
                type     = GenvKey,
                optional = True,
                default  = 'analyse_isba'
            ),
        )
    )

    @property
    def realkind(self):
        return 'isba'
