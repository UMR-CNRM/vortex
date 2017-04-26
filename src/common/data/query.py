#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division

from vortex.data.outflow import NoDateResource
from gco.syntax.stdattrs import gvar

"""
Query files used by various databases.
"""

#: No automatic export
__all__ = []


class Query(NoDateResource):
    """Class to deal with queries."""

    _abstract = True
    _footprint = [
        gvar,
        dict(
            info = 'Abstract class for queries.',
        )
    ]


class BDAPQuery(Query):
    """Class to deal with BDAP queries."""
    _footprint = dict(
        info = 'BDAP query',
        attr = dict(
            kind = dict(
                values = ['bdap_query']
            ),
            gvar = dict(
                values  = ['extract_stuff'],
                default = 'extract_stuff'
            ),
            origin = dict(
                default = 'bdap',
                values  = ['bdap'],
                optional = True
            ),
            source = dict(
                values   = ['dir_sea_ice', 'dir_SST'],
            ),
        )
    )

    @property
    def realkind(self):
        return 'bdap_query'

    def gget_urlquery(self):
        """GGET specific query : ``extract``."""
        return 'extract=' + self.source


class BDMQuery(Query):
    """Class to deal with BDM queries."""
    _footprint = dict(
        info = 'BDM query',
        attr = dict(
            kind = dict(
                values = ['bdm_query']
            ),
            gvar = dict(
                values  = ['extract_stuff'],
                default = 'extract_stuff'
            ),
            origin = dict(
                default = 'bdm',
                values  = ['bdm'],
                optional = True
            ),
            source = dict(),
        )
    )

    @property
    def realkind(self):
        return 'bdap_query'

    def gget_urlquery(self):
        """GGET specific query : ``extract``."""
        return 'extract=' + self.source
