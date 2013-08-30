#!/bin/env python
# -*- coding:Utf-8 -*-

"""
This package handles cache objects that could be in charge of
hosting data resources. The associated modules defines the catalog
factory based on the shared footprint mechanism.
"""

#: No automatic export
__all__ = []

import re, sys

from vortex.autolog import logdefault as logger
from vortex.syntax import BFootprint
from vortex.tools.config import GenericConfigParser
from vortex.utilities.catalogs import ClassesCollector, build_catalog_functions


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
                values = [ 'std' ]
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
            record = dict(
                optional = True,
                type = bool,
                default = False,
            )
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Abstract cache init %s', self.__class__)
        super(Cache, self).__init__(*args, **kw)
        self._logrecord = list()
        if not self.config:
            self._attributes['config'] = GenericConfigParser(inifile=self.inifile, mkforce=self.iniauto)

    @property
    def realkind(self):
        return 'cache'

    @property
    def logrecord(self):
        return self._logrecord[:]

    def actual(self, attr):
        """Return the actual attribute, either defined in config or plain attribute."""
        thisattr = self._attributes.get(attr, 'conf')
        if thisattr == 'conf':
            if self.config.has_option(self.kind, attr):
                thisattr = self.config.get(self.kind, attr)
            else:
                raise AttributeError('Could not find default ' + attr + ' in config.')
        return thisattr

    @property
    def actual_rootdir(self):
        return self.actual('rootdir')

    @property
    def actual_headdir(self):
        return self.actual('headdir')

    @property
    def actual_record(self):
        return self.actual('record')

    def entry(self, system):
        """Tries to figure out what could be the actual entry point for cache space."""
        return system.path.join(self.actual_rootdir, self.kind, self.actual_headdir)

    def flushrecord(self):
        """Clear the log record."""
        rlog = self._logrecord[:]
        self._logrecord = list()
        return rlog

    def addrecord(self, action, item, infos):
        """Push a new record to the cache log."""
        if self.actual_record:
            self._logrecord.append([item, action, infos])

    def insert(self, item, infos=None):
        """Insert an item in the current cache."""
        self.addrecord('insert', item, infos)

    def retrieve(self, item, infos=None):
        """Insert an item in the current cache."""
        self.addrecord('retrieve', item, infos)

    def delete(self, item, infos=None):
        """Insert an item in the current cache."""
        self.addrecord('delete', item, infos)


class MtoolCache(Cache):
    """Cache items for the MTOOL jobs."""

    _footprint = dict(
        info = 'Default cache description',
        attr = dict(
            kind = dict(
                values = [ 'mtool', 'swapp' ],
                remap = dict(
                    swapp = 'mtool'
                ),
            ),
            rootdir = dict(
                optional = True,
                default = 'auto'
            ),
            headdir = dict(
                optional = True,
                default = 'vortex',
            ),
        )
    )

    def entry(self, system):
        """Tries to figure out what could be the actual entry point for cache space."""
        if ( self.rootdir == 'auto' ):
            e = system.env
            if e.MTOOL_STEP_CACHE and system.path.isdir(e.MTOOL_STEP_CACHE):
                cache = e.MTOOL_STEP_CACHE
                logger.info('Using %s mtool cache %s', self, cache)
            else:
                cache = system.path.join(e.FTDIR or e.WORKDIR or e.TMPDIR, self.kind)
                logger.info('Using %s default cache %s', self, cache)
        else:
            cache = self.actual_rootdir
        return system.path.join(cache, self.actual_headdir)


class CachesCatalog(ClassesCollector):
    """Class in charge of collecting :class:`Cache` items."""

    def __init__(self, **kw):
        """
        Define defaults regular expresion for module search, list of tracked classes
        and the item entry name in pickled footprint resolution.
        """
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
        """The entry point for global catalogs table. -- Here: caches."""
        return 'caches'


build_catalog_functions(sys.modules.get(__name__), CachesCatalog)
