#!/bin/env python
# -*- coding:Utf-8 -*-

r"""
The :mod:`vortex` syntax mostly deals with attributes resolution and arguments expansion.
The most important usage is done by :class:`BFootprint` derivated objects.
"""

#: No automatic export
__all__ = []

import logging, re, copy
from footprint import BFootprint, Footprint


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
            logging.error('Expansion is getting messy... (%d) ?', nbpass)
            break
        for i, d in enumerate(ld):
            for k, v in d.iteritems():
                if type(v) == list or type(v) == tuple or type(v) == set:
                    logging.info(' > List %s', v)
                    ld[i:i+1] = map(lambda x: inplace(d, k, x), v)
                    todo = True
                    break
                if type(v) == str and re.search(',', v):
                    logging.info(' > Coma string %s', v)       
                    ld[i:i+1] = map(lambda x: inplace(d, k, x), v.split(','))
                    todo = True
                    break

    logging.debug('Expand in %d loops', nbpass)       
    return ld


if __name__ == '__main__':
    import doctest
    doctest.testmod()
    
