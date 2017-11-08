#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

import footprints
logger = footprints.loggers.getLogger(__name__)

from common.data.consts import GenvStaticGeoResource
from common.data.namelists import Namelist, NamelistContent


class ImportFailer(object):
    """Temporary class to del with a missing snowtools package."""

    def __new__(self, *kargs, **kwargs):
        raise RuntimeError('snowtools is not available')


try:
    from snowtools.tools.update_namelist import update_surfex_namelist
except ImportError:
    update_surfex_namelist = ImportFailer


class SurfexNamelistUpdate(update_surfex_namelist, NamelistContent):
    """Fake DataContent subclass."""
    pass


class List(GenvStaticGeoResource):

    _footprint = dict(
        info = 'Namelist file used by  Safran.',
        attr = dict(
            kind = dict(
                values = ['listem', 'lystem', 'listeo', 'lysteo', 'listeml', 'lysteml',
                          'rsclim', 'icrccm', 'NORELot', 'NORELmt', 'blacklist'],
            ),
            nativefmt = dict(
                values  = ['ascii'],
                default = 'ascii',
            ),
            gvar = dict(
                default = '[kind]_[vconf]',
            ),
            vconf = dict(
                values = ['alp', 'pyr', 'cor']
            ),
        )
    )

    @property
    def realkind(self):
        return 'safran_namelist'


class Metadata(Namelist):
    _footprint = [
        dict(
            info = 'Namelist for SURFEX',
            attr = dict(
                kind = dict(
                    values   = ['metadata', 'metadata.xml', 'METADATA', 'METADATA.xml']
                ),
                clscontents = dict(
                    default  = SurfexNamelistUpdate
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'METADATA.xml'


class Options(Namelist):
    _footprint = [
        dict(
            info = 'Namelist for SURFEX',
            attr = dict(
                kind = dict(
                    values   = ['options', 'options.nam', 'OPTIONS', 'OPTIONS.nam']
                ),
                clscontents = dict(
                    default  = SurfexNamelistUpdate
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'OPTIONS.nam'

    def contents_handler(self, **kw):
        self.clscontents(self.date)


class Snowr_param(GenvStaticGeoResource):

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ["drdt_bst_fit"],
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
