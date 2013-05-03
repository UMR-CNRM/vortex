#!/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []


import sys, re
from vortex.autolog import logdefault as logger
from vortex.syntax import BFootprint
from vortex.utilities.catalogs import ClassesCollector, cataloginterface
from vortex.tools.env import Environment


class Glove(BFootprint):
    """Base class for GLObal Versatile Environment."""

    _footprint = dict(
        info = 'Abstract glove',
        attr = dict(
            mail = dict(
                alias = [ 'address' ],
                optional = True,
                default = Environment(active=False)['email']
            ),
            tag = dict(
                optional = True,
                default = 'default',
            ),
            user = dict(
                alias = ( 'logname', 'username' ),
                optional = True,
                default = Environment(active=False)['logname']
            ),
            profile = dict(
                alias = ( 'kind', 'membership' )
            )
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Glove abstract %s init', self.__class__)
        super(Glove, self).__init__(*args, **kw)
        self._vapp = 'play'
        self._vconf = 'sandbox'
        self._rmdepthmin = 3
        self._siteroot = None
        self._siteconf = None

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

    def setvapp(self, app=None):
        """Change the default vortex application name."""
        if app:
            self._vapp = app
        return self._vapp

    def setvconf(self, conf=None):
        """Change the default vortex configuration name."""
        if conf:
            self._vconf = conf
        return self._vconf

    def setenv(self, app=None, conf=None):
        """Change ``vapp`` or/and ``vconf`` in one call."""
        self.setvapp(app)
        self.setvconf(conf)
        return ( self._vapp, self._vconf )

    @property
    def vapp(self):
        """Vortex application name."""
        return self._vapp

    @property
    def vconf(self):
        """Vortex configuration name."""
        return self._vconf

    def setmail(self, mailaddr):
        """Redefine the mail address."""
        self._attributes['mail'] = mailaddr

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
            self.user, str(self.profile), str(self.vapp), self.vconf, self.configrc
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
                default = 'research',
                values = [ 'research', 'tourist' ]
            )
        )
    )

    @property
    def realkind(self):
        return 'tourist'


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
                values = [ 'mxpt001' ]
            ),
            profile = dict(
                optional = False,
                values = [ 'oper', 'opuser', 'optest' ]
            )
        )
    )

    @property
    def realkind(self):
        return 'opuser'


class GlovesCatalog(ClassesCollector):
    """Class in charge of collecting :class:`Store` items."""

    def __init__(self, **kw):
        logger.debug('Gloves catalog init %s', self)
        cat = dict(
            remod = re.compile(r'.*\.(?:sessions|gloves)'),
            classes = [ Glove ],
            itementry = 'glove'
        )
        cat.update(kw)
        super(GlovesCatalog, self).__init__(**cat)

    @classmethod
    def tablekey(cls):
        return 'gloves'


cataloginterface(sys.modules.get(__name__), GlovesCatalog)
