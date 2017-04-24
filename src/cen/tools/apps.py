#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []


import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.layout.nodes import Task


class CenTask(Task):
    """Wrapper for setting up and performing a miscellaneous cen task for a serial execution."""

    _tag_topcls = False


    def defaults(self, extras):
        """Set defaults for toolbox defaults, with priority to actual conf."""
        print self.conf
        extras.setdefault('namespace', self.conf.get('namespace', 'cen.cache.fr'))
        extras.setdefault('gnamespace', self.conf.get('gnamespace', 'cengco.cache.fr'))
        super(CenTask, self).defaults(extras)


