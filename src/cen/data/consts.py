#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

from bronx.fancies import loggers

from common.data.consts import GenvModelGeoResource
from gco.syntax.stdattrs import gdomain

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class List(GenvModelGeoResource):

    _footprint = [
        gdomain,
        dict(
            info = 'Config file used by  S2M models.',
            attr = dict(
                kind = dict(
                    values = ['listem', 'lystem', 'listeo', 'lysteo', 'listeml', 'lysteml', 'carpost',
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


class SSA_param(GenvModelGeoResource):

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ["ssa_params"],
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
        return self.kind


class climTG(GenvModelGeoResource):
    """
    Ground temperature climatological resource.
    """

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ["climTG"],
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

    _extension_remap = dict(netcdf='nc')

    @property
    def realkind(self):
        return 'climTG'

    def namebuilding_info(self):
        nbi = super(climTG, self).namebuilding_info()
        nbi.update(
            # will work only with the @cen namebuilder:
            cen_rawbasename = ('init_TG_' + self.geometry.area + '.' +
                               self._extension_remap.get(self.nativefmt, self.nativefmt)),
            # With the standard provider, the usual keys will be used.
        )
        return nbi
