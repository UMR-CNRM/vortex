#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
TODO module description.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

from . import pools

#: No automatic export
__all__ = []


def ask(**kw):
    """Build a proper request to Jeeves."""

    # default date is the actual pool stamp
    kw.setdefault('date', pools.timestamp())

    # build a proper json filename if requested
    kw.setdefault('jtag', kw.pop('jfile', 'depot/config'))

    # at least get a request object
    jr = pools.Request(**kw)

    # dump the json file if any
    if jr.jtag is not None:
        jr.dump()

    return jr


def ask_active(*args):
    """Switch on the specified pools."""
    return ask(todo='active', data=args)


def ask_any(**kw):
    """Ask for some miscellaneous action..."""
    kw.setdefault('todo', 'foo')
    kw.setdefault('jtag', kw.pop('jfile', 'depot/' + kw['todo']))
    return ask(**kw)


def ask_conf():
    """Wrapper for configuration display."""
    return ask(todo='show')


def ask_debug():
    """Switch log verbosity to DEBUG level."""
    return ask(todo='level', data='debug')


def ask_level(value):
    """Switch log verbosity to sepcified level."""
    return ask(todo='level', data=str(value))


def ask_mute(*args):
    """Switch off the specified pools."""
    return ask(todo='mute', data=args)


def ask_on(*args):
    """Switch on the specified actions."""
    return ask(todo='seton', data=args)


def ask_off(*args):
    """Switch off the specified actions."""
    return ask(todo='setoff', data=args)


def ask_reload(*args):
    """Force reload of the ini file and pool creation."""
    if not args:
        args = ('config', 'mkpools')
    return ask(todo='reload', data=args)


def ask_sleep(duration=30):
    """Make the server perfom a little nap."""
    return ask(todo='sleep', data=int(duration))


def ask_update(**kw):
    """Wrapper for configuration update and display."""
    return ask(todo='update', data=kw)
