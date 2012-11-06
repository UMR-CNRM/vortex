#!/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

import logging

from vortex.syntax.priorities import top
from vortex.data.stores import Store, Finder

class IgaFinder(Finder):
    """
    Inline disk store for operational data resources produced outside
    of the vortex scope.
    """

    _footprint = dict(
        info = 'Iga file access',
        attr = dict(
            netloc = dict(
                values = [ 'oper.inline.fr', 'oper' ],
            ),
            rootdir = dict(
                alias = [ 'suitehome' ],
                optional = True,
                default = '/ch/mxpt/mxpt001'
            )
        ),
        priority = dict(
            level = top.OPER
        )
    )

    def __init__(self, *args, **kw):
        logging.debug('IgaFinder store init %s', self.__class__)
        super(IgaFinder, self).__init__(*args, **kw)

    @classmethod
    def realkind(cls):
        return 'igafinder'

    def hostname(self):
        return self.netloc

    def _realpath(self, remote):
        if remote['query'].get('relative', False):
            return remote['path'].lstrip('/')
        else:
            return self.rootdir  + remote['path']

class SopranoStore(Store):

    _footprint = dict(
        info = 'Soprano access',
        attr = dict(
            scheme = dict(
                values = [ 'ftp', 'ftserv' ],
            ),
            netloc = dict(
                values = [ 'prod.inline.fr', 'intgr.inline.fr' ],
                default = 'prod.inline.fr'
            ),
            rootdir = dict(
                alias = [ 'sopranohome' ],
                default = '/SOPRANO'
            ),
            storage = dict(
                optional = True,
                values = [ 'piccolo.meteo.fr, piccolo-int.meteo.fr' ],
                default = 'piccolo.meteo.fr'
            ),
        )
    )

    def __init__(self, *args, **kw):
        logging.debug('Soprano store init %s', self.__class__)
        super(SopranoStore, self).__init__(*args, **kw)

    @classmethod
    def realkind(cls):
        return 'prodsoprano'

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

