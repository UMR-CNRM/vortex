# -*- coding: utf-8 -*-

"""
Special derivated builtins to be used as attributes in footprints descriptions
in order to avoid automatic value expansion (for example).
"""

from __future__ import print_function, absolute_import, division, unicode_literals

import copy
import re

from bronx.syntax.decorators import secure_getattr

#: Automatic export
__all__ = ['FPDict', 'FPList', 'FPSet', 'FPTuple', 'FPRegex']


class FPDict(dict):
    """A dict type for FootPrints arguments (without expansion)."""
    def __hash__(self):
        return hash(tuple(self.items()))


class FPList(list):
    """A list type for FootPrints arguments (without expansion)."""

    def __hash__(self):
        return hash(tuple(self))

    def items(self):
        """Return a list copy of internal components of the FPList."""
        return self[:]


class FPSet(set):
    """A set type for FootPrints arguments (without expansion)."""

    def __hash__(self):
        return hash(tuple(self))

    def items(self):
        """Return a tuple copy of internal components of the FPSet."""
        return tuple(self)

    def footprint_export(self):
        """A set is not jsonable so it will be converted to a list."""
        try:
            return sorted(self)
        except TypeError:
            return list(self)


class FPTuple(tuple):
    """A tuple type for FootPrints arguments (without expansion)."""

    def items(self):
        """Return a list copy of internal components of the FPTuple."""
        return list(self)


class FPRegex(object):
    """A Compiled Regex like object that can be deepcopied"""

    def __init__(self, pattern, flags=0):
        self._re = re.compile(pattern, flags=flags)

    @secure_getattr
    def __getattr__(self, name):
        return getattr(self._re, name)

    def __deepcopy__(self, memo):
        # A shallow copy is enough since self._re is not mutable
        new = copy.copy(self)
        memo[id(self)] = new
        return new

    def footprint_export(self):
        """Convert the Regex to a tuple."""
        return (self._re.pattern, self._re.flags)

    def __str__(self):
        return "FPRegex(r'{0:s}', flags={1:d})".format(self._re.pattern, self._re.flags)

    def __repr__(self):
        parent_repr = super(FPRegex, self).__repr__().rstrip('>')
        return "{0:s} | {1:s}>".format(parent_repr, str(self))
