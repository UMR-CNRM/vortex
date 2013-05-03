#!/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

from vortex.autolog import logdefault as logger

from vortex.data.providers import Provider
from gco.tools import genv


class GGet(Provider):
    """
    Provides a description of GCO central repository of op components.
    
    Extended footprint:
    
    * gget (mandatory)
    * gspool (optional, default: ``tampon``)
    """

    _footprint = dict(
        info = 'GGet provider',
        attr = dict(
            gget = dict(),
            gspool = dict(
                alias = ( 'gtmp', 'gcotmp', 'gcospool', 'tampon' ),
                optional = True,
                default = 'tampon'
            )
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('GGet provider init %s', self)
        super(GGet, self).__init__(*args, **kw)

    @property
    def realkind(self):
        """Default realkind is ``gget``."""
        return 'gget'

    def scheme(self):
        """Default scheme is ``gget``."""
        return 'gget'

    def domain(self):
        """Default domain is ``gco.meteo.fr``."""
        return 'gco.meteo.fr'

    def pathname(self, resource):
        """Equal to gspool name."""
        return self.gspool

    def basename(self, resource):
        """Concatenation of gget attribute and current resource basename."""
        return self.gget + resource.basename(self.realkind)


class GEnv(Provider):
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
                alias = ( 'gco_cycle', 'gcycle' )
            ),
            gspool = dict(
                alias = ( 'gtmp', 'gcotmp', 'gcospool', 'tampon' ),
                optional = True,
                default = 'tampon'
            )
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Genv provider init %s', self)
        super(GEnv, self).__init__(*args, **kw)


    @property
    def realkind(self):
        """Default realkind is ``genv``."""
        return 'genv'

    def scheme(self):
        """Default scheme is ``gget``."""
        return 'gget'

    def domain(self):
        """Default domain is ``gco.meteo.fr``."""
        return 'gco.meteo.fr'

    def pathname(self, resource):
        """Equal to gspool name."""
        return self.gspool

    def basename(self, resource):
        """Relies on :mod:`gco.tools.genv` contents for current ``genv`` attribute value
        in relation to current resource ``gvar`` attribute."""
        gconf = genv.contents(cycle=self.genv)
        if not gconf:
            logger.error('No such registered cycle %s', self.genv)
            raise Exception('Unknow cycle ' + self.genv)
        gkey = resource.gvar
        if gkey not in gconf:
            logger.error('Key %s unknown in cycle %s', gkey, self.genv)
            raise Exception('Unknow gvar ' + gkey)
        return gconf[gkey] + resource.basename(self.realkind)
