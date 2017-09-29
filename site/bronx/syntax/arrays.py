#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Syntaxic useful tools.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import numpy

import footprints.loggers

logger = footprints.loggers.getLogger(__name__)

#: No automatic export
__all__ = []


def stretch_array(array):
    """
    Return array.flatten() or compressed(), whether the array is
    masked or not.
    """
    if isinstance(array, numpy.ma.masked_array):
        array = array.compressed()
    elif isinstance(array, numpy.ndarray):
        array = array.flatten()
    else:
        raise NotImplementedError('type: {} array'.format(type(array)))
    return array
