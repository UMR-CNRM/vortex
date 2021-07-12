# -*- coding: utf-8 -*-

"""
TODO: Module documentation
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import os.path

from bronx.fancies import loggers

from vortex.syntax.stdattrs import namespacefp
from vortex.util.config import GenericConfigParser
from vortex.data.providers import Provider

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
        namespacefp,
        dict(
            info = 'ALPHA Soprano provider',
            attr = dict(
                namespace = dict(
                    values   = ['alphadev.soprano.fr'],
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

    @property
    def realkind(self):
        return 'alpha_sopranodev'

    def scheme(self, resource):  # @UnusedVariable
        """The actual scheme is the ``tube`` attribute of the current provider."""
        return self.tube

    def netloc(self, resource):  # @UnusedVariable
        """The actual netloc is the ``namespace`` attribute of the current provider."""
        return self.storage

    def basename(self, resource):
        """Generate the URI path's basename given the *resource*."""
        result = None
        if resource.realkind == 'gridpoint':
            if resource.model == 'ifs':
                if self.vapp == 'ifs' and self.vconf == 'eps':
                    result = ('cep_eps_{0.date!s}_MB{1.member:02d}_{.geometry.area}_ECH{0.term.fmth:s}.X.grb'
                              .format(resource, self))
                if self.vapp == 'ifs' and self.vconf == 'determ':
                    result = ('cep_ifs_{0.date!s}_{.geometry.area}_ECH{0.term.fmth:s}.X.grb'
                              .format(resource, self))
        if result is None:
            raise NotImplementedError('This provider is not able to handle the {!r} resource'
                                      .format(resource))
        else:
            return result

    def pathname(self, resource):
        """Generate the URI path's directory part given the *resource*.

        The actual pathname is the directly obtained using the config ini file
        provided through the ``config`` footprint attribute.
        """
        suffix = self.config.resolvedpath(self.storage)
        info = self.pathinfo(resource)
        modelmap = {('ifs', 'ifs', 'determ'): 'ifs',
                    ('ifs', 'ifs', 'eps'): 'eps', }
        path = os.path.join(suffix,
                            modelmap.get((info['model'], self.vapp, self.vconf),
                                         info['model']),
                            str(info['date']))
        return path
