#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Fake module for automatic import of a logger.

#: No automatic export
__all__ = []

import sys, imp
import autolog
logger = autolog.logdefault


class VortexImporter(object):
    """Import hook for modules from the install package of VORTEX."""

    def __init__(self, prefix=set([ 'vortex', 'common', 'olive', 'gco' ])):
        self._import_prefix = prefix
        logger.debug('Vortex Importer < name: %s >', self._import_prefix)

    def register(self, package):
        """Add a prefix package nam to the current set."""
        self._import_prefix.add(package)

    def unregister(self, package):
        """Discard a prefix package nam from the current set."""
        self._import_prefix.discard(package)

    @property
    def prefixes(self):
        """Return a list of the internal set of prefixes the hook applies to."""
        return list(self._import_prefix)

    def load_module(self, fullname):
        """Standard load overwritting. Set the logger value."""
        if fullname in sys.modules:
            return sys.modules[fullname]
        modname = fullname.rpartition('.')[-1]
        try:
            info = imp.find_module(modname, self.path)
            logger.debug('Vortex Module Import < name: %s %s >', fullname, str(info))
        except ImportError:
            logger.debug('Vortex Module Import < stop: %s %s>', modname, self.path)
            return None
        try:
            mod = imp.load_module(fullname, *info)
            mod.logger = autolog.logmodule(fullname)
            return mod
        finally:
            if info[0]:
                info[0].close()
        return None

    def find_module(self, fullname, path=None):
        """Standard find overwritting. Return the current loader when ``fullname`` module matchs prefixes."""
        logger.debug('Vortex Module Finder <name: %s> <path: %s>', fullname, path)
        modparts = fullname.split('.')
        if modparts and modparts[0] in self._import_prefix:
            logger.debug('Vortex Module Finder < load: %s %s >', fullname, path)
            self.path = path
            return self
        else:
            return None


sys.meta_path.append(VortexImporter())
