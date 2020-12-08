#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Promethee gridfiles
"""

from __future__ import print_function, absolute_import, unicode_literals, division

#from vortex.data.resources import Resource
from vortex.data.outflow import StaticResource
from common.data.gridfiles import TimePeriodGridPoint
from promethee.syntax.stdattrs import param_deco, version_deco, promid_deco
from vortex.syntax.stddeco import namebuilding_insert


#: No automatic export
__all__ = []


class PrometheeGridPoint(TimePeriodGridPoint):
    """
    Gridpoint files calculated in a post-processing task or module for
    a given time period.
    """
    _footprint = [
        param_deco,
        dict(
            info = "Promethee gridpoint",
            attr = dict(
                kind = dict(
                    optional = False,
                    values = ["gridpoint", "promethee_gridpoint"]
                ),
                model = dict(
                    optional = False,
                    values = ["promethee", "prom", "arpege", "arp", "arp_court", 
                    "arome", "aro", "aearp", "pearp", "ifs", "aroifs", "cifs", 
                    "mfwam", "pg1", "alpha",]
                ),
                origin = dict(
                    info = "Describes where the data originally comes from",
                    values = [
                        'analyse', 'ana', 'guess', 'gss', 'arpege', 'arp', 'arome', 'aro',
                        'aladin', 'ald', 'historic', 'hst', 'forecast', 'fcst', 'era40', 'e40',
                        'era15', 'e15', 'interp', 'sumo', 'filter', 'stat_ad', "post",
                    ],
                    remap = dict(
                        analyse = 'ana',
                        guess = 'gss',
                        arpege = 'arp',
                        aladin = 'ald',
                        arome = 'aro',
                        historic = 'hst',
                        forecast = 'fcst',
                        era40 = 'e40',
                        era15 = 'e15'
                    )
                ),
            )
        )
    ]


@namebuilding_insert("radical", lambda s: s.realkind)
#class PrometheeMask(Resource):
class PrometheeMask(StaticResource):
    """
    Promethee Mask 
    """
    _footprint = [
        promid_deco,
        version_deco,
        dict(
            info = "Promethee mask",
            attr = dict(
                kind    = dict(
                    optional    = False,
                    values      = ["promethee_mask"]
                ),
                nativefmt = dict(
                    optional    = True,
                    values      = ["netcdf", ],
                    default     = "netcdf"
                )
            )
        )
    ]

    @property
    def realkind(self):
        return "mask"