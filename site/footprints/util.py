#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
Utility functions of the :mod:`footprints` package.
"""

#: No automatic export
__all__ = []

import re, copy, glob
import types
from weakref import WeakSet

from . import loggers
logger = loggers.getLogger(__name__)


def dictmerge(d1, d2):
    """
    Merge two dictionaries d1 and d2 with a recursive function (d1 and d2 can be
    dictionaries of dictionaries). The result is in d1.
    If keys exist in d1 and d2, d1 keys are replaced by d2 keys.

    >>> a = {'name':'clim','attr':{'model':{'values':('arpege','arome')}}}
    >>> b = {'name':'clim model','attr':{'truncation':{'type':'int','optional':'False'}}}
    >>> dictmerge(a, b)
    {'name': 'clim model', 'attr': {'model': {'values': ('arpege', 'arome')}, 'truncation': {'type': 'int', 'optional': 'False'}}}

    >>> dictmerge({'a':'1'},{'b':'2'})
    {'a': '1', 'b': '2'}

    >>> dictmerge({'a':'1','c':{'d':'3','e':'4'},'i':{'b':'2','f':{'g':'5'}}}, {'c':{'h':'6', 'e':'7'}})
    {'a': '1', 'i': {'b': '2', 'f': {'g': '5'}}, 'c': {'h': '6', 'e': '7', 'd': '3'}}
    """

    for key, value in d2.iteritems():
        if type(value) is types.DictType:
            if key in d1 and type(d1[key])is types.DictType:
                dictmerge(d1[key], d2[key])
            else:
                d1[key] = copy.deepcopy(value)
        else:
            d1[key] = value

    return d1


def list2dict(a, klist):
    """
    Reshape any entry of ``a`` specified in ``klist`` as a dictionary of the iterable contents
    of these entry.
    """

    for k in klist:
        if k in a and ( type(a[k]) is types.TupleType or type(a[k]) is types.ListType):
            ad = dict()
            for item in a[k]:
                ad.update(item)
            a[k] = ad
    return a


def mktuple(obj):
    """Make a tuple from any kind of object."""
    if isinstance(obj, list) or isinstance(obj, set) or isinstance(obj, tuple):
        return tuple(obj)
    else:
        return (obj,)


class TimeInt(int):
    """
    Extended integer able to handle simple integers or integer plus minutes.
    In the later case, the first integer is not limitated to 24.
    """

    def __new__(cls, ti, tm=None):
        ti = str(ti)
        if not re.match(r'-?\d*(?::\d\d+)?$', ti):
            return ValueError('{} is not a valid TimeInt'.format(ti))
        if ti.startswith('-'):
            thesign = -1
            ti = ti[1:]
        else:
            thesign = 1
        if ':' in ti:
            ti, tm = ti.split(':')
            ti = 0 if ti == '' else int(ti)
            tm = int(tm)
        obj = int.__new__(cls, thesign * int(ti))
        if tm is None:
            obj._int = True
            tm = 0
        else:
            obj._int = False
        obj._ti, obj._tm = thesign * int(ti), thesign * int(tm)
        return obj

    @property
    def ti(self):
        return self._ti

    @property
    def tm(self):
        return self._tm

    def is_int(self):
        return self._int

    @property
    def str_time(self):
        signstr = '-' if self.ti * 60 + self.tm < 0 else ''
        return '{0:}{1:04d}:{2:02d}'.format(signstr,
                                            abs(self.ti), abs(self.tm))

    def __str__(self):
        if self.is_int():
            return str(self.ti)
        else:
            return self.str_time

    def __hash__(self):
        return self.ti * 60 + self.tm

    def __eq__(self, other):
        try:
            other = self.__class__(other)
        except (ValueError, TypeError):
            return False
        return self.ti * 60 + self.tm == other.ti * 60 + other.tm

    def __cmp__(self, other):
        # This may fail if other is malformed, but maybe it's for the best...
        other = self.__class__(other)
        return cmp(self.ti * 60 + self.tm, other.ti * 60 + other.tm)

    @staticmethod
    def __split_timedelta(dt):
        """Format a timedelta expressed in minutes, in a valid hhhh:mm expression"""
        thesign = int(dt > 0) * 2 - 1
        ti = 0
        while abs(dt) >= 60:
            ti += thesign
            dt -= thesign * 60
        return ti, dt

    def __add__(self, other):
        # This may fail if other is malformed, but maybe it's for the best...
        other = self.__class__(other)
        timedelay = (self.ti + other.ti) * 60 + (self.tm + other.tm)
        ti, tm = self.__split_timedelta(timedelay)
        if tm:
            signstr = '-' if timedelay < 0 else ''
            return self.__class__('{}{:d}:{:02d}'.format(signstr,
                                                         abs(ti), abs(tm)))
        else:
            return self.__class__(ti)

    def __radd__(self, other):
        """Commutative add."""
        return self.__add__(other)

    def __sub__(self, other):
        # This may fail if other is malformed, but maybe it's for the best...
        other = self.__class__(other)
        timedelay = (self.ti - other.ti) * 60 + (self.tm - other.tm)
        ti, tm = self.__split_timedelta(timedelay)
        if tm:
            signstr = '-' if timedelay < 0 else ''
            return self.__class__('{}{:d}:{:02d}'.format(signstr,
                                                         abs(ti), abs(tm)))
        else:
            return self.__class__(ti)

    @property
    def realtype(self):
        return 'int' if self.is_int() else 'time'

    @property
    def value(self):
        return self.ti if self.is_int() else str(self)


def rangex(start, end=None, step=None, shift=None, fmt=None, prefix=None):
    """
    Extended range expansion.
    When ``start`` is already a complex definition (as a string), ``end`` and ``step`` only apply
    as default when the sub-definition in ``start`` does not contain any ``end`` or ``step`` value.
    """
    rangevalues = list()

    pstarts = ([str(s) for s in start]
               if isinstance(start, (list, tuple)) else str(start).split(','))
    for pstart in pstarts:

        if re.search('_', pstart):
            prefix, realstart = pstart.split('_')
            prefix += '_'
        else:
            realstart = pstart
        if realstart.startswith('-'):
            realstart = '__MINUS__' + realstart[1:]
        if '--' in realstart:
            realstart = realstart.replace('--', '/__MINUS__').replace('-', '/')
        realstart = realstart.replace('-', '/')
        realstart = realstart.replace('__MINUS__', '-')
        actualrange = realstart.split('/')
        realstart = TimeInt(actualrange[0])

        if len(actualrange) > 1:
            realend = actualrange[1]
        elif end is None:
            realend = realstart
        else:
            realend = end
        realend = TimeInt(realend)

        if len(actualrange) > 2:
            realstep = actualrange[2]
        elif step is None:
            realstep = 1
        else:
            realstep = step
        realstep = TimeInt(realstep)

        if shift is not None:
            realshift = TimeInt(shift)
            realstart += realshift
            realend   += realshift

        signstep = int(realstep > 0) * 2 - 1
        pvalues = [ realstart ]
        while cmp(pvalues[-1], realend) == - signstep:
            pvalues.append(pvalues[-1] + realstep)
        if cmp(pvalues[-1], realend) == signstep:
            pvalues.pop()

        if all([ x.is_int() for x in pvalues ]):
            pvalues = [ x.value for x in pvalues ]
        else:
            pvalues = [ x.str_time for x in sorted(pvalues) ]

        if fmt is not None:
            if fmt.startswith('%'):
                fmt = '{0:' + fmt[1:] + '}'
            pvalues = [fmt.format(x, i + 1, type(x).__name__)
                       for i, x in enumerate(pvalues)]

        if prefix is not None:
            pvalues = [ prefix + str(x) for x in pvalues ]
        rangevalues.extend(pvalues)

    return sorted(set(rangevalues))


def inplace(desc, key, value, globs=None):
    """
    Redefined the ``key`` value in a deep copy of the description ``desc``.

    >>> inplace({'test':'alpha'}, 'ajout', 'beta')
    {'test': 'alpha', 'ajout': 'beta'}

    >>> inplace({'test':'alpha', 'recurs':{'a':1, 'b':2}}, 'ajout', 'beta')
    {'test': 'alpha', 'ajout': 'beta', 'recurs': {'a': 1, 'b': 2}}
    """
    newd = copy.deepcopy(desc)
    newd[key] = value
    if globs:
        for k in [ x for x in newd.keys() if (x != key and isinstance(newd[x], basestring) ) ]:
            for g in globs.keys():
                newd[k] = re.sub(r'\[glob:' + g + r'\]', globs[g], newd[k])
    return newd


def expand(desc):
    """
    Expand the given description according to iterable or expandable arguments.

    >>> expand( {'test': 'alpha'} )
    [{'test': 'alpha'}]

    >>> expand( { 'test': 'alpha', 'niv2': [ 'a', 'b', 'c' ] } )
    [{'test': 'alpha', 'niv2': 'a'}, {'test': 'alpha', 'niv2': 'b'}, {'test': 'alpha', 'niv2': 'c'}]

    >>> expand({'test': 'alpha', 'niv2': 'x,y,z'})
    [{'test': 'alpha', 'niv2': 'x'}, {'test': 'alpha', 'niv2': 'y'}, {'test': 'alpha', 'niv2': 'z'}]

    """

    ld = [ desc ]
    todo = True
    nbpass = 0

    while todo:
        todo = False
        nbpass += 1
        if nbpass > 25:
            logger.error('Expansion is getting messy... (%d) ?', nbpass)
            raise MemoryError('Expand depth too high')
        for i, d in enumerate(ld):
            for k, v in d.iteritems():
                if v.__class__.__name__.startswith('FP'):
                    continue
                if isinstance(v, list) or isinstance(v, tuple) or isinstance(v, set):
                    logger.debug(' > List expansion %s', v)
                    ld[i:i+1] = [ inplace(d, k, x) for x in v ]
                    todo = True
                    break
                if isinstance(v, str) and re.match(r'range\(\d+(,\d+)?(,\d+)?\)$', v, re.IGNORECASE):
                    logger.debug(' > Range expansion %s', v)
                    lv = [ int(x) for x in re.split(r'[\(\),]+', v) if re.match(r'\d+$', x) ]
                    if len(lv) < 2:
                        lv.append(lv[0])
                    lv[1] += 1
                    ld[i:i+1] = [ inplace(d, k, x) for x in range(*lv) ]
                    todo = True
                    break
                if isinstance(v, str) and re.search(r',', v):
                    logger.debug(' > Coma separated string %s', v)
                    ld[i:i+1] = [ inplace(d, k, x) for x in v.split(',') ]
                    todo = True
                    break
                if isinstance(v, str) and re.search(r'{glob:', v):
                    logger.debug(' > Globbing from string %s', v)
                    vglob = v
                    globitems = list()
                    def getglob(matchobj):
                        globitems.append([matchobj.group(1), matchobj.group(2)])
                        return '*'
                    vglob = re.sub(r'{glob:(\w+):([^\}]+)}', getglob, vglob)
                    ngrp = 0
                    while re.search(r'{glob:', v):
                        v = re.sub(r'{glob:\w+:([^\}]+)}', '{' + str(ngrp) + '}', v, count=1)
                        ngrp += 1
                    v = v.replace('+', r'\+')
                    v = v.replace('.', r'\.')
                    ngrp = 0
                    while re.search(r'{\d+}', v):
                        v = re.sub(r'{\d+}', '(' + globitems[ngrp][1] + ')', v, count=1)
                        ngrp += 1
                    repld = list()
                    for filename in glob.glob(vglob):
                        m = re.search(r'^' + v + r'$', filename)
                        if m:
                            globmap = dict()
                            for ig in range(len(globitems)):
                                globmap[globitems[ig][0]] = m.group(ig+1)
                            repld.append(inplace(d, k, filename, globmap))
                    ld[i:i+1] = repld
                    todo = True
                    break
                if isinstance(v, dict):
                    for dk in [ x for x in v.keys() if x in d ]:
                        dv = d[dk]
                        if not(isinstance(dv, list) or isinstance(dv, tuple) or isinstance(dv, set)):
                            ld[i] = inplace(d, k, v[dk][str(dv)])
                            todo = True
                            break
                    if todo:
                        break

    logger.debug('Expand in %d loops', nbpass)
    return ld


class GetByTagMeta(type):
    """
    Meta class constructor for :class:`GetByTag`.
    The purpose is quite simple : to set a dedicated shared table
    in the new class in construction.
    """

    def __new__(cls, n, b, d):
        logger.debug('Base class for getbytag usage "%s / %s", bc = ( %s ), internal = %s', cls, n, b, d)
        if d.setdefault('_tag_topcls', True):
            d['_tag_table'] = dict()
            d['_tag_focus'] = dict(default=None)
            d['_tag_class'] = WeakSet()
        realnew = super(GetByTagMeta, cls).__new__(cls, n, b, d)
        realnew._tag_class.add(realnew)
        return realnew

    def __call__(cls, *args, **kw):
        return cls.__new__(cls, *args, **kw)


class GetByTag(object):
    """
    Utility to retrieve a new object by a special named argument ``tag``.
    If an object had already been created with that tag, return this object.
    """

    __metaclass__ = GetByTagMeta

    _tag_default = 'default'

    def __new__(cls, *args, **kw):
        """Check for an existing object with same tag."""
        tag = kw.pop('tag', None)
        if tag is None:
            if args:
                args = list(args)
                tag  = args.pop(0)
            else:
                tag = cls._tag_default
        tag = cls.tag_clean(tag)
        new = kw.pop('new', False)
        if not new and tag in cls._tag_table:
            newobj = cls._tag_table[tag]
        else:
            newobj = super(GetByTag, cls).__new__(cls)
            newobj._tag = tag
            newobj.__init__(*args, **kw)
            cls._tag_table[tag] = newobj
        return newobj

    @property
    def tag(self):
        return self._tag

    @classmethod
    def tag_clean(cls, tag):
        """By default, return the actual tag."""
        return tag

    @classmethod
    def tag_keys(cls):
        """Return an alphabetic ordered list of actual keys of the objects instanciated."""
        return sorted(cls._tag_table.keys())

    @classmethod
    def tag_values(cls):
        """Return a non-ordered list of actual values of the objects instanciated."""
        return cls._tag_table.values()

    @classmethod
    def tag_items(cls):
        """Proxy to the ``items`` method of the internal dictionary table of objects."""
        return cls._tag_table.items()

    @classmethod
    def tag_focus(cls, select='default'):
        """Return the tag value of the actual object with focus according to the ``select`` value."""
        return cls._tag_focus[select]

    @classmethod
    def set_focus(cls, obj, select='default'):
        """Define a new tag value for the focus in the scope of the ``select`` value."""
        cls._tag_focus[select] = obj.tag

    def has_focus(self, select='default'):
        """Return a boolean value on equality of current tag and focus tag."""
        return self.tag == self.__class__._tag_focus[select]

    def catch_focus(self, select='default'):
        """The current object decides to be on focus !"""
        self.__class__._tag_focus[select] = self.tag

    @classmethod
    def tag_clear(cls):
        """Clear all internal information about objects and focus for that class."""
        cls._tag_table = dict()
        cls._tag_focus = dict(default=None)

    @classmethod
    def tag_classes(cls):
        """Return a list of current classes that have been registred with the same GetByTag root."""
        return list(cls._tag_class)

    def __copy__(self):
        """I don't know how to deep copy a GetByTag..."""
        logger.debug("There is no trivial way to copy a GetByTag instance: returning self")
        return self

    def __deepcopy__(self, memo):
        """I don't know how to deep copy a GetByTag..."""
        logger.debug("There is no trivial way to deepcopy a GetByTag instance: returning self")
        memo[id(self)] = self
        return self


