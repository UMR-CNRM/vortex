#!/bin/env python
# -*- coding:Utf-8 -*-

r"""
The :mod:`vortex` syntax mostly deals with attributes resolution and arguments expansion.
The most important usage is done by :class:`BFootprint` derivated objects.
"""

#: No automatic export
__all__ = []

import re, copy
from vortex.autolog import logdefault as logger
from footprint import BFootprint, Footprint


def rangex(start, end=None, step=None, shift=None):
    """Extended range exansion."""
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
        elif end == None:
            realend = realstart
        else:
            realend = end
        realend = int(realend)

        if len(actualrange) > 2:
            realstep = actualrange[2]
        elif step == None:
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

def inplace(desc, key, value):
    """
    Redefined the ``key`` value in a deep copy of the description ``desc``.

    >>> inplace({'test':'alpha'}, 'ajout', 'beta')
    {'test': 'alpha', 'ajout': 'beta'}

    >>> inplace({'test':'alpha', 'recurs':{'a':1, 'b':2}}, 'ajout', 'beta')
    {'test': 'alpha', 'ajout': 'beta', 'recurs': {'a': 1, 'b': 2}}

    """
    newd = copy.deepcopy(desc)
    newd[key] = value
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
                    logger.info(' > List expansion %s', v)
                    ld[i:i+1] = [ inplace(d, k, x) for x in v ]
                    todo = True
                    break
                if isinstance(v, str) and re.match('range\(\d+(,\d+)?(,\d+)?\)$', v, re.IGNORECASE):
                    logger.info(' > Range expansion %s', v)
                    lv = [ int(x) for x in re.split('[\(\),]+', v) if re.match('\d+$', x) ]
                    if len(lv) < 2:
                        lv.append(lv[0])
                    lv[1] += 1
                    ld[i:i+1] = [ inplace(d, k, x) for x in range(*lv) ]
                    todo = True
                    break
                if isinstance(v, str) and re.search(',', v):
                    logger.info(' > Coma separated string %s', v)
                    ld[i:i+1] = [ inplace(d, k, x) for x in v.split(',') ]
                    todo = True
                    break

    logger.debug('Expand in %d loops', nbpass)       
    return ld


if __name__ == '__main__':
    import doctest
    doctest.testmod()
    
