#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import footprints

from common.data.consts import GenvModelGeoResource
from gco.syntax.stdattrs import gdomain
from vortex.data.resources import Resource

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
                              'rsclim', 'icrccm', 'NORELot', 'NORELmt', 'blacklist', 'metadata', 'NORELo', 'NORELm'],
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


class Params(GenvModelGeoResource):

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['ssa_params', 'surfz'],
            ),
            nativefmt = dict(
                values  = ['netcdf', 'nc', 'ascii'],
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
        return 'init_TG'

    def namebuilding_info(self):

        nbi = super(climTG, self).namebuilding_info()
        nbi.update(
            # will work only with the @cen namebuilder:
            cen_rawbasename = (self.realkind + "." + self._extension_remap.get(self.nativefmt, self.nativefmt)),
            # With the standard provider, the usual keys will be used.
        )
        return nbi


class ConfFile(Resource):
    """
    Vortex configuration file.
    """

    _footprint = dict(
        attr = dict(
            kind = dict(
                type = str,
                values =['ini_file', ],
            ),
            nativefmt = dict(
                optional = True
            ),
            vapp = dict(
                type = str,
                values = ['s2m'],
            ),
            vconf = dict(
                type = str,
            ),
        )
    )

    @property
    def realkind(self):
        return self.vapp + '_' + self.vconf
