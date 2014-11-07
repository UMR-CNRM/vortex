#!/usr/bin/env python
# -*- coding:Utf-8 -*-

r"""
An empty module to be filled with some kind of blackholes objects.
"""

#: No automatic export
__all__ = []

import footprints
logger = footprints.loggers.getLogger(__name__)


class DataConst(object):
    """Constants stored as raw attributes."""

    def __init__(self, **kw):
        self.__dict__.update(kw)
        logger.debug('DataConst init %s', self)

    def __str__(self):
        return super(DataConst, self).__str__() + ' : ' + str(sorted(self.__dict__.keys()))

    def __contains__(self, item):
        return item in self.__dict__
