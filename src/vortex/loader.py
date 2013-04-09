#!/bin/env python
# -*- coding: utf-8 -*-

# Fake module for automatic import of a logger.

#: No automatic export
__all__ = []

import sys, imp
import autolog
logger = autolog.logdefault

class VortexImporter(object):

    _import_prefix = set([ 'vortex', 'common', 'olive' ])

    @classmethod
    def register(cls, package):
        cls._import_prefix.add(package)

    @classmethod
    def unregister(cls, package):
        cls._import_prefix.discard(package)

    def load_module(self, fullname):
        if fullname in sys.modules:
            return sys.modules[fullname]
        modname = fullname.rpartition('.')[-1]
        try:
            info = imp.find_module(modname, self.path)
            logger.info('Vortex Module Import < name: %s %s >', fullname, str(info))
        except ImportError:
            logger.info('Vortex Module Import < stop: %s %s>', modname, self.path)
            return None
        try:
            mod = imp.load_module(fullname, *info)
            mod.logger = autolog.logmodule(fullname)
            return mod
        finally:
            if info[0]: info[0].close()
        return None

    def find_module(self, fullname, path=None):
        logger.debug('Vortex Module Finder < name: %s >', fullname)
        logger.debug('Vortex Module Finder < path: %s >', path)
        vp = False
        for prefix in self.__class__._import_prefix:
            if fullname.startswith(prefix  + '.'):
                vp = True
                break
        if vp:
            self.path = path
            logger.info('Vortex Module Finder < load: %s %s >', fullname, path)
            return self
        return None

sys.meta_path.append(VortexImporter())