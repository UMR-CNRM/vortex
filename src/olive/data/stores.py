#!/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import re
from vortex.autolog import logdefault as logger
from vortex.data.stores import StoreGlue, IniStoreGlue, Store, VortexStore, VortexArchiveStore, VortexCacheStore

rextract = re.compile('^extract=(.*)$')
oparchivemap = IniStoreGlue('oparchive-collector.ini')


class OliveArchiveStore(VortexArchiveStore):

    _footprint = dict(
        info = 'Olive archive access',
        attr = dict(
            scheme = dict(
                values = [ 'olive' ],
            ),
            headdir = dict(
                optional = True,
                default = 'xp'
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
        """Gateway to :meth:`vortexlocate`."""
        return self.vortexlocate(remote, options)

    def oliveget(self, remote, local, options):
        """Gateway to :meth:`vortexget`."""
        return self.vortexget(remote, local, options)

    def oliveput(self, local, remote, options):
        """Gateway to :meth:`vortexput`."""
        return self.vortexput(local, remote, options)


class OliveCacheStore(VortexCacheStore):

    _footprint = dict(
        info = 'Olive cache access',
        attr = dict(
            scheme = dict(
                values = [ 'olive' ],
            ),
            headdir = dict(
                default = 'xp'
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Olive cache store init %s', self.__class__)
        super(OliveCacheStore, self).__init__(*args, **kw)

    def olivelocate(self, remote, options):
        """Gateway to :meth:`vortexlocate`."""
        return self.vortexlocate(remote, options)

    def oliveget(self, remote, local, options):
        """Gateway to :meth:`vortexget`."""
        return self.vortexget(remote, local, options)

    def oliveput(self, local, remote, options):
        """Gateway to :meth:`vortexput`."""
        return self.vortexput(local, remote, options)



class OliveStore(VortexStore):

    _footprint = dict(
        info = 'Olive multi access',
        attr = dict(
            scheme = dict(
                values = [ 'olive' ],
            ),
        )
    )


class OpArchiveStore(Store):

    _footprint = dict(
        info = 'Archive access',
        attr = dict(
            scheme = dict(
                values = [ 'ftop', 'ftp' ],
                remap = dict( ftop = 'ftp' ),
            ),
            netloc = dict(
                values = [ 'oper.archive.fr', 'dbl.archive.fr', 'archive.meteo.fr' ],
                default = 'archive.meteo.fr'
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

    @property
    def realkind(self):
        return 'archive'

    def hostname(self):
        """Returns the current :attr:`storage`."""
        return self.storage

    def _realpath(self, remote):
        return self.rootdir + remote['path']

    def ftplocate(self, remote, options):
        """Delegates to ``system`` a distant check."""
        system = options.get('system', None)
        ftp = system.ftp(self.hostname(), remote['username'])
        if ftp:
            extract = remote['query'].get('extract', None)
            cleanpath = self._realpath(remote)
            (dirname, basename) = system.path.split(cleanpath)
            if not extract and self.collector.containsfile(basename):
                cleanpath, u_targetpath = self.collector.filemap(system, dirname, basename)
            rloc = ftp.fullpath(cleanpath)
            ftp.close()
            return rloc
        else:
            return None

    def ftpcheck(self, remote, options):
        """Delegates to ``system.ftp`` a distant check."""
        system = options.get('system', None)
        ftp = system.ftp(self.hostname(), remote['username'])
        if ftp:
            extract = remote['query'].get('extract', None)
            cleanpath = self._realpath(remote)
            (dirname, basename) = system.path.split(cleanpath)
            if not extract and self.collector.containsfile(basename):
                cleanpath, u_targetpath = self.collector.filemap(system, dirname, basename)
            rc = ftp.size(cleanpath)
            ftp.close()
            return rc

    def ftpget(self, remote, local, options):
        """File transfert: get from store."""
        system = options.get('system', None)
        ftp = system.ftp(self.hostname(), remote['username'])
        if ftp:
            targetpath = local
            cleanpath = self._realpath(remote)
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

    def ftpput(self, local, remote, options):
        """File transfert: put to store."""
        system = options.get('system', None)
        ftp = system.ftp(self.hostname(), remote['username'])
        if ftp:
            rc = ftp.put(local, self._realpath(remote))
            ftp.close()
            return rc


