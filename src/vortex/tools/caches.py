#!/bin/env python
# -*- coding:Utf-8 -*-

"""
This package handles cache objects that could be in charge of
hosting data resources. Cache objects use the :mod:`footprints` mechanism.
"""

#: No automatic export
__all__ = []

import footprints

from vortex.autolog import logdefault as logger
from vortex.tools.config import GenericConfigParser


class Cache(footprints.FootprintBase):
    """Root class for any :class:Cache subclasses."""

    _abstract  = True
    _collector = ('cache',)
    _footprint = dict(
        info = 'Default cache description',
        attr = dict(
            config = dict(
                type     = GenericConfigParser,
                optional = True,
                default  = None,
            ),
            inifile = dict(
                optional = True,
                default  = 'cache-[storage].ini',
            ),
            iniauto = dict(
                type     = bool,
                optional = True,
                default  = True,
            ),
            kind = dict(
                values   = [ 'std' ]
            ),
            rootdir = dict(
                optional = True,
                default  = '/tmp'
            ),
            headdir = dict(
                optional = True,
                default  = 'cache',
            ),
            storage = dict(
                optional = True,
                default  = 'localhost'
            ),
            record = dict(
                type     = bool,
                optional = True,
                default  = False,
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
                values   = [ 'mtool', 'swapp' ],
                remap    = dict(swapp = 'mtool'),
            ),
            rootdir = dict(
                optional = True,
                default  = 'auto'
            ),
            headdir = dict(
                optional = True,
                default  = 'vortex',
            ),
        )
    )

    def entry(self, system):
        """Tries to figure out what could be the actual entry point for cache space."""
        if self.rootdir == 'auto':
            e = system.env
            if e.MTOOL_STEP_CACHE and system.path.isdir(e.MTOOL_STEP_CACHE):
                cache = e.MTOOL_STEP_CACHE
                logger.info('Using %s mtool step cache %s', self, cache)
            elif e.MTOOLDIR and system.path.isdir(e.MTOOLDIR):
                cache = system.path.join(e.MTOOLDIR, 'cache')
                logger.info('Using %s mtool dir cache %s', self, cache)
            else:
                cache = system.path.join(e.FTDIR or e.WORKDIR or e.TMPDIR, self.kind, 'cache')
                logger.info('Using %s default cache %s', self, cache)
        else:
            cache = self.actual_rootdir
        return system.path.join(cache, self.actual_headdir)

