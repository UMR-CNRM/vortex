#!/usr/bin/env python
# -*- coding:Utf-8 -*-
# pylint: disable=unused-argument

import tempfile

import footprints

from vortex.data.stores import Store, MultiStore, CacheStore

#: No automatic export
__all__ = []

logger = footprints.loggers.getLogger(__name__)


class GcoCentralStore(Store):
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
                values   = ['gget'],
            ),
            netloc = dict(
                values   = ['gco.meteo.fr'],
            ),
            ggetcmd = dict(
                optional = True,
                default  = None
            ),
            ggetpath = dict(
                optional = True,
                default  = None
            ),
            ggetroot = dict(
                optional = True,
                default  = None
            ),
            ggetarchive = dict(
                optional = True,
                default  = None
            ),
        )
    )

    def __init__(self, *args, **kw):
        """Proxy init abstract method. Logging only for the time being."""
        logger.debug('Gco store init %s', self.__class__)
        super(GcoCentralStore, self).__init__(*args, **kw)

    @property
    def realkind(self):
        """Default realkind is ``gstore``."""
        return 'gstore'

    def _actualgget(self, rpath):
        """Return actual (gtool, garchive, tampon, gname)."""
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

        garchive = self.ggetarchive
        if garchive is None:
            garchive = tg.get('gco:ggetarchive', 'hendrix')

        return (self.system.path.join(gpath, gcmd), garchive, tampon, gname)

    def ggetcheck(self, remote, options):
        """Verify disponibility in GCO's tampon using ``gget`` external tool."""
        gloc = self.ggetlocate(remote, options)
        if gloc:
            return self.system.size(gloc)
        else:
            return False

    def ggetlocate(self, remote, options):
        """Get location in GCO's tampon using ``gget`` external tool."""
        (gtool, archive, tampon, gname) = self._actualgget(remote['path'])
        sh = self.system
        sh.env.GGET_TAMPON = tampon
        gloc = sh.spawn([gtool, '-path', '-host', archive, gname], output=True)
        if gloc and sh.path.exists(gloc[0]):
            return gloc[0]
        else:
            return False

    def ggetget(self, remote, local, options):
        """System call to ``gget`` external tool."""
        (gtool, archive, tampon, gname) = self._actualgget(remote['path'])
        sh = self.system
        sh.env.GGET_TAMPON = tampon

        fmt = options.get('fmt', 'foo')
        extract = remote['query'].get('extract', None)
        if extract and sh.path.exists(gname):
            logger.info("The resource was already fetched in a previous extract.")
            rc = True
        else:
            rc = sh.spawn([gtool, '-host', archive, gname], output=False)

        if rc and sh.path.exists(gname):
            if extract:
                # The file to extract may be in a tar file...
                if not sh.path.isdir(gname) and sh.is_tarname(gname) and sh.is_tarfile(gname):
                    destdir = sh.tarname_radix(sh.path.realpath(gname))
                    if sh.path.exists(destdir):
                        logger.info("%s was already fetched in a previous extract.", destdir)
                    else:
                        rc = len(sh.smartuntar(gname, destdir, output=False,
                                               uniquelevel_ignore=True)) > 0
                    gname = destdir
                logger.info('GCO Central Store get %s', gname + '/' + extract[0])
                rc = rc and sh.cp(gname + '/' + extract[0], local, fmt=fmt)
            else:
                # Always  move the resource to destination (fmt may influence the result)
                logger.info('GCO Central Store get %s', gname)
                rc = rc and sh.filecocoon(local)
                rc = rc and sh.mv(gname, local, fmt=fmt)
                # Automatic untar if needed... (the local file need to ends with a tar extension)
                if not sh.path.isdir(local) and sh.is_tarname(local) and sh.is_tarfile(local):
                    destdir = sh.path.dirname(sh.path.realpath(local))
                    sh.smartuntar(local, destdir, output=False, uniquelevel_ignore=True)
        else:
            logger.warning('GCO Central Store get %s was not successful (%s)', gname, rc)
        return rc

    def ggetdelete(self, remote, options):
        """This operation is not supported."""
        logger.warning('Removing from GCO Store is not supported')
        return False


class GcoCacheStore(CacheStore):
    """Some kind of cache for GCO components."""

    _footprint = dict(
        info = 'GCO cache access',
        attr = dict(
            scheme = dict(
                values  = ['gget'],
            ),
            netloc = dict(
                values  = ['gco.cache.fr'],
            ),
            strategy = dict(
                default = 'mtool',
            ),
            rootdir = dict(
                default = 'auto'
            ),
            headdir = dict(
                default = 'gco',
                outcast = ['xp', 'vortex'],
            ),
        )
    )

    def __init__(self, *args, **kw):
        """Proxy init method. Perform a cache reset after initialisation."""
        logger.debug('GCO cache store init %s', self.__class__)
        super(GcoCacheStore, self).__init__(*args, **kw)

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
            options_tmp = options.copy()
            options_tmp['auto_tarextract'] = True
            return self.incacheget(remote, local, options_tmp)

    def ggetput(self, local, remote, options):
        """Gateway to :meth:`incacheputt`."""
        extract = remote['query'].get('extract', None)
        if extract:
            logger.warning('Skip cache put with extracted %s', extract)
            return False
        else:
            return self.incacheput(local, remote, options)

    def ggetdelete(self, remote, options):
        """Gateway to :meth:`incachedelete`."""
        return self.incachedelete(remote, options)


class GcoStore(MultiStore):
    """Combined cache and central GCO stores."""

    _footprint = dict(
        info = 'GCO multi access',
        attr = dict(
            scheme = dict(
                values   = ['gget'],
            ),
            netloc = dict(
                values   = ['gco.multi.fr'],
            ),
            refillstore = dict(
                default  = True,
            )
        )
    )

    def alternates_netloc(self):
        """Tuple of alternates domains names, e.g. ``cache`` and ``archive``."""
        return ('gco.cache.fr', 'gco.meteo.fr')
