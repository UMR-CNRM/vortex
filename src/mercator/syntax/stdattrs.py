#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
This module provides some pre-defined attributes descriptions or combined sets
of attributes description that could be used in the footprint definition of any
class which follow the :class:`vortex.syntax.Footprint` syntax.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import footprints

#: Export a set of attributes :data:`grids`, :data:`bogus`, etc..
__all__ = [ 'grids', 'bogus', 'experiences' ]

grids = ['orca025', 'atl12', 'neatl36']
experiences = [ 'ORCA025_LIM-T00', 'ATL12-T00', 'NEATL36-T03', 'PISC_BIO', 'PSY2G2R1', 'ORCA12_LIM-T103' ]
bogus = [ 'DS_BOGUS_HBR', 'DS_BOGUS_HBRST', 'DS_BOGUS_gradHBR', 'IS_BOGUS_HunderICE', 'VP_BOGUS_RUNOFF',
          'VP_BOGUS_TSUVonTROP', 'VP_BOGUS_TSUVunderICE' ]
atmofields = [ 'BULKCLOU', 'BULKHUMI', 'BULKTAIR', 'BULKU10M', 'BULKV10M', 'BULKWIND', 'FLUXPRE',
               'FLUXSSRD', 'FLUXSTRD', 'PRES', 'STRESSU', 'STRESSV' ]

atmoForcingOrigin = [ 'ECMWF', ]


models = [ 'PSY3V2R2', 'PSY2V4R2', 'PSY4V1R3', 'IBI36V2R1' ]
Model = dict(
    optional = False,
    values = models,
    remap = dict(
        psy2  = 'PSY2V4R2',
        psy3  = 'PSY3V2R2',
        psy4  = 'PSY4V1R3',
        ibi36 = 'IBI36V2R1',
    ),
)

model = footprints.Footprint( info = 'Model', attr = dict( model = Model ) )
