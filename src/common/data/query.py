#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division


from vortex.data.outflow import NoDateResource
from gco.syntax.stdattrs import gvar

#: No automatic export
__all__ = []


class Query(NoDateResource):
    """Class to deal with queries."""

    _abstract = True
    _footprint = [
        dict(
            info = 'Abstract class for queries.',
        )
    ]

    def vortex_pathinfo(self):
         """Default path informations (used by :class:`vortex.data.providers.Vortex`)."""
         return dict(
             origin = self.origin,
         )

    def vortex_basename(self):
        """Default basename """
        return dict(
            kind = self.realkind,
        )


class BDAPQuery(Query):
    """Class to deal with BDAP queries."""
    _footprint = [
        gvar,
        dict(
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
    ]

    @property
    def realkind(self):
        return 'bdap_query'

    def basename_info(self):
        return dict(
            radical = self.kind,
            src = [self.source],
        )

    def gget_urlquery(self):
        """GGET specific query : ``extract``."""
        return 'extract=' + self.source