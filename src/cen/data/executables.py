#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.data.executables import BlackBox, Script, NivologyModel 
from gco.syntax.stdattrs import gdomain, GenvKey
from vortex.tools.date import Date


class Safran(NivologyModel):
    """Base class for the Safran model executables."""
    _footprint = [
        gdomain,
        dict(
            info = 'Safran module',
            attr = dict(
                kind = dict(
                    values = ['SafranAnalysis']
                ),
                gvar = dict(
                    type = GenvKey,
                ),
                model = dict(
                    values = ['safran', ],
                ),
                rundir = dict(
                    optional = True,
                    outcast  = '',
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'safran_module'

    def command_line(self, **opts):
        return ''

    
class PearpFiltering(Script):
    """Base class for the creation of P files used by SAFRAN."""    

    _footprint = [
        dict(
            info = 'Prepare the input files for SAFRAN',
            attr = dict(
                kind = dict(
                    values = ['PearpFiltering']
                ),
                gvar = dict(
                    type = GenvKey,
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'pearpfiltering'

