#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
Some general pupose decorators.
"""

#: Automatic export of most convenient decorators.
__all__ = ['disabled', 'printargs', 'timelimit']

import time
from vortex.autolog import logdefault as logger


def nicedeco(decorator):
    """This decorator enforces that the resulting decorated functions looks like the original one."""
    def new_decorator(f):
        g = decorator(f)
        g.__name__ = f.__name__
        g.__doc__ = f.__doc__
        g.__dict__.update(f.__dict__)
        return g
    return new_decorator


@nicedeco
def disabled(func):
    """This decorator disables the provided function, and does nothing."""
    def empty_func(*args, **kw):
        pass
    return empty_func


@nicedeco
def printargs(func):
    """This decorator prints out the arguments passed to a function before calling it."""
    argnames = func.func_code.co_varnames[:func.func_code.co_argcount]
    fname = func.func_name

    def echo_func_args(*args, **kw):
        print '> > >', fname, '(', ', '.join(
            '%s=%r' % entry
            for entry in zip(argnames, args) + kw.items()), ')'
        return func(*args, **kw)
    return echo_func_args


def timelimit(nbsec):
    """This decorator warn if the function is more than ``nbsec`` seconds long."""
    @nicedeco
    def internal_decorator(func):
        def timed_func(*args, **kw):
            t0 = time.time()
            results = func(*args, **kw)
            tt = time.time() - t0
            if tt >= nbsec:
                logger.warn('Function %s took %f seconds', func.func_name, tt)
            return results
        return timed_func
    return internal_decorator