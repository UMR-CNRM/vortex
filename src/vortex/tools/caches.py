#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
This package handles cache objects that could be in charge of
hosting data resources. Cache objects use the :mod:`footprints` mechanism.
"""

import hashlib
import ftplib
from datetime import datetime

import footprints
from vortex import sessions
from vortex.util.config import GenericConfigParser
from vortex.util.structs import History
from vortex.tools.actions import actiond as ad

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

    def formatted_path(self, subpath, **kwargs):
        return self.sh.path.join(self.entry, subpath.lstrip('/'))

    def fullpath(self, subpath, **kwargs):
        """Actual full path in the storage place."""
        return self.formatted_path(subpath, **kwargs)

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

    def __init__(self, *args, **kwargs):
        logger.debug('Abstract cache init %s', self.__class__)
        super(Cache, self).__init__(*args, **kwargs)

    @property
    def realkind(self):
        return 'cache'

    def check(self, item, **kwargs):
        """Check/Stat an item in the current cache."""
        path = self.fullpath(item, **kwargs)
        try:
            st = self.sh.stat(path)
        except OSError:
            st = None
        return st

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
                values   = ['archive-std'],
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
                values = ['ftp', 'ftserv',],
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Abstract archive init %s', self.__class__)
        super(Archive, self).__init__(*args, **kw)

    @property
    def entry(self):
        """Tries to figure out what could be the actual entry point for archive space."""
        if self.rootdir == 'auto':
            archive = "~"
        else:
            archive = self.actual_rootdir
        return self.sh.path.join(archive, self.actual_headdir)

    @property
    def realkind(self):
        return 'archive'

    def ftpfullpath(self, subpath, **kwargs):
        """Actual full path in the archive place using ftp"""
        username = kwargs.get('username', None)
        rc = None
        ftp = self.sh.ftp(hostname=self.storage,
                          logname=username,
                          delayed = True)
        if ftp:
            rc = ftp.netpath(subpath)
            ftp.close()
        return rc

    def ftpcheck(self, item, **kwargs):
        """Check/Stat an item from the current archive using Ftp"""
        username = kwargs.get('username', None)
        rc = None
        ftp = self.sh.ftp(hostname=self.storage,
                          logname=username)
        if ftp:
            try:
                rc = ftp.size(item)
            except (ValueError, TypeError, ftplib.all_errors):
                pass
            finally:
                ftp.close()
        return rc

    def ftpretrieve(self, item, local, **kwargs):
        """Retrieve an item from the current archive using ftp."""
        logger.info('ftpget on ftp://%s/%s (to: %s)', self.storage, item, local)
        rc = self.sh.smartftget(
            item,
            local,
            # Ftp control
            hostname = self.storage,
            logname = kwargs.get('username'),
            cpipeline = kwargs.get('compressionpipeline', None),
            fmt = kwargs.get('fmt'),
        )
        return rc

    def ftpinsert(self, item, local, **kwargs):
        """Insert an item in the current archive using ftp."""
        sync_insert = kwargs.get('sync')
        if sync_insert:
            logger.info('ftpput to ftp://%s/%s (from: %s)', self.storage, item, local)
            rc = self.sh.smartftput(
                local,
                item,
                # Ftp control
                hostname = self.storage,
                logname = kwargs.get('username'),
                cpipeline = kwargs.get('compressionpipeline', None),
                fmt = kwargs.get('fmt'),
                sync = kwargs.get('enforcesync', False)
            )
        else:
            logger.info('delayed ftpput to ftp://%s/%s (from: %s)', self.storage, item, local)
            tempo = footprints.proxy.service(kind='hiddencache',
                                             asfmt=kwargs.get('fmt'))
            compressionpipeline = kwargs.get('compressionpipeline', None)
            if compressionpipeline is None:
                compressionpipeline = ''
            else:
                compressionpipeline = compressionpipeline.description_string
            rc = ad.jeeves(
                hostname = self.storage,
                logname = kwargs.get('username'),
                cpipeline = compressionpipeline,
                fmt = kwargs.get('fmt'),
                todo = 'ftput',
                rhandler = kwargs.get('rhandler', None),
                source = tempo(local),
                destination = item,
                original = self.sh.path.abspath(local),
            )
        return rc

    def ftpdelete(self, item, **kwargs):
        """Delete an item from the current archive using ftp."""
        rc = None
        username = kwargs.get('username', None)
        ftp = self.system.ftp(self.storage, username)
        if ftp:
            if self.check(item, kwargs):
                logger.info('ftpdelete on ftp://%s/%s', self.storage, item)
                rc = ftp.delete(item)
                ftp.close()
            else:
                logger.error('Try to remove a non-existing resource <%s>', item)
        return rc

    def formatted_path(self, subpath, **kwargs):
        root = kwargs.get('root')
        if root is not None and root != self.actual_rootdir:
            rawpath = self.sh.path.join(root, self.actual_headdir, subpath.lstrip('/'))
        else:
            rawpath = super(Archive, self).formatted_path(subpath, **kwargs)
        compressionpipeline = kwargs.get('compressionpipeline', None)
        if compressionpipeline is not None:
            rawpath += compressionpipeline.suffix
        return rawpath

    def fullpath(self, subpath, **kwargs):
        """Actual full path in the archive place according to the compression used."""
        # Define the name of the file
        format_path = self.formatted_path(subpath, **kwargs)
        if format_path is not None:
            # Locate the file according to the scheme
            if self.scheme in ['ftp', 'ftserv']:
                format_path = self.ftpfullpath(format_path, **kwargs)
            else:
                raise NotImplementedError('The scheme is not implemented.')
        else:
            logger.error('The path is void')
            raise ValueError('The path is void.')
        return format_path

    def check(self, item, **kwargs):
        """Check/Stat an item from the current archive."""
        rc = None
        path = self.formatted_path(item, **kwargs)
        if path is not None:
            if self.scheme in ['ftp', 'ftserv']:
                rc = self.ftpcheck(path, **kwargs)
            else:
                raise NotImplementedError('The scheme is not implemented.')
        else:
            logger.error('The path is void.')
            raise ValueError('The path is void.')
        return rc

    def insert(self, item, local, **kwargs):
        """Insert an item in the current archive."""
        rc = None
        path = self.formatted_path(item, **kwargs)
        if path is not None:
            if self.scheme in ['ftp', 'ftserv']:
                rc = self.ftpinsert(path, local, **kwargs)
            else:
                raise NotImplementedError('The scheme is not implemented.')
        else:
            logger.error('The path is void.')
            raise ValueError('The path is void.')
        return rc

    def retrieve(self, item, local, **kwargs):
        """Retrieve an item from the current archive."""
        rc = None
        path = self.formatted_path(item, **kwargs)
        print(path)
        if path is not None:
            if self.scheme in ['ftp', 'ftserv']:
                rc = self.ftpretrieve(path, local, **kwargs)
            else:
                raise NotImplementedError('The scheme is not implemented.')
        else:
            logger.error('The path is void.')
            raise ValueError('The path is void.')
        return rc

    def delete(self, item, **kwargs):
        """Delete an item from the current archive."""
        rc = None
        path = self.formatted_path(item, **kwargs)
        if path is not None:
            if self.scheme in ['ftp', 'ftserv']:
                rc = self.ftpdelete(path, **kwargs)
            else:
                raise NotImplementedError('The scheme is not implemented.')
        else:
            logger.error('The path is void.')
            raise ValueError('The path is void.')
        return rc


class VortexArchive(Archive):
    """Archive items for the Vortex like applications"""

    _footprint = dict(
        info = 'Vortex like archive',
        attr = dict(
            kind = dict(
                values   = ['vortex-archive'],
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
            scheme=dict(
                optional=True,
                default='ftp',
                values=['ftp', 'ftserv', 'ectrans'],
            )
        )
    )


class OliveArchive(Archive):
    """Archive items for the Olive like applications"""

    _footprint = dict(
        info = 'Olive like archive',
        attr = dict(
            kind = dict(
                values   = ['olive-archive'],
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
            scheme=dict(
                optional=True,
                default='ftp',
                values=['ftp', 'ftserv', 'ectrans'],
            )
        )
    )


class OpArchive(Archive):
    """Archive items for the old operational applications in ksh"""

    _footprint = dict(
        info = 'Old operational like archive',
        attr = dict(
            kind = dict(
                values   = ['op-ksh-archive'],
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
                default  = "hendrix.meteo.fr",
            ),
            scheme = dict(
                optional = True,
                default  = 'ftp',
                values   = ['ftp', 'ftserv'],
            )
        )
    )

    def formatted_path(self, subpath, **kwargs):
        targetpath = None
        extract = kwargs.get('extract', None)
        glue = kwargs.get('glue')
        if glue is None:
            logger.info('The glue object is None. It should not. Stop.')
            raise ValueError('The glue object is None. It should not. Stop.')
        cleanpath = self.actual_rootdir + subpath
        (dirname, basename) = self.sh.path.split(cleanpath)
        if not extract and glue.containsfile(basename):
            (cleanpath, targetpath) = glue.filemap(self.system, dirname, basename)
        return cleanpath, targetpath, basename

    def fullpath(self, subpath, **kwargs):
        """Define the fullpath of resources in the case of the old ksh op archive"""
        rc = None
        (cleanpath, targetpath, basename) = self.formatted_path(subpath, **kwargs)
        if cleanpath is not None:
            rc = self.ftpfullpath(cleanpath, **kwargs)
        return rc

    def delete(self, item, **kwargs):
        raise NotImplementedError
        return False

    def retrieve(self, item, local, **kwargs):
        """Retrieve an item from the current archive."""
        rc = False
        extract = kwargs.get('extract', None)
        glue = kwargs.get('glue')
        (cleanpath, targetpath, basename) = self.formatted_path(item, **kwargs)
        if targetpath is None:
            targetpath = local
        if not extract and glue.containsfile(basename):
            extract = basename
        elif extract:
            extract = extract[0]
            targetpath = basename
        targetstamp = targetpath + '.stamp' + hashlib.md5(cleanpath).hexdigest()
        if cleanpath is not None:
            if extract and self.sh.path.exists(targetpath):
                if self.system.path.exists(targetstamp):
                    logger.info("%s was already fetched. that's great !", targetpath)
                    rc = True
                else:
                    self.system.rm(targetpath)
                    self.system.rmall(targetpath + '.stamp*')
            if not rc:
                rc = self.ftpretrieve(cleanpath, targetpath, **kwargs)
            if not rc:
                logger.error('FTP could not get file %s', cleanpath)
            elif extract:
                self.sh.touch(targetstamp)
                if extract == 'all':
                    rc = self.sh.untar(targetpath, output = False)
                else:
                    heaven = 'a_very_safe_untar_heaven'
                    fulltarpath = self.sh.path.abspath(targetpath)
                    with self.sh.cdcontext('a_very_safe_untar_heaven', create=True):
                        rc = self.sh.untar(fulltarpath, extract, output=False)
                    rc = rc and self.sh.rm(local)
                    rc = rc and self.sh.mv(self.system.path.join(heaven, extract),
                                               local)
                    self.sh.rm(heaven)  # Sadly this is a temporary heaven
        else:
            logger.error('The path is void.')
            raise ValueError('The path is void.')
        return rc
