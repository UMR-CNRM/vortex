# -*- coding: utf-8 -*-

"""
Various addons needed to work confortably at ECMWF.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

from vortex.tools.addons import AddonGroup

# Load the proper Addon modules...
from . import ecfs  # @UnusedImport
from . import ectrans  # @UnusedImport

#: No automatic export
__all__ = []


class EcmwfAddonsGroup(AddonGroup):
    """A set of usual ECMWF Addons."""

    _footprint = dict(
        info = 'Default ECMWF Addons',
        attr = dict(
            kind = dict(
                values = ['ecmwf', ],
            ),
        )
    )

    _addonslist = ('ecfs', 'ectrans')
