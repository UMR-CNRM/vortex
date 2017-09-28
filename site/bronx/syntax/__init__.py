#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
*syntax* sub-module:

Syntaxic useful tools.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import os
import sys
from contextlib import contextmanager

import footprints.loggers

logger = footprints.loggers.getLogger(__name__)

#: No automatic export
__all__ = []


# TODO: rajouter nicedeco & co ? (j'en ai une copie dans epygram...)


def str2dict(string, try_convert=None):
    """
    Parse a **string** (of syntax 'key1:value1,key2=value2') to a dict.

    :param try_convert: try to convert values as type **try_convert**,
                        e.g. try_convert=int
    """
    if ':' not in string and '=' not in string:
        raise SyntaxError("string: '{}' is not convertible to a dict".format(string))
    d = {i.replace('=', ':').split(':')[0].strip() : i.replace('=', ':').split(':')[1].strip()
         for i in string.split(',')}
    if try_convert is not None:
        for k, v in d.items():
            try:
                d[k] = try_convert(v)
            except ValueError:
                pass
    return d


def soft_string(s, escaped_characters={' ':'_',
                                       '{':'', '}':'',
                                       '(':'', ')':'',
                                       '[':'', ']':'',
                                       '*':''}):
    """
    Returns str(*s*) escaping special characters that may
    be forbidden in filenames.

    :param escaped_characters: special characters to escape,
                               and their replacement in case.
    """
    result = str(s).strip()
    for repl in escaped_characters.items():
        result = result.replace(*repl)
    return result


def stretch_array(array):
    """
    Return array.flatten() or compressed(), whether the array is
    masked or not.
    """
    import numpy
    if isinstance(array, numpy.ma.masked_array):
        array = array.compressed()
    elif isinstance(array, numpy.ndarray):
        array = array.flatten()
    else:
        raise NotImplementedError('type: {} array'.format(type(array)))
    return array
