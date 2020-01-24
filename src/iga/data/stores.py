#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=unused-argument

from __future__ import print_function, absolute_import, unicode_literals, division

from bronx.fancies import loggers
import footprints

from vortex.data.abstractstores import Store
from vortex.data.stores import Finder
from vortex.syntax.stdattrs import DelayedEnvValue, hashalgo_avail_list

from gco.data.stores import GcoCacheStore

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class IgaGcoCacheStore(GcoCacheStore):
    """Some kind of cache for GCO components in OP context."""

    _footprint = dict(
        info = 'OPGCO cache access',
        attr = dict(
            netloc = dict(
                values  = ['opgco.cache.fr'],
            ),
            rootdir = dict(
                default = DelayedEnvValue('op_gcocache'),
            ),
        )
    )

    def ggetget(self, remote, local, options):
        """
        Gateway to :meth:`incacheget`.
        Resources should be already extracted from in-cache archives files.
        """
        extract = remote['query'].get('extract', None)
        options_tmp = options.copy()
        options_tmp['auto_tarextract'] = True
        # Is it a preprocessed tar (i.e ggetall alreadu untared it ?)
        if remote['path'].endswith('.tgz'):
            remote['path'] = remote['path'][:-4]
            if not extract:
                options_tmp['auto_dirextract'] = True
        if extract:
            remote['path'] = self.system.path.join(remote['path'], extract[0])
            logger.info('Extend remote path with extract value <%s>', remote['path'])
        return self.incacheget(remote, local, options_tmp)


class IgaFinder(Finder):
    """
    Inline disk store for operational data resources produced outside
    of the vortex scope.
    """

    _footprint = dict(
        info = 'Iga file access',
        attr = dict(
            netloc = dict(
                outcast  = list(),
                values   = ['oper.inline.fr', 'dbl.inline.fr', 'dble.inline.fr', 'test.inline.fr'],
                remap    = {
                    'dbl.inline.fr': 'dble.inline.fr'
                }
            ),
            rootdir = dict(
                alias    = [ 'opdata', 'datadir' ],
                optional = True,
                default  = DelayedEnvValue('DATADIR'),
            ),
        ),
        priority = dict(
            level = footprints.priorities.top.OPER
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('IgaFinder store init %s', self.__class__)
        super(IgaFinder, self).__init__(*args, **kw)

    def fullpath(self, remote):
        if remote['query'].get('relative', False):
            return remote['path'].lstrip('/')
        else:
            return self.rootdir + remote['path']

    def fileget(self, remote, local, options):
        """Delegates to ``system`` the copy of ``remote`` to ``local``."""
        rpath = self.fullpath(remote)
        logger.info('fileget on %s (to: %s)', rpath, local)
        rc = self.system.cp(rpath, local, intent=options.get('intent'), fmt=options.get('fmt'))
        rc = rc and self._hash_get_check(self.fileget, remote, local, options)
        if rc:
            self._localtarfix(local)
        return rc


class SopranoStore(Store):

    _footprint = dict(
        info = 'Soprano access',
        attr = dict(
            scheme = dict(
                values   = ['ftp', 'ftserv'],
            ),
            netloc = dict(
                values   = ['prod.soprano.fr', 'intgr.soprano.fr'],
                default  = 'prod.soprano.fr'
            ),
            storage = dict(
                optional = True,
                values   = ['piccolo.meteo.fr', 'piccolo-int.meteo.fr'],
                default  = 'piccolo.meteo.fr',
            ),
            storeroot = dict(
                alias    = ['sopranohome'],
                default  = '/SOPRANO',
                optional = True,
            ),
            storehash = dict(
                values = hashalgo_avail_list,
            ),
        ),
        priority = dict(
            level = footprints.priorities.top.OPER
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Soprano store init %s', self.__class__)
        super(SopranoStore, self).__init__(*args, **kw)

    @property
    def realkind(self):
        return 'soprano'

    def hostname(self):
        return self.storage

    def fullpath(self, remote):
        return self.storeroot + remote['path']

    def ftplocate(self, remote, options):
        """Delegates to ``system`` a distant check."""
        ftp = self.system.ftp(self.hostname(), remote['username'], delayed=True)
        if ftp:
            rloc = ftp.netpath(self.fullpath(remote))
            ftp.close()
            return rloc
        else:
            return None

    def ftpcheck(self, remote, options):
        """Delegates to ``system`` a distant check."""
        ftp = self.system.ftp(self.hostname(), remote['username'])
        if ftp:
            rc = ftp.size(self.fullpath(remote))
            ftp.close()
            return rc

    def ftpget(self, remote, local, options):
        ftp = self.system.ftp(self.hostname(), remote['username'])
        if ftp:
            rc = ftp.get(self.fullpath(remote), local)
            ftp.close()
            rc = rc and self._hash_get_check(self.ftpget, remote, local, options)
            extract = remote['query'].get('extract', None)
            if extract:
                if extract == 'all':
                    rc = self.system.untar(local, output=False)
                else:
                    rc = self.system.untar(local, extract, output=False)
                    if local != extract:
                        rc = self.system.mv(extract, local)
            return rc

    def ftpput(self, local, remote, options):
        rc = self.system.ftput(
            local,
            self.fullpath(remote),
            # ftp control
            hostname = self.hostname(),
            logname  = remote['username'],
            fmt      = options.get('fmt')
        )
        return rc and self._hash_put(self.ftpput, local, remote, options)
