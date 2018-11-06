#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

from vortex.tools.addons import AddonGroup

# Load the proper Addon modules...
import vortex.tools.folder  # @UnusedImport
import vortex.tools.lfi  # @UnusedImport
import vortex.tools.grib  # @UnusedImport
import vortex.tools.listings  # @UnusedImport
import vortex.tools.surfex  # @UnusedImport

#: No automatic export
__all__ = []


class NWPAddonsGroup(AddonGroup):
    """A set of usual NWP Addons."""

    _footprint = dict(
        info = 'Default NWP Addons',
        attr = dict(
            kind = dict(
                values = ['nwp', ],
            ),
        )
    )

    _addonslist = ('allfolders',  # Folder like...
                   'lfi', 'iopoll',  # Wonderful FA/LFI world...
                   'grib', 'gribapi',  # GRIB stuff...
                   'arpifs_listings',  # Obscure IFS/Arpege listings...
                   'sfx',  # Surfex...
                   )
