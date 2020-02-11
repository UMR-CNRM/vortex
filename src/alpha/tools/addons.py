#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
TODO: Module documentation
"""

from __future__ import print_function, absolute_import, unicode_literals, division

from vortex.tools.addons import AddonGroup

# Load the proper Addon modules...
from . import polling  # @UnusedImport

#: No automatic export
__all__ = []


class AlphaAddonsGroup(AddonGroup):
    """A set of usual Alpha Addons."""

    _footprint = dict(
        info = 'Default Alpha Addons',
        attr = dict(
            kind = dict(
                values = ['alpha', ],
            ),
        )
    )

    _addonslist = ('iopoll_alpha',)  # IO polling
