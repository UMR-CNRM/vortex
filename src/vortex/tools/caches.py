#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
This package handles cache objects that could be in charge of
hosting data resources. Cache objects use the :mod:`footprints` mechanism.
"""

from datetime import datetime

import footprints
from vortex import sessions
from vortex.util.config import GenericConfigParser
from vortex.util.structs import History

#: No automatic export
__all__ = []

logger = footprints.loggers.getLogger(__name__)


class Storage(footprints.FootprintBase):
    """Root class for any Storage class, ex: Cache"""

    _abstract = True,
    _footprint = dict(
        info = 'Default storage place description',
        attr = dict(
            config=dict(
                type=GenericConfigParser,
                optional=True,
                default=None,
            ),
            inifile=dict(
                optional=True,
                default='@storage-[storage].ini',
            ),
            iniauto=dict(
                type=bool,
                optional=True,
                default=True,
            ),
            kind=dict(
                values=['generic'],
            ),
            rootdir=dict(
                optional=True,
                default='default',
            ),
            headdir=dict(
                optional=True,
                default='default',
            ),
            storage=dict(
                optional=True,
                default='default',
            ),
            record=dict(
                type=bool,
                optional=True,
                default=False,
                access='rwx',
            ),
            readonly=dict(
                type=bool,
                optional=True,
                default=False,
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Abstract storage init %s', self.__class__)
        super(Storage, self).__init__(*args, **kw)
        self._actual_config = self.config
        if self._actual_config is None:
            self._actual_config = GenericConfigParser(inifile=self.inifile, mkforce=self.iniauto)
        self._history = History(tag=self.entry)

    @property
    def realkind(self):
        return 'storage'

    @property
    def sh(self):
        return sessions.system()

    @property
    def history(self):
        return self._history

    def actual(self, attr):
        """Return the actual attribute, either defined in config or plain attribute."""
        thisattr = getattr(self, attr, 'conf')
        if thisattr == 'conf':
            if self._actual_config.has_option(self.kind, attr):
                thisattr = self._actual_config.get(self.kind, attr)
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
        """Tries to figure out what could be the actual entry point for storage space."""
        return self.sh.path.join(self.actual_rootdir, self.kind, self.actual_headdir)

    def fullpath(self, subpath):
        """Actual full path in the storage place."""
        return self.sh.path.join(self.entry, subpath.lstrip('/'))

    def addrecord(self, action, item, **infos):
        """Push a new record to the storage place log."""
        if self.actual_record:
            self.history.append(action, item, infos)

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

    def catalog(self):
        """List all files present in this storage place (for cache mainly).

        NB: It might be quite slow...
        """
        entry = self.sh.path.expanduser(self.entry)
        files = self.sh.ffind(entry)
        return [f[len(entry):] for f in files]

    def _recursive_touch(self, rc, item):
        """Make recursive touches on parent directories.

        It might be usefull for cleaning scripts.
        """
        if self.rtouch and (not self.readonly) and rc:
            items = item.lstrip('/').split('/')
            if len(items) > 2:
                items = items[:-2]  # It's useless to touch the rightmost directory
                for index in range(len(items), self.rtouchskip, -1):
                    self.sh.touch(self.fullpath(self.sh.path.join(*items[:index])))

    def insert(self, item, local, **kwargs):
        """Insert an item in the current storage place."""
        pass

    def retrieve(self, item, local, **kwargs):
        """Retrieve an item from the current storage place."""
        pass

    def delete(self, item, **kwargs):
        """Delete an item from the current storage place."""
        pass

    def check(self, item, **kwargs):
        """Check/Stat an item from the current storage place."""
        pass


class Cache(Storage):
    """Root class for any :class:Cache subclasses."""

    _abstract  = True
    _collector = ('cache',)
    _footprint = dict(
        info = 'Default cache description',
        attr = dict(
            inifile = dict(
                optional = True,
                default  = '@cache-[storage].ini',
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
            rtouch = dict(
                type     = bool,
                optional = True,
                default  = False,
            ),
            rtouchskip = dict(
                type     = int,
                optional = True,
                default  = 0,
            ),
        )
    )

    def check(self, item, **kwargs):
        """Check/Stat an item from the current cache."""
        try:
            st = self.system.stat(self.incachelocate(item, kwargs))
        except OSError:
            st = None
        return st

    def __init__(self, *args, **kwargs):
        logger.debug('Abstract cache init %s', self.__class__)
        super(Cache, self).__init__(*args, **kwargs)

    @property
    def realkind(self):
        return 'cache'

    def insert(self, item, local, **kwargs):
        """Insert an item in the current cache."""
        # Get the relevant options
        intent = kwargs.get("intent", "in")
        fmt = kwargs.get("fmt", "foo")
        info = kwargs.get("info", None)
        # Insert the element
        if self.readonly:
            raise IOError("This Cache is readonly.")
        rc = self.sh.cp(local, self.fullpath(item), intent=intent, fmt=fmt)
        self._recursive_touch(rc, item)
        self.addrecord('INSERT', item, status=rc, info=info, fmt=fmt, intent=intent)
        return rc

    def retrieve(self, item, local, **kwargs):
        """Retrieve an item from the current cache."""
        # Get the relevant options
        intent = kwargs.get("intent", "in")
        fmt = kwargs.get("fmt", "foo")
        info = kwargs.get("info", None)
        silent = kwargs.get("silent", False)
        dirextract = kwargs.get("dirextract", False)
        tarextract = kwargs.get("tarextract", False)
        uniquelevel_ignore = kwargs.get("uniquelevel_ignore", True)
        source = self.fullpath(item)
        # If auto_dirextract, copy recursively each file contained in source
        if dirextract and self.sh.path.isdir(source) and self.sh.is_tarname(local):
            rc = True
            destdir = self.sh.path.dirname(self.sh.path.realpath(local))
            logger.info('Automatic directory extract to: %s', destdir)
            for subpath in self.sh.glob(source + '/*'):
                rc = rc and self.sh.cp(subpath,
                                       self.sh.path.join(destdir, self.sh.path.basename(subpath)),
                                       intent=intent, fmt=fmt)
                # For the insitu feature to work...
                rc = rc and self.sh.touch(local)
        # The usual case: just copy source
        else:
            rc = self.sh.cp(source, local, intent=intent, fmt=fmt, silent=silent)
            # If auto_tarextract, a potential tar file is extracted
            if (rc and tarextract and not self.sh.path.isdir(local) and
                    self.sh.is_tarname(local) and self.sh.is_tarfile(local)):
                destdir = self.sh.path.dirname(self.sh.path.realpath(local))
                logger.info('Automatic Tar extract to: %s', destdir)
                rc = rc and self.sh.smartuntar(local, destdir, output=False,
                                               uniquelevel_ignore=uniquelevel_ignore)
        self._recursive_touch(rc, item)
        self.addrecord('RETRIEVE', item, status=rc, info=info, fmt=fmt, intent=intent)
        return rc

    def delete(self, item, **kwargs):
        """Delete an item from the current cache."""
        # Get the relevant options
        fmt = kwargs.get("fmt", "foo")
        info = kwargs.get("info", None)
        # Delete the element
        if self.readonly:
            raise IOError("This Cache is readonly.")
        rc = self.sh.remove(self.fullpath(item), fmt=fmt)
        self.addrecord('DELETE', item, status=rc, info=info, fmt=fmt)
        return rc


class MtoolCache(Cache):
    """Cache items for the MTOOL jobs (or any job that acts like it)."""

    _footprint = dict(
        info = 'MTOOL like Cache',
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
            elif e.FTDIR or e.WORKDIR:
                cache = self.sh.path.join(e.FTDIR or e.WORKDIR, self.kind, 'cache')
                logger.debug('Using %s default cache %s', self, cache)
            else:
                logger.error('Unable to find an appropriate location for the cache space.')
                logger.error('Tip: Set either the MTOOLDIR, FTDIR or WORKDIR environment variables ' +
                             '(MTOOLDIR having the highest priority)')
                raise RuntimeError('Unable to find an appropriate location for the cache space')
        else:
            cache = self.actual_rootdir
        return self.sh.path.join(cache, self.actual_headdir)


class FtStashCache(MtoolCache):
    """A place to store file to be sent with ftserv."""

    _footprint = dict(
        info = 'A place to store file to be sent with ftserv',
        attr = dict(
            kind = dict(
                values   = ['ftstash', ],
            ),
            headdir = dict(
                optional = True,
                default  = 'ftspool',
            ),
        )
    )


class Op2ResearchCache(Cache):
    """Cache of the operational suite (read-only)."""

    _footprint = dict(
        info = 'MTOOL like Operations Cache (read-only)',
        attr = dict(
            kind = dict(
                values   = ['op2r_primary', 'op2r_secondary'],
            ),
            rootdir = dict(
                optional = True,
                default  = 'auto'
            ),
            headdir = dict(
                optional = True,
                default  = 'vortex',
            ),
            readonly = dict(
                default = True,
            )
        )
    )

    @property
    def entry(self):
        if self.rootdir == 'auto':
            fs = self.sh.default_target.get('op:' + self.kind[5:] + 'fs', '')
            mt = self.sh.default_target.get('op:mtooldir', None)
            if mt is None:
                raise ValueError("The %s cache can't be initialised since op:mtooldir is missing",
                                 self.kind)
            cache = fs + mt if mt.startswith('/') else self.sh.path.join(fs, mt)
            cache = self.sh.path.join(cache, 'cache')
        else:
            cache = self.actual_rootdir
        return self.sh.path.join(cache, self.actual_headdir)


class HackerCache(Cache):
    """A dirty cache where users can hack things."""

    _footprint = dict(
        info = 'A place to hack things...',
        attr = dict(
            kind = dict(
                values   = ['hack'],
            ),
            rootdir = dict(
                optional = True,
                default  = 'auto'
            ),
            readonly = dict(
                default = True,
            ),
        )
    )

    @property
    def entry(self):
        """Tries to figure out what could be the actual entry point for cache space."""
        sh = self.sh
        if self.rootdir == 'auto':
            gl = sessions.current().glove
            sweethome = sh.path.join(gl.configrc, 'hack')
            sh.mkdir(sweethome)
            logger.debug('Using %s hack cache: %s', self, sweethome)
        else:
            sweethome = self.actual_rootdir
        return sh.path.join(sweethome, self.actual_headdir)


class Archive(Storage):
    """Root class for any :class:Archive subclasses."""

    _abstract  = True
    _collector = ('archive',)
    _footprint = dict(
        info = 'Default archive description',
        attr = dict(
            inifile = dict(
                optional = True,
                default  = '@archive-[storage].ini',
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
                default  = 'sto',
            ),
            storage = dict(
                optional = True,
                default  = 'localhost',
            ),
            scheme = dict(
                optional = True,
                default = "file",
                values = ['ftp', 'ftserv', 'scp', 'rcp', 'ectrans', 'ecfs', 'file']
            )
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Abstract archive init %s', self.__class__)
        super(Archive, self).__init__(*args, **kw)

    @property
    def realkind(self):
        return 'archive'

    def check(self, item, **kwargs):
        """Check/Stat an item from the current archive."""
        if isinstance(self.scheme, ['ftp', 'ftserv']):
            pass
        elif isinstance(self.scheme, ['ectrans']):
            pass
        elif isinstance(self.scheme, ['ecfs']):
            pass
        elif isinstance(self.scheme, ['rcp']):
            pass
        elif isinstance(self.scheme, ['scp']):
            pass
        elif isinstance(self.scheme, ['file']):
            pass
        return False

    def insert(self, item, local, **kwargs):
        """Insert an item in the current archive."""
        pass

    def retrieve(self, item, local, **kwargs):
        """Retrieve an item from the current archive."""
        pass

    def delete(self, item, **kwargs):
        """Delete an item from the current archive."""
        pass


class VortexArchive(Archive):
    """Archive items for the Vortex like applications"""

    _footprint = dict(
        info = 'Vortex like archive',
        attr = dict(
            kind = dict(
                values   = ['vortex'],
            ),
            rootdir = dict(
                optional = True,
                default  = 'auto'
            ),
            headdir = dict(
                optional = True,
                default  = 'vortex',
                outcast = ['xp',],
            ),
            storage = dict(
                optional = True,
                default = "hendrix.meteo.fr",
            ),
        )
    )

    @property
    def entry(self):
        """Tries to figure out what could be the actual entry point for archive space."""
        if self.rootdir == 'auto':
            pass
        else:
            archive = self.actual_rootdir
        return self.sh.path.join(archive, self.actual_headdir)


class OliveArchive(Archive):
    """Archive items for the Olive like applications"""

    _footprint = dict(
        info = 'Olive like archive',
        attr = dict(
            kind = dict(
                values   = ['olive'],
            ),
            rootdir = dict(
                optional = True,
                default  = 'auto'
            ),
            headdir = dict(
                optional = True,
                default  = 'xp',
                outcast = ['olive',],
            ),
            storage = dict(
                optional = True,
                default = "hendrix.meteo.fr",
            ),
        )
    )

    @property
    def entry(self):
        """Tries to figure out what could be the actual entry point for archive space."""
        if self.rootdir == 'auto':
            pass
        else:
            archive = self.actual_rootdir
        return self.sh.path.join(archive, self.actual_headdir)


class OpArchive(Archive):
    """Archive items for the old operational applications in ksh"""

    _footprint = dict(
        info = 'Old operational like archive',
        attr = dict(
            kind = dict(
                values   = ['op-ksh'],
            ),
            rootdir = dict(
                optional = True,
                default  = 'auto'
            ),
            headdir = dict(
                optional = True,
                default  = None,
            ),
            storage = dict(
                optional = True,
                default = "hendrix.meteo.fr",
            ),
        )
    )

    @property
    def entry(self):
        """Tries to figure out what could be the actual entry point for archive space."""
        if self.rootdir == 'auto':
            pass
        else:
            archive = self.actual_rootdir
        return self.sh.path.join(archive, self.actual_headdir)
