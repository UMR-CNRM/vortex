#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

from bronx.fancies import loggers

from vortex.tools import addons

#: Export nothing
__all__ = []

logger = loggers.getLogger(__name__)


class IO_Poll_Marine(addons.Addon):
    """
    """
    _footprint = dict(
        info = 'Default io_poll marine system interface',
        attr = dict(
            kind = dict(
                values  = ['iopoll_marine'],
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

    def iopoll_marine(self, prefix, model=None, forcage=None):
        """Do the actual job of polling files prefixed by ``prefix``."""
        logger.info("Execution IOPOLL Marine")
        cmd = ['--prefix', prefix]
        if model is not None:
            cmd.extend(['--model', model])
        if forcage is not None:
            cmd.extend(['--forcage', forcage])
        logger.info("cmd: %s", cmd)

        # Catch the processed file
        rawout = self._spawn(cmd)
        # Cumulative results
        return rawout
