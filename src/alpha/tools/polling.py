#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

from bronx.fancies import loggers

from vortex.tools import addons

#: Export nothing
__all__ = []

logger = loggers.getLogger(__name__)


class IO_Poll_Alpha(addons.Addon):
    """
    Scpecific script for polling files. 
    """
    _footprint = dict(
        info = 'Default io_poll alpha system interface',
        attr = dict(
            kind = dict(
                values  = ['iopoll_alpha'],
            ),
            interpreter = dict(
                values  = ['bash', 'sh','ksh'],
                default = 'sh',
                optional = True,
            ),
            toolkind = dict(
                default = 'iopoll'
            )
        )
    )

    def iopoll_alpha(self, vconf):  # @UnusedVariable
        """Do the actual job of polling files prefixed by ``prefix``."""
        logger.info("Execution IOPOLL Alpha")
        cmd = [vconf]
        # Catch the processed files in the stdout flux of the script
        rawout = self._spawn(cmd)
        # Cumulative results
        return rawout
