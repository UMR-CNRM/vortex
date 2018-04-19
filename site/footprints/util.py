#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
Utility functions of the :mod:`footprints` package.
"""

from __future__ import print_function, absolute_import, division

import re
import copy
import glob
from weakref import WeakSet
from collections import deque
import six
import string

from . import loggers

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


def dictmerge(d1, d2):
    """
    Merge two dictionaries d1 and d2 with a recursive function (d1 and d2 can be
    dictionaries of dictionaries). The result is in d1.
    If keys exist in d1 and d2, d1 keys are replaced by d2 keys.

    Examples::

        >>> a = {'name':'clim','attr':{'model':{'values':('arpege','arome')}}}
        >>> b = {'name':'clim model','attr':{'truncation':{'type':'int','optional':'False'}}}
        >>> dictmerge(a, b)
        {'name': 'clim model', 'attr': {'model': {'values': ('arpege', 'arome')}, 'truncation': {'type': 'int', 'optional': 'False'}}}

        >>> dictmerge({'a':'1'},{'b':'2'})
        {'a': '1', 'b': '2'}

        >>> dictmerge({'a':'1','c':{'d':'3','e':'4'},'i':{'b':'2','f':{'g':'5'}}}, {'c':{'h':'6', 'e':'7'}})
        {'a': '1', 'i': {'b': '2', 'f': {'g': '5'}}, 'c': {'h': '6', 'e': '7', 'd': '3'}}
    """

    for key, value in six.iteritems(d2):
        if isinstance(value, dict) and not value.__class__.__name__.startswith('FP'):
            if key in d1 and isinstance(d1[key], dict) and not value.__class__.__name__.startswith('FP'):
                dictmerge(d1[key], d2[key])
            else:
                d1[key] = copy.deepcopy(value)
        else:
            d1[key] = value

    return d1


def list2dict(a, klist):
    """
    Reshape any entry of ``a`` specified in ``klist`` as a dictionary of the
    iterable contents of these entries.
    """

    for k in klist:
        if k in a and isinstance(a[k], (list, tuple)):
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
    """Extended integer able to handle simple integers or integer plus minutes.

    In the later case, the first integer is not limited to 24.
    """

    def __new__(cls, ti, tm=None):
        ti = str(ti)
        if not re.match(r'-?\d*(?::\d\d+)?$', ti):
            raise ValueError('{} is not a valid TimeInt'.format(ti))
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

    def __lt__(self, other):
        other = self.__class__(other)
        return self.ti * 60 + self.tm < other.ti * 60 + other.tm

    def __le__(self, other):
        return self.__lt__(other) or self.__eq__(other)

    def __gt__(self, other):
        other = self.__class__(other)
        return self.ti * 60 + self.tm > other.ti * 60 + other.tm

    def __ge__(self, other):
        return self.__gt__(other) or self.__eq__(other)

    @staticmethod
    def __split_timedelta(dt):
        """Format a timedelta expressed in minutes, in a valid hhhh:mm expression."""
        thesign = int(dt > 0) * 2 - 1
        ti = 0
        while abs(dt) >= 60:
            ti += thesign
            dt -= thesign * 60
        return ti, dt

    def __split_timedelta_and_reclass(self, dt):
        ti, tm = self.__split_timedelta(dt)
        if tm:
            signstr = '-' if dt < 0 else ''
            return self.__class__('{}{:d}:{:02d}'.format(signstr,
                                                         abs(ti), abs(tm)))
        else:
            return self.__class__(ti)

    def __add__(self, other):
        # This may fail if other is malformed, but maybe it's for the best...
        other = self.__class__(other)
        timedelay = (self.ti + other.ti) * 60 + (self.tm + other.tm)
        return self.__split_timedelta_and_reclass(timedelay)

    def __radd__(self, other):
        """Swapped add."""
        return self.__add__(other)

    def __sub__(self, other):
        # This may fail if other is malformed, but maybe it's for the best...
        other = self.__class__(other)
        timedelay = (self.ti - other.ti) * 60 + (self.tm - other.tm)
        return self.__split_timedelta_and_reclass(timedelay)

    def __rsub__(self, other):
        """Swapped sub."""
        # This may fail if other is malformed, but maybe it's for the best...
        other = self.__class__(other)
        timedelay = (other.ti - self.ti) * 60 + (other.tm - self.tm)
        return self.__split_timedelta_and_reclass(timedelay)

    def __mul__(self, other):
        # The result might be truncated since second/microseconds are not suported
        other = self.__class__(other)
        factor = other.ti * 60 + other.tm
        me = self.ti * 60 + self.tm
        return self.__split_timedelta_and_reclass((me * factor) // 60)

    def __rmul__(self, other):
        return self.__mul__(other)

    @property
    def realtype(self):
        return 'int' if self.is_int() else 'time'

    @property
    def value(self):
        return self.ti if self.is_int() else str(self)


def rangex(start, end=None, step=None, shift=None, fmt=None, prefix=None):
    """Extended range expansion.

    When ``start`` is already a complex definition (as a string), ``end`` and
    ``step`` only apply as default when the sub-definition in ``start`` does not
    contain any ``end`` or ``step`` value.

    Basic examples::

        >>> rangex(0, 12, 3)
        [0, 3, 6, 9, 12]
        >>> rangex('0-12-3')
        [0, 3, 6, 9, 12]
        >>> rangex('0-12-3', shift=24)
        [24, 27, 30, 33, 36]
        >>> rangex(0, 12, 3, shift=24)
        [24, 27, 30, 33, 36]
        >>> rangex('0-12-3', shift=24, fmt='%03d')
        ['024', '027', '030', '033', '036']

    Hour/Minutes examples::

        >>> rangex(0, 3, '0:30')
        ['0000:00', '0000:30', '0001:00', '0001:30', '0002:00', '0002:30', '0003:00']
        >>> rangex('0:00', '3:00', '0:30')
        ['0000:00', '0000:30', '0001:00', '0001:30', '0002:00', '0002:30', '0003:00']
        >>> rangex(0, 3, '0:30', shift=24)
        ['0024:00', '0024:30', '0025:00', '0025:30', '0026:00', '0026:30', '0027:00']

    It also works with negative values::

        >>> rangex(3, 0,'-0:30')
        ['0000:00', '0000:30', '0001:00', '0001:30', '0002:00', '0002:30', '0003:00']
        >>> rangex(-3, 0,'0:30')
        ['-0000:30', '-0001:00', '-0001:30', '-0002:00', '-0002:30', '-0003:00', '0000:00']
        >>> rangex(-3, 0, 1)
        [-3, -2, -1, 0]

    With complex strings::

        >>> rangex('0-12-3,18-36-6,48')
        [0, 3, 6, 9, 12, 18, 24, 30, 36, 48]
    """
    rangevalues = list()

    # Very strange case of an empty range
    if start is None:
        return list()

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
        while signstep * (pvalues[-1] - realend) < 0:
            pvalues.append(pvalues[-1] + realstep)
        if signstep * (pvalues[-1] - realend) > 0:
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
    Redefine the ``key`` value in a deep copy of the description ``desc``.

    Examples::

        >>> inplace({'test':'alpha'}, 'ajout', 'beta')
        {'test': 'alpha', 'ajout': 'beta'}

        >>> inplace({'test':'alpha', 'recurs':{'a':1, 'b':2}}, 'ajout', 'beta')
        {'test': 'alpha', 'ajout': 'beta', 'recurs': {'a': 1, 'b': 2}}
    """
    newd = copy.deepcopy(desc)
    newd[key] = value
    if globs:
        for k in [ x for x in newd.keys() if (x != key and isinstance(newd[x], six.string_types) ) ]:
            for g in globs.keys():
                newd[k] = re.sub(r'\[glob:' + g + r'\]', globs[g], newd[k])
    return newd


