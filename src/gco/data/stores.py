#!/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

import re
from vortex.autolog import logdefault as logger
from vortex.data.stores import Store, CacheStore, MultiStore

rextract = re.compile('^extract=(.*)$')


class GCOCentralStore(Store):
    """
    GCO central storage class.

    Extended footprint:

    * scheme (in values: ``gget``)
    * netloc (in values: ``gco.meteo.fr``) 
    """

    _footprint = dict(
        info = 'GCO Central Store',
        attr = dict(
            scheme = dict(
                values = [ 'gget' ],
            ),
            netloc = dict(
                values = [ 'gco.meteo.fr' ],
            ),
            ggetbin = dict(
                optional = True,
                default = 'gget'
            ),
            ggetpath = dict(
                optional = True,
                default = None
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Gco store init %s', self.__class__)
        super(GCOCentralStore, self).__init__(*args, **kw)

    @property
    def realkind(self):
        """Default realkind is ``gstore``."""
        return 'gstore'

    def actualgget(self, system, remotepath):
        """Return actual (gtool, gname)."""
        l = rpath.lstrip('/').split('/')
        gname = l.pop()
        tampon = '/' + '/'.join(l)
        gtool = self.ggetbin
        if self.ggetpath:
            gtool = system.path.join(self.ggetpath, gtool)
        return ( gtool, tampon, gname )

    def ggetcheck(self, remote, options):
        """Verify disponibility in GCO's tampon using ``gget`` external tool."""
        gloc = self.ggetlocate(remote, options)
        if gloc:
            system = options.get('system', None)
            return system.size(gloc)
        else:
            return False

    def ggetlocate(self, remote, options):
        """Get location in GCO's tampon using ``gget`` external tool."""
        system = options.get('system', None)
        (gtool, tampon, gname) = self.actualgget(system, remote['path'])
        system.env.gget_tampon = tampon
        gloc = system.spawn([gtool, '-path', gname], output=True)
        if gloc and system.path.exists(gloc):
            return gloc
        else:
            return False

    def ggetget(self, remote, local, options):
        """System call to ``gget`` external tool."""
        system = options.get('system', None)
        (gtool, tampon, gname) = self.actualgget(system, remote['path'])
        system.env.gget_tampon = tampon
        rc = system.spawn([gtool, gname], output=False)
        if rc and system.path.exists(gname):
            if not system.path.isdir(gname) and system.is_tarfile(gname):
                rc = system.untar(gname, output=False)
            extract = remote['query'].get('extract', None)
            if extract:
                logger.info('GCOCentralStore get %s', gname + '/' + extract[0])
                rc = system.cp(gname + '/' + extract[0], local)
            else:
                logger.info( 'GCOCentralStore get %s', gname )
                rc = system.mv(gname, local)
        else:
            logger.warning('GCOCentralStore get %s was not successful (%s)', gname, rc)
        del system.env.gget_tampon
        return rc


class GCOCacheStore(CacheStore):
    """Some kind of cache for VORTEX experiments."""

    _footprint = dict(
        info = 'VORTEX cache access',
        attr = dict(
            scheme = dict(
                values = [ 'gget' ],
            ),
            netloc = dict(
                values = [ 'gco.cache.fr' ],
            ),
            strategy = dict(
                default = 'mtool',
            ),
            rootdir = dict(
                default = 'conf'
            ),
            headdir = dict(
                default = 'gco',
                outcast = [ 'xp', 'vortex' ],
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('GCO cache store init %s', self.__class__)
        super(GCOCacheStore, self).__init__(*args, **kw)
        self.resetcache()

    def gcocheck(self, remote, options):
        """Gateway to :meth:`incachecheck`."""
        return self.incachecheck(remote, options)

    def gcolocate(self, remote, options):
        """Gateway to :meth:`incachelocate`."""
        return self.incachelocate(remote, options)

    def gcoget(self, remote, local, options):
        """Gateway to :meth:`incacheget`."""
        return self.incacheget(remote, local, options)

    def gcoput(self, local, remote, options):
        """Gateway to :meth:`incacheputt`."""
        return self.incacheput(local, remote, options)


class GCOStore(MultiStore):
    """Combined cache and central GCO stores."""

    _footprint = dict(
        info = 'GCO multi access',
        attr = dict(
            scheme = dict(
                values = [ 'gco' ],
            ),
            netloc = dict(
                values = [ 'gco.multi.fr' ],
            ),
            refillstore = dict(
                default = True,
            )
        )
    )

    def alternates_netloc(self):
        """Tuple of alternates domains names, e.g. ``cache`` and ``archive``."""
        return ( 'gco.cache.fr', 'gco.meteo.fr' )
