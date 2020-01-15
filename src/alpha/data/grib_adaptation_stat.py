#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function, division, unicode_literals

from bronx.fancies import loggers

from vortex.data.contents import TextContent
from vortex.data.flow import FlowResource, GeoFlowResource
from vortex.syntax.stdattrs import term_deco
from vortex.syntax.stddeco import namebuilding_append, namebuilding_delete, namebuilding_insert

#: Automatic export of  class
__all__ = [ ]

logger = loggers.getLogger(__name__)

@namebuilding_delete('src')
class Adaptations_statistics(GeoFlowResource):
    """adaptation_statistics file."""

    _footprint = [
        term_deco,
        dict(
            info = 'adaptations statistic file',
            attr = dict(
                kind = dict(
                    values = ['adaptations_statistics'],
                ),
                nativefmt = dict(
                    values   = ['grib'],
                    default  = 'grib',
                ),
                vapp_origin = dict(
                    values = ['pg1'],
                    optional = True,
                ),
                vconf_origin = dict(
                    values = ['pagrex','parome','parotro','pearp','pa'],
                    optional = True,
                ),
            )
        )
    ]

    @property
    def realkind(self):
        name = 'grid.'+ self.vapp_origin + '-' + self.vconf_origin 
        return name

