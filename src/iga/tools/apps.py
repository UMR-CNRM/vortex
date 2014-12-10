#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []


import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.layout.nodes import Task

from . import op

class OpTask(Task):
    """Wrapper for setting up and performing a miscellaneous op task."""

    _tag_topcls = False

    def register_cycle(self, cycle):
        """Register a given GCO cycle."""
        self.header('GCO cycle ' + cycle)
        op.register(self.ticket, cycle)

    def defaults(self, extras):
        """Set defaults for toolbox defaults, with priority to actual conf."""
        extras.setdefault('namespace', self.conf.get('namespace', 'vortex.cache.fr'))
        extras.setdefault('gnamespace', self.conf.get('gnamespace', 'opgco.cache.fr'))
        super(OpTask, self).defaults(extras)
