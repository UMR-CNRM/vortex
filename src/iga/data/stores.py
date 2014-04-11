#!/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import footprints

from vortex.autolog import logdefault as logger
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
                outcast = list(),
                values = [ 'oper.inline.fr', 'dbl.inline.fr', 'dble.inline.fr', 'test.inline.fr' ],
                remap = {
                    'dbl.inline.fr' : 'dble.inline.fr'
                }
            ),
            rootdir = dict(
                alias = [ 'opdata', 'datadir' ],
                optional = True,
                default = '/chaine/mxpt001'
            )
        ),
        priority = dict(
            level = footprints.priorities.top.OPER
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('IgaFinder store init %s', self.__class__)
        super(IgaFinder, self).__init__(*args, **kw)

    @property
    def realkind(self):
        return 'igafinder'

    def hostname(self):
        return self.netloc

    def fullpath(self, remote):
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
        logger.debug('Soprano store init %s', self.__class__)
        super(SopranoStore, self).__init__(*args, **kw)

    @property
    def realkind(self):
        return 'prodsoprano'

    def hostname(self):
        return self.storage

    def fullpath(self, remote):
        return self.rootdir + remote['path']

    def ftplocate(self, remote, options):
        """Delegates to ``system`` a distant check."""
        ftp = self.system.ftp(self.hostname(), remote['username'])
        if ftp:
            rloc = ftp.netpath(self.fullpath(remote))
            ftp.close()
            return rloc
        else:
            return None

    def ftpcheck(self, remote, options):
        """Delegates to ``system`` a distant check."""
        ftp = self.system.ftp(self.hostname(), remote['username'])
        if ftp:
            rc = ftp.size(self.fullpath(remote))
            ftp.close()
            return rc

    def ftpget(self, remote, local, options):
        ftp = self.system.ftp(self.hostname(), remote['username'])
        if ftp:
            rc = ftp.get(self.fullpath(remote), local)
            ftp.close()
            extract = remote['query'].get('extract', None)
            if extract:
                if extract == 'all' :
                    rc = self.system.untar(local, output=False)
                else:
                    rc = self.system.untar(local , extract, output=False)
                    if local != extract:
                        rc = self.system.mv(extract, local)
            return rc

    def ftpput(self, local, remote, options):
         return self.system.ftput(
            local,
            self.fullpath(remote),
            # ftp control
            hostname = self.hostname(),
            logname  = remote['username'],
            fmt      = options.get('fmt')
        )
