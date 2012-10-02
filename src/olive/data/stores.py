#!/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

import logging, re

from vortex.data.stores import Store, VortexStore, VortexArchiveStore, VortexCacheStore


rextract = re.compile('^extract=(.*)$')


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
                alias = [ 'archivehome' ],
                default = '/home/m/mxpt/mxpt001'
            ),
            storage = dict(
                optional = True,
                default = 'cougar.meteo.fr'
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
            rc = ftp.get(self._realpath(remote), local)
            ftp.close() 
            extract = remote['query'].get('extract', None)
            if extract:
                if re.match('tgz$', remote['path']):
                    cmdltar = 'xvfz'
                else:
                    cmdltar = 'xvf'
                if extract == 'all' :
                    rc = system.tar(cmdltar, local)
                else:
                    rc = system.tar(cmdltar, local , extract)
                    if local != extract:
                        rc = system.mv(extract, local)
            return rc
        
    def ftpput(self, system, local, remote):
        ftp = system.ftp(self.hostname(), remote['username'])
        if ftp:
            rc = ftp.put(local, self._realpath(remote))
            ftp.close()
            return rc


