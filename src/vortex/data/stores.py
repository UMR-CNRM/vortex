#!/bin/env python
# -*- coding: utf-8 -*-

r"""
This package handles store objects in charge of physically accessing resources.
The associated modules defines the catalog factory based on the shared footprint
mechanism.
"""

#: No automatic export
__all__ = [ 'Store' ]

import logging, re, sys

from vortex.syntax import BFootprint
from vortex.syntax.priorities import top
from vortex.utilities.catalogs import ClassesCollector, cataloginterface
from vortex.tools.config import DelayedConfigParser

from vortex import sessions


class StoreGlue(object):
    """Defines a way to glue stored objects together."""

    def __init__(self, gluemap=dict()):
        logging.debug('Abstract glue init %s', self.__class__)
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
            logging.warning('No such section <%s> or option <%s> in %s', section, option, self)
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
            logging.warning('No such section <%s> in %s', section, self)
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

    def containsformat(self, format):
        """Shortcut to contains for a specified format."""
        return self.contains('format', format)

    def getitem(self, itemtype, itemname):
        """Generic function to obtain the associated description of the item specified by type and name."""
        if self.contains(itemtype, itemname):
            return self.crossitem(itemtype).get(itemname)
        else:
            return None

    def getfile(self, filename):
        """Shortcut to get an item for a specified file."""
        return self.getitem('file', filename)

    def getformat(self, format):
        """Shortcut to get an item for a specified format."""
        return self.getitem('format', format)

    def filemap(self, system, dirname, basename):
        """Reformulates the actual physical path for the file requested."""
        gluedesc = self.getfile(basename)
        if len(gluedesc) > 1:
            logging.error('Multiple glue entries %s', gludesc)
            cleanpath, targetpath = ( None, None )
        else:
            gluedesc = gluedesc[0]
            targetpath = self.gluename(gluedesc['section']) + '.' + self.gluetype(gluedesc['section'])
            cleanpath = system.path.join(dirname, targetpath)
        return ( cleanpath, targetpath )

        
class IniStoreGlue(StoreGlue):
    """Initialised StoreGlue with a delayed ini file."""

    def __init__(self, inifile=None):
        logging.debug('IniStoreGlue init %s', self.__class__)
        super(IniStoreGlue, self).__init__(DelayedConfigParser(inifile))


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
        logging.debug('Abstract store init %s', self.__class__)
        super(Store, self).__init__(*args, **kw)

    @classmethod
    def realkind(cls):
        """Defines the kind of this object, here ``store``."""
        return 'store'

    def notyet(self, system, desc):
        """
        Internal method to be used as a critical backup method
        when a specific method is not yet defined.
        """
        logging.critical('Scheme %s not yet implemented', self.scheme)

    def check(self, remote):
        """Proxy method to dedicated check method accordind to scheme."""
        logging.debug('Store check from %s', remote)
        return getattr(self, self.scheme + 'check', self.notyet)(sessions.system(), remote)

    def locate(self, remote):
        """Proxy method to dedicated get method accordind to scheme."""
        logging.debug('Store locate %s', remote)
        return getattr(self, self.scheme + 'locate', self.notyet)(sessions.system(), remote)

    def get(self, remote, local):
        """Proxy method to dedicated get method accordind to scheme."""
        logging.debug('Store get from %s to %s', remote, local)
        return getattr(self, self.scheme + 'get', self.notyet)(sessions.system(), remote, local)

    def put(self, local, remote):
        """Proxy method to dedicated put method accordind to scheme."""
        logging.debug('Store put from %s to %s', local, remote)
        return getattr(self, self.scheme + 'put', self.notyet)(sessions.system(), local, remote)


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
        logging.debug('Abstract multi store init %s', self.__class__)
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
        logging.info('Multi active stores %s = %s', self, activestores)
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

    def check(self, remote):
        """Go through internal opened stores and check for the resource."""
        logging.debug('Multi Store check from %s', remote)
        rc = False
        for sto in self.openedstores:
            rc = sto.check(remote)
            if rc:
                break
        return rc

    def locate(self, remote):
        """Go through internal opened stores and locate the expected resource for each of them."""
        logging.debug('Multi Store locate %s', remote)
        if not self.openedstores:
            return False
        rloc = list
        for sto in self.openedstores:
            logging.info('Multi locate at %s', sto)
            rloc.append(sto.locate(remote))
        return ';'.join(rloc)

    def get(self, remote, local):
        """Go through internal opened stores for the first available resource."""
        logging.info('Multi Store get from %s to %s', remote, local)
        rc = False
        for sto in self.openedstores:
            logging.info('Multi get at %s', sto)
            rc = sto.get(remote, local)
            if rc:
                break
        return rc

    def put(self, local, remote):
        """Go through internal opened stores and put resource for each of them."""
        logging.debug('Multi Store put from %s to %s', local, remote)
        if not self.openedstores:
            return False
        rc = True
        for sto in self.openedstores:
            logging.info('Multi put at %s', sto)
            rc = rc & sto.put(local, remote)
        return rc


