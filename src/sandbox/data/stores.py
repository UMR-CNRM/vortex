# -*- coding: utf-8 -*-

"""
This module contains "fake" stores for demonstration purposes.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

from vortex.data.stores import VortexArchiveStore, VortexCacheMtStore, VortexStore, \
    PromiseCacheStore, VortexPromiseStore

from gco.data.stores import UgetHackCacheStore, _UgetCacheStore, UgetArchiveStore, UgetStore


class VortexDemoArchiveStore(VortexArchiveStore):
    """Archive for demo VORTEX experiments."""

    _footprint = dict(
        info = 'VORTEX archive access for demo experiments',
        attr = dict(
            netloc = dict(
                values   = ['vortex-demo.archive.fr'],
            ),
            storeroot = dict(
                default  = None,
            ),
            storage = dict(
                default  = 'localhost',
            ),
            storetube=dict(
                # Use this very special protocol...
                default  = 'demo',
            ),
        )
    )


class VortexDemoCacheStore(VortexCacheMtStore):
    """Cache for demo VORTEX experiments."""

    _footprint = dict(
        info = 'VORTEX MTOOL like Demo cache access',
        attr = dict(
            netloc = dict(
                values  = ['vortex-demo.cache.fr'],
            ),
            strategy = dict(
                default = 'mtool-demo',
            ),
        )
    )


class VortexDemoStore(VortexStore):
    """Combined cache and archive for demo VORTEX experiments."""

    _footprint = dict(
        info = 'VORTEX Demo access',
        attr = dict(
            netloc = dict(
                values  = ['vortex-demo.multi.fr'],
            ),
        )
    )


class DemoPromiseCacheStore(PromiseCacheStore):
    """Some kind of vortex cache for demo expected resources."""

    _footprint = dict(
        info = 'EXPECTED cache access',
        attr = dict(
            netloc = dict(
                values  = ['promise-demo.cache.fr'],
            ),
            headdir = dict(
                default = 'promise',
                outcast = ['xp', 'vortex'],
            ),
            strategy=dict(
                default='mtool-demo',
            ),
        )
    )


class VortexDemoPromiseStore(VortexPromiseStore):
    """Combine a Promise Store for expected resources and a Demo VORTEX Store."""

    _footprint = dict(
        info = 'VORTEX promise store',
        attr = dict(
            scheme = dict(
                values = ['xvortex'],
            ),
            prstorename=dict(
                optional=True,
                default='promise-demo.cache.fr',
            ),
            netloc = dict(
                outcast = [],
                values = ['vortex-demo.cache.fr', 'vortex-demo.multi.fr'],
            ),
        )
    )


class UgetDemoArchiveStore(UgetArchiveStore):
    """Uget Demo archive store."""

    _footprint = dict(
        info = 'Uget Archive Store',
        attr = dict(
            netloc = dict(
                values   = ['uget-demo.archive.fr'],
            ),
            storeroot = dict(
                default  = None,
            ),
            storage = dict(
                default  = 'localhost',
            ),
            storetube=dict(
                # Use this very special protocol...
                default  = 'demo',
            ),
            readonly = dict(
                default = True,
            )
        )
    )

    def _actual_storeroot(self, uuid):
        """Ignore the configuration file data."""
        return '.'


class UgetDemoCacheStore(_UgetCacheStore):
    """Some kind of cache for Demo Uget storage."""

    _footprint = dict(
        info = 'Uget Demo MTOOL cache access',
        attr = dict(
            netloc = dict(
                values  = ['uget-demo.cache.fr'],
            ),
            strategy = dict(
                default = 'mtool-demo',
            ),
        )
    )


class UgetDemoHackCacheStore(UgetHackCacheStore):
    """Some kind of hack for Demo Uget storage."""

    _footprint = dict(
        info='Uget Demo Hack access',
        attr=dict(
            netloc=dict(
                values=['uget-demo.hack.fr'],
            ),
        ),
    )


class UgetDemoStore(UgetStore):
    """Combined cache and archive for Demo Uget storage."""

    _footprint = dict(
        info='Uget Demo access',
        attr=dict(
            netloc=dict(
                values=['uget-demo.multi.fr'],
            ),
        ),
    )

    def alternates_netloc(self):
        """Tuple of alternates domains names, e.g. ``cache`` and ``archive``."""
        return 'uget-demo.hack.fr', 'uget-demo.cache.fr', 'uget-demo.archive.fr'
