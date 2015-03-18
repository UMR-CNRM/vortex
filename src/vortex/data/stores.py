#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module handles store objects in charge of physically accessing resources.
Store objects use the :mod:`footprints` mechanism.
"""

#: Export base class
__all__ = [ 'Store' ]

import re
import json

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex import sessions
from vortex.layout import dataflow
from vortex.util import config
from vortex.tools import caches, date


class StoreGlue(object):
    """Defines a way to glue stored objects together."""

    def __init__(self, gluemap=None):
        logger.debug('Abstract glue init %s', self.__class__)
        if gluemap is None:
            self._gluemap = dict()
        else:
            self._gluemap = gluemap
        self._asdict = None
        self._cross = dict()

    @property
    def gluemap(self):
        """Property that returns internal glue-map object."""
        return self._gluemap

    def as_dump(self):
        """Return a nicely formated class name for dump in footprint."""
        return "{0:s}.{1:s}('{2:s}')".format(self.__module__, self.__class__.__name__, str(self.gluemap))

    def sections(self):
        """Returns a list of available glue section names. Mostly file archive names."""
        return self.gluemap.sections()

    def glueretrieve(self, section, option):
        """Generic function to retrieve the associated value to ``option`` in the specified ``section``."""
        if self.gluemap.has_option(section, option):
            return self.gluemap.get(section, option)
        else:
            logger.warning('No such section <%s> or option <%s> in %s', section, option, self)
            return None

    def gluetype(self, section):
        """Shortcut to retrieve option ``objtype``."""
        return self.glueretrieve(section, 'objtype')

    def gluename(self, section):
        """Shortcut to retrieve option ``objname``."""
        return self.glueretrieve(section, 'objname')

    def gluelist(self, section):
        """returns the list of options in the specified ``section``."""
        if self.gluemap.has_section(section):
            return [ x for x in self.gluemap.options(section) if not x.startswith('obj') ]
        else:
            logger.warning('No such section <%s> in %s', section, self)
            return []

    def as_dict(self):
        """Return the current internal gluemap as a pure dictionary."""
        if not self._asdict:
            self._asdict = dict()
            for section in self.gluemap.sections():
                self._asdict[section] = dict()
                for (opt, value) in self.gluemap.items(section):
                    lopt = re.split('[ :]', value)
                    self._asdict[section][opt] = dict(zip(lopt[::2], lopt[1::2]))
        return self._asdict

    def crossitem(self, item):
        """
        Possibly builds and then returns a reverse dictionay
        of founded options with the specified ``item`` defined.
        """
        if not item in self._cross:
            self._cross[item] = dict()
            for section, contents in self.as_dict().iteritems():
                for option, desc in contents.iteritems():
                    if item in desc:
                        if desc[item] not in self._cross[item]:
                            self._cross[item][desc[item]] = list()
                        localdesc = dict(section=section, option=option)
                        localdesc.update(desc)
                        self._cross[item][desc[item]].append(localdesc)
        return self._cross[item]

    def contains(self, checktype, checkvalue):
        """Generic boolean function to check if the specified ``value`` exists for this ``type``."""
        return checkvalue in self.crossitem(checktype)

    def containsfile(self, filename):
        """Shortcut to contains for a specified file."""
        return self.contains('file', filename)

    def containsformat(self, aformat):
        """Shortcut to contains for a specified format."""
        return self.contains('format', aformat)

    def getitem(self, itemtype, itemname):
        """Generic function to obtain the associated description of the item specified by type and name."""
        if self.contains(itemtype, itemname):
            return self.crossitem(itemtype).get(itemname)
        else:
            return None

    def getfile(self, filename):
        """Shortcut to get an item for a specified file."""
        return self.getitem('file', filename)

    def getformat(self, aformat):
        """Shortcut to get an item for a specified format."""
        return self.getitem('format', aformat)

    def filemap(self, system, dirname, basename):
        """Reformulates the actual physical path for the file requested."""
        gluedesc = self.getfile(basename)
        if len(gluedesc) > 1:
            logger.error('Multiple glue entries %s', gluedesc)
            cleanpath, targetpath = (None, None)
        else:
            gluedesc = gluedesc[0]
            targetpath = self.gluename(gluedesc['section']) + '.' + self.gluetype(gluedesc['section'])
            cleanpath = system.path.join(dirname, targetpath)
        return (cleanpath, targetpath)


class IniStoreGlue(StoreGlue):
    """Initialised StoreGlue with a delayed ini file."""

    def __init__(self, inifile=None):
        logger.debug('IniStoreGlue init %s', self.__class__)
        super(IniStoreGlue, self).__init__(config.DelayedConfigParser(inifile))


class Store(footprints.FootprintBase):
    """Root class for any :class:`Store` subclasses."""

    _abstract  = True
    _collector = ('store',)
    _footprint = dict(
        info = 'Default store',
        attr = dict(
            scheme = dict(
                alias = ('protocol',)
            ),
            netloc = dict(
                alias = ('domain', 'namespace')
            ),
        ),
    )

    def __init__(self, *args, **kw):
        logger.debug('Abstract store init %s', self.__class__)
        sh = kw.pop('system', sessions.system())
        super(Store, self).__init__(*args, **kw)
        self._sh = sh
        self.delayed = False

    @property
    def realkind(self):
        return 'store'

    @property
    def system(self):
        """Shortcut to current system interface."""
        return self._sh

    def use_cache(self):
        """Boolean fonction to check if the current store use a local cache."""
        return False

    def in_situ(self, local, options):
        """Return true when insitu option is active and local file exists."""
        return bool(options.get('insitu', False) and self.system.path.exists(local))

    def notyet(self, *args):
        """
        Internal method to be used as a critical backup method
        when a specific method is not yet defined.
        """
        logger.critical('Scheme %s not yet implemented', self.scheme)

    def check(self, remote, options=None):
        """Proxy method to dedicated check method accordind to scheme."""
        logger.debug('Store check from %s', remote)
        return getattr(self, self.scheme + 'check', self.notyet)(remote, options)

    def locate(self, remote, options=None):
        """Proxy method to dedicated get method accordind to scheme."""
        logger.debug('Store locate %s', remote)
        return getattr(self, self.scheme + 'locate', self.notyet)(remote, options)

    def get(self, remote, local, options=None):
        """Proxy method to dedicated get method accordind to scheme."""
        logger.debug('Store get from %s to %s', remote, local)
        if options is not None and options.get('incache', False) and not self.use_cache():
            logger.warning('Skip this store because a cache is requested')
            return True
        else:
            if self.in_situ(local, options):
                logger.info('Store %s in situ resource <%s>', self.footprint_clsname(), local)
                return True
            else:
                return getattr(self, self.scheme + 'get', self.notyet)(remote, local, options)

    def put(self, local, remote, options=None):
        """Proxy method to dedicated put method accordind to scheme."""
        logger.debug('Store put from %s to %s', local, remote)
        if options is not None and options.get('incache', False) and not self.use_cache():
            logger.warning('Skip this store because a cache is requested')
            return True
        else:
            return getattr(self, self.scheme + 'put', self.notyet)(local, remote, options)

    def delete(self, remote, options=None):
        """Proxy method to dedicated delete method accordind to scheme."""
        logger.debug('Store delete from %s', remote)
        return getattr(self, self.scheme + 'delete', self.notyet)(remote, options)


class MultiStore(footprints.FootprintBase):
    """Agregate various :class:`Store` items."""

    _abstract  = True
    _collector = ('store',)
    _footprint = dict(
        info = 'Multi store',
        attr = dict(
            scheme = dict(
                alias    = ('protocol',)
            ),
            netloc = dict(
                alias    = ('domain', 'namespace')
            ),
            refillstore = dict(
                type     = bool,
                optional = True,
                default  = False,
            )
        ),
    )

    def __init__(self, *args, **kw):
        logger.debug('Abstract multi store init %s', self.__class__)
        super(MultiStore, self).__init__(*args, **kw)
        self.openedstores = self.loadstores()
        self.delayed = False

    @property
    def realkind(self):
        return 'multistore'

    def loadstores(self):
        """
        Load default stores during the initialisation of the current object.
        Stores could be relaoded at any time. The current method provides
        a default loading mechanism through the actual module :func:`load` function
        and an alternate list of footprint descriptors as returned by method
        :func:`alternates_fp`.
        """
        activestores = list()
        for desc in self.alternates_fp():
            xstore = footprints.proxy.store(**desc)
            if xstore:
                activestores.append(xstore)
        logger.debug('Multistore %s includes active stores %s', self, activestores)
        return activestores

    def alternates_scheme(self):
        """Default method returns actual scheme in a tuple."""
        return (self.scheme,)

    def alternates_netloc(self):
        """Abstract method."""
        pass

    def alternates_fp(self):
        """
        Returns a list of anonymous descriptions to be used as footprint entries
        while loading alternates stores.
        """
        return [
            dict(scheme=x, netloc=y)
                for x in self.alternates_scheme()
                for y in self.alternates_netloc()
        ]

    def use_cache(self):
        """Boolean fonction to check if any included store use a local cache."""
        return any([ x.use_cache() for x in self.openedstores ])

    def in_situ(self, local, options):
        """Return cumulative value for the same method of internal opened stores."""
        rc = True
        for sto in self.openedstores:
            rc = rc and sto.in_situ(local, options)
        return rc

    def check(self, remote, options=None):
        """Go through internal opened stores and check for the resource."""
        logger.debug('Multistore check from %s', remote)
        rc = False
        for sto in self.openedstores:
            rc = sto.check(remote.copy(), options)
            if rc:
                break
        return rc

    def locate(self, remote, options=None):
        """Go through internal opened stores and locate the expected resource for each of them."""
        logger.debug('Multistore locate %s', remote)
        if not self.openedstores:
            return False
        rloc = list()
        for sto in self.openedstores:
            logger.debug('Multistore locate at %s', sto)
            rloc.append(sto.locate(remote.copy(), options))
        return ';'.join(rloc)

    def get(self, remote, local, options=None):
        """Go through internal opened stores for the first available resource."""
        logger.debug('Multistore get from %s to %s', remote, local)
        rc = False
        for num, sto in enumerate(self.openedstores):
            logger.debug('Multistore get at %s', sto)
            rc = sto.get(remote.copy(), local, options)
            if rc:
                if self.refillstore and num > 0:
                    restore = self.openedstores[num-1]
                    logger.info('Refill back in previous store [%s]', restore)
                    rc = restore.put(local, remote.copy(), options)
                break
        return rc

    def put(self, local, remote, options=None):
        """Go through internal opened stores and put resource for each of them."""
        logger.debug('Multistore put from %s to %s', local, remote)
        if not self.openedstores:
            logger.warning('Funny attemp to put on an emty multistore...')
            return False
        rc = True
        for sto in self.openedstores:
            logger.info('Multistore put at %s', sto)
            rcloc = sto.put(local, remote.copy(), options)
            logger.info('Multistore out = %s', rcloc)
            rc = rc and rcloc
        return rc

    def delete(self, remote, options=None):
        """Go through internal opened stores and delete the resource."""
        logger.debug('Multistore delete from %s', remote)
        rc = False
        for sto in self.openedstores:
            logger.info('Multistore delete at %s', sto)
            rc = sto.delete(remote.copy(), options)
            if not rc:
                break
        return rc


class MagicPlace(Store):
    """Somewher, over the rainbow!"""

    _footprint = dict(
        info = 'Evanescent physical store',
        attr = dict(
            scheme = dict(
                values   = ['magic'],
            ),
        ),
        priority = dict(
            level = footprints.priorities.top.DEFAULT
        )
    )

    @property
    def realkind(self):
        return 'magicstore'

    def magiccheck(self, remote, options):
        """Void - Always False."""
        return False

    def magiclocate(self, remote, options):
        """Void - Empty string returned."""
        return ''

    def magicget(self, remote, local, options):
        """Void - Always True."""
        return True

    def magicput(self, local, remote, options):
        """Void - Always True."""
        return True

    def magicdelete(self, remote, options):
        """Void - Always False."""
        return False


class Finder(Store):
    """The most usual store: your current filesystem!"""

    _footprint = dict(
        info = 'Miscellaneous file access',
        attr = dict(
            scheme = dict(
                values  = ['file', 'ftp', 'rcp', 'scp'],
            ),
            netloc = dict(
                outcast = ['oper.inline.fr'],
            )
        ),
        priority = dict(
            level = footprints.priorities.top.DEFAULT
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Abstract store init %s', self.__class__)
        super(Finder, self).__init__(*args, **kw)

    @property
    def realkind(self):
        return 'finder'

    def hostname(self):
        """Returns the current :attr:`netloc`."""
        return self.netloc

    def fullpath(self, remote):
        """Return actual path unless explicitly defined as relative path."""
        if remote['query'].get('relative', False):
            return remote['path'].lstrip('/')
        else:
            return remote['path']

    def filecheck(self, remote, options):
        """Returns a stat-like object if the ``remote`` exists on the ``system`` provided."""
        try:
            st = self.system.stat(self.fullpath(remote))
        except OSError:
            st = None
        return st

    def filelocate(self, remote, options):
        """Returns the real path."""
        return self.fullpath(remote)

    def fileget(self, remote, local, options):
        """Delegates to ``system`` the copy of ``remote`` to ``local``."""
        rpath = self.fullpath(remote)
        if 'intent' in options and options['intent'] == dataflow.intent.IN:
            logger.info('Ignore intent <in> for remote input %s', rpath)
        return self.system.cp(rpath, local, fmt=options.get('fmt'))

    def fileput(self, local, remote, options):
        """Delegates to ``system`` the copy of ``local`` to ``remote``."""
        return self.system.cp(local, self.fullpath(remote), fmt=options.get('fmt'))

    def filedelete(self, remote, options):
        """Delegates to ``system`` the removing of ``remote``."""
        rc = None
        if self.filecheck(remote, options):
            rc = self.system.remove(self.fullpath(remote), fmt=options.get('fmt'))
        else:
            logger.error('Try to remove a non-existing resource <%s>', self.fullpath(remote))
        return rc

    def ftpcheck(self, remote, options):
        """Delegates to ``system.ftp`` a distant check."""
        rc = None
        ftp = self.system.ftp(self.hostname(), remote['username'])
        if ftp:
            rc = ftp.size(self.rootdir + remote['path'])
            ftp.close()
        return rc

    def ftplocate(self, remote, options):
        """Delegates to ``system`` qualified name creation."""
        ftp = self.system.ftp(self.hostname(), remote['username'])
        if ftp:
            rloc = ftp.netpath(self.fullpath(remote))
            ftp.close()
            return rloc
        else:
            return None

    def ftpget(self, remote, local, options):
        """Delegates to ``system`` the file transfer of ``remote`` to ``local``."""
        return self.system.ftget(
            self.fullpath(remote),
            local,
            # ftp control
            hostname = self.hostname(),
            logname  = remote['username'],
            fmt      = options.get('fmt'),
        )

    def ftpput(self, local, remote, options):
        """Delegates to ``system`` the file transfer of ``local`` to ``remote``."""
        return self.system.ftput(
            local,
            self.fullpath(remote),
            # ftp control
            hostname = self.hostname(),
            logname  = remote['username'],
            fmt      = options.get('fmt'),
        )

    def ftpdelete(self, remote, options):
        """Delegates to ``system`` a distant remove."""
        rc = None
        ftp = self.system.ftp(self.hostname(), remote['username'])
        if ftp:
            actualpath = self.fullpath(remote)
            if self.ftpcheck(actualpath):
                rc = ftp.delete(actualpath)
                ftp.close()
            else:
                logger.error('Try to remove a non-existing resource <%s>', actualpath)
        return rc


class ArchiveStore(Store):
    """Generic Archive Store."""

    _footprint = dict(
        info = 'Generic archive store',
        attr = dict(
            scheme = dict(
                values   = ['ftp', 'ftserv'],
            ),
            netloc = dict(
                values   = ['open.archive.fr'],
            ),
            rootdir = dict(
                optional = True,
                default  = '/home/m/marp/marp999',
            ),
            headdir = dict(
                optional = True,
                default  = 'sto',
            ),
            storage = dict(
                optional = True,
                default  = 'hendrix.meteo.fr',
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Archive store init %s', self.__class__)
        super(ArchiveStore, self).__init__(*args, **kw)

    @property
    def realkind(self):
        return 'archivestore'

    def hostname(self):
        """Returns the current :attr:`storage`."""
        return self.storage

    def remapget(self, remote, options):
        """Reformulates the remote path to compatible vortex namespace."""
        pass

    def ftpcheck(self, remote, options):
        """Delegates to ``system.ftp`` a distant check."""
        rc = None
        ftp = self.system.ftp(self.hostname(), remote['username'])
        if ftp:
            rc = ftp.size(self.rootdir + remote['path'])
            ftp.close()
        return rc

    def ftplocate(self, remote, options):
        """Delegates to ``system.ftp`` the path evaluation."""
        rc = None
        ftp = self.system.ftp(self.hostname(), remote['username'])
        if ftp:
            rc = ftp.netpath(self.rootdir + remote['path'])
            ftp.close()
        return rc

    def ftpget(self, remote, local, options):
        """Delegates to ``system.ftp`` the get action."""
        return self.system.ftget(
            self.rootdir + remote['path'],
            local,
            # ftp control
            hostname = self.hostname(),
            logname  = remote['username'],
            fmt      = options.get('fmt'),
        )

    def ftpput(self, local, remote, options):
        """Delegates to ``system.ftp`` the put action."""
        return self.system.ftput(
            local,
            self.system.path.join(
                remote.get('root', self.rootdir),
                remote['path'].lstrip(self.system.path.sep)
            ),
            # ftp control
            hostname = self.hostname(),
            logname  = remote['username'],
            fmt      = options.get('fmt'),
        )

    def ftpdelete(self, remote, options):
        """Delegates to ``system`` a distant remove."""
        rc = None
        ftp = self.system.ftp(self.hostname(), remote['username'])
        if ftp:
            actualpath = self.fullpath(remote)
            if self.ftpcheck(actualpath):
                rc = ftp.delete(actualpath)
                ftp.close()
            else:
                logger.error('Try to remove a non-existing resource <%s>', actualpath)
        return rc


class VortexArchiveStore(ArchiveStore):
    """Some kind of archive for VORTEX experiments."""

    _footprint = dict(
        info = 'VORTEX archive access',
        attr = dict(
            scheme = dict(
                values   = ['vortex', 'ftp', 'ftserv'],
            ),
            netloc = dict(
                values   = ['open.archive.fr', 'vortex.archive.fr'],
                remap    = {
                    'vortex.archive.fr': 'open.archive.fr'
                },
            ),
            headdir = dict(
                default  = 'vortex',
                outcast  = ['xp'],
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Vortex archive store init %s', self.__class__)
        super(VortexArchiveStore, self).__init__(*args, **kw)

    def remapget(self, remote, options):
        """Reformulates the remote path to compatible vortex namespace."""
        xpath = remote['path'].split('/')
        xpath[3:4] = list(xpath[3])
        xpath[:0] = [self.system.path.sep, self.headdir]
        remote['path'] = self.system.path.join(*xpath)

    def vortexcheck(self, remote, options):
        """Remap and ftpcheck sequence."""
        self.remapget(remote, options)
        return self.ftpcheck(remote, options)

    def vortexlocate(self, remote, options):
        """Remap and ftplocate sequence."""
        self.remapget(remote, options)
        return self.ftplocate(remote, options)

    def vortexget(self, remote, local, options):
        """Remap and ftpget sequence."""
        self.remapget(remote, options)
        return self.ftpget(remote, local, options)

    def vortexput(self, local, remote, options):
        """Remap root dir and ftpput sequence."""
        if not 'root' in remote:
            remote['root'] = self.headdir
        return self.ftpput(local, remote, options)

    def vortexdelete(self, remote, options):
        """Remap and ftpdelete sequence."""
        self.remapget(remote, options)
        return self.ftpdelete(remote, options)


class CacheStore(Store):
    """Generic Cache Store."""

    _footprint = dict(
        info = 'Generic cache store',
        attr = dict(
            scheme = dict(
                values   = ['incache'],
            ),
            netloc = dict(
                values   = ['open.cache.fr'],
            ),
            strategy = dict(
                optional = True,
                default  = 'std',
            ),
            rootdir = dict(
                optional = True,
                default  = 'conf'
            ),
            headdir = dict(
                optional = True,
                default  = 'conf',
            ),
            storage = dict(
                optional = True,
                default  = None,
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Generic cache store init %s', self.__class__)
        super(CacheStore, self).__init__(*args, **kw)
        del self.cache

    @property
    def realkind(self):
        return 'cachestore'

    @property
    def hostname(self):
        """Returns the current :attr:`storage`."""
        tg = self.system.target()
        return tg.inetname if self.storage is None else self.storage

    def use_cache(self):
        """Boolean value to insure that this store is using a cache."""
        return True

    def _get_cache(self):
        if not self._cache:
            self._cache = footprints.proxy.caches.default(
                kind    = self.strategy,
                storage = self.hostname,
                rootdir = self.rootdir,
                headdir = self.headdir,
            )
        return self._cache

    def _set_cache(self, newcache):
        """Set a new cache reference."""
        if isinstance(newcache, caches.Cache):
            self._cache = newcache

    def _del_cache(self):
        """Invalidate internal cache reference."""
        self._cache = None

    cache = property(_get_cache, _set_cache, _del_cache)

    def incachecheck(self, remote, options):
        """Returns a stat-like object if the ``remote`` exists in the current cache."""
        try:
            st = self.system.stat(self.incachelocate(remote, options))
        except OSError:
            st = None
        return st

    def incachelocate(self, remote, options):
        """Agregates cache to remote subpath."""
        return self.cache.fullpath(remote['path'])

    def incacheget(self, remote, local, options):
        """Simple copy from current cache cache to ``local``."""
        return self.cache.retrieve(
            remote['path'],
            local,
            intent = options.get('intent'),
            fmt    = options.get('fmt')
        )

    def incacheput(self, local, remote, options):
        """Simple copy from ``local`` to the current cache in readonly mode."""
        return self.cache.insert(
            remote['path'],
            local,
            intent = 'in',
            fmt    = options.get('fmt')
        )

    def incachedelete(self, remote, options):
        """Simple removing of the remote resource in cache."""
        return self.cache.delete(
            remote['path'],
            fmt = options.get('fmt')
        )


class VortexCacheStore(CacheStore):
    """Some kind of cache for VORTEX experiments."""

    _footprint = dict(
        info = 'VORTEX cache access',
        attr = dict(
            scheme = dict(
                values  = ['vortex'],
            ),
            netloc = dict(
                values  = ['open.cache.fr', 'vortex.cache.fr'],
                remap   = {
                    'vortex.cache.fr': 'open.cache.fr'
                },
            ),
            strategy = dict(
                default = 'mtool',
            ),
            rootdir = dict(
                default = 'auto'
            ),
            headdir = dict(
                default = 'vortex',
                outcast = ['xp'],
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Vortex cache store init %s', self.__class__)
        super(VortexCacheStore, self).__init__(*args, **kw)
        del self.cache

    def vortexcheck(self, remote, options):
        """Proxy to :meth:`incachecheck`."""
        return self.incachecheck(remote, options)

    def vortexlocate(self, remote, options):
        """Proxy to :meth:`incachelocate`."""
        return self.incachelocate(remote, options)

    def vortexget(self, remote, local, options):
        """Proxy to :meth:`incacheget`."""
        return self.incacheget(remote, local, options)

    def vortexput(self, local, remote, options):
        """Proxy to :meth:`incacheputt`."""
        return self.incacheput(local, remote, options)

    def vortexdelete(self, remote, options):
        """Proxy to :meth:`incachedelete`."""
        return self.incachedelete(remote, options)


class VortexStore(MultiStore):
    """Combined cache and archive VORTEX stores."""

    _footprint = dict(
        info = 'VORTEX multi access',
        attr = dict(
            scheme = dict(
                values  = ['vortex'],
            ),
            netloc = dict(
                values  = ['vortex.multi.fr'],
            ),
            refillstore = dict(
                default = True,
            )
        )
    )

    def alternates_netloc(self):
        """Tuple of alternates domains names, e.g. ``cache`` and ``archive``."""
        return ('vortex.cache.fr', 'vortex.archive.fr')


class PromiseCacheStore(VortexCacheStore):
    """Some kind of vortex cache for EXPECTED resources."""

    _footprint = dict(
        info = 'EXPECTED cache access',
        attr = dict(
            netloc = dict(
                values  = ['promise.cache.fr'],
            ),
            headdir = dict(
                default = 'promise',
                outcast = ['xp', 'vortex'],
            ),
        )
    )


class PromiseStore(footprints.FootprintBase):
    """Combined a Promise Store for expected resources and any other matching Store."""

    _abstract  = True
    _collector = ('store',)
    _footprint = dict(
        info = 'Promise store',
        attr = dict(
            scheme = dict(
                alias    = ('protocol',)
            ),
            netloc = dict(
                alias    = ('domain', 'namespace')
            ),
            prstorename = dict(
                optional = True,
                default  = 'promise.cache.fr',
            ),
            prlogfile = dict(
                optional = True,
                default  = 'vortex-promises.log',
            ),
        ),
    )

    def __init__(self, *args, **kw):
        logger.debug('Abstract promise store init %s', self.__class__)
        sh = kw.pop('system', sessions.system())
        super(PromiseStore, self).__init__(*args, **kw)
        self._sh = sh

        # Assume that the actual scheme is the current scheme without "x" prefix
        self.proxyscheme = self.scheme.lstrip('x')

        # Find a store for the promised resources
        self.promise = footprints.proxy.store(
            scheme = self.proxyscheme,
            netloc = self.prstorename,
        )
        if self.promise is None:
            logger.critical('Could not find store scheme <%s> netloc <%s>', self.proxyscheme, self.prstorename)
            raise ValueError('Could not get a Promise Store')

        # Find the other "real" store (could be a multi-store)
        self.other = footprints.proxy.store(
            scheme = self.proxyscheme,
            netloc = self.netloc,
        )
        if self.other is None:
            logger.critical('Could not find store scheme <%s> netloc <%s>', self.proxyscheme, self.netloc)
            raise ValueError('Could not get an Other Store')

        self.openedstores = (self.promise, self.other)
        self.delayed = False

    @property
    def realkind(self):
        return 'promisestore'

    @property
    def system(self):
        """Shortcut to current system interface."""
        return self._sh

    def in_situ(self, local, options):
        """Return cumulative value for the same method of internal opened stores."""
        rc = True
        for sto in self.openedstores:
            rc = rc and sto.in_situ(local, options)
        return rc

    def mkpromise_info(self, remote, options):
        """Build a dictionary with relevant informations for the promise."""
        return dict(
            promise  = True,
            stamp    = date.stamp(),
            itself   = self.promise.locate(remote, options),
            locate   = self.other.locate(remote, options),
            datafmt  = options.get('fmt', None),
            rhandler = options.get('rhandler', None),
        )

    def mkpromise_file(self, info, local):
        """Build a virtual container with specified informations."""
        pfile = local + '.pr'
        self.system.json_dump(info, pfile)
        return pfile

    def mkpromise_log(self, info):
        """Insert current promise information to promises logfile."""
        sh = self.system
        loglist = list()
        logboard = footprints.observers.get(tag='Promises-Log')
        if self.prlogfile and sh.path.exists(self.prlogfile):
            loglist = sh.json_load(self.prlogfile)
        else:
            logboard.notify_new(self, dict(logfile=sh.path.realpath(self.prlogfile)))
        loglist.append(info)
        sh.json_dump(loglist, self.prlogfile)
        logboard.notify_upd(
            self, dict(
                logfile = sh.path.realpath(self.prlogfile),
                logsize = len(loglist),
            )
        )

    def check(self, remote, options=None):
        """Go through internal opened stores and check for the resource."""
        logger.debug('Promise check from %s', remote)
        return self.other.check(remote.copy(), options) or self.promise.check(remote.copy(), options)

    def locate(self, remote, options=None):
        """Go through internal opened stores and locate the expected resource for each of them."""
        logger.debug('Promise locate %s', remote)
        return self.promise.locate(remote.copy(), options) + ';' + self.other.locate(remote.copy(), options)

    def get(self, remote, local, options=None):
        """Go through internal opened stores for the first available resource."""
        logger.debug('Promise get %s', remote)
        if options is None:
            options = dict()
        self.delayed = False
        if self.in_situ(local, options):
            logger.info('Store %s in situ resource <%s>', self.footprint_clsname(), local)
            if self.system.size(local) < 4096:
                pr = dict()
                try:
                    pr = self.system.json_load(local)
                except ValueError:
                    logger.warning('Small expected in situ resource not json friendly <%s>', local)
                self.delayed = pr.get('promise', False)
            return True
        else:
            logger.info('Try promise from store %s', self.promise)
            oldfmt = options.pop('fmt', None)
            options['fmt'] = 'ascii'
            rc = self.promise.get(remote.copy(), local, options)
            if rc:
                self.delayed = True
            else:
                logger.info('Try promise from store %s', self.other)
                options['fmt'] = oldfmt
                rc = self.other.get(remote.copy(), local, options)
            if not rc and options.get('pretend', False):
                logger.warning('Pretending to get a promise for <%s>', local)
                pr_info = self.mkpromise_info(remote, options)
                pr_file = self.mkpromise_file(pr_info, local)
                self.system.move(pr_file, local)
                rc = self.delayed = True
        return rc

    def put(self, local, remote, options=None):
        """Put a promise or the actual resource if available."""
        logger.debug('Multistore put from %s to %s', local, remote)
        rc = False
        if options is None:
            options = dict()
        if options.get('force', False) or not self.system.path.exists(local):
            if not self.other.use_cache():
                logger.critical('Could not promise resource without other cache <%s>', self.other)
                raise ValueError('Could not promise: other store does not use cache')
            logger.warning('Log a promise instead of missing resource <%s>', local)
            pr_info = self.mkpromise_info(remote, options)
            pr_file = self.mkpromise_file(pr_info, local)
            oldfmt = options.pop('fmt', None)
            options['fmt'] = 'ascii'
            rc = self.promise.put(pr_file, remote.copy(), options)
            self.mkpromise_log(pr_info)
            self.system.remove(pr_file)
            if rc:
                options['fmt'] = oldfmt
                self.other.delete(remote.copy(), options)
        else:
            logger.info('Actual promise does exists <%s>', local)
            rc = self.other.put(local, remote.copy(), options)
            if rc:
                options['fmt'] = 'ascii'
                self.promise.delete(remote.copy(), options)
        return rc

    def delete(self, remote, options=None):
        """Go through internal opened stores and delete the resource."""
        logger.debug('Promise delete from %s', remote)
        return self.promise.delete(remote.copy(), options) and self.other.delete(remote.copy(), options)


class VortexPromiseStore(PromiseStore):
    """Combined a Promise Store for expected resources and any VORTEX Store."""

    _footprint = dict(
        info = 'VORTEX promise store',
        attr = dict(
            scheme = dict(
                values = ['xvortex'],
            ),
        )
    )

class PromisesObserver(footprints.util.GetByTag, footprints.observers.Observer):
    """Track promises logfiles."""

    def __init__(self):
        """Instanciate a set of lognames."""
        self._logs = dict()
        footprints.observers.get(tag='Promises-Log').register(self)

    @property
    def logs(self):
        return self._logs

    def newobsitem(self, item, info):
        """A new ``item`` has been created. Some information is provided through the dict ``info``."""
        super(PromisesObserver, self).newobsitem(item, info)
        self.logs[info.get('logfile')] = 0

    def updobsitem(self, item, info):
        """A new ``item`` has been created. Some information is provided through the dict ``info``."""
        super(PromisesObserver, self).updobsitem(item, info)
        self.logs[info.get('logfile')] = info.get('logsize')

    def clear_promises(self):
        """Remove promises registred in current logfiles."""
        for thislog in self.logs:
            logger.info('Clear promises from <%s>', thislog)