class Finder(Store):
    """The most usual store: your current filesystem!"""

    _footprint = dict(
        info = 'Miscellaneous file access',
        attr = dict(
            scheme = dict(
                values = [ 'file', 'ftp', 'rcp', 'scp' ],
            ),
        ),
        priority = dict(
            level = top.DEFAULT
        )
    )

    def __init__(self, *args, **kw):
        logging.debug('Abstract store init %s', self.__class__)
        super(Finder, self).__init__(*args, **kw)

    @classmethod
    def realkind(cls):
        return 'finder'

    def hostname(self):
        """Returns the current :attr:`netloc`."""
        return self.netloc

    def _realpath(self, remote):
        if remote['query'].get('relative', False):
            return remote['path'].lstrip('/')
        else:
            return remote['path']

    def filecheck(self, system, remote):
        """Returns a stat-like object if the ``remote`` exists on the ``system`` provided."""
        try:
            st = system.stat(self._realpath(remote))
        except OSError:
            st = None
        return st

    def filelocate(self, system, remote):
        """Returns the real path."""
        return self._realpath(remote)

    def fileget(self, system, remote, local):
        """Delegates to ``system`` the copy of ``remote`` to ``local``."""
        return system.cp(self._realpath(remote), local)

    def fileput(self, system, local, remote):
        """Delegates to ``system`` the copy of ``local`` to ``remote``."""
        return system.cp(local, self._realpath(remote))

    def ftpcheck(self, system, remote):
        """Delegates to ``system`` a distant check."""
        ftp = system.ftp(self.hostname(), remote['username'])
        if ftp:
            rc = ftp.size(self._realpath(remote))
            ftp.close()
            return rc

    def ftplocate(self, system, remote):
        """Delegates to ``system`` qualified name creation."""
        ftp = system.ftp(self.hostname(), remote['username'])
        if ftp:
            rloc = ftp.fullpath(self._realpath(remote))
            ftp.close()
            return rloc
        else:
            return None

    def ftpget(self, system, remote, local):
        """Delegates to ``system`` the file transfert of ``remote`` to ``local``."""
        ftp = system.ftp(self.hostname(), remote['username'])
        if ftp:
            rc = ftp.get(self._realpath(remote), local)
            ftp.close()
            return rc

    def ftpput(self, system, local, remote):
        """Delegates to ``system`` the file transfert of ``local`` to ``remote``."""
        ftp = system.ftp(self.hostname(), remote['username'])
        if ftp:
            rc = ftp.put(local, self._realpath(remote))
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
        logging.debug('Vortex archive store init %s', self.__class__)
        super(VortexArchiveStore, self).__init__(*args, **kw)

    @classmethod
    def realkind(cls):
        return 'archive'

    def hostname(self):
        """Returns the current :attr:`storage`."""
        return self.storage

    def remapget(self, system, remote):
        """Reformulates the remote path to compatible vortex namespace."""
        xpath = remote['path'].split('/')
        xpath[3:4] = list(xpath[3])
        xpath[:0] = [ system.path.sep, self.headdir ]
        remote['path'] = system.path.join(*xpath)

    def ftplocate(self, system, remote):
        """Delegates to ``system.ftp`` a distant check."""
        ftp = system.ftp(self.hostname(), remote['username'])
        if ftp:
            rloc = ftp.fullpath(self.rootdir + remote['path'])
            ftp.close()
            return rloc
        else:
            return None

    def vortexlocate(self, system, remote):
        """Remap and ftplocate sequence."""
        self.remapget(system, remote)
        return self.ftplocate(system, remote)

    def ftpget(self, system, remote, local):
        """Delegates to ``system.ftp`` the put action."""
        ftp = system.ftp(self.hostname(), remote['username'])
        if ftp:
            rc = ftp.get(self.rootdir + remote['path'], local)
            ftp.close()
            return rc
        else:
            return False

    def vortexget(self, system, remote, local):
        """Remap and ftpget sequence."""
        self.remapget(system, remote)
        return self.ftpget(system, remote, local)

    def ftpput(self, system, local, remote):
        """Delegates to ``system.ftp`` the put action."""
        ftp = system.ftp(self.hostname(), remote['username'])
        if ftp:
            rootpath = remote.get('root', self.rootdir)
            rc = ftp.put(local, system.path.join(rootpath, remote['path'].lstrip(system.path.sep)))
            ftp.close()
            return rc
        else:
            return False

    def vortexput(self, system, local, remote):
        """Remap root dir and ftpput sequence."""
        if not 'root' in remote: remote['root'] = self.headdir
        return self.ftpput(system, local, remote)


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
            rootdir = dict(
                optional = True,
                default = 'mtool'
            ),
            headdir = dict(
                optional = True,
                default = 'vortex'
            ),
            storage = dict(
                optional = True,
                default = 'localhost'
            ),
        )
    )

    def __init__(self, *args, **kw):
        logging.debug('Vortex cache store init %s', self.__class__)
        super(VortexCacheStore, self).__init__(*args, **kw)

    @classmethod
    def realkind(cls):
        return 'cache'

    def hostname(self):
        """Returns the current :attr:`storage`."""
        return self.storage

    def cachepath(self, system):
        """Tries to figure out what could be the actual cache space."""
        cache = self.rootdir
        e = system.env
        if ( cache == 'mtool' or ( e.SWAPP_OUTPUT_CACHE and e.SWAPP_OUTPUT_CACHE == 'mtool' ) ):
            if e.MTOOL_STEP_CACHE and system.path.isdir(e.MTOOL_STEP_CACHE):
                cache = e.MTOOL_STEP_CACHE
                logging.debug('Store %s uses mtool cache %s', self, cache)
            else:
                cache = e.WORKDIR or e.TMPDIR
                logging.debug('Store %s uses default cache %s', self, cache)
        return system.path.join(cache, self.headdir)

    def vortexlocate(self, system, remote):
        """Agregates cache to remore subpath."""
        return self.cachepath(system) + remote['path']

    def vortexget(self, system, remote, local):
        """Simple copy from vortex cache to ``local``."""
        return system.cp(self.cachepath(system) + remote['path'], local)

    def vortexput(self, system, local, remote):
        """Simple copy from ``local`` to vortex cache in readonly mode."""
        targetcp = self.cachepath(system) + remote['path']
        system.remove(targetcp)
        pst = system.cp(local, targetcp)
        if pst:
            system.readonly(targetcp)
        return pst


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
        logging.debug('Stores catalog init %s', self)
        cat = dict(
            remod = re.compile(r'.*\.stores'),
            classes = [ Store, MultiStore ],
            itementry = Store.realkind()
        )
        cat.update(kw)
        super(StoresCatalog, self).__init__(**cat)

    @classmethod
    def tablekey(cls):
        return 'stores'


cataloginterface(sys.modules.get(__name__), StoresCatalog)

