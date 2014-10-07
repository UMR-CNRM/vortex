#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
Proxy objects to footprints catalogs.
"""

#: No automatic export
__all__ = []

import logging
logger = logging.getLogger('footprints.proxies')

from . import collectors, util


# Module interface

def get(**kw):
    """Return actual proxy object matching description."""
    return FootprintProxy(**kw)


# Base class

class FootprintProxy(util.GetByTag):
    """Access to alive footprint items."""

    def __call__(self):
        self.cat()

    def __iter__(self):
        """Iterates over collectors."""
        for item in collectors.values():
            yield item

    def cat(self):
        """Print a list of all existing collectors."""
        for k, v in sorted(collectors.items()):
            print str(len(v)).rjust(4), (k+'s').ljust(16), v

    def catlist(self):
        """Return a list of tuples (len, name, collector) for all alive collectors."""
        return [ (len(v), k+'s', v) for k, v in sorted(collectors.items()) ]

    def objects(self):
        """Print the list of all existing objects tracked by the collectors."""
        for k, c in sorted(collectors.items()):
            objs = c.instances()
            print str(len(objs)).rjust(4), (k+'s').ljust(16), objs

    def objectsmap(self):
        """Return a dictionary of instances sorted by collectors entries."""
        return dict([ (k+'s', c.instances()) for k, c in collectors.items() ])

    def exists(self, tag):
        """Check if a given ``tag`` of objects is tracked or not."""
        return tag.rstrip('s') in collectors.keys()

    def __contains__(self, item):
        """Similar as ``self.exists(item)``."""
        return self.exists(item)

    def getitem(self, item, value=None):
        """Mimic the get access of a dictionary for defined collectors."""
        if item in self:
            return collectors.get(tag=item)
        else:
            return value

    def __getattr__(self, attr):
        """Gateway to collector (plural noun) or load method (singular)."""
        if attr.startswith('_') or attr not in self:
            return None
        else:
            if attr.endswith('s'):
                return collectors.get(tag=attr)
            else:
                return collectors.get(tag=attr).load
