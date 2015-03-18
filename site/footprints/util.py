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


def rangex(start, end=None, step=None, shift=None, fmt=None, prefix=None):
    """
    Extended range expansion.
    When ``start`` is already a complex definition (as a string), ``end`` and ``step`` only apply
    as default when the sub-definition in ``start`` does not contain any ``end`` or ``step`` value.
    """
    rangevalues = list()

    for pstart in str(start).split(','):

        if re.search('_', pstart):
            prefix, realstart = pstart.split('_')
            prefix += '_'
        else:
            realstart = pstart
        if realstart.startswith('-'):
            actualrange = [ realstart ]
        else:
            actualrange = realstart.split('-')
        realstart = int(actualrange[0])

        if len(actualrange) > 1:
            realend = actualrange[1]
        elif end is None:
            realend = realstart
        else:
            realend = end
        realend = int(realend)

        if len(actualrange) > 2:
            realstep = actualrange[2]
        elif step is None:
            realstep = 1
        else:
            realstep = step
        realstep = int(realstep)

        if realstep < 0:
            realend -= 1
        else:
            realend += 1
        if shift is not None:
            realshift = int(shift)
            realstart += realshift
            realend   += realshift

        pvalues = range(realstart, realend, realstep)
        if fmt is not None:
            if fmt.startswith('%'):
                fmt = '{0:' + fmt[1:] + '}'
            pvalues = [ fmt.format(x, i+1, type(x).__name__) for i, x in enumerate(pvalues) ]
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
        for k in [ x for x in newd.keys() if (x != key and type(newd[x]) is types.StringType) ]:
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
                    while re.search(r'{glob:', vglob):
                        vglob = re.sub(r'{glob:(\w+):([^\}]+)}', getglob, vglob)
                    ngrp = 0
                    while re.search(r'{glob:', v):
                        v = re.sub(r'{glob:\w+:([^\}]+)}', '{' + str(ngrp) + '}', v)
                        ngrp += 1
                    v = v.replace('+', r'\+')
                    v = v.replace('.', r'\.')
                    ngrp = 0
                    while re.search(r'{\d+}', v):
                        v = re.sub(r'{\d+}', '(' + globitems[ngrp][1] + ')', v)
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

    logger.debug('Expand in %d loops', nbpass)
    return ld


class GetByTagMeta(type):
    """
    Meta class constructor for :class:`GetByTag`.
    The purpose is quite simple : to set a dedicated shared table
    in the new class to be build.
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
        return self.tag == self._tag_focus[select]

    @classmethod
    def tag_clear(cls):
        """Clear all internal information about objects and focus for that class."""
        cls._tag_table = dict()
        cls._tag_focus = dict(default=None)

    @classmethod
    def tag_classes(cls):
        """Return a list of current classes that have been registred with the same GetByTag root."""
        return list(cls._tag_class)


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


class LowerCaseDict(SpecialDict):
    """A dictionary with only lower case keys."""

    def __getitem__(self, key):
        """Force lower case key retrieve."""
        return dict.__getitem__(self, key.lower())

    def __setitem__(self, key, value):
        """Force lower case key setting."""
        dict.__setitem__(self, key.lower(), value)

    def __delitem__(self, key):
        """Force lower case key deletion."""
        dict.__delitem__(self, key.lower())

    def __contains__(self, key):
        """Force lower case ``in`` check."""
        return dict.__contains__(self, key.lower())


class UpperCaseDict(SpecialDict):
    """A dictionary with only upper case keys."""

    def __getitem__(self, key):
        """Force upper case key retrieve."""
        return dict.__getitem__(self, key.upper())

    def __setitem__(self, key, value):
        """Force upper case key setting."""
        dict.__setitem__(self, key.upper(), value)

    def __delitem__(self, key):
        """Force upper case key deletion."""
        dict.__delitem__(self, key.upper())

    def __contains__(self, key):
        """Force upper case ``in`` check."""
        return dict.__contains__(self, key.upper())


if __name__ == '__main__':
    import doctest
    doctest.testmod()

