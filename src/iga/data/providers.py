#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import os

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.data.providers  import Provider
from vortex.util.config     import GenericConfigParser
from vortex.syntax.stdattrs import a_suite, Namespace

from gco.data.providers import GEnv

import iga.util.bpnames as bp

#: TODO move in config file
ATM_LIST_ONE = set([
    'antiguy', 'arome', 'aromepi', 'arpege', 'caledonie', 'polynesie',
    'restart_cep', 'reunion', 'ssmice', 'varpack'
])

#: TODO move in config file
ATM_LIST_TWO = set([
    'perle_arp', 'perle_ifs', 'perle_arom',
    'ctbto', 'mocchim', 'mocvolc'
])

class SopranoModelError(ValueError):
    pass


class IgaGEnvProvider(GEnv):
    """Almost identical to base, except for the specific netloc value."""

    _footprint = dict(
        info = 'GCO provider in OP context',
        attr = dict(
            gnamespace = dict(
                values = ['opgco.cache.fr'],
                default = 'opgco.cache.fr',
            ),
        )
    )


class IgaCfgParser(GenericConfigParser):

    def resolvedpath(self, resname):
        """
        Shortcut to retrieve the ``resolvedpath`` entry in the ``resname`` section
        of the current config file.
        """
        return self.get(resname, 'resolvedpath')


class IgaProvider(Provider):
    """
    Provider to inline-disk resources handled by the current operations system.
    These resources are not yet part of the Vortex scope, so some specific mapping
    needs to be done. This is provided through a dedicated ini file.
    """

    _footprint = dict(
        info = 'Iga job provider',
        attr = dict(
            namespace = dict(
                optional = True,
                default  = '[suite].inline.fr',
                values   = ['oper.inline.fr', 'dble.inline.fr', 'dbl.inline.fr', 'test.inline.fr'],
                remap    = {
                    'dbl.inline.fr': 'dble.inline.fr'
                },
            ),
            tube = dict(
                optional = True,
                values  = ['scp', 'rcp', 'file'],
                default = 'file'
            ),
            suite = a_suite,
            source = dict(
                optional = True,
                values   = ['arpege', 'arome'],
            ),
            member = dict(
                type     = int,
                optional = True,
            ),
            igakey = dict(),
            config = dict(
                type     = IgaCfgParser,
                optional = True,
                default  = IgaCfgParser('iga-map-resources.ini')
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('IGA job provider init %s', self.__class__)
        super(IgaProvider, self).__init__(*args, **kw)

    @property
    def realkind(self):
        return 'iga'

    def scheme(self):
        """The actual scheme is the ``tube`` attribute of the current provider."""
        return self.tube

    def netloc(self):
        """The actual netloc is the ``namespace`` attribute of the current provider."""
        return self.namespace

    def basename(self, resource):
        """Use mod:`iga.utilities.bpnames` as name factory."""
        return bp.global_bnames(resource, self)

    def pathname(self, resource):
        """
        The actual pathname is the directly obtained from the templated ini file
        provided through the ``config`` footprint attribute.
        """
        info = bp.global_pnames(self, resource)
        #patch pour les couplages
        if (
            'fmt' in info and
            resource.realkind == 'boundary' and
            self.igakey != 'reunion'
        ):
            info['fmt'] = 'fic_day'
        if not hasattr(resource, 'model') or resource.model =='surfex':
            info['model'] = self.vapp
        self.config.setall(info)
        logger.debug('IgaProvider:pathname info %s', info)
        #patch for the pearp kind experiment
        if self.member:
            suffix = 'RUN' + str(self.member)
            new_path = os.path.join(
                self.config.resolvedpath(resource.realkind),
                suffix
            )
            return new_path
        else:
            return self.config.resolvedpath(resource.realkind)


class SopranoProvider(Provider):

    _footprint = dict(
        info = 'Soprano provider',
        attr = dict(
            namespace = dict(
                type     = Namespace,
                optional = True,
                values   = ['prod.soprano.fr', 'intgr.soprano.fr'],
                default  = 'prod.soprano.fr'
            ),
            tube = dict(
                optional = True,
                values   = ['scp', 'rcp', 'ftp'],
                default  = 'ftp'
            ),
            suite = a_suite,
            source = dict(
                values   = list(ATM_LIST_ONE | ATM_LIST_TWO),
                optional = True
            ),
            config = dict(
                type     = IgaCfgParser,
                optional = True,
                default  = IgaCfgParser('iga-map-resources.ini')
            )
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('IGA job provider init %s', self.__class__)
        super(SopranoProvider, self).__init__(*args, **kw)

    @property
    def realkind(self):
        return 'soprano'

    def scheme(self):
        """The actual scheme is the ``tube`` attribute of the current provider."""
        return self.tube

    def netloc(self):
        """The actual netloc is the ``namespace`` attribute of the current provider."""
        return self.namespace.netloc

    def basename(self, resource):
        return bp.global_snames(resource, self)

    def pathname(self, resource):
        """
        The actual pathname is the directly obtained from the templated ini file
        provided through the ``config`` footprint attribute.
        """
        info = self.pathinfo(resource)
        if self.vapp == 'arome' and self.vconf == 'pifrance':
            info['model'] = 'aromepi'
        else:
            info['model'] = self.vapp
        if info['model'] in ATM_LIST_ONE:
            info['level_one']   = 'modele'
            info['level_two']   = self.suite
            info['level_three'] = info['model']
        elif info['model'] in ATM_LIST_TWO:
            info['level_one']   = 'serv'
            info['level_two']   = 'env'
            info['level_three'] = info['sys_prod']
        else:
            raise SopranoModelError('No such model: %s' % info['model'])
        logger.debug('sopranoprovider::pathname info %s', info)
        self.config.setall(info)
        return self.config.resolvedpath('soprano')

