#!/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import os
from vortex.autolog import logdefault as logger

from vortex.data.providers import Provider
from vortex.tools.config import GenericConfigParser
from vortex.syntax.stdattrs import a_suite
#from iga.utilities.loggers import MyLogger
from iga.utilities import bpnames as bp


ATM_LIST_ONE = ['antiguy', 'arome', 'arpege', 'caledonie', 'polynesie',
                'restart_cep', 'reunion', 'ssmice', 'varpack']

ATM_LIST_TWO = ['perle_arp', 'perle_ifs', 'perle_arom', 'ctbto', 'mocchim',
                'mocvolc']

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
                default = '[suite].inline.fr',
                values = [ 'oper.inline.fr', 'dble.inline.fr', 'dbl.inline.fr', 'test.inline.fr' ],
                remap = {
                    'dbl.inline.fr' : 'dble.inline.fr'
                },
            ),
            tube = dict(
                optional = True,
                values = [ 'scp', 'rcp', 'file' ],
                default = 'file'
            ),
            suite = a_suite,
            source = dict(
                values = [ 'arpege', 'arome' ],
                optional = True
            ),
            member = dict(
                type = int,
                optional = True,
            ),
            igakey = dict(),
            config = dict(
                type = IgaCfgParser,
                optional = True,
                default = IgaCfgParser('iga-map-resources.ini')
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('IGA job provider init %s', self)
        super(IgaProvider, self).__init__(*args, **kw)
        self._listOfLoggers = []
        self._post = 'initialisation du provider iga'
        #self.register(self.logger)
        #self.notifyAll()

    @property
    def realkind(self):
        return 'iga'

    def scheme(self):
        """The actual scheme is the ``tube`` attribute of the current provider."""
        return self.tube

    def domain(self):
        """The actual domain is the ``namespace`` attribute of the current provider."""
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
            "fmt" in info and
            resource.realkind == 'boundary' and
            self.igakey != 'reunion'
        ):
            info['fmt'] = 'fic_day'
        self.config.setall(info)
        self.writeNewPost('IgaProvider:pathname info %s' % info)
        self.notifyAll()
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

    def register(self, alogger):
        """docstring for register"""
        if alogger not in self._listOfLoggers:
            self._listOfLoggers.append(alogger)

    def unregister(self, alogger):
        """docstring for unregister"""
        self._listOfLoggers.remove(alogger)

    def notifyAll(self):
        """docstring for notifyAll"""
        for obs in self._listOfLoggers:
            obs.notify(self._post)

    def writeNewPost(self, message):
        """docstring for writeNewPost"""
        self._post = message
        self.notifyAll()


class SopranoProvider(Provider):
    _footprint = dict(
        info = 'Soprano provider',
        attr = dict(
            namespace = dict(
                optional = True,
                values = [ 'prod.inline.fr', 'intgr.inline.fr' ],
                default = 'prod.inline.fr'
            ),
            tube = dict(
                optional = True,
                values = [ 'scp', 'rcp', 'ftp' ],
                default = 'ftp'
            ),
            suite = a_suite,
            source = dict(
                values = ATM_LIST_ONE + ATM_LIST_TWO,
                optional = True
            ),
            config = dict(
                type = IgaCfgParser,
                optional = True,
                default = IgaCfgParser('iga-map-resources.ini')
            )
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('IGA job provider init %s', self)
        super(SopranoProvider, self).__init__(*args, **kw)

    @property
    def realkind(self):
        return 'soprano'

    def scheme(self):
        """The actual scheme is the ``tube`` attribute of the current provider."""
        return self.tube

    def domain(self):
        """The actual domain is the ``namespace`` attribute of the current provider."""
        return self.namespace

    def basename(self, resource):
        return bp.global_snames(resource)

    def pathname(self, resource):
        """
        The actual pathname is the directly obtained from the templated ini file
        provided through the ``config`` footprint attribute.
        """
        info = self.pathinfo(resource)
        info['model'] = self.vapp
        if info['model'] in ATM_LIST_ONE:
            info['level_three'] = info['model']
            info['level_two'] = self.suite
        elif info['model'] in ATM_LIST_TWO:
            info['level_one'] = 'serv'
            info['level_two'] = 'env'
            info['level_three'] = info['sys_prod']
        logger.debug('sopranoprovider::pathname info %s', info)
        self.config.setall(info)
        return self.config.resolvedpath('soprano')

