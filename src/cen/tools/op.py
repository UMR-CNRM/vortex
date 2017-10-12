#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []


import vortex  # @UnusedImport
import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.layout.jobs import JobAssistant


class CenJobAssistant(JobAssistant):

    _footprint = dict(
        info = 'Cen Job assistant.',
        attr = dict(
            kind = dict(
                values = ['cen'],
            ),
        ),
    )

    def register_cycle(self, cycle):
        """Load and register a cycle contents."""
        from gco.syntax.stdattrs import UgetId
        try:
            cycle = UgetId(cycle)
        except ValueError:
            return
        from gco.tools import uenv
        if cycle in uenv.cycles():
            logger.info('Cycle %s already registered', cycle)
        else:
            pass
