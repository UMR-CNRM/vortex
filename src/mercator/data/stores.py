#!/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

import logging

from vortex.data.stores import Store


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
                default = 'cougar.meteo.fr'
            ),
        )
    )

    def __init__(self, *args, **kw):
        logging.debug('Mercator Archive store init %s', self.__class__)
        super(MercatorArchiveStore, self).__init__(*args, **kw)

    @classmethod
    def realkind(cls):
        return 'mercator archive'

    def hostname(self):
        return self.storage

    def mercatorget(self, system, remote, local):
        ftp = system.ftp(self.hostname(), remote['username'])
        if ftp:
            rc = ftp.get(self.rootdir + remote['path'], local)
            ftp.close()
            return rc
        
    def mercatorput(self, system, local, remote):
        ftp = system.ftp(self.hostname(), remote['username'])
        if ftp:
            rc = ftp.put(local, self.rootdir + remote['path'])
            ftp.close()
            return rc

