#!/bin/env python
# -*- coding:Utf-8 -*-

r"""
This package handles target computers objects that could in charge of
hosting a specific execution. The associated modules defines the catalog
factory based on the shared footprint mechanism.
"""

#: No automatic export
__all__ = []

import re, sys

from vortex.autolog import logdefault as logger
from vortex.syntax import BFootprint
from vortex.utilities.catalogs import ClassesCollector, cataloginterface


class Target(BFootprint):
    """Root class for any :class:`Target` subclasses."""

    def __init__(self, *args, **kw):
        logger.debug('Abstract target computer init %s', self.__class__)
        super(Target, self).__init__(*args, **kw)
    
    @property
    def realkind(self):
        return 'target'


class TargetsCatalog(ClassesCollector):
    """Class in charge of collecting :class:`Target` items."""

    def __init__(self, **kw):
        logger.debug('Target computers catalog init %s', self)
        cat = dict(
            remod = re.compile(r'.*\.targets'),
            classes = [ Target ],
            itementry = 'target'
        )
        cat.update(kw)
        super(TargetsCatalog, self).__init__(**cat)

    @classmethod
    def tablekey(cls):
        return 'targets'


cataloginterface(sys.modules.get(__name__), TargetsCatalog)
