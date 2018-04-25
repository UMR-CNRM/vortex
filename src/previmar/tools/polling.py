#!/usr/bin/env python
# -*- coding: utf-8 -*-

import footprints

from vortex.tools import addons

#: Export nothing
__all__ = []

logger = footprints.loggers.getLogger(__name__)


class IO_Poll_Marine(addons.Addon):
    """
    """
    _footprint = dict(
        info = 'Default io_poll marine system interface',
        attr = dict(
            kind = dict(
                values  = ['iopoll_marine' ],
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

    def iopoll_marine(self, prefix, model=None):
        """Do the actual job of polling files prefixed by ``prefix``."""
        logger.info("Execution IOPOLL Marine")
        if model is not None:
            cmd = ['--model', model]
        else:
            cmd = []
        cmd.extend(['--prefix', prefix])
        # Catch the processed file
        rawout = self._spawn(cmd)
        # Cumulative results
        return rawout
