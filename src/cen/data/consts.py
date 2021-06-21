# -*- coding: utf-8 -*-

"""
TODO: Module documentation.
"""

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
                    values = ['listem', 'lystem', 'listeo', 'lysteo', 'listeml', 'lysteml',
                              'carpost', 'rsclim', 'icrccm', 'NORELot', 'NORELmt', 'blacklist',
                              'metadata', 'NORELo', 'NORELm', 'shapefile'],
                ),
                nativefmt = dict(
                    values  = ['ascii', 'shp'],
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


class Params(GenvModelGeoResource):

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['ssa_params', 'surfz'],
            ),
            nativefmt = dict(
                values  = ['netcdf', 'nc', 'ascii'],
                default = 'netcdf',
                remap   = dict(nc='netcdf'),
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
                remap   = dict(nc='netcdf'),
            ),
            gvar = dict(
                default = '[kind]',
            ),
        )
    )

    _extension_remap = dict(netcdf='nc')

    @property
    def realkind(self):
        return 'init_TG'

    def namebuilding_info(self):

        nbi = super(climTG, self).namebuilding_info()
        nbi.update(
            # will work only with the @cen namebuilder:
            cen_rawbasename=(self.realkind + "." + self._extension_remap.get(self.nativefmt, self.nativefmt)),
            # With the standard provider, the usual keys will be used.
        )
        return nbi


class GridTarget(GenvModelGeoResource):
    """
    Resource describing a grid for interpolation of data based on massifs geometry
    """

    _footprint = [
        gdomain,
        dict(
            attr = dict(
                kind = dict(
                    values = ["interpolgrid"],
                ),
                nativefmt = dict(
                    values  = ['netcdf', 'nc'],
                    default = 'netcdf',
                    remap   = dict(nc='netcdf'),
                ),
                gvar = dict(
                    default = '[kind]_[gdomain]',
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return self.kind
