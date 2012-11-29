#!/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import logging, re

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
        logging.debug('Olive archive store init %s', self.__class__)
        super(OliveArchiveStore, self).__init__(*args, **kw)

    def remapget(self, system, remote):
        xpath = remote['path'].split('/')
        xpath[1:2] = list(xpath[1])
        xpath[:0] = [ system.path.sep, self.headdir ]
        remote['path'] = system.path.join(*xpath)

    def oliveget(self, system, remote, local):
        return self.vortexget(system, remote, local)

    def oliveput(self, system, local, remote):
        return self.vortexput(system, local, remote)


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
        logging.debug('Olive cache store init %s', self.__class__)
        super(OliveCacheStore, self).__init__(*args, **kw)

    def oliveget(self, system, remote, local):
        return self.vortexget(system, remote, local)

    def oliveput(self, system, local, remote):
        return self.vortexput(system, local, remote)



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
                values = [ 'ftp', 'ftserv' ],
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
        logging.debug('Archive store init %s', self.__class__)
        super(OpArchiveStore, self).__init__(*args, **kw)

    @classmethod
    def realkind(cls):
        return 'archive'

    def hostname(self):
        return self.storage

    def _realpath(self, remote):
        return self.rootdir + remote['path']

    def ftplocate(self, system, remote):
        """Delegates to ``system`` a distant check."""
        ftp = system.ftp(self.hostname(), remote['username'])
        if ftp:
            rloc = ftp.fullpath(self._realpath(remote))
            ftp.close()
            return rloc
        else:
            return None

    def ftpcheck(self, system, remote):
        """Delegates to ``system`` a distant check."""
        ftp = system.ftp(self.hostname(), remote['username'])
        if ftp:
            rc = ftp.size(self._realpath(remote))
            ftp.close()
            return rc

    def ftpget(self, system, remote, local):
        ftp = system.ftp(self.hostname(), remote['username'])
        if ftp:
            extract = remote['query'].get('extract', None)
            cleanpath = self._realpath(remote)
            targetpath = local
            (dirname, basename) = system.path.split(cleanpath)
            if not extract and self.collector.containsfile(basename):
                gluedesc = self.collector.getfile(basename)
                if len(gluedesc) > 1:
                    logging.error('Multiple glue entries %s', gludesc)
                    return 1
                else:
                    gluedesc = gluedesc[0]
                extract = basename
                targetpath = self.collector.gluename(gluedesc['section']) + '.' + self.collector.gluetype(gluedesc['section'])
                cleanpath = system.path.join(dirname, targetpath)
            rc = ftp.get(cleanpath, targetpath)
            ftp.close()
            if extract:
                if re.match('tgz$', targetpath):
                    cmdltar = 'xvfz'
                else:
                    cmdltar = 'xvf'
                if extract == 'all' :
                    rc = rc and system.tar(cmdltar, targetpath)
                else:
                    rc = system.tar(cmdltar, targetpath , extract)
                    if local != extract:
                        rc = rc and system.mv(extract, local)
            return rc

    def ftpput(self, system, local, remote):
        ftp = system.ftp(self.hostname(), remote['username'])
        if ftp:
            rc = ftp.put(local, self._realpath(remote))
            ftp.close()
            return rc


