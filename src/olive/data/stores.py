#!/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import re
from vortex.autolog import logdefault as logger
from vortex.data.stores import StoreGlue, IniStoreGlue, ArchiveStore, CacheStore, MultiStore

rextract = re.compile('^extract=(.*)$')
oparchivemap = IniStoreGlue('oparchive-collector.ini')


class OliveArchiveStore(ArchiveStore):

    _footprint = dict(
        info = 'Olive archive access',
        attr = dict(
            scheme = dict(
                values = [ 'olive' ],
            ),
            netloc = dict(
                values = [ 'open.archive.fr', 'olive.archive.fr' ],
                remap = {
                    'olive.archive.fr' : 'open.archive.fr'
                },
            ),
            headdir = dict(
                default = 'xp',
                outcast = [ 'vortex' ]
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Olive archive store init %s', self.__class__)
        super(OliveArchiveStore, self).__init__(*args, **kw)

    def remapget(self, remote, options):
        """Remap actual remote path to distant store path."""
        system = options.get('system', None)
        xpath = remote['path'].split('/')
        xpath[1:2] = list(xpath[1])
        xpath[:0] = [ system.path.sep, self.headdir ]
        remote['path'] = system.path.join(*xpath)

    def olivelocate(self, remote, options):
        """Remap and ftplocate sequence."""
        self.remapget(remote, options)
        return self.ftplocate(remote, options)

    def oliveget(self, remote, local, options):
        """Remap and ftpget sequence."""
        self.remapget(remote, options)
        return self.ftpget(remote, local, options)

    def oliveput(self, local, remote, options):
        """Remap root dir and ftpput sequence."""
        if not 'root' in remote: remote['root'] = self.headdir
        return self.ftpput(local, remote, options)


class OliveCacheStore(CacheStore):

    _footprint = dict(
        info = 'Olive cache access',
        attr = dict(
            scheme = dict(
                values = [ 'olive' ],
            ),
            netloc = dict(
                values = [ 'open.cache.fr', 'olive.cache.fr' ],
                remap = {
                    'olive.cache.fr' : 'open.cache.fr'
                },
            ),
            strategy = dict(
                default = 'mtool',
            ),
            rootdir = dict(
                default = 'auto'
            ),
            headdir = dict(
                default = 'xp',
                outcast = [ 'vortex' ]
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


class OliveStore(MultiStore):

    _footprint = dict(
        info = 'Olive multi access',
        attr = dict(
            scheme = dict(
                values = [ 'olive' ],
            ),
            netloc = dict(
                values = [ 'olive.multi.fr' ],
            ),
        )
    )

    def alternates_netloc(self):
        """Tuple of alternates domains names, e.g. ``cache`` and ``archive``."""
        return ( 'olive.cache.fr', 'olive.archive.fr' )


class OpArchiveStore(ArchiveStore):

    _footprint = dict(
        info = 'Archive access',
        attr = dict(
            scheme = dict(
                values = [ 'op', 'ftop' ],
                remap = dict( ftop = 'op' ),
            ),
            netloc = dict(
                values = [ 'oper.archive.fr', 'dbl.archive.fr', 'dble.archive.fr' ],
                default = 'oper.archive.fr',
                remap = { 'dbl.archive.fr' : 'dble.archive.fr' }
            ),
            rootdir = dict(
                optional = True,
                alias = [ 'archivehome' ],
                default = '/home/m/mxpt/mxpt001'
            ),
            storage = dict(
                optional = True,
                default = 'cougar.meteo.fr'
            ),
            collector = dict(
                optional = True,
                default = oparchivemap,
                type = StoreGlue
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Archive store init %s', self.__class__)
        super(OpArchiveStore, self).__init__(*args, **kw)

    def fullpath(self, remote):
        return self.rootdir + remote['path']

    def oplocate(self, remote, options):
        """Delegates to ``system`` a distant check."""
        system = options.get('system', None)
        ftp = system.ftp(self.hostname(), remote['username'])
        if ftp:
            extract = remote['query'].get('extract', None)
            cleanpath = self.fullpath(remote)
            (dirname, basename) = system.path.split(cleanpath)
            if not extract and self.collector.containsfile(basename):
                cleanpath, u_targetpath = self.collector.filemap(system, dirname, basename)
            rloc = ftp.netpath(cleanpath)
            ftp.close()
            return rloc
        else:
            return None

    def opcheck(self, remote, options):
        """Delegates to ``system.ftp`` a distant check."""
        system = options.get('system', None)
        ftp = system.ftp(self.hostname(), remote['username'])
        if ftp:
            extract = remote['query'].get('extract', None)
            cleanpath = self.fullpath(remote)
            (dirname, basename) = system.path.split(cleanpath)
            if not extract and self.collector.containsfile(basename):
                cleanpath, u_targetpath = self.collector.filemap(system, dirname, basename)
            rc = ftp.size(cleanpath)
            ftp.close()
            return rc

    def opget(self, remote, local, options):
        """File transfert: get from store."""
        system = options.get('system', None)
        ftp = system.ftp(self.hostname(), remote['username'])
        if ftp:
            targetpath = local
            cleanpath = self.fullpath(remote)
            extract = remote['query'].get('extract', None)
            (dirname, basename) = system.path.split(cleanpath)
            if not extract and self.collector.containsfile(basename):
                extract = basename
                cleanpath, targetpath = self.collector.filemap(system, dirname, basename)
            if cleanpath == None:
                rc = False
            else:
                rc = ftp.get(cleanpath, targetpath)
                ftp.close()
                if rc and extract:
                    if extract == 'all' :
                        rc = system.untar(targetpath, output=False)
                    else:
                        rc = system.untar(targetpath, extract, output=False)
                        if local != extract:
                            rc = rc and system.mv(extract, local)
            return rc
        else:
            logger.error('Could not get ftp connection to %s', self.hostname())
            return False

    def opput(self, local, remote, options):
        """File transfert: put to store."""
        system = options.get('system', None)
        ftp = system.ftp(self.hostname(), remote['username'])
        if ftp:
            rc = ftp.put(local, self.fullpath(remote))
            ftp.close()
            return rc


class OpCacheStore(CacheStore):
    """User cache for Op resources."""

    _footprint = dict(
        info = 'OP cache access',
        attr = dict(
            scheme = dict(
                values = [ 'op' ],
            ),
            netloc = dict(
                values = [ 'oper.cache.fr', 'dble.cache.fr' ],
            ),
            strategy = dict(
                default = 'mtool',
            ),
            rootdir = dict(
                default = 'conf'
            ),
            headdir = dict(
                default = 'op',
                outcast = [ 'xp', 'vortex', 'gco' ],
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('OP cache store init %s', self.__class__)
        super(OpCacheStore, self).__init__(*args, **kw)
        self.resetcache()

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


class OpStore(MultiStore):
    """Combined cache and archive Oper/Dble stores."""

    _footprint = dict(
        info = 'Op multi access',
        attr = dict(
            scheme = dict(
                values = [ 'op' ],
            ),
            netloc = dict(
                values = [ 'oper.multi.fr', 'dble.multi.fr' ],
            ),
            refillstore = dict(
                default = True,
            )
        )
    )

    def alternates_netloc(self):
        """Tuple of alternates domains names, e.g. ``cache`` and ``archive``."""
        prefix, multi, region = self.netloc.split('.')
        return ( prefix + '.cache.fr', prefix + '.archive.fr' )

