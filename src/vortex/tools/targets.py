#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
This package handles targets computers objects that could in charge of
hosting a specific execution.Target objects use the :mod:`footprints` mechanism.
"""

#: No automatic export
__all__ = []

import platform

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.util.config import GenericConfigParser


class Target(footprints.FootprintBase):
    """Root class for any :class:`Target` subclasses."""

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
        """Get the actual value of the specified ``key`` ( ``section:option`` )."""
        if ':' in key:
            section, option = [ x.strip() for x in key.split(':', 1) ]
            if self.config.has_option(section, option):
                return self.config.get(section, option)
            else:
                return default
        else:
            for section in [ x for x in self.config.sections() if self.config.has_option(x, key) ]:
                return self.config.get(section, key)
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

    _footprint = dict(
        info = 'Nice local target',
        attr = dict(
            sysname = dict(
                values = [ 'Linux', 'Darwin', 'Local', 'Localhost' ]
            ),
        )
    )

