#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module provides some pre-defined attributes descriptions or combined sets
of attributes description that could be used in the footprint definition of any
class which follow the :class:`footprints.Footprint` syntax.
"""

import copy
import re

import footprints

from vortex.tools import env
from vortex.tools.date import Date, Time, Month
from bronx.system import hash as hashutils


#: Export a set of attributes :data:`a_model`, :data:`a_date`, etc..
__all__ = [
    'a_month', 'a_domain', 'a_truncation', 'a_model', 'a_date', 'a_cutoff', 'a_term',
    'a_nativefmt', 'a_actualfmt', 'a_suite'
]

#: Default values for atmospheric models.
models = set([
    'arpege', 'arp', 'arp_court', 'aladin', 'ald', 'arome', 'aro',
    'aearp', 'pearp', 'mocage', 'mesonh', 'surfex', 'hycom', 'psy4',
    'safran', 'ifs',
])

#: Default values for the most common binaries.
binaries  = set(['arpege', 'aladin', 'arome', 'batodb', 'peace', 'mocage', 'mesonh', 'safran'])
utilities = set(['batodb'])

#: Default attributes excluded from `repr` display
notinrepr = set(['kind', 'unknown', 'clscontents', 'gvar', 'nativefmt'])

#: Known formats
knownfmt = set([
    'auto', 'autoconfig', 'unknown', 'foo', 'arpifslist',
    'ascii', 'txt', 'json', 'fa', 'lfi', 'lfa', 'netcdf', 'grib',
    'bufr', 'hdf5', 'obsoul', 'odb', 'ecma', 'ccma',
    'bullx', 'sx', 'ddhpack', 'tar', 'rawfiles', 'binary', 'bin',
    'obslocationpack', 'geo',
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

    def as_dump(self):
        return 'varname={},default={}'.format(self.varname, self.default)

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


class DelayedInit(object):
    """
    Delays the proxied object creation until it's actually accessed.
    """

    def __init__(self, proxied, initializer):
        self.__proxied = proxied
        self.__initializer = initializer

    def __getattr__(self, name):
        if self.__proxied is None:
            self.__proxied = self.__initializer()
        return getattr(self.__proxied, name)

    def __repr__(self):
        orig = re.sub('^<(.*)>$', r'\1', super(DelayedInit, self).__repr__())
        return '<{:s} | proxied={:s}>'.format(orig,
                                              'Not yet Initialised' if self.__proxied is None
                                              else repr(self.__proxied))

    def __str__(self):
        return repr(self) if self.__proxied is None else str(self.__proxied)


class FmtInt(int):
    """Formated integer."""

    def __new__(cls, value, fmt='02'):
        obj = int.__new__(cls, value)
        obj._fmt = fmt
        return obj

    def __str__(self):
        return '{0:{fmt}d}'.format(self.__int__(), fmt=self._fmt)

    def export_dict(self):
        """The pure dict/json output is the raw integer"""
        return int(self)

    def nice(self, value):
        """Returns the specified ``value`` with the format of the current object."""
        return '{0:{fmt}d}'.format(value, fmt=self._fmt)


class XPid(str):
    """Basestring wrapper for experiment ids (abstract)."""
    pass


class LegacyXPid(XPid):
    """Basestring wrapper for experiment ids (Olive/Oper convention)."""
    def __new__(cls, value):
        if len(value) != 4 or '@' in value:
            raise ValueError('XPid should be a 4 digits string')
        return str.__new__(cls, value.upper())

    def isoper(self):
        """Return true if current value looks like an op id."""
        return str(self) in opsuites


class FreeXPid(XPid):
    """Basestring wrapper for experiment ids (User defined)."""

    _re_valid = re.compile(r'^\w+@\w+$')

    def __new__(cls, value):
        if not cls._re_valid.match(value):
            raise ValueError('XPid should be something like "id@location" (not "{:s}")'
                             .format(value))
        return str.__new__(cls, value)

    @property
    def id(self):
        return self.split('@')[0]

    @property
    def location(self):
        return self.split('@')[1]


#: Default values for operational experiment names.
opsuites = set([LegacyXPid(x) for x in (['OPER', 'DBLE', 'TEST', 'MIRR'] +
                                        ['OP{0:02d}'.format(i) for i in range(100)])])


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
        if '.' in self.netloc:
            return self.split('.', 1)[1]
        else:
            return self.netloc

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

#: Usual definition for the ``xpid`` or experiment name.
a_xpid = dict(
    info     = "The experiment's identifier.",
    type     = XPid,
    optional = False,
)

xpid = footprints.Footprint(info = 'Abstract experiment id',
                            attr = dict(experiment = a_xpid))

#: Usual definition for an Olive/Oper ``xpid`` or experiment name.
a_legacy_xpid = copy.copy(a_xpid)
a_legacy_xpid['type'] = LegacyXPid

legacy_xpid = footprints.Footprint(info = 'Abstract experiment id',
                                   attr = dict(experiment = a_legacy_xpid))

#: Usual definition for a user-defined ``xpid`` or experiment name.
a_free_xpid = copy.copy(a_xpid)
a_free_xpid['type'] = FreeXPid

free_xpid = footprints.Footprint(info = 'Abstract experiment id',
                                 attr = dict(experiment = a_free_xpid))

#: Usual definition of the ``nativefmt`` attribute.
a_nativefmt = dict(
    info     = "The resource's storage format.",
    optional = True,
    default  = 'foo',
    values   = knownfmt,
    remap    = dict(auto = 'foo'),
)

nativefmt = footprints.Footprint(info = 'Native format', attr = dict(nativefmt = a_nativefmt))

#: Usual definition of the ``actualfmt`` attribute.
a_actualfmt = dict(
    info     = "The resource's format.",
    optional = True,
    default  = '[nativefmt#unknown]',
    alias    = ('format',),
    values   = knownfmt,
    remap    = dict(auto = 'foo'),
)

actualfmt = footprints.Footprint(info = 'Actual data format', attr = dict(actualfmt = a_actualfmt))

#: Usual definition of the ``cutoff`` attribute.
a_cutoff = dict(
    info     = "The cutoff type of the generating process.",
    type     = str,
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
    info     = "The model name (from a source code perspective).",
    type     = str,
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
    info = "The generating process run date.",
    type = Date,
    optional = False,
)

date = footprints.Footprint(info = 'Abstract date', attr = dict(date = a_date))

#: Usual definition of the ``month`` attribute.
a_month = dict(
    info     = "The generating process run month.",
    type     = Month,
    args     = dict(year=0),
    optional = False,
    values   = range(1, 13)
)

month = footprints.Footprint(info = 'Abstract month', attr = dict(month = a_month))

#: Usual definition of the ``truncation`` attribute.
a_truncation = dict(
    info     = "The resource's truncation.",
    type     = int,
    optional = False,
)

truncation = footprints.Footprint(info = 'Abstract truncation', attr = dict(truncation = a_truncation))

#: Usual definition of the ``domain`` attribute.
a_domain = dict(
    info     = "The resource's geographical domain.",
    type     = str,
    optional = False,
)

domain = footprints.Footprint(info = 'Abstract domain', attr = dict(domain = a_domain ))

#: Usual definition of the ``term`` attribute.
a_term = dict(
    info     = "The resource's forecast term.",
    type     = Time,
    optional = False,
)

term = footprints.Footprint(info = 'Abstract term', attr = dict(term = a_term))

#: Usual definition of operational suite
a_suite = dict(
    info   = "The operational suite identifier.",
    values = [ 'oper', 'dble', 'dbl', 'test', 'mirr', 'miroir' ],
    remap  = dict(
        dbl = 'dble',
        miroir = 'mirr',
    )
)

#: Usual definition of the ``member`` attribute
a_member = dict(
    info     = "The member's number (`None` for a deterministic configuration).",
    type     = int,
    optional = True,
)

member = footprints.Footprint(info = 'Abstract member', attr = dict(member = a_member))

#: Usual definition of the ``block`` attribute
a_block = dict(
    info     = 'The subpath where to store the data.',
)

block = footprints.Footprint(info = 'Abstract block', attr = dict(block = a_block))

#: Usual definition of the ``namespace`` attribute
a_namespace = dict(
    info     = "The namespace where to store the data.",
    type     = Namespace,
    optional = True,
)

namespacefp = footprints.Footprint(info = 'Abstract namespace',
                                   attr = dict(namespace = a_namespace))

a_hashalgo = dict(
    info = "The hash algorithm used to check data integrity",
    optional = True,
    values = [None, ],
)

hashalgo = footprints.Footprint(info = 'Abstract Hash Algo', attr = dict(storehash = a_hashalgo))

hashalgo_avail_list = hashutils.HashAdapter.algorithms()

a_compressionpipeline = dict(
    info = "The compression pipeline used for this store",
    optional = True,
)

compressionpipeline = footprints.Footprint(info = 'Abstract Compression Pipeline',
                                           attr = dict(store_compressed = a_compressionpipeline))


def show():
    """Returns available items and their type."""
    dmod = globals()
    for stda in sorted(filter(lambda x: x.startswith('a_') or type(dmod[x]) == footprints.Footprint, dmod.keys())):
        print '{0} ( {1} ) :\n  {2}\n'.format(stda, type(dmod[stda]).__name__, dmod[stda])
