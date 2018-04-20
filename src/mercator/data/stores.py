#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import footprints

from vortex.data.stores import Store

#: No automatic export
__all__ = []

logger = footprints.loggers.getLogger(__name__)


class MercatorArchiveStore(Store):

    _footprint = dict(
        info = 'Mercator Archive access',
        attr = dict(
            scheme = dict(
                values = [ 'mercator', 'ftp', 'ftserv' ],
            ),
            netloc = dict(
                values = [ 'mercator.archive.fr' ],
                default = 'mercator.archive.fr'
            ),
            rootdir = dict(
                alias = [ 'archivehome' ],
                default = '/home/s/smer/smer886'
            ),
            storage = dict(
                optional = True,
                default = 'hendrix.meteo.fr'
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Mercator Archive store init %s', self.__class__)
        super(MercatorArchiveStore, self).__init__(*args, **kw)

    @property
    def realkind(self):
        return 'mercatorarchive'

    def hostname(self):
        return self.storage

    def mercatorget(self, remote, local, options):
        ftp = self.system.ftp(self.hostname(), remote['username'])
        if ftp:
            rc = ftp.get(self.rootdir + remote['path'], local)
            ftp.close()
            return rc

    def mercatorput(self, local, remote, options):
        ftp = self.system.ftp(self.hostname(), remote['username'])
        if ftp:
            rc = ftp.put(local, self.rootdir + remote['path'])
            ftp.close()
            return rc
