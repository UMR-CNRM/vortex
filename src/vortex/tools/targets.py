#!/bin/env python
# -*- coding:Utf-8 -*-

"""
This package handles target computers objects that could in charge of
hosting a specific execution.Target objects use the :mod:`footprints` mechanism.
"""

#: No automatic export
__all__ = []

import re, platform

import footprints

from vortex.autolog import logdefault as logger
from vortex.tools.config import GenericConfigParser


class Target(footprints.FootprintBase):
    """Root class for any :class:`Target` subclasses."""

    _abstract  = True
    _collector = ('target',)
    _footprint = dict(
        info = 'Default target description',
        attr = dict(
            hostname = dict(
                optional = True,
                default = platform.node(),
                alias = ('nodename', 'computer')
            ),
            sysname = dict(
                optional = True,
                default = platform.system(),
            ),
            config = dict(
                optional = True,
                default = None,
                type = GenericConfigParser,
            ),
            inifile = dict(
                optional = True,
                default = 'target-[hostname].ini',
            ),
            iniauto = dict(
                optional = True,
                type = bool,
                default = True,
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

    def get(self, key, default=None):
        """Get the actual value of the specified ``key`` ( ``section:option`` )."""
        if re.search(':', key):
            section, option = key.split(':', 1)
            if self.config.has_option(section, option):
                return self.config.get(section, option)
            else:
                return default
        else:
            for section in [ x for x in self.config.sections() if self.config.has_option(x, key) ]:
                return self.config.get(section, key)
            return default


class LocalTarget(Target):

    _footprint = dict(
        info = 'Nice local target',
        attr = dict(
            sysname = dict(
                values = [ 'Linux', 'Darwin', 'Local', 'Localhost' ]
            ),
        )
    )

