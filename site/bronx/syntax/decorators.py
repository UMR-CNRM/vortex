#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Useful decorators.
"""

from __future__ import print_function, absolute_import, unicode_literals, division


#: No automatic export
__all__ = []

# TODO: import whole vortex.util.decorators as such ?


def nicedeco(decorator):
    """
    A decorator of decorator, for the decorated method to keep the original
    __name__, __doc__ and __dict__.
    """
    def new_decorator(f):
        g = decorator(f)
        g.__name__ = f.__name__
        g.__doc__ = f.__doc__
        g.__dict__.update(f.__dict__)
        return g
    return new_decorator