class Catalog(object):
    """
    Abstract class for managing a collection of *items*.
    The interface is very light : :meth:`clear` and :meth:`refill` !
    Of course a catalog is an iterable object. It is also callable,
    and then returns a copy of the list of its items.
    """

    def __init__(self, **kw):
        logger.debug('Abstract %s init', self.__class__)
        self._weak  = kw.pop('weak', False)
        self._items = kw.pop('items', list())
        if self._weak:
            self._items = WeakSet(self._items)
        else:
            self._items = set(self._items)
        self.__dict__.update(kw)

    @classmethod
    def fullname(cls):
        """Returns a nicely formated name of the current class (dump usage)."""
        return '{0:s}.{1:s}'.format(cls.__module__, cls.__name__)

    @property
    def filled(self):
        """Boolean value, true if at least one item in the catalog."""
        return bool(self._items)

    @property
    def weak(self):
        """Boolean value, true if catalog built with weaked references."""
        return self._weak

    def items(self):
        """A list copy of catalog items."""
        return list(self._items)

    def __iter__(self):
        """Catalog is iterable... at least!"""
        for c in self._items:
            yield c

    def __call__(self):
        return self.items()

    def __len__(self):
        return len(self._items)

    def __contains__(self, item):
        return item in self._items

    def __getstate__(self):
        d = self.__dict__.copy()
        d['_items'] = list(self._items)
        return d

    def __setstate__(self, state):
        self.__dict__.update(state)
        self._items = WeakSet(self._items) if self._weak else set(self._items)

    def add(self, *items):
        """Add the ``item`` entry in the current catalog."""
        for item in items:
            self._items.add(item)

    def discard(self, bye):
        """Remove the ``bye`` entry from current catalog."""
        self._items.discard(bye)

    def clear(self):
        """Completly clear the list of items previously recorded in this catalog."""
        self._items = WeakSet() if self._weak else set()


