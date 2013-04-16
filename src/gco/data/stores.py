#!/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

import re
from vortex.autolog import logdefault as logger
from vortex.data.stores import Store

rextract = re.compile('^extract=(.*)$')


class GStore(Store):
    """
    GCO central storage class.
    
    Extended footprint:
    
    * scheme (in values: ``gget``)
    * netloc (in values: ``gco.meteo.fr``) 
    """
    
    _footprint = dict(
        info = 'GCO Central Store',
        attr = dict(
            scheme = dict(
                values = [ 'gget' ],
            ),
            netloc = dict(
                values = [ 'gco.meteo.fr' ],
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Gco store init %s', self.__class__)
        super(GStore, self).__init__(*args, **kw)

    @classmethod
    def realkind(cls):
        """Default realkind is ``gstore``."""
        return 'gstore'

    def ggetget(self, system, remote, local):
        """System call to ``gget`` external tool."""
        rpath = remote['path']
        l = rpath.lstrip('/').split('/')
        gname = l.pop()
        tampon = '/' + '/'.join(l)
        system.env.gget_tampon = tampon
        rc = system.spawn(['gget', gname], output=False)
        if rc and system.path.exists(gname):
            extract = remote['query'].get('extract', None)
            if extract:
                logger.info('GStore get %s', gname + '/' + extract[0])
                rc = system.cp(gname + '/' + extract[0] , local)
            else:
                logger.info( 'GStore get %s', gname )
                rc = system.mv(gname, local)
        else:
            logger.warning('GStore get %s was not successful (%s)', gname, rc)
        del system.env.gget_tampon
        return rc

