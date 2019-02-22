#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Various config files.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

from vortex.data.outflow import StaticResource
from gco.syntax.stdattrs import gvar
from vortex.data.contents import JsonDictContent

#: No automatic export
__all__ = []


class OOPSConfig(StaticResource):
    """
    Configuration files for OOPS, defining the oops objects to be built
    """
    _footprint = [
        gvar,
        dict(
            info = 'Oops config from a pack of',
            attr = dict(
                kind = dict(
                    values   = ['oopsconfig']
                ),
                gvar = dict(
                    default  = 'config_oops'
                ),
                objects=dict(
                    info="objects to be built"
                ),
                source = dict(
                    info        = 'The config name within the config pack.',
                    optional    = True,
                    default     = '[objects].json',
                ),
                clscontents = dict(
                    default  = JsonDictContent
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'oopsconfig'

    def gget_urlquery(self):
        """GGET specific query : ``extract``."""
        return 'extract=' + self.source
