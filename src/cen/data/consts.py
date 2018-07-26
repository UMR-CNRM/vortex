#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import footprints

from common.data.consts import GenvModelGeoResource
from gco.syntax.stdattrs import gdomain

#: No automatic export
__all__ = []

logger = footprints.loggers.getLogger(__name__)


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

    def basename_info(self):
        return dict(
            fmt     = self.nativefmt,
            geo     = [ self.geometry.area, self.geometry.rnice ],
            radical = self.realkind,
        )

    def cenvortex_basename(self):
        """CEN specific naming convention"""
        return 'init_TG_' + self.geometry.area + '.' + self._extension_remap.get(self.nativefmt, self.nativefmt)
