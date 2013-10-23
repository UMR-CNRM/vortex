#!/bin/env python
# -*- coding:Utf-8 -*-

"""
Utility functions of the :mod:`footprints` package.
"""

#: No automatic export
__all__ = []

import re, copy, glob

import logging
logger = logging.getLogger('footprints.util')

from weakref import WeakSet


def dictmerge(d1, d2):
    """
    Merge two dictionaries d1 and d2 with a recursive function (d1 and d2 can be dictionaries of dictionaries).
    The result is in d1.
    If keys exist in d1 and d2, d1 keys are replaced by d2 keys.

    >>> dictmerge({'name':'clim','attr':{'model':{'values':('arpege','arome')}}},{'name':'clim model','attr':{'truncation':{'type':'int','optional':'False'}}})
    {'name': 'clim model', 'attr': {'model': {'values': ('arpege', 'arome')}, 'truncation': {'optional': 'False', 'type': 'int'}}}

    >>> dictmerge({'a':'1'},{'b':'2'})
    {'a': '1', 'b': '2'}

    >>> dictmerge({'a':'1','c':{'d':'3','e':'4'},'i':{'b':'2','f':{'g':'5'}}}, {'c':{'h':'6', 'e':'7'}})
    {'a': '1', 'i': {'b': '2', 'f': {'g': '5'}}, 'c': {'h': '6', 'e': '7', 'd': '3'}}
    """

    for key, value in d2.iteritems():
        if type(value) == type(dict()):
            if d1.has_key(key):
                dictmerge(d1[key], d2[key])
            else :
                d1[key] = value
        else:
            d1[key] = value

    return d1


def list2dict(a, klist):
    """
    Convert any list value in a merged dictionary for the specified top entries
    of the ``klist`` from the dictionnary ``a``.
    """

    for k in klist:
        if k in a and type(a[k]) != dict:
            ad = dict()
            for item in a[k]:
                ad.update(item)
            a[k] = ad
    return a


def rangex(start, end=None, step=None, shift=None, fmt=None):
    """
    Extended range expansion.

    When ``start`` is already a complex definition (as a string), ``end`` and ``step`` only apply
    as default when the sub-definition in ``start`` does not contain any ``end`` or ``step`` value.

    >>> rangex(2)
    [2]
    """
    rangevalues = list()

    for pstart in str(start).split(','):

        if re.search('_', pstart):
            prefix, realstart = pstart.split('_')
        else:
            prefix = None
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
            realend = realend - 1
        else:
            realend = realend + 1
        if shift != None:
            realshift = int(shift)
            realstart = realstart + realshift
            realend = realend + realshift

        pvalues = range(realstart, realend, realstep)
        if prefix:
            pvalues = [ prefix + '_' + str(x) for x in pvalues ]
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
        for k in [ x for x in newd.keys() if (x != key and type(newd[x]) == str)]:
            for g in globs.keys():
                newd[k] = re.sub('\[glob:'+g+'\]', globs[g], newd[k])
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
        nbpass = nbpass + 1
        if nbpass > 100:
            logger.error('Expansion is getting messy... (%d) ?', nbpass)
            break
        for i, d in enumerate(ld):
            for k, v in d.iteritems():
                if isinstance(v, list) or isinstance(v, tuple) or isinstance(v, set):
                    logger.debug(' > List expansion %s', v)
                    ld[i:i+1] = [ inplace(d, k, x) for x in v ]
                    todo = True
                    break
                if isinstance(v, str) and re.match('range\(\d+(,\d+)?(,\d+)?\)$', v, re.IGNORECASE):
                    logger.debug(' > Range expansion %s', v)
                    lv = [ int(x) for x in re.split('[\(\),]+', v) if re.match('\d+$', x) ]
                    if len(lv) < 2:
                        lv.append(lv[0])
                    lv[1] += 1
                    ld[i:i+1] = [ inplace(d, k, x) for x in range(*lv) ]
                    todo = True
                    break
                if isinstance(v, str) and re.search(',', v):
                    logger.debug(' > Coma separated string %s', v)
                    ld[i:i+1] = [ inplace(d, k, x) for x in v.split(',') ]
                    todo = True
                    break
                if isinstance(v, str) and re.search('{glob:', v):
                    logger.debug(' > Globbing from string %s', v)
                    vglob = v
                    globitems = list()
                    def getglob(matchobj):
                        globitems.append([matchobj.group(1), matchobj.group(2)])
                        return '*'
                    while ( re.search('{glob:', vglob) ):
                        vglob = re.sub('{glob:(\w+):([^\}]+)}', getglob, vglob)
                    ngrp = 0
                    while ( re.search('{glob:', v) ):
                        v = re.sub('{glob:\w+:([^\}]+)}', '{'+str(ngrp)+'}', v)
                        ngrp += 1
                    v = v.replace('+', '\+')
                    v = v.replace('.', '\.')
                    ngrp = 0
                    while ( re.search('{\d+}', v) ):
                        v = re.sub('{\d+}', '('+globitems[ngrp][1]+')', v)
                        ngrp += 1
                    repld = list()
                    for filename in glob.glob(vglob):
                        m = re.search(r'^'+v+ r'$', filename)
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
        self._filled = bool(self._items)
        self.__dict__.update(kw)

    @classmethod
    def fullname(self):
        """Returns a nicely formated name of the current class (dump usage)."""
        return '{0:s}.{1:s}'.format(self.__module__, self.__name__)

    def items(self):
        return list(self._items)

    def __iter__(self):
        """Catalog is iterable... at least!"""
        for c in self._items:
            yield c

    def __call__(self):
        return self.items()

    def __len__(self):
        return len(self._items)

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
        self._items = set()


if __name__ == '__main__':
    import doctest
    doctest.testmod()
