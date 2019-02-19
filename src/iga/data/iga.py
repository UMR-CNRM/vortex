#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function, division, unicode_literals

from bronx.fancies import loggers

from vortex.data.contents import TextContent
from vortex.data.flow import FlowResource, GeoFlowResource
from vortex.syntax.stdattrs import term_deco
#from vortex.syntax.stddeco import namebuilding_append, namebuilding_delete, namebuilding_insert
from vortex.syntax        import stdattrs, stddeco

#: Automatic export of  class
__all__ = [ ]

logger = loggers.getLogger(__name__)


@stddeco.namebuilding_insert('src', lambda s: s.scope)
class Listing_Observations_Request(GeoFlowResource):
    """Chemical boundary conditions produced by some external model."""

    _footprint = [
        term_deco,
        dict(
            info = 'OULOUTPUT files',
            attr = dict(
                kind = dict(
                    values   = ['listing_ouloutput'],
                ),
                format = dict(
                    default  = 'ascii',
                ),
                scope = dict(
                    values  = ['conv', 'surf', 'b1', 'b2', 'b3', 'b4','1','oulan'],
                ),
                term = dict(
                    optional = True,
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'listing_ouloutput'
