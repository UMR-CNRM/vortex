#!/bin/env python
# -*- coding: utf-8 -*-

"""
This module handles store objects in charge of physically accessing resources.
The associated modules defines the catalog factory based on the shared footprint
mechanism.
"""

#: Export base class
__all__ = [ 'Store' ]

import re
import sys
from vortex.autolog import logdefault as logger
from vortex.syntax import BFootprint
from vortex.syntax.priorities import top
from vortex.layout import dataflow
from vortex.tools import config, caches
from vortex.utilities.catalogs import ClassesCollector, cataloginterface


class StoreGlue(object):
    """Defines a way to glue stored objects together."""

    def __init__(self, gluemap=dict()):
        logger.debug('Abstract glue init %s', self.__class__)
        self.gluemap = gluemap
        self._asdict = None
        self._cross = dict()

    def dumpinfp(self):
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


class Store(BFootprint):
    """Root class for any :class:`Store` subclasses."""

    _footprint = dict(
        info = 'Default store',
        attr = dict(
            scheme = dict(
                alias = ( 'protocol', )
            ),
            netloc = dict(
                alias = ( 'domain', 'namespace' )
            ),
        ),
    )

    def __init__(self, *args, **kw):
        logger.debug('Abstract store init %s', self.__class__)
        super(Store, self).__init__(*args, **kw)

    @property
    def realkind(self):
        """Defines the kind of this object, here ``store``."""
        return 'store'

    def in_situ(self, local, options):
        system = options.get('system', None)
        return bool(system and options.get('insitu', False) and system.path.exists(local))

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
            logger.warning('Store %s using in situ resource: %s', self.shortname(), local)
            return True
        else:
            return getattr(self, self.scheme + 'get', self.notyet)(remote, local, options)

    def put(self, local, remote, options=None):
        """Proxy method to dedicated put method accordind to scheme."""
        logger.debug('Store put from %s to %s', local, remote)
        return getattr(self, self.scheme + 'put', self.notyet)(local, remote, options)


