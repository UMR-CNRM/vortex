"""
Some convenient functions to explore the source code or its documentation.
"""

import re
import inspect

from bronx.fancies import loggers

from vortex import sessions

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class Sherlock:
    """Centralized interface to introspection functions."""

    def __init__(self, **kw):
        self.verbose = False
        self.ticket = kw.pop("ticket", sessions.current())
        self.glove = self.ticket.glove
        self.__dict__.update(kw)
        logger.debug("Sherlock init %s", self)

    def rstfile(self, modpath):
        """Return the sphinx documentation associated to module reference or module path given."""
        if not isinstance(modpath, str):
            modpath = modpath.__file__
        subpath = modpath
        for installpath in self.glove.sitesrc:
            subpath = re.sub(installpath, "", subpath)
        subpath = re.sub(r"\.pyc?", "", subpath)
        subpath = subpath.split("/")
        if subpath[-1] == "__init__":
            subpath[-1] = subpath[-2]
        subpath[-1] += ".rst"

        subpath[1:1] = [
            "library",
        ]
        return self.glove.sitedoc + "/".join(subpath)

    def rstshort(self, filename):
        """Return relative path name of ``filename`` according to :meth:`siteroot`."""
        return re.sub(self.glove.siteroot, "", filename)[1:]

    def getlocalmembers(self, obj, topmodule=None):
        """Return members of the module ``obj`` which are defined in the source file of the module."""
        objs = dict()
        if topmodule is None:
            topmodule = obj
        modfile = topmodule.__file__.rstrip("c")
        for x, y in inspect.getmembers(obj):
            if (
                inspect.isclass(y)
                or inspect.isfunction(y)
                or inspect.ismethod(y)
            ):
                try:
                    if modfile == inspect.getsourcefile(y):
                        if self.verbose:
                            print(x, y)
                        objs[x] = y
                except TypeError:
                    pass
        return objs
