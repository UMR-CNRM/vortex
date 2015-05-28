#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import re

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.tools import date, odb
from vortex.algo.components import BlindRun, Parallel
from common.algo.ifsroot import IFSParallel

class IFSSST(IFSParallel):
    """Used for SST domain fit"""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values  = ['sst'],
                remap   = dict(autoremap = 'first'),
            ),
            conf = dict(
                default = '931',
            ),
            xpname = dict(
                default = 'XSST',
            ),
            timestep = dict(
                default  = '1.',
            ),
        )
    )

