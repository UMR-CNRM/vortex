#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module provides some pre-defined attributes descriptions or combined sets
of attributes description that could be used in the footprint definition of any
class which follow the :class:`footprints.Footprint` syntax.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import copy
import re
import six

from bronx.stdtypes.date import Date, Time, Month
from bronx.syntax.decorators import secure_getattr
from bronx.system import hash as hashutils
import footprints

from .stddeco import namebuilding_append, namebuilding_insert, generic_pathname_insert
from vortex.tools import env


#: Export a set of attributes :data:`a_model`, :data:`a_date`, etc..
__all__ = [
    'a_xpid', 'a_month', 'a_domain', 'a_truncation', 'a_model', 'a_member',
    'a_date', 'a_cutoff', 'a_term', 'a_nativefmt', 'a_actualfmt', 'a_suite',
    'a_namespace', 'a_hashalgo', 'a_compressionpipeline', 'a_block', 'a_number'
]

#: Possible values for the *model* attribute.
models = set([
    'arpege', 'arp', 'arp_court', 'aladin', 'ald', 'arome', 'aro',
    'aearp', 'pearp', 'mocage', 'mesonh', 'surfex', 'hycom', 'psy4',
    'safran', 'ifs', 'aroifs',
])

#: Possible values for the most common binaries.
binaries  = set(['arpege', 'aladin', 'arome', 'batodb', 'peace', 'mocage', 'sumo',
                 'corromegasurf', 'mesonh', 'safran', 'surfex', 'macc', 'mktopbd',
                 'ifs', ])
#: Possible values for the most common utility programs.
utilities = set(['batodb'])

#: Known formats
knownfmt = set([
    'auto', 'autoconfig', 'unknown', 'foo', 'arpifslist',
    'ascii', 'txt', 'json', 'fa', 'lfi', 'lfa', 'netcdf', 'grib', 'grib1', 'grib2',
    'bufr', 'hdf5', 'obsoul', 'odb', 'ecma', 'ccma',
    'bullx', 'sx', 'ddhpack', 'tar', 'rawfiles', 'binary', 'bin',
    'obslocationpack', 'obsfirepack', 'geo', 'nam', 'png', 'pdf', 'dir/hdr'
])

#: Default attributes excluded from `repr` display
notinrepr = set(['kind', 'unknown', 'clscontents', 'gvar', 'nativefmt'])


class DelayedEnvValue(object):
    """
    Store an environment variable name and compute its value when needed,
    *e.g.* in a footprint evaluation.
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
    *e.g.* in a footprint evaluation.
    """

    def __init__(self, proxied, initializer):
        self.__proxied = proxied
        self.__initializer = initializer

    @secure_getattr
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
        return repr(self) if self.__proxied is None else six.text_type(self.__proxied)


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


class XPid(six.text_type):
    """Basestring wrapper for experiment ids (abstract)."""
    pass


class LegacyXPid(XPid):
    """Basestring wrapper for experiment ids (Olive/Oper convention)."""
    def __new__(cls, value):
        if len(value) != 4 or '@' in value:
            raise ValueError('XPid should be a 4 digits string')
        return six.text_type.__new__(cls, value.upper())

    def isoper(self):
        """Return true if current value looks like an op id."""
        return six.text_type(self) in opsuites


class FreeXPid(XPid):
    """Basestring wrapper for experiment ids (User defined)."""

    _re_valid = re.compile(r'^\S+@\w+$')

    def __new__(cls, value):
        if not cls._re_valid.match(value):
            raise ValueError('XPid should be something like "id@location" (not "{:s}")'
                             .format(value))
        return six.text_type.__new__(cls, value)

    @property
    def id(self):
        return self.split('@')[0]

    @property
    def location(self):
        return self.split('@')[1]


#: The list of operational experiment names.
opsuites = set([LegacyXPid(x) for x in (['OPER', 'DBLE', 'TEST', 'MIRR'] +
                                        ['OP{0:02d}'.format(i) for i in range(100)])])


class Namespace(six.text_type):
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
        thisns = six.text_type.__new__(cls, value)
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


class Latitude(float):
    """Bounded floating point value with N-S nice representation."""
    def __new__(cls, value):
        value = six.text_type(value).lower()
        if value.endswith('n'):
            value = value[:-1]
        elif value.endswith('s'):
            value = value[:-1]
            if not value.startswith('-'):
                value = '-' + value
        if not -90 <= float(value) <= 90:
            raise ValueError('Latitude out of bounds: ' + value)
        return float.__new__(cls, value)

    def nice(self):
        ns = 'N' if self >= 0 else 'S'
        return six.text_type(self).strip('-') + ns

    @property
    def hemisphere(self):
        return 'North' if self >= 0 else 'South'


class Longitude(float):
    """Bounded floating point value with E-W nice representation."""
    def __new__(cls, value):
        value = six.text_type(value).lower()
        if value.endswith('e'):
            value = value[:-1]
        elif value.endswith('w'):
            value = value[:-1]
            if not value.startswith('-'):
                value = '-' + value
        if not -180 <= float(value) <= 180:
            raise ValueError('Longitude out of bounds: ' + value)
        return float.__new__(cls, value)

    def nice(self):
        ns = 'E' if self >= 0 else 'W'
        return six.text_type(self).strip('-') + ns

    @property
    def hemisphere(self):
        return 'East' if self >= 0 else 'West'


# predefined attributes

#: Usual definition for the ``xpid`` (*e.g.* experiment name).
a_xpid = dict(
    info     = "The experiment's identifier.",
    type     = XPid,
    optional = False,
)

xpid = footprints.Footprint(info = 'Abstract experiment id',
                            attr = dict(experiment = a_xpid))

#: Usual definition for an Olive/Oper ``xpid`` (*e.g.* experiment name).
a_legacy_xpid = copy.copy(a_xpid)
a_legacy_xpid['type'] = LegacyXPid

legacy_xpid = footprints.Footprint(info = 'Abstract experiment id',
                                   attr = dict(experiment = a_legacy_xpid))

#: Usual definition for a user-defined ``xpid`` (*e.g.* experiment name).
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


def _namebuilding_insert_nativefmt(cls):

    if hasattr(cls, 'namebuilding_info'):
        original_namebuilding_info = cls.namebuilding_info

        def namebuilding_info(self):
            vinfo = original_namebuilding_info(self)
            ext_remap = getattr(self, '_extension_remap', dict())
            ext_value = ext_remap.get(self.nativefmt, self.nativefmt)
            if ext_value is not None:
                vinfo.setdefault('fmt', ext_remap.get(self.nativefmt, self.nativefmt))
            return vinfo

        namebuilding_info.__doc__ = original_namebuilding_info.__doc__
        cls.namebuilding_info = namebuilding_info

    return cls


nativefmt_deco = footprints.DecorativeFootprint(
    nativefmt,
    decorator = [_namebuilding_insert_nativefmt,
                 generic_pathname_insert('nativefmt', lambda self: self.nativefmt, setdefault=True)])

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

cutoff_deco = footprints.DecorativeFootprint(
    cutoff,
    decorator = [namebuilding_append('flow',
                                     lambda self: None if self.cutoff is None else {'shortcutoff': self.cutoff},
                                     none_discard=True),
                 generic_pathname_insert('cutoff', lambda self: self.cutoff, setdefault=True)])

#: Usual definition of the ``model`` attribute.
a_model = dict(
    info     = "The model name (from a source code perspective).",
    alias    = ('turtle', ),
    optional = False,
    values   = models,
    remap    = dict(
        arp = 'arpege',
        ald = 'aladin',
        aro = 'arome'
    ),
)

model = footprints.Footprint(info = 'Abstract model', attr = dict(model = a_model))

model_deco = footprints.DecorativeFootprint(
    model,
    decorator = [namebuilding_append('src', lambda self: [self.model, ]),
                 generic_pathname_insert('model', lambda self: self.model, setdefault=True)])

#: Usual definition of the ``date`` attribute.
a_date = dict(
    info = "The generating process run date.",
    type = Date,
    optional = False,
)

date = footprints.Footprint(info = 'Abstract date', attr = dict(date = a_date))

date_deco = footprints.DecorativeFootprint(
    date,
    decorator = [namebuilding_append('flow', lambda self: {'date': self.date}),
                 generic_pathname_insert('date', lambda self: self.date, setdefault=True)])

