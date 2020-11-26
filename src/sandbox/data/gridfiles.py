#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
TODO: Module documentation
"""

from __future__ import print_function, absolute_import, unicode_literals, division

from vortex.data.contents import JsonDictContent
from vortex.data.flow import FlowResource

#: No automatic export
__all__ = []


class GribInfos(FlowResource):
    """List of available GRIB files with file size and md5sum."""

    _footprint = dict(
        info = 'Available GRIB files with file size and md5sum.',
        attr = dict(
            kind = dict(
                values   = ['gribinfos', ],
            ),
            clscontents = dict(
                default = JsonDictContent,
            ),
            nativefmt   = dict(
                values  = ['json'],
                default = 'json',
            ),
        )
    )

    @property
    def realkind(self):
        return 'gribinfos'
