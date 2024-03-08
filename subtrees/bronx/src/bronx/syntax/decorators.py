"""
Useful decorators.
"""

import inspect
import time
from functools import wraps

#: No automatic export
__all__ = []


def nicedeco(decorator):
    """
    A decorator of decorator, this decorator enforces that the resulting
    decorated functions looks like the original one.
    """

    def new_decorator(f):
        g = decorator(f)
        g.__name__ = f.__name__
        g.__doc__ = f.__doc__
        g.__dict__.update(f.__dict__)
        return g

    return new_decorator


def nicedeco_plusdoc(doc_bonus):
    """
    A decorator of decorator, this decorator enforces that the resulting
    decorated functions looks like the original one but an extra bit of
    documentation is added.
    """

    def nicedeco_doc(decorator):
        def new_decorator(f):
            g = decorator(f)
            g.__name__ = f.__name__
            g.__doc__ = (f.__doc__ +
                         doc_bonus.format(name=f.__name__))
            g.__dict__.update(f.__dict__)
            return g

        return new_decorator

    return nicedeco_doc


@nicedeco
def disabled(func):  # @UnusedVariable
    """This decorator disables the provided function, and does nothing."""

    def empty_func(*args, **kw):
        pass

    return empty_func


def printargs(func):
    """This decorator prints out the arguments passed to a function
    before calling it, including parameters names and effective values.
    """

    @wraps(func)
    def echo_func_args(*args, **kwargs):
        func_args = inspect.signature(func).bind(*args, **kwargs).arguments
        args_str = ", ".join(['{}={}'.format(k, v) for k, v in func_args.items()])
        print("> > > {}::{}({})".format(func.__module__, func.__qualname__, args_str))
        return func(*args, **kwargs)

    return echo_func_args


@printargs
def printargs_pytest(a, b=4, c="blah-blah", *args, **kwargs):
    """Documentation for the function.

    >>> printargs_pytest(1)
    > > > decorators::printargs_pytest(a=1)
    >>> printargs_pytest(1, 2)
    > > > decorators::printargs_pytest(a=1, b=2)
    >>> printargs_pytest(1, d=4)
    > > > decorators::printargs_pytest(a=1, kwargs={'d': 4})
    >>> printargs_pytest(1, 2, 3, 7, d=4, e=5)
    > > > decorators::printargs_pytest(a=1, b=2, c=3, args=(7,), kwargs={'d': 4, 'e': 5})
    >>> printargs_pytest.__doc__.startswith('Documentation for the function.')
    True
    >>> print(printargs_pytest.__name__)
    printargs_pytest
    >>> list(printargs_pytest.__dict__.keys())
    ['__wrapped__']
    """
    pass


def timelimit(logger, nbsec):
    """This decorator warns if the function is more than ``nbsec`` seconds long."""

    @nicedeco
    def internal_decorator(func):
        def timed_func(*args, **kw):
            t0 = time.time()
            results = func(*args, **kw)
            tt = time.time() - t0
            if tt >= nbsec:
                logger.warn('Function %s took %f seconds', func.__name__, tt)
            return results

        return timed_func

    return internal_decorator


@nicedeco
def secure_getattr(func):
    """
    This decorator is to be used on __getattr__ methods to ensure that essential
    method such as __getstate__/__setstate__ are not looked for.
    """

    def secured_getattr(self, key):
        # Avoid nasty interactions when copying/pickling
        if key in ('__bases__',
                   '__deepcopy__', '__copy__',
                   '__reduce__', '__reduce_ex__',
                   '__getinitargs__', '__getnewargs__', '__getnewargs_ex__',
                   '__getstate__', '__setstate__'):
            raise AttributeError(key)
        else:
            return func(self, key)

    return secured_getattr
