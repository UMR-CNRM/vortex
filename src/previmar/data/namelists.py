#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

import re

import footprints
logger = footprints.loggers.getLogger(__name__)
from gco.syntax.stdattrs import gdomain

from previmar.data.contents import SurgeTemplate
from common.data.ctpini import AsciiFiles
from bronx.stdtypes.date import Date


class BlkdatNamFiles(AsciiFiles):
    """
    """
    _footprint = [
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
                date = dict(
                    optional = True,
                    type = Date,
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