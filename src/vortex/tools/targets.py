#!/bin/env python
# -*- coding:Utf-8 -*-

"""
This package handles target computers objects that could in charge of
hosting a specific execution. The associated modules defines the catalog
factory based on the shared footprint mechanism.
"""

#: No automatic export
__all__ = []

import re, sys, platform

import footprints

from vortex.autolog import logdefault as logger
from vortex.tools.config import GenericConfigParser
from vortex.utilities.catalogs import ClassesCollector, build_catalog_functions


class Target(footprints.BFootprint):
    """Root class for any :class:`Target` subclasses."""

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


class TargetsCatalog(ClassesCollector):
    """Class in charge of collecting :class:`Target` items."""

    def __init__(self, **kw):
        """
        Define defaults regular expresion for module search, list of tracked classes
        and the item entry name in pickled footprint resolution.
        """
        logger.debug('Target computers catalog init %s', self)
        cat = dict(
            remod = re.compile(r'.*\.targets'),
            classes = [ Target ],
            itementry = 'target'
        )
        cat.update(kw)
        super(TargetsCatalog, self).__init__(**cat)

    @classmethod
    def tablekey(cls):
        """The entry point for global catalogs table. -- Here: targets."""
        return 'targets'


build_catalog_functions(sys.modules.get(__name__), TargetsCatalog)
