#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=unused-argument

"""
This module handles store objects in charge of physically accessing resources.
Store objects use the :mod:`footprints` mechanism.
"""

#: Export base class
__all__ = ['Store']

from collections import defaultdict
import copy
import ftplib
import re

from bronx.stdtypes import date
from bronx.system import hash as hashutils
import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex import sessions
from vortex.layout import dataflow
from vortex.util import config
from vortex.syntax.stdattrs import hashalgo, hashalgo_avail_list, compressionpipeline
from vortex.tools import caches
from vortex.tools import compression
from vortex.tools import net
from vortex.tools.systems import ExecutionError
from vortex.tools.actions import actiond as ad
from vortex.syntax.stdattrs import Namespace, FreeXPid
from vortex.syntax.stdattrs import DelayedEnvValue


OBSERVER_TAG = 'Stores-Activity'

_CACHE_PUT_INTENT = 'in'
_CACHE_GET_INTENT_DEFAULT = 'in'


def observer_board(obsname=None):
    """Proxy to :func:`footprints.observers.get`."""
    if obsname is None:
        obsname = OBSERVER_TAG
    return footprints.observers.get(tag=obsname)


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
        return str(self.gluemap)

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
            return [x for x in self.gluemap.options(section) if not x.startswith('obj')]
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
        Possibly builds and then returns a reverse dictionary
        of founded options with the specified ``item`` defined.
        """
        if item not in self._cross:
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
    _footprint = [
        hashalgo,
        dict(
            info = 'Default store',
            attr = dict(
                scheme = dict(
                    alias = ('protocol',)
                ),
                netloc = dict(
                    type  = Namespace,
                    alias = ('domain', 'namespace')
                ),
                storetrack = dict(
                    type     = bool,
                    default  = True,
                    optional = True,
                ),
                readonly = dict(
                    type     = bool,
                    optional = True,
                    default  = False,
                ),
            ),
        )
    ]

    def __init__(self, *args, **kw):
        logger.debug('Abstract store init %s', self.__class__)
        sh = kw.pop('system', sessions.system())
        super(Store, self).__init__(*args, **kw)
        self._sh = sh
        self._observer = observer_board()
        self._observer.notify_new(self, dict())
        self._cpipeline = False
        self.delayed = False

    def __del__(self):
        self._observer.notify_del(self, dict())
        super(Store, self).__del__()

    @property
    def realkind(self):
        return 'store'

    @property
    def system(self):
        """Shortcut to current system interface."""
        return self._sh

    def use_cache(self):
        """Boolean function to check if the current store use a local cache."""
        return False

    def _observer_notify(self, action, rc, remote, local=None, options=None):
        if self.storetrack:
            infos = dict(action=action, status=rc, remote=remote)
            # Is a localpath provided ?
            if local is not None:
                infos['local'] = local
            # We may want to cheat on the localpath...
            if options is not None and 'obs_overridelocal' in options:
                infos['local'] = options['obs_overridelocal']
            self._observer.notify_upd(self, infos)

    def notyet(self, *args):
        """
        Internal method to be used as a critical backup method
        when a specific method is not yet defined.
        """
        logger.critical('Scheme %s not yet implemented', self.scheme)

    @property
    def writeable(self):
        return not self.readonly

    def enforce_readonly(self):
        if self.readonly:
            raise IOError('This store is in readonly mode')

    @staticmethod
    def _verbose_log(options, level, *kargs, **kwargs):
        slevel = kwargs.pop('slevel', 'debug')
        if options is not None and options.get('silent', False):
            level = slevel
        getattr(logger, level)(*kargs, **kwargs)

    @property
    def _actual_cpipeline(self):
        """Check if the current store has a CompressionPipeline."""
        if self._cpipeline is False:
            cpipeline_desc = getattr(self, 'store_compressed', None)
            if cpipeline_desc is not None:
                self._cpipeline = compression.CompressionPipeline(self.system,
                                                                  cpipeline_desc)
            else:
                self._cpipeline = None
        return self._cpipeline

    def check(self, remote, options=None):
        """Proxy method to dedicated check method according to scheme."""
        logger.debug('Store check from %s', remote)
        if options is not None and options.get('incache', False) and not self.use_cache():
            self._verbose_log(options, 'info', 'Skip this store because a cache is requested')
            rc = False
        else:
            rc = getattr(self, self.scheme + 'check', self.notyet)(remote, options)
            self._observer_notify('check', rc, remote)
        return rc

    def locate(self, remote, options=None):
        """Proxy method to dedicated locate method according to scheme."""
        logger.debug('Store locate %s', remote)
        if options is not None and options.get('incache', False) and not self.use_cache():
            self._verbose_log(options, 'info', 'Skip this store because a cache is requested')
            return None
        else:
            return getattr(self, self.scheme + 'locate', self.notyet)(remote, options)

    def prestage_advertise(self, remote, options=None):
        """Use the Stores-Activity observer board to advertise the prestaging request.

        Hopefully, something will register to the ober board in order to process
        the request.
        """
        logger.debug('Store prestage through hub %s', remote)
        infos_cb = getattr(self, self.scheme + 'prestageinfo', None)
        if infos_cb:
            infodict = infos_cb(remote, options)
            infodict.setdefault('issuerkind', self.realkind)
            infodict.setdefault('scheme', self.scheme)
            if options and 'priority' in options:
                infodict['priority'] = options['priority']
            infodict['action'] = 'prestage_req'
            self._observer.notify_upd(self, infodict)
        else:
            logger.info('Prestaging is not supported for scheme: %s', self.scheme)
        return True

    def prestage(self, remote, options=None):
        """Proxy method to dedicated prestage method according to scheme."""
        logger.debug('Store prestage %s', remote)
        if options is not None and options.get('incache', False) and not self.use_cache():
            self._verbose_log(options, 'info', 'Skip this store because a cache is requested')
            return True
        else:
            return getattr(self, self.scheme + 'prestage', self.prestage_advertise)(remote, options)

    def _hash_store_defaults(self, options):
        """Update default options when fetching hash files."""
        options = options.copy() if options is not None else dict()
        options['fmt'] = 'ascii'
        options['intent'] = _CACHE_GET_INTENT_DEFAULT
        options['auto_tarextract'] = False
        options['auto_dirextract'] = False
        return options

    def _hash_get_check(self, callback, remote, local, options=None):
        """Update default options when fetching hash files."""
        if (self.storehash is None) or (remote['path'].endswith('.' + self.storehash)):
            return True
        options = self._hash_store_defaults(options)
        remote = remote.copy()
        remote['path'] = remote['path'] + '.' + self.storehash  # Name of the hash file
        remote['query'].pop('extract', None)  # Ignore any extract request
        try:
            # First, try to fetch the sum in a real file
            # (in order to potentially use ftserv...)
            tempcontainer = footprints.proxy.container(shouldfly=True)
            try:
                rc = callback(remote, tempcontainer.iotarget(), options)
            except (OSError, IOError):
                # This may happen if the user has insufficient rights on
                # the current directory
                tempcontainer = footprints.proxy.container(incore=True)
                rc = callback(remote, tempcontainer.iotarget(), options)
            # check the hash key
            hadapt = hashutils.HashAdapter(self.storehash)
            rc = rc and hadapt.filecheck(local, tempcontainer)
            if rc:
                logger.info("%s hash sanity check succeeded.", self.storehash)
            else:
                logger.warning("%s hash sanity check failed.", self.storehash)
        finally:
            tempcontainer.clear()
        return rc

    def get(self, remote, local, options=None):
        """Proxy method to dedicated get method according to scheme."""
        logger.debug('Store get from %s to %s', remote, local)
        if options is not None and options.get('incache', False) and not self.use_cache():
            self._verbose_log(options, 'info', 'Skip this store because a cache is requested')
            return False
        else:
            if (options is None or (not options.get('insitu', False)) or
                    self.use_cache()):
                rc = getattr(self, self.scheme + 'get', self.notyet)(remote, local, options)
                self._observer_notify('get', rc, remote, local=local, options=options)
                return rc
            else:
                logger.error('Only cache stores can be used when insitu is True.')
                return False

    def _hash_put(self, callback, local, remote, options=None):
        """Put a hash file next to the 'real' file."""
        if (self.storehash is None) or (remote['path'].endswith('.' + self.storehash)):
            return True
        options = self._hash_store_defaults(options)
        remote = remote.copy()
        remote['path'] = remote['path'] + '.' + self.storehash
        # Generate the hash sum
        hadapt = hashutils.HashAdapter(self.storehash)
        tmplocal = hadapt.file2hash_fh(local)
        # Write it whereever the original store wants to.
        return callback(tmplocal, remote, options)

    def put(self, local, remote, options=None):
        """Proxy method to dedicated put method according to scheme."""
        logger.debug('Store put from %s to %s', local, remote)
        self.enforce_readonly()
        if options is not None and options.get('incache', False) and not self.use_cache():
            self._verbose_log(options, 'info', 'Skip this store because a cache is requested')
            return True
        else:
            filtered = False
            if options is not None and 'urifilter' in options:
                filtered = options['urifilter'](self, remote)
            if filtered:
                rc = True
                logger.info("This remote URI has been filtered out: we are skipping it.")
            else:
                dryrun = False
                if options is not None and 'dryrun' in options:
                    dryrun = options['dryrun']
                rc = dryrun or getattr(self, self.scheme + 'put', self.notyet)(local, remote, options)
                self._observer_notify('put', rc, remote, local=local, options=options)
            return rc

    def delete(self, remote, options=None):
        """Proxy method to dedicated delete method according to scheme."""
        logger.debug('Store delete from %s', remote)
        self.enforce_readonly()
        if options is not None and options.get('incache', False) and not self.use_cache():
            self._verbose_log(options, 'info', 'Skip this store because a cache is requested')
            rc = True
        else:
            rc = getattr(self, self.scheme + 'delete', self.notyet)(remote, options)
            self._observer_notify('del', rc, remote)
        return rc


class MultiStore(footprints.FootprintBase):
    """Agregate various :class:`Store` items."""

    _abstract  = True
    _collector = ('store',)
    _footprint = [
        compressionpipeline,
        hashalgo,
        dict(
            info = 'Multi store',
            attr = dict(
                scheme = dict(
                    alias    = ('protocol',)
                ),
                netloc = dict(
                    type     = Namespace,
                    alias    = ('domain', 'namespace')
                ),
                refillstore = dict(
                    type     = bool,
                    optional = True,
                    default  = False,
                ),
                storage = dict(
                    optional = True,
                    default  = None,
                ),
            ),
        )
    ]

    def __init__(self, *args, **kw):
        logger.debug('Abstract multi store init %s', self.__class__)
        sh = kw.pop('system', sessions.system())
        super(MultiStore, self).__init__(*args, **kw)
        self._sh = sh
        self.openedstores = self.loadstores()
        self.delayed = False

    @property
    def realkind(self):
        return 'multistore'

    @property
    def system(self):
        """Shortcut to current system interface."""
        return self._sh

    @staticmethod
    def _verbose_log(options, level, *kargs, **kwargs):
        slevel = kwargs.pop('slevel', 'debug')
        if options is not None and options.get('silent', False):
            level = slevel
        getattr(logger, level)(*kargs, **kwargs)

    def loadstores(self):
        """
        Load default stores during the initialisation of the current object.
        Stores could be reloaded at any time. The current method provides
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
            dict(system=self.system, storehash=self.storehash, storage=self.storage,
                 store_compressed=self.store_compressed,
                 scheme=x, netloc=y)
            for x in self.alternates_scheme()
            for y in self.alternates_netloc()
        ]

    def use_cache(self):
        """Boolean function to check if any included store use a local cache."""
        return any([x.use_cache() for x in self.openedstores])

    @property
    def readonly(self):
        return all([x.readonly for x in self.openedstores])

    @property
    def writeable(self):
        return not self.readonly

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
            tmp_rloc = sto.locate(remote.copy(), options)
            if tmp_rloc:
                rloc.append(tmp_rloc)
        return ';'.join(rloc)

    def prestage(self, remote, options=None):
        """Go through internal opened stores and prestage the resource for each of them."""
        logger.debug('Multistore prestage %s', remote)
        if not self.openedstores:
            return False
        rc = True
        for sto in self.openedstores:
            logger.debug('Multistore prestage at %s', sto)
            rc = rc and sto.prestage(remote.copy(), options)
        return rc

    def get(self, remote, local, options=None):
        """Go through internal opened stores for the first available resource."""
        logger.debug('Multistore get from %s to %s', remote, local)
        rc = False
        refill_in_progress = True
        get_options = copy.copy(options) if options is not None else dict()
        get_options['silent'] = True
        while refill_in_progress:
            for num, sto in enumerate(self.openedstores):
                logger.debug('Multistore get at %s', sto)
                rc = sto.get(remote.copy(), local, get_options)
                # Are we trying a refill ? -> find the previous writeable store
                restores = []
                if rc and self.refillstore and num > 0:
                    restores = [ostore for ostore in self.openedstores[:num]
                                if ostore.writeable]
                # Do the refills and check if one of them succeed
                refill_in_progress = False
                for restore in restores:
                    # Another refill may have filled the gap...
                    if not restore.check(remote.copy(), options):
                        logger.info('Refill back in writeable store [%s]', restore)
                        try:
                            refill_in_progress = ((restore.put(local, remote.copy(), options) and
                                                   (options.get('intent', _CACHE_GET_INTENT_DEFAULT) !=
                                                    _CACHE_PUT_INTENT)) or
                                                  refill_in_progress)
                        except ExecutionError as e:
                            logger.error("An ExecutionError happened during the refill: %s", str(e))
                            logger.error("This error is ignored... but that's ugly !")
                if refill_in_progress:
                    logger.info("Starting another round because at least one refill succeeded")
                # Whatever the refill's outcome, that's fine
                if rc:
                    break
        if not rc:
            self._verbose_log(options, 'warning',
                              "None of the opened store succeeded... that's too bad !",
                              slevel='info')
        return rc

    def put(self, local, remote, options=None):
        """Go through internal opened stores and put resource for each of them."""
        logger.debug('Multistore put from %s to %s', local, remote)
        if not self.openedstores:
            logger.warning('Funny attempt to put on an empty multistore...')
            return False
        rc = True
        for sto in [ostore for ostore in self.openedstores if ostore.writeable]:
            logger.info('Multistore put at %s', sto)
            rcloc = sto.put(local, remote.copy(), options)
            logger.info('Multistore out = %s', rcloc)
            rc = rc and rcloc
        return rc

    def delete(self, remote, options=None):
        """Go through internal opened stores and delete the resource."""
        logger.debug('Multistore delete from %s', remote)
        rc = False
        for sto in [ostore for ostore in self.openedstores if ostore.writeable]:
            logger.info('Multistore delete at %s', sto)
            rc = sto.delete(remote.copy(), options)
            if not rc:
                break
        return rc


