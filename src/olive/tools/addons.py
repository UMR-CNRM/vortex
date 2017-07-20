#!/usr/bin/env python
# -*- coding: utf-8 -*-

from vortex.tools.addons import AddonGroup

# Load the proper Addon modules...
import common.tools.addons  # @UnusedImport
import common.tools.gribdiff  # @UnusedImport

#: No automatic export
__all__ = []


class OliveAddonsGroup(AddonGroup):
    """A set of usual Olive Addons."""

    _footprint = dict(
        info = 'Default Olive Addons',
        attr = dict(
            kind = dict(
                values = ['olive', ],
            ),
        )
    )

    _addonslist = ('nwp', )  # This is a group of groups !
