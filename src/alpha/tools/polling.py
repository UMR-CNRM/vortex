#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
TODO: Module documentation
"""

from __future__ import print_function, absolute_import, unicode_literals, division

from bronx.fancies import loggers

from vortex.tools import addons

#: Export nothing
__all__ = []

logger = loggers.getLogger(__name__)


class IO_Poll_Alpha(addons.Addon):
    """Specific script for polling files produce by an Alpha script/executable."""
    _footprint = dict(
        info = 'Default io_poll alpha system interface',
        attr = dict(
            kind = dict(
                values  = ['iopoll_alpha'],
            ),
            interpreter = dict(
                values  = ['bash', 'sh', 'ksh'],
                default = 'sh',
                optional = True,
            ),
            toolkind = dict(
                default = 'iopoll'
            )
        )
    )

    def iopoll_alpha(self, prefix, domain):  # @UnusedVariable
        """Do the actual job of polling files prefixed by ``prefix``."""
        logger.info("IOPOLL Alpha execution")
        cmd = ['--domain', domain]
        # Catch the processed files in the stdout flux of the script
        rawout = self._spawn(cmd)
        # Cumulative results
        return rawout