class MagicPlace(Store):
    """Somewhere, over the rainbow!"""

    _footprint = dict(
        info = 'Evanescent physical store',
        attr = dict(
            scheme = dict(
                values   = ['magic'],
            ),
        ),
        priority = dict(
            level = footprints.priorities.top.DEFAULT  # @UndefinedVariable
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


class FunctionStoreCallbackError(Exception):
    pass


class FunctionStore(Store):
    """Calls a function that returns a File like object (get only).

    This store is only able to perform the get action: it imports and calls
    the function specified in the URI path. This function should return a
    file like object that will be written in the local container.

    The function is given an option dictionary that contains all of the
    options provided to the store's get function, plus any additional
    information specified in the 'query' part of the URI.

    :Example:

    Lets consider the following URI:

      ``function:///sandbox.utils.storefunctions.echofunction?msg=toto&msg=titi``

    It will be seen as follows:

    * scheme: ``'function'``
    * netloc: ``''``
    * path: ``'/sandbox.utils.storefunctions.echofunction'``
    * query: ``dict(msg=['toto', 'titi'])``

    As a result, the :func:`sandbox.utils.storefunctions.echofunction` will be
    called with an option dictionary that contains ['toto', 'titi'] for the
    'msg' key (plus any other options passed to the store's get method).
    """

    _footprint = dict(
        info = 'Dummy store that calls a function',
        attr = dict(
            scheme = dict(
                values   = ['function'],
            ),
            netloc = dict(
                values   = [''],
            )
        ),
        priority = dict(
            level = footprints.priorities.top.DEFAULT  # @UndefinedVariable
        )
    )

    @property
    def realkind(self):
        return 'functionstore'

    def functioncheck(self, remote, options):
        """Void - Always False."""
        return False

    def functionlocate(self, remote, options):
        """The name of the function that will be called."""
        cleanname = remote['path'][1:]
        if cleanname.endswith('/'):
            cleanname = cleanname[:-1]
        return cleanname

    def functionget(self, remote, local, options):
        """Calls the appropriate function and writes the result."""
        # Find the appropriate function
        cbfunc = self.system.import_function(self.functionlocate(remote,
                                                                 options))
        # ... and call it
        opts = dict()
        opts.update(options)
        opts.update(remote['query'])
        try:
            fres = cbfunc(opts)
        except FunctionStoreCallbackError as e:
            logger.error("An exception was raised in the Callback function")
            logger.error("Here is the exception: %s", str(e))
            fres = None
        if fres is not None:
            if 'intent' in options and options['intent'] == dataflow.intent.IN:
                logger.info('Ignore intent <in> for function input.')
            # NB: fres should be a file like object (StringIO will do the trick)
            return self.system.cp(fres, local)
        else:
            return False

    def functionput(self, local, remote, options):
        """This should not happen - Always False."""
        logger.error("The function store is not able to perform PUTs.")
        return False

    def functiondelete(self, remote, options):
        """This should not happen - Always False."""
        logger.error("The function store is not able to perform Deletes.")
        return False


class Finder(Store):
    """The most usual store: your current filesystem!"""

    _footprint = dict(
        info = 'Miscellaneous file access',
        attr = dict(
            scheme = dict(
                values  = ['file', 'ftp', 'symlink', 'rcp', 'scp'],
            ),
            netloc = dict(
                outcast = ['oper.inline.fr'],
            ),
            storehash = dict(
                values = hashalgo_avail_list,
            ),
        ),
        priority = dict(
            level = footprints.priorities.top.DEFAULT  # @UndefinedVariable
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

    def _localtarfix(self, local):
        if (isinstance(local, basestring) and self.system.path.isfile(local) and
                self.system.is_tarfile(local)):
            destdir = self.system.path.dirname(self.system.path.realpath(local))
            self.system.smartuntar(local, destdir, output=False)

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
        logger.info('fileget on %s (to: %s)', rpath, local)
        if 'intent' in options and options['intent'] == dataflow.intent.IN:
            logger.info('Ignore intent <in> for remote input %s', rpath)
        rc = self.system.cp(rpath, local, fmt=options.get('fmt'), intent=dataflow.intent.INOUT)
        rc = rc and self._hash_get_check(self.fileget, remote, local, options)
        if rc:
            self._localtarfix(local)
        return rc

    def fileput(self, local, remote, options):
        """Delegates to ``system`` the copy of ``local`` to ``remote``."""
        rpath = self.fullpath(remote)
        logger.info('fileput to %s (from: %s)', rpath, local)
        rc = self.system.cp(local, rpath, fmt=options.get('fmt'))
        return rc and self._hash_put(self.fileput, local, remote, options)

    def filedelete(self, remote, options):
        """Delegates to ``system`` the removing of ``remote``."""
        rc = None
        if self.filecheck(remote, options):
            rpath = self.fullpath(remote)
            logger.info('filedelete on %s', rpath)
            rc = self.system.remove(rpath, fmt=options.get('fmt'))
        else:
            logger.error('Try to remove a non-existing resource <%s>', self.fullpath(remote))
        return rc

    symlinkcheck = filecheck
    symlinklocate = filelocate

    def symlinkget(self, remote, local, options):
        rpath = self.fullpath(remote)
        if 'intent' in options and options['intent'] == dataflow.intent.INOUT:
            logger.error('It is unsafe to have a symlink with intent=inout: %s', rpath)
            return False
        rc = self.system.remove(local)
        self.system.symlink(rpath, local)
        return rc and self.system.path.exists(local)

    def symlinkput(self, local, remote, options):
        logger.error("The Finder store with scheme:symlink is not able to perform Puts.")
        return False

    def symlinkdelete(self, remote, options):
        logger.error("The Finder store with scheme:symlink is not able to perform Deletes.")
        return False

    def ftpcheck(self, remote, options):
        """Delegates to ``system.ftp`` a distant check."""
        rc = None
        ftp = self.system.ftp(self.hostname(), remote['username'])
        if ftp:
            try:
                rc = ftp.size(self.fullpath(remote))
            except (ValueError, TypeError, ftplib.all_errors):
                pass
            finally:
                ftp.close()
        return rc

    def ftplocate(self, remote, options):
        """Delegates to ``system`` qualified name creation."""
        ftp = self.system.ftp(self.hostname(), remote['username'], delayed=True)
        if ftp:
            rloc = ftp.netpath(self.fullpath(remote))
            ftp.close()
            return rloc
        else:
            return None

    def ftpget(self, remote, local, options):
        """Delegates to ``system`` the file transfer of ``remote`` to ``local``."""
        rpath = self.fullpath(remote)
        logger.info('ftpget on ftp://%s/%s (to: %s)', self.hostname(), rpath, local)
        rc = self.system.smartftget(
            rpath,
            local,
            # ftp control
            hostname = self.hostname(),
            logname  = remote['username'],
            fmt      = options.get('fmt'),
        )
        rc = rc and self._hash_get_check(self.ftpget, remote, local, options)
        if rc:
            self._localtarfix(local)
        return rc

    def ftpput(self, local, remote, options):
        """Delegates to ``system`` the file transfer of ``local`` to ``remote``."""
        rpath = self.fullpath(remote)
        put_opts = dict()
        put_opts['fmt'] = options.get('fmt')
        put_opts['sync'] = options.get('enforcesync', False)
        logger.info('ftpput to ftp://%s/%s (from: %s)', self.hostname(), rpath, local)
        rc = self.system.smartftput(
            local,
            rpath,
            # ftp control
            hostname = self.hostname(),
            logname  = remote['username'],
            ** put_opts
        )
        return rc and self._hash_put(self.ftpput, local, remote, options)

    def ftpdelete(self, remote, options):
        """Delegates to ``system`` a distant remove."""
        rc = None
        ftp = self.system.ftp(self.hostname(), remote['username'])
        if ftp:
            actualpath = self.fullpath(remote)
            if self.ftpcheck(actualpath, options=options):
                logger.info('ftpdelete on ftp://%s/%s', self.hostname(), actualpath)
                rc = ftp.delete(actualpath)
                ftp.close()
            else:
                logger.error('Try to remove a non-existing resource <%s>', actualpath)
        return rc


class ArchiveStore(Store):
    """Generic Archive Store."""

    _abstract = True
    _footprint = [
        compressionpipeline,
        dict(
            info = 'Generic archive store',
            attr = dict(
                scheme = dict(
                    values   = ['ftp', 'ftserv'],
                ),
                netloc = dict(
                    values   = ['open.archive.fr'],
                ),
                storehash = dict(
                    values = hashalgo_avail_list,
                ),
                storage = dict(
                    optional = True,
                    default  = None,
                ),
                storeroot = dict(
                    optional = True,
                    default  = '/tmp',
                ),
                storehead = dict(
                    optional = True,
                    default  = 'sto',
                ),
                storesync = dict(
                    alias    = ('archsync', 'synchro'),
                    type     = bool,
                    optional = True,
                    default  = True,
                ),
                storetrue = dict(
                    type     = bool,
                    optional = True,
                    default  = True,
                ),
            )
        ),
    ]

    def __init__(self, *args, **kw):
        logger.debug('Archive store init %s', self.__class__)
        super(ArchiveStore, self).__init__(*args, **kw)

    @property
    def realkind(self):
        return 'archivestore'

    def _str_more(self):
        return 'hostname={:s}'.format(self.hostname())

    def hostname(self):
        """Returns the current :attr:`storage` or the value from the configuration file."""
        if self.storage is None:
            return self.system.env.get('VORTEX_DEFAULT_STORAGE',
                                       self.system.default_target.get('stores:storage', 'hendrix.meteo.fr'))
        else:
            return self.storage

    def _ftpformatpath(self, remote):
        formatted = self.system.path.join(
            remote.get('root', self.storeroot),
            remote['path'].lstrip(self.system.path.sep)
        )
        if self._actual_cpipeline is not None:
            formatted += self._actual_cpipeline.suffix
        return formatted

    def ftpcheck(self, remote, options):
        """Delegates to ``system.ftp`` a distant check."""
        rc = None
        ftp = self.system.ftp(self.hostname(), remote['username'])
        if ftp:
            try:
                rc = ftp.size(self._ftpformatpath(remote))
            except (ValueError, TypeError, ftplib.all_errors):
                pass
            finally:
                ftp.close()
        return rc

    def ftplocate(self, remote, options):
        """Delegates to ``system.ftp`` the path evaluation."""
        rc = None
        ftp = self.system.ftp(self.hostname(), remote['username'], delayed=True)
        if ftp:
            rc = ftp.netpath(self._ftpformatpath(remote))
            ftp.close()
        return rc

    def ftpprestageinfo(self, remote, options):
        """Returns the prestaging informations"""
        logname = remote['username']
        if logname is None:
            ftp = self.system.ftp(self.hostname(), remote['username'], delayed=True)
            logname = ftp.logname
        baseinfo = dict(storage=self.hostname(),
                        logname=logname,
                        location=self._ftpformatpath(remote), )
        return baseinfo

    def ftpget(self, remote, local, options):
        """Delegates to ``system.ftp`` the get action."""
        rpath = self._ftpformatpath(remote)
        logger.info('ftpget on ftp://%s/%s (to: %s)', self.hostname(), rpath, local)
        rc = self.system.smartftget(
            rpath, local,
            # ftp control
            hostname  = self.hostname(),
            logname   = remote['username'],
            cpipeline = self._actual_cpipeline,
            fmt       = options.get('fmt'),
        )
        return rc and self._hash_get_check(self.ftpget, remote, local, options)

    def ftpput(self, local, remote, options):
        """Delegates to ``system.ftp`` the put action."""
        put_sync = options.get('synchro', not options.get('delayed', not self.storesync))
        put_opts = dict(
            hostname  = self.hostname(),
            logname   = remote['username'],
            cpipeline = self._actual_cpipeline,
            fmt       = options.get('fmt'),
        )
        rpath = self._ftpformatpath(remote)
        if put_sync:
            logger.info('ftpput to ftp://%s/%s (from: %s)', self.hostname(), rpath, local)
            put_opts['sync'] = options.get('enforcesync', False)
            rc = self.system.smartftput(local, rpath, **put_opts)
        else:
            logger.info('delayed ftpput to ftp://%s/%s (from: %s)', self.hostname(), rpath, local)
            tempo = footprints.proxy.service(kind='hiddencache', asfmt=put_opts['fmt'])
            put_opts.update(
                todo        = 'ftput',
                rhandler    = options.get('rhandler', None),
                source      = tempo(local),
                destination = rpath,
                original    = self.system.path.abspath(local),
                cpipeline   = ('' if self._actual_cpipeline is None
                               else self._actual_cpipeline.description_string)
            )
            rc = ad.jeeves(**put_opts)
        return rc and self._hash_put(self.ftpput, local, remote, options)

    def ftpdelete(self, remote, options):
        """Delegates to ``system`` a distant remove."""
        rc = None
        ftp = self.system.ftp(self.hostname(), remote['username'])
        if ftp:
            if self.ftpcheck(remote, options=options):
                rpath = self._ftpformatpath(remote)
                logger.info('ftpdelete on ftp://%s/%s', self.hostname(), rpath)
                rc = ftp.delete(rpath)
                ftp.close()
            else:
                logger.error('Try to remove a non-existing resource <%s>',
                             self._ftpformatpath(remote))
        return rc


class ConfigurableArchiveStore(object):
    """Generic Archive Store with the ability to read a configuration file.

    This is a mixin class...
    """

    #: Path to the Store configuration file (please overwrite !)
    _store_global_config = None
    _datastore_id = None

    @staticmethod
    def _get_remote_config(store, url, container):
        """Fetch a configuration file from **url** using **store**."""
        rc = store.get(url, container.iotarget(), dict(fmt='ascii'))
        if rc:
            return config.GenericConfigParser(inifile=container.iotarget())
        else:
            return None

    def _load_config(self, conf):
        """Load the store configuration.

        1. The global store's configuration file is read (see
           ``self.__store_global_config``)
        2. Given ``self.storage``, the proper section of the global configuration
           file is read: it may contain localconf or remoteconfXXX options that
           describe additional configuration files
        3. Fist, the local configuration file is read
        4. Then, the remote configuration files are read

        The relevant content of the configuration file is stored in the ``conf``
        dictionary.
        """
        logger.info("Some store configuration data is needed (for %s://%s)",
                    self.scheme, self.netloc)

        # Because _store_global_config and _datastore_id must be overwritten...
        assert self._store_global_config is not None
        assert self._datastore_id is not None

        # Global configuration file
        logger.info("Reading config file: %s", self._store_global_config)
        maincfg = config.GenericConfigParser(inifile=self._store_global_config)
        conf['host'] = dict(maincfg.items(self.hostname()))

        # Look for a local configuration file
        localcfg = conf['host'].get('localconf', None)
        if localcfg is not None:
            logger.info("Reading config file: %s", localcfg)
            localcfg = config.GenericConfigParser(inifile=localcfg)
            conf['locations'] = defaultdict(dict)
            conf['locations']['generic'] = localcfg.defaults()
            for section in localcfg.sections():
                logger.debug("New location found: %s", section)
                conf['locations'][section] = dict(localcfg.items(section))

        # Look for remote configurations
        remotecfgs = sorted([key for key in conf['host'].iterkeys()
                             if key.startswith('remoteconf')])
        for remotecfg in [conf['host'][k] for k in remotecfgs]:
            logger.info("Reading config file: %s", remotecfg)
            url = net.uriparse(remotecfg)
            tempstore = footprints.proxy.store(
                scheme=url['scheme'],
                netloc=url['netloc'],
                storetrack=False,
            )
            retry = False
            # First, try with a temporary ShouldFly
            try:
                tempcontainer = footprints.proxy.container(shouldfly=True)
                remotecfg_parser = self._get_remote_config(tempstore, url, tempcontainer)
            except (OSError, IOError):
                # This may happen if the user has insufficient rights on
                # the current directory
                retry = True
            finally:
                self.system.remove(tempcontainer.filename)
            # Is retry needed ? This time a completely virtual file is used.
            if retry:
                remotecfg_parser = self._get_remote_config(tempstore, url,
                                                           footprints.proxy.container(incore=True))
            # Update the configuration using the parser
            if remotecfg_parser is not None:
                for section in remotecfg_parser.sections():
                    logger.debug("New location found: %s", section)
                    conf['locations'][section].update(dict(remotecfg_parser.items(section)))
            else:
                raise IOError("The remote configuration {:s} couldn't be found."
                              .format(remotecfg))

    def _actual_fromconf(self, uuid, item):
        """For a given **uuid**, Find the corresponding value of the **item** key
        in the configuration data.

        Access the session's datastore to get the configuration data. If
        necessary, configuration data are read in using the :meth:`_load_config`
        method
        """
        ds = sessions.current().datastore
        conf = ds.get(self._datastore_id, dict(storage=self.hostname()),
                      default_payload=dict(), readonly=True)
        if not conf:
            # If the configuration is empty, do what it takes...
            self._load_config(conf)
        mylocation = uuid.location
        st_root = None
        if mylocation in conf['locations']:
            st_root = conf['locations'][mylocation].get(item, None)
        st_root = st_root or conf['locations']['generic'].get(item, None)
        return st_root

    def _actual_storeroot(self, uuid):
        """For a given **uuid**, determine the proper storeroot."""
        if self.storeroot is None:
            # Read the sotreroot from the configuration data
            st_root = self._actual_fromconf(uuid, 'storeroot')
            if st_root is None:
                raise IOError("No valid storeroot could be found.")
            # The location may be an alias: find the real username
            realname = self._actual_fromconf(uuid, 'realname')
            if realname is None:
                mylocation = uuid.location
            else:
                mylocation = realname
            return st_root.format(location=mylocation)
        else:
            return self.storeroot


class VortexArchiveStore(ArchiveStore):
    """Some kind of archive for VORTEX experiments."""

    _abstract = True
    _footprint = dict(
        info = 'VORTEX archive access',
        attr = dict(
            scheme = dict(
                values   = ['vortex', 'ftp', 'ftserv'],
            ),
            netloc = dict(
                values   = ['vortex.archive.fr'],
            ),
            storehead = dict(
                default  = 'vortex',
                outcast  = ['xp'],
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Vortex archive store init %s', self.__class__)
        super(VortexArchiveStore, self).__init__(*args, **kw)

    def remap_read(self, remote, options):
        """Reformulates the remote path to compatible vortex namespace."""
        pass

    def remap_write(self, remote, options):
        """Remap actual remote path to distant store path for intrusive actions."""
        if 'root' not in remote:
            remote = copy.copy(remote)
            remote['root'] = self.storehead
        return remote

    def vortexcheck(self, remote, options):
        """Remap and ftpcheck sequence."""
        remote = self.remap_read(remote, options)
        return self.ftpcheck(remote, options)

    def vortexlocate(self, remote, options):
        """Remap and ftplocate sequence."""
        remote = self.remap_read(remote, options)
        return self.ftplocate(remote, options)

    def vortexprestageinfo(self, remote, options):
        """Remap and ftpprestageinfo sequence."""
        remote = self.remap_read(remote, options)
        return self.ftpprestageinfo(remote, options)

    def vortexget(self, remote, local, options):
        """Remap and ftpget sequence."""
        remote = self.remap_read(remote, options)
        return self.ftpget(remote, local, options)

    def vortexput(self, local, remote, options):
        """Remap root dir and ftpput sequence."""
        if not self.storetrue:
            logger.info("put deactivated for %s", str(local))
            return True
        remote = self.remap_write(remote, options)
        return self.ftpput(local, remote, options)

    def vortexdelete(self, remote, options):
        """Remap root dir and ftpdelete sequence."""
        remote = self.remap_write(remote, options)
        return self.ftpdelete(remote, options)


class VortexStdArchiveStore(VortexArchiveStore):
    """Archive for casual VORTEX experiments: Support for legacy XPIDs"""

    _footprint = dict(
        info = 'VORTEX archive access for casual experiments',
        attr = dict(
            netloc = dict(
                values   = ['vortex.archive.fr'],
            ),
            storeroot = dict(
                default  = '/home/m/marp/marp999',
            ),
        )
    )

    def remap_read(self, remote, options):
        """Reformulates the remote path to compatible vortex namespace."""
        remote = copy.copy(remote)
        xpath = remote['path'].split('/')
        xpath[3:4] = list(xpath[3])
        xpath[:0] = [self.system.path.sep, self.storehead]
        remote['path'] = self.system.path.join(*xpath)
        return remote


class VortexFreeStdArchiveStore(VortexArchiveStore, ConfigurableArchiveStore):
    """Archive for casual VORTEX experiments: Support for Free XPIDs"""

    #: Path to the vortex-free Store configuration file
    _store_global_config = '@store-vortex-free.ini'
    _datastore_id = 'store-vortex-free-conf'

    _footprint = dict(
        info = 'VORTEX archive access for casual experiments',
        attr = dict(
            netloc = dict(
                values   = ['vortex-free.archive.fr', ],
            ),
            storeroot = dict(
                default  = None,  # That way it will be read from the config file
            ),
        )
    )

    def remap_read(self, remote, options):
        """Reformulates the remote path to compatible vortex namespace."""
        remote = copy.copy(remote)
        xpath = remote['path'].split('/')
        f_xpid = FreeXPid(xpath[3])
        xpath[3] = f_xpid.id
        xpath[:0] = [self.storehead, ]
        if 'root' not in remote:
            remote['root'] = self._actual_storeroot(f_xpid)
        remote['path'] = self.system.path.join(*xpath)
        return remote

    remap_write = remap_read


class VortexOpArchiveStore(VortexArchiveStore):
    """Archive for op VORTEX experiments."""

    _footprint = dict(
        info = 'VORTEX archive access for op experiments',
        attr = dict(
            netloc = dict(
                values   = ['vsop.archive.fr'],
            ),
            storeroot = dict(
                default  = '/home/m/mxpt/mxpt001',
            ),
            storetrue = dict(
                default = DelayedEnvValue('op_archive', True),
            ),
        )
    )

    def remap_read(self, remote, options):
        """Reformulates the remote path to compatible vortex namespace."""
        remote = copy.copy(remote)
        xpath = remote['path'].split('/')
        vxdate = list(xpath[4])
        vxdate.insert(4, '/')
        vxdate.insert(7, '/')
        vxdate.insert(10, '/')
        xpath[4] = ''.join(vxdate)
        xpath[:0] = [self.system.path.sep, self.storehead]
        remote['path'] = self.system.path.join(*xpath)
        return remote

    remap_write = remap_read


class CacheStore(Store):
    """Generic Cache Store."""

    # Each Cache object created by a CacheStore will be stored here:
    # This way it won't be garbage collect and could be re-used later on
    _caches_object_stack = set()

    _footprint = dict(
        info = 'Generic cache store',
        attr = dict(
            scheme = dict(
                values   = ['incache'],
            ),
            netloc = dict(
                values   = ['open.cache.fr'],
            ),
            storehash = dict(
                values = hashalgo_avail_list,
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
            rtouch = dict(
                type     = bool,
                optional = True,
                default  = False,
            ),
            rtouchskip = dict(
                type     = int,
                optional = True,
                default  = 0,
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Generic cache store init %s', self.__class__)
        del self.cache
        super(CacheStore, self).__init__(*args, **kw)

    @property
    def realkind(self):
        return 'cachestore'

    @property
    def hostname(self):
        """Returns the current :attr:`storage`."""
        tg = self.system.default_target
        return tg.inetname if self.storage is None else self.storage

    def use_cache(self):
        """Boolean value to insure that this store is using a cache."""
        return True

    @property
    def underlying_cache_kind(self):
        """The kind of cache that will be used."""
        return self.strategy

    def _get_cache(self):
        if not self._cache:
            self._cache = footprints.proxy.caches.default(
                kind       = self.underlying_cache_kind,
                storage    = self.hostname,
                rootdir    = self.rootdir,
                headdir    = self.headdir,
                rtouch     = self.rtouch,
                rtouchskip = self.rtouchskip,
                readonly   = self.readonly
            )
            self._caches_object_stack.add(self._cache)
        return self._cache

    def _set_cache(self, newcache):
        """Set a new cache reference."""
        if isinstance(newcache, caches.Cache):
            self._cache = newcache

    def _del_cache(self):
        """Invalidate internal cache reference."""
        self._cache = None

    cache = property(_get_cache, _set_cache, _del_cache)

    def _str_more(self):
        return 'entry={:s}'.format(self.cache.entry)

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

    def incacheprestageinfo(self, remote, options):
        """Returns pre-staging informations."""
        return dict(strategy=self.strategy,
                    location=self.incachelocate(remote, options), )

    def incacheget(self, remote, local, options):
        """Simple copy from current cache cache to ``local``."""
        logger.info('incacheget on %s://%s/%s (to: %s)',
                    self.scheme, self.netloc, remote['path'], local)
        rc = self.cache.retrieve(
            remote['path'],
            local,
            intent             = options.get('intent', _CACHE_GET_INTENT_DEFAULT),
            fmt                = options.get('fmt'),
            info               = options.get('rhandler', None),
            tarextract         = options.get('auto_tarextract', False),
            dirextract         = options.get('auto_dirextract', False),
            uniquelevel_ignore = options.get('uniquelevel_ignore', True),
            silent             = options.get('silent', False),
        )
        return rc and self._hash_get_check(self.incacheget, remote, local, options)

    def incacheput(self, local, remote, options):
        """Simple copy from ``local`` to the current cache in readonly mode."""
        logger.info('incacheput to %s://%s/%s (from: %s)',
                    self.scheme, self.netloc, remote['path'], local)
        rc = self.cache.insert(
            remote['path'],
            local,
            intent = _CACHE_PUT_INTENT,
            fmt    = options.get('fmt'),
            info   = options.get('rhandler', None),
        )
        return rc and self._hash_put(self.incacheput, local, remote, options)

    def incachedelete(self, remote, options):
        """Simple removing of the remote resource in cache."""
        logger.info('incachedelete on %s://%s/%s',
                    self.scheme, self.netloc, remote['path'])
        return self.cache.delete(
            remote['path'],
            fmt  = options.get('fmt'),
            info = options.get('rhandler', None),
        )


class _VortexCacheBaseStore(CacheStore):
    """Some kind of cache for VORTEX experiments: one still needs to choose the cache strategy."""

    _abstract = True
    _footprint = dict(
        info = 'VORTEX cache access',
        attr = dict(
            scheme = dict(
                values  = ['vortex'],
            ),
            rootdir = dict(
                default = 'auto'
            ),
            headdir = dict(
                default = 'vortex',
                outcast = ['xp'],
            ),
            rtouch = dict(
                default = True,
            ),
            rtouchskip = dict(
                default = 3,
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Vortex cache store init %s', self.__class__)
        super(_VortexCacheBaseStore, self).__init__(*args, **kw)
        del self.cache

    def vortexcheck(self, remote, options):
        """Proxy to :meth:`incachecheck`."""
        return self.incachecheck(remote, options)

    def vortexlocate(self, remote, options):
        """Proxy to :meth:`incachelocate`."""
        return self.incachelocate(remote, options)

    def vortexprestageinfo(self, remote, options):
        """Proxy to :meth:`incacheprestageinfo`."""
        return self.incacheprestageinfo(remote, options)

    def vortexget(self, remote, local, options):
        """Proxy to :meth:`incacheget`."""
        return self.incacheget(remote, local, options)

    def vortexput(self, local, remote, options):
        """Proxy to :meth:`incacheputt`."""
        return self.incacheput(local, remote, options)

    def vortexdelete(self, remote, options):
        """Proxy to :meth:`incachedelete`."""
        return self.incachedelete(remote, options)


class VortexCacheMtStore(_VortexCacheBaseStore):
    """Some kind of MTOOL cache for VORTEX experiments."""

    _footprint = dict(
        info = 'VORTEX MTOOL like Cache access',
        attr = dict(
            netloc = dict(
                values  = ['vortex.cache.fr', 'vortex.cache-mt.fr',
                           'vortex-free.cache.fr', 'vortex-free.cache-mt.fr',
                           'vsop.cache-mt.fr'],
            ),
            strategy = dict(
                default = 'mtool',
            ),
        )
    )


class VortexCacheOp2ResearchStore(_VortexCacheBaseStore):
    """The DSI/OP VORTEX cache where researchers can get the freshest data."""

    _footprint = dict(
        info = 'VORTEX Mtool cache access',
        attr = dict(
            netloc = dict(
                values  = ['vsop.cache-primary.fr', 'vsop.cache-secondary.fr'],
            ),
            strategy = dict(
                default = 'op2r',
            ),
            readonly = dict(
                default = True,
            )
        )
    )

    @property
    def underlying_cache_kind(self):
        """The kind of cache that will be used."""
        mgrp = re.match(r'\w+\.cache-(\w+)\.\w+', self.netloc)
        return '_'.join((self.strategy, mgrp.group(1)))


class VortexVsopCacheStore(MultiStore):

    _footprint = dict(
        info = 'VORTEX vsop magic cache access',
        attr = dict(
            scheme = dict(
                values  = ['vortex'],
            ),
            netloc = dict(
                values  = ['vsop.cache.fr', ],
            ),
            glovekind = dict(
                optional = True,
                default = '[glove::realkind]',
            ),
            refillstore = dict(
                default = False,
            )
        )
    )

    def alternates_netloc(self):
        '''For Non-Op users, Op caches may be accessed in read-only mode.'''
        todo = ['vsop.cache-mt.fr', ]  # The MTOOL Cache remains a must :-)
        if self.glovekind != 'opuser':
            for loc in ('primary', 'secondary'):
                if int(self.system.default_target.get('stores:vsop_cache_op{}'.format(loc), '0')):
                    todo.append('vsop.cache-{}.fr'.format(loc))
        return todo


class VortexStore(MultiStore):
    """Combined cache and archive VORTEX stores."""

    _footprint = dict(
        info = 'VORTEX multi access',
        attr = dict(
            scheme = dict(
                values  = ['vortex'],
            ),
            netloc = dict(
                values  = ['vortex.multi.fr', 'vortex-free.multi.fr', 'vsop.multi.fr'],
            ),
            refillstore = dict(
                default = True,
            )
        )
    )

    def alternates_netloc(self):
        """Tuple of alternates domains names, e.g. ``cache`` and ``archive``."""
        return [self.netloc.firstname + d for d in ('.cache.fr', '.archive.fr')]


class PromiseCacheStore(VortexCacheMtStore):
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

    @staticmethod
    def _add_default_options(options):
        if options is not None:
            options_upd = options.copy()
        else:
            options_upd = dict()
        options_upd['fmt'] = 'ascii'  # Promises are always JSON files
        return options_upd

    def vortexget(self, remote, local, options):
        """Proxy to :meth:`incacheget`."""
        return super(PromiseCacheStore, self).vortexget(remote, local, self._add_default_options(options))

    def vortexput(self, local, remote, options):
        """Proxy to :meth:`incacheput`."""
        return super(PromiseCacheStore, self).vortexput(local, remote, self._add_default_options(options))

    def vortexdelete(self, remote, options):
        """Proxy to :meth:`incachedelete`."""
        return super(PromiseCacheStore, self).vortexdelete(remote, self._add_default_options(options))


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
            storetrack = dict(
                type  = bool,
                default = True,
                optional = True,
            ),
            prstorename = dict(
                optional = True,
                default  = 'promise.cache.fr',
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
            scheme=self.proxyscheme,
            netloc=self.prstorename,
            storetrack=self.storetrack,
        )
        if self.promise is None:
            logger.critical('Could not find store scheme <%s> netloc <%s>',
                            self.proxyscheme, self.prstorename)
            raise ValueError('Could not get a Promise Store')

        # Find the other "real" store (could be a multi-store)
        self.other = footprints.proxy.store(
            scheme=self.proxyscheme,
            netloc=self.netloc,
            storetrack=self.storetrack,
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
        self.system.json_dump(info, pfile, sort_keys=True, indent=4)
        return pfile

    def check(self, remote, options=None):
        """Go through internal opened stores and check for the resource."""
        logger.debug('Promise check from %s', remote)
        return self.other.check(remote.copy(), options) or self.promise.check(remote.copy(), options)

    def locate(self, remote, options=None):
        """Go through internal opened stores and locate the expected resource for each of them."""
        logger.debug('Promise locate %s', remote)

        inpromise = True
        if options:
            inpromise = options.get('inpromise', True)

        locate_other = self.other.locate(remote.copy(), options)
        if inpromise:
            locate_promised = self.promise.locate(remote.copy(), options)
            return locate_promised + ';' + locate_other
        return locate_other

    def get(self, remote, local, options=None):
        """Go through internal opened stores for the first available resource."""
        logger.debug('Promise get %s', remote)
        if options is None:
            options = dict()
        self.delayed = False
        logger.info('Try promise from store %s', self.promise)
        rc = self.promise.get(remote.copy(), local, options)
        if rc:
            self.delayed = True
        else:
            logger.info('Try promise from store %s', self.other)
            rc = self.other.get(remote.copy(), local, options)
        if not rc and options.get('pretend', False):
            logger.warning('Pretending to get a promise for <%s>', local)
            pr_info = self.mkpromise_info(remote, options)
            pr_file = self.mkpromise_file(pr_info, local)
            self.system.move(pr_file, local)
            rc = self.delayed = True
        return rc

    @staticmethod
    def _clean_pr_json(prjson):
        del prjson['stamp']
        if 'options' in prjson['rhandler']:
            prjson['rhandler']['options'].pop('storetrack', False)
        return prjson

    def put(self, local, remote, options=None):
        """Put a promise or the actual resource if available."""
        logger.debug('Multistore put from %s to %s', local, remote)
        if options is None:
            options = dict()
        if options.get('force', False) or not self.system.path.exists(local):
            if not self.other.use_cache():
                logger.critical('Could not promise resource without other cache <%s>', self.other)
                raise ValueError('Could not promise: other store does not use cache')
            pr_info = self.mkpromise_info(remote, options)
            pr_file = self.mkpromise_file(pr_info, local)
            # Check if a previous promise with the same description exists
            preexisting = self.promise.check(remote.copy(), options)
            if preexisting:
                pr_old_file = self.promise.locate(remote.copy())
                prcheck = self._clean_pr_json(self.system.json_load(pr_old_file))
                prnew = self._clean_pr_json(self.system.json_load(pr_file))
                preexisting = prcheck == prnew
                if preexisting:
                    logger.info("The promise file <%s> preexisted and is compatible",
                                pr_old_file)
                    rc = True
                else:
                    logger.warning("The promise file <%s> already exists but doesn't match",
                                   pr_old_file)

            # Put the new promise file in the PromiseCache
            options['obs_overridelocal'] = local  # Pretty nasty :-(
            if not preexisting:
                logger.warning('Log a promise instead of missing resource <%s>', local)
                rc = self.promise.put(pr_file, remote.copy(), options)
                if rc:
                    del options['obs_overridelocal']
                    self.other.delete(remote.copy(), options)
            else:
                options['dryrun'] = True  # Just update the tracker
                rc = self.promise.put(pr_file, remote.copy(), options)
            self.system.remove(pr_file)

        else:
            logger.info('Actual promise does exists <%s>', local)
            rc = self.other.put(local, remote.copy(), options)
            if rc:
                self.promise.delete(remote.copy(), options)
        return rc

    def delete(self, remote, options=None):
        """Go through internal opened stores and delete the resource."""
        logger.debug('Promise delete from %s', remote)
        return self.promise.delete(remote.copy(), options) and self.other.delete(remote.copy(), options)


class VortexPromiseStore(PromiseStore):
    """Combine a Promise Store for expected resources and any VORTEX Store."""

    _footprint = dict(
        info = 'VORTEX promise store',
        attr = dict(
            scheme = dict(
                values = ['xvortex'],
            ),
        )
    )


# Activate the footprint's fasttrack on the stores collector
fcollect = footprints.collectors.get(tag='store')
fcollect.fasttrack = ('netloc', 'scheme')
del fcollect
