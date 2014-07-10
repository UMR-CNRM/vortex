#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module provides some pre-defined attributes descriptions or combined sets
of attributes description that could be used in the footprint definition of any
class which follow the :class:`footprints.Footprint` syntax.
"""

import footprints

from vortex.tools.date import Date, Time, Month

#: Export a set of attributes :data:`a_model`, :data:`a_date`, etc..
__all__ = [
    'a_month', 'a_domain', 'a_truncation', 'a_model', 'a_date', 'a_cutoff', 'a_term',
    'a_nativefmt', 'a_actualfmt', 'a_suite'
]

#: Default values for atmospheric models.
models = set(['arpege', 'arp', 'aladin', 'ald', 'arome', 'aro',
              'aearp', 'pearp', 'mocage', 'mesonh'])

#: Default values for the most common binaries.
binaries = set(['arpege', 'aladin', 'arome', 'peace', 'mocage', 'mesonh'])

#: Default attributes excluded from `repr` display
notinrepr = set(['kind', 'unknown', 'clscontents', 'gvar', 'nativefmt'])

#: Known formats
knownfmt = set([
    'auto', 'autoconfig', 'unknown', 'foo',
    'ascii', 'txt', 'fa', 'lfi', 'lfa', 'netcdf', 'grib',
    'bufr', 'obsoul', 'odb', 'ecma', 'ccma',
    'bullx', 'sx'
])


class FmtInt(int):
    """Formated integer."""

    def __new__(cls, value, fmt='02'):
        obj = int.__new__(cls, value)
        obj._fmt = fmt
        return obj

    def __str__(self):
        return '{0:{fmt}d}'.format(self.__int__(), fmt=self._fmt)

    def nice(self, value):
        """Returns the specified ``value`` with the format of the current object."""
        return '{0:{fmt}d}'.format(value, fmt=self._fmt)


#: Usual definition of the ``nativefmt`` attribute.
a_nativefmt = dict(
    optional = True,
    default = 'foo',
    values = knownfmt,
    remap = dict(auto = 'foo'),
)

nativefmt = footprints.Footprint( info = 'Native format', attr = dict( nativefmt = a_nativefmt ) )

#: Usual definition of the ``actualfmt`` attribute.
a_actualfmt = dict(
    optional = True,
    default = '[nativefmt#unknown]',
    alias = ('format',),
    values = knownfmt,
    remap = dict(auto = 'foo'),
)

actualfmt = footprints.Footprint( info = 'Actual data format', attr = dict( actualfmt = a_actualfmt ) )

#: Usual definition of the ``cutoff`` attribute.
a_cutoff = dict(
    type = str,
    optional = False,
    alias = ('cut',),
    values = [
        'a', 'assim', 'assimilation', 'long',
        'p', 'prod', 'production', 'short'
    ],
    remap = dict(
        a = 'assim',
        p = 'production',
        prod = 'production',
        long = 'assim',
        assimilation = 'assim'
    )
)

cutoff = footprints.Footprint( info = 'Abstract cutoff', attr = dict( cutoff = a_cutoff ) )

#: Usual definition of the ``model`` attribute.
a_model = dict(
    type = str,
    optional = False,
    values = models,
    remap = dict(
        arp = 'arpege',
        ald = 'aladin',
        aro = 'arome'
    ),
    alias = ( 'engine', 'turtle' )
)

model = footprints.Footprint( info = 'Abstract model', attr = dict( model = a_model ) )

#: Usual definition of the ``date`` attribute.
a_date = dict(
    type = Date,
    optional = False,
)

date = footprints.Footprint( info = 'Abstract date', attr = dict( date = a_date ) )

#: Usual definition of the ``month`` attribute.
a_month = dict(
    type = Month,
    args = dict(year=0),
    optional = False,
    values = range(1, 13)
)

month = footprints.Footprint( info = 'Abstract month', attr = dict( month = a_month ) )

#: Usual definition of the ``truncation`` attribute.
a_truncation = dict(
    type = int,
    optional = False,
)

truncation = footprints.Footprint( info = 'Abstract truncation', attr = dict( truncation = a_truncation ) )

#: Usual definition of the ``domain`` attribute.
a_domain = dict(
    type = str,
    optional = False,
)

domain = footprints.Footprint( info = 'Abstract domain', attr = dict( domain = a_domain ) )

#: Usual definition of the ``term`` attribute.
a_term = dict(
    type = Time,
    optional = False,
)

term = footprints.Footprint( info = 'Abstract term', attr = dict( term = a_term ) )

#: Usual definition of operational suite
a_suite = dict(
    values = [ 'oper', 'dble', 'dbl', 'test' ],
    remap = dict(
        dbl = 'dble'
    )
)


def show():
    """Returns available items and their type."""
    dmod = globals()
    for stda in sorted(filter(lambda x: x.startswith('a_') or type(dmod[x]) == footprints.Footprint, dmod.keys())):
        print '{0} ( {1} ) :\n  {2}\n'.format(stda, type(dmod[stda]).__name__, dmod[stda])
