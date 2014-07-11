#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module handles store objects in charge of physically accessing resources.
Store objects use the :mod:`footprints` mechanism.
"""

#: Export base class
__all__ = [ 'Store' ]

import re

import footprints

from vortex import sessions
from vortex.autolog import logdefault as logger
from vortex.layout import dataflow
from vortex.tools import config


class StoreGlue(object):
    """Defines a way to glue stored objects together."""

    def __init__(self, gluemap=dict()):
        logger.debug('Abstract glue init %s', self.__class__)
        self.gluemap = gluemap
        self._asdict = None
        self._cross = dict()

    def dumpshortcut(self):
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
            return filter(lambda x: not x.startswith('obj'), self.gluemap.options(section))
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
            cleanpath, targetpath = ( None, None )
        else:
            gluedesc = gluedesc[0]
            targetpath = self.gluename(gluedesc['section']) + '.' + self.gluetype(gluedesc['section'])
            cleanpath = system.path.join(dirname, targetpath)
        return ( cleanpath, targetpath )


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

    @property
    def realkind(self):
        """Defines the kind of this object, here ``store``."""
        return 'store'

    @property
    def system(self):
        """Shortcut to current system interface."""
        return self._sh

    def in_situ(self, local, options):
        """Return true when insitu option is active and local file exists."""
        return bool(options.get('insitu', False) and self.system.path.exists(local))

    def in_place(self, localio):
        """Return true when the current io resource is defined (either io descriptor or file)."""
        return bool(localio is not None and (type(localio) is not str or self.system.path.exists(localio)))

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
        if self.in_situ(local, options):
            logger.warning('Store %s in situ resource %s', self.shortname(), local)
            return True
        else:
            return getattr(self, self.scheme + 'get', self.notyet)(remote, local, options)

    def put(self, local, remote, options=None):
        """Proxy method to dedicated put method accordind to scheme."""
        logger.debug('Store put from %s to %s', local, remote)
        return getattr(self, self.scheme + 'put', self.notyet)(local, remote, options)


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

    def loadstores(self):
        """
        Load default stores during the initialisation of the current object.
        Stores could be relaoded at any time. The current method provides
        a default loading mechanism through the actual module :func:`load` function
        and an alternate list of footprint descriptors as returned by method
        :func:`alternatefp`.
        """
        activestores = list()
        for desc in self.alternatefp():
            xstore = footprints.proxy.store(**desc)
            if xstore:
                activestores.append(xstore)
        logger.info('Multi store %s includes active stores %s', self, activestores)
        return activestores

    def alternatefp(self):
        """
        Returns a list of anonymous descriptions to be used as footprint entries
        while loading alternates stores."""
        fplist = list()
        for domain in self.alternates_netloc():
            fplist.append(dict(
                scheme=self.scheme,
                netloc=domain,
            ))
        return fplist

    def alternates_netloc(self):
        """Abstract method."""
        pass

    def in_situ(self, local, options):
        """Return cumulative value for the same method of internal opened stores."""
        rc = True
        for sto in self.openedstores:
            rc = rc and sto.in_situ(local, options)
        return rc

    def in_place(self, localio):
        """Return cumulative value for the same method of internal opened stores."""
        rc = True
        for sto in self.openedstores:
            rc = rc and sto.in_place(localio)
        return rc

    def check(self, remote, options=None):
        """Go through internal opened stores and check for the resource."""
        logger.debug('Multi Store check from %s', remote)
        rc = False
        for sto in self.openedstores:
            rc = sto.check(remote.copy(), options)
            if rc:
                break
        return rc

    def locate(self, remote, options=None):
        """Go through internal opened stores and locate the expected resource for each of them."""
        logger.debug('Multi Store locate %s', remote)
        if not self.openedstores:
            return False
        rloc = list()
        for sto in self.openedstores:
            logger.info('Multi locate at %s', sto)
            rloc.append(sto.locate(remote.copy(), options))
        return ';'.join(rloc)

    def get(self, remote, local, options=None):
        """Go through internal opened stores for the first available resource."""
        logger.info('Multi Store get from %s to %s', remote, local)
        rc = False
        for num, sto in enumerate(self.openedstores):
            logger.info('Multi get at %s', sto)
            rc = sto.get(remote.copy(), local, options)
            if rc:
                if self.refillstore and num > 0:
                    restore = self.openedstores[num-1]
                    logger.info('Refill back in previous store %s', restore)
                    rc = restore.put(local, remote.copy(), options)
                break
        return rc

    def put(self, local, remote, options=None):
        """Go through internal opened stores and put resource for each of them."""
        logger.debug('Multi Store put from %s to %s', local, remote)
        if not self.openedstores:
            return False
        rc = True
        for sto in self.openedstores:
            logger.info('Multi put at %s', sto)
            rc = sto.put(local, remote.copy(), options) and rc
        return rc


class MagicPlace(Store):
    """Somewher, over the rainbow!"""

    _footprint = dict(
        info = 'Evanescent physical store',
        attr = dict(
            scheme = dict(
                values   = [ 'magic' ],
            ),
        ),
        priority = dict(
            level = footprints.priorities.top.DEFAULT
        )
    )

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


class Finder(Store):
    """The most usual store: your current filesystem!"""

    _footprint = dict(
        info = 'Miscellaneous file access',
        attr = dict(
            scheme = dict(
                values   = [ 'file', 'ftp', 'rcp', 'scp' ],
            ),
            netloc = dict(
                outcast  = [ 'oper.inline.fr' ],
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
            logger.warning('Ignore intent <in> for remote input %s', rpath)
        return self.system.cp(rpath, local, fmt=options.get('fmt'))

    def fileput(self, local, remote, options):
        """Delegates to ``system`` the copy of ``local`` to ``remote``."""
        return self.system.cp(local, self.fullpath(remote), fmt=options.get('fmt'))

    def ftpcheck(self, remote, options):
        """Delegates to ``system`` a distant check."""
        ftp = self.system.ftp(self.hostname(), remote['username'])
        if ftp:
            rc = ftp.size(self.fullpath(remote))
            ftp.close()
            return rc
        else:
            return None

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
        """Delegates to ``system`` the file transfert of ``remote`` to ``local``."""
        ftp = self.system.ftp(self.hostname(), remote['username'])
        if ftp:
            rc = ftp.get(self.fullpath(remote), local)
            ftp.close()
            return rc

    def ftpput(self, local, remote, options):
        """Delegates to ``system`` the file transfert of ``local`` to ``remote``."""
        return self.system.ftput(
            local,
            self.fullpath(remote),
            # ftp control
            hostname = self.hostname(),
            logname  = remote['username'],
            fmt      = options.get('fmt')
        )


class ArchiveStore(Store):
    """Generic Archive Store."""

    _footprint = dict(
        info = 'Generic archive store',
        attr = dict(
            scheme = dict(
                values   = [ 'ftp', 'ftserv' ],
            ),
            netloc = dict(
                values   = [ 'open.archive.fr' ],
            ),
            rootdir = dict(
                optional = True,
                default  = '/home/m/marp/marp999'
            ),
            headdir = dict(
                optional = True,
                default  = 'sto'
            ),
            storage = dict(
                optional = True,
                default  = 'cougar.meteo.fr'
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
        ftp = self.system.ftp(self.hostname(), remote['username'])
        if ftp:
            rc = ftp.size(self.rootdir + remote['path'])
            ftp.close()
            return rc
        else:
            return None

    def ftplocate(self, remote, options):
        """Delegates to ``system.ftp`` the path evaluation."""
        ftp = self.system.ftp(self.hostname(), remote['username'])
        if ftp:
            rloc = ftp.netpath(self.rootdir + remote['path'])
            ftp.close()
            return rloc
        else:
            return None

    def ftpget(self, remote, local, options):
        """Delegates to ``system.ftp`` the put action."""
        ftp = self.system.ftp(self.hostname(), remote['username'])
        if ftp:
            rc = ftp.get(self.rootdir + remote['path'], local)
            ftp.close()
            return rc
        else:
            return False

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
            fmt      = options.get('fmt')
        )


class VortexArchiveStore(ArchiveStore):
    """Some kind of archive for VORTEX experiments."""

    _footprint = dict(
        info = 'VORTEX archive access',
        attr = dict(
            scheme = dict(
                values   = [ 'vortex', 'ftp', 'ftserv' ],
            ),
            netloc = dict(
                values   = [ 'open.archive.fr', 'vortex.archive.fr' ],
                remap    = {
                    'vortex.archive.fr': 'open.archive.fr'
                },
            ),
            headdir = dict(
                default  = 'vortex',
                outcast  = [ 'xp' ]
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
        xpath[:0] = [ self.system.path.sep, self.headdir ]
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


class CacheStore(Store):
    """Generic Cache Store."""

    _footprint = dict(
        info = 'Generic cache store',
        attr = dict(
            scheme = dict(
                values   = [ 'incache' ],
            ),
            netloc = dict(
                values   = [ 'open.cache.fr' ],
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
                default  = 'localhost'
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Generic cache store init %s', self.__class__)
        super(CacheStore, self).__init__(*args, **kw)
        self.resetcache()

    @property
    def realkind(self):
        return 'storecache'

    @property
    def hostname(self):
        """Returns the current :attr:`storage`."""
        return self.storage

    def setcache(self, newcache):
        """Set a new cache reference."""
        self._cache = newcache

    def resetcache(self):
        """Invalidate internal cache reference."""
        self._cache = None

    @property
    def cache(self):
        if not self._cache:
            self._cache = footprints.proxy.caches.default(
                kind    = self.strategy,
                storage = self.storage,
                rootdir = self.rootdir,
                headdir = self.headdir
            )
        return self._cache

    def incachecheck(self, remote, options):
        """Returns a stat-like object if the ``remote`` exists in the current cache."""
        try:
            st = self.system.stat(self.incachelocate(remote, options))
        except OSError:
            st = None
        return st

    def incachelocate(self, remote, options):
        """Agregates cache to remore subpath."""
        return self.cache.entry(self.system) + remote['path']

    def incacheget(self, remote, local, options):
        """Simple copy from current cache cache to ``local``."""
        return self.system.cp(
            self.cache.entry(self.system) + remote['path'],
            local,
            intent = options.get('intent'),
            fmt    = options.get('fmt')
        )

    def incacheput(self, local, remote, options):
        """Simple copy from ``local`` to the current cache in readonly mode."""
        return self.system.cp(
            local,
            self.cache.entry(self.system) + remote['path'],
            intent = 'in',
            fmt    = options.get('fmt')
        )


class VortexCacheStore(CacheStore):
    """Some kind of cache for VORTEX experiments."""

    _footprint = dict(
        info = 'VORTEX cache access',
        attr = dict(
            scheme = dict(
                values = [ 'vortex' ],
            ),
            netloc = dict(
                values = [ 'open.cache.fr', 'vortex.cache.fr' ],
                remap = {
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
                outcast = [ 'xp' ],
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Vortex cache store init %s', self.__class__)
        super(VortexCacheStore, self).__init__(*args, **kw)
        self.resetcache()

    def vortexcheck(self, remote, options):
        """Gateway to :meth:`incachecheck`."""
        return self.incachecheck(remote, options)

    def vortexlocate(self, remote, options):
        """Gateway to :meth:`incachelocate`."""
        return self.incachelocate(remote, options)

    def vortexget(self, remote, local, options):
        """Gateway to :meth:`incacheget`."""
        return self.incacheget(remote, local, options)

    def vortexput(self, local, remote, options):
        """Gateway to :meth:`incacheputt`."""
        return self.incacheput(local, remote, options)


class VortexStore(MultiStore):
    """Combined cache and archive VORTEX stores."""

    _footprint = dict(
        info = 'Vortex multi access',
        attr = dict(
            scheme = dict(
                values = [ 'vortex' ],
            ),
            netloc = dict(
                values = [ 'vortex.multi.fr' ],
            ),
            refillstore = dict(
                default = True,
            )
        )
    )

    def alternates_netloc(self):
        """Tuple of alternates domains names, e.g. ``cache`` and ``archive``."""
        return ( 'vortex.cache.fr', 'vortex.archive.fr' )


