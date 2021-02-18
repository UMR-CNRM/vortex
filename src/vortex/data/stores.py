#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=unused-argument

"""
This module handles store objects in charge of physically accessing resources.
Store objects use the :mod:`footprints` mechanism.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import copy
import ftplib
import re
import six

from bronx.fancies import loggers
import footprints

from vortex.data.abstractstores import Store, ArchiveStore, ConfigurableArchiveStore, CacheStore
from vortex.data.abstractstores import MultiStore, PromiseStore
from vortex.layout import dataflow
from vortex.syntax.stdattrs import hashalgo_avail_list
from vortex.syntax.stdattrs import FreeXPid
from vortex.syntax.stdattrs import DelayedEnvValue

#: Export base class
__all__ = []

logger = loggers.getLogger(__name__)


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

    def has_fast_check(self):
        """A void check is very fast !"""
        return True

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

    def has_fast_check(self):
        """A void check is very fast !"""
        return True

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
            # Handle StringIO objects, by changing them to ByteIOs...
            if isinstance(fres, six.StringIO):
                s_fres = fres
                s_fres.seek(0)
                fres = six.BytesIO()
                for l in s_fres:
                    fres.write(l.encode(encoding='utf-8'))
                fres.seek(0)
            # NB: fres should be a file like object (BytesIO will do the trick)
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
        logger.debug('Finder store init %s', self.__class__)
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
        if (isinstance(local, six.string_types) and self.system.path.isfile(local) and
                self.system.is_tarfile(local)):
            destdir = self.system.path.dirname(self.system.path.realpath(local))
            self.system.smartuntar(local, destdir)

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
            except (ValueError, TypeError):
                pass
            except ftplib.all_errors:
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
            hostname=self.hostname(),
            logname=remote['username'],
            fmt=options.get('fmt'),
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
            hostname=self.hostname(),
            logname=remote['username'],
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


class VortexArchiveStore(ArchiveStore):
    """Some kind of archive for VORTEX experiments."""

    _abstract = True
    _footprint = dict(
        info = 'VORTEX archive access',
        attr = dict(
            scheme = dict(
                values   = ['vortex'],
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

    def remap_list(self, remote, options):
        """Reformulates the remote path to compatible vortex namespace."""
        if len(remote['path'].split('/')) >= 4:
            return self.remap_read(remote, options)
        else:
            logger.critical('The << %s >> path is not listable.', remote['path'])
            return None
        return remote

    def remap_write(self, remote, options):
        """Remap actual remote path to distant store path for intrusive actions."""
        if 'root' not in remote:
            remote = copy.copy(remote)
            remote['root'] = self.storehead
        return remote

    def vortexcheck(self, remote, options):
        """Remap and ftpcheck sequence."""
        remote = self.remap_read(remote, options)
        return self.inarchivecheck(remote, options)

    def vortexlocate(self, remote, options):
        """Remap and ftplocate sequence."""
        remote = self.remap_read(remote, options)
        return self.inarchivelocate(remote, options)

    def vortexlist(self, remote, options):
        """Remap and ftplist sequence."""
        remote = self.remap_list(remote, options)
        if remote:
            return self.inarchivelist(remote, options)
        else:
            return None

    def vortexprestageinfo(self, remote, options):
        """Remap and ftpprestageinfo sequence."""
        remote = self.remap_read(remote, options)
        return self.inarchiveprestageinfo(remote, options)

    def vortexget(self, remote, local, options):
        """Remap and ftpget sequence."""
        remote = self.remap_read(remote, options)
        return self.inarchiveget(remote, local, options)

    def vortexearlyget(self, remote, local, options):
        """Remap and ftpget sequence."""
        remote = self.remap_read(remote, options)
        return self.inarchiveearlyget(remote, local, options)

    def vortexfinaliseget(self, result_id, remote, local, options):
        """Remap and ftpget sequence."""
        remote = self.remap_read(remote, options)
        return self.inarchivefinaliseget(result_id, remote, local, options)

    def vortexput(self, local, remote, options):
        """Remap root dir and ftpput sequence."""
        if not self.storetrue:
            logger.info("put deactivated for %s", str(local))
            return True
        remote = self.remap_write(remote, options)
        return self.inarchiveput(local, remote, options)

    def vortexdelete(self, remote, options):
        """Remap root dir and ftpdelete sequence."""
        remote = self.remap_write(remote, options)
        return self.inarchivedelete(remote, options)


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
        xpath = remote['path'].strip('/').split('/')
        f_xpid = FreeXPid(xpath[2])
        xpath[2] = f_xpid.id
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
        if len(xpath) >= 5 and re.match(r'^\d{8}T\d{2,4}', xpath[4]):
            # If a date is detected
            vxdate = list(xpath[4])
            vxdate.insert(4, '/')
            vxdate.insert(7, '/')
            vxdate.insert(10, '/')
            xpath[4] = ''.join(vxdate)
        xpath[:0] = [self.system.path.sep, self.storehead]
        remote['path'] = self.system.path.join(*xpath)
        return remote

    remap_write = remap_read


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
                outcast = ['xp', ],
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
        del self.cache
        super(_VortexCacheBaseStore, self).__init__(*args, **kw)

    def vortexcheck(self, remote, options):
        """Proxy to :meth:`incachecheck`."""
        return self.incachecheck(remote, options)

    def vortexlocate(self, remote, options):
        """Proxy to :meth:`incachelocate`."""
        return self.incachelocate(remote, options)

    def vortexlist(self, remote, options):
        """Proxy to :meth:`incachelocate`."""
        return self.incachelist(remote, options)

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
                values  = ['vortex.cache-mt.fr', 'vortex-free.cache-mt.fr',
                           'vsop.cache-mt.fr'],
            ),
            strategy = dict(
                default = 'mtool',
            ),
        )
    )


class VortexCacheBuddiesStore(_VortexCacheBaseStore):
    """Some kind of MTOOL cache for VORTEX experiments."""

    _footprint = dict(
        info = 'VORTEX MTOOL like Cache access',
        attr = dict(
            netloc = dict(
                values  = ['vortex.cache-buddies.fr', 'vortex-free.cache-buddies.fr', ],
            ),
            strategy = dict(
                default = 'mtoolbuddies',
            ),
            headdir = dict(
                default = 'vortexbuddies',
            ),
            rtouch = dict(
                default = False,
            ),
            readonly = dict(
                values  = [True, ],
                default = True,
            )
        )
    )


class VortexCacheMarketPlaceStore(_VortexCacheBaseStore):
    """Some kind of centralised cache for VORTEX experiments."""

    _footprint = dict(
        info = "VORTEX's centralised Cache access",
        attr = dict(
            netloc = dict(
                values  = ['vortex.cache-market.fr', 'vortex-free.cache-market.fr', ],
            ),
            strategy = dict(
                default = 'marketplace',
            ),
            rtouch = dict(
                default = False,
            ),
        )
    )


class VortexCacheStore(MultiStore):

    _footprint = dict(
        info = 'VORTEX cache access',
        attr = dict(
            scheme = dict(
                values  = ['vortex'],
            ),
            netloc = dict(
                values  = ['vortex.cache.fr', 'vortex-free.cache.fr', ],
            ),
            refillstore = dict(
                default = False,
            )
        )
    )

    def filtered_readable_openedstores(self, remote):
        ostores = [self.openedstores[0], ]
        ostores.extend([sto for sto in self.openedstores[1:]
                        if sto.cache.allow_reads(remote['path'])])
        return ostores

    def filtered_writeable_openedstores(self, remote):
        ostores = [self.openedstores[0], ]
        ostores.extend([sto for sto in self.openedstores[1:]
                        if sto.cache.allow_writes(remote['path'])])
        return ostores

    def alternates_netloc(self):
        """For Non-Op users, Op caches may be accessed in read-only mode."""
        netloc_m = re.match(r'(?P<base>vortex.*)\.cache\.(?P<country>\w+)', self.netloc)
        mt_netloc = '{base:s}.cache-mt.{country:s}'.format(** netloc_m.groupdict())
        bd_netloc = '{base:s}.cache-buddies.{country:s}'.format(** netloc_m.groupdict())
        ma_netloc = '{base:s}.cache-market.{country:s}'.format(** netloc_m.groupdict())
        return [mt_netloc, bd_netloc, ma_netloc]


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
        """For Non-Op users, Op caches may be accessed in read-only mode."""
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
        options_upd['intent'] = 'in'  # Promises are always read-only
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
