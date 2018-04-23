#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import footprints

from vortex.tools import addons

#: Export nothing
__all__ = []

logger = footprints.loggers.getLogger(__name__)


class IO_Poll_Mocage(addons.Addon):
    """
    """
    _footprint = dict(
        info = 'Default io_poll mocage system interface',
        attr = dict(
            kind = dict(
                values  = ['iopoll_mocage' ],
            ),
            interpreter = dict(
                values  = ['bash', 'sh'],
                default = 'sh',
                optional = True,
            ),
            toolkind = dict(
                default = 'iopoll'
            )
        )
    )

    def iopoll_mocage(self, prefix, vconf):
        """Do the actual job of polling files prefixed by ``prefix``."""
        logger.info("Execution IOPOLL Mocage")
        # Call the script get from GCO historisation with toolkind=iopoll
        # with 2 args : the vconf caller and the prefix (optional)
        cmd = [vconf, ]
        # Catch the processed files in the stdout flux of the script
        rawout = self._spawn(cmd)
        # Cumulative results
        return rawout
