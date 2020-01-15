#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

from bronx.fancies import loggers

from vortex.util.config     import GenericConfigParser
from vortex.data.providers  import Provider
from vortex.syntax.stdattrs import namespacefp
from vortex.tools.names	    import VortexNameBuilder, VortexPeriodNameBuilder
import iga.util.bpnames as bp

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)

class AlphaSopranoDevProvider(Provider):
    """
    Alpha Soprano Provider to get some files in rason.
    """


    _footprint = [
        namespacefp,
        dict(
            info = 'ALPHA Soprano provider',
            attr = dict(
                namespace = dict(
                    values   = ['alpha.soprano.fr'],
                    optional  = False,
                ),
                storage = dict(
                    values   = ['rason.meteo.fr', ],
                    optional  = False,
                ),
                tube = dict(
                    optional = True,
                    values   = ['scp', 'ftp'],
                    default  = 'ftp'
                )
            )
        )
    ]

    def __init__(self, *args, **kw):
        logger.debug('SOPRANO provider init %s', self.__class__)
        super(AlphaSopranoDevProvider, self).__init__(*args, **kw)

    @property
    def realkind(self):
        return 'alpha_sporano'

    def scheme(self, resource):
        """The actual scheme is the ``tube`` attribute of the current provider."""
        return self.tube

    def netloc(self, resource):
        """The actual netloc is the ``namespace`` attribute of the current provider."""
        return self.storage

    def basename(self, resource):
        """   """
        #return 'test.X.grb'

	binfos = resource.namebuilding_info()

	#nbuilder = VortexNameBuilder()
	#return nbuilder.pack_basename(binfos)

	return "-".join([str(k)+':'+str(v) for k,v in binfos.iteritems()])

	#nbuilder = VortexPeriodNameBuilder()
	#return nbuilder.pack_basename(binfos)


    def pathname(self, resource):
        """
        The actual pathname is the directly obtained from the templated ini file
        provided through the ``config`` footprint attribute.
        """
        return 'home/previ_amont/couixj/data/'




