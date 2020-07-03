#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
TODO: module documentation.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

from bronx.fancies import loggers

from vortex.tools import addons

#: Export nothing
__all__ = []

logger = loggers.getLogger(__name__)


class IO_Poll_Mocage(addons.Addon):
    """TODO class documentation."""

    # fmt: off
    _footprint = dict(
        info = 'Default io_poll mocage system interface',
        attr = dict(
            kind = dict(
                values  = ['iopoll_mocage', ],
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
    # fmt: on

    def iopoll_mocage(self, prefix, vconf):  # @UnusedVariable
        """Do the actual job of polling files prefixed by ``prefix``."""
        logger.info("Execution IOPOLL Mocage")
        # Call the script get from GCO historisation with toolkind=iopoll
        # with 2 args : the vconf caller and the prefix (optional)
        cmd = [vconf, ]
        # Catch the processed files in the stdout flux of the script
        rawout = self._spawn(cmd)
        # Cumulative results
        return rawout


class IopollMocacc(addons.Addon):
    """Polling for MOCAGE Accident.
    """

    # fmt: off
    _footprint           = dict(
        info             = 'Default io_poll mocage accident system interface',
        attr             = dict(
            kind         = dict(
                values   = ['iopoll_mocacc'],
            ),
            interpreter  = dict(
                values   = ['python', 'bash', 'sh'],
                default  = 'python',
                optional = True,
            ),
            toolkind     = dict(
                default  = 'iopoll'
            ),
        )
    )
    # fmt: on

    def iopoll_mocacc(self, prefix, witness, donefile, regex):  # @UnusedVariable
        """Do the actual job of polling files prefixed by ``prefix``."""
        logger.info("Execution IOPOLL Mocage")
        # Call the script get from GCO historisation with toolkind=iopoll
        cmd = ["--witness", witness, "--donefile", donefile, "--regex", regex]
        # Catch the processed files in the stdout flux of the script
        rawout = self._spawn(cmd)
        # Cumulative results
        return rawout
