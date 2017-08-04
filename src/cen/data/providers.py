#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.util.config     import GenericConfigParser
from vortex.data.providers  import Provider
from vortex.syntax.stdattrs import namespacefp, a_suite

map_suffix = {'alp':'_al', 'pyr':'_py', 'cor':'_co'}

class CenCfgParser(GenericConfigParser):

    def resolvedpath(self, resource, vapp, vconf, resname=None):
        """
        Shortcut to retrieve the ``resolvedpath`` entry in the ``resname`` section
        of the current config file.
        """
        if resname is None:
            resname = resource.realkind
        cutoff = getattr(resource, 'cutoff', None)

        extended_resname = resname + '@' + vapp

        if self.has_section(extended_resname + vconf):
            resname = extended_resname + vconf
        elif cutoff is not None and self.has_section(extended_resname + cutoff):
            resname = extended_resname + cutoff
        return self.get(resname, 'resolvedpath')


class SopranoDevProvider(Provider):

    _footprint = [
        namespacefp,
        dict(
            info = 'Soprano provider',
            attr = dict(
                namespace = dict(
                    values   = ['guppy.meteo.fr', 'dev.soprano.fr'],
                    default  = 'guppy.meteo.fr',
                    #default  = 'dev.soprano.fr'
                ),
                tube = dict(
                    optional = True,
                    values   = ['scp', 'rcp', 'ftp'],
                    default  = 'ftp'
                ),
                suite = dict(
                    optional = True,
                ),
                config = dict(
                    type     = CenCfgParser,
                    optional = True,
                    default  = CenCfgParser('@cen-map-resources.ini')
                )
            )
        )
    ]

    def __init__(self, *args, **kw):
        logger.debug('SOPRANO dev job provider init %s', self.__class__)
        super(SopranoDevProvider, self).__init__(*args, **kw)

    @property
    def realkind(self):
        return 'soprano'

    def scheme(self, resource):
        """The actual scheme is the ``tube`` attribute of the current provider."""
        return self.tube

    def netloc(self, resource):
        """The actual netloc is the ``namespace`` attribute of the current provider."""
        return self.namespace.netloc

    def basename(self, resource):
        """Use the resource basename."""
        return resource.origin_basename()

    def pathname(self, resource):
        """
        The actual pathname is the directly obtained from the templated ini file
        provided through the ``config`` footprint attribute.
        """
        info = self.pathinfo(resource)
        info['model'] = 's2m'
        info['level_one'] = self.vconf.split('@')[0]
        suffix = map_suffix[info['level_one']]
        season = resource.date.nivologyseason()
        if resource.realkind in [ 'synop', 'precipitation', 'hourlyobs']:
            info['level_two']   = 'obs/rs' + season + suffix
        elif resource.realkind == 'radiosondage':
            info['level_two']   = 'a' + season + suffix
        elif resource.realkind == 'nebulosity':
            info['level_two']   = 'neb/n' + season + suffix
        elif resource.realkind == 'guess':
            info['level_two']   = 'p' + season + suffix
        elif resource.realkind == 'prep':
            info['level_two']   = 'prep' + season + suffix
        
        info['level_three'] = resource.date.ymd           
 
        logger.debug('sopranodevprovider::pathname info %s', info)
        self.config.setall(info)
        return self.config.resolvedpath(resource, self.vapp, self.vconf, 'guppy')


