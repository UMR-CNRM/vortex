#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import footprints

from vortex.data.providers import Provider
from vortex.syntax.stdattrs import Namespace

from gco.tools import genv, uenv
from gco.syntax.stdattrs import GgetId, UgetId

#: No automatic export
__all__ = []

logger = footprints.loggers.getLogger(__name__)

_COMMON_GCO_FP = dict(
    gspool = dict(
        alias    = ('gtmp', 'gcotmp', 'gcospool', 'tampon'),
        optional = True,
        default  = 'tampon'
    ),
    gnamespace = dict(
        type     = Namespace,
        optional = True,
        values   = ['gco.cache.fr', 'gco.meteo.fr', 'gco.multi.fr'],
        default  = Namespace('gco.meteo.fr'),
    ))


class GcoProvider(Provider):
    """Abstract GCO base class for GGet and GEnv providers."""

    _abstract = True
    _footprint = dict(
        info = 'GCO abstract provider',
        attr = _COMMON_GCO_FP,
    )

    def __init__(self, *args, **kw):
        """Proxy init abstract method. Logging only for the time being."""
        logger.debug('GcoProvider abstract init %s', self.__class__)
        super(GcoProvider, self).__init__(*args, **kw)

    def scheme(self, resource):
        """Default scheme is ``gget``."""
        return 'gget'

    def netloc(self, resource):
        """Default network location is ``gco.meteo.fr``."""
        return self.gnamespace

    def pathname(self, resource):
        """Equal to gspool name."""
        return self.gspool


class GGet(GcoProvider):
    """
    Provides a description of GCO central repository of op components.

    Extended footprint:

    * gget (mandatory)
    * gspool (optional, default: ``tampon``)
    """

    _footprint = dict(
        info = 'GGet provider',
        attr = dict(
            gget = dict(
                type = GgetId,
            ),
        )
    )

    def __init__(self, *args, **kw):
        """Proxy init method. Logging only for the time being."""
        logger.debug('GGet provider init %s', self.__class__)
        super(GGet, self).__init__(*args, **kw)

    @property
    def realkind(self):
        """Default realkind is ``gget``."""
        return 'gget'

    def basename(self, resource):
        """Concatenation of gget attribute and current resource basename."""
        return self.gget + resource.basename(self.realkind)


class GEnv(GcoProvider):
    """
    Provides a description of GCO global cycles contents.

    Extended footprint:

    * genv (mandatory)
    * gspool (optional, default: ``tampon``)
    """

    _footprint = dict(
        info = 'GEnv provider',
        attr = dict(
            genv = dict(
                alias = ('gco_cycle', 'gcocycle', 'cyclegco', 'gcycle'),
                type = GgetId,
            ),
        )
    )

    def __init__(self, *args, **kw):
        """Proxy init method. Logging only for the time being."""
        logger.debug('GEnv provider init %s', self.__class__)
        super(GEnv, self).__init__(*args, **kw)

    @property
    def realkind(self):
        """Default realkind is ``genv``."""
        return 'genv'

    def _str_more(self):
        """Additional information to print representation."""
        return "cycle='{0:s}'".format(self.genv)

    def basename(self, resource):
        """
        Relies on :mod:`gco.tools.genv` contents for current ``genv`` attribute value
        in relation to current resource ``gvar`` attribute.
        """
        gconf = genv.contents(cycle=self.genv)
        if not gconf:
            logger.error('Cycle not registred <%s>', self.genv)
            raise ValueError('Unknow cycle ' + self.genv)
        gkey = resource.basename(self.realkind)
        if gkey not in gconf:
            logger.error('Key <%s> unknown in cycle <%s>', gkey, self.genv)
            raise ValueError('Unknow gvar ' + gkey)
        return gconf[gkey] + resource.basename(GGet.footprint_clsrealkind())


class _UtypeProvider(Provider):
    """Abstract Uget/env base class for Uget and Uenv providers."""

    _abstract = True
    _footprint = dict(
        info = 'Uget/Uenv abstract provider',
        attr = dict(
            unamespace = dict(
                type     = Namespace,
                optional = True,
                values   = ['uget.hack.fr', 'uget.cache.fr', 'uget.archive.fr', 'uget.multi.fr'],
                default  = Namespace('uget.multi.fr'),
            )
        )
    )


class UGetProvider(_UtypeProvider):
    """Provides a description of a Uget repository of op components."""

    _footprint = dict(
        info = 'Uget provider',
        attr = dict(
            uget = dict(
                type = UgetId,
            ),
        )
    )

    @property
    def realkind(self):
        """Default realkind is ``gget``."""
        return 'uget'

    def scheme(self, resource):
        """Default scheme is ``gget``."""
        return 'uget'

    def netloc(self, resource):
        """Default network location is ``gco.meteo.fr``."""
        return self.unamespace

    def pathname(self, resource):
        """Uget only fetched data."""
        return 'data'

    def basename(self, resource):
        """Concatenation of gget attribute and current resource basename."""
        return '{0.id:s}{1:s}@{0.location:s}'.format(self.uget,
                                                     resource.basename(self.realkind))


class UEnvProvider(_UtypeProvider):
    """Provides a description of a Uenv global cycles contents."""

    _footprint = dict(
        info = 'UEnv provider',
        attr = [_COMMON_GCO_FP,
                dict(
                    uenv = dict(
                        alias = ('genv', 'gco_cycle', 'gcocycle', 'cyclegco', 'gcycle'),
                        type = UgetId,
                    ),
                )
                ]
    )

    def __init__(self, *kargs, **kwargs):
        super(UEnvProvider, self).__init__(*kargs, **kwargs)
        self._id_cache = dict()

    @property
    def realkind(self):
        """Default realkind is ``genv``."""
        return 'uenv'

    def _str_more(self):
        """Additional information to print representation."""
        return "cycle='{0:s}'".format(self.uenv)

    def _get_id(self, resource):
        """Return the UgetId or GgetId associated with a given resource."""
        if id(resource) not in self._id_cache:
            gconf = uenv.contents(cycle=self.uenv, scheme='uget', netloc=self.unamespace)
            gkey = resource.basename(self.realkind)
            if gkey not in gconf:
                logger.error('Key <%s> unknown in cycle <%s>', gkey, self.uenv)
                raise ValueError('Unknow gvar ' + gkey)
            self._id_cache[id(resource)] = gconf[gkey]
        return self._id_cache[id(resource)]

    def scheme(self, resource):
        """Default scheme is ``gget``."""
        theid = self._get_id(resource)
        return 'uget' if isinstance(theid, UgetId) else 'gget'

    def netloc(self, resource):
        """Default network location is ``gco.meteo.fr``."""
        theid = self._get_id(resource)
        return self.unamespace if isinstance(theid, UgetId) else self.gnamespace

    def pathname(self, resource):
        """Uenv fetches Uget data or some stuff from the Ggetn tampon."""
        theid = self._get_id(resource)
        return 'data' if isinstance(theid, UgetId) else self.gspool

    def basename(self, resource):
        """
        Relies on :mod:`gco.tools.genv` contents for current ``genv`` attribute value
        in relation to current resource ``gvar`` attribute.
        """
        theid = self._get_id(resource)
        if isinstance(theid, UgetId):
            return ('{0.id:s}{1:s}@{0.location:s}'.
                    format(theid, resource.basename(UGetProvider.footprint_clsrealkind())))
        else:
            return '{0:s}{1:s}'.format(theid,
                                       resource.basename(GGet.footprint_clsrealkind()))
