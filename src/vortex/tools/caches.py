#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
This package handles cache objects that could be in charge of
hosting data resources. Cache objects use the :mod:`footprints` mechanism.
"""

#: No automatic export
__all__ = []

from datetime import datetime

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex import sessions
from vortex.util.config  import GenericConfigParser
from vortex.util.structs import History


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
                values   = ['std'],
            ),
            rootdir = dict(
                optional = True,
                default  = '/tmp',
            ),
            headdir = dict(
                optional = True,
                default  = 'cache',
            ),
            storage = dict(
                optional = True,
                default  = 'localhost',
            ),
            record = dict(
                type     = bool,
                optional = True,
                default  = False,
                access   = 'rwx',
            )
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Abstract cache init %s', self.__class__)
        super(Cache, self).__init__(*args, **kw)
        self._sh = sessions.system()
        if not self.config:
            self._attributes['config'] = GenericConfigParser(inifile=self.inifile, mkforce=self.iniauto)
        self._history = History(tag=self.entry)

    @property
    def realkind(self):
        return 'cache'

    @property
    def sh(self):
        return self._sh

    @property
    def history(self):
        return self._history

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

    @property
    def entry(self):
        """Tries to figure out what could be the actual entry point for cache space."""
        return self.sh.path.join(self.actual_rootdir, self.kind, self.actual_headdir)

    def fullpath(self, subpath):
        """Actual full path in the cache."""
        return self.sh.path.join(self.entry, subpath.lstrip('/'))

    def addrecord(self, action, item, **infos):
        """Push a new record to the cache log."""
        if self.actual_record:
            self.history.append(action, item, infos)

    def insert(self, item, local, intent='in', fmt='foo', info=None):
        """Insert an item in the current cache."""
        rc = self.sh.cp(local, self.fullpath(item), intent=intent, fmt=fmt)
        self.addrecord('INSERT', item, status=rc, info=info, fmt=fmt, intent=intent)
        return rc

    def retrieve(self, item, local, intent='in', fmt='foo', info=None):
        """Retrieve an item from the current cache."""
        source = self.fullpath(item)
        if self.sh.path.isdir(source) and local is None:
            rc = True
            for subpath in self.sh.glob(source + '/*'):
                rc = rc and self.sh.cp(subpath, self.sh.path.basename(subpath), intent=intent, fmt=fmt)
        else:
            rc = self.sh.cp(source, local, intent=intent, fmt=fmt)
        self.addrecord('RETRIEVE', item, status=rc, info=info, fmt=fmt, intent=intent)
        return rc

    def delete(self, item, fmt='foo', info=None):
        """Delete an item from the current cache."""
        rc = self.sh.remove(self.fullpath(item), fmt=fmt)
        self.addrecord('DELETE', item, status=rc, info=info, fmt=fmt)

    def flush(self, dumpfile=None):
        """Flush actual history to the specified ``dumpfile`` if record is on."""
        if dumpfile is None:
            logfile = '.'.join((
                'HISTORY',
                datetime.now().strftime('%Y%m%d%H%M%S.%f'),
                'P{0:06d}'.format(self.sh.getpid()),
                self.sh.getlogname()
            ))
            dumpfile = self.sh.path.join(self.entry, '.history', logfile)
        if self.actual_record:
            self.sh.pickle_dump(self.history, dumpfile)


class MtoolCache(Cache):
    """Cache items for the MTOOL jobs."""

    _footprint = dict(
        info = 'Default cache description',
        attr = dict(
            kind = dict(
                values   = ['mtool', 'swapp'],
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

    @property
    def entry(self):
        """Tries to figure out what could be the actual entry point for cache space."""
        if self.rootdir == 'auto':
            e = self.sh.env
            if e.MTOOL_STEP_CACHE and self.sh.path.isdir(e.MTOOL_STEP_CACHE):
                cache = e.MTOOL_STEP_CACHE
                logger.debug('Using %s mtool step cache %s', self, cache)
            elif e.MTOOLDIR and self.sh.path.isdir(e.MTOOLDIR):
                cache = self.sh.path.join(e.MTOOLDIR, 'cache')
                logger.debug('Using %s mtool dir cache %s', self, cache)
            else:
                cache = self.sh.path.join(e.FTDIR or e.WORKDIR or e.TMPDIR, self.kind, 'cache')
                logger.debug('Using %s default cache %s', self, cache)
        else:
            cache = self.actual_rootdir
        return self.sh.path.join(cache, self.actual_headdir)

