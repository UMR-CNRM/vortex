#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

import footprints
logger = footprints.loggers.getLogger(__name__)

from common.data.consts import GenvStaticGeoResource
from common.data.namelists import Namelist, NamelistContent
from snowtools.tools.update_namelist import update_surfex_namelist


class SurfexNamelistUpdate(update_surfex_namelist, NamelistContent):
     """Fake DataContent subclass."""
     pass


class List(GenvStaticGeoResource):

    _footprint = dict(
        info = 'Namelist file used by  Safran.',
        attr = dict(
            kind = dict(
                values = ['listem', 'lystem', 'listeo', 'lysteo', 'listeml', 'lysteml',
                          'rsclim', 'icrccm', 'NORELot', 'NORELmt'],
            ),
            nativefmt = dict(
                values  = ['ascii'],
                default = 'ascii',
            ),
            gvar = dict(
                default = '[kind]',
            ),
        )
    )

    @property
    def realkind(self):
        return 'safran_namelist'


class NamelistSurfex(Namelist):
    _footprint = [
        dict(
            info = 'Namelist for SURFEX',
            attr = dict(
                kind = dict(
                    values   = ['surfex_namelist']
                ),
                clscontents = dict(
                    default  = SurfexNamelistUpdate
                ),
            )
        )
    ]
       
    def realkind(self):
        return 'surfex_namelist'
       
    def contents_handler(self,**kw):
        self.clscontents(self.date)
        
