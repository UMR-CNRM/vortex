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


class IO_Poll_Marine(addons.Addon):
    """TODO: Class documentation."""
    _footprint = dict(
        info = 'Default io_poll marine system interface',
        attr = dict(
            kind = dict(
                values  = ['iopoll_marine', 'iopoll_waves', 'iopoll_ww3'],
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

    def iopoll_marine(self, prefix, model=None, forcage=None, pollingdir=['RES0.']):
        """Do the actual job of polling files prefixed by ``prefix``."""
        logger.info("Execution IOPOLL Marine")
        if model and forcage is not None:
            cmd = ['--model', model, '--forcage', forcage]
        else:
            cmd = []
        cmd.extend(['--prefix', prefix])

        logger.info("cmd: %s", cmd)
        strpollingdir = ','.join(x for x in pollingdir)
        cmd.extend(['--pollingdir', strpollingdir])
        logger.info("cmd: %s", cmd)
        # Catch the processed file
        rawout = self._spawn(cmd)
        # Cumulative results
        return rawout

    def iopoll_waves(self, prefix, model=None, forcage=None):
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

    def iopoll_ww3(self, prefix, datpivot, stepout=3):
        """Do the actual job of polling files prefixed by ``prefix``."""
        logger.info("Execution IOPOLL WW3")

        cmd = ['--logout', prefix]
        cmd.extend(['--datpivot', datpivot])
        cmd.extend(['--stepout', stepout])
        logger.info("cmd: %s", cmd)
        rawout = self._spawn(cmd)
        return rawout
