#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import os

import footprints

from vortex.data.providers  import Provider
from vortex.util.config     import GenericConfigParser
from vortex.syntax.stdattrs import a_suite, member, namespacefp

from gco.data.providers import GEnv

from common.tools.igastuff import IgakeyFactoryInline

import iga.util.bpnames as bp

#: No automatic export
__all__ = []

logger = footprints.loggers.getLogger(__name__)

#: TODO move in config file
ATM_LIST_ONE = {'antiguy', 'arome', 'aromepi', 'arpege', 'caledonie', 'aromeaefr',
                'polynesie', 'restart_cep', 'reunion', 'ssmice', 'varpack', 'mfwam'}

#: TODO move in config file
ATM_LIST_TWO = {'perle_arp', 'perle_ifs', 'perle_arom', 'ctbto', 'mocchim', 'mocvolc'}


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


class IgaProvider(Provider):
    """
    Provider to inline-disk resources handled by the current operations system.
    These resources are not yet part of the Vortex scope, so some specific mapping
    needs to be done. This is provided through a dedicated ini file.
    """

    _footprint = [
        namespacefp,
        member,
        dict(
            info = 'Iga job provider',
            attr = dict(
                namespace = dict(
                    default  = '[suite].inline.fr',
                    values   = ['oper.inline.fr', 'dble.inline.fr', 'dbl.inline.fr',
                                'test.inline.fr', 'mirr.inline.fr', 'miroir.inline.fr'],
                    remap    = {
                        'dbl.inline.fr': 'dble.inline.fr',
                        'miroir.inline.fr': 'mirr.inline.fr'
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
                igakey = dict(
                    type     = IgakeyFactoryInline,
                    optional = True,
                    default  = '[vapp]/[vconf]'
                ),
                config = dict(
                    type     = IgaCfgParser,
                    optional = True,
                    default  = IgaCfgParser('@iga-map-resources.ini')
                ),
            )
        )
    ]

    def __init__(self, *args, **kw):
        logger.debug('IGA job provider init %s', self.__class__)
        super(IgaProvider, self).__init__(*args, **kw)

    @property
    def realkind(self):
        return 'iga'

    def scheme(self, resource):
        """The actual scheme is the ``tube`` attribute of the current provider."""
        return self.tube

    def netloc(self, resource):
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
        # patch pour les couplages
        if ('fmt' in info and
                resource.realkind == 'boundary' and
                self.igakey != 'reunion'):
            info['fmt'] = 'fic_day'
        if not hasattr(resource, 'model') or resource.model == 'surfex':
            info['model'] = self.vapp
        self.config.setall(info)
        logger.debug('IgaProvider:pathname info %s', info)
        # patch for the pearp kind experiment
        if self.member is not None:
            suffix = 'RUN{!s}'.format(self.member)
            new_path = os.path.join(
                self.config.resolvedpath(resource, self.vapp, self.vconf),
                suffix
            )
            return new_path
        else:
            return self.config.resolvedpath(resource, self.vapp, self.vconf)


class SopranoProvider(Provider):

    _footprint = [
        namespacefp,
        dict(
            info = 'Soprano provider',
            attr = dict(
                namespace = dict(
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
                    default  = IgaCfgParser('@iga-map-resources.ini')
                )
            )
        )
    ]

    def __init__(self, *args, **kw):
        logger.debug('IGA job provider init %s', self.__class__)
        super(SopranoProvider, self).__init__(*args, **kw)

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
        return bp.global_snames(resource, self)

    def pathname(self, resource):
        """
        The actual pathname is the directly obtained from the templated ini file
        provided through the ``config`` footprint attribute.
        """
        suite_map = dict(dble='double', mirr='oper')
        info = self.pathinfo(resource)
        if self.vapp == 'arome' and self.vconf == 'pifrance':
            info['model'] = 'aromepi'
        elif self.vapp == 'arome' and self.vconf == 'aefrance':
            info['model'] = 'aromeaefr'
        else:
            info['model'] = self.vapp
        if info['model'] in ATM_LIST_ONE:
            info['level_one']   = 'modele'
            info['level_two']   = suite_map.get(self.suite, self.suite)
            info['level_three'] = info['model']
        elif info['model'] in ATM_LIST_TWO:
            info['level_one']   = 'serv'
            info['level_two']   = 'env'
            info['level_three'] = info['sys_prod']
        else:
            raise SopranoModelError('No such model: %s' % info['model'])
        logger.debug('sopranoprovider::pathname info %s', info)
        self.config.setall(info)
        return self.config.resolvedpath(resource, self.vapp, self.vconf, 'soprano')
