#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function, division, unicode_literals

from bronx.fancies import loggers

from vortex.data.flow import GeoFlowResource
from vortex.syntax import stddeco

#: Automatic export of  class
__all__ = [ ]

logger = loggers.getLogger(__name__)


@stddeco.namebuilding_append('src', lambda s: s.scope)
class Listing_Observations_Request(GeoFlowResource):
    """Soprano's extraction listings."""

    _footprint = [
        dict(
            info = 'OULOUTPUT files',
            attr = dict(
                kind = dict(
                    values   = ['listing_ouloutput', ],
                ),
                format = dict(
                    default  = 'ascii',
                ),
                scope = dict(
                    values  = ['conv', 'surf', 'b1', 'b2', 'b3', 'b4', '1', 'oulan'],
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'listing_ouloutput'
