#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

from bronx.fancies import loggers
from bronx.stdtypes.date import Date

from vortex.data.outflow import ModelResource
from gco.syntax.stdattrs import gvar, gdomain
from previmar.data.contents import SurgeTemplate

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class BlkdatNamFiles(ModelResource):
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
                date = dict(
                    type     = Date,
                    optional = True,
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
