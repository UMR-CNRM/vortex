#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

from vortex.tools.addons import AddonGroup

# Load the proper Addon modules...
from . import polling  # @UnusedImport

#: No automatic export
__all__ = []


class MarineAddonsGroup(AddonGroup):
    """A set of usual Marine Addons."""

    _footprint = dict(
        info = 'Default Marine Addons',
        attr = dict(
            kind = dict(
                values = ['marine', ],
            ),
        )
    )

    _addonslist = ('iopoll_marine',  # IO polling
                   )