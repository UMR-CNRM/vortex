#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
This package handles targets computers objects that could in charge of
hosting a specific execution.Target objects use the :mod:`footprints` mechanism.
"""

#: No automatic export
__all__ = []

import re
import platform

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.util.config import GenericConfigParser
from vortex import sessions


class Target(footprints.FootprintBase):
    """Root class for any :class:`Target` subclasses.

    Target classes are used to define specific settings and/or behaviour for a
    given host (*e.g.* your own workstation) or group of hosts (*e.g.* each of
    the nodes of a cluster).

    Through the :meth:`get` method, it gives access to the **Target**'s specific
    configuration file (``target-[hostname].ini`` by default).
    """

    _abstract  = True
    _explicit  = False
    _collector = ('target',)
    _footprint = dict(
        info = 'Default target description',
        attr = dict(
            hostname = dict(
                optional = True,
                default  = platform.node(),
                alias    = ('nodename', 'computer')
            ),
            inetname = dict(
                optional = True,
                default  = platform.node(),
            ),
            sysname = dict(
                optional = True,
                default  = platform.system(),
            ),
            config = dict(
                type     = GenericConfigParser,
                optional = True,
                default  = None,
            ),
            inifile = dict(
                optional = True,
                default  = 'target-[hostname].ini',
            ),
            iniauto = dict(
                type     = bool,
                optional = True,
                default  = True,
            )
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Abstract target computer init %s', self.__class__)
        super(Target, self).__init__(*args, **kw)
        if not self.config:
            self._attributes['config'] = GenericConfigParser(inifile=self.inifile, mkforce=self.iniauto)

    @property
    def realkind(self):
        return 'target'

    def generic(self):
        """Generic name is inetname by default."""
        return self.inetname

    def get(self, key, default=None):
        """Get the actual value of the specified ``key`` ( ``section:option`` ).

        Sections of the configuration file may be overwritten with sections
        specific to a given user's group (identified by the Glove's realkind
        property).

        :example:
        Let's consider a user with the *opuser* Glove's realkind and the
        following configuration file::

            [sectionname]
            myoption = generic
            [sectionname@opuser]
            myoption = operations

        The :meth:`get` method called whith ``key='sectionname:myoption'`` will
        return 'operations'.
        """
        my_glove_rk = '@' + sessions.current().glove.realkind
        glove_rk_id = re.compile(r'^.*@\w+$')
        if ':' in key:
            section, option = [ x.strip() for x in key.split(':', 1) ]
            # Check if an override section exists
            sections = [ x for x in (section + my_glove_rk, section)
                         if x in self.config.sections() ]
        else:
            option = key
            # First look in override sections, then in default one
            sections = ([ s for s in self.config.sections() if s.endswith(my_glove_rk) ] +
                        [ s for s in self.config.sections() if not glove_rk_id.match(s) ])
        # Return the first matching section/option
        for section in [ x for x in sections if self.config.has_option(x, option) ]:
            return self.config.get(section, option)
        return default

    @classmethod
    def is_anonymous(cls):
        """Return a boolean either the current footprint define or not a mandatory set of hostname values."""
        fp = cls.footprint_retrieve()
        return not bool(fp.attr['hostname']['values'])

    def spawn_hook(self, sh):
        """Specific target hook before any serious execution."""
        pass


class LocalTarget(Target):
    """A very generic class usable for most of the computers."""

    _footprint = dict(
        info = 'Nice local target',
        attr = dict(
            sysname = dict(
                values = [ 'Linux', 'Darwin', 'Local', 'Localhost' ]
            ),
        )
    )

