#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module provides some pre-defined attributes descriptions or combined sets
of attributes description that could be used in the footprint definition of any
class which follow the :class:`footprints.Footprint` syntax.
"""

import footprints

from vortex.tools import env
from vortex.tools.date import Date, Time, Month


#: Export a set of attributes :data:`a_model`, :data:`a_date`, etc..
__all__ = [
    'a_month', 'a_domain', 'a_truncation', 'a_model', 'a_date', 'a_cutoff', 'a_term',
    'a_nativefmt', 'a_actualfmt', 'a_suite'
]

#: Default values for atmospheric models.
models = set([
    'arpege', 'arp', 'arp_court', 'aladin', 'ald', 'arome', 'aro',
    'aearp', 'pearp', 'mocage', 'mesonh', 'surfex'
])

#: Default values for the most common binaries.
binaries  = set(['arpege', 'aladin', 'arome', 'batodb', 'peace', 'mocage', 'mesonh'])
utilities = set(['batodb'])

#: Default attributes excluded from `repr` display
notinrepr = set(['kind', 'unknown', 'clscontents', 'gvar', 'nativefmt'])

#: Known formats
knownfmt = set([
    'auto', 'autoconfig', 'unknown', 'foo',
    'ascii', 'txt', 'fa', 'lfi', 'lfa', 'netcdf', 'grib',
    'bufr', 'obsoul', 'odb', 'ecma', 'ccma',
    'bullx', 'sx'
])

# Special classes

class DelayedEnvValue(object):
    """
    Store a environment variable and restitue value when needed,
    eg. in a footprint evaluation.
    """

    def __init__(self, varname, default=None, refresh=False):
        self.varname = varname
        self.default = default
        self.refresh = refresh
        self._value  = None
        self._frozen = False

    def footprint_value(self):
        """
        Return the actual env value of the ``varname`` variable.
        Optional argument ``refresh`` set to ``True`` do not store this value.
        """
        if not self._frozen:
            self._value = env.current().get(self.varname, self.default)
            if not self.refresh:
                self._frozen = True
        return self._value

    def export_dict(self):
        """The pure dict/json value is the actual value."""
        return self.footprint_value()


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


class XPid(str):
    """Basestring wrapper for experiment ids."""
    def __new__(cls, value):
        if len(value) != 4:
            raise ValueError('XPid should be a 4 digits string')
        return str.__new__(cls, value.upper())

    def isoper(self):
        """Return true if current value looks like an op id."""
        return str(self) in opsuites

#: Default values for operational experiment names.
opsuites = set([ XPid(x) for x in ['OPER', 'DBLE', 'TEST'] + [ 'OP{0:02d}'.format(i) for i in range(100) ] ])


class Namespace(str):
    """Basestring wrapper for namespaces (as net domains)."""
    def __new__(cls, value):
        value = value.lower()
        full = value
        if '@' in value:
            netuser, value = value.split('@')
            if ':' in netuser:
                netuser, netpass = netuser.split(':')
            else:
                netpass = None
        else:
            netuser, netpass = None, None
        if ':' in value:
            value, port = value.split(':')
        else:
            port = None
        if 0 < value.count('.') < 2:
            raise ValueError('Namespace should contain one or at least 3 fields')
        thisns = str.__new__(cls, value)
        thisns._port = int(port) if port else None
        thisns._user = netuser
        thisns._pass = netpass
        thisns._full = full
        return thisns

    @property
    def firstname(self):
        return self.split('.', 1)[0]

    @property
    def domain(self):
        return self.split('.', 1)[1]

    @property
    def netuser(self):
        return self._user

    @property
    def netpass(self):
        return self._pass

    @property
    def netport(self):
        return self._port

    @property
    def netloc(self):
        return self._full


# predefined attributes

#: Usal definition fo the ``xpid`` or experiment name.

a_xpid = dict(
    type     = XPid,
    optional = False,
)

xpid = footprints.Footprint(info = 'Abstract experiment id', attr = dict(experiment = a_xpid))

#: Usual definition of the ``nativefmt`` attribute.
a_nativefmt = dict(
    optional = True,
    default  = 'foo',
    values   = knownfmt,
    remap    = dict(auto = 'foo'),
)

nativefmt = footprints.Footprint(info = 'Native format', attr = dict(nativefmt = a_nativefmt))

#: Usual definition of the ``actualfmt`` attribute.
a_actualfmt = dict(
    optional = True,
    default  = '[nativefmt#unknown]',
    alias    = ('format',),
    values   = knownfmt,
    remap    = dict(auto = 'foo'),
)

actualfmt = footprints.Footprint(info = 'Actual data format', attr = dict(actualfmt = a_actualfmt))

#: Usual definition of the ``cutoff`` attribute.
a_cutoff = dict(
    type = str,
    optional = False,
    alias    = ('cut',),
    values   = [
        'a', 'assim', 'assimilation', 'long',
        'p', 'prod', 'production', 'short'
    ],
    remap    = dict(
        a = 'assim',
        p = 'production',
        prod = 'production',
        long = 'assim',
        assimilation = 'assim'
    )
)

cutoff = footprints.Footprint(info = 'Abstract cutoff', attr = dict(cutoff = a_cutoff))

#: Usual definition of the ``model`` attribute.
a_model = dict(
    type = str,
    alias    = ('engine', 'turtle'),
    optional = False,
    values   = models,
    remap    = dict(
        arp = 'arpege',
        ald = 'aladin',
        aro = 'arome'
    ),
)

model = footprints.Footprint(info = 'Abstract model', attr = dict(model = a_model))

#: Usual definition of the ``date`` attribute.
a_date = dict(
    type = Date,
    optional = False,
)

date = footprints.Footprint(info = 'Abstract date', attr = dict(date = a_date))

#: Usual definition of the ``month`` attribute.
a_month = dict(
    type     = Month,
    args     = dict(year=0),
    optional = False,
    values   = range(1, 13)
)

month = footprints.Footprint(info = 'Abstract month', attr = dict(month = a_month))

#: Usual definition of the ``truncation`` attribute.
a_truncation = dict(
    type     = int,
    optional = False,
)

truncation = footprints.Footprint(info = 'Abstract truncation', attr = dict(truncation = a_truncation))

#: Usual definition of the ``domain`` attribute.
a_domain = dict(
    type     = str,
    optional = False,
)

domain = footprints.Footprint(info = 'Abstract domain', attr = dict(domain = a_domain ))

#: Usual definition of the ``term`` attribute.
a_term = dict(
    type     = Time,
    optional = False,
)

term = footprints.Footprint(info = 'Abstract term', attr = dict(term = a_term))

#: Usual definition of operational suite
a_suite = dict(
    values = [ 'oper', 'dble', 'dbl', 'test' ],
    remap  = dict(
        dbl = 'dble'
    )
)


def show():
    """Returns available items and their type."""
    dmod = globals()
    for stda in sorted(filter(lambda x: x.startswith('a_') or type(dmod[x]) == footprints.Footprint, dmod.keys())):
        print '{0} ( {1} ) :\n  {2}\n'.format(stda, type(dmod[stda]).__name__, dmod[stda])
