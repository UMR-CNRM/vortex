#!/bin/env python
# -*- coding:Utf-8 -*-

"""
This package handles cache objects that could be in charge of
hosting data resources. The associated modules defines the catalog
factory based on the shared footprint mechanism.
"""

#: No automatic export
__all__ = []

import re, sys, platform

from vortex.autolog import logdefault as logger
from vortex.syntax import BFootprint
from vortex.tools.config import GenericConfigParser
from vortex.utilities.catalogs import ClassesCollector, cataloginterface


class Cache(BFootprint):
    """Root class for any :class:Cache subclasses."""

    _footprint = dict(
        info = 'Default cache description',
        attr = dict(
            config = dict(
                optional = True,
                default = None,
                type = GenericConfigParser,
            ),
            inifile = dict(
                optional = True,
                default = 'cache-[storage].ini',
            ),
            iniauto = dict(
                optional = True,
                type = bool,
                default = True,
            ),
            kind = dict(
                values = [ 'tmp', 'mtool' ]
            ),
            rootdir = dict(
                optional = True,
                default = '/tmp'
            ),
            headdir = dict(
                optional = True,
                default = 'cache',
            ),
            storage = dict(
                optional = True,
                default = 'localhost'
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Abstract cache init %s', self.__class__)
        super(Cache, self).__init__(*args, **kw)
        if not self.config:
            self._attributes['config'] = GenericConfigParser(inifile=self.inifile, mkforce=self.iniauto)

    @property
    def realkind(self):
        return 'cache'

    def entry(self, system):
        """Tries to figure out what could be the actual entry point for cache space."""
        cache = self.rootdir
        e = system.env
        if ( self.kind == 'mtool' or ( e.SWAPP_OUTPUT_CACHE and e.SWAPP_OUTPUT_CACHE == 'mtool' ) ):
            if e.MTOOL_STEP_CACHE and system.path.isdir(e.MTOOL_STEP_CACHE):
                cache = e.MTOOL_STEP_CACHE
                logger.debug('Using %s mtool cache %s', self, cache)
            else:
                cache = e.FTDIR or e.WORKDIR or e.TMPDIR
                logger.debug('Using %s default cache %s', self, cache)
        return system.path.join(cache, self.headdir)


class UserCache(Cache):
    pass


class CachesCatalog(ClassesCollector):
    """Class in charge of collecting :class:`Cache` items."""

    def __init__(self, **kw):
        logger.debug('Caches catalog init %s', self)
        cat = dict(
            remod = re.compile(r'.*\.caches'),
            classes = [ Cache ],
            itementry = 'cache'
        )
        cat.update(kw)
        super(CachesCatalog, self).__init__(**cat)

    @classmethod
    def tablekey(cls):
        return 'caches'


cataloginterface(sys.modules.get(__name__), CachesCatalog)
