#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=unused-argument

#: No automatic export
__all__ = []

import re
import ftplib

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.data.stores import StoreGlue, IniStoreGlue, ArchiveStore, CacheStore, MultiStore

rextract = re.compile('^extract=(.*)$')
oparchivemap = IniStoreGlue('oparchive-glue.ini')


class OliveArchiveStore(ArchiveStore):

    _footprint = dict(
        info = 'Olive archive access',
        attr = dict(
            scheme = dict(
                values  = ['olive'],
            ),
            netloc = dict(
                values  = ['open.archive.fr', 'olive.archive.fr'],
                remap   = {'olive.archive.fr': 'open.archive.fr'},
            ),
            storeroot = dict(
                default  = '/home/m/marp/marp999',
            ),
            storehead = dict(
                default = 'xp',
                outcast = ['vortex']
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Olive archive store init %s', self.__class__)
        super(OliveArchiveStore, self).__init__(*args, **kw)

    def remap_read(self, remote, options):
        """Remap actual remote path to distant store path for read-only actions."""
        xpath = remote['path'].split('/')
        xpath[1:2] = list(xpath[1])
        xpath[:0] = [ self.system.path.sep, self.storehead ]
        remote['path'] = self.system.path.join(*xpath)

    def remap_write(self, remote, options):
        """Remap actual remote path to distant store path for intrusive actions."""
        if 'root' not in remote:
            remote['root'] = self.storehead

    def olivecheck(self, remote, options):
        """Remap and ftpcheck sequence."""
        self.remap_read(remote, options)
        return self.ftpcheck(remote, options)

    def olivelocate(self, remote, options):
        """Remap and ftplocate sequence."""
        self.remap_read(remote, options)
        return self.ftplocate(remote, options)

    def oliveget(self, remote, local, options):
        """Remap and ftpget sequence."""
        self.remap_read(remote, options)
        return self.ftpget(remote, local, options)

    def oliveput(self, local, remote, options):
        """Remap root dir and ftpput sequence."""
        self.remap_write(remote, options)
        return self.ftpput(local, remote, options)

    def olivedelete(self, remote, options):
        """Remap and ftpdelete sequence."""
        self.remap_write(remote, options)
        return self.ftpdelete(remote, options)


class OliveCacheStore(CacheStore):

    _footprint = dict(
        info = 'Olive cache access',
        attr = dict(
            scheme = dict(
                values  = ['olive'],
            ),
            netloc = dict(
                values  = ['open.cache.fr', 'olive.cache.fr'],
                remap   = {'olive.cache.fr': 'open.cache.fr'},
            ),
            strategy = dict(
                default = 'mtool',
            ),
            rootdir = dict(
                default = 'auto'
            ),
            headdir = dict(
                default = 'xp',
                outcast = ['vortex']
            ),
            rtouch = dict(
                default = True,
            ),
            rtouchskip = dict(
                default = 1,
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Olive cache store init %s', self.__class__)
        super(OliveCacheStore, self).__init__(*args, **kw)

    def olivecheck(self, remote, options):
        """Gateway to :meth:`incachecheck`."""
        return self.incachecheck(remote, options)

    def olivelocate(self, remote, options):
        """Gateway to :meth:`incachelocate`."""
        return self.incachelocate(remote, options)

    def oliveget(self, remote, local, options):
        """Gateway to :meth:`incacheget`."""
        return self.incacheget(remote, local, options)

    def oliveput(self, local, remote, options):
        """Gateway to :meth:`incacheputt`."""
        return self.incacheput(local, remote, options)

    def olivedelete(self, remote, options):
        """Gateway to :meth:`incachedelete`."""
        return self.incachedelete(remote, options)


class OliveStore(MultiStore):

    _footprint = dict(
        info = 'Olive multi access',
        attr = dict(
            scheme = dict(
                values = ['olive'],
            ),
            netloc = dict(
                values = ['olive.multi.fr'],
            ),
            refillstore = dict(
                default = True,
            )
        )
    )

    def alternates_netloc(self):
        """Tuple of alternates domains names, e.g. ``cache`` and ``archive``."""
        return ('olive.cache.fr', 'olive.archive.fr')


class OpArchiveStore(ArchiveStore):

    _footprint = dict(
        info = 'Archive access',
        attr = dict(
            scheme = dict(
                values   = ['op', 'ftop'],
                remap    = dict(ftop = 'op'),
            ),
            netloc = dict(
                values   = ['oper.archive.fr', 'dbl.archive.fr', 'dble.archive.fr'],
                default  = 'oper.archive.fr',
                remap    = {'dbl.archive.fr': 'dble.archive.fr'},
            ),
            storage = dict(
                optional = True,
                default  = 'hendrix.meteo.fr',
            ),
            storeroot = dict(
                optional = True,
                alias    = ['archivehome'],
                default  = '/home/m/mxpt/mxpt001',
            ),
            glue = dict(
                type     = StoreGlue,
                optional = True,
                default  = oparchivemap,
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Archive store init %s', self.__class__)
        super(OpArchiveStore, self).__init__(*args, **kw)

    def fullpath(self, remote):
        return self.storeroot + remote['path']

    def oplocate(self, remote, options):
        """Delegates to ``system`` a distant check."""
        ftp = self.system.ftp(self.hostname(), remote['username'])
        if ftp:
            extract = remote['query'].get('extract', None)
            cleanpath = self.fullpath(remote)
            (dirname, basename) = self.system.path.split(cleanpath)
            if not extract and self.glue.containsfile(basename):
                cleanpath, _ = self.glue.filemap(self.system, dirname, basename)
            if cleanpath is not None:
                rloc = ftp.netpath(cleanpath)
            else:
                rloc = None
            ftp.close()
            return rloc
        else:
            return None

    def opcheck(self, remote, options):
        """Delegates to ``system.ftp`` a distant check."""
        ftp = self.system.ftp(self.hostname(), remote['username'])
        rc = None
        if ftp:
            extract = remote['query'].get('extract', None)
            cleanpath = self.fullpath(remote)
            (dirname, basename) = self.system.path.split(cleanpath)
            if not extract and self.glue.containsfile(basename):
                cleanpath, _ = self.glue.filemap(self.system, dirname, basename)
            try:
                rc = ftp.size(cleanpath)
            except (ValueError, TypeError, ftplib.all_errors):
                pass
            finally:
                ftp.close()
        return rc

    def opget(self, remote, local, options):
        """File transfer: get from store."""
        targetpath = local
        cleanpath  = self.fullpath(remote)
        extract    = remote['query'].get('extract', None)
        (dirname, basename) = self.system.path.split(cleanpath)
        if not extract and self.glue.containsfile(basename):
            extract = basename
            cleanpath, targetpath = self.glue.filemap(self.system, dirname, basename)
        if cleanpath is None:
            rc = False
        else:
            rc = self.system.smartftget(
                cleanpath,
                targetpath,
                # ftp control
                hostname = self.hostname(),
                logname  = remote['username'],
                fmt      = options.get('fmt'),
            )
            if not rc:
                logger.error('FTP could not get file %s', cleanpath)
            elif extract:
                if extract == 'all':
                    rc = self.system.untar(targetpath, output=False)
                else:
                    rc = self.system.untar(targetpath, extract, output=False)
                    if local != extract:
                        rc = rc and self.system.mv(extract, local)
        return rc

    def opput(self, local, remote, options):
        """File transfer: put to store."""
        return self.system.smartftput(
            local,
            self.fullpath(remote),
            # ftp control
            hostname = self.hostname(),
            logname  = remote['username'],
            fmt      = options.get('fmt'),
        )

    def opdelete(self, remote, options):
        """This operation is not supported."""
        logger.warning('Removing from OP Archive Store is not supported')
        return False


class OpCacheStore(CacheStore):
    """User cache for Op resources."""

    _footprint = dict(
        info = 'OP cache access',
        attr = dict(
            scheme = dict(
                values = ['op'],
            ),
            netloc = dict(
                values = ['oper.cache.fr', 'dble.cache.fr'],
            ),
            strategy = dict(
                default = 'mtool',
            ),
            rootdir = dict(
                default = 'auto'
            ),
            headdir = dict(
                default = 'oper',
                outcast = ['xp', 'vortex', 'gco'],
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('OP cache store init %s', self.__class__)
        super(OpCacheStore, self).__init__(*args, **kw)

    def opcheck(self, remote, options):
        """Gateway to :meth:`incachecheck`."""
        return self.incachecheck(remote, options)

    def oplocate(self, remote, options):
        """Gateway to :meth:`incachelocate`."""
        return self.incachelocate(remote, options)

    def opget(self, remote, local, options):
        """Gateway to :meth:`incacheget`."""
        return self.incacheget(remote, local, options)

    def opput(self, local, remote, options):
        """Gateway to :meth:`incacheputt`."""
        return self.incacheput(local, remote, options)

    def opdelete(self, remote, options):
        """Gateway to :meth:`incachedelete`."""
        return self.incachedelete(remote, options)


class OpStore(MultiStore):
    """Combined cache and archive Oper/Dble stores."""

    _footprint = dict(
        info = 'Op multi access',
        attr = dict(
            scheme = dict(
                values = ['op'],
            ),
            netloc = dict(
                values = ['oper.multi.fr', 'dble.multi.fr'],
            ),
            refillstore = dict(
                default = True,
            )
        )
    )

    def alternates_netloc(self):
        """Tuple of alternates domains names, e.g. ``cache`` and ``archive``."""
        prefix, u_multi, u_region = self.netloc.split('.')
        return ( prefix + '.cache.fr', prefix + '.archive.fr' )
