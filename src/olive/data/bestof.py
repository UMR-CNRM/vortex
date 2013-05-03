#!/bin/env python
# -*- coding:Utf-8 -*-

r"""
Obsolescent package to define ressources that should now be defined inside
the shared package :mod:`common` and more specifically in subpackage :mod:`common.data`.
"""

#: No automatic export
__all__ = []

from vortex.data.flow import FlowResource


class InflFactor(FlowResource):
    
    _footprint = dict(
        info = 'Inflation factor file',
        attr = dict(
            kind = dict(
                values = [ 'inflfactor' ]
            ),
        )
    )
    
    @property
    def realkind(self):
        return 'inflfactor'

    def basename_info(self):
        return dict(radical='inflfactor', src=self.model)
      
    def olive_basename(self):
        return ('inflation_factor')
    
    def archive_basename(self):
        return ('inflation_factor')
