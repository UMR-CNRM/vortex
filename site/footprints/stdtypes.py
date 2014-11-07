#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
Special derivated builtins to be used as attributes in footprints descriptions
in order to avoid autompatic value expansion (for example).
"""

#: Automatic export
__all__ = ['FPDict', 'FPList', 'FPSet', 'FPTuple']

import copy

from . import loggers
logger = loggers.getLogger(__name__)


class FPDict(dict):
    """A dict type for FootPrints arguments (without expansion)."""
    def __hash__(self):
        return hash(tuple(self.items()))


class FPList(list):
    """A list type for FootPrints arguments (without expansion)."""

    def __init__(self, *args):
        list.__init__(self, args)

    def __hash__(self):
        return hash(tuple(self))

    def __copy__(self):
        args = self.items()
        return self.__class__(*args)

    def __deepcopy__(self, memo):
        args = copy.deepcopy(self.items())
        return self.__class__(*args)

    def items(self):
        return self[:]


class FPSet(set):
    """A set type for FootPrints arguments (without expansion)."""

    def __init__(self, *args):
        set.__init__(self, args)

    def __hash__(self):
        return hash(tuple(self))

    def __copy__(self):
        args = self.items()
        return self.__class__(*args)

    def __deepcopy__(self, memo):
        args = copy.deepcopy(self.items())
        return self.__class__(*args)

    def items(self):
        return tuple(self)


class FPTuple(tuple):
    """A tuple type for FootPrints arguments (without expansion)."""

    def __new__(cls, *args):
        return tuple.__new__(cls, args)

    def items(self):
        return list(self)
