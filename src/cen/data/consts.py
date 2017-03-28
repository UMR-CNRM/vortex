#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

import footprints
logger = footprints.loggers.getLogger(__name__)

from common.data.consts import GenvStaticGeoResource
from vortex.syntax.stdattrs import term, a_date

_domain_map = dict(alp='_al', pyr='_py', cor='_co')



class List(GenvStaticGeoResource):

    _footprint = dict(
        info = 'Namelist file used by  Safran.',
        attr = dict(
            kind = dict(
                values = ['listem', 'lystem', 'listeo', 'lysteo', 'listeml', 'lysteml', 'rsclim', 'icrccm'],
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