def _parse_globs(todo):
    """Process the **todo** string that contains ``glob`` statements.

    Nested brackets are dealt with.

    Returns a 3-elements tuple consisting of:

        * A set that contains the glob's names ;
        * The compiled regular expression that can be used to select the files
          and detect the glob's expressions ;
        * The python's glob string that can be used to look for files.

    """
    gstart = re.compile('^{glob:(\w+):')
    glob_names = set()
    finalglob = ''
    finalpattern = ''
    curbuffer = ''
    curname = None
    bracket_count = 0

    def glob2re(cbuffer):
        """Convert a Unix glob string to a regular expression (very crude)."""
        fpattern = ''
        for c in cbuffer:
            if c == '*':
                fpattern += '.*'
            elif c == '?':
                fpattern += '.'
            else:
                fpattern += re.escape(c)
        return fpattern

    while todo:
        # Usual text processing
        if not curname:
            gmatch = gstart.match(todo)
            if gmatch:
                # Starting a glob pattern match
                if curbuffer:
                    finalpattern += glob2re(curbuffer)
                    finalglob += curbuffer
                    curbuffer = ''
                curname = gmatch.group(1)
                if curname in glob_names:
                    raise ValueError("Duplicated glob's name ('{:s}' has already been defined)"
                                     .format(curname))
                glob_names.add(curname)
                todo = gstart.sub('', todo)
                continue
        # Pattern processing
        else:
            if (not curbuffer or curbuffer[-1] != '\\') and todo[0] == '{':
                # Opening bracket detected
                bracket_count += 1
            elif (not curbuffer or curbuffer[-1] != '\\') and todo[0] == '}':
                # Closing bracket detected
                if bracket_count:
                    bracket_count -= 1
                else:
                    # Pattern definition is done
                    try:
                        re.compile(curbuffer)
                    except re.error:
                        raise ValueError("Unable to compile << {:s} >> for glob's name = << {:s} >>"
                                         .format(curbuffer, curname))
                    finalpattern += '(?P<{:s}>{:s})'.format(curname, curbuffer)
                    finalglob += '*'
                    curname = None
                    curbuffer = ''
                    todo = todo[1:]
                    continue

        curbuffer += todo[0]
        todo = todo[1:]

    if curname:
        raise ValueError("Unbalanced brackets in << {:s} >> for glob's name = << {:s} >>"
                         .format(curbuffer, curname))

    if curbuffer:
        # Save the remain
        finalpattern += glob2re(curbuffer)
        finalglob += curbuffer

    return glob_names, re.compile('^' + finalpattern + '$'), finalglob