class SpecialDict(dict):
    """Add some special features to std dict for dealing to dedicated case dictionaries."""

    def __init__(self, *kargs, **kwargs):
        tmpdict = dict(*kargs, **kwargs)
        # Check the dictionnary keys. If necessary change them
        for k, v in [(k, v) for k, v in tmpdict.iteritems() if k != self.remap(k)]:
            del tmpdict[k]
            tmpdict[self.remap(k)] = v
        super(SpecialDict, self).__init__(tmpdict)

    def show(self, ljust=24):
        """Print the actual values of the dictionary."""
        for k in sorted(self.keys()):
            print '+', k.ljust(ljust), '=', self.get(k)

    def update(self, *args, **kw):
        """Extended dictionary update with args as dict and extra keywords."""
        args = list(args)
        args.append(kw)
        for objiter in args:
            for k, v in objiter.items():
                self.__setitem__(k, v)

    def __call__(self, **kw):
        """Calling a special dict is equivalent to updating."""
        self.update(**kw)

    def remap(self, key):
        """Return a new value for the actual ``key``. Default is identity."""
        return key

    def __getitem__(self, key):
        """Force remapped key retrieve."""
        return dict.__getitem__(self, self.remap(key))

    def __setitem__(self, key, value):
        """Force remapped key setting."""
        dict.__setitem__(self, self.remap(key), value)

    def __delitem__(self, key):
        """Force remapped key deletion."""
        dict.__delitem__(self, self.remap(key))

    def __contains__(self, key):
        """Force remapped key ``in`` check."""
        return dict.__contains__(self, self.remap(key))


class LowerCaseDict(SpecialDict):
    """A dictionary with only lower case keys."""

    def remap(self, key):
        """Return a lower case value of the actual key."""
        return key.lower()


class UpperCaseDict(SpecialDict):
    """A dictionary with only upper case keys."""

    def remap(self, key):
        """Return a upper case value of the actual key."""
        return key.upper()


if __name__ == '__main__':
    import doctest
    doctest.testmod()
