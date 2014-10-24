#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

from vortex.data.outflow import ModelResource, StaticResource
from vortex.data.geometries import SpectralGeometry
from gco.syntax.stdattrs import GenvKey


class PGDRaw(StaticResource):
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
                default = 'pgd_[nativefmt]',
            ),
            geometry = dict(
                type = SpectralGeometry,
            )
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
                values = ['pgdlfi']
            ),
            nativefmt = dict(
                default = 'lfi'
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
                values = ['pgdfa']
            ),
            nativefmt = dict(
                default = 'fa'
            )
        )
    )


class CoverParams(StaticResource):
    """
    Class of a tar-zip file of coefficients for radiative transferts computations.
    A Genvkey can be given.
    """
    _footprint = dict(
        info = 'Coefficients of RRTM scheme',
        attr = dict(
            kind = dict(
                values = ['coverparams', 'surfexcover']
            ),
            source = dict(
                values = ['ecoclimap', 'ecoclimap1', 'ecoclimap2'],
                optional = True,
                default = 'ecoclimap',
            ),
            gvar = dict(
                type = GenvKey,
                optional = True,
                default = '[source]_covers_param'
            ),
        )
    )

    @property
    def realkind(self):
        return 'coverparams'
