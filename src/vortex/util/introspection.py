#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
Some convenient functions to explore the source code or its documentation.
"""

#: No automatic export
__all__ = []

import re
import inspect

from vortex import sessions
from vortex.autolog import logdefault as logger


class Sherlock(object):
    """Centralized interface to introspection functions."""

    def __init__(self, **kw):
        self.verbose = False
        kw.setdefault('ticket', sessions.ticket())
        kw.setdefault('glove', sessions.glove())
        self.__dict__.update(kw)
        logger.debug('Sherlock init %s', self)

    def rstfile(self, modpath):
        """Return the sphinx documentation associated to module reference or module path given."""
        if type(modpath) != str:
            modpath = modpath.__file__
        subpath = re.sub(self.glove.sitesrc, '', modpath)
        subpath = re.sub('.py', '', subpath)
        subpath = subpath.split('/')
        if subpath[-1] == '__init__':
            subpath[-1] = subpath[-2]
        subpath[-1] += '.rst'

        if subpath[1] == 'vortex' and len(subpath) == 3:
            subpath[2:2] = [ 'kernel' ]
        subpath[1:1] = [ 'library' ]
        return self.glove.sitedoc + '/'.join(subpath)

    def rstshort(self, filename):
        """Return relative path name of ``filename`` according to :meth:`siteroot`."""
        return re.sub(self.glove.siteroot, '', filename)[1:]

    def getlocalmembers(self, obj, topmodule=None):
        """Return members of the module ``m`` which are defined in the source file of the module."""
        objs = dict()
        if topmodule is None:
            topmodule = obj
        for x, y in inspect.getmembers(obj):
            if inspect.isclass(y) or inspect.isfunction(y) or inspect.ismethod(y):
                try:
                    if topmodule.__file__ == inspect.getsourcefile(y):
                        if self.verbose:
                            print x, y
                        objs[x] = y
                except TypeError:
                    pass
        return objs
