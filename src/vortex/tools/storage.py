#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
This package handles :class:`Storage` objects that could be in charge of
hosting data resources both locally ("Cache") or on a remote host "Archive").

* :class:`Storage` is the main abstract class that defines the user-interface for
  every classes of this module. :meth:`Storage.fullpath`, :meth:`Storage.check`,
  :meth:`Storage.insert`, :meth:`Storage.retrieve` and :meth:`Storage.delete` are
  frequently used form a user point of view.
* The :class:`Cache` abstract class is a specialisation of the :class:`Storage`
  class that handles data resources locally (i.e. data hosted on the same machine
  that are readily and timelessly accessible). In this module, various concrete
  implementations are provided for this class in order to support various cache
  flavor.
* The :class:`Archive` class (readily usable) is a specialisation of the
  :class:`Storage` class dedicated to data resources stored remotely (e.g on a
  mass archive system).

These classes purely focus on the technical aspects (e.g. how to transfer a given
filename, directory or file like object to its storage place ?). For :class:`Cache`
based storage it determines the location of the data on the filesystem, in a
database, ... For :class:`Archive` based storage it smoothly handles communication
protocol between the local host and the remote archive.

These classes are used by :class:`Store` objects to access data. Thus,
:class:`Store` objects do not need to worry anymore about the technical
aspects. Using the :mod:`footprints` package, for a given execution target, it
allows to customise the way data are accessed leaving the :class:`Store` objects
unchanged.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

from datetime import datetime
import ftplib
import re

from bronx.syntax.decorators import nicedeco
import footprints
from vortex import sessions
from vortex.util.config import GenericConfigParser
from vortex.util.structs import History
from vortex.tools.actions import actiond as ad

#: No automatic export
__all__ = []

logger = footprints.loggers.getLogger(__name__)


# Decorators: for internal use in the Storage class
# -------------------------------------------------

def do_recording(flag):
    """Add a record line in the History object (if sensible)."""
    @nicedeco
    def do_flagged_recording(f):
        def wrapped_action(self, item, *kargs, **kwargs):
            infos = self._findout_record_infos(kwargs)
            (rc, extrainfos) = f(self, item, *kargs, **kwargs)
            infos.update(extrainfos)
            self.addrecord(flag, item, status=rc, **infos)
            return rc
        return wrapped_action
    return do_flagged_recording


@nicedeco
def enforce_readonly(f):
    """Check that the current storage object is not readonly."""
    def wrapped_action(self, item, *kargs, **kwargs):
        if self.readonly:
            raise IOError("This Storage place is readonly.")
        return f(self, item, *kargs, **kwargs)
    return wrapped_action


# Main Storage abstract class
# ---------------------------

class Storage(footprints.FootprintBase):
    """Root class for any Storage class, ex: Cache, Archive, ...

    Tips for developers:

    The following methods needs to be defined in the child classes:

        * *_actual_fullpath*
        * *_actual_check*
        * *_actual_insert*
        * *_actual_retrieve*
        * *_actual_delete*

    They must return a two elements tuple consisting of a returncode and a
    dictionary whose items will be written in the object's record.
    """

    _abstract = True,
    _footprint = dict(
        info = 'Default/Abstract storage place description.',
        attr = dict(
            config=dict(
                info='A ready to use configuration file object for this storage place.',
                type=GenericConfigParser,
                optional=True,
                default=None,
            ),
            inifile=dict(
                info=('The name of the configuration file that will be used (if ' +
                      '**config** is not provided.'),
                optional=True,
                default='@storage-[storage].ini',
            ),
            iniauto=dict(
                info='If needed, use **inifile** to create a configuration file object.',
                type=bool,
                optional=True,
                default=True,
            ),
            kind=dict(
                info="The storage place's kind.",
                values=['std'],
            ),
            storage=dict(
                info="The storage target.",
                optional=True,
            ),
            record=dict(
                info="Record insert, retrieve, delete actions in an History object.",
                type=bool,
                optional=True,
                default=False,
                access='rwx',
            ),
            readonly=dict(
                info="Disallow insert and delete action for this storage place.",
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
        self._history = History(tag=self.tag)

    @property
    def tag(self):
        """The identifier of the storage place."""
        raise NotImplementedError()

    @property
    def realkind(self):
        return 'storage'

    def _str_more(self):
        return 'tag={:s}'.format(self.tag)

    @property
    def sh(self):
        """Shortcut to the active System object."""
        return sessions.system()

    @property
    def history(self):
        """The History object that will be used by this storage place.

        :note: History objects are associated with the self.tag identifier. i.e.
               all Storage's objects with the same tag will use the same History
               object.
        """
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
    def actual_record(self):
        """Do we record things in the History object ?"""
        return self.actual('record')

    def addrecord(self, action, item, **infos):
        """Push a new record to the storage place log/history."""
        if self.actual_record:
            self.history.append(action, item, infos)

    def flush(self, dumpfile=None):
        """Flush actual history to the specified ``dumpfile`` if record is on.

        :note: May raise the :class:`NotImplementedError` exception.
        """
        raise NotImplementedError()

    def _findout_record_infos(self, kwargs):
        return dict(info=kwargs.get("info", None))

    def fullpath(self, item, **kwargs):
        """Return the path/URI to the **item**'s storage location."""
        # Currently no recording is performed for the check action
        (rc, _) = self._actual_fullpath(item, **kwargs)
        return rc

    def check(self, item, **kwargs):
        """Check/Stat an **item** from the current storage place."""
        # Currently no recording is performed for the check action
        (rc, _) = self._actual_check(item, **kwargs)
        return rc

    @enforce_readonly
    @do_recording('INSERT')
    def insert(self, item, local, **kwargs):
        """Insert an **item** in the current storage place.

        :note: **local** may be a path to a file or any kind of file like objects.
        """
        return self._actual_insert(item, local, **kwargs)

    @do_recording('RETRIEVE')
    def retrieve(self, item, local, **kwargs):
        """Retrieve an **item** from the current storage place.

        :note: **local** may be a path to a file or any kind of file like objects.
        """
        return self._actual_retrieve(item, local, **kwargs)

    @enforce_readonly
    @do_recording('DELETE')
    def delete(self, item, **kwargs):
        """Delete an **item** from the current storage place."""
        return self._actual_delete(item, **kwargs)


# Defining the two main flavours of storage places
# -----------------------------------------------

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
            rootdir = dict(
                info     = "The cache's location (usually on a filesystem).",
                optional = True,
                default  = '/tmp',
            ),
            headdir = dict(
                info     = "The cache's subdirectory (within **rootdir**).",
                optional = True,
                default  = 'cache',
            ),
            storage = dict(
                optional = True,
                default  = 'localhost',
            ),
            rtouch = dict(
                info     = "Perform the recursive touch command on the directory structure.",
                type     = bool,
                optional = True,
                default  = False,
            ),
            rtouchskip = dict(
                info     = "Do not 'touch' the first **rtouchskip** directories.",
                type     = int,
                optional = True,
                default  = 0,
            ),
        )
    )

    @property
    def realkind(self):
        return 'cache'

    @property
    def actual_rootdir(self):
        """This cache rootdir (potentially read form the configuration file)."""
        return self.actual('rootdir')

    @property
    def actual_headdir(self):
        """This cache headdir (potentially read form the configuration file)."""
        return self.actual('headdir')

    @property
    def entry(self):
        """Tries to figure out what could be the actual entry point for storage space."""
        return self.sh.path.join(self.actual_rootdir, self.kind, self.actual_headdir)

    @property
    def tag(self):
        """The identifier of this cache place."""
        return '{:s}_{:s}'.format(self.realkind, self.entry)

    def _formatted_path(self, subpath, **kwargs):  # @UnusedVariable
        return self.sh.path.join(self.entry, subpath.lstrip('/'))

    def catalog(self):
        """List all files present in this cache.

        :note: It might be quite slow...
        """
        entry = self.sh.path.expanduser(self.entry)
        files = self.sh.ffind(entry)
        return [f[len(entry):] for f in files]

    def _recursive_touch(self, rc, item):
        """Make recursive touches on parent directories.

        It might be useful for cleaning scripts.
        """
        if self.rtouch and (not self.readonly) and rc:
            items = item.lstrip('/').split('/')
            if len(items) > 2:
                items = items[:-2]  # It's useless to touch the rightmost directory
                for index in range(len(items), self.rtouchskip, -1):
                    self.sh.touch(self._formatted_path(self.sh.path.join(*items[:index])))

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

    def _actual_fullpath(self, subpath, **kwargs):
        """Return the path/URI to the **item**'s storage location."""
        return self._formatted_path(subpath, **kwargs), dict()

    def _actual_check(self, item, **kwargs):
        """Check/Stat an **item** from the current storage place."""
        path = self._formatted_path(item, **kwargs)
        try:
            st = self.sh.stat(path)
        except OSError:
            st = None
        return st, dict()

    def _actual_insert(self, item, local, **kwargs):
        """Insert an **item** in the current storage place."""
        # Get the relevant options
        intent = kwargs.get("intent", "in")
        fmt = kwargs.get("fmt", "foo")
        # Insert the element
        rc = self.sh.cp(local, self._formatted_path(item), intent=intent, fmt=fmt)
        self._recursive_touch(rc, item)
        return rc, dict(intent=intent, fmt=fmt)

    def _actual_retrieve(self, item, local, **kwargs):
        """Retrieve an **item** from the current storage place."""
        # Get the relevant options
        intent = kwargs.get("intent", "in")
        fmt = kwargs.get("fmt", "foo")
        silent = kwargs.get("silent", False)
        dirextract = kwargs.get("dirextract", False)
        tarextract = kwargs.get("tarextract", False)
        uniquelevel_ignore = kwargs.get("uniquelevel_ignore", True)
        source = self._formatted_path(item)
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
        return rc, dict(intent=intent, fmt=fmt)

    def _actual_delete(self, item, **kwargs):
        """Delete an **item** from the current storage place."""
        # Get the relevant options
        fmt = kwargs.get("fmt", "foo")
        # Delete the element
        rc = self.sh.remove(self._formatted_path(item), fmt=fmt)
        return rc, dict(fmt=fmt)


class Archive(Storage):
    """The default class to handle storage to a remote location."""

    _default_tube = 'ftp'
    _default_storage = 'hendrix.meteo.fr'

    _collector = ('archive', )
    _footprint = dict(
        info = 'Default archive description',
        attr = dict(
            inifile = dict(
                optional = True,
                default  = '@archive-[storage].ini',
            ),
            storage = dict(
                optional = True,
                default  = 'generic',
            ),
            tube = dict(
                info     = "How to communicate with the archive ?",
                optional = True,
                values   = ['ftp', ],
            ),
        )
    )

    @property
    def tag(self):
        """The identifier of this cache place."""
        return '{:s}_{:s}_{:s}'.format(self.realkind, self.actual_storage, self.kind)

    @property
    def realkind(self):
        return 'archive'

    @property
    def actual_storage(self):
        """This archive network name (potentially read form the configuration file)."""
        return ((self.storage if self.storage != 'generic' else None) or
                self.sh.env.VORTEX_DEFAULT_STORAGE or
                (self._actual_config.get(self.kind, 'storage')
                 if self._actual_config.has_option(self.kind, 'storage') else None) or
                self.sh.default_target.get('stores:archive_storage', None) or
                self.sh.default_target.get('stores:storage', None) or
                self._default_storage)

    @property
    def actual_tube(self):
        """This archive communication scheme (potentially read form the configuration file)."""
        return (self.tube or
                (self._actual_config.get(self.kind, 'tube', None)
                 if self._actual_config.has_option(self.kind, 'tube') else None) or
                self.sh.default_target.get('stores:archive_tube', None) or
                self._default_tube)

    def _formatted_path(self, rawpath, **kwargs):
        root = kwargs.get('root', None)
        if root is not None:
            rawpath = self.sh.path.join(root, rawpath.lstrip('/'))
        compressionpipeline = kwargs.get('compressionpipeline', None)
        if compressionpipeline is not None:
            rawpath += compressionpipeline.suffix
        return rawpath

    def __getattr__(self, attr):
        """Provides proxy methods for _actual_* methods."""
        mattr = re.match(r'_actual_(?P<action>fullpath|check|insert|retrieve|delete)', attr)
        if mattr:
            pmethod = getattr(self, '_{:s}{:s}'.format(self.actual_tube, mattr.group('action')))

            def actual_proxy(item, *kargs, **kwargs):
                path = self._formatted_path(item, **kwargs)
                if path is None:
                    raise ValueError("The archive's path is void.")
                return pmethod(path, *kargs, **kwargs)

            actual_proxy.__name__ = pmethod.__name__
            actual_proxy.__doc__ = pmethod.__doc__
            return actual_proxy
        else:
            raise AttributeError("The {:s} attribute was not found in this object"
                                 .format(attr))

    def _ftpfullpath(self, subpath, **kwargs):
        """Actual _fullpath using ftp."""
        username = kwargs.get('username', None)
        rc = None
        ftp = self.sh.ftp(hostname=self.actual_storage,
                          logname=username,
                          delayed = True)
        if ftp:
            rc = ftp.netpath(subpath)
            ftp.close()
        return rc, dict()

    def _ftpcheck(self, item, **kwargs):
        """Actual _check using ftp."""
        username = kwargs.get('username', None)
        rc = None
        ftp = self.sh.ftp(hostname=self.actual_storage,
                          logname=username)
        if ftp:
            try:
                rc = ftp.size(item)
            except (ValueError, TypeError, ftplib.all_errors):
                pass
            finally:
                ftp.close()
        return rc, dict()

    def _ftpretrieve(self, item, local, **kwargs):
        """Actual _retrieve using ftp."""
        logger.info('ftpget on ftp://%s/%s (to: %s)', self.actual_storage, item, local)
        extras = dict(fmt=kwargs.get('fmt', 'foo'),
                      cpipeline=kwargs.get('compressionpipeline', None))
        rc = self.sh.smartftget(
            item,
            local,
            # Ftp control
            hostname = self.actual_storage,
            logname = kwargs.get('username', None),
            ** extras
        )
        return rc, extras

    def _ftpinsert(self, item, local, **kwargs):
        """Actual _insert using ftp."""
        sync_insert = kwargs.get('sync')
        if sync_insert:
            logger.info('ftpput to ftp://%s/%s (from: %s)', self.actual_storage, item, local)
            extras = dict(fmt=kwargs.get('fmt', 'foo'),
                          cpipeline=kwargs.get('compressionpipeline', None))
            rc = self.sh.smartftput(
                local,
                item,
                # Ftp control
                hostname = self.actual_storage,
                logname = kwargs.get('username', None),
                sync = kwargs.get('enforcesync', False),
                ** extras
            )
        else:
            logger.info('delayed ftpput to ftp://%s/%s (from: %s)', self.actual_storage, item, local)
            tempo = footprints.proxy.service(kind='hiddencache',
                                             asfmt=kwargs.get('fmt'))
            compressionpipeline = kwargs.get('compressionpipeline', '')
            if compressionpipeline:
                compressionpipeline = compressionpipeline.description_string
            extras = dict(fmt=kwargs.get('fmt', 'foo'),
                          compressionpipeline=compressionpipeline)
            rc = ad.jeeves(
                hostname = self.actual_storage,
                logname = kwargs.get('username', None),
                todo = 'ftput',
                rhandler = kwargs.get('rhandler', None),
                source = tempo(local),
                destination = item,
                original = self.sh.path.abspath(local),
                ** extras
            )
        return rc, extras

    def _ftpdelete(self, item, **kwargs):
        """Actual _delete using ftp."""
        rc = None
        username = kwargs.get('username', None)
        ftp = self.system.ftp(self.actual_storage, username)
        if ftp:
            if self.check(item, kwargs):
                logger.info('ftpdelete on ftp://%s/%s', self.actual_storage, item)
                rc = ftp.delete(item)
                ftp.close()
            else:
                logger.error('Try to remove a non-existing resource <%s>', item)
        return rc, dict()


# Concrete cache implementations
# ------------------------------

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