def expand(desc):
    """
    Expand the given description according to iterable or expandable arguments.

    List expansion::

        >>> expand( {'test': 'alpha'} )
        [{'test': 'alpha'}]

        >>> expand( { 'test': 'alpha', 'niv2': [ 'a', 'b', 'c' ] } )
        [{'test': 'alpha', 'niv2': 'a'}, {'test': 'alpha', 'niv2': 'b'}, {'test': 'alpha', 'niv2': 'c'}]

        >>> expand({'test': 'alpha', 'niv2': 'x,y,z'})
        [{'test': 'alpha', 'niv2': 'x'}, {'test': 'alpha', 'niv2': 'y'}, {'test': 'alpha', 'niv2': 'z'}]

        >>> expand({'test': 'alpha', 'niv2': 'range(1,3)'})
        [{'test': 'alpha', 'niv2': 1}, {'test': 'alpha', 'niv2': 2}, {'test': 'alpha', 'niv2': 3}]
        >>> expand({'test': 'alpha', 'niv2': 'range(0,6,3)'})
        [{'test': 'alpha', 'niv2': 0}, {'test': 'alpha', 'niv2': 3}, {'test': 'alpha', 'niv2': 6}]

    List expansion + dictionary matching::

        >>> expand({'test': 'alpha', 'niv2': ['x', 'y'], 'niv3': {'niv2': {'x': 'niv2 is x', 'y': 'niv2 is y'}}})
        [{'test': 'alpha', 'niv3': 'niv2 is x', 'niv2': 'x'}, {'test': 'alpha', 'niv3': 'niv2 is y', 'niv2': 'y'}]

    Globbing::

        >>> # Let's assume that the following files are present in the current working directory: # doctest: +SKIP
        ... # - testfile_abc_1
        ... # - testfile_abc_2
        ... # - testfile_def_2
        ... # - testfile_def_3
        ... # - testfile_a_trap
        >>> expand({'fname': 'testfile_{glob:i:\w+}_{glob:n:\d+}', 'id':'[glob:i]', 'n':'[glob:n]'}) # doctest: +SKIP
        [{'id': 'abc', 'fname': 'testfile_abc_1', 'n': '1'}, {'id': 'def', 'fname': 'testfile_def_2', 'n': '2'}, {'id': 'def', 'fname': 'testfile_def_3', 'n': '3'}, {'id': 'abc', 'fname': 'testfile_abc_2', 'n': '2'}]

    Explanation: The files currently in the working directory are matched using regular
    expressions. If the filename matches, some matching parts may be re-used to fill
    other keys in the dictionary.
    """

    ld = deque([ desc, ])
    todo = True
    nbpass = 0

    while todo:
        todo = False
        nbpass += 1
        if nbpass > 25:
            logger.error('Expansion is getting messy... (%d) ?', nbpass)
            raise MemoryError('Expand depth too high')
        newld = deque()
        while ld:
            d = ld.popleft()
            somechanges = False
            for k, v in six.iteritems(d):
                if v.__class__.__name__.startswith('FP'):
                    continue
                if isinstance(v, list) or isinstance(v, tuple) or isinstance(v, set):
                    logger.debug(' > List expansion %s', v)
                    newld.extend([ inplace(d, k, x) for x in v ])
                    somechanges = True
                    break
                if isinstance(v, six.string_types) and re.match(r'range\(\d+(,\d+)?(,\d+)?\)$', v, re.IGNORECASE):
                    logger.debug(' > Range expansion %s', v)
                    lv = [ int(x) for x in re.split(r'[\(\),]+', v) if re.match(r'\d+$', x) ]
                    if len(lv) < 2:
                        lv.append(lv[0])
                    lv[1] += 1
                    newld.extend([ inplace(d, k, x) for x in range(*lv) ])
                    somechanges = True
                    break
                if isinstance(v, six.string_types) and re.search(r',', v):
                    logger.debug(' > Coma separated string %s', v)
                    newld.extend([ inplace(d, k, x) for x in v.split(',') ])
                    somechanges = True
                    break
                if isinstance(v, six.string_types) and re.search(r'{glob:\w+:', v):
                    logger.debug(' > Globbing from string %s', v)
                    g_names, g_re, g_glob = _parse_globs(v)
                    repld = list()
                    for filename in glob.glob(g_glob):
                        m = g_re.match(filename)
                        if m:
                            globmap = dict()
                            for g in g_names:
                                globmap[g] = m.group(g)
                            repld.append(inplace(d, k, filename, globmap))
                    newld.extend(repld)
                    somechanges = True
                    break
                if isinstance(v, dict):
                    for dk in [ x for x in v.keys() if x in d ]:
                        dv = d[dk]
                        if not(isinstance(dv, list) or isinstance(dv, tuple) or isinstance(dv, set)):
                            newld.append(inplace(d, k, v[dk][str(dv)]))
                            somechanges = True
                            break
                    if somechanges:
                        break
            todo = todo or somechanges
            if not somechanges:
                newld.append(d)
        ld = newld

    logger.debug('Expand in %d loops', nbpass)
    return list(ld)


