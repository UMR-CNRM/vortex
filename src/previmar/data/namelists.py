#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

import footprints

from vortex.data.outflow import NoDateResource
from gco.syntax.stdattrs import gvar, gdomain
from previmar.data.contents import SurgeTemplate

logger = footprints.loggers.getLogger(__name__)


class BlkdatNamFiles(NoDateResource):
    """
    """
    _footprint = [
        gvar,
        gdomain,
        dict(
            info = "blkdat ascii files. list to tweak",
            attr = dict(
                kind = dict(
                    values = ["blkdat_nam_file"],
                ),
                gvar = dict(
                    default = "[model]_blkdat_[param]_[gdomain]",
                ),
                param = dict(
                    values  = ['full_prv', 'full_ana', 'ms', 'full'],
                ),
                clscontents=dict(
                    default = SurgeTemplate
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return "blkdat_nam_file"
