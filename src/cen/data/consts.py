#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

import footprints
logger = footprints.loggers.getLogger(__name__)

from common.data.consts import GenvStaticGeoResource
from gco.syntax.stdattrs import gdomain


class ImportFailer(object):
    """Temporary class to del with a missing snowtools package."""

    def __new__(self, *kargs, **kwargs):
        raise RuntimeError('snowtools is not available')


try:
    from snowtools.tools.update_namelist import update_surfex_namelist
except ImportError:
    update_surfex_namelist = ImportFailer


class List(GenvStaticGeoResource):

    _footprint = [
        gdomain,
        dict(
            info = 'Config file used by  S2M models.',
            attr = dict(
                kind = dict(
                    values = ['listem', 'lystem', 'listeo', 'lysteo', 'listeml', 'lysteml',
                              'rsclim', 'icrccm', 'NORELot', 'NORELmt', 'blacklist', 'metadata'],
                ),
                nativefmt = dict(
                    values  = ['ascii'],
                    default = 'ascii',
                ),
                gvar = dict(
                    default = '[kind]_[gdomain]',
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'safran_namelist'


class Snowr_param(GenvStaticGeoResource):

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ["function_param"],
            ),
            nativefmt = dict(
                values  = ['netcdf', 'nc'],
                default = 'netcdf',
            ),
            gvar = dict(
                default = '[kind]',
            ),
        )
    )

    @property
    def realkind(self):
        return 'param_definition'
