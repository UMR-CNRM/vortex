#!/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []


import re

import footprints

from vortex.autolog import logdefault as logger
from vortex.tools.env import Environment


class Glove(footprints.FootprintBase):
    """Base class for GLObal Versatile Environment."""

    _abstract  = True
    _collector = ('glove',)
    _footprint = dict(
        info = 'Abstract glove',
        attr = dict(
            email = dict(
                alias    = ['address'],
                optional = True,
                default  = Environment(active=False)['email'],
                access   = 'rwx',
            ),
            vapp = dict(
                optional = True,
                default  = 'play',
                access   = 'rwx',
            ),
            vconf = dict(
                optional = True,
                default  = 'sandbox',
                access   = 'rwx',
            ),
            tag = dict(
                optional = True,
                default  = 'default',
            ),
            user = dict(
                alias    = ('logname', 'username'),
                optional = True,
                default  = Environment(active=False)['logname']
            ),
            profile = dict(
                alias    = ('kind', 'membership'),
                values   = ['oper', 'dble', 'test', 'research', 'tourist'],
                remap    = dict(tourist = 'research')
            )
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Glove abstract %s init', self.__class__)
        super(Glove, self).__init__(*args, **kw)
        self._rmdepthmin = 3
        self._siteroot   = None
        self._siteconf   = None
        self._sitedoc    = None
        self._sitesrc    = None

    @property
    def realkind(self):
        """Returns the litteral string identity of the current glove."""
        return 'glove'

    @property
    def configrc(self):
        """Returns the path of the default directory where ``.ini`` files are stored."""
        return Environment(active=False).HOME + '/.vortexrc'

    @property
    def siteroot(self):
        """Returns the path of the vortex install directory."""
        if not self._siteroot:
            self._siteroot = '/'.join(__file__.split('/')[0:-3])
        return self._siteroot

    @property
    def siteconf(self):
        """Returns the path of the default directory where ``.ini`` files are stored."""
        if not self._siteconf:
            self._siteconf = '/'.join((self.siteroot, 'conf'))
        return self._siteconf

    @property
    def sitedoc(self):
        """Returns the path of the default directory where ``.ini`` files are stored."""
        if not self._sitedoc:
            self._sitedoc = '/'.join((self.siteroot, 'sphinx'))
        return self._sitedoc

    @property
    def sitesrc(self):
        """Returns the path of the default directory where ``.ini`` files are stored."""
        if not self._sitesrc:
            self._sitesrc = '/'.join((self.siteroot, 'src'))
        return self._sitesrc

    def setenv(self, app=None, conf=None):
        """Change ``vapp`` or/and ``vconf`` in one call."""
        if app is not None:
            self.vapp = app
        if conf is not None:
            self.vconf = conf
        return (self.vapp, self.vconf)

    def setmail(self, domain=None):
        """Refresh actual email with current username and provided ``domain``."""
        if domain is None:
            from vortex import sessions
            domain = sessions.system().getfqdn()
        self.email = '@'.join((self.user, domain))

    @property
    def xmail(self):
        if self.email is None:
            self.setmail()
        return self.email

    def safedirs(self):
        """Protected paths as a list a tuples (path, depth)."""
        e = Environment(active=False)
        return [ (e.HOME, 2), (e.TMPDIR, 1) ]

    def idcard(self):
        """Returns a printable description of the current glove."""
        indent = ''
        card = "\n".join((
            '{0}User     : {1:s}',
            '{0}Profile  : {2:s}',
            '{0}Vapp     : {3:s}',
            '{0}Vconf    : {4:s}',
            '{0}Configrc : {5:s}'
        )).format(
            indent,
            self.user, str(self.profile), self.vapp, self.vconf, self.configrc
        )
        return card


class ResearchGlove(Glove):
    """
    The default glove as long as you do not need operational privileges.
    Optional arguments are:

    * mail
    * profile (default is research)
    """

    _footprint = dict(
        info = 'Research glove',
        attr = dict(
            profile = dict(
                optional = True,
                default  = 'research',
            )
        )
    )

    @property
    def realkind(self):
        return 'research'


class OperGlove(Glove):
    """
    The default glove if you need operational privileges.
    Mandatory arguments are:

    * user
    * profile
    """

    _footprint = dict(
        info = 'Operational glove',
        attr = dict(
            user = dict(
                values   = ['mxpt001']
            ),
            profile = dict(
                optional = False,
            )
        )
    )

    @property
    def realkind(self):
        return 'opuser'