class GetByTagMeta(type):
    """Meta class constructor for :class:`GetByTag`.

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

    def __call__(self, *args, **kw):
        return self.__new__(self, *args, **kw)


@six.add_metaclass(GetByTagMeta)
class GetByTag(object):
    """
    Utility to retrieve a new/existing object by a special argument named ``tag``.
    If an object had already been created with that tag, return this object.
    """

    _tag_default = 'default'

    #: If set to False, unless new=True is specified, it won't be allowed to
    #: create new objects (a RuntimeError will be thrown).
    _tag_implicit_new = True

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
            if not cls._tag_implicit_new and not new:
                cls._tag_implicit_new_error(tag)
            newobj = super(GetByTag, cls).__new__(cls)
            newobj._tag = tag
            cls._tag_table[tag] = newobj
            newobj.__init__(*args, **kw)
        return newobj

    @classmethod
    def _tag_implicit_new_error(cls, tag):
        """Called whenever a tag does not exist and _tag_implicit_new = False."""
        raise RuntimeError(("It's not allowed to create a new {:s} object (new tag={:s}) "
                            "without an explicit new=True argument.").format(cls.__name__, tag))

    @property
    def tag(self):
        return self._tag

    @classmethod
    def tag_clean(cls, tag):
        """By default, return the actual tag."""
        return tag

    @classmethod
    def tag_keys(cls):
        """Return an alphabetically ordered list of actual keys of the objects instantiated."""
        return sorted(cls._tag_table.keys())

    @classmethod
    def tag_values(cls):
        """Return a non-ordered list of actual values of the objects instantiated."""
        return list(cls._tag_table.values())

    @classmethod
    def tag_items(cls):
        """Proxy to the ``items`` method of the internal dictionary table of objects."""
        return list(cls._tag_table.items())

    @classmethod
    def tag_check(cls, tag):
        """Check if the tag is in list of actual keys of the objects instanciated."""
        return (tag in cls._tag_table.keys())

    @classmethod
    def tag_focus(cls, select='default'):
        """Return the tag value of the actual object with focus according to the ``select`` value."""
        return cls._tag_focus[select]

    @classmethod
    def set_focus(cls, obj, select='default'):
        """Define a new tag value for the focus in the scope of the ``select`` value."""
        # Do the sanity checks
        obj.focus_gain_allow()
        # Call the hook on the previous default object
        prev_focus = cls._tag_focus[select]
        if prev_focus is not None:
            prev_obj = cls(prev_focus)
            prev_obj.focus_loose_hook()
        # Actually change the default
        cls._tag_focus[select] = obj.tag
        # Call the hook on the new default object
        obj.focus_gain_hook()

    def has_focus(self, select='default'):
        """Return a boolean value on equality of current tag and focus tag."""
        return self.tag == self.__class__._tag_focus[select]

    def catch_focus(self, select='default'):
        """The current object decides to be on focus !"""
        self.set_focus(self, select)

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

    def focus_loose_hook(self):
        """This method is called when an object looses the focus."""
        pass

    def focus_gain_allow(self):
        """This method is called on the target object prior to any focus change.

        It might be useful if one wants to perform checks and raise an exception.
        """
        pass

    def focus_gain_hook(self):
        """This method is called when an object gains the focus."""
        pass


class Catalog(object):
    """Abstract class for managing a collection of *items*.

    The interface is very light : :meth:`clear` and :meth:`refill` !
    Of course a catalog is an iterable object. It is also callable,
    and then returns a copy of the list of its items.
    """

    def __init__(self, **kw):
        logger.debug('Abstract %s init', self.__class__)
        self._items = kw.pop('items', list())
        self.weak = kw.pop('weak', False)
        self.__dict__.update(kw)

    @classmethod
    def fullname(cls):
        """Returns a nicely formatted name of the current class (dump usage)."""
        return '{0:s}.{1:s}'.format(cls.__module__, cls.__name__)

    @property
    def filled(self):
        """Boolean value, true if there is at least one item in the catalog."""
        return bool(self._items)

    def _get_weak(self):
        """Boolean value, true if the catalog is built with weak references."""
        return self._weak

    def _set_weak(self, switch):
        """Set boolean value, true if the catalog should be made of weak references."""
        self._weak = bool(switch)
        if self._weak:
            self._items = WeakSet(self._items)
        else:
            self._items = set(self._items)

    weak = property(_get_weak, _set_weak)

    def items(self):
        """A list, copy of the catalog items."""
        return list(self._items)

    def __iter__(self):
        """Catalog is iterable... at least!"""
        for c in self._items:
            yield c

    def __call__(self):
        return list(self.items())

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
        for k, v in [(k, v) for k, v in six.iteritems(tmpdict) if k != self.remap(k)]:
            del tmpdict[k]
            tmpdict[self.remap(k)] = v
        super(SpecialDict, self).__init__(tmpdict)

    def show(self, ljust=24):
        """Print the actual values of the dictionary."""
        for k in sorted(self.keys()):
            print('+', k.ljust(ljust), '=', self.get(k))

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
        """Force remapped key retrieval."""
        return dict.__getitem__(self, self.remap(key))

    def __setitem__(self, key, value):
        """Force remapped key setting."""
        dict.__setitem__(self, self.remap(key), value)

    def __delitem__(self, key):
        """Force remapped key deletion."""
        dict.__delitem__(self, self.remap(key))

    def __contains__(self, key):
        """Force remapped key ``in`` checking."""
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


class FoxyFormatter(string.Formatter):
    """A string formatter that may try to call an argument-less method."""

    def get_field(self, field_name, args, kwargs):
        """Given a **field_name**, find the object it references."""
        obj, used_key = super(FoxyFormatter, self).get_field(field_name, args, kwargs)
        if callable(obj):
            obj = obj()
        return (obj, used_key)
