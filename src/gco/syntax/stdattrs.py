#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
This module provides some pre-defined attributes descriptions or combined sets
of attributes description that could be used in the footprint definition of any
class which follow the :class:`footprints.Footprint` syntax.
"""

import re
from functools import total_ordering

#: Export some new class for attributes in footprint objects, eg : GenvKey
__all__ = [ 'GenvKey', 'GenvDomain' ]

domain_remap = dict(
    caledonie = 'NCAL'
)


def _lowerattr(matchobj):
    """Internal and technical function returning lower case value of the complete match item."""
    return matchobj.group(0).lower()


class GenvKey(str):
    """
    Attribute for a GEnv cycle name.
    Implicit attributes inside brackets are translated to lower case.
    See also :mod:`gco.tools.genv`.
    """

    def __new__(cls, value):
        """Proxy to ``str.__new___`` with attributes inside brackets translated to lower case."""
        return str.__new__(cls, re.sub('\[\w+\]', _lowerattr, value.upper()))


class GenvDomain(str):
    """
    Remap plain area names to specific Genv short domain names.
    See also :mod:`gco.tools.genv`.
    """

    def __new__(cls, value):
        """Proxy to ``str.__new___`` with on the fly remapping of domain names to short values."""
        return str.__new__(cls, domain_remap.get(value, value))


@total_ordering
class ArpIfsSimplifiedCycle(object):
    """
    Type that holds a simplified representation of an ArpegeIFS cycle.
    
    It provides basic comparison operators to determine if a given cycle is more recent or not
    compared to another one.
    
    It can be used in a footprint specification.
    """
    _cy_re = re.compile('(?:cy|al)(\d+)(?:t(\d{1,3}))?(?:_.*?(?:op(\d{1,3}))?(:?\.\d+)?)?$')
    _hash_shift = 10000

    def __init__(self, cyclestr):
        cy_match = self._cy_re.match(cyclestr)
        if cy_match:
            self._number = int(cy_match.group(1))
            self._toulouse = (int(cy_match.group(2)) + 1
                              if cy_match.group(2) is not None else 0)
            self._op = (int(cy_match.group(3)) + 1
                        if cy_match.group(3) is not None else 0)
        else:
            raise ValueError('Malformed cycle: {}'.format(cyclestr))

    def __hash__(self):
        return (self._number * self._hash_shift + self._toulouse) * self._hash_shift + self._op

    def __eq__(self, other):
        if not isinstance(other, ArpIfsSimplifiedCycle):
            try:
                other = ArpIfsSimplifiedCycle(other)
            except StandardError:
                return False
        return hash(self) == hash(other)

    def __gt__(self, other):
        if not isinstance(other, ArpIfsSimplifiedCycle):
            other = ArpIfsSimplifiedCycle(other)
        return hash(self) > hash(other)

    def __str__(self):
        return ('cy{:d}'.format(self._number) +
                ('t{:d}'.format(self._toulouse) if self._toulouse else ''),
                ('_op{:d}'.format(self._op) if self._op else ''))

    def __repr__(self):
        return '{} | {}'.format(self.__class__, str(self))