class MultiStore(BFootprint):
    """Agregate various :class:`Store` items."""

    _footprint = dict(
        info = 'Multi store',
        attr = dict(
            scheme = dict(
                alias = ( 'protocol', )
            ),
            netloc = dict(
                alias = ( 'domain', 'namespace' )
            ),
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
        thisloader = sys.modules.get(__name__).load
        activestores = list()
        for desc in self.alternatefp():
            xstore = thisloader(**desc)
            if xstore:
                activestores.append(xstore)
        logger.info('Multi active stores %s = %s', self, activestores)
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

    def check(self, remote, options=None):
        """Go through internal opened stores and check for the resource."""
        logger.debug('Multi Store check from %s', remote)
        rc = False
        for sto in self.openedstores:
            rc = sto.check(remote, options)
            if rc:
                break
        return rc

    def locate(self, remote, options=None):
        """Go through internal opened stores and locate the expected resource for each of them."""
        logger.debug('Multi Store locate %s', remote)
        if not self.openedstores:
            return False
        rloc = list
        for sto in self.openedstores:
            logger.info('Multi locate at %s', sto)
            rloc.append(sto.locate(remote, options))
        return ';'.join(rloc)

    def get(self, remote, local, options=None):
        """Go through internal opened stores for the first available resource."""
        logger.info('Multi Store get from %s to %s', remote, local, options)
        rc = False
        for sto in self.openedstores:
            logger.info('Multi get at %s', sto)
            rc = sto.get(remote, local, options)
            if rc:
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
            rc = sto.put(local, remote) and rc
        return rc


class Finder(Store):
    """The most usual store: your current filesystem!"""

    _footprint = dict(
        info = 'Miscellaneous file access',
        attr = dict(
            scheme = dict(
                values = [ 'file', 'ftp', 'rcp', 'scp' ],
            ),
            netloc = dict(
                outcast = [ 'oper.inline.fr' ],
            )
        ),
        priority = dict(
            level = top.DEFAULT
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
        system = options.get('system', None)
        try:
            st = system.stat(self.fullpath(remote))
        except OSError:
            st = None
        return st

    def filelocate(self, remote, options):
        """Returns the real path."""
        return self.fullpath(remote)

    def fileget(self, remote, local, options):
        """Delegates to ``system`` the copy of ``remote`` to ``local``."""
        system = options.get('system', None)
        rpath = self.fullpath(remote)
        if 'intent' in options and options['intent'] == dataflow.intent.IN:
            logger.warning('Ignoring intent in for remote input %s', rpath)
        return system.cp(rpath, local)

    def fileput(self, local, remote, options):
        """Delegates to ``system`` the copy of ``local`` to ``remote``."""
        system = options.get('system', None)
        return system.cp(local, self.fullpath(remote))

    def ftpcheck(self, remote, options):
        """Delegates to ``system`` a distant check."""
        system = options.get('system', None)
        ftp = system.ftp(self.hostname(), remote['username'])
        if ftp:
            rc = ftp.size(self.fullpath(remote))
            ftp.close()
            return rc

    def ftplocate(self, remote, options):
        """Delegates to ``system`` qualified name creation."""
        system = options.get('system', None)
        ftp = system.ftp(self.hostname(), remote['username'])
        if ftp:
            rloc = ftp.netpath(self.fullpath(remote))
            ftp.close()
            return rloc
        else:
            return None

    def ftpget(self, remote, local):
        """Delegates to ``system`` the file transfert of ``remote`` to ``local``."""
        system = options.get('system', None)
        ftp = system.ftp(self.hostname(), remote['username'])
        if ftp:
            rc = ftp.get(self.fullpath(remote), local)
            ftp.close()
            return rc

    def ftpput(self, local, remote):
        """Delegates to ``system`` the file transfert of ``local`` to ``remote``."""
        system = options.get('system', None)
        ftp = system.ftp(self.hostname(), remote['username'])
        if ftp:
            rc = ftp.put(local, self.fullpath(remote))
            ftp.close()
            return rc


class VortexArchiveStore(Store):

    _footprint = dict(
        info = 'VORTEX archive access',
        attr = dict(
            scheme = dict(
                values = [ 'vortex', 'ftp', 'ftserv' ],
            ),
            netloc = dict(
                values = [ 'open.archive.fr', 'vortex.archive.fr' ],
                remap = {
                    'vortex.archive.fr' : 'open.archive.fr'
                },
                default = 'open.archive.fr'
            ),
            rootdir = dict(
                optional = True,
                default = '/home/m/marp/marp999'
            ),
            headdir = dict(
                optional = True,
                default = 'vortex'
            ),
            storage = dict(
                optional = True,
                default = 'cougar.meteo.fr'
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Vortex archive store init %s', self.__class__)
        super(VortexArchiveStore, self).__init__(*args, **kw)

    @property
    def realkind(self):
        return 'archive'

    def hostname(self):
        """Returns the current :attr:`storage`."""
        return self.storage

    def remapget(self, remote, options):
        """Reformulates the remote path to compatible vortex namespace."""
        system = options.get('system', None)
        xpath = remote['path'].split('/')
        xpath[3:4] = list(xpath[3])
        xpath[:0] = [ system.path.sep, self.headdir ]
        remote['path'] = system.path.join(*xpath)

    def ftplocate(self, remote, options):
        """Delegates to ``system.ftp`` a distant check."""
        system = options.get('system', None)
        ftp = system.ftp(self.hostname(), remote['username'])
        if ftp:
            rloc = ftp.netpath(self.rootdir + remote['path'])
            ftp.close()
            return rloc
        else:
            return None

    def vortexlocate(self, remote, options):
        """Remap and ftplocate sequence."""
        self.remapget(remote, options)
        return self.ftplocate(remote, options)

    def ftpget(self, remote, local, options):
        """Delegates to ``system.ftp`` the put action."""
        system = options.get('system', None)
        ftp = system.ftp(self.hostname(), remote['username'])
        if ftp:
            rc = ftp.get(self.rootdir + remote['path'], local)
            ftp.close()
            return rc
        else:
            return False

    def vortexget(self, remote, local, options):
        """Remap and ftpget sequence."""
        self.remapget(remote, options)
        return self.ftpget(remote, local, options)

    def ftpput(self, local, remote, options):
        """Delegates to ``system.ftp`` the put action."""
        system = options.get('system', None)
        ftp = system.ftp(self.hostname(), remote['username'])
        if ftp:
            rootpath = remote.get('root', self.rootdir)
            rc = ftp.put(local, system.path.join(rootpath, remote['path'].lstrip(system.path.sep)))
            ftp.close()
            return rc
        else:
            return False

    def vortexput(self, local, remote, options):
        """Remap root dir and ftpput sequence."""
        if not 'root' in remote: remote['root'] = self.headdir
        return self.ftpput(local, remote, options)


class VortexCacheStore(Store):

    _footprint = dict(
        info = 'VORTEX cache access',
        attr = dict(
            scheme = dict(
                values = [ 'vortex' ],
            ),
            netloc = dict(
                values = [ 'open.cache.fr', 'vortex.cache.fr' ],
                remap = {
                    'vortex.cache.fr' : 'open.cache.fr'
                },
                default = 'open.cache.fr'
            ),
            strategy = dict(
                optional = True,
                default = 'mtool',
            ),
            rootdir = dict(
                optional = True,
                default = '/tmp/toolbox'
            ),
            headdir = dict(
                optional = True,
                default = 'vortex',
                outcast = [ 'xp' ],
            ),
            storage = dict(
                optional = True,
                default = 'localhost'
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Vortex cache store init %s', self.__class__)
        super(VortexCacheStore, self).__init__(*args, **kw)
        self.resetcache()

    @property
    def realkind(self):
        return 'storecache'

    @property
    def hostname(self):
        """Returns the current :attr:`storage`."""
        return self.storage

    def resetcache(self):
        """Invalidate internal cache reference."""
        self._cache = None

    @property
    def cache(self):
        if not self._cache:
            self._cache = caches.default(
                kind    = self.strategy,
                storage = self.storage,
                rootdir = self.rootdir,
                headdir = self.headdir
            )
        return self._cache

    def vortexlocate(self, remote, options):
        """Agregates cache to remore subpath."""
        system = options.get('system', None)
        return self.cache.entry(system) + remote['path']

    def vortexget(self, remote, local, options):
        """Simple copy from vortex cache to ``local``."""
        system = options.get('system', None)
        rpath = self.cache.entry(system) + remote['path']
        if 'intent' in options and options['intent'] == dataflow.intent.IN:
            return system.smartcp(rpath, local)
        else:
            return system.cp(rpath, local)

    def vortexput(self, local, remote, options):
        """Simple copy from ``local`` to vortex cache in readonly mode."""
        system = options.get('system', None)
        return system.smartcp(local, self.cache.entry(system) + remote['path'])


class VortexStore(MultiStore):

    _footprint = dict(
        info = 'Vortex multi access',
        attr = dict(
            scheme = dict(
                values = [ 'vortex' ],
            ),
            netloc = dict(
                values = [ 'open.meteo.fr', 'multi.open.fr' ],
            ),
        )
    )

    def alternates_netloc(self):
        """Tuple of alternates domains names, e.g. ``cache`` and ``archive``."""
        return ( 'open.cache.fr', 'open.archive.fr' )


class StoresCatalog(ClassesCollector):
    """Class in charge of collecting :class:`Store` items."""

    def __init__(self, **kw):
        logger.debug('Stores catalog init %s', self)
        cat = dict(
            remod = re.compile(r'.*\.stores'),
            classes = [ Store, MultiStore ],
            itementry = 'store'
        )
        cat.update(kw)
        super(StoresCatalog, self).__init__(**cat)

    @classmethod
    def tablekey(cls):
        return 'stores'


cataloginterface(sys.modules.get(__name__), StoresCatalog)

