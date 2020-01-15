#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

from bronx.fancies import loggers

from vortex.util.config     import GenericConfigParser
from vortex.data.providers  import Provider
from vortex.syntax.stdattrs import namespacefp
from vortex.tools.names	    import VortexNameBuilder, VortexPeriodNameBuilder
import iga.util.bpnames as bp
import os.path

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)

class AlphaCfgParser(GenericConfigParser):

    def resolvedpath(self, resname):
        """
        Shortcut to retrieve the ``resolvedpath`` entry in the ``resname`` section
        of the current config file.
        """
        return self.get(resname, 'resolvedpath')

class AlphaSopranoDevProvider(Provider):

    _footprint = [
        #namespacefp,
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
                ),
                config = dict(
                    type     = AlphaCfgParser,
                    optional = True,
                    default  = AlphaCfgParser('@alpha-map-resources.ini')
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

	binfos = resource.namebuilding_info()
	
	if resource.kind == 'gribSoprano':
            if resource.model == 'eps':
		#name = '_'.join([resource.model, str(resource.member), resource.date.compact(), resource.term.fmth, resource.geometry.area,'.X.grb'])
		name = '_'.join(['cep', resource.model, str(resource.date), 'MB'+str(resource.member).zfill(2), resource.geometry.area, 'ECH'+resource.term.fmth])+'.X.grb'
		return name
            elif resource.model == 'ifs':
		name = '_'.join(['cep', resource.model, str(resource.date), resource.geometry.area, 'ECH'+resource.term.fmth])+'.X.grb'
		return name
	else:
		return 'test.py'

    def pathname(self, resource):
        """
        The actual pathname is the directly obtained from the templated ini file
        provided through the ``config`` footprint attribute.
        """
        suffix=self.config.resolvedpath(self.storage)
        info = self.pathinfo(resource)
        path = os.path.join(suffix,info['model'],str(info['date']))
        return path




