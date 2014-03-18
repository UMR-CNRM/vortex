#!/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

from vortex.autolog import logdefault as logger
from vortex.data.stores import Store, MultiStore, CacheStore

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
            ggetcmd = dict(
                optional = True,
                default = None
            ),
            ggetpath = dict(
                optional = True,
                default = None
            ),
            ggetroot = dict(
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

    def actualgget(self, rpath):
        """Return actual (gtool, gname)."""
        tg = self.system.target()

        l = rpath.lstrip('/').split('/')
        gname = l.pop()

        if 'GGET_TAMPON' in self.system.env:
            tampon = self.system.env.GGET_TAMPON
        else:
            rootdir = self.ggetroot
            if rootdir is None:
                rootdir = tg.get('gco:rootdir', '')
            tampon = rootdir + '/' + '/'.join(l)

        gcmd = self.ggetcmd
        if gcmd is None:
            gcmd = tg.get('gco:ggetcmd', 'gget')

        gpath = self.ggetpath
        if gpath is None:
            if 'GGET_PATH' in self.system.env:
                gpath = self.system.env.GGET_PATH
            else:
                gpath = tg.get('gco:ggetpath', '')

        return (self.system.path.join(gpath, gcmd), tampon, gname)

    def ggetcheck(self, remote, options):
        """Verify disponibility in GCO's tampon using ``gget`` external tool."""
        gloc = self.ggetlocate(remote, options)
        if gloc:
            return self.system.size(gloc)
        else:
            return False

    def ggetlocate(self, remote, options):
        """Get location in GCO's tampon using ``gget`` external tool."""
        (gtool, tampon, gname) = self.actualgget(remote['path'])
        self.system.env.gget_tampon = tampon
        gloc = self.system.spawn([gtool, '-path', gname], output=True)
        if gloc and self.system.path.exists(gloc[0]):
            return gloc[0]
        else:
            return False

    def ggetget(self, remote, local, options):
        """System call to ``gget`` external tool."""
        (gtool, tampon, gname) = self.actualgget(remote['path'])
        self.system.env.gget_tampon = tampon
        rc = self.system.spawn([gtool, gname], output=False)
        if rc and self.system.path.exists(gname):
            if not self.system.path.isdir(gname) and self.system.is_tarfile(gname):
                rc = self.system.untar(gname, output=False)
            extract = remote['query'].get('extract', None)
            if extract:
                logger.info('GCOCentralStore get %s', gname + '/' + extract[0])
                rc = self.system.cp(gname + '/' + extract[0], local)
            else:
                logger.info( 'GCOCentralStore get %s', gname )
                rc = self.system.mv(gname, local)
        else:
            logger.warning('GCOCentralStore get %s was not successful (%s)', gname, rc)
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
                default = 'auto'
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

    def ggetcheck(self, remote, options):
        """Gateway to :meth:`incachecheck`."""
        return self.incachecheck(remote, options)

    def ggetlocate(self, remote, options):
        """Gateway to :meth:`incachelocate`."""
        return self.incachelocate(remote, options)

    def ggetget(self, remote, local, options):
        """Gateway to :meth:`incacheget`."""
        extract = remote['query'].get('extract', None)
        if extract:
            logger.warning('Skip cache get with extracted %s', extract)
            return False
        else:
            rc = self.incacheget(remote, local, options)
            if rc and not self.system.path.isdir(local) and self.system.is_tarfile(local):
                rc = self.system.untar(local, output=False)
            return rc

    def ggetput(self, local, remote, options):
        """Gateway to :meth:`incacheputt`."""
        extract = remote['query'].get('extract', None)
        if extract:
            logger.warning('Skip cache put with extracted %s', extract)
            return True
        else:
            return self.incacheput(local, remote, options)


class GCOStore(MultiStore):
    """Combined cache and central GCO stores."""

    _footprint = dict(
        info = 'GCO multi access',
        attr = dict(
            scheme = dict(
                values = [ 'gget' ],
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
        return ('gco.cache.fr', 'gco.meteo.fr')
