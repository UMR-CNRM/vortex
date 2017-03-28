#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
This module provides some pre-defined attributes descriptions or combined sets
of attributes description that could be used in the footprint definition of any
class which follow the :class:`footprints.Footprint` syntax.
"""

import re
from functools import total_ordering

import footprints

#: Export some new class for attributes in footprint objects, eg : GenvKey
__all__ = [ 'GenvKey', 'GenvDomain' ]

domain_remap = dict(
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
        return str.__new__(cls, re.sub(r'\[\w+\]', _lowerattr, value.upper()))

a_gvar = dict(info            = 'The key that identifies the resource in the Genv database.',
              type            = GenvKey,
              optional        = True,
              doc_visibility  = footprints.doc.visibility.ADVANCED,
              )

#: Usual definition of the ``genv`` attribute.
gvar = footprints.Footprint(info = 'A GENV access key',
                            attr = dict(gvar = a_gvar))


class GenvDomain(str):
    """
    Remap plain area names to specific Genv short domain names.
    See also :mod:`gco.tools.genv`.
    """

    def __new__(cls, value):
        """Proxy to ``str.__new___`` with on the fly remapping of domain names to short values."""
        return str.__new__(cls, domain_remap.get(value, value))


a_gdomain = dict(info = "The resource's geographical domain name in the Genv database.",
                 type = GenvDomain,
                 optional = True,
                 default = '[geometry::area]',
                 doc_visibility  = footprints.doc.visibility.ADVANCED,)

#: Usual definition of the ``gdomain`` attribute.
gdomain = footprints.Footprint(info = 'A domain name in GCO convention',
                               attr = dict(gdomain = a_gdomain))


@total_ordering
class ArpIfsSimplifiedCycle(object):
    """
    Type that holds a simplified representation of an ArpegeIFS cycle.

    It provides basic comparison operators to determine if a given cycle is more recent or not
    compared to another one.

    It can be used in a footprint specification.
    """
    _cy_re = re.compile(r'(?:u(?:env|get):)?(?:cy|al)(\d+)(?:t(\d{1,3}))?(?=_|$)(?:.*?(?:[_-]op(\d{1,3})))?')
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
            except (ValueError, TypeError):
                return False
        return hash(self) == hash(other)

    def __gt__(self, other):
        if not isinstance(other, ArpIfsSimplifiedCycle):
            other = ArpIfsSimplifiedCycle(other)
        return hash(self) > hash(other)

    def __str__(self):
        return ('cy{:d}'.format(self._number) +
                ('t{:d}'.format(self._toulouse - 1) if self._toulouse else '') +
                ('_op{:d}'.format(self._op - 1) if self._op else ''))

    def __repr__(self):
        return '{} | {}'.format(self.__class__, str(self))

    def export_dict(self):
        """The pure dict/json output is the raw integer"""
        return str(self)


a_arpifs_cycle = dict(info     = "An Arpege/IFS cycle name",
                      type     = ArpIfsSimplifiedCycle,
                      optional = True,
                      default  = 'cy40',  # For "old" Olive configurations to keep working
                      )

#: Usual definition of the ``cycle`` attribute.
arpifs_cycle = footprints.Footprint(info = 'An abstract arpifs_cycle in GCO convention',
                                    attr = dict(cycle = a_arpifs_cycle))


uget_sloppy_id_regex = re.compile(r'(?P<shortuget>(?P<id>\S+)@(?P<location>\w+))')
uget_id_regex = r'(?P<fulluget>u(?:get|env):' + uget_sloppy_id_regex.pattern + ')'
uget_id_regex_only = re.compile('^' + uget_id_regex + '$')
uget_id_regex = re.compile(r'\b' + uget_id_regex + r'\b')


class GgetId(str):
    """Basestring wrapper for Gget Ids."""
    def __new__(cls, value):
        if uget_id_regex_only.match(value):
            raise ValueError('A GgetId cannot look like a UgetId !')
        return str.__new__(cls, value)


class UgetId(str):
    """Basestring wrapper for Uget Ids."""

    def __new__(cls, value):
        vmatch = uget_id_regex_only.match(value)
        if not vmatch:
            raise ValueError('Invalid UgetId (got "{:s}")'.format(value))
        me = str.__new__(cls, value)
        me._id = vmatch.group('id')
        me._location = vmatch.group('location')
        return me

    @property
    def id(self):
        return self._id

    @property
    def location(self):
        return self._location

    @property
    def short(self):
        return self._id + '@' + self._location
