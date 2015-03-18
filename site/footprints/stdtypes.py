#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
Special derivated builtins to be used as attributes in footprints descriptions
in order to avoid autompatic value expansion (for example).
"""

#: Automatic export
__all__ = ['FPDict', 'FPList', 'FPSet', 'FPTuple']

from . import loggers
logger = loggers.getLogger(__name__)


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


class FPTuple(tuple):
    """A tuple type for FootPrints arguments (without expansion)."""

    def items(self):
        """Return a list copy of internal components of the FPTuple."""
        return list(self)