#: Usual definition of the ``begindate`` and ``enddate`` attributes.

dateperiod = footprints.Footprint(info = 'Abstract date period',
                                  attr = dict(begindate = dict(info = "The resource's begin date.",
                                                               type = Date,
                                                               optional = False),
                                              enddate = dict(info = "The resource's end date.",
                                                             type = Date,
                                                             optional = False),
                                              ))

dateperiod_deco = footprints.DecorativeFootprint(
    dateperiod,
    decorator = [namebuilding_append('flow',
                                     lambda self: [{'begindate': self.begindate},
                                                   {'enddate': self.enddate}]),
                 generic_pathname_insert('begindate', lambda self: self.begindate, setdefault=True),
                 generic_pathname_insert('enddate', lambda self: self.enddate, setdefault=True)])

#: Usual definition of the ``month`` attribute.
a_month = dict(
    info     = "The generating process run month.",
    type     = Month,
    args     = dict(year=0),
    optional = False,
    values   = range(1, 13)
)

month = footprints.Footprint(info = 'Abstract month', attr = dict(month = a_month))


def _add_month2gget_basename(cls):
    """Decorator that appends the month's number at the end of the gget_basename"""
    original_gget_basename = getattr(cls, 'gget_basename', None)
    if original_gget_basename is not None:

        def gget_basename(self):
            """GGET specific naming convention."""
            return original_gget_basename(self) + '.m{!s}'.format(self.month)

        cls.gget_basename = gget_basename
    return cls


def _add_month2olive_basename(cls):
    """Decorator that appends the month's number at the end of the olive_basename."""
    original_olive_basename = getattr(cls, 'olive_basename', None)
    if original_olive_basename is not None:

        def olive_basename(self):
            """GGET specific naming convention."""
            return original_olive_basename(self) + '.{!s}'.format(self.month)

        cls.olive_basename = olive_basename
    return cls


month_deco = footprints.DecorativeFootprint(
    month,
    decorator=[namebuilding_append('suffix', lambda self: {'month': self.month}),
               _add_month2gget_basename, _add_month2olive_basename])

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

term_deco = footprints.DecorativeFootprint(
    term,
    decorator = [namebuilding_insert('term',
                                     lambda self: None if self.term is None else self.term.fmthm,
                                     none_discard=True, setdefault=True), ])


#: Usual definition of the ``begintime`` and ``endtime`` attributes.

timeperiod = footprints.Footprint(info = 'Abstract Time Period',
                                  attr = dict(begintime = dict(info = "The resource's begin forecast term.",
                                                               type = Time,
                                                               optional = False),
                                              endtime = dict(info = "The resource's end forecast term.",
                                                             type = Time,
                                                             optional = False),
                                              ))

timeperiod_deco = footprints.DecorativeFootprint(
    timeperiod,
    decorator = [namebuilding_insert('period',
                                     lambda self: [{'begintime': self.begintime},
                                                   {'endtime': self.endtime}]), ])

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

#: Usual definition of the ``scenario`` attribute
a_scenario = dict(
    info     = "The scenario identifier of the climate simulation (optional, especially in an NWP context).",
    optional = True,
)

scenario = footprints.Footprint(info = 'Abstract scenario', attr = dict(scenario = a_scenario))

#: Usual definition of the ``number`` attribute (e.g. a perturbation number)
a_number = dict(
    info    = "Any kind of numbering...",
    type    = FmtInt,
    args    = dict(fmt = '03'),
)

number = footprints.Footprint(info = 'Abstract number', attr = dict(number = a_number))

number_deco = footprints.DecorativeFootprint(
    number,
    decorator = [namebuilding_insert('number', lambda self: self.number, setdefault=True), ])

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

#: Usual definition of the ``storehash`` attribute
a_hashalgo = dict(
    info = "The hash algorithm used to check data integrity",
    optional = True,
    values = [None, ],
)

hashalgo = footprints.Footprint(info = 'Abstract Hash Algo', attr = dict(storehash = a_hashalgo))

hashalgo_avail_list = hashutils.HashAdapter.algorithms()

#: Usual definition of the ``store_compressed`` attribute
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
        print('{0} ( {1} ) :\n  {2}\n'.format(stda, type(dmod[stda]).__name__, dmod[stda]))
