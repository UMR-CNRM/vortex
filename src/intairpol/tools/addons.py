#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

from vortex.tools.addons import AddonGroup

# Load the proper Addon modules...
from . import polling  # @UnusedImport

#: No automatic export
__all__ = []


class MocageAddonsGroup(AddonGroup):
    """A set of usual Mocage Addons."""

    _footprint = dict(
        info = 'Default Mocage Addons',
        attr = dict(
            kind = dict(
                values = ['mocage', ],
            ),
        )
    )

    _addonslist = ('iopoll_mocage', )  # IO polling
